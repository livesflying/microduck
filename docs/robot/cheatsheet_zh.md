# 机器人使用速查表

`robotctl` 是运行在机器人上的命令行工具。只读命令通常不需要权限，修改硬件或系统
配置的操作一般需要 `sudo`。

## 首先执行

```bash
robotctl version
robotctl health
robotctl monitor
```

它们分别用于确认运行版本、健康状态和控制循环现场。

## 常用操作

```bash
sudo robotctl configure
robotctl policy list
sudo robotctl policy update
robotctl net status
sudo robotctl net connect <ssid> --psk-stdin
robotctl update status
sudo robotctl update apply daemon
sudo robotctl update rollback daemon
```

机器人还支持游戏手柄、声音、chorale、theremin、ToF、WebRTC 和蓝牙控制。
执行会让机器人移动、断网、重启或修改策略的命令前，应先确认周围没有障碍物，并阅读
对应章节的安全说明。

英文源文档：[cheatsheet.md](cheatsheet.md)。
