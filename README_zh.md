<p align="center">
  <img src="https://github.com/user-attachments/assets/c2f7c245-8217-46a1-8d1e-e0ba967cd969" alt="Microduck" width="820">
</p>

<h1 align="center">Microduck</h1>

<p align="center">
  <em>一款使用强化学习策略驱动的微型双足机器人。</em>
</p>

<p align="center">
  <a href="https://pollen-robotics.com/microduck"><b>购买 Microduck</b></a> ·
  <a href="docs/robot/cheatsheet_zh.md">使用速查表</a> ·
  <a href="https://github.com/pollen-robotics/microduck_rl">训练强化学习策略</a> ·
  <a href="docs/design/architecture_zh.md">系统架构</a> ·
  <a href="CONTRIBUTING.md">参与贡献</a>
</p>

<p align="center">
  <a href="https://github.com/pollen-robotics/microduck/actions/workflows/ci.yml"><img src="https://github.com/pollen-robotics/microduck/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
</p>

---

## 项目简介

这个仓库是 Microduck 的“大脑”。

Microduck 高约 25 cm、重约 800 g，运行在 Rockchip RK3566 平台上。系统包含一个
50 Hz 的控制循环，可驱动 15 个舵机，并负责运行神经网络策略、处理无线通信和摄像头
数据，以及安全地安装和回滚软件更新。

本仓库包含运行 Microduck 所需的大部分机器人端软件。如果你还没有机器人，可以在
[Pollen Robotics](https://pollen-robotics.com/microduck) 了解和购买。

机器人的强化学习策略不在本仓库中，而是在
[microduck_rl](https://github.com/pollen-robotics/microduck_rl) 中训练。该项目包含
MuJoCo 仿真、PPO 训练、sim-to-real 流程，以及导出为本仓库可加载的 ONNX 模型的工具。

## 能做什么

<table>
<tr>
<td width="50%">
  <video src="https://github.com/user-attachments/assets/356a6011-8e0d-4b28-bda9-da78646583a3" controls width="100%"></video>
</td>
<td width="50%">
  <video src="https://github.com/user-attachments/assets/abfbf250-1b1c-42cb-8430-00267e2b148a" controls width="100%"></video>
</td>
</tr>
<tr>
<td><b>行走</b>：连接游戏手柄即可控制机器人移动。</td>
<td><b>滚动</b>：安装轮子后按住十字键上方向，机器人会加载对应策略。</td>
</tr>
<tr>
<td width="50%">
  <video src="https://github.com/user-attachments/assets/7e70c1da-e120-428f-ae0b-f4de62f25984" controls width="100%"></video>
</td>
<td width="50%">
  <video src="https://github.com/user-attachments/assets/3eef63a5-6f84-47cf-90de-e717e6d7f8f0" controls width="100%"></video>
</td>
</tr>
<tr>
<td><b>拾取物体</b>：让机器人低头，按下一个按钮即可执行拾取动作。</td>
<td><b>自主起身</b>：即使被碰倒，机器人也可以自行恢复站立。</td>
</tr>
</table>

此外，Microduck 还支持坐下、踢球、按指令向前滚动，并能使用每台机器人独有的声音
进行鸣叫。

## 从哪里开始

### 你已经有一台机器人

| 文档 | 内容 |
| --- | --- |
| [使用速查表](docs/robot/cheatsheet_zh.md) | `robotctl` 的完整命令，包括移动、配置、声音、Wi-Fi、更新和日志。建议从这里开始。 |
| [连接游戏手柄](docs/robot/pair-a-gamepad_zh.md) | 游戏手柄配对、按键映射，以及无法绑定或连接中断时的排查方法。 |
| [`duckctl`](docs/robot/duckctl_zh.md) | 通过蓝牙从电脑控制机器人，不需要网络或 SSH。 |
| [软件更新](docs/robot/cheatsheet_zh.md#更新-updaterd) | 安装、回滚和锁定版本。每次更新都会校验，并经过健康检查，失败时自动回滚。 |

### 你正在开发机器人软件

| 文档 | 内容 |
| --- | --- |
| [microduck_rl](https://github.com/pollen-robotics/microduck_rl) | 强化学习策略的来源，包括 MuJoCo、PPO、域随机化和 ONNX 导出。 |
| [系统架构](docs/design/architecture_zh.md) | 服务划分、进程间通信、状态所有权、安全边界和更新流程。 |
| [搭建开发板](docs/robot/install-dev_zh.md) | 从空白开发板开始配置，使其能够安装分支构建版本。 |
| [开发者速查表](docs/robot/cheatsheet-dev_zh.md) | 分支构建、候选版本、从电脑控制机器人，以及更新后的重启注意事项。 |
| [推送分支构建](docs/robot/dev-push_zh.md) | 在本机编译后通过 SSH 安装到开发板，通常只需约一分钟。 |
| [贡献指南](CONTRIBUTING.md) | 构建、测试、代码布局、约定和发布流程。 |
| [文档索引](docs/README_zh.md) | 设计文档、项目记录、路线图和待设计功能的完整索引。 |

## 系统组成

这是一个不依赖大型框架的 Rust workspace。主要服务包括：

- `robotd`：拥有控制循环和电机总线，负责运行运动策略、姿态控制、声音和动作。
- `updaterd`：安装已签名的软件版本，并在健康检查失败时自动回滚。
- `configd`：管理 Wi-Fi、机器人身份、配对 PIN 和系统配置。
- `btd`：提供手机或其他客户端使用的蓝牙入口。
- `padd`：读取游戏手柄输入，并将其转换为机器人意图。
- `mediad`：通过 WebRTC 推送摄像头和麦克风数据，并提供远程控制通道。
- `tofd`：管理头部深度传感器并发布 ToF 数据。
- `robotctl`：运行在机器人上的命令行工具，用于诊断、控制和配置。
- `duckctl`：运行在电脑上的蓝牙客户端，不会随机器人版本部署。

服务之间通过 Unix socket 使用 JSON-RPC 通信，协议定义在
[`duck-ipc-proto`](duck-ipc-proto/) 中。手机应用、控制台、游戏手柄和脚本使用同一套
调用接口访问机器人。

更完整的服务关系和设计决策请阅读 [`docs/design/`](docs/design/)。项目当前状态和已知
问题记录在 [`docs/project/`](docs/project/)。中文设计文档均以 `_zh.md` 结尾。

## 构建和测试

### 环境要求

- Rust stable `1.89` 或更高版本
- Linux 或 macOS 开发环境
- 目标机器人运行 aarch64 Linux

在仓库根目录执行：

```bash
cargo test --workspace
```

格式化代码：

```bash
cargo fmt --all
```

只测试某个 crate：

```bash
cargo test -p <crate>
```

Linux 还需要安装以下依赖：

```bash
sudo apt-get install -y libudev-dev libgstreamer1.0-dev
sudo apt-get install -y libgstreamer-plugins-base1.0-dev libgstreamer-plugins-bad1.0-dev
```

需要针对机器人目标进行检查时，可以使用：

```bash
RUSTFLAGS="-D warnings" cargo clippy -p configd --all-targets --target aarch64-unknown-linux-gnu
```

### 部署到开发板

开发板安装和分支构建流程请参考：

- [搭建开发板](docs/robot/install-dev_zh.md)
- [推送分支构建](docs/robot/dev-push_zh.md)
- [开发者速查表](docs/robot/cheatsheet-dev_zh.md)

典型的分支构建推送命令如下：

```bash
./scripts/dev-push.sh <user@board>
```

该流程会交叉编译并通过机器人自身的更新机制安装，仍然会执行签名、哈希、健康检查
和自动回滚。

## 常用命令

以下命令需要在机器人上执行。只读命令通常不需要 root 权限，修改硬件或系统配置的
命令一般需要 `sudo`。

查看运行版本和健康状态：

```bash
robotctl version
robotctl health
```

查看控制循环、关节、姿态和传感器状态：

```bash
robotctl monitor
```

配置机器人：

```bash
sudo robotctl configure
robotctl configure --list
```

查看和更新策略：

```bash
robotctl policy list
robotctl policy check
sudo robotctl policy update
```

控制机器人动作：

```bash
sudo robotctl robot init
robotctl quack
robotctl chorale
robotctl theremin
```

查看更新状态或回滚：

```bash
robotctl update status
robotctl update log
sudo robotctl update apply daemon
sudo robotctl update rollback daemon
```

完整命令、参数和安全注意事项请以
[机器人使用速查表](docs/robot/cheatsheet_zh.md) 为准。

## 目录结构

```text
btd/             蓝牙服务
configd/         网络、身份和系统配置服务
duck-control/    控制核心：模型、电机总线、IMU、观测、策略和安全
duck-detect/     基于 Rockchip NPU 的目标检测
duck-ipc-proto/  服务间 JSON-RPC 协议
duckctl/         电脑端蓝牙客户端
kinematics/      运动学和机器人模型
mediad/          摄像头、麦克风和 WebRTC 服务
odometry/        里程计
padd/            游戏手柄输入服务
pet-detect/      宠物互动声音检测
robotctl/        机器人端命令行工具
robotd/          机器人主控制服务
robotd-params/   robotd 的参数、默认值和校验
sounds/          语音合成和多人合奏
tof/             头部 ToF 深度传感器服务
updater/         更新引擎和 updaterd
xtask/           打包、签名和发布工具
deploy/          机器人运行时配置、信任密钥和 systemd 文件
hooks/           更新前后执行的脚本
scripts/         开发板安装、部署、测试和救援脚本
docs/            使用文档、设计文档、项目记录和路线图
```

## 相关项目

- [microduck_rl](https://github.com/pollen-robotics/microduck_rl)：训练和导出机器人强化学习策略。
- [Microduck 产品页](https://pollen-robotics.com/microduck)：了解机器人硬件和购买方式。

## 许可证

本项目使用 [Apache License 2.0](LICENSE) 授权。

## 关于鸭子

制作这台机器人没有伤害任何鸭子。我们咨询过几只。
