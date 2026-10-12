# 重启的内容和时机

每条路径移动 `current` 符号链接以及启动时的权威顺序。因为“哪个守护进程重启了，以及在什么时间”这个问题在不同文档中被回答了三种不同的方式，而答案决定了如何诊断偏移。

这里的所有内容都是从代码中读取的，每一步都指明了负责它的函数。如果其他地方的叙述性注释与此页面不符，那么注释就是错误的。

## 1. 七个守护进程和一个不是

每次发布都会包含七个守护进程——`robotd`、`configd`、`btd`、`padd`、`mediad`、`tofd`、`updaterd`——每个守护进程的 `ExecStart` 指向 `/opt/robot/daemon/current/bin/` 下的一个路径，因此每个守护进程在符号链接移动的瞬间都会变得过时，每个守护进程要么由更新重启，要么在更新之后重启。

它还包含 `robot-boot-check.service`，这 **不是** 其中之一，并且更新绝不能重启它：它会询问启动的发行版是否成功启动，如果没有成功则将控制权交给 `robot-rescue`，因此在更新过程中运行它会将回滚检查指向正在合法重启的守护进程。它没有 `[Install]` 部分，正是这一点将其排除在外——参见 §1.1。
| 单位 | 中途更新时重启 | 回复后约5秒后重启 |
|---|---|---|
| `robotd` | 是 | — |
| `configd` | 是 | — |
| `padd` | 是 | — |
| `mediad` | 是 | — |
| `tofd` | 是 | — |
| `updaterd` | **从未** — 它是执行更新的进程 | 是 |
| `btd` | **从未** — 它可能是更新到达的传输方式 | 是 |

两部分是一个决定，并且一个测试（`every_unit_held_back_is_restarted_once_the_answer_is_out`）断言`engine.rs`中的两个列表是相同的集合：`NEVER_RESTART` 和 `RESTART_AFTER_REPLYING`。

没有单位在重启前被保留。在`RESTART_AFTER_REPLYING`存在之前就是如此，这也是关于此系统的最常见的过时说法。

并且因为调度重启并不意味着重启发生，所以在下一个`updaterd`启动时会检查每个单位的状态与当前版本，并重启任何过时的单位 — §5。

### 1.1 什么算作更新开始时的单位

带有 `[Install]` 部分的 `systemd/*.service` 文件。没有 `[Install]` 部分的单位由其他因素触发 — 一个定时器，或另一个单位的依赖 — 因此其生命周期不由更新驱动，`engine.rs::has_install_section` 是决定这一点的地方。
要求而不是一长串名称，因为已经有两个地方在应用这个规则并且意见不一：`hooks/postinstall` 拒绝在没有 `[Install]` 的单元上使用 `enable --now`，直接用字面意思拒绝了——*“在安装它时在中间运行回滚检查，合法的守护进程正处于重启中”*——而引擎则在稍后的一刻重新启动了每一个 `*.service`。基于部分，两者通过构造达成一致，下一个类似的单元不需要任何人记住。

无法阅读的单元文件也算一个需要重启的。这更可能是权限问题而不是故意不触发的单元，公开失败的重启比默默跳过要好。

### 集合是如何计算的

两个集合，相差一个函数。`engine.rs::units_shipped` 包含一切发布的单元：
```
(the release's own systemd/*.service stems)  ∪  (on_apply.units from /etc/robot/updater.toml)
```
排序并去重。`engine.rs::units_to_restart` 是那个内容，减去 `NEVER_RESTART`：
```
units_shipped(…)  −  {updaterd, btd}
```
An update重启`units_to_restart`；启动检查在§5中读作`units_shipped`，因为两个更新无法触及的单元正是它存在的目的要监控的两个单元。

今天发布的`units_to_restart`正好是：
```
configd, mediad, padd, robotd, tofd
```
在字母顺序中——即按字母顺序排列，因此每块电路板和每次测试中的顺序都相同。`deploy/updater.toml` 中没有任何内容添加到列表中以包含 `mediad` 和 `tofd`，也无需添加：两者都随附了一个带有 `[Install]` 部分的单元，这就是全部规则。

从发布的版本派生出它而不是从电路板派生出的两个后果：

- 即使 `deploy/updater.toml` 中从未提及 `padd`，它也会被重启。配置列表是 **累加的**，而不是权威性的；它只需命名发布的版本中不随附的单元。
- 一个其 `updater.toml` 文件早于守护程序的电路板仍然会重启该守护程序。该文件属于操作员，`install.sh` 会保留它，这就是 `configd` 有一段时间未被重启的原因（`../project/install-path-gap.md` §4）。

每个单元都是通过其自身的 `systemctl restart <unit>` 调用重启的，从不批量重启——一个 `systemctl restart a b` 命令在任一单元未知时会整体失败，**不会**重启存在的那个单元。systemd 报告为 `LoadState=not-found` 的单元会被带有警告的消息跳过；一个存在的单元如果重启失败，则会 **导致更新失败并回滚**。

## 2. `robotctl update apply` / `update.apply` 通过蓝牙执行
`engine.rs::apply` → `apply_inner` → `stage_and_swap` → `post_swap`。在第8步之前没有任何操作会触碰活路径。

| # | 步骤 | 重启了任何东西吗？ |
|---|---|---|
| 1 | 预检：时钟，机器人停止，无活会话 | 否 |
| 2 | 获取清单，验证其签名，通道/固定/降级/兼容性检查 | 否 |
| 3 | 再次预检，这次是磁盘空间（要求来自清单） | 否 |
| 4 | 下载到 `releases/.staging-<ver>/dl/` | 否 |
| 5 | 验证 sha256，然后验证文件签名 | 否 |
| 6 | 解压到 `releases/.staging-<ver>/root/`，写入 `.updater-manifest.json` | 否 |
| 7 | **`hooks/preinstall`**（当前工作目录 = 打包的树）——如果低于门槛则安装 ONNX 运行时，然后运行发布版的 `scripts/setup-gstreamer.sh` 以为 `mediad` 的堆栈做准备 | 否 |
**钩子脚本来自传入的版本发布，而运行它的代码则不是。** `updaterd` 在更新过程中从不自行重启（§1），因此表中的每一步都由已经运行的 `updaterd` 执行——即上一个版本的 `updaterd`。因此，对钩子脚本运行、日志记录或限制方式的任何更改将在 `updaterd` 重启到携带这些更改的版本后的一个应用时生效。这曾经导致过一次困惑的“钩子运行但未记录任何内容”的循环；`cat /run/updaterd/identity.json` 是告诉你即将运行你的钩子的是哪个构建。
| 8 | `rename`已提交的树到`releases/<ver>/` | 无 |
| 9 | 在交换之前，对启动计数器(`pending.json`)进行武装 | 无 |
| 10 | 交换 `current` → `releases/<ver>` | 无 |
| 11 | **`hooks/postinstall`** (当前目录 = `releases/<ver>`) | **启动新发布的单元** |
| 12 | `on_apply` — 依次重启§1中的每个服务单元 | **configd, mediad, padd, robotd, tofd** |
| 13 | `releases/<ver>/bin/updaterd --self-test` | 无 |
| 14 | 健康门：每500毫秒通过其套接字轮询`robotd`，最多30秒 | 无 |
| 15 | 确认启动计数器，修剪旧版本 | 无 |
| 16 | 释放更新锁，安排延迟重启 | **安排updaterd, btd的重启** |
| 17 | 回复发送到`robotctl` / 应用程序 | — |
| 18 | 自第16步后约5秒 | **updaterd, btd** |

任何从第11步开始的失败都会回滚：交换 `current` 回去，重新运行 `on_apply` 对于之前的版本，确认启动计数器，记录日志。第1到10步失败时，旧版本仍然存活且没有可撤销的操作。
**第2步也可能结束操作，并不一定非要重启任何东西。**如果清单指明了已安装的版本，操作会在该处停止并报告 `already_current` — 没有下载任何内容，也没有进行任何切换。在回复之前，它会重新检查该版本的单元和 `stale` 中正在运行的任何内容，并将这些内容按步骤16-18中安排的延迟对进行调度。因此，对于一个已更新的机器人，`apply` 是无作用的；而对于一个其守护进程与已安装内容不一致的机器人，`apply` 则不是无作用的。对于一个板子上已激活的版本，`select` 也会做同样的事情，原因相同。

### 详细说明第11步 — `hooks/postinstall`

钩子包含在签名的文件中，并以发布目录作为其当前工作目录（cwd）。按顺序：
1. 将每份 `systemd/sysusers.d/*.conf` 安装到 `/usr/lib/sysusers.d/`，然后运行 `systemd-sysusers`。账号在单位之前安装，因为命名了缺失 `User=` 的单位将无法启动，并被视为一个损坏的服务。
2. 将每份 `systemd/*.service` 安装到 `/etc/systemd/system/`，覆盖原有文件。**所有文件**，包括 `updaterd.service` 和 `btd.service` —— 此挂钩没有排除列表，也不需要。
3. 运行 `systemctl daemon-reload`。
4. 对于每个具有 `[Install]` 部分的单位（§1.1），运行 `systemctl enable --now`；没有此部分的单位将被安装并留置，而 `.timer` 单位在不带 `--now` 的情况下启用。

第 4 步就是为什么 §1 中的排除仍然适用的原因：`--now` 表示 *启动*，而启动一个已经运行的单位是一个无效操作。它不会重启 `updaterd` 或 `btd`。它所做的就是启动一个板子从未有过的单位——这就是此挂钩的全部意义所在，意味着 **一个新引入的服务在引入它的发行版中会启动两次**：一次在这里，另一次在第 12 步。
- 转换的全文要忠实原文。不要省略或添加内容。
每次 hook 内的失败都是警告，除了单元或 sysusers 文件的 `install` 失败，这会以非零状态退出并因此回滚更新。服务无法启动并不致命：`btd` 在无线电尚未出现的板卡上合法地失败。

### 第 13 步 — 自检

`updaterd` 在更新过程中不会重新启动自身，因此一个无法启动的替换二进制文件将在下次启动、提交后被 process 失败时发现，此时恢复功能将嵌入在失败的进程中。相反，新的 `bin/updaterd` 会通过 `--self-test` 运行：它加载 `/etc/robot/updater.toml`，构建引擎，然后在不触碰任何状态的情况下退出。10 秒时间限制。

失败会携带 `Error::SelfTest` 并附带二进制文件的最后一条 stderr，从而回滚。没有 `bin/updaterd`（一个模型组件）的版本会通过。除非 `on_apply` 是重启，否则它会完全跳过，这正是它避开 bootstrap 安装的原因。

### 第 16–18 步 — 延迟重启

`engine.rs::schedule_deferred_restarts`，然后是 `updaterd` 和 `btd`：
```
systemd-run --on-active=5s --timer-property=AccuracySec=100ms -- systemctl restart <unit>
```
承载负荷的四个细节：
- **一个瞬态单元，不是子进程。** `systemctl restart updaterd` 会杀死 `updaterd` 的整个 cgroup，而 `updaterd` 的一个子进程 *在* 这个 cgroup 内 —— 它会在重启自己的父进程过程中被中途杀死。一个 `systemd-run` 定时器则生活在它的外部。
- **更新锁会首先被释放**（步骤 16，之前是 fork）。fork 会复制每一个打开的描述符，因此在持有锁的情况下启动子进程会将一个副本交给子进程。
- **在 `Applied` 和 `already_current` 且单位过时的情况下** —— `engine.rs::restarts_owed` 决定了哪一种情况，而且只有它决定了这一点。前者欠下固定的那对重启；后者欠下 §2 发现正在运行错误版本的那部分，通常是 `updaterd` 本身。回滚不欠下任何东西：它会留下驻留的 `updaterd` 已经匹配 `current`，因此从那里重启只会造成无谓的变动而没有需要解决的问题。
- **每个单元都会经过定时器**，包括那些在步骤 12 中会被更新原地重启的单元。为 `configd` 和 `robotd` 提供一个额外的、立即的路径可以节省五秒时间，但会增加一个机制的成本。
- **失败会被记录，从不返回错误。** 一次成功的更新不会被报告为失败，因为
  重启无法安排；这带来的代价是一个在旧二进制上运行的守护进程，直到下次启动。

定时器在回复被写入之前被安排（引擎运行在 `update.apply` 调用内部），
因此这 5 秒是从步骤 16 开始测量的，而不是从客户端看到答案时开始。客户端看到其结果，然后连接中断——对于 BLE，这是一个普通的重新连接。

### 重启后的 `updaterd` 做什么

这是一个正常的启动，因此它会完整地运行 §4 的启动序列：`clean_staging`，`record_boot`，以及 §5 的重合——这是捕捉未发生 `btd` 重启的地方——然后提供服务。有两件事情很容易被忽略：

- **启动计数器计算 `updaterd` 的启动次数，而不是实际的启动次数。** 成功的应用在步骤 15 确认了自己的尝试，所以没有待处理的任务可以推进——但是由较早中断的更新遗留下来的尝试会被这次重启推进。
- **周期性检查时钟重置。** `INITIAL_CHECK_DELAY` 从进程启动开始为 60 秒，`check_interval` 从那里开始计数。

## 3. 其他转换
`select`，`rollback` 和 `reset-to-golden` 共享 `engine.rs::transition_to`：分支，交换，`on_apply`，健康门限，失败时回滚。它们 **不** 运行挂钩，**也不** 自我测试——没有提取任何文件，因此没有新的内容需要安装或验证。

| | 挂钩 | `on_apply` (§1) | 自我测试 | 延迟更新器d/btd重启 |
|---|---|---|---|---|
| `update apply` | 是 | 是 | 是 | **是** |
| `update select <ver>` | 否 | 是 | 否 | **是** |
| `update rollback` | 否 | 是 | 否 | **否** |
| `update reset-to-golden` | 否 | 是 | 否 | **否** |
| 失败应用中的自动回滚 | 否 | 是 | 否 | **否** |
| 启动时的 boot-counter 回滚 | 否 | 是 | 否 | **否** |

底部的两个 `否` 是正确的：在失败的应用和 boot-counter 回滚中，`updaterd` 和 `btd` 从未重启，因此它们仍然是返回的发行版所属的二进制文件。
The `no` 对于显式的 `rollback` / `reset-to-golden` 是一个不同的情况，值得了解：
如果之前某个时间点该发布被成功应用，`updaterd` 和 `btd` *确实*
重启到了该发布点，显式的回退会留下它们在那个点。`robotd`、`configd` 和 `padd` 会回退；这两个则保持 **领先** 于当前活动的发布。

这会在下一个 `updaterd` 启动时自行解决，而不是在重启时：§5 从两个方向进行比较，因此 `btd` 运行一个比 `current` 更新的发布被认为是过时的，并被重启。`updaterd` 是唯一一个设计上不会自我修复的进程。

由于 `select` 和回退跳过了 `hooks/postinstall`，它们也不会 *移除* 单元文件。降级到一个比守护进程更早的发布会留下该守护进程的单元文件，指向一个该较旧发布不包含的二进制文件；该单元会失败，并且由于它在重启集中，失败的重启会失败过渡（`../project/install-path-gap.md`）。

## 4. 启动时

systemd 从 `multi-user.target` 启动守护进程，并且 `robot-boot-check.timer` 在 180 秒后启动恢复检查。**没有对这些守护进程之间的启动顺序进行排序**，仅在 `robotd` 之后 `padd`（建议 — `padd` 每 5 秒退出并重试，如果套接字不存在），`dbus`/`bluetooth` 之后 `btd`。没有任何服务等待 `updaterd`，而 `updaterd` 也不等待任何服务，仅等待 `network-online.target`，后者是 `Wants` 而不是 `Requires`。

在该板卡上，`hci0` 在通电后大约 73 秒后才存在，因此 `btd` 会重试以获取适配器而不是失败。

`updaterd` 的启动过程如下（按顺序 `main.rs::serve`）：
1. 在 `warn` 级别记录启动标识行 — 版本、修订号，**`exe`路径**，pid。`exe`路径告诉你进程实际来自哪个发布目录。
2. 加载 `/etc/robot/updater.toml` 和可信密钥。任何一种加载失败都是致命的。
3. 构造引擎。
4. `--self-test` 在任何状态被触碰之前返回这里。
5. `Engine::recover_on_start`，**在服务套接字之前**，因此一个启动到错误发布版本的机器人在任何其他请求它做事之前就已经开始恢复：
   - `clean_staging` 对于每个组件：删除 `releases/.staging-*`。
   - `record_rescue`：如果 `<state_dir>/rescued` 存在，启动恢复网络在没有任何运行时已经将 `current` 切换到黄金版本。将它复制到更新日志中作为回滚，**清除该组件的试验**，并删除该文件。故意在 `record_boot` 之前执行：救援已经比试验走得更远，而一个留有武装的试验会在几次启动后将 `current` 重新移回黄金版本。删除该文件也是释放救援循环保护的手段。
   - `refresh_golden_links`: 发布每个组件配置的“golden”链接为一个`golden`符号链接在`current`旁边，这样救援可以在使用一次`readlink`命令时找到它，而无需解析器。
   - `record_boot`: 在每次启动成功的试验记录中增加`boots`计数器，记录在`pending.json`中。
   - 对于每个`boots >= 2`（`MAX_BOOT_ATTEMPTS`）的试验：回退到`previous`，当`previous`不存在、缺失或自身被记录为回滚时，升级到`golden`。这意味着交换符号链接、确认试验并重新运行`on_apply`——**因此回退重启会重新启动`configd`、`padd`和`robotd`。**它不运行任何挂钩且不安排任何任务，因此`updaterd`和`btd`系统启动的进程将从被放弃的版本中继续运行。第6步随后会捕获`btd`，因为它在之后运行并与回退激活的版本进行比较；`updaterd`被记录并保留，直到下次启动才会过时。
   - 记录结果。如果在此处失败，将进行记录并继续服务：拒绝服务会移除修复它的唯一途径。
6. `Engine::reconcile_running_units` — §5. **在恢复之后**，因为恢复可能会改变哪些单元正在运行。
   release 是活动的，并且在之前的一个单元会与机器人正在放弃中的版本进行比较。这一步可以重启单元。
7. `--check-only` 返回这里。请注意，它 *执行* 了第 6 步的恢复和重聚操作 — 它是一个操作工具，而不是探测器，并且它可以回滚发布并重启守护进程。
8. 提供 `/run/updaterd.sock`。
9. 如果设置了 `check_interval`，则启动调度器：首次在启动后 60 秒，然后每隔一个间隔。`auto_apply` 决定在没有客户端连接时它可以安装什么。

只有在第 2 节的第 9 步和第 15 步之间被打断的应用尝试才存在 — 例如，断电、`kill -9` 或在交换之后取消的 RPC。一个已提交的更新不会留下任何武装状态。由于 `exhausted` 是 `boots >= 2` 而 `arm` 写入 `boots = 0`，因此在中断后的 *第一次* `updaterd` 启动时会记录 "更新仍在试验中"，而在 *第二次* 启动时会回滚。
**每一步都假设存在一个`updaterd`并启动。**在没有其他步骤运行的情况下，还会发生一件事：`robot-boot-check.timer`在180秒后触发，询问`robotd`、`configd`、`btd`和`updaterd`是否启动，并将控制权交给一个`/bin/sh`救援模式，如果它们没有启动，则将`current`切换为金色版本并重启。它故意不在本页面的任何进程中——[`boot-recovery-net.md`](boot-recovery-net_zh.md)拥有它，包括为什么它是一个截止日期而不是这些单元的`OnFailure=`。

## 5. 启动校正——重启是否发生？

`systemd-run`返回成功意味着创建了一个临时计时器。但这并不意味着重启运行了，也不意味着新的二进制文件启动了；第2步的第16步故意吞下了这些失败。这留下了一种无声的方式，使得机器人运行了一个它没有安装的版本，并且它落在了没有任何其他单元监视的两个单元上。`updater/src/reconcile.rs`关闭了它。

### 它读取的内容

每个守护进程在启动时都会发布自己的身份——`duck_ipc_proto::publish_identity`，每个守护进程打开时都会从`log_startup_identity!`宏调用：
```
/run/<service>/identity.json    { service, version, revision, built_at, exe, pid }
```
The `exe` 字段来自 `/proc/self/exe`，因此它通过 `current` 符号链接解析，并命名了实际启动该进程的发布目录。`Identity::release()` 从中解析出 `releases/<ver>` 组件。

自我发布而不是从外部读取：一个进程知道自己的版本和修订版本，并且可以无需特权读取自己的 `exe`，而读取其他用户的则需要 root 权限。每个单元中的 `RuntimeDirectory=<service>` 创建一个由该单元的 `User=` 拥有的目录，并且在 `ProtectSystem=strict` 下存活，当单元停止时，由 systemd 删除 —— 因此一个停止的服务不会留下一个声称正在运行的身份声明。

### 它所决定的内容

对于每个 `units_shipped`（§1）中的单元，按组件进行比较，将发布的发布版本与组件的当前发布版本进行对比。`verdict_for` 是一个纯函数；所有的系统调用都保持在其外部。
| 判决 | 当时 | 行动 |
|---|---|---|
| `Current` | 发布版本 == 当前版本 | 无操作，静默 |
| `Restarted` | 两者不同 | `systemctl restart <unit>`，在 `warn` 级别 |
| `ReportedOnly` | 两者不同 **且 单元是 `updaterd`** | 记录日志，从不采取行动 |
| `RestartFailed` | 重启尝试失败 | 在 `error` 级别记录日志 |
| `Unknown` | 无身份文件 | 无操作 |
- **`updaterd`从不在此重启自身。**如果一个后继者认为当前活动的版本有争议，它会重启，再次产生分歧，并陷入循环——在拥有恢复功能的单一进程中，没有其他进程可以打破这个循环。因此，可以安全地报告：该进程刚刚启动，任何过时的信息都是在本代码运行之前决定的。它从另一侧得到修复——请参见下方。
- **停止的单元保持停止状态。**没有身份文件意味着要么停止，要么太旧而无法发布，两者在这里读取结果相同。启动它会在每次`updaterd`启动时覆盖之前停止它的任何人。
- **发布过任何内容的守护进程不会被视为过时。**为旧守护进程重启机器人是一个没有人要求的决定；下一次更新会让他们能够做出回应。

比较是方向无关的——任何差异都是过时的——这就是它能够覆盖一个通过显式回滚而领先于`current`版本的发布，而不仅仅是落后于它的发布。

它在每次`updaterd`启动时运行，因此在启动时它是无效操作：一切从同一个符号链接启动。成本是每个单元读取一个文件。

### 同样的读取，来自`apply`
`reconcile::stale_units` 是 `verdict_for` 对同一身份文件的过时单元进行处理，其中过时的单元不包括当前活动的单元，而 `apply` 和 `select` 会在它们已经是最新的路径上调用它（§2）。它的存在是因为上述的例外情况：一个过时的 `updaterd` 是这个模块拒绝修复的唯一例外，而唯一会查看它的就是运行 `apply` 的人，因为某个守护进程似乎出了问题。过去，它会回答 `already_current` 并调度什么都不做，这被解读为确认没有需要修复的内容。

两个特性让它避免成为 §5 防止的循环。它是在接收到请求时触发，而不是每次启动时触发，并且它通过 `systemd-run` 调度，而不是从正在重启的进程中驱动 `systemctl`。它不仅报告还采取行动：在 `already_current` 的结果中列出了这些单元的名称，因此客户端 —— `robotctl` 或应用程序 —— 可以看到哪些守护进程没有运行安装的机器人所对应的版本。
Both stale 判决都算作 stale (`Restarted` 和 `ReportedOnly`); 两者之间的区别在于谁可以执行重启，而不是有什么问题。表格中的其他内容没有变化：一个停止的单元和服务端没有发布任何内容仍然不算 stale。

## 6. 首次安装

在裸板上按顺序运行 `scripts/install.sh` (`main`):
1. 编写 `/etc/robot/updater.toml` 和受信任的密钥。
2. `bootstrap_first_release`: 获取独立的 `updaterd` 可执行文件并运行 `updaterd install [--from <dir>]`。这相当于 `Engine::apply` 但有两个设置被强制执行，因为在没有发布版本的板子上，它们是事实而不是策略：`on_apply = none`（单位位于正在安装的发布版本内部）和 `health = none`（没有 `robotd` 可以探测）。因此 §2 运行时会跳过步骤 12、13 和 14 — 但 **步骤 11 仍然运行**，`hooks/postinstall` 安装了这些单位并使用 `[Install]` 部分的 `enable --now` 启动它们。启动守护进程也从钩子内部开始。步骤 16 也不会被跳过：`updaterd` 和 `btd` 的重启被安排在 `install.sh` 仍在运行的 5 秒后。
3. `install_units`: 再次复制单位，`daemon-reload`，然后依次启用 `updaterd`、`robotd`、`configd`、`btd`、`padd`、`mediad` — `configd` 位于 `btd` 之前，因为 `btd` 会向 `configd` 请求配对 PIN，而 `mediad` 最后，因为其单位的 `After=` 依赖于三个
   其他。`btd`、`padd` 和 `mediad` 可能会失败而不影响安装：没有无线电、没有游戏手柄或没有摄像头的机器人仍然会更新和行走。然后 `robot-boot-check.timer` 会在没有 `--now` 的情况下启用。这与钩子冗余且无害；这也是比钩子更早版本的发布路径。一个在发布中包含而此函数不知晓的单元，会被报告并被忽略。`tofd` 被命名为已知的，但没有自己的 `enable_unit`：钩子在更早的步骤中已将其启用，且没有其他依赖，因此此函数没有对其排序发表意见的必要。
4. `install_token_dropin`：写入 `GITHUB_TOKEN` 插件，`daemon-reload`，以及 `systemctl try-restart updaterd` — 仅 `daemon-reload` 会使正在运行的 `updaterd` 失去令牌，这在每个板上都是必要的。

`DUCK_FORCE_REINSTALL=1` 在步骤 2 前添加 `stop_for_reinstall`：按顺序对 `padd`、`tofd`、`btd`、`configd`、`robotd` 和 `updaterd` 执行 `systemctl stop`。在此交换过程中，没有内容处于活动状态，且其后没有健康检查门。

## 7. 诊断偏移

两个版本号可以同时合法地不同，而哪一对决定了诊断结果。
| 观察 | 含义 |
|---|---|
| 更新后的安装版本后方出现 `updaterd` 或 `btd`，持续几秒钟 | 正常 —— 延迟重启尚未触发 |
| `btd`、`robotd`、`configd`、`padd`、`mediad` 或 `tofd` 与 `current` 不一致，且持续存在 | 重启未生效 *且* 第5条未解决问题 —— 因此，可能是 `updaterd` 自从上次更新以来未重启，或者其重启失败（日志中显示 `error`） |
| `updaterd` 持续滞后 | 延迟重启从未触发，第5条也无法解决问题。`robotctl update apply daemon` 可修复此问题 —— 它会报告 `already_current` 并将 `updaterd` 置为 `stale`，并安排重启。手动执行 `systemctl restart updaterd` 也有相同效果；无论哪种方式，日志中会显示未触发的原因 |
| 任何报告 `restarting` 的守护进程 | 守护进程已退出，systemd 正在重新启动它。更新后的几秒钟内，这是重启本身。持续存在时，守护进程无法启动 —— `mediad` 与摄像头柔性线未连接的情况即为此例 —— 第5条不会对此进行处理，因为未运行的守护进程没有可供比较的身份。`journalctl -u <name> -b` 可显示其退出的原因 |
| 任何报告为 `failed` 的守护进程 | 它无法启动，systemd 已停止重试。同一条目日志，与 `stopped` 不同，没有人选择它 |
| 任何报告为 `build unknown` 的守护进程 | 它正在运行，并未发布身份信息：可能是早期版本的构建，或在 `exec` 和其第一条目之间的瞬间。§5 不处理这种情况。一次更新可以使旧版本变得可回答 |
```bash
robotctl health
```
The `units` 块按每个守护进程打印一行，显示其进程启动的版本，并警告当这与安装的版本不符时。

手动获取与守护进程发布的文件相同的结果：
```bash
cat /run/configd/identity.json; readlink /opt/robot/daemon/current
```
