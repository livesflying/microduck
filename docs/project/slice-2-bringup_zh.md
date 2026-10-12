# Slice 2 布局在硬件上

在真实机器人上运行 slice 2 的笔记。以下内容均在 Radxa Zero 3W 上观察到，未推断。

## 状态

Slice 2 已合并，且板子发现的一个问题——**`ort` 异常而不是返回错误，导致控制线程结束，使 `robot.health` 责备错误的事物**——已修复：`duck-control::policy::catching_ort_panics` 将其转换为 `PolicyError`，因此它会走现有的“保持姿态并报告原因”的路径。

**两者现在在硬件上均已关闭。** 修复已在板子上通过将 `robotd` 指向 1.20.1 运行时（通过 `ORT_DYLIB_PATH`）进行验证：循环持续运行，健康状态指出了版本不匹配，而不是一个死掉的控制线程报告“尚未完成一个周期”。Slice 2 然后在每次心跳中运行推理，并从稳定通道安装了 `0.2.0` ——这是包含任何相关内容的第一个版本。

不再有任何链接指向此文件。它被保留为记录板子实际所说的内容；可重用的部分是下面的食谱，而需要再次使用的命令应最终出现在 [`cheatsheet.md`](../robot/cheatsheet_zh.md) 中。

## 已验证可工作的内容

在有线机器人上运行 `0.1.4`（slice 1）：

- 15 个伺服和 `imu_to_dxl` 板在 `/dev/ttyS2` 回应
- 控制循环频率为 **50.0 Hz**，15022 次心跳中有 3 次未命中（0.02%）
- `robotctl health` → `healthy`
- 更新路径从头到尾得到了验证：安装、健康门、提交和自动回滚

因此，总线、伺服、IMU、频率和更新器 **都不是** 疑点。现在失败的任何内容都是 slice 2 的代码或板子的 ONNX 运行时。

## 失败情况

`sudo robotctl update apply daemon --ref slice-2-walk-stand` 回滚了：
```
  HealthGate
  RollingBack
{
  "attempted": "0.1.4-dev.58.6781f98",
  "outcome": "rolled_back",
  "reason": "health check failed: not healthy within 30s:
             control loop has not completed a cycle yet",
  "reverted_to": "0.1.4"
}
```
日志给出了真实原因：
```
thread 'control' panicked at ort-2.0.0-rc.11/src/lib.rs:191:41:
Failed to load ONNX Runtime dylib: Error { code: GenericFailure, msg:
  "ort 2.0.0-rc.11 is not compatible with the ONNX Runtime binary found at
   `libonnxruntime.so`; expected version >= '1.23.x', but got '1.20.1'" }
```
### 为什么健康原因无效

`RobotState::health` 当 `ticks == 0 && startup_bus_failures == 0` 时报告 `control loop has not completed a cycle yet`。一个惊吓控制 *线程* 不会杀死进程，因此 `robotd` 保持运行，继续服务其套接字，并且回答的正是那条消息——一个没有指出原因的消息。将原因字符串读作“循环从未开始且从未记录原因”，而不是“仍在启动中”。

## 两种原因。一种已修复。

**1. 板子使用的运行时版本不兼容 — 已在 #17 中修复（已合并）。** `setup-board.sh` 固定了 ONNX Runtime 1.20.1；`ort 2.0.0-rc.11` 需要 >= 1.23。现在该检查是版本感知的，因此重新运行脚本会替换错误版本而不是报告“已经存在”。

地板和目标位于根 `Cargo.toml` 中的 `[workspace.metadata.onnxruntime]`，并且 #18 从它们生成了发布的 `hooks/preinstall`，因此低于地板的板子会被修复——或者更新在交换之前中止——而不是安装后才惊吓。

**2. `ort` 惊吓而不是出错 — 修复了。**

`ensure_runtime()` 在允许 `ort` 触及 dylib 之前使用 `libloading` 进行探测。其文档注释曾经声称：

> 成功的探测意味着加载也会成功，惊吓不会触发

**板子否定了这一点。** 探测只证明了库 *加载* 了；1.20.1 加载没有问题。`ort` 自身的兼容性检查随后拒绝了 *版本* 并在 `setup_api` 中惊吓，`ensure_runtime` 无法看到这一点。因此，防护关闭了“缺失”的情况而不是“错误版本”的情况——而且从构造上讲，它也无法关闭所有未来的 `ort` 惊吓。

修复没有尝试这样做。`catching_ort_panics` 将 `ort` 调用包裹在 `Policy::load` 内，并将任何惊吓转换为 `PolicyError::RuntimePanic`，携带惊吓消息——上面的版本号就是全部诊断，因此丢失它们会留下一个无人能采取行动的健康原因。这将惊吓置于 `robotd` 已有的路径上，即对于一个无法加载的策略记录 `policy unavailable; holding the pose`，存储原因，将 `controller` 保持为 `None`，**继续以固定速率计数**，并报告 `policy unavailable: <reason>` 以便更新者因明确原因回滚发布。

关于它的两件事要知道：
- The catch 只包裹 `ort` 部分，而不包裹整个 `load`，因此我们真正的错误不会被重新标记为“策略不可用”。`AssertUnwindSafe` 是因为 `Session` 不是 `UnwindSafe`；在成功时，会话被移动到 `Policy` 中并在失败时被丢弃，所以在 catch 之后我们观察不到任何东西。
- **`panic = "abort"` 会破坏这一点。** 目前根 `Cargo.toml` 中没有 `[profile.release]`；添加一个会默默地恢复死掉的控制线程。

### 测试覆盖范围及其不足

在 `duck-control` 和 `robotd` 中离线覆盖：`ort` 路径上的 panic 转变为错误并保留其消息，成功通过未受影响，不可打印的负载仍然提供原因，并且 — 通过 `an_unloadable_policy_holds_the_pose_and_reports_why` — 一个无法加载的策略在循环中继续运行，并在健康字符串中包含底层原因。

离线未覆盖：真正的 `ort` 路径上的 panic 通过控制环路传递。重现它需要错误版本的运行时，即一块板子，而在 `Policy::load` 中模拟一个会意味着在 `duck-control` 中分发一个故障注入旋钮来测试三行代码。下面的板子检查就是关闭它的。

## 在板子上验证

板子需要一次开发密钥，否则会拒绝 `--ref`。`install.sh` 同时完成两部分 — 安装密钥并切换 `allow_dev_keys` — 给定公共半部分的路径：
```bash
sudo DUCK_TOKEN="$DUCK_TOKEN" DUCK_DEV_KEY=/tmp/team.dev.pub sh /tmp/install.sh
```
`team.dev.pub` 位于 `deploy/dev-key/`，而不是 `trusted_keys/`，因此默认情况下不会安装它。手动等效操作参见 [`../deploy/README.md`](../../deploy/README.md)。

然后：
```bash
sudo robotctl update apply daemon --ref slice-2-walk-stand
```
**重新获取 `setup-board.sh` 以确保其安全性。** `/usr/local/sbin/robot-setup-board` 是在上次运行时的一个快照拷贝；它从不会自动刷新，因此可能会默默地运行预-#17 逻辑，并报告“已存在”而实际运行环境是不兼容的。

成功的表现为状态块中显示 `ONNX Runtime  1.28.0`，更新提交而不是回滚，并且：
```bash
journalctl -u robotd -b --no-pager | grep -E 'policy|control loop'
```
showing `policy loaded` 跟随 `control loop running driving=true`。然后重新测量速率 —— 切片 2 在同一刻添加推理，切片 1 基线（50.0 Hz，`missed=3`）是需要对比的对象。`missed` 的大幅增加是推理成本，而不是抖动。

## 规约

- **在 `/tmp` 下的新克隆分支中进行操作**，永远不要在工作检出中操作。共享克隆中的过时工作树是如何让 #13 悄然回滚了 #12 —— `git checkout -b` 将未提交的更改带入了新分支中，`git add -A` 将其作为删除操作进行了提交。
- 提交记录尾部为 `Assisted-by: Claude:claude-opus-5`。永远不要使用 `Co-Authored-By`。
- 范围测试运行：`cargo test -p <crate>`，仅一次。保存 `--workspace` 用于预 PR 检查。
- 在做架构决策之前先询问。
- 修复发布路径中的错误并发布一个版本；不要移交一个本地的临时解决方案。

## 特意未做

- MuJoCo 后端，以及剩余的六项技能。
- 每个关节的限制。`duck-control/src/safety.rs` 对执行器行程（±π）进行了限制，而不是对每个关节的范围进行限制；这需要引入 alpha MJCF。
- 从 `microduck_brain` 获取黄金观测向量，以固定 61 维编码与原型的一致性。布局测试仅覆盖形状，而不涉及与原始版本的一致性。
- `hooks/postinstall` —— #18 只打包了 `preinstall`。
