# 文档索引

这里是 Microduck 中文文档的入口。英文原文保留在同目录下，文件名不带 `_zh` 后缀。
中文版本的文件名统一添加 `_zh.md`。

如果你已经有一台机器人，建议从[机器人使用速查表](robot/cheatsheet_zh.md)开始。
如果你要搭建开发环境，请阅读[开发板安装指南](robot/install-dev_zh.md)和
[贡献指南](../CONTRIBUTING.md)。

## `robot/`：使用机器人

| 文档 | 内容 |
| --- | --- |
| [使用速查表](robot/cheatsheet_zh.md) | `robotctl` 的常用命令和机器人日常操作。 |
| [连接游戏手柄](robot/pair-a-gamepad_zh.md) | 配对手柄、排查绑定失败和连接中断。 |
| [开发者速查表](robot/cheatsheet-dev_zh.md) | 开发板、分支构建和候选版本。 |
| [推送分支构建](robot/dev-push_zh.md) | 在本机编译并通过 SSH 安装到机器人。 |
| [`duckctl`](robot/duckctl_zh.md) | 通过蓝牙从电脑访问机器人。 |
| [从零安装开发板](robot/install-dev_zh.md) | 配置一块空白开发板。 |
| [手动安装](robot/install-by-hand_zh.md) | 将安装流程拆成可单独测试的步骤。 |

## `design/`：系统设计

| 文档 | 内容 |
| --- | --- |
| [系统架构](design/architecture_zh.md) | 服务划分、IPC、状态所有权、安全和权限。 |
| [`robotd` 设计](design/robotd-design_zh.md) | 控制循环、电机总线、传感器、策略和安全机制。 |
| [更新系统设计](design/updater-design_zh.md) | 签名校验、原子切换、健康检查和回滚。 |
| [策略通道设计](design/policy-channel-design_zh.md) | ONNX 策略来源、官方策略集、社区策略和重置行为。 |
| [重启顺序](design/restart-order_zh.md) | 更新或启动时各 systemd 服务的重启顺序。 |
| [应用通道设计](design/app-path-design_zh.md) | 手机通过 BLE 配置机器人。 |
| [远程 WebRTC](design/remote-webrtc_zh.md) | WebRTC 会话、信令和控制通道。 |
| [WebRTC 控制台](design/webrtc-console_zh.md) | 机器人提供的 WebRTC 网页客户端。 |
| [远程访问](design/remote-access-design_zh.md) | 通过账户和中继服务从局域网外访问机器人。 |
| [启动恢复网络](design/boot-recovery-net_zh.md) | 当前版本启动失败时回到 golden 版本。 |

## `project/`：项目记录

| 文档 | 内容 |
| --- | --- |
| [路线图](project/roadmap_zh.md) | 里程碑、当前状态和后续计划。 |
| [CI 配置](project/ci-setup_zh.md) | 发布流水线、密钥和轮换。 |
| [安装路径缺口](project/install-path-gap_zh.md) | 安装流程中曾出现的问题及修复。 |
| [Slice 2 硬件验证](project/slice-2-bringup_zh.md) | 在真实机器人上运行 Slice 2 的记录。 |
| [BLE 更新](project/update-over-ble_zh.md) | 从手机通过蓝牙驱动更新流程。 |
| [媒体硬件验证](project/media-bringup_zh.md) | 摄像头、VPU、MPP 和 GStreamer 插件。 |
| [NPU 验证](project/npu-bringup_zh.md) | RK3566 NPU 上的鸭子检测器。 |
| [游戏手柄最小配对环境](project/pad-minimal-pairing_zh.md) | 手柄建立连接所需的最小系统配置。 |
| [空闲 CPU 分析](project/idle-cpu_zh.md) | 机器人没有操作时各服务的 CPU 行为。 |

## `ideas/`：尚未定稿的想法

| 文档 | 内容 |
| --- | --- |
| [自主行为栈](ideas/autonomous_behavior_zh.md) | 自主行为运行时的缺口和待讨论方案。 |

## 其他入口

| 文档 | 内容 |
| --- | --- |
| [策略清单规范](policy-manifest_zh.md) | `manifest.json` 的字段和校验规则。 |
| [贡献指南](../CONTRIBUTING.md) | 构建、测试、代码布局和发布流程。 |
| [部署说明](../deploy/README.md) | 机器人镜像配置和 provisioning 流程。 |

英文源文档索引：[docs/README.md](README.md)。
