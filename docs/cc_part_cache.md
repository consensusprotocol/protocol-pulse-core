Read ~/protocol_pulse/PIPELINE_LAWS.md.
Read ~/protocol_pulse/video_pipeline_v3/daily_producer.py lines 520-700 (run_pipeline, content lock logic).
Read ~/protocol_pulse/video_pipeline_v3/assembler.py lines 1-100 (imports, constants).
Read ~/protocol_pulse/video_pipeline_v3/config/feature_flags.json.
Read ~/protocol_pulse/video_pipeline_v3/utils/feature_flags.py 2>/dev/null || grep -n "is_enabled\|load_all" ~/protocol_pulse/video_pipeline_v3/utils/feature_flags.py.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RENDERED PARTS CACHE — FEATURE FLAG IMPLEMENTATION
Goal: skip re-rendering identical part_*.mp4 files between
iterations. Expected: 90min renders → 15-20min on iter 2+.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CROSS-LLM AUDIT FIRST (mandatory):
Register in utils/cross_llm_audit.py:
  FEATURE_MAP["part-cache"] = ("PIPELINE_LAWS.md", "main")
  EXPLICIT_FILES["part-cache"] = [
      "video_pipeline_v3/daily_producer.py",
      "video_pipeline_v3/assembler.py",
      "video_pipeline_v3/config/feature_flags.json",
  ]

Each LLM answers these 3 questions:
Q1: Where in daily_producer.py/assembler.py are part_*.mp4 files
    generated? What is the exact call chain from run_pipeline to
    each part file being written to disk?
Q2: What inputs determine each part file's content? If script.json,
    clips/, and tts/ are identical (content lock), are the resulting
    part_*.mp4 files guaranteed to be identical?
Q3: What is the safest cache key for each part? Filename only?
    Hash of inputs? What breaks if we use a stale cached part?

python3 utils/cross_llm_audit.py --feature part-cache
Save C1 to docs/audits/part_cache_c1.json
Cycle 2 with --cycle 2, save C2.
Synthesize consensus.

IMPLEMENTATION (after audit confirms):

STEP 1 — ADD FLAG TO feature_flags.json
Add to ~/protocol_pulse/video_pipeline_v3/config/feature_flags.json:
  "cache_rendered_parts": false

Default OFF. We enable it explicitly when ready.

STEP 2 — SAVE PARTS TO LOCKED_CONTENT ON ITER 1
In daily_producer.py, in the content lock save block (around line 1121
where script.json, clips/, tts/ are saved):

After saving TTS, also save the rendered parts directory:
  if is_enabled("cache_rendered_parts"):
      parts_src = os.path.join(run_dir, "parts")
      parts_dst = os.path.join(locked_dir, "parts")
      if os.path.exists(parts_src) and os.listdir(parts_src):
          shutil.copytree(parts_src, parts_dst, dirs_exist_ok=True)
          logger.info(f"PARTS CACHED: {len(os.listdir(parts_src))} parts → {parts_dst}")

STEP 3 — RESTORE PARTS FROM CACHE ON REUSE ITERATIONS
In daily_producer.py, in the reuse_content block (around line 601):

After restoring TTS from locked_content, also restore parts:
  if is_enabled("cache_rendered_parts"):
      cached_parts = os.path.join(locked_dir, "parts")
      live_parts = os.path.join(run_dir, "parts")
      if os.path.exists(cached_parts) and os.listdir(cached_parts):
          os.makedirs(live_parts, exist_ok=True)
          shutil.copytree(cached_parts, live_parts, dirs_exist_ok=True)
          part_count = len(os.listdir(live_parts))
          logger.info(f"PARTS RESTORED: {part_count} cached parts → skipping assembly")
          # Set a flag so assembler knows to skip to final concat
          os.makedirs(os.path.join(run_dir, ".cache_flags"), exist_ok=True)
          open(os.path.join(run_dir, ".cache_flags", "parts_cached"), "w").close()
      else:
          logger.info("No cached parts found — running full assembly")

STEP 4 — SKIP ASSEMBLY IF PARTS CACHED
In daily_producer.py, find where assembler is called (Step 7).
Wrap the assembler call:
  parts_cached_flag = os.path.join(run_dir, ".cache_flags", "parts_cached")
  if is_enabled("cache_rendered_parts") and os.path.exists(parts_cached_flag):
      logger.info("PARTS CACHE HIT — skipping assembly, going straight to final concat")
      # Skip to final concat step — parts already exist
      # The assembler's concat_final() or equivalent should be called directly
      # Find the exact function that does final concat from existing parts
  else:
      # Normal assembly
      result = assemble(...)

STEP 5 — CLEAR CACHE ON GRADE A
In overnight_render_loop.py, on Grade A before clearing locked_content:
  if is_enabled("cache_rendered_parts"):
      parts_cache = os.path.join(locked_dir, "parts")
      if os.path.exists(parts_cache):
          shutil.rmtree(parts_cache, ignore_errors=True)
          log("Parts cache cleared — Grade A achieved, fresh content next cycle")

SAFETY RULES (must be in code):
- NEVER use cached parts if script.json hash differs from when parts were cached
  Store hash: json.dumps(script, sort_keys=True) → md5 → save to locked_content/parts_hash.txt
  On restore: verify hash matches. If not, log warning and skip cache.
- NEVER use cached parts if clips/ directory has different file count or names
- If any cached part file is 0 bytes or corrupt (ffprobe check): skip cache, run full assembly
- Log every cache hit/miss with part count

VERIFICATION:
Run iter1 with cache_rendered_parts: false — confirm no change in behavior
Enable flag: set "cache_rendered_parts": true in feature_flags.json
Run iter2 — confirm parts are restored from cache and assembly is skipped in logs
Measure time: should be ~15-20min vs ~90min
Run regression_test.sh — 0 FAILs

COMMIT:
git add video_pipeline_v3/daily_producer.py \
  video_pipeline_v3/config/feature_flags.json \
  overnight_render_loop.py \
  docs/audits/part_cache_c1.json \
  docs/audits/part_cache_c2.json
git commit -m "feat(pipeline): rendered parts cache — skip assembly on iter 2+ when parts identical
- Feature flag: cache_rendered_parts (default OFF, enable to activate)
- Saves cached parts to locked_content/parts/ after iter 1
- Restores on iter 2+ if script hash + clip list match
- Safety: hash verification + ffprobe integrity check per part
- Expected: 90min renders → 15-20min on iter 2+"
git push
