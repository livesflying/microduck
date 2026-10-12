# 软件开发手册 — 开发板

仅在由
[`install-dev.md`](install-dev_zh.md) 安装的开发板上才有意义的命令。机器人日常所需的一切都在
[`cheatsheet.md`](cheatsheet_zh.md) 中。

## 开发频道

安装 CI 最后构建的分支所安装的内容：
Install what a branch last built on CI:
```
sudo robotctl update apply --ref <branch> daemon
```

```
sudo robotctl update apply --ref main daemon
```
`--version` 会固定到一个确切的版本。除非你确实想要“去稳定版”，否则就使用其中一个。

**`apply daemon` 未指定 `--ref` 安装的是最新 *稳定版* 发行版，在开发板上通常是降级。** 它并不是“安装最新版本”；而是“安装稳定渠道提供的版本”。在分支合并后，那个稳定版发行版仍然比你一直在测试的版本要旧——而且如果它早于现在在板上有单元文件的守护进程，它的 `ExecStart` 指向了一个较旧版本的守护进程不包含的二进制文件，重启失败，更新回滚。这是闸门在起作用，但触发它的命令看起来像是显而易见的命令。

标签 `daemon-dev-<branch>` 会随着分支移动，因此没有版本号需要复制。内部的版本 *始终* 每次构建都唯一——`0.1.0-dev.42.c719ec8`——所以同一个分支的两次构建不会混淆。`--ref main` 是开发板回到主线而不离开开发渠道的方法；而单纯的 `apply daemon` 会离开，因为预发布版会排在正式版之下，且没有单独的退出步骤。

合并不会立即发布：CI 必须先构建 `main`，`--ref main` 才会解析为它。
```
gh run list --branch main
```
## 释出候选版本

`release.yml` 发布到 staging 环境且尚未有人进行推广的内容——在推广之前，canary 机器人应该运行的内容：
```
sudo robotctl update apply --staging daemon
```

```
sudo robotctl update apply --staging --version 0.3.0 daemon
```
一个候选者使用发布密钥签署，就像任何发布一样，并携带它将要发布的版本。使其在没有标志的情况下不可达的是它被标记为预发布版本，而普通的 `apply` 会跳过这些，因此没有机器人会误入未经验证的构建。`--staging` 是这个过滤器的唯一选项，它仅应用于该命令，并且之后不会开启任何功能。

## 更新之后 — 令人头疼的部分

- **`robotd`、`configd` 和 `padd` 在更新期间重启。`updaterd` 和 `btd` 在它回复后 5 秒重启** — 第一个不能在更新中重启自己，而第二个可能正在携带回复。因此，一个 `btd` 的修复会在几秒钟后生效，无需手动操作。重新连接后，它就会在那里。
- **如果这两个重启中的任何一个没有发生，下一个 `updaterd` 启动会修复它。** 除了 `updaterd` 本身，它会报告分歧而不是重启自己。再次运行应用以解决这个问题：它会回答 `already_current`，命名未运行该命令的守护进程，并安排重启。手动执行 `sudo systemctl restart updaterd` 也能做到同样的事情。
- **运行 `updaterd` 早于 0.4.0 的板卡没有这些功能**，并且会一直停留在旧二进制文件上，直到你重启它们。一次更新可以解决这个问题，只有在那之后的行为才符合预期。
- **如果你请求一个板卡已经有的版本，`robotctl update apply` 会报告 `already_current` 并安装 nothing** — 但这不再是惰性的。它会检查哪些守护进程正在运行该版本，并重启那些未运行的守护进程，将它们命名为 `stale`。因此，它确实是当你发现修复缺失时应该使用的命令：要么它会解决问题，要么 `stale` 为空且该修复从未包含在该版本中。

症状是一个已安装且肯定不起作用的修复。询问每个守护进程正在运行的版本：
```
robotctl health
```
The `units` 块每行打印一个守护进程及其进程启动的发行版信息，并在发行版信息与已安装的不符时发出警告。`build unknown` 表示该守护进程正在运行且未发布身份标识 —— 通常是旧版本；重启它即可。`restarting` 表示该守护进程已退出且systemd正在将其恢复：在更新后几秒内是正常的，如果守护进程一直保持这种状态则无法启动。

如果守护进程确实过时，可以重启它 —— 这通常不需要，因此值得查看 journal 以了解为何会这样：
```
sudo systemctl restart configd
```
`updaterd` 自身永远无法修复：
```
sudo systemctl restart updaterd
```
编辑板卡的 `updater.toml` 并不需要 — 重启顺序来自发布的单元。`../design/restart-order.md` 是完整的步骤序列。

## 从笔记本电脑操作 — 在这里构建，安装到板卡上

完全跳过 CI：在你的机器上构建并通过 ssh 安装，大约只需一分钟。
```bash
scripts/dev-push.sh radxa@<board>
```
The 结果是一个普通的门控更新，因此上述重启陷阱仍然适用。
[`dev-push.md`](dev-push_zh.md) 包含设置、容器构建、`--dry-run`、首次推送至一个低于0.5.0的板子，以及推送失败时应采取的措施。

## 从笔记本电脑 — 一手拿着平板

一手拿着平板，工作台上有一台机器人，两者均未安装任何软件：`padd` 是一个普通的客户端，因此可以从克隆的代码中运行，并针对转发的套接字进行操作。

首先停止机器人上的那个进程，否则两个进程会争夺控制权：
```bash
sudo systemctl stop padd
```
转发套接字并保持打开状态：
```bash
ssh -L /tmp/robotd.sock:/run/robotd.sock radxa@192.168.1.42
```
然后在另一个终端中从这个克隆目录操作：
```bash
cargo run -p padd -- --socket /tmp/robotd.sock
```
`systemctl start padd` 启动机器人的自身回退功能。这也是 `padd` 的标志值得拥有之处 —— `--max-linear`（m/s），`--max-angular`（rad/s），`--max-head`（弧度）和 `--deadzone`，因为没有它，类比摇杆很少会恰好停留在零，从而导致机器人无意识移动。系统默认运行这些设置，因此尝试其他值意味着你需要自己运行二进制文件，这里或在板子上：
```bash
sudo -u padd /opt/robot/daemon/current/bin/padd --max-linear 0.25
```
## 从笔记本电脑 — `duckctl`

通过蓝牙LE连接机器人，没有网络也没有ssh：
[`duckctl.md`](duckctl_zh.md) 中包含了所有命令。
