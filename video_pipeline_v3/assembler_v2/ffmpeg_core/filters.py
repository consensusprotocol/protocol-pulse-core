"""
Protocol Pulse V2 - ffmpeg_core/filters.py
Reusable FFmpeg filter snippets. Pure functions — return filter strings.
No FFmpeg calls here. All transforms composable.
"""
from __future__ import annotations
from ..constants import (
    VIDEO_W, VIDEO_H, VIDEO_FPS, VIDEO_PIX_FMT,
    AUDIO_SAMPLE_RATE, AUDIO_CHANNELS, AUDIO_FORMAT,
    AUDIO_TARGET_LUFS, AUDIO_MAX_TRUE_PEAK, AUDIO_LRA, AUDIO_LIMITER,
    COLOR_BG
)


def normalize_video(label_in: str, label_out: str,
                    w: int = VIDEO_W, h: int = VIDEO_H) -> str:
    """Scale, set SAR, set pixel format, reset PTS. Apply to every video input."""
    return (
        f"[{label_in}]scale={w}:{h}:force_original_aspect_ratio=decrease,"
        f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:{COLOR_BG},"
        f"setsar=1,format={VIDEO_PIX_FMT},"
        f"fps={VIDEO_FPS},"
        f"setpts=PTS-STARTPTS[{label_out}]"
    )


def normalize_audio(label_in: str, label_out: str,
                    apply_loudnorm: bool = False) -> str:
    """
    Normalize audio to pipeline standard.
    apply_loudnorm=True for final voice segments.
    apply_loudnorm=False for clips where we preserve original dynamics.
    Always: resample, stereo, reset PTS, limiter.
    """
    chain = (
        f"[{label_in}]aformat=channel_layouts=stereo:"
        f"sample_rates={AUDIO_SAMPLE_RATE}:sample_fmts={AUDIO_FORMAT},"
        f"asetpts=PTS-STARTPTS"
    )
    if apply_loudnorm:
        chain += (
            f",loudnorm=I={AUDIO_TARGET_LUFS}:TP={AUDIO_MAX_TRUE_PEAK}"
            f":LRA={AUDIO_LRA}:linear=true"
        )
    chain += f",alimiter=limit={AUDIO_LIMITER}:attack=5:release=50[{label_out}]"
    return chain


def overlay_pip(bg_label: str, pip_label: str, out_label: str,
                x: int = 1240, y: int = 160,
                w: int = 640, h: int = 360) -> str:
    """
    Overlay PiP video on background.
    eof_action=pass: PiP loops without freezing at end.
    """
    return (
        f"[{pip_label}]scale={w}:{h}:force_original_aspect_ratio=decrease,"
        f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:{COLOR_BG},"
        f"format={VIDEO_PIX_FMT}[pip_scaled];"
        f"[{bg_label}][pip_scaled]overlay=x={x}:y={y}:"
        f"eof_action=pass:shortest=0[{out_label}]"
    )


def build_waveform(audio_label: str, out_label: str,
                   w: int = 1920, h: int = 80,
                   color: str = "0xFF3B5F") -> str:
    """Waveform visualizer strip from audio signal."""
    return (
        f"[{audio_label}]showwaves=s={w}x{h}:mode=cline:"
        f"colors={color}@0.8:scale=sqrt,format={VIDEO_PIX_FMT}[{out_label}]"
    )


def fade_video(label_in: str, label_out: str,
               duration: float, fade_out_dur: float = 0.3) -> str:
    """Add fade-out to end of video segment."""
    fade_start = max(0.0, duration - fade_out_dur)
    return (
        f"[{label_in}]fade=t=out:st={fade_start:.3f}:"
        f"d={fade_out_dur}[{label_out}]"
    )


def drawtext(label_in: str, label_out: str,
             text: str, font: str, size: int,
             color: str, x: str, y: str,
             box: bool = False, box_color: str = "black@0.5") -> str:
    """Single drawtext filter. Sanitize text before calling."""
    safe = text.replace("'", "\'").replace(":", "\:").replace("\n", "")
    box_str = f":box=1:boxcolor={box_color}:boxborderw=8" if box else ""
    return (
        f"[{label_in}]drawtext=fontfile={font}:text='{safe}':"
        f"fontcolor={color}:fontsize={size}:x={x}:y={y}{box_str}[{label_out}]"
    )
