"""
faye_routes.py
==============
Flask blueprint for Faye — the scam-check tool.

Mount in core/app.py:
    from core.routes_faye import faye_bp
    app.register_blueprint(faye_bp)

Endpoint:
    POST /api/faye/analyze
    Form fields:
        kind: 'image' | 'audio'
        file: the captured media
    Returns JSON:
        { verdict: 'scam'|'ok'|'warn', title: str, reason: str, confidence: float, signals: [..] }

Design philosophy:
    - Default to caution. Anything ambiguous -> 'warn', not 'ok'.
    - Cite specific signals so the user can verify.
    - <4 seconds end-to-end target.
"""
from __future__ import annotations
import base64
import logging
import os
import re
import tempfile
import time
from pathlib import Path
from typing import Optional

from flask import Blueprint, jsonify, render_template, request

log = logging.getLogger(__name__)
faye_bp = Blueprint("faye", __name__)

# ---------------------------------------------------------------
# API key resolution
# ---------------------------------------------------------------
# app.py loads only core/.env, which holds ANTHROPIC_API_KEY but NOT the
# Gemini key. The Gemini key lives in the project-root .env. Resolve keys
# by checking the process environment first, then both .env files on disk.
_ENV_FILES = (
    "/home/ultron/protocol_pulse/.env",       # project-root .env (has GEMINI_API_KEY)
    "/home/ultron/protocol_pulse/core/.env",  # core/.env (loaded by app.py)
)


def _resolve_key(*names: str) -> Optional[str]:
    """Return the first matching key from os.environ, then from the .env files."""
    for n in names:
        v = os.environ.get(n)
        if v:
            return v
    try:
        from dotenv import dotenv_values  # type: ignore
        for env_path in _ENV_FILES:
            if not os.path.exists(env_path):
                continue
            vals = dotenv_values(env_path)
            for n in names:
                if vals.get(n):
                    return vals[n]
    except Exception as e:
        log.warning("faye: .env key resolution failed: %s", e)
    return None


def _gemini_key() -> Optional[str]:
    return _resolve_key("GEMINI_API_KEY", "GOOGLE_API_KEY", "GOOGLE_GEMINI_API_KEY")


def _anthropic_key() -> Optional[str]:
    return _resolve_key("ANTHROPIC_API_KEY")


def _anthropic_available() -> bool:
    """Anthropic credits get exhausted periodically; the ops stack drops a flag
    file when the spend cap is hit. Skip the (slow, guaranteed-400) call then."""
    flag = "/home/ultron/protocol_pulse/logs/ANTHROPIC_SPEND_CAP_HIT.flag"
    return _anthropic_key() is not None and not os.path.exists(flag)


@faye_bp.route("/faye", methods=["GET"])
@faye_bp.route("/faye/", methods=["GET"])
def faye_page():
    """Serve the Faye landing page."""
    return render_template("faye.html")

# ---------------------------------------------------------------
# Known-bad patterns. Extend this aggressively from real cases.
# ---------------------------------------------------------------
SCAM_PATTERNS = [
    # Hardware-wallet impersonation (the Karen Faye case)
    (r"ledger.*(verify|validate|update|migrate|recover)", "Ledger impersonation language"),
    (r"trezor.*(verify|validate|update|migrate|recover)", "Trezor impersonation language"),
    (r"(seed|recovery)\s*phrase", "Asking for seed/recovery phrase — Ledger/Trezor NEVER do this"),
    (r"24[\s-]?word", "Reference to 24-word phrase outside official setup"),
    # Urgency
    (r"(within\s+24\s*hours|act\s+now|immediately|urgent|account\s+(suspended|locked|frozen))",
     "Manufactured urgency — classic scam tell"),
    # Crypto support impersonation
    (r"(coinbase|binance|kraken|gemini)\s+(support|security|team).*(call|verify|click)",
     "Exchange-support impersonation"),
    # Wallet drainers
    (r"(connect|verify)\s+(your\s+)?wallet", "Wallet-connection prompt — common drainer pattern"),
    (r"approve\s+(this\s+)?transaction", "Unsolicited approval request"),
    # Generic fraud
    (r"government\s+(grant|refund|stimulus)", "Government grant scam"),
    (r"(irs|hmrc|cra).*(arrest|warrant|tax\s+fraud)", "Tax-authority impersonation"),
    (r"romance|lonely|widow.*invest", "Romance/pig-butchering pattern"),
]

KNOWN_GOOD_DOMAINS = {
    "ledger.com", "shop.ledger.com",
    "trezor.io", "shop.trezor.io",
    "coinbase.com", "kraken.com",
    "blockstream.com", "mempool.space",
}

LOOKALIKE_REGEX = re.compile(
    r"(led[g9]er|tre[z2]or|c[o0]inbase|binan[c5]e|krak[e3]n|metamasc?k)",
    re.IGNORECASE,
)

# ---------------------------------------------------------------
# Vision and transcription
# ---------------------------------------------------------------
FAYE_PROMPT = (
    "You are Faye, a fraud-detection assistant for crypto and Bitcoin users. "
    "The user pointed their phone at something — an email, a letter, a website, "
    "a QR code, a chat message — and wants to know if it is a scam. Be thorough "
    "and bias toward caution: when in doubt, return verdict='warn'.\n\n"
    "Return JSON ONLY (no markdown, no preamble) with these keys:\n"
    '  "extracted_text": all visible text, verbatim\n'
    '  "urls_or_qr": any URL or QR target you can read\n'
    '  "claimed_sender": who/what this claims to be from\n'
    '  "urgency_markers": list of urgency/pressure phrases (e.g. "24 hours", "act now")\n'
    '  "asks_for_seed": true if it asks for seed/recovery phrase or 24-word phrase\n'
    '  "asks_for_funds": true if it asks the user to send crypto, connect wallet, or approve a transaction\n'
    '  "lookalike_brand": brand name being impersonated, or null\n'
    '  "assessment": one paragraph plain-English analysis (<=200 chars)\n'
    '  "verdict": "scam" | "ok" | "warn"\n'
    '  "confidence": float 0.0 to 1.0\n'
)


def _sniff_image_type(data: bytes) -> str:
    """
    Detect the true image MIME type from magic bytes.

    The Faye frontend saves every camera capture as '.jpg' regardless of the
    real format, so the file suffix is meaningless. iOS photos are commonly
    HEIC — mislabeling HEIC as image/jpeg makes Gemini unable to decode it,
    which is exactly the 'Not enough signal' failure mode.
    """
    if not data or len(data) < 12:
        return "image/jpeg"
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    # HEIC / HEIF: an 'ftyp' box at offset 4, brand code follows at offset 8
    if data[4:8] == b"ftyp":
        brand = data[8:12]
        if brand in (b"heic", b"heix", b"hevc", b"hevx"):
            return "image/heic"
        if brand in (b"mif1", b"msf1", b"heif", b"mif1"):
            return "image/heif"
        return "image/heic"  # unknown ftyp brand — treat as HEIC
    return "image/jpeg"


# Gemini 2.5 Flash natively decodes these; no local conversion needed
_GEMINI_OK_TYPES = {"image/jpeg", "image/png", "image/webp", "image/heic", "image/heif", "image/gif"}
_MAX_EDGE = 1600  # downscale very large phone photos for speed; Gemini tiles at ~1568px


def _prepare_image(image_path: Path) -> tuple:
    """
    Load an uploaded image and return (bytes, mime_type) ready for an LLM.

    - JPEG/PNG/WEBP/GIF: opened via PIL, EXIF-rotated upright, downscaled if huge,
      re-encoded as a clean JPEG (fixes sideways letters and oversized photos).
    - HEIC/HEIF: passed through untouched with the correct mime type — Gemini
      decodes HEIC server-side, so no local HEIC codec is required.
    """
    raw = image_path.read_bytes()
    mime = _sniff_image_type(raw)

    if mime in ("image/heic", "image/heif"):
        # Cannot re-encode HEIC without a native codec; Gemini handles it directly.
        return raw, mime

    try:
        from PIL import Image, ImageOps  # type: ignore
        import io
        with Image.open(io.BytesIO(raw)) as im:
            im = ImageOps.exif_transpose(im)        # honour phone orientation
            im = im.convert("RGB")
            if max(im.size) > _MAX_EDGE:
                im.thumbnail((_MAX_EDGE, _MAX_EDGE), Image.LANCZOS)
            buf = io.BytesIO()
            im.save(buf, format="JPEG", quality=88)
            return buf.getvalue(), "image/jpeg"
    except Exception as e:
        log.warning("faye: image prep fell back to raw bytes: %s", e)
        return raw, (mime if mime in _GEMINI_OK_TYPES else "image/jpeg")


def analyze_image_with_gemini(image_path: Path) -> dict:
    """Primary vision LLM — Gemini 2.5 Flash. Fast and currently the funded path."""
    try:
        import google.generativeai as genai  # type: ignore
        api_key = _gemini_key()
        if not api_key:
            log.warning("faye: no GEMINI_API_KEY in env or .env files")
            return {}
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(_resolve_key("GEMINI_MODEL") or "gemini-2.5-flash")

        img_bytes, media_type = _prepare_image(image_path)
        log.info("faye: gemini input mime=%s bytes=%d", media_type, len(img_bytes))

        resp = model.generate_content(
            [FAYE_PROMPT, {"mime_type": media_type, "data": img_bytes}],
            generation_config={
                "temperature": 0.2,
                "max_output_tokens": 1024,
                # Force valid JSON — eliminates markdown-fence / preamble parse failures
                "response_mime_type": "application/json",
            },
        )
        raw_text = getattr(resp, "text", "") or ""
        parsed = _parse_llm_json(raw_text)
        if not parsed:
            # Surface what Gemini actually said so failures are diagnosable
            log.warning("faye: gemini returned unparseable response: %s", raw_text[:300])
        return parsed
    except Exception as e:
        log.exception("faye: gemini analysis failed: %s", e)
        return {}


def analyze_image_with_claude(image_path: Path) -> dict:
    """
    Vision analysis. Gemini is primary; Claude fallback via raw httpx (the local
    anthropic SDK 0.84.0 has a pydantic compatibility bug — by_alias NoneType).
    """
    # Primary: Gemini
    result = analyze_image_with_gemini(image_path)
    if result and result.get("verdict"):
        return result

    # Fallback: Anthropic via raw HTTPS (skip the broken SDK)
    if not _anthropic_available():
        log.info("faye: anthropic fallback unavailable (no key or spend cap hit)")
        return {}
    api_key = _anthropic_key()
    try:
        import httpx  # type: ignore
        img_bytes, media_type = _prepare_image(image_path)
        if media_type not in ("image/jpeg", "image/png", "image/webp", "image/gif"):
            # Anthropic's vision API does not accept HEIC; Gemini is the HEIC path
            log.info("faye: anthropic fallback skipped — unsupported mime %s", media_type)
            return {}
        b64 = base64.standard_b64encode(img_bytes).decode()
        payload = {
            "model": "claude-opus-4-7",
            "max_tokens": 1024,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}},
                    {"type": "text",  "text": FAYE_PROMPT},
                ],
            }],
        }
        r = httpx.post(
            "https://api.anthropic.com/v1/messages",
            json=payload,
            timeout=20,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
        )
        if r.status_code != 200:
            log.warning("faye: anthropic fallback returned %d: %s", r.status_code, r.text[:200])
            return {}
        data = r.json()
        text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
        return _parse_llm_json(text)
    except Exception as e:
        log.exception("faye: anthropic fallback failed: %s", e)
        return {}


def transcribe_audio(audio_path: Path) -> str:
    """Whisper large-v3 on local GPU per Ultron stack."""
    try:
        import whisper  # type: ignore
        model = whisper.load_model("large-v3", device="cuda")
        result = model.transcribe(str(audio_path), fp16=True)
        return result.get("text", "").strip()
    except Exception as e:
        log.exception("whisper failed: %s", e)
        return ""


def _parse_llm_json(text: str) -> dict:
    import json
    cleaned = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(cleaned)
    except Exception:
        m = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if m:
            try: return json.loads(m.group(0))
            except Exception: pass
    return {}


# ---------------------------------------------------------------
# Signal synthesis
# ---------------------------------------------------------------
def score_text(text: str) -> list[dict]:
    """Pattern-match the text. Each hit is a signal with weight."""
    signals = []
    low = text.lower()
    for pattern, label in SCAM_PATTERNS:
        if re.search(pattern, low):
            signals.append({"label": label, "weight": 1.0, "kind": "pattern"})
    for m in LOOKALIKE_REGEX.finditer(text):
        token = m.group(0).lower()
        # Exact known-good vs lookalike spelling
        if any(token in d for d in KNOWN_GOOD_DOMAINS):
            continue
        if token in {"ledger", "trezor", "coinbase", "binance", "kraken", "metamask"}:
            continue  # the real word, not a typo-squat
        signals.append({"label": f"Possible typo-squat: {m.group(0)!r}", "weight": 0.8, "kind": "lookalike"})
    return signals


def cross_check_x(claimed_sender: Optional[str]) -> list[dict]:
    """
    Stub for X/Twitter cross-check.
    Real impl: use Protocol Pulse's existing X scraper (services/x_scraper.py)
    to search for recent posts mentioning this sender + scam reports.
    """
    if not claimed_sender:
        return []
    # TODO: wire to services/x_scraper.search(f'"{claimed_sender}" scam OR fake OR phishing since:7d')
    return []


def synthesize_verdict(llm: dict, pattern_signals: list[dict], x_signals: list[dict]) -> dict:
    """Combine all signals into a final verdict. Defaults to caution."""
    signals_out = list(pattern_signals) + list(x_signals)

    llm_verdict = (llm.get("verdict") or "").lower()
    llm_conf = float(llm.get("confidence") or 0)

    if llm.get("asks_for_seed"):
        signals_out.append({"label": "Asks for seed/recovery phrase", "weight": 1.5, "kind": "llm"})
    if llm.get("asks_for_funds"):
        signals_out.append({"label": "Asks to connect wallet or send funds", "weight": 1.2, "kind": "llm"})
    if llm.get("urgency_markers"):
        signals_out.append({"label": f"Urgency: {', '.join(llm['urgency_markers'][:3])}", "weight": 0.6, "kind": "llm"})
    if llm.get("lookalike_brand"):
        signals_out.append({"label": f"Impersonating {llm['lookalike_brand']}", "weight": 1.0, "kind": "llm"})

    total = sum(s["weight"] for s in signals_out)

    # Did the vision/audio model actually return a usable analysis?
    llm_ran = bool(llm) and bool(
        llm.get("verdict") or llm.get("extracted_text") or llm.get("assessment")
    )

    # Decision: bias toward caution
    if total >= 1.5 or llm_verdict == "scam":
        verdict = "scam"
        title = "Likely a scam."
        reason = signals_out[0]["label"] if signals_out else "Multiple fraud indicators detected."
    elif total >= 0.5 or llm_verdict == "warn":
        verdict = "warn"
        title = "Inconclusive."
        reason = "Some risk markers present — verify the source independently before acting."
    elif llm_verdict == "ok" and llm_conf >= 0.7 and total == 0:
        verdict = "ok"
        title = "Looks legitimate."
        reason = (llm.get("assessment") or "No fraud patterns matched.")[:140]
    elif not llm_ran and total == 0:
        # The model returned nothing usable — be honest, don't imply we analyzed it
        verdict = "warn"
        title = "Couldn't read that clearly."
        reason = ("I couldn't make out the content. Try again — more light, hold steady, "
                  "and fill the frame with the message. When in doubt, don't proceed.")
    else:
        verdict = "warn"
        title = "Not enough signal."
        reason = "When in doubt — walk away. Never share your seed phrase."

    return {
        "verdict": verdict,
        "title": title,
        "reason": reason,
        "confidence": round(min(1.0, total / 3.0), 2),
        "signals": signals_out[:8],
    }


# ---------------------------------------------------------------
# Route
# ---------------------------------------------------------------
@faye_bp.route("/api/faye/analyze", methods=["POST"])
def analyze():
    t0 = time.time()
    kind = request.form.get("kind", "image")
    upload = request.files.get("file")
    if not upload:
        return jsonify(verdict="warn", title="No input received.", reason="Try again."), 400

    suffix = ".jpg" if kind == "image" else ".webm"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        upload.save(tmp.name)
        path = Path(tmp.name)

    try:
        if kind == "image":
            llm = analyze_image_with_claude(path)
            text = (llm.get("extracted_text") or "") + " " + (llm.get("urls_or_qr") or "")
        else:
            transcript = transcribe_audio(path)
            text = transcript
            # For audio, run a text-only LLM pass over the transcript
            llm = _text_only_assessment(transcript)

        pattern_signals = score_text(text)
        x_signals = cross_check_x(llm.get("claimed_sender"))
        result = synthesize_verdict(llm, pattern_signals, x_signals)
        result["elapsed_ms"] = int((time.time() - t0) * 1000)
        log.info("faye verdict=%s elapsed=%dms signals=%d",
                 result["verdict"], result["elapsed_ms"], len(result["signals"]))
        return jsonify(result)
    except Exception as e:
        log.exception("faye analysis failed")
        return jsonify(verdict="warn",
                       title="Service hiccup.",
                       reason="Could not complete the check. Treat as inconclusive."), 200
    finally:
        try: path.unlink(missing_ok=True)
        except Exception: pass


def _text_only_assessment(transcript: str) -> dict:
    """Quick text-only LLM pass for audio transcripts. Gemini-first."""
    if not transcript:
        return {}
    try:
        import google.generativeai as genai  # type: ignore
        api_key = _gemini_key()
        if not api_key:
            log.warning("faye: no GEMINI_API_KEY for audio assessment")
            return {}
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(_resolve_key("GEMINI_MODEL") or "gemini-2.5-flash")
        prompt = (
            f"You are Faye, a fraud-detection assistant. Below is a transcript of "
            f"audio someone is suspicious of. Decide if it is a scam.\n\n"
            f"TRANSCRIPT:\n\"\"\"{transcript}\"\"\"\n\n"
            "Return JSON ONLY: claimed_sender, urgency_markers (list), "
            "asks_for_seed (bool), asks_for_funds (bool), lookalike_brand, "
            "assessment (<=200 chars), verdict (scam|ok|warn), confidence (0-1)."
        )
        resp = model.generate_content(prompt, generation_config={"temperature": 0.2, "max_output_tokens": 768})
        return _parse_llm_json(resp.text or "")
    except Exception as e:
        log.exception("faye: text-only assessment failed: %s", e)
        return {}
