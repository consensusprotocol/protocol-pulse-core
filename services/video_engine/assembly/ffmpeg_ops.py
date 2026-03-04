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


def audio_over_looping_video(video_bg_path: str, audio_path: str,
                              output_path: str, bg_music_path: str = None,
                              bg_music_vol: float = 0.125,
                              w: int = 1920, h: int = 1080, fps: int = 30) -> str:
    """Create video from looping background video + TTS audio + optional bg music.

    Args:
        video_bg_path: Short video to loop as background
        audio_path: TTS audio (determines duration)
        output_path: Output file
        bg_music_path: Optional background music to mix at bg_music_vol
        bg_music_vol: Volume for bg music (0.125 = ~-18dB)
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    audio_dur = get_duration(audio_path)

    # Calculate loop count needed (ceil to ensure enough video)
    bg_dur = get_duration(video_bg_path)
    loop_count = max(0, int(audio_dur / bg_dur) + 1) if bg_dur > 0 else 10

    if bg_music_path and os.path.exists(bg_music_path):
        # Loop bg video + TTS audio + bg music mixed
        # bg music fades in over 1s, fades out over 1s at end
        fade_out_start = max(0, audio_dur - 1.0)
        cmd = [
            "ffmpeg", "-y",
            "-stream_loop", str(loop_count), "-i", video_bg_path,  # [0] looping bg
            "-i", audio_path,                                       # [1] TTS audio
            "-i", bg_music_path,                                    # [2] bg music
            "-filter_complex",
            f"[0:v]scale={w}:{h}:force_original_aspect_ratio=decrease,"
            f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black,fps={fps}[bg];"
            f"[1:a]aformat=sample_rates=44100:channel_layouts=stereo[tts];"
            f"[2:a]volume={bg_music_vol},"
            f"afade=t=in:st=0:d=1,"
            f"afade=t=out:st={fade_out_start}:d=1,"
            f"aformat=sample_rates=44100:channel_layouts=stereo[music];"
            f"[tts][music]amix=inputs=2:duration=first:dropout_transition=0[audio]",
            "-map", "[bg]", "-map", "[audio]",
            "-c:v", "libx264", "-preset", "fast", "-crf", "20",
            "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-t", str(audio_dur + 0.5),
            "-movflags", "+faststart",
            output_path
        ]
    else:
        # Loop bg video + TTS audio only (no bg music)
        cmd = [
            "ffmpeg", "-y",
            "-stream_loop", str(loop_count), "-i", video_bg_path,
            "-i", audio_path,
            "-filter_complex",
            f"[0:v]scale={w}:{h}:force_original_aspect_ratio=decrease,"
            f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black,fps={fps}[bg]",
            "-map", "[bg]", "-map", "1:a",
            "-c:v", "libx264", "-preset", "fast", "-crf", "20",
            "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-t", str(audio_dur + 0.5),
            "-movflags", "+faststart",
            output_path
        ]

    _run(cmd, timeout=120, label="audio_over_looping_video")
    return output_path


def overlay_png_timed(video_path: str, overlay_path: str, output_path: str,
                      x: str = "W-w-20", y: str = "20",
                      start: float = 0, end: float = None,
                      fade_in: float = 0.3, fade_out: float = 0.3) -> str:
    """Overlay a transparent PNG on video with fade in/out timing."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    if end is None:
        end = get_duration(video_path)

    # Build overlay filter with alpha fade
    fade_in_end = start + fade_in
    fade_out_start = end - fade_out
    enable = f"between(t,{start},{end})"

    # Simple overlay with enable timing (no alpha animation for reliability)
    cmd = [
        "ffmpeg", "-y", "-i", video_path, "-i", overlay_path,
        "-filter_complex",
        f"[0:v][1:v]overlay={x}:{y}:enable='{enable}':format=auto[out]",
        "-map", "[out]", "-map", "0:a?",
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-c:a", "copy",
        output_path
    ]
    _run(cmd, timeout=300, label="overlay_timed")
    return output_path


def multi_overlay(video_path: str, overlays: list, output_path: str) -> str:
    """Apply multiple PNG overlays on video in a single ffmpeg call.

    Args:
        overlays: list of dicts with keys:
            path: overlay PNG path
            x: x position (ffmpeg expression)
            y: y position (ffmpeg expression)
            start: start time in seconds
            end: end time in seconds
    """
    if not overlays:
        import shutil
        shutil.copy2(video_path, output_path)
        return output_path

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    inputs = ["-i", video_path]
    for ov in overlays:
        inputs += ["-i", ov["path"]]

    # Build chain of overlays
    filter_parts = []
    prev = "0:v"
    for i, ov in enumerate(overlays):
        out_label = f"v{i}" if i < len(overlays) - 1 else "out"
        enable = f"between(t,{ov['start']},{ov['end']})"
        filter_parts.append(
            f"[{prev}][{i+1}:v]overlay={ov['x']}:{ov['y']}:"
            f"enable='{enable}':format=auto[{out_label}]"
        )
        prev = out_label

    cmd = ["ffmpeg", "-y"] + inputs + [
        "-filter_complex", ";".join(filter_parts),
        "-map", "[out]", "-map", "0:a?",
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-c:a", "copy",
        output_path
    ]
    _run(cmd, timeout=300, label="multi_overlay")
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
