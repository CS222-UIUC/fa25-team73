import json
from typing import Optional, Dict
from app.core.redis import get_redis_client
from app.config import settings


class CacheService:
    """Redis cache service for storing verified claims by video ID."""

    def __init__(self):
        self.ttl = settings.CACHE_TTL_SECONDS

    async def get_video_claims(self, video_id: str) -> Optional[Dict]:
        """
        Get cached claims for a video.

        Args:
            video_id: YouTube video ID

        Returns:
            Cached claims data or None if not found
        """
        redis = await get_redis_client()
        key = f"video:{video_id}"

        try:
            cached_data = await redis.get(key)
            if cached_data:
                return json.loads(cached_data)
            return None
        except Exception as e:
            print(f"Error getting cached claims: {e}")
            return None

    async def set_video_claims(self, video_id: str, claims_data: Dict):
        """
        Cache claims for a video.

        Args:
            video_id: YouTube video ID
            claims_data: Claims data to cache
        """
        redis = await get_redis_client()
        key = f"video:{video_id}"

        try:
            await redis.setex(
                key,
                self.ttl,
                json.dumps(claims_data)
            )
        except Exception as e:
            print(f"Error caching claims: {e}")

    async def invalidate_video(self, video_id: str):
        """
        Invalidate cached claims for a video.

        Args:
            video_id: YouTube video ID
        """
        redis = await get_redis_client()
        key = f"video:{video_id}"

        try:
            await redis.delete(key)
        except Exception as e:
            print(f"Error invalidating cache: {e}")
