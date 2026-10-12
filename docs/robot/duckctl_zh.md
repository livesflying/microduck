# `duckctl` — 每个命令

用笔记本电脑与一个机器人对话，无需网络和 ssh。它是手机应用的替代品，也是从未接触过 wifi 网络的机器人的访问方式。

今天它是通过蓝牙 LE 实现的，但名字刻意没有提到这一点：`mediad` 为机器人提供了一种第二种传输方式，可以访问不同的方法，因此工具的名字是根据它所交谈的对象来命名的，而不是当前使用的无线电。它曾是 `duck-btctl`，当时蓝牙 LE 是唯一的选择。

**绝不要在机器人上使用。** 在任何版本中都不会依赖它 —— `robotctl` 是发布的工具，而 [`cheatsheet.md`](cheatsheet_zh.md) 列出了它的命令，大多数命令在下面都有 `duckctl` 的对应版本。

## 获取它

从这个仓库的克隆版本中运行它：
```bash
cargo run -q -p duckctl -- --name <robot-name> info
```
Or 安装一次，代价是获得一个不再跟随分支的快照：
```bash
cargo install --path duckctl
```

```bash
duckctl --name <robot-name> info
```
Every command below是安装后的形式。请在前面加上`cargo run -q -p duckctl --`来从克隆的代码运行它。

此工具以前会将其自身安装为`btctl`。如果`which btctl`仍然能找到它，那么它是你安装时的一个构建版本，并且永远不会再次更改：
```bash
cargo uninstall btd --bin btctl
```
## 寻找机器人
```bash
duckctl scan
```

```
1 robot(s) advertising the duck service:
  aa:bb:cc:dd:ee:ff duck-c51b — 192.168.1.42, 1 service(s)  ← DUCK_ROBOT

7 other device(s) in range, not listed. …
```
Robots 只读，其他一切都在无线电范围内统计而非列出。`--verbose` 会扩展这个列表，并且当你要找的机器人不在第一个列表中时，值得阅读。  
每台机器人广播其 IPv4 地址，因此这也是 SSH 连接地址的来源。没有建立连接，也不需要 PIN。列表中显示 `no address` 表示该机器人未连接网络；没有地址的行意味着该机器人来自在机器人广播地址之前的一个版本，并且 `duckctl wifi status` 仍然会报告它。  
列表中不显示 SSID — 它无法在广播中容纳。`duckctl wifi status` 会显示 SSID，以及信号强度和两个地址。  
单独显示地址：
```bash
ssh radxa@$(duckctl ip)
```
`ip` 打印地址后什么也不打印，因此它充当替代品。它读取广告信息，所以它不连接到任何东西，不需要 PIN，且大约需要一秒钟 —— 而答案并非过时：`btd` 每五秒重新读取地址并重新广告当它移动时。

Or skip the substitution:
```bash
duckctl ssh
```

```bash
duckctl ssh -- sudo robotctl pad pair
```
`ssh` 使用 `ip` 的方式找到地址，然后成为 `ssh`，因此提示、终端和退出状态都是 `ssh` 自己的。账号是 `--user`，否则是从环境变量中读取的 `DUCK_BOARD_USER` —— 这个变量是 `dev-push.sh`（参见 [dev-push.md](dev-push_zh.md)）读取的，因此配置用于推送的笔记本电脑也配置了这个功能 —— 否则为 `radxa`。`--` 之后的参数会在机器人上运行而不是打开一个 shell。

文件也是如此传输的：
```bash
duckctl scp report.md :/tmp/
```

```bash
duckctl scp :/var/log/robotd.log .
```
A 路径以 `:` 开始是在机器人上 — `scp` 的 `host:path`，省略了主机名，因为主机名是这个工具为你找到的。其余部分按原样传递给 `scp`，包括 `-r` 和其他所有标志，进度条和退出状态均为 `scp` 自身。账号解析方式与 `ssh` 一致。

此工具的标志位于路径之前：
```bash
duckctl --name ducky scp -r logs/ :/tmp/
```
A 未包含 `:` 的副本在扫描前会被拒绝，因为它是一个机器人未参与的本地到本地的复制，`scp` 的输出也不会说明这一点。一个确实名为 `:foo` 的本地文件是 `./:foo`。

与这台机器绑定的机器人通常会停止为其提供服务，然后 `ip` 连接并询问 `net.status`。这会变慢并需要输入 PIN，但它总是会回答。`--verbose` 会说明发生了哪种情况。

没有网络地址的机器人会被告知如何处理，而不是被报告为空，因为修复是通过无线电进行的，而且必须如此 —— `net.connect` 由于设计原因不会通过 WebRTC 来执行。

从未重命名过的机器人会称自己为 `duck-` 加上从其序列号派生的四个字符，因此为 `duck-c51b`。一个同时以两个名称报告的机器人的任意一半 —— macOS 显示 `radxa-zero3 [duck-c51b]` —— 可以通过 `--name` 来使用。
A 机器人扫描为 `duck-c51b`，然后在一次连接后仅显示为 `radxa-zero3`。该机器人所在的版本给广告命名但未给适配器命名，而客户端缓存了适配器的名称。更新该机器人。这不会清除客户端已缓存的内容，因此也需要清除缓存：在 Linux 上使用 `bluetoothctl remove <mac>`，在 macOS 中则在蓝牙设置中忘记该机器人。

如果没有名称——没有 `--name`，也没有 `DUCK_ROBOT`——则首先找到的机器人获胜。如果有名称，两个回答该名称的机器人将是一个错误而不是选择：
```
2 robots answer to "radxa-zero3": radxa-zero3, radxa-zero3
```
That 发生在一个启动加载程序将其串行端口留空的电路板上，因为在这种情况下，电路板会根据其主机名命名，因此从同一个映像烧录到的所有电路板都会使用同一个主机名。从机器人本身重命名一个，并使用新的名称：
```bash
robotctl system set-name ducky
```
## 控制台

机器人提供一个页面，实时流式传输其摄像头画面并控制其行驶：
```bash
duckctl open
```
Finds the机器人,然后在浏览器中打开`http://<地址>:8080/`。`--print`会给出URL，适用于没有浏览器的机器或脚本；`--port`用于启动使用非默认`mediad --web-port`的机器人。

无需安装任何内容，也无需提供服务——`mediad`嵌入了页面，因此运行该守护进程的机器人具有控制台。

页面上有什么：带有链接的比特率、帧率、丢包率和往返时间的摄像头；两个操纵杆和键`W`/`A`/`S`/`D`和`Q`/`E`用于控制，速度为游戏手柄的0.3米/秒和1.5弧度/秒；拖动图片以查看某个点；启用、初始化、放松、停止和关闭；语音库作为菜单和**机器人填充的技能菜单**——机器人具有哪些技能由配置决定，因此页面会询问`robot.policies`而不是提供一个猜测的列表；以及每2秒更新一次的`robot.health`旁边的状态流，其中会命名热伺服器、扁平包装或运行缓慢的循环。

`stop`会清零页面发送的意图。**这不是紧急停止**——系统中没有任何内容会从浏览器切断伺服器电源——因此该按钮只是一个普通的停止按钮。
The 原始 JSON 盒子、日志以及 WebRTC 对端被拒绝的两次调用都在底部的抽屉里。它们证明正在查询路由表而不是驱动机器人。

涉及两个端口，仅此一个被输入：页面通过它被服务的主机本身连接到 8443 的信号服务器。如果页面加载后说其信号端口没有响应，那么机器人已经启动，而你和 8443 之间缺少的可能是——通常是防火墙。

摄像机和驱动控制依赖于 WebRTC，除此之外别无他物，因此没有网络地址的机器人没有控制台。首先将它通过无线电连接到一个网络——下面的 `duckctl wifi connect` 不需要自己的网络。

## 总是同一个机器人

将名称放在环境变量中而不是每个命令行中：
```bash
export DUCK_ROBOT=duck-c51b
```
将那行代码添加到 `~/.zshrc` 中以保持它。此后面的每个命令都可以省略 `--name`：
```bash
duckctl info
```
`DUCK_PIN` 对应 `--pin`，对于每个命令都需要一个自己的PIN的机器人来说，需要使用它：
```bash
export DUCK_PIN=418299
```
对于针对不同机器人的一个命令，`--name` 仍然生效：
```bash
duckctl --name duck-ffff info
```
To 忽略一个命令的默认设置——一个与别人机器人一起的测试——将其设置为
nothing：
```bash
DUCK_ROBOT= duckctl scan
```
`scan` 标记机器人 `DUCK_ROBOT` 并将其列在首位，而每一条寻找它的命令在开始扫描之前都会说明这一点。

## 身份
```bash
duckctl --name <robot-name> info
```
名称, 序列号和运行时间。
```bash
duckctl --name <robot-name> name <new-name>
```
Up to 24个字符。生效几秒内无需重启，但Mac会继续使用它之前学到的名称，因此`scan`和macOS蓝牙设置都会滞后。每个后续命令都会使用新的名称。

重命名不会遵循`DUCK_ROBOT`。工具之后会这么说；变量需要手动更改，否则每个后续命令都会寻找一个不再响应的名称。
```bash
duckctl --name <robot-name> reboot
```
## Wifi
```bash
duckctl --name <robot-name> wifi status
```
SSID，信号和地址。
```bash
duckctl --name <robot-name> wifi scan
```
Takes a few seconds — 机器人扫过无线电而不是返回之前的扫描。
```bash
duckctl --name <robot-name> wifi connect <ssid> --psk <passphrase>
```
- 使用 `--psk` 用于开放网络。连接断开后，机器人将从当前网络断开连接，因此通过 Wi-Fi 的 ssh 会话会中断；这就是该命令的效果。该命令最多可能需要 45 秒才能响应。
```bash
duckctl --name <robot-name> wifi forget <ssid>
```
## 是的
```bash
duckctl --name <robot-name> health
```
是否控制回路健康。
```bash
duckctl --name <robot-name> status
```
The version握手和更新状态。

## 它正在运行哪个版本
```bash
duckctl --name <robot-name> version
```
The API版本、发布的版本以及它所构建的git修订版本。`revision`为`null`意味着该发布是在某人的笔记本电脑上构建的，而不是由CI构建的。

## 日志
```bash
duckctl --name <robot-name> logs robotd
```
The last 40 行 那个守护进程的日志，在这次启动中。更多信息，请参阅上次启动：
```bash
duckctl --name <robot-name> logs robotd -n 200
```

```bash
duckctl --name <robot-name> logs btd --boot -1
```
可读单位: `updaterd`, `robotd`, `configd`, `btd`, `padd`, `mediad`, `tofd`，以及 `bluetooth` 和 `NetworkManager`。`.service` 后缀是可选的，任何其他内容都会被拒绝处理。

日志输出到 stdout，其他内容输出到 stderr，因此 `logs robotd -n 200 | grep -i panic` 可以正常工作。长尾会被修剪到无线电能承载的长度，按最早时间顺序显示，并附带说明。

跨越重启的日志尾部会说明位置：
```
2026-09-09T12:27:20+00:00 systemd[1]: Starting robotd.service - Robot control daemon...
-- new robotd process, pid 3227 --
2026-09-09T12:27:21+00:00 robotd[3227]: control loop running joints=15 hz=50.0 driving=true
```
Which 条款 在更新后变得重要，当四十行包含两个不同构建的输出。任何在 `-- … --` 中的内容来自机器人而不是日志。

没有 `-f`，没有 `--since`，也没有搜索功能。对于这些功能，请通过 ssh 登录：
```bash
ssh radxa@$(duckctl --name <robot-name> ip)
```

```bash
journalctl -u robotd -f
```
## 更新

与 `robotctl update` 的含义相同，因此在机器人上学习到的命令在这里也适用。每一个命令都接受 `--component <name>` 选项，并默认为 `daemon`，这是机器人目前唯一的组件。
```bash
duckctl --name <robot-name> update check
```

```bash
duckctl --name <robot-name> update status
```

```bash
duckctl --name <robot-name> update versions
```

```bash
duckctl --name <robot-name> update log --limit 20
```
安装只需几分钟，并会在安装过程中打印进度信息：
```bash
duckctl --name <robot-name> update apply
```

```
· daemon: preflight
· daemon: downloading 12%
· daemon: downloading 47%
· daemon: verifying
· daemon: swapping
· daemon: health_gate
{
  "outcome": "applied",
  "from": "0.5.1",
  "to": "0.6.0"
}
note: the robot restarts its daemons now, and `btd` about five seconds after this reply — so this
connection drops. That is the update working. Reconnect and run `duckctl update status`:
`last_attempt` carries the outcome of what just ran.
```
The connection 断开后才是更新生效，不是失败。重新连接并读取
`更新状态`。

一个分支构建、精确版本或 staging 候选版本：
```bash
duckctl --name <robot-name> update apply --ref my-branch
```

```bash
duckctl --name <robot-name> update apply --version 0.5.1
```

```bash
duckctl --name <robot-name> update apply --staging
```
`--dry-run` 验证一切并在交换前停止。`--ref` 和 `--version` 是替代选项；同时请求两者会被拒绝。

回退 — 上一个版本，或者从 `更新版本` 中指定的一个版本：
```bash
duckctl --name <robot-name> update rollback
```

```bash
duckctl --name <robot-name> update select 0.5.1
```
Both都是像apply一样被限制的，所以没有出现的会被回滚。 neither 也不会丢弃任何内容。

其他人开始的更新进度，或者由机器人本身触发的更新进度：
```bash
duckctl --name <robot-name> update watch
```
It 打印出正在飞行中的更新到了哪里，然后打印出所有后续的内容。它从不接收
回复，因此会通过 Ctrl-C 结束。

## The Hugging Face 账户
```
duckctl account login
```
打印代码并打开 <https://hf.co/oauth/device>，在那里输入它——Hugging Face 的设备页面不接受 URL 中的代码，因此打开此页面可以保存导航历史而不是重复输入。**机器人会等待**，因此此工具在打印代码后会断开连接——在它打开的浏览器中批准它，或从任何其他设备批准，然后：
```
duckctl account status
```

```
duckctl account logout
```
This is the one thing that works on a机器人从未见过网络的机器:没有Wi-Fi意味着没有控制台和LAN,只剩下蓝牙。通过BLE进行登录与设置向导运行的流程相同。
```
duckctl account login --no-open
```
for 代码和URL无需浏览器——这也是当输出不是终端时你自动获得的内容，因此一个脚本不会启动任何内容。

已登录的机器人会拒绝并命名其账号，同样，等待代码审批的机器人也会这样做。`--force` 可以替换这两种情况——废弃的代码将失效。

## 策略与技能

每个插槽运行的内容，以及此机器人拥有的技能：
```bash
duckctl policy list
```
The `skills` 数组是回答“这个机器人可以被要求做些什么”的答案。它们是配置项，因此在不同的机器人之间会有所不同，并没有默认的列表可以假设——在提供按钮之前请先阅读。


Run one:
```bash
duckctl do roulade
```
**机器人必须处于行驶状态。**首先在手柄上按下Start，否则它会这么说。不过它不需要手柄输入：死人按钮会自动归零，因此一个没有人操控的机器人会原地不动并执行任务。

更改它行走的方式，实时进行：
```bash
duckctl policy load walk /opt/robot/policies/current/alpha_walking.onnx
```
放回那个插槽：
```bash
duckctl policy reset walk
```
One slot 一次，因为电线调用一次处理一个——重置所有七个需要 `robotctl policy reset` 命令。路径在 *机器人* 上，必须是绝对路径。

从这里加载的配置在重启后 **会保留**，就像机器人上的 `robotctl policy load` 做的一样：守护进程会在切换前将槽位写入 `robotd.toml`。`duckctl policy reset <slot>` 是撤销操作。

重新从配置文件读取每个槽位，当其他因素更改了它们时：
```bash
duckctl policy reload
```
The 机器人带着扭矩开启、负载存在并且再次启动——几秒钟后，超时允许其继续。任何不是 `obs[1,61] -> actions[1,14]` 的文件在任何变化之前都会被拒绝，即使负载失败，也会保持运行中的策略。

### 来自 Hub

对于这个机器人的其他发布内容，以及官方集是否已更改：
- 翻译全文，不得省略、增加内容。
```bash
duckctl policy search microduck
```

```bash
duckctl policy check
```
安装最新官方版本 — 或者使用 `--version v1` 回退：
```bash
duckctl policy update
```
下载别人的，不要运行它：
Download somebody else's, without running it:
```bash
duckctl policy fetch RemiFabre/microduck-flamingo-cycle
```
The reply 指明了它着陆的路径。`load` 接受一个路径参数，并且从不处理 `org/repo`：在这里，获取和加载是两个独立的调用，`robotctl` 使用同一个字符串来表示两者。

### 给它起个名字

`fetch` 下载一个文件；这使得它成为 `robot do` 可以处理的内容：
```bash
duckctl policy skill polite-bow --path /var/lib/robot/policies/fffiloni/microduck-polite-bow-b1d864/main/policy.onnx --duration 4
```

```bash
duckctl do polite-bow
```
One call — 机器人编写其配置并重新加载，所以 nothing restarts 不重启。`--duration` 第一次调用时必需，之后则保持不变，因此更改一个字段意味着发送一个字段： `--duration` 第一次调用时必需，之后则保持不变，因此更改一个字段意味着发送一个字段：
```bash
duckctl policy skill polite-bow --command 1,0,0
```
`--command` 是网络运行时输入的扭曲，通常为零，除非策略读取的扭曲不同 —— 翡冷翠的扭曲为 `[flag, side, 0]`。`--unwind` 和 `--unwind-s` 是将一直保持到被取消的策略带回的方法。

这台机器人可以被要求做的事情及其背后的时间安排：
```bash
duckctl policy skills
```
`built_in` 在那个答案中命名了 `ground_pick` 和 `sit_toggle`，robot 也会接受这些名称，但它们由机器人本身驱动，并不是表格中的条目。
```bash
duckctl policy unskill polite-bow
```
A 该机器人发布的版本中包含的一项技能会在你这样做时返回，因为移除条目只会移除覆盖。

没有任何陌生人发布的内容会被任何人验证。使其安全可试的是下载前的清单门控，加载时的形状门控，关节夹钳和跌落反射——而不是描述。第一次让机器人站在支架上。

## 哪个按钮运行哪个技能
```bash
duckctl pad bindings
```

```bash
duckctl pad bind x polite-bow
```

```bash
duckctl pad reset x
```
**无需重启也无需其他操作** — `padd` 会在一秒钟内重新读取文件。名称会首先与这个机器人的技能进行比对，因此拼写错误会以拒绝命名真实技能的方式返回，而不是成为一个按下后没有任何反应的按钮。

列出的两件事是客户端无法自行解决的：`overridden`，因此即使不知道默认值，也能看到某人的更改；`error`，表示与这个机器人不再具备的技能关联的按钮 —— 获得这种按钮的现实方式是移除一个技能，而不是误输入。

`""` 可以关闭一个按钮，这与 `pad reset` 将其恢复为机器人出厂设置的方式不同。五个按钮可以绑定：`a`, `x`, `lb`, `rb`, `dpad_down` — 而 `lb`/`rb` 被称为 **扳机键**，因为模拟扳机是机器人的嘴和呱呱声。

配对一个手柄属于不同的命名空间和不同的守护进程 —— `pad.pair` 和 `pad.forget` 是 `configd` 的，通过 `call` 调用。这两个操作是 `robotd` 的，因为检查技能名称需要技能列表。

## 其他任何事情 — `call`
```bash
duckctl --name <robot-name> call <method> '<json-params>'
```
Params 默认为 `{}`。这些参数可以通过蓝牙访问，但没有自己的包装器，并且不需要在前面加上 `duckctl --name <robot-name>`：

| | |
|---|---|
| `call system.services` | 哪些守护进程正在运行，以及每个守护进程运行的版本。|
| `call pad.status` | 游戏手柄是否已配对以及是否已连接？|
| `call pad.pair '{"timeout_seconds":30}'` | 配对模式下的手柄进行配对。|
| `call pad.forget '{"mac":"<地址>"}'` | 删除配对关系。|

`call` 命令等待 60 秒以获取响应。上述更新命令则是等待 *静默* —— 三分钟内没有任何数据到达 —— 因此它们是运行更新的方式，而不是 `call update.apply`。

## 全局选项
- `--name <robot-name>` — 哪个机器人。如果没有指定，使用 `DUCK_ROBOT`；如果没有 `DUCK_ROBOT`，则使用第一个找到的已连接外设。通常总是指定：它会跳过一个缓慢的后备层级，该层级会尝试 Mac 上所有已连接的外设，包括耳塞。
- `--pin <六位数字>` — 默认为 `DUCK_PIN`，如果没有，则为 `000000`。在机器人上运行 `robotctl system pin` 可查看实际的 PIN。
- `--verbose` — 打印每条发送和接收的行，并让 `scan` 列出所有设备而不是仅列出机器人。当遇到卡顿时，应最先添加的选项。

## 它会打印什么

回复会输出到 stdout，格式化为漂亮的 JSON，而其他内容，如进度、诊断信息或无线电接收到的内容，则输出到 stderr。`logs` 是例外情况，会按行打印其内容，因为 JSON 格式的日志转义后难以阅读；从它那里拒绝的回复仍然会以 JSON 格式输出。因此，`duckctl ... info > reply.json` 可以将两者分开，而来自机器人的 JSON-RPC 错误仍然会以非零退出状态结束。进度行以 `·` 开头，每行一个，因此 `update apply > outcome.json` 会将它们保留在屏幕上并将结果保存在文件中。

一个命令对应一个连接：它会找到机器人，如果需要会进行配对，验证 PIN，询问并断开连接。
Every command 在一段时间的静默后放弃执行，而不是在固定的时间内放弃，因此缓慢的更新永远不会被中断，而停止回答问题的机器人会在几秒内被报告。一个断开连接的链接会立即被报告，而不是等待它断开。在应用后，它会说明这一点：断开连接是由于重启造成的。在飞行中的更新会继续执行：机器人会继续执行，没有人关注，之后 `update status` 命令会显示更新的结果。

## 被拒绝的内容

`teleop`（`robot.move`, `robot.head`, `robot.enable`, `robot.stop`, `robot.init`, `robot.relax`），高频率的遥测数据（`robot.subscribe`），两个需要明确操作的更新命令（`update.pin`, `update.resetToGolden`）以及配对PIN（`system.pairingPin`, `system.setPairingPin`）都会被 `btd` 自身拒绝，这些命令永远不会到达守护进程。

`robot.do` 并不在这个列表中，尽管它可以移动机器人：`teleop` 是每秒五十次的小更新流，这超出了 20 字节的通知预算，而一个技能只是一次请求。它们会返回错误代码 14，“不可以通过蓝牙提供”。
那是一个安全边界而非缺失的功能，并且每次拒绝都有其原因紧挨在 `btd/src/route.rs` 中 —— [`app-path-design.md`](../design/app-path-design_zh.md) §3.1 是设计说明。
这些命令是机器人上的 `robotctl`。

## 当无法找到机器人时
```bash
duckctl --verbose scan
```
An 空列表 — 并没有一对耳塞 — 指向 Mac 而不是机器人：Bluetooth 关闭，
或者终端从未授予 Bluetooth 权限。

缺少机器人项的列表指向机器人。它在扫描响应中宣传其名称，但可能单独被忽略，因此一个报告无名称且无服务的设备可能是机器人；`--name` 仍然可以连接到它。如果 macOS 显示机器人已配对但连接或第一次读取挂起，那么连接是半完成的：
```bash
sudo pkill bluetoothd
```
Forgetting 机器人 在 macOS 蓝牙设置中同样可以实现相同的功能。在机器人本身上，
`journalctl -u btd -b` 可以说明 GATT 应用程序是否注册过。
