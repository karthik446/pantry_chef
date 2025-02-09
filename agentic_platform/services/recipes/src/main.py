import logging
import os
import sys

from workflow_consumer import start_workflow_command_consumer

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def main():
    """Main function to start the RecipeAgentService."""
    logging.info("Starting RecipeAgentService...")

    # Start the workflow command consumer
    start_workflow_command_consumer()

    logging.info("RecipeAgentService started successfully.")


if __name__ == "__main__":
    main()
