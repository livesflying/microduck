# 模拟：相同的守护进程，MuJoCo中的身体

**状态:** 已构建并使用中。`robotd --sim`，`tofd --sim` 和 `mediad --sim-camera` 均已实现，`microduck_rl` 的 `duck-body` 服务另一半；容器（§8），以太网（§5）和每个鸭子的摄像头均从 `scripts/duck-sim` 运行。测量结果显示：守护进程保持 `50.0 of 50.0 Hz · 0 漏失`，与 MuJoCo 身体进行比较，能够检测模拟器自身关节角度所表示的坐姿靴子，并且 `robotctl robot init` 运行站立政策直到鸭子直立并保持直立；四个鸭子在容器中通过以太网唱完整合唱。如何使用它请参阅 [`docs/robot/simulation.md`](../robot/simulation_zh.md)；此页面是设计说明。

目标是开发一个与开发机器人时相同的鸭子：相同的二进制文件，相同的单位，相同的 `robotctl`，相同的 `duckctl open` —— 仅将身体置于 MuJoCo 而非桌面之上。这不是一个模拟，也不是测试框架。这是一个双胞胎，具有书面边界。

## 1. 使用它的样子

一条命令即可获得一个鸭子。之后它就是一个机器人，你已经知道如何操作了。

**今天能实现的功能** (`scripts/duck-sim`，一个鸭子，没有容器)：
```
scripts/duck-sim               # a window opens, the duck stands up, and it is yours
scripts/duck-sim drive         # walk it forward, then stop
scripts/duck-sim ctl health    # or anything else robotctl does
scripts/duck-sim log
scripts/duck-sim down
```
It 建立缺失的部分，编写参数，找到 RL 仓库 venv 中的 ONNX 运行时，启动两部分并竖起鸭子。它存在的三个目的就是为了防止任何人手动输入，因为这些信息是猜不出来的：策略在机器人上位于 `/opt/robot/daemon/current`，在笔记本上位于此仓库中；`ort` 会加载 libonnxruntime，而笔记本上没有此库；并且由于 Unix 套接字路径最多只能有约 108 字节，因此状态目录必须很短。

**它会去向何处**，一旦容器就位：
```
duck-sim up 4                  # four ducks, sharing one MuJoCo window
duck-sim shell duck-a          # you are on duck-a
```
Inside, 没有什么特别的：
```
duck-a # robotctl health
duck-a # robotctl configure
duck-a # robotctl chorale
duck-a # journalctl -u robotd -f
```
And 从你自己的终端中，就像桌上的机器人一样：
```
duckctl open duck-a
scripts/dev-push.sh microduck@duck-a
```
Four 规则约束着这个框架，因为需要运行手册的开发工具不会被使用：

- **无需任何人记住任何设置步骤。** 在从未运行过的机器上执行 `duck-sim up` 会构建根文件系统，获取缺失的部分并告知用户 —— 仅此一次。如果它确实无法为你完成某些操作，它会打印出具体的命令行，格式与 `scripts/` 中的其他脚本一致。

- **默认值是最常见的情况。** 没有指定数量意味着一只鸭子。没有指定场景意味着公寓。没有指定 `--cameras` 则不使用摄像头，因为大多数会话不需要它们，而且它们是最昂贵的部分。

- **你可以随时停止任何操作。** 每只鸭子都作为 systemd 单元运行，因此 `duck-sim down` 是 `systemctl stop` —— 而不是快捷键组合。这条规则是在一个容器需要从第二个终端强制终止，因为 `Ctrl-]` 在法语键盘上是 `AltGr + )` 后才得以实现的。

- **每只鸭子都可以通过名称访问。** `duck-a`、`duck-b` 等，每只鸭子都有自己的机器标识符 —— 因此 `robotctl quack` 在每只鸭子上听起来都不同，因为鸭子的声音是根据其序列号生成的。合唱中的四只鸭子不应该发出四次相同的声音。

## 2. 缝合之处
`duck_control::io::RobotIo` — 六个方法，且唯一允许存在模拟器的地方：
```rust
fn read(&mut self) -> Result<Sensors>;          // joints and IMU, one transaction
fn write(&mut self, targets: &JointTargets) -> Result<()>;
fn set_gain(&mut self, kp: u16) -> Result<()>;
fn set_torque(&mut self, on: bool) -> Result<()>;
fn slow_sensors(&mut self) -> Result<SlowSensors>;   // volts, per-joint temperature
```
Above it, 没有变化：50 Hz 循环，ONNX 策略，`Safety`，跌倒检测，里程计，运动学，maploc，每一个 IPC 调用，以及 `robotctl` 和 `duckctl` 的所有内容。在它之下只有一件事 — `DynamixelIo`，并且 IMU 不是独立的，因为在该机器人上，IMU 是一个 Dynamixel 节点，在与十五个伺服机相同的 `sync_read` 中读取。

`FakeIo` 已经是这个特性的完整实现，这就是为什么 `cargo test` 不需要硬件。`RemoteIo` 是第三个。

**当传感器的守护程序即是其驱动程序时，既不要替换前者，也不要替换后者。** `tofd --fake` 在循环级别已经合成了帧，而 `tof/src/sensor.rs` 明确指出，外部的 `Sensor` "不是一个模拟传感器，且永远不能成为模拟传感器"。模拟深度视图将该现有循环。同样的逻辑将适用于任何其他其驱动程序不能与其硬件分离的情况。

## 3. 身体协议

TCP，换行符分隔的 JSON，每次调用一个请求和一个回答。`duck_control::sim` 是其实现并承载了这一逻辑；简短版本为：
* **TCP** 因为一个 Unix 路径的最大长度为 `SUN_LEN`（约 108 字节），并且由于模拟器必须从运行守护进程所在的容器（在 Linux 上）或 macOS 上主机上的 Linux 虚拟机（带有 MuJoCo）外部都能访问。
* **JSON** 因为一帧数据约为 1 KB，所以 50 KB/s 的传输速度比使用 `nc` 读取一帧并在 Python 中写入另一端的代码要快。两个语言中两个仓库共享的打包结构体是这个项目在之前浪费了数天时间的原因。
* **`TCP_NODELAY`**，不仅仅是为了微优化：Nagle 延迟一个小写数据包最多 40 毫秒，大约是两帧的时间，这会表现为一个慢速的模拟器。

请求为 `{"op":"hello"|"read"|"write"|"gain"|"torque"|"slow", …}`。握手过程携带 `protocol`（当前为 1），并且在两个方向上都会进行检查，因为模拟器和守护进程分别位于两个仓库中，“你的模拟器过时了”和“你的守护进程过时了”是相同的症状。

**模拟器以机器人的自身单位报告数据**——弧度、弧度/秒、毫安以及 IMU 已经转换到躯干坐标系。MuJoCo 知道其模型的顺序、缩放和坐标系；在这个方面增加一层转换会是另一种数据漂移的来源。
**一死模拟器就是一个坏时间步。**MuJoCo 编译其模型，因此改变鸭子的数量会重启它，鸭子必须活过那个过程。一个断开的连接会返回一个错误给调用者，并在下一次调用时进行重连——没有回退线程，因为控制循环就是重试计时器。

## 4. 模拟无线电的成本为零

存在本身已经在 `robotd` 的自身套接字上定义了一个IPC合约：`chorale.subscribe`，`chorale.beacon`（要广告的内容）和 `chorale.heard`（听到的内容，带有“年龄”而不是时间戳）。而 `btd` 是 `robotd` 的 **客户端**，而不是服务器——因此模拟的以太网不会冒充任何东西，也不会窃取任何套接字路径。一个进程为每只鸭子持有一个连接，收集每只鸭子想要广告的内容，并通过基于它们身体之间距离计算的RSSI将其传递给其他鸭子。
No 改动 `robotd`，没有协议工作，开发中比无线电更好的三点：
基于年龄的同步路径真正被执行；来自地面真实数据的 RSSI 使范围截止点和不对称链路成为可调节的旋钮而非启动问题；并且 `from` 被文档化为仅用于去重的身份，因此定时旋转它将地址旋转错误从花费一天的问题转变为回归测试。

## 5. 无线电必须不好，否则错误会被隐藏

完美的以太网会隐藏实际无线电引起的错误，这一点是通过测量而非争论来衡量的。每次两只鸭子中的双胞胎都会同时汇聚到同一部分——无论是同时启动，还是错开启动，结果都一样——因为每只鸭子都能瞬间无损地被其他鸭子看到。导致现场错误的唯一属性是模拟器没有建模的属性。
`duck-ether --discovery <s> --loss <f> --seed <n>` 使其成为一个糟糕的广播：一只鸭子被注意到需要一段时间，每对按时间计算从广播开始时算起，并且有一部分广播会被丢弃。这是因为每对鸭子是因为不对称性将一群鸭子分开——一个延迟不能由每个人共享来产生。种子初始化，因为一个不稳定的广播仅在故障重复出现时才有用以进行调试。

**复现**，四只鸭子，`a` 和 `b` 在 `c` 和 `d` 加入前十二秒鸣叫：
```
duck-ether --discovery 90 --loss 0.3 --seed 3
```
在main的圣咏中：

| 鸭子 | 部分 | 小节 | 名单 |
|---|---|---|---|
| a | *不唱歌* | — | 1人在范围内 |
| b | 低音 | 4 | 3个声部 |
| c | 高音 | 4 | 2个声部 |
| d | 低音 | 2 | 2个声部 |

这是一份情况报告 — "有时什么也不发生，有时唱两首不同的歌" — 与不一致的名单以及重复的部分。

**尚未证明的是。**即使将`chorale-election`合并进来，同样的场景仍然会分裂（小节5、12和8：三个时间线）。但在`--discovery 20 --loss 0.4`下，两者都收敛了，所以90秒的探索时间比代码写的要严格，这并不能证明修复失败于机器人。值得进行的实验是一个扫掠 — 在哪个探索值下每个版本停止收敛 — 现在是一个数字循环，而不是四个机器人和一个房间。

## 6. 架构遵循宿主机

该项目构建的每个制品都是aarch64。吸引人的想法是，在x86笔记本电脑上使用`qemu-user`运行板上的二进制文件 — 同样的字节，完美的来源证明。

**仅守护进程本身是好的。** CI的真实aarch64制品，在x86笔记本电脑上模拟：

| | |
|---|---|
| `robotctl health` | `50.0 of 50.0 Hz · 3804 ticks · 0 missed` |
| host CPU | 4.7% 的一个核心，九个 ONNX 会话加载中，策略驱动中 |
| policy inference | 0.029 毫秒，针对 20 毫秒的节拍（本地测量）|

吞吐量从未是风险——而实际节拍中较慢的部分，即 Dynamixel 同步读取，是一个本地套接字。

**在 systemd 中并非如此。** 在 `systemd-nspawn` 中启动，aarch64 系统d 257 在 8.7 秒后启动完毕，但无法启动任何内容：
```
robotd.service:            (code=exited, status=226/NAMESPACE)
systemd-journald.service:  (code=exited, status=243/CREDENTIALS)
systemd-logind, systemd-tmpfiles, console-getty: the same
```
qemu-user 8.2 不支持 systemd 257 使用的新挂载 API (`fsopen`, `move_mount`, `open_tree`)，这些 API 用于单个单元的命名空间和凭证。单个单元的强化是启动容器而不是在终端中运行七个进程的全部原因，因此失去它就失去了意义。较新的 qemu 可能会修复这个问题；在 Debian 13 和 Ubuntu 25.04 中，静态包是过渡性的，实际的二进制文件是动态链接的，因此这是一个需要从源代码构建的问题，而不是一个 apt 命令的问题。

所以双系统运行 **宿主机的架构**：

* **x86 宿主机** — 一个 amd64 容器和一个本地构建。真实的单元，真实的强化，真实的日志；除了 CI 精确的字节外，一切皆真。
* **arm64 宿主机（Apple Silicon）** — 一个 arm64 容器运行机器人自己的签名文件，本地执行。完整的溯源，无模拟，相同的命令。
The 更新路径的后果很小，值得明确说明：`robotctl update apply` 会从头到尾运行 —— 包括预检、签名、文件校验和、兼容性检查、健康门限、自动回滚 —— 因为这是 `dev-push.sh` 安装的方式。而 x86 双胞胎无法完成的是安装已发布的版本。`board-test.sh` 已经在 CI 中覆盖了实际的文件在实际架构上的安装情况。

## 7. 这是什么，又不是什么的双胞胎

完全相同，因为它们是相同的代码在相同的路径上：控制循环、策略、安全措施、失能检测、运动学、里程计、整个 IPC 表面及其客户端、chorale 的选举和节拍、带有实际 `User=`、组、`RuntimeDirectory=` 和加固的 systemd 单元。

模拟 —— 实际代码路径，合成输入：执行器响应（BAM 模型拟合到实际的 XL330s）、IMU、ToF 深度、RSSI、相机图像以及在 x86 主机上的版本源。

缺失 —— 完全未被测试：Dynamixel 总线驱动、BLE 无线电、相机 ISP 和 rkaiq 的 3A、NPU、硬件编码器及其 RGA 路径、温度和电池。
**一个有用的检查项：**用一周的实际错误跑一遍。一个 `videoflip` 因为破坏了编码器到 RGA 的零拷贝路径而以 22 fps 的成本计算；一个 3A 引擎缺少流启动事件；一个自动曝光循环只收敛一次就停止；一个 INT8 头部其评分通道压缩为两个值；一个伺服总线丢失读取。双胞胎测试仪不会发现 **任何一个**。这不是设计上的缺陷，而是其边界——并且硬件是唯一能够验证驱动程序真实性的地方。

## 8. 虚拟的鸭子就是鸭子，而且会这么说一次

在 MuJoCo 中注册的鸭子会参与会合，并出现在其所有者的 Hugging Face 机器人列表中，紧挨着真实的鸭子。这很有价值——它代表了整个远程访问路径，可以在没有硬件的情况下进行测试——并且明确这一点也很重要，因为无法区分两者客户端最终会导致有人在模拟中驾驶，而困惑为什么架子上的机器人仍然没有反应。
**一个事实，只声明一次。** `configd --simulated <serial>` 是唯一声明它的地方。
`system.info` 携带它，`mediad` 在那里学习它——它已经在启动时询问该问题，并在 `meta` 中注册时放入 `simulated: true`。`robotctl system info` 打印它。没有任何其他地方推断它，特别是没有以 `sim-` 开头的序列号上的客户端密钥：这是一个三个地方必须达成一致并且其中一个会出错的约定。

`mediad --sim-camera` 也会设置它。这不是第二个真相来源——而是一个后备方案，以防唯一的情况出错：`configd` 在一个所有守护进程在同一瞬间启动的机器上被询问一次，并带有超时，如果延迟回答会导致将一个模拟鸭子注册为硬件。两者不能产生分歧，因为没有安排使得帧来自模拟器而对应的机器人却是真实的。
**身份是旗帜取值的原因。**模拟鸭子没有SoC序列号，也没有每只鸭子的`/etc/machine-id`——一个场景中的四只鸭子共享同一台笔记本的`machine-id`，因此它们会逐一被排除在列表之外，而macOS根本没有这样的文件，因此它们都不会注册。`sim-duck-a`是每只鸭子稳定的，且在重启后保持不变，这正是`hardware_id`需要做到的（`remote-access-design.md` §3.7）。机器人的名称正是从它派生出来的，就像真实鸭子的那样，因此双胞胎中的鸭子是`duck-eb55`，而不是运行它的机器的主机名。

**账户是机器人的自有流程，而不是授予它的凭据。**`updaterd`在模拟器中运行，`--token`指向状态目录，而`robotctl account login`则是针对Hugging Face的RFC 8628：在手机或浏览器中输入一个代码，就像在机器人上一样。`mediad`会轮询该文件并在其出现时进行注册，因此在会话中登录的鸭子无需重启。凭据路径中的任何内容都不进行模拟，这正是重点——这是远程访问中最容易细微出错且最难在电路板上进行测试的一半。
The 后果是rendezvous的，不是我们的：同伴是通过令牌键入的，因此每次只列出一个账号下的一个鸭子。每个鸭子运行自己的设备流，所以这是一个关于账号的规则，而不是模拟器的限制。

## 9. GStreamer 并非 Linux 特有部分

`mediad`的管道完全被 `#[cfg(target_os = "linux")]` 门控，当唯一的来源是板载摄像头时为真，而当 `Source::Sim` 到来时停止为真。大约230行的 `pipeline.rs` 确实是硬件相关的：`v4l2src`，驱动的缓冲池以及 `GstVideoMeta` 分配查询，以及媒体拓扑中的传感器模式读取。其余部分——appsrc，tee，appsink，`webrtcsink`，编码设置信号——是 GStreamer，运行在 GStreamer 运行的任何地方。

所以门控条件是 `any(target_os = "linux", feature = "gstreamer")`：在机器人的操作系统上假定，其他地方可选。开发者的机器会获得真实的守护进程，真实的控制台和真实的 WebRTC 对于一个模拟摄像头，两个 Homebrew 公式，而 Linux 上的 `Source::Camera` 是一个明显的错误而不是缺少 ARM 支持。
Two,不是一，并且第二个是值得记录下的陷阱：Homebrew的`gstreamer`将`libgstnice.dylib`链接到了一个单独的`libnice-gstreamer`公式中，但这个公式并不依赖于`libnice`。如果没有这个公式，链接就会悬空，`webrtcbin`没有ICE代理，一切正常——管道、摄像头、会话注册——直到第一个消费者请求一个pad，然后会话在GStreamer线程中以“libnice元素不可用”而崩溃。构建检查看不到这个问题，因此`scripts/duck-sim`会检查元素而不是pkg-config文件。`exposure.rs`仅限Linux使用，这并不是打包——它通过`ioctl`写入V4L2控制，而模拟源后面没有传感器用于测量。
Off by default there, deliberately: Homebrew 的 `gstreamer` 是一个合并的公式，会拉取 gtk4 和 ffmpeg，而正在 `robotd` 上工作的某人不应为了运行 `cargo check` 而需要它。代价是，没有 CI 作业会编译这种组合——CI 作业始终是 `ubuntu-*`——因此是开发者运行它来保持其正常工作。一个 `macos-latest` 作业执行 `cargo check -p mediad --features gstreamer` 将改变这一点，但出于故意，它被排除在外：CI 已经很慢，而 macOS 跑步程序更慢。

## 10. 引擎

一个 MuJoCo 进程，一个窗口，N 个鸭子的身体在一个场景中，因此鸭子们共享物理引擎并可以相互碰撞。`microduck_rl` 拥有这一半：它已经拥有场景、BAM 作动器模型和 mjlab，并向守护进程提供一个身体相当于今天所进行的 sim2real。

每个鸭子都是一个 `systemd-nspawn` 容器——没有守护进程，没有镜像格式，一个容器就是一个目录——从一个 Debian 13 Trixie 根文件系统（`mmdebstrap`，非特权，238 MB，不到三分钟）启动，每个鸭子有一个叠加层。将每个鸭子作为服务运行（`systemd-run --unit=duck-a …`），因此 `duck-sim down` 等同于 `systemctl stop`：一个你无法退出的鸭子不是一个真正的鸭子。
`machinectl shell duck-a` 是进入的方式，`duckctl open duck-a` 是观看的方式，而
`scripts/dev-push.sh microduck@duck-a` 是安装构建的方式。

两个由物理学而非管道决定的限制。**鸭子不会热加入**——MuJoCo 编译其模型，因此更改数量会重启模拟器，这就是为什么 `RemoteIo` 会重新连接。
并且**相机渲染是缩放的瓶颈**，而不是双足机器人：N 个离屏渲染在 30 fps 下的成本远超过 N 个十五自由度的身体，因此相机应按鸭子选择性启用。45 Hz 的健康门限设定了一个硬边界而非软边界——鸭子太多时，它们不会变慢，而是变得*不健康*，更新器开始回滚发布。

## 11. 三种选错模型的方式

每种情况都表现为“鸭子翻了个身”，每种情况都花费了一个小时。
**`scene_walk.xml` 没有碰撞。**它包含了 RL 工作训练所用的模型，该模型的执行器默认类携带 `contype="0" conaffinity="0"`。鸭子穿过场景中确实存在的地板下沉 — trunk z 从 0.120 变为 -0.105，在一秒钟内 — 且守护程序报告一只倒下的机器人，这是正确的。`scene.xml` 包含 `robot_allcollisions.xml`，是双胞胎想要的。

**`qpos0` 不是一个姿态。**每个关节在零位时代表机器人从未处于的姿态；守护程序从其起始坐标系测量到 0.41 弧度，并合理地尝试使已经折叠的机器人站立。场景中携带 `INIT`、`STAND`、`SIT` 和 `FOLD`，而 `STAND` 与 `duck_control::DEFAULT_POSITION` 匹配 — 其右腿是 *镜像* 而非对称，这值得阅读而不是假设。

**启动时应设置扭矩。**`robotd` 在启动时从不启用扭矩，因为由更新重启的守护程序必须使站立的机器人保持站立状态 — 伺服电机已经保持住了。一个从无支撑开始的模拟器会在第一次读取之前使鸭子落在地上。
The 启动守护进程实际上是为了 `--keyframe SIT`：一只被折叠起来的鸭子，它认出并用坐立策略站起来。

## 12. 已知可重用的材料

`~/MISC/microduck_maploc`（在其他所有方面都已过时）中有两件值得取用的东西：`sim/tof_sensor.py` 中的一个模拟的 VL53L5CX — 8×8 区域，45° 方形视场，4 米范围，噪声随距离增大，15 Hz — 以及 `sim/assets/apartment.xml`，一个包含 83 个几何体的室内场景。对 maploc、wander 以及任何隐藏的东西而言，一个房间的价值远大于一个地面平面。
