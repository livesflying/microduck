# 应用通道设计：`btd` 与 `configd`

本文描述手机如何通过蓝牙配置机器人，包括 Wi-Fi、名称、重启、版本查询和触发更新。
`btd` 提供 BLE 入口，`configd` 负责身份、网络和系统配置。

## 设计重点

- BLE 接口只暴露明确允许的 RPC 方法。
- 需要修改系统状态的操作由 `configd` 执行并进行权限校验。
- 配网、改名、设置 PIN 和重启等操作需要清晰的状态反馈。
- 更新请求交给 `updaterd`，应用通道只负责传递请求和进度。
- 蓝牙断开不能导致更新过程被取消或留下半成品。

本文与[系统架构](architecture_zh.md)和[更新系统设计](updater-design_zh.md)配套阅读。

英文源文档：[app-path-design.md](app-path-design.md)。
