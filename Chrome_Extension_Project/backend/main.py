from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from typing import Dict

# Initialize the FastAPI application
app = FastAPI()

# CORS Configuration
origins = [
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic Models for Endpoints

# Model for the existing /echo endpoint
class EchoRequest(BaseModel):
    message: str

# Model for the incoming transcript data
class TranscriptRequest(BaseModel):
    """Expects a body like: {"transcript": "Some text from a call or chat."}"""
    transcript: str

# Model for the outgoing verdict response
class VerdictResponse(BaseModel):
    """Returns a body like: {"verdict": "Safe"}"""
    verdict: str

# Endpoints

@app.get("/health", summary="Health Check")
def health_check() -> Dict[str, str]:
    return {"status": "ok"}

@app.post("/echo", summary="Echo Endpoint")
def echo(request: EchoRequest) -> Dict[str, str]:
    return {"echo_message": request.message}

# Transcript Analysis Endpoint

@app.post("/analyze-transcript", response_model=VerdictResponse, summary="Analyze Transcript and Return Fake Verdict")
def analyze_transcript(request: TranscriptRequest):
    """
    Accepts a transcript and returns a fake verdict based on simple keyword matching.
    """
    # Convert transcript to lower case for case-insensitive matching
    text = request.transcript.lower()
    
    # Fake verdict logic:
    # Check for simple keywords to simulate a simple AI/ML model
    if any(keyword in text for keyword in ["scam", "fraud", "illegal", "money transfer"]):
        verdict_status = "Flagged: High Risk"
    elif len(text) < 10:
        verdict_status = "Inconclusive: Too Short"
    else:
        verdict_status = "Safe"
        
    # Return the verdict using the defined VerdictResponse model
    return VerdictResponse(verdict=verdict_status)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)