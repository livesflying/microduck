# 2026-08-18 Radxa Zero 3W `50:37:CD:16:2A:39` 下的最小设置

使用 Xbox 无线控制器 `78:86:2E:92:47:67` 进行配对。已在另一块相同的 Radxa Zero 3W 上确认。

## 成功的配对序列

为 Radxa Zero 3 安装 Armbian Minimal。在 imager 中填写 wifi 和用户名。不要安装其他任何内容 — 不要安装任何守护进程或进行任何预配置。
```bash
sudo sed -i -E 's|^[[:space:]]*#?[[:space:]]*Privacy[[:space:]]*=.*|Privacy = device|' /etc/bluetooth/main.conf
```

```bash
grep -n "^Privacy" /etc/bluetooth/main.conf
```

```bash
sudo reboot
```
A 重启而不是 `systemctl restart bluetooth`：有时重启会让内核持有 `hci0` 并显示 `No default controller available` 的错误，只有重启才能清除这个错误。

按住设备的配对按钮直到指示灯快速闪烁，然后：
```bash
bluetoothctl
```

```
scan on
```
等待 `[NEW] 设备 78:86:2E:92:47:67 Xbox 无线控制器`，然后：
```
scan off
```

```
connect 78:86:2E:92:47:67
```
Answer `是` to `请求授权`,然后：
```
trust 78:86:2E:92:47:67
```
`pair` 从未被类型化。

## 当它正常工作时的样子
```bash
ls /dev/input/js*
```

```bash
dmesg | tail -3
```

```
input: Xbox Wireless Controller as /devices/virtual/misc/uhid/0005:045E:0B13.0001/input/input5
microsoft 0005:045E:0B13.0001: input,hidraw0: BLUETOOTH HID v5.09 Gamepad [Xbox Wireless Controller]
```
- 转动左摇杆并持续移动，查看超出前184字节的内容，寻找类型为 `0x02` 且时间戳递增的事件：
```bash
sudo timeout 5 cat /dev/input/js0 | od -Ad -tx1 | head -20
```
The bond 在进行垫片电源周期后仍能存活（按住Xbox按钮约6秒，然后切换回开机）：
```bash
ls /dev/input/js*; bluetoothctl info 78:86:2E:92:47:67 | grep -E "Connected|Bonded|Trusted"
```
## 用于测试的电路板

并非任何人预期中的配置，因此每个配置都记录了下来：

| | |
|---|---|
| `cat /sys/module/aic8800_bsp/srcversion` | `738316A2E9D9825966BDB6B` (86016) |
| `conn_min_interval` / `conn_max_interval` | 24 / 40 — 内核默认值，30–50 毫秒 |
| `/etc/bluetooth/main.conf` | `Privacy = device` |
| 运行的守护进程 | 无 |

驱动程序是 `design/pad-bond-failure.md` 调用的损坏的构建。连接间隔未更改。同样未更改的是决定是否连接的因素。

## 什么失败了

| 配置 | 结果 |
|---|---|
| 纯 Armbian，`Privacy = off`（或未设置 — BlueZ 默认为 `off`） | `connect` 返回 `le-connection-abort-by-local`；`Paired: no`；完全没有 SMP 交换 |
| 纯 Armbian，没有 `Privacy` 行，以 `pair` 而不是 `connect` 开头 | 建立连接，然后每次重新连接都会失败 `Encryption Change: PIN or Key Missing (0x06)`，每秒波动约 1 次 |
| 配置好的电路板（确认第 99 行 `Privacy = device`），`padd` 和 `btd` 停止，手动 `connect` | 接受 `Request authorization`，然后 `ServicesResolved: no` — 该垫片立即断开连接，没有 `js0` |

第三行是开放的：相同的卡映像和相同的 `Privacy` 值在电路板配置后失败。因此，是配置更改导致的问题，而不是运行中的某个进程 — 停止 `padd` 和 `btd` 并未恢复配对。

## 建立连接和保持连接是不同的

在完全配置好的电路板上，一个 **已配对** 的垫片可以连接并驱动。一个 **新鲜** 的 `robotctl pad pair`，在 `pad forget` 后并在垫片处于配对模式下执行，会失败。

所以这里没有破坏现有的连接。安装系统中的某些东西阻止了新连接的建立。`configd` 和 `btd` 的日志没有提供有用的信息。

## 明天：一次添加一个东西

从一个重新刷写并由页面顶部的序列确认工作的电路板开始，一次添加一层，重启，尝试新鲜配对，然后再添加下一层。

将脚本复制到 `~`，**不** 是 `/tmp` — 每一步都会重启，而 `/tmp` 无法在一次重启后存活。同样，任何值得保留的 `btmon` 捕获也应如此。
```bash
scp scripts/setup-board.sh scripts/migrate-network.sh pierre@BOARD:~/
```
| 步骤 | 添加的内容 | 有配对对吗？ | 备注 |
|---|---|---|---|
| 0 | 没有添加 — 上面的最小序列 | 是 | 控制 |
| 1 | `sudo sh ~/setup-board.sh` — 覆盖层，`console=display`，getty屏蔽，onnxruntime | **是** | |
| 2 | `sudo sh ~/migrate-network.sh` — netplan → NetworkManager | **是** | |
| 3 | `sudo -E sh ~/install.sh` | **否** | 初次尝试；守护进程已运行 |
| 3b | `DUCK_NO_START=1`，然后重启 | **是** | 所以 `install.sh` 写入磁盘的内容没有问题 |
| 4 | `systemctl enable --now updaterd` | | |
| 5 | `... robotd` | | |
| 6 | `... configd` | | |
| 7 | `... btd` | | |
| 8 | `... padd` | | |

2026-08-19 执行，每一步都手动与 `bluetoothctl` 配对，并在之后移除配对。步骤 1 和 2 配对良好；问题出现在 `install.sh`。因此，板卡启动、设备树覆盖层、控制台迁移和 NetworkManager 切换均被排除。

在 `install.sh` 内部 2026-08-19 分割：使用 `DUCK_NO_START=1` 和重启后，配对成功。因此，`install.sh` 写入磁盘的内容没有问题 —— 不是单元、用户、组、发布树或令牌插件。问题出在五个守护进程中的一个，它们在运行。

在测量该指标时，前三次尝试都失败了，原因相同：发布树内的 `hooks/postinstall` 在 `updaterd install` 内部对每个单元执行 `systemctl enable --now`，而 `install_units` 之前就已运行，因此在每次测试中守护进程均已启动，之后的 `systemctl disable --now` 无法撤销它们推送到适配器的内容。`btd` 保持 `Pairable` 状态，一个广告实例，并且使用默认配对代理设置的适配器的 IO 能力。**测量前重启。**

## 问题在于 `btd`

2026-08-19，一个变量，`2A:39` 上可重复：

| | |
|---|---|
| `btd` 启用，重启，重置配对，重新配对 | **失败** |
| `btd` 禁用，重启，重置配对，重新配对 | **成功** |

`/var/lib/bluetooth` 在成功运行中 **未** 被清空，因此 `btd` 导致 BlueZ 写入的两个文件 —— `attributes`，持久化的本地 GATT 数据库，和 `identity`，适配器的本地 IRK —— 均被排除。其他任何持久化的内容也被排除。
早期的一轮中，禁用 `btd` 并未恢复配对是因为手柄自身的绑定槽位：Xbox 手柄持有主机绑定槽，而半完成的尝试使其持有板子不再拥有的密钥。**在尝试之间，在笔记本上重置手柄**，否则故障将与中毒的手柄无法区分——这耗费了两天多的时间。

没有运行中的程序会阻止现有绑定继续工作：绑定的手柄可以连接并使用整个堆栈进行驱动。只有 *创建* 绑定会失败。

### 机制，尚未测量

`btd` 会连续作为外设进行广播。当 `Privacy = device` 时，广播使用可解析的私有地址，而同一适配器作为中心来绑定手柄。SMP DHKey 检查是基于两个设备的地址计算的，因此这种形式会产生 `DHKey check failed (0x0b)` — 这是导致这个分支放弃 `Privacy = device` 的原因，当时 `btd` 正在运行。通过 `btmon` 捕获一次失败的配对，读取自己的地址类型和 SMP 失败原因，可以确定这一点。

### 两个故障，它们被当作一个读取

在重置手柄后重新测试，因此两个结果都不是基于中毒的绑定槽位：

1. **板子分裂。** 在没有任何安装内容的新 Armbian 中，一些 Zero 3W 单元在 BlueZ 的默认 `Privacy = off` 下绑定手柄。另一些则在 `off` 下根本不绑定，只有 `device` 起作用。每组大约有十个中的五个，没有任何可测量的区别。
2. **`device` 与 `btd`。** 在 `device` 下，手柄在 `btd` 广播时无法形成新的绑定。

它们共同解释了 `DHKey check failed (0x0b)`，这导致这个分支将 `Privacy = off` 设置为默认值：这是故障 2，测量时板子需要 `device` 来解决故障 1，而这个结果被解读为 `device` 破坏了配对。结果是一个设置，它在一半的板子上无法绑定手柄，持续了两周。

单独停止 `btd` 并不足够：它推送到控制器的数据会持续存在，因此每次手动配对成功后都需要 **重启**。通过 `bluetoothctl power off && power on` 来断电和重新启动适配器可以替代重启——测量日期为 2026-08-19，在完全安装的板子上 `pad pair` 首次尝试成功——这正是保持配对一次命令所需的。
Both 工作around 都在 `provision-board.sh --weird-ble` 之后，因此不需要它们的板子不会携带这些 workaround：这个标志设置 `Privacy = device` 并保留 `/var/lib/robot/weird-ble`，而 `robotctl pad pair` 只在带有该标记的板子上暂停 `btd`。首先尝试没有该标志的板子。两者在aic8800完成时都会结束。

每一步之后都需要重启，并在每次尝试之前清除 **两个** 半键：在板子上使用 `pad forget` 或 `bluetoothctl remove`，并在保持配对模式的pad上执行。一个Xbox pad会保持一个主机半键，而半完成的尝试会让它持有板子不再拥有的密钥——这与故障现象完全相同。

Step 3 需要 `install.sh` 读取的环境：
```bash
export DUCK_TOKEN=github_pat_replace_with_your_token
```

```bash
export DUCK_REF=pad-privacy-device-not-off
```

```bash
export DUCK_DEV_KEY=$HOME/team.dev.pub
```
步骤 1 和 2 无需 token 也不需要网络。

## 与 `microduck_runtime` 未测试的差异

`microduck_runtime` 的安装程序会在活动的 NetworkManager 连接上禁用 wifi 电源管理状态
(`install.sh:244`, `:383`)：
```
sudo nmcli con mod "$WIFI_CON" wifi.powersave 2
```
`scripts/` 没有对应的项。aic8800 是一个集成了 WiFi 和 Bluetooth 的部件，共用一个 SDIO 接口的无线电，因此这可能是上面第三行的候选项——但裸板上工作的值从未被读取，所以它是一个候选项而不是发现。
```bash
iw dev wlan0 get power_save
```
## 故障 3: 在手机连接时，一个焊接点无法重新连接  · **测量**（2026-09-17）

上述两个故障与“焊接”有关。这个故障是单独的，是使用手机应用时遇到的第一个问题。

在 `lavandiere` 上 —— 配置了 `--weird-ble`，因此 `隐私 = 设备` —— 一个 Xbox 控制器已经焊接并信任：

| | |
|---|---|
| 应用连接，控制板打开 | 控制板从未连接 |
| 应用退出，控制板打开 | 立即连接 |
| 先连接控制板，然后应用 | **两者都正常工作** |

所以这不是焊接问题，也不是控制板问题。无论哪个连接先建立，都会保留，第二个连接可以添加到其中 —— 但在 `btd` 持有一个外围设备连接时，无法开始一个新的中心连接。

从板上明确发起的连接会这样说，而不仅仅是超时：
```
Failed to connect: org.bluez.Error.Failed le-connection-abort-by-local
```
That 是本地主机放弃，而不是PAD拒绝。BlueZ的背景自动连接对受信任设备的操作通常是导致这种情况的原因，而它也会以同样的方式失败——这就是为什么PAD只是静静地坐在那里。

**`btd`当时没有进行广告。**当一个中心设备连接时，`btd`会停止广告，这就是为什么`duckctl scan`无法看到某人手机正在与其通信的机器人。因此，这并不是另一种故障的表现：广告已关闭且初始化仍然失败，这表明控制器在作为外设而不是选择的任何守护程序时拒绝成为初始化器。

### 不值得构建的内容

显而易见的修复方法——`configd`或`padd`轮询一个已连接但未连接的PAD并将其连接起来——**不起作用**，因为正是这个调用返回了上述错误。

能够起作用的两种方法都对这个无线模块来说是糟糕的交易。`btd`可以随时断开与PAD的连接，这使得手机在随机时间断开连接，需要`btd`知道PAD正在请求连接，但它没有这种学习方式。或者，配对和重新连接可以被移到一个应用程序驱动的序列中，该序列在故意断开连接后执行，但这与本页面讨论的芯片替换工作相抵触。

### 应该怎么做

**在打开应用之前先开启PAD。**这样两者都能正常工作，而顺序就是整个变通方案。`pad.status`分别报告`paired`和`connected`，因此客户端可以观察到这种状态——已配对、已信任、未连接——并告知用户，而不是让用户在忽略Xbox按钮的机器人面前按按钮。

就像其他两种情况一样，这也会在aic8800上失效。
