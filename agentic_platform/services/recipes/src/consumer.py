import asyncio
import os
import logging
from abc import ABC, abstractmethod

import aio_pika


class BaseConsumer(ABC):
    def __init__(self, queue_name: str):
        self.queue_name = queue_name
        self.rabbitmq_host = os.environ.get("RABBITMQ_HOST", "localhost")
        self.rabbitmq_port = int(os.environ.get("RABBITMQ_PORT", 5672))
        self.rabbitmq_user = os.environ.get("RABBITMQ_USER", "guest")
        self.rabbitmq_password = os.environ.get("RABBITMQ_PASSWORD", "guest")
        self.connection: aio_pika.Connection = None
        self.channel: aio_pika.Channel = None

    async def connect_to_rabbitmq(self):
        try:
            login = self.rabbitmq_user
            password = self.rabbitmq_password
            self.connection = await aio_pika.connect(
                host=self.rabbitmq_host,
                port=self.rabbitmq_port,
                login=login,
                password=password,
            )
            self.channel = await self.connection.channel()
            # Ensure queue arguments match existing queue configuration
            try:
                await self.channel.declare_queue(
                    self.queue_name,
                    durable=True,
                    arguments={
                        "x-queue-type": "quorum",
                        "x-max-length": 10000,
                        "x-max-length-bytes": 104857600,
                        "x-overflow": "reject-publish",
                    },
                )
                logging.info(f"Queue {self.queue_name} declared successfully.")
            except aio_pika.exceptions.ChannelPreconditionFailed as e:
                logging.warning(
                    f"Queue {self.queue_name} already declared with incompatible arguments, skipping declaration. Warning: {e}"
                )
            except Exception as e:
                logging.warning(
                    f"Error declaring queue {self.queue_name}, might already be declared. Error: {e}"
                )
            logging.info(f"Connected to RabbitMQ queue: {self.queue_name}")
        except Exception as e:
            logging.error(f"Error connecting to RabbitMQ: {e}")
            raise

    @abstractmethod
    async def process_message(
        self, channel: aio_pika.Channel, delivery: aio_pika.abc.AbstractIncomingMessage
    ):
        """Process message from queue"""
        pass

    async def start_consuming(self):
        try:
            try:
                queue = await self.channel.get_queue(self.queue_name)
            except aio_pika.exceptions.QueueEmpty as e:
                logging.warning(
                    f"Queue {self.queue_name} is empty or not yet ready.  Please ensure it is declared. Error: {e}"
                )
                return  # Or consider raising the exception again if you want to stop consuming on this error
            except Exception as e:
                logging.error(f"Error getting queue {self.queue_name}: {e}")
                raise  # Re-raise the exception to be caught in the main loop if necessary

            await queue.consume(self.process_message)
            logging.info(f"Start consuming from queue: {self.queue_name}")
        except Exception as e:
            logging.error(f"Error consuming from queue: {e}")

    async def close(self):
        if self.channel:
            await self.channel.close()
        if self.connection:
            await self.connection.close()
