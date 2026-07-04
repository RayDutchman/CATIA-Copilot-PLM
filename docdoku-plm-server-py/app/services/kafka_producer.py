"""Kafka 生产者，发送 CAD 转换任务。与 Payara ConverterBean 消息格式兼容。"""
import json
import logging
from kafka import KafkaProducer
from app.core.config import settings

logger = logging.getLogger(__name__)

_producer: KafkaProducer | None = None


def _get_producer() -> KafkaProducer:
    """懒初始化 Kafka producer（单例）。"""
    global _producer
    if _producer is None:
        _producer = KafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS.split(","),
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
    return _producer


def send_conversion_order(
    workspace_id: str,
    part_number: str,
    version: str,
    iteration: int,
    filename: str,
    user_token: str,
) -> None:
    """
    发送 CAD 转换任务到 Kafka topic CONVERT。
    消息为嵌套结构，与 conversion-service-py handle_order 契约一致：
      partIterationKey{workspaceId,partMasterNumber,partRevisionVersion,iteration}
      binaryResource{fullName(vault相对路径), name}
      userToken(回调 Bearer 认证用)
    """
    full_name = (
        f"{workspace_id}/parts/{part_number}/{version}/{iteration}"
        f"/nativecad/{filename}"
    )
    message = {
        "partIterationKey": {
            "workspaceId": workspace_id,
            "partMasterNumber": part_number,
            "partRevisionVersion": version,
            "iteration": iteration,
        },
        "binaryResource": {
            "fullName": full_name,
            "name": filename,
        },
        "userToken": user_token,
    }
    producer = _get_producer()
    producer.send(
        settings.KAFKA_CONVERSION_TOPIC,
        value=message,
    )
    producer.flush()
    logger.info(
        "已发送转换任务：%s/%s-%s iter=%d file=%s",
        workspace_id, part_number, version, iteration, filename,
    )
