"""
cache/redis_client.py
Redis is an OPTIONAL caching layer. If Redis is unavailable, all functions
return None/0/False/[] and callers fall through to Qdrant. Never raise.
"""
import json
import logging
import os

logger = logging.getLogger(__name__)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")


def get_redis():
    """Return a Redis client or None if unavailable."""
    try:
        import redis as redis_lib
        client = redis_lib.from_url(REDIS_URL, decode_responses=True, socket_connect_timeout=2)
        client.ping()
        return client
    except Exception as exc:
        logger.warning("Redis unavailable (%s) — cache disabled", exc)
        return None


def cache_get(key: str):
    """Get JSON value from Redis. Returns None on miss or error."""
    r = get_redis()
    if r is None:
        return None
    try:
        val = r.get(key)
        return json.loads(val) if val else None
    except Exception as exc:
        logger.warning("Redis GET '%s' failed: %s", key, exc)
        return None


def cache_set(key: str, value, ttl: int = 86400) -> bool:
    """Set JSON value in Redis with TTL seconds. Returns True on success."""
    r = get_redis()
    if r is None:
        return False
    try:
        r.setex(key, ttl, json.dumps(value))
        return True
    except Exception as exc:
        logger.warning("Redis SET '%s' failed: %s", key, exc)
        return False


def cache_delete_pattern(pattern: str) -> int:
    """Delete all keys matching glob pattern. Returns count deleted."""
    r = get_redis()
    if r is None:
        return 0
    try:
        keys = r.keys(pattern)
        return r.delete(*keys) if keys else 0
    except Exception as exc:
        logger.warning("Redis DELETE '%s' failed: %s", pattern, exc)
        return 0


def cache_status() -> list[dict]:
    """Return all prices:/chart: keys with TTL. Returns [] if Redis down."""
    r = get_redis()
    if r is None:
        return []
    try:
        keys = sorted(r.keys("prices:*") + r.keys("chart:*"))
        return [{"key": k, "ttl_seconds": r.ttl(k)} for k in keys]
    except Exception as exc:
        logger.warning("Redis STATUS failed: %s", exc)
        return []
