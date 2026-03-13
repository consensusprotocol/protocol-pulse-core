Read PIPELINE_LAWS.md first. Then make these EXACT changes to video_pipeline_v3/tts_engine.py:

1. Update the module docstring to say "TTS Engine V7 — Dual-provider: ElevenLabs (default) + Inworld."

2. After the VOICES dict (line ~46), add:

```python
# ── INWORLD VOICE CONFIGS (set TTS_PROVIDER=inworld in .env to activate) ──
# Winners selected 2026-03-12: Lauren (sharp female) + Nate (authoritative male)
_LAUREN_INWORLD = {
    "voice_id": "Lauren",
    "name": "Lauren",
    "model_id": "inworld-tts-1.5-max",
    "speed": 1.0,
    "temperature": 0.5,
}
_NATE_INWORLD = {
    "voice_id": "Nate",
    "name": "Nate",
    "model_id": "inworld-tts-1.5-max",
    "speed": 1.0,
    "temperature": 0.5,
}
INWORLD_VOICES = {
    1: _LAUREN_INWORLD,
    2: _NATE_INWORLD,
}

def _get_tts_provider() -> str:
    return os.environ.get("TTS_PROVIDER", "elevenlabs").lower().strip()
```

3. Add a new function `tts_inworld(text, output_path, host=1, segment_type="narration") -> bool` BEFORE `tts_elevenlabs`. It should:
   - Load INWORLD_API_KEY from env via _get_cached_key("INWORLD_API_KEY")
   - POST to https://api.inworld.ai/tts/v1/voice with voiceId, modelId, speakingRate=1.0, temperature=0.5
   - Decode base64 audioContent from response
   - Write to temp .mp3 file
   - Run ffmpeg atempo=1.2 on it -> output_path (libmp3lame -q:a 2)
   - CRITICAL: check os.path.getsize(output_path) >= 10240 — if not, raise RuntimeError("TTS output too small — silent file detected")
   - Return True on success, raise RuntimeError on any failure (never silently fail)

4. Find the line in the generate/render loop that calls `tts_elevenlabs(text, line_path, ...)` and wrap it:
```python
_provider = _get_tts_provider()
if _provider == "inworld":
    _tts_ok = tts_inworld(text, line_path, host_num, segment_type=segment_type)
else:
    _tts_ok = tts_elevenlabs(text, line_path, host_num, segment_type=segment_type)
if _tts_ok:
    # ... rest of existing success block
```

5. DO NOT change anything else. DO NOT touch the ElevenLabs logic. V9 is currently rendering with ElevenLabs — this change only activates when TTS_PROVIDER=inworld is set in .env.

6. Run: python3 -c "import ast; ast.parse(open('video_pipeline_v3/tts_engine.py').read()); print('OK')"

7. Commit: git add video_pipeline_v3/tts_engine.py && git commit -m "feat(tts): add Inworld provider Lauren+Nate (TTS_PROVIDER=inworld), ElevenLabs default" && git push