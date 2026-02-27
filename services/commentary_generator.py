from __future__ import annotations

import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict

import requests

from app import db
import models
from services import ollama_runtime


class CommentaryGeneratorService:
    def __init__(self) -> None:
        self.audio_root = Path("/home/ultron/protocol_pulse/static/audio/commentary")
        self.audio_root.mkdir(parents=True, exist_ok=True)
        self.elevenlabs_key = (os.environ.get("ELEVENLABS_API_KEY") or "").strip()
        self.voice_id = (os.environ.get("ELEVENLABS_VOICE_ID") or "EXAVITQu4vr4xnSDxMaL").strip()

    def _draft_context_bridge(self, segment: models.PulseSegment, tone: str = "Sovereign, High-Intelligence, No-Nonsense.") -> str:
        pvideo = segment.partner_video
        title = (pvideo.title if pvideo else "partner update") or "partner update"
        label = (segment.label or "highlight")[:180]
        prompt = (
            "write exactly two sentences in lowercase.\n"
            f"tone: {tone}\n"
            "sentence1: set context before clip. sentence2: why this matters for active bitcoin operators.\n"
            f"video_title={title}\n"
            f"segment_label={label}"
        )
        txt = ollama_runtime.generate(prompt=prompt, preferred_model="llama3.1", options={"temperature": 0.4, "num_predict": 120}, timeout=8)
        if txt:
            sentences = [s.strip() for s in txt.replace("\n", " ").split(".") if s.strip()]
            if len(sentences) >= 2:
                return f"{sentences[0]}. {sentences[1]}."
            return txt.strip()[:280]
        return f"this cut from {title[:80]} is the setup. it matters because {label[:110]} tightens timing and conviction for operators."

    def _draft_post_clip(self, segment: models.PulseSegment, tone: str = "Sovereign, High-Intelligence, No-Nonsense.") -> str:
        pvideo = segment.partner_video
        title = (pvideo.title if pvideo else "partner update") or "partner update"
        label = (segment.label or "highlight")[:180]
        prompt = (
            "write exactly two sentences in lowercase.\n"
            f"tone: {tone}\n"
            "sentence1: react to the clip. sentence2: one extra sovereign insight.\n"
            f"video_title={title}\n"
            f"segment_label={label}"
        )
        txt = ollama_runtime.generate(prompt=prompt, preferred_model="llama3.1", options={"temperature": 0.35, "num_predict": 120}, timeout=8)
        if txt:
            sentences = [s.strip() for s in txt.replace("\n", " ").split(".") if s.strip()]
            if len(sentences) >= 2:
                return f"{sentences[0]}. {sentences[1]}."
            return txt.strip()[:280]
        return f"that clip validates the core read from {title[:80]}. sovereign edge comes from acting early while the crowd is still parsing the headline."

    def _synthesize_audio(self, text: str, out_file: Path) -> str:
        out_file.parent.mkdir(parents=True, exist_ok=True)
        if self.elevenlabs_key:
            try:
                r = requests.post(
                    f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}",
                    headers={"xi-api-key": self.elevenlabs_key, "Content-Type": "application/json"},
                    json={
                        "text": text,
                        "model_id": "eleven_multilingual_v2",
                        "voice_settings": {"stability": 0.4, "similarity_boost": 0.7},
                    },
                    timeout=45,
                )
                if r.ok and r.content:
                    out_file.write_bytes(r.content)
                    return str(out_file)
            except Exception:
                pass

        # silence fallback
        import subprocess
        subprocess.run(
            ["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-t", "7", "-c:a", "aac", str(out_file)],
            capture_output=True,
            text=True,
            timeout=60,
        )
        return str(out_file)

    def run(self, hours_back: int = 24, tone: str = "Sovereign, High-Intelligence, No-Nonsense.") -> Dict:
        cutoff = datetime.utcnow() - timedelta(hours=hours_back)
        segs = (
            models.PulseSegment.query.filter(models.PulseSegment.created_at >= cutoff)
            .order_by(models.PulseSegment.priority.desc(), models.PulseSegment.created_at.desc())
            .limit(120)
            .all()
        )
        updated = 0
        for seg in segs:
            pre_bridge = self._draft_context_bridge(seg, tone=tone)
            post_bridge = self._draft_post_clip(seg, tone=tone)
            pvideo = seg.partner_video
            title = (pvideo.title if pvideo else "segment") or "segment"
            fname_base = f"{seg.video_id}_{seg.start_sec}_{abs(hash(title)) % 10000}"
            pre_audio_path = self.audio_root / f"{fname_base}_pre.m4a"
            post_audio_path = self.audio_root / f"{fname_base}_post.m4a"
            pre_audio = self._synthesize_audio(pre_bridge, pre_audio_path)
            post_audio = self._synthesize_audio(post_bridge, post_audio_path)
            seg.commentary_audio = pre_audio
            seg.intelligence_brief = (
                f"{pre_bridge}\n\n"
                f"post_clip: {post_bridge}\n"
                f"post_audio: {post_audio}"
            )
            updated += 1
        db.session.commit()
        return {"ok": True, "segments_updated": updated}


commentary_generator_service = CommentaryGeneratorService()

