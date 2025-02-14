import asyncio
import os
import json
import logging

import aio_pika
from pydantic import ValidationError

from consumer import BaseConsumer
from event_models import MetricsEvent


class InvalidMessageError(Exception):
    """Custom exception for invalid messages."""

    pass


class MetricsConsumer(BaseConsumer):
    def __init__(self):
        queue_name = os.environ.get("METRICS_QUEUE_NAME", "metrics_queue")
        super().__init__(queue_name)

    async def process_message(self, delivery: aio_pika.abc.AbstractIncomingMessage):
        try:
            body = delivery.body.decode("utf-8")
            message_data = json.loads(body)
            logging.info(f"Received metrics message: {message_data}")

            try:
                MetricsEvent.model_validate(message_data)
            except ValidationError as e:
                raise InvalidMessageError(f"Invalid metrics message: {e}")

            logging.info(f"Received metrics message: {message_data}")

            event_type = message_data.get("event_type")
            duration = message_data.get("duration")
            metadata = message_data.get("metadata")
            timestamp = message_data.get("timestamp")

            log_message = f"Event Type: {event_type}, Duration: {duration}, Metadata: {metadata}, Timestamp: {timestamp}"
            logging.info(log_message)

            await delivery.ack()
            logging.info(f"Acknowledged message: {delivery.delivery_tag}")

        except json.JSONDecodeError as e:
            logging.error(f"Error decoding JSON: {e}")
            await delivery.nack(requeue=False)
        except Exception as e:
            logging.error(f"Error processing metrics message: {e}")
            await delivery.nack(requeue=True)


async def main():
    consumer = MetricsConsumer()
    try:
        await consumer.connect_to_rabbitmq()
        await consumer.start_consuming()
        await asyncio.Future()  # Run forever
    except Exception as e:
        logging.error(f"Main error: {e}")
    finally:
        await consumer.close()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Exiting")
