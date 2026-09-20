# 机器人守护进程：总体架构

Microduck 由多个职责单一的 Rust 服务组成。各服务通过 Unix socket 上的 JSON-RPC
协议通信，避免把网络、硬件和更新逻辑耦合到同一个进程。

## 服务职责

- `robotd`：50 Hz 控制循环、电机总线、策略、姿态和安全。
- `updaterd`：版本存储、签名校验、安装、健康检查和回滚。
- `configd`：Wi-Fi、机器人名称、PIN 和系统设置。
- `btd`：蓝牙入口和手机访问通道。
- `padd`：游戏手柄输入。
- `mediad`：摄像头、麦克风和 WebRTC。
- `tofd`：深度传感器。

## 核心原则

状态应由唯一服务拥有，硬件总线不能被多个进程同时访问，客户端通过统一 IPC 契约
请求操作。更新必须可验证、可恢复，并且不能绕过健康检查破坏机器人。

发布顺序和当前里程碑见[路线图](../project/roadmap_zh.md)。更新细节见
[更新系统设计](updater-design_zh.md)。

英文源文档：[architecture.md](architecture.md)。
