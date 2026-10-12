# 硬件上的媒体启用

Radxa Zero 3W 对视频的支持。以下内容均基于观察所得，未作推断——
其中仍有假设的地方会明确标注。

## 本文解决的问题

`mediad` 需要硬件 H.264 编码：软件编码不是一个更慢的选择，而是一个不可行的选择。
仅靠 `jpegenc` 无法在该 SoC 上以 30 fps 的速度处理 640x480 的分辨率（`microduck_runtime/src/camera.rs:500`），而 H.264 每帧的成本高于 JPEG，这四颗 Cortex-A55 已经被 `robotd` 的 50 Hz 控制循环所占用。

**VPU 负责编码 H.264，比特流有效，并通过 Rockchip 的 MPP 而非 V4L2 接口访问编码器。** 必须从源代码构建两个 GStreamer 插件才能使用其中任何功能，且均不受未知因素限制。
| | |
|---|---|
| VPU 编码 720p H.264 | 是 — 60 帧，428 KB，通过 `mpi_enc_test` |
| 该内核支持比特流 | 是 — `avdec_h264` 解码干净，高配置级别 4，4:2:0 8 位 |
| 通过 | `/dev/mpp_service`（瑞芯微 MPP）。**不是** V4L2 M2M |
| 1.x 版本的 GStreamer 插件 ABI | 没有风险 — 一个在 1.14 版本编译的插件在 1.26.2 版本中注册干净 |
| `mpph264enc` 元素 | 必须编译（参见 [需要编译的内容](#what-has-to-be-built)）|
| `webrtcsink` / `webrtcsrc` | 必须单独编译 |

## 板子上有什么

在预置的板子上没有安装任何与媒体相关的软件。`scripts/setup-gstreamer.sh` 安装并报告硬件的功能；该脚本是本页面的可执行形式，也是需要再次执行的命令最终所在的地方。

GStreamer 来自 **纯 Debian trixie** — `apt-cache policy` 显示 `deb.debian.org` 和 `security.debian.org` 没有 Armbian 多媒体叠加层，因此存档中的版本完全适用：
| 包 | 版本 |
|---|---|
| `gstreamer1.0-plugins-bad` (包含 `webrtcbin`) | 1.26.2-3+deb13u3 |
| `libgstreamer-plugins-bad1.0-dev` (包含 `gstreamer-webrtc-1.0.pc`) | 1.26.2-3+deb13u3 |
| `gstreamer1.0-nice` | 0.1.22-1 |
| `gstreamer1.0-plugins-rs` | **在任何Debian套件中均不存在** |

内核为 `6.1.115-vendor-rk35xx`。这重要两次：相机的MIPI-CSI ISP捕获驱动程序仅存在于Armbian的供应商分支中，VPU节点也是如此。`setup-board.sh` 已经安装了该内核——用于音频编解码器的I²S树，而不是用于视频——所以在任何人要求之前，先决条件已经满足。一次偶然的 `apt upgrade` 拉取了 `current` 内核并重定向了 `/boot`，会移除它们。

## 相机需要一个overlay，并在前缀下镜像

插上的CSI相机在设备树overlay启用之前 **不会产生 `/dev/video*` 设备节点和dmesg中的任何内容**——这就像一个未连接的相机。
启用它有一个陷阱值得单独说明。Armbian 以 `radxa-zero3-rpi-camera-v2.dtbo` 的形式提供了 overlay，**没有 `rk3568-` 前缀**，而板子运行的是 `overlay_prefix=rk3568`。因此，`overlays=` 项解析为 `rk3568-radxa-zero3-rpi-camera-v2.dtbo`，加载器找不到任何内容，板子在没有摄像头的情况下愉快地启动——这与 `configure_overlay` 为 `uart2-m0` 防止的静默失败相同。文件必须 **首先镜像到带有前缀的名称下**，然后才能在 `overlays=` 中命名。`microduck_runtime/install.sh` 遇到了这个问题，并且也做了同样的事情。

`setup-board.sh` 中的 `configure_camera` 两者都做了，进入供应商内核的 overlay 目录——MIPI-CSI 捕获驱动仅存在于该分支上，这也是为什么供应商内核不可选的第二个原因。`DUCK_CAMERA_OVERLAY` 选择了另一个模块；Armbian 每个传感器提供一个，对于这块板子，它们是 `radxa-zero3-rpi-camera-v2`（Pi Cam v2 / IMX219）或 `radxa-zero3-rpi-camera-v1.3`（Pi Cam v1.3 / OV5647）。这里仅使用过第一个。

## 编码器是 MPP，不是 V4L2

`v4l2h264enc` 不存在且 `/dev/video*` 为空。这都不是错误：

- 在Rockchip BSP内核中，VPU以 `/dev/mpp_service` 的形式暴露，而不是作为V4L2 M2M编码器。
  `v4l2h264enc` 只有在找到编码节点时才会由 `gstreamer1.0-plugins-good` 注册，因此它的缺失是预期的形态，而不是缺少包。
- 完全没有 `/dev/video*` 也正好是未连接摄像头的样子 —— rkisp 捕获节点仅在探测到传感器时才会出现。

这值得明确说明，因为它是一个分支点。如果内核暴露了一个V4L2编码器，硬件H.264就完全不需要任何额外的树外代码。

### 权限陷阱

`/dev/mpp_service` 的权限为 `crw------- root root`，模式为 0600。非 root 进程无法打开它 —— 而且 **`mpi_enc_test` 对它的测试会写入一个空文件并退出 0**。没有错误，也没有日志行。
因此，零退出状态并不是证据；文件大小才是证据。
`mediad` 将以独立用户身份运行，就像这里其他每个守护进程一样 —— `tofd` 骑入 `i2c`，`padd` 骑入 `input`，`btd` 骑入 `bluetooth` —— 因此 VPU 需要同样的待遇：一个 udev 规则给节点分配一个组，以及单元文件中的 `SupplementaryGroups=`。`scripts/setup-gstreamer.sh` 安装了这条规则（`99-robot-mpp.rules`，组 `video`，模式 0660），遵循 `setup-board.sh` 中 `configure_tof` 的 i2c 规则的形状。

`video` 而不是 `robot`：`robot` 控制我们定义的 IPC 套接字（参见 `[app-path-design.md](../design/app-path-design_zh.md)` §，套接字模式加组的分层）。一个内核设备节点不是我们能重新定义的，`video` 是这个设备类的发行版惯例，因此一个拥有 `gst-launch` 的开发者将以与 `mediad` 相同的方式进入。

## Radxa 提供的内容

Rockchip MPP 不在 Debian 中。Radxa 将其发布为 GitHub Pages apt 仓库，并直接作为 **`.deb` 下载** 而不是通过将仓库添加到 `sources.list` —— 这正是 `microduck_runtime/radxa_setup/setup_rkaiq.sh` 在此板上为 `rkaiq_3A_server` 所使用的路径。基础：`https://radxa-repo.github.io/bullseye/pool/main`。
| 包 | 版本 | 为什么 |
|---|---|---|
| `m/mpp/librockchip-mpp1` | 1.5.0-1 | MPP用户空间库 |
| `m/mpp/librockchip-vpu0` | 1.5.0-1 | `rockchip-mpp-demos` 依赖于它且版本精确 |
| `m/mpp/rockchip-mpp-demos` | 1.5.0-1 | `mpi_enc_test` — 证明VPU不涉及GStreamer |
| `m/mpp/librockchip-mpp-dev` | 1.5.0-1 | 头文件，用于构建编码插件 |
| `libr/librga/librga2` | 2.2.0-1 | 鲲鹏2D加速器；rockchip插件依赖于它 |
| `libr/librga/librga-dev` | 2.2.0-1 | 头文件，相同的构建 |
| `g/gstreamer1.0-rockchip/gstreamer1.0-rockchip1` | 1.14-4 | MPP GStreamer插件 — 请参阅下方 |

这些是bullseye构建，它们可以干净地配置在trixie上，与glibc 2.41兼容。

**`dpkg -i` 无法解决任何问题**，因为这些包没有来自配置的apt源。每个缺失的依赖项都是未配置的包而不是自动修复的安装，因此每个集合必须列出其完整的闭包。这花了三个往返才能了解清楚。

### Radxa的预构建插件并非仅解码，而此页面曾说它是
`gstreamer1.0-rockchip1_1.14-4` 在 GStreamer 1.26.2 中安装和注册得非常顺利，显示了 `mppvideodec` 和 `mppjpegdec`。这表明“没有编码器”，而该页面正是这样宣称的——这是错误的。通过 `strings` 命令查看其 `.so` 文件，列出了 `mpph264enc`、`mpph265enc`、`mppjpegenc` 和 `mppvp8enc`。它们都在那里。

**权限陷阱是整个解释，它在这一点明确之前产生了四个单独的误导结果：**

| 看起来像 | 实际上是 |
|---|---|
| `mpi_enc_test` 没有任何输出并且 **退出码为 0** | 节点不可打开；零退出码表示 nothing |
| Radxa 的 deb 包仅用于解码 | 它包含所有编码器 |
| 第三方的 1.14-8 deb 包仍然没有显示 `mpph264enc` | 同样的原因再次出现 |
| 我们的 CI 构建仅列出了两个解码器 | 容器也没有 `/dev/mpp_service` —— 这是预期的，而不是失败 |

一个 MPP 插件 **无条件地注册其解码器，并在注册编码器之前探测 MPP。** 当 `/dev/mpp_service` 的权限为 `0600 root:root` 时，探测会静默失败，因此即使插件中包含编码器，编码器也会被省略。
So 插件仅列出解码器是关于 *设备节点* 的证据，而不是关于插件本身，`gst-inspect-1.0 mpph264enc` 在 udev 规则就位之前没有任何意义。

安装确实证明了一件事，而且它依然有效：**一个构建于 GStreamer 1.14 的插件可以在 1.26.2 中注册而没有任何抱怨**。插件的 ABI 是担心源码构建的原因，但其实并不是风险。

## 需要构建的内容

两个插件，出于两个不相关的原因。它们互不替代。

| 插件 | 源码 | 提供 | 为什么不能安装 |
|---|---|---|---|
| `gstreamer-rockchip` | [`JeffyCN/mirrors`](https://github.com/JeffyCN/mirrors) 分支 `gstreamer-rockchip`，meson | `mpph264enc` — 硬件编码器 | Debian 完全没有 Rockchip 编码器。Radxa 的构建确实有这些编码器，因此这是关于一个我们控制的引脚，移除 `libx11-6`，并随下面的插件一起构建 |
| `gst-plugin-webrtc` | [`gst-plugins-rs`](https://gitlab.freedesktop.org/gstreamer/gst-plugins-rs) 版本 0.15.3，cargo-c | `webrtcsink`，`webrtcsrc` | `gst-plugins-rs` 在 **任何** Debian suite 中都没有打包 |
0.15.3 而不是 0.14.5 的 `reachy_mini` SDK 文档：0.14.5 是关键版本 — 在此之下，`webrtcsink` 之间缺少了一个关于远程描述和 ICE 处理之间的死锁修复，这表现为客户端永远卡在“连接中”——而 0.15.3 则是更新的版本。两个系列都声明需要 GStreamer `v1_22` 特性，并且机器人运行的是 1.26.2，因此更新的版本没有任何额外成本。

`webrtcbin` **确实**已经安装了，来自 `gstreamer1.0-plugins-bad`。因此，今天可以不进行第二次构建就使用 WebRTC 会话，代价是我们需要自己实现信令协议。`webrtcsink` 更受欢迎，因为它的信令协议是中继代理使用的，这使得中央信令服务器可以重复使用。

### 为什么不使用预构建版本
The 硬件、内核驱动和MPP的用户空间库都工作在没有任何编译的情况下——`mpi_enc_test` 来自一个deb包，并且第一次尝试就编码了720p H.264。缺少的是 *GStreamer 绑定*：一个插件，将 `librockchip-mpp` 包装为一个管道可以使用的元素。`mpi_enc_test` 是一个独立程序；GStreamer 并不知道它的存在。这里与 ONNX 运行时相同——`libonnxruntime.so` 是从一个 tarball 安装的，没有任何编译，`ort` 是使其可访问的绑定。

预构建的绑定：

| 来源 | 所包含的内容 |
|---|---|
| Radxa `bullseye` 池 | `gstreamer1.0-rockchip1_1.14-4` — 安装并检查：`mppvideodec` + `mppjpegdec` 仅此而已 |
| Radxa `rk3588s2-bookworm` 池 | 同样的 `1.14-4`，字节级相同 |
| [`numbqq/gstreamer-rockchip-debs`](https://github.com/numbqq/gstreamer-rockchip-debs) | `1.14-8` — **包含每一个编码器** |
The last one是在构建任何东西之前值得尝试的。它的`bookworm/arm64/<板卡>/`条目是
指向`jammy/arm64/`的符号链接，因此这是一个基于Ubuntu 22.04的构建，来自
`rockchip-linux/gstreamer-rockchip`（现在404），由陈杰夫维护——Radxa构建的同一个上游版本，在一个启用了编码器的分支上。`mpph264enc`、`mpph265enc`、`mppjpegenc` 和 `mppvp8enc` 都包含在`.so`文件中。

它的`DT_NEEDED`由上面的deb包已经提供的板卡所满足：
`librockchip_mpp.so.1`、`librga.so.2`、`libgstreamer-1.0.so.0`、`libgstvideo`、
`libgstallocators`、`libgstpbutils`、`libdrm2`、`libglib2.0-0`、`libx11-6`、`libc6 >= 2.33`，针对glibc 2.41。其中没有任何RK3588特定的内容——SoC的差异存在于MPP内部，而不在于插件——并且`Depends`仅从下限（`>= 1.14`）约束GStreamer。

我们的构建在[`microduck-gst-plugins`](https://github.com/pollen-robotics/microduck-gst-plugins)
——一个独立的仓库，有意为之：
- **不在构建板上。**RK3566编译Rust部分过于缓慢，无法等待。
- **也不是交叉编译。**守护进程通过`cargo-zigbuild`进行交叉构建，`scripts/ci-cross-deps.sh`明确指出其唯一的C依赖“是那个例外的成本，值得在添加另一个之前阅读”。GStreamer将是第二个更大的例外，而两条路径——x86多架构，或带有meson交叉文件的sysroot——都会链接到目标的近似版本。
- **在`debian:trixie`容器中的arm64运行器上本地构建，**这是机器人的用户空间。没有任何近似。公共仓库中的arm64运行器是免费的。
- **还有一个公共原因更为重要：**下载发生在配置过程中，并且从更新器的`preinstall`挂钩中进行，该挂钩在清空环境并且**没有令牌**的情况下运行。这与守护进程已经依赖于ONNX Runtime的相同安排相同。
- 翻译全文，保持忠实。不要总结、省略或添加新内容。
它会构建两个插件，在一个 `pins.env` 中按提交或标签锁定上游代码，禁用 `rkximage` 和 `kmssrc`（同一树中的 X11 和 KMS 汇聚点——一个无头机器人既不需要它们，也是为什么预构建的 Radxa deb 依赖于 `libx11-6` 的原因），并发布一个 tarball 及其 sha256 哈希值，以及一个 `MANIFEST` 文件，该文件按插件指明了确切的上游引用。该清单就是第三方 deb 无法回答的东西。

它防范了两个陷阱，都是通过阅读树结构而不是失败发现的：
`gst/rockchipmpp/meson.build` 结尾是 `if not mpp_dep.found() → subdir_done()`，因此缺少 `librockchip-mpp-dev` 会使 meson **跳过该插件并成功**；而 `dpkg -i` 对直接下载的 `.deb` 文件不起作用，因此 Radxa 闭包可以在一次调用中安装。

**`mediad.service` 必须设置 `GST_PLUGIN_PATH`。** 这些插件安装到 `/usr/local/lib/gstreamer-1.0`，而 GStreamer 默认不会搜索该目录——其内置路径是发行版的 `/usr/lib/aarch64-linux-gnu/gstreamer-1.0`，并且该目录故意被避开，以免 `apt` 操作可以替换或移除它们。因此该单元需要
```
Environment=GST_PLUGIN_PATH=/usr/local/lib/gstreamer-1.0
```
alongside the `SupplementaryGroups=video` VPU节点需要。两者都很容易被遗忘，两者在运行时的表现也相同：编码器 simply 不存在，没有任何信息说明原因。

`scripts/setup-gstreamer.sh` 在一个 **固定版本** 下消费它 —— 从不使用 "latest"。两天内两次不同的预置运行生成了不同的插件，而没有任何记录，这相当于一个未再现的媒体错误。这个固定版本存在于 `Cargo.toml` 中的 `[workspace.metadata.gst-plugins]` 中，脚本中使用了字面值，因为它单独通过 `curl` 获取，而 `xtask` 测试断言它们一致 —— 同样的安排，同样的原因，就像 `ONNX_VERSION` 一样。

**尝试第三方 deb 不同于依赖它。** 它只是一个我们无法控制出处的单板特定 dump，如果那个仓库消失了，它也会随之消失。它以低廉的成本提供了唯一真正的问题的答案 —— 这个插件是否与 *我们的* MPP 和 GStreamer 版本兼容 —— 如果兼容，那么自己构建相同的源代码就降低了风险而不是变得多余。我们自己的固定版本构建仍然是最终目标。
**The build could be完全避免构建**通过从`mediad`调用MPP的C API并借助Rust FFI，这已经被`mpi_enc_test`证明可行。这将一个meson构建换成了手写并手动维护的供应商库绑定，这是交易的劣势一面——但这确实是一个可行的选择，而不是死胡同，如果插件最终与GStreamer 1.26冲突的话。

### 上游

`rockchip-linux/gstreamer-rockchip`已不存在（404）。`JeffyCN/mirrors@gstreamer-rockchip`是活跃的镜像——最后一次提交日期为2026-05-21——并且`gst/rockchipmpp`包含`gstmpph264enc.c`，`gstmpph265enc.c`，`gstmppjpegenc.c`，`gstmppvp8enc.c`。围绕它存在一些分支；无论使用哪个分支和标签，都需要固定并记录，原因与`gst-plugin-webrtc`固定在≥0.14.5相同。

### `gst-plugin-webrtc`的固定版本

**0.14.5或更新版本，而不是0.14.4。** 早期的标签缺少了一个`webrtcsink`死锁修复，该修复涉及远程描述和ICE处理之间的问题，这表现为客户端无限期地停留在“连接”状态。`reachy_mini`的SDK安装文档记录了这一点；请注意，`reachy-mini-desktop-app`提供了0.14.4版本，因此处于那条线的错误一侧。
Pollen已经为**x86_64**提供了此插件——通过`cargo cinstall`本地构建，剥离后提交，并按架构分开。CI会固定在某个提交引用加上sha256。在同一位置的`aarch64/`分支可能比这里增加一个管道要少一些工作量。

### 插件应放置的位置

在守护进程的发布包中，`GST_PLUGIN_PATH`指向`current`目录——不在`apt`中，也不在每台机器上的`/opt`目录中。

插件版本与`mediad`的代码是纠缠在一起的：上述0.14.5的情况就是一个插件版本决定守护进程是否需要一个变通方案的案例。版本不一致是`mediad`的bug，因此它需要`mediad`的生命周期——原子交换、回滚、健康门。`librockchip-mpp`正好相反：这是一个与内核配对的系统库，任何接触VPU的组件都需要它，并且应该在包管理器中。

## 已度量，未度量

**测得结果：** GStreamer 1.26.2 及其来源；`webrtcbin` 存在；`webrtcsink`/`webrtcsrc` 不存在；`v4l2h264enc` 不存在且无 `/dev/video*`；`/dev/mpp_service` 以 0600 根权限:根存在；非 root 用户运行 `mpi_enc_test` 时静默无输出，以 root 用户运行时输出 428 KB；该比特流解码干净，符合 High/4.0；Radxa debs 的依赖闭包；在 1.26.2 中 rockchip 插件加载时包含两个解码元素。

**编码路径在硬件上端到端被关闭。** 顺序如下：
1. `v1` 从公共发布版本获取，sha256 校验后安装到了 `/usr/local/lib/gstreamer-1.0`。
2. `gst-inspect-1.0 mpph264enc` 返回 `provided-by /usr/local/lib/gstreamer-1.0/libgstrockchipmpp.so` — 我们的构建版本。第三方 deb 首先被移除，以便答案可以归因于某个特定的版本。
3. 它 **编码**：`videotestsrc ! mpph264enc profile=baseline header-mode=each-idr bps=2000000 ! h264parse ! filesink` 生成了 60 帧 720p 视频的 476 KB，耗时 **0.44 秒**（包含源生成和管道设置时间），比实时处理快得多。结果可以通过 `avdec_h264` 正常解码。
4. 它 **无需 root 权限**：在 udev 规则将 `/dev/mpp_service` 设为 `660 root:video` 并且用户加入 `video` 组后，`gst-inspect` 以该用户身份返回结果。这也是 `mediad` 的情况，而在此之前的每一个检查都使用了 `sudo`。

**整个媒体链在硬件上是封闭的。** 从传感器到可协商的 WebRTC 流：
| 步骤 | 证据 |
|---|---|
| 覆盖层应用 | `csi2-dphy0` 探测成功，`rkisp` 启动，十个 `/dev/videoN` |
| 传感器识别 | `imx219 2-0010: 模型 ID 0x0219，批次 ID 0x5a8e73，芯片 ID 0x0773` |
| 捕获节点 | `/dev/video0`，卡名 `rkisp_mainpath`，格式为 3280x2464 |
| 帧数 | 13,824,000 字节，`--stream-count=10` 720p NV12 — 精确 |
| 硬件编码 | `v4l2-ctl … --stream-to=-` 进入 `fdsrc ! rawvideoparse ! mpph264enc` |
| 流 | 解码清晰；`h264parse` 报告 **1280x720 限制基线** |

节点编号在不同启动中不一致，因此捕获节点通过匹配 `/sys/class/video4linux/*/name` 下的卡名 `rkisp_mainpath` 找到 —— 如 `camera.rs:219` 所示。

### 需要 `video` 组的设备节点有三个，而不是一个

这花费了三次单独的调试轮次，每次都有命名不同的失败：
| 节点 | 根用户唯一时的症状 |
|---|---|
| `/dev/mpp_service` | `mpi_enc_test` 写入 nothing 并 **退出 0**；`mpph264enc` 从未注册 |
| `/dev/rga` | 元素存在，管道启动，然后出现 `尝试使用未初始化的 rgaCtx=(nil)` 和 `rga 调用 blit 失败` 的页面 |
| `/dev/video0` | 到达 `root:video`，所以是那个不起作用的 |

`setup-gstreamer.sh` 安装了一个 udev 规则覆盖前两个。
**`mediad.service` 需要 `SupplementaryGroups=video`** — 与 `Environment=GST_PLUGIN_PATH` 一起，
这是在工作管道和四个不同的令人困惑的失败之间仅有的两行代码。

### 那个花费 22 fps 的旋转

相机安装了一个四分之一的偏移，显而易见的修复 — 在 tee 之前使用 `videoflip`，这样每个
消费者都能得到一个直立的图像 — 在机器人上测量是错误的：

| | RGA 失败 | `v4l2src` 丢失的帧数 | fps | SoC |
|---|---|---|---|---|
| 未旋转 | 0 | 0 | ~30 | 正常 |
| 旋转 | 一个会话中 5522 | 1565 | 7–8 | 97 °C，CPU 408 MHz |
`mpph264enc` 将UYVY→NV12的转换交给SoC的2D引擎处理，并不为此支付任何费用。
`videoflip` 的输出是RGA拒绝处理的缓冲区——`10000 is unsupport format`，然后在`rect[0, 0, 720, 1280]`上出现`RGA_BLIT fail: Bad address`——因此MPP不得不在软件中转换 **每一帧**。这使CPU饱和，SoC达到其热限，一切都被限制到408 MHz，相机无法交付的帧数开始丢失。旋转本身只是账单中较小的一部分。

因此，管道中没有任何东西进行旋转。镜头 *报告* 了（`media.video`，每控制通道一次）并且显示图片的人会旋转它：控制台使用CSS transform来实现，这是免费的，而感知消费者会将其纳入其已经进行的插值中。`--flip-in-pipeline` 为一个无法自行旋转且负担得起这种行为的消费者恢复了旧的行为。

如果确实需要直立的流，正确的修复方法是在插件集中添加一个RGA元素：2D引擎旋转是免费的，这就是编码器能够使用它的原因。
### 3A引擎必须在流开始前等待
`rkaiq_3A_server` 连接到ISP然后等待一个 **流开始** 事件——但它错过了已经发生的一个。在 `mediad` 流式传输时重启它，它会停留在
```
DBG: /dev/media0: wait stream start event...
```
for ever: 不统计循环，因此没有自动曝光和白平衡，结果是一张绿色的照片。重启“修复”了这个问题，只是因为重启恰好顺序正确地解决了问题。

这使得这是一个没有明显原因的回归，因为 **每次 `robotctl update apply` 重启了正在运行的流下的引擎**：预安装挂钩运行 `setup-rkaiq.sh`，这个脚本会重启 `rkaiq_3A`。甚至打印了“重启摄像头流才能生效”的提示——但没有人遵循这条建议，也没有强制执行。

因此，这个脚本安装的 drop-in 现在携带了不变量：
```ini
ExecStartPost=-/bin/systemctl --no-block try-restart mediad.service
```
每当引擎启动时，流会被抛在它的后面，因此它等待的事件是一个尚未发生的事情。`try-restart`会留下一个没有 `mediad` 的棋盘，而 `--no-block` 则防止一个单位因等待另一个单位的任务而死锁 systemd。手动救援一个棋盘的关键在于顺序：
```bash
sudo systemctl stop mediad && sudo systemctl restart rkaiq_3A && sleep 2 && sudo systemctl start mediad
```
### rkaiq的自动曝光只触发一次，并且仅在捕捉到流时触发

`scripts/setup-rkaiq.sh`首次发布时开启了rkaiq的AE功能，原因在于：原型版中禁用了AE，是为了避免引擎与拥有自身曝光控制的运行时发生冲突，而在`mediad`中没有任何组件拥有曝光控制，因此引擎应该拥有这一控制权。它确实会写入传感器值，但不会持续写入。

在一台机器人上进行测量，当组件启动顺序正确时——`rkaiq_3A`在17:24:01启动，`mediad`在17:24:11启动，`wait stream start event success`在17:24:17启动：

| 事项 | 值 |
|---|---|
| `mediad`在17:24:17写入 | `exposure=600 analogue_gain=1024` |
| `/dev/v4l-subdev3`，几分钟后 | `exposure: 1589  analogue_gain: 1536` |
| 手动写入`exposure=300 analogue_gain=256`，然后观察25秒 | `300 / 256`，未校正 |

因此，引擎仅收敛了一次，收敛的结果明显是引擎自己的，而不是我们的，然后停止了：在流启动时只进行一次收敛，并不意味着实现了自动曝光——一台从窗户走进走廊的机器人，不会改变窗户的曝光设置。

| what | value |
|---|---|
| `mediad`在17:24:17写入 | `exposure=600 analogue_gain=1024` |
| `/dev/v4l-subdev3`，几分钟后 | `exposure: 1589  analogue_gain: 1536` |
| 手动写入`exposure=300 analogue_gain=256`，然后观察25秒 | `300 / 256`，未校正 |
**并且在引擎错过流启动事件的启动器中——上述部分——即使一次事件也没有发生。** 这个情况首先被测量并读取错误：传感器在被监视期间一直停留在 `600 / 1024`，并且手动写入操作卡住，这看起来像是一个从未工作的AE，而实际上是一个从未被给予流的AE。这两种状态从单次读取传感器的角度来看是不可区分的，这就是为什么这两种修复需要一起进行：排序修复是使它们变得可观察的原因。

`mediad::exposure` 是闭合回路的部分，是从原型的 `ae_loop` 转移过来的：每秒两次从摄像机的原始分支获取平均亮度与设定点 90 进行对比，并且一个阻尼乘法步骤分布在噪声顺序中的三个控制中——快门至 600 行（≈11 毫秒，短到不会模糊行走的机器人），然后是模拟增益至 11 倍，然后是快门至 1200 行，最后是ISP数字增益。硬快门上限是一个实际的天花板：驱动程序对超过帧长的曝光时间通过 *拉伸帧时间* 而不是钳位来响应，因此 3500 行会无声地给出 15 帧每秒。
Two 事情它做了不同之处，因为 `mediad` 是更适合它的地方。
Luma 来自已经为鸭子检测器提取的帧，因此没有进行 JPEG 解码，也没有再次打开摄像头 —— 与原型的第一版不同，后者通过使用并行的 `v4l2-ctl` 采样 ISP 自身路径来计量，这在驱动级别上与自身的捕获争抢资源，并间歇性地中断了流水线。而且第一次写入会进行读取回显：任何可能导致失败的方式（缺少控制节点、拒绝访问、没有 `v4l2-ctl`），否则都会使摄像头保持在一个曝光值上，这与它要修复的 bug 没有区别。

`setup-rkaiq.sh` 现在断言 `CommCtrl.Enable = 0`。不是因为引擎的 AE 无所作为，而是因为它的操作发生在流开始时 —— 正是 mediad 的循环从其初始值收敛到一起的时候，也就是两个写入者争夺一个控制权的时候。
**One thing `v4l2-ctl`会做而你在测量任何这些内容时：**一个未知的控制名称会导致整个`--set-ctrl`或`--get-ctrl`失败。`--get-ctrl=exposure,analogue_gain,digital_gain`返回`unknown control 'digital_gain'`且没有读取到曝光值，这表示该节点既不携带曝光值也不携带数字增益值。`mediad::exposure`由于这个原因需要在两次调用中分别写入传感器对和ISP的数字增益。

### 两个已知未完成的问题

**码率比目标低约50倍。**3.3秒的捕获数据量为15,553字节，相对于`bps=2000000`，码率约为37 kbps。要么场景足够静态以至于CBR崩溃——这是有可能的；要么ISP处于默认设置，图像在`scripts/setup-rkaiq.sh`运行之前是绿色且噪点较多（该脚本是从原型移植而来；配置和预安装挂钩现在都会运行它）；或者捕获帧率低于30 fps。帧计数尚未测量。如果是后者，传感器模式可能是嫌疑对象：IMX219在启动时设置为3280x2464，原型通过`media-ctl`在每次捕获前固定模式（`camera.rs:277`）。
**`rawvideoparse blocksize=1382400` 是一个启动快捷方式，而不是设计。**它之所以能正常工作，是因为
`v4l2-ctl` 以我们计算出的大小发出紧密打包的 NV12，并且一旦在其他分辨率上出现对齐填充，它就会变得错误——`camera.rs` 正是这样记录的。`mediad` 通过自己的 V4L2 mmap 循环直接进入 `appsrc`，而不是假设对齐值，从而获取真实的对齐值。

## 管道需要决定的两件事

**捕获不能使用 `v4l2src`。** rkisp 驱动程序向它提供一个 2 缓冲区池，但它重新排队得太慢，每丢弃一帧——从 30 fps 的传感器获取约 20 fps 的帧率，并且会检测到“丢失帧”。`v4l2-ctl --stream-mmap` 可以维持全速率，因此 `microduck_runtime` 使用它并将其原始帧管道到一个 `fdsrc` 管道中（`camera.rs:487`）。`mediad` 需要这种子进程的形状或者它自己的 V4L2 mmap 循环向 `appsrc` 供入数据。

**四个 `mpph264enc` 属性是管道决策，而不是默认继承的属性。** 从板上的元素读取它们：
| 属性 | 默认值 | `mediad` 应该设置为何 | 原因 |
|---|---|---|---|
| `profile` | `high` | **`baseline`** | WebRTC 的互操作底线是 Constrained Baseline (`profile-level-id 42e01f`)。当前浏览器协商为 High；较旧的对等方则不然。设置 `baseline` 会生成一个 `h264parse` 报告为 `constrained-baseline` 的流——经过验证，而不是假设，因为该枚举仅说明为“baseline” |
| `header-mode` | `first-frame` | **`each-idr`** | 第一帧中的 SPS/PPS 仅意味着后来加入的对等方——或丢失了该数据包——永远无法解码任何内容。`reachy_mini` 的 Pi 管道通过 `repeat_sequence_header=1` 在 `v4l2h264enc` 上设置了这一点；同样的需求，不同的拼写 |
| `rotation` | `0` | **`180`** 在 alpha 中 | IMX219 逆置安装。`microduck_runtime` 通过 `videoflip method=rotate-180` 来解决这个问题——在 SoC `robotd` 共享的每帧上进行一次完整的 CPU 过滤。编码器在硬件中免费完成此操作 |
| `bps` | `0`（自动） | 明确的目标 | `rc-mode` 已经默认为 `cbr`，这正是有损链路所需要的；比特率不应留待“自动计算” |

两个实际上不需要决策的事情：
- **根本没有B帧开关**，因此§5.5的“不使用B帧”要求是通过构造而不是配置来满足的。
- **sink pad 接受 `NV12`**，这正是rkisp捕获路径发出的内容。在捕获和编码之间没有 `videoconvert`，也没有RGA颜色转换。

关键帧应来自 `min-force-key-unit-interval` 而不是周期性的 `gop`：WebRTC 是从对端的PLI驱动它们的，而 `gop` 的默认值是一秒一个IDR，无论是否需要。

### 限制标志值得一看，而模板比标志更差

这个页面以前会要求某人验证某件事而不是假设它：`profile` 枚举值为 `baseline`（66），而WebRTC 协商的是*受限*基础配置，一个避免FMO、ASO和冗余切片的基础流正是受限基础解码器所期望的。从黑板上读取：
### 限制标志值得一看，而模板比标志更差

这个页面以前会要求某人验证某件事而不是假设它：`profile` 枚举值为 `baseline`（66），而WebRTC 协商的是*受限*基础配置，一个避免FMO、ASO和冗余切片的基础流正是受限基础解码器所期望的。从黑板上读取：
```
gst-launch-1.0 -v videotestsrc num-buffers=60 ! video/x-raw,format=NV12,width=1280,height=720,framerate=30/1 ! mpph264enc profile=baseline ! h264parse ! fakesink
```
`h264parse` 在其 src pad 上协商 `profile=(string)constrained-baseline`。因此，流是正确的：`profile=baseline` 关闭了 CABAC 和 8x8 变换，MPP 不发出 FMO、ASO 或冗余切片，且 SPS 携带 `profile_idc=66` 以及 `constraint_set1_flag`。

**错误在于 pad 模板，这花费了一整天。** `mpph264enc` 的 src 模板列出了 `profile = { baseline, main, high }`，而省略了 `constrained-baseline` —— 这正是 WebRTC 所要求的唯一配置文件。只有当编码器位于 `webrtcsink` 内部而不是其前端时，这一点才重要，这也是为什么这里最初没有看到它的原因：
1. `webrtcsink` 的编解码发现机制在没有输出 caps 的情况下构建其编码链，因此 `force_profile` 为真，并插入一个 capsfilter 要求 `profile=constrained-baseline`。
2. `h264parse` 从 caps 查询中剥离了 `alignment`、`stream-format` 和 `parsed`，但 **不剥离 `profile`**，因此该需求传递到了编码器的 src 垫。
3. 空交集与模板。`GstVideoEncoder` 的 sink getcaps 返回空值，失败在上游四个元素处显现为 `videorate` 报告它“无法将 NV12 … 转换为我们支持的任何内容”。
4. 发现机制在 `gst::warning!` 中丢弃了 H.264，转而协商 VP8，会话在 `rtpvp8pay` 处结束。** nowhere 命名了该配置文件。**

两个教训而不是一个。插件仓库现在携带了一个一字补丁，扩展了该模板，并以 `v3` 版本发布。而 `mediad` 必须在这一切变得可见之前，将 GStreamer 的日志和管道总线桥接到日志中——在此之前，所有媒体失败都是静默的，包括会话在协商中途结束的情况。

### 预编码不再是那个形状
This page 以前通过指出 `webrtcsink` 接收其接收端口预编码的 H.264 来关闭，因此 `appsrc ! mpph264enc ! h264parse ! webrtcsink` 保持编码器完全不出现在协商之外。确实，这最初有效 —— 但这样做有两个难以弥补的成本。`webrtcsink` 无法访问它不拥有的编码器，因此拥塞控制无法根据链路调整比特率，而且对等方的 PLI 也无法生成关键帧：一个丢失关键帧的观众将保持损坏状态，直到下一个周期的 GOP。

因此 `mediad` 会向它提供原始的 NV12 并让其构建编码器，通过 `encoder-setup` 信号配置每个编码器 —— 这就是上面表格现在适用的地方。代价是编码器 *确实* 参与了协商，这也是上面模板缺口被发现的原因。
