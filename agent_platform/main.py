from loguru import logger
import sys
from queue.setup import setup_rabbitmq

# Configure logger
logger.remove()  # Remove default handler
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO",
)
logger.add(
    "logs/agent_platform.log", rotation="500 MB", retention="10 days", level="DEBUG"
)


def main():
    """Main entry point for the agent platform."""
    try:
        # Setup RabbitMQ queues
        logger.info("Setting up RabbitMQ queues...")
        if not setup_rabbitmq():
            logger.error("Failed to setup RabbitMQ queues")
            sys.exit(1)
        logger.success("RabbitMQ queues setup complete")

        # Initialize manager agent
        logger.info("Initializing manager agent...")
        # TODO: Implement manager agent with queue consumers

        # Keep the application running
        logger.info("Agent platform running. Press CTRL+C to exit.")
        try:
            # Block until keyboard interrupt
            input()
        except KeyboardInterrupt:
            logger.info("Shutting down agent platform...")

    except Exception as e:
        logger.exception(f"Application error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
