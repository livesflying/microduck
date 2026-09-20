# 在开发板上安装

本文介绍如何把一块空白 Radxa Zero 3W 配置成可以接收分支构建的开发板。
开发板信任团队开发密钥；客户机器人使用不同的信任配置，默认拒绝开发密钥。

## 前置条件

- 已刷写并联网的 Radxa Zero 3W。
- 可用的 SSH key 登录方式。
- 本仓库的本地 clone。
- 私有发布仓库需要 GitHub token。

## 安装

```bash
export DUCK_TOKEN=github_pat_replace_with_your_token
./scripts/provision-board.sh --pause-btd-on-pair --name <MY_COOL_ROBOT_NAME> radxa@192.168.1.42
```

安装完成后检查：

```bash
robotctl health
grep -c 'DEV BOARD' /var/lib/robot/provision.log
```

开发板安装仍执行签名、哈希、健康检查和自动回滚。蓝牙手柄配对、Wi-Fi 地址变化、
无网络安装和旧 updaterd 的特殊处理请参阅英文源文档。

英文源文档：[install-dev.md](install-dev.md)。
