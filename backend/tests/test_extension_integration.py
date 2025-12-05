"""
Integration tests to verify extension transcript format works with backend
"""
import pytest
import json
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_json3_transcript_format(client: AsyncClient):
    """Test that the transcript format from json3 API works with backend"""

    # Simulated transcript in the format the extension now sends
    # (after parsing YouTube's json3 format)
    transcript = [
        {
            "text": "Climate change is real",
            "start": 0.0,
            "duration": 3.5
        },
        {
            "text": "The Earth is flat",
            "start": 3.5,
            "duration": 2.5
        },
        {
            "text": "Water boils at 100 degrees Celsius",
            "start": 6.0,
            "duration": 4.0
        }
    ]

    response = await client.post(
        "/api/verify-transcript",
        json={
            "video_id": "test_json3_format",
            "transcript": transcript
        }
    )

    assert response.status_code == 200
    data = response.json()

    # Verify response structure
    assert "video_id" in data
    assert "claims" in data
    assert "cached" in data

    # Verify video_id matches
    assert data["video_id"] == "test_json3_format"

    # Should have detected some claims
    assert isinstance(data["claims"], list)
    print(f"\nFound {len(data['claims'])} claims")

    # Verify claim structure if any were found
    if len(data["claims"]) > 0:
        claim = data["claims"][0]
        assert "claim" in claim
        assert "verdict" in claim
        assert "confidence" in claim
        assert "timestamp" in claim

        # Timestamp should be from our transcript
        assert claim["timestamp"] >= 0.0
        assert claim["timestamp"] <= 10.0

        print(f"\nSample claim: {claim['claim']}")
        print(f"Verdict: {claim['verdict']}")
        print(f"Confidence: {claim['confidence']}")


@pytest.mark.asyncio
async def test_chunked_transcript_processing(client: AsyncClient):
    """Test processing transcript chunks like the extension does"""

    # Create a longer transcript that would be split into chunks
    transcript_chunk_1 = [
        {"text": f"Statement {i} with some content", "start": float(i * 5), "duration": 4.0}
        for i in range(20)  # 100 seconds of content
    ]

    transcript_chunk_2 = [
        {"text": f"Statement {i} with more content", "start": float(100 + i * 5), "duration": 4.0}
        for i in range(20)  # Another 100 seconds
    ]

    # Process first chunk
    response1 = await client.post(
        "/api/verify-transcript",
        json={
            "video_id": "test_chunked_video_chunk_0",
            "transcript": transcript_chunk_1
        }
    )

    assert response1.status_code == 200
    data1 = response1.json()
    claims1 = data1["claims"]

    # Process second chunk
    response2 = await client.post(
        "/api/verify-transcript",
        json={
            "video_id": "test_chunked_video_chunk_1",
            "transcript": transcript_chunk_2
        }
    )

    assert response2.status_code == 200
    data2 = response2.json()
    claims2 = data2["claims"]

    print(f"\nChunk 1: {len(claims1)} claims")
    print(f"Chunk 2: {len(claims2)} claims")

    # Verify timestamps in each chunk are in the right range
    if claims1:
        for claim in claims1:
            assert 0 <= claim["timestamp"] < 100, "Chunk 1 timestamps should be 0-100s"

    if claims2:
        for claim in claims2:
            assert 100 <= claim["timestamp"] < 200, "Chunk 2 timestamps should be 100-200s"


@pytest.mark.asyncio
async def test_empty_transcript(client: AsyncClient):
    """Test handling of empty transcript"""

    response = await client.post(
        "/api/verify-transcript",
        json={
            "video_id": "empty_video",
            "transcript": []
        }
    )

    assert response.status_code == 200
    data = response.json()

    # Empty transcript should return no claims
    assert data["claims"] == []


@pytest.mark.asyncio
async def test_transcript_with_special_characters(client: AsyncClient):
    """Test transcript segments with special characters and unicode"""

    transcript = [
        {"text": "Hello 世界! Testing unicode", "start": 0.0, "duration": 3.0},
        {"text": "Special chars: @#$%^&*()", "start": 3.0, "duration": 2.0},
        {"text": "Quotes: \"Hello\" and 'world'", "start": 5.0, "duration": 3.0},
    ]

    response = await client.post(
        "/api/verify-transcript",
        json={
            "video_id": "special_chars_video",
            "transcript": transcript
        }
    )

    assert response.status_code == 200
    data = response.json()

    # Should process without errors
    assert "claims" in data
    print(f"\nProcessed transcript with special characters: {len(data['claims'])} claims")


@pytest.mark.asyncio
async def test_caching_works_for_chunks(client: AsyncClient):
    """Test that chunk results are cached properly"""

    transcript = [
        {"text": "The moon is made of cheese", "start": 0.0, "duration": 3.0},
    ]

    # First request
    response1 = await client.post(
        "/api/verify-transcript",
        json={
            "video_id": "cache_test_chunk_0",
            "transcript": transcript
        }
    )

    assert response1.status_code == 200
    data1 = response1.json()
    assert data1["cached"] == False

    # Second request with same video_id should be cached
    response2 = await client.post(
        "/api/verify-transcript",
        json={
            "video_id": "cache_test_chunk_0",
            "transcript": transcript
        }
    )

    assert response2.status_code == 200
    data2 = response2.json()
    assert data2["cached"] == True

    # Results should be identical
    assert len(data1["claims"]) == len(data2["claims"])
    print(f"\nCache working: First request processed, second request cached")


@pytest.mark.asyncio
async def test_realistic_youtube_transcript(client: AsyncClient):
    """Test with a realistic YouTube transcript format"""

    # This mimics what the extension would send after parsing YouTube's json3 format
    transcript = [
        {"text": "Welcome to this video about science", "start": 0.52, "duration": 3.84},
        {"text": "Today we're going to talk about", "start": 4.36, "duration": 2.12},
        {"text": "the speed of light which is", "start": 6.48, "duration": 2.44},
        {"text": "299,792,458 meters per second", "start": 8.92, "duration": 3.68},
        {"text": "This is a universal constant", "start": 12.6, "duration": 2.88},
        {"text": "Albert Einstein proved this in 1905", "start": 15.48, "duration": 3.24},
    ]

    response = await client.post(
        "/api/verify-transcript",
        json={
            "video_id": "realistic_science_video",
            "transcript": transcript
        }
    )

    assert response.status_code == 200
    data = response.json()

    # Should detect factual claims about speed of light and Einstein
    assert isinstance(data["claims"], list)

    if len(data["claims"]) > 0:
        # Check that timestamps are reasonable
        for claim in data["claims"]:
            assert 0 <= claim["timestamp"] <= 20
            assert 0 <= claim["confidence"] <= 1
            assert claim["verdict"] in ["True", "False", "Mixed", "Unverifiable"]

        print(f"\nFound {len(data['claims'])} claims in realistic transcript")
        for claim in data["claims"]:
            print(f"  - [{claim['verdict']}] {claim['claim']} at {claim['timestamp']:.1f}s")
