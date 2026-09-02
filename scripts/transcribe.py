import json
import sys
from pathlib import Path

import whisper


# ---------------------------------------------------------
# CONFIG
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_FILE = PROJECT_ROOT / "config" / "project.json"
DATA_DIR = PROJECT_ROOT / "data"
AUDIO_DIR = PROJECT_ROOT / "assets" / "audio"

DATA_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------
# LOAD PROJECT CONFIG
# ---------------------------------------------------------

with open(CONFIG_FILE, "r", encoding="utf-8") as f:
    config = json.load(f)


language = config["transcription"].get("language", "auto")
word_timestamps = config["transcription"].get("word_timestamps", True)


# ---------------------------------------------------------
# FIND AUDIO FILE
# ---------------------------------------------------------

audio_extensions = {
    ".mp3",
    ".wav",
    ".m4a",
    ".aac",
    ".flac",
    ".ogg",
    ".mp4"
}

audio_files = [
    file for file in AUDIO_DIR.iterdir()
    if file.is_file() and file.suffix.lower() in audio_extensions
]

if not audio_files:
    print("ERROR: No audio file found in assets/audio/")
    sys.exit(1)

if len(audio_files) > 1:
    print("WARNING: Multiple audio files found.")
    print("Using:", audio_files[0].name)

audio_file = audio_files[0]

print("=" * 60)
print("MANHWA VIDEO WORKFLOW - TRANSCRIPTION")
print("=" * 60)
print("Audio:", audio_file)
print("Language:", language)
print("Word timestamps:", word_timestamps)
print("=" * 60)


# ---------------------------------------------------------
# LOAD WHISPER
# ---------------------------------------------------------

# tiny = fastest
# base = better accuracy
# small = better accuracy but slower
# medium = high accuracy but needs more resources

MODEL_NAME = "base"

print("\nLoading Whisper model:", MODEL_NAME)

model = whisper.load_model(MODEL_NAME)


# ---------------------------------------------------------
# TRANSCRIBE
# ---------------------------------------------------------

print("\nTranscribing audio...\n")

options = {
    "word_timestamps": word_timestamps,
    "verbose": False
}

if language != "auto":
    options["language"] = language

result = model.transcribe(
    str(audio_file),
    **options
)


# ---------------------------------------------------------
# CREATE CLEAN TRANSCRIPT
# ---------------------------------------------------------

segments = []

for index, segment in enumerate(result.get("segments", [])):

    words = []

    for word in segment.get("words", []):

        words.append({
            "word": word.get("word", "").strip(),
            "start": round(float(word.get("start", 0)), 3),
            "end": round(float(word.get("end", 0)), 3)
        })

    segments.append({
        "id": index,
        "start": round(float(segment["start"]), 3),
        "end": round(float(segment["end"]), 3),
        "text": segment["text"].strip(),
        "words": words
    })


# ---------------------------------------------------------
# FINAL JSON
# ---------------------------------------------------------

transcript = {
    "audio": audio_file.name,
    "language": result.get("language", "unknown"),
    "segments": segments
}


output_file = DATA_DIR / "transcript.json"

with open(output_file, "w", encoding="utf-8") as f:
    json.dump(
        transcript,
        f,
        ensure_ascii=False,
        indent=2
    )


# ---------------------------------------------------------
# DONE
# ---------------------------------------------------------

print("=" * 60)
print("TRANSCRIPTION COMPLETE")
print("=" * 60)

print("Language:", transcript["language"])
print("Segments:", len(segments))
print("Output:", output_file)

if segments:
    print("\nFirst segment:")
    print(segments[0]["text"])

print("=" * 60)
