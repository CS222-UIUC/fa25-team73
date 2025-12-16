# LiveCheck - Real-Time Video Fact Checker

The LiveCheck system is a Chrome extension designed to fact-check claims in YouTube videos by analyzing transcripts and displaying real-time verification overlays. Its architecture relies on a FastAPI Backend (Python) to manage all processing, communicating with the extension's Content Script and Background Script. The core workflow involves the backend fetching the video transcript, splitting it into 5-minute segments for chunked processing, and sending these segments concurrently to OpenAI GPT-4o-mini for claim detection and verification. Before contacting the LLM, the system performs a Cache Check in the Redis Cache to retrieve verified claims instantly for repeat views. Once claims are processed, they are stored in the cache and returned to the extension, which monitors video playback for Overlay Timing to display the results accurately. This ensures immediate and reliable claim verification, with a focus on progressive results and reduced processing time.

## Architecture

### System Design
- **Chrome Extension** (Vanilla JavaScript): Displays overlays, manages state
- **FastAPI Backend**: Fetches transcripts, processes claims via OpenAI
- **Redis Cache**: Stores verified claims (7-day TTL)
- **OpenAI GPT-4o-mini**: Claim detection and verification

### Key Features
- Automatic transcript extraction from YouTube videos
- Chunked processing (5-minute segments) for progressive results
- Real-time overlay display at claim timestamps
- Cached results for instant repeated access
- Progressive status tracking in popup

## Quick Start

### Prerequisites
- Python 3.11+
- Docker & Docker Compose
- Chrome browser
- OpenAI API key

### 1. Setup Environment

```bash
# Clone/navigate to repository
cd livecheck

# Create .env file
cp .env.example .env

# Edit .env and add your OpenAI API key:
# OPENAI_API_KEY=sk-proj-your-key-here
```

### 2. Start Backend

```bash
cd infra
docker-compose up
```

Verify backend is running:
```bash
curl http://localhost:8000/api/v1/health
# Should return: {"status":"healthy","redis":"connected","openai":"configured"}
```

### 3. Load Chrome Extension

1. Open Chrome and go to `chrome://extensions/`
2. Enable "Developer mode" (toggle in top-right)
3. Click "Load unpacked"
4. Select the `extension/` directory
5. Extension should now appear in your extensions list

### 4. Test It

1. Go to a YouTube video with captions
2. Open browser console (Cmd+Option+J on Mac) to see processing logs
3. Wait 15-20 seconds for first results
4. Watch for overlays at claim timestamps
5. Click the LiveCheck extension icon to see all claims

## Project Structure

```
livecheck/
├── backend/                   # FastAPI backend
│   ├── app/
│   │   ├── main.py           # FastAPI app entry point
│   │   ├── config.py         # Settings/environment config
│   │   ├── core/
│   │   │   └── redis.py      # Redis connection
│   │   ├── services/
│   │   │   ├── claim_service.py    # OpenAI claim processing
│   │   │   └── cache.py            # Redis caching
│   │   └── api/
│   │       ├── fetch_transcript.py # YouTube transcript fetching
│   │       ├── transcript.py       # /api/verify-transcript endpoint
│   │       └── v1/health.py        # /api/v1/health endpoint
│   ├── tests/
│   │   ├── conftest.py       # Pytest fixtures
│   │   ├── test_api.py       # API endpoint tests
│   │   ├── test_debate.py    # Debate transcript test
│   │   └── fixtures/
│   │       ├── trump_biden_debate.json          # Original transcript
│   │       └── trump_biden_debate_converted.json # Test-ready format
│   └── requirements.txt
├── extension/                 # Chrome extension (Vanilla JS)
│   ├── manifest.json         # Extension configuration
│   ├── popup.html            # Popup UI
│   ├── src/
│   │   ├── content.js        # Main content script for YouTube
│   │   └── popup.js          # Popup logic
│   └── assets/               # Icons
├── infra/
│   ├── docker-compose.yml    # Docker Compose config
│   └── docker/
│       └── Dockerfile.backend
├── tests/
│   └── test_youtube_transcript.py  # YouTube transcript test script
├── .env                      # Environment variables (not in git)
├── .env.example             # Environment template
└── README.md
```

## How It Works

### Extension Flow

1. **Video Detection**: Content script detects YouTube video load
2. **Transcript Fetch**: Calls backend to get transcript
3. **Chunking**: Splits transcript into 5-minute segments
4. **Parallel Processing**: Sends chunks to backend API concurrently
5. **Progressive Display**: Shows claims as each chunk completes
6. **Overlay Timing**: Monitors video playback and displays overlays at claim timestamps

### Backend Processing

1. **Transcript Fetching**: Extracts captions directly from YouTube video pages
2. **Cache Check**: Looks for existing results in Redis (by video_id)
3. **Claim Detection**: Sends transcript to OpenAI to identify factual claims
4. **Verification**: OpenAI verifies each claim and provides verdict
5. **Cache Storage**: Stores results in Redis (7-day TTL)
6. **Response**: Returns claims with timestamps, verdicts, confidence scores

## Development

### Running Tests

```bash
# Run all tests with the test runner
./run_tests.sh

# Or run tests individually:

# Backend unit tests
cd backend
pip install -r requirements.txt
pip install pytest pytest-asyncio httpx

# Run all backend tests
pytest -v

# Run specific test
pytest tests/test_api.py -v

# Run with coverage
pytest --cov=app tests/
```

### Environment Variables

```bash
# .env file
REDIS_URL=redis://localhost:6379/0
OPENAI_API_KEY=sk-proj-your-key-here
HOST=0.0.0.0
PORT=8000
ENVIRONMENT=development
CORS_ORIGINS=chrome-extension://*
CACHE_TTL_SECONDS=604800  # 7 days
LLM_MODEL=gpt-4o-mini
LLM_TEMPERATURE=0.3
LLM_MAX_TOKENS=1000
CLAIM_CONFIDENCE_THRESHOLD=0.7
```

## Troubleshooting

### Extension Not Working
- Check browser console for errors
- Verify backend is running: `curl http://localhost:8000/api/v1/health`
- Ensure OpenAI API key is set in `.env`
- Try reloading the extension at `chrome://extensions/`

### No Transcript Available
- Video must have captions/subtitles enabled
- Try a different video with confirmed captions
- Check YouTube's transcript availability manually
- Extension only works with videos that have publicly accessible captions

### Transcript Fetching Fails
- Verify the video has captions enabled on YouTube
- Check backend logs: `docker-compose logs backend`
- Some videos may have captions but block automated access

### Backend Issues
- **Redis connection error**: Ensure Docker Compose is running
- **OpenAI API error**: Verify API key is valid and has credits
- **Port already in use**: Change port in `docker-compose.yml`

### Performance Issues
- Long videos may take several minutes to fully process
- First chunk results appear in 15-20 seconds
- Cached results load instantly

## License

MIT

## Who Did What
Paige: Worked on the Backend, helped write test cases and created the presentation.
Ben: Added timestamp functionality to openAI fallback.
Malcolm: Worked on clean pycache, added gitignore, and transcript API.
Krish: Added scripts for writing to the extension and getting the UI up also for querying GPT with questions.
