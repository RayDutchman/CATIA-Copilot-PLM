"""转换订单 DTO（对标 ConversionOrder — Kafka 消息体）。"""
from dataclasses import dataclass


@dataclass
class ConversionOrder:
    """发给 conversion-service 的 Kafka 转换订单。"""
    workspace_id: str
    part_number: str
    version: str
    iteration: int
    file_name: str           # 源文件名称
    file_full_name: str      # vault 中完整路径
    user_token: str = ""     # 回调认证 token
