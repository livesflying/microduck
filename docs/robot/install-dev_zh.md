# 在开发板上安装

从无到有，将一块板子变成可以推送分支的机器人。

开发板信任团队开发密钥，因此它可以安装团队中任何人构建的任何内容。客户机器人设置不同，故意拒绝这些构建——这里的所有假设都是针对开发板，而不是客户机器人。

开发构建没有任何放松：相同的签名和哈希验证，相同的健康门，相同的自动回滚。唯一的区别在于哪个密钥进行了签名，而这正是这些构建能够避开客户机器人的原因——它们拒绝了两次开发密钥。`allow_dev_keys = false`，只有当信任密钥的文件名以 `.dev.pub` 结尾时，它才被视为开发密钥。下面的设置的两部分就是为了切换这一点而存在的。

## 烧录板子

使用 [Armbian imager](https://www.armbian.com/radxa-zero-3/)。选择 **Radxa Zero 3**，然后选择 **Armbian 26.2.1 Minimal**。

在写入之前，填写 imager 的配置文件——Wi-Fi 网络和密码，以及你想要的用户名和密码。在这里完成这些设置可以节省后续的串口控制台：板子在首次启动时会连接到你的网络，并且可以直接通过 ssh 访问。
然后添加你的ssh密钥，以便在设备重新启动后 provisioning 可以重新连接：
```bash
ssh-copy-id radxa@192.168.1.42
```
## 需要

- 该板的 **IP地址**。此图中 mDNS 不可靠，因此 `.local` 名称在感觉合适时解析。`duckctl ip` 通过蓝牙询问机器人，无需您自己的网络和 DHCP 租约即可读取；如果板尚未广播，路由器的租约表是备用方案。
- **ssh密钥访问**，来自上述步骤。预置会重启板并自行重新连接，因此在重新连接过程中无法出现密码提示。
- 一个 **GitHub令牌**，因为此仓库是私有的：没有令牌，其发布资源将无法访问。一旦仓库变为公开，令牌可选且仅能获得更高的API速率限制（参见 `docs/design/updater-design.md` §6.1）。
- 一个 **此仓库的克隆**。它所需的开发密钥已提交至 `deploy/dev-key/team.dev.pub`，因此无需向任何人求助。

## 安装

从您机器上的克隆，两个命令：
```bash
export DUCK_TOKEN=github_pat_replace_with_your_token
```

```bash
./scripts/provision-board.sh --pause-btd-on-pair --name <MY_COOL_ROBOT_NAME> radxa@192.168.1.42
```
That 发送你的开发密钥，启动配置，等待重启，流式传输日志，并在 `robotctl health` 结束。

### 为什么在该命令中包含 `--pause-btd-on-pair`

在aic8800无线电中，当`btd`正在广播时，一个电容垫无法形成新的绑定。这个标志会留下一个标记，使得 `robotctl pad pair` 停止 `btd` 并对适配器进行电源循环以创建配对窗口，然后再次启动它。现有的绑定不受影响——一个已绑定的垫片会连接并驱动整个堆栈处于活动状态——因此成本是一个守护进程在配对期间的停机时间。

这里默认使用它是因为一个需要它且未在配置中包含它的电路板会表现为一个无法配对的游戏手柄，并且你追查的每一个可能的原因都可能在其他地方。

### 三种配置，以及如何确定你拥有哪种

有两个独立的故障，因此有两个标志。**配对一个垫片并查看失败信息**，然后选择：
| 你看到的 | 印刷电路板想要的 |
|---|---|
| 垫片焊接和驱动 | 无 — 无标志的预留 |
| 垫片无法焊接；最后一个 SMP 步骤从未完成 | `--pause-btd-on-pair` |
| 即使暂停了 `btd`，垫片也无法焊接 | `--weird-ble`（隐含暂停，增加 `Privacy = device`）|
| 垫片焊接，然后 **振荡** — `PIN 或密钥缺失 (0x06)`，无输入设备 | `--weird-ble` 对于这块板来说是错误的：去掉它，保留暂停 |
| 最后一行是最需要注意的。对于这块板，`Privacy = device` 会导致焊接立即失效，这比明显无法配对的垫片更难诊断 —— 在 `50:37:CD:16:1D:90` 上测量，`off` 加暂停焊接并保持连接，而 `device` 在 45 秒内振荡 46 次。因此 `--weird-ble` **不再** 是默认选项。|

为了将板子从 `--weird-ble` 转换为仅保留暂停标志，操作如下：
```bash
sudo sed -i 's/^Privacy = device/Privacy = off/' /etc/bluetooth/main.conf && sudo reboot
```
To 去反方向，带着脚本副本在白板上配置叶子节点：
```bash
sudo DUCK_WEIRD_BLE=1 /usr/local/sbin/robot-setup-board && sudo reboot
```
And 检查一块电路板既不需要，删去两者并配对一块电路板即可：
```bash
sudo rm /var/lib/robot/weird-ble
sudo sed -i '/^Privacy = /d' /etc/bluetooth/main.conf && sudo reboot
```
- 重新配对任何对 `隐私` 的更改：因为存储的密钥是根据其地址派生的，所以现有绑定会停止匹配，并在重新建立连接前显示 `PIN或密钥丢失` 错误。
- 这一切只是针对aic8800无线模块的临时解决方案，不是设计的一部分；当无线模块不再使用时，这一问题也会随之解决。[pair-a-gamepad.md](pair-a-gamepad_zh.md) 中有详细说明。

它只是一个 **观察者**，而不是执行工作的实体——预配会安装一个systemd单元，在启动时恢复运行，因此即使你不再观看，板子也会完成工作。Ctrl-C不会对你造成任何损失，你可以从断点继续查看日志：
```bash
ssh -t radxa@192.168.1.42 'sudo tail -f /var/lib/robot/provision.log'
```
`--ref BRANCH` 从分支获取配置：其脚本执行启动过程，其构建的守护程序安装在其顶部。`golden` 保持稳定版本 — 它是启动恢复网络的备用方案，而一个分支构建的 golden 会为一个损坏的分支提供一个损坏的备用方案 — 而 `current` 则是该分支本身。

如果该构建无法安装，则配置 **失败**；或者即使安装后又被健康门回滚。当请求分支时，一个正在安静地运行稳定版本的开发板是最难调试的失败情况：一切看起来都已安装，但测试的代码却不存在。给 CI 一分钟时间再进行配置，并通过 `gh run list --branch BRANCH` 检查它是否停止。

其他有用的标志：`--name Ducky` 为机器人命名而不是使用它从自身序列号推导出的 `duck-7f3a`（`robotctl system set-name` 可稍后更改它，因此这仅节省了一个命令），`--local` 发送此克隆的 `provision.sh` 而不是从远程获取它（这是在合并之前测试配置脚本更改的一种方法），`--no-dev-key` 则创建只能安装发布版本的板子。

## 检查是否生效
```bash
robotctl health
```
The board 只有在真的安装了 key 才算作开发板，而这是一件你可以检查的事情，而不是一件你需要记住的事情：
```bash
grep -c 'DEV BOARD' /var/lib/robot/provision.log
```
`1` 表示是。`0` 表示该密钥未成功部署，且稍后会因错误而拒绝使用 `--ref`。这正是此检查存在的目的，以早期捕获失败。然后进行实际测试——在其中放置一个分支：
```bash
sudo robotctl update apply --ref main daemon
```
## 当重新刷写后 ssh 连接被拒绝

重新刷写会生成板子的主机密钥，所以你上次使用的地址现在呈现了一个不同的密钥。`StrictHostKeyChecking=accept-new` 并不能涵盖这种情况：主机不是新的，它的密钥是新的。直接的 ssh 错误信息是一大段关于可能攻击的文字。
```bash
./scripts/provision-board.sh radxa@192.168.1.42 --forget-host-key
```
This 比听起来更重要，因为DHCP租约会被重复使用——上周这个地址属于一块板子，今天可能属于不同的板子，且带有不同的密钥。

## 当板子返回到不同的地址时

在配置过程中中间进行的无线网络切换可能会使板子占用一个不同于你分配的地址的租约。`provision-board.sh`会进行查找：在等待ssh的同时，它还会通过蓝牙询问机器人最终得到了哪个地址，并采用这个答案。
```
  bluetooth: the robot reports 192.168.1.57, and 192.168.1.42 was its old lease.
```
- 无需执行——其余的运行内容已在别处处理。
- 有三个原因使其无法正常工作，并且会指出这些原因：
  - 它需要 `cargo` 和此克隆，因为 `duckctl` 是一个示例而不是安装的二进制文件。
  - 只能在 `btd` 运行后询问一次，而在首次为板子进行配置时，这通常是在阶段 2 几分钟后。
  - 机器人会报告其 **wifi** 地址，因此通过以太网连接的板子不在覆盖范围内。

`--no-ble` 可以关闭此功能。一个已被分配了配对 PIN 的机器人需要在 `DUCK_PIN` 中包含它。

## 使现有板子接受开发构建

对于以其他方式配置的板子，或者在你获得密钥之前设置的板子。两部分都需要：单独使用任何一部分都会使板子仍然拒绝分支构建。

简单的方法是重新运行安装程序并输入密钥，这一步会验证密钥并一次性切换标志：
```bash
sudo DUCK_TOKEN="$DUCK_TOKEN" DUCK_DEV_KEY=/tmp/team.dev.pub sh /tmp/install.sh
```
It 安装密钥为 `team.dev.pub` 无论源文件叫什么名字。这个名字很重要：`.dev.` 前缀是将密钥分类为开发密钥的标准，而任何其他名称下的密钥被视为 **发布** 密钥。

手动操作的话，如果你希望看到每一步：
```bash
sudo cp team.dev.pub /etc/robot/trusted_keys/team.dev.pub
```

```bash
sudo sed -i 's/^allow_dev_keys.*/allow_dev_keys        = true/' /etc/robot/updater.toml
```

```bash
sudo systemctl restart updaterd
```
## 令牌，手动设置

`scripts/install.sh` 在给定 `DUCK_TOKEN` 时会为你写好这个内容。这些步骤适用于以其他方式配置的板子——并且仅在该仓库为私有状态或板子频繁拉取代码以获取令牌提供的更高速率限制时才需要这些步骤。

`updaterd` 从自身的环境变量读取 `GITHUB_TOKEN`，因此在你的 shell 中导出它不会到达守护进程——它需要一个 systemd 插件。
```bash
sudo mkdir -p /etc/systemd/system/updaterd.service.d
```
Substitute 你的令牌 在下一个块中 — 它是这里的唯一占位符：
```bash
sudo tee /etc/systemd/system/updaterd.service.d/token.conf > /dev/null <<'EOF'
[Service]
Environment=GITHUB_TOKEN=ghp_replace_with_your_token
EOF
```
A drop-in 默认是世界可读的，并且这个 drop-in 持有一个凭证：
```bash
sudo chmod 600 /etc/systemd/system/updaterd.service.d/token.conf
```

```bash
sudo systemctl daemon-reload
```

```bash
sudo systemctl restart updaterd
```
一个开发者板上的token是可以的。一个客户机器人上的token则不行——整个车队的凭证若嵌入图像中则无法旋转更新，因此答案是一个公共仓库而非打包的token（`docs/design/updater-design.md` §6.1）。即使没有token，一个板子仍然可以通过本地目录或开发推送来安装。

## 无需网络安装

在一个已有发布版本的板子上，通过守护进程以健康网关和自动回滚的方式普通地安装一个本地目录——

```bash
sudo robotctl update apply daemon --from /media/usb/release
```
That 也是 `scripts/dev-push.sh` 的结尾；[`dev-push.md`](dev-push_zh.md) 是
笔记本到板子的路径。

这一节剩下的部分是 **裸板** 情况：在没有守护进程可以询问的工厂或离线安装之前。因此使用的是 `updaterd` 而不是 `robotctl`，并且 `updaterd` 故意不在 `PATH` 中：
```bash
sudo /opt/robot/daemon/current/bin/updaterd install --from /media/usb/release
```
The 目录包含一个发布版本的内容：`<version>.manifest.json`，其 `.minisig`，文件 artifact 以及 artifact 的 `.minisig`。签名、哈希值和兼容性检查与下载时完全相同 —— `--from` 只改变字节的来源，而不改变信任的内容。

该命令在发布上线后将拒绝运行，因为这会强制关闭 `on_apply` 和健康检查门，对正在工作的机器人执行这样的操作会无声地禁用自动回滚。尽管有这种情况需要这样做，但 `robotctl update apply` 无法解决它 —— 一个安装的 `updaterd` 过旧以至于无法接受修复了过旧问题的发布。每次都会回滚新发布，而运行该检查门的二进制文件正是要被替换的那个。请明确地停止机器人并说明这一点：
```bash
sudo systemctl stop robotd
```

```bash
sudo /opt/robot/daemon/current/bin/updaterd install --from /media/usb/release --force
```
`--force` 在 `robotd` 仍在响应时也被拒绝，因为反对的是一个正在工作的机器人失去了其安全网。它只为那个安装放弃了自动回滚功能，其他一切——签名、哈希值和兼容性——仍然会被检查，如果发布版本行为异常，可以通过运行 `sudo robotctl update rollback daemon` 来恢复。

## 更深入

[`部署/README.md`](../../部署/README.md) 是所有这些操作的参考文档：信任链、最终文件的位置、其他进入方式（在没有克隆的情况下通过主板手动安装）、日志文件的位置以及重启后保留的内容。
