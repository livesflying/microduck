# 连接游戏手柄

手柄完成一次配对后，`padd.service` 会在启动时自动连接并驱动机器人，不依赖 SSH
会话或手动启动进程。

## 配对流程

1. 将 Xbox 或兼容手柄置于配对模式。
2. 按照机器人端的配对命令扫描并建立绑定。
3. 确认 `padd` 能看到输入事件。
4. 在安全支撑状态下测试 Start、摇杆和动作按键。

如果手柄无法绑定，先检查蓝牙广播、`btd` 状态、SMP 日志和控制器固件。若能绑定但输入
中断，使用 `robotctl monitor`、`pad-link-test.sh` 和 `pad-stack-report.sh` 区分无线链路
问题与输入设备问题。

英文源文档：[pair-a-gamepad.md](pair-a-gamepad.md)。
