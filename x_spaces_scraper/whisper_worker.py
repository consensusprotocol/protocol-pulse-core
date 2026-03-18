"""
whisper_worker.py — Singleton GPU Whisper worker.

Loads model ONCE, keeps alive across calls. Never instantiate inside fetch functions.
Call WhisperWorker.get() always.
"""

import logging
import threading

logger = logging.getLogger(__name__)

_init_lock = threading.Lock()


class WhisperWorker:
    _instance = None

    @classmethod
    def get(cls):
        if cls._instance is None:
            with _init_lock:
                if cls._instance is None:  # double-checked locking
                    cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.model = None
        self.model_name = None
        self._load_model()

    def _load_model(self):
        try:
            from faster_whisper import WhisperModel

            for model_name in ["distil-large-v3", "small.en", "base.en", "base"]:
                try:
                    self.model = WhisperModel(
                        model_name,
                        device="cuda",
                        compute_type="float16",
                        num_workers=1,
                        cpu_threads=4,
                    )
                    self.model_name = model_name
                    logger.info(f"WhisperWorker loaded model: {model_name}")
                    break
                except Exception as e:
                    logger.debug(f"WhisperWorker: {model_name} unavailable: {e}")
                    continue
        except ImportError:
            logger.warning("faster_whisper not installed — WhisperWorker unavailable")
            self.model = None
            self.model_name = None

    def transcribe(self, audio_path, language="en"):
        """
        Transcribe audio file. Returns:
        {
          "text": str,
          "segments": [{"start": float, "end": float, "text": str, "speaker": str}],
          "language": str,
          "language_probability": float,
          "word_count": int,
          "source": "audio_replay"
        }
        """
        if not self.model:
            return {
                "text": "", "segments": [], "language": "en",
                "language_probability": 0.0, "word_count": 0, "source": "unavailable",
            }

        try:
            segments_iter, info = self.model.transcribe(
                audio_path,
                beam_size=5,
                language=language,
                vad_filter=True,
                vad_parameters={"min_silence_duration_ms": 500},
                word_timestamps=False,
            )
            segments = []
            full_text_parts = []
            for seg in segments_iter:
                segments.append({
                    "start": round(seg.start, 2),
                    "end": round(seg.end, 2),
                    "text": seg.text.strip(),
                    "speaker": "unknown",
                })
                full_text_parts.append(seg.text.strip())

            full_text = " ".join(full_text_parts)
            return {
                "text": full_text,
                "segments": segments,
                "language": info.language,
                "language_probability": round(info.language_probability, 3),
                "word_count": len(full_text.split()),
                "source": "audio_replay",
            }
        except Exception as e:
            logger.error(f"WhisperWorker.transcribe error: {e}")
            return {
                "text": "", "segments": [], "language": "en",
                "language_probability": 0.0, "word_count": 0,
                "source": "error", "error": str(e),
            }

    def transcribe_live_chunk(self, audio_chunk_path, chunk_index, overlap_seconds=2.0):
        """30-second rolling window transcription for live Spaces."""
        result = self.transcribe(audio_chunk_path)
        result["source"] = "live_capture"
        result["chunk_index"] = chunk_index
        return result
