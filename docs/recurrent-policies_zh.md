# 循环 ONNX 策略

运行时接受前馈策略和由 mjlab/rsl_rl 生成的显式状态 LSTM 导出。两者都消耗现有的 61D 观测值，并在 50 Hz 下生成相同的 14 个原始关节动作。观测值归一化必须烘焙到导出的模型中。训练用的评论家（critic）不会部署。这不会增加任何传感器或动作过滤。

## 模型契约

所有张量都是 float32。输入和输出按名称匹配，与顺序无关。

| 模型 | 输入 | 输出 |
| --- | --- | --- |
| Feed-forward | `obs [1, 61]` | 一个输出 `[1, 14]`（现有输出名称仍然有效） |
| LSTM | `obs [1, 61]`, `h_in [layers, 1, hidden]`, `c_in [layers, 1, hidden]` | `actions [1, 14]`, `h_out [layers, 1, hidden]`, `c_out [layers, 1, hidden]` |

批次维度可以是符号的；推理总是使用一个机器人。层数和隐藏宽度必须是正的静态维度，并且在四个状态张量中必须相同。每个状态限制为 1,048,576 个元素。不支持的名称、秩、类型、宽度和额外张量在加载时会失败。预热（Warm-up）也会拒绝无效或非有限的输出。未实现 GRU 和其他循环导出签名。

使用 **`model_api: 2`** 发布循环策略，以便旧守护进程在安装前拒绝它们。该守护进程也接受现有的 API 1 前馈模型。清单模式（manifest schema）、观测宽度和动作宽度没有变化。

## 内存生命周期

每个加载的策略都拥有预分配的隐藏层和单元张量。每次成功的推理都会将两个新状态复制到这些缓冲区中。失败的推理会清除内存；非有限的输出在提交任一状态之前都会被拒绝。预热状态会被丢弃。

内存在初始激活、切换网络（包括切换回）、显式禁用、暂停或跌倒恢复后的控制器重置，以及链式技能重启时从零开始。短暂的传感器掉线遵循现有的恢复宽限期。

活动网络中的命令更改会保留内存。

替换一个非活动槽位，只有当其 ONNX 文件具有相同的 SHA-256 digest 时，才会保留活动网络的内存。更改的活动模型会从头开始，即使文件路径相同也是如此。使用自包含的 ONNX 导出以保证这一点：外部引用的权重文件不属于 ONNX 文件摘要。显式控制器重置总是会清除所有槽位。

现有的动作缩放和可选运行时过滤器保留了它们的配置。对于未经动作过滤训练的策略，请在其部署调优中禁用这些过滤器；增加循环性并不能使不匹配的过滤器配置有效。

## 离线排练和板级时序

示例使用生产 Rust 推理路径，并且从未打开过电机总线：
```sh
export ORT_DYLIB_PATH=/path/to/libonnxruntime.so
cargo run --release -p duck-control --example policy-rehearsal -- policy.onnx > rehearsal.json
```
它会预热执行器，清除状态，然后测量在名义重力、零命令和前一次动作反馈下的 1,000 次推理。JSON 包含 p50/p95/p99/max 延迟、超过 20 毫秒的次数以及动作。请在 **Radxa** 上运行内置示例以建立板载计时；开发主机上的计时无法建立机器人的计时预算。这些计时排除了传感器读取、电机写入和调度延迟。

对于与 PyTorch 或 Python ONNX Runtime 进行确定性多步比较，请将记录的 JSON 数组作为第二个参数提供：
```json
[{"obs": ["replace with exactly 61 numbers"], "reset": true}]
```
每个记录提供完整的观测值，包括之前的动作。在回合边界设置 `reset`。将返回的动作序列与具有相同观测值和重置的参考值进行比较。这检查的是推理和内存处理，而不是物理的 sim2real 迁移。通过训练仓库的标准化导出器导出训练好的检查点。

## 测试
```sh
cargo test -p duck-control
# Requires ONNX Runtime >= 1.23:
cargo test -p duck-control --test recurrent_policy -- --ignored
cargo test -p robotd recurrent_memory_resets_with_controller_feedback -- --ignored
```
小型已检入的 fixture 使用实际的 ONNX LSTM 操作符。它们涉及内存连续性、重置、策略切换、故障转移选择、预热、热插拔、动态批次维度、无效契约和非有限状态。使用 `python duck-control/tests/fixtures/generate.py` 在包含 `onnx` 和 `numpy` 的环境中重新生成。
