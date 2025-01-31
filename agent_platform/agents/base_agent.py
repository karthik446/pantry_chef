from abc import ABC, abstractmethod
import pika
from typing import Dict, Optional, Set
from loguru import logger
import json


from models.messages import AgentMessage, MessageStatus, ErrorDetail, MessageType
from queue_handler.queue_setup import AGENT_DLQ
from services.auth import AuthService
from config.queue_config import (
    AGENT_TASK_QUEUE,
    AGENT_RESULT_QUEUE,
    RABBITMQ_HOST,
    RABBITMQ_PORT,
    RABBITMQ_USER,
    RABBITMQ_PASSWORD,
)


class BaseAgent(ABC):
    """Base class for all agents in the platform."""

    MAX_RETRIES = 3
    RETRY_DELAYS = [5, 15, 30]  # Retry delays in seconds

    def __init__(self, agent_id: str, base_url: str):
        self.agent_id = agent_id
        self.auth_service = AuthService(base_url)
        if not self.auth_service.initialize_auth():
            raise Exception("Failed to initialize authentication")
        self._setup_connection()
        self.tools = {}  # Tool registry
        self.supported_message_types: Set[MessageType] = set()
        self.message_handlers: Dict[MessageType, callable] = (
            {}
        )  # Store handler functions for each message type

    def _setup_connection(self):
        """Setup RabbitMQ connection and channel."""
        credentials = pika.PlainCredentials(
            username=RABBITMQ_USER, password=RABBITMQ_PASSWORD
        )
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=RABBITMQ_HOST, port=RABBITMQ_PORT, credentials=credentials
            )
        )
        self.channel = self.connection.channel()
        self.channel.basic_qos(prefetch_count=1)

    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for API requests."""
        return self.auth_service.get_headers()

    def register_tool(self, name: str, tool_func: callable):
        """Register a tool for the agent to use."""
        self.tools[name] = tool_func
        logger.info(f"Registered tool: {name}")

    def register_message_handler(self, message_type: MessageType, handler: callable):
        """
        Register a handler function for a specific message type.

        Args:
            message_type (MessageType): Type of message to handle
            handler (callable): Async function that takes AgentMessage and returns AgentMessage
        """
        self.supported_message_types.add(message_type)
        self.message_handlers[message_type] = handler
        logger.info(f"Registered handler for message type: {message_type}")

    @abstractmethod
    async def process_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Process incoming message using registered handler."""
        handler = self.message_handlers.get(message.message_type)
        if not handler:
            raise ValueError(
                f"No handler registered for message type: {message.message_type}"
            )

        return await handler(message)

    def publish_result(self, message: AgentMessage):
        """Publish result to result queue."""
        try:
            self.channel.basic_publish(
                exchange="",
                routing_key=AGENT_RESULT_QUEUE,
                body=message.model_dump_json(),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Make message persistent
                    content_type="application/json",
                ),
            )
            logger.info(f"Published result for message: {message.message_id}")
        except Exception as e:
            logger.error(f"Error publishing result: {str(e)}")

    def start_consuming(self):
        """Start consuming messages from task queue."""
        try:
            self.channel.basic_consume(
                queue=AGENT_TASK_QUEUE, on_message_callback=self._message_callback
            )
            logger.info(f"Agent {self.agent_id} started consuming messages")
            self.channel.start_consuming()
        except Exception as e:
            logger.error(f"Error consuming messages: {str(e)}")

    async def _message_callback(self, ch, method, properties, body):
        """Handle incoming messages with error handling."""
        try:
            message_data = json.loads(body)
            message = AgentMessage(**message_data)

            # Validate message type support
            if message.message_type not in self.supported_message_types:
                raise ValueError(f"Unsupported message type: {message.message_type}")

            # Validate payload
            message.validate_payload()

            # Update message status
            message.status = MessageStatus.PROCESSING
            message.agent_id = self.agent_id

            try:
                # Process message
                result = await self.process_message(message)

                if result:
                    result.status = MessageStatus.COMPLETED
                    self.publish_result(result)

                # Acknowledge message
                ch.basic_ack(delivery_tag=method.delivery_tag)

            except Exception as e:
                # Handle processing error
                error_details = self._handle_processing_error(message, e)

                if message.retry_count < self.MAX_RETRIES:
                    # Negative ack and retry
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
                    logger.warning(
                        f"Retrying message {message.message_id}. Attempt {message.retry_count + 1}"
                    )
                else:
                    # Max retries reached, send to DLQ
                    message.status = MessageStatus.FAILED
                    self._send_to_dlq(message, error_details)
                    ch.basic_ack(delivery_tag=method.delivery_tag)

        except Exception as e:
            logger.error(f"Critical error in message handling: {str(e)}")
            # Negative ack in case of critical errors
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    def _handle_processing_error(
        self, message: AgentMessage, error: Exception
    ) -> ErrorDetail:
        """Handle processing errors and update message."""
        error_detail = ErrorDetail(
            code="PROCESSING_ERROR",
            message=str(error),
            details={"error_type": error.__class__.__name__, "agent_id": self.agent_id},
        )
        message.error = error_detail
        message.retry_count += 1
        return error_detail

    def _send_to_dlq(self, message: AgentMessage, error_detail: ErrorDetail):
        """Send failed message to Dead Letter Queue."""
        try:
            message.error = error_detail
            self.channel.basic_publish(
                exchange="",
                routing_key=AGENT_DLQ,
                body=message.model_dump_json(),
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    content_type="application/json",
                    headers={"error": error_detail.model_dump_json()},
                ),
            )
            logger.error(
                f"Message {message.message_id} sent to DLQ: {error_detail.message}"
            )
        except Exception as e:
            logger.error(f"Failed to send message to DLQ: {str(e)}")

    def cleanup(self):
        """Cleanup connections."""
        if not self.connection.is_closed:
            self.connection.close()
