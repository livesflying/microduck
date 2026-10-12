#!/usr/bin/env python3
import argparse
import os
import select
import termios
import time


READ_DATA = 0x02
POSITION = 56
PRESENT_VOLTAGE = 62
PRESENT_TEMPERATURE = 63


def checksum(body):
    return (~sum(body)) & 0xFF


def packet(servo_id, instruction, params):
    body = [servo_id, len(params) + 2, instruction, *params]
    return bytes([0xFF, 0xFF, *body, checksum(body)])


def open_serial(path, baud):
    fd = os.open(path, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    attrs = termios.tcgetattr(fd)
    speed = getattr(termios, f"B{baud}")
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


def read_exact(fd, length, timeout):
    deadline = time.monotonic() + timeout
    out = bytearray()
    while len(out) < length:
        left = deadline - time.monotonic()
        if left <= 0:
            raise TimeoutError(f"timeout after {len(out)}/{length} bytes")
        ready, _, _ = select.select([fd], [], [], left)
        if not ready:
            continue
        chunk = os.read(fd, length - len(out))
        if chunk:
            out.extend(chunk)
    return bytes(out)


def transact(fd, servo_id, instruction, params, timeout):
    termios.tcflush(fd, termios.TCIFLUSH)
    os.write(fd, packet(servo_id, instruction, params))
    header = read_exact(fd, 4, timeout)
    if header[:2] != b"\xff\xff" or header[2] != servo_id:
        raise ValueError(f"bad header {header.hex(' ')}")
    length = header[3]
    tail = read_exact(fd, length, timeout)
    full = header + tail
    expected = checksum(full[2:-1])
    if full[-1] != expected:
        raise ValueError(f"bad checksum got=0x{full[-1]:02x} expected=0x{expected:02x}")
    err = full[4]
    return err, full[5:-1]


def read_reg(fd, servo_id, address, length, timeout):
    return transact(fd, servo_id, READ_DATA, [address, length], timeout)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("ids", nargs="*", type=int)
    parser.add_argument("--port", default="/dev/serial/by-id/usb-1a86_USB_Single_Serial_5C84287064-if00")
    parser.add_argument("--baud", default=1000000, type=int)
    parser.add_argument("--timeout", default=0.08, type=float)
    args = parser.parse_args()
    ids = args.ids or [20, 21, 22, 23, 24, 30, 31, 32, 33, 34, 10, 11, 12, 13, 14]
    fd = open_serial(args.port, args.baud)
    try:
        for servo_id in ids:
            try:
                pos_err, pos = read_reg(fd, servo_id, POSITION, 2, args.timeout)
                volt_err, volt = read_reg(fd, servo_id, PRESENT_VOLTAGE, 1, args.timeout)
                temp_err, temp = read_reg(fd, servo_id, PRESENT_TEMPERATURE, 1, args.timeout)
                raw = int.from_bytes(pos, "little")
                voltage = volt[0] / 10.0
                print(
                    f"id={servo_id:3d} raw={raw:4d} voltage={voltage:4.1f}V temp={temp[0]:3d}C "
                    f"errors=0x{pos_err:02x}/0x{volt_err:02x}/0x{temp_err:02x}"
                )
            except Exception as exc:
                print(f"id={servo_id:3d} ERROR {exc}")
    finally:
        os.close(fd)


if __name__ == "__main__":
    main()
