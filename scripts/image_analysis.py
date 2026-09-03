#!/usr/bin/env python3
"""
scripts/image_analysis.py
=========================

Image analysis module for the Manhwa Shorts video pipeline.

Analyzes every image in assets/images/ using Python/Pillow.

Extracts:
    - width, height
    - aspect ratio
    - orientation (portrait / landscape / square)
    - dominant brightness (dark / medium / bright)
    - approximate focal point (center of mass of non-background pixels)
    - average color

Output:
    data/image_analysis.json

Usage:
    python scripts/image_analysis.py
"""

import json
import sys
from pathlib import Path

try:
    from PIL import Image, ImageStat
except ImportError:
    print("ERROR: Pillow is not installed.")
    print("Install with: pip install Pillow")
    sys.exit(1)


# =========================================================
# PATHS
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_FILE = PROJECT_ROOT / "config" / "project.json"
IMAGES_DIR = PROJECT_ROOT / "assets" / "images"
OUTPUT_FILE = PROJECT_ROOT / "data" / "image_analysis.json"

(PROJECT_ROOT / "data").mkdir(parents=True, exist_ok=True)


# =========================================================
# HELPER FUNCTIONS
# =========================================================

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def load_config():
    """Load project configuration."""
    if not CONFIG_FILE.exists():
        print("ERROR: config/project.json not found.")
        sys.exit(1)
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def find_images():
    """Find and sort all image files in assets/images/."""
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


def analyze_single_image(image_path):
    """
    Analyze a single image and return metadata dict.

    Uses Pillow only (no external AI needed).
    """
    try:
        with Image.open(image_path) as img:
            img = img.convert("RGB")
            width, height = img.size

            # --- Aspect ratio ---
            ratio = width / height if height else 0

            # --- Orientation ---
            if height > width:
                orientation = "portrait"
            elif width > height:
                orientation = "landscape"
            else:
                orientation = "square"

            # --- Brightness analysis ---
            stat = ImageStat.Stat(img)
            avg_brightness = sum(stat.mean) / len(stat.mean)

            if avg_brightness < 60:
                brightness = "dark"
                mood = "somber"
            elif avg_brightness < 140:
                brightness = "medium"
                mood = "neutral"
            else:
                brightness = "bright"
                mood = "cheerful"

            # --- Average color ---
            r, g, b = stat.mean[0], stat.mean[1], stat.mean[2]
            avg_color = {
                "r": round(r),
                "g": round(g),
                "b": round(b),
            }

            # --- Focal point (center of non-white/non-black pixels) ---
            # Downscale for speed
            small = img.resize((100, 100))
            pixels = small.load()

            total_weight = 0
            weighted_x = 0
            weighted_y = 0

            for y in range(100):
                for x in range(100):
                    pr, pg, pb = pixels[x, y]
                    # Weight = distance from mid-gray (non-background)
                    gray = (pr + pg + pb) / 3
                    weight = abs(gray - 128) / 128
                    total_weight += weight
                    weighted_x += x * weight
                    weighted_y += y * weight

            if total_weight > 0:
                focal_x = weighted_x / total_weight / 100
                focal_y = weighted_y / total_weight / 100
            else:
                focal_x = 0.5
                focal_y = 0.5

            # --- Character focus (approximate) ---
            # Check if upper-center has more detail (typical face area)
            upper_region = small.crop((25, 10, 75, 50))
            upper_stat = ImageStat.Stat(upper_region)
            upper_variance = sum(upper_stat.stddev) / 3

            lower_region = small.crop((25, 50, 75, 90))
            lower_stat = ImageStat.Stat(lower_region)
            lower_variance = sum(lower_stat.stddev) / 3

            if upper_variance > lower_variance:
                character_focus = "upper"
            else:
                character_focus = "lower"

            return {
                "file": str(image_path.relative_to(PROJECT_ROOT)),
                "width": width,
                "height": height,
                "aspect_ratio": round(ratio, 4),
                "orientation": orientation,
                "brightness": brightness,
                "mood": mood,
                "avg_brightness": round(avg_brightness, 2),
                "avg_color": avg_color,
                "focal_point": {
                    "x": round(focal_x, 4),
                    "y": round(focal_y, 4),
                },
                "character_focus": character_focus,
                "detail_upper": round(upper_variance, 2),
                "detail_lower": round(lower_variance, 2),
            }

    except Exception as exc:
        print(f"WARNING: Could not analyze {image_path.name}: {exc}")
        return {
            "file": str(image_path.relative_to(PROJECT_ROOT)),
            "width": 0,
            "height": 0,
            "aspect_ratio": 0,
            "orientation": "unknown",
            "brightness": "unknown",
            "mood": "unknown",
            "avg_brightness": 0,
            "avg_color": {"r": 0, "g": 0, "b": 0},
            "focal_point": {"x": 0.5, "y": 0.5},
            "character_focus": "center",
            "detail_upper": 0,
            "detail_lower": 0,
        }


# =========================================================
# MAIN
# =========================================================

def main():
    print("=" * 60)
    print("MANHWA VIDEO WORKFLOW - IMAGE ANALYSIS")
    print("=" * 60)

    config = load_config()
    images = find_images()

    print(f"Images found: {len(images)}")
    print("=" * 60)

    results = []
    for index, img_path in enumerate(images):
        print(f"  Analyzing [{index + 1}/{len(images)}] {img_path.name}...")
        analysis = analyze_single_image(img_path)
        analysis["index"] = index
        results.append(analysis)

    output = {
        "project": config.get("project", {}).get("name", "manhwa-shorts"),
        "version": "1.0",
        "image_count": len(results),
        "images": results,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print("IMAGE ANALYSIS COMPLETE")
    print("=" * 60)
    print(f"Images analyzed: {len(results)}")
    print(f"Output:          {OUTPUT_FILE}")

    if results:
        first = results[0]
        print(f"\nFirst image: {first['file']}")
        print(f"  Size:       {first['width']}x{first['height']}")
        print(f"  Orientation: {first['orientation']}")
        print(f"  Brightness:  {first['brightness']} ({first['avg_brightness']})")
        print(f"  Focal point: ({first['focal_point']['x']}, {first['focal_point']['y']})")

    print("=" * 60)


if __name__ == "__main__":
    main()
