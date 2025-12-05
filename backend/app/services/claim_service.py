import json
from typing import List, Dict
from openai import AsyncOpenAI

from app.config import settings
from app.services.cache import CacheService


class ClaimService:
    """
    Unified service for claim detection and verification using OpenAI.

    This service processes entire YouTube transcripts in one batch:
    1. Takes full transcript with timestamps
    2. Extracts and verifies ALL claims in a single OpenAI call
    3. Returns claims with their timestamps
    4. Caches results by video_id
    """

    def __init__(self, cache: CacheService):
        self.cache = cache
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.LLM_MODEL

    async def process_transcript(self, video_id: str, transcript: List[Dict]) -> Dict:
        """
        Process entire transcript and extract/verify all claims.

        Args:
            video_id: YouTube video ID
            transcript: List of transcript segments
                [
                    {"text": "...", "start": 0.0, "duration": 5.0},
                    ...
                ]

        Returns:
            {
                "video_id": "abc123",
                "claims": [
                    {
                        "claim": "...",
                        "verdict": "True|False|Mixed|Unverified",
                        "confidence": 0.95,
                        "explanation": "...",
                        "timestamp": 12.5,
                        "sources": [...]
                    }
                ],
                "cached": False
            }
        """
        # Check cache first
        cached_result = await self.cache.get_video_claims(video_id)
        if cached_result:
            return {**cached_result, "cached": True}

        # Build full transcript text with timestamp markers
        full_text = self._build_transcript_text(transcript)

        # Process with OpenAI
        prompt = self._build_prompt(full_text)

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a fact-checking assistant that extracts and verifies factual claims from video transcripts."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=settings.LLM_TEMPERATURE,
                max_tokens=settings.LLM_MAX_TOKENS,
                response_format={"type": "json_object"}
            )

            content = response.choices[0].message.content
            result = json.loads(content)

            claims = result.get("claims", [])

            # Map timestamps from transcript segments
            processed_claims = self._map_timestamps(claims, transcript)

            # Filter by confidence threshold
            filtered_claims = [
                c for c in processed_claims
                if c.get("confidence", 0) >= settings.CLAIM_CONFIDENCE_THRESHOLD
            ]

            result_data = {
                "video_id": video_id,
                "claims": filtered_claims,
                "cached": False
            }

            # Cache the result
            await self.cache.set_video_claims(video_id, result_data)

            return result_data

        except Exception as e:
            print(f"Error processing transcript: {e}")
            return {
                "video_id": video_id,
                "claims": [],
                "cached": False,
                "error": str(e)
            }

    def _build_transcript_text(self, transcript: List[Dict]) -> str:
        """Build full transcript text with timestamp markers."""
        lines = []
        for segment in transcript:
            timestamp = segment.get("start", 0.0)
            text = segment.get("text", "")
            lines.append(f"[{timestamp:.1f}s] {text}")
        return "\n".join(lines)

    def _build_prompt(self, transcript_text: str) -> str:
        """Build the prompt for claim extraction and verification."""
        return f"""Extract and fact-check ALL verifiable claims from this video transcript.

Transcript (with timestamps):
{transcript_text}

For each claim found:
1. Extract the exact claim text
2. Note the timestamp where it appears (from [X.Xs] markers)
3. Fact-check the claim (True/False/Mixed/Unverified)
4. Provide confidence score (0.0-1.0)
5. Brief explanation of your verdict
6. Sources or reasoning used

Return JSON in this format:
{{
    "claims": [
        {{
            "claim": "exact claim text",
            "timestamp_ref": "12.5",
            "verdict": "True" | "False" | "Mixed" | "Unverified",
            "confidence": 0.95,
            "explanation": "brief explanation",
            "sources": ["source1", "source2"]
        }}
    ]
}}

Guidelines:
- Only extract FACTUAL claims that can be verified (not opinions, questions, or vague statements)
- Each claim should be specific and standalone
- Only include claims with confidence >= {settings.CLAIM_CONFIDENCE_THRESHOLD}
- Verdicts:
  - "True": Factually accurate based on established knowledge
  - "False": Factually incorrect
  - "Mixed": Contains both true and false elements
  - "Unverified": Cannot determine with available information
- Provide clear, concise explanations (1-2 sentences)
- Extract timestamp from the [Xs] markers in the transcript
- If no verifiable claims found, return empty claims array
"""

    def _map_timestamps(self, claims: List[Dict], transcript: List[Dict]) -> List[Dict]:
        """Map timestamp references to actual timestamps."""
        for claim in claims:
            timestamp_ref = claim.get("timestamp_ref", "0")
            try:
                # Extract numeric timestamp from reference
                timestamp = float(timestamp_ref)
                claim["timestamp"] = timestamp
            except:
                # If parsing fails, default to 0
                claim["timestamp"] = 0.0

            # Remove the timestamp_ref field
            if "timestamp_ref" in claim:
                del claim["timestamp_ref"]

        return claims
