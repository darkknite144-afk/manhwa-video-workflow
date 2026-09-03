#!/usr/bin/env python3
"""
scripts/transcribe.py
======================

Transcription module for the Manhwa Shorts video pipeline.

Uses OpenAI Whisper to convert the voiceover audio file into
timestamped text with segment-level and word-level timing.

Output:
    data/transcript.json

Usage:
    python scripts/transcribe.py
"""

import json
import sys
from pathlib import Path


# =========================================================
# PATHS
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_FILE = PROJECT_ROOT / "config" / "project.json"
DATA_DIR = PROJECT_ROOT / "data"
AUDIO_DIR = PROJECT_ROOT / "assets" / "audio"
SCRIPT_FILE = PROJECT_ROOT / "assets" / "script" / "script.txt"
OUTPUT_FILE = DATA_DIR / "transcript.json"

DATA_DIR.mkdir(parents=True, exist_ok=True)


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def load_config():
    """Load project configuration JSON."""
    if not CONFIG_FILE.exists():
        print("ERROR: config/project.json not found.")
        sys.exit(1)
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def find_audio_file():
    """
    Automatically detect the audio file in assets/audio/.

    Supports: .mp3, .wav, .m4a, .aac, .flac, .ogg, .mp4
    """
    audio_extensions = {
        ".mp3", ".wav", ".m4a", ".aac",
        ".flac", ".ogg", ".mp4"
    }
    if not AUDIO_DIR.exists():
        print("ERROR: assets/audio/ directory not found.")
        sys.exit(1)

    audio_files = sorted([
        f for f in AUDIO_DIR.iterdir()
        if f.is_file() and f.suffix.lower() in audio_extensions
    ])

    if not audio_files:
        print("ERROR: No audio file found in assets/audio/.")
        print("Supported formats: mp3, wav, m4a, aac, flac, ogg, mp4")
        sys.exit(1)

    if len(audio_files) > 1:
        print(f"WARNING: Multiple audio files found ({len(audio_files)}).")
        print(f"Using: {audio_files[0].name}")

    return audio_files[0]


def load_script_text():
    """
    Load optional script.txt for semantic assistance.

    The script is NOT used to replace transcription.
    It is used only as additional semantic context.
    """
    if not SCRIPT_FILE.exists():
        return None
    try:
        with open(SCRIPT_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception as exc:
        print(f"WARNING: Could not read script.txt: {exc}")
        return None


def run_transcription(audio_path, language="auto", word_timestamps=True, model_name="base"):
    """
    Run Whisper transcription on the given audio file.

    Returns the raw Whisper result dictionary.
    """
    try:
        import whisper
    except ImportError:
        print("ERROR: openai-whisper is not installed.")
        print("Install with: pip install openai-whisper")
        sys.exit(1)

    print(f"\nLoading Whisper model: {model_name}")
    model = whisper.load_model(model_name)

    print(f"Transcribing: {audio_path.name}")

    options = {
        "word_timestamps": word_timestamps,
        "verbose": False,
    }

    if language and language != "auto":
        options["language"] = language

    result = model.transcribe(str(audio_path), **options)
    return result


def build_transcript_json(result, audio_filename, script_text=None):
    """
    Build a clean transcript JSON structure from Whisper output.

    Preserves exact segment and word-level timing.
    """
    segments = []

    for index, segment in enumerate(result.get("segments", [])):
        words = []
        for word in segment.get("words", []):
            words.append({
                "word": word.get("word", "").strip(),
                "start": round(float(word.get("start", 0)), 3),
                "end": round(float(word.get("end", 0)), 3),
            })

        segments.append({
            "id": index,
            "start": round(float(segment["start"]), 3),
            "end": round(float(segment["end"]), 3),
            "text": segment["text"].strip(),
            "words": words,
        })

    transcript = {
        "audio": audio_filename,
        "language": result.get("language", "unknown"),
        "duration": round(
            float(segments[-1]["end"]) if segments else 0.0, 3
        ),
        "segments": segments,
    }

    # Attach script as semantic reference (timing from audio is primary)
    if script_text:
        transcript["script_available"] = True
        transcript["script_note"] = (
            "Script is used only for semantic assistance. "
            "Audio timing is the primary source."
        )
    else:
        transcript["script_available"] = False

    return transcript


def save_transcript(transcript):
    """Save transcript JSON to data/transcript.json (UTF-8)."""
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(transcript, f, ensure_ascii=False, indent=2)


# =========================================================
# MAIN
# =========================================================

def main():
    print("=" * 60)
    print("MANHWA VIDEO WORKFLOW - TRANSCRIPTION")
    print("=" * 60)

    config = load_config()
    transcribe_config = config.get("transcription", {})

    language = transcribe_config.get("language", "auto")
    word_ts = transcribe_config.get("word_timestamps", True)
    model_name = transcribe_config.get("model", "base")

    audio_file = find_audio_file()
    script_text = load_script_text()

    print(f"Audio:       {audio_file.name}")
    print(f"Language:    {language}")
    print(f"Word timestamps: {word_ts}")
    print(f"Model:       {model_name}")
    print(f"Script:      {'available' if script_text else 'not found'}")
    print("=" * 60)

    result = run_transcription(
        audio_file,
        language=language,
        word_timestamps=word_ts,
        model_name=model_name,
    )

    transcript = build_transcript_json(
        result,
        audio_filename=audio_file.name,
        script_text=script_text,
    )

    save_transcript(transcript)

    print("\n" + "=" * 60)
    print("TRANSCRIPTION COMPLETE")
    print("=" * 60)
    print(f"Language:  {transcript['language']}")
    print(f"Duration:  {transcript['duration']}s")
    print(f"Segments:  {len(transcript['segments'])}")
    print(f"Output:    {OUTPUT_FILE}")

    if transcript["segments"]:
        first = transcript["segments"][0]
        print(f"\nFirst segment (0:00 - {first['end']}s):")
        print(f"  {first['text']}")

    print("=" * 60)


if __name__ == "__main__":
    main()
