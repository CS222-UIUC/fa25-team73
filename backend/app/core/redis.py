import redis.asyncio as redis
from app.config import settings

# Global Redis client
redis_client: redis.Redis = None


async def get_redis_client() -> redis.Redis:
    """
    Get Redis client instance.

    Returns:
        Redis client
    """
    global redis_client
    if redis_client is None:
        redis_client = await redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return redis_client


async def close_redis_client():
    """Close Redis connection."""
    global redis_client
    if redis_client:
        await redis_client.close()
        redis_client = None
