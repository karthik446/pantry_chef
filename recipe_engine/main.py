from agents.manager.manager_agent import ManagerAgent
from loguru import logger
import sys

# Configure logger
logger.remove()  # Remove default handler
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO"
)
logger.add(
    "logs/recipe_engine.log",
    rotation="500 MB",
    retention="10 days",
    level="DEBUG"
)

def main():
    """Main entry point for the recipe engine."""
    try:
        # Initialize manager agent
        logger.info("Initializing manager agent...")
        manager = ManagerAgent()
        
        # Test recipe search
        query = "korean spicy chicken"
        logger.info(f"Searching for recipe: {query}")
        result = manager.search_recipe(query)
        
        if "error" in result:
            logger.error(f"Search failed: {result['error']}")
        else:
            logger.success("Recipe search successful!")
            logger.debug(f"Search result: {result}")
            
    except Exception as e:
        logger.exception(f"Application error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 