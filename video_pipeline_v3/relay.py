"""Key resolution helper for Protocol Pulse pipeline.

Resolution order for every key:
  1. Process environment variable (os.environ)
  2. ~/protocol_pulse/.env file
  3. video_pipeline_v3/.env file (local override)
  4. Raise KeyError with a clear message — no network calls.

Replit relay is deprecated (migrated to Ultron self-hosted Flask).
The run() and query_db() stubs are kept for import compatibility but
do nothing — callers should be updated to use direct DB/service calls.
"""
import os
from pathlib import Path

# ── .env loader ──────────────────────────────────────────────────────────────

_env_cache: dict = {}
_env_loaded = False

def _load_dotenv_file(path: str) -> dict:
    """Parse a .env file and return key→value dict (no shell expansion)."""
    result = {}
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                k = k.strip()
                v = v.strip().strip("'\"'").strip()  # strip surrounding quotes
                if k:
                    result[k] = v
    except FileNotFoundError:
        pass
    return result

def _load_env():
    global _env_cache, _env_loaded
    if _env_loaded:
        return
    base = Path(__file__).resolve().parent
    # Load root .env first, then pipeline-local .env (local wins)
    root_env   = base.parent / ".env"           # ~/protocol_pulse/.env
    local_env  = base / ".env"                  # video_pipeline_v3/.env
    merged = {}
    merged.update(_load_dotenv_file(str(root_env)))
    merged.update(_load_dotenv_file(str(local_env)))
    _env_cache = merged
    _env_loaded = True

# ── Public API ───────────────────────────────────────────────────────────────

def get_key(name: str, required: bool = True) -> str:
    """Return the value of an API key.

    Checks (in order):
      1. os.environ   — set by systemd unit, Docker, or manual export
      2. .env files   — ~/protocol_pulse/.env then video_pipeline_v3/.env

    Args:
        name:     Environment variable name, e.g. "ELEVENLABS_API_KEY"
        required: If True (default), raises KeyError when key is missing.
                  If False, returns empty string instead.
    """
    # 1. Live environment
    val = os.environ.get(name, "")
    if val:
        return val

    # 2. .env files
    _load_env()
    val = _env_cache.get(name, "")
    if val:
        return val

    if required:
        raise KeyError(
            f"[relay] API key \'{name}\' not found.\n"
            f"  Add it to ~/protocol_pulse/.env or export it before running the pipeline.\n"
            f"  Example:  echo \'ELEVENLABS_API_KEY=sk-...\' >> ~/protocol_pulse/.env"
        )
    return ""

def reload_env():
    """Force re-read of .env files (useful after adding keys at runtime)."""
    global _env_loaded
    _env_loaded = False
    _load_env()

# ── Deprecated stubs (kept for import compatibility) ─────────────────────────

def run(cmd: str, timeout: int = 25) -> str:
    """DEPRECATED — Replit relay is dead. Returns empty string."""
    print(f"[relay] WARNING: run() called but Replit relay is deprecated. cmd={cmd!r:.60}")
    return ""

def query_db(sql: str) -> str:
    """DEPRECATED — use direct SQLAlchemy calls on Ultron instead."""
    print(f"[relay] WARNING: query_db() called but Replit relay is deprecated.")
    return "[]"


# ── LLM fallback helper ─────────────────────────────────────────────────────

def call_llm(prompt: str, max_tokens: int = 4000, temperature: float = 0.3) -> str | None:
    """Call an LLM with Anthropic→Grok fallback. Returns response text or None."""
    import logging
    log = logging.getLogger("relay.call_llm")

    # Try Anthropic first
    anthropic_key = get_key("ANTHROPIC_API_KEY", required=False)
    if anthropic_key:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=anthropic_key)
            resp = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            return resp.content[0].text.strip()
        except Exception as e:
            log.warning(f"Anthropic failed: {e}")

    # Fallback to Grok/xAI
    xai_key = get_key("XAI_API_KEY", required=False)
    if xai_key:
        try:
            import requests
            resp = requests.post(
                "https://api.x.ai/v1/chat/completions",
                headers={"Authorization": f"Bearer {xai_key}", "Content-Type": "application/json"},
                json={
                    "model": "grok-3-mini-fast",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                },
                timeout=120,
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"].strip()
            log.warning(f"Grok API error {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            log.warning(f"Grok failed: {e}")

    # Fallback to Gemini
    gemini_key = get_key("GEMINI_API_KEY", required=False)
    if gemini_key:
        try:
            import requests
            gemini_model = get_key("GEMINI_MODEL", required=False) or "gemini-2.0-flash"
            resp = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{gemini_model}:generateContent?key={gemini_key}",
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"maxOutputTokens": max_tokens, "temperature": temperature},
                },
                timeout=120,
            )
            if resp.status_code == 200:
                data = resp.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                log.info("Gemini fallback succeeded")
                return text
            log.warning(f"Gemini API error {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            log.warning(f"Gemini failed: {e}")

    log.error("All LLM providers failed (Anthropic + Grok + Gemini)")
    return None
