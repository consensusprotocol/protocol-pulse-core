"""Immutable codec law. Every value here is gospel — no segment may deviate."""

VIDEO_W = 1920
VIDEO_H = 1080
VIDEO_FPS = 30
VIDEO_PIX_FMT = "yuv420p"
VIDEO_CODEC = "libx264"
VIDEO_CRF = 17
VIDEO_PRESET = "medium"
VIDEO_BITRATE = "8M"
VIDEO_MAXRATE = "10M"
VIDEO_BUFSIZE = "15M"

AUDIO_CODEC = "aac"
AUDIO_BITRATE = "192k"
AUDIO_SAMPLE_RATE = 48000
AUDIO_CHANNELS = 2
AUDIO_FORMAT = "fltp"
AUDIO_TARGET_LUFS = -14.0
AUDIO_MAX_TRUE_PEAK = -2.0
AUDIO_LRA = 7.0
AUDIO_LIMITER = 0.85

# Asset paths (all relative to PIPELINE_DIR)
import os
from pathlib import Path
PIPELINE_DIR = Path(__file__).parent.parent  # video_pipeline_v3/
ASSETS_DIR = PIPELINE_DIR / "assets"
INTRO_TAG = ASSETS_DIR / "intro_tag.mp4"
INTRO_MUSIC = ASSETS_DIR / "intro_music.mp3"
BG_LOOP = ASSETS_DIR / "bg_loop.mp4"
OUTRO_BRANDED = ASSETS_DIR / "outro_branded_new.mp4"
SCANLINE = ASSETS_DIR / "scanline_overlay.png"
SFX_WHOOSH = ASSETS_DIR / "sfx" / "custom_whoosh.wav"
SFX_SWOOSH = ASSETS_DIR / "sfx" / "card_swoosh.wav"
FONT_BOLD = ASSETS_DIR / "fonts" / "JetBrainsMono-Bold.ttf"
FONT_MONO = ASSETS_DIR / "fonts" / "JetBrainsMono-Regular.ttf"
CHARTS_DIR = PIPELINE_DIR / "cache" / "charts"

# Brand colors
COLOR_BG = "0x0A0A0F"
COLOR_RED = "0xFF3B5F"
COLOR_WHITE = "0xFFFFFF"
COLOR_CYAN = "0x5DE4FF"

# QC acceptance policy
QC_MIN_DURATION = 480   # 8 minutes
QC_MAX_DURATION = 900   # 15 minutes
QC_MAX_FILLER_SECONDS = 60
QC_MAX_DEGRADED_SEGMENTS = 2
QC_MAX_BLACK_FRAME_SECONDS = 2.0
QC_MAX_SILENCE_SECONDS = 2.0
