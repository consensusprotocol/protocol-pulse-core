"""
VISION GUIDE — Gemini-powered hardware setup guidance
=======================================================
Analyzes images of Bitcoin hardware (Coldcard, Trezor, BitAxe, Start9, etc.)
and provides step-by-step setup walkthroughs via multi-turn sessions.

SECURITY: Never reads/repeats visible seed phrases — warns user immediately.
"""

import os
import json
import time
import uuid
import logging
import threading
from gemini_client import GeminiClient

logger = logging.getLogger("vision_guide")

SYSTEM_PROMPT = """You are Protocol Pulse Oracle — a Bitcoin hardware expert specializing in:
- Hardware wallets: Coldcard, Trezor, Ledger, BitKey, Foundation Passport, SeedSigner, Jade (Blockstream)
- Mining hardware: BitAxe, Antminer, Whatsminer, custom ASIC setups, mining rig configuration
- Node software: Start9, Umbrel, RaspiBlitz, myNode, Bitcoin Core, Casa node
- Multisig setups: Sparrow, Electrum, Specter Desktop, Casa multisig, Nunchuk
- Seed phrase backup: metal plates (Cryptosteel, Billfodl), paper backup best practices
- Air-gapped signing, PSBTs, and secure key management

When analyzing images:
1. Identify the device/screen shown
2. Explain what step the user is at in the setup process
3. Give clear, numbered next steps
4. Flag any security concerns visible in the image

CRITICAL SECURITY RULES:
- If you see ANY seed phrase, mnemonic words, private keys, or recovery phrases in the image:
  * DO NOT read them out or repeat them
  * IMMEDIATELY warn: "⚠️ SEED PHRASE VISIBLE — Never share this with anyone. Cover it now."
  * Do NOT include any of the visible words in your response
- If you see passwords, PINs, or passphrases, do NOT repeat them
- Always remind users to verify firmware signatures
- Always recommend air-gapped operations when possible

Respond in JSON format:
{
    "device_name": "identified device or 'unknown'",
    "category": "wallet|miner|node|signing|other",
    "current_step": "description of what's shown",
    "security_alert": null or "warning message",
    "steps": ["step 1", "step 2", ...],
    "guidance_text": "natural language explanation for TTS"
}"""


def analyze_image(image_b64, mime_type="image/jpeg", context=""):
    """
    Analyze a single image of Bitcoin hardware.

    Args:
        image_b64: base64-encoded image data
        mime_type: image MIME type
        context: optional user context/question

    Returns:
        dict with analysis results or error
    """
    # Strip data URL prefix if present (defense-in-depth)
    if image_b64.startswith("data:"):
        image_b64 = image_b64.split(",", 1)[1]

    client = GeminiClient()
    if not client.enabled:
        return {"error": "Vision guide disabled (no GEMINI_API_KEY)"}

    prompt = "Analyze this Bitcoin hardware image."
    if context:
        prompt += f"\n\nUser context: {context}"
    prompt += "\n\nRespond in the JSON format specified in your instructions."

    result = client.generate_with_image(
        prompt=prompt,
        image_b64=image_b64,
        mime_type=mime_type,
        system_instruction=SYSTEM_PROMPT,
        temperature=0.3,
        max_tokens=1024,
    )

    if "error" in result:
        return result

    # Parse JSON from response
    text = result.get("text", "")
    try:
        # Strip markdown code fences if present
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
            if cleaned.startswith("json"):
                cleaned = cleaned[4:].strip()
        parsed = json.loads(cleaned)
        parsed["_raw_usage"] = result.get("usage", {})
        return parsed
    except json.JSONDecodeError:
        return {
            "device_name": "unknown",
            "category": "other",
            "guidance_text": text,
            "steps": [],
            "security_alert": None,
            "_parse_fallback": True,
        }


class GuideSession:
    """Multi-turn setup guide session with conversation history."""

    # Class-level session store
    _sessions = {}
    _lock = threading.Lock()
    SESSION_TTL = 3600  # 1 hour

    def __init__(self, session_id=None):
        self.session_id = session_id or str(uuid.uuid4())
        self.history = []  # list of {"role": ..., "parts": [...]}
        self.created_at = time.time()
        self.last_active = time.time()
        self.device_name = None
        self.client = GeminiClient()

    @classmethod
    def get_or_create(cls, session_id=None):
        """Get existing session or create new one."""
        with cls._lock:
            # Cleanup expired sessions
            now = time.time()
            expired = [
                sid for sid, s in cls._sessions.items()
                if now - s.last_active > cls.SESSION_TTL
            ]
            for sid in expired:
                del cls._sessions[sid]

            if session_id and session_id in cls._sessions:
                session = cls._sessions[session_id]
                session.last_active = now
                return session

            session = cls(session_id)
            cls._sessions[session.session_id] = session
            return session

    @classmethod
    def active_count(cls):
        return len(cls._sessions)

    def send_image(self, image_b64, mime_type="image/jpeg", question=""):
        """Send an image with optional question in the guided session."""
        # Strip data URL prefix if present
        if image_b64.startswith("data:"):
            image_b64 = image_b64.split(",", 1)[1]

        if not self.client.enabled:
            return {"error": "Vision guide disabled (no GEMINI_API_KEY)"}

        parts = []
        if question:
            parts.append({"text": question})
        else:
            parts.append({"text": "What do you see? Guide me through the next steps."})
        parts.append({"inlineData": {"mimeType": mime_type, "data": image_b64}})

        self.history.append({"role": "user", "parts": parts})

        result = self.client.generate(
            contents=self.history,
            system_instruction=SYSTEM_PROMPT,
            temperature=0.3,
            max_tokens=1024,
        )

        if "error" in result:
            # Remove failed message from history
            self.history.pop()
            return result

        text = result.get("text", "")
        self.history.append({"role": "model", "parts": [{"text": text}]})
        self.last_active = time.time()

        # Try parsing JSON
        try:
            cleaned = text.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3]
                cleaned = cleaned.strip()
                if cleaned.startswith("json"):
                    cleaned = cleaned[4:].strip()
            parsed = json.loads(cleaned)
            if parsed.get("device_name") and parsed["device_name"] != "unknown":
                self.device_name = parsed["device_name"]
            parsed["session_id"] = self.session_id
            parsed["turn"] = len(self.history) // 2
            return parsed
        except json.JSONDecodeError:
            return {
                "session_id": self.session_id,
                "turn": len(self.history) // 2,
                "guidance_text": text,
                "device_name": self.device_name,
                "_parse_fallback": True,
            }

    def send_text(self, question):
        """Send a text-only follow-up question."""
        if not self.client.enabled:
            return {"error": "Vision guide disabled (no GEMINI_API_KEY)"}

        self.history.append({"role": "user", "parts": [{"text": question}]})

        result = self.client.generate(
            contents=self.history,
            system_instruction=SYSTEM_PROMPT,
            temperature=0.3,
            max_tokens=1024,
        )

        if "error" in result:
            self.history.pop()
            return result

        text = result.get("text", "")
        self.history.append({"role": "model", "parts": [{"text": text}]})
        self.last_active = time.time()

        return {
            "session_id": self.session_id,
            "turn": len(self.history) // 2,
            "guidance_text": text,
            "device_name": self.device_name,
        }

    def info(self):
        return {
            "session_id": self.session_id,
            "device_name": self.device_name,
            "turns": len(self.history) // 2,
            "created_at": self.created_at,
            "last_active": self.last_active,
        }
