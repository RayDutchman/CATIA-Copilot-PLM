"""WebSocket 服务（对标 Java ws/ 包 — WebRTC 信令 + 聊天 + 协同 + 状态广播）。

FastAPI 原生支持 WebSocket，无需 JSR-356 式的 @ServerEndpoint。
核心适配：
- WebSocketApplication → FastAPI websocket 路由 handler
- WebSocketMessage → JSON dict with 'type' discriminator
- WebSocketSessionsManager → user_login → List[WebSocket] 的映射
- WebSocketModule → 可插拔的消息处理模块
"""
