"""
API endpoint for fetching YouTube transcripts using YouTube Data API v3
"""
from fastapi import APIRouter, HTTPException
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import requests
import xml.etree.ElementTree as ET
from html import unescape

from app.config import settings

import asyncio
import tempfile
from pathlib import Path
import yt_dlp

from openai import OpenAI
import os

router = APIRouter()

client = OpenAI(api_key=settings.OPENAI_API_KEY)

def _download_audio_sync(video_id: str) -> str:
    """Download YouTube audio to a temp file and return its path."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    tmpdir = tempfile.mkdtemp(prefix="yt_audio_")
    outtmpl = str(Path(tmpdir) / "%(id)s.%(ext)s")

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": outtmpl,
        "quiet": True,
        "noplaylist": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)

    return filename

async def download_audio(video_id: str) -> str:
    return await asyncio.to_thread(_download_audio_sync, video_id)

async def fetch_transcript_stt(video_id: str):
    """Fallback: transcribe audio with OpenAI STT."""
    audio_path = await download_audio(video_id)

    with open(audio_path, "rb") as f:
        transcription = client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            response_format="json",
        )

    text = transcription.text

    # Minimal version: just one big segment
    return [
        {
            "text": text,
            "start": 0.0,
            "duration": 0.0,
        }
    ]




async def fetch_transcript_youtube_api(video_id: str):
    """
    Fetch transcript using YouTube Data API v3.

    This is the official, supported method from Google.
    Requires YOUTUBE_API_KEY in environment.
    """
    if not settings.YOUTUBE_API_KEY:
        raise ValueError("YOUTUBE_API_KEY not configured")

    try:
        youtube = build('youtube', 'v3', developerKey=settings.YOUTUBE_API_KEY)

        # Get caption tracks for the video
        captions_response = youtube.captions().list(
            part='snippet',
            videoId=video_id
        ).execute()

        if not captions_response.get('items'):
            return None

        # Find English caption track
        caption_id = None
        for item in captions_response['items']:
            lang = item['snippet'].get('language', '')
            if lang.startswith('en'):
                caption_id = item['id']
                break

        if not caption_id:
            caption_id = captions_response['items'][0]['id']

        # Download the caption track
        caption_download = youtube.captions().download(
            id=caption_id,
            tfmt='srt'  # Get SRT format
        ).execute()

        # Parse SRT format
        return parse_srt(caption_download)

    except HttpError as e:
        print(f"YouTube API error: {e}")
        return None


def parse_srt(srt_content: str):
    """Parse SRT subtitle format into our transcript format."""
    transcript = []
    lines = srt_content.strip().split('\n\n')

    for block in lines:
        lines_in_block = block.split('\n')
        if len(lines_in_block) >= 3:
            # Line 0: sequence number
            # Line 1: timestamp (00:00:00,000 --> 00:00:03,500)
            # Line 2+: text

            timestamp_line = lines_in_block[1]
            text = ' '.join(lines_in_block[2:])

            # Parse start time
            start_str = timestamp_line.split(' --> ')[0]
            start_seconds = srt_time_to_seconds(start_str)

            # Parse duration
            end_str = timestamp_line.split(' --> ')[1]
            end_seconds = srt_time_to_seconds(end_str)
            duration = end_seconds - start_seconds

            transcript.append({
                'text': text,
                'start': start_seconds,
                'duration': duration
            })

    return transcript


def srt_time_to_seconds(time_str: str) -> float:
    """Convert SRT timestamp (00:00:00,000) to seconds."""
    time_str = time_str.replace(',', '.')
    parts = time_str.split(':')
    hours = int(parts[0])
    minutes = int(parts[1])
    seconds = float(parts[2])
    return hours * 3600 + minutes * 60 + seconds


async def fetch_transcript_direct_xml(video_id: str):
    """
    Fallback method: Try to fetch transcript XML directly.

    This method scrapes the YouTube page to find caption URLs,
    then attempts to download them. Less reliable but doesn't
    need API key.
    """
    try:
        # Fetch YouTube page
        page_url = f"https://www.youtube.com/watch?v={video_id}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        response = requests.get(page_url, headers=headers, timeout=10)
        html = response.text

        # Find ytInitialPlayerResponse
        import re
        match = re.search(r'ytInitialPlayerResponse\s*=\s*({.+?});', html)
        if not match:
            return None

        import json
        player_response = json.loads(match.group(1))

        # Get caption tracks
        tracks = player_response.get('captions', {}).get(
            'playerCaptionsTracklistRenderer', {}
        ).get('captionTracks', [])

        if not tracks:
            return None

        # Find English track
        caption_url = None
        for track in tracks:
            if track.get('languageCode', '').startswith('en'):
                caption_url = track.get('baseUrl')
                break

        if not caption_url:
            caption_url = tracks[0].get('baseUrl')

        if not caption_url:
            return None

        # Fetch caption XML
        caption_response = requests.get(caption_url, headers=headers, timeout=10)
        xml_text = caption_response.text

        if not xml_text or len(xml_text) == 0:
            return None

        # Parse XML
        root = ET.fromstring(xml_text)
        transcript = []

        for text_elem in root.findall('.//text'):
            text = unescape(text_elem.text or '')
            if text.strip():
                transcript.append({
                    'text': text.strip(),
                    'start': float(text_elem.get('start', '0')),
                    'duration': float(text_elem.get('dur', '0'))
                })

        return transcript if transcript else None

    except Exception as e:
        print(f"Direct XML fetch error: {e}")
        return None


@router.get("/api/fetch-transcript/{video_id}")
async def fetch_transcript(video_id: str):
    """
    Fetch transcript for a YouTube video.

    Tries multiple methods:
    1. YouTube Data API v3 (if API key configured)
    2. Direct XML scraping (fallback)

    Args:
        video_id: YouTube video ID (e.g., "qqG96G8YdcE")

    Returns:
        {
            "video_id": "...",
            "transcript": [
                {"text": "...", "start": 0.0, "duration": 3.5},
                ...
            ],
            "method": "youtube_api" or "direct_xml"
        }
    """
    print(f"Fetching transcript for video: {video_id}")

    transcript = None
    method = None

    # Method 1: Try YouTube Data API v3 (if configured)
    if settings.YOUTUBE_API_KEY:
        print("Attempting YouTube Data API v3...")
        try:
            transcript = await fetch_transcript_youtube_api(video_id)
            if transcript:
                method = "youtube_api"
                print(f"Got transcript via YouTube API ({len(transcript)} segments)")
        except Exception as e:
            print(f"YouTube API failed: {e}")

    # Method 2: Fallback to direct XML scraping
    if not transcript:
        print("Attempting direct XML fetch...")
        transcript = await fetch_transcript_direct_xml(video_id)
        if transcript:
            method = "direct_xml"
            print(f"Got transcript via direct XML ({len(transcript)} segments)")

    # Method 3: External STT fallback
    if not transcript:
        print("Falling back to OpenAI STT...")
        try:
            transcript = await fetch_transcript_stt(video_id)
            if transcript:
                method = "openai_stt"
                print(f"Got transcript via OpenAI STT ({len(transcript)} segments)")
        except Exception as e:
            print(f"OpenAI STT failed: {e}")

    # If both methods failed
    if not transcript:
        print(f"All methods failed for video: {video_id}")
        raise HTTPException(
            status_code=404,
            detail="No transcript available. Video may not have captions, or YouTube may be blocking access."
        )

    return {
        "video_id": video_id,
        "transcript": transcript,
        "method": method
    }
