import logging
from typing import Any, Optional
from datetime import datetime, timedelta
from app.config import settings

logger = logging.getLogger(__name__)


class CacheStore:
    def __init__(self, ttl_seconds: int = 30):
        self.ttl = ttl_seconds
        self.store = {}

    def get(self, key: str) -> Optional[Any]:
        if key not in self.store:
            return None

        data, timestamp = self.store[key]
        if datetime.now() - timestamp > timedelta(seconds=self.ttl):
            del self.store[key]
            return None

        return data

    def set(self, key: str, value: Any):
        self.store[key] = (value, datetime.now())

    def clear(self):
        self.store.clear()

    def stats(self):
        return {
            "items": len(self.store),
            "ttl": self.ttl
        }


cache = CacheStore(ttl_seconds=settings.cache_ttl)
