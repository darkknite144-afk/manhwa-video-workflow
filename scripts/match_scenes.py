import json
import sys
from pathlib import Path


# ---------------------------------------------------------
# PATHS
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

CONFIG_FILE = PROJECT_ROOT / "config" / "project.json"
TRANSCRIPT_FILE = PROJECT_ROOT / "data" / "transcript.json"
IMAGES_DIR = PROJECT_ROOT / "assets" / "images"
OUTPUT_FILE = PROJECT_ROOT / "data" / "scenes.json"


# ---------------------------------------------------------
# LOAD CONFIG
# ---------------------------------------------------------

if not CONFIG_FILE.exists():
    print("ERROR: config/project.json not found.")
    sys.exit(1)

with open(CONFIG_FILE, "r", encoding="utf-8") as f:
    config = json.load(f)


# ---------------------------------------------------------
# LOAD TRANSCRIPT
# ---------------------------------------------------------

if not TRANSCRIPT_FILE.exists():
    print("ERROR: data/transcript.json not found.")
    print("Run transcribe.py first.")
    sys.exit(1)

with open(TRANSCRIPT_FILE, "r", encoding="utf-8") as f:
    transcript = json.load(f)


# ---------------------------------------------------------
# FIND IMAGES
# ---------------------------------------------------------

image_extensions = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp"
}

images = sorted(
    [
        file for file in IMAGES_DIR.iterdir()
        if file.is_file() and file.suffix.lower() in image_extensions
    ],
    key=lambda x: x.name.lower()
)


if not images:
    print("ERROR: No images found in assets/images/")
    sys.exit(1)


print("=" * 60)
print("MANHWA SCENE MATCHING")
print("=" * 60)

print("Images found:", len(images))
print("Transcript segments:", len(transcript["segments"]))
print("=" * 60)


# ---------------------------------------------------------
# MATCH SCENES
# ---------------------------------------------------------

segments = transcript["segments"]

scenes = []

image_index = 0

for segment in segments:

    if image_index >= len(images):
        image_index = len(images) - 1

    image_file = images[image_index]

    scene = {
        "id": len(scenes),

        "image": str(
            image_file.relative_to(PROJECT_ROOT)
        ),

        "start": segment["start"],

        "end": segment["end"],

        "duration": round(
            segment["end"] - segment["start"],
            3
        ),

        "text": segment["text"],

        "words": segment.get("words", []),

        "animation": {
            "type": "auto",
            "start_scale": 1.0,
            "end_scale": 1.08,
            "start_x": 0.5,
            "start_y": 0.5,
            "end_x": 0.5,
            "end_y": 0.5
        }
    }

    scenes.append(scene)

    image_index += 1


# ---------------------------------------------------------
# HANDLE EXTRA IMAGES
# ---------------------------------------------------------

if len(images) > len(segments):

    print(
        f"\nWARNING: {len(images) - len(segments)} "
        "images were not assigned to transcript segments."
    )


# ---------------------------------------------------------
# HANDLE MORE SEGMENTS THAN IMAGES
# ---------------------------------------------------------

if len(segments) > len(images):

    print(
        f"\nWARNING: {len(segments) - len(images)} "
        "segments had to reuse the last image."
    )


# ---------------------------------------------------------
# OUTPUT
# ---------------------------------------------------------

output = {
    "project": config["project"]["name"],

    "audio": transcript["audio"],

    "language": transcript["language"],

    "scene_count": len(scenes),

    "scenes": scenes
}


with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(
        output,
        f,
        ensure_ascii=False,
        indent=2
    )


# ---------------------------------------------------------
# SUMMARY
# ---------------------------------------------------------

print("\nScene matching complete.")

print("Scenes created:", len(scenes))

print("Output:", OUTPUT_FILE)

if scenes:
    print("\nExample scene:")
    print(json.dumps(
        scenes[0],
        ensure_ascii=False,
        indent=2
    ))

print("=" * 60) 
