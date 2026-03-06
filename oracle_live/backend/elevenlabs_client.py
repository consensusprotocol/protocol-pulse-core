import base64, time
from typing import Any, Dict, Tuple
import httpx
from config import settings

class ElevenLabsClient:
    def __init__(self):
        self._base = "https://api.elevenlabs.io/v1"
        self._headers = {
            "xi-api-key": settings.elevenlabs_api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        self._timeout = settings.request_timeout_sec

    async def text_to_speech_with_timestamps(self, text: str, voice_id: str = None) -> Tuple[Dict[str, Any], float]:
        voice = voice_id or settings.elevenlabs_voice_id
        url = f"{self._base}/text-to-speech/{voice}/with-timestamps"
        payload = {
            "text": text[:settings.max_text_len],
            "model_id": settings.elevenlabs_model_id,
            "voice_settings": {
                "stability": 0.55, "similarity_boost": 0.85,
                "style": 0.45, "use_speaker_boost": True,
            },
        }
        t0 = time.perf_counter()
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(url, headers=self._headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
        return data, time.perf_counter() - t0

    @staticmethod
    def estimate_duration_from_alignment(alignment: dict) -> float:
        ends = alignment.get("character_end_times_seconds", [])
        return float(ends[-1]) if ends else 0.0

    @staticmethod
    def b64_audio_size_bytes(audio_b64: str) -> int:
        try: return len(base64.b64decode(audio_b64))
        except: return 0
