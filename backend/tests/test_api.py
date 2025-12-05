"""
Integration tests for API endpoints
"""
import pytest
from fastapi.testclient import TestClient


def test_root_endpoint(client):
    """Test root endpoint returns service info"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "LiveCheck API"
    assert data["version"] == "1.0.0"
    assert data["status"] == "running"


def test_health_endpoint(client):
    """Test health check endpoint"""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "redis" in data
    assert "openai" in data


@pytest.mark.asyncio
async def test_verify_transcript_endpoint_validation(client):
    """Test transcript verification with invalid input"""
    # Missing video_id
    response = client.post("/api/verify-transcript", json={
        "transcript": [
            {"text": "Test", "start": 0.0, "duration": 1.0}
        ]
    })
    assert response.status_code == 422  # Validation error

    # Missing transcript
    response = client.post("/api/verify-transcript", json={
        "video_id": "test123"
    })
    assert response.status_code == 422  # Validation error

    # Empty transcript
    response = client.post("/api/verify-transcript", json={
        "video_id": "test123",
        "transcript": []
    })
    assert response.status_code == 422  # Validation error


# NOTE: This test requires a valid OpenAI API key and will make a real API call
# Comment out if you don't want to use API credits
@pytest.mark.skip(reason="Requires OpenAI API key and makes real API call")
@pytest.mark.asyncio
async def test_verify_transcript_real_api(client):
    """Test transcript verification with real API (SKIPPED by default)"""
    response = client.post("/api/verify-transcript", json={
        "video_id": "test_video_123",
        "transcript": [
            {"text": "The sky is blue", "start": 0.0, "duration": 2.0},
            {"text": "Water freezes at 0 degrees Celsius", "start": 2.0, "duration": 3.0}
        ]
    })
    assert response.status_code == 200
    data = response.json()
    assert "video_id" in data
    assert "claims" in data
    assert isinstance(data["claims"], list)
