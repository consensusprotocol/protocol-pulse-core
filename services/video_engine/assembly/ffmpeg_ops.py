"""
FFmpeg Operations
==================
Low-level ffmpeg/ffprobe wrappers for local video assembly.
All operations use subprocess with proper error checking.
"""
import json
import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger("FFmpegOps")


def _run(cmd: list, timeout: int = 300, label: str = "ffmpeg") -> subprocess.CompletedProcess:
    """Run a command with error checking."""
    logger.debug(f"  [{label}] {' '.join(str(c) for c in cmd)}")
    result = subprocess.run(
        [str(c) for c in cmd],
        capture_output=True, timeout=timeout
    )
    if result.returncode != 0:
        stderr = result.stderr.decode(errors="replace")[:500]
        raise RuntimeError(f"{label} failed (rc={result.returncode}): {stderr}")
    return result


def probe(input_path: str) -> dict:
    """Get media info via ffprobe. Returns dict with duration, width, height, codecs."""
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", str(input_path)
    ]
    result = _run(cmd, label="ffprobe")
    info = json.loads(result.stdout)

    out = {
        "duration": float(info.get("format", {}).get("duration", 0)),
        "streams": [],
    }

    for s in info.get("streams", []):
        stream = {"codec_type": s.get("codec_type"), "codec_name": s.get("codec_name")}
        if s.get("codec_type") == "video":
            stream["width"] = int(s.get("width", 0))
            stream["height"] = int(s.get("height", 0))
            stream["fps"] = _parse_fps(s.get("r_frame_rate", "30/1"))
            out["width"] = stream["width"]
            out["height"] = stream["height"]
        elif s.get("codec_type") == "audio":
            stream["sample_rate"] = int(s.get("sample_rate", 44100))
            stream["channels"] = int(s.get("channels", 2))
        out["streams"].append(stream)

    return out


def _parse_fps(r_frame_rate: str) -> float:
    """Parse ffprobe r_frame_rate like '30/1' or '30000/1001'."""
    try:
        num, den = r_frame_rate.split("/")
        return round(float(num) / float(den), 2)
    except Exception:
        return 30.0


def get_duration(input_path: str) -> float:
    """Get duration in seconds."""
    return probe(input_path)["duration"]


def concat_clips(clip_paths: list, output_path: str, copy_codec: bool = True) -> str:
    """
    Concatenate clips using ffmpeg concat demuxer.
    If copy_codec=True, uses stream copy (fastest, requires same codec/params).
    If False, re-encodes to h264/aac (slower, but handles mixed inputs).
    """
    if not clip_paths:
        raise ValueError("No clips to concatenate")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # Write concat list file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        for path in clip_paths:
            f.write(f"file '{os.path.abspath(path)}'\n")
        list_file = f.name

    try:
        if copy_codec:
            cmd = [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", list_file, "-c", "copy", output_path
            ]
        else:
            cmd = [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", list_file,
                "-c:v", "libx264", "-preset", "fast", "-crf", "20",
                "-c:a", "aac", "-b:a", "192k",
                "-movflags", "+faststart",
                output_path
            ]
        _run(cmd, timeout=600, label="concat")
    finally:
        os.unlink(list_file)

    logger.info(f"  Concatenated {len(clip_paths)} clips -> {output_path}")
    return output_path


def add_audio_mix(video_path: str, audio_path: str, output_path: str,
                  audio_volume: float = 1.0, video_volume: float = 0.0) -> str:
    """
    Mix audio onto video.
    video_volume=0 replaces video audio entirely.
    video_volume>0 mixes both tracks.
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    if video_volume > 0:
        # Mix both audio tracks
        filter_complex = (
            f"[0:a]volume={video_volume}[va];"
            f"[1:a]volume={audio_volume}[na];"
            f"[va][na]amix=inputs=2:duration=first[out]"
        )
        cmd = [
            "ffmpeg", "-y", "-i", video_path, "-i", audio_path,
            "-filter_complex", filter_complex, "-map", "0:v", "-map", "[out]",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-shortest", output_path
        ]
    else:
        # Replace audio entirely
        cmd = [
            "ffmpeg", "-y", "-i", video_path, "-i", audio_path,
            "-map", "0:v", "-map", "1:a",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-shortest", output_path
        ]

    _run(cmd, timeout=300, label="audio_mix")
    return output_path


def overlay_image(video_path: str, image_path: str, output_path: str,
                  x: int = 0, y: int = 0,
                  start: float = 0, end: float = None) -> str:
    """Overlay a PNG image on video (supports alpha transparency)."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    if end is None:
        end = get_duration(video_path)

    enable = f"between(t,{start},{end})"
    cmd = [
        "ffmpeg", "-y", "-i", video_path, "-i", image_path,
        "-filter_complex",
        f"[0:v][1:v]overlay={x}:{y}:enable='{enable}'[out]",
        "-map", "[out]", "-map", "0:a?",
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-c:a", "copy",
        output_path
    ]
    _run(cmd, timeout=300, label="overlay")
    return output_path


def add_text_overlay(video_path: str, text: str, output_path: str,
                     fontfile: str = None,
                     fontsize: int = 48, fontcolor: str = "white",
                     x: str = "(w-tw)/2", y: str = "(h-th)/2",
                     start: float = 0, end: float = None,
                     box: bool = False, boxcolor: str = "black@0.5") -> str:
    """Add text overlay using drawtext filter."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    if end is None:
        end = get_duration(video_path)

    # Escape special characters for drawtext
    safe_text = text.replace("'", "\\'").replace(":", "\\:")

    dt = f"drawtext=text='{safe_text}':fontsize={fontsize}:fontcolor={fontcolor}"
    dt += f":x={x}:y={y}"
    dt += f":enable='between(t,{start},{end})'"

    if fontfile:
        dt += f":fontfile='{fontfile}'"

    if box:
        dt += f":box=1:boxcolor={boxcolor}:boxborderw=10"

    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-vf", dt,
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-c:a", "copy",
        output_path
    ]
    _run(cmd, timeout=300, label="text_overlay")
    return output_path


def crossfade(clip1: str, clip2: str, duration: float, output_path: str) -> str:
    """Apply crossfade transition between two clips."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    dur1 = get_duration(clip1)

    offset = max(0, dur1 - duration)

    cmd = [
        "ffmpeg", "-y", "-i", clip1, "-i", clip2,
        "-filter_complex",
        f"[0:v][1:v]xfade=transition=fade:duration={duration}:offset={offset}[v];"
        f"[0:a][1:a]acrossfade=d={duration}[a]",
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k",
        output_path
    ]
    _run(cmd, timeout=300, label="crossfade")
    return output_path


def scale_and_pad(input_path: str, output_path: str,
                  w: int = 1920, h: int = 1080,
                  bg_color: str = "black") -> str:
    """Scale input to fit within w x h, pad with bg_color to exact dimensions."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    vf = f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color={bg_color}"

    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-vf", vf,
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k",
        "-r", "30",
        "-movflags", "+faststart",
        output_path
    ]
    _run(cmd, timeout=300, label="scale_pad")
    return output_path


def extract_audio(video_path: str, output_path: str,
                  codec: str = "libmp3lame", bitrate: str = "192k") -> str:
    """Extract audio track from video."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-vn", "-c:a", codec, "-b:a", bitrate,
        output_path
    ]
    _run(cmd, timeout=120, label="extract_audio")
    return output_path


def trim_clip(input_path: str, output_path: str,
              start: float, end: float, copy: bool = True) -> str:
    """Trim a clip from start to end seconds."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    cmd = ["ffmpeg", "-y", "-ss", str(start), "-to", str(end), "-i", input_path]

    if copy:
        cmd += ["-c", "copy"]
    else:
        cmd += ["-c:v", "libx264", "-preset", "fast", "-crf", "20",
                "-c:a", "aac", "-b:a", "192k"]

    cmd.append(output_path)
    _run(cmd, timeout=120, label="trim")
    return output_path


def loudnorm(input_path: str, output_path: str,
             target_i: float = -16, target_tp: float = -1.5,
             target_lra: float = 11) -> str:
    """Apply EBU R128 loudness normalization."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-af", f"loudnorm=I={target_i}:TP={target_tp}:LRA={target_lra}",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k",
        output_path
    ]
    _run(cmd, timeout=300, label="loudnorm")
    return output_path


def generate_color_clip(output_path: str, duration: float = 5,
                        color: str = "black",
                        w: int = 1920, h: int = 1080,
                        fps: int = 30) -> str:
    """Generate a solid color video clip with silent audio."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c={color}:s={w}x{h}:d={duration}:r={fps}",
        "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo",
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-c:a", "aac", "-b:a", "128k",
        "-t", str(duration),
        "-movflags", "+faststart",
        output_path
    ]
    _run(cmd, timeout=60, label="color_clip")
    return output_path


def image_to_video(image_path: str, output_path: str,
                   duration: float = 5, fps: int = 30) -> str:
    """Convert a still image to a video clip with silent audio."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", image_path,
        "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-t", str(duration),
        "-pix_fmt", "yuv420p",
        "-r", str(fps),
        "-c:a", "aac", "-b:a", "128k",
        "-shortest",
        "-movflags", "+faststart",
        output_path
    ]
    _run(cmd, timeout=60, label="img2video")
    return output_path


def audio_over_image(image_path: str, audio_path: str, output_path: str,
                     fps: int = 30) -> str:
    """Create video from still image + audio track. Duration matches audio."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", image_path,
        "-i", audio_path,
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-r", str(fps),
        "-shortest",
        "-movflags", "+faststart",
        output_path
    ]
    _run(cmd, timeout=120, label="audio_over_image")
    return output_path


def frames_to_video(frame_pattern: str, output_path: str,
                    fps: int = 30, audio_path: str = None) -> str:
    """Encode PNG frame sequence to video. frame_pattern like '/tmp/frames/frame_%04d.png'."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    cmd = ["ffmpeg", "-y", "-framerate", str(fps), "-i", frame_pattern]

    if audio_path:
        cmd += ["-i", audio_path]

    cmd += [
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
    ]

    if audio_path:
        cmd += ["-c:a", "aac", "-b:a", "192k", "-shortest"]
    else:
        # Add silent audio track for concat compatibility
        cmd = ["ffmpeg", "-y", "-framerate", str(fps), "-i", frame_pattern,
               "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
               "-c:v", "libx264", "-preset", "fast", "-crf", "20",
               "-pix_fmt", "yuv420p",
               "-c:a", "aac", "-b:a", "128k",
               "-shortest",
               "-movflags", "+faststart"]

    cmd.append(output_path)
    _run(cmd, timeout=120, label="frames2video")
    return output_path
