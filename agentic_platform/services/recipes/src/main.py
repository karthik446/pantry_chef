import asyncio
import logging
import os
import sys

from workflow_consumer import main as workflow_consumer_main

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def main():
    """Main function to start the RecipeAgentService."""
    logging.info("Starting RecipeAgentService...")

    # Start the workflow command consumer and metrics consumer
    asyncio.run(workflow_consumer_main())

    logging.info("RecipeAgentService started successfully.")


if __name__ == "__main__":
    main()
