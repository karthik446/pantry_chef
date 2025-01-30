"""RabbitMQ queue setup using work queues pattern."""

import pika
from loguru import logger
from config.queue_config import (
    AGENT_TASK_QUEUE,
    AGENT_RESULT_QUEUE,
    AGENT_DLQ,
    PREFETCH_COUNT,
    MESSAGE_TTL,
    RABBITMQ_HOST,
    RABBITMQ_PORT,
    RABBITMQ_USER,
    RABBITMQ_PASSWORD,
)


class QueueSetup:
    def __init__(self, host=RABBITMQ_HOST, port=RABBITMQ_PORT):
        """Initialize RabbitMQ connection and channel."""
        credentials = pika.PlainCredentials(
            username=RABBITMQ_USER, password=RABBITMQ_PASSWORD
        )
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=host, port=port, credentials=credentials)
        )
        self.channel = self.connection.channel()
        # Enable fair dispatch
        self.channel.basic_qos(prefetch_count=PREFETCH_COUNT)

    def setup_queues(self):
        """Setup work queues with proper configuration."""
        # Declare dead letter queue
        self.channel.queue_declare(queue=AGENT_DLQ, durable=True)

        # Declare main task queue with dead letter config
        self.channel.queue_declare(
            queue=AGENT_TASK_QUEUE,
            durable=True,
            arguments={
                "x-dead-letter-exchange": "",
                "x-dead-letter-routing-key": AGENT_DLQ,
                "x-message-ttl": MESSAGE_TTL,
            },
        )

        # Declare result queue
        self.channel.queue_declare(queue=AGENT_RESULT_QUEUE, durable=True)

        logger.info("Work queues setup completed successfully")

    def close(self):
        """Close the connection."""
        if not self.connection.is_closed:
            self.connection.close()
            logger.info("Queue connection closed")


def setup_rabbitmq():
    """Setup RabbitMQ queues and exchanges."""
    try:
        queue_setup = QueueSetup()
        queue_setup.setup_queues()
        queue_setup.close()
        return True
    except Exception as e:
        logger.error(f"Failed to setup RabbitMQ: {str(e)}")
        return False
