from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.core.redis import get_redis_client, close_redis_client
from app.api.v1 import health
from app.api import transcript, fetch_transcript


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    """
    # Startup
    print("Starting LiveCheck API...")

    # Initialize Redis connection
    try:
        redis = await get_redis_client()
        await redis.ping()
        print("Redis connection established")
    except Exception as e:
        print(f"Warning: Redis connection failed: {e}")

    yield

    # Shutdown
    print("Shutting down LiveCheck API...")
    await close_redis_client()


# Create FastAPI application
app = FastAPI(
    title="LiveCheck API",
    version="1.0.0",
    description="YouTube video fact-checking backend (simplified MVP)",
    lifespan=lifespan
)

# CORS middleware - allow Chrome extension origins
# origins = settings.CORS_ORIGINS.split(",") if "," in settings.CORS_ORIGINS else [settings.CORS_ORIGINS]
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=origins + ["http://localhost:3000", "*"],  # Add localhost for development
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change this from [] to ["*"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(transcript.router, prefix="/api", tags=["transcript"])
app.include_router(fetch_transcript.router, tags=["transcript"])
app.include_router(health.router, prefix="/api/v1/health", tags=["health"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "LiveCheck API",
        "version": "1.0.0",
        "description": "YouTube video fact-checking (simplified MVP)",
        "status": "running",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.ENVIRONMENT == "development"
    )
