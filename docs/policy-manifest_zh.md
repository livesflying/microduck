# 微鸭策略清单，方案2

一个 `manifest.json` 旁边的一个微鸭 `.onnx` 文件说了些什么，以及机器人对每个字段的处理方式。
一种词汇对应两种形状：一个 **单一策略仓库**（在 Hub 上，`<user>/microduck-<name>`，一个 `policy.onnx`，顶级字段）和 **官方集**（`pollen-robotics/microduck-policies`，十个文件，每个条目在 `policies` 下的顶级字段）。一个读者可以理解两者，向发布者提出需求是“添加一个字段”，而不是“采用我们的格式”。

`pollen-robotics/microduck_rl` 中的 `uv run publish` 可以从一个检查点或一个 ONNX 文件生成一个符合规范的单一策略仓库。`robotctl policy load <slot> <repo>` 和 `robotctl policy add <name> <repo>` 可以读取它。`docs/design/policy-channel-design.md` 第9节解释了原因；本文件是合同。

## 两个轴

**`kind` 说明了策略的结束者。**

| `kind` | 含义 | 变为 |
| --- | --- | --- |
| `episodic` | 运行 `duration_s` 后返回安全姿态 | 一项技能，如果其命令是恒定的 |
| `perpetual` | 运行直到被停止——一种步态，或一个人必须结束的姿态 | 一个插槽的步态（`policy load`）；或者，带有 `unwind_s` 时，一个带有 `--hold` 的技能 |
| `scripted` | 间歇性但可中断：守护进程可以在飞行中更改其命令 | 录制的；守护进程自身的臂读取其时间 |

**`command.encoding` 说明了守护进程向其提供的内容。**

| `encoding` | 扭曲 | 谁 |
| --- | --- | --- |
| 缺省或 `constant` | 窗口中的固定扭曲，返回时为 `idle` | 每次踢腿，滚翻，迄今为止的每个社区一次性技能 |
| `phase` | `[cos 2πφ, sin 2πφ, 0]`，φ 从 0 跨过 `period_s` s，结束于 `end_phase` | 地面拾取；滚翻蹲 |
| `posture_flag` | 一个插槽携带 `sit` 或 `stand` | 坐立变换 |

只有恒定命令的 `episodic` 策略可以是通用的一次性技能。带有 `phase` 或 `posture_flag` 的策略会被 `policy add` 拒绝，并且属于守护进程驱动的插槽（`policy load ground_pick …`，`policy load sitstand …`）。守护进程在编码上而不是名称上保护这一点。

## 字段

除了集合中的 `file` 字段外，一切皆可选。缺失的字段不是证据：机器人仅在存在且错误的声明上拒绝策略。
| 字段 | 类型 | 读取方式 | 含义 |
| --- | --- | --- | --- |
| `schema_version` | int | 显示 | `2`。它是1的超集；没有任何东西依赖于它 |
| `model_api` | int | 获取 | 策略所需的daemon API；如果比daemon的新，则被拒绝 |
| `obs_len` | int | 获取 | `61`；如果与机器人不符，则被拒绝 |
| `action_len` | int | 获取 | `14`；如果与不符，则被拒绝 |
| `robot.model` | str | 获取 | `microduck`；如果为另一机器人，则被拒绝 |
| `robot.hw_rev`, `robot.servos`, `robot.control_hz` | | 显示 | `1`, `xl330`, `50` |
| `name` | str | 技能 | 客户端请求的内容；默认为文件的 stem |
| `description` | str | 显示 | 一行，不可信 |
| `kind` | str | 技能, 槽位 | 见上方 |
| `duration_s` | float | 技能 | 运行秒数；对于阶段策略，`period_s × end_phase` |
| `chain` | bool | 技能 | 持有按钮结束当前运行时，启动另一个运行 |
| `action_scale` | float | 技能 | 运行期间自身的输出缩放 |
| `unwind_s` | float | 技能, 坐立 | 驱动 `command.idle` 前的秒数；对于坐立，上升时间 |
| `ramp_s` | float | 坐立 | 座椅稳定所需秒数；关机坐立等待两倍于此时间 |
| `mode` | str | 设置 | `walk`（默认）或 `roller`；哪种模式的地面上选择阶段入口 |
| `slot` | str | 显示 | 对于永续步态：它所对应的槽位（`walk`, `stand`, …），因此 `policy load <slot> <repo>` 是安装命令 |
| `entry_pose` | str | 显示 | 策略期望开始的姿态，例如 `standing` |
| `command.encoding` | str | 技能 | 见上方 |
| `command.idle` | [3] | 技能 | 表示“停止做这件事”的扭转 |
| `command.period_s`, `command.end_phase` | float | 地面选择 | 阶段周期 |
| `command.sit`, `command.stand`, `command.slot` | | 显示 | 标志的值及其所在位置 |
| `command.twist`, `command.head`, `command.body` | 文字 | 显示 | 每个块对人的意义 |
| `training` | 对象 | 显示 | `task_id`, `repo`, `commit`, `branch`, `dirty`, `run`, `checkpoint`, `exported` |
| `eval` | 对象 | 显示 | 自由格式：检查的内容，所用的模拟器，表现如何 |
| `policies[]` | 数组 | 设置 | 每个文件一个条目，加上上方的任一策略字段 |

循环LSTM导出需要 `model_api: 2`；现有前馈导出保持API 1。
参见 [循环策略](recurrent-policies_zh.md) 以了解张量合同，内存生命周期
和离线排练。

## 单策略仓库
```json
{
  "schema_version": 2,
  "model_api": 1,
  "obs_len": 61,
  "action_len": 14,
  "robot": { "model": "microduck", "hw_rev": 1, "servos": "xl330", "control_hz": 50 },
  "name": "polite-bow",
  "kind": "episodic",
  "duration_s": 4.0,
  "chain": false,
  "entry_pose": "standing",
  "description": "Bows from a two-foot stand and comes back up.",
  "command": { "encoding": "constant", "idle": [0, 0, 0],
               "twist": "unused (zeros)", "head": "unused (zeros)", "body": "unused (zeros)" },
  "training": { "task_id": "Mjlab-PoliteBow-Flat-MicroDuck", "repo": "pollen-robotics/microduck_rl",
                "commit": "0bf9897", "branch": "bow", "dirty": false,
                "run": "pollen-robotics/mjlab_microduck/abc123", "checkpoint": 3000,
                "exported": "2026-09-02T14:05:00Z" }
}
```
The repo 携带恰好一个 `.onnx` 文件，命名为 `policy.onnx`。`robotctl policy add polite-bow
<user>/microduck-polite-bow` 读取 `duration_s`、`chain`、`action_scale`、`command.idle` 和 `unwind_s`，在 `obs_len`、`action_len`、`model_api`、`robot.model` 或非常量编码时拒绝，并写入技能。`RemiFabre/microduck-flamingo-cycle` 是一个发布的 `perpetual` 示例：没有 `duration_s`，因此需要 `--hold`，并且其 `command.idle` 是 unwind 驱动的。

## 官方集合

在 `policies` 下，每个条目一次包含相同的字段，加上 `file`。当前的副本是 `https://huggingface.co/pollen-robotics/microduck-policies/blob/main/manifest.json`；集合的 `phase` 条目设置了每种模式的地面拾取时间，并且其 `scripted` 条目设置了从坐到站的转换，这就是重新训练的拾取具有更长周期时会成为一个标签而不是守护程序发布。

每个 `file` 都是一个普通的文件名 —— 没有目录，没有前导点。一个命名包含路径的 manifest 的条目会被种子和 `robotctl policy update` 都跳过。

manifest 被安装 **到集合中**，因此 `/opt/robot/policies/current/manifest.json` 是 `robotd` 读取技能的地方。它也是下载列表：添加一个策略是在这里和一个标签中添加，而首次安装电路板和每次 `policy update` 都会从它们安装的版本中获取列表。

## 从模式 1 的变化

模式 1 是官方集合的第一个形状：`kind` 有值 `perpetual`、`episodic`、`scripted`，其中 `scripted` 的意思是“守护程序生成命令”，并应用于地面拾取。模式 2 将此含义移至 `command.encoding`，使 `scripted` 意味着可中断的周期性（从坐到站），并添加了 `chain`、`ramp_s`、`mode`、`entry_pose`、`training`、`eval` 以及 `command.*` 的时间字段。读取模式-1 文件的守护程序会为所有内容获取原型的时间，并且在版本上没有任何拒绝。
