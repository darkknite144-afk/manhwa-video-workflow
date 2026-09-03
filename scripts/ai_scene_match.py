#!/usr/bin/env python3
"""
scripts/ai_scene_match.py
=========================

AI Scene Matching module for the Manhwa Shorts video pipeline.

Determines which image best represents each dialogue segment.

Matching strategy (with graceful fallback):
    1. AI vision matching (if configured and available)
    2. Semantic / text matching (using dialogue keywords)
    3. Sequential matching (fallback)

The system NEVER crashes if AI is unavailable.
It always falls back to sequential image assignment.

Output:
    data/scenes_ai.json

Usage:
    python scripts/ai_scene_match.py
"""

import json
import sys
from pathlib import Path
from difflib import SequenceMatcher

try:
    from PIL import Image
except ImportError:
    Image = None  # Continue without Pillow if unavailable


# =========================================================
# PATHS
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_FILE = PROJECT_ROOT / "config" / "project.json"
AI_CONFIG_FILE = PROJECT_ROOT / "config" / "ai.json"
TRANSCRIPT_FILE = PROJECT_ROOT / "data" / "transcript.json"
IMAGE_ANALYSIS_FILE = PROJECT_ROOT / "data" / "image_analysis.json"
IMAGES_DIR = PROJECT_ROOT / "assets" / "images"
SCRIPT_FILE = PROJECT_ROOT / "assets" / "script" / "script.txt"
OUTPUT_FILE = PROJECT_ROOT / "data" / "scenes_ai.json"

(PROJECT_ROOT / "data").mkdir(parents=True, exist_ok=True)


# =========================================================
# HELPER FUNCTIONS
# =========================================================

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def load_json(path, error_msg):
    """Load a JSON file with error handling."""
    if not path.exists():
        print(f"ERROR: {error_msg}")
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def find_images():
    """Find and sort all image files."""
    if not IMAGES_DIR.exists():
        print("ERROR: assets/images/ directory not found.")
        sys.exit(1)

    images = sorted(
        [p for p in IMAGES_DIR.iterdir()
         if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS],
        key=lambda p: p.name.lower(),
    )

    if not images:
        print("ERROR: No images found in assets/images/.")
        sys.exit(1)

    return images


def load_script_text():
    """Load optional script.txt for semantic matching."""
    if not SCRIPT_FILE.exists():
        return None
    try:
        with open(SCRIPT_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return None


def text_similarity(text_a, text_b):
    """Calculate similarity ratio between two text strings."""
    if not text_a or not text_b:
        return 0.0
    return SequenceMatcher(None, text_a.lower(), text_b.lower()).ratio()


def extract_keywords(text):
    """
    Extract meaningful keywords from dialogue text.
    Handles Hindi, English, and mixed text.
    """
    if not text:
        return []

    # Common stop words (English + common Hindi)
    stop_words = {
        "the", "a", "an", "is", "was", "are", "were", "to", "of",
        "in", "on", "at", "and", "or", "but", "for", "with", "by",
        "hai", "tha", "thi", "the", "aur", "ya", "par", "mein",
        "se", "ka", "ki", "ke", "ko", "ne", "ne", "hua", "hui",
        "kya", "kyon", "kahan", "kab", "kaun", "jab", "tab", "yeh",
        "woh", "mera", "tera", "uska", "meri", "teri", "uski",
        "ek", "do", "char", "pach", "nahi", "nahin", "haan",
    }

    words = text.lower().strip().split()
    keywords = [
        w.strip(".,!?\"'()[]{}")
        for w in words
        if w.strip(".,!?\"'()[]{}")
        and w.lower() not in stop_words
        and len(w.strip(".,!?\"'()[]{}")) > 1
    ]
    return keywords


# =========================================================
# SCENE MATCHING STRATEGIES
# =========================================================

def match_sequential(segments, images_metadata):
    """
    Fallback: Assign images sequentially to segments.
    Reuse last image if more segments than images.
    """
    scenes = []
    for scene_id, segment in enumerate(segments):
        image_index = min(scene_id, len(images_metadata) - 1)
        image = images_metadata[image_index]

        start = float(segment.get("start", 0))
        end = float(segment.get("end", start))
        duration = max(0.01, end - start)

        scenes.append({
            "id": scene_id,
            "image": image["file"],
            "start": round(start, 3),
            "end": round(end, 3),
            "duration": round(duration, 3),
            "text": segment.get("text", "").strip(),
            "words": segment.get("words", []),
            "image_info": {
                "width": image.get("width", 0),
                "height": image.get("height", 0),
                "orientation": image.get("orientation", "unknown"),
                "focal_point": image.get("focal_point", {"x": 0.5, "y": 0.5}),
            },
            "ai": {
                "enabled": False,
                "match_score": 1.0,
                "method": "sequential_fallback",
                "character_focus": image.get("character_focus", "center"),
                "action": None,
                "location": None,
                "mood": image.get("mood", "unknown"),
            },
        })
    return scenes


def match_semantic(segments, images_metadata, script_text=None):
    """
    Semantic matching: Use dialogue keywords and image analysis
    to score the best image match for each segment.
    """
    scenes = []

    # Build image keyword profiles from analysis
    image_profiles = []
    for img in images_metadata:
        profile = {
            "file": img["file"],
            "mood": img.get("mood", "neutral"),
            "brightness": img.get("brightness", "medium"),
            "character_focus": img.get("character_focus", "center"),
            "focal_point": img.get("focal_point", {"x": 0.5, "y": 0.5}),
        }
        image_profiles.append(profile)

    used_images = set()

    for scene_id, segment in enumerate(segments):
        dialogue = segment.get("text", "").strip()
        keywords = extract_keywords(dialogue)

        # Score each image
        best_score = -1
        best_index = 0

        for idx, profile in enumerate(image_profiles):
            score = 0.0

            # Base score: text similarity with script if available
            if script_text:
                score += text_similarity(dialogue, script_text) * 0.2

            # Mood matching (dialogue mood vs image mood)
            dialogue_lower = dialogue.lower()
            if any(w in dialogue_lower for w in ["fight", "ladai", "yudh", "sword", "talwar", "attack", "attack"]):
                if profile["mood"] in ("somber", "neutral"):
                    score += 0.3
            elif any(w in dialogue_lower for w in ["love", "pyaar", "ishq", "romantic"]):
                if profile["mood"] in ("cheerful", "neutral"):
                    score += 0.3
            elif any(w in dialogue_lower for w in ["dark", "andhera", "fear", "darr", "scary"]):
                if profile["mood"] == "somber":
                    score += 0.3

            # Prefer images not yet used
            if idx not in used_images:
                score += 0.15

            # Slight preference for sequential order
            score += max(0, 0.1 - abs(idx - scene_id) * 0.02)

            if score > best_score:
                best_score = score
                best_index = idx

        used_images.add(best_index)
        image = image_profiles[best_index]
        image_raw = images_metadata[best_index]

        start = float(segment.get("start", 0))
        end = float(segment.get("end", start))
        duration = max(0.01, end - start)

        scenes.append({
            "id": scene_id,
            "image": image["file"],
            "start": round(start, 3),
            "end": round(end, 3),
            "duration": round(duration, 3),
            "text": dialogue,
            "words": segment.get("words", []),
            "image_info": {
                "width": image_raw.get("width", 0),
                "height": image_raw.get("height", 0),
                "orientation": image_raw.get("orientation", "unknown"),
                "focal_point": image_raw.get("focal_point", {"x": 0.5, "y": 0.5}),
            },
            "ai": {
                "enabled": True,
                "match_score": round(best_score, 4),
                "method": "semantic_keyword",
                "character_focus": image.get("character_focus", "center"),
                "action": None,
                "location": None,
                "mood": image.get("mood", "unknown"),
            },
        })

    return scenes


# =========================================================
# MAIN
# =========================================================

def main():
    print("=" * 60)
    print("MANHWA VIDEO WORKFLOW - AI SCENE MATCHING")
    print("=" * 60)

    config = load_json(CONFIG_FILE, "config/project.json not found.")
    ai_config = load_json(AI_CONFIG_FILE, "config/ai.json not found.")
    transcript = load_json(TRANSCRIPT_FILE, "data/transcript.json not found. Run transcribe.py first.")

    images = find_images()
    script_text = load_script_text()

    # Load image analysis if available
    image_analysis_data = None
    if IMAGE_ANALYSIS_FILE.exists():
        try:
            with open(IMAGE_ANALYSIS_FILE, "r", encoding="utf-8") as f:
                image_analysis_data = json.load(f)
        except Exception:
            pass

    # Build images metadata
    if image_analysis_data and "images" in image_analysis_data:
        images_metadata = image_analysis_data["images"]
    else:
        # Build basic metadata inline
        images_metadata = []
        for idx, img_path in enumerate(images):
            metadata = {"file": str(img_path.relative_to(PROJECT_ROOT))}
            if Image:
                try:
                    with Image.open(img_path) as img:
                        w, h = img.size
                        metadata.update({
                            "width": w, "height": h,
                            "orientation": "portrait" if h > w else "landscape" if w > h else "square",
                            "mood": "neutral",
                            "brightness": "medium",
                            "focal_point": {"x": 0.5, "y": 0.5},
                            "character_focus": "center",
                        })
                except Exception:
                    metadata.update({"width": 0, "height": 0, "orientation": "unknown"})
            images_metadata.append(metadata)

    segments = transcript.get("segments", [])

    print(f"Images:              {len(images)}")
    print(f"Transcript segments:  {len(segments)}")
    print(f"Script available:     {'yes' if script_text else 'no'}")
    print(f"Image analysis:       {'available' if image_analysis_data else 'basic'}")

    # --- Determine matching strategy ---
    ai_enabled = ai_config.get("vision", {}).get("enabled", False)

    if ai_enabled:
        print("\nStrategy: AI vision matching")
        # AI vision matching would go here
        # For now, fall back to semantic
        print("WARNING: AI vision not yet configured. Using semantic matching.")
        scenes = match_semantic(segments, images_metadata, script_text)
        method = "semantic_keyword"
    else:
        print("\nStrategy: Semantic keyword matching")
        scenes = match_semantic(segments, images_metadata, script_text)
        method = "semantic_keyword"

    # Fallback to sequential if no scenes created
    if not scenes:
        print("WARNING: Semantic matching produced no scenes. Falling back to sequential.")
        scenes = match_sequential(segments, images_metadata)
        method = "sequential_fallback"

    output = {
        "project": config.get("project", {}).get("name", "manhwa-shorts"),
        "version": "1.0",
        "method": method,
        "image_count": len(images),
        "scene_count": len(scenes),
        "scenes": scenes,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print("AI SCENE MATCHING COMPLETE")
    print("=" * 60)
    print(f"Method:   {method}")
    print(f"Scenes:   {len(scenes)}")
    print(f"Output:   {OUTPUT_FILE}")

    if scenes:
        print(f"\nFirst scene:")
        print(f"  Image: {scenes[0]['image']}")
        print(f"  Text:  {scenes[0]['text'][:60]}...")
        print(f"  Score: {scenes[0]['ai']['match_score']}")

    print("=" * 60)


if __name__ == "__main__":
    main()
