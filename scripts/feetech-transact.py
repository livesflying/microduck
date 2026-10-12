#!/usr/bin/env python3
"""Print raw Feetech SCS/STS serial transactions.

This is a bench diagnostic tool. Stop robotd before using it, otherwise two
processes will read and write the same half-duplex bus and the dump is not
meaningful.
"""

import argparse
import os
import select
import shutil
import subprocess
import sys
import termios
import time


PING = 0x01
READ_DATA = 0x02
WRITE_DATA = 0x03
REBOOT = 0x08

POSITION = 56
PRESENT_VOLTAGE = 62
PRESENT_TEMPERATURE = 63

DEFAULT_IDS = [20, 21, 22, 23, 24, 30, 31, 32, 33, 34, 10, 11, 12, 13, 14]
DEFAULT_PORT = "/dev/serial/by-id/usb-1a86_USB_Single_Serial_5C84287064-if00"


def hex_bytes(data):
    return " ".join(f"{byte:02x}" for byte in data)


def checksum(body):
    return (~sum(body)) & 0xFF


def packet(servo_id, instruction, params):
    body = [servo_id, len(params) + 2, instruction, *params]
    return bytes([0xFF, 0xFF, *body, checksum(body)])


def parse_int(value):
    return int(value, 0)


def check_port_owner(path, force):
    if force or not shutil.which("fuser"):
        return
    try:
        result = subprocess.run(
            ["fuser", "-v", path],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
    except OSError:
        return
    if result.returncode == 0 and result.stdout.strip():
        print(result.stdout.rstrip(), file=sys.stderr)
        raise SystemExit(
            f"{path} is in use. Stop robotd first, or rerun with --force if this is intentional."
        )


def open_serial(path, baud):
    fd = os.open(path, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    try:
        attrs = termios.tcgetattr(fd)
        try:
            speed = getattr(termios, f"B{baud}")
        except AttributeError as exc:
            raise SystemExit(f"termios on this system does not expose B{baud}") from exc

        attrs[0] = 0
        attrs[1] = 0
        attrs[2] = termios.CS8 | termios.CLOCAL | termios.CREAD
        attrs[3] = 0
        attrs[4] = speed
        attrs[5] = speed
        attrs[6][termios.VMIN] = 0
        attrs[6][termios.VTIME] = 0
        termios.tcsetattr(fd, termios.TCSANOW, attrs)
        termios.tcflush(fd, termios.TCIOFLUSH)
        return fd
    except Exception:
        os.close(fd)
        raise


def read_some(fd, deadline, max_len=256):
    chunks = []
    while time.monotonic() < deadline:
        left = max(0.0, deadline - time.monotonic())
        ready, _, _ = select.select([fd], [], [], left)
        if not ready:
            break
        try:
            chunk = os.read(fd, max_len)
        except BlockingIOError:
            continue
        if not chunk:
            continue
        chunks.append(chunk)
        if len(chunk) < max_len:
            break
    return b"".join(chunks)


def read_exact(fd, length, deadline, label):
    out = bytearray()
    while len(out) < length:
        left = max(0.0, deadline - time.monotonic())
        if left <= 0:
            raise TimeoutError(f"timeout reading {label}: got {len(out)}/{length} bytes")
        ready, _, _ = select.select([fd], [], [], left)
        if not ready:
            continue
        chunk = os.read(fd, length - len(out))
        if chunk:
            print(f"RX chunk ({label}) {hex_bytes(chunk)}")
            out.extend(chunk)
    return bytes(out)


def read_status(fd, servo_id, timeout):
    deadline = time.monotonic() + timeout
    header = read_exact(fd, 4, deadline, "header")
    if header[:2] != b"\xff\xff" or header[2] != servo_id:
        extra = read_some(fd, time.monotonic() + 0.02)
        if extra:
            print(f"RX extra {hex_bytes(extra)}")
        return {
            "ok": False,
            "full": header + extra,
            "reason": f"bad header for id {servo_id}: {hex_bytes(header)}",
        }

    length = header[3]
    if not 2 <= length <= 64:
        extra = read_some(fd, time.monotonic() + 0.02)
        if extra:
            print(f"RX extra {hex_bytes(extra)}")
        return {
            "ok": False,
            "full": header + extra,
            "reason": f"bad length for id {servo_id}: {length}",
        }

    tail = read_exact(fd, length, deadline, "tail")
    full = header + tail
    expected = checksum(full[2:-1])
    error = full[4]
    data = full[5:-1]
    ok = full[-1] == expected and error == 0
    reason = "ok"
    if full[-1] != expected:
        reason = f"bad checksum got=0x{full[-1]:02x} expected=0x{expected:02x}"
    elif error != 0:
        reason = f"servo returned error=0x{error:02x}"
    return {
        "ok": ok,
        "full": full,
        "id": full[2],
        "length": length,
        "error": error,
        "data": data,
        "checksum": full[-1],
        "expected_checksum": expected,
        "reason": reason,
    }


def transact(fd, servo_id, instruction, params, timeout, expect_reply=True):
    tx = packet(servo_id, instruction, params)
    termios.tcflush(fd, termios.TCIFLUSH)
    print(f"TX id={servo_id} inst=0x{instruction:02x} params={hex_bytes(params)}")
    print(f"TX raw {hex_bytes(tx)}")
    os.write(fd, tx)
    termios.tcdrain(fd)
    if not expect_reply:
        print("RX skipped")
        return None
    rx = read_status(fd, servo_id, timeout)
    print(f"RX raw {hex_bytes(rx['full'])}")
    if "id" in rx:
        print(
            "RX parsed "
            f"id={rx['id']} len={rx['length']} error=0x{rx['error']:02x} "
            f"data={hex_bytes(rx['data'])} checksum=0x{rx['checksum']:02x} "
            f"expected=0x{rx['expected_checksum']:02x}"
        )
    print(f"RESULT {'OK' if rx['ok'] else 'BAD'} {rx['reason']}")
    return rx


def read_reg(fd, servo_id, address, length, timeout):
    return transact(fd, servo_id, READ_DATA, [address, length], timeout)


def status(fd, servo_id, timeout):
    print(f"\n== id {servo_id} position/speed ==")
    pos = read_reg(fd, servo_id, POSITION, 4, timeout)
    print(f"\n== id {servo_id} voltage ==")
    volt = read_reg(fd, servo_id, PRESENT_VOLTAGE, 1, timeout)
    print(f"\n== id {servo_id} temperature ==")
    temp = read_reg(fd, servo_id, PRESENT_TEMPERATURE, 1, timeout)

    if pos and pos["ok"] and len(pos["data"]) == 4:
        raw_pos = int.from_bytes(pos["data"][:2], "little")
        raw_speed = int.from_bytes(pos["data"][2:4], "little")
        print(f"DECODE id={servo_id} position_raw={raw_pos} speed_raw=0x{raw_speed:04x}")
    if volt and volt["ok"] and len(volt["data"]) == 1:
        print(f"DECODE id={servo_id} voltage={volt['data'][0] / 10.0:.1f}V")
    if temp and temp["ok"] and len(temp["data"]) == 1:
        print(f"DECODE id={servo_id} temperature={temp['data'][0]}C")


def main():
    parser = argparse.ArgumentParser(
        description="Send Feetech SCS/STS packets and print raw TX/RX bytes."
    )
    parser.add_argument("--port", default=DEFAULT_PORT)
    parser.add_argument("--baud", type=int, default=1000000)
    parser.add_argument("--timeout", type=float, default=0.08)
    parser.add_argument("--force", action="store_true", help="do not refuse when fuser sees the port in use")

    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("ping", help="send PING to one id")
    p.add_argument("id", type=parse_int)

    p = sub.add_parser("read", help="read one register block")
    p.add_argument("id", type=parse_int)
    p.add_argument("address", type=parse_int)
    p.add_argument("length", type=parse_int)

    p = sub.add_parser("write", help="write bytes to one register; use carefully")
    p.add_argument("id", type=parse_int)
    p.add_argument("address", type=parse_int)
    p.add_argument("data", nargs="+", type=parse_int)

    p = sub.add_parser("reboot", help="send servo reboot instruction")
    p.add_argument("id", type=parse_int)

    p = sub.add_parser("status", help="read position/speed, voltage and temperature")
    p.add_argument("ids", nargs="*", type=parse_int, default=DEFAULT_IDS)

    args = parser.parse_args()
    check_port_owner(args.port, args.force)
    fd = open_serial(args.port, args.baud)
    try:
        print(f"OPEN port={args.port} baud={args.baud} timeout={args.timeout}s")
        if args.command == "ping":
            transact(fd, args.id, PING, [], args.timeout)
        elif args.command == "read":
            transact(fd, args.id, READ_DATA, [args.address, args.length], args.timeout)
        elif args.command == "write":
            data = [byte & 0xFF for byte in args.data]
            transact(fd, args.id, WRITE_DATA, [args.address, *data], args.timeout)
        elif args.command == "reboot":
            transact(fd, args.id, REBOOT, [], args.timeout)
        elif args.command == "status":
            for servo_id in args.ids:
                status(fd, servo_id, args.timeout)
    finally:
        os.close(fd)


if __name__ == "__main__":
    main()
