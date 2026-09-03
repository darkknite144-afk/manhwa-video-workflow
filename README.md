# Manhwa Video Workflow

Automated AI-assisted Manhwa Shorts video production pipeline.

Converts voiceover audio + Manhwa images into polished vertical videos
(1080x1920, 30fps, H.264/AAC) suitable for YouTube Shorts, Instagram Reels,
and TikTok.

## Pipeline

```
Audio -> Transcription -> Word Timestamps -> Image Analysis
    -> AI Scene Matching -> Scene Timeline -> Camera Motion
    -> Captions -> SFX -> FFmpeg Render -> Final MP4
```

## Repository Structure

```
manhwa-video-workflow/
|
|-- assets/
|   |-- audio/          Voiceover audio files (.mp3, .wav, etc.)
|   |-- images/         Vertical Manhwa images (001.png, 002.png, ...)
|   |-- script/         Optional script.txt for semantic assistance
|   `-- sfx/            Optional sound effects (.wav)
|
|-- config/
|   |-- project.json    Main configuration (video, animation, captions, etc.)
|   `-- ai.json         AI/vision configuration
|
|-- data/               Auto-generated data (transcript, scenes, timeline)
|
|-- output/             Final video output (final_manhwa_short.mp4)
|
|-- scripts/
|   |-- transcribe.py        Whisper transcription with word timestamps
|   |-- image_analysis.py    Pillow-based image analysis (focal point, mood)
|   |-- ai_scene_match.py    AI/semantic scene-to-image matching
|   |-- match_scenes.py      Sequential scene matching (fallback)
|   |-- generate_timeline.py Camera motion + caption timing + SFX metadata
|   |-- captions.py          ASS subtitle generation from word timestamps
|   |-- render.py             FFmpeg rendering pipeline
|   `-- validate_project.py   Pre-flight validation
|
|-- requirements.txt    Python dependencies
|
`-- .github/
    `-- workflows/
        `-- build-video.yml   GitHub Actions CI/CD pipeline
```

## Quick Start

1. Place your voiceover audio in `assets/audio/`
2. Place your Manhwa images in `assets/images/` (vertical format preferred)
3. Optionally place a script in `assets/script/script.txt`
4. Optionally place SFX files in `assets/sfx/`
5. Run the pipeline locally:

```bash
pip install -r requirements.txt
python scripts/validate_project.py
python scripts/transcribe.py
python scripts/image_analysis.py
python scripts/ai_scene_match.py
python scripts/match_scenes.py
python scripts/generate_timeline.py
python scripts/captions.py
python scripts/render.py
```

Or trigger via GitHub Actions (automatic on push, or manual via `workflow_dispatch`).

## Output

- `output/final_manhwa_short.mp4` - Final rendered video
- `data/transcript.json` - Transcription with word timestamps
- `data/scenes_ai.json` - AI-matched scenes
- `data/timeline.json` - Full timeline with camera motion + captions
- `data/captions.ass` - ASS subtitle file
- `data/image_analysis.json` - Image analysis results

## Configuration

All settings are in `config/project.json`. Key settings:

| Setting | Default | Description |
|---------|---------|-------------|
| `video.width` | 1080 | Output width |
| `video.height` | 1920 | Output height |
| `video.fps` | 30 | Frames per second |
| `animation.min_scale` | 1.0 | Minimum zoom scale |
| `animation.max_scale` | 1.12 | Maximum zoom scale |
| `captions.max_words` | 6 | Max words per caption line |
| `transcription.model` | base | Whisper model (tiny/base/small/medium) |
| `sfx.volume` | 0.3 | SFX volume (0-1) |

## Fallback System

The pipeline never crashes when AI services are unavailable:

1. AI vision matching -> falls back to semantic keyword matching
2. Semantic matching -> falls back to sequential image assignment
3. Missing SFX -> continues without sound effects
4. Missing script -> continues without semantic assistance

## Requirements

- Python 3.11+
- FFmpeg (installed via apt in GitHub Actions)
- openai-whisper
- Pillow
