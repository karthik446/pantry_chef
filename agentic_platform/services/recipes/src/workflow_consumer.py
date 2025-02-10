import pika
import os
import json
import logging
import asyncio

import uuid

from workflow_orchestrator import WorkflowOrchestrator
from recipe_consumer import RecipeConsumer
from metrics_consumer import MetricsConsumer


async def main():
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    recipe_consumer = RecipeConsumer()
    metrics_consumer = MetricsConsumer()

    try:
        await recipe_consumer.connect_to_rabbitmq()
        await metrics_consumer.connect_to_rabbitmq()

        asyncio.create_task(recipe_consumer.start_consuming())
        asyncio.create_task(metrics_consumer.start_consuming())

        await asyncio.Future()  # Run forever
    except Exception as e:
        logging.error(f"Main error: {e}")
    finally:
        await recipe_consumer.close()
        await metrics_consumer.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Exiting")
