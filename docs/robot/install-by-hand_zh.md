# 手动安装，逐步进行

`scripts/provision-board.sh` 执行的操作，作为单独的命令。在需要单独测试某个步骤时使用；在只需要一个可用的板子时使用 `provision-board.sh`。

## 复制文件

从你机器上的克隆版本。复制到 `~`，**不是** `/tmp` — 中间有一个重启，`/tmp` 在重启后不会保留。
```bash
scp scripts/setup-board.sh scripts/migrate-network.sh pierre@192.168.1.42:~/
```

```bash
scp scripts/install.sh deploy/dev-key/team.dev.pub pierre@192.168.1.42:~/
```
## 重启前

先创建 `robot` 组，这样在重启后成员身份立即生效，而不是需要再次创建：
```bash
sudo groupadd --system robot
```

```bash
sudo usermod -aG robot "$USER"
```
板卡 bring-up — 设备树覆盖，内核控制台关闭电机UART，getty屏蔽，
`Privacy = device`，onnxruntime：
```bash
sudo sh ~/setup-board.sh
```
网络 — netplan到NetworkManager：
```bash
sudo sh ~/migrate-network.sh
```

```bash
sudo reboot
```
重启是必不可少的：设备树覆盖和网络栈无法在运行中的内核下进行交换。

## 重启之后

两者都会再次生效。它们是幂等的，第二次运行 `migrate-network.sh` 是为了退役那个会使得在任何无线网络连接慢的启动时板卡恢复为 netplan 的无线回退机制：
```bash
sudo sh ~/setup-board.sh
```

```bash
sudo sh ~/migrate-network.sh
```
然后是守护进程。`install.sh` 从环境变量中读取其设置，而 `sudo -E` 则确保这些设置能够通过：
```bash
export DUCK_TOKEN=github_pat_replace_with_your_token
```

```bash
export DUCK_REF=main
```

```bash
export DUCK_DEV_KEY=$HOME/team.dev.pub
```

```bash
sudo -E sh ~/install.sh
```
Drop `DUCK_DEV_KEY` 仅保留应只安装发布的板子。将 `DUCK_REF` 设置为一个分支以安装该分支最后构建的内容。

在 `setup-board.sh` 脚本中设置 `DUCK_WEIRD_BLE=1` 是 `--weird-ble`：对于一个蓝牙完全无法与手柄配对的板子。请参阅 [pair-a-gamepad.md](pair-a-gamepad_zh.md)。

设置 `DUCK_NO_START=1` 会安装发布版、单元、用户和组，但不会启用任何内容 —— 甚至不会为下次启动启用任何内容。它还会停止并禁用之前安装留下的任何守护进程，因此无论卡是否全新，状态都是一样的。用于分离板级故障与守护进程：重启进入没有我们任何内容运行的板子，测试，然后逐个启用它们。
```bash
sudo -E DUCK_NO_START=1 sh ~/install.sh
```

```bash
sudo reboot
```
The 重启 是其中的一部分，而不是整洁。发布的 `hooks/postinstall` 会在 `install.sh` 能够停止它们之前启用并启动每一个守护进程，因此无论旋钮如何设置，它们在那次启动时已经运行过——并且一个守护进程不会撤销它在死亡前对子系统的更改。`btd` 会留下 `Pairable` 设置、一个广告实例，以及适配器默认配对代理赋予的 IO 能力。

要让它再次成为一台可用的机器人：
```bash
sudo systemctl enable --now updaterd robotd configd btd padd
```
命名它，如果你想要一个名称：
```bash
robotctl system set-name duck-01
```
## GStreamer, 用于支持流媒体的板卡

配置默认会启用 GStreamer — 在 `provision-board.sh` 中使用 `--no-gstreamer` 可跳过此步骤（此处为 `DUCK_GSTREAMER=0`）。无论是否启用，都不需要重启，因此可以在任何时间手动在跳过了此步骤的板卡上运行。
```bash
scp scripts/setup-gstreamer.sh pierre@192.168.1.42:~/
```

```bash
sudo sh ~/setup-gstreamer.sh
```
It 打印出这块板子能编码的内容 — 哪些 `webrtc*` 元素被注册了，H.264 编码器是否可达，以及内核是否暴露了 VPU。在 Zero 3W 上，它报告 `/dev/mpp_service` 并没有 `v4l2h264enc`，这是 Rockchip BSP 内核预期的形态：VPU 通过 MPP 而不是 V4L2 达到，报告指出了两个 Radxa 包证明了这一点，表明它能够编码。在任何内核更改后重新运行它；这是改变答案的事件：
```bash
sudo /usr/local/sbin/robot-setup-gstreamer
```
添加 `--dev` 以同时安装头文件，在板子上或 aarch64 系统根目录下编译 `gst-plugin-webrtc`，或进行跨平台编译。

## 检查它
```bash
robotctl health
```

```bash
robotctl version
```
`robotd` 在一个机架板上报告无响应且带有未供电伺服电机是诚实的回答，而不是安装失败。

然后是游戏手柄——[`pair-a-gamepad.md`](pair-a-gamepad_zh.md):
```bash
sudo robotctl pad pair
```
