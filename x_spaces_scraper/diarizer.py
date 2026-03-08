"""
diarizer.py — Speaker diarization for X Spaces transcripts.

Waterfall:
  1. pyannote-audio (if installed + HF token available)
  2. Energy-based heuristic (silence gaps = speaker change)
  3. All segments labeled "HOST" (graceful fallback)
"""

import logging

logger = logging.getLogger(__name__)


def diarize(audio_path, segments, num_speakers=4):
    """
    Assign speaker labels to Whisper segments.
    Returns segments with "speaker" field updated:
      "HOST" for the primary speaker (most speaking time)
      "GUEST_1", "GUEST_2" etc for others
      "UNKNOWN" if diarization fails
    """
    if not segments:
        return segments

    # Method 1: pyannote
    try:
        import os
        hf_token = os.environ.get("HF_TOKEN", "")
        if hf_token:
            from pyannote.audio import Pipeline
            pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                use_auth_token=hf_token,
            )
            diarization = pipeline(audio_path, num_speakers=num_speakers)
            for seg in segments:
                mid = (seg["start"] + seg["end"]) / 2
                for turn, _, label in diarization.itertracks(yield_label=True):
                    if turn.start <= mid <= turn.end:
                        seg["speaker"] = _normalize_label(label)
                        break
            logger.info("Diarization: pyannote success")
            return segments
    except Exception as e:
        logger.debug(f"pyannote diarization failed: {e}")

    # Method 2: Energy-based heuristic
    try:
        speaker_idx = 0
        prev_end = 0.0
        label_map = {}
        for seg in segments:
            if seg["start"] - prev_end > 1.5:
                speaker_idx = (speaker_idx + 1) % num_speakers
            label = f"SPEAKER_{speaker_idx}"
            seg["speaker"] = label
            label_map[label] = label_map.get(label, 0) + len(seg["text"].split())
            prev_end = seg["end"]

        # Rename most-speaking speaker to HOST
        if label_map:
            host_label = max(label_map, key=label_map.get)
            for seg in segments:
                if seg["speaker"] == host_label:
                    seg["speaker"] = "HOST"
                elif seg["speaker"].startswith("SPEAKER_"):
                    n = seg["speaker"].split("_")[1]
                    seg["speaker"] = f"GUEST_{n}"
        logger.info("Diarization: energy-based heuristic applied")
        return segments
    except Exception as e:
        logger.debug(f"Energy-based diarization failed: {e}")

    # Fallback: all HOST
    for seg in segments:
        seg["speaker"] = "HOST"
    logger.info("Diarization: fallback — all segments labeled HOST")
    return segments


def _normalize_label(raw_label):
    mapping = {
        "SPEAKER_00": "HOST",
        "SPEAKER_01": "GUEST_1",
        "SPEAKER_02": "GUEST_2",
        "SPEAKER_03": "GUEST_3",
    }
    return mapping.get(raw_label, raw_label)
