from redis import Redis
from typing import Optional, Any
import json
from loguru import logger
from config.redis_config import (
    REDIS_HOST,
    REDIS_PORT,
    REDIS_PASSWORD,
)
import os


class RedisClient:
    """Redis client for caching."""

    def __init__(self):
        self.redis = Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            password=REDIS_PASSWORD,
            decode_responses=True,
        )

    def set(self, key: str, value: Any, expiry: Optional[int] = None) -> bool:
        """Set a key-value pair in Redis."""
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            self.redis.set(key, value, ex=expiry)
            return True
        except Exception as e:
            logger.error(f"Redis set error: {str(e)}")
            return False

    def get(self, key: str, as_json: bool = False) -> Any:
        """Get a value from Redis."""
        try:
            value = self.redis.get(key)
            if value and as_json:
                return json.loads(value)
            return value
        except Exception as e:
            logger.error(f"Redis get error: {str(e)}")
            return None

    def delete(self, key: str) -> bool:
        """Delete a key from Redis."""
        try:
            self.redis.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis delete error: {str(e)}")
            return False
