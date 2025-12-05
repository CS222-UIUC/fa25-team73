"""
Convert raw YouTube caption format to our test format
"""
import json
import sys
from pathlib import Path


def convert_youtube_captions(input_file: str, output_file: str = None):
    """Convert YouTube pb3 format to our transcript format"""
    with open(input_file) as f:
        data = json.load(f)

    transcript = []

    # Extract events (each event has segments)
    for event in data.get("events", []):
        segs = event.get("segs", [])
        if not segs:
            continue

        # Combine segments into full text
        text = "".join(seg.get("utf8", "") for seg in segs).strip()

        if text:
            transcript.append({
                "text": text,
                "start": event.get("tStartMs", 0) / 1000.0,  # Convert ms to seconds
                "duration": event.get("dDurationMs", 0) / 1000.0
            })

    result = {
        "video_id": Path(input_file).stem,
        "description": f"Converted from {Path(input_file).name}",
        "transcript": transcript[:100]  # Limit to first 100 segments for testing
    }

    if output_file is None:
        output_file = input_file.replace(".json", "_converted.json")

    with open(output_file, "w") as f:
        json.dump(result, f, indent=2)

    print(f"Converted {len(transcript)} segments")
    print(f"Output: {output_file}")
    print(f"First 100 segments saved for testing")

    return result


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python convert_youtube_format.py <input_file> [output_file]")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    convert_youtube_captions(input_file, output_file)
