# 超级速查表

`robotctl`，运行在机器人上。这里的每个命令都来自随分支一起发布的 `--help`，而不是来自记忆。

只读命令不需要特权。任何需要 **改变** 机器人的命令需要 `sudo`（或 `--allow-user`/`--allow-group` 用于 `configd`，`updater.toml` 中的 `allow_uids`/`allow_gids` 用于 `updaterd`）。

分支构建、发布候选版本以及更新后的重启陷阱都在 [`cheatsheet-dev.md`](cheatsheet-dev_zh.md) 中——这需要一个开发板。通过蓝牙从笔记本电脑连接同一台机器人，没有网络和 ssh，相关内容在 [`duckctl.md`](duckctl_zh.md) 中。## 在机器人上 — `robotctl`

### 首先要运行的命令

```
robotctl version
```
每个守护进程正在运行的版本与已安装的版本进行比较，并在它们不一致时发出警告。在相信任何其他诊断之前，请先运行此命令——在更新后守护进程仍在运行旧代码的情况看起来与您刚刚发布的修复程序中的 bug 完全一致。请参阅下方的“更新后”部分。
```
robotctl health
```
硬件和软件一目了然。当机器人状态不佳或无法访问时，返回非零值，以便控制脚本——如果报告的是过热的电机或被锁定的组件，而不是进行判断，不会影响退出代码。使用 `--json` 选项获取支持包。

### 监控循环
```
robotctl monitor
```
客户要求与实际应用之间的差异，当它们不同时给出原因——
安全夹钳经常被提及，否则“杆向前而机器人仍静止”是无法理解的。一个限制明确地表述出来而不是命名它：`deadman — 近期未收到意图信号，速度归零`。
Also on the frame: 每个关节与命令值的偏差、IMU 预测的重力以及从中得出的跌倒判决，还有实现的循环速率作为轨迹，以便已经恢复的卡顿仍然可见。预测的重力是此流中唯一的 IMU 数据量——直立状态大约为 `[0, 0, -1]`，这也是决定 `fallen` 的依据。过时读取计数器及其含义与 `robotctl health` 中的实时数据共存。
表头的最后一行是机器人的状态而不是行为：电池的电压和电量占比、最热的伺服电机以及电路板自身的温度。这些信息来自 `robot.health`，每两秒查询一次，因为这些信息不在状态流中——而任何问题都会在这里被命名，无论是 `unhealthy: 控制环路频率为 43.9 Hz`、`degraded: 在尝试三次后，电机总线上没有检测到机器人` 或 `方向冻结 — 25 个过时读数`。最后一个信息仅出现在这一行，而不会出现在帧的其他地方：一个停止融合的电路板会继续回应请求。
因此，没有任何错误发生，重力矢量上方保持一个合理的姿态无限期地持续着。
0% 为 `BATTERY_EMPTY_V`，此时 `robotd` 会让机器人坐下并切断电源，因此这个数值是一个倒计时而非电量计——在 30% 时显示黄色，在 15% 时显示红色。如果未进行读取，则显示 `batt not read yet` 而不是 `0.00 V`，这与启动后的第一秒以及无法回应的总线看起来相似。即使没有任何状态，这一行也会被绘制出来，而这恰恰是最关键的情况：当电路板的伺服电源关闭时，它永远不会完成控制周期，因此没有任何数据到达流中，原因仅在健康状态回答中体现。
底部边框命名加载的策略——即`.onnx`文件，以及是否配置了静态网络——因为`walk`是一种在两种不同步态下发布的模式。没有策略的机器人会这么说，而那些策略无法加载的机器人则会说另外一种情况，而这正是流的`held`无法区分的。
在右侧，**以站立姿态绘制的机器人**——与训练策略所针对的相同视觉模型，由测量的关节角度摆出姿势，并通过IMU的重力向量倾斜。一条腿折错了方向，头部朝向地面，一只鸭子侧躺在地上，所有这些都是关节表中的数字；在这里，它们都一目了然。它默认开启，并且当终端足够宽（大约110列——表格先显示，然后机器人占据剩余空间）时就会出现。**`d`** 可以关闭它；**`[`** 和 **`]`**，或者 `←`/`→`，可以围绕它旋转。
每当ToF在传输帧时，它所看到的内容会被绘制到同一场景中——命中时显示黄色，地板时显示绿色——并通过与机器人自身身体进行深度测试来判断，因此喙后面的点会被遮挡。这就是为什么“它是在看我的手，还是在看自己”这个问题可以回答的原因。它不需要任何关键帧：当帧到达时点出现，当帧停止时点消失。
在下方，当列足够高时，**机器人去过的地方的地图**：来自足部接触点和IMU的里程计轨迹，以盲文形式呈现。面板不会变大——随着轨迹的扩大，世界也在缩放，因此整个路径始终在画面内。`+` 表示起点，`●` 表示机器人，带有指向其朝向的短射线，屏幕向上表示其启动时的朝向。没有磁力计，因此这是相对运动，会漂移；它回答“它是否走了一个圈”而不是“它在哪里”。
`q` 退出；`↑`/`↓` 在窗口过短无法显示全部关节列表时滚动关节列表；`u` 切换角度单位为度和弧度之间；`t` 打开 [ToF 矩阵](#the-tof-sensor-tofd)；`c` 打开 [摄像头](#the-camera-mediad)；`d` 切换机器人视图并在 `[` / `]` 中旋转它；`p` 打开手柄的原始输入流 —— 每个来自游戏手柄的 evdev 报告及其之间的间隔，这是唯一可以看到停滞的无线通信的地方（[将游戏手柄配对](pair-a-gamepad_zh.md#when-it-drops-while-you-are-driving)）。一个带有惯性传感器的手柄
unit — Pro 控制器克隆体有一个，而 Xbox 没有 — 在这个块上增加了一个面板：一个线框平板，可以倾斜和旋转，与你手中的平板同步，显示其俯仰角、滚转角和偏航角，以及原始加速度和角速度，还有陀螺仪的静止偏置是否已被学习（保持它半秒钟）。黄色条是平板的前端。角度在屏幕上以度显示 — 关节、头部和偏航率。重定向或管道输出时，每 tick 打印一行，因此 `> run.log` 和 `| grep FALLEN` 的行为一致，无论屏幕设置如何，这些数字始终以弧度表示。关节向量在
`--json`，用于携带整个状态，每行一个对象：
```
robotctl monitor --json --hz 50 > run.jsonl
```
### 配置机器人
```
sudo robotctl configure
```
在这款机器人上所做的更改，且仅此更改：
```
robotctl configure --list
```
一个无人触碰的机器人什么也不打印——这就是答案。添加 `--json` 可以获取支持包。它不需要 root 权限和终端，这正是它的目的：它是关于一个行为异常的机器人首先要问的问题，而到目前为止，回答这个问题意味着需要通过 ssh 使用全屏编辑器。
一个对 `/etc/robot/robotd.toml` 的交互式编辑器：每个守护进程都知道的键，首先是功能开关（策略开/关，行走/轮式，跛行跌倒，音频，宠物检测，电池断电，摄像头和视频质量…），当前值与默认值对比，每行有一条文档注释。SPACE 键切换，ENTER 键输入一个值，`u` 键将键恢复为其默认值，`ctrl+f` 打开屏幕上的模糊搜索（输入时选择会跟随；ENTER 或 ESC 保持选择）。黄色背景（标记为 `•`）的值表示此机器人与默认值不同；其他一切都是内置默认值，`unset`
optionals 显示它们解析为的内容 `(auto)`。

值得信赖的三个属性：
optionals 显示它们解析为的内容 `(auto)`。

值得信赖的三个属性：
- **它不能与守护进程产生分歧。** 架构、默认值和验证均来自 `robotd` 解析文件的同一个 crate，键列表由一个测试完全锁定——如果守护进程中的 `[section]` 新增到这里，构建将失败。
- **它不会吃掉你的文件。** 其他版本的注释、顺序和键将保持不变；只有你更改的键会被写入。撤销一个键会移除它（以及与其关联的注释），而不是锁定默认值，因此文件保持为一系列 *决策*，而不是默认值的副本。
- **它无法写入机器人拒绝启动的文件。** 每次保存都会先通过守护进程自身的加载器进行验证（原子操作，临时文件 + 重命名），并因原因被拒绝。
保存会根据实际需要变更的内容，从实际读取变更的守护进程进行操作：大多数键（`[media]` 和 `[duck_detector]` 是 `mediad` 的，`[head_imu]` 是 `tofd` 的）需要重启；`[policy]` 需要 `robotd` 重新加载（电机保持供电）；而 `[pad]` 和 `[pad_imu_head_control]` 则无需任何操作，`padd` 会在一秒钟内读取这些变更。由于文件由 root 拥有，因此需要 `sudo`，否则编辑器会以只读模式打开并在第一次写入时提示。`--file` 选项用于指向其他位置进行测试复制。随附的 `deploy/robotd.toml` 保持不变。
参考说明每个旋钮存在的原因；这用于调整它们。

#### 视频质量
```
sudo robotctl configure
```
设置 `media.quality` — `1080p30`, `720p30`, `720p15` 或 `360p30` — 然后重启以获取更新。将 `media.source` 设置为 `test` 会播放测试图案，这正是没有摄像头的板子所需要的：WebRTC 的 *控制* 通道依赖于视频轨道，因此一个无法启动的管道会同时浪费成本。测试图案会忽略 `media.quality`，并以 256x144@5 的分辨率运行 —— 它的存在只是为了使会话得以存在，而绘制一个 720p 的图案会消耗五倍于实际摄像头的 CPU 资源。如果不自定义设置，则 `media.bitrate` 会跟随 `media.quality`，单位为比特每秒。
`media.congestion_control` 是该部分的另一个调节项，它会移动 CPU：
`disabled` 会禁用带宽估算器，这是 `mediad` 中最大的单一消费者（占核心资源的 7.6%，而捕获仅为 0.3%），从而使 `media.bitrate` 成为速率而非起始点。这会牺牲适应性——在网络质量下降时，画面会停滞而不是速率降低。
720p30 是管道测量的基准；这是一个达不到标准的台阶，达不到标准时会运行得更慢而不是失败。`robotctl monitor` 在底部以黄色显示达到的速率，并在低于所要求的90%时旁边显示 `of <target>`。实际应用情况如下：
```
journalctl -u mediad -b | grep streaming
```
### 策略与技能

一个 **插槽** 是机器人默认运行的内容——行走步态、站立网络。一个 **技能** 是在被请求时运行的内容：踢腿、翻滚、鞠躬。两者都是 Hub 上的文件，无需 daemon 释放即可更改，且无需重启任何部分。

当前机器人正在运行的内容：
```
robotctl policy list
```
两个表格：七个插槽，然后是技能——默认运行的内容，以及请求时运行的内容。
```text
   SKILL        RUNS FOR  POLICY
   kick_left       0.5 s  ball_kick_left.onnx
   roulade           1 s  roulade.onnx
 * polite-bow        4 s  fffiloni/microduck-polite-bow-b1d864/main/policy.onnx
   ground_pick         —  driven by the robot itself
   sit_toggle          —  driven by the robot itself
```
一个 `*` 标记了每行配置有意见的每一项，底部有计数。你关闭的槽位会显示 `switched off` 而不是像机器人从未拥有过一样。目录从路径中移除，因为 `ORIGIN` 列已经指明了它是哪个。

`ground_pick` 和 `sit_toggle` 没有长度，因为机器人自己驱动它们 —— 它们响应 `robot do`，和其他项一样，但你无法更改它们。

#### 更新的官方版本

机器人行走的配置集存放在 Hub 上，并且版本单独列出：
```
robotctl policy check
```

```
sudo robotctl policy update
```
`check` 打印已安装的内容、最新版本以及仓库提供的其他内容；它不会做任何改变，并会在无法连接到 Hub 时明确地说明这一点。`update` 会安装最新版本，除非你指定了一个特定版本——例如，`--version v1` 就是用来回退到特定版本的。机器人会回到初始姿态，重新读取每个插槽并再次运行，而 **你自行加载的插槽将保持不变**，因为它们指向完全不同的地方。

#### 更新的鸭子检测器

模型 `mediad` 以相同的方式在 Hub 上查找其他鸭子的生命状态 (`pollen-robotics/microduck-duck-detector`)，并在单独一行中列出其版本：
```
robotctl duck-detector check
```

```
sudo robotctl duck-detector update
```
与策略对相同——`--version <tag>`命名一个，而`check`则不作任何更改。`update`会重启`mediad`，这会使控制台的视频暂停片刻；检测器是否运行则取决于`[duck_detector] enabled`在`robotctl configure`中的设置。

#### 尝试自己的文件

没有发布版本，没有需要编辑的文件，也不会重启：
```
sudo robotctl policy load walk /home/radxa/my_walking.onnx
```
如果机器人正在行走，它会回到初始姿态，加载该姿态并再次行走。如果它正在做其他事情——坐着或静止不动——则不会有任何动作：因为正在替换的网络不是正在运行的网络，且切换发生在底层。`sudo robotctl policy reset walk` 可以将那个插槽恢复；如果没有插槽，则会将所有七个姿态都恢复。

#### 尝试别人的策略

其他人也为这个机器人发布了策略：
```
robotctl policy search microduck
```

```
sudo robotctl policy load walk RemiFabre/microduck-flamingo-cycle
```
仓库名称就足够了——它会在一步中被获取和加载。添加 `@v2` 以指定修订版本，`:policy.onnx` 用于携带多个文件的仓库。`policy list` 标记它为 `community`。

**任何人都不会验证陌生人发布的任何内容。** 使其安全可试的是联合钳位、坠落反射和形状门——而不是描述。第一次让机器人站在那里。
一个声明不会在此运行的策略——观测宽度错误、新版本的守护进程、不同的机器人——会在下载前被拒绝。没有声明的策略会被接受，并按常规在加载时进行检查。

#### 添加技能

行走插槽中的策略会替换步态。作为技能添加的策略会与其并存，并在被请求时运行，这正是大多数发布的单次执行所希望的：
```
sudo robotctl policy add polite-bow fffiloni/microduck-polite-bow-b1d864
```

```
robotctl robot do polite-bow
```
长度来自仓库的清单。一项政策在未被明确更改之前将持续有效——就像一只单脚站立——本身没有长度，所以给它一个长度，然后它就会读取：

```toml
length = 12
```

这样，它就有了一个长度。
```
sudo robotctl policy add flamingo RemiFabre/microduck-flamingo-cycle --hold 5 --command 1,1,0
```
`--command` 是网络在运行时所喂入的内容。大多数技能不需要它：它们是在全零命令下进行训练的，被选中本身即是触发条件。如果策略将其扭曲为其他内容——例如，火烈鸟的策略是 `[flag, side, 0]` ——则需要明确指定，其 README 中会说明各个插槽的含义。

执行 `sudo robotctl policy remove <name>` 可以移除策略。当你执行此操作时，机器人发布的技能会返回，因为仅移除了覆盖设置。

在技能运行之前，机器人必须处于驾驶状态——首先在控制板上按下 **Start** ，否则请求会被拒绝。
#### 将技能放在按钮上
```
robotctl pad bindings
```
```text
a           ground_pick
x           roulade
lb          kick_left
rb          kick_right
dpad_down   sit_toggle

`robotctl pad bind <button> <skill>` changes one; padd picks it up within a second.
```

```
sudo robotctl pad bind x polite-bow
```
```text
a           ground_pick
x           polite-bow
lb          kick_left
rb          kick_right
dpad_down   sit_toggle
```
这只会写一行，并且只写你命名的按钮：
```toml
[pad]
x = "polite-bow"
```
放回去：
```
sudo robotctl pad reset
```
**Nothing restarts** — `padd` 会在一秒钟内做出响应。

一个绑定到机器人不具有的技能的按键会在列表中标记出来，而不是在你按下它时默默无动于衷。

五个按键可以进行绑定：`a`、`x`、`lb`、`rb`、`dpad_down`。**`lb`/`rb` 是扳机键**，而不是模拟触发器，模拟触发器是嘴巴和呱呱声。一个空的名称会关闭一个按键，而 `pad reset <button>` 可以将其恢复。默认设置是原型所具有的映射，因此一个没有 `[pad]` 部分的机器人会像以往一样行为。
剩下的区域不可绑定：Start 切换策略，Y 和 B 改变摇杆的意义，而按住 Select 会启动机器人——那个停止机器人的按钮是不允许因配置编辑而丢失的。名称会与机器人实际拥有的进行比对，因此任何拼写错误都会被列表拒绝，而不是变成一个无效的按钮。

#### 重新整合一切
```
sudo robotctl policy reset
```
```
sudo robotctl pad reset
```
```
robotctl configure --list
```
最后一个只会打印出这个机器人与默认设置不同的地方，除此之外什么也不打印。如果一个机器人没有被修改过，它只会打印一行说明。这是在机器人行为异常且不确定哪些设置被保留时首先运行的内容。

#### 机器人槽位及四点注意事项

槽位包括 `walk`、`stand`、`sitstand`、`ground_pick`、`kick_left`、`kick_right` 和 `roulade`。`load` 会将选择写入 `/etc/robot/robotd.toml`，因此在重启和更新后仍然保留。更新会替换二进制文件和随附的策略，而不是指向其他地方的那行配置。
- **重置已经重置过的东西不会做任何事情，并且会明确说明这一点。** 不需要进行归位、重新加载，也不需要 `sudo` 权限，除非有需要写入的内容。
- **如果策略不是 `obs[1,61] -> actions[1,14]`，则在任何更改之前都会被拒绝。** 文件会在机器人仍在运行旧策略时被打开并检查。
- **即使加载失败，也会保留正在运行的策略。** 尝试一种步态不会让你失去现有的步态。
- **下次启动时丢失的文件会占用其插槽，而不是占用机器人的资源。** 插槽会减少。
  根据这个机器人的政策，`robotctl health` 报告 *降级* 并命名文件，而 `policy reset <插槽>` 可以清除它。一个无法加载的官方政策仍然是 **不健康** 的——这是个有缺陷的版本，更新程序会将其回滚。

`none` 可以关闭一个插槽——除了 `walk` 插槽，其他插槽都会退回到 `walk` 插槽，而 `walk` 插槽不能为空。有些政策需要这样做：一个自己完成站立动作的政策希望将站立网络放在一边，或者在命令为零时将机器人交给那个政策。

#### 为每台机器人发布政策
一个官方设置中的策略会覆盖每一个机器人，添加一个策略只需四个步骤且无需释放守护进程：

1. 将 `.onnx` 文件上传到 `pollen-robotics/microduck-policies`。
2. 在其 `manifest.json` 中添加一条记录：
   ```json
   { "file": "polite-bow.onnx", "kind": "episodic", "duration_s": 4.0 }
   ```
   该集合的 `manifest` 是 `schema_version: 2`；一个普通的单次执行策略只需要这三条记录。
3. 打标签 — `hf repos tag create pollen-robotics/microduck-policies v4`。
4. 在一个机器人上执行：`sudo robotctl policy update`。
这个条目是一个一次性任务所需的一切：**`episodic` 且带有 `duration_s`，在它训练时使用的全零命令，变成了机器人通过名称回应的一项技能**——只需等待 `robot do` 和一个按钮，无需进行其他编辑。一个**`perpetual`** 一次性任务则是一个步态，需要指向一个槽位。
一个守护进程必须“驱动”的策略——随着时间的推移编写一个阶段，或者切换一个姿态标志——声明在 `command.encoding` 下，其数值表示该手臂的时机，而不是一种新技能。蹲下和坐下↔站立是两种姿态，其中任何一个条目错误都是这里唯一值得小心的错误。

完整的声明文件，每个字段及其对机器人所做的更改如下：
[`../policy-manifest.md`](../policy-manifest_zh.md)。
政策需要具有的形状以及加载时还会检查什么内容可以在 [`../design/robotd-design.md`](../design/robotd-design_zh.md) §2.3 中找到；政策的来源、`official` 的含义以及技能如何声明自己都在 [`../design/policy-channel-design.md`](../design/policy-channel-design_zh.md) 中。

### 关节的权力 (`robotd`)
```
sudo robotctl robot init
```

```
sudo robotctl robot relax --yes
sudo robotctl robot reboot-motors           # every servo; or `reboot-motors 3 11` for just those. Torque off, then init / Start
```
`init` 为关节和滑板提供动力，并在大约两秒内将其移动到起始姿态——**它会移动每一个关节**，因此请将机器人放置在支架上。它不需要任何策略，这也是游戏手柄的 Start 按钮在开始驾驶之前所做的，因此手动操作时它是一个测试项。

`relax` 切断电源，**机器人会自动瘫倒**，除非有其他力量支撑它，这就是为什么它需要 `--yes` 参数的原因。这是在不拔插头的情况下返回瘫痪状态的唯一方法：再次按下 Start 按钮会停止策略并保持机器人站立，而 `robot.stop` 则会将速度归零，机器人仍然站立。
两者都通过 `robotd`，后者拥有电机总线。`robotd init` 这个子命令仍然存在，用于在机器人守护程序未运行的情况下初始化机器人，因为它需要停止守护程序，因为两个写操作在同一串口上会互相干扰其回复：
```
sudo systemctl stop robotd && sudo /opt/robot/daemon/current/bin/robotd init && sudo systemctl start robotd
```
**更换电机**无需配置工具。直接从包装盒中安装新的伺服电机（ID 1，57600 波特率），为伺服电机供电，`robotd` — 或 `robotd init` — 会找到不再响应的那个关节，将新的伺服电机设置为该关节，更新其寄存器并重新启动。日志显示 `总线上安装了出厂伺服电机；将其设置为缺失的关节`，然后显示 `已采用替换伺服电机`。一次一个：当缺少两个关节时，它无法确定新伺服电机对应哪个关节，会等待并显示相关信息。
`init` 无论机器人是否摔倒都能工作——默认情况下，摔倒只是一个 *报告*（在 `robotctl monitor` 中可见），而不是一个门限，这与原型相符。如果电路板在 `robotd.toml` 中设置了 `[safety] fall_limp` 或 `fall_recover`，则会启用门限：在这种情况下，摔倒的机器人会变得无力，并拒绝执行 `init`/`enable`/技能，直到它被扶起。

### 游戏手柄 (`configd`)

每个按钮的具体功能——以及如何更改这些功能——请参阅上方的 **策略和技能** (`robotctl pad bindings`)。本节是关于如何连接游戏手柄。
```
robotctl pad status
```

```
sudo robotctl pad pair
```

```
sudo robotctl pad pair 78:86:2E:BB:13:28
```

```
sudo robotctl pad forget 78:86:2E:BB:13:28
```
配对仅需一次，并且有一整页说明——
[`pair-a-gamepad.md`](pair-a-gamepad_zh.md): 哪个按钮可以将手柄置于配对模式，如何在不忘记第一个手柄的情况下添加第二个手柄，以及当手柄无法连接时应采取的措施（通常情况下，`/etc/bluetooth/main.conf` 中的 `Privacy` 设置是解决问题的答案）。

`padd.service` 从启动时就开始运行，并驱动连接的手柄，因此配对是唯一的步骤。映射方式是原型机的，所以肌肉记忆可以延续：
| 控制 | 功能 |
| --- | --- |
| 左摇杆 | 驱动：前进/后退和侧移 · 头部：头部的左右转动和上下倾斜 · 身体姿态：上下移动和蹲下 |
| 右摇杆 | 驱动：转向 · 头部：颈部上下倾斜和头部滚转 · 身体姿态：上下倾斜和左右倾斜 |
| **Start** | 首次按下：施加扭矩并以2秒斜坡过渡到起始姿态，然后保持。第二次按下：策略驱动。之后切换策略 |
| **Y** / 三角形 | 头部模式：摇杆控制头部姿态（身体保持静止）。启用 `[pad_imu_head_control]` 并使用带有IMU的控制器：控制器的倾斜姿态控制头部，摇杆继续驱动 — 详情见下文 |
| **B** / circle | 体态模式：棍子倾斜并蹲下站立机器人 |
| **A** / cross | 地面拾取 |
| **X** / square | 前滚翻 — 一次前滚翻；按住可连续滚翻 |
| **LB / RB** | 左 / 右踢 |
| **DPad-Down** | 坐 ↔ 站立 |
| **RT / LT** | 嘴（任一扳机）—— RT 还会发出呱呱声；LT 保持时发出“哇”的声音 |
| **DPad-Up**，按住 3 秒 | 切换驱动模式，步行 ↔ 滚行 |
| **DPad-Right** | 重启每个伺服：从过载中恢复的方法，无需拔掉电池。先断开扭矩，然后启动 |
| **Select**，短按 | 扭矩关闭 (`robot.relax`) 在释放时生效：紧急停止。机器人会下落，所以请握住它。然后 Start 会再次将其立起 |
| **Select**，按 2 秒 | 坐下，扭矩关闭，电源关闭 —— 释放后不再执行其他操作 |

**使用手柄本身驱动头部。** Pro 控制器内置 IMU，和
```bash
sudo robotctl configure      # Controller-IMU head control → enabled
```
Y 在这种手柄上含义不同：第一次按下会将头部交给手柄——倾斜手柄，头部也会倾斜；转动手柄，头部也会随之转动——而摇杆则继续控制身体。再次按下 Y，头部会保持当前位置，摇杆仍然控制身体。第三次按下 Y 后，手柄会再次从当前位置控制头部 **：手柄的偏航仅由陀螺仪决定并漂移，每次重新进入时重新校准即可抵消漂移**。同一部分中的 `gain` 为头部弧度每手柄弧度，缺省值为 1。在 Xbox 手柄上或关闭开关时，Y 会控制摇杆头部。
模式为“above”。`padd` 可在一秒内拾取变化；无需重启。

没有停止按钮：松开手柄，机器人站立，`robotd` 的死机检测会停止它。在滚轮机器人（`robotd.toml` 中 `mode = "roller"`）中，手柄会自动调整滚轮的形状 —— 不对称推/刹车，无侧移 —— 而 A 键触发蹲下。其他技能也会随之发挥：坐、踢和翻滚在轮式机器人上也能正常运作，正如原型机所示。
**在两个模式之间切换 DPad-Up 按钮**，当您刚刚为鸭子安装了轮子或取下了轮子时：机器人会发出一次呱声表示步行模式，或发出两次呱声表示滚轮模式，然后返回到其初始姿态，加载该模式的策略并再次行驶——几秒钟内全程保持扭矩，无需重启。`robotd.toml` 不会受到影响，因此重启后会恢复配置模式；使用 `robotctl configure`（或 `[policy] mode`）使其保持不变。这是由于在驾驶过程中容易依靠 DPad-Up 按钮。
`pad status` 分别回答两个问题，因为连接的垫片和死掉的驱动器从外部看起来是相同的：
```
pad     Xbox Wireless Controller 78:86:2E:BB:13:28  connected
padd    active — driving whatever pad connects
```
要使用非默认限制，请先停止服务，否则两个进程可能会为此争斗：
```
sudo systemctl stop padd
```

```
sudo -u padd /opt/robot/daemon/current/bin/padd --max-linear 0.25
```
当链接本身是可疑对象时，可以实时查看它——使用 `robotctl monitor`，然后按 `p`。这种方法同样适用于没有机器人的情况：在伺服电机未供电或 `robotd` 停止的电路板上，监视器会打开在垫块块上而不是拒绝。如果需要通过窗口进行裁决，可以将测量值从这个仓库的一个克隆版本中复制过来：
```
scp scripts/pad-link-test.sh radxa@<board>:/tmp/
```
已在 `padd` 的日志中掉落——无需垫片，且会立即回应：
```
sudo sh /tmp/pad-link-test.sh --history
```
或者现在就测量它，整个两分钟都要保持木棍移动：
```
sudo sh /tmp/pad-link-test.sh
```
它会针对每个情况记录内核自身的丢包原因，并测量按键输入报告之间的间隔——这是“padd”无法察觉的失败，即使链接保持正常，机器人也会在过时的命令下行走。[pair-a-gamepad.md](pair-a-gamepad_zh.md#当您驾驶时它会掉落)会读取这些数字。

当两块板子在使用相同的按键时表现出不同行为，差异在于它们下方的堆栈：
当两块板子在使用相同的按键时表现出不同行为，差异在于它们下方的堆栈：
```
scp scripts/pad-stack-report.sh radxa@<board>:/tmp/
```

```
sudo sh /tmp/pad-stack-report.sh
```
内核、BlueZ、控制器固件、LE 或 BR/EDR 以及手柄自身的固件版本——打印并保存到 `/tmp/pad-stack-<host>-<when>.log`。`--fingerprint` 仅打印必须在两块板之间匹配的值，用于 `diff`。[pair-a-gamepad.md](pair-a-gamepad_zh.md#is-this-board-running-the-same-stack-as-that-one) 中有比较内容。

### 语音
```
robotctl quack
```
区分鸭子最响亮的方式：每台机器人的声音库都是从其 SoC 串行号生成的（通过 `sounds ensure-bank` 生成，每次发布安装都会运行），因此回答问题的机器人——以它独有的声音——就是你 SSH 进入的那一台。没有声音的机器人——静音，或者没有声音库——会说“没有声音”而不是打印 🦆，所以沉默总是意味着错误的鸭子。
机器人还会在 `robotd` 启动时问候，在关机前啄嘴告别，如果你要求它这样做，它还会在麦克风听到它的头部被挠时发出咕咕声。那个功能默认是关闭的。
两种模式（`audio.pet_detect = true` 可以启用该功能；分类器包含在发行版中）：始终开启的版本会对每次偶然的接触发出叫声，最终让人感到厌烦。启动问候有自己的开关，适用于整天重启守护进程的任何人：
```
sudo robotctl configure
```
设置 `audio.greet = false`，并在保存时接受其提供的重启。这会消除一声呱呱声，同时保留触发器和麦克风，而 `audio.enabled = false` 则不会这样做。音频硬件初始化——编解码器驱动、叠加层、混音器——是 `setup-board.sh` 脚本中的音频部分，每个板卡一次。

要试听一个声音或手动重新生成声库，发行版中包含生成器：

```bash
./generate-audio-bank.sh
```
/opt/robot/daemon/current/bin/sounds show
sudo /opt/robot/daemon/current/bin/sounds ensure-bank --force
```
`sounds theremin` 测试实时合成器——这是 theremin 演奏的声音，由 ToF 自身的帧率驱动的手扫脚本控制。`--out sweep.wav` 会将其写入文件而不是播放，这样你就可以在没有机器人的情况下听到声音的变化。

### 鸭子齐声合唱
```
robotctl chorale
```
两只鸭子在房间里一起唱四重唱；更多的鸭子加入已经进行的合唱。直到按下 Ctrl-C。`--off` 可以停止。

默认关闭——在 `robotd.toml` 中使用 `[chorale] accept`，并且必须在所有应参与的鸭子上设置。合唱会移动嘴巴和头部，因此另一只鸭子进来后开始动画的鸭子会进行无人要求的动作。关闭还意味着 *不可见*：未选择参与的鸭子不会将任何内容发送到空中，而不是礼貌地拒绝。

按问题出现的顺序工作方式如下：
- **没有人负责。** 两只鸭子看到相同的灯塔，较低的鸭子会进行导引，因此不存在需要失去的选举，也没有必须到达的消息。
- **没有共享时钟。** 印刷电路板没有 NTP 和 RTC 协议，因此导引者的节拍计数器就是时间基准：它会在每次节拍时在 BLE 广告中增加一个字节，新的值的到来就是强拍。跟随者会平均大约 25 个节拍的相位，这使得无线电的抖动保持在合奏所需范围内的 ±20 毫秒以内。
- **零件是分配出来的，不是指派的。** 最低音的鸭子唱低音。指挥员广播了名单，每个人都在名单上重新排列座位——这正是当两只鸭子可以看到房间的不同部分时，它们不会唱同一旋律的原因。
- **加入不会改变任何人的角色。** 一只鸭子到来时，它会占据空出来的角色。一只鸭子离开时，它会保留它的*座位*——它的旋律将无人演唱，就像合唱团中有人中途离场一样——因为中场调整座位是唯一值得避免的事情。
读出名称会在部件固定后立即显示，因此鸭子最终唱的是什么会保留在滚动缓冲中：
```
listening for other ducks — Ctrl-C to stop
  singing tenor    with 3 voices
  tenor    bar   12  beat  45.2  3 voices
```
指挥家根据每场演出选择乐曲，一场演出结束后——在最后一个音符之后，大家回到聆听状态，稍作调整，然后在下一个呼吸间唱起另一首歌。
`robotctl chorale --piece 2` 将确定机器人选择的乐曲（跟随者会唱出信标命名的歌曲，因此要将它设置在每只鸭子上以确保歌曲一致）；未知的 ID 会被机器人目录拒绝。ID：1 悲伤的，2 鸭子的 strut，3 外星球（测试资源，不用于发布）。`robotd` 环境中的 `DUCK_CHORALE_PIECE=<id>` 是固定的设置。
fallback — 请注意，它必须在 **robotd** 上运行，而不是在 `robotctl` 命令行中。

要听到没有鸭子的编排，一台机器可以渲染整个合奏：
```
sounds chorale --voices 4                 # or --seeds 100,7,42 for particular ducks
sounds chorale --score my-piece.mid       # anything a notation editor exported
sounds chorale --rolloff 0                # for a full-range speaker, not a duck's
```
分数来源于 `sounds/scores/*.duckscore` — 一种行式文本格式，详见 `wistful.duckscore`，这也是随附的文件 — 或者是 MIDI 文件，这是值得使用的路径：**MuseScore 是乐谱编辑器。** 每个声部一个乐器而不是一架钢琴的五线谱，命名各个部分，然后导出 MIDI。声部是通过平均音高匹配的，因此一个从上五线谱开始写的乐谱仍然会将低音放在低音部分；一个名为“女高音”的轨道会因其音高而被忽略。

### 播放鸭子（ToF 磁控管）

---

保留了原文的格式和内容，未做任何删减或修改。
```
robotctl theremin
```
头部的深度传感器变成了一个乐器：喙前的手的位置表示音高——手越近音调越高——嘴张开的幅度对应音符，高音区张得更开。演奏直到按下 Ctrl-C，然后在离开时放下乐器。`--off` 会放下一个客户端留下的乐器。
**默认禁用** — `[theremin] enabled` 在 `robotd.toml` 中，如鸭子所述，就像上面的和声一样。
使用 `robotctl configure` 可以设置此选项，并会提供 `robotd` 重启以应用更改；
在此之前，`robotctl theremin` 会拒绝并指出该键。除此之外没有其他方式关闭它：`tofd` 无论何时都会运行，因此即使从未演奏过任何音符的鸭子也能继续使用下方的深度网格。
一个没有任何花哨功能的显式模式：当它处于运行状态时，可玩范围内最近的返回值是“手”。将鸭子指向空旷的空间，它会保持静默；将鸭子指向距离40厘米的墙面，它会发出稳定的音符。无论鸭子是坐着、站着还是行走，都会发出声音——嘴巴并不参与任何策略。

读数的最后一列是**传感器对该帧的描述**，这也是每一个“它为什么停止播放”的答案：
```
  0.34 m    438.1 Hz   60% ██████    14 usable · 255:38 4*:9 5*:5 1:12
```
有多少个区域携带了机器人认为的状态，然后按 ST 状态码进行计数，并在认为正确的状态码前加上 `*`。`~` 之前的注释表示这是一个 *保留* 注释，用于弥补传感器断开连接的情况，而不是当前测量的结果。
那列存在是因为它会在一分钟内发现一个bug：ST文档5和9被标记为“范围有效”，而一个只相信这些文档的构建在大约30厘米处——超过这个距离，移动的手会重新被识别为4或13（*一致性失败*，sigma值过高），携带一个完全适合于音高的距离。如果伸展范围较短，在`robotd.toml`中的`[theremin] statuses`中添加代码；如果在空中演奏出幻影音符，就移除一些代码。`hold_ms`是防断奏的功能：它会越过一个闪烁的区域。
注意 `robotctl monitor` 的ToF网格比 theremin 更严格——它将任何超出 5/9 的值标记为 `x`，*无法测量*。全网格为 `x` 并不意味着传感器损坏；而是表示它对现有的数值持谨慎态度。

### ToF 传感器 (`tofd`)

头部传感器的 8×8 深度矩阵。`robotctl monitor`，然后 **`t`**：
```
┌ tof VL53L8CX · 15 Hz · 8×8 · 48/64 ranged · 0.12–3.54 m ─────────────┐
│ 0.12 0.15    x 1.44 1.86    · 2.70 3.12                              │
└ · nothing in range · x could not measure · near→far ── seq 412 · 6 ms ┘
```
距离以米为单位，从近暖色渐变到远冷色。两个标记很重要：`·` 表示 *测量未发现目标，无范围内的物体* — 这意味着存在自由空间，这是有价值的信息；而 `x` 表示 *无法测量*，这完全不能说明外界的情况。如果网格显示两者均为空白，则会掩盖这种差异。

这是传感器自身的坐标系，而不是机器人的坐标系：直到存在运动学关系，才会有重新投影，这也是检查安装角度的正确位置。
`tofd` 拥有传感器，其他设备不会读取总线。它只是一个普通的服务——
运行 `sudo systemctl stop tofd` 是安全的，没有其他服务依赖于它，`monitor` 会显示 "no depth stream" 并继续运行。它区分了三件事，因为每种情况需要不同的修复：

| 信息显示 | 含义 |
| --- | --- |
| `connecting to tofd…` / `no depth stream` | 服务未运行 |
| `no sensor: …` | `tofd` 已启动；总线上没有接收到响应（大多数鸭子） |
| `waiting for the first frame…` | 传感器正在扫描；其第一帧扫描将在约 66 毫秒后开始 |
手动查看总线上有什么，或者在没有终端 UI 的情况下观看帧：
```
sudo i2cdetect -y -r 3
journalctl -u tofd -b
```
传感器共用了编解码器的 I²C 总线，因此 `setup-board.sh` 的音频部分已经配置了该总线本身；ToF 步骤仅添加了稳定的 `/dev/i2c-pihat` 名称。两个传感器系列都得到了支持——板上可以互换使用 VL53L5CX 和 VL53L8CX 传感器，而守护进程会根据读取的 ID 来选择驱动程序。

#### 头部 IMU (`head_imu.stream`)
`tofd` 还为头模块的 BMI088 —陀螺仪、加速度计和 Madgwick 方向 — 服务，并且它 **默认是关闭的**：在 `robotd.toml` 中通过 `[head_imu] enabled` 进行设置，使用 `robotctl configure` 进行配置，这会提供 `tofd` 的重启功能。读取它在 100 Hz 下会占用约 4% 的核心资源，目前还没有任何订阅者，因此一只未进行映射的鸭子在启动时就支付了这笔费用。当它关闭时有一个订阅者会收到一个命名键的原因，而不是未匹配传感器给出的沉默。`tofd --imu` 会在一个会话中读取它而不修改文件，而 `--imu-hz` 会线性地在速率和成本之间进行权衡。
这些都不涉及深度：ToF 距离可以在任何范围内工作，因此上方的网格适用于从未开启过 IMU 的鸭子。

### 摄像头 (`mediad`)

终端中从头部摄像头获取的一帧。`robotctl monitor`，然后 **`c`**：
```
camera 1280×720 · mount 90° · answered in 41 ms                    0.5 s ago
```
图片是以每字符单元格两个像素绘制的，无论安装角度如何都是正确的方向。
它很小——在这台机器人旋转四分之一圈后，图片变为纵向，大约16个像素宽——
而这已经足够表达数字无法说明的内容：头部实际上指向的方向，房间是否足够明亮以检测到任何东西，镜头是否被涂抹或有手指遮挡。
**当块被关闭时，什么都不会被获取。** 一个帧是 `mediad` 从捕获分支复制的 1.84 MiB 数据，只有在有人请求时才会复制，因此，运行监控并关闭块不会给相机带来任何成本。当块打开时，它每秒询问两次，`answered in 41 ms` 是相机的健康状态：请求会等待下一次捕获，因此，健康的 30 fps 相机大约在一个帧周期内回答，而停止的相机则会超时并失败。关闭块会忘记图片，因此重新打开会显示新的帧而不是十分钟前的房间景象。
| the block says | 代表的意思 |
| --- | --- |
| `asking mediad for a frame…` | 第一个请求仍在进行中 |
| `no picture: connection refused` | `mediad` 未运行 |
| `no picture: no frame arrived within the capture timeout` | `mediad` 正常运行；摄像头未生成 |

对于全尺寸图片而不是缩略图：
```
robotctl frame --output /tmp/frame.uyvy
```
一个原始的UYVY帧，其中的几何信息和安装角度会打印到stderr。命令行工具`mediad`在`:8080`端口上运行，并在`GET /frame`路径提供已旋转正确的PNG格式的同一帧。

### Wi-Fi (`configd`)
```
robotctl net status
```

```
robotctl net scan
```

```
sudo robotctl net connect <ssid> --psk <passphrase>
```

```
sudo robotctl net connect <ssid> --psk-stdin
```

```
sudo robotctl net forget <ssid>
```
`--psk-stdin` 将密钥短语保持在 `ps` 之外，而 `ps` 会显示一个包含 `--psk` 参数的命令给箱子里的每个用户，直到该命令结束。在任何共享的环境中都应优先使用它。

加入网络会 **断开机器人与当前网络的连接**，因此通过 Wi-Fi 的 SSH 会话将会中断。这是正常操作。扫描需要几秒钟 — 它会等待无线电完成扫描而不是返回之前的扫描结果。

### Hugging Face 账户 (`updaterd`)

将机器人登录到 Hugging Face 账户将允许你从其自身的网络之外访问它。目前其他操作不需要它。
```
sudo robotctl account login
```
这将打印一个代码。在任何设备上打开 <https://hf.co/oauth/device>，输入代码，然后命令完成：
```
Open https://hf.co/oauth/device and enter this code:

    A6MY-0314

Waiting for approval…
Signed in as PierreRouanet.
```

```
robotctl account status
```

```
sudo robotctl account logout
```
Ctrl-C 在等待时不会产生任何成本——机器人会继续轮询，`account status` 会显示是否已被批准。代码的有效期为五分钟；之后，需要再次运行 `login`。

已登录的机器人会拒绝，并指出账户名称：
```
sudo robotctl account login --force
```
同一个标志会放弃仍在等待审批的代码——例如，有人开始登录然后走了。旧代码将停止工作；之后对其进行审批将没有任何效果。

令牌有效期为三十天，机器人会自行更新它。如果机器人关闭时间超过这个期限，它会需要再次进行`login`，而`account status`会明确指出这一点。

### 身份与权限 (`configd`)
```
robotctl system info
```

```
robotctl system pin
```

```
sudo robotctl system set-name <name>
```

```
sudo robotctl system set-pin <six-digits>
```

```
sudo robotctl system reboot
```
开箱即用时，机器人会称呼自己为 `duck-` 加上其自身序列号的四个字符，因此即使两块板子从同一个镜像烧录，它们在手机的蓝牙列表中也会看起来不同。重命名会在几秒钟内通过蓝牙生效——无需重启——但手机需要重新扫描才能看到更改。

蓝牙配对时，手机会使用配对码进行认证。默认的配对码是 `000000`，任何阅读了此仓库内容的人都可以进行认证。

### 更新 (`updaterd`)
```
robotctl update status
```

```
robotctl update check daemon
```

```
sudo robotctl update apply daemon
```

```
sudo robotctl update rollback daemon
```

```
robotctl update log
```

```
robotctl update show
```

```
robotctl update watch
```
`log` 列出尝试记录，每行一个记录，最新的一行在最前面；第一列是运行编号。`show` 接受其中一个编号（或不接受，显示最近的一次），然后打印该运行的所有内容，以及同一窗口的日志：
```
run 42 · daemon · 2025-08-27 13:06:40 UTC
  applied 0.1.3 → 0.1.4
  asked for latest, from github.com/pollen-robotics/microduck, onto 0.1.3
  requested by uid=1000 gid=1000 pid=2317

  13:06:41      +1s  manifest     0.1.4 · 184.2 MB · sha256 3f9a1c2b… · signed by release.pub · rev 88efc03
  13:06:41           downloading
  13:07:58   +1m17s  note         downloaded 184.2 MB to /opt/robot/daemon/staging/0.1.4/dl/…
  13:08:02      +4s  note         hash matches; signature verifies against release.pub
  13:08:20     +18s  pre-hook
  13:10:12   +1m52s  hook         hooks/preinstall
                                 │ onnxruntime 1.20.1 already present
                                 │ gstreamer: h264 encode ok
  13:10:12           swapping     0.1.3 → 0.1.4
  13:10:14      +1s  unit         robotd: restart
  13:10:23      +8s  health       the robot reported healthy
  13:10:24           ended        applied 0.1.3 → 0.1.4

  ── journal · 2025-08-27 13:06:40 to 2025-08-27 13:11:24 UTC ──
```
时间是 UTC，日志也是 UTC。`+` 列表示与上一行的时间差，这就是你找到两分钟的方式。

阅读日志需要 `robot` 组没有的权限，因此除非你是 root，否则后半部分会为空。在这种情况下，它会打印出 `journalctl` 的那行；前面加上 `sudo` 就可以解决。`--no-journal` 会直接打印那行而不尝试解析，`--json` 则仅给出转录内容。
The component is `daemon` — 一个组件涵盖了所有的二进制文件。`apply daemon` 安装稳定渠道提供的内容；分支构建和候选发布版本需要使用 [`cheatsheet-dev.md`](cheatsheet-dev_zh.md)。

### 无需下载切换

切换到板子已经解压的内容，不涉及网络操作：
```
sudo robotctl update select daemon 0.1.4
```

```
sudo robotctl update rollback daemon
```

```
sudo robotctl update reset-to-golden daemon
```
`select` 激活已安装的版本，`rollback` 返回到之前已安装的版本，而 `reset-to-golden` 则返回到从未被修剪过的已知良好版本。

完全拒绝移动：
```
sudo robotctl update pin daemon 0.1.4
```

```
sudo robotctl update pin daemon
```
第二种形式会解除绑定。

### 当 `updaterd` 本身无法启动时

以上所有内容都需要通过 `updaterd` 来运行，因此当 `updaterd` 是那个宕机的守护进程时，所有内容都无法工作。请检查是哪一个：
```
systemctl status updaterd robotd btd configd
```
然后去掉它再回到黄金状态：
```
sudo robot-rescue --dry-run
```

```
sudo robot-rescue --reboot
```
`--dry-run` 会显示它将要执行的操作但不会进行任何更改。如果没有 `--reboot` 选项，它会交换版本并打印重启命令而不是运行该命令：由于每个守护进程都是通过 `current` 执行的，所以在守护进程重启之前没有任何东西会注意到这个交换，因此一个站立的机器人应该优先被捕捉。

它会拒绝并说明原因，当没有配置黄金版本或 `current` 已经是黄金版本时——如果守护进程在黄金版本本身上失败，回滚并不是解决方案，日志记录如下：
```
journalctl -b -u robotd -u updaterd -u btd -u configd
```
### 机器人可能已经执行过此操作

每次启动的前三分钟，一个计时器会询问是否已启动了守护进程，如果没有启动，则会回退到黄金版本。因此，如果一台机器人自行重启并且运行的是您安装的较旧版本之前的版本，它很可能已经自我恢复了。它所做的事情是：
```
robotctl update log
```
条目记录了一次回滚，失败的守护进程在其原因中被命名。要查看决策过程而不是其结果：
```
journalctl -b -u robot-boot-check
```

```
sudo robot-boot-check --dry-run
```
它只会执行一次。如果第一次救援仍在记录中，第二次救援将被拒绝——`updaterd` 在下次启动时会清除这一记录，因此被拒绝意味着守护进程在黄金版本中也没有启动，答案是查看日志而不是再次重启。如果在读完日志后你决定：
```
sudo robot-rescue --force --reboot
```
### 容易出错的三件事
`rollback` 需要一个前驱，但一次更新会创建一个。刚配置好的板子恰好只有一个版本，因此当时立即进行 `rollback` 没有更早的版本可以回滚到，因此会这么说。自动回滚不受影响：应用一个版本会将其与当前版本并行解压，然后才移动 `current`，因此在健康门运行时已经有两个版本了，你从来的那个版本就是目标。`rollback_target` 会选择 `current` 之下已安装且日志未记录为无效的最高版本——因此，一个只有一个版本的板子从配置的那一刻起就完全得到了保护。
进行了第一次更新。

真正未受保护的安装是 bootstrap 本身，因为它在定义上没有之前版本。`golden` 会覆盖这一点，并且在 1.0.0 不存在时故意未设置 —— 因此 `reset-to-golden` 会诚实地报告没有配置任何内容，而不是做些令人惊讶的事情。

**`version` 显示每个组件的当前版本，而不是发布存储库中的版本。** 无论解压了多少个版本，它都不会列出两个版本。直接询问存储库：

```text
ask the store directly:
```
ls -l /opt/robot/daemon/releases/ /opt/robot/daemon/current
```
**`apply --version` 需要该版本仍然存在于上游；而 `select` 则不需要。** 已知存在缺陷的版本会被从 GitHub 上删除，因此 `apply --version 0.1.3` 有意失败，而 `select 0.1.3` 在已经解压了该版本的板子上仍然可以正常工作。这种不对称性是故意设计的：新的板子不能获取到有缺陷的版本，而已经拥有有缺陷版本的板子则保留了退出机制。

### 无网络安装

---

保留了原文的语气和结构，确保翻译准确无误。
侧载、工厂安装或恢复一个 `updaterd` 过于陈旧以至于无法接受修复的电路板。请参阅 [`install-dev.md`](install-dev_zh.md) — 它是 `updaterd install --from`，在使用 `--force` 变体之前请阅读其注意事项。

### 日志
```
journalctl -u configd -b --no-pager | tail -40
```

```
journalctl -u btd -f
```
替换为 `robotd` 或 `updaterd`。`-f` 表示后续版本；`-b` 表示仅此启动。

启动行携带版本、git 版本和进程启动时所在的发布目录，在 `warn` 级别时保存，因此即使日志级别发生变化也能幸存下来。

更新历史故意与日志分开——每个条目在 `/var/lib/robot/updater/` 下通过 `fsync` 保存，因此即使日志本身是易失性的也能幸存下来：
```
robotctl update log
```
最近二十次运行也在 `runs/` 目录下保留了完整的日志，它们按实际发生时的顺序记录：

```
robotctl update show 42
```

这些记录能在交换、回滚和断电之后存活下来，而这个板子上的日志记录并非如此——
`/var/log` 是 zram。如果 `robotctl` 本身出现了问题，文件是以换行符分隔的 JSON，并且可以用 `cat` 正常读取：

```
sudo cat /var/lib/robot/updater/runs/000042.jsonl
```
### Tab 补全

`install.sh` 在 `/etc/bash_completion.d/` 中设置了这一功能，作为一个加载器，它会向二进制文件请求其自身的补全项——这样补全项会跟随安装的版本，而不是在更新添加命令时变得过时。对于 `install.sh` 没有覆盖的 shell，或者你直接从 `target/` 目录运行的构建：

```
eval "$(robotctl completions bash)"
```
`zsh`, `fish`, `elvish` 和 `powershell` 可以替代 `bash`。
