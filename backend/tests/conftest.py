"""
Pytest configuration and fixtures
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """Test client for FastAPI app"""
    return TestClient(app)


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI response for testing"""
    return {
        "claims": [
            {
                "claim": "The economy grew by 5%",
                "timestamp_ref": "10.5",
                "verdict": "Mixed",
                "confidence": 0.85,
                "explanation": "GDP grew 4.9% in Q3 2023, close to stated figure",
                "sources": ["Bureau of Economic Analysis"]
            }
        ]
    }
