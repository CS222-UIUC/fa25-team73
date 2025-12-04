"""
Test using fixture transcripts

Run this after pasting your own transcripts into tests/fixtures/
"""
import json
import pytest
from pathlib import Path
from fastapi.testclient import TestClient


def load_fixture(filename: str):
    """Load a transcript fixture file"""
    fixture_path = Path(__file__).parent / "fixtures" / filename
    with open(fixture_path) as f:
        return json.load(f)


@pytest.mark.asyncio
async def test_short_example_transcript(client: TestClient):
    """Test with the short example transcript"""
    data = load_fixture("example_transcript_short.json")

    response = client.post("/api/verify-transcript", json={
        "video_id": data["video_id"],
        "transcript": data["transcript"]
    })

    print(f"\n{'='*60}")
    print(f"Testing: {data.get('description', 'No description')}")
    print(f"Video ID: {data['video_id']}")
    print(f"Transcript segments: {len(data['transcript'])}")
    print(f"{'='*60}\n")

    if response.status_code == 200:
        result = response.json()
        claims = result.get("claims", [])
        cached = result.get("cached", False)

        print(f"SUCCESS - Found {len(claims)} claims")
        print(f"Cached: {cached}")
        print()

        for i, claim in enumerate(claims, 1):
            print(f"Claim {i}:")
            print(f"  Timestamp: {claim['timestamp']}s")
            print(f"  Claim: \"{claim['claim']}\"")
            print(f"  Verdict: {claim['verdict']}")
            print(f"  Confidence: {claim['confidence']*100:.0f}%")
            print(f"  Explanation: {claim['explanation']}")
            if claim.get('sources'):
                print(f"  Sources: {', '.join(claim['sources'][:3])}")
            print()

        assert len(claims) >= 0, "Should return claims list (can be empty)"
        for claim in claims:
            assert "claim" in claim
            assert "verdict" in claim
            assert claim["verdict"] in ["True", "False", "Mixed", "Unverified"]
            assert 0 <= claim["confidence"] <= 1
    else:
        print(f"FAILED - Status code: {response.status_code}")
        print(f"Response: {response.text}")
        pytest.fail(f"API returned {response.status_code}")


# ============================================================================
# ADD YOUR OWN TESTS HERE!
# ============================================================================

# @pytest.mark.asyncio
# async def test_my_custom_transcript(client: TestClient):
#     """Test with your custom transcript - UNCOMMENT AND MODIFY"""
#     data = load_fixture("my_transcript.json")  # Your filename here
#
#     response = client.post("/api/verify-transcript", json={
#         "video_id": data["video_id"],
#         "transcript": data["transcript"]
#     })
#
#     # Add your assertions here
#     assert response.status_code == 200


# Template for performance testing
@pytest.mark.skip(reason="Template - uncomment to use")
@pytest.mark.asyncio
async def test_transcript_performance(client: TestClient):
    """Measure processing time for transcript"""
    import time

    data = load_fixture("example_transcript_short.json")

    start = time.time()
    response = client.post("/api/verify-transcript", json={
        "video_id": data["video_id"],
        "transcript": data["transcript"]
    })
    duration = time.time() - start

    print(f"\nProcessing time: {duration:.2f}s")

    assert response.status_code == 200
    assert duration < 10.0, "Should process in under 10 seconds"
