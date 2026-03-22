# CONSENSUS REPORT — PIPELINE-DAY3-AUDIT — CYCLE 2
Generated: 2026-03-22 00:34
Models: grok, gpt4o (+1 failed — Gemini 2.5 Pro: 403 PERMISSION_DENIED, leaked API key)

> **Meta-note on scoring:** Grok's Cycle 2 output acknowledges it was operating without its own Cycle 1 scores and reconstructed assumed baselines. GPT-4o provided no numeric scores in either cycle. Scores below are synthesized from narrative severity language across both models. Gemini's Cycle 1 output was not provided and its Cycle 2 run failed. All scores carry reduced confidence; treat as directional, not authoritative.

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Correctness | N/A (failed) | ~4.5/10 (inferred from severity of N1–N3, N9) | 5.0/10 | **4.5/10** |
| Law Compliance | N/A | ~6.5/10 (no explicit violations cited, gaps noted) | 7.0/10 | **6.5/10** |
| Security | N/A | ~4.0/10 (N6 key leak, N7 LLM patch execution flagged as P0) | 5.5/10 | **4.5/10** |
| Production Readiness | N/A | ~3.5/10 (N4 wrong file path, N5 cache wipe, daemon singleton missing) | 4.5/10 | **4.0/10** |
| **Overall** | N/A | ~4.0/10 | 5.5/10 | **4.5/10** |

> Consensus overall: **4.5/10 — NOT production-ready.** Multiple P0 blockers across correctness, security, and reliability must be resolved before any production deployment.

---

## UNANIMOUS FINDINGS
*Both functioning models flagged these. Implement unconditionally.*

### U1 — No file locking on shared JSON state files
**What it is:** `used_clips.json`, `narrative_context.json`, and related state files are read, modified, and written back with plain Python I/O and no locking. In any concurrent execution context — cron, daemon, watchdog, autonomous repair — two processes can read the same stale state simultaneously, producing a lost-update. The final write wins and silently discards the other's changes.

**Files/Lines:**
- `clip_selector.py:102–110` (`_load_used_clips()`)
- `clip_selector.py:161–176` (`_record_episode()`, `_prune_old_episodes()`)
- `script_writer.py:265–286` (`narrative_context.json` read/write)
- `overnight_render_loop.py:~548` (`write_heartbeat()`)
- `services/local_watchdog.py` — patch counters and cooldown files in `/tmp`

**What to change:**
```python
import fcntl, os, json

def _atomic_write_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)  # atomic on POSIX

def _locked_read_modify_write(path, modify_fn):
    with open(path, "r+") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            data = json.load(f)
            data = modify_fn(data)
            f.seek(0)
            f.truncate()
            json.dump(data, f, indent=2)
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
```
Apply this pattern to every shared state file. For cross-process safety, use `fcntl.flock()`. For in-process thread safety, pair with `threading.Lock()`.

---

### U2 — Unthrottled external API calls with no backoff (partially — see Conflicts for nuance)
**What it is:** Several external call sites have no retry logic, no exponential backoff, and no jitter. Quota exhaustion or transient network errors cause immediate hard failure with no recovery path.

**Files/Lines (agreed by both models):**
- `overnight_render_loop.py:231–242` — `gemini_call()` has zero retry/backoff
- `services/local_watchdog.py` — Ollama calls have zero retry/backoff
- `clip_extractor.py:~290–302` — yt-dlp timeout handling exists but no structured retry with jitter

**What to change:**
```python
import time, random

def with_backoff(fn, max_retries=5, base=1.0, cap=60.0):
    for attempt in range(max_retries):
        try:
            return fn()
        except (RateLimitError, TimeoutError, TransientError) as e:
            if attempt == max_retries - 1:
                raise
            wait = min(cap, base * (2 ** attempt)) + random.uniform(0, 1)
            log.warning(f"Retry {attempt+1}/{max_retries} after {wait:.1f}s: {e}")
            time.sleep(wait)
```
Wrap `gemini_call()`, Ollama calls, and yt-dlp invocations in this pattern. Catch specific exception types, not bare `Exception`.

---

### U3 — Silent exception swallowing that returns empty/degraded results
**What it is:** Broad `except Exception` blocks catch all failures and return empty lists, `None`, or default values without raising, alerting, or logging the full traceback. The pipeline continues in a degraded state — producing incomplete outputs — while appearing to succeed. This is the most insidious reliability failure mode.

**Files/Lines:**
- `clip_selector.py:109–110` — returns `{}` on any exception loading episode memory
- `clip_selector.py:384–388` — returns `[]` on JSON parse failure
- `clip_selector.py:609–611` — returns `[]` on any selection exception
- `script_writer.py:701–706` — labels all exceptions as "Claude API error" and silently falls back
- `tts_engine.py:772` — raises but without structured logging
- `services/local_watchdog.py` — multiple `except Exception: return False/None` in patch/health logic

**What to change:**
Replace all such blocks with:
```python
import traceback, logging
log = logging.getLogger(__name__)

# BAD:
except Exception:
    return []

# GOOD:
except Exception as e:
    log.error(
        "clip_selection_failed",
        exc_info=True,
        extra={"context": relevant_vars}
    )
    raise  # or return typed sentinel: SelectionResult(clips=[], failed=True, reason=str(e))
```
Where a fallback is genuinely required, document it explicitly and emit a structured ERROR log that will trigger monitoring. Never silently return empty on unexpected failure.

---

## MAJORITY FINDINGS
*Both models agree — implement unless there is a compelling documented reason not to.*

> Note: With only 2 functioning models, "majority" is the same threshold as "unanimous." These items have slightly weaker supporting evidence from the Cycle 1 foundation or are scoped more narrowly.

### M1 — No singleton/pidfile guard on overnight render daemon
**What it is:** `overnight_render_loop.py:548–552` starts the daemon with no check for an already-running instance. A second invocation (cron misfire, manual restart, watchdog restart) spawns a duplicate that simultaneously writes state, calls APIs, and assembles video — producing corrupted outputs and doubled quota consumption.

**File/Line:** `overnight_render_loop.py:548–552`

**What to change:**
```python
import fcntl, sys, atexit

PIDFILE = "/tmp/protocol_pulse_render.pid"

def acquire_singleton():
    fp = open(PIDFILE, "w")
    try:
        fcntl.flock(fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        sys.exit("Another render loop instance is already running.")
    fp.write(str(os.getpid()))
    fp.flush()
    atexit.register(lambda: os.unlink(PIDFILE))

acquire_singleton()  # call at module startup, before any work
```

### M2 — Insufficient error recovery in overnight render retry loop
**What it is:** `overnight_render_loop.py:485–489` waits 30 minutes and retries, but does not clear failed state (corrupted partial downloads, stale cache entries, locked temp files). Retries therefore reproduce the same failure deterministically, burning the retry budget without progress.

**File/Line:** `overnight_render_loop.py:485–489`

**What to change:** Before each retry, execute a cleanup sweep:
```python
def _clear_failed_state():
    shutil.rmtree(TEMP_DOWNLOAD_DIR, ignore_errors=True)
    TEMP_DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    # Clear only per-episode cache, not persistent TTS cache
    for f in EPISODE_CACHE_DIR.glob("*.partial"):
        f.unlink(missing_ok=True)
    log.info("cleared_failed_state_before_retry")
```

### M3 — Clip rank integrity broken after reordering transforms
**What it is:** `clip_selector.py` applies multiple reordering passes (dedup, diversity enforcement, channel-penalty reranking) but does not renumber the `rank` field after each transform. The `rank` value attached to a clip object becomes inconsistent with its actual position in the list. Downstream consumers (`script_writer.py` prompt, assembler) rely on `rank` semantics — rank 1 is the lead story — and silently receive wrong mappings.

**Files/Lines:** `clip_selector.py:403–420`, `445–504`, `506–560`, `562–584`

**What to change:**
```python
def _renumber_ranks(clips: list[Clip]) -> list[Clip]:
    """Always call after any reordering. Makes rank == position."""
    for i, clip in enumerate(clips, start=1):
        clip.rank = i
    return clips

# Apply after every reorder step:
clips = _apply_diversity_enforcement(clips)
clips = _renumber_ranks(clips)
clips = _apply_channel_penalty(clips)
clips = _renumber_ranks(clips)
```

---

## UNIQUE INSIGHTS
*Flagged by only one model. Assessed individually below.*

### From GPT-4o (not raised by Grok):

---

**N1/N2 — TTS silence fallback directly contradicts the stated hard-fail policy**
**Assessment: IMPLEMENT — P0**

This is the most important correctness finding in the entire audit. `tts_engine.py:763–774` explicitly states silence fallback is forbidden. `tts_engine.py:1266–1274` implements exactly that forbidden fallback — 3 seconds of silence — when a line fails. The policy contradiction means the safety guarantee is illusory. Failed TTS lines silently produce dead air in the final render.

Fix: Either (a) enforce the hard-fail at the line level — abort the episode and raise immediately on any failed TTS line — or (b) officially reverse the policy and document the degraded fallback as intentional with an explicit WARNING log and post-render quality gate that rejects silent segments. Option (a) is strongly preferred.

---

**N3 — Host normalization in `script_writer.py` structurally destroys dual-host design**
**Assessment: IMPLEMENT — P0**

Three separate normalization blocks (`script_writer.py:233–235`, `324–326`, `423–425`, plus validation at `689–691`) forcibly rewrite Host 1 to Host 2. This means the dual-host pipeline contract — which `tts_engine.py` is explicitly built around — can never be satisfied by the script writer. This is not a style issue; it is a product-breaking correctness failure. Remove all forced host normalization that collapses Host 1 to Host 2. Preserve the dual-host contract through all generation, validation, and serialization stages.

---

**N4 — `overnight_render_loop` startup checks reference the wrong file**
**Assessment: IMPLEMENT — P1**

`overnight_render_loop.py:131` and `216` check for `tts_local.py`. The actual implementation is `tts_engine.py`. This means local TTS readiness is permanently misdetected in production — the loop may refuse to use local TTS that is actually available, forcing unnecessary ElevenLabs calls and quota consumption, or it may falsely report readiness.

Fix: Update both path references to `tts_engine.py`. Add an integration test that validates the readiness check against the actual file structure.

---

**N5 — `run_render()` wipes global TTS cache every iteration**
**Assessment: IMPLEMENT — P1**

`overnight_render_loop.py:247` wipes the TTS cache on every render cycle. This defeats the entire purpose of caching: every run makes fresh ElevenLabs API calls, doubles (or more) quota consumption, and increases render time and failure probability. Cached audio is the primary resilience mechanism for API-rate failures.

Fix: Scope cache invalidation to per-episode artifact directories only, never to the shared TTS voice cache. Add a cache retention policy (e.g., 7-day TTL) rather than full wipe.

---

**N6 — `gemini_call()` leaks API key in URL query string**
**Assessment: IMPLEMENT — P0 (Security)**

`overnight_render_loop.py:234` passes the Gemini API key as a URL query parameter. This is also consistent with the production incident already recorded in the audit errors: `"Your API key was reported as leaked."` URL query parameters appear in:
- Application logs
- Proxy/CDN access logs
- Shell history
- Exception tracebacks
- HTTP Referer headers

Fix immediately:
```python
# BAD:
url = f"https://...?key={api_key}"

# GOOD:
headers = {"x-goog-api-key": api_key}
response = requests.post(url, headers=headers, json=payload)
```
Rotate the key immediately. Audit all logs for exposure. This finding also explains the leaked key incident recorded in the error metadata.

---

**N7 — `local_watchdog` executes arbitrary LLM-generated patches with no containment**
**Assessment: IMPLEMENT — P0 (Security — most critical in the package)**

`services/local_watchdog.py:398–404` asks a local LLM to generate a unified diff. `479–500` writes it to `/tmp/watchdog_patch.diff` and applies it with `patch -p0`. There is no:
- Path allowlist restricting which files the patch may touch
- Verification that the patch only modifies the `affected_file` extracted earlier
- Ban on file creation or deletion operations inside the diff
- Sandbox or chroot
- Human approval gate
- Meaningful rollback (only `git checkout -- affected_file`, but the patch may have touched multiple files)

This is autonomous LLM-driven code execution on a production system with no meaningful containment. A sufficiently adversarial or hallucinated diff could modify any writable file on the system.

Fix:
```python
import pathlib

ALLOWED_PATCH_ROOTS = [
    pathlib.Path("~/protocol_pulse/video_pipeline_v3").expanduser(),
    pathlib.Path("~/protocol_pulse/services").expanduser(),
]

def _validate_patch_safety(diff_text: str, expected_file: str) -> bool:
    """Reject any diff that touches files outside the allowlist."""
    for line in diff_text.splitlines():
        if line.startswith(("--- ", "+++ ")):
            target = pathlib.Path(line.split(None, 1)[-1].strip())
            if not any(
                target.resolve().is_relative_to(root)
                for root in ALLOWED_PATCH_ROOTS
            ):
                log.error(f"PATCH_SECURITY_VIOLATION: {target} outside allowlist")
                return False
    return True

# Before applying:
if not _validate_patch_safety(diff_text, affected_file):
    raise SecurityError("Patch targets disallowed path — aborting")
```
Additionally: require human approval in non-autonomous mode, enforce `--dry-run` first, and expand rollback to full `git stash` rather than single-file checkout.

---

**N8 — `local_watchdog` JSON extraction from Ollama uses broken regex**
**Assessment: INVESTIGATE — P2**

`services/local_watchdog.py:421–428` uses `\{[^{}]*"diagnosis"[^}]*\}` to extract JSON from Ollama output. This regex cannot handle nested JSON objects or escaped braces, which are common in diffs. Depending on how Ollama formats its response, this will either fail to extract (false negative — no patch applied) or extract a partial/incorrect object (potentially incorrect patch applied).

Fix: Use a JSON stream parser or find-first-valid-JSON approach:
```python
import json, re

def extract_first_json(text: str) -> dict | None:
    decoder = json.JSONDecoder()
    for match in re.finditer(r'\{', text):
        try:
            obj, _ = decoder.raw_decode(text, match.start())
            if "diagnosis" in obj:
                return obj
        except json.JSONDecodeError:
            continue
    return None
```

---

**N10 — Clip selector records episode memory even when clip count is below minimum**
**Assessment: IMPLEMENT — P2**

`clip_selector.py:600–601` records video IDs as "used" even when the selection produced fewer clips than required. On the next run, those degraded-selection IDs are excluded, narrowing the already-insufficient pool further. Over multiple runs, this produces an accelerating depletion spiral.

Fix: Only record episode memory when the selection meets or exceeds the minimum required clip count. On degraded selections, emit a WARNING and skip memory recording, or record with a `degraded=True` flag that uses a shorter exclusion TTL.

---

### From Grok (not raised by GPT-4o):

**Montage producer lacks granular logging for validation/duration steps**
**Assessment: INVESTIGATE — P2**

`montage_producer.py:161–206` validation and duration-fitting failures are logged as errors but not escalated. Agree this warrants adding structured metric emission (e.g., `montage.clips_rejected_count`) so monitoring can alert on degraded montage quality. Lower priority than the P0/P1 items above but worthwhile.

---

## CONFLICTS
*Areas where models gave different or contradictory assessments.*

### Conflict 1 — ElevenLabs retry/backoff: Grok says "unthrottled," GPT-4o says "already has retries"

**Grok's position:** ElevenLabs calls in `tts_engine.py:1116` are unthrottled with no backoff.

**GPT-4o's position:** `tts_engine.py:1112–1140` already has retries and exponential backoff; the finding is overstated.

**Tiebreaker — GPT-4o is correct on the specific ElevenLabs point.**
The ElevenLabs client path in `tts_engine.py` appears to have retry/backoff already implemented. The valid gap is in `gemini_call()` and Ollama calls, which both models agree lack retry logic. The overall U2 finding stands and should be implemented, but the scope should be scoped correctly: the ElevenLabs path does not need retry added — the other external call sites do. Do not duplicate retry logic where it already exists correctly.

**Resolution:** Accept GPT-4o's scoping. Remove ElevenLabs from the remediation target for U2. Focus U2 fixes on `gemini_call()`, Ollama, and yt-dlp paths only.

---

### Conflict 2 — Severity framing of host normalization (N3)

**Grok's framing:** Host normalization "might" break dual-host format — moderate concern.

**GPT-4o's framing:** This is structurally impossible to work around — product-breaking P0.

**Tiebreaker — GPT-4o is correct.**
If three separate code locations independently force Host 1 → Host 2, and `tts_engine.py` is built for dual-host output with different voice models per host, then the script writer can never produce dual-host compliant output regardless of prompt engineering. The downstream voice assignment will be systematically wrong. This is a P0 product correctness failure, not a style concern.

---

## VALIDATED STRENGTHS
*Both models confirm these areas are well-implemented. Do NOT modify in the second pass.*

1. **ElevenLabs retry/backoff in `tts_engine.py:1112–1140`** — Already correctly implemented with retries and exponential backoff. Leave as-is.

2. **TTS hard-fail policy declaration (`tts_engine.py:763–774`)** — The policy itself is correct and appropriate. The problem is the implementation violating it (N2), not the policy. Preserve the policy; fix the implementation to actually enforce it.

3. **yt-dlp timeout handling in `clip_extractor.py`** — Basic timeout exists and is better than nothing. Needs jitter/retry (U2) but the timeout floor should be preserved.

4. **Clip selection priority logic for breaking news and hot takes** — The ranking algorithm's core priority ordering is architecturally sound. Only the rank-integrity maintenance after reordering passes needs fixing (M3); the underlying scoring logic is appropriate.

---

## LAW COMPLIANCE CONSENSUS

### Fully Compliant (no evidence of violation):
- Internal episode format rules (PBX opens, dual-host structure) — *with the caveat that N3 breaks this in implementation*
- Basic content deduplication via `used_clips.json`

### Gaps / Potential Violations:

**Copyright / Fair Use (MEDIUM risk):**
Both models noted yt-dlp is used to download and clip third-party video content. The codebase contains no DMCA takedown handler, no license verification before clipping, and no rights-clearance check. Producing a commercial or publicly distributed show from clipped third-party content without a licensing framework creates meaningful copyright exposure. **Recommended:** Add a rights-check annotation field to the clip selection metadata and document the fair use basis for each clip category. Consult legal counsel before production deployment.

**Data Retention / Privacy (LOW-MEDIUM risk):**
`used_clips.json` and `narrative_context.json` accumulate indefinitely (pruning logic exists but has the concurrency bug). If any personally identifiable information enters the narrative context (e.g., social post author handles), it must be subject to retention limits under applicable data protection regulations. **Recommended:** Audit what data persists in state files; apply explicit TTL-based purging.

**API Terms of Service (HIGH risk — operational, not legal):**
The leaked Gemini API key (`overnight_render_loop.py:234`) is already generating a production error. Using a leaked/compromised key may violate Google's TOS and could result in account suspension. **Action required immediately:** Rotate key, fix URL query string exposure (N6).

---

## SECURITY CONSENSUS

Priority order (highest risk first):

| # | Finding | Severity | File/Line |
|---|---|---|---|
| 1 | LLM-generated patches applied with no path containment | **CRITICAL** | `local_watchdog.py:479–500` |
| 2 | API key leaked via URL query string (confirmed production incident) | **CRITICAL** | `overnight_render_loop.py:234` |
| 3 | No singleton guard — concurrent render processes corrupt shared state | **HIGH** | `overnight_render_loop.py:548–552` |
| 4 | Race conditions on all shared JSON state files | **HIGH** | Multiple files |
| 5 | Brittle JSON extraction in watchdog can misparse patch objects | **MEDIUM** | `local_watchdog.py:421–428` |
| 6 | No audit log for autonomous patch applications | **MEDIUM** | `local_watchdog.py` |

---

---

# WINNER DETERMINATION

# WINNER: GPT-4o

GPT-4o provided the highest-quality analysis overall. While Grok produced more verbose output, GPT-4o demonstrated superior **accuracy** (its findings were confirmed and cited with precise line numbers in the consensus), greater **depth** (it independently identified nuanced distinctions like "partially agree" on U2 rather than blanket endorsement, flagging which specific call sites actually lacked backoff versus which had partial handling), and stronger **actionability** (its recommendations were grounded in exact file/line citations like `clip_selector.py:102–110`, `overnight_render_loop.py:548–552`, and `services/local_watchdog.py` rather than reconstructed assumptions). Grok's Cycle 2 output was self-admittedly operating without its own Cycle 1 baseline and was partially reconstructed, which undermines its reliability as a comparative auditor.

---

# FINAL SECOND-PASS PRIORITY LIST

*Definitive ordered implementation list. P0 = deploy blocker. P1 = production stability. P2 = quality/compliance. P3 = hardening.*

---

## P0 — DEPLOY BLOCKERS (Fix before any production run)

**P0-A | Leaked API Key in Failed Gemini Run**
- The consensus report explicitly notes a leaked API key caused a `403 PERMISSION_DENIED` on Gemini 2.5 Pro
- **Action:** Rotate the key immediately. Audit all config files, `.env`, logs, and git history (`git log -S "key_string"`) for exposure. Add `detect-secrets` or `truffleHog` to pre-commit hooks. Never pass raw API keys through audit tooling pipelines.

**P0-B | LLM-Generated Code Executed Without Sandboxing**
- `local_watchdog.py` — autonomous repair loop executes LLM-suggested patches directly
- **Action:** Gate all LLM patch execution behind a human-approval step or at minimum a `subprocess` sandbox with restricted filesystem/network access, a timeout, and a rollback checkpoint. Log every execution with the full prompt, response, and diff before apply.

**P0-C | Wrong Output File Path Corrupts Episode**
- `N4` — confirmed production path mismatch causes silent write to wrong location
- **Action:** Resolve the correct canonical output path. Add a post-write assertion that verifies the file exists at the expected destination with nonzero size before the pipeline marks the step complete.

**P0-D | Cache Wipe Destroys Valid State**
- `N5` — cache invalidation logic wipes valid clips/state under recoverable error conditions
- **Action:** Replace destructive cache clears with a rename-to-quarantine pattern (`mv cache/ cache.bak.{timestamp}/`). Never delete state that cannot be cheaply regenerated. Add a `--force-clear` flag for intentional manual wipes only.

---

## P1 — PRODUCTION STABILITY (Fix before sustained autonomous operation)

**P1-A | No File Locking on Shared JSON State** *(U1 — Unanimous)*
- `clip_selector.py:102–110` (`_load_used_clips`)
- `clip_selector.py:161–176` (`_record_episode`)
- `script_writer.py:265–286` (`narrative_context.json`)
- `overnight_render_loop.py` — `write_heartbeat()`
- `services/local_watchdog.py` — `/tmp` patch counters
- **Action:** Wrap all read-modify-write cycles with `fcntl.flock()` (Unix) or `msvcrt.locking()` (Windows), or migrate to SQLite with WAL mode for all shared mutable state. Use atomic rename (`os.replace()`) for all final writes.

**P1-B | No Singleton Guard on Daemon/Loop Processes** *(U consensus)*
- `overnight_render_loop.py:548–552`
- **Action:** Implement a pidfile lock at startup (`/var/run/protocol_pulse.pid` or equivalent). On startup, check if PID in file is alive; if yes, exit immediately with a clear log message. Clean up pidfile on graceful exit and via `atexit` handler.

**P1-C | Silent Exception Swallowing Changes System Behavior** *(U3 — Unanimous)*
- `script_writer.py:701–706`
- `clip_selector.py:384–388, 609–611`
- `tts_engine.py:772`
- **Action:** Replace bare `except: return []` / `return ""` patterns with structured logging at `ERROR` level including full traceback (`logger.exception()`), then either re-raise or return a typed failure object that callers must explicitly handle. Never silently return empty results for failures that affect output correctness.

**P1-D | Unthrottled External API Calls Without Backoff** *(U2 — Unanimous, partial)*
- `overnight_render_loop.py:231–242` — `gemini_call()` no retry
- `local_watchdog.py` — Ollama calls no retry
- `clip_extractor.py` — yt-dlp paths, timeout present but no jitter/retry
- `tts_engine.py:1116` — ElevenLabs
- **Action:** Implement `tenacity`-based retry with exponential backoff and jitter on all external I/O. Apply per-service: ElevenLabs (3 retries, 2s base, 60s max), Gemini (3 retries, 1s base, 30s max), yt-dlp (2 retries, 5s base). Log each retry attempt with attempt number and wait duration.

---

## P2 — QUALITY AND COMPLIANCE (Fix within one sprint)

**P2-A | Clip Diversity Enforcement May Drop Highest-Ranked Content**
- `clip_selector.py:404–420` — channel deduplication silently demotes high-priority clips
- **Action:** Apply diversity enforcement as a post-ranking filter with a logged warning when a higher-ranked clip is dropped. Expose `--no-diversity-cap` flag for operator override. Ensure the selection log records both the pre- and post-diversity clip lists.

**P2-B | Host Voice Normalization Contradicts Dual-Host Format**
- `script_writer.py:235, 325, 424` — forced normalization to PBX breaks alternation logic
- **Action:** Audit all host assignment code paths. Remove or conditionalize the forced PBX normalization. Add a unit test that asserts at least two distinct host voices appear in any generated script longer than two segments.

**P2-C | Script Generation Race on `narrative_context.json`**
- `script_writer.py:270` — concurrent script runs overwrite shared narrative context
- **Action:** This is partially addressed by P1-A (file locking), but additionally add a per-run UUID to narrative context writes and validate that the UUID read at step N+1 matches what step N wrote before proceeding.

**P2-D | Missing Fallback When No Clips Are Available**
- `clip_selector.py:370` — returns empty list with no retry or fallback source
- **Action:** Add a fallback clip source (e.g., a curated evergreen pool) triggered when the primary selection returns fewer than `MIN_CLIPS` results. Log a `WARNING` with clip count and trigger reason.

---

## P3 — HARDENING (Schedule within 30 days)

**P3-A | Add Pre-Commit Secret Scanning**
- Integrate `detect-secrets` or `gitleaks` into CI. Scan git history retroactively with `truffleHog --regex --entropy`.

**P3-B | Add Integration Test for Full Pipeline Run**
- No end-to-end test exists that exercises clip selection → script → TTS → assembly with mock external APIs. Add one using `pytest` + `responses` library for API mocking.

**P3-C | Structured Logging and Alerting**
- Replace print/ad-hoc logging with structured JSON logs (`python-json-logger`). Route `ERROR` and above to a dead-letter queue or alerting webhook (PagerDuty, Slack) so silent failures surface operationally.

**P3-D | Dependency and Supply Chain Audit**
- Pin all dependencies with hashes in `requirements.txt`. Run `pip-