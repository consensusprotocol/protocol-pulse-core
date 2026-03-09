# FEATURE SPEC — [FEATURE_NAME]
<!-- Copy this file to scripts/agent/specs/SPEC_[feature-name].md and fill every section -->
<!-- Incomplete specs = broken agents. Be ruthlessly specific. -->

## IDENTITY
- **FEATURE:**        [human-readable name]
- **BRANCH:**         agent/[feature-name]
- **WORKTREE_DIR:**   ~/worktrees/[feature-name]
- **AGENT_SESSION:**  agent_[feature-name]
- **PRIORITY:**       🔴 High / 🟡 Medium / 🟢 Queue

---

## SCOPE
<!-- 1 paragraph. What this builds. What it does NOT build. -->
[What is being built, exactly. Be specific about the feature boundary.]

---

## SUCCESS CRITERIA
<!-- Numbered. Measurable. No vibes. Agent must satisfy ALL of these. -->
1. [Specific measurable outcome]
2. [Specific measurable outcome]
3. [Specific measurable outcome]
4. Regression test passes with zero FAILs
5. All changes committed and pushed to branch agent/[feature-name]

---

## FILES_TO_TOUCH
<!-- Agent ONLY modifies these files. No exceptions. -->
- `video_pipeline_v3/[file.py]` — [what change]
- `core/[file.py]` — [what change]
- `scripts/agent/specs/SPEC_[feature-name].md` — this file (mark complete when done)

## FILES_NEVER_TOUCH
<!-- Touching any of these = immediate stop, do not commit -->
- `video_pipeline_v3/PIPELINE_LAWS.md` — gospel, read-only
- `regression_test.sh` — immutable
- `core/routes.py` — unless explicitly in FILES_TO_TOUCH
- Any file in `~/protocol_pulse/` (production) — worktree only

## SHARED_DEPS
<!-- Read but never written -->
- `video_pipeline_v3/assembler.py`
- `video_pipeline_v3/tts_engine.py`
- `video_pipeline_v3/relay.py`
- `video_pipeline_v3/config/feature_flags.json`

---

## BOOT SEQUENCE
<!-- Agent reads these IN ORDER before writing a single line of code -->
1. Read this FEATURE_SPEC.md completely
2. Read ~/protocol_pulse/video_pipeline_v3/PIPELINE_LAWS.md
3. Read AGENT_CONTEXT.md (auto-generated in worktree root)
4. Run: cat test_data/intelligence/live_signals_template.json | head -50
5. Begin implementation

---

## TEST COMMAND
```bash
# Run this before every commit. Must return exit 0.
cd ~/worktrees/[feature-name] && TEST_MODE=true python3 -m pytest test_data/test_[feature].py -v
# OR for pipeline tests:
cd ~/worktrees/[feature-name]/video_pipeline_v3 && TEST_MODE=true python3 -c "from [module] import [function]; [function](test=True); print('PASS')"
```

## PASS CRITERIA
- Exit code: 0
- Output must contain: "PASS" or "passed"
- No FAIL lines in output
- No Python tracebacks

---

## LAWS TO LOAD
- [x] PIPELINE_LAWS.md (always)
- [ ] ARTICLE_PAGE_LAWS.md (only if touching article code)
- [ ] LIVE_INTELLIGENCE_LAWS.md (only if touching live signals)
- [ ] PULSE_TERMINAL_LAWS.md (only if touching terminal API)

---

## DATA ISOLATION
- All reads from production: OK (read-only)
- All writes: MUST go to `~/worktrees/[feature-name]/test_data/`
- TEST_DB_PATH: `~/worktrees/[feature-name]/test_data/test.db`
- Never write to `~/protocol_pulse/data/` or `~/protocol_pulse/instance/`

---

## GPU USAGE
- Requires GPU render: YES / NO
- If YES: acquire lock first: `~/protocol_pulse/scripts/agent/gpu_lock.sh acquire agent_[feature-name]`
- Release on completion: `~/protocol_pulse/scripts/agent/gpu_lock.sh release`

---

## PR FORMAT
- **Title:** `feat([feature-name]): [one-line description]`
- **Base branch:** main
- **Head branch:** agent/[feature-name]

---

## COMPLETION COMMAND
```bash
~/protocol_pulse/scripts/agent/merge_agent.sh [feature-name]
```

---

## STATUS
- [ ] Spec written
- [ ] Agent launched
- [ ] Build in progress
- [ ] Tests passing
- [ ] PR opened
- [ ] Merged to main
