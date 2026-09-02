import json
import sys
from pathlib import Path


# ---------------------------------------------------------
# PATHS
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

CONFIG_FILE = PROJECT_ROOT / "config" / "project.json"
SCENES_FILE = PROJECT_ROOT / "data" / "scenes.json"
OUTPUT_FILE = PROJECT_ROOT / "data" / "timeline.json"


# ---------------------------------------------------------
# LOAD FILES
# ---------------------------------------------------------

if not CONFIG_FILE.exists():
    print("ERROR: config/project.json not found.")
    sys.exit(1)

if not SCENES_FILE.exists():
    print("ERROR: data/scenes.json not found.")
    print("Run match_scenes.py first.")
    sys.exit(1)


with open(CONFIG_FILE, "r", encoding="utf-8") as f:
    config = json.load(f)

with open(SCENES_FILE, "r", encoding="utf-8") as f:
    scene_data = json.load(f)


# ---------------------------------------------------------
# VIDEO SETTINGS
# ---------------------------------------------------------

video_config = config["video"]

WIDTH = video_config["width"]
HEIGHT = video_config["height"]
FPS = video_config["fps"]


# ---------------------------------------------------------
# ANIMATION SETTINGS
# ---------------------------------------------------------

animation_config = config.get("animation", {})

MIN_SCALE = animation_config.get("min_scale", 1.0)
MAX_SCALE = animation_config.get("max_scale", 1.12)

EASING = animation_config.get(
    "easing",
    "ease_in_out"
)


# ---------------------------------------------------------
# MOTION PATTERNS
# ---------------------------------------------------------

MOTION_PATTERNS = [

    {
        "name": "zoom_in",
        "start": {
            "x": 0.50,
            "y": 0.50,
            "scale": MIN_SCALE
        },
        "end": {
            "x": 0.50,
            "y": 0.50,
            "scale": MAX_SCALE
        }
    },

    {
        "name": "zoom_out",
        "start": {
            "x": 0.50,
            "y": 0.50,
            "scale": MAX_SCALE
        },
        "end": {
            "x": 0.50,
            "y": 0.50,
            "scale": MIN_SCALE
        }
    },

    {
        "name": "pan_left",
        "start": {
            "x": 0.60,
            "y": 0.50,
            "scale": 1.06
        },
        "end": {
            "x": 0.40,
            "y": 0.50,
            "scale": 1.06
        }
    },

    {
        "name": "pan_right",
        "start": {
            "x": 0.40,
            "y": 0.50,
            "scale": 1.06
        },
        "end": {
            "x": 0.60,
            "y": 0.50,
            "scale": 1.06
        }
    },

    {
        "name": "pan_up",
        "start": {
            "x": 0.50,
            "y": 0.60,
            "scale": 1.06
        },
        "end": {
            "x": 0.50,
            "y": 0.40,
            "scale": 1.06
        }
    },

    {
        "name": "pan_down",
        "start": {
            "x": 0.50,
            "y": 0.40,
            "scale": 1.06
        },
        "end": {
            "x": 0.50,
            "y": 0.60,
            "scale": 1.06
        }
    }
]


# ---------------------------------------------------------
# CREATE TIMELINE
# ---------------------------------------------------------

timeline_scenes = []

scenes = scene_data.get("scenes", [])


for index, scene in enumerate(scenes):

    motion = MOTION_PATTERNS[
        index % len(MOTION_PATTERNS)
    ]

    duration = float(scene["duration"])

    # Very short shots don't need heavy movement.
    if duration < 1.0:

        motion = {
            "name": "static",

            "start": {
                "x": 0.50,
                "y": 0.50,
                "scale": 1.02
            },

            "end": {
                "x": 0.50,
                "y": 0.50,
                "scale": 1.02
            }
        }


    timeline_scene = {

        "id": scene["id"],

        "image": scene["image"],

        "start": scene["start"],

        "end": scene["end"],

        "duration": duration,

        "text": scene["text"],

        "animation": {

            "type": motion["name"],

            "easing": EASING,

            "keyframes": [

                {
                    "time": 0.0,

                    "x": motion["start"]["x"],

                    "y": motion["start"]["y"],

                    "scale": motion["start"]["scale"]
                },

                {
                    "time": duration,

                    "x": motion["end"]["x"],

                    "y": motion["end"]["y"],

                    "scale": motion["end"]["scale"]
                }
            ]
        },

        "transition": {

            "type": "cut",

            "duration": 0.0
        },

        "caption": {

            "enabled": config["captions"]["enabled"],

            "text": scene["text"],

            "start": scene["start"],

            "end": scene["end"],

            "position": config["captions"].get(
                "position",
                "bottom"
            ),

            "max_words": config["captions"].get(
                "max_words",
                6
            )
        }
    }

    timeline_scenes.append(timeline_scene)


# ---------------------------------------------------------
# PROJECT TIMELINE
# ---------------------------------------------------------

total_duration = 0.0

if timeline_scenes:
    total_duration = max(
        scene["end"]
        for scene in timeline_scenes
    )


timeline = {

    "project": scene_data.get(
        "project",
        "manhwa-shorts"
    ),

    "format": {

        "width": WIDTH,

        "height": HEIGHT,

        "fps": FPS,

        "aspect_ratio": "9:16"
    },

    "duration": round(
        total_duration,
        3
    ),

    "scenes": timeline_scenes
}


# ---------------------------------------------------------
# SAVE
# ---------------------------------------------------------

with open(
    OUTPUT_FILE,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        timeline,
        f,
        ensure_ascii=False,
        indent=2
    )


# ---------------------------------------------------------
# SUMMARY
# ---------------------------------------------------------

print("=" * 60)
print("TIMELINE GENERATION COMPLETE")
print("=" * 60)

print("Resolution:", WIDTH, "x", HEIGHT)

print("FPS:", FPS)

print(
    "Duration:",
    round(total_duration, 3),
    "seconds"
)

print(
    "Scenes:",
    len(timeline_scenes)
)

print(
    "Output:",
    OUTPUT_FILE
)

print("=" * 60)
