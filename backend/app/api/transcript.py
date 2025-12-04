from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List

from app.services.claim_service import ClaimService
from app.services.cache import CacheService

router = APIRouter()


class TranscriptSegment(BaseModel):
    """Single transcript segment with timing."""
    text: str
    start: float = Field(..., ge=0.0)
    duration: float = Field(..., ge=0.0)


class VerifyTranscriptRequest(BaseModel):
    """Request model for transcript verification."""
    video_id: str = Field(..., min_length=1, max_length=100)
    transcript: List[TranscriptSegment] = Field(..., min_items=1)


class ClaimResult(BaseModel):
    """Single verified claim."""
    claim: str
    verdict: str  # True/False/Mixed/Unverified
    confidence: float = Field(..., ge=0.0, le=1.0)
    explanation: str
    timestamp: float
    sources: List[str] = []


class VerifyTranscriptResponse(BaseModel):
    """Response model for transcript verification."""
    video_id: str
    claims: List[ClaimResult]
    cached: bool = False


@router.post("/verify-transcript", response_model=VerifyTranscriptResponse)
async def verify_transcript(request: VerifyTranscriptRequest):
    """
    Process entire YouTube transcript and extract/verify all claims.

    This endpoint:
    1. Checks cache for existing results (by video_id)
    2. If not cached, processes entire transcript with OpenAI
    3. Returns all claims with timestamps
    4. Caches results for 7 days

    Args:
        request: Video ID and transcript segments

    Returns:
        All verified claims with timestamps and verdicts
    """
    try:
        cache = CacheService()
        claim_service = ClaimService(cache=cache)

        # Convert Pydantic models to dicts
        transcript_data = [
            {
                "text": seg.text,
                "start": seg.start,
                "duration": seg.duration
            }
            for seg in request.transcript
        ]

        # Process transcript
        result = await claim_service.process_transcript(
            video_id=request.video_id,
            transcript=transcript_data
        )

        # Convert to response model
        claims = [
            ClaimResult(
                claim=c.get("claim", ""),
                verdict=c.get("verdict", "Unverified"),
                confidence=c.get("confidence", 0.0),
                explanation=c.get("explanation", ""),
                timestamp=c.get("timestamp", 0.0),
                sources=c.get("sources", [])
            )
            for c in result.get("claims", [])
        ]

        return VerifyTranscriptResponse(
            video_id=result.get("video_id", request.video_id),
            claims=claims,
            cached=result.get("cached", False)
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing transcript: {str(e)}"
        )
