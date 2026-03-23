Read ~/protocol_pulse/PIPELINE_LAWS.md first.

TASK: Eliminate 4 mid-video silence gaps. Grade D flagged 4 silence gaps >0.8s.
Root cause: ElevenLabs API latency between TTS calls creates dead audio when one
call takes longer than expected, and explicit 0.3s silence gaps accumulate.

FILES IN SCOPE: video_pipeline_v3/tts_engine.py ONLY
DO NOT touch: assembler.py, overnight_render_loop.py, daily_producer.py, script_writer.py

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 1 — CROSS-LLM AUDIT (mandatory)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
cd ~/protocol_pulse

Register in utils/cross_llm_audit.py FEATURE_MAP and EXPLICIT_FILES:
  "fix-silence-gaps": ("PIPELINE_LAWS.md", "main")
  EXPLICIT_FILES["fix-silence-gaps"] = ["video_pipeline_v3/tts_engine.py"]

python3 utils/cross_llm_audit.py --feature fix-silence-gaps
[save C1 output]
python3 utils/cross_llm_audit.py --feature fix-silence-gaps --cycle 2 --cycle1-results [C1_PATH]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 2 — AUDIT TTS ENGINE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Read tts_engine.py fully. Find:
1. Where 0.3s silence gaps are inserted between lines
2. How ElevenLabs API calls are made — is there retry logic?
3. What happens if an ElevenLabs call fails or times out — does it produce silence?
4. The audio concatenation logic — how are individual line audio files joined?

Run a test to confirm ElevenLabs is being used and measure latency:
  cd ~/protocol_pulse/video_pipeline_v3
  time python3 -c "
  import os; os.environ['TTS_PROVIDER']='elevenlabs'
  from tts_engine import synthesize_speech
  synthesize_speech('Bitcoin is the exit.', host=2, output_path='/tmp/test_el.mp3')
  print('done')
  "

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 3 — FIX SILENCE GAPS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Fix 1 — Reduce inter-line silence: The 0.3s silence between lines is too long.
Reduce to 0.1s maximum for ElevenLabs (which already has natural pauses built in).
Find the silence insertion logic and reduce duration when TTS_PROVIDER=elevenlabs.

Fix 2 — ElevenLabs retry with fallback: If ElevenLabs call fails or returns
empty audio, retry once with exponential backoff (wait 2s, retry).
If retry fails, fall back to local Kokoro for that line only — never produce silence.

Fix 3 — Pre-generate all TTS in parallel before assembly:
If not already done, generate ALL dialogue lines concurrently using ThreadPoolExecutor
before any assembly begins. This prevents API latency stacking sequentially.
Check if this is already implemented — if so, verify it's working correctly.

Fix 4 — Trim leading/trailing silence from each ElevenLabs output:
ElevenLabs sometimes pads audio with 0.1-0.2s silence at start/end.
After each synthesis, run: ffmpeg -af silenceremove=start_periods=1:start_silence=0.03:start_threshold=-40dB
This removes sub-40dB silence at the start of each clip.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 4 — VERIFY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
python3 -m py_compile video_pipeline_v3/tts_engine.py && echo SYNTAX_OK

Test full TTS generation for a sample dialogue:
  python3 -c "
  import os; os.environ['TTS_PROVIDER']='elevenlabs'
  from tts_engine import generate_episode_audio
  # or equivalent function that generates all lines
  " 2>&1 | grep -E "silence|gap|ERROR|generated|duration" | head -10

After next render, silence_check must show 0 gaps >0.8s.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 5 — REGRESSION + COMMIT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
bash ~/protocol_pulse/regression_test.sh  # must show 0 FAILs
git add video_pipeline_v3/tts_engine.py
git commit -m "fix(tts): eliminate silence gaps — reduced inter-line silence, ElevenLabs retry+fallback, parallel pre-generation, leading silence trim"
git push

IMPORTANT: Do not ask for confirmation before committing. Run git add, git commit, and git push automatically. The commit is part of the task, not optional.
