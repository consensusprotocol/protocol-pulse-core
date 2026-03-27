# CONSENSUS REPORT — FIX-SILENCE-GAPS — CYCLE 2
Generated: 2026-03-22 16:24
Models: gpt4o, grok (+1 failed: gemini 403 PERMISSION_DENIED — leaked key)

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Backend Logic | N/A | 50 | 60 | **52** |
| Error Handling | N/A | 35 | ~45 (est.) | **38** |
| Security | N/A | 43 | ~40 (est.) | **41** |
| Performance | N/A | 42 | ~45 (est.) | **43** |
| Law Compliance | N/A | 65 | ~60 (est.) | **62** |
| **Overall** | N/A | **47** | **~52 (est.)** | **49** |

> **Note:** Grok did not provide Cycle 1 baseline scores in its Cycle 2 output; estimates are inferred from its narrative. Gemini excluded entirely due to API key failure. Consensus scores weighted between the two functioning models. A score of 49/100 overall is a hard fail for production deployment.

---

## UNANIMOUS FINDINGS
*(Both models agree — implement unconditionally)*

### U1 — Silence Fallback Directly Contradicts Hard-Fail Policy
- **What it is:** `_tts_generate_silence_fallback()` (lines 756–767) intentionally raises an exception to enforce a no-silent-render policy. But `generate_dialogue_audio()` catches the failure and writes 3 seconds of synthetic silence anyway (lines 1259–1267). The guard is completely bypassed.
- **File/Lines:** `video_pipeline_v3/tts_engine.py`, lines 756–767 and 1259–1267
- **What to change:** Remove the silence-write block entirely from lines 1259–1267. On TTS failure, raise a descriptive exception with the host number and line index, and let the caller decide to retry or abort. Do not produce audio outputs that silently misrepresent TTS failures.

### U2 — Cache Writes Are Not Atomic and Not Concurrency-Safe
- **What it is:** `_tts_cache_get` and `_tts_cache_put` (lines 729–754) perform read and write operations on cache files without locks or atomic replacement. Concurrent requests hitting the same cache key can produce corrupt audio files that persist and poison future cache reads.
- **File/Lines:** `video_pipeline_v3/tts_engine.py`, lines 729–754
- **What to change:** Write cache content to a uniquely named temp file (e.g., using `tempfile.NamedTemporaryFile` with `delete=False`), then use `os.replace()` to atomically rename it into the final cache path. Add a file lock (e.g., `fcntl.flock` or `threading.Lock` keyed by cache path) around the read-check-write sequence.

### U3 — FFmpeg Subprocess Return Codes Are Systematically Ignored
- **What it is:** Multiple `subprocess.run()` / `subprocess.call()` invocations for ffmpeg concatenation and conversion do not check return codes. A failed concat silently produces a missing or zero-byte output file. Downstream code then either crashes with an unhelpful error or, worse, proceeds with bad state.
- **File/Lines:** `video_pipeline_v3/tts_engine.py`, lines 225–235, 249–256, 690–718, 795–804, 837–848, 893–904, 1164–1169, 1294–1309
- **What to change:** For every `subprocess.run()` call involving ffmpeg or ffprobe: check `returncode != 0`, capture `stderr`, log the full ffmpeg stderr output, and raise a `RuntimeError` with the command, return code, and stderr. Do not continue if media operations fail.

### U4 — Per-Host Success Accounting Is Structurally Invalid
- **What it is:** The host validation block (lines 1316–1339) determines success by checking whether a file path exists (`os.path.exists(l["path"])`). Because failed lines are replaced with synthetic silence files (see U1), those files exist, so they pass the check. A host where every single line failed TTS will be reported as fully successful.
- **File/Lines:** `video_pipeline_v3/tts_engine.py`, lines 1316–1339
- **What to change:** Track TTS success explicitly per line at generation time using a boolean flag stored alongside the path. Count `host_stats["ok"]` only for lines where the flag is `True` (genuine synthesis), not inferred from file existence.

### U5 — Preflight Validation Does Not Cover Host 2's Actual Runtime Path
- **What it is:** `tts_preflight_local()` validates the Kokoro host 1 path (lines 974–980) and logs F5 status, but does not validate the `am_onyx` host 2 voice that is actually used at runtime (lines 180, 203–207). Preflight can pass green while host 2 is completely broken. Additionally, comments still reference `am_adam` (line 990) when the implementation uses `am_onyx`.
- **File/Lines:** `video_pipeline_v3/tts_engine.py`, lines 180, 203–207, 969–993
- **What to change:** Add explicit preflight synthesis for host 2's actual configured voice. Remove all references to `am_adam` in comments that do not match the live configuration. Fail preflight if either host 1 or host 2 is non-functional.

---

## MAJORITY FINDINGS
*(2 of 2 models agree — implement unless compelling reason not to)*

All unanimous findings above are also majority findings. Additional majority items below:

### M1 — `dur` Variable Can Be Unbound at Runtime
- **What it is:** In the per-line processing loop, `dur` is assigned only in the success branch (line 1255). If `_tts_ok` is True, the file exists and size is acceptable, but `len(text) <= 10` skips the duration-check block, `dur` may be referenced at lines 1272 and 1279 without ever being assigned. This is a latent crash on any short valid line ("Yes.", "OK.", etc.).
- **File/Lines:** `video_pipeline_v3/tts_engine.py`, lines 1250–1279
- **What to change:** Initialize `dur = 0.0` before the TTS call block. After the call, assign `dur` unconditionally using ffprobe duration if the file exists and is valid. Remove the branch structure that allows `dur` to remain undefined.

### M2 — Predictable Temp File Naming Causes Collision Under Concurrency
- **What it is:** Intermediate files are named by appending suffixes to `output_path` (e.g., `output_path + ".kokoro.wav"`, `".cb.wav"`, `".f5.wav"`, `".chunkN.mp3"`, `".concat.txt"`). Two concurrent runs sharing or approximating the same output path will overwrite each other's temp files, producing corrupted audio with no error.
- **File/Lines:** `video_pipeline_v3/tts_engine.py`, lines 779, 826, 877, 1102, 1159–1160, 1290
- **What to change:** Replace all deterministic temp file paths with `tempfile.mktemp()` or `tempfile.NamedTemporaryFile(delete=False, suffix=".wav")` scoped to the operation. Clean up in a `finally` block regardless of success or failure.

### M3 — `sys.path` Mutation at Request Time Is Unsafe
- **What it is:** `tts_local()` appends to `sys.path` (lines 927–930) during what may be a per-request code path. In a multi-worker server, this mutates shared interpreter state, can cause import races, and introduces non-deterministic module resolution across concurrent requests.
- **File/Lines:** `video_pipeline_v3/tts_engine.py`, lines 926–933
- **What to change:** Move all `sys.path` modifications to module import time (top of file) or to application startup, behind a one-time guard (`if not already_patched`). Never mutate `sys.path` during request processing.

### M4 — Silence Gap Inserted Between Same-Speaker Consecutive Lines
- **What it is:** The feature spec and comments describe silence gaps as being between speakers. The implementation adds a 0.3s silence before every non-CLIP line regardless of whether the speaker changed (lines 1281–1285). If the intent is cross-speaker pacing, same-speaker gaps are wasteful and create unnatural pacing in monologue runs.
- **File/Lines:** `video_pipeline_v3/tts_engine.py`, lines 1281–1285
- **What to change:** Either (a) update the comment to accurately describe "between all adjacent spoken lines" if that is intended behavior, or (b) track `previous_host` and only insert the gap on host change. Choose and commit to one interpretation; do not leave spec and code in contradiction.

### M5 — ElevenLabs API Has No Application-Level Rate Limiting
- **What it is:** ElevenLabs calls (lines 1108–1134) rely on server-side rate limits to reject excessive requests. There is no client-side quota tracking, token bucket, or backoff governor. Under concurrent load (~1000 users), the application will exhaust quota and receive 429s en masse with no graceful degradation.
- **File/Lines:** `video_pipeline_v3/tts_engine.py`, lines 1108–1134
- **What to change:** Add a `threading.Semaphore` or token bucket (e.g., using `ratelimit` or a custom implementation) that caps concurrent ElevenLabs calls to a safe limit derived from your API tier. Log quota pressure events at WARN level.

---

## UNIQUE INSIGHTS
*(Single-model findings — evaluated individually)*

### GPT-4o Unique Findings

**G1 — `validate_tts_output()` Can Raise Despite Bool-Returning Caller Contract**
- **Assessment: IMPLEMENT**
- `tts_local()` and `tts_elevenlabs()` are used as boolean functions by callers but internally call `validate_tts_output()` which can raise `RuntimeError`. This creates an implicit dual interface (bool + exception) that callers are not prepared for. Standardize: either always raise on failure (and update all callers to use try/except) or always return bool and never raise from validation.

**G2 — Global Lazy Init Is Not Thread-Safe**
- **Assessment: IMPLEMENT**
- Model instantiation globals (lines 21–27, 215) are initialized on first access without locks. Two simultaneous first requests can double-initialize or race on model load. Use `threading.Lock` around init checks: `if not _kokoro_model: with _init_lock: if not _kokoro_model: _kokoro_model = load(...)`.

**G3 — Docstring Drift: Chatterbox Referenced as Active When Removed**
- **Assessment: IMPLEMENT (low effort, high operational value)**
- Multiple docstrings and comments reference Chatterbox as an active provider (lines 917–918, 203–207) when it appears to be unused or deprecated. Stale documentation causes false confidence during incident triage. Audit all provider references, remove or clearly mark deprecated paths.

**G4 — Provider Re-Read Inside Loop Can Mix Providers Mid-Dialogue**
- **Assessment: IMPLEMENT**
- GPT-4o caught that `_active_provider` is computed once at line 1199 but fetched again inside the per-line loop. If the environment variable changes during a run (edge case but possible in hot-reload environments), one dialogue could mix ElevenLabs and local TTS, producing inconsistent audio quality mid-episode. Use the precomputed value exclusively.

### Grok Unique Findings

**K1 — Temp File Cleanup Skipped on Early Failure**
- **Assessment: IMPLEMENT**
- Temporary concat list files and intermediate MP3s are cleaned up in the happy path (lines 1171–1175) but not on failure. Over time, failed runs accumulate orphaned temp files, creating disk pressure in production. Wrap temp file operations in `try/finally` to ensure cleanup always runs.

**K2 — Inconsistent Exception Logging in Validation Paths**
- **Assessment: IMPLEMENT**
- `tts_local()` raises `RuntimeError` from validation (line 960) without logging the underlying cause before raising. By the time the exception propagates, the original ffprobe output or silence-detection detail is lost. Log the full diagnostic before raising, not after catching at a higher level.

**K3 — CLIP Entry Timing Assumptions Undocumented**
- **Assessment: INVESTIGATE FURTHER**
- CLIP entries advance the timeline without producing audio (lines 1219–1231). This is only safe if downstream assemblers treat `lines` entries with no audio path as pure timeline markers. The contract is implicit and undocumented. If any downstream consumer iterates `lines` expecting audio for every entry, this silently breaks. Document the contract explicitly in the return type docstring, and add a `"type": "clip"` vs `"type": "audio"` discriminator to the returned line metadata.

**K4 — ffmpeg 90-Second Timeout Does Not Cover All Network Paths**
- **Assessment: INVESTIGATE FURTHER**
- The 90-second timeout on ElevenLabs (line 1110) is reasonable, but no timeout is set on ffmpeg subprocess calls. A hanging ffmpeg process (e.g., reading from a stalled network mount) can block the worker indefinitely. Add `timeout=` parameter to all `subprocess.run()` calls involving ffmpeg.

---

## NEW FINDINGS (identified during synthesis — not in either model's Cycle 1 or 2)

### S1 — FFmpeg Concat List File Does Not Escape Apostrophes in Paths
- **What it is:** The concat demuxer format requires `file '/path/to/file'`. Paths are written raw via `os.path.abspath(p)` (lines 1161–1163, 1291–1293). Any path containing `'` will produce a malformed concat list, causing ffmpeg to fail or silently skip files.
- **Severity:** P1 — affects any deployment where output paths include project names with apostrophes
- **Fix:** Escape single quotes in paths written to concat list: `path.replace("'", "'\\''")`

### S2 — `_generate_silence()` Return Value Is Ignored
- **What it is:** `_generate_silence()` returns a bool (lines 1207–1208), but the caller discards it. If silence file generation fails (ffmpeg error, disk full), the concat list will reference a non-existent file. This error is completely silent until ffmpeg fails at concat time with an unintelligible error.
- **Severity:** P1
- **Fix:** Check return value and raise immediately if silence generation fails: `if not _generate_silence(...): raise RuntimeError("Silence gap generation failed")`

### S3 — Preflight Uses Fixed Globally Shared Temp Path
- **What it is:** `tts_preflight_local()` writes to `/tmp/tts_preflight_local.m4a` (line 972). Concurrent preflights (e.g., multiple workers starting simultaneously) will write to the same file and produce race-corrupted validation results.
- **Severity:** P1
- **Fix:** Use `tempfile.NamedTemporaryFile()` for preflight output path.

### S4 — HuggingFace Download Subprocess Return Code Unchecked in `_init_kokoro()`
- **What it is:** `_init_kokoro()` runs a HuggingFace model download via subprocess (lines 49–55) and ignores the return code. If the download fails (network issue, auth failure, disk full), code proceeds to instantiate the ONNX model from missing files, producing a confusing downstream error instead of a clear "model download failed" message.
- **Severity:** P1
- **Fix:** Check subprocess return code, log stderr, and raise `RuntimeError("Kokoro model download failed")` before attempting ONNX instantiation.

---

## CONFLICTS
*(Models gave contradictory or meaningfully different assessments)*

### Conflict 1: Shell Injection Risk via TTS Text Input
- **Grok (Cycle 1):** Flagged unprintable Unicode and potentially malicious text as a shell injection risk passed to TTS engines.
- **GPT-4o (Cycle 2):** Explicitly disagreed — subprocess calls use argument lists, not shell strings, so text is not shell-interpolated. The real risk is concat list path escaping, not text injection.
- **Verdict: GPT-4o is correct.** Subprocess argument lists prevent shell injection from `text` content regardless of characters. Text sanitization is a robustness concern (preventing TTS engine crashes on invalid Unicode) not a security concern. The concat list path escaping (see S1) is the actual shell-adjacent risk and is legitimately P1. Do not conflate these.

### Conflict 2: Empty Dialogue List Handling
- **Grok:** Flagged empty dialogue as a bug — returns empty result without error, downstream may fail.
- **GPT-4o:** Did not explicitly flag this.
- **Verdict: Partially valid, but context-dependent.** An empty dialogue producing an empty result is only a bug if callers assume at least one line. The fix is documentation and a caller-side guard, not necessarily an exception here. Mark as P2: add an explicit early return with a logged warning if `len(dialogue) == 0`, and document that callers must handle empty results.

### Conflict 3: Severity of CLIP Entry Timing Gaps
- **GPT-4o:** Flagged as a timing discontinuity risk.
- **Grok:** Flagged as requiring documentation of the downstream contract.
- **Verdict: Both are right, Grok's framing is more actionable.** The code behavior may be intentional — the fix is contract documentation plus a metadata discriminator (`type: "clip"` vs `type: "audio"`), not necessarily changing the silence-gap behavior. Implement Grok's K3 recommendation.

---

## VALIDATED STRENGTHS
*(Both models agreed these areas are solid — do NOT touch in second pass)*

1. **ElevenLabs Retry Logic (lines 1108–1134):** The exponential backoff with jitter and 90-second timeout for ElevenLabs calls is well-structured. Both models acknowledged this without criticism. Leave as-is.

2. **Multi-Provider Fallback Chain Architecture:** The overall design of Kokoro → F5-TTS → ElevenLabs as a fallback chain is sound and flexible. The architecture is not the problem; the execution of individual steps within it is. Do not restructure the chain.

3. **Per-Line Output File Organization:** Writing individual line audio to named output paths indexed by line number is correct and traceable. The file naming convention for per-line outputs (excluding the collision-prone suffixes) is sensible.

4. **Silence Gap Duration (0.3s):** Neither model disputed the 0.3s silence gap as an audio design choice. The value is not the issue; the conditional logic around when to apply it is.

---

## LAW COMPLIANCE CONSENSUS

Both models scored law compliance highest relative to other subsystems (GPT-4o: 65, Grok: ~60). However, neither model had access to `PIPELINE_LAWS.md` to verify against Protocol Pulse's specific internal laws. The following is a best-effort determination:

| Concern | Status | Detail |
|---|---|---|
| Audio output integrity | **VIOLATED** | Hard-fail policy exists in law but is bypassed by silence fallback (U1) |
| Concurrent access safety | **VIOLATED** | No file locks on shared cache resources (U2) |
| Subprocess failure handling | **VIOLATED** | Return codes not checked (U3), likely a pipeline law requirement |
| Provider validation pre-flight | **VIOLATED** | Preflight does not cover host 2 runtime path (U5) |
| ElevenLabs usage / attribution | **LIKELY COMPLIANT** | API key check exists; no evidence of ToS violation in code |
| Audio content / copyright | **OUT OF SCOPE** | Cannot assess from engine code alone |

**Final determination:** This code is not law-compliant with its own stated hard-fail policy. Three or more pipeline laws appear to be violated at the implementation level.

---

## SECURITY CONSENSUS

Both models identified the following security concerns in priority order:

| Priority | Issue | Both Models? |
|---|---|---|
| P0 | Non-atomic cache writes — cache poisoning via race condition | Yes (U2) |
| P0 | `sys.path` mutation at request time — import hijacking risk in shared environments | Yes (M3) |
| P1 | Predictable temp file names — TOCTOU and collision attacks | Yes (M2) |
| P1 | Global lazy model init without locks — resource exhaustion via init race | Yes (G2) |
| P2 | No rate limiting on ElevenLabs — quota exhaustion as denial-of-service | Yes (M5) |
| P2 | Concat list path not escaped — malformed paths on apostrophe input | GPT-4o + synthesis (S1) |
| P3 | TTS text not sanitized — engine crash on malformed Unicode (robustness, not injection) | Grok only |

**Security summary:** No evidence of credential leakage or outbound data exfiltration. Primary security surface is internal: shared mutable state under concurrency, predictable file paths, and cache integrity. These are all fixable without architectural change.

---

## WORLD-CLASS GAP CONSENSUS
*(Items 2+ models mentioned as missing from a truly world-class product)*

1. **Observability / Structured Logging for TTS Failures** — Both models noted that failures are logged inconsistently or not at all before being swallowed. A world-class system emits structured JSON logs per TTS attempt: `{line_index, host, provider, success, duration_ms, fallback_triggered, error}`. This is the minimum for production incident response.

2. **Atomic, Verifiable Audio Output Contracts** — Both models identified that the return value of `generate_dialogue_audio()` cannot be trusted (file existence ≠ TTS success, `full=None` is possible without exception). A world-class system returns a typed result object with explicit validity state, not an implicit success-by-file-existence assumption.

3. **Concurrency-Safe Resource Management** — Both models converged on the absence of any locking or isolation across cache, temp files, globals, and preflight paths. A world-class TTS engine either runs in an isolated process per request or uses explicit resource ownership boundaries. Neither exists here.

4. **Contract-Documented Return Types** — Both models noted that the `lines` list mixes audio entries and CLIP timeline markers without a type discriminator. A world-class API makes this explicit in the return schema, enabling downstream consumers to be written defensively without reading the engine source code.

---

## FINAL ACTION PLAN

### P0 CRITICAL

| # | Change | File:Line | Models | Why |
|---|---|---|---|---|
| P0-1 | Remove synthetic silence write on TTS failure; raise exception instead | `tts_engine.py:1259–1267` | Both | Directly violates hard-fail policy; produces corrupt renders that pass all downstream checks |
| P0-2 | Make cache writes atomic using temp file + `os.replace()` + file lock | `tts_engine.py:729–754` | Both | Cache corruption under concurrency poisons future runs irreversibly |
| P0-3 | Check all ffmpeg/ffprobe subprocess return codes; raise on non-zero with stderr | `tts_engine.py:225–235, 249–256, 690–718, 795–804, 837–848, 893–904, 1164–1169, 1294–1309` | Both | Silent media operation failures propagate to corrupt final output |
| P0-4 | Fix per-host success accounting to track actual synthesis success, not file existence | `tts_engine.py:1316–1339` | Both | Quality guard is structurally invalid; all-silence host passes as healthy |
| P0-5 | Initialize `dur = 0.0` before branching; assign unconditionally after TTS call | `tts_engine.py:1250–1279` | Both | Latent `UnboundLocalError` crash on any short valid text line |

### P1 HIGH

| # | Change | File:Line | Models

---

# WINNER DETERMINATION

# WINNER: GPT-4o

GPT-4o delivered the highest-quality analysis across both cycles. In Cycle 1 it identified the most structurally significant bugs first — the silence-fallback policy contradiction, the incomplete preflight for host2, and the comment/config drift — with precise line citations and clear causal chains explaining *why* each issue would fail in production, not merely *that* it would fail. In Cycle 2 it validated its own prior findings, explicitly credited and integrated findings from the other model, and added the `dur` unbound-variable bug and the invalid per-host success accounting, both of which are correctness issues Grok either missed or underweighted. Its recommendations were consistently specific enough to implement directly (remove lines 1259–1267, raise with host number and line index, replace file-existence check with a TTS-success flag) rather than describing problems at a category level. Grok's analysis was substantive and scored slightly higher on backend logic in the consensus, but its Cycle 2 output spent significant space reconstructing what it assumed it had said in Cycle 1 rather than advancing the analysis, and several of its recommendations remained at the pattern level without actionable specifics.

---

# FINAL SECOND-PASS PRIORITY LIST

Ordered by: production risk first, then correctness, then reliability, then hygiene. Each item is self-contained and implementable independently.

---

## P0 — BLOCKS DEPLOYMENT (fix before any production traffic)

**P0-1 — Remove silence-write fallback in `generate_dialogue_audio()` (lines 1259–1267)**
The no-silent-render policy enforced by `_tts_generate_silence_fallback()` is completely bypassed here. Delete the silence-write block. On TTS failure, raise `TTSLineFailure(host=host_num, line_index=i, reason=...)` and let the caller abort or retry. A render that silently replaces failed lines with synthetic silence is worse than a render that crashes, because the crash is visible.

**P0-2 — Make ffmpeg subprocess calls check return codes everywhere (lines 226–235, 1164–1168, 1294–1298)**
All ffmpeg calls must capture return code and stderr. On non-zero exit, raise immediately with the captured stderr. The current pattern allows a failed concat to produce a zero-byte or truncated file that passes all downstream checks and ships to users.

**P0-3 — Fix `dur` potentially unbound before use (lines 1255–1272)**
`dur` is only assigned inside conditional branches. If `_tts_ok` is true, the file exists, size passes, and `len(text) <= 10`, `dur` is never set before line 1272 reads it. Assign a safe default (`dur = 0.0`) before the branch block and assert it is overwritten before use, or restructure so all paths assign it explicitly.

**P0-4 — Fix per-host success accounting to track TTS success, not file existence (lines 1316–1339)**
`host_stats["ok"]` is incremented when a file exists, but failed lines are replaced with silence files that also exist. The guard therefore passes when a host is entirely silence. Replace the file-existence check with a success flag set only when actual TTS output is confirmed, tracked per line in the metadata dict.

---

## P1 — HIGH RISK (fix within one sprint, before scaling)

**P1-1 — Make cache writes atomic and add file-level locking (`_tts_cache_get` / `_tts_cache_put`, lines 729–754)**
Write to a `.tmp` file in the same directory, then `os.replace()` to the final path. Wrap with a per-key `threading.Lock` or a file lock (e.g., `fcntl.flock`) so concurrent requests on the same cache key cannot interleave writes. A corrupted cache entry persists and poisons every subsequent request for that key.

**P1-2 — Move `sys.path` mutation out of `tts_local()` request path (lines 927–930)**
`sys.path` is global interpreter state. Mutating it inside a per-request function in a multi-threaded server is a data race. Move all path setup to module import time or application startup. If the dependency truly requires dynamic path insertion, isolate it in a subprocess.

**P1-3 — Complete preflight validation for host2 actual runtime path (`tts_preflight_local()`, lines 974–990)**
Preflight currently validates only host1 Kokoro. Host2's production path (`am_onyx` → F5 → ElevenLabs fallback) is not validated. Preflight can pass while host2 is completely broken. Add explicit validation for each step of the host2 fallback chain and fail loudly if any required resource is missing.

**P1-4 — Resolve config/comment drift: `am_adam` vs `am_onyx` (lines 180, 990)**
The preflight warning and at least one docstring still reference `am_adam` while the implementation uses `am_onyx`. This is not cosmetic — it indicates the code path and the operational runbook are out of sync. Audit every reference to voice model names, canonicalize to a single config constant, and remove all hardcoded strings.

---

## P2 — MEDIUM RISK (fix within two sprints)

**P2-1 — Clarify and enforce silence-gap insertion semantics (lines 1281–1285)**
The feature is named `fix-silence-gaps` and comments say gaps are inserted "between speakers," but the implementation inserts a gap between *all adjacent spoken lines* including same-host consecutive lines. Either change the implementation to match the comment (only insert gap on host change) or change the comment to match the implementation. Document the decision explicitly because downstream timing calculations depend on it.

**P2-2 — Handle CLIP timing discontinuities (lines 1218–1231)**
CLIP entries advance the timeline but generate no audio and receive no silence gap. If the downstream assembler expects a continuous audio timeline aligned to `current_time`, gaps will appear at every CLIP boundary. Either generate a correctly-sized silence segment for CLIP duration to maintain timeline continuity, or document that the assembler is responsible for filling CLIP segments and add an assertion verifying that contract.

**P2-3 — Handle `full_path = None` explicitly after concat failure (line 1343)**
Even with the ffmpeg return-code fix (P0-2), the metadata return path should assert `full_path is not None` before returning. Returning a result dict with `full_path=None` to a caller that does not check it produces a delayed, untraceable crash. Fail fast here with a clear exception.

**P2-4 — Log original TTS failure cause before any fallback action**
Across the codebase, fallback paths (silence writes, provider switches) execute without preserving the original exception. The root cause is lost by the time the render fails downstream. At every fallback branch, log `exc_info=True` with host number, line index, provider name, and text length before taking any fallback action.

---

## P3 — LOW RISK / HYGIENE (fix in background or next major refactor)

**P3-1 — Add integration test: TTS failure must propagate, not produce silence**
The P0-1 fix will be regressed the first time someone adds a "helpful" try/except. Write an integration test that injects a TTS failure and asserts the pipeline raises rather than producing audio output.

**P3-2 — Add integration test: concurrent cache writes do not produce corrupt files**
Spin up N threads hitting the same cache key simultaneously and assert the resulting cached file is valid audio. This is the only reliable regression guard for P1-1.

**P3-3 — Extract all magic numbers to named constants**
`0.3` (silence gap duration), `3` (fallback silence duration), `10` (short-text threshold) appear as literals. Name them (`INTER_LINE_GAP_S`, `FALLBACK_SILENCE_S`, `SHORT_TEXT_CHAR_LIMIT`) and place them in a single config block at module top.

**P3-4 — Add Gemini to the audit pipeline with a non-leaked key**
The consensus report lost one of three auditors to a leaked API key. A three-model audit with a tiebreaker is materially more reliable than a two-model audit. Rotate the key, store it in the secrets manager, and re-run Gemini on the next cycle.