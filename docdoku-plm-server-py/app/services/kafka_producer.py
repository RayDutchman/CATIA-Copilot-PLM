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
) -> None:
    """
    发送 CAD 转换任务到 Kafka。
    消息格式与 Payara ConverterBean.convertFile() 兼容，conversion 容器能直接消费。
    """
    message = {
        "workspaceId": workspace_id,
        "partNumber": part_number,
        "version": version,
        "iteration": iteration,
        "filename": filename,
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
