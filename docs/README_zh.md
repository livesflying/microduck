# 文档

[`README`](../README_zh.md) 是入门页面——介绍什么是微鸭以及如何使用。如果你面前有一个微鸭并且想要驱动它，可以从[速查表](robot/cheatsheet_zh.md)开始。

[`faq.md`](faq_zh.md)是另一个入门页面：来自试图在微鸭上构建而不是修改它的用户提出的任务型问题——运行一个超出了板卡能力的模型，将相机集成到自己的程序中，为什么一个Space无法连接。

这也是出版商的起点：[`policy-manifest.md`](policy-manifest_zh.md)是微鸭`.onnx`旁边`manifest.json`的合约，并且它拥有每个字段。设计文档给出了理由并指出了这一点。

## `robot/`——你有一个机器人
| | |
|---|---|
| [`cheatsheet_zh.md`](robot/cheatsheet_zh.md) | 每个 `robotctl` 命令。 |
| [`pair-a-gamepad_zh.md`](robot/pair-a-gamepad_zh.md) | 每个手柄一次：配对模式，`pad pair`，以及无法配对时应采取的措施。 |
| [`cheatsheet-dev_zh.md`](robot/cheatsheet-dev_zh.md) | 需要开发板的命令：分支构建，候选版本，开发推送。 |
| [`dev-push_zh.md`](robot/dev-push_zh.md) | 在本地构建并使用 ssh 安装到板子上，无需 CI 运行。 |
| [`simulation.md`](robot/simulation_zh.md) | 模拟鸭子：`scripts/duck-sim`，MuJoCo 体素上的真实守护进程，一个鸭子或多个鸭子在容器中。 |
| [`duckctl.md`](robot/duckctl_zh.md) | 每个 `duckctl` 命令 —— 通过蓝牙从笔记本控制机器人。 |
| [`assembly-install_zh.md`](robot/assembly-install_zh.md) | 伺服电机 ID，初始姿态值，齿轮对齐以及装配验收检查。 |
| [`install-dev.md`](robot/install-dev_zh.md) | 从零开始设置板子进行开发。 |
| [`install-by-hand.md`](robot/install-by-hand_zh.md) | 单独命令的安装过程，用于逐步测试。 |

## `design/` — 你正在更改守护进程
如何运作及其原因。这些内容变化很少；当行为与设计文档不符时，文档才是错误。

**一页拥有某种机制，其他页面则链接到它。** 下表即为此分配：如果一个事实属于这里列出的某个页面，其他页面则说一句话并指向它，而不是重新解释。写在六个地方的事实会在六个方向上漂移，每个方向上都是合理的——这就是为什么六份文档都承诺 `updaterd` 和 `btd` 在下次重启前保留旧的二进制文件，而实际上它们在两个发布周期后就停止这样做，包括那些在诊断具体问题时会读到的两个页面。因此，当两份文档存在分歧时，不拥有该机制的文档就是错误。
| | |
|---|---|
| [`architecture_zh.md`](design/architecture_zh.md) | 服务拆分，IPC 合同，状态所有权，安全与权限。|
| [`robotd-design_zh.md`](design/robotd-design_zh.md) | 控制回路：Dynamixel 总线和端口的所有权，模型，感知，观测，策略，安全 —— 以及还有哪些挂载在 tick 上。|
| [`updater-design.md`](design/updater-design_zh.md) | 更新引擎：验证，原子交换，健康门，回滚，发布格式。|
| [`policy-channel-design_zh.md`](design/policy-channel-design_zh.md) | ONNX 策略的来源：`policies` 组件，尝试别人的策略，以及 `reset` 会放回什么。|
| [`restart-order.md`](design/restart-order_zh.md) | 哪个单元在哪个步骤重启，在每条移动 `current` 的路径上 —— 以及在启动时。|
| [`app-path-design_zh.md`](design/app-path-design_zh.md) | `btd` 和 `configd` —— 电话如何通过 BLE 配置机器人。|
| [`mobile-app.md`](design/mobile-app_zh.md) | 电话应用 —— 它由什么构建，以及机器人还欠它什么。代码在 [`microduck-app`](https://github.com/pollen-robotics/microduck-app) 中。|
| [`remote-webrtc_zh.md`](设计/remote-webrtc_zh.md) | WebRTC会话、信令和控制通道——一个对端如何驱动和观察机器人。 |
| [`webrtc-console.md`](设计/webrtc-console.md) | WebRTC客户端：从机器人提供它、找到机器人以及页面应该是什么。 |
| [`remote-access-design_zh.md`](设计/remote-access-design_zh.md) | 超出局域网访问鸭子：Hugging Face账户、设备流程以及与会合服务的桥梁。 |
| [`boot-recovery-net.md`](设计/boot-recovery-net.md) | 当启动的版本无法启动其守护程序时，退回到黄金版本。 |
| [`simulation.md`](设计/simulation.md) | 双胞胎：守护程序与身体之间的分界线、身体协议、假电台、容器以及它是什么和不是什么的双胞胎。 |

## `project/` — 你正在运行该项目

这些记录按日期记录而不是作为参考。它们描述了一个时刻，并故意过时。
| | |
|---|---|
| [`roadmap.md`](project/roadmap_zh.md) | 里程碑，以及当前实现与设计之间的差异。 |
| [`ci-setup.md`](project/ci-setup_zh.md) | 一次性的发布流水线设置：密钥、秘密和轮换。 |
| [`install-path-gap.md`](project/install-path-gap_zh.md) | 四个安装路径错误为何会上报给董事会，以及它们是如何被解决的。已关闭——它所教授的规则是 [`updater-design.md`](design/updater-design_zh.md) §9.1。 |
| [`slice-2-bringup.md`](project/slice-2-bringup_zh.md) | 实际的 Radxa Zero 3W 在使用 slice 2 时的表现。 |
| [`update-over-ble.md`](project/update-over-ble_zh.md) | 从手机驱动更新路径：发现了什么，以及最终决定通过无线电进行回滚。 |
| [`media-bringup.md`](project/media-bringup_zh.md) | Radxa Zero 3W 如何处理视频：VPU、MPP 需求以及必须构建的两个插件。 |
| [`pad-minimal-pairing.md`](project/pad-minimal-pairing_zh.md) | 通过逐一移除组件找到的游戏手柄可以配对的最小板卡配置。 |
| [`idle-cpu_zh.md`](project/idle-cpu_zh.md) | 当没有人要求它们做事情时，守护进程在做什么：四件停止了的事情，两件被测量后留下的事情，以及仍然需要一块电路板的事项。 |
| [`tof-on-demand.md`](project/tof-on-demand_zh.md) | `tofd` 的空闲 5% 是九部分头部 IMU 之一部分深度，而 IMU 没有消费者。为什么激光和单位被留了下来，而 IMU 得到了一个开关。 |

## `ideas/` — 尚未设计

暂存区。一些需要设计文档的东西，在它还没有设计文档之前就写下来，以免思考被遗忘或误认为是决策。

| | |
|---|---|
| [`autonomous_behavior.md`](ideas/autonomous_behavior_zh.md) | 行为堆栈：运行时的大脑需要放弃什么，以及合唱和 theremin 留下的想法。 |

## 其他地方
| | |
|---|---|
| [`../CONTRIBUTING.md`](../CONTRIBUTING.md) | 构建、测试、仓库布局、约定、发布。|
| [`project/npu-bringup.md`](project/npu-bringup_zh.md) | RK3566 NPU 的鸭子检测器：运行了什么、如何对其进行基准测试以及仍然缺失的帧路径。|
| [`../deploy/README.md`](../deploy/README.md) | 机器人镜像配置了什么，以及预配置实际做了什么。|
