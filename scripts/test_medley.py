#!/usr/bin/env python3
"""Batch 3 smoke test: narration + compilation into master Intelligence Reel.

Gate: produce a playable MP4 with narrator segments stitched around 2 partner clips.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.elevenlabs_service import ElevenLabsService  # noqa: E402


def _run(cmd: list[str], timeout: int = 900) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def _ffprobe_duration(path: Path) -> float:
    proc = _run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=nw=1:nk=1",
            str(path),
        ],
        timeout=30,
    )
    if proc.returncode != 0:
        return 0.0
    try:
        return float((proc.stdout or "").strip() or 0.0)
    except Exception:
        return 0.0


def _render_narration_segment(bg: Path, audio: Path, out: Path) -> bool:
    dur = _ffprobe_duration(audio)
    if dur <= 0:
        return False

    # Simple Protocol Pulse hue signature overlay.
    vf = (
        "scale=1920:1080:force_original_aspect_ratio=increase,"
        "crop=1920:1080,format=yuv420p,"
        "drawbox=x=0:y=0:w=iw:h=ih:color=#DC2626@0.06:t=fill,"
        "drawbox=x=0:y=620:w=iw:h=460:color=#0A0A0A@0.35:t=fill"
    )

    cmd = [
        "ffmpeg",
        "-y",
        "-loop",
        "1",
        "-i",
        str(bg),
        "-i",
        str(audio),
        "-t",
        f"{dur:.3f}",
        "-vf",
        vf,
        "-c:v",
        "h264_nvenc",
        "-preset",
        "p4",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-shortest",
        "-movflags",
        "+faststart",
        str(out),
    ]

    proc = _run(cmd, timeout=300)
    if proc.returncode != 0:
        # CPU fallback.
        cmd2 = [c for c in cmd]
        cmd2[cmd2.index("h264_nvenc")] = "libx264"
        cmd2 = [x for x in cmd2 if x not in {"-preset", "p4"}]
        proc = _run(cmd2, timeout=420)

    return proc.returncode == 0 and out.exists() and out.stat().st_size > 10_000


def _concat_segments(segments: list[Path], out: Path) -> bool:
    # Use concat demuxer then re-encode (robust across mismatched sources).
    concat_txt = out.parent / "concat_medley.txt"
    concat_txt.write_text("".join([f"file '{p.as_posix()}'\n" for p in segments]), encoding="utf-8")

    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_txt),
        "-c:v",
        "h264_nvenc",
        "-preset",
        "p4",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-movflags",
        "+faststart",
        str(out),
    ]
    proc = _run(cmd, timeout=900)
    if proc.returncode != 0:
        cmd2 = [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_txt),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-movflags",
            "+faststart",
            str(out),
        ]
        proc = _run(cmd2, timeout=1200)

    return proc.returncode == 0 and out.exists() and out.stat().st_size > 20_000


def main() -> int:
    clips_dir = PROJECT_ROOT / "data" / "clips"
    # Allow explicit override for the validator.
    env_clip1 = os.environ.get("MEDLEY_CLIP_1")
    env_clip2 = os.environ.get("MEDLEY_CLIP_2")
    clip1 = Path(env_clip1) if env_clip1 else (clips_dir / "job_2_seg_01.mp4")
    clip2 = Path(env_clip2) if env_clip2 else (clips_dir / "job_2_seg_02.mp4")

    if not clip1.exists() or not clip2.exists():
        # Fallback: pick the two newest mp4s in data/clips/
        mp4s = sorted(
            [p for p in clips_dir.glob("*.mp4") if p.is_file()],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if len(mp4s) >= 2:
            clip1, clip2 = mp4s[0], mp4s[1]
        else:
            print("FAIL: no clip mp4s found in data/clips/ and MEDLEY_CLIP_1/2 not set")
            return 1

    bg = PROJECT_ROOT / "static" / "img" / "terminal_bg.png"
    if not bg.exists():
        print("FAIL: missing static/img/terminal_bg.png")
        return 1

    partner = (os.environ.get("MEDLEY_PARTNER_NAME") or "Partner").strip()
    intro_text = f"Watch as {partner} explains why the Bitcoin signal is tightening. Here's the setup."
    bridge_text = f"Watch as {partner} explains the next angle as the narrative shifts. Then we close with the key takeaway."
    outro_text = "That's the intelligence reel. Lock the signal, ignore the noise."

    svc = ElevenLabsService()
    if not svc.api_key:
        print("FAIL: ELEVENLABS_API_KEY missing")
        return 1

    out_dir = PROJECT_ROOT / "logs"
    out_dir.mkdir(parents=True, exist_ok=True)

    intro_audio = out_dir / "batch3_smoke_intro.mp3"
    bridge_audio = out_dir / "batch3_smoke_bridge.mp3"
    outro_audio = out_dir / "batch3_smoke_outro.mp3"

    r1 = svc.synthesize(text=intro_text, out_path=intro_audio, use_alignment=True)
    r2 = svc.synthesize(text=bridge_text, out_path=bridge_audio, use_alignment=True)
    r3 = svc.synthesize(text=outro_text, out_path=outro_audio, use_alignment=True)
    if not (r1.ok and r2.ok and r3.ok):
        print("FAIL: narration synthesis failed", r1, r2, r3)
        return 1

    intro_vid = out_dir / "batch3_smoke_intro.mp4"
    bridge_vid = out_dir / "batch3_smoke_bridge.mp4"
    outro_vid = out_dir / "batch3_smoke_outro.mp4"
    if not _render_narration_segment(bg, intro_audio, intro_vid):
        print("FAIL: intro segment render failed")
        return 1
    if not _render_narration_segment(bg, bridge_audio, bridge_vid):
        print("FAIL: bridge segment render failed")
        return 1
    if not _render_narration_segment(bg, outro_audio, outro_vid):
        print("FAIL: outro segment render failed")
        return 1

    master = out_dir / "intelligence_reel_master.mp4"
    segments = [intro_vid, clip1, bridge_vid, clip2, outro_vid]
    if not _concat_segments(segments, master):
        print("FAIL: concat master render failed")
        return 1

    dur = _ffprobe_duration(master)
    if dur <= 0:
        print("FAIL: master has invalid duration")
        return 1

    print("OK: master reel built", str(master))
    print("Narrator required phrase used:", f"Watch as {partner} explains...")
    print("Synthesis model:", svc.model_id, "alignment:", (r1.used_alignment or r2.used_alignment or r3.used_alignment))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

