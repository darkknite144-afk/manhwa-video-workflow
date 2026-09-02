import json
import sys
from pathlib import Path
from difflib import SequenceMatcher

from PIL import Image


# =========================================================
# PATHS
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

CONFIG_FILE = PROJECT_ROOT / "config" / "project.json"
TRANSCRIPT_FILE = PROJECT_ROOT / "data" / "transcript.json"
IMAGES_DIR = PROJECT_ROOT / "assets" / "images"
OUTPUT_FILE = PROJECT_ROOT / "data" / "scenes_ai.json"


# =========================================================
# CHECK FILES
# =========================================================

if not CONFIG_FILE.exists():
    print("ERROR: config/project.json not found.")
    sys.exit(1)

if not TRANSCRIPT_FILE.exists():
    print("ERROR: data/transcript.json not found.")
    print("Run transcribe.py first.")
    sys.exit(1)

if not IMAGES_DIR.exists():
    print("ERROR: assets/images/ not found.")
    sys.exit(1)


# =========================================================
# LOAD CONFIG
# =========================================================

with open(CONFIG_FILE, "r", encoding="utf-8") as f:
    config = json.load(f)


# =========================================================
# LOAD TRANSCRIPT
# =========================================================

with open(TRANSCRIPT_FILE, "r", encoding="utf-8") as f:
    transcript = json.load(f)


# =========================================================
# FIND IMAGES
# =========================================================

IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp"
}

images = sorted(
    [
        p for p in IMAGES_DIR.iterdir()
        if p.is_file()
        and p.suffix.lower() in IMAGE_EXTENSIONS
    ],
    key=lambda p: p.name.lower()
)


if not images:
    print("ERROR: No images found.")
    sys.exit(1)


# =========================================================
# IMAGE ANALYSIS
# =========================================================

def analyze_image(image_path):
    """
    Collect lightweight information about an image.

    This does not modify the image.
    """

    try:
        with Image.open(image_path) as img:

            width, height = img.size

            ratio = width / height if height else 0

            return {
                "width": width,
                "height": height,
                "aspect_ratio": round(ratio, 4),
                "orientation": (
                    "portrait"
                    if height > width
                    else "landscape"
                    if width > height
                    else "square"
                )
            }

    except Exception as exc:

        print(
            f"WARNING: Could not analyze "
            f"{image_path.name}: {exc}"
        )

        return {
            "width": 0,
            "height": 0,
            "aspect_ratio": 0,
            "orientation": "unknown"
        }


# =========================================================
# TEXT SIMILARITY
# =========================================================

def text_similarity(text_a, text_b):
    """
    Basic text similarity helper.

    Reserved for future AI/metadata matching.
    """

    if not text_a or not text_b:
        return 0.0

    return SequenceMatcher(
        None,
        text_a.lower(),
        text_b.lower()
    ).ratio()


# =========================================================
# BUILD IMAGE METADATA
# =========================================================

image_metadata = []

for index, image_path in enumerate(images):

    metadata = analyze_image(image_path)

    metadata["index"] = index

    metadata["file"] = str(
        image_path.relative_to(PROJECT_ROOT)
    )

    image_metadata.append(metadata)


# =========================================================
# MATCHING STRATEGY
# =========================================================

"""
Current MVP strategy:

1. Keep transcript timing exactly as Whisper produced it.
2. Assign images in sequence.
3. Reuse the final image if there are more dialogue
   segments than images.
4. Store visual metadata for the future AI matcher.

Later this same file can be connected to a vision model
to understand characters, locations, actions and dialogue.
"""


segments = transcript.get("segments", [])

scenes = []


for scene_id, segment in enumerate(segments):

    if not image_metadata:
        break

    # ---------------------------------------------
    # Select image
    # ---------------------------------------------

    image_index = min(
        scene_id,
        len(image_metadata) - 1
    )

    image = image_metadata[image_index]


    # ---------------------------------------------
    # Timing
    # ---------------------------------------------

    start = float(
        segment.get("start", 0)
    )

    end = float(
        segment.get("end", start)
    )

    duration = max(
        0.01,
        end - start
    )


    # ---------------------------------------------
    # Scene
    # ---------------------------------------------

    scene = {

        "id": scene_id,

        "image": image["file"],

        "start": round(start, 3),

        "end": round(end, 3),

        "duration": round(duration, 3),

        "text": segment.get(
            "text",
            ""
        ).strip(),

        "words": segment.get(
            "words",
            []
        ),

        "image_info": {

            "width": image["width"],

            "height": image["height"],

            "aspect_ratio": image[
                "aspect_ratio"
            ],

            "orientation": image[
                "orientation"
            ]
        },

        "ai": {

            "enabled": False,

            "match_score": 1.0,

            "reason": "sequential_fallback",

            "character_focus": None,

            "action": None,

            "location": None
        }
    }


    scenes.append(scene)


# =========================================================
# OUTPUT
# =========================================================

output = {

    "project": config["project"]["name"],

    "version": "1.0",

    "method": "fallback_sequential",

    "image_count": len(images),

    "scene_count": len(scenes),

    "scenes": scenes
}


with open(
    OUTPUT_FILE,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        output,
        f,
        ensure_ascii=False,
        indent=2
    )


# =========================================================
# SUMMARY
# =========================================================

print("=" * 60)
print("AI SCENE MATCHING")
print("=" * 60)

print(
    "Images:",
    len(images)
)

print(
    "Transcript segments:",
    len(segments)
)

print(
    "Scenes created:",
    len(scenes)
)

print(
    "Mode:",
    "fallback_sequential"
)

print(
    "Output:",
    OUTPUT_FILE
)

print("=" * 60)

print(
    "\nAI vision matching is currently disabled."
)

print(
    "The pipeline is ready for a vision-model adapter."
)

print("=" * 60)
