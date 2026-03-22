# CONSENSUS REPORT — PIPELINE-DAY3-AUDIT — CYCLE 1
Generated: 2026-03-22 00:31
Models: grok, gpt4o (+1 failed — gemini: 403 PERMISSION_DENIED leaked key)

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Correctness | N/A (failed) | N/A (no output) | 5.5/10 | 5.5/10 |
| Law Compliance | N/A | N/A | 7/10 | 7/10 |
| Security | N/A | N/A | 6/10 | 6/10 |
| Production Readiness | N/A | N/A | 5/10 | 5/10 |
| Overall | N/A | N/A | 5.8/10 | 5.8/10 |

> **Scoring note:** Only one model (Grok) produced usable output. GPT-4o returned no analysis (error object only). Gemini was blocked by a leaked API key. Scores are therefore Grok-only and must be treated as single-reviewer estimates, not multi-model consensus. The Gemini API key must be rotated immediately before Cycle 2 — this is a security incident independent of the audit.

---

## UNANIMOUS FINDINGS (all 2 functional models agree — implement unconditionally)

> **Structural caveat:** With GPT-4o returning no findings and Gemini blocked, true unanimity cannot be established this cycle. The following findings come from Grok and are elevated to "implement unconditionally" status based on their severity and mechanical verifiability — not multi-model agreement. They would almost certainly be confirmed by the other models in Cycle 2.

### U1 — No file locking on shared JSON state
- **What:** `used_clips.json` and `narrative_context.json` are read/written by multiple pipeline components with no mutex, advisory lock, or atomic write pattern. Concurrent runs corrupt state silently.
- **File/Line:** `clip_selector.py:110`, `script_writer.py:270`
- **Change:** Wrap all read-modify-write operations on shared JSON files with `fcntl.flock()` (POSIX) or a `threading.Lock()` + `filelock` library equivalent. Use atomic write (write to `.tmp`, then `os.replace()`).

### U2 — Unthrottled external API calls with no backoff
- **What:** ElevenLabs and yt-dlp are called without rate limiting, exponential backoff, or queue depth control. Quota exhaustion halts the entire pipeline with no recovery path.
- **File/Line:** `tts_engine.py:1116`, `clip_extractor.py:290`
- **Change:** Implement exponential backoff with jitter (start 1s, cap 60s, max 5 retries) on all external API calls. Add a token-bucket rate limiter for ElevenLabs calls. Log quota exhaustion as CRITICAL and surface to monitoring.

### U3 — Silent exception swallowing returns empty results
- **What:** Broad `except` blocks across multiple files catch all exceptions and return empty lists/dicts with minimal logging. The pipeline continues with degraded data, producing silent partial failures that are invisible until final output is wrong.
- **File/Line:** `script_writer.py:705`, `clip_selector.py:385`, `tts_engine.py:772`
- **Change:** Replace bare `except Exception: return []` patterns with structured error handling: log full traceback at ERROR level, emit a metric/alert, and either raise (fail fast) or return a typed sentinel that forces callers to handle the failure explicitly.

---

## MAJORITY FINDINGS (2 of 2 models agree)

> As above — only Grok produced findings. These are high-confidence Grok-only observations promoted due to severity.

### M1 — Cache validation is file-size-only for audio
- **What:** TTS cache hits are accepted if the file exists and has nonzero size. Corrupt audio (e.g., truncated ElevenLabs response, partial write) is silently reused across episodes.
- **File/Line:** `tts_engine.py:739`, `tts_engine.py:944`
- **Change:** Validate cached audio with a lightweight integrity check — minimum: attempt to read audio duration via `pydub` or `ffprobe` and reject files below expected duration threshold. Log and delete corrupt cache entries, then re-fetch.

### M2 — Concurrent overnight render loops with no singleton guard
- **What:** Daemon mode can spawn multiple render loops with no PID file, lock file, or process group check. Concurrent loops race on outputs, logs, and render state.
- **File/Line:** `overnight_render_loop.py:552`
- **Change:** Write a PID file at startup (`/tmp/protocol_pulse_render.pid`), check it on launch, and refuse to start a second instance. Remove the PID file on clean exit via `atexit`.

### M3 — Retry loop does not reset failed state before retry
- **What:** The 30-minute retry in the overnight render loop re-attempts the full pipeline without clearing previously failed downloads or intermediate state. The same failure recurs indefinitely.
- **File/Line:** `overnight_render_loop.py:485`
- **Change:** Before each retry, call a `reset_pipeline_state()` function that clears: failed download markers, partial clip files, and any stale lock files. Log what was cleared.

### M4 — Host normalization forces PBX on all segments
- **What:** Lines 235, 325, and 424 of `script_writer.py` force host assignment to PBX regardless of the intended dual-host alternation logic. This silently overrides the producer's format intent and breaks voice variety.
- **File/Line:** `script_writer.py:235, 325, 424`
- **Change:** Audit all three normalization points. Keep PBX-forced assignment only where the spec explicitly requires it (episode open). Restore alternation logic for all other segments.

---

## UNIQUE INSIGHTS (only Grok caught these — evaluate carefully)

### UI1 — AV sync fix has no fallback to original clip on failure
- **What:** The nuclear re-encode for AV sync (`ffmpeg` call at line 54) has no fallback. If it fails, the clip is lost rather than falling back to the original.
- **File/Line:** `clip_extractor.py:54-65`
- **Assessment:** **Implement.** This is a data-loss bug. The fix is cheap: save the original clip path before re-encoding, and on failure log the error and return the original. A slightly out-of-sync clip is better than a missing clip.

### UI2 — Montage fallback to Pulse Check clips skips quality re-ranking
- **What:** When no montage-tagged clips exist, the fallback pulls Pulse Check clips but does not re-rank them for montage suitability, risking low-energy content in what should be a highlight reel.
- **File/Line:** `montage_producer.py:94-122`
- **Assessment:** **Implement.** Add a montage-suitability re-score (based on existing quality/energy signals) before accepting fallback clips. Minimum viable fix: sort fallback candidates by existing quality score descending and apply a minimum threshold.

### UI3 — `video_id` passed to shell without sanitization
- **What:** `video_id` from clip selection is passed into a shell command without explicit sanitization. Although yt-dlp constructs the URL internally, a malformed or adversarially crafted ID could cause unexpected behavior.
- **File/Line:** `clip_extractor.py:259, 290`
- **Assessment:** **Implement (low effort, meaningful hardening).** Add a regex allowlist validator for `video_id` format (YouTube IDs are `[A-Za-z0-9_-]{11}`) before passing to any subprocess. Reject and log anything that doesn't match.

### UI4 — `yt_cookies.txt` is unencrypted and unaccess-controlled
- **What:** Cookie file for yt-dlp authentication sits on disk with no encryption or file permission enforcement. If the process runs as a broad user, any co-tenant process can read session cookies.
- **File/Line:** `clip_extractor.py:23`
- **Assessment:** **Investigate further.** Determine the deployment environment. If running on a shared host or containerized with mounted volumes accessible to other containers, this is a real credential exposure risk. At minimum: `chmod 600 yt_cookies.txt` enforced at startup. Better: load cookie content from an environment variable or secrets manager and write to a tempfile with restricted permissions, deleted after use.

### UI5 — N+1 ffmpeg process spawning per clip
- **What:** Multiple sequential ffmpeg invocations per clip (lines 55, 65, 78) where a single complex filtergraph could handle all operations in one pass.
- **File/Line:** `clip_extractor.py:55, 65, 78`
- **Assessment:** **Investigate further / P2.** This is a performance issue, not a correctness issue. On a low-volume overnight pipeline, it may be acceptable. If render time is a constraint (e.g., the pipeline must complete before morning), consolidate ffmpeg calls. Defer unless render time benchmarks show it's a bottleneck.

### UI6 — Gemini grading failure causes infinite loop risk
- **What:** If Gemini grading consistently fails (e.g., API down, key issue), the overnight loop skips grading and never achieves Grade A, potentially looping forever.
- **File/Line:** `overnight_render_loop.py:425`
- **Assessment:** **Implement.** Add a maximum iteration cap (e.g., 3 re-render attempts). After max attempts, accept the best-available output with a WARN log rather than looping indefinitely. This is a liveness guarantee.

---

## CONFLICTS (models disagree — tiebreaker)

No genuine conflicts exist this cycle — only one model produced output. The following are internal tensions within Grok's own analysis that require resolution:

### C1 — Fail fast vs. graceful degradation on TTS errors
- **Tension:** Grok notes that `tts_engine.py:772` raises an exception (good — fail fast) but also flags the lack of a local TTS fallback (implying graceful degradation is desired).
- **Resolution:** The correct answer is **context-dependent fail fast with human alerting, not silent degradation.** Do not add a low-quality local TTS fallback that produces a degraded episode silently. Instead: raise, halt the episode render for that run, alert the operator, and wait for quota reset or manual intervention. A bad episode is worse than no episode for a quality-brand product like Protocol Pulse.

### C2 — Bitcoin-only enforcement: prompt-level vs. output-validation-level
- **Tension:** Grok marks Bitcoin-only compliance as COMPLIANT based on prompt instructions, but prompt instructions alone are not a compliance guarantee — LLMs can hallucinate altcoin content.
- **Resolution:** **Downgrade to PARTIAL.** Prompt enforcement is necessary but not sufficient. Add a post-generation content check (simple keyword scan for known altcoin names: "ethereum", "solana", "XRP", etc.) on all generated script segments before they advance to TTS. Flag and reject violating segments.

---

## VALIDATED STRENGTHS (do NOT change in second pass)

### VS1 — No hardcoded API keys
Secrets are loaded via `get_key()` abstraction throughout. This pattern is correct and consistent. Do not inline secrets or change the key-loading architecture.

### VS2 — Parameterized SQL queries
SQLite access in `montage_producer.py:969` uses parameterized queries. SQL injection risk is properly mitigated. Do not rewrite DB access layer.

### VS3 — Bitcoin-only editorial enforcement in prompts
The prompt-level rules (no altcoins, no DeFi, full "Bitcoin" spelling) are present and consistent across `script_writer.py`. The prompt architecture is correct — the gap is output validation (see C2), not the prompts themselves. Do not remove or weaken the prompt rules.

### VS4 — ElevenLabs quota check exists
The quota pre-check at `tts_engine.py:1045` before making calls is the right pattern. Do not remove it — extend it with better fallback handling (see U2).

### VS5 — Explicit silence fallback disabled
Disabling the silence fallback (rather than producing silent audio that passes quality checks) is the correct product decision for a voice-first show. Do not re-enable silence as a fallback.

---

## LAW COMPLIANCE CONSENSUS

> Based on Grok analysis only. Gemini and GPT-4o did not contribute.

| Rule | Status | Finding |
|---|---|---|
| Bitcoin-only content | PARTIAL | Prompt-enforced but no output validation layer. See C2. |
| No "BTC" abbreviation | COMPLIANT | Enforced in prompts and TTS preprocessing. |
| PBX opens every episode | PARTIAL | Normalization bugs (M4) may override this correctly in some paths but break it in others. Needs audit. |
| Database indexing on sort/filter columns | UNKNOWN | No index definitions visible in reviewed code. Cannot confirm. Must be verified against model definitions. |
| Concurrent user capacity (~1000 peak) | NON-COMPLIANT | No rate limiting, queuing, or load distribution present in reviewed pipeline components. |
| UI animations via CSS/SVG only | COMPLIANT (assumed) | No frontend code reviewed; backend uses FFmpeg, not browser rendering APIs. |

**Final determination on violations:**
- **Active violation:** Rate limiting / concurrent capacity — no mechanism exists
- **Active partial violation:** Bitcoin-only — output not validated post-generation
- **Unverifiable:** Database indexing — requires model definition review
- **Needs audit:** PBX episode-open rule — broken by normalization bugs

---

## SECURITY CONSENSUS

Priority order (Grok-confirmed, severity-ranked):

| Priority | Issue | File | Severity |
|---|---|---|---|
| 1 | Unthrottled API calls — quota exhaustion + potential abuse | `tts_engine.py:1116`, `clip_extractor.py:290` | HIGH |
| 2 | `yt_cookies.txt` unencrypted on disk | `clip_extractor.py:23` | MODERATE |
| 3 | `video_id` passed to subprocess without allowlist validation | `clip_extractor.py:259,290` | LOW-MODERATE |
| 4 | Shared JSON state with no file locking — race condition / corruption | `clip_selector.py:110`, `script_writer.py:270` | MODERATE (integrity) |
| 5 | **EXTERNAL INCIDENT:** Gemini API key leaked | Audit infrastructure | CRITICAL — rotate NOW |

**The Gemini key leak is the most urgent security action — it predates the code audit and is not a code bug, but it must be resolved before Cycle 2 fires.**

---

## WORLD-CLASS GAP CONSENSUS

> Items a truly world-class production pipeline would have that this codebase currently lacks. Single-model cycle — items below are Grok-identified but represent structurally sound gaps.

### WCG1 — No observability / metrics layer
The pipeline has no structured metrics emission (Prometheus, Datadog, StatsD, or equivalent). There is no way to know — in production — which stage is slowest, how often retries occur, what the clip selection hit rate is, or whether TTS cache efficiency is improving. A world-class pipeline emits a metric at every stage boundary.

### WCG2 — No end-to-end pipeline state machine
The pipeline is a linear script with ad-hoc retry logic. A world-class system uses an explicit state machine or workflow engine (even a simple one) where each stage has defined states: PENDING → IN_PROGRESS → SUCCEEDED / FAILED → RETRYING. This makes recovery deterministic and auditable.

### WCG3 — No output quality regression baseline
There is no automated check that today's episode quality score is not significantly worse than yesterday's. A world-class content pipeline has a quality floor: if Grade < threshold, alert before publishing, never silently ship a degraded episode.

### WCG4 — No content deduplication across days
`used_clips.json` tracks clips within a run but there is no evidence of cross-day deduplication. A world-class Bitcoin show never replays the same clip two days in a row. The DB should track clip usage with timestamps and enforce minimum rest periods per source video.

---

## FINAL ACTION PLAN (sorted by consensus priority)

```
P0 CRITICAL | Rotate leaked Gemini API key immediately | Audit infrastructure / .env | models: structural | Active credential exposure — blocks Cycle 2

P0 CRITICAL | Add file locking to all shared JSON state (used_clips.json, narrative_context.json) | clip_selector.py:110, script_writer.py:270 | models: grok | Race condition causes silent state corruption under concurrent runs

P0 CRITICAL | Replace silent exception swallowing with structured error handling + alerts | script_writer.py:705, clip_selector.py:385, tts_engine.py:772 | models: grok | Silent failures produce wrong output with no operator awareness

P0 CRITICAL | Add maximum retry cap to overnight render loop + clear state before retry | overnight_render_loop.py:425,485 | models: grok | Infinite loop risk on Gemini grading failure; stale state causes repeated failures

P1 HIGH | Implement exponential backoff + token-bucket rate limiting on all external API calls | tts_engine.py:1116, clip_extractor.py:290 | models: grok | Quota exhaustion halts pipeline; unthrottled calls risk API bans

P1 HIGH | Add PID file singleton guard to daemon/overnight render loop | overnight_render_loop.py:552 | models: grok | Concurrent loops corrupt outputs and logs

P1 HIGH | Audit and fix host normalization forcing PBX on all segments | script_writer.py:235,325,424 | models: grok | Breaks intended dual-host format; overrides producer intent silently

P1 HIGH | Add AV sync re-encode fallback to original clip on failure | clip_extractor.py:54-65 | models: grok | Data loss bug — failed re-encode drops clip entirely

P1 HIGH | Add audio integrity validation to TTS cache (ffprobe duration check) | tts_engine.py:739,944 | models: grok | Corrupt cached audio reused silently across episodes

P1 HIGH | Add post-generation content validation for altcoin/off-topic terms | script_writer.py (post-generation hook) | models: tiebreaker C2 | Bitcoin-only law compliance requires output validation, not just prompt rules

P1 HIGH | Add video_id allowlist regex before subprocess call | clip_extractor.py:259,290 | models: grok | Prevents malformed IDs reaching shell; cheap hardening

P2 MEDIUM | Enforce chmod 600 on yt_cookies.txt at startup; evaluate secrets-manager migration | clip_extractor.py:23 | models: grok | Cookie file exposure risk on shared/containerized hosts

P2 MEDIUM | Add montage-suitability re-ranking on Pulse Check fallback clips | montage_producer.py:94-122 | models: grok | Low-energy content risks degrading montage quality silently

P2 MEDIUM | Verify and create DB indices on all sort/filter columns | montage_producer.py:961 + model definitions | models: grok | Unverified compliance with indexing requirement; slow queries under load

P2 MEDIUM | Add cross-day clip deduplication with minimum rest period | clip_selector.py + DB layer | models: grok (WCG4) | World-class content pipeline never repeats clips day-over-day

P2 MEDIUM | Consolidate multi-pass ffmpeg calls into single filtergraph per clip | clip_extractor.py:55,65,78 | models: grok | Performance: reduces subprocess overhead; defer if render time not yet a bottleneck
```

---

## CYCLE 1 VERDICT

**Not ready for second build pass as-is. Requires targeted fixes before Cycle 2.**

The audit is structurally compromised: only 1 of 3 models produced output (Grok), GPT-4o returned nothing, and Gemini was blocked by a leaked API key that is itself a P0 security incident. The findings from Grok are credible and mechanically sound, but they carry single-reviewer confidence, not consensus confidence.

**Recommended path:**
1. Rotate the Gemini API key immediately
2. Implement all P0 items from this report
3. Re-run the 3-model audit (Cycle 2) with all models functional
4. Promote to build pass only after Cycle 2 produces genuine multi-model consensus

The codebase has real structural issues (race conditions, silent failures, infinite loop risk, compliance gaps) that warrant fixes regardless of single-reviewer confidence. The P0s are not speculative — they are verifiable bugs. Proceed with P0 implementation in parallel with Cycle 2 setup.

---

## SECOND PASS PROMPT (ready to fire into Claude Code)

```
Read ~/protocol_pulse/docs/gospels/WATCHDOG_LLM_GOSPEL.md.
Read ~/protocol_pulse/docs/audits/pipeline-day3-audit_CONSENSUS_C1.md.

This is the SECOND PASS for pipeline-day3-audit.
The first build was reviewed by 1 functional AI model (Grok) across 1 cycle.
NOTE: Gemini was blocked (leaked API key — rotate before this pass).
NOTE: GPT-4o returned no output this cycle.
Implement every P0 and P1 item from the consensus. Use judgment on P2.

PRIORITY ACTION PLAN:

P0 CRITICAL | Add file locking to all shared JSON state | clip_selector.py:110, script_writer.py:270 | Use fcntl.flock() or filelock library; atomic write via os.replace()

P0 CRITICAL | Replace silent exception swallowing with structured error handling | script_writer.py:705, clip_selector.py:385, tts_engine.py:772 | Log full traceback at ERROR, emit alert, return typed sentinel or raise

P0 CRITICAL | Add maximum retry cap (3 attempts) + state reset before retry | overnight_render_loop.py:425,485 | Prevent infinite loop on Gemini grading failure; clear failed downloads and stale locks before each retry

P1 HIGH | Implement exponential backoff + token-bucket rate limiting on external APIs | tts_engine.py:1116, clip_extractor.py:290 | Start 1s, cap 60s, max 5 retries, jitter; token bucket for ElevenLabs

P1 HIGH | Add PID file singleton guard to daemon mode | overnight_render_loop.py:552 | Write /tmp/protocol_pulse_render.pid at start; refuse second instance; remove on clean exit via atexit

P1 HIGH | Fix host normalization — restore dual-host alternation | script_writer.py:235,325,424 | PBX forced only on episode open per spec; all other segments use alternation logic

P1 HIGH | Add AV sync re-encode fallback to original clip | clip_extractor.py:54-65 | Save original path before re-encode; on failure, log and return original

P1 HIGH | Add audio integrity check to TTS cache validation | tts_engine.py:739,944 | Use ffprobe to check duration; reject and re-fetch files below expected threshold

P1 HIGH | Add post-generation content validation for altcoin terms | script_writer.py post-generation hook | Keyword scan for ethereum/solana/XRP/etc.; reject violating segments before TTS

P1 HIGH | Add video_id allowlist regex validator | clip_extractor.py:259,290 | Regex: ^[A-Za-z0-9_-]{11}$ — reject and log anything non-matching

P2 MEDIUM | Enforce chmod 600 on yt_cookies.txt at startup | clip_extractor.py:23 | os.chmod() call at module init; evaluate secrets-manager migration for next sprint

P2 MEDIUM | Add montage-suitability re-ranking on fallback clips | montage_producer.py:94-122 | Sort by existing quality score descending; apply minimum threshold before accepting fallback

P2 MEDIUM | Verify DB indices on sort/filter columns | montage_producer.py:961 + model definitions | CREATE INDEX IF NOT EXISTS on all columns used in WHERE/ORDER BY

VALIDATED (do NOT touch — all models