#!/usr/bin/env python3
"""Generate ElevenLabs TTS narration for V4 episode."""
import requests
import os
from pathlib import Path

API_KEY = "sk_95def513603b1a0f95c66836f9d00a74740575b972c1fbd9"
VOICE_ID = "HmUVvDlHsEz0m3eUGLgu"
MODEL = "eleven_turbo_v2_5"
AUDIO_DIR = Path(__file__).parent / "audio"
AUDIO_DIR.mkdir(exist_ok=True)

INTRO_TEXT = """Bitcoin. Sixty-six thousand seven hundred ninety-four dollars. Down but not out.

Fear and Greed sits at twelve. Extreme Fear. For those who've studied the cycles, you know what this means. Every time this index has dropped below fifteen, it marked a generational buying opportunity. Not opinion. History.

Meanwhile, the hashrate just hit one thousand thirty-eight exahash per second. The network has never been stronger. Miners aren't slowing down. They're doubling down. While weak hands panic-sell, the infrastructure powering this network grows more resilient by the day.

Mempool is clear. Fees at three sats per vbyte. It's practically free to move your bitcoin right now. Day seven hundred and eight since the halving. The supply shock isn't coming. It's already here. Three point one two five BTC per block. Math doesn't negotiate.

The network doesn't lie. Stay free. Stay sovereign."""

PIP_TEXT = """While mainstream media fixates on price action, the chain tells a different story entirely. Block after block, every ten minutes, the network settles billions in value without permission, without intermediaries, without downtime.

The partners we feature today understand this. They're building for the signal, not the noise. When the market tests your conviction, you look at the fundamentals. Hashrate up. Fees low. Difficulty climbing. Every metric that matters is screaming strength.

This is what conviction looks like when the market tests you."""

def generate_tts(text: str, output_path: Path):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
    headers = {"xi-api-key": API_KEY, "Content-Type": "application/json"}
    body = {
        "text": text,
        "model_id": MODEL,
        "voice_settings": {
            "stability": 0.45,
            "similarity_boost": 0.82,
            "speed": 1.2
        }
    }
    print(f"[TTS] Generating: {output_path.name} ({len(text)} chars)...")
    resp = requests.post(url, json=body, headers=headers, timeout=60)
    if resp.status_code != 200:
        print(f"[TTS] ERROR {resp.status_code}: {resp.text[:500]}")
        return False
    output_path.write_bytes(resp.content)
    size_kb = len(resp.content) / 1024
    print(f"[TTS] Saved: {output_path} ({size_kb:.1f} KB)")
    return size_kb > 50

if __name__ == "__main__":
    intro_ok = generate_tts(INTRO_TEXT, AUDIO_DIR / "narration_intro_20260328.wav")
    pip_ok = generate_tts(PIP_TEXT, AUDIO_DIR / "narration_pip_20260328.wav")
    
    if not intro_ok:
        print("[TTS] INTRO FAILED - file too small or error")
        exit(1)
    if not pip_ok:
        print("[TTS] PIP FAILED - file too small or error")
        exit(1)
    print("[TTS] All narrations generated successfully.")
