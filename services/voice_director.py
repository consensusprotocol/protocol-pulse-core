from __future__ import annotations

import json
import logging
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import requests
from services import ollama_runtime

logger = logging.getLogger(__name__)


class VoiceDirectorService:
    def __init__(self) -> None:
        self.project_root = Path("/home/ultron/protocol_pulse")
        self.edit_metadata = self.project_root / "data" / "edit_metadata.json"
        self.brief_path = self.project_root / "data" / "daily_briefs.json"
        self.voice_dir = self.project_root / "data" / "voice"
        self.voice_dir.mkdir(parents=True, exist_ok=True)
        self.elevenlabs_key = (os.environ.get("ELEVENLABS_API_KEY") or "").strip()
        self.voice_id = (os.environ.get("ELEVENLABS_VOICE_ID") or "EXAVITQu4vr4xnSDxMaL").strip()

    def _latest_brief_text(self) -> str:
        if not self.brief_path.exists():
            return "bitcoin macro context is shifting; stay focused on sovereign signal."
        try:
            payload = json.loads(self.brief_path.read_text(encoding="utf-8"))
            briefs = payload.get("briefs") or []
            if not briefs:
                return "market context forming; sovereign signal remains in motion."
            b = briefs[-1]
            urgent = b.get("urgent_events") or []
            summary = str(b.get("summary") or "")
            return f"{summary}\nurgent: {'; '.join(urgent)}"
        except Exception:
            return "macro context evolving; use disciplined sovereign framing."

    def _build_script_blocks(self, clips: List[Dict]) -> Dict[str, str]:
        c1 = clips[0] if clips else {}
        c2 = clips[1] if len(clips) > 1 else c1
        brief = self._latest_brief_text()
        prompt = (
            "write five short narration blocks in lowercase, chill/world-class tone.\n"
            "format json object with keys: context, bridge, synthesis, outro.\n"
            "context introduces clip1, bridge connects clip1->clip2, synthesis summarizes edge, outro closes.\n"
            "each block <= 40 words.\n"
            f"brief={brief[:1000]}\n"
            f"clip1={json.dumps(c1, ensure_ascii=True)}\n"
            f"clip2={json.dumps(c2, ensure_ascii=True)}"
        )
        raw = ollama_runtime.generate(prompt, preferred_model="llama3.1", options={"temperature": 0.45, "num_predict": 240}, timeout=10)
        if raw:
            try:
                obj = json.loads(raw)
                if isinstance(obj, dict):
                    return {
                        "context": str(obj.get("context") or "").strip(),
                        "bridge": str(obj.get("bridge") or "").strip(),
                        "synthesis": str(obj.get("synthesis") or "").strip(),
                        "outro": str(obj.get("outro") or "").strip(),
                    }
            except Exception:
                pass
        return {
            "context": "context: the signal map tightened overnight. watch this first clip for the key setup.",
            "bridge": "bridge: that framing sets up the next angle where pressure meets opportunity.",
            "synthesis": "synthesis: together these clips point to sovereign positioning over short-term noise.",
            "outro": "outro: lock in the signal, ignore the fog, and move with conviction.",
        }

    def _synthesize(self, text: str, out_path: Path) -> str:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        if self.elevenlabs_key:
            try:
                url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}"
                payload = {
                    "text": text,
                    "model_id": "eleven_multilingual_v2",
                    "voice_settings": {"stability": 0.38, "similarity_boost": 0.73},
                }
                r = requests.post(
                    url,
                    headers={"xi-api-key": self.elevenlabs_key, "Content-Type": "application/json"},
                    json=payload,
                    timeout=50,
                )
                if r.ok and r.content:
                    out_path.write_bytes(r.content)
                    return str(out_path)
            except Exception:
                logger.exception("elevenlabs voice generation failed")

        # fallback silent narration block
        cmd = [
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", "anullsrc=r=44100:cl=stereo",
            "-t", "8", "-c:a", "aac", str(out_path),
        ]
        subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return str(out_path)

    def run(self) -> Dict:
        if not self.edit_metadata.exists():
            return {"ok": False, "error": "edit_metadata missing"}
        payload = json.loads(self.edit_metadata.read_text(encoding="utf-8"))
        clips = payload.get("clips") or []
        if not clips:
            return {"ok": False, "error": "no clips to narrate"}

        blocks = self._build_script_blocks(clips)
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        files = {}
        for key, text in blocks.items():
            files[key] = self._synthesize(text, self.voice_dir / f"{ts}_{key}.m4a")

        out = {
            "ts": datetime.utcnow().isoformat(),
            "script_blocks": blocks,
            "audio_blocks": files,
        }
        out_path = self.project_root / "data" / "voice_script.json"
        out_path.write_text(json.dumps(out, ensure_ascii=True, indent=2), encoding="utf-8")
        return {"ok": True, **out}


voice_director_service = VoiceDirectorService()

