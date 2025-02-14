import asyncio
import os
import json
import logging

import aio_pika
from pydantic import ValidationError

from consumer import BaseConsumer
from workflow_orchestrator import WorkflowOrchestrator
from event_models import WorkflowInitiateMessage


class InvalidMessageError(Exception):
    """Custom exception for invalid messages."""

    pass


class RecipeConsumer(BaseConsumer):
    def __init__(self):
        queue_name = os.environ.get("WORKFLOW_MESSAGES_QUEUE_NAME", "workflow_messages")
        super().__init__(queue_name)

    async def process_message(self, message: aio_pika.abc.AbstractIncomingMessage):
        try:
            body = message.body.decode("utf-8")
            message_data = json.loads(body)

            try:
                WorkflowInitiateMessage.model_validate(message_data)
            except ValidationError as e:
                raise InvalidMessageError(f"Invalid workflow initiate message: {e}")

            logging.info(f"Received workflow message: {message_data}")

            workflow_type = message_data.get("workflow_type")
            workflow_payload = message_data.get("workflow_payload")

            workflow_orchestrator = WorkflowOrchestrator()
            await workflow_orchestrator._connect_to_rabbitmq()
            await workflow_orchestrator.initiate_workflow(
                workflow_type, workflow_payload
            )

            logging.info(
                f"Workflow Type: {workflow_type}, Workflow Payload: {workflow_payload}"
            )

            await message.ack()
            logging.info(f"Acknowledged message: {message.delivery_tag}")

        except InvalidMessageError as e:
            logging.error(e)
            await message.nack(requeue=False)
        except json.JSONDecodeError as e:
            logging.error(f"Error decoding JSON: {e}")
            await message.nack(requeue=False)
        except Exception as e:
            logging.error(f"Error processing message: {e}")
            await message.nack(requeue=True)


async def main():
    consumer = RecipeConsumer()
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
