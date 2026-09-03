#!/usr/bin/env python3
"""
scripts/render.py
================

Video rendering module for the Manhwa Shorts video pipeline.

Uses FFmpeg to render the final vertical video with:
    - Camera motion (zoompan per scene)
    - Captions (ASS subtitle overlay)
    - Optional SFX mixing
    - Original voiceover audio
    - 1080x1920 @ 30fps H.264 + AAC

Pipeline:
    1. Read timeline.json
    2. Render each scene with camera animation
    3. Concat all scenes
    4. Overlay captions
    5. Mix SFX (optional)
    6. Attach original audio
    7. Output final MP4

Output:
    output/final_manhwa_short.mp4

Usage:
    python scripts/render.py
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


# =========================================================
# PATHS
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_FILE = PROJECT_ROOT / "config" / "project.json"
TIMELINE_FILE = PROJECT_ROOT / "data" / "timeline.json"
CAPTIONS_FILE = PROJECT_ROOT / "data" / "captions.ass"
AUDIO_DIR = PROJECT_ROOT / "assets" / "audio"
SFX_DIR = PROJECT_ROOT / "assets" / "sfx"
OUTPUT_DIR = PROJECT_ROOT / "output"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# =========================================================
# HELPER FUNCTIONS
# =========================================================

AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".mp4"}


def load_json(path, error_msg):
    """Load a JSON file with error handling."""
    if not path.exists():
        print(f"ERROR: {error_msg}")
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def find_audio_file():
    """Find the voiceover audio file."""
    if not AUDIO_DIR.exists():
        print("ERROR: assets/audio/ directory not found.")
        sys.exit(1)

    audio_files = sorted([
        f for f in AUDIO_DIR.iterdir()
        if f.is_file() and f.suffix.lower() in AUDIO_EXTENSIONS
    ])

    if not audio_files:
        print("ERROR: No audio file found in assets/audio/.")
        sys.exit(1)

    if len(audio_files) > 1:
        print(f"WARNING: Multiple audio files found. Using: {audio_files[0].name}")

    return audio_files[0]


def check_ffmpeg():
    """Verify FFmpeg is installed."""
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
    except Exception:
        print("ERROR: FFmpeg is not installed.")
        print("Install with: sudo apt-get install ffmpeg")
        sys.exit(1)


def run_ffmpeg(command, error_label="FFmpeg"):
    """Run an FFmpeg command and handle errors."""
    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        print(f"\n{error_label} error:\n")
        print(result.stderr[-2000:])
        sys.exit(1)
    return result


# =========================================================
# SCENE RENDERING
# =========================================================

def render_scene_video(
    image_path,
    duration,
    keyframes,
    width,
    height,
    fps,
    output_path,
):
    """
    Render a single scene video with zoompan camera motion.

    Uses FFmpeg's zoompan filter with interpolated keyframes.
    """
    kf_start = keyframes[0]
    kf_end = keyframes[-1]

    start_scale = float(kf_start["scale"])
    end_scale = float(kf_end["scale"])
    start_x = float(kf_start["x"])
    end_x = float(kf_end["x"])
    start_y = float(kf_start["y"])
    end_y = float(kf_end["y"])

    frames = max(1, int(duration * fps))

    # Zoompan expressions (interpolated)
    zoom_expr = f"{start_scale}+({end_scale}-{start_scale})*on/{frames}"
    x_expr = f"(iw-ow)*({start_x}+({end_x}-{start_x})*on/{frames})"
    y_expr = f"(ih-oh)*({start_y}+({end_y}-{start_y})*on/{frames})"

    # Scale up first (for quality), then zoompan to target size
    filter_complex = (
        f"scale={width * 2}:{height * 2}:"
        f"force_original_aspect_ratio=increase,"
        f"crop={width * 2}:{height * 2},"
        f"zoompan="
        f"z='{zoom_expr}':"
        f"x='{x_expr}':"
        f"y='{y_expr}':"
        f"d=1:"
        f"s={width}x{height}:"
        f"fps={fps},"
        f"setsar=1"
    )

    command = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", str(image_path),
        "-t", str(duration),
        "-vf", filter_complex,
        "-r", str(fps),
        "-an",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        str(output_path),
    ]

    run_ffmpeg(command, f"Scene render ({output_path.name})")


def concat_videos(video_files, output_path):
    """Concatenate multiple video files using FFmpeg concat demuxer."""
    concat_file = output_path.parent / "concat_list.txt"

    with open(concat_file, "w", encoding="utf-8") as f:
        for video in video_files:
            safe_path = str(video).replace("\\", "/")
            f.write(f"file '{safe_path}'\n")

    command = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_file),
        "-c", "copy",
        str(output_path),
    ]

    run_ffmpeg(command, "Concat")

    # Cleanup
    concat_file.unlink(missing_ok=True)


def overlay_captions(video_path, captions_path, output_path):
    """Overlay ASS captions on the video."""
    if not captions_path or not captions_path.exists():
        print("Captions file not found. Skipping caption overlay.")
        shutil.copy2(video_path, output_path)
        return

    # Escape path for FFmpeg filter
    ass_path_escaped = str(captions_path).replace("\\", "/").replace(":", "\\:")

    command = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-vf", f"ass='{ass_path_escaped}'",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-an",
        str(output_path),
    ]

    run_ffmpeg(command, "Caption overlay")


def mix_sfx(video_path, timeline, sfx_dir, output_path, sfx_volume=0.3):
    """
    Mix optional SFX into the video.

    If no SFX directory or no SFX files, skip silently.
    """
    if not sfx_dir or not sfx_dir.exists():
        print("No SFX directory found. Skipping SFX mix.")
        shutil.copy2(video_path, output_path)
        return

    # Collect SFX files
    sfx_files = {}
    for ext in (".wav", ".mp3", ".m4a", ".aac", ".ogg"):
        for f in sfx_dir.glob(f"*{ext}"):
            sfx_files[f.stem.lower()] = f

    if not sfx_files:
        print("No SFX files found. Skipping SFX mix.")
        shutil.copy2(video_path, output_path)
        return

    # Build SFX audio track
    sfx_inputs = []
    sfx_filter_parts = []
    input_index = 1  # 0 is the video

    scenes = timeline.get("scenes", [])

    for scene in scenes:
        sfx_file = scene.get("sfx", {}).get("file")
        if not sfx_file:
            continue

        sfx_path = PROJECT_ROOT / sfx_file
        if not sfx_path.exists():
            continue

        stem = sfx_path.stem.lower()
        if stem not in sfx_files:
            matched = None
            for key, path in sfx_files.items():
                if stem in key or key in stem:
                    matched = path
                    break
            if not matched:
                continue
            sfx_path = matched

        scene_start = float(scene.get("start", 0))

        sfx_inputs.extend(["-i", str(sfx_path)])
        delay_ms = int(scene_start * 1000)

        sfx_filter_parts.append(
            f"[{input_index}:a]adelay={delay_ms}|{delay_ms},"
            f"volume={sfx_volume}[sfx{input_index}]"
        )
        input_index += 1

    if not sfx_filter_parts:
        print("No matching SFX for scenes. Skipping SFX mix.")
        shutil.copy2(video_path, output_path)
        return

    # Build filter complex
    filter_complex = ";".join(sfx_filter_parts)

    # Mix all SFX streams together
    sfx_stream_labels = "".join(f"[sfx{i}]" for i in range(1, input_index))
    filter_complex += f";{sfx_stream_labels}amix=inputs={input_index - 1}:duration=longest[sfxmix]"

    command = [
        "ffmpeg", "-y",
        "-i", str(video_path),
    ]
    command.extend(sfx_inputs)

    command.extend([
        "-filter_complex", filter_complex,
        "-map", "0:v",
        "-map", "[sfxmix]",
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        str(output_path),
    ])

    run_ffmpeg(command, "SFX mix")


def add_audio(video_path, audio_path, output_path, audio_bitrate="192k"):
    """
    Attach the original voiceover audio to the video.

    Uses -shortest to ensure video and audio are same length.
    Audio timing is preserved exactly.
    """
    command = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-i", str(audio_path),
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", audio_bitrate,
        "-shortest",
        str(output_path),
    ]

    run_ffmpeg(command, "Audio merge")


# =========================================================
# MAIN
# =========================================================

def main():
    print("=" * 60)
    print("MANHWA VIDEO WORKFLOW - RENDER")
    print("=" * 60)

    config = load_json(CONFIG_FILE, "config/project.json not found.")
    timeline = load_json(TIMELINE_FILE, "data/timeline.json not found. Run generate_timeline.py first.")

    check_ffmpeg()

    # --- Settings ---
    video_config = config["video"]
    WIDTH = timeline["format"]["width"]
    HEIGHT = timeline["format"]["height"]
    FPS = timeline["format"]["fps"]
    AUDIO_BITRATE = video_config.get("audio_bitrate", "192k")
    SFX_VOLUME = config.get("sfx", {}).get("volume", 0.3)

    audio_file = find_audio_file()

    print(f"Resolution:  {WIDTH}x{HEIGHT}")
    print(f"FPS:         {FPS}")
    print(f"Audio:       {audio_file.name}")
    print(f"Scenes:      {len(timeline['scenes'])}")
    print(f"Duration:    {timeline.get('duration', 0)}s")
    print("=" * 60)

    # --- Temp directory ---
    temp_dir = Path(tempfile.mkdtemp(prefix="manhwa_render_"))

    try:
        # STEP 1: Render each scene
        print("\n--- Step 1: Rendering scenes ---")

        scene_files = []
        scenes = timeline["scenes"]

        for index, scene in enumerate(scenes):
            image_path = PROJECT_ROOT / scene["image"]

            if not image_path.exists():
                print(f"ERROR: Image not found: {image_path}")
                sys.exit(1)

            duration = float(scene["duration"])
            keyframes = scene["animation"]["keyframes"]

            scene_output = temp_dir / f"scene_{index:04d}.mp4"

            print(f"  [{index + 1}/{len(scenes)}] {scene['image']} ({duration:.1f}s, {scene['animation']['type']})")

            render_scene_video(
                image_path=image_path,
                duration=duration,
                keyframes=keyframes,
                width=WIDTH,
                height=HEIGHT,
                fps=FPS,
                output_path=scene_output,
            )

            scene_files.append(scene_output)

        # STEP 2: Concatenate scenes
        print("\n--- Step 2: Concatenating scenes ---")

        joined_video = temp_dir / "joined.mp4"
        concat_videos(scene_files, joined_video)
        print(f"  Joined video: {joined_video.name}")

        # STEP 3: Overlay captions
        print("\n--- Step 3: Overlaying captions ---")

        captioned_video = temp_dir / "captioned.mp4"

        if CAPTIONS_FILE.exists():
            overlay_captions(joined_video, CAPTIONS_FILE, captioned_video)
            print(f"  Captions overlaid")
        else:
            print(f"  WARNING: captions.ass not found. Run captions.py first.")
            shutil.copy2(joined_video, captioned_video)

        # STEP 4: Mix SFX (optional)
        print("\n--- Step 4: Mixing SFX ---")

        sfx_video = temp_dir / "sfx_mixed.mp4"
        mix_sfx(captioned_video, timeline, SFX_DIR, sfx_video, SFX_VOLUME)

        # STEP 5: Add original audio
        print("\n--- Step 5: Adding original audio ---")

        output_file = OUTPUT_DIR / "final_manhwa_short.mp4"
        add_audio(sfx_video, audio_file, output_file, AUDIO_BITRATE)

    finally:
        # Cleanup temp directory
        shutil.rmtree(temp_dir, ignore_errors=True)

    # DONE
    print("\n" + "=" * 60)
    print("RENDER COMPLETE")
    print("=" * 60)
    print(f"Output:      {output_file}")
    print(f"Resolution:  {WIDTH}x{HEIGHT}")
    print(f"FPS:         {FPS}")
    print(f"Duration:    {timeline.get('duration', 0)}s")
    print(f"Audio:       {audio_file.name}")
    print(f"Bitrate:     {AUDIO_BITRATE}")
    print("=" * 60)


if __name__ == "__main__":
    main()
