#!/usr/bin/env python3
"""
scripts/captions.py
==================

Caption generation module for the Manhwa Shorts video pipeline.

Generates ASS subtitle file from word-level timestamps.

Features:
    - Word-level timing from transcription
    - Max 4-6 words per caption line
    - Bottom-center positioning
    - Strong contrast (white text + black outline)
    - Bold readable font
    - Fade in/out animation
    - Safe margins for mobile
    - Hindi/Unicode text support

Output:
    data/captions.ass

Usage:
    python scripts/captions.py
"""

import json
import sys
from pathlib import Path


# =========================================================
# PATHS
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_FILE = PROJECT_ROOT / "config" / "project.json"
TIMELINE_FILE = PROJECT_ROOT / "data" / "timeline.json"
OUTPUT_FILE = PROJECT_ROOT / "data" / "captions.ass"

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


def seconds_to_ass_time(seconds):
    """
    Convert seconds to ASS subtitle time format.
    Format: H:MM:SS.cc
    """
    if seconds is None or seconds < 0:
        seconds = 0

    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centi = int((seconds % 1) * 100)

    return f"{hours}:{minutes:02d}:{secs:02d}.{centi:02d}"


def escape_ass_text(text):
    """Escape special characters for ASS subtitle format."""
    if not text:
        return ""
    text = text.replace("\\", "\\\\")
    text = text.replace("{", "\\{")
    text = text.replace("}", "\\}")
    return text


# =========================================================
# ASS HEADER
# =========================================================

def build_ass_header(config):
    """Build the ASS file header with style definitions."""
    cap_config = config.get("captions", {})
    font_size = cap_config.get("font_size", 64)
    font_color = cap_config.get("font_color", "white")
    outline_color = cap_config.get("outline_color", "black")
    outline_width = cap_config.get("outline_width", 3)
    margin_v = cap_config.get("margin_v", 80)
    position = cap_config.get("position", "bottom")

    color_map = {
        "white": "&H00FFFFFF",
        "black": "&H00000000",
        "yellow": "&H0000FFFF",
        "red": "&H000000FF",
        "blue": "&H00FF0000",
        "green": "&H0000FF00",
    }

    primary_color = color_map.get(font_color, "&H00FFFFFF")
    outline_c = color_map.get(outline_color, "&H00000000")
    alignment = 2 if position == "bottom" else 8

    header = f"""[Script Info]
Title: Manhwa Shorts Captions
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
PlayResX: 1080
PlayResY: 1920
YCbCr Matrix: TV.709

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,{font_size},{primary_color},{primary_color},{outline_c},{outline_c},1,0,0,0,100,100,0,0,1,{outline_width},1,{alignment},80,80,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    return header


# =========================================================
# BUILD CAPTION EVENTS
# =========================================================

def build_caption_events(timeline):
    """Build ASS dialogue events from timeline caption segments."""
    events = []
    scenes = timeline.get("scenes", [])

    for scene in scenes:
        caption_data = scene.get("caption", {})
        if not caption_data.get("enabled", False):
            continue

        segments = caption_data.get("segments", [])
        for seg in segments:
            start = seg.get("start", 0)
            end = seg.get("end", start + 1)
            text = seg.get("text", "")

            if not text.strip():
                continue

            start_str = seconds_to_ass_time(start)
            end_str = seconds_to_ass_time(end)
            escaped_text = escape_ass_text(text)

            fade_in = 200
            fade_out = 200

            duration_ms = max(1, int((end - start) * 1000))
            fade_in = min(fade_in, duration_ms // 3)
            fade_out = min(fade_out, duration_ms // 3)

            styled_text = f"{{\\fad({fade_in},{fade_out})}}{escaped_text}"

            event_line = (
                f"Dialogue: 0,{start_str},{end_str},"
                f"Default,,0,0,0,,{styled_text}"
            )
            events.append(event_line)

    return events


# =========================================================
# MAIN
# =========================================================

def main():
    print("=" * 60)
    print("MANHWA VIDEO WORKFLOW - CAPTION GENERATION")
    print("=" * 60)

    config = load_json(CONFIG_FILE, "config/project.json not found.")
    timeline = load_json(TIMELINE_FILE, "data/timeline.json not found. Run generate_timeline.py first.")

    cap_config = config.get("captions", {})

    print(f"Font size:    {cap_config.get('font_size', 64)}")
    print(f"Max words:    {cap_config.get('max_words', 6)}")
    print(f"Position:     {cap_config.get('position', 'bottom')}")
    print("=" * 60)

    header = build_ass_header(config)
    events = build_caption_events(timeline)

    ass_content = header
    for event in events:
        ass_content += event + "\n"

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(ass_content)

    print("\n" + "=" * 60)
    print("CAPTION GENERATION COMPLETE")
    print("=" * 60)
    print(f"Caption events: {len(events)}")
    print(f"Output:         {OUTPUT_FILE}")

    if events:
        first = events[0]
        parts = first.split(",")
        if len(parts) >= 4:
            print(f"\nFirst caption:")
            print(f"  Start: {parts[1]}")
            print(f"  End:   {parts[2]}")
            print(f"  Text:  {parts[9] if len(parts) > 9 else 'N/A'}")

    print("=" * 60)


if __name__ == "__main__":
    main()
