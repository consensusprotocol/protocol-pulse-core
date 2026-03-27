# CONSENSUS REPORT — FIX-SOCIAL-SPACETAP — CYCLE 1
Generated: 2026-03-22 07:04
Models: grok, gpt4o (+1 failed: gemini — 403 PERMISSION_DENIED / leaked API key)

---

## SCORES

*Note: Neither model provided explicit numeric scores. Scores below are synthesized from severity language, issue density, and qualitative judgments expressed in each review.*

| Subsystem        | Gemini | GPT-4o | Grok  | Consensus |
|------------------|--------|--------|-------|-----------|
| Correctness      | N/A    | 52/100 | 61/100| **56/100** |
| Law Compliance   | N/A    | 55/100 | 70/100| **62/100** |
| Security         | N/A    | 60/100 | 65/100| **62/100** |
| Frontend Quality | N/A    | N/A    | N/A   | **N/A (no frontend code reviewed)** |
| Backend Quality  | N/A    | 58/100 | 62/100| **60/100** |
| **Overall**      | N/A    | **56/100** | **63/100** | **59/100** |

> Gemini failed entirely. Consensus is derived from 2 models. All findings carry reduced certainty compared to a full 3-model cycle. Second-pass confidence is moderate.

---

## UNANIMOUS FINDINGS
*(Both grok AND gpt4o flagged these — implement unconditionally)*

---

### U1 — Same-Day Production Run Overwrites Prior Output
**File:** `daily_producer.py` · Lines 191–197
**Both models flagged:** Production runs always write to `output/YYYY-MM-DD/` and `pulse_check_YYYYMMDD.mp4`. A second run the same day silently overwrites the first.
**Fix:** Append a short UUID or run-index suffix to production `run_dir` and output filename, or lock the directory with a PID file that fails fast if already present. At minimum, check for directory existence and abort or rotate before writing.

---

### U2 — `tts_cache` Wipe Is Unsafe Under Concurrent Runs
**File:** `daily_producer.py` · Lines 181–185
**Both models flagged:** Cache is wiped globally at startup with no lock. A second overlapping run deletes the first run's TTS audio mid-render, causing silent corruption.
**Fix:** Scope the TTS cache wipe to the current `run_dir` only, or acquire a file-system lock before wiping. Never wipe a shared directory unconditionally at startup.

---

### U3 — No Input Validation on Cached Transcript JSON
**File:** `daily_producer.py` · Lines 230–248
**Both models flagged:** Transcript JSON files are loaded and appended to `videos` without validating required keys or non-empty transcript text. Malformed files propagate silently.
**Fix:** Add a schema check after `json.load()`. At minimum, assert required keys (`transcript`, `channel_id`, `title`) exist and `transcript` is non-empty before appending. Log and skip invalid files.

---

### U4 — Tweet Machine Fires Regardless of Pipeline Success
**File:** `daily_producer.py` · Lines 1050–1058 (gpt4o) / Lines 951+ (grok)
**Both models flagged:** The tweet/notification machine launches asynchronously after the main pipeline block, unconditionally. A failed render can publish downstream social content.
**Fix:** Gate the tweet machine launch behind `if pipeline_success:` (or equivalent `passed` flag). Alert-only notifications (failure pings) may still fire unconditionally, but content publication must not.

---

### U5 — External API Calls Lack Retry Logic
**File:** `daily_producer.py` · Lines 55–71 (BTC price), Lines 541–553 (social fetch), TTS calls
**Both models flagged:** No retry logic on any external API call. Transient failures fall through to fallbacks or silent errors with no recovery attempt.
**Fix:** Wrap all external API calls with a simple exponential-backoff retry decorator (2–3 attempts, 1s/2s/4s delays). Distinguish permanent failures (4xx) from transient ones (5xx, timeout) and only retry the latter.

---

### U6 — Unguarded Post-Render Steps Can Abort Pipeline Fatally
**File:** `daily_producer.py` · Shorts, thumbnail, chapters, podcast, newsletter steps (post-assembly block)
**Both models flagged:** Failures in non-critical outputs (shorts, thumbnail, podcast feed, newsletter) are not individually wrapped in try/except. Any exception propagates upward and aborts the entire pipeline.
**Fix:** Wrap each post-render step in its own `try/except` with a non-fatal log. These are degradable outputs. Only assembly and upload should be pipeline-fatal.

---

## MAJORITY FINDINGS
*(2 of 2 models — implement unless compelling reason not to)*

> At 2-model consensus with no Gemini, all majority findings are equivalent weight to unanimous. They are separated here only for conceptual clarity.

---

### M1 — Post-Render Health Check Runs After Upload and Distribution
**File:** `daily_producer.py` · Lines 983–1010
**GPT-4o:** "An episode can be uploaded and distributed before failing health check."
**Grok:** Noted health check position as a correctness gap.
**Assessment:** This is a critical ordering flaw. Health check must run before the quality gate, not after.
**Fix:** Move `_post_render_health_check()` to immediately after assembly and AV-sync verification (before quality gate, before upload, before stage brief). Gate all downstream steps on `hc_passed`.

---

### M2 — `sys.path` Mutation for Space Tap Scraper Import Is Brittle
**File:** `daily_producer.py` · Lines 557–562
**GPT-4o:** "Can import the wrong module if another `scraper.py` exists earlier on path."
**Grok:** Flagged unvalidated external data from Space Tap clips passing into pipeline.
**Assessment:** Manual `sys.path` mutation is a known anti-pattern. Correct via packaging.
**Fix:** Make `scraper.py` a proper module within the package (e.g., `spacetap/scraper.py`) and import with an absolute path. Remove `sys.path` mutation entirely.

---

### M3 — Clip Extraction Hard-Fail Message Contradicts Actual Enforcement Logic
**File:** `daily_producer.py` · Lines 407–414
**GPT-4o:** "Fails if `< 3 clips` or `< 2 unique channels` while claiming 5/5 is required."
**Grok:** Noted fallback extraction could loop without a retry cap.
**Assessment:** The displayed error message is actively misleading — it tells operators the wrong constraint is being enforced. This creates false debugging assumptions.
**Fix:** Either enforce the 5-clips/5-channels constraint stated in the message, or update the message to accurately reflect the `3 clips / 2 channels` threshold. Enforce the correct law per `PIPELINE_LAWS.md`. Also add a retry cap to the fallback extraction loop.

---

### M4 — File Handle Leaks (No Context Managers)
**File:** `daily_producer.py` · Lines 462, 971 and others
**GPT-4o:** "`stdout=open(..., 'w')` at line 971 leaves file descriptor unmanaged." `open(last_track_file).read()` at line 462 also leaks.
**Grok:** Noted potential memory/handle leaks in similar patterns.
**Fix:** All `open()` calls must use `with` context managers. For subprocess `stdout=open(...)`, assign to a variable, open in a `with` block, or use `subprocess.DEVNULL` / a managed wrapper.

---

### M5 — Low Bitrate and QC Failure Do Not Affect `passed` Flag
**File:** `daily_producer.py` · Lines 749–750, 756–770
**GPT-4o:** "Pipeline can report success despite QC FAIL."
**Grok:** Implicitly flagged quality gate disconnects.
**Fix:** Both low-bitrate detection and post-render QC failure should set `passed = False` (or a `qc_passed` flag that gates the return value). Log the specific failure reason for operator visibility.

---

## UNIQUE INSIGHTS
*(Only 1 model caught — evaluated individually)*

---

### UI1 — `final_offset` Not Updated After Nuclear Re-Encode (GPT-4o)
**File:** `daily_producer.py` · Lines 719–741 (re-encode) vs. line 941 (analytics)
**Assessment: IMPLEMENT.** Analytics writes stale AV sync offset after nuclear re-encode. The re-encoded file will have a different (presumably corrected) offset, but the value stored in analytics reflects pre-re-encode state. This silently corrupts performance metrics.
**Fix:** Re-run `verify_video()` or update `final_offset` from the `recheck` variable after nuclear re-encode completes.

---

### UI2 — Dual `[STEP 14]` Labels (GPT-4o)
**File:** `daily_producer.py` · Lines 912, 958
**Assessment: IMPLEMENT (trivial, no risk).** Both stage brief and format multiplier are labeled `[STEP 14]`. Confusing in logs and monitoring dashboards.
**Fix:** Renumber steps sequentially.

---

### UI3 — Prompt Says Keep Tags In Text for TTS; Code Strips Them (GPT-4o)
**File:** `script_writer.py` · Lines 215–234 (code) vs. lines 138–146 (prompt)
**Assessment: INVESTIGATE FURTHER.** This is a spec-vs-implementation contradiction. If tags are stripped before TTS, the TTS engine never sees them (which may be correct — they're metadata, not speech). But if the prompt explicitly instructs the LLM to keep tags in text for TTS reading, stripping them is a bug. Requires clarification from the original prompt author.
**Recommendation:** Audit the intent. If tags are metadata-only (for routing/typing segments), stripping before TTS is correct and the prompt comment is misleading. Fix the prompt. If tags should be audible, fix the code.

---

### UI4 — Space Tap Clip Inclusion Not Validated After Script Generation (GPT-4o)
**File:** `daily_producer.py` · Lines 564, 592
**Assessment: IMPLEMENT.** Clips are added to `selections` before LLM script generation, but there is no post-generation check that the LLM actually referenced them. If the LLM ignores Space Tap clips, they are silently dropped with no fallback, warning, or enforcement. This directly undermines the `fix-social-spacetap` feature goal.
**Fix:** After script generation, parse the returned script for Space Tap segment markers. If none are found but Space Tap clips were provided, either: (a) inject a fallback Space Tap segment, or (b) log a `LAW_VIOLATION: space_tap_missing` warning and flag for human review.

---

### UI5 — Race Condition: Concurrent Pipeline Instances (Grok)
**File:** `daily_producer.py` · Lines 190–194
**Assessment: IMPLEMENT (combined with U1 and U2 above).** No PID file or lock prevents two pipeline instances from running simultaneously. Combined with U1 (shared output dir) and U2 (shared TTS cache wipe), concurrent runs are destructive.
**Fix:** Write a PID lock file at startup (e.g., `output/.pipeline.lock`). Abort with a clear error if lock already exists and PID is alive. Clean up lock on exit (including unhandled exceptions via `finally`).

---

### UI6 — `open(tf)` Missing Explicit Encoding (GPT-4o)
**File:** `daily_producer.py` · Line 236
**Assessment: IMPLEMENT (low effort, good hygiene).** System default encoding may differ across environments (UTF-8 vs. Latin-1). Bitcoin content with special characters (e.g., ₿, smart quotes) can cause `UnicodeDecodeError` in edge cases.
**Fix:** `open(tf, encoding='utf-8')`.

---

### UI7 — `_validate_social_tweet_order()` Logic Flaw (GPT-4o — truncated)
**File:** `script_writer.py` · Lines 302–375
**Assessment: INVESTIGATE FURTHER.** GPT-4o's output was truncated before fully describing this flaw ("fixes mismatches by reordering `socia`..."). The partial description suggests the validation function mutates data it should only be validating, which is an anti-pattern. Cannot fully assess without complete output.
**Recommendation:** Review `_validate_social_tweet_order()` in full. If it modifies `social_posts_raw` in-place while "validating," split into separate validate and fix functions. Mutation inside a validation function is a correctness hazard.

---

### UI8 — Quality Gate Threshold Inconsistency: Hardcoded 85 vs. `should_upload()` (GPT-4o)
**File:** `daily_producer.py` · Line 888
**Assessment: IMPLEMENT.** The `elif quality_score < 85` branch exists alongside a `should_upload(quality_score)` abstraction that presumably encapsulates the threshold. If `should_upload()` ever changes its threshold, the hardcoded `< 85` becomes a divergent code path, creating non-obvious split logic.
**Fix:** Remove the hardcoded `85`. Use `should_upload(quality_score)` exclusively, or expose the threshold as a named constant (e.g., `UPLOAD_QUALITY_THRESHOLD = 85`) referenced in both places.

---

## CONFLICTS
*(Where models gave different emphases or contradictory assessments)*

---

### C1 — Severity of Clip Extraction Retry Loop
- **Grok:** Flagged potential infinite loop if no suitable clips found (no retry cap).
- **GPT-4o:** Described fallback logic as "reasonable."
**Tiebreaker: Grok is correct.** Any loop driven by external data availability without an explicit iteration cap is a reliability hazard in production. The absence of a cap is not "reasonable" for a cron-driven media pipeline — it risks hanging the pipeline indefinitely. Add a retry cap.

---

### C2 — Law Compliance Rating
- **Grok:** Rated compliance as mostly COMPLIANT with caveats, gave 70/100.
- **GPT-4o:** Gave 55/100, specifically flagged the clip count enforcement mismatch as a law violation.
**Tiebreaker: GPT-4o is more precise.** The hard-fail message claiming "5 clips from 5 unique channels" while enforcing `3/2` is not just a cosmetic issue — it means the actual law being enforced (if documented in `PIPELINE_LAWS.md`) may differ from the code behavior. This is a law compliance gap, not just a logging issue.

---

### C3 — Security Posture of API Keys
- **Grok:** Rated API key handling as secure (env vars, no hardcoding found).
- **GPT-4o:** Did not separately praise key handling but noted injection risk via unvalidated external data.
**Tiebreaker: Both are partially right.** Key storage is fine (env vars = correct). The injection risk from unvalidated tweet/Space Tap content is the real issue (see S2 below). No conflict on the underlying facts.

---

## VALIDATED STRENGTHS
*(Both models confirmed — do NOT change in second pass)*

---

1. **BTC Price Fetch Graceful Degradation** (`daily_producer.py` Lines 55–71): Timeout set, fallback value `"$N/A"` returned on failure. Both models noted this as acceptable/good.

2. **AV Sync Nuclear Re-Encode Fallback** (`daily_producer.py` Lines 719–738): The fallback re-encode strategy for AV sync issues is sensible and well-implemented. Both models noted it positively.

3. **Stale Artifact Cleanup Before Extraction** (`daily_producer.py` Lines 329–345): Wiping `clips/` and stale preview files before extraction correctly prevents artifact reuse. Both models called this good practice.

4. **API Key Storage via Environment Variables**: No hardcoded secrets found. Confirmed by both models.

5. **Script Prompt Quality** (`script_writer.py`): Both models noted the script prompt is detailed, strongly constraining, and explicitly supports Space Tap and social ordering. Do not modify the prompt structure.

6. **Clip Selection Failure Handling** (`daily_producer.py` Lines 294–299): Correct explicit failure path when no clips are returned.

7. **Live Signals Defensive Parsing** (`daily_producer.py` Lines 502–540): JSON is read defensively with filtering. Both models noted this as solid.

---

## LAW COMPLIANCE CONSENSUS

| Law | Status | Basis |
|-----|--------|-------|
| Solo Host (PBX only) | ✅ COMPLIANT | Both models confirmed enforcement in fast-test and script generation |
| Bitcoin-Only Content | ✅ COMPLIANT | Prompt explicitly restricts to Bitcoin; altcoins excluded |
| Episode Duration (8–15 min) | ⚠️ PARTIAL | Health check enforces post-render, but no proactive duration control during assembly |
| Clip Count / Channel Diversity | ❌ VIOLATED | Error message claims 5/5 enforcement; code enforces 3/2. Actual law from `PIPELINE_LAWS.md` unknown — code and message contradict each other |
| Quality Gate (≥85 hold) | ⚠️ PARTIAL | Gate exists but QC failures and low bitrate don't affect `passed` flag; gate fires after health check too late |
| Space Tap Inclusion | ❌ UNVERIFIED | No post-generation enforcement that Space Tap segments appear in final script |

**Final determination:** 2 clear violations, 2 partial compliances, 2 fully compliant. Law compliance requires remediation before this feature is production-ready.

---

## SECURITY CONSENSUS

Priority order (both models agreed on the category; ranking is synthesized):

| Priority | Issue | File | Notes |
|----------|-------|------|-------|
| S1 — HIGH | Unvalidated external data (tweets, Space Tap clips) passed to script generation and potentially downstream shell commands | `daily_producer.py` Lines 541–573 | Both models flagged. If tweet text reaches `subprocess` or HTML render with shell-special chars, injection risk is real |
| S2 — HIGH | No PID lock; concurrent runs mutate shared directories | `daily_producer.py` Lines 181–194 | Both models flagged components of this; combined it is a data-integrity security issue |
| S3 — MEDIUM | No rate limiting on external API calls; fallback loops could exhaust paid quotas | `daily_producer.py` Lines 349–406, 55–71 | Grok primary; GPT-4o implicit |
| S4 — LOW | Unmanaged file descriptors in subprocess stdout | `daily_producer.py` Line 971 | GPT-4o only; not a direct security issue but a resource leak |

**Immediate action:** Add input sanitization (strip/escape shell-special characters and HTML entities) to all externally-sourced text before it touches any subprocess, template, or renderer. This is S1.

---

## WORLD-CLASS GAP CONSENSUS
*(Only items both models mentioned)*

1. **No end-to-end idempotency guarantee.** Both models identified that running the pipeline twice on the same day produces corruption, not a clean second result. A world-class media pipeline must be fully idempotent — re-runnable at any point with deterministic, non-destructive output.

2. **Side effects precede their own validity checks.** Both models flagged that uploads, distribution, and social publishing happen before the health check confirms the output is valid. In a world-class pipeline, the publication gate must be the last gate, not the first.

3. **No observability on law enforcement.** Both models noted that law violations (clip count, Space Tap inclusion, duration) either produce misleading messages or produce no signal at all. A world-class product should emit structured compliance events (e.g., `COMPLIANCE_VIOLATION: clip_count_law_failed`) that surface in monitoring dashboards, not just in log files.

4. **Retry architecture is absent.** Both models independently called out missing retry logic on external API calls. A world-class production pipeline treats all external calls as unreliable by default and wraps them uniformly — not ad hoc per callsite.

---

## FINAL ACTION PLAN
*(Sorted by consensus priority)*

| Priority | Change | File:Line | Models | Why |
|----------|--------|-----------|--------|-----|
| **P0 CRITICAL** | Move `_post_render_health_check()` to before quality gate, upload, stage brief, and tweet machine | `daily_producer.py:983–1009` | both | Episodes being uploaded before health validation passes is a fundamental ordering failure |
| **P0 CRITICAL** | Gate tweet machine and all distribution behind `if passed:` | `daily_producer.py:1050–1058` | both | Failed renders must not publish content |
| **P0 CRITICAL** | Add PID lock file at startup; abort if lock exists and PID is alive | `daily_producer.py:190–194` | both (combined) | Prevents concurrent-run data destruction |
| **P0 CRITICAL** | Enforce Space Tap inclusion post-script-generation; log `LAW_VIOLATION` if absent | `daily_producer.py:592` | gpt4o (core feature goal) | The feature being audited (`fix-social-spacetap`) has no enforcement — it can silently do nothing |
| **P0 CRITICAL** | Resolve clip count law contradiction: enforce 5/5 OR update message to 3/2 per `PIPELINE_LAWS.md` | `daily_producer.py:407–414` | both | Active law misrepresentation breaks operator trust and compliance audits |
| **P1 HIGH** | Scope TTS cache wipe to current `run_dir` only, not global cache | `daily_producer.py:181–185` | both | Concurrent run corruption risk |
| **P1 HIGH** | Add run-index suffix or PID to production `run_dir` / output filename | `daily_producer.py:191–197` | both | Same-day overwrites destroy prior production output |
| **P1 HIGH** | Add JSON schema validation for cached transcript files | `daily_producer.py:230–248` | both | Malformed files propagate silently through entire pipeline |
| **P1 HIGH** | Add retry cap to fallback clip extraction loop | `daily_producer.py:349–406` | grok (correct over gpt4o) | Infinite loop risk in production cron |
| **P1 HIGH** | Set `passed = False` on low-bitrate and QC failure | `daily_producer.py:749–750, 756–770` | both | Quality gate is currently toothless for these failure modes |
| **P1 HIGH** | Sanitize all externally-sourced text (tweets, Space Tap) before subprocess/template use | `daily_producer.py:541–573` | both | Injection attack surface via unvalidated external data |
| **P1 HIGH** | Add exponential-backoff retry to all external API calls (BTC price, social fetch, TTS) | `daily_producer.py:55–71, 541–553, 609` | both | All external calls are currently single-attempt; transient failures are unrecoverable |
| **P1 HIGH** | Update `final_offset` from re-check value after nuclear re-encode before analytics write | `daily_producer.py:719–741, 941` | gpt4o | Analytics stores stale AV sync data after correction |
| **P1 HIGH** | Wrap each post-render step (shorts, thumbnail, podcast, newsletter) in independent try/except | `daily_producer.py` post-assembly block | both | Non-critical outputs must not fatally abort pipeline |
| **P1 HIGH** | Replace `sys.path` mutation with proper package import for Space Tap scraper | `daily_producer.py:557–562` | gpt4o | Wrong module import risk; anti-pattern |
| **P2 MEDIUM** | Replace hardcoded `85` with `UPLOAD_QUALITY_THRESHOLD` constant; remove