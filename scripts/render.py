import json
import subprocess
import sys
import tempfile
from pathlib import Path


# ---------------------------------------------------------
# PATHS
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

CONFIG_FILE = PROJECT_ROOT / "config" / "project.json"
TIMELINE_FILE = PROJECT_ROOT / "data" / "timeline.json"
AUDIO_DIR = PROJECT_ROOT / "assets" / "audio"
OUTPUT_DIR = PROJECT_ROOT / "output"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------
# LOAD CONFIG
# ---------------------------------------------------------

if not CONFIG_FILE.exists():
    print("ERROR: config/project.json not found.")
    sys.exit(1)

if not TIMELINE_FILE.exists():
    print("ERROR: data/timeline.json not found.")
    print("Run generate_timeline.py first.")
    sys.exit(1)


with open(CONFIG_FILE, "r", encoding="utf-8") as f:
    config = json.load(f)

with open(TIMELINE_FILE, "r", encoding="utf-8") as f:
    timeline = json.load(f)


# ---------------------------------------------------------
# VIDEO SETTINGS
# ---------------------------------------------------------

WIDTH = timeline["format"]["width"]
HEIGHT = timeline["format"]["height"]
FPS = timeline["format"]["fps"]


# ---------------------------------------------------------
# FIND AUDIO
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
    if file.is_file()
    and file.suffix.lower() in audio_extensions
]

if not audio_files:
    print("ERROR: No audio file found in assets/audio/")
    sys.exit(1)

audio_file = audio_files[0]


# ---------------------------------------------------------
# CHECK FFMPEG
# ---------------------------------------------------------

try:
    subprocess.run(
        ["ffmpeg", "-version"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True
    )
except Exception:
    print("ERROR: FFmpeg is not installed.")
    sys.exit(1)


# ---------------------------------------------------------
# CREATE TEMP DIRECTORY
# ---------------------------------------------------------

temp_dir = Path(
    tempfile.mkdtemp(
        prefix="manhwa_render_"
    )
)

print("=" * 60)
print("MANHWA VIDEO RENDERER")
print("=" * 60)

print("Resolution:", WIDTH, "x", HEIGHT)
print("FPS:", FPS)
print("Audio:", audio_file.name)
print("Scenes:", len(timeline["scenes"]))

print("=" * 60)


# ---------------------------------------------------------
# CREATE INDIVIDUAL SCENE VIDEOS
# ---------------------------------------------------------

scene_files = []


for index, scene in enumerate(timeline["scenes"]):

    image_path = PROJECT_ROOT / scene["image"]

    if not image_path.exists():
        print(
            f"ERROR: Image not found: {image_path}"
        )
        sys.exit(1)

    duration = float(scene["duration"])

    animation = scene["animation"]

    keyframes = animation["keyframes"]

    start_frame = keyframes[0]
    end_frame = keyframes[-1]

    start_scale = float(
        start_frame["scale"]
    )

    end_scale = float(
        end_frame["scale"]
    )

    start_x = float(
        start_frame["x"]
    )

    end_x = float(
        end_frame["x"]
    )

    start_y = float(
        start_frame["y"]
    )

    end_y = float(
        end_frame["y"]
    )


    # -----------------------------------------------------
    # ZOOM/PAN EXPRESSION
    # -----------------------------------------------------

    frames = max(
        1,
        int(duration * FPS)
    )

    zoom_expression = (
        f"{start_scale}+"
        f"({end_scale}-{start_scale})"
        f"*on/{frames}"
    )


    x_expression = (
        f"(iw-ow)*("
        f"{start_x}+"
        f"({end_x}-{start_x})"
        f"*on/{frames}"
        f")"
    )


    y_expression = (
        f"(ih-oh)*("
        f"{start_y}+"
        f"({end_y}-{start_y})"
        f"*on/{frames}"
        f")"
    )


    # -----------------------------------------------------
    # SCALE + CROP
    # -----------------------------------------------------

    filter_complex = (
        f"scale="
        f"{WIDTH * 2}:"
        f"{HEIGHT * 2}:"
        f"force_original_aspect_ratio=increase,"
        f"crop="
        f"{WIDTH * 2}:"
        f"{HEIGHT * 2},"
        f"zoompan="
        f"z='{zoom_expression}':"
        f"x='{x_expression}':"
        f"y='{y_expression}':"
        f"d=1:"
        f"s={WIDTH}x{HEIGHT}:"
        f"fps={FPS},"
        f"setsar=1"
    )


    scene_output = temp_dir / (
        f"scene_{index:04d}.mp4"
    )

    command = [
        "ffmpeg",
        "-y",

        "-loop",
        "1",

        "-i",
        str(image_path),

        "-t",
        str(duration),

        "-vf",
        filter_complex,

        "-r",
        str(FPS),

        "-an",

        "-c:v",
        "libx264",

        "-preset",
        "medium",

        "-crf",
        "18",

        "-pix_fmt",
        "yuv420p",

        str(scene_output)
    ]


    print(
        f"\nRendering scene "
        f"{index + 1}/{len(timeline['scenes'])}"
    )

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )


    if result.returncode != 0:

        print(
            "\nFFmpeg error:\n"
        )

        print(result.stderr)

        sys.exit(1)


    scene_files.append(scene_output)


# ---------------------------------------------------------
# CREATE CONCAT FILE
# ---------------------------------------------------------

concat_file = temp_dir / "concat.txt"


with open(
    concat_file,
    "w",
    encoding="utf-8"
) as f:

    for scene_file in scene_files:

        safe_path = str(
            scene_file
        ).replace(
            "\\",
            "/"
        )

        f.write(
            f"file '{safe_path}'\n"
        )


# ---------------------------------------------------------
# CONCAT VIDEO
# ---------------------------------------------------------

joined_video = temp_dir / "joined.mp4"


print("\nJoining scenes...")


concat_command = [

    "ffmpeg",
    "-y",

    "-f",
    "concat",

    "-safe",
    "0",

    "-i",
    str(concat_file),

    "-c",
    "copy",

    str(joined_video)
]


result = subprocess.run(
    concat_command,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)


if result.returncode != 0:

    print(
        "\nConcat error:\n"
    )

    print(result.stderr)

    sys.exit(1)


# ---------------------------------------------------------
# ADD AUDIO
# ---------------------------------------------------------

output_file = (
    OUTPUT_DIR /
    "final_manhwa_short.mp4"
)


print("\nAdding audio...")


audio_command = [

    "ffmpeg",
    "-y",

    "-i",
    str(joined_video),

    "-i",
    str(audio_file),

    "-map",
    "0:v:0",

    "-map",
    "1:a:0",

    "-c:v",
    "copy",

    "-c:a",
    "aac",

    "-b:a",
    config["video"].get(
        "audio_bitrate",
        "192k"
    ),

    "-shortest",

    str(output_file)
]


result = subprocess.run(
    audio_command,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)


if result.returncode != 0:

    print(
        "\nAudio merge error:\n"
    )

    print(result.stderr)

    sys.exit(1)


# ---------------------------------------------------------
# DONE
# ---------------------------------------------------------

print("\n" + "=" * 60)

print("RENDER COMPLETE")

print("=" * 60)

print(
    "Output:",
    output_file
)

print(
    "Resolution:",
    WIDTH,
    "x",
    HEIGHT
)

print(
    "FPS:",
    FPS
)

print("=" * 60)
