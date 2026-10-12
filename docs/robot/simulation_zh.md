# 仿真的鸭子

在MuJoCo中的鸭子，由真实的守护程序驱动。你对其开发与对桌上机器人的开发完全相同：相同的`robotd`，相同的策略，相同的50 Hz循环，相同的`robotctl`，相同的控制台。只有身体是不同的。

本页面是如何使用它。[`design/simulation.md`](../design/simulation_zh.md) 是它的定义和构建方式，而不是它的孪生兄弟，以及为何它要这样构建。


## 它是什么
`robotd --sim host:port` 使用 `duck_control::sim::RemoteIo` 替代伺服总线：每隔一拍，关节位置、速度和IMU数据通过TCP套接字从一个MuJoCo 进程传来，而策略的目标则返回出去。在那缝合线以上的一切——控制环路、策略、安全措施、跌倒检测、运动学、里程计、整个IPC表面——都是机器人运行的代码，未作更改且无法区分。`tofd --sim` 从同一个模拟器获取其 8×8 深度帧；`mediad --sim-camera` 获取一个渲染的头部摄像头图像，像真实的一样旋转了四分之一圈。`configd` 和 `updaterd` 也未作更改地运行，这正是赋予模拟鸭子一个串口、一个名称以及一个可以通过此网络外侧访问的Hugging Face账户的原因。

MuJoCo 部分则存在于 [`microduck_rl`](https://github.com/pollen-robotics/microduck_rl) 中，作为 `duck-body`：一个进程，一个窗口，一个场景中 N 个鸭子身体，使用 BAM 作动器模型，这些模型是策略训练所针对的。
**适用范围：** 任何在守护进程及其客户端中的内容——进程间通信(IPC)、`robotctl`、控制台、更新程序、合唱团、策略的站立和行走、地图生成。**无法告知的内容：**
任何在驱动程序中的内容。动态ixel总线、BLE无线模块、摄像头ISP、NPU和硬件编码器均未建模，其中任何一个的bug仅在机器人上可见。

## 所需内容

- 这个仓库是为你的机器构建的（`cargo build`会自动进行）。
- 一个包含 `microduck_rl` 的检出及其 venv — 该 venv 可以在该仓库旁边，或者 `DUCK_SIM_RL` 指向的任何地方。它提供了 `duck-body`、场景以及笔记本电脑通常缺少的 `libonnxruntime`。相机位于其 `develop` 分支上。
- 对于带有相机的鸭子（非 Linux 系统）：`brew install gstreamer libnice-gstreamer`。第一个是包含 `webrtcsink`、srtp 和 x264 的合并公式。第二个是 ICE 代理 `webrtcbin` 所需的，第一个不依赖于它 —— 在没有它的前提下，鸭子会启动并开始流媒体，直到浏览器请求视频时才会失败。`scripts/duck-sim` 会检查这两个依赖项。
- 仅对于容器形式：`sudo`、`systemd-nspawn`（软件包 `systemd-container`）和 `mmdebstrap`。脚本会指出缺少哪个，并打印出安装它的命令行。

## `up` 或 `boot`？

两者都驱动同一个 MuJoCo 体，并使用相同的 `robotd`。它们的区别在于运行这些守护进程的底层环境不同。
| | `scripts/duck-sim` (`up`) | `scripts/duck-sim boot N` |
|---|---|---|
| 进程运行于 | 作为普通进程，你的用户，每个进程一个pid文件 | systemd服务，每个鸭子一个`systemd-nspawn`容器，来自真实的单元文件 |
| 需要 | 除了仓库和`microduck_rl`之外的任何东西 | `sudo`，一次性的Debian根文件系统构建 |
| 启动时间 | 几秒 | 第一次启动需要一分钟，之后几秒 |
| 身份 | 你的笔记本电脑；多个鸭子是一个进程树 | 一个机器ID，每个鸭子一个声音和一个套接字，以及`duck-ether`在它们之间 |
| 练习 | 控制回路、策略、IPC、`robotctl`、控制台 | 所有这些，加上`User=`/组/`RuntimeDirectory=`/强化，更新器的应用，健康门，回滚和重启顺序，`journalctl` |

经验法则：**`up`** 当你在处理控制回路、策略、IPC或客户端时。
**`boot`** 当你在处理任何涉及systemd、更新器或配置，或者多个鸭子之间通信的事情时。这个模拟器已经捕获了两个错误：一个守护进程的用户不存在，因此其单元文件从未启动——这是一类`up`无法看到的错误。

## 一个鸭子，没有容器
```sh
scripts/duck-sim                # a MuJoCo window opens, the duck stands up, and it is yours
scripts/duck-sim status         # health, and whether it is standing
scripts/duck-sim drive          # walk forward for 8 s (args: vx vyaw, default 0.15 0)
scripts/duck-sim ctl health     # anything robotctl does, aimed at this duck
scripts/duck-sim monitor        # robotctl monitor: joints, IMU, ToF, sticks
scripts/duck-sim log            # robotd's log
scripts/duck-sim simlog         # the MuJoCo side
scripts/duck-sim realtime       # how fast the world is running (see below)
scripts/duck-sim down
```
- 脚本不带参数时，从你当前所在的分支构建守护进程，生成一个参数文件来命名此仓库中的策略，启动 `duck-body`、`tofd --sim` 和 `robotd --sim`，在 `~/.cache/duck-sim` 下运行，并启用默认策略。`ctl` 是指向该鸭子套接字的 `robotctl`，唯一的不同之处在于：在电路板上，套接字位于 `/run`，而在这里它们位于状态目录下。

要从你自己的工具与之通信，套接字为 `~/.cache/duck-sim/duck-a.sock`（机器人守护进程；`duck.sock` 是指向 `ctl` 通信的鸭子的链接）和 `~/.cache/duck-sim/duck-a-tof.sock`，并且身体在 TCP 端口 7801。

## 几只鸭子，每只都是一个你可以登录的机器
```sh
scripts/duck-sim boot 4         # four ducks in one world, each in its own container (sudo)
scripts/duck-sim shell          # you are on duck-a
scripts/duck-sim shell duck-c   # or any other
duck-a # robotctl health
duck-a # journalctl -u robotd -f
scripts/duck-sim down
```
`boot` 在真实的systemd环境下运行每个鸭子的守护进程，使用 `systemd-nspawn` 容器，从一个 Debian 13 rootfs（构建一次，大约需要三分钟，并保存在状态目录下）启动，每个鸭子有一个独立的覆盖层。这买来了普通形式无法模仿的部分：真实的单元文件及其 `User=`、组、`RuntimeDirectory=` 和加固措施，在真实的初始化系统下——因此 `robotctl update apply`、健康检查和重启顺序的行为与机器人上相同。鸭子们分别称为 `duck-a`、`duck-b` 等，并且每个鸭子都有自己的 machine-id 和自己的声音。

如果有多个鸭子，脚本还会启动 `duck-ether`，这是一个模拟的无线电，用于在容器之间传输合唱团的 BLE 信标。它故意设计为一个 *差* 的无线电——丢失和延迟的信标——因为一个完美的无线电会隐藏真实无线电展示的错误。

第一次运行时，`boot` 会构建 rootfs 并可能要求你安装 `mmdebstrap`。每个鸭子都是一个 systemd 单元，因此 `down` 是 `systemctl stop`，而不是快捷键组合。

## 一个可供观察的房间，以及观察的眼睛
```sh
DUCK_SIM_SCENE=apartment DUCK_SIM_CAMERAS=a scripts/duck-sim boot 2
```
默认世界是一个空旷的地板。`公寓`有六个房间，面积为7×6米，门道故意偏离中心，以便鸭子以45°前视角度可以识别出姿势；任何带有斜杠的都是通往你自己的场景的路径，`microduck_rl`的`scene_*.xml`文件是内置的。

相机是每个鸭子可选的（`a`，`a,c`，或`all`），因为渲染一帧画面需要12毫秒，而步进四个鸭子的物理模拟只需要0.3毫秒：一个相机相当于三分之一的内核，四个相机则几乎占满了一个内核。每个带有相机的鸭子都有自己的`mediad`，并且其控制台在`http://127.0.0.1:8080`，`8081`，...按索引提供，与机器人提供的页面完全相同。

## 从任何地方访问

模拟鸭子登录到一个 Hugging Face 账户，并出现在该账户的机器人列表中，就像桌面上的机器人一样。控制台，一个应用程序或一个 Space，然后通过 WebRTC 跨网络访问它，而无需在本网络中。

## 从任何地方访问

模拟鸭子登录到一个 Hugging Face 账户，并出现在该账户的机器人列表中，就像桌面上的机器人一样。控制台，一个应用程序或一个 Space，然后通过 WebRTC 跨网络访问它，而无需在本网络中。
```bash
DUCK_SIM_CAMERAS=a scripts/duck-sim
```

```bash
scripts/duck-sim ctl account login
```
打开 `hf.co/oauth/device`，输入它打印的代码，几秒钟后这只鸭子就会被列出。
`scripts/duck-sim ctl account status` 会显示它属于哪个账号，而 `scripts/duck-sim ctl system info` 会打印序列号并显示 `body MuJoCo`。
在列表中，它会带有 `simulated` 标记和从其序列号派生的名字（如 `duck-eb55`），因此看起来并不像架子上的机器人。除了这一点，它和其他鸭子并无二致：同样的控制通道，同样的 H.264，同样的政策。

从通过令牌会话键入对端的两条规则中可以得出：

- **一次只能有一个鸭子属于一个账号。** 同一账号的第二次 `login` 会取代第一次，两者看起来都完好无损——它们轮流被列出。第二个鸭子需要第二个账号。
- **占据这个鸭子的空间需要自己的令牌**，而不是鸭子的令牌；发布的空间使用访客自己的登录。

`scripts/duck-sim ctl account logout` 可以将其从列表中移除。

## 调整项

环境变量，均为可选：

| 变量 | 默认值 | 作用 |
|---|---|---|
| `DUCK_SIM_RL` | `~/Pollen/microduck_rl` | `duck-body`、场景和ONNX运行时的位置。 |
| `DUCK_SIM_STATE` | `~/.cache/duck-sim` | 套接字、日志、参数、根文件系统和鸭子的覆盖层。简短的原因：unix套接字路径大约限制在108字节。 |
| `DUCK_SIM_DUCKS` | `1` | 鸭子的数量；`boot N` 也会设置它。 |
| `DUCK_SIM_SCENE` | 空白地板 | 场景名称（`apartment`）或路径。 |
| `DUCK_SIM_CAMERAS` | 无 | 哪些鸭子渲染摄像头：`a`，`a,c`，`all`。 |
| `DUCK_SIM_DUCK` | `duck-a` | `ctl` 和 `monitor` 与哪个鸭子通信。 |
| `DUCK_SIM_KEYFRAME` | `SIT` | 鸭子开始的位置：`SIT` 折叠在地板上（站立策略从中升起），`HOME`，`STAND`，`FOLD`。 |
| `DUCK_SIM_VIEWER` | `1` | `0` 以无头模式运行 MuJoCo。 |
| `DUCK_SIM_PORT` | `7801` | 第一只鸭子的 body 端口；每只鸭子加1。 |
| `DUCK_SIM_FRAME_PORT` | `7901` | 第一个摄像头的帧端口；每增加一个摄像头加1。 |

## 值得了解的事物
**实时很重要。**守护进程的循环是基于墙钟时间的。模拟器以低于1.0倍实时速度运行不仅观看起来很慢：策略驱动的机器人移动速度低于预期，无法保持平衡。`scripts/duck-sim realtime`会报告这个倍率，`boot`会打印它。鸭子太多，或者摄像头太多，鸭子不会变慢——它们会在45 Hz门限处变得不健康，在容器形式中更新器会开始回滚发布。减少鸭子的数量，减少摄像头的数量，或者使用无头查看器是解决办法，按这个顺序来。

**鸭子不能热加入。**MuJoCo 编译其模型，因此改变鸭子的数量会重启模拟器。守护进程能够生存下来：`RemoteIo`会在下一个心跳时重新连接，一个短暂消失的鸭子会报告为不健康而不是死亡，就像没有电源的机器人在总线上一样。

**`--sim` 不是 `--fake`。**`robotd --fake` 是一个没有任何物理属性的机器人：没有物理模拟，位置反馈完美，不会倒下。它用于单元测试和需要完全无身体的笔记本工作。`--sim` 是它的双胞胎。这两个标志是互斥的。
**鸭子不应该认为自己是笔记本电脑。**鸭子的声音和其chorale身份是由硬件序列号派生出来的，而在同一台机器上的几只鸭子会共享这个序列号。脚本会为每只鸭子设置`DUCK_IDENTITY`，使它们不同；这台机器上的机器人不会设置这个值。

## 手动设置，不使用脚本

每半部分都需要一个`host:port`，可以单独运行，这在出现问题时非常有用：
```sh
# the body, from the RL repo's venv
duck-body --ducks 1 --port 7801 --keyframe SIT
# the daemons, from this repo
target/debug/tofd --sim 127.0.0.1:7801 --socket /tmp/d/duck-a-tof.sock
DUCK_RUNTIME_DIR=/tmp/d ORT_DYLIB_PATH=<libonnxruntime.so> \
    target/debug/robotd --sim 127.0.0.1:7801 --params <params.toml> --socket /tmp/d/duck-a.sock
# who it is, and which account it belongs to
target/debug/configd --socket /tmp/d/duck-a-config.sock --state-dir /tmp/d/duck-a \
    --simulated sim-duck-a --fake-net --fake-pads
target/debug/updaterd --config /tmp/d/updater.toml --socket /tmp/d/duck-a-updater.sock \
    --token /tmp/d/duck-a/hf-token
# a camera, if duck-body was started with --cameras a
printf '[media]\nquality = "360p30"\n' > /tmp/d/mediad.toml
target/debug/mediad --sim-camera 127.0.0.1:7901 --config /tmp/d/mediad.toml \
    --robot-socket /tmp/d/duck-a.sock --tof-socket /tmp/d/duck-a-tof.sock \
    --config-socket /tmp/d/duck-a-config.sock --updater-socket /tmp/d/duck-a-updater.sock \
    --token /tmp/d/duck-a/hf-token
```
- 使用Linux以外的系统时，`mediad`需要通过其管道进行构建：`cargo build -p mediad --features gstreamer`。如果没有启用该功能，它会自行启动并提示缺少该功能后退出。

`--token`参数在两个守护进程中必须相同 —— `updaterd`会在该文件中写入凭证，而`mediad`会读取该文件。如果指向不同的文件，鸭子会登录但不会注册。

两者的摄像机几何尺寸必须匹配 —— `mediad`会流式传输 `[media] quality` 级别（`360p30`分辨率为640×360），并且主体必须渲染为相同的大小，因为帧以未握手的方式到达，`mediad`会拒绝显示一个不符合尺寸要求的图片，而不是显示无人能读的图片。
`scripts/duck-sim` 记录了其余的参数；在即兴发挥之前，请先阅读它。
