from fastapi import APIRouter
from app.core.redis import get_redis_client
from app.config import settings

router = APIRouter()


@router.get("")
async def health_check():
    """
    Health check endpoint.

    Returns:
        Health status of all services
    """
    health_status = {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "redis": "disconnected",
        "openai": "configured" if settings.OPENAI_API_KEY else "not_configured"
    }

    # Check Redis
    try:
        redis = await get_redis_client()
        await redis.ping()
        health_status["redis"] = "connected"
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["redis"] = f"error: {str(e)}"

    return health_status
