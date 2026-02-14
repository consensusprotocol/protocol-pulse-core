from __future__ import annotations

import base64
import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import requests

logger = logging.getLogger(__name__)


@dataclass
class SynthesisResult:
    ok: bool
    audio_path: Optional[str] = None
    voice_id: Optional[str] = None
    model_id: Optional[str] = None
    used_alignment: bool = False
    error: Optional[str] = None


class ElevenLabsService:
    """Thin wrapper around ElevenLabs TTS.

    No new deps: uses requests. Never raises to callers.
    """

    def __init__(self) -> None:
        self.api_key = (os.environ.get("ELEVENLABS_API_KEY") or "").strip()
        self.voice_id = (os.environ.get("ELEVENLABS_VOICE_ID") or "").strip()
        self.voice_name = (os.environ.get("ELEVENLABS_VOICE_NAME") or "Professional Narrator").strip()
        # Requirement: ElevenLabs Flash v2.5 (make default, overridable)
        self.model_id = (os.environ.get("ELEVENLABS_MODEL_ID") or "eleven_flash_v2_5").strip()
        self.base_url = (os.environ.get("ELEVENLABS_BASE_URL") or "https://api.elevenlabs.io").rstrip("/")
        self._voice_cache: Dict[str, str] = {}

    def _headers(self) -> Dict[str, str]:
        return {"xi-api-key": self.api_key, "Content-Type": "application/json"}

    def _resolve_voice_id(self) -> Optional[str]:
        if self.voice_id:
            return self.voice_id
        if not self.api_key:
            return None
        if self.voice_name in self._voice_cache:
            return self._voice_cache[self.voice_name]
        try:
            r = requests.get(f"{self.base_url}/v1/voices", headers={"xi-api-key": self.api_key}, timeout=20)
            if not r.ok:
                return None
            payload = r.json() or {}
            voices = payload.get("voices") or []
            target = self.voice_name.lower()
            for v in voices:
                name = str((v or {}).get("name") or "").strip()
                vid = str((v or {}).get("voice_id") or "").strip()
                if vid and name.lower() == target:
                    self._voice_cache[self.voice_name] = vid
                    return vid
        except Exception as e:
            logger.warning("ElevenLabs voice list failed: %s", e)
        return None

    def synthesize(self, *, text: str, out_path: Path, use_alignment: bool = True) -> SynthesisResult:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.api_key:
            return SynthesisResult(ok=False, error="ELEVENLABS_API_KEY missing")
        voice_id = self._resolve_voice_id()
        if not voice_id:
            return SynthesisResult(ok=False, error="voice_id unresolved")

        clean_text = (text or "").strip()
        if not clean_text:
            return SynthesisResult(ok=False, error="empty text")

        # Forced alignment path (best-effort): with-timestamps endpoint returns alignment metadata.
        if use_alignment:
            try:
                url = f"{self.base_url}/v1/text-to-speech/{voice_id}/with-timestamps"
                payload = {
                    "text": clean_text,
                    "model_id": self.model_id,
                    "voice_settings": {"stability": 0.4, "similarity_boost": 0.7},
                }
                r = requests.post(url, headers=self._headers(), json=payload, timeout=60)
                if r.ok:
                    data = r.json() or {}
                    audio_b64 = data.get("audio_base64")
                    if audio_b64:
                        out_path.write_bytes(base64.b64decode(audio_b64))
                        if out_path.exists() and out_path.stat().st_size > 1024:
                            return SynthesisResult(
                                ok=True,
                                audio_path=str(out_path),
                                voice_id=voice_id,
                                model_id=self.model_id,
                                used_alignment=True,
                            )
            except Exception as e:
                logger.info("ElevenLabs alignment path unavailable, falling back: %s", e)

        # Standard TTS path.
        try:
            url = f"{self.base_url}/v1/text-to-speech/{voice_id}"
            payload = {
                "text": clean_text,
                "model_id": self.model_id,
                "voice_settings": {"stability": 0.4, "similarity_boost": 0.7},
            }
            r = requests.post(url, headers=self._headers(), json=payload, timeout=60)
            if not r.ok or not r.content:
                return SynthesisResult(ok=False, error=f"tts failed status={r.status_code}")
            out_path.write_bytes(r.content)
            if not out_path.exists() or out_path.stat().st_size <= 1024:
                return SynthesisResult(ok=False, error="tts output empty")
            return SynthesisResult(ok=True, audio_path=str(out_path), voice_id=voice_id, model_id=self.model_id)
        except Exception as e:
            return SynthesisResult(ok=False, error=str(e))

    # Back-compat for existing ContentEngine integrations.
    def generate_article_summary_audio(self, title: str, content: str, voice_type: str = "professional") -> Optional[str]:
        """Generate a short audio version for an article.

        Existing code expects this method to exist and return a filepath (or None).
        """
        try:
            if not self.api_key:
                return None
            safe_title = (title or "").strip()
            safe_content = (content or "").strip()
            if not safe_title and not safe_content:
                return None

            # Keep it short to avoid long synthesis + huge files.
            script = safe_title
            if safe_content:
                script = f"{safe_title}. {safe_content[:1200]}"

            out_dir = Path(os.environ.get("ELEVENLABS_AUDIO_DIR") or (Path.cwd() / "data" / "audio"))
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / "article_summary.mp3"

            res = self.synthesize(text=script, out_path=out_path, use_alignment=False)
            if not res.ok:
                logger.warning("ElevenLabs article audio failed (%s): %s", voice_type, res.error)
                return None
            return str(out_path)
        except Exception as e:
            logger.warning("ElevenLabs article audio exception: %s", e)
            return None

