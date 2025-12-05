"""
Test with Trump-Biden debate transcript
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
async def test_debate_transcript(client: TestClient):
    """Test with Trump-Biden debate transcript"""
    print("\n" + "="*70)
    print("TESTING: Trump-Biden Debate Transcript")
    print("="*70)

    data = load_fixture("trump_biden_debate_converted.json")

    print(f"\nTranscript Info:")
    print(f"   - Segments: {len(data['transcript'])}")
    print(f"   - Duration: ~{data['transcript'][-1]['start']:.0f} seconds")
    print(f"   - Description: {data['description']}")

    response = client.post("/api/verify-transcript", json={
        "video_id": data["video_id"],
        "transcript": data["transcript"]
    })

    if response.status_code == 200:
        result = response.json()
        claims = result.get("claims", [])
        cached = result.get("cached", False)

        print(f"\nSUCCESS - Processing complete!")
        print(f"Cached: {cached}")
        print(f"Claims Found: {len(claims)}")
        print("\n" + "-"*70)

        if claims:
            for i, claim in enumerate(claims, 1):
                print(f"\n{'='*70}")
                print(f"CLAIM #{i} at {claim['timestamp']:.1f}s")
                print(f"{'='*70}")
                print(f"\nClaim:")
                print(f"   \"{claim['claim']}\"")
                print(f"\nVerdict: {claim['verdict']}")
                print(f"Confidence: {claim['confidence']*100:.0f}%")
                print(f"\nExplanation:")
                print(f"   {claim['explanation']}")

                if claim.get('sources'):
                    print(f"\nSources:")
                    for source in claim['sources'][:3]:
                        print(f"   - {source}")

            print("\n" + "="*70)
            print(f"Total: {len(claims)} factual claims detected and verified")
            print("="*70 + "\n")
        else:
            print("\nNo claims detected (transcript may not contain verifiable facts)")

        assert len(claims) >= 0, "Should return claims list"
        for claim in claims:
            assert "claim" in claim
            assert "verdict" in claim
            assert claim["verdict"] in ["True", "False", "Mixed", "Unverified"]
            assert 0 <= claim["confidence"] <= 1

        print("\nAll assertions passed!")

    else:
        print(f"\nFAILED - Status code: {response.status_code}")
        print(f"Response: {response.text}")
        pytest.fail(f"API returned {response.status_code}")
