Read ~/protocol_pulse/PIPELINE_LAWS.md — specifically the CONTENT LOCK law.
Read ~/protocol_pulse/video_pipeline_v3/daily_producer.py lines 520-560 (run_pipeline args).
Read ~/protocol_pulse/overnight_render_loop.py lines 344-360 (run_render function).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONTENT LOCK — SURGICAL IMPLEMENTATION
Lock content after iter 1. Re-run assembly only on iters 2+.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CROSS-LLM AUDIT FIRST (mandatory):
Register "content-lock" in utils/cross_llm_audit.py:
  FEATURE_MAP["content-lock"] = ("PIPELINE_LAWS.md", "main")
  EXPLICIT_FILES["content-lock"] = [
      "video_pipeline_v3/daily_producer.py",
      "overnight_render_loop.py",
  ]
Run: python3 utils/cross_llm_audit.py --feature content-lock
Save cycle 1 to docs/audits/content_lock_c1.json
Run cycle 2: python3 utils/cross_llm_audit.py --feature content-lock --cycle 2 --cycle1-results docs/audits/content_lock_c1.json
Synthesize consensus. Implement only consensus-agreed design.

IMPLEMENTATION SPEC (after audit confirms):

CHANGE 1 — daily_producer.py:
Add --reuse-content argument to argparse:
  parser.add_argument("--reuse-content", action="store_true",
      help="Skip Steps 1-6 (fetch/script/TTS), reuse locked content from previous run")

In run_pipeline(), add reuse_content=False parameter.
When reuse_content=True:
  - Skip the tts_cache wipe entirely
  - Skip Steps 1, 2, 3, 3b, 4, 4m, 5a, 5, 6 entirely
  - Load script.json from locked content dir:
      locked_dir = os.path.join(run_dir, "locked_content")
      with open(os.path.join(locked_dir, "script.json")) as f:
          script = json.load(f)
  - Set clips_dir = os.path.join(locked_dir, "clips")
  - Set tts_cache to the locked tts dir
  - Jump directly to Step 7 (assemble)
  - Log: "REUSE MODE: skipping content fetch, using locked content from {locked_dir}"

When reuse_content=False (normal iter 1):
  After TTS generation completes (end of Step 6), save locked content:
      locked_dir = os.path.join(run_dir, "locked_content")
      os.makedirs(locked_dir, exist_ok=True)
      shutil.copy(script_json_path, os.path.join(locked_dir, "script.json"))
      shutil.copytree(clips_dir, os.path.join(locked_dir, "clips"), dirs_exist_ok=True)
      shutil.copytree(tts_cache_dir, os.path.join(locked_dir, "tts"), dirs_exist_ok=True)
      log "CONTENT LOCKED to {locked_dir} — subsequent iterations will reuse this"

CHANGE 2 — overnight_render_loop.py:
In run_render(iteration):
  - If iteration == 1: run "python3 daily_producer.py --skip-scan" (current behavior)
  - If iteration > 1: run "python3 daily_producer.py --skip-scan --reuse-content"
  - On iteration > 1: DO NOT wipe tts_cache (remove the rm -rf tts_cache line for iter > 1)

In the main loop, on Grade A:
  - Delete locked_content dir: shutil.rmtree(locked_dir, ignore_errors=True)
  - Log "Content lock cleared — next cycle will fetch fresh content"

VERIFICATION:
- Run daily_producer.py --reuse-content with a test locked_content dir
- Confirm steps 1-6 are skipped in logs
- Confirm step 7 runs with existing content
- Confirm assembly completes and produces output

bash ~/protocol_pulse/regression_test.sh — 0 FAILs
git add -A
git commit -m "feat(pipeline): content lock — reuse content across iterations, assemble-only on iter 2+, fresh fetch only on Grade A"
git push
