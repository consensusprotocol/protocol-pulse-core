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

sys.path.insert(0, "/home/ultron/protocol_pulse/video_pipeline_v3")
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
    print(f"  Voice: {voice_key} = {voice_id}")
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
        print(f"  Generating: {stem_name} ({len(text.split())} words)")
        wav_path = os.path.join(vo_dir, f"{stem_name}.wav")

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
    # Extract channel names and segment id for signoff generator
    channels_list = []
    for clip in edl.get("clips", []):
        ch = clip.get("channel", "")
        if ch and ch not in channels_list:
            channels_list.append(ch)
    segment_id = os.path.basename(os.path.normpath(segment_dir))
    topic = edl.get("topic", "")

    if channels_list:
        try:
            from signoff import generate_signoff
            signoff_text = generate_signoff(topic, channels_list, segment_id)
        except Exception as e:
            print(f"  Signoff generation failed: {e}")
            if not signoff_text:
                signoff_text = f"Clips today from {', '.join(channels_list[:-1])}, and {channels_list[-1]}. Go follow them. Links are below." if len(channels_list) > 1 else f"Clips today from {channels_list[0]}. Go follow them. Links are below."
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
