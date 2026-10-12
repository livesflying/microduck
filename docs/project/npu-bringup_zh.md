# NPU 及其上的鸭子检测器

RK3566 配备了一个小型 INT8 NPU — 0.8 TOPS，单核。本文档记录了将训练好的鸭子检测器部署到其上的过程：需要运行的内容、预期结果以及在行为能够使用它之前还缺少什么。

该模型在 [duck_detector](https://github.com/pollen-robotics/duck_detector) 中进行训练，并以量化后的 `.rknn` 格式提供。第一个模型，作为参考：`yolo11n`，分辨率为 320×320，一个类别，来自三个会话的 150 帧，保留会话外的 mAP50 为 0.976 — 经过 INT8 量化后，大小为 3.9 MB，且保留了与桌面上的浮点模型在 95% 盒重叠率下的 2 个检测中的 2 个。

## 模型的来源

**The Hub，策略执行的方式。** `duck_detector` 每次运行都会发布到
[`pollen-robotics/microduck-duck-detector`](https://huggingface.co/pollen-robotics/microduck-duck-detector)
—— NPU 为 `duck_detect.rknn`，CPU 回退为 `duck_detect.onnx`，在仓库根目录下以固定名称命名，每次运行一个标签。此仓库中没有任何内容携带权重：`mediad` 从 `/opt/robot/detector/current` 读取它们，而填充该目录的是

| | |
|---|---|
| `scripts/seed-detector.sh` | 由发布后的安装钩子运行；在没有任何内容的板上安装引脚，并且仅安装它未安装的设置 |
| `robotctl duck-detector check` | 与仓库提供的内容进行比对 |
| `sudo robotctl duck-detector update [--version <tag>]` | 安装一个修订版并重启 `mediad` 到该修订版 |

这是 `seed-policies.sh` 和 `robotctl policy check/update` 的不同根目录和固定文件列表，由相同的 `updaterd` 调用（`detector.check`，`detector.install`）提供，并且 `docs/design/policy-channel-design.md` §9 中有延续的推理：引脚是一个底线，任何不完整的更改都不会上线，重训练是一个标签而不是一个守护进程发布。

值得了解的两件事。模型仓库 **与数据集仓库同名**；机器人仅针对模型进行地址（`…/resolve/<rev>/…`，`api/models/…`），而数据集则位于 `datasets/` 下，因此机器人上没有任何内容会意外地落在帧上。而 `update` 的“最新”是根据 **版本标签** 决定的（`v2` 排序在 `v1` 之上；名称如 `experimental` 从不计入），因此用于机器人的运行希望有一个 `vN` 标签 — 第一次运行被标记为 `duck-v1`，这是引脚所命名的，且可以通过名称安装，但 `check` 无法对其进行排名。

## 这里包含的内容
| | |
|---|---|
| `duck-detect` | 信封、运行时绑定和解码——以及 `duck-bench`。 |
| `scripts/setup-npu.sh` | 启用NPU节点，安装 `librknnrt.so`，并报告驱动程序状态。 |

两个在阅读之前需要知道的决定：

**`dlopen`，而不是链接。** `librknnrt.so` 并不在任何 Debian 仓库中，且一个链接了它的 crate 在 CI 中无法进行交叉编译。`robotd` 通过相同的方式与 ONNX Runtime 交互。代价是 `duck-detect/src/rknn.rs`；好处是 `cargo board --bins` 在笔记本上仍然可以正常工作。

**运行时去量化。** 量化模型的输出张量是带有缩放因子和零点的 int8。`rknn_outputs_get` 如果被请求的话会将其转换为浮点数，而它确实被请求了——否则，携带缩放因子到解码器中并悄悄地出错一次是另一种选择。

## 运行基准测试

驱动程序是关键：它是供应商内核的一部分，主线内核中没有，而用户空间中的任何内容都无法绕过其缺失。

**普通的 `robotctl update` 就能完成这个任务。** `hooks/preinstall` 会在 `setup-gstreamer.sh` 和 `setup-rkaiq.sh` 旁边运行发行版自己的副本，从不致命，并将报告记录在更新日志中——因此，一个在 NPU 之前存在的板子可以通过更新来修复，而不是通过有人记得某个命令来修复。手动运行它是一个重试过程：
```bash
sudo sh /opt/robot/daemon/current/scripts/setup-npu.sh
```
**预期第一个包含此内容的更新会要求进行重启。**Armbian在每个Radxa Zero 3上将`npu@fde40000`设置为`status = "disabled"`，因此一块出厂的板子有硬件、内核和驱动，但仍然没有NPU。脚本会写入修复它的overlay并说明这一点；节点会在下次启动时绑定。`--no-enable-node`仅安装运行时，而`dmesg | grep rknpu`是确认的方法。

运行发布版本而不是`/usr/local/sbin/robot-setup-npu`：overlay的源代码位于脚本旁边，而`/usr/local/sbin`中的副本在第一次运行时没有任何内容。

然后，从你机器上的克隆版本：
```bash
cargo board --bins -p duck-detect
scp target/aarch64-unknown-linux-gnu/release/duck-bench microduck@<robot>:/var/tmp/
scp <the>.rknn microduck@<robot>:/var/tmp/duck.rknn
scp -r datasets/raw/<a-session> microduck@<robot>:/var/tmp/frames
```
`duck-bench` 不在任何版本中：它是一个测量工具，将其打包会将它安装在每台机器人上，只为两个人提供便利。它会使用 `scp`，直到出现需要检测器的行为，此时发布的将是 `mediad` 内的检测器，而不是这个工具本身。
```bash
/var/tmp/duck-bench --model /var/tmp/duck.rknn --frames /var/tmp/frames
```
它依次回答三个问题：

1. **能运行吗？** 如果运行环境无法加载、模型构建于其他平台或运行时驱动版本过旧，都会在此阶段失败，而不是在守护进程内部。
2. **还能识别鸭子吗？** 它以每帧报告检测结果，因为一个能运行但无法识别任何内容的模型与正常工作的模型看起来完全一样。
3. **成本是多少？** 延迟百分位数和此进程所消耗的CPU —— 使用NPU的目的是让`robotd`的50 Hz循环保持不变，这也是需要衡量的指标。

`--threshold` 是首先要尝试的标志。**量化模型的得分有自己的标度** —— 浮点模型的0.5并不等于此模型的0.5 —— 因此，检测不到任何内容的运行更可能是阈值问题而非转换失败。在相信最坏情况之前，可以先尝试`0.2`。

## 数据

从Radxa Zero 3出发，`duck-bench`以2 Hz的节奏运行，30帧，3次通过：

| | 测量值 | 备注 |
|---|---|---|
| 驱动 / 运行时 | 0.9.8 / 2.3.2 | `setup-npu.sh` 打印两者 |
| 延迟 p50 / p95 | 25.7 ms / 58.4 ms | 推理加上解码，不包括JPEG解码 |
| 每帧CPU | 20.7 ms | 请参阅下方 —— 这并非全部推理 |
| 识别结果 | | 对比已由人力标注的帧 |
| SoC温度 | 63 °C | 在持续运行结束时 |

**CPU数值并非NPU的成本，而其报告方式容易让人误读为成本。** 延迟列的时间为`infer` + `decode`；CPU列是整个循环中此进程的CPU总耗时除以帧数，因此也包括了`letterbox_rgb` —— 一个从1280×720到320×320的分辨率调整，运行在CPU上且不在延迟中体现。剩余部分是否意味着`rknn_run`忙等待（将NPU的等待时间转嫁给CPU）尚不清楚。在2 Hz下，无论哪种情况都占一个核心的4%；在任何人引用这个数字作为感知成本之前，两者应分别测量。

## 仍缺失的内容

`mediad`有一个原始分支tee，专门为此而设 —— `architecture.md` §5.3。有两种前进方式，它们并不互相排斥：
- **`media.frame`** — **已完成。** 一个返回一帧图像的调用，通过 `mediad` 自己的 Unix 套接字 (`/run/mediad/media.sock`) 返回，与其他观察套接字一样具有组读权限。这不仅用于感知（控制台中的快照，用于错误报告的静止图像），还意味着捕获数据集不再需要停止 `mediad` 来获取相机图像。它会以 JSON-RPC 头命名字节数，然后发送这些字节：一个原始帧约为 1.8 MiB，这并不是将其 base64 编码到控制回复中的好主意。它会从 tee 请求下一个帧而不是使用缓存的帧，因此读者无法获得相机停止时所显示的帧。
- **`mediad` 内部的检测器**：订阅 raw 分支，以几赫兹的频率运行模型，并在状态流上发布检测结果。这就是它最终的位置——感知靠近传感器，提取特征而不是传输像素——这也是行为会消费的内容。

一旦检测结果以状态形式存在，`docs/ideas/autonomous_behavior.md` 中目前依赖于蓝牙（“一只鸭子 *在附近*”）的行为就可以依赖于视觉（“一只鸭子 *在那里*”）：接近、跟随、面对，以及鸭子在歌唱时彼此注视的合唱。

### 拍摄快照

在机器人上，`robotctl frame --output frame.uyvy` 保存一个新鲜的打包好的 UYVY 帧，并在标准错误中打印其 JSON 元数据：宽度、高度、字节数、捕获时间戳和 `rotate` —— 从垂直方向旋转的角度，与 `media.video` 告诉 WebRTC 对端的数字相同。在转换时使用这些尺寸，并应用这个旋转，例如 `ffmpeg -f rawvideo -pixel_format uyvy422 -video_size 1280x720 -i frame.uyvy -frames:v 1 -vf transpose=1 frame.png` 用于从 90° 安装的 1280×720 捕获；不要假设在更改相机模式或安装后这两个数字。文件仅在完整响应到达后写入。

**像素是传感器提供的，`rotate` 被报告而不是应用**——由于 `videoflip` 使编码器失去了零拷贝路径并降低了板载帧率至 22 fps，因此管道停止了旋转帧。因此，每个消费者都自行旋转。省略上述 `-vf` 选项，图片会倒置且没有任何信息说明原因，这正是 `rotate` 存在的目的。当 `--flip-in-pipeline` 已经旋转了它们时，`rotate` 为 0。
从与机器人局域网连接的浏览器中打开 `http://<机器人>:8080/frame`，或者使用 `curl --fail http://<机器人>:8080/frame -o frame.png` 保存它。这返回一个 **直立** 的 PNG，带有 `Cache-Control: no-store`。这条路由是上述段落的例外情况，因为 PNG 没有地方携带角度：四分之一转的安装会交换其宽度和高度与捕获几何形状，代价是每次请求旋转一次而不是每次帧旋转一次。停止或不可用的摄像头返回 HTTP 503，从不返回最后好的图片。PNG 保留了 RGB 转换而没有 JPEG 压缩；它不是 raw UYVY 数据的字节对字节的替代。这条路由与现有的控制台和摄像头流具有相同的局域网访问边界；此路由上没有额外的身份验证。

本地端点支持 `hello`，然后在同一连接上支持 `media.frame`。其套接字可以通过 `mediad --frame-socket <路径>` 和 `robotctl --media-socket <路径> frame` 进行配置。未能抢占套接字会中止启动；现有文件或活动监听器保持不变。最多支持 16 个本地连接，每个连接最多五秒，最多四个 HTTP 截图任务。HTTP 捕获有三秒的截止时间，响应元数据被限制在 4 KiB。无效的几何形状和大于 16 MiB 的负载包被客户端拒绝。

`media.frame` 故意没有 `Call`/服务车道路由：其 JSON 头部后跟一个二进制尾部。WebRTC 控制数据通道和 `duckctl` 当前的 BLE 传输不携带快照。使用本地套接字或控制台的 HTTP 路由；远程视频传输是单独的。未来共享套接字组助手可以替换现有的重复的所有权代码，而不将此功能耦合到多守护进程重构中。
