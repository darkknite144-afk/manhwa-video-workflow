#!/usr/bin/env python3
"""
scripts/generate_timeline.py
============================

Timeline generation module for the Manhwa Shorts video pipeline.

Reads scene data from ai_scene_match output and generates:
    - Camera motion keyframes (zoom, pan, diagonal, static)
    - Motion variation based on scene mood and duration
    - Caption timing from word timestamps
    - Transition metadata
    - SFX placement metadata

Output:
    data/timeline.json

Usage:
    python scripts/generate_timeline.py
"""

import json
import random
import sys
from pathlib import Path


# =========================================================
# PATHS
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_FILE = PROJECT_ROOT / "config" / "project.json"
SCENES_AI_FILE = PROJECT_ROOT / "data" / "scenes_ai.json"
OUTPUT_FILE = PROJECT_ROOT / "data" / "timeline.json"

(PROJECT_ROOT / "data").mkdir(parents=True, exist_ok=True)


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def load_json(path, error_msg):
    """Load a JSON file with error handling."""
    if not path.exists():
        print(f"ERROR: {error_msg}")
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# =========================================================
# MOTION PATTERNS
# =========================================================

def build_motion_patterns(min_scale, max_scale):
    """Build the full set of camera motion patterns."""
    mid_scale = round((min_scale + max_scale) / 2, 4)
    pan_scale = round(min_scale + (max_scale - min_scale) * 0.5, 4)

    return [
        {
            "name": "zoom_in",
            "start": {"x": 0.50, "y": 0.50, "scale": min_scale},
            "end":   {"x": 0.50, "y": 0.50, "scale": max_scale},
        },
        {
            "name": "zoom_out",
            "start": {"x": 0.50, "y": 0.50, "scale": max_scale},
            "end":   {"x": 0.50, "y": 0.50, "scale": min_scale},
        },
        {
            "name": "pan_left",
            "start": {"x": 0.65, "y": 0.50, "scale": pan_scale},
            "end":   {"x": 0.35, "y": 0.50, "scale": pan_scale},
        },
        {
            "name": "pan_right",
            "start": {"x": 0.35, "y": 0.50, "scale": pan_scale},
            "end":   {"x": 0.65, "y": 0.50, "scale": pan_scale},
        },
        {
            "name": "pan_up",
            "start": {"x": 0.50, "y": 0.65, "scale": pan_scale},
            "end":   {"x": 0.50, "y": 0.35, "scale": pan_scale},
        },
        {
            "name": "pan_down",
            "start": {"x": 0.50, "y": 0.35, "scale": pan_scale},
            "end":   {"x": 0.50, "y": 0.65, "scale": pan_scale},
        },
        {
            "name": "diagonal_push",
            "start": {"x": 0.40, "y": 0.40, "scale": min_scale},
            "end":   {"x": 0.60, "y": 0.60, "scale": max_scale},
        },
        {
            "name": "static",
            "start": {"x": 0.50, "y": 0.50, "scale": round(min_scale + 0.02, 4)},
            "end":   {"x": 0.50, "y": 0.50, "scale": round(min_scale + 0.02, 4)},
        },
    ]


def select_motion(scene, index, patterns, randomize=True):
    """
    Select a camera motion pattern for a scene.

    Selection considers:
        - Scene mood
        - Duration (short = static)
        - Variation (don't repeat same motion consecutively)
    """
    duration = float(scene.get("duration", 3.0))

    # Very short scenes get static
    if duration < 1.0:
        return patterns[-1]  # static

    mood = scene.get("ai", {}).get("mood", "neutral")

    # Mood-based selection
    if mood in ("somber", "intense"):
        # Action: faster push/pan
        candidates = [p for p in patterns if p["name"] in
                      ("zoom_in", "diagonal_push", "pan_left", "pan_right")]
    elif mood in ("cheerful",):
        # Calm: slow zoom
        candidates = [p for p in patterns if p["name"] in
                      ("zoom_out", "pan_up", "pan_down")]
    else:
        # Neutral: any motion
        candidates = patterns[:-1]  # exclude static

    if not candidates:
        candidates = patterns

    if randomize:
        return random.choice(candidates)
    else:
        return candidates[index % len(candidates)]


def adjust_motion_for_focal_point(motion, focal_point):
    """
    Adjust camera end position toward detected focal point
    (e.g., a face or important character).
    """
    if not focal_point:
        return motion

    fp_x = focal_point.get("x", 0.5)
    fp_y = focal_point.get("y", 0.5)

    # Only adjust if focal point is significantly off-center
    if abs(fp_x - 0.5) < 0.1 and abs(fp_y - 0.5) < 0.1:
        return motion

    # Blend end position toward focal point (50% blend)
    adjusted = {
        "name": motion["name"],
        "start": dict(motion["start"]),
        "end": {
            "x": round((motion["end"]["x"] + fp_x) / 2, 4),
            "y": round((motion["end"]["y"] + fp_y) / 2, 4),
            "scale": motion["end"]["scale"],
        },
    }
    return adjusted


# =========================================================
# CAPTION GENERATION
# =========================================================

def generate_captions(words, max_words=6):
    """
    Generate caption segments from word timestamps.
    Groups words into chunks of max_words.
    """
    if not words:
        return []

    captions = []
    current_chunk = []
    chunk_start = None

    for word in words:
        if not current_chunk:
            chunk_start = word.get("start", 0)

        current_chunk.append(word.get("word", ""))

        if len(current_chunk) >= max_words:
            captions.append({
                "text": " ".join(current_chunk),
                "start": round(chunk_start, 3),
                "end": round(word.get("end", chunk_start), 3),
            })
            current_chunk = []

    # Don't forget remaining words
    if current_chunk:
        last_end = words[-1].get("end", chunk_start) if words else chunk_start
        captions.append({
            "text": " ".join(current_chunk),
            "start": round(chunk_start, 3),
            "end": round(last_end, 3),
        })

    return captions


# =========================================================
# SFX MAPPING
# =========================================================

SFX_MAP = {
    "fight": "assets/sfx/impact.wav",
    "sword": "assets/sfx/sword.wav",
    "hit": "assets/sfx/hit.wav",
    "movement": "assets/sfx/whoosh.wav",
    "reveal": "assets/sfx/whoosh.wav",
    "whoosh": "assets/sfx/whoosh.wav",
    "impact": "assets/sfx/impact.wav",
}

SFX_DIR = None  # Set in main()


def determine_sfx(scene_text, mood, sfx_enabled):
    """Determine if SFX should be placed for a scene."""
    if not sfx_enabled:
        return None

    text_lower = scene_text.lower()

    for keyword, sfx_file in SFX_MAP.items():
        if keyword in text_lower:
            return sfx_file

    # Mood-based SFX
    if mood in ("somber", "intense"):
        return "assets/sfx/impact.wav"

    return None


# =========================================================
# MAIN
# =========================================================

def main():
    print("=" * 60)
    print("MANHWA VIDEO WORKFLOW - TIMELINE GENERATION")
    print("=" * 60)

    config = load_json(CONFIG_FILE, "config/project.json not found.")
    scene_data = load_json(SCENES_AI_FILE, "data/scenes_ai.json not found. Run ai_scene_match.py first.")

    # --- Video settings ---
    video_config = config["video"]
    WIDTH = video_config["width"]
    HEIGHT = video_config["height"]
    FPS = video_config["fps"]

    # --- Animation settings ---
    anim_config = config.get("animation", {})
    MIN_SCALE = anim_config.get("min_scale", 1.0)
    MAX_SCALE = anim_config.get("max_scale", 1.12)
    EASING = anim_config.get("easing", "ease_in_out")
    RANDOMIZE = anim_config.get("randomize_motion", True)

    # --- Caption settings ---
    cap_config = config.get("captions", {})
    CAP_ENABLED = cap_config.get("enabled", True)
    MAX_WORDS = cap_config.get("max_words", 6)

    # --- SFX settings ---
    sfx_config = config.get("sfx", {})
    SFX_ENABLED = sfx_config.get("enabled", True)

    if RANDOMIZE:
        random.seed(42)  # Reproducible runs

    patterns = build_motion_patterns(MIN_SCALE, MAX_SCALE)

    scenes = scene_data.get("scenes", [])
    print(f"Input scenes:    {len(scenes)}")
    print(f"Resolution:      {WIDTH}x{HEIGHT}")
    print(f"FPS:             {FPS}")
    print(f"Animation:       {'enabled' if anim_config.get('enabled', True) else 'disabled'}")
    print(f"Captions:        {'enabled' if CAP_ENABLED else 'disabled'}")
    print(f"Randomize motion: {RANDOMIZE}")
    print("=" * 60)

    timeline_scenes = []
    prev_motion_name = None

    for index, scene in enumerate(scenes):
        duration = float(scene["duration"])

        # --- Select motion ---
        motion = select_motion(scene, index, patterns, RANDOMIZE)

        # Avoid repeating same motion twice in a row
        if RANDOMIZE and motion["name"] == prev_motion_name:
            alt_patterns = [p for p in patterns if p["name"] != prev_motion_name]
            motion = random.choice(alt_patterns) if alt_patterns else motion

        prev_motion_name = motion["name"]

        # --- Adjust for focal point ---
        focal_point = scene.get("image_info", {}).get("focal_point", {"x": 0.5, "y": 0.5})
        motion = adjust_motion_for_focal_point(motion, focal_point)

        # --- Captions ---
        captions = []
        if CAP_ENABLED:
            words = scene.get("words", [])
            captions = generate_captions(words, MAX_WORDS)

        # --- SFX ---
        mood = scene.get("ai", {}).get("mood", "neutral")
        sfx_file = determine_sfx(scene.get("text", ""), mood, SFX_ENABLED)

        # --- Build timeline scene ---
        timeline_scene = {
            "id": scene["id"],
            "image": scene["image"],
            "start": scene["start"],
            "end": scene["end"],
            "duration": duration,
            "text": scene.get("text", ""),
            "animation": {
                "type": motion["name"],
                "easing": EASING,
                "keyframes": [
                    {
                        "time": 0.0,
                        "x": motion["start"]["x"],
                        "y": motion["start"]["y"],
                        "scale": motion["start"]["scale"],
                    },
                    {
                        "time": duration,
                        "x": motion["end"]["x"],
                        "y": motion["end"]["y"],
                        "scale": motion["end"]["scale"],
                    },
                ],
            },
            "transition": {
                "type": config.get("transitions", {}).get("default", "cut"),
                "duration": config.get("transitions", {}).get("duration", 0.0),
            },
            "caption": {
                "enabled": CAP_ENABLED,
                "segments": captions,
                "position": cap_config.get("position", "bottom"),
                "max_words": MAX_WORDS,
            },
            "sfx": {
                "file": sfx_file,
                "volume": sfx_config.get("volume", 0.3) if sfx_file else 0,
            },
            "image_info": scene.get("image_info", {}),
        }

        timeline_scenes.append(timeline_scene)

    # --- Total duration ---
    total_duration = 0.0
    if timeline_scenes:
        total_duration = max(s["end"] for s in timeline_scenes)

    timeline = {
        "project": scene_data.get("project", "manhwa-shorts"),
        "format": {
            "width": WIDTH,
            "height": HEIGHT,
            "fps": FPS,
            "aspect_ratio": "9:16",
        },
        "duration": round(total_duration, 3),
        "scene_count": len(timeline_scenes),
        "scenes": timeline_scenes,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(timeline, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print("TIMELINE GENERATION COMPLETE")
    print("=" * 60)
    print(f"Resolution:  {WIDTH}x{HEIGHT}")
    print(f"FPS:         {FPS}")
    print(f"Duration:    {round(total_duration, 3)} seconds")
    print(f"Scenes:      {len(timeline_scenes)}")
    print(f"Output:      {OUTPUT_FILE}")

    # Motion distribution
    motion_types = {}
    for s in timeline_scenes:
        m = s["animation"]["type"]
        motion_types[m] = motion_types.get(m, 0) + 1
    print(f"\nMotion distribution:")
    for m, count in sorted(motion_types.items()):
        print(f"  {m:20s} {count} scenes")

    print("=" * 60)


if __name__ == "__main__":
    main()
