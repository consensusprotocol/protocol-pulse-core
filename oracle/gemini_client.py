"""
GEMINI CLIENT — Thin wrapper for Google Generative AI API
==========================================================
POST to generativelanguage.googleapis.com, handles errors,
timeouts, JSON parsing, and rate limiting (60 RPM free tier).
"""

import os
import json
import time
import logging
import threading
import urllib.request
import urllib.error

logger = logging.getLogger("gemini_client")

API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
DEFAULT_MODEL = "gemini-2.5-flash"
TIMEOUT_SEC = 30
RPM_LIMIT = 60


class RateLimiter:
    """Simple sliding-window rate limiter."""

    def __init__(self, max_calls, window_sec=60):
        self.max_calls = max_calls
        self.window = window_sec
        self.timestamps = []
        self.lock = threading.Lock()

    def wait(self):
        with self.lock:
            now = time.time()
            self.timestamps = [t for t in self.timestamps if now - t < self.window]
            if len(self.timestamps) >= self.max_calls:
                sleep_for = self.window - (now - self.timestamps[0]) + 0.1
                if sleep_for > 0:
                    logger.info(f"Rate limit: sleeping {sleep_for:.1f}s")
                    time.sleep(sleep_for)
            self.timestamps.append(time.time())


class GeminiClient:
    """Minimal Gemini API client using urllib (no extra deps)."""

    def __init__(self, api_key=None, model=DEFAULT_MODEL):
        # Lazy-load key: read from env OR .env file directly
        key = api_key or os.environ.get("GEMINI_API_KEY", "")
        if not key:
            for env_path in [
                os.path.join(os.path.dirname(__file__), "..", ".env"),
                "/home/ultron/protocol_pulse/.env",
            ]:
                if os.path.exists(env_path):
                    for line in open(env_path):
                        if line.startswith("GEMINI_API_KEY="):
                            key = line.strip().split("=", 1)[1].strip().strip("\"'")
                            break
                if key:
                    break
        self.api_key = key
        self.model = model
        self.rate_limiter = RateLimiter(RPM_LIMIT)
        self.enabled = bool(self.api_key)
        if not self.enabled:
            logger.warning("GEMINI_API_KEY not set — Gemini client disabled")

    def generate(self, contents, system_instruction=None, temperature=0.7, max_tokens=2048):
        """
        Send a generateContent request.

        Args:
            contents: list of content parts, e.g.:
                [{"role": "user", "parts": [{"text": "hello"}]}]
            system_instruction: optional system prompt string
            temperature: sampling temperature
            max_tokens: max output tokens

        Returns:
            dict with 'text' (str) and 'usage' (dict) on success,
            or dict with 'error' (str) on failure.
        """
        if not self.enabled:
            return {"error": "Gemini client disabled (no API key)"}

        self.rate_limiter.wait()

        url = f"{API_BASE}/{self.model}:generateContent?key={self.api_key}"

        body = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        if system_instruction:
            body["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_SEC) as resp:
                result = json.loads(resp.read().decode("utf-8"))

            # Extract text from response
            candidates = result.get("candidates", [])
            if not candidates:
                return {"error": "No candidates in response", "raw": result}

            parts = candidates[0].get("content", {}).get("parts", [])
            text = "".join(p.get("text", "") for p in parts)

            usage = result.get("usageMetadata", {})
            return {"text": text, "usage": usage}

        except urllib.error.HTTPError as e:
            body_text = e.read().decode("utf-8", errors="replace")
            logger.error(f"Gemini API HTTP {e.code}: {body_text[:500]}")
            return {"error": f"HTTP {e.code}", "detail": body_text[:500]}

        except urllib.error.URLError as e:
            logger.error(f"Gemini API URL error: {e.reason}")
            return {"error": f"URL error: {e.reason}"}

        except json.JSONDecodeError as e:
            logger.error(f"Gemini API JSON parse error: {e}")
            return {"error": f"JSON parse error: {e}"}

        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return {"error": str(e)}

    def generate_text(self, prompt, system_instruction=None, **kwargs):
        """Convenience: send a single text prompt, return text or error string."""
        contents = [{"role": "user", "parts": [{"text": prompt}]}]
        result = self.generate(contents, system_instruction=system_instruction, **kwargs)
        return result.get("text", result.get("error", "Unknown error"))

    def generate_with_image(self, prompt, image_b64, mime_type="image/jpeg",
                            system_instruction=None, **kwargs):
        """Send text + image, return result dict."""
        contents = [{
            "role": "user",
            "parts": [
                {"text": prompt},
                {"inlineData": {"mimeType": mime_type, "data": image_b64}},
            ],
        }]
        return self.generate(contents, system_instruction=system_instruction, **kwargs)
