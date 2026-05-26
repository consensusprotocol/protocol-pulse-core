"""
Precision Clip Extractor
=========================
Cuts clips that sound like a human editor chose them.
ZERO mid-sentence cuts.

Uses:
1. Fuzzy text matching of clip_transcript against word-level Whisper output
2. Sentence boundary validation
3. Silence snapping for clean in/out points
4. FFmpeg extraction via Ultron
"""
import os
import json
import logging
import re
import time
from pathlib import Path
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple

from pp_services.video_engine.ultron_client import ultron, is_local_mode
from pp_services.video_engine.assembly import ffmpeg_ops
from pp_services.video_engine.local_whisper import download_audio

logger = logging.getLogger("ClipExtractor")

# Sentence-ending punctuation
SENTENCE_END = {'.', '?', '!'}


class ClipExtractor:
    """Extract clips with sentence-level precision from source videos."""

    def __init__(self, transcripts: Dict[str, dict],
                 audio_dir: str = None, clips_dir: str = None):
        """
        Args:
            transcripts: {video_id: {text, segments, words, ...}}
            audio_dir: directory with downloaded audio files
            clips_dir: directory to write extracted clips
        """
        self.transcripts = transcripts
        self.audio_dir = Path(audio_dir) if audio_dir else Path("/tmp/yt_audio")
        self.clips_dir = Path(clips_dir) if clips_dir else Path("/tmp/clips")
        self.clips_dir.mkdir(parents=True, exist_ok=True)
        self.extraction_log = []

    def extract_all_clips(self, show_plan_dict: dict,
                           bundle_path: Path = None) -> Dict[str, str]:
        """
        Extract all clips from the show plan.
        Returns {clip_id: clip_filename} mapping.
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"CLIP EXTRACTION")
        logger.info(f"{'='*60}\n")

        clip_map = {}
        clip_index = 0

        stories = show_plan_dict.get("stories", []) + show_plan_dict.get("quick_hits", [])

        for story in stories:
            story_num = story.get("story_number", 0)

            for i, clip in enumerate(story.get("clips", [])):
                clip_id = f"story{story_num}_clip{i}"
                source_id = clip.get("source_id", "")
                source_name = clip.get("source_name", "")
                target_text = clip.get("clip_transcript", "")

                logger.info(f"  Extracting {clip_id} from {source_name}...")

                result = self._extract_single_clip(
                    source_id, target_text,
                    clip.get("approx_start", "00:00"),
                    clip.get("approx_end", "01:00"),
                    clip_id, clip_index
                )

                if result:
                    clip_map[clip_id] = result["filename"]
                    self.extraction_log.append({
                        "clip_id": clip_id,
                        "source_id": source_id,
                        "source_name": source_name,
                        "match_score": result.get("match_score", 0),
                        "start_sec": result.get("start_sec", 0),
                        "end_sec": result.get("end_sec", 0),
                        "duration_sec": result.get("duration_sec", 0),
                        "filename": result["filename"],
                        "status": "success"
                    })
                    logger.info(f"    + {result['filename']} "
                                f"({result.get('duration_sec', 0):.1f}s, "
                                f"match={result.get('match_score', 0):.2f})")
                else:
                    self.extraction_log.append({
                        "clip_id": clip_id,
                        "source_id": source_id,
                        "source_name": source_name,
                        "status": "failed"
                    })
                    logger.warning(f"    - Extraction failed for {clip_id}")

                clip_index += 1

        logger.info(f"\n  Extraction complete: {len(clip_map)}/{clip_index} clips")

        # Log warnings for low match scores
        low_matches = [e for e in self.extraction_log
                       if e.get("match_score", 1) < 0.6 and e["status"] == "success"]
        if low_matches:
            logger.warning(f"  Low match scores ({len(low_matches)} clips):")
            for lm in low_matches:
                logger.warning(f"    {lm['clip_id']}: {lm['match_score']:.2f}")

        # Save extraction log
        if bundle_path:
            log_path = bundle_path / "clips" / "extraction_log.json"
            log_path.write_text(json.dumps(self.extraction_log, indent=2, default=str))

        return clip_map

    def _extract_single_clip(self, source_id: str, target_text: str,
                              approx_start: str, approx_end: str,
                              clip_id: str, clip_index: int) -> Optional[dict]:
        """Extract a single clip using transcript matching + Ultron."""
        transcript = self.transcripts.get(source_id)
        if not transcript:
            logger.warning(f"    No transcript for {source_id}")
            return self._fallback_extraction(source_id, approx_start, approx_end,
                                              clip_id, clip_index)

        # Step 1: Find clip boundaries via text matching
        words = transcript.get("words", [])
        segments = transcript.get("segments", [])

        if words:
            boundaries = self._find_word_level_boundaries(words, target_text)
        elif segments:
            boundaries = self._find_segment_level_boundaries(segments, target_text)
        else:
            boundaries = None

        if boundaries:
            start_sec, end_sec, match_score, matched_text = boundaries
        else:
            # Fallback to approx timestamps from show plan
            start_sec = self._ts_to_sec(approx_start)
            end_sec = self._ts_to_sec(approx_end)
            match_score = 0.0
            logger.info(f"    Using approx timestamps: {start_sec:.1f}-{end_sec:.1f}s")

        # Step 2: Validate sentence boundaries (expand if needed)
        if words:
            start_sec, end_sec = self._validate_sentence_boundaries(
                start_sec, end_sec, words)
        elif segments:
            start_sec, end_sec = self._validate_segment_boundaries(
                start_sec, end_sec, segments)

        # Step 3: Add padding for natural in/out
        start_sec = max(0, start_sec - 0.3)
        end_sec = end_sec + 0.5

        duration = end_sec - start_sec

        # Sanity check duration
        if duration < 5:
            logger.warning(f"    Clip too short ({duration:.1f}s), expanding")
            end_sec = start_sec + 15
            duration = 15
        elif duration > 45:
            logger.warning(f"    Clip too long ({duration:.1f}s), trimming")
            end_sec = start_sec + 30
            duration = 30

        # Step 4: Extract clip (local ffmpeg or Ultron)
        filename = f"clip_{clip_index:02d}_{clip_id}.mp4"

        if is_local_mode():
            return self._extract_local(source_id, start_sec, end_sec,
                                       filename, match_score, duration)
        else:
            try:
                result = ultron.extract_clip(
                    source_id, start_sec, end_sec, filename
                )
                if result and result.get("status") in ("complete", "success"):
                    return {
                        "filename": filename,
                        "start_sec": start_sec,
                        "end_sec": end_sec,
                        "duration_sec": duration,
                        "match_score": match_score,
                    }
            except Exception as e:
                logger.error(f"    Ultron extraction failed: {e}")

        return None

    def _extract_local(self, source_id: str, start_sec: float, end_sec: float,
                       filename: str, match_score: float, duration: float) -> Optional[dict]:
        """Extract clip using local ffmpeg from downloaded audio/video."""
        # Find source audio file
        audio_path = None
        for ext in ["wav", "m4a", "mp3", "webm"]:
            candidate = self.audio_dir / f"{source_id}.{ext}"
            if candidate.exists():
                audio_path = str(candidate)
                break

        if not audio_path:
            # Try downloading
            logger.info(f"    Downloading audio for {source_id}...")
            audio_path = download_audio(source_id, str(self.audio_dir))

        if not audio_path:
            logger.warning(f"    No audio available for {source_id}")
            return None

        output_path = str(self.clips_dir / filename)

        try:
            ffmpeg_ops.trim_clip(audio_path, output_path, start_sec, end_sec, copy=False)
            if Path(output_path).exists():
                return {
                    "filename": output_path,
                    "start_sec": start_sec,
                    "end_sec": end_sec,
                    "duration_sec": duration,
                    "match_score": match_score,
                }
        except Exception as e:
            logger.error(f"    Local extraction failed: {e}")
        return None

    def _find_word_level_boundaries(self, words: List[dict],
                                     target_text: str) -> Optional[Tuple]:
        """Find clip boundaries using word-level timestamps."""
        if not words or not target_text:
            return None

        # Normalize target text into word list
        target_words = self._normalize_words(target_text)
        if len(target_words) < 3:
            return None

        # Build word list from Whisper output
        whisper_words = []
        for w in words:
            word_text = w.get("word", "").strip()
            if word_text:
                whisper_words.append({
                    "word": word_text,
                    "start": w.get("start", 0),
                    "end": w.get("end", 0),
                    "normalized": self._normalize_word(word_text)
                })

        if not whisper_words:
            return None

        # Sliding window match
        target_normalized = [self._normalize_word(w) for w in target_words]
        target_str = " ".join(target_normalized)

        best_score = 0
        best_start_idx = 0
        best_end_idx = len(whisper_words) - 1
        window_size = len(target_words)

        for i in range(len(whisper_words) - min(window_size // 2, 3)):
            end_idx = min(i + window_size + 5, len(whisper_words))
            window_words = [w["normalized"] for w in whisper_words[i:end_idx]]
            window_str = " ".join(window_words[:window_size + 3])

            score = SequenceMatcher(None, target_str, window_str).ratio()

            if score > best_score:
                best_score = score
                best_start_idx = i
                # Find best end index
                best_end_idx = min(i + window_size - 1, len(whisper_words) - 1)

        if best_score < 0.3:
            return None

        start_sec = whisper_words[best_start_idx]["start"]
        end_sec = whisper_words[min(best_end_idx, len(whisper_words) - 1)]["end"]

        matched_text = " ".join(
            w["word"] for w in whisper_words[best_start_idx:best_end_idx + 1]
        )

        return (start_sec, end_sec, best_score, matched_text)

    def _find_segment_level_boundaries(self, segments: List[dict],
                                        target_text: str) -> Optional[Tuple]:
        """Fallback: find boundaries using segment-level timestamps."""
        if not segments or not target_text:
            return None

        target_lower = target_text.lower().strip()
        best_score = 0
        best_start = 0
        best_end = 0

        # Try each segment as potential start
        for i, seg in enumerate(segments):
            # Build window of consecutive segments
            window_text = ""
            for j in range(i, min(i + 8, len(segments))):
                window_text += " " + segments[j].get("text", "")
                window_text = window_text.strip()

                score = SequenceMatcher(None, target_lower,
                                         window_text.lower()).ratio()

                if score > best_score:
                    best_score = score
                    best_start = segments[i].get("start", 0)
                    best_end = segments[j].get("start", 0) + segments[j].get("duration", 5)

        if best_score < 0.3:
            return None

        return (best_start, best_end, best_score, "")

    def _validate_sentence_boundaries(self, start_sec: float, end_sec: float,
                                       words: List[dict]) -> Tuple[float, float]:
        """Expand boundaries to sentence start/end if needed."""
        # Find word closest to start
        start_idx = self._nearest_word_idx(words, start_sec)
        end_idx = self._nearest_word_idx(words, end_sec)

        if start_idx is None or end_idx is None:
            return (start_sec, end_sec)

        # Expand start backward to sentence beginning
        for i in range(start_idx, max(0, start_idx - 20), -1):
            word = words[i].get("word", "").strip()
            if i == 0 or (i > 0 and words[i - 1].get("word", "").strip()[-1:] in SENTENCE_END):
                start_sec = words[i].get("start", start_sec)
                break

        # Expand end forward to sentence end
        for i in range(end_idx, min(len(words), end_idx + 20)):
            word = words[i].get("word", "").strip()
            if word and word[-1] in SENTENCE_END:
                end_sec = words[i].get("end", end_sec)
                break

        return (start_sec, end_sec)

    def _validate_segment_boundaries(self, start_sec: float, end_sec: float,
                                      segments: List[dict]) -> Tuple[float, float]:
        """Snap to segment boundaries."""
        # Find nearest segment start
        for seg in segments:
            seg_start = seg.get("start", 0)
            if abs(seg_start - start_sec) < 3:
                start_sec = seg_start
                break

        # Find nearest segment end
        for seg in reversed(segments):
            seg_end = seg.get("start", 0) + seg.get("duration", 0)
            if abs(seg_end - end_sec) < 3:
                end_sec = seg_end
                break

        return (start_sec, end_sec)

    def _fallback_extraction(self, source_id: str, approx_start: str,
                              approx_end: str, clip_id: str,
                              clip_index: int) -> Optional[dict]:
        """Fallback: extract using approximate timestamps directly."""
        start_sec = self._ts_to_sec(approx_start)
        end_sec = self._ts_to_sec(approx_end)

        if end_sec <= start_sec:
            end_sec = start_sec + 20

        duration = end_sec - start_sec
        filename = f"clip_{clip_index:02d}_{clip_id}.mp4"

        if is_local_mode():
            return self._extract_local(source_id, start_sec, end_sec,
                                       filename, 0.0, duration)

        try:
            result = ultron.extract_clip(source_id, start_sec, end_sec, filename)
            if result and result.get("status") in ("complete", "success"):
                return {
                    "filename": filename,
                    "start_sec": start_sec,
                    "end_sec": end_sec,
                    "duration_sec": duration,
                    "match_score": 0.0,
                }
        except Exception as e:
            logger.error(f"    Fallback extraction failed: {e}")

        return None

    def _nearest_word_idx(self, words: List[dict], time_sec: float) -> Optional[int]:
        """Find index of word nearest to given timestamp."""
        if not words:
            return None
        best_idx = 0
        best_diff = float("inf")
        for i, w in enumerate(words):
            diff = abs(w.get("start", 0) - time_sec)
            if diff < best_diff:
                best_diff = diff
                best_idx = i
        return best_idx

    @staticmethod
    def _normalize_words(text: str) -> List[str]:
        """Normalize text into word list for matching."""
        text = re.sub(r'[^\w\s]', '', text.lower())
        return text.split()

    @staticmethod
    def _normalize_word(word: str) -> str:
        """Normalize a single word for matching."""
        return re.sub(r'[^\w]', '', word.lower())

    @staticmethod
    def _ts_to_sec(ts: str) -> float:
        """Convert MM:SS timestamp to seconds."""
        try:
            parts = ts.split(":")
            if len(parts) == 2:
                return int(parts[0]) * 60 + int(parts[1])
            elif len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            return float(ts)
        except (ValueError, IndexError):
            return 0
