# 手动安装：逐步执行

本文把 `scripts/provision-board.sh` 拆成多个可单独验证的步骤，适合调试安装脚本或
定位某一步失败。只想获得可用开发板时，应优先使用一键 provisioning 流程。

## 主要阶段

1. 将安装脚本、配置和信任密钥复制到板上。
2. 安装系统依赖和 systemd 服务。
3. 写入机器人配置、开发密钥和更新器配置。
4. 安装初始版本并重启。
5. 使用 `robotctl health` 和日志确认结果。

手动执行时不要跳过签名校验、权限设置和健康门禁。

英文源文档：[install-by-hand.md](install-by-hand.md)。
