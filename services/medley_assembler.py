from __future__ import annotations

import json
import logging
import os
import subprocess
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class MedleyAssemblerService:
    def __init__(self) -> None:
        self.project_root = Path("/home/ultron/protocol_pulse")
        self.edit_metadata = self.project_root / "data" / "edit_metadata.json"
        self.voice_script = self.project_root / "data" / "voice_script.json"
        self.out_file = self.project_root / "static" / "media" / "medley_daily_FINAL.mp4"
        self.work_dir = self.project_root / "logs" / "medley_assembler" / date.today().isoformat()
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.out_file.parent.mkdir(parents=True, exist_ok=True)
        self.bg_candidates = [
            self.project_root / "static" / "img" / "terminal_bg.png",
            self.project_root / "static" / "img" / "starfield_deep.png",
            self.project_root / "static" / "background.jpg",
        ]

    def _run(self, cmd: List[str], timeout: int = 600) -> subprocess.CompletedProcess:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

    def _ff_escape(self, value: str) -> str:
        return (value or "").replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'").replace("%", "\\%")

    def _is_remote_source(self, value: str) -> bool:
        check = (value or "").strip().lower()
        return check.startswith("http://") or check.startswith("https://")

    def _pick_background(self) -> Optional[Path]:
        for candidate in self.bg_candidates:
            if candidate.exists():
                return candidate
        return None

    def _asset_missing(self, kind: str, path: str) -> None:
        logger.error("ERROR: MISSING ASSET | kind=%s | path=%s", kind, path)

    def _preflight_check(self, clips: List[dict], voice: dict) -> Tuple[bool, List[Dict[str, str]]]:
        missing: List[Dict[str, str]] = []
        bg = self._pick_background()
        if bg is None:
            missing.append({"kind": "background", "path": str(self.project_root / "static" / "img")})
            self._asset_missing("background", str(self.project_root / "static" / "img"))

        for idx, c in enumerate(clips[:8], start=1):
            src = str(c.get("source_video") or "").strip()
            if not src:
                continue
            if self._is_remote_source(src):
                missing.append({"kind": f"clip_{idx:02d}", "path": src})
                self._asset_missing(f"clip_{idx:02d}", src)
                continue
            p = Path(src)
            if not p.exists():
                missing.append({"kind": f"clip_{idx:02d}", "path": src})
                self._asset_missing(f"clip_{idx:02d}", src)

        audio_blocks = voice.get("audio_blocks") or {}
        for label in ("context", "bridge", "synthesis", "outro"):
            src = str(audio_blocks.get(label) or "").strip()
            if not src:
                continue
            if self._is_remote_source(src):
                missing.append({"kind": f"audio_{label}", "path": src})
                self._asset_missing(f"audio_{label}", src)
                continue
            p = Path(src)
            if not p.exists():
                missing.append({"kind": f"audio_{label}", "path": src})
                self._asset_missing(f"audio_{label}", src)

        return (len(missing) == 0, missing)

    def _validate_video_output(self, video_path: Path) -> Tuple[bool, str]:
        if not video_path.exists():
            return False, "output missing"
        size = int(video_path.stat().st_size)
        if size < 10 * 1024:
            try:
                video_path.unlink()
            except Exception:
                pass
            return False, f"output too small ({size} bytes)"

        try:
            head = video_path.read_bytes()[:8192].lower()
            if b"<html" in head or b"<!doctype html" in head:
                try:
                    video_path.unlink()
                except Exception:
                    pass
                return False, "output contains html payload"
        except Exception as e:
            return False, f"header read failed: {e}"

        probe_cmd = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "stream=codec_type,codec_name:format=duration,size",
            "-of",
            "json",
            str(video_path),
        ]
        probe = self._run(probe_cmd, timeout=60)
        if probe.returncode != 0:
            return False, "ffprobe failed"
        try:
            payload = json.loads(probe.stdout or "{}")
            streams = payload.get("streams") or []
            has_video = any((s or {}).get("codec_type") == "video" for s in streams)
            duration = float((payload.get("format") or {}).get("duration") or 0.0)
            if not has_video or duration <= 0:
                return False, "ffprobe invalid stream metadata"
            logger.info(
                "VIDEO VALIDATION OK | file=%s | size=%d | duration=%.2fs",
                str(video_path),
                size,
                duration,
            )
            return True, "ok"
        except Exception as e:
            return False, f"ffprobe parse failed: {e}"

    def _clip(self, src: str, start: float, end: float, idx: int) -> str:
        out = self.work_dir / f"clip_{idx:02d}.mp4"
        duration = max(1.0, float(end) - float(start))
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(max(0.0, start)),
            "-i", str(src),
            "-t", str(duration),
            "-c:v", "h264_nvenc",
            "-gpu", str(os.environ.get("MEDLEY_RENDER_GPU", "1")),
            "-preset", "p4",
            "-c:a", "aac",
            str(out),
        ]
        proc = self._run(cmd, timeout=240)
        if proc.returncode != 0:
            # cpu fallback
            cmd = [
                "ffmpeg", "-y",
                "-ss", str(max(0.0, start)),
                "-i", str(src),
                "-t", str(duration),
                "-c:v", "libx264",
                "-c:a", "aac",
                str(out),
            ]
            self._run(cmd, timeout=240)
        return str(out)

    def _transition_slide(self, title: str, idx: int) -> str:
        out = self.work_dir / f"transition_{idx:02d}.mp4"
        bg = self._pick_background()
        if bg is None:
            self._asset_missing("background", "static/img")
            return str(out)
        # Glassmorphic-ish dark backdrop with red accent and JetBrains Mono text.
        vf = (
            "scale=1920:1080,"
            "drawbox=x=80:y=120:w=1760:h=840:color=black@0.55:t=fill,"
            "drawbox=x=80:y=120:w=1760:h=4:color=#DC2626@0.95:t=fill,"
            f"drawtext=font='JetBrains Mono':text='{self._ff_escape(title[:48])}':fontcolor=white:fontsize=44:x=(w-text_w)/2:y=(h/2)-20,"
            "drawtext=font='JetBrains Mono':text='protocol pulse medley':fontcolor=#DC2626:fontsize=28:x=(w-text_w)/2:y=(h/2)+44"
        )
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", str(bg),
            "-t", "3.5",
            "-vf", vf,
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            str(out),
        ]
        self._run(cmd, timeout=90)
        return str(out)

    def _audio_block_video(self, audio: str, label: str, idx: int) -> str:
        out = self.work_dir / f"voice_{idx:02d}_{label}.mp4"
        bg = self._pick_background()
        if bg is None:
            self._asset_missing("background", "static/img")
            return str(out)
        vf = (
            "scale=1920:1080,"
            "drawbox=x=120:y=180:w=1680:h=720:color=black@0.45:t=fill,"
            "drawbox=x=120:y=180:w=1680:h=4:color=#DC2626@0.95:t=fill,"
            f"drawtext=font='JetBrains Mono':text='{{{self._ff_escape(label)}}}':fontcolor=white:fontsize=40:x=(w-text_w)/2:y=(h/2)-10"
        )
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", str(bg),
            "-i", str(audio),
            "-vf", vf,
            "-shortest",
            "-c:v", "libx264", "-c:a", "aac",
            str(out),
        ]
        self._run(cmd, timeout=180)
        return str(out)

    def _normalize_audio(self, src: str, out: str) -> str:
        cmd = [
            "ffmpeg", "-y", "-i", src,
            "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
            "-c:v", "copy",
            "-c:a", "aac",
            out,
        ]
        proc = self._run(cmd, timeout=600)
        return out if proc.returncode == 0 else src

    def run(self) -> Dict:
        if not self.edit_metadata.exists():
            return {"ok": False, "error": "edit_metadata missing"}
        if not self.voice_script.exists():
            return {"ok": False, "error": "voice_script missing"}
        meta = json.loads(self.edit_metadata.read_text(encoding="utf-8"))
        voice = json.loads(self.voice_script.read_text(encoding="utf-8"))
        clips = list(meta.get("clips") or [])
        if not clips:
            return {"ok": False, "error": "no clips"}
        preflight_ok, missing_assets = self._preflight_check(clips, voice)
        if not preflight_ok:
            return {"ok": False, "error": "ERROR: MISSING ASSET", "missing_assets": missing_assets}

        timeline: List[str] = []
        # Context block
        ctx_audio = (voice.get("audio_blocks") or {}).get("context")
        if ctx_audio:
            timeline.append(self._audio_block_video(ctx_audio, "context", 0))

        for idx, c in enumerate(clips[:8], start=1):
            src = str(c.get("source_video") or "")
            if not src:
                continue
            clip_path = self._clip(src, float(c.get("start", 0)), float(c.get("end", 0)), idx)
            timeline.append(clip_path)
            if idx == 1 and (voice.get("audio_blocks") or {}).get("bridge"):
                timeline.append(self._audio_block_video(voice["audio_blocks"]["bridge"], "bridge", idx))
            elif idx == 2 and (voice.get("audio_blocks") or {}).get("synthesis"):
                timeline.append(self._audio_block_video(voice["audio_blocks"]["synthesis"], "synthesis", idx))
            if idx < min(len(clips), 8):
                timeline.append(self._transition_slide(str(c.get("topic") or c.get("video_title") or "transition"), idx))

        outro_audio = (voice.get("audio_blocks") or {}).get("outro")
        if outro_audio:
            timeline.append(self._audio_block_video(outro_audio, "outro", 99))

        # Append tag card.
        tag_candidates = [
            self.project_root / "static" / "assets" / "tag.mp4",
            self.project_root / "static" / "video" / "tag.mp4",
            self.project_root / "medley_engine" / "branding" / "tag.mp4",
        ]
        for p in tag_candidates:
            if p.exists():
                timeline.append(str(p))
                break

        concat_txt = self.work_dir / "concat.txt"
        concat_txt.write_text("".join([f"file '{p}'\n" for p in timeline]), encoding="utf-8")
        tmp_out = self.work_dir / "medley_daily_tmp.mp4"
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", str(concat_txt),
            "-c:v", "h264_nvenc",
            "-gpu", str(os.environ.get("MEDLEY_RENDER_GPU", "1")),
            "-preset", "p4",
            "-c:a", "aac",
            str(tmp_out),
        ]
        proc = self._run(cmd, timeout=1800)
        if proc.returncode != 0:
            cmd = [
                "ffmpeg", "-y",
                "-f", "concat", "-safe", "0",
                "-i", str(concat_txt),
                "-c:v", "libx264",
                "-c:a", "aac",
                str(tmp_out),
            ]
            self._run(cmd, timeout=1800)

        final = self._normalize_audio(str(tmp_out), str(self.out_file))
        valid, validation_msg = self._validate_video_output(Path(final))
        report = {
            "ok": bool(valid),
            "output": final,
            "timeline_count": len(timeline),
            "ts": datetime.utcnow().isoformat(),
            "timeline": timeline,
            "validation": validation_msg,
        }
        if not valid:
            logger.error("MEDLEY ASSEMBLY FAILED VALIDATION | output=%s | reason=%s", final, validation_msg)
        (self.work_dir / "report.json").write_text(json.dumps(report, ensure_ascii=True, indent=2), encoding="utf-8")
        return report


medley_assembler_service = MedleyAssemblerService()

