# 游戏手柄建立连接所需的最小配置

本文记录在 Radxa Zero 3W 和特定无线控制器上验证得到的最小蓝牙配置，重点是区分
无线电、BlueZ、内核和 `btd` 各层问题。

## 排查方法

- 使用最小 Armbian 镜像并逐项加入软件包。
- 记录 SMP 配对过程和控制器日志。
- 分别测试首次绑定、已有绑定重连和持续输入。
- 不要把 `Privacy = device` 作为默认修复；它可能导致绑定后反复出现密钥缺失。
- 需要时使用 `pad-link-test.sh` 和 `pad-stack-report.sh` 收集证据。

英文源文档：[pad-minimal-pairing.md](pad-minimal-pairing.md)。
