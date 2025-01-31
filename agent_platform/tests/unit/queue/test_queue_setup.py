from unittest.mock import call
from queue_handler.queue_setup import QueueSetup, setup_rabbitmq
from config.queue_config import (
    AGENT_TASK_QUEUE,
    AGENT_RESULT_QUEUE,
    AGENT_DLQ,
    PREFETCH_COUNT,
    MESSAGE_TTL,
    RABBITMQ_DEFAULT_PRIORITY,
)


def test_queue_initialization(mocker):
    """Test QueueSetup initialization and configuration."""
    # Mock pika's connection setup
    mock_pika = mocker.patch("queue_handler.queue_setup.pika")
    mock_conn = mock_pika.BlockingConnection.return_value
    mock_channel = mock_conn.channel.return_value

    # Initialize QueueSetup
    qs = QueueSetup()

    # Verify connection setup
    mock_pika.PlainCredentials.assert_called_once()
    mock_pika.ConnectionParameters.assert_called_once()
    mock_pika.BlockingConnection.assert_called_once()

    # Verify QoS setting
    mock_channel.basic_qos.assert_called_once_with(prefetch_count=PREFETCH_COUNT)


def test_setup_queues(mocker):
    """Test queue declarations with correct parameters."""
    # Mock pika's connection setup
    mock_pika = mocker.patch("queue_handler.queue_setup.pika")
    mock_channel = mock_pika.BlockingConnection.return_value.channel.return_value

    # Setup queues
    qs = QueueSetup()
    qs.setup_queues()

    # Verify all queue declarations
    expected_calls = [
        # DLQ declaration
        call(queue=AGENT_DLQ, durable=True),
        # Task queue declaration
        call(
            queue=AGENT_TASK_QUEUE,
            durable=True,
            arguments={
                "x-dead-letter-exchange": "",
                "x-dead-letter-routing-key": AGENT_DLQ,
                "x-message-ttl": MESSAGE_TTL,
                "x-max-priority": RABBITMQ_DEFAULT_PRIORITY,
            },
        ),
        # Result queue declaration
        call(queue=AGENT_RESULT_QUEUE, durable=True),
    ]
    mock_channel.queue_declare.assert_has_calls(expected_calls, any_order=False)
    assert mock_channel.queue_declare.call_count == 3


def test_close_connection(mocker):
    """Test connection closure."""
    mock_pika = mocker.patch("queue_handler.queue_setup.pika")
    mock_conn = mock_pika.BlockingConnection.return_value
    mock_conn.is_closed = False

    qs = QueueSetup()
    qs.close()

    mock_conn.close.assert_called_once()


def test_setup_rabbitmq_success(mocker):
    """Test successful RabbitMQ setup."""
    mock_queue_setup = mocker.patch("queue_handler.queue_setup.QueueSetup")

    result = setup_rabbitmq()

    assert result is True
    mock_queue_setup.return_value.setup_queues.assert_called_once()
    mock_queue_setup.return_value.close.assert_called_once()


def test_setup_rabbitmq_failure(mocker):
    """Test RabbitMQ setup failure handling."""
    mock_queue_setup = mocker.patch("queue_handler.queue_setup.QueueSetup")
    mock_queue_setup.return_value.setup_queues.side_effect = Exception(
        "Connection failed"
    )

    result = setup_rabbitmq()

    assert result is False
    mock_queue_setup.return_value.setup_queues.assert_called_once()


def test_setup_queues_creates_dlq(mocker):
    """Test DLQ creation."""
    # Mock pika
    mock_pika = mocker.patch("queue_handler.queue_setup.pika")
    mock_channel = mock_pika.BlockingConnection.return_value.channel.return_value

    # Setup queues
    qs = QueueSetup()
    qs.setup_queues()

    # Verify DLQ was created
    mock_channel.queue_declare.assert_any_call(queue=AGENT_DLQ, durable=True)


def test_setup_queues_creates_task_queue(mocker):
    """Test task queue creation with correct settings."""
    # Mock pika
    mock_pika = mocker.patch("queue_handler.queue_setup.pika")
    mock_channel = mock_pika.BlockingConnection.return_value.channel.return_value

    # Setup queues
    qs = QueueSetup()
    qs.setup_queues()

    # Verify task queue was created with correct settings
    mock_channel.queue_declare.assert_any_call(
        queue=AGENT_TASK_QUEUE,
        durable=True,
        arguments={
            "x-dead-letter-exchange": "",
            "x-dead-letter-routing-key": AGENT_DLQ,
            "x-message-ttl": MESSAGE_TTL,
            "x-max-priority": RABBITMQ_DEFAULT_PRIORITY,
        },
    )
