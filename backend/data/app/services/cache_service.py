import json
import os
import time
from typing import Any, Optional
import logging

logger = logging.getLogger(__name__)

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

class CacheService:
    @staticmethod
    def get(key: str, ttl_seconds: Optional[int] = None) -> Optional[Any]:
        filepath = os.path.join(CACHE_DIR, f"{key}.json")
        if not os.path.exists(filepath):
            return None
        
        try:
            if ttl_seconds is not None:
                mtime = os.path.getmtime(filepath)
                if time.time() - mtime > ttl_seconds:
                    return None
                    
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Cache read error for {key}: {e}")
            return None

    @staticmethod
    def set(key: str, data: Any) -> None:
        filepath = os.path.join(CACHE_DIR, f"{key}.json")
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f)
        except Exception as e:
            logger.error(f"Cache write error for {key}: {e}")
            
    @staticmethod
    def invalidate_all():
        for f in os.listdir(CACHE_DIR):
            if f.endswith(".json"):
                try:
                    os.remove(os.path.join(CACHE_DIR, f))
                except:
                    pass
