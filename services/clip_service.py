from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Absolute paths for all clip outputs (4090 Forge: no relative path ambiguity).
CLIPS_OUT_DIR = (PROJECT_ROOT / "data" / "clips").resolve()

from app import app, db
import models

logger = logging.getLogger(__name__)


@dataclass
class ClipRenderResult:
    ok: bool
    job_id: int
    outputs: List[str]
    errors: List[str]
    elapsed_ms: int


def _nvidia_smi_snapshot() -> str:
    """Best-effort GPU utilization snapshot (no hard dependency)."""
    try:
        proc = subprocess.run(
            [
                "nvidia-smi",
                # Include encoder/decoder utilization; NVENC often doesn't bump utilization.gpu much.
                "--query-gpu=index,name,utilization.gpu,utilization.encoder,utilization.decoder,utilization.memory,memory.used,memory.total,temperature.gpu",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=8,
        )
        if proc.returncode != 0:
            return ""
        base = (proc.stdout or "").strip()

        # Add a 1-sample dmon snapshot (shows %enc / %dec clearly).
        dmon_line = ""
        try:
            dmon = subprocess.run(
                ["nvidia-smi", "dmon", "-s", "u", "-c", "1"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if dmon.returncode == 0 and dmon.stdout:
                lines = [ln.strip() for ln in dmon.stdout.splitlines() if ln.strip() and not ln.strip().startswith("#")]
                # Keep the last 1-2 GPU lines if present.
                dmon_line = "dmon=" + " | ".join(lines[-2:])
        except Exception:
            dmon_line = ""

        return (base + ((" ; " + dmon_line) if dmon_line else "")).strip()
    except Exception:
        return ""


def _log_gpu(tag: str) -> None:
    snap = _nvidia_smi_snapshot()
    if snap:
        logger.info("GPU(%s): %s", tag, snap.replace("\n", " | "))


def _inject_hwaccel(cmd: List[str], accel: str) -> List[str]:
    """Insert hwaccel args before the first `-i` input. Supports nvdec, cuda, vulkan."""
    if accel not in {"nvdec", "cuda", "vulkan"}:
        return cmd
    try:
        i = cmd.index("-i")
    except ValueError:
        return cmd
    return cmd[:i] + ["-hwaccel", accel, "-hwaccel_device", "0"] + cmd[i:]


def _run_ffmpeg_hwaccel(cmd: List[str], timeout: int) -> subprocess.CompletedProcess:
    """Force 4090 GPU: -hwaccel cuda -hwaccel_device 0 -c:v h264_nvenc."""
    prefer = (os.environ.get("CLIP_HWACCEL", "cuda") or "").strip().lower()
    order = [x.strip() for x in prefer.split(",") if x.strip()] or ["cuda"]
    tried = set()
    for accel in order:
        if accel in tried or accel not in {"nvdec", "cuda", "vulkan"}:
            continue
        tried.add(accel)
        logger.info("Using GPU acceleration: %s", accel)
        _log_gpu(f"before_ffmpeg_{accel}")
        proc = _run_ffmpeg(_inject_hwaccel(cmd, accel), timeout=timeout)
        _log_gpu(f"after_ffmpeg_{accel}")
        if proc.returncode == 0:
            return proc
        logger.warning("ffmpeg hwaccel=%s failed (rc=%s), retrying", accel, proc.returncode)
    logger.info("Using GPU acceleration: disabled")
    return _run_ffmpeg(cmd, timeout=timeout)


def _is_html_slop(path: Path) -> bool:
    try:
        head = path.read_bytes()[:8192].lower()
        return (b"<html" in head) or (b"<!doctype html" in head)
    except Exception:
        return False


def _ffprobe_ok(path: Path) -> Tuple[bool, str]:
    try:
        proc = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "stream=codec_type,codec_name,width,height:format=duration,size",
                "-of",
                "json",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if proc.returncode != 0:
            return False, "ffprobe failed"
        payload = json.loads(proc.stdout or "{}")
        streams = payload.get("streams") or []
        fmt = payload.get("format") or {}
        has_video = any((s or {}).get("codec_type") == "video" for s in streams)
        duration = float(fmt.get("duration") or 0.0)
        size = int(float(fmt.get("size") or 0.0))
        if not has_video or duration <= 0 or size <= 0:
            return False, "invalid stream metadata"
        v = next((s for s in streams if (s or {}).get("codec_type") == "video"), {}) or {}
        wh = f"{v.get('width')}x{v.get('height')}"
        return True, f"ok duration={duration:.2f}s size={size} res={wh}"
    except Exception as e:
        return False, f"ffprobe exception: {e}"


def _resolve_local_source(video_id: str) -> Optional[Path]:
    project_root = Path("/home/ultron/protocol_pulse")
    manifest = project_root / "data" / "raw_footage_manifest.json"
    vid = (video_id or "").strip()
    if not vid:
        return None

    # If a direct path was stored, accept it.
    if vid.startswith("/"):
        p = Path(vid)
        return p if p.exists() else None

    # Use ingest manifest mapping where possible.
    if manifest.exists():
        try:
            payload = json.loads(manifest.read_text(encoding="utf-8"))
            for row in (payload.get("videos") or []):
                if str(row.get("video_id") or "") == vid:
                    p = Path(str(row.get("local_video_path") or ""))
                    return p if p.exists() else None
        except Exception:
            pass

    # Best-effort search: match by substring in filename.
    candidates = sorted((project_root / "data" / "raw_footage").glob(f"**/*{vid}*.mp4"))
    return candidates[-1] if candidates else None


def _safe_media_id(raw: str) -> str:
    """Convert arbitrary ids/paths into a filename-safe identifier."""
    s = (raw or "").strip()
    if not s:
        return "unknown"
    # If it's a path-like string, prefer the basename stem.
    if "/" in s or "\\" in s:
        try:
            s = Path(s).stem or s
        except Exception:
            pass
    s = re.sub(r"[^A-Za-z0-9_-]+", "_", s).strip("_")
    if not s:
        return "unknown"
    return s[:80]


def _video_id_from_url(url_or_id: str) -> str:
    u = (url_or_id or "").strip()
    m = re.search(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{6,})", u)
    return _safe_media_id(m.group(1) if m else u)


def _download_thumbnail(video_id: str, out_path: Path) -> Tuple[bool, str]:
    """Download a YouTube thumbnail to a local path (best-effort)."""
    vid = _video_id_from_url(video_id)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # Use existing YouTubeService helpers to keep URL logic centralized.
    try:
        from services.youtube_service import YouTubeService  # local import to avoid heavy deps at module import time
        urls = [
            YouTubeService.get_thumbnail(vid),
            YouTubeService.get_hq_thumbnail(vid),
            f"https://img.youtube.com/vi/{vid}/0.jpg",
        ]
    except Exception:
        urls = [
            f"https://img.youtube.com/vi/{vid}/maxresdefault.jpg",
            f"https://img.youtube.com/vi/{vid}/hqdefault.jpg",
            f"https://img.youtube.com/vi/{vid}/0.jpg",
        ]
    try:
        import requests
        for url in urls:
            try:
                r = requests.get(url, timeout=12)
                if not r.ok or not r.content:
                    continue
                out_path.write_bytes(r.content)
                if out_path.exists() and out_path.stat().st_size > 1024:
                    return True, url
            except Exception:
                continue
        return False, "thumbnail download failed"
    except Exception as e:
        return False, f"requests unavailable: {e}"


def _ff_escape_drawtext(s: str) -> str:
    # Escape for ffmpeg drawtext filter. Keep it conservative.
    return (s or "").replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def _audio_duration_seconds(path: Path) -> float:
    try:
        proc = subprocess.run(
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
            capture_output=True,
            text=True,
            timeout=15,
        )
        if proc.returncode != 0:
            return 0.0
        return float((proc.stdout or "").strip() or 0.0)
    except Exception:
        return 0.0


def generate_static_brief(
    video_id: str,
    *,
    channel_name: str = "Partner",
    job_id: Optional[int] = None,
) -> Dict:
    """When Whisper returns empty transcript: log warning, 30s thumbnail MP4 + red/black overlay + 'Protocol Pulse Insight'. DO NOT ABORT."""
    logger.warning("Empty transcript fallback: creating 30s thumbnail MP4 with Protocol Pulse Insight (video_id=%s job_id=%s)", video_id, job_id)
    narration_path = None
    try:
        from services.elevenlabs_service import ElevenLabsService
        svc = ElevenLabsService()
        script = (
            f"Protocol Pulse Insight. Featured from {channel_name or 'our partner'}. "
            "No speech detected; this is a static briefing."
        )
        out_dir = CLIPS_OUT_DIR
        out_dir.mkdir(parents=True, exist_ok=True)
        vid = _video_id_from_url(video_id)
        audio_path = out_dir / f"static_brief_{vid}_{job_id or 0}.mp3"
        res = svc.synthesize(text=script, out_path=audio_path, use_alignment=False)
        if res.ok and res.audio_path and Path(res.audio_path).exists():
            narration_path = res.audio_path
            logger.info("generate_static_brief: ElevenLabs narration saved to %s", narration_path)
    except Exception as e:
        logger.warning("generate_static_brief: ElevenLabs unavailable, using silent track: %s", e)
    return fallback_thumbnail_reel(
        video_id,
        narration_path=narration_path,
        channel_name=channel_name or "Partner",
        job_id=job_id,
        duration_seconds=30.0,
        draw_text="Protocol Pulse Insight",
    )


def fallback_clip(
    video_id: str,
    narration_path: Optional[str] = None,
    *,
    channel_name: str = "Partner",
) -> Dict:
    """Create a narrated thumbnail reel MP4 (30-60s) with brand overlay."""
    return fallback_thumbnail_reel(video_id, narration_path=narration_path, channel_name=channel_name)


def fallback_thumbnail_reel(
    video_id: str,
    narration_path: Optional[str] = None,
    *,
    channel_name: str = "Partner",
    job_id: Optional[int] = None,
    duration_seconds: Optional[float] = None,
    draw_text: Optional[str] = None,
) -> Dict:
    """Create a vertical MP4 using static thumbnail + narration (or silent). Red/black overlay.

    Empty-transcript fallback: pass duration_seconds=30, draw_text='Protocol Pulse Insight'.
    """
    t0 = time.time()
    out_dir = CLIPS_OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    os.makedirs(str(out_dir), exist_ok=True)
    vid = _video_id_from_url(video_id)
    thumb_path = out_dir / f"thumb_{vid}.jpg"
    out_mp4 = out_dir / (f"job_{int(job_id)}_fallback.mp4" if job_id is not None else f"fallback_{vid}.mp4")
    os.makedirs(os.path.dirname(str(out_mp4)), exist_ok=True)

    ok, src_url = _download_thumbnail(vid, thumb_path)
    if not ok:
        local_bg = PROJECT_ROOT / "static" / "img" / "terminal_bg.png"
        if local_bg.exists():
            thumb_path = local_bg
            src_url = "local:static/img/terminal_bg.png"
            logger.warning("thumbnail download failed for %s; using local background", vid)
        else:
            return {"ok": False, "error": "thumbnail download failed", "detail": src_url}

    audio_in = None
    if narration_path:
        p = Path(narration_path)
        if p.exists():
            audio_in = str(p)

    if not audio_in:
        audio_in = "anullsrc=channel_layout=stereo:sample_rate=48000"

    target_dur = duration_seconds if duration_seconds is not None else 45.0
    try:
        env_d = float((os.environ.get("CLIP_FALLBACK_DURATION") or "").strip() or 0.0)
        if env_d > 0 and duration_seconds is None:
            target_dur = min(60.0, max(30.0, env_d))
    except Exception:
        pass

    vf = _overlay_filters()
    featured = draw_text if draw_text else "Protocol Pulse Intelligence"
    vf += (
        ",drawtext=text='"
        + _ff_escape_drawtext(featured)
        + "':x=(w-text_w)/2:y=h*0.08:fontcolor=white:fontsize=52:"
        + "box=1:boxcolor=#0A0A0A@0.55:boxborderw=18"
    )

    cmd = [
        "ffmpeg",
        "-y",
        "-loop",
        "1",
        "-i",
        str(thumb_path),
    ]
    if audio_in.startswith("anullsrc="):
        cmd += ["-f", "lavfi", "-i", audio_in]
    else:
        cmd += ["-i", audio_in]
    cmd += [
        "-t",
        f"{target_dur:.3f}",
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
        # Keep consistent duration even when narration is short; pad audio as needed.
        "-af",
        "apad=pad_dur=60",
        "-movflags",
        "+faststart",
        str(out_mp4),
    ]
    _log_gpu("before_fallback")
    proc = _run_ffmpeg_hwaccel(cmd, timeout=240)
    if proc.returncode != 0:
        # CPU fallback
        cmd = [c for c in cmd if c not in {"h264_nvenc", "p4"}]
        # Replace codec args in-place (simple approach).
        cmd = [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-i",
            str(thumb_path),
        ] + (["-f", "lavfi", "-i", audio_in] if audio_in.startswith("anullsrc=") else ["-i", audio_in]) + [
            "-t",
            f"{target_dur:.3f}",
            "-vf",
            vf,
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-af",
            "apad=pad_dur=60",
            "-movflags",
            "+faststart",
            str(out_mp4),
        ]
        proc = _run_ffmpeg_hwaccel(cmd, timeout=360)
    _log_gpu("after_fallback")

    if proc.returncode != 0:
        try:
            if out_mp4.exists():
                out_mp4.unlink()
        except Exception:
            pass
        return {"ok": False, "error": "fallback ffmpeg failed", "stderr": (proc.stderr or "")[:200]}

    if not out_mp4.exists() or out_mp4.stat().st_size < 10 * 1024 or _is_html_slop(out_mp4):
        try:
            if out_mp4.exists():
                out_mp4.unlink()
        except Exception:
            pass
        return {"ok": False, "error": "fallback output invalid"}

    ok_probe, detail = _ffprobe_ok(out_mp4)
    if not ok_probe:
        try:
            out_mp4.unlink()
        except Exception:
            pass
        return {"ok": False, "error": "fallback ffprobe invalid", "detail": detail}

    elapsed_ms = int((time.time() - t0) * 1000)
    return {"ok": True, "output": str(out_mp4), "thumb_source": src_url, "elapsed_ms": elapsed_ms}


def _write_srt_from_segments(segments: List[dict], out_path: Path) -> None:
    def tc(seconds: float) -> str:
        ms = int(max(0.0, seconds) * 1000)
        h = ms // 3_600_000
        ms %= 3_600_000
        m = ms // 60_000
        ms %= 60_000
        s = ms // 1000
        ms = ms % 1000
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    rows = []
    for idx, seg in enumerate(segments, start=1):
        start = float(seg.get("start", 0.0) or 0.0)
        end = float(seg.get("end", 0.0) or 0.0)
        text = str(seg.get("text") or "").strip().replace("\n", " ")
        if not text or end <= start:
            continue
        rows.append(f"{idx}\n{tc(start)} --> {tc(end)}\n{text}\n")
    out_path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    # Caller validates at least one cue was written.


def _whisper_transcribe_to_srt(video_path: Path, srt_path: Path) -> Tuple[bool, str]:
    """Generate an SRT file using faster-whisper. Tries GPU then CPU."""
    try:
        from faster_whisper import WhisperModel
    except Exception as e:
        return False, f"faster-whisper missing: {e}"

    model_size = os.environ.get("CLIP_WHISPER_MODEL", "large-v3")
    gpu_idx = int(os.environ.get("CLIP_WHISPER_GPU", "0"))
    prefer_device = os.environ.get("CLIP_WHISPER_DEVICE", "cuda").strip().lower()
    try:
        model = None
        if prefer_device in {"cuda", "gpu"}:
            try:
                model = WhisperModel(model_size, device="cuda", device_index=gpu_idx, compute_type="float16")
            except Exception as gpu_exc:
                logger.warning("Whisper GPU init failed, falling back to CPU: %s", gpu_exc)
                model = None
        if model is None:
            model = WhisperModel(model_size, device="cpu", compute_type="int8")

        try:
            segs, _ = model.transcribe(str(video_path), beam_size=4, vad_filter=True)
        except Exception as runtime_exc:
            # CUDA runtime can fail during transcribe (missing libcublas, etc). Retry on CPU.
            if prefer_device in {"cuda", "gpu"}:
                logger.warning("Whisper GPU transcribe failed, retrying on CPU: %s", runtime_exc)
                model = WhisperModel(model_size, device="cpu", compute_type="int8")
                segs, _ = model.transcribe(str(video_path), beam_size=2, vad_filter=True)
            else:
                raise
        segments = []
        for seg in segs:
            txt = str(seg.text or "").strip()
            if not txt:
                continue
            segments.append({"start": float(seg.start), "end": float(seg.end), "text": txt})
        if not segments:
            return False, "no speech segments (empty transcript)"
        _write_srt_from_segments(segments, srt_path)
        if not srt_path.exists() or srt_path.stat().st_size < 10:
            return False, "srt empty"
        return True, "ok"
    except Exception as e:
        return False, f"whisper failed: {e}"


def _ff_escape_path(path: Path) -> str:
    return str(path).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def _overlay_filters() -> str:
    """Protocol Pulse hue: bottom dark gradient + red tint overlay."""
    # CPU-safe filter chain (works reliably on FFmpeg 4.4.x).
    # We still use NVENC for encode; hwaccel is attempted at input level.
    base = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,format=yuv420p,"
    return base + (
        "drawbox=x=0:y=0:w=iw:h=ih:color=#DC2626@0.06:t=fill,"
        "drawbox=x=0:y=1100:w=iw:h=120:color=#0A0A0A@0.10:t=fill,"
        "drawbox=x=0:y=1220:w=iw:h=120:color=#0A0A0A@0.16:t=fill,"
        "drawbox=x=0:y=1340:w=iw:h=120:color=#0A0A0A@0.22:t=fill,"
        "drawbox=x=0:y=1460:w=iw:h=120:color=#0A0A0A@0.30:t=fill,"
        "drawbox=x=0:y=1580:w=iw:h=120:color=#0A0A0A@0.40:t=fill,"
        "drawbox=x=0:y=1700:w=iw:h=120:color=#0A0A0A@0.55:t=fill,"
        "drawbox=x=0:y=1820:w=iw:h=120:color=#0A0A0A@0.70:t=fill"
    )


def _burn_captions_filter(srt_path: Path) -> str:
    # Crimson Pro is not installed on this machine by default; allow override via font file.
    # If user installs the font system-wide later, FontName will resolve.
    font_name = os.environ.get("CLIP_CAPTION_FONT", "Crimson Pro")
    # Libass style string. Keep conservative sizing for 1080x1920.
    style = (
        f"FontName={font_name},Fontsize=46,"
        "PrimaryColour=&H00FFFFFF,OutlineColour=&H00101010,"
        "BorderStyle=3,Outline=1,Shadow=0,Alignment=2,MarginV=120"
    )
    fontsdir = os.environ.get("CLIP_FONTS_DIR", "")
    fontsdir_part = f":fontsdir={_ff_escape_path(Path(fontsdir))}" if fontsdir else ""
    return f"subtitles='{_ff_escape_path(srt_path)}'{fontsdir_part}:force_style='{style}'"


def _run_ffmpeg(cmd: List[str], timeout: int) -> subprocess.CompletedProcess:
    # Optional lightweight GPU monitor while ffmpeg runs (captures NVENC %enc).
    monitor = None
    monitor_out = ""
    try:
        samples = int((os.environ.get("CLIP_GPU_DMON_SAMPLES") or "4").strip() or "4")
    except Exception:
        samples = 4
    try:
        if samples > 0 and (os.environ.get("CLIP_GPU_DMON", "1").strip() != "0"):
            monitor = subprocess.Popen(
                ["nvidia-smi", "dmon", "-s", "u", "-c", str(samples)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
    except Exception:
        monitor = None

    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

    if monitor is not None:
        try:
            monitor_out = (monitor.communicate(timeout=1)[0] or "").strip()
        except Exception:
            try:
                monitor.terminate()
            except Exception:
                pass
        if monitor_out:
            lines = [ln.strip() for ln in monitor_out.splitlines() if ln.strip() and not ln.strip().startswith("#")]
            # Keep last few lines (often includes %enc/%dec columns).
            tail = " | ".join(lines[-4:])
            logger.info("GPU(dmon during ffmpeg): %s", tail)

    return proc


def process_viral_job(
    job_id: int,
    video_id_override: Optional[str] = None,
    narration_path: Optional[str] = None,
    channel_name: Optional[str] = None,
) -> Dict:
    """Process ClipJob into vertical short clips with overlay + captions."""
    t0 = time.time()
    outputs: List[str] = []
    errors: List[str] = []
    any_speech = False

    out_dir = CLIPS_OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    os.makedirs(str(out_dir), exist_ok=True)

    with app.app_context():
        job = models.ClipJob.query.get(int(job_id))
        if not job:
            return {"ok": False, "error": "job not found"}
        try:
            stamps = json.loads(job.timestamps_json or "[]")
        except Exception:
            stamps = []
        video_id = (video_id_override or str(job.video_id or "")).strip()

        src = _resolve_local_source(video_id)
        if not src or not src.exists():
            logger.warning("missing source video for job=%s video_id=%s — using narrated thumbnail fallback", job_id, video_id)
            fb = fallback_thumbnail_reel(
                video_id,
                narration_path=(narration_path or os.environ.get("CLIP_FALLBACK_NARRATION_PATH")),
                channel_name=(channel_name or os.environ.get("CLIP_FEATURED_CHANNEL") or "Partner"),
                job_id=int(job_id),
            )
            job.status = "Completed" if fb.get("ok") else "Failed"
            db.session.commit()
            return {"ok": bool(fb.get("ok")), "job_id": int(job_id), "fallback": True, "video_id": video_id, **fb}

        job.status = "Processing"
        db.session.commit()

    _log_gpu("before_job")
    # Ensure data/clips/ exists (absolute path for 4090 Forge)
    os.makedirs(str(CLIPS_OUT_DIR), exist_ok=True)
    # Render outside the session to avoid holding locks while ffmpeg runs.
    for idx, st in enumerate(stamps, start=1):
        try:
            start = float(st.get("start", 0.0) or 0.0)
            end = float(st.get("end", 0.0) or 0.0)
            if end <= start:
                continue
            duration = max(1.0, end - start)

            raw_clip = out_dir / f"job_{job_id}_seg_{idx:02d}_raw.mp4"
            srt_path = out_dir / f"job_{job_id}_seg_{idx:02d}.srt"
            final_clip = out_dir / f"job_{job_id}_seg_{idx:02d}.mp4"

            # 1) Extract segment (fast seek).
            extract_cmd = [
                "ffmpeg",
                "-y",
                "-ss",
                str(max(0.0, start)),
                "-i",
                str(src),
                "-t",
                str(duration),
                "-c:v",
                "h264_nvenc",
                "-preset",
                "p4",
                "-c:a",
                "aac",
                str(raw_clip),
            ]
            proc = _run_ffmpeg_hwaccel(extract_cmd, timeout=240)
            if proc.returncode != 0:
                # CPU fallback
                extract_cmd = [
                    "ffmpeg",
                    "-y",
                    "-ss",
                    str(max(0.0, start)),
                    "-i",
                    str(src),
                    "-t",
                    str(duration),
                    "-c:v",
                    "libx264",
                    "-c:a",
                    "aac",
                    str(raw_clip),
                ]
                proc = _run_ffmpeg(extract_cmd, timeout=240)
            if proc.returncode != 0 or not raw_clip.exists() or raw_clip.stat().st_size == 0:
                errors.append(f"segment_extract_failed:{idx}")
                continue

            # 2) Whisper SRT.
            ok, detail = _whisper_transcribe_to_srt(raw_clip, srt_path)
            if not ok:
                # FALLBACK: empty transcript -> do NOT fail; trigger generate_static_brief (thumbnail + Red/Black + ElevenLabs)
                detail_lower = (detail or "").lower()
                if "empty" in detail_lower or "no speech" in detail_lower:
                    logger.warning("Whisper empty transcript for job=%s video_id=%s; triggering generate_static_brief", job_id, video_id)
                    with app.app_context():
                        job = models.ClipJob.query.get(int(job_id))
                        if job:
                            fb = generate_static_brief(
                                video_id,
                                narration_path=(narration_path or os.environ.get("CLIP_FALLBACK_NARRATION_PATH")),
                                channel_name=(channel_name or getattr(job, "channel_name", None) or os.environ.get("CLIP_FEATURED_CHANNEL") or "Partner"),
                                job_id=int(job_id),
                            )
                            job.status = "Completed" if fb.get("ok") else "Failed"
                            db.session.commit()
                            return {"ok": bool(fb.get("ok")), "job_id": int(job_id), "fallback": True, "video_id": video_id, **fb}
                # else: allow clip render without captions, log error
                logger.warning("SRT generation failed for job=%s idx=%s: %s", job_id, idx, detail)
                try:
                    if srt_path.exists():
                        srt_path.unlink()
                except Exception:
                    pass
                srt_path = None  # type: ignore
            else:
                any_speech = True

            # 3) Vertical + overlay + (optional) captions burn.
            vf = _overlay_filters()
            if srt_path is not None and Path(srt_path).exists():
                vf = vf + "," + _burn_captions_filter(Path(srt_path))

            render_cmd = [
                "ffmpeg",
                "-y",
                "-i",
                str(raw_clip),
                "-vf",
                vf,
                "-map",
                "0:v:0",
                "-map",
                "0:a?",
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
                str(final_clip),
            ]
            proc = _run_ffmpeg_hwaccel(render_cmd, timeout=360)
            if proc.returncode != 0:
                # CPU fallback
                render_cmd = [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(raw_clip),
                    "-vf",
                    vf,
                    "-map",
                    "0:v:0",
                    "-map",
                    "0:a?",
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    "-c:a",
                    "aac",
                    "-movflags",
                    "+faststart",
                    str(final_clip),
                ]
                proc = _run_ffmpeg(render_cmd, timeout=600)

            if proc.returncode != 0:
                # Remove partial output (often 0 bytes / missing moov atom).
                try:
                    if final_clip.exists():
                        final_clip.unlink()
                except Exception:
                    pass
                errors.append(f"render_failed:{idx}")
                continue

            # Quality gate: no empty/html slop + ffprobe valid.
            if not final_clip.exists() or final_clip.stat().st_size < 10 * 1024:
                try:
                    if final_clip.exists():
                        final_clip.unlink()
                except Exception:
                    pass
                errors.append(f"invalid_small_output:{idx}")
                continue
            if _is_html_slop(final_clip):
                try:
                    final_clip.unlink()
                except Exception:
                    pass
                errors.append(f"invalid_html_output:{idx}")
                continue
            ok_probe, probe_detail = _ffprobe_ok(final_clip)
            if not ok_probe:
                try:
                    final_clip.unlink()
                except Exception:
                    pass
                errors.append(f"invalid_ffprobe:{idx}:{probe_detail}")
                continue

            outputs.append(str(final_clip))
        except Exception as e:
            errors.append(f"exception:{idx}:{e}")

    elapsed_ms = int((time.time() - t0) * 1000)
    _log_gpu("after_job")

    # Empty transcript handling (Batch 3): use generate_static_brief (thumbnail + Red/Black + ElevenLabs). DO NOT ABORT.
    if stamps and not any_speech:
        logger.warning("NO SPEECH DETECTED – triggering generate_static_brief (job=%s video_id=%s)", job_id, video_id)
        fb = generate_static_brief(
            video_id,
            channel_name=(channel_name or os.environ.get("CLIP_FEATURED_CHANNEL") or "Partner"),
            job_id=int(job_id),
        )
        if fb.get("ok") and fb.get("output"):
            outputs = [str(fb["output"])]
            errors = []

    # If we produced nothing (bad timestamps / extraction failures), emit static brief fallback.
    if not outputs:
        logger.warning("NO CLIPS RENDERED – creating static brief fallback for job=%s video_id=%s", job_id, video_id)
        fb = generate_static_brief(
            video_id,
            channel_name=(channel_name or os.environ.get("CLIP_FEATURED_CHANNEL") or "Partner"),
            job_id=int(job_id),
        )
        if fb.get("ok") and fb.get("output"):
            outputs = [str(fb["output"])]
            errors = []

    with app.app_context():
        job = models.ClipJob.query.get(int(job_id))
        if job:
            # Batch 3 gate: do not leave jobs in Failed when a fallback MP4 exists.
            job.status = "Completed" if outputs else "Failed"
            db.session.commit()

    return {
        "ok": bool(outputs) and not errors,
        "job_id": int(job_id),
        "outputs": outputs,
        "errors": errors,
        "elapsed_ms": elapsed_ms,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Process ClipJob into clips")
    parser.add_argument("--job-id", type=int, required=False)
    parser.add_argument("--video-id", type=str, required=False)
    parser.add_argument("--narration-path", type=str, required=False)
    parser.add_argument("--channel-name", type=str, required=False)
    args = parser.parse_args()
    if args.video_id and not args.job_id:
        out = fallback_clip(
            args.video_id,
            narration_path=args.narration_path,
            channel_name=(args.channel_name or os.environ.get("CLIP_FEATURED_CHANNEL") or "Partner"),
        )
    else:
        out = process_viral_job(
            int(args.job_id),
            video_id_override=args.video_id,
            narration_path=args.narration_path,
            channel_name=(args.channel_name or None),
        )
    print(json.dumps(out, ensure_ascii=True, indent=2))

