# 远程访问设计

本文描述机器人如何从局域网外被访问。核心是一个能标识机器人的账户凭据，以及一个
负责在外部网络之间转发连接的 rendezvous 服务。

## 设计边界

- 账户凭据只用于证明机器人属于某个账户。
- rendezvous 服务负责发现和转发，不直接拥有机器人的控制权限。
- 机器人上的 WebRTC 信令和控制权限仍由本地服务决定。
- 本地网络访问不应依赖远程服务；远程服务不可用时，局域网功能仍应工作。
- 凭据需要可更新、可撤销，并且不能硬编码到机器人镜像中。

WebRTC 会话和控制通道见[远程 WebRTC](remote-webrtc_zh.md)；蓝牙侧入口见
[应用通道设计](app-path-design_zh.md)。

英文源文档：[remote-access-design.md](remote-access-design.md)。
