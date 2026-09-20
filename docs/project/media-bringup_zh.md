# 硬件上的媒体验证

本文记录 Radxa Zero 3W 上的视频链路验证结果。`mediad` 需要硬件 H.264 编码，
GStreamer 的 Rockchip MPP 插件以及 WebRTC 相关插件必须与板上驱动匹配。

## 结论

- 软件编码不能满足目标帧率，因此不能作为简单替代。
- 摄像头、编码器、WebRTC sink/source 和控制数据通道必须一起验证。
- 分辨率、帧率和码率配置会直接影响 CPU、延迟和稳定性。
- 没有摄像头时应使用明确的测试图或返回清晰错误，而不是让控制通道静默失效。

部署脚本和插件版本以当前仓库配置为准。

英文源文档：[media-bringup.md](media-bringup.md)。
