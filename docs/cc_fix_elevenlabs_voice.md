Read ~/protocol_pulse/PIPELINE_LAWS.md first.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MANDATORY AUDIT-FIRST LAW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DO NOT write any code until the cross-LLM audit completes.
The audit fires Gemini + GPT-4o + Grok in parallel on the actual files.
Their consensus determines what gets built and how.
This is non-negotiable — skipping the audit is what caused every regression tonight.

TASK: ElevenLabs voice integration — broadcast quality PBX voice for all renders.
TTS_PROVIDER=elevenlabs already set in .env. PBX voice ID HmUVvDlHsEz0m3eUGLgu in tts_engine.py.
Problems: turbo model used instead of broadcast quality, intro music too loud vs narrator.

FILES IN SCOPE:
- video_pipeline_v3/tts_engine.py
- video_pipeline_v3/assembler.py (music volume only)
DO NOT touch: overnight_render_loop.py, daily_producer.py, script_writer.py

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 1 — CROSS-LLM AUDIT (Cycle 1 + 2)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
cd ~/protocol_pulse
python3 utils/cross_llm_audit.py --feature fix-elevenlabs-voice
[save C1 output]
python3 utils/cross_llm_audit.py --feature fix-elevenlabs-voice --cycle 2 --cycle1-results [C1_OUTPUT]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 2 — IMPLEMENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
In tts_engine.py:
1. Change eleven_turbo_v2_5 → eleven_multilingual_v2 for PBX voice
   Turbo is fast/cheap. Multilingual v2 is broadcast quality.
2. Set stability=0.5, similarity_boost=0.85, style=0.3 for PBX
   These settings produce authoritative broadcaster tone.
3. Verify ALL host:2 lines route to ElevenLabs when TTS_PROVIDER=elevenlabs
4. Ensure proper error handling — if ElevenLabs API fails, fall back to local

In assembler.py (music volume only — DO NOT touch anything else):
5. Find intro music volume setting — search for: volume=0.0[0-9], music_vol, intro_mus
   Current issue: music drowns out narrator in intro segment.
   Target: narrator at 1.0 (full), music bed at 0.07-0.09
   Find the exact ffmpeg volume filter for intro music and reduce it.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 3 — TEST VOICE QUALITY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
cd ~/protocol_pulse/video_pipeline_v3
python3 -c "
import os; os.environ['TTS_PROVIDER']='elevenlabs'
from tts_engine import synthesize_speech
result = synthesize_speech(
    'Bitcoin is not a bet. It is a declaration of sovereignty. Stay in the signal.',
    host=2, output_path='/tmp/pbx_elevenlabs_test.mp3', segment_type='cold_open'
)
print('Result:', result)
import subprocess
r = subprocess.run(['ffprobe','-v','quiet','-show_entries',
    'format=duration:stream=codec_name','-of','default=noprint_wrappers=1',
    '/tmp/pbx_elevenlabs_test.mp3'], capture_output=True, text=True)
print('Audio:', r.stdout.strip())
"
Listen to /tmp/pbx_elevenlabs_test.mp3 — should sound like a real broadcaster.
Run ffmpeg loudness check:
  ffmpeg -i /tmp/pbx_elevenlabs_test.mp3 -af ebur128 -f null - 2>&1 | grep "I:"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 4 — REGRESSION + COMMIT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
bash ~/protocol_pulse/regression_test.sh
git add video_pipeline_v3/tts_engine.py video_pipeline_v3/assembler.py
git commit -m "feat(tts): ElevenLabs eleven_multilingual_v2 broadcast quality, stability tuned, intro music balance fixed"
git push