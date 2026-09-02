from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent.parent

required = [
    ROOT / "config" / "project.json",
    ROOT / "config" / "ai.json",
    ROOT / "scripts" / "transcribe.py",
    ROOT / "scripts" / "match_scenes.py",
    ROOT / "scripts" / "generate_timeline.py",
    ROOT / "scripts" / "render.py",
    ROOT / "scripts" / "ai_scene_match.py",
]

for file in required:
    if not file.exists():
        raise FileNotFoundError(f"Missing: {file}")

audio = list((ROOT / "assets" / "audio").glob("*"))
images = list((ROOT / "assets" / "images").glob("*"))

if not audio:
    raise RuntimeError("No audio found in assets/audio")

if not images:
    raise RuntimeError("No images found in assets/images")

with open(ROOT / "config" / "project.json", encoding="utf-8") as f:
    json.load(f)

with open(ROOT / "config" / "ai.json", encoding="utf-8") as f:
    json.load(f)

print("Project validation successful.")
print(f"Audio files: {len(audio)}")
print(f"Image files: {len(images)}")
