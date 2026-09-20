# NPU 与鸭子检测器

RK3566 带有 INT8 NPU。本文记录将训练好的鸭子检测模型转换为 `.rknn`、加载到 NPU
并验证推理性能的过程。

## 当前状态

- 模型来自独立的训练项目。
- `duck-detect` 负责加载 RKNN 模型并调用 NPU runtime。
- 模型输入尺寸、量化方式和 runtime 版本必须匹配。
- 推理链路已经可以运行，但将检测结果接入完整行为系统仍有后续工作。

遇到初始化失败时，优先检查 NPU runtime、模型版本、设备节点和输入格式。

英文源文档：[npu-bringup.md](npu-bringup.md)。
