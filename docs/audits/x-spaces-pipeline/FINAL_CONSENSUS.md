# CONSENSUS REPORT — X-SPACES-PIPELINE — CYCLE 2
Generated: 2026-03-18 18:15
Models: grok, gpt4o, gemini

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Correctness | 3/10 | 5/10 | 5/10 | **4/10** |
| Law Compliance | 6/10 | 6/10 | 6/10 | **6/10** |
| Security | 6/10 | 6/10 | 6/10 | **6/10** |
| Backend Quality | 4/10 | 5/10 | 5/10 | **5/10** |
| Production Readiness | 2/10 | 4/10 | 4/10 | **3/10** |
| Overall | 4/10 | 5/10 | 5/10 | **4/10** |

> **Scoring note:** Gemini scored most aggressively downward after catching the broken state machine and transcript data corruption in full. GPT-4o and Grok landed closer together. The consensus skews toward Gemini's severity assessment on P0 items — these bugs are genuinely show-stopping.

---

## UNANIMOUS FINDINGS (all 3 models agree — implement unconditionally)

### U1 — No Atomic Work-Claiming: Concurrent Runs Duplicate Processing and Publication
- **What it is:** `run_pipeline()` fetches unprocessed spaces and immediately begins expensive work (yt-dlp, Anthropic API, publishing) with no claim/lease step. Two overlapping cron runs will discover the same spaces, both transcribe them, both generate articles, and potentially both publish — resulting in duplicate publications and wasted API spend.
- **File/lines:** `x_spaces_scraper/run_scraper.py:88–190`, `x_spaces_scraper/spaces_state.py:57–138`
- **What to change:** Add a `claiming_at` timestamp column (or `status = 'processing'`) to `spaces_state`. Before any expensive work, execute an atomic `UPDATE spaces SET claiming_at = NOW() WHERE space_id = ? AND claiming_at IS NULL` and skip the row if 0 rows were affected. On crash/timeout, a sweep job resets stale claims older than N minutes.

### U2 — No Rate Limiting or Cost Caps on Paid APIs
- **What it is:** Neither `article_generator.py` (Anthropic/Claude) nor `transcript_fetcher.py` (map-reduce summarization chain, also Claude) implements any persisted call budget, throttle, or cost ceiling. A large batch of discovered spaces will call Claude unboundedly. The deprecated `curator.py` had this feature — it was regressed out.
- **File/lines:** `x_spaces_scraper/article_generator.py` (all Claude calls), `x_spaces_scraper/transcript_fetcher.py:259–271`
- **What to change:** Introduce a persisted daily call counter (SQLite or a sidecar file). Before each Claude invocation, check counter ≤ budget. On breach, log a cost-limit warning and skip remaining spaces for the current run. Restore the pattern from the deprecated `curator.py`.

### U3 — Tombstoned/Deprecated Code Still Present and Importable
- **What it is:** Entire directories (`x_spaces_pipeline/`, `video_pipeline_v3/utils/spaces_monitor.py`) marked "TOMBSTONED" or "DEPRECATED" remain in the repository, are importable, and contain hardcoded absolute paths (`/home/ultron/...`), brittle lock-file concurrency, and references to sensitive files (`yt_cookies.txt`). An automated process or junior engineer could accidentally execute them.
- **File/lines:** `x_spaces_pipeline/` (entire directory), `video_pipeline_v3/utils/spaces_monitor.py`
- **What to change:** Delete these files entirely. If historical reference is needed, they belong in git history only, not in the working tree.

---

## MAJORITY FINDINGS (2 of 3 models agree)

### M1 — Discovery Does Not Filter to `TARGET_ACCOUNTS` (GPT-4o + Gemini)
- **What it is:** `find_spaces()` runs keyword searches via Twitter API v2 and Guest Token GraphQL, then adds results without checking whether the host is in `TARGET_ACCOUNTS`. The feature docstring says "Find recent X Spaces from key Bitcoin accounts" — but the implementation is a pure keyword search open to any account.
- **File/lines:** `scraper.py:421–433`
- **What to change:** After collecting API/guest results, filter: `if result.host_username not in TARGET_ACCOUNTS: continue`. Apply consistently to all three discovery paths.

### M2 — Transcript Replaced by LLM Summary: Transcript Truth-Model Violation (GPT-4o + Gemini, Grok implicitly)
- **What it is:** In `_try_audio_replay()`, when a transcript exceeds a length threshold, the code overwrites `result["transcript"]` with an LLM-generated map-reduce summary while leaving `result["source"]` as `audio_replay`. Downstream consumers (article generator, any future consumer) receive a summary they believe is a raw transcript. This is a silent data corruption bug.
- **File/lines:** `x_spaces_scraper/transcript_fetcher.py:182–187`
- **What to change:** Save the summary to a new key: `result["summary_text"] = summary`. Never overwrite `result["transcript"]`. If the full transcript is too large to store, truncate it with a clear marker — do not replace it with generated content.

### M3 — State Machine Is Broken: Multiple States Never Marked (GPT-4o + Gemini, Grok partially)
- **What it is:** The defined state machine (`discovered → downloaded → transcribed → summarized → injected → published`) is largely fictional in the implementation:
  - `downloaded_at` is never set after audio download (`transcript_fetcher.py`)
  - `summarized_at` is never set after `generate_article()` (`run_scraper.py:161`)
  - `published_at` is never set after `publish_article()` (`run_scraper.py:181`)
  - `injected_at` is marked *after* publishing, which is the wrong order per the state definition
  - `get_pending(state)` is therefore useless for all states beyond `transcribed`
- **File/lines:** `transcript_fetcher.py` (downloaded_at), `run_scraper.py:161,178–183`, `scraper.py:408–410`, `spaces_state.py:14,117–123`
- **What to change:** Mark each state at the correct moment. Add `mark(space_id, "downloaded")` after audio download succeeds. Add `mark(space_id, "summarized")` after article generation. Add `mark(space_id, "published")` after successful publish. Fix the injected/published ordering per the spec.

### M4 — Serial yt-dlp Sweep Creates Severe Latency / Cron Overrun Risk (GPT-4o + Grok)
- **What it is:** `find_spaces()` runs yt-dlp once per account, sequentially, with a 30-second timeout per call, across 14 target accounts. Worst-case this stage alone takes ~7 minutes — before any transcription or article generation. This can exceed cron cadence, cause overlapping runs, and compound U1.
- **File/lines:** `scraper.py:435–440`, `scraper.py:343–349`
- **What to change:** Parallelize yt-dlp calls using `concurrent.futures.ThreadPoolExecutor` with a bounded pool (e.g., 4–6 workers). Add a global wall-clock budget for the discovery phase and bail out gracefully if exceeded.

### M5 — Mixed Naive/Aware UTC Timestamps (GPT-4o + Grok)
- **What it is:** `run_scraper.py:102,216` uses `datetime.utcnow().isoformat()` (naive), while `spaces_state.py:123` uses timezone-aware UTC. SQLite stores both as text; this won't crash immediately but creates inconsistent ordering, comparison semantics, and subtle bugs in any future date arithmetic.
- **File/lines:** `run_scraper.py:102,216`, `spaces_state.py:123`
- **What to change:** Standardize on `datetime.now(timezone.utc).isoformat()` everywhere. Audit all timestamp writes in the codebase.

### M6 — `title` Argument Never Passed to `fetch_transcript` (GPT-4o + Gemini)
- **What it is:** `run_scraper.py:116` calls `fetch_transcript(space.space_id, space.url, db=db)`, omitting `title=space.title`. The function signature is `fetch_transcript(space_id, space_url, title="", db=None)`. The metadata fallback path in `transcript_fetcher.py:94–95` loses title context silently.
- **File/lines:** `run_scraper.py:116`, `transcript_fetcher.py:324`
- **What to change:** `fetch_transcript(space.space_id, space.url, title=space.title, db=db)`

---

## UNIQUE INSIGHTS (only 1 model caught this — evaluate carefully)

### Unique-1 (GPT-4o) — `published` State Is Never Marked; `mark_processed` Maps to `injected`
- **Assessment: IMPLEMENT.** This is a real, specific bug: `scraper.py:408–410` shows `mark_processed` maps to `injected`, not `published`. This is separate from M3's broader state machine concern and deserves its own fix entry. The operational consequence is that published articles are permanently invisible to any query on `published_at`, breaking reporting and idempotency checks.

### Unique-2 (GPT-4o) — Transcript Metadata Columns (`source`, `word_count`, `quality_score`) Never Persisted to DB
- **Assessment: IMPLEMENT.** The schema defines `transcript_source`, `transcript_word_count`, `transcript_quality_score` columns (`spaces_state.py:31–34`), but the active code path never writes them. This is pure wasted schema and eliminates any ability to operationally query transcript quality or source distribution. Fix: pass and persist these values when marking `transcribed`.

### Unique-3 (GPT-4o) — Article Generation Success Never Reflected in DB (`summarized_at` Not Marked)
- **Assessment: IMPLEMENT.** Covered partially by M3, but GPT-4o is more specific: `generate_article()` has no DB interaction at all. This means if the pipeline crashes after generation but before publication, the next run re-generates the article and re-charges the Anthropic API. Fix: mark `summarized_at` immediately after a successful `generate_article()` return and cache the generated content.

### Unique-4 (Grok) — No Retry Logic for Transient API Failures
- **Assessment: IMPLEMENT (P2).** No exponential backoff retry exists for Twitter API, Claude, or yt-dlp network calls. A single transient 429 or connection reset silently drops the space from the current run. A simple `tenacity`-based decorator with 3 attempts and jittered backoff is low-effort and high-value.

### Unique-5 (Grok) — No Cleanup of Stale Cache Files in Transcript Cache Directory
- **Assessment: IMPLEMENT (P2).** The cache directory accumulates files including expired negative-cache entries indefinitely. A periodic sweep deleting files older than 48 hours is straightforward and prevents slow disk exhaustion.

### Unique-6 (GPT-4o) — `setup_logging()` Silently No-ops if Root Logger Already Configured
- **Assessment: INVESTIGATE.** The `if not root.handlers` guard means if any imported module has already configured root logging, the intended file/console handlers are never attached. In production CLI use this is probably fine, but in test harnesses or when called from a larger orchestrator this will silently suppress log output. Low priority but worth a comment at minimum.

### Unique-7 (GPT-4o) — `WhisperWorker.get()` Singleton Enforcement Is Convention-Only
- **Assessment: SKIP.** The docstring convention is sufficient for an internal codebase. Enforcing it via `__new__` or raising in `__init__` would add complexity with minimal real-world benefit given the pattern is already clearly documented.

### Unique-8 (Gemini) — `get_spaces_by_user` Method Is Dead Code
- **Assessment: IMPLEMENT (P2).** `TwitterAPIv2Scraper.get_spaces_by_user()` (`scraper.py:133`) is defined but never called in the pipeline. Dead code increases maintenance surface and creates confusion. Remove it or document that it is a utility for ad-hoc use only.

---

## CONFLICTS (models disagree — your tiebreaker)

### Conflict 1 — Severity of "Date Parse Failure Excludes Space"
- **Grok:** Flagged as a meaningful silent failure issue.
- **Gemini:** Partially agreed but noted the code does log a `warning` and the comment explicitly says "EXCLUDE undatable spaces, never silently include them." Assessed as intentional and acceptable.
- **Tiebreaker: Gemini is right.** The behavior is intentional, documented inline, and logged. Excluding spaces with unparseable dates is the correct conservative default to avoid processing stale or invalid content. No fix needed; at most add a metric counter for monitoring.

### Conflict 2 — "Mark Processed Before or After Publish?"
- **Grok:** Suggested marking earlier to avoid reprocessing on transient failure.
- **GPT-4o:** Pushed back — marking before successful publish would be strictly worse (a crashed run would suppress republication forever). The real fix is an intermediate `processing` claim state, not moving the mark-processed call earlier.
- **Tiebreaker: GPT-4o is right.** Marking a space as published before it is published is a worse bug than reprocessing. The correct fix is U1's atomic claim mechanism combined with M3's correct state marking. Do not move `mark_processed` earlier in isolation.

### Conflict 3 — "Does WAL + Upsert Prevent Race Conditions?"
- **Gemini:** Praised WAL + atomic upsert as a major correctness strength.
- **GPT-4o:** Partially disagreed — WAL protects write integrity but does not prevent duplicate *workflow execution* across concurrent processes.
- **Tiebreaker: Both are correct in different domains.** WAL + upsert correctly prevents DB corruption and duplicate DB rows. It does not prevent two processes from both reading the same unprocessed row and both doing expensive work on it. The statement "WAL prevents race conditions" is too broad — qualify it. The DB layer is sound; the orchestration layer is not.

---

## VALIDATED STRENGTHS (all models agree this is already excellent)

1. **SQLite WAL + Atomic Upsert in `spaces_state.py`:** The use of `PRAGMA journal_mode=WAL` and `INSERT ... ON CONFLICT DO UPDATE` provides correct concurrent write semantics at the DB layer. Do not change this pattern.

2. **Multi-Method Discovery with Fallbacks (`find_spaces`):** The three-tier discovery approach (API v2 → Guest Token → yt-dlp) is architecturally sound and resilient. The fallback hierarchy is correct and well-reasoned.

3. **Space Deduplication by `space_id`:** Deduplicating within the discovery phase before DB writes prevents unnecessary processing of duplicate results from multiple discovery methods.

4. **Subprocess Timeout and Cleanup Pattern for yt-dlp:** The timeout mechanism and process kill logic for yt-dlp subprocesses is broadly correct. The `proc.poll() is None` guard is defensive and appropriate.

5. **Explicit "TOMBSTONED" and "DEPRECATED" Headers:** The deprecated files do carry explicit headers warning engineers off them. This is better than no warning. (The fix is to delete them, not to add more warnings, but the intent was correct.)

6. **N+1-Free Database Access Pattern:** All DB lookups use batch queries (`get_pending`, `get_injected_ids`). No row-by-row query loops exist in the hot path.

---

## LAW COMPLIANCE CONSENSUS

**Governing Laws section was empty in the specification.**

All three models returned the same verdict: **NOT APPLICABLE** as formally specified. No legal violations to report against defined governing laws.

**Practical note (unscored):** The pipeline scrapes X (Twitter) content, fetches audio, transcribes it, and publishes derived works. While outside the formal audit scope, real-world deployment should confirm alignment with X's Terms of Service, DMCA safe harbor posture for scraped audio, and any applicable data retention obligations. This is flagged for product/legal review, not as a code defect.

---

## SECURITY CONSENSUS

All three models scored Security at **6/10** — the only dimension with perfect score agreement. The codebase is broadly adequate on injection and secrets handling. Shared security concerns in priority order:

1. **Cost/Resource Exhaustion via Unbounded API Calls (Medium):** Covered as U2. An adversary who can inject spaces into the discovery pipeline (or simply a large batch run) can exhaust Anthropic API budget. Not a traditional security vulnerability but a financial DoS vector. Fix: implement U2's call budget.

2. **Tombstoned Code References Sensitive File Paths (Low-Medium):** The deprecated code contains paths like `/home/ultron/yt_cookies.txt`. If these files exist on the server, their paths are now documented in source. Fix: delete tombstoned code (U3).

3. **No File Locking on Transcript Cache Writes (Low):** Concurrent processes writing the same JSON cache file without locking can produce a corrupt file. The failure mode is a bad cache entry causing a re-fetch, not data exfiltration. Fix: use atomic write via temp file + `os.replace()`.

4. **Guest Token GraphQL Scraping Brittleness (Accepted Risk):** Hard dependency on X internal API structure. Will break without notice and may trigger IP bans if called too aggressively. No code change will fully resolve this; it is an accepted architectural risk requiring monitoring.

No critical security vulnerabilities (injection, auth bypass, credential exposure in code) were identified by any model.

---

## WORLD-CLASS GAP CONSENSUS

Items mentioned by 2+ models as missing from a truly world-class implementation:

1. **Operational Observability / Metrics (Grok + GPT-4o):** No structured metrics are emitted (spaces discovered, transcripts fetched, articles generated, API calls made, costs incurred, failures by type). A world-class pipeline emits StatsD/Prometheus counters or writes a run-summary JSON for every execution. Without this, production debugging relies entirely on log grepping.

2. **Idempotent, Restartable Pipeline (All models, implicit):** The broken state machine means the pipeline cannot be restarted mid-run after a crash without risk of duplication or skipping steps. A world-class pipeline can be killed at any point and resumed from exactly where it left off, with all intermediate state preserved.

3. **End-to-End Integration Test / Regression Suite (Grok + Gemini):** No integration tests exist that exercise the full discovery → transcript → generate → publish path against mock/fixture data. This makes confident refactoring of any P0 fix impossible without manual verification.

4. **Cost Accounting and Budget Alerting (GPT-4o + Gemini):** Beyond a simple cap (U2), a world-class system tracks per-run and rolling API costs, stores them in the DB, and alerts when approaching budget thresholds. The deprecated `curator.py` had a primitive version of this that was regressed.

5. **Parallelized Transcript Fetching (GPT-4o + Grok):** Serial processing of spaces through the entire pipeline is slow. A world-class implementation uses a worker pool or task queue (even a simple `ThreadPoolExecutor`) to process multiple spaces concurrently within the atomic-claim safety of U1.

---

## FINAL ACTION PLAN (sorted by consensus priority)

| Priority | Change | File:Line | Models | Why |
|---|---|---|---|---|
| **P0 CRITICAL** | Add atomic `claiming_at` lease before any expensive work; skip if claim fails | `run_scraper.py:88–190`, `spaces_state.py:57–138` | All 3 | Concurrent runs duplicate work and publish; unshippable without this |
| **P0 CRITICAL** | Fix transcript truth model: save LLM summary to `summary_text`, never overwrite `transcript` | `transcript_fetcher.py:182–187` | All 3 | Silent data corruption; downstream consumers receive fabricated "transcript" |
| **P0 CRITICAL** | Implement daily call budget / cost cap for all Claude/Anthropic invocations | `article_generator.py`, `transcript_fetcher.py:259–271` | All 3 | Unbounded API spend; financial DoS on large batches |
| **P0 CRITICAL** | Delete tombstoned directories and deprecated files entirely | `x_spaces_pipeline/`, `video_pipeline_v3/utils/spaces_monitor.py` | All 3 | Executable deprecated code with hardcoded paths and sensitive file references |
| **P0 CRITICAL** | Filter API/guest discovery results to `TARGET_ACCOUNTS` hosts only | `scraper.py:421–433` | 2/3 (GPT-4o, Gemini) | Feature does not do what it says; unrelated accounts processed |
| **P0 CRITICAL** | Fix state machine: mark `downloaded_at`, `summarized_at`, `published_at` at correct steps; fix `injected` ordering | `transcript_fetcher.py`, `run_scraper.py:161,178–183`, `spaces_state.py:117–123` | 2/3 (GPT-4o, Gemini) + Grok partial | State machine is non-functional; pipeline is not idempotent or restartable |
| **P1 HIGH** | Fix `mark_processed` to map to `published`, not `injected` | `scraper.py:408–410`, `run_scraper.py:178–183` | GPT-4o (unique, validated) | Published articles permanently invisible to `published_at` queries |
| **P1 HIGH** | Persist `transcript_source`, `transcript_word_count`, `transcript_quality_score` to DB on transcribed mark | `transcript_fetcher.py:69–70`, `spaces_state.py:31–34` | GPT-4o (unique, validated) | Schema columns exist but are never written; operational observability broken |
| **P1 HIGH** | Pass `title=space.title` to `fetch_transcript()` | `run_scraper.py:116` | 2/3 (GPT-4o, Gemini) | Silent argument drop degrades fallback transcript quality |
| **P1 HIGH** | Parallelize yt-dlp per-account discovery with `ThreadPoolExecutor` | `scraper.py:435–440` | 2/3 (GPT-4o, Grok) | Serial 14-account sweep = ~7 min worst case; causes cron overrun and compounds U1 |
| **P1 HIGH** | Standardize all timestamps to `datetime.now(timezone.utc).isoformat()` | `run_scraper.py:102,216`, `spaces_state.py:123` | 2/3 (GPT-4o, Grok) | Mixed naive/aware timestamps create ordering and comparison bugs |
| **P1 HIGH** | Cache generated article content after `generate_article()` before publish; mark `summarized_at` immediately | `run_scraper.py:161` | GPT-4o (unique, validated) | Crash after generation but before publish causes re-generation and re-charges API |
| **P2 MEDIUM** | Add exponential backoff retry (3 attempts, jittered) for transient API failures | `scraper.py:84–98`, `transcript_fetcher.py:306–315` | Grok (unique, validated) | Single transient error silently drops a space from the run |
| **P2 MEDIUM** | Implement atomic transcript cache writes via `tempfile` + `os.replace()` | `transcript_fetcher.py:133–136` | Grok | Concurrent cache writes can corrupt JSON; low-effort fix |
| **P2 MEDIUM** |

---

# WINNER DETERMINATION

# WINNER: GPT-4o

GPT-4o delivered the highest-quality analysis across both cycles. It was the **original source** of the three most critical findings — TARGET_ACCOUNTS filter bypass, transcript truth-model violation (summary overwriting raw transcript), and state machine mismatches — all of which were validated by Gemini and Grok in Cycle 2 as findings they had missed. Its recommendations were specific to file and line number, semantically precise (distinguishing a data corruption bug from a mere code smell), and directly actionable without requiring further decomposition.

---

# FINAL SECOND-PASS PRIORITY LIST

Ordered by production risk. Implement in this sequence.

---

## P0 — Show-Stoppers: Do Not Ship Without These Fixed

### P0-1 — No Atomic Work-Claiming (Duplicate Publication Risk)
**File:** `run_scraper.py:88–190`, `spaces_state.py:57–138`
**Fix:** Add `status = 'processing'` or a `claimed_at` timestamp column. Before any expensive work begins, execute:
```sql
UPDATE spaces SET status = 'processing', claimed_at = NOW()
WHERE space_id = ? AND status = 'pending' AND claimed_at IS NULL
```
Skip if 0 rows affected. A background sweep resets claims older than a configurable TTL (suggest 15 minutes). Without this, two overlapping cron runs will both publish the same article.

---

### P0-2 — Transcript Overwritten by LLM Summary (Data Corruption)
**File:** `transcript_fetcher.py:182–187`
**Fix:** Store the summary under a distinct key. Never mutate `result["transcript"]`:
```python
# BEFORE (corrupt)
result["transcript"] = summarize(result["transcript"])

# AFTER
result["transcript_summary"] = summarize(result["transcript"])
result["transcript_truncated"] = False
```
Update all downstream consumers (`article_generator.py`) to check for `transcript_summary` first, falling back to `transcript`. The file's own docstring guarantees transcript fidelity — this code violates that contract.

---

### P0-3 — State Machine Broken: `mark_processed` Sets Wrong State After Publish
**File:** `run_scraper.py:182`, `spaces_state.py`
**Fix:** The state after successful publication must be `published`, not `injected`. Trace the full state transition path and enforce it:
```
pending → processing → transcribed → generated → published
```
Ensure `downloaded_at` is actually written in `transcript_fetcher.py` (currently never set). Add a guard that prevents re-entry if state is already `published`.

---

### P0-4 — Discovery Does Not Filter to TARGET_ACCOUNTS
**File:** `scraper.py:421–433`
**Fix:** After API v2 and guest-token keyword searches return results, filter before insertion:
```python
results = [s for s in raw_results if s.get("host_id") in TARGET_ACCOUNT_IDS]
```
Pre-compute `TARGET_ACCOUNT_IDS` as a set at module load. Without this, any account mentioning Bitcoin keywords gets ingested and published, which is a direct product correctness failure and a reputational risk.

---

## P1 — Critical: Fix Within First Post-Launch Sprint

### P1-1 — No Rate Limiting or Cost Caps on Paid APIs
**File:** `article_generator.py`, `transcript_fetcher.py:259–271`
**Fix:** Implement a persisted daily call budget in SQLite or Redis:
```python
if get_daily_claude_calls() >= CLAUDE_DAILY_LIMIT:
    raise BudgetExceededError("Claude call budget exhausted")
increment_daily_claude_calls()
```
Apply to every Anthropic invocation. Set a hard cap (suggest 200 calls/day initially) with alerting at 80%. The map-reduce summarization chain can fan out unboundedly on long transcripts — add a max-chunks guard.

---

### P1-2 — Serial yt-dlp Per Account Creates Cron Overrun Risk
**File:** `scraper.py:435–440`
**Fix:** Parallelize with `concurrent.futures.ThreadPoolExecutor` and a bounded pool:
```python
with ThreadPoolExecutor(max_workers=4) as executor:
    futures = {executor.submit(self._yt_dlp_fetch, account): account
               for account in TARGET_ACCOUNTS}
```
Worst-case serial runtime across 14 accounts at 30s timeout each is ~7 minutes before a single transcript is fetched. This will cause cron overlap without parallelization.

---

### P1-3 — Timestamp Inconsistency: Naive vs. Aware UTC Throughout
**File:** `run_scraper.py:102,216`, `spaces_state.py:123`
**Fix:** Standardize on timezone-aware UTC exclusively. Replace all instances of:
```python
datetime.utcnow().isoformat()  # naive — remove everywhere
```
With:
```python
datetime.now(timezone.utc).isoformat()
```
Enforce via a shared utility function `utils.utcnow()` imported everywhere. Mixed naive/aware timestamps will produce silent comparison errors on Python 3.11+.

---

### P1-4 — No JSON Schema Validation After Claude Response Parse
**File:** `article_generator.py:113–131`
**Fix:** After `json.loads`, validate required keys before use:
```python
REQUIRED_KEYS = {"title", "summary", "body", "tags"}
parsed = json.loads(response_text)
missing = REQUIRED_KEYS - parsed.keys()
if missing:
    raise ValueError(f"Claude response missing required keys: {missing}")
```
A malformed Claude response currently propagates as a `KeyError` deep in the publish path, leaving the space in a broken intermediate state with no actionable log message.

---

### P1-5 — `title` Argument Silently Dropped from `fetch_transcript` Call
**File:** `run_scraper.py:116`
**Fix:**
```python
# BEFORE
fetch_transcript(space.space_id, space.url, db=db)

# AFTER
fetch_transcript(space.space_id, space.url, title=space.title, db=db)
```
The omission silently degrades cache quality and metadata fallback accuracy. One line, zero risk.

---

## P2 — Quality and Hygiene: Address Before Codebase Scales

### P2-1 — File-Level Race Condition on Cache Writes
**File:** `transcript_fetcher.py:135`
**Fix:** Use `fcntl.flock` or write to a `.tmp` file then `os.replace()` (atomic on POSIX):
```python
tmp_path = cache_path.with_suffix('.tmp')
tmp_path.write_text(json.dumps(data))
tmp_path.replace(cache_path)  # atomic
```

### P2-2 — Dead Code: `get_spaces_by_user` Never Called
**File:** `scraper.py:133`
**Fix:** Delete or mark `# TODO: wire into find_spaces() for account-scoped search`. Dead importable methods create maintenance confusion and false confidence that account-scoped search is already implemented.

### P2-3 — Duplicate DB Connection on `XSpacesScraper` Init
**File:** `scraper.py:395–403`, `run_scraper.py:85–88`
**Fix:** Accept an optional `db` argument in `XSpacesScraper.__init__` and skip internal `SpaceStateDB()` creation if one is provided. Eliminates the silent extra open SQLite connection.

### P2-4 — Negative-Cache TTL Blocks Valid Retries
**File:** `transcript_fetcher.py:109–121`
**Fix:** Reduce negative-cache TTL from 24 hours to 2–4 hours, or add a force-refresh flag (`force=True`) to `fetch()`. A Space replay can become available within hours of the live event; 24-hour blocking is too aggressive.

### P2-5 — No Alerting on State Stagnation
**File:** `spaces_state.py`, `run_scraper.py`
**Fix:**