"""Local LLM inference via Ollama — replaces paid API calls for:
1. Transcript sentiment extraction (was Claude Haiku)
2. Script quality grading (was Claude API)
3. Clip visual quality scoring (multimodal — future)
"""

import requests
import json
import logging
import time

log = logging.getLogger("local_llm")

OLLAMA_URL = "http://localhost:11434"
DEFAULT_MODEL = "gemma3:27b"

# ── Core API ──────────────────────────────────────────────────────────────────


def _resolve_model():
    """Return best available Gemma model, or None."""
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        models = [m["name"] for m in r.json().get("models", [])]
        # Prefer gemma4, fall back to gemma3
        for candidate in ["gemma4:27b", "gemma3:27b"]:
            if candidate in models:
                return candidate
        # Partial match
        for m in models:
            if "gemma" in m:
                return m
    except Exception:
        pass
    return None


def _ollama_generate(prompt, model=None, system=None, temperature=0.3, max_tokens=2000, timeout=300):
    """Call Ollama API for text generation."""
    model = model or _resolve_model() or DEFAULT_MODEL
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
            "num_ctx": 8192,  # 8K context is plenty for transcripts; avoids bloated KV cache
        },
    }
    if system:
        payload["system"] = system

    try:
        r = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=timeout)
        r.raise_for_status()
        return r.json().get("response", "")
    except requests.exceptions.ConnectionError:
        log.error("Ollama not running — start with: ollama serve")
        return None
    except Exception as e:
        log.error(f"Ollama error: {e}")
        return None


def _ollama_chat(messages, model=None, temperature=0.3):
    """Call Ollama chat API."""
    model = model or _resolve_model() or DEFAULT_MODEL
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {"temperature": temperature, "num_ctx": 8192},
    }
    try:
        r = requests.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=300)
        r.raise_for_status()
        return r.json().get("message", {}).get("content", "")
    except Exception as e:
        log.error(f"Ollama chat error: {e}")
        return None


def is_available():
    """Check if Ollama is running and a Gemma model is loaded."""
    return _resolve_model() is not None


def _parse_json_response(text):
    """Extract JSON object from LLM response text."""
    if not text:
        return None
    try:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
    except json.JSONDecodeError:
        pass
    return None


# ── TRANSCRIPT SENTIMENT (replaces Claude Haiku) ─────────────────────────────


def extract_kol_sentiment(channel_name, transcript_text, max_chars=6000):
    """Extract structured KOL intelligence from a transcript.

    Replaces the Claude Haiku call in transcript_intelligence.py.
    Cost: $0 (local inference) vs ~$0.001/call on Haiku.

    Returns dict matching transcript_intelligence.py schema:
        sentiment, sentiment_score, main_thesis, key_quotes, topics,
        price_prediction, confidence
    """
    prompt = f"""Analyze this Bitcoin video transcript from {channel_name}.

TRANSCRIPT (truncated):
{transcript_text[:max_chars]}

Extract the following as JSON:
{{
  "sentiment": "bullish" | "bearish" | "neutral" | "mixed",
  "sentiment_score": 0-100 (0=extremely bearish, 50=neutral, 100=extremely bullish),
  "main_thesis": "1-2 sentence summary of the creator's main argument",
  "key_quotes": ["up to 3 notable direct quotes, max 100 chars each"],
  "topics": ["list of 3-5 specific topics discussed: e.g. 'ETF flows', 'mining difficulty', 'Fed policy'"],
  "price_prediction": "any specific price target or timeline mentioned, or null",
  "confidence": "high" | "medium" | "low" (how confident the creator seems)
}}

Focus on Bitcoin-specific content. Ignore ads, intros, sponsor segments.
Return ONLY the JSON object."""

    result = _ollama_generate(prompt, temperature=0.1, max_tokens=500)
    parsed = _parse_json_response(result)
    if parsed:
        log.info(f"  Local LLM: {channel_name} -> {parsed.get('sentiment')} ({parsed.get('sentiment_score', '?')}/100)")
    else:
        log.warning(f"Failed to parse local LLM response for {channel_name}")
    return parsed


# ── DIGEST SUMMARY (replaces Claude Haiku) ────────────────────────────────────


def summarize_creator_consensus(creator_summaries_text):
    """Generate a 3-4 sentence summary of what Bitcoin creators are saying.

    Replaces the Haiku call in build_transcript_digest().
    """
    prompt = f"""Summarize what Bitcoin creators are saying in 3-4 sentences.
Focus on consensus and divergence. Be concise and direct.

{creator_summaries_text}

Return ONLY the summary text, nothing else."""

    result = _ollama_generate(prompt, temperature=0.3, max_tokens=300)
    if result:
        return result.strip()
    return ""


# ── SCRIPT QUALITY GATE (replaces Claude API) ────────────────────────────────


def grade_script(script_json):
    """Grade a Pulse Check script before rendering.
    Returns (grade: str, issues: list, score: int).
    """
    dialogue = script_json.get("dialogue", [])
    text = " ".join(d.get("text", "") for d in dialogue)

    prompt = f"""Grade this Bitcoin news show script on a scale of A-F.

SCRIPT:
{text[:3000]}

Evaluate:
1. Does it have a clear narrative arc (hook -> body -> conclusion)?
2. Is the voice authoritative and direct (not generic AI)?
3. Are transitions between clips natural?
4. Does it end with a strong signoff?

Return ONLY valid JSON:
{{
  "grade": "A" | "B" | "C" | "D" | "F",
  "score": 0-100,
  "issues": ["issue1", "issue2"],
  "suggestion": "one sentence improvement"
}}"""

    result = _ollama_generate(prompt, temperature=0.1, max_tokens=300)
    if not result:
        return "B", [], 75  # safe default

    parsed = _parse_json_response(result)
    if parsed:
        return parsed.get("grade", "B"), parsed.get("issues", []), parsed.get("score", 75)
    return "B", [], 75


# ── TWEET GENERATION (supplement tweet machine) ──────────────────────────────


def generate_signal_tweet(brief_text, style="observation"):
    """Generate a Protocol Pulse tweet from the morning brief."""
    prompt = f"""You are a ghost analyst inside Protocol Pulse. Bitcoin only.
Style: dry, understated, data-first. No emoji. No exclamation marks.
Max 280 chars. One clean observation.

BRIEF:
{brief_text[:2000]}

Write ONE tweet. Return ONLY the tweet text, nothing else."""

    result = _ollama_generate(prompt, temperature=0.7, max_tokens=100)
    if result:
        return result.strip().strip('"').strip("'")
    return None
