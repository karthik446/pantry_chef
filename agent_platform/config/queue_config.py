"""Queue configuration constants."""

import os

# Queue names (using work queues pattern)
AGENT_TASK_QUEUE = "agent.tasks"  # Main work queue for agents
AGENT_RESULT_QUEUE = "agent.results"
AGENT_DLQ = "agent.dlq"

# RabbitMQ connection settings
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", 5672))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "user")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "rabbitmq")

# Message types (for routing different agent tasks)
MESSAGE_TYPES = {
    "RECIPE_SEARCH": "recipe.search",
    "RECIPE_PARSE": "recipe.parse",
    "RESEARCH": "research",
    # Add more message types as needed
}

# Priority configuration (should match PriorityLevel enum in messages.py)
NUM_PRIORITY_LEVELS = 4  # Total number of priority levels
RABBITMQ_DEFAULT_PRIORITY = (
    NUM_PRIORITY_LEVELS - 1
)  # RabbitMQ requires max priority value (0-based)

# Queue settings
PREFETCH_COUNT = 1  # Ensure fair dispatch
MESSAGE_TTL = 300000  # 5 minutes in milliseconds
