#!/usr/bin/env python3
"""pipeline/vo.py — Parameterised VO generator.

FROZEN from segment_v1/gen_vo.py. Logic unchanged.
Only difference: paths resolved from --segment dir instead of hardcoded BASE.

Usage:
    python3 -m pipeline.vo --segment <segment_dir>
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import resolve_paths

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "video_pipeline_v3"))   # this checkout, never a fixed path (Claude-gates C4)
from relay import get_key


def generate_vo(segment_dir, voice_key="ELEVENLABS_VOICE_ID_PP2",
                model_id="eleven_v4"):
    """Generate VO stems from EDL. Returns manifest dict."""
    paths = resolve_paths(segment_dir)
    vo_dir = paths["vo_dir"]
    os.makedirs(vo_dir, exist_ok=True)

    with open(paths["edl_json"]) as f:
        edl = json.load(f)

    voice_id = get_key(voice_key)
    if not voice_id:
        print(f"FATAL: {voice_key} not in .env")
        sys.exit(1)
    voice_id = voice_id.strip()

    print(f"=== VO GENERATION ===")
    print(f"  Voice: {voice_key} (id from .env, not printed)")
    print(f"  Model: {model_id}")

    from elevenlabs import ElevenLabs
    api_key = get_key("ELEVENLABS_API_KEY")
    client = ElevenLabs(api_key=api_key)

    voice_settings = {
        "stability": 0.60,
        "similarity_boost": 0.80,
        "style": 0.30,
        "use_speaker_boost": True,
    }

    manifest = {}

    def _generate_stem(text, stem_name):
        # law L-a: a stem is keyed by the hash of (text, voice id, model): a stem is reused only for the exact
        # same script, never for a different channel list (the stem name used to be fixed per role)
        import hashlib
        key = hashlib.sha256(f"{text}\x1f{voice_id}\x1f{model_id}".encode()).hexdigest()[:12]
        stem_name = f"{stem_name}_{key}"
        wav_path = os.path.join(vo_dir, f"{stem_name}.wav")
        def _readable(path):
            import wave
            try:
                with wave.open(path, "rb") as wf:
                    return wf.getnframes() > wf.getframerate() // 2    # at least 0.5 s of audio
            except Exception:
                return False
        if os.path.exists(wav_path) and _readable(wav_path):
            print(f"  Reusing: {stem_name} (same text, voice and model)")
            return {"stem_wav": os.path.basename(wav_path), "voice_id": voice_id, "model_id": model_id,
                    "text": text, "key": key}
        print(f"  Generating: {stem_name} ({len(text.split())} words)")

        audio_gen = client.text_to_speech.convert(
            voice_id=voice_id,
            text=text,
            model_id=model_id,
            voice_settings=voice_settings,
            output_format="pcm_22050",
        )

        import struct
        import wave
        pcm_data = b"".join(audio_gen)
        with wave.open(wav_path, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(22050)
            wf.writeframes(pcm_data)

        print(f"    Saved: {wav_path}")
        return {
            "stem_wav": os.path.basename(wav_path),
            "voice_id": voice_id,
            "model_id": model_id,
            "text": text,
            "key": key,
        }

    # Intro
    vo_section = edl.get("vo", {})
    intro_text = vo_section.get("intro", "")
    if intro_text:
        manifest["intro"] = _generate_stem(intro_text, f"vo_intro_{voice_key.split('_')[-1].lower()}_v1")

    # Bridges
    bridges = vo_section.get("bridges", [])
    for i, bridge in enumerate(bridges):
        text = bridge.get("text", "")
        if text:
            bkey = f"bridge_{i+1:02d}"
            manifest[bkey] = _generate_stem(text, f"vo_{bkey}_{voice_key.split('_')[-1].lower()}_v1")

    # Signoff — generate fresh via signoff.py (S2 law)
    signoff_text = vo_section.get("signoff", "")
    # Law L-a: the sign-off names EVERY credited channel, in the credits card's order (the hook's channel
    # first, then each clip's, each once), from the final EDL. It used to list the clips' channels only, so
    # the hook's channel was never spoken (2026-11-11 preview: DataDash on the card, not in the sign-off).
    from credit_rings import credit_channels
    channels_list = credit_channels(edl)
    segment_id = os.path.basename(os.path.normpath(segment_dir))
    topic = edl.get("topic", "")

    if channels_list:
        try:
            from signoff import generate_signoff
            signoff_text = generate_signoff(topic, channels_list, segment_id)
        except Exception as e:
            print(f"  Signoff generation failed: {e}")
            if not signoff_text:          # fresh phrasing per video even without the generator: rotate the
                import hashlib            # generator's three registers by run (credit / thanks / follow first)
                names = (f"{', '.join(channels_list[:-1])}, and {channels_list[-1]}" if len(channels_list) > 1
                         else channels_list[0])
                signoff_text = [f"Clips today from {names}. Go follow them for more. Links are below.",
                                f"Big thanks to {names} for today's clips. Follow them all, links are below.",
                                f"Go follow {names}. Today's clips came from them. Links are below."][
                    int(hashlib.sha256(segment_id.encode()).hexdigest(), 16) % 3]
    if signoff_text:
        manifest["signoff"] = _generate_stem(signoff_text, f"vo_signoff_{voice_key.split('_')[-1].lower()}_v1")

    # Write manifest
    manifest_path = os.path.join(vo_dir, "VO_MANIFEST.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"\n  Manifest: {manifest_path}")

    return manifest


def main():
    p = argparse.ArgumentParser(description="Parameterised VO generator (frozen from gen_vo.py)")
    p.add_argument("--segment", required=True, help="Segment directory")
    p.add_argument("--voice-key", default="ELEVENLABS_VOICE_ID_PP2", help="Voice env key")
    p.add_argument("--model", default="eleven_v4", help="ElevenLabs model ID")
    args = p.parse_args()

    generate_vo(args.segment, args.voice_key, args.model)


if __name__ == "__main__":
    main()
