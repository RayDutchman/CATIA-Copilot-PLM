from unittest.mock import patch, MagicMock
from app.services.kafka_producer import send_conversion_order

def test_send_conversion_order_calls_producer():
    """send_conversion_order 应调用 Kafka producer 发送消息。"""
    with patch("app.services.kafka_producer._get_producer") as mock_get:
        mock_producer = MagicMock()
        mock_get.return_value = mock_producer

        send_conversion_order("WS1", "PART-001", "A", 1, "model.stp")

        mock_producer.send.assert_called_once()
        call_args = mock_producer.send.call_args
        # 第一个参数是 topic 名称
        assert call_args[0][0] == "docdoku-conversions"

def test_conversion_order_message_structure():
    """发送的消息体包含必要的字段。"""
    with patch("app.services.kafka_producer._get_producer") as mock_get:
        mock_producer = MagicMock()
        mock_get.return_value = mock_producer

        send_conversion_order("WS1", "PART-001", "A", 1, "model.stp")

        msg = mock_producer.send.call_args[1]["value"]
        assert msg["workspaceId"] == "WS1"
        assert msg["partNumber"] == "PART-001"
        assert msg["version"] == "A"
        assert msg["iteration"] == 1
