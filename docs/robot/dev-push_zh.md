# 在这里构建，安装到板子上

从修改一行代码到观察机器人运行它之间的循环，无需推送、无需 CI 运行和无需打标签。从这个仓库的一个克隆版本中运行一个命令即可为板子构建、签名结果并通过 ssh 安装它——增量构建大约需要一分钟，推送时则需要加上 CI 运行，大约需要几分钟。

`scripts/dev-push.sh` 就是那个命令。以下内容都是该命令的参数。

## 一次，首次推送之前

三件事，之后就不再需要了。

**板子必须是开发板。** 构建产物会使用团队开发密钥签名，因此客户机器人会拒绝它，就像它会拒绝 `--ref` 一样。[`install-dev.md`](install-dev_zh.md) 介绍了如何将板子变成开发板。

**开发签名密钥** 放在 `~/.duck-keys/team.dev.key` — 这是 CI 签名分支构建的密钥的私钥部分，团队成员拥有它。如果该密钥存放在其他位置，请设置 `DUCK_DEV_SECRET_KEY`。

**可以为板子构建的工具链。** 可以安装交叉编译器：
```bash
cargo install cargo-zigbuild --locked
```

```bash
brew install zig
```
- 安装 nothing，并在每个 `dev-push.sh` 下面加上 `--docker`，这只需要运行一个 Docker 服务。这条路启动较慢，是你在没有任何开发板的情况下应该选择的路径——参见 [在容器中构建](#build-in-a-container-instead)。

## 循环

给机器人命名，并让推送找到它：
```bash
scripts/dev-push.sh --name duck-c51b
```
Or 每次在一个shell中：
```bash
export DUCK_ROBOT=duck-c51b
```

```bash
scripts/dev-push.sh
```
The name is the one `duckctl scan` 列出和 `robotctl system set-name` 设置的 — 同样是 `duckctl.md` 中所述的 `[DUCK_ROBOT]` 工具读取的名称。它的地址通过蓝牙请求 — 该机器人的 `net.status` 回复它 — 然后缓存起来，因此只有当推送无法到达缓存地址时才会回到无线电。这会触发一个新的 DHCP 租约、重新刷写或不同的网络无需任何成本。

SSH 用户是 `radxa`。如果你的不是：
```bash
export DUCK_BOARD_USER=pierre
```
地址仍然有效，并且会完全跳过无线电：
```bash
scripts/dev-push.sh radxa@192.168.1.42
```

```bash
export DUCK_BOARD=radxa@192.168.1.42
```
It 在交叉编译工作区后，生成与发布相同的构建包，使用 dev 密钥对其进行签名，将其复制到板上的 `~/duck-sideload`，然后通过 `robotctl update apply --from` 应用该构建包。然后它会等待守护进程报告新的发布：
```
==> building 0.5.1-dev.local.1763400000.g7fc1444 for the board (zigbuild)
==> packaging
==> signing with /Users/you/.duck-keys/team.dev.key
==> copying to radxa@192.168.1.42:/home/radxa/duck-sideload
==> applying on radxa@192.168.1.42
==> 0.5.1-dev.local.1763400000.g7fc1444 is live on radxa@192.168.1.42
==> checking every daemon is running it
    current -> 0.5.1-dev.local.1763400000.g7fc1444
    [ok] robotd
    [ok] configd
    [ok] padd
    [ok] updaterd
    [ok] btd
    [ok] mediad
    [ok] tofd
==> every daemon on radxa@192.168.1.42 is running 0.5.1-dev.local.1763400000.g7fc1444
```
`updaterd` 和 `btd` 在应用回复后五秒重新启动，因此这两行信息需要稍等片刻。`[--] padd 发布了 nothing` 并不表示失败 — 这也是停止运行或故意禁用的守护进程以及没有摄像头的板上 `mediad` 所呈现的样子。

`[--] tofd 发布了 nothing` 表示一个在 `tofd` 发布身份之前就已发布的版本 — 一次推送即可修复 — 而不是缺少传感器：`tofd` 无论是否安装传感器都会运行。

在板子上，这个版本是 `robotctl version` 报告的内容：
```bash
robotctl version
```
Two pushes的同一脏树从不碰撞——版本携带的是推送的时间戳，而不仅仅是提交。这里预期该树是脏的。

**这是一个普通的更新。**签名、artifact哈希、兼容性、健康门和自动回滚都会运行：一个未成功的构建会被回滚，板子回到它原本运行的状态。故意回滚也是普通的命令：
```bash
sudo robotctl update rollback daemon
```
## 在推送之后查看推送内容

从第二个终端，在推送之前查看，这样重启会显示在其中：
From a second terminal, before the push, so the restart shows up in it:
```bash
ssh radxa@192.168.1.42 'journalctl -f -u robotd -u configd -u btd -u padd'
```
- `-u updaterd` 单独使用时是更新本身——每个阶段，健康门以及它调度的重启：
```bash
ssh radxa@192.168.1.42 'journalctl -f -u updaterd'
```
A panic在一个守护进程里发生，并带有完整的回溯信息：这些二进制文件没有任何内容被剥离，因此回溯帧有名称。
```bash
ssh radxa@192.168.1.42 robotctl health
```
控制回路是否启动，以及每个守护进程正在运行哪个版本。
[`cheatsheet.md`](cheatsheet_zh.md) 中列出了其余需要询问的内容。

### 超过 `info` 级别

每个单元设置 `RUST_LOG=info`。要查看守护进程的 `debug!` 日志，可以在板卡上通过 drop-in 文件覆盖它——以 `robotd` 为例：
### 超过 `info` 级别

每个单元设置 `RUST_LOG=info`。要查看守护进程的 `debug!` 日志，可以在板卡上通过 drop-in 文件覆盖它——以 `robotd` 为例：
```bash
sudo mkdir -p /etc/systemd/system/robotd.service.d
```

```bash
sudo tee /etc/systemd/system/robotd.service.d/log.conf > /dev/null <<'EOF'
[Service]
Environment=RUST_LOG=debug
EOF
```

```bash
sudo systemctl daemon-reload && sudo systemctl restart robotd
```
The drop-in 位于 `/etc`，因此它比所有后续推送都持久。用完后将其移除：
The drop-in lives in `/etc`, so it outlives every later push. Take it back off when you are done:
```bash
sudo rm /etc/systemd/system/robotd.service.d/log.conf
```

```bash
sudo systemctl daemon-reload && sudo systemctl restart robotd
```
## 验证而不安装
```bash
scripts/dev-push.sh --dry-run radxa@192.168.1.42
```
Builds, signs, 复制，并然后做真实 apply 做的一切，除了交换：签名、哈希、兼容性、提取以及检查没有安装的单元指向此构建不包含的二进制文件。它在 `current` 移动之前停止，因此板卡继续运行它正在运行的内容，并且没有守护进程重启。

## 在容器中构建

```bash
scripts/dev-push.sh --docker radxa@192.168.1.42
```
No zig, no `cargo-zigbuild`,和没有需要复制libudev的板子。在Apple Silicon Mac上，容器的目标是宿主机，因此不进行交叉编译；在x86笔记本上它在模拟器中运行，脚本会说明这一点。同一个构建产物，`--dry-run`和`--bootstrap`的效果相同。

两种模式各自保持独立的`target/`目录，因此在它们之间切换需要一次完整的重新构建。默认模式日常使用更快，并且是CI使用的模式。

## 重新安装板子上已有的内容

推送操作会在板子上的`~/duck-sideload`中留下构建产物，因此无需重新构建就可以再次安装：
```bash
sudo robotctl update apply daemon --from ~/duck-sideload
```
The same command 可以对任何包含发布版本的目录进行操作——例如，一个USB闪存盘。每次推送都会替换该目录，而不是向其添加内容。

## 无需机器人编译目标板

为了检查变更是否可以为目标板构建——即，C链接的crate和仅在Linux下的路径——即使没有目标板在手边：
```bash
cargo board --bins
```
`cargo board` 是 `cargo zigbuild`，其中包含了板子的目标和 glibc 底限，这些定义在 `.cargo/config.toml` 中。它需要与默认推送相同的 zig 工具链，而 `padd` 则需要从板子中获取的第一个推送所获取的 libudev 复制件。`--docker` 则不需要这些。

## 低于 0.5.0 版本的板子的首次推送

`apply --from` 需要 API 版本 7，该版本首次出现在 0.5.0 中。运行任何早期版本的板子上的 `updaterd` 无法被要求使用该版本，并且会拒绝该调用而不是默默地从其配置来源进行安装。一旦有了不受限制的方式，就交付该版本：
## 低于 0.5.0 版本的板子的首次推送

`apply --from` 需要 API 版本 7，该版本首次出现在 0.5.0 中。运行任何早期版本的板子上的 `updaterd` 无法被要求使用该版本，并且会拒绝该调用而不是默默地从其配置来源进行安装。一旦有了不受限制的方式，就交付该版本：
```bash
scripts/dev-push.sh --bootstrap radxa@192.168.1.42
```
That 停止 `robotd` 并为此安装放弃健康门。之后的每次推送都是普通的命令。

## 当它不起作用时

**`no dev signing key at ...`** — 板子会像验证任何发布一样验证此文件，因此必须对其进行签名。从团队成员处获取 `team.dev.key`，或者将 `DUCK_DEV_SECRET_KEY` 指向它。

**`cargo-zigbuild is not installed`** — 安装它和 zig，或者使用 `--docker`。

**`no libudev.so.1 on <board>`** — 第一次推送会将该库从板子复制下来以链接 `padd`。尚未启动的板子无法提供它；`--docker` 不需要它。

**重新刷写板子后关于 libudev 的链接器错误** — 该副本已缓存。删除它，下一次推送会获取一个新鲜的副本：
```bash
rm -rf ~/.cache/duck-cross/aarch64
```
**`apply failed (exit 2)`, 与 `robotctl` 和 `updaterd` 报告 API 不匹配** — 板子安装的版本早于 `apply --from`。请使用 `--bootstrap` 一次。

**`preflight check failed: SideloadDir: ... 不存在于 updaterd 中`** — 该版本位于 `/tmp` 或 `/var/tmp` 下，这发生在 `DUCK_SIDELOAD_DIR` 或手动指定的 `--from` 指向这些目录时。`updaterd.service` 设置了 `PrivateTmp=yes`，因此该守护进程有自己的 `/tmp` 和 `/var/tmp`，而你的 shell 并未将这些目录复制进去。其他路径均可；默认路径 `~/duck-sideload` 是其中之一。在板子安装的版本早于该检查的板子上，同样的错误会表现为 `no manifest for version <version> in <dir>` — 对于一个 `ls` 列表中恰好包含该 manifest 的目录。

**`verification failed: 签名未验证通过任何可用的可信密钥中的一个`** — 看起来像是一个损坏的版本，通常意味着该板子不是开发板：开发密钥从未被包含，或者 `allow_dev_keys` 关闭，这两种情况都会使该密钥不在可用密钥集中。在板子上：
```bash
grep -c 'DEV BOARD' /var/lib/robot/provision.log
```
`0` 表示键缺失；[`install-dev.md`](install-dev_zh.md) 包含了修复的两部分。

**`无法通过蓝牙连接 <name>`** — 机器人必须正在广播并且在范围内，以便通过名称路径解析地址。
```bash
duckctl scan
```
Nothing 列出的是离线、超出范围或已连接到电话的机器人。请提供地址而不是使用无线电：
```bash
scripts/dev-push.sh radxa@192.168.1.42
```
**`<name> 通过蓝牙回复了但没有 wifi 地址`** — 它是激活的但不在网络上，因此
无法通过 ssh 连接。在同一无线电上加入一个：
```bash
duckctl --name duck-c51b wifi connect <ssid> --psk <passphrase>
```
**`still <address>, 无法通过 ssh 达到`** — 地址从未改变，所以 ssh 不高兴的原因可能是其他方面的问题。通常需要重新刷写电路板；请参见下方的主机密钥。

**ssh 在重新刷写后拒绝连接** — 电路板重新生成了主机密钥。
```bash
./scripts/provision-board.sh radxa@192.168.1.42 --forget-host-key
```
**`发布已上线但并非一切都在运行`** — 交换已经发生且健康门已通过，但一个守护进程仍在旧二进制上运行，这被解读为一个未解决问题。脚本指明了哪些。在板子上：
```bash
robotctl health
```
The `units` 块命名了每个守护进程正在运行的发布版本。
```bash
journalctl -u updaterd -b | tail
```
Look for `重启安排`，或者根本没有原因。
```bash
sudo systemctl restart updaterd
```
This 不应是必要的，因此值得阅读日志以了解原因。
[`cheatsheet-dev.md`](cheatsheet-dev_zh.md) 中包含了完整的重启陷阱，而
[`../design/restart-order.md`](../design/restart-order_zh.md) 则是逐步的顺序。

## 配置

| | |
|---|---|
| `DUCK_ROBOT` | 机器人名称。其地址通过蓝牙找到并缓存。 |
| `DUCK_BOARD_USER` | 板子上的 ssh 用户，用于名称路径。默认 `radxa`。`duckctl ssh` 和 `duckctl scp` 也会读取它。 |
| `DUCK_PIN` | 机器人的配对 PIN，如果它不是工厂默认的 `000000`。由 `duckctl` 读取。 |
| `DUCK_BOARD_CACHE` | 解析后的地址缓存位置。默认 `~/.cache/duck/boards`。 |
| `DUCK_BOARD` | 通过地址指定的板子，而不是参数。`radxa@192.168.1.42`。 |
| `DUCK_DEV_SECRET_KEY` | 开发签名密钥。默认 `~/.duck-keys/team.dev.key`。 |
| `DUCK_SIDELOAD_DIR` | 构件在板子上的落脚点。默认 `~/duck-sideload`。从 `/tmp` 或 `/var/tmp` 之下绝对不要，`updaterd` 有私有的副本会读取它们。 |
| `DUCK_CROSS_SYSROOT` | 缓存的 libudev 复制。默认 `~/.cache/duck-cross/aarch64`。 |

## 这里故意不做的事情

不包含任何用于溯源的发布内容。版本携带的是时间戳而不是标签，构件使用的是客户拒绝的密钥进行签名，并且没有任何内容被发布——因此其他人无法安装你刚刚运行的内容。发布仍然需要打标签和 `release.yml`([`../../README.md`](../../README_zh.md))。
