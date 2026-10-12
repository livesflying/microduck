# CI 设置

状态: 草案 · 日期: 2026-07-28 · 负责人: pierre

一次性设置用于发布管道。请参阅 [`updater-design.md`](../design/updater-design_zh.md)
§5.4 了解密钥保管和 §16.3 了解测试环境 → 生产环境模型。

## 决定：两个密钥、两个触发器和无门禁

**决定于 2026-07-29。** 分支推送使用 `team.dev` 签名；标记版本和推广使用 `release-1` 签名。两个密钥均存于 CI 中。

| 触发器 | 工作流 | 密钥 | 达到客户机器人 |
|---|---|---|---|
| 任何分支的推送 | `dev.yml` | `team.dev`（仓库秘密） | **否** — 该工作流中 `allow_dev_keys = false`，且受信任的文件名必须以 `.dev.pub` 结尾 |
| 标记 `daemon-staging-v*` | `release.yml` | `release-1`（`release` 环境秘密） | 未推广前不会 — 作为预发布版本发布 |
| 手动推广 | `promote.yml` | `release-1` | **是** |

这种划分方式比早期提案更清晰：密钥从未在测试环境 → 生产环境路径内跨过，因此推广仍然会重新签名一个完全相同的字节的清单（§16.3）。由 `team.dev` 签名的文件不能被推广，因为 `promote` 将 `sig_url` 指向了现有签名的测试环境文件 —— 这就是为什么开发构建保持为开发构建而不是成为候选版本的原因。

### 所期望的和为何没有实现

原计划是将 `release-1` 门禁在 `release` 环境的必需审查者规则之后。但无法创建该门禁：
```
HTTP 422: Failed to create the environment protection rule.
Please ensure the billing plan supports the required reviewers protection rule.
```
标签保护被检查为替代方案，也是不可用的：
```
403: Upgrade to GitHub Pro or make this repository public to enable this feature.
```
要求的审查者、部署分支策略、分支保护和规则集都是私有仓库的Team/专业功能。`pollen-robotics`处于免费计划中。`release`环境存在且没有任何保护规则。

### 明确接受的风险

**任何具有推送权限的人都可以读取 `release-1`。** 将其范围限定在 `release` 环境中可以阻止未声明该环境的工作流查看它，但任何合作者都可以创建一个声明该环境的工作流。因此，“仅用于发布”只是一个团队成员之间相互信任的约定，而不是访问控制——工作流文件并不是一个边界。

这是故意接受的风险：团队规模小且相互信任，没有机器人离开团队，而选择手动签署每次发布则在当前不存在的威胁面前毫无意义。

**当其中任何一个条件变为现实时重新评估**，因为成本会急剧变化，而失败是这种设计无法挽回的——泄露的密钥意味着需要向每台机器人分发带有 `release-2` 签名的更新，并且任何未收到更新的机器人将永远信任被破解的密钥：

- 一台机器人在某人的家中，或者
- 一个具有推送权限的人是你不会直接给予其签名密钥的人。

此时的修复措施是将组织升级到 GitHub Team，这会保持这种分离并增加保护；或者将 `release-1` 签名回退到一台笔记本电脑。

## 分层（保持不变，仍然是限制损害的关键）

无论上面做出什么决定，限制妥协成本的关键在于哪个密钥可以从哪个位置访问：

| 密钥 | 在 CI 中 | 角色 |
|---|---|---|
| `release-1` | **当前不可用** — 请参阅上方 | 签署每次发布和推广 |
| `release-2` | 无 | 如果 CI 或 `release-1` 被妥协，则作为第一个轮换目标 |
| `release-3` | 无，理想情况下从未在网络机器上 | 最后手段 |
| `team.dev` | 意图，仅开发工作流 | 分支构建；不能接触客户机器人，因为 `allow_dev_keys` 为假 |

所有 **公开** 密钥从一开始就包含在每台机器人的镜像中——机器人只能验证内置的密钥集，因此这是唯一一次在不物理重新刷写的情况下实现轮换的机会。

## 密钥和变量

GitHub Secrets 是 **只写** 的：一旦设置，任何人都无法读取它们，包括你自己。它们是一个 *部署副本*，而不是存储。密码管理器仍然是记录系统；丢失它意味着密钥丢失，而依赖它的每台机器人将无法再次被签名。

**将它们限制在 `release` 环境中，而不是仓库中。**仓库中的秘密可以在仓库中的每个工作流作业中读取；而环境秘密仅可被声明了该环境的工作流作业读取。在本计划中，这种区别可以阻止无关的工作流看到该密钥——但这是严格更好的，并且没有任何额外成本：
```bash
gh secret set MINISIGN_SECRET_KEY --env release < ~/.duck-keys/release-1.key
```

```bash
gh secret set MINISIGN_PASSWORD --env release
```
The second 提示，因此口令从未出现在命令行历史或转录中。

**Secrets**（加密，不可读）。当前状态：

| 名称 | 范围 | 值 | 设置 |
|---|---|---|---|
| `MINISIGN_SECRET_KEY` | `release` 环境 | `~/.duck-keys/release-1.key`，两行 | ✅ |
| `MINISIGN_PASSWORD` | `release` 环境 | `release-1` 的口令 | ✅ |
| `MINISIGN_DEV_SECRET_KEY` | **repo** | `~/.duck-keys/team.dev.key` | ✅ |

`MINISIGN_DEV_SECRET_KEY` 有意设置为 repo 范围：每次分支推送都会使用它进行签名，因此将其置于环境变量后意味着开发流程声明了一个适用于 `release-1` 的密钥。它不需要口令密钥——开发密钥未加密，以便 CI 可以非交互式地签名，这由 `xtask keycheck` 确认并称为开发密钥正确而发布密钥错误。

**Variables**（明文，可读——公钥不是秘密）：

| 名称 | 值 |
|---|---|
| `MINISIGN_PUBLIC_KEY` | `~/.duck-keys/release-1.pub` 的公钥行 |

公钥用于 `release.yml` 在发布之前通过机器人自己的代码路径验证发布。将其作为 *变量* 而非秘密保留是故意的：将公钥视为秘密会让人混淆哪一半是公钥哪一半是私钥。

**不要**添加 `release-2` 或 `release-3`。它们的整个值在此处为空。

## `release` 环境

`release.yml` 和 `promote.yml` 声明 `环境: release`。在设置中创建它，并添加 **必需审查者**。

如果没有它，任何可以推送 `daemon-staging-v*` 标签的人都可以为整个舰队签名。有了它，达到签名密钥需要第二个人的批准——这在很大程度上恢复了本地签名所给予的东西，代价是每次发布点击一次。

拉取请求分叉从不接收密钥，因此无论从贡献者 PR 中都无法访问该密钥。

## 密钥的处理位置

每个工作流中恰好有一个步骤将密钥写入磁盘，并且立即删除：
```
umask 077
printf '%s' "$MINISIGN_SECRET_KEY" > "$RUNNER_TEMP/secret.key"
cargo run -p xtask -- sign --dir dist --key "$RUNNER_TEMP/secret.key"
shred -u "$RUNNER_TEMP/secret.key" || rm -f "$RUNNER_TEMP/secret.key"
```
Written 到文件而不是作为参数传递，因为命令行中的键在运行器上的其他任何内容中都可以在进程列表中看到。

`release.yml` 的验证步骤特意不需要任何键：`xtask package` 会发出一个带有裸文件名 URL 的第二个清单文件（用于 `LocalDir`），而 `xtask sign` 会一次性完成签名。重新签名以验证会意味着在一个作业中两次处理签名密钥而没有任何好处。

## 切割一个发布

**GitHub 发布页面是入口点。** 你创建的内容决定了会发生什么，`release.yml` 会读取标签来确定操作：

| 你创建 | 模式 | CI 做什么 |
|---|---|---|
| 预发布，标签 `daemon-staging-v0.4.0` | `staging` | 为 aarch64 交叉构建，打包，使用 `release-1` 签名，并通过实际引擎验证，发布一个 **预发布版本** |
| 正式发布，标签 `daemon-v0.4.0`，存在 staging 0.4.0 | `promote` | 在 staging 验证的相同二进制文件上重新签名一个稳定的清单文件；无需重新构建；退役 staging 发布 |
| 正式发布，标签 `daemon-v0.4.0`，不存在 staging 0.4.0 | `stable` | 构建 0.4.0 并直接发布到稳定版本，附带说明从未进行过测试发布 |

运行总结会指出是哪一种运行，因为“是哪个”是当一个发布看起来有问题时的第一个问题。

从终端推送标签会做同样的事情——发布对象会为你创建：
```
git tag daemon-staging-v0.4.0 && git push --tags
```
提升工作区版本后：`xtask package` 对于与 `Cargo.toml` 不一致的标签会拒绝打标签。

两个值得了解的属性，因为它们是进行拆分的目的：

- 预发布版本会在普通的 `update apply` 中被跳过，因此未经推广的构建无法到达没有使用 `--staging` 请求它的机器人。两个发布步骤会在已存在的发布上重新声明该标志 —— 一个未打勾的草稿发布否则会被整个舰队安装，而一个标记为预发布的稳定发布则不会被任何人分发。
- 推广不会重新构建。稳定的发布最终会自包含（清单、签名、制品、启动二进制文件），这就是为什么之后可以删除草稿发布。在那之前发布的稳定发布 —— `daemon-v0.3.0` —— 仍然指向它们的草稿发布，因此 **这些草稿发布不能被删除。**

手动推广就是同样的配方，只是没有先创建一个发布，而 `min_supported` 就生活在其中（§8.1 —— 它强制要求低于该版本的机器人更新，而无需等待客户端）：
```
gh workflow run promote --field version=0.4.0
```
### 工作流

```
release.yml            the entry point: decides staging / promote / stable
_build-release.yml     build · package · sign · verify · publish        (called)
_promote-release.yml   copy bytes · verify sha · re-sign · retire staging (called)
promote.yml            workflow_dispatch → _promote-release.yml
dev.yml                every push: an unsigned-for-customers dev build, `team.dev` key
```
The 食谱存放在名为workflows的两个文件中，因此staging和stable路径在所交付的内容上不会分离。`xtask`的打包陷阱通过读取`_build-release.yml`和`dev.yml`来获取`--include`列表，因此未被打包的单元、挂钩或sysusers文件将失败测试而不是由机器人处理。

两个发布步骤仅在发布不存在时创建发布，然后使用`--clobber`上传，因此可以重新运行中途失败的任务。在此之前并非如此：如果发布任务在创建发布后失败，只能通过手动删除发布和标签重新运行。

## 旋转密钥

如果`release-1`或CI被攻破：

1. 将`MINISIGN_SECRET_KEY` / `MINISIGN_PASSWORD`替换为`release-2`的。
2. 发布一个由`release-2`签名的发布。机器人已经信任它——这就是为什么第一个镜像中同时提供了两个公钥的原因。
3. 在后续的发布中从`trusted_keys_dir`中移除`release-1.pub`，这样被攻破的密钥将不再被接受。
4. 生成一个备用的第三个密钥：`cargo xtask keygen --kind release --name release-4 --out ~/.duck-keys`

步骤3故意滞后于步骤2：在每个机器人都接受新签名的发布之前撤销旧密钥，会导致任何错过新发布信息的机器人被搁置。
