import redis
import json
from typing import Optional, Any
import pickle
from functools import lru_cache
from loguru import logger
from app.config.settings import settings

class CacheManager:
    """Redis-based cache for improved scalability"""
    
    def __init__(self):
        self.redis_client = redis.Redis(
            host='localhost',
            port=6379,
            db=0,
            decode_responses=True
        )
        self.local_cache = {}
    
    def get(self, key: str, use_local: bool = True) -> Optional[Any]:
        """Get value from cache"""
        try:
            # Try local cache first
            if use_local and key in self.local_cache:
                return self.local_cache[key]
            
            # Try Redis
            value = self.redis_client.get(key)
            if value:
                result = json.loads(value)
                # Update local cache
                if use_local:
                    self.local_cache[key] = result
                return result
        except Exception as e:
            logger.warning(f"Cache get error: {e}")
        return None
    
    def set(self, key: str, value: Any, ttl: int = 3600, use_local: bool = True):
        """Set value in cache"""
        try:
            # Set in Redis
            serialized = json.dumps(value)
            self.redis_client.setex(key, ttl, serialized)
            
            # Update local cache
            if use_local:
                self.local_cache[key] = value
        except Exception as e:
            logger.warning(f"Cache set error: {e}")
    
    def invalidate(self, key: str):
        """Invalidate cache entry"""
        try:
            self.redis_client.delete(key)
            if key in self.local_cache:
                del self.local_cache[key]
        except Exception as e:
            logger.warning(f"Cache invalidation error: {e}")
    
    def cache_response(self, func):
        """Decorator for caching function responses"""
        @lru_cache(maxsize=128)
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # Try to get from cache
            cached = self.get(cache_key)
            if cached is not None:
                return cached
            
            # Call function and cache result
            result = func(*args, **kwargs)
            self.set(cache_key, result, ttl=300)
            return result
        return wrapper