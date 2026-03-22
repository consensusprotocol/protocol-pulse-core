Read ~/protocol_pulse/PIPELINE_LAWS.md first.

TASK: ElevenLabs voice integration audit — ensure PBX voice sounds broadcast-quality,
intro music balance is correct, and ElevenLabs is used for all render voices.

TTS_PROVIDER=elevenlabs is already set in .env.
PBX voice ID: HmUVvDlHsEz0m3eUGLgu (already in tts_engine.py)
ElevenLabs API key: already in .env as ELEVENLABS_API_KEY

DO NOT touch: assembler.py, overnight_render_loop.py, gemini_grade.py, daily_producer.py

STEP 1 — AUDIT TTS ENGINE
Read tts_engine.py fully — find the ElevenLabs path.
Verify TTS_PROVIDER=elevenlabs routes ALL host 2 (PBX) lines to ElevenLabs.
Check the ElevenLabs model: should be eleven_multilingual_v2 for best quality, not turbo.
Check stability/similarity_boost settings — for broadcast: stability=0.5, similarity_boost=0.85.

STEP 2 — AUDIO LEVEL AUDIT
The intro narrator volume is too quiet vs music.
Find in assembler.py where intro music volume is set vs narrator volume.
The music should be at 0.08-0.10 volume, narrator at 1.0 (full).
Check the current values and fix if wrong.
Find: intro_volume, music_volume, or equivalent variable names.

STEP 3 — TEST ELEVENLABS
Test a single line synthesis:
  cd ~/protocol_pulse/video_pipeline_v3
  python3 -c "
  import os; os.environ['TTS_PROVIDER']='elevenlabs'
  from tts_engine import synthesize_speech
  synthesize_speech('Bitcoin is the exit. Stay sovereign.', host=2, output_path='/tmp/test_pbx.mp3')
  import subprocess
  r = subprocess.run(['ffprobe','-v','quiet','-show_entries','format=duration','-of','default=noprint_wrappers=1','/tmp/test_pbx.mp3'], capture_output=True, text=True)
  print('Duration:', r.stdout.strip())
  "
Verify audio file exists and sounds correct.

STEP 4 — MODEL UPGRADE
Change eleven_turbo_v2_5 to eleven_multilingual_v2 for PBX voice.
Turbo is fast but lower quality. Multilingual v2 is broadcast quality.
This is the model that sounds like a real broadcaster.

STEP 5 — COMMIT
git add video_pipeline_v3/tts_engine.py
git commit -m "feat(tts): ElevenLabs eleven_multilingual_v2 for PBX, optimized stability/similarity, intro music balance fixed"
git push