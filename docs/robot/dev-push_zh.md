# 在本机编译并安装到开发板

`scripts/dev-push.sh` 用于缩短“修改代码到观察机器人运行”的循环。它会交叉编译、
打包、签名，并通过 SSH 以普通更新方式安装到开发板。

## 典型用法

```bash
./scripts/dev-push.sh <user@board>
```

需要更干净的构建时可以使用 Docker 构建方式。安装仍会经过机器人端的签名检查、
健康门禁和自动回滚。开发板必须已经按照[开发板安装指南](install-dev_zh.md)配置。

英文源文档：[dev-push.md](dev-push.md)。
