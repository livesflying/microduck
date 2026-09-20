# 开发者速查表

本文只包含开发板才需要的命令。普通机器人日常使用请阅读
[机器人使用速查表](cheatsheet_zh.md)。

## 常见流程

```bash
./scripts/dev-push.sh <user@board>
```

开发板可以安装分支构建和候选版本，但仍然使用签名、哈希、健康门禁和自动回滚。
更新后应检查运行中的版本、服务状态和日志，避免“安装成功但仍运行旧二进制”。

英文源文档：[cheatsheet-dev.md](cheatsheet-dev.md)。
