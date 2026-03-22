Load ~/protocol_pulse/PIPELINE_LAWS.md first. Three surgical fixes. Read each file fully before touching it. bash regression_test.sh before commit.

CONTEXT:
- TTS_PROVIDER=local in .env
- F5 fine-tune is distorted/metallic — abandoning it
- ElevenLabs quota exhausted
- Chatterbox TTS v0.1.6 is installed, proven quality (used in oracle/avatar_server.py)
- Chatterbox API: from chatterbox.tts import ChatterboxTTS; model = ChatterboxTTS.from_pretrained(device="cuda:0")
- Eryn (Host 1) = Kokoro af_heart — keep as-is, working fine
- PBX (Host 2) = currently broken F5 — switch to Chatterbox
- Space Tap is wired in daily_run.py line 164 BUT inside "if not clips / else" block — never runs with --skip-scan
- Space Tap scraper works (captured Jesse Tevelow today, clips in cache)
- Social segment upgrade was supposed to happen in social_episode CC but check if it committed

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FIX 1 — tts_engine.py: Replace F5 with Chatterbox for PBX (Host 2)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Read the full tts_engine.py synthesize_host2() function first.

Replace the F5 code path with Chatterbox:
1. Add lazy init function _init_chatterbox() similar to _init_f5():
   global _CHATTERBOX_MODEL
   from chatterbox.tts import ChatterboxTTS
   _CHATTERBOX_MODEL = ChatterboxTTS.from_pretrained(device="cuda:0")

2. In synthesize_host2(), replace the F5 call with:
   wav = _CHATTERBOX_MODEL.generate(text, exaggeration=0.4, cfg_weight=0.5)
   # Save wav to output_path via torchaudio or soundfile
   import torchaudio
   torchaudio.save(output_path.replace(".m4a", ".wav"), wav, 24000)
   # Convert wav to m4a
   subprocess.run(["ffmpeg", "-y", "-i", output_path.replace(".m4a", ".wav"),
                   "-c:a", "aac", "-ar", "48000", "-ac", "2", output_path],
                  capture_output=True)

3. Remove ALL the F5 EQ chain (highpass, equalizer calls) — Chatterbox does not need post-processing EQ

4. Keep the ElevenLabs fallback path intact but it will fail gracefully since quota is 0

5. Test immediately after writing:
   cd ~/protocol_pulse/video_pipeline_v3
   python3 -c "
   from tts_engine import synthesize_host2
   synthesize_host2('Bitcoin hashrate just hit a new all-time high while price is in extreme fear. The machines never lie.', '/tmp/pbx_chatterbox_test.m4a')
   print('Test OK')
   "
   Then ffprobe /tmp/pbx_chatterbox_test.m4a to confirm valid audio.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FIX 2 — daily_run.py: Move Space Tap OUTSIDE the skip-scan block
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Read daily_run.py lines 145-200 fully.

Space Tap (Step 2c) is currently INSIDE the "else: clips found" block.
This means it only runs when cached_only=False AND clips were found.
The overnight loop uses --skip-scan (cached_only=True) so Space Tap NEVER runs.

Fix: Move the Space Tap block to run AFTER Step 3 (script generation) but BEFORE
Step 4 (TTS) — this way it runs regardless of cached_only mode.

Specifically:
1. CUT the entire Step 2c block (lines ~164-179):
   # ─── Step 2c: Space Tap clip discovery (pre-script) ───
   try:
       sys.path.insert(...)
       from scraper import get_best_space_clips
       _st_data = get_best_space_clips(max_clips=4)
       ...
   except Exception as e:
       print(f"  Space Tap: skipped ({e})")

2. PASTE it after the script save (after line ~195 where script.json is saved)
   but BEFORE Step 4 TTS. Also keep the space_tap_clips injection into script dict.

3. Since Space Tap now runs after script generation, also inject space_tap_clips
   back into the script and re-save script.json:
   if selections.get("space_tap_clips"):
       script["space_tap_clips"] = selections["space_tap_clips"]
       with open(os.path.join(run_dir, "script.json"), "w") as f:
           json.dump(script, f, indent=2)
       print(f"  Space Tap: injected {len(selections["space_tap_clips"])} clips into script")

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FIX 3 — Check social_episode CC output, complete if needed
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Check: tmux capture-pane -t social_episode -p | tail -20
Check: cd ~/protocol_pulse && git log --oneline -5

If social_episode CC did NOT commit the social segment upgrade:
Complete it here. In script_writer.py, find where social segment narration is generated
(search for "social_posts", "TWEET LAW", "social_segment").

Upgrade the narration style instruction in the prompt to:
  "For each social post, PBX narrates as LIVE field intelligence:
   Structure: [handle] just posted [engagement figure if likes>1000]: [quote/paraphrase].
   Then 1-2 sentences of PBX analysis — what this signals, why it matters TODAY.
   Feel: PBX has been tracking Bitcoin Twitter all morning and is reporting back live.
   Do NOT say posted on Twitter or X. Just say posted or said.
   Max 3 posts total. 20-25 seconds each. Total segment ~75 seconds.
   TWEET LAW still applies: only reference handles actually in the social_posts list."

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
VALIDATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. python3 -c "from tts_engine import synthesize_host2; synthesize_host2('test', '/tmp/t.m4a'); print('OK')"
2. ffprobe /tmp/t.m4a — confirm valid audio
3. bash ~/protocol_pulse/regression_test.sh — ZERO FAILs

COMMIT:
git add video_pipeline_v3/tts_engine.py video_pipeline_v3/daily_run.py video_pipeline_v3/script_writer.py
git commit -m "fix(tts): replace F5 with Chatterbox for PBX voice — clean no-distortion; fix(pipeline): move Space Tap outside skip-scan block — fires every render; fix(social): upgrade segment to live field intelligence narration"
git push

After commit, restart the overnight loop:
pkill -f overnight_render_loop; pkill -f daily_producer; sleep 3
tmux send-keys -t render_main "cd ~/protocol_pulse && git pull && python3 overnight_render_loop.py --daemon" Enter

Do NOT touch: assembler.py, gemini_grade.py, gemini_grade.py, overnight_render_loop.py itself (structure).
tts_engine.py + daily_run.py + script_writer.py only.
