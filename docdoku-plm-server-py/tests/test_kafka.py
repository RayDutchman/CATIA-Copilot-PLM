from unittest.mock import patch, MagicMock
from app.services.kafka_producer import send_conversion_order

def test_send_conversion_order_calls_producer():
    """send_conversion_order 应调用 Kafka producer 发送消息。"""
    with patch("app.services.kafka_producer._get_producer") as mock_get:
        mock_producer = MagicMock()
        mock_get.return_value = mock_producer

        send_conversion_order("WS1", "PART-001", "A", 1, "model.stp", "tok123")

        mock_producer.send.assert_called_once()
        call_args = mock_producer.send.call_args
        assert call_args[0][0] == "CONVERT"

def test_conversion_order_message_structure():
    """发送的消息为嵌套结构，含 partIterationKey/binaryResource/userToken。"""
    with patch("app.services.kafka_producer._get_producer") as mock_get:
        mock_producer = MagicMock()
        mock_get.return_value = mock_producer

        send_conversion_order("WS1", "PART-001", "A", 2, "model.stp", "tok123")

        msg = mock_producer.send.call_args[1]["value"]
        key = msg["partIterationKey"]
        assert key["workspaceId"] == "WS1"
        assert key["partMasterNumber"] == "PART-001"
        assert key["partRevisionVersion"] == "A"
        assert key["iteration"] == 2
        assert msg["binaryResource"]["fullName"] == \
            "WS1/parts/PART-001/A/2/nativecad/model.stp"
        assert msg["binaryResource"]["name"] == "model.stp"
        assert msg["userToken"] == "tok123"
