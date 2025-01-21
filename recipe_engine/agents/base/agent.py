from typing import Optional, Dict, Any
from abc import ABC, abstractmethod
import redis

from config.settings import settings


class BaseAgent(ABC):
    """Base agent class with common functionality for all agents.
    
    This class provides:
    1. Model management
    2. Cache integration
    3. Basic error handling
    4. Common utility methods
    """
    
    def __init__(self, name: str):
        """Initialize the base agent.
        
        Args:
            name: Name of the agent for identification
        """
        self.name = name
        self.model = None
        self._setup_cache()
    
    def _setup_cache(self) -> None:
        """Initialize Redis cache connection."""
        try:
            self.cache = redis.from_url(settings.REDIS_URL)
        except Exception as e:
            print(f"Warning: Cache initialization failed: {str(e)}")
            self.cache = None
    
    def cache_get(self, key: str) -> Optional[str]:
        """Get value from cache.
        
        Args:
            key: Cache key to retrieve
            
        Returns:
            Cached value if exists, None otherwise
        """
        if not self.cache:
            return None
        try:
            return self.cache.get(key)
        except Exception as e:
            print(f"Cache get error: {str(e)}")
            return None
    
    def cache_set(self, key: str, value: str, expire: int = 3600) -> bool:
        """Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            expire: Expiration time in seconds (default: 1 hour)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.cache:
            return False
        try:
            return bool(self.cache.setex(key, expire, value))
        except Exception as e:
            print(f"Cache set error: {str(e)}")
            return False
    
    @abstractmethod
    async def run(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Run the agent's main task.
        
        This method must be implemented by all agent subclasses.
        """
        pass
