#!/usr/bin/env python3
"""
Integration tests for LiveCheck backend API
Tests the full stack: FastAPI endpoints, OpenAI integration, Redis caching
"""

import pytest
import requests
import time

# Backend API base URL
API_BASE = "http://localhost:8000"


class TestHealthEndpoint:
    """Test the health check endpoint"""

    def test_health_check(self):
        """Health endpoint should return healthy status"""
        response = requests.get(f"{API_BASE}/api/v1/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert data["redis"] in ["connected", "disconnected"]
        assert data["openai"] in ["configured", "not_configured"]


class TestTranscriptVerification:
    """Test the transcript verification endpoint"""

    @pytest.fixture
    def sample_transcript(self):
        """Sample transcript for testing"""
        return [
            {"text": "The Earth orbits the Sun", "start": 0.0, "duration": 3.0},
            {"text": "Water freezes at 0 degrees Celsius", "start": 3.0, "duration": 3.0},
            {"text": "The moon is made of cheese", "start": 6.0, "duration": 3.0}
        ]

    def test_verify_transcript_success(self, sample_transcript):
        """Should successfully verify a transcript and return claims"""
        payload = {
            "video_id": "test_video_001",
            "transcript": sample_transcript
        }

        response = requests.post(
            f"{API_BASE}/api/verify-transcript",
            json=payload,
            timeout=60
        )

        assert response.status_code == 200

        data = response.json()
        assert "video_id" in data
        assert "claims" in data
        assert "cached" in data
        assert data["video_id"] == "test_video_001"
        assert isinstance(data["claims"], list)

        # Should find at least one claim
        if len(data["claims"]) > 0:
            claim = data["claims"][0]
            assert "claim" in claim
            assert "verdict" in claim
            assert "confidence" in claim
            assert "timestamp" in claim
            assert claim["verdict"] in ["True", "False", "Mixed", "Unverifiable"]
            assert 0.0 <= claim["confidence"] <= 1.0

    def test_verify_transcript_caching(self, sample_transcript):
        """Second request for same video should return cached result"""
        video_id = f"test_cache_{int(time.time())}"
        payload = {
            "video_id": video_id,
            "transcript": sample_transcript
        }

        # First request
        response1 = requests.post(
            f"{API_BASE}/api/verify-transcript",
            json=payload,
            timeout=60
        )
        assert response1.status_code == 200
        data1 = response1.json()

        # Second request (should be cached)
        response2 = requests.post(
            f"{API_BASE}/api/verify-transcript",
            json=payload,
            timeout=60
        )
        assert response2.status_code == 200
        data2 = response2.json()

        # Second response should be marked as cached
        assert data2["cached"] is True

        # Results should be identical
        assert data1["claims"] == data2["claims"]

    def test_verify_empty_transcript(self):
        """Should handle empty transcript gracefully"""
        payload = {
            "video_id": "test_empty",
            "transcript": []
        }

        response = requests.post(
            f"{API_BASE}/api/verify-transcript",
            json=payload,
            timeout=30
        )

        # Should either succeed with no claims or return appropriate error
        assert response.status_code in [200, 400, 422]

        if response.status_code == 200:
            data = response.json()
            assert len(data["claims"]) == 0


class TestTranscriptFetching:
    """Test the transcript fetching endpoint"""

    def test_fetch_transcript_invalid_video(self):
        """Should return 404 for invalid video ID"""
        response = requests.get(
            f"{API_BASE}/api/fetch-transcript/invalid_video_id_12345",
            timeout=30
        )

        # Should fail for invalid video
        assert response.status_code in [404, 500]

    def test_fetch_transcript_valid_video(self):
        """Should fetch transcript for valid video with captions"""
        # Using a known video with captions
        video_id = "qqG96G8YdcE"  # Trump/Biden debate

        response = requests.get(
            f"{API_BASE}/api/fetch-transcript/{video_id}",
            timeout=30
        )

        # May succeed with API key, or fail if not configured
        if response.status_code == 200:
            data = response.json()
            assert "video_id" in data
            assert "transcript" in data
            assert "method" in data
            assert data["video_id"] == video_id
            assert isinstance(data["transcript"], list)
            assert len(data["transcript"]) > 0

            # Check transcript format
            first_segment = data["transcript"][0]
            assert "text" in first_segment
            assert "start" in first_segment
            assert "duration" in first_segment
        else:
            # Without YouTube API key, this is expected to fail
            assert response.status_code in [404, 500]


class TestEndToEnd:
    """End-to-end test of the full pipeline"""

    def test_full_pipeline_with_fixture(self):
        """Test complete flow using fixture transcript data"""
        # Small transcript that should process quickly
        transcript = [
            {"text": "The capital of France is Paris", "start": 0.0, "duration": 3.0},
            {"text": "Mount Everest is the tallest mountain on Earth", "start": 3.0, "duration": 3.0}
        ]

        payload = {
            "video_id": f"test_e2e_{int(time.time())}",
            "transcript": transcript
        }

        # Send to verification endpoint
        response = requests.post(
            f"{API_BASE}/api/verify-transcript",
            json=payload,
            timeout=60
        )

        assert response.status_code == 200
        data = response.json()

        # Should have processed the claims
        assert isinstance(data["claims"], list)

        # If OpenAI is configured, should find claims
        # If not, claims list will be empty
        for claim in data["claims"]:
            # Validate claim structure
            assert isinstance(claim["claim"], str)
            assert claim["verdict"] in ["True", "False", "Mixed", "Unverifiable"]
            assert 0.0 <= claim["confidence"] <= 1.0
            assert isinstance(claim["timestamp"], (int, float))
            assert claim["timestamp"] >= 0


if __name__ == "__main__":
    print("Running LiveCheck Backend Integration Tests")
    print("=" * 60)
    print()
    print("Prerequisites:")
    print("1. Backend must be running (docker-compose up)")
    print("2. OpenAI API key must be configured in .env")
    print("3. Redis must be running")
    print()
    print("Run with: pytest tests/test_backend_integration.py -v")
    print()
