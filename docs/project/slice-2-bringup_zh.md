# Slice 2 硬件验证

本文记录 Slice 2 在真实 Radxa Zero 3W 和机器人上的运行结果。内容以硬件观察为主，
用于记录板级问题、runtime 版本、服务启动和更新流程的实际表现。

## 关注内容

- 控制循环、舵机总线和策略加载。
- ONNX Runtime 版本与模型兼容性。
- 安装脚本、systemd 服务和健康检查。
- 从故障日志中提炼应加入自动化测试的场景。

英文源文档：[slice-2-bringup.md](slice-2-bringup.md)。
