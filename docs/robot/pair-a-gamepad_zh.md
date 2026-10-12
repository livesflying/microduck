# 连接游戏手柄

每个手柄一次。之后，`padd.service` 会驱动连接的手柄，从启动开始——无需启动，也不会因你的 SSH 会话结束而停止。

## 将手柄置于配对模式

对于 **Xbox** 控制器，这是两次按压，第二次按压容易出错：

1. 通过 **短按** Xbox 按钮来开启它。不要按住该按钮——按住会关掉控制器。
2. 按下顶部边缘靠近 USB-C 端口的 **Sync** 按钮，直到 Xbox 灯光 **快速闪烁**。缓慢闪烁表示已开启但未配对。

对于 **DualSense**：同时按住 Create 和 PS 按钮直到灯条闪烁。

对于 **Pro Controller** —— 无名的 Switch 风格手柄，蓝牙控制台会将其列出为 `Pro Controller` —— 同时按住顶部边缘靠近 USB-C 端口的 **Sync** 按钮，直到玩家指示灯来回扫动。Xbox 为经典蓝牙（BR/EDR）手柄，而 DualSense 为低功耗蓝牙（LE）手柄，两者配对顺序相反；`pad pair` 会自动选择正确的手柄，而 [手动配对 Pro Controller](#手动配对 Pro Controller) 说明了如果需要手动配对时的顺序。

## 进行配对

```bash
sudo robotctl pad pair
```

```
looking for a gamepad in pairing mode — on an Xbox pad, press the small Sync button on the
top edge (not the Xbox button, which switches it off)
paired  Xbox Wireless Controller 78:86:2E:BB:13:28
padd is driving from it now.
```
无需MAC地址：机器人会在配对模式中寻找游戏手柄，并自动配对找到的第一个手柄。该手柄会被*信任*并配对，这也是它在无人登录的情况下重启后能够自动重新连接的原因。

如果有两个手柄处于配对模式，机器人会拒绝配对而不是猜测，并打印出它们的地址。为这些手柄命名也是将未被识别为游戏手柄的硬件配对的方式：
```bash
sudo robotctl pad pair 78:86:2E:BB:13:28
```
**第二个垫子无需遗忘。**一个已经绑定的垫子处于范围之内，并且每次扫面都会在配对模式中，因此机器人更倾向于选择一个处于配对模式的垫子；两者之后都会保持配对状态，`padd`会驱动连接的任意一个。代价是，如果在配对模式中没有新的垫子，重新运行时需要等待整个搜索窗口才能报告你已经拥有的垫子——如果你只是修复信任的话，就是`--timeout 5`。

## 检查它
```bash
robotctl pad status
```

```
pad     Xbox Wireless Controller 78:86:2E:BB:13:28  connected
padd    active — driving whatever pad connects
```
Two lines, 因为它们单独来看都会失败：一个连接的焊盘与一个死掉的驱动器看起来和一个正常工作但忽略你的机器人一模一样。

Pro 控制器也配备了一个六轴IMU，内核将其作为第二个输入设备暴露出来，除了驱动器之外。`robotctl monitor`，使用 `p` 选择焊盘块，会显示一个仅在焊盘有一个驱动器时才会出现的面板：一个线框焊盘以真实焊盘的姿态呈现，俯仰和滚转由重力决定，偏航由陀螺仪单独决定（它会漂移 —— 没有任何东西会观察航向），以及陀螺仪的静止偏置，克隆需要学习这个偏置才能让画面停止自行旋转。将焊盘放下半秒钟，面板会显示 `settled`。只有当监控器打开时，流数据才会产生成本：`padd` 只在有人订阅了 tap 时或它正在从该 tap 控制头部时读取 IMU 节点。
相同的姿态可以驱动机器人的头部。`sudo robotctl configure`，在 *Controller-IMU
头部控制* 部分，`enabled`: Y 然后将头部交给垫片的倾斜度，而摇杆继续控制，再次按下 Y 保持头部，第三次按下 Y 重新对准垫片当前的姿态并再次跟随——完整的循环可以在 [速查表](cheatsheet_zh.md#gamepad-configd) 中找到。监视器中的图像和头部使用同一个滤波器，因此绘制的垫片指向哪里，头部就转向哪里。

`配对但未信任`是值得了解的状态。现在它可以正常工作，并且在重启后不会重新连接，因为重新连接需要一个代理，而在启动时没有代理。重新运行 `pad pair` 可以修复这个问题。

## 忘记一个
```bash
sudo robotctl pad forget 78:86:2E:BB:13:28
```
This removes **机器人的半份**债券，这是机器人能移除的全部。垫片保留了它自己的半份，因此再次配对需要它处于配对模式——否则它会带着一个这个机器人不再拥有的密钥，从而被拒绝配对。

一个Xbox垫片只能持有 **一个** 主机债券，半完成的尝试会使其持有这个电路板不再拥有的密钥——这与电路板损坏时失败的方式完全相同。如果配对持续失败，先将垫片配对到一台笔记本电脑一次，然后在那里移除它；这会消耗并释放其债券槽位，仅仅将其置于配对模式并不能可靠地做到这一点。

## 当垫片完全无法配对时

在aic8800无线电中，当`btd`正在广播时，垫片无法形成 **新的** 债券。使用`--pause-btd-on-pair`重新配置这样的电路板：
```bash
./scripts/provision-board.sh --pause-btd-on-pair pierre@192.168.1.42
```
That 在 `/var/lib/robot/weird-ble` 处留下一个标记，并不改变其他任何内容。在带有该标记的板子上，`sudo robotctl pad pair` 会自行处理剩余部分 — 它会停止 `btd`，重启适配器，进行配对，然后再启动 `btd`。它会边做边说。现有的绑定关系不会受到任何影响，因此配对的垫子在所有服务运行的情况下会连接并驱动。

一些单位在 BlueZ 默认的 `Privacy = off` 下也无法进行绑定，即使 `btd` 被暂停也是如此。这些情况需要使用 `--weird-ble`，这会暂停 `btd` 并且也将 `Privacy` 设置为 `device`。

**先尝试暂停。** 在仅需暂停而不需要 `--weird-ble` 的板子上，`Privacy = device` 会导致更差的失败情况：垫子会绑定，然后在 `Encryption Change: PIN or Key Missing (0x06)` 的情况下振荡，从未创建输入设备。如果你看到这种情况，请去掉 `--weird-ble` 并保留暂停 — 详见 [`install-dev.md`](install-dev_zh.md#the-three-configurations-and-how-to-tell-which-you-have) 中的表格和命令，用于在两种配置之间切换。

在这样的板子上手动配对需要以下两个步骤：
```bash
sudo systemctl stop btd
```

```bash
sudo bluetoothctl power off && sudo bluetoothctl power on
```
Pair, 然后：
```bash
sudo systemctl start btd
```
The 电源循环是必不可少的。停止 `btd` 会留下其广告和配对代理给控制器提供的 IO 能力，而且一个垫子仍然拒绝配对——重启也有同样的效果，这就是这个问题被发现的方式。不要使用 `systemctl restart bluetooth`：在该板卡上，这会直到重启后才留下任何适配器。

`--weird-ble` 是默认选项，因为大约有一半的板卡需要它，而没有任何可量化的证据表明需要哪个。但是，不需要它的板卡也不应该携带它——这个标志在每次配对时都会导致 `btd` 停止和适配器电源循环——因此，那一页也说明了如何检查以及如何移除它。

两者都是针对 aic8800 无线电的变通方案，而不是设计特性。当无线电不再需要时，它们就会消失。

### 一个经典的垫子和 bluetoothd 的 CPU
A Pro Controller 每个包都会流式传输 IMU 样本，大约每秒 200 个包，无论是否有人触摸它。使用 BlueZ 的默认 `UserspaceHID=true`，每个包都会通过 bluetoothd 通过 uhid 传输，这在 graphite 上闲置的触摸板上占用了 16% 的核心资源。`scripts/setup-board.sh` 在每个板子上将 `/etc/bluetooth/input.conf` 中的 `UserspaceHID=false` 设置为 false，将通道交给内核的 `hidp`，从而将 bluetoothd 从数据路径中移除——在触摸板闲置的情况下，测量结果显示为 0.0%。使用相同的驱动程序，相同的输入节点，相同的连接。此设置在下次启动时生效。一个如 Xbox 之类的 LE 触摸板不受此设置的影响：HID 通过 GATT 从未经过 `input.conf`。一个在本设置存在之前进行预配置的板子可以通过重新运行脚本来获得此设置：
```bash
sudo sh scripts/setup-board.sh && sudo reboot
```
## 手动配对Pro手柄

仅在 `pad pair`不可用时。顺序很重要，并且是Xbox one的反序：
```bash
bluetoothctl pair 98:B6:E9:28:06:09
```

```bash
bluetoothctl connect 98:B6:E9:28:06:09
```

```bash
bluetoothctl trust 98:B6:E9:28:06:09
```
`connect` 首先 — 这个过程作为副作用会建立连接 — 最终会导致最难读取的状态：触摸板的指示灯变为常亮，`pad status` 显示 `connected`，`bluetoothctl info` 显示 `Paired: yes` 和 `Connected: yes`，但 **没有输入设备存在**，因此 `padd` 停留在“等待 padd 打开触摸板”的状态，没有任何输入。恢复的方法是使用 `sudo robotctl pad forget <address>`，将触摸板重新置于配对模式并重新配对。运行 `pad pair` 从不会产生这种状态：它会根据 BlueZ 报告的类型在配对前就进行配对。

## 当每次配对都失败时

检查 `/etc/bluetooth/main.conf` 中的 `Privacy` 设置。它应该显示为 `Privacy = device`。一块带有 `Privacy = off` 的电路板可能会完全拒绝与触摸板建立连接 — 连接会以 `le-connection-abort-by-local` 结束，触摸板从未达到 `Paired: yes`。

如果捕获显示配对过程在 `DHKey check failed (0x0b)` 处失败，那么 `Privacy = off` 就是需要尝试的值。在更改值之前先进行 `btmon` 捕获，因为这两种情况都曾出现过，需要不同的解决方案。
```bash
sudo sh scripts/setup-board.sh
```

```bash
sudo reboot
```
`setup-board.sh` 正确设置值，但直到重启后才会生效。

否则通常的原因是垫片在交换开始前已经退出配对模式：再次点击 Sync 并在灯光仍然快速闪烁时重新运行。要查看交换本身：
```bash
sudo btmon -t > /tmp/btmon.log 2>&1 &
```
Pair, 然后 `sudo pkill btmon`，并查找 `SMP: Pairing Failed` 以及旁边的失败原因。这就是区分板卡设置与未监听的垫子的唯一工具。

## 当你在驾驶时它掉了

观察垫子自身的输入流，它已经在板卡上：
Watch the pad's own input stream, which is already on the board:
```bash
robotctl monitor
```
按 `p`。打开的块是 `padd` 正在驱动的原始 evdev 流 —— 每个报告由内核按时间戳标记：
```
┌ pad Xbox Wireless Controller · /dev/input/event5 · 78:86:2e:bb:13:28 ─────────────┐
│ cadence  124/s while driving · last 8 ms ago · worst 84 ms · over 100 ms 0 · …    │
│ gap ms                                       ▁▁▁▁▂▁▁▁▁▃▁▁▁▁▁▁▂▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁ │
│ X     ····│██··   -8734 Y     ····│····       0 Z     ·········       0 …         │
│ held     BTN_START                                                                │
└ 4213 reports · gap ≤100 ms ───────────────────────────────── reports intact ──────┘
```
Move the 棒子并跟随它们移动。轨迹的作用在于上方的行：每份报告对应一根 棒子，因此一个停顿是一个峰值，而已经恢复的则仍然显示在屏幕上。全高为100毫秒——这是司机开始感受到的时间点——超过500毫秒后，`robotd`会将速度归零。

**机器人上没有其他部分能显示这一点。**`padd`以50赫兹重发最新的 棒子值，因此一个停止传输的无线电在下游看起来仍然像是一个活跃的司机：`robot.state`携带最新的意图，死机按钮从未触发，而机器人继续按照无人下达的命令行走。上方块中的`asked`列在这一列平直时看起来完美无缺。

静止的垫子不会发送任何信息，因此沉默只是在驾驶时的证据。该块显示“棒子仍然静止”超过五秒，而不是指责连接问题，并将这些时间段单独计数。

然后，为了在一个窗口中做出判断而不是实时画面，将测量值复制到此仓库的克隆版本中的白板上：
```bash
scp scripts/pad-link-test.sh radxa@<board>:/tmp/
```
已发生的事情，出自 `padd` 的日记——无需任何垫子，且能立即作答：
```bash
sudo sh /tmp/pad-link-test.sh --history
```
To measure the link现在，请保持拍打棒移动整个两分钟：静止的拍打棒不会发送任何信号，而沉默正好像是断开的链接。**保持拍打棒移动整个两分钟**：静止的拍打棒发送 nothing，而沉默正好像是一个 stalled 的链接。
```bash
sudo sh /tmp/pad-link-test.sh
```
It 计数滴答声，并在连接时记录按键之间的间隔。500 毫秒以上的间隔表示机器人停止——`robotd` 在那里将速度归零。每次滴答声后都会跟上内核的原因：`0x08` 表示监督超时，意味着范围或干扰；`0x13` 表示有人关闭了按键。

将按键放下不是停滞，也不被计为停滞——但这段时间内测量结果没有收获，因此报告会告诉你实际上驾驶了多少窗口时间，并且不会对它几乎看不到的连接进行评判。

在机器人监视时远离机器人是找到范围的方法。

## 这块板子是否运行相同的堆栈

一个按键在一台机器人上停滞而在其双胞胎上没有停滞，通常不是按键的问题。两块分别在几周前制造的板子运行不同的内核、不同的 BlueZ、不同的控制器固件，以及不同的按键固件——而这些在 `pad status` 中都看不到。

从这个仓库的克隆中复制报告到每块板子上：
```bash
scp scripts/pad-stack-report.sh radxa@<board>:/tmp/
```

```bash
sudo sh /tmp/pad-stack-report.sh
```
It 打印整个堆栈并在 `/tmp/pad-stack-<host>-<when>.log` 中保存相同的文本：内核,
BlueZ，适配器的 HCI 版本，它是哪个无线电以及内核在启动时为其加载的固件，哪个设备携带 HID，密钥绑定持有哪些键，当前使用的传输方式，以及 pad 的固件版本。它无需 root 权限运行，并对需要它的三件事说 `unreadable`。

要比较两块板子，只需询问每块板子那些必须匹配的值： 
To compare two boards, ask each for only the values that have to match:
```bash
ssh radxa@<board-a> sudo sh /tmp/pad-stack-report.sh --fingerprint > /tmp/a.fp
```

```bash
ssh radxa@<board-b> sudo sh /tmp/pad-stack-report.sh --fingerprint > /tmp/b.fp
```

```bash
diff /tmp/a.fp /tmp/b.fp
```
No输出意味着相同的堆栈。指纹不携带时间戳和地址，因此`diff`打印的任何内容都是真正的差异。

在其余内容之前再读两行。到目前为止，`transport`是`LE`，并且一个标有`BR/EDR`的板子将垫片通过内核的经典HID路径而不是BlueZ的——不同的驱动程序，不同的按钮编号。`input`是`Bus`/`Vendor`/`Product`/`Version`四元组，SDL和`gilrs`将其哈希为映射GUID：两个在这些方面不同的板子有不同的轴和按钮映射，其他方面匹配。

---

驾驶——控制和速度限制——在[作弊表](cheatsheet_zh.md#gamepad-configd)中；从笔记本电脑通过转发的套接字运行`padd`是在[开发作弊表](cheatsheet-dev_zh.md#from-a-laptop--drive-with-a-pad-in-your-hands)中。
