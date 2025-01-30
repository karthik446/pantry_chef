"""Redis configuration constants."""

import os

# Redis connection settings
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")

# Cache keys
AUTH_TOKEN_KEY = "auth:tokens"
AUTH_TOKEN_EXPIRY = 3600  # 1 hour in seconds
