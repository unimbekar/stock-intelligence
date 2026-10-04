from __future__ import annotations

import time
from collections import defaultdict

import redis
from meridian_config.settings import Settings


class RateLimiter:
    def __init__(self, settings: Settings) -> None:
        self.limit = settings.rate_limit_per_minute
        self._memory: dict[str, tuple[int, int]] = defaultdict(lambda: (0, 0))
        self._redis: redis.Redis | None
        try:
            client = redis.Redis.from_url(settings.redis_url, socket_connect_timeout=0.2, socket_timeout=0.2)
            client.ping()
            self._redis = client
        except redis.RedisError:
            self._redis = None

    def allow(self, key: str) -> bool:
        bucket = int(time.time() // 60)
        if self._redis is not None:
            try:
                redis_key = f"meridian:rl:{key}:{bucket}"
                count = int(self._redis.incr(redis_key))
                if count == 1:
                    self._redis.expire(redis_key, 120)
                return count <= self.limit
            except redis.RedisError:
                self._redis = None
        window, count = self._memory[key]
        if window != bucket:
            window, count = bucket, 0
        count += 1
        self._memory[key] = (window, count)
        return count <= self.limit
