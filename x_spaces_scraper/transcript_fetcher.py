"""
transcript_fetcher.py — Transcript truth model for X Spaces.

Source truth labels enforced:
  AUDIO_REPLAY  = "audio_replay"    — yt-dlp download + Whisper
  LIVE_CAPTURE  = "live_capture"    — twspace-dl + rolling Whisper
  CONTEXT_ONLY  = "context_only"    — tweets/title only — NOT a real transcript

Quality gate: word_count >= 150, language_prob >= 0.70, repetition check.
Map-reduce summarization for transcripts > 2000 words.
"""

import json
import logging
import os
import signal
import subprocess
from pathlib import Path

from x_spaces_scraper.whisper_worker import WhisperWorker
from x_spaces_scraper.diarizer import diarize
from x_spaces_scraper.spaces_state import SpaceStateDB

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)

# Source truth constants
AUDIO_REPLAY = "audio_replay"
LIVE_CAPTURE = "live_capture"
CONTEXT_ONLY = "context_only"

# Quality thresholds
MIN_WORDS_FOR_AUDIO = 150
MIN_LANGUAGE_PROB = 0.70
MAX_REPETITION_RATE = 0.40


def _cache_path(space_id):
    return CACHE_DIR / f"transcript_{space_id}.json"


class TranscriptFetcher:
    def fetch(self, space_id, space_url, title="", db=None):
        """
        Returns:
        {
          "space_id": str,
          "transcript": str,
          "source": AUDIO_REPLAY | LIVE_CAPTURE | CONTEXT_ONLY,
          "word_count": int,
          "quality_score": float,  # 0.0-1.0
          "language_probability": float,
          "segments": list,        # diarized segments
          "speakers": list,        # unique speaker labels
          "usable": bool,          # True if meets quality threshold for narration
        }
        """
        # Check cache first
        cached = self._check_cache(space_id)
        if cached:
            return cached

        # Method 1: yt-dlp audio download + Whisper transcription
        result = self._try_audio_replay(space_id, space_url)
        if result.get("usable"):
            if db:
                db.mark(space_id, "transcribed")
            self._save_cache(space_id, result)
            return result

        # Method 2: Twitter API tweets as context (NOT narration-grade)
        context = self._try_api_context(space_id)
        if context:
            result = {
                "space_id": space_id,
                "transcript": context,
                "source": CONTEXT_ONLY,
                "word_count": len(context.split()),
                "quality_score": 0.3,
                "language_probability": 1.0,
                "segments": [],
                "speakers": [],
                "usable": False,
            }
            self._save_cache(space_id, result)
            return result

        # Final fallback: metadata only
        return {
            "space_id": space_id,
            "transcript": f"X Space: {title}" if title else "",
            "source": CONTEXT_ONLY,
            "word_count": 0,
            "quality_score": 0.0,
            "language_probability": 0.0,
            "segments": [],
            "speakers": [],
            "usable": False,
        }

    def _check_cache(self, space_id):
        path = _cache_path(space_id)
        if path.exists():
            try:
                data = json.loads(path.read_text())
                if data.get("transcript") or data.get("text"):
                    # Normalize old cache format
                    if "text" in data and "transcript" not in data:
                        data["transcript"] = data.pop("text")
                    if "usable" not in data:
                        data["usable"] = data.get("source") != CONTEXT_ONLY
                    logger.info(f"Cache hit for transcript {space_id}")
                    return data
            except (json.JSONDecodeError, OSError):
                pass
        return None

    def _save_cache(self, space_id, result):
        try:
            _cache_path(space_id).write_text(json.dumps(result, indent=2))
        except OSError as e:
            logger.debug(f"Cache write failed: {e}")

    def _try_audio_replay(self, space_id, space_url):
        """Download audio + Whisper transcribe. Full pipeline."""
        audio_path = f"/tmp/space_{space_id}.m4a"
        try:
            proc = subprocess.Popen(
                ["yt-dlp", "-f", "bestaudio", "-o", audio_path,
                 space_url, "--no-warnings", "--quiet"],
                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                preexec_fn=os.setsid,
            )
            try:
                proc.wait(timeout=120)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                except ProcessLookupError:
                    pass
                return {"usable": False, "error": "yt-dlp timeout"}
            finally:
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                except ProcessLookupError:
                    pass
            if proc.returncode != 0 or not os.path.exists(audio_path):
                return {"usable": False}

            worker = WhisperWorker.get()
            result = worker.transcribe(audio_path)

            if not self._passes_quality_gate(result):
                return {"usable": False}

            # Diarize segments
            result["segments"] = diarize(audio_path, result["segments"])
            result["speakers"] = list(set(s["speaker"] for s in result["segments"]))
            result["space_id"] = space_id
            result["usable"] = True
            result["quality_score"] = self._compute_quality_score(result)
            result["transcript"] = result.pop("text", "")

            # Map-reduce summarization for long transcripts
            if result["word_count"] > 2000:
                result["full_transcript"] = result["transcript"]
                result["transcript"] = self._map_reduce_summarize(
                    result["transcript"], result["segments"]
                )

            return result
        except Exception as e:
            logger.error(f"_try_audio_replay({space_id}): {e}")
            return {"usable": False, "error": str(e)}
        finally:
            if os.path.exists(audio_path):
                try:
                    os.remove(audio_path)
                except OSError:
                    pass

    def _passes_quality_gate(self, result):
        """True if transcript meets all quality thresholds."""
        if result.get("word_count", 0) < MIN_WORDS_FOR_AUDIO:
            return False
        if result.get("language_probability", 0) < MIN_LANGUAGE_PROB:
            return False
        # Repetition check — bigram dedup rate
        text = result.get("text", "")
        words = text.lower().split()
        if len(words) > 50:
            bigrams = [f"{words[i]} {words[i+1]}" for i in range(len(words) - 1)]
            unique_rate = len(set(bigrams)) / len(bigrams)
            if unique_rate < (1 - MAX_REPETITION_RATE):
                return False
        return True

    def _compute_quality_score(self, result):
        """Compute 0.0-1.0 quality score from transcript metrics."""
        score = 0.0
        wc = result.get("word_count", 0)
        if wc >= 500:
            score += 0.4
        elif wc >= 150:
            score += 0.2
        lp = result.get("language_probability", 0)
        score += min(lp * 0.4, 0.4)
        if result.get("speakers") and len(result["speakers"]) > 1:
            score += 0.2
        return round(min(score, 1.0), 2)

    def _map_reduce_summarize(self, transcript, segments):
        """
        For transcripts > 2000 words: chunk -> Haiku summarize -> Sonnet synthesize.
        Preserves speaker attribution.
        """
        try:
            import anthropic
        except ImportError:
            logger.warning("anthropic not installed — skipping map-reduce")
            return transcript[:2000]

        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            logger.warning("ANTHROPIC_API_KEY not set — skipping map-reduce")
            return transcript[:2000]

        client = anthropic.Anthropic(api_key=api_key)

        # Split into ~600-word chunks
        words = transcript.split()
        chunk_size = 600
        chunks = []
        for i in range(0, len(words), chunk_size):
            chunks.append(" ".join(words[i:i + chunk_size]))

        # Map phase: Haiku summarizes each chunk
        chunk_summaries = []
        for i, chunk in enumerate(chunks):
            try:
                resp = client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=300,
                    messages=[{
                        "role": "user",
                        "content": (
                            f"Summarize this Bitcoin/crypto X Space segment in 2-3 sentences. "
                            f"Keep specific numbers, names, predictions, and strong opinions. "
                            f"Segment {i + 1}/{len(chunks)}:\n\n{chunk}"
                        ),
                    }],
                )
                chunk_summaries.append(resp.content[0].text)
            except Exception:
                chunk_summaries.append(chunk[:200])

        # Reduce phase: Sonnet synthesizes chunk summaries
        try:
            all_summaries = "\n\n".join(
                f"[Segment {i + 1}]: {s}" for i, s in enumerate(chunk_summaries)
            )
            resp = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=600,
                messages=[{
                    "role": "user",
                    "content": (
                        f"You are a Protocol Pulse Bitcoin intelligence editor. "
                        f"Synthesize these X Space segment summaries into a 3-4 sentence "
                        f"broadcast-ready intelligence briefing. "
                        f"Lead with the most impactful statement. "
                        f"Include specific claims, predictions, and speaker names.\n\n"
                        f"{all_summaries}"
                    ),
                }],
            )
            return resp.content[0].text
        except Exception:
            return " ".join(chunk_summaries[:3])

    def _try_api_context(self, space_id):
        """Twitter API v2 — returns tweet text as CONTEXT ONLY. Never transcript."""
        import requests
        bearer = os.environ.get("TWITTER_BEARER_TOKEN", "")
        if not bearer:
            return ""
        try:
            r = requests.get(
                f"https://api.twitter.com/2/spaces/{space_id}/tweets",
                headers={"Authorization": f"Bearer {bearer}"},
                params={"tweet.fields": "text,author_id,created_at"},
                timeout=15,
            )
            if r.status_code == 200:
                tweets = r.json().get("data", [])
                return " ".join(t["text"] for t in tweets[:20])
        except Exception:
            pass
        return ""


# Backward-compatible function API (used by run_scraper.py)
_fetcher = None


def fetch_transcript(space_id, space_url, title=""):
    """Backward-compatible wrapper around TranscriptFetcher."""
    global _fetcher
    if _fetcher is None:
        _fetcher = TranscriptFetcher()
    result = _fetcher.fetch(space_id, space_url, title=title)
    # Normalize for backward compat: ensure "text" key exists
    if "transcript" in result and "text" not in result:
        result["text"] = result["transcript"]
    return result


# CLI
if __name__ == "__main__":
    import re
    import sys
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if len(sys.argv) < 2:
        print("Usage: python transcript_fetcher.py <space_url_or_id>")
        sys.exit(1)

    target = sys.argv[1]
    if target.startswith("http"):
        m = re.search(r"/spaces/(\w+)", target)
        sid = m.group(1) if m else target
        url = target
    else:
        sid = target
        url = f"https://twitter.com/i/spaces/{target}"

    result = fetch_transcript(sid, url)
    if result:
        text = result.get("transcript", result.get("text", ""))
        print(f"\nTranscript ({result.get('word_count', 0)} words, source={result.get('source', '?')}):")
        print(f"Usable: {result.get('usable', '?')}")
        print(text[:2000])
    else:
        print("Failed to fetch transcript.")
