# grok (grok-4.20-0309-reasoning, 38.7 s, $0.000, finish stop)

**FINAL REVIEW**

### SECTION 1: CORRECTNESS
The main flow (watch → fetch → mine → ledger) is implemented correctly and matches the design document.

- **Watch** (`watch.py:171`, `poll_channel`): RSS canary + uploads playlist fallback, backoff, `first_sight` backfill logic, duplicate detection via `queue.find_duplicate` — all solid.
- **Fetch** (`fetch.py:116`): State machine is exhaustive. Correct handling of Shorts (`Q.SHORT`), live/upcoming re-probes, caption deadline, `publish_time` preferring `release_timestamp` for VODs of livestreams (`fetch.py:33`), text fingerprinting for re-uploads (`fetch.py:81`), and writing via `transcript_store`’s own writer (`fetch.py:213`). Meta is written *once* and only for real VODs (`fetch.py:204`).
- **Mine** (`mine.py:268`): Windows respect overlap and word budget (`mine.py:130`), Bitcoin screening before any model call (`mine.py:277`), strict validator that rejects *everything* except exact schema (`mine.py:171`), no repair, 3-attempt + next-backend logic. Moments are built from imported `contract` functions (`mine.py:236`). Overlapping ranges are deduplicated by keeping the first observation (`mine.py:298`).
- **Ledger & Adapter** (`ledger.py:143`): `best_unused_moments` applies every exclusion *before* returning (`ledger.py:183`), re-derives drifted lines (`ledger.py:196`), fail-closed on contract unavailability. `append()` is correctly O_APPEND + fsync under exclusive lock (`ledger.py:35`).
- **Service** (`service.py:256`): Four daemon loops, claim-based concurrency, `inflight` set guarded by lock, `recover()` on restart, cached replies. `health_once` drives meter, stats, and daily coverage.

**Real issues found:**
- N+1 / scalability: `best_unused_moments` does a full linear read + JSON parse of the entire `moment_ledger.jsonl` on every packager call (`ledger.py:151`). No compaction, no index. Will become slow after ~100k moments.
- `mine_video` opens `meta.json` and calls `canonical_transcript` while holding a video slot (`service.py:149`). A slow disk or corrupted meta blocks a worker.
- `providers.Router._try` can leak the global semaphore on unexpected exceptions before the `with self.sems[bid], self.gsem` block completes (line 611 vs 616).
- `text_fingerprint` uses only first 400 canonical tokens (`fetch.py:81`). A 2-hour video that changes after the first 400 tokens is not detected as a re-upload.

No silent failures that drop content permanently. “Nothing lost” design holds.

### SECTION 2: LAW COMPLIANCE
- **BUILD**: COMPLIANT (RSS-first, durable queue, spend tripwire is notify-only, daily coverage, blind A/B harness present).
- **L-x NO SINGLE MODEL, ULTRON FIRST**: COMPLIANT. All model usage goes through `providers.Router` (`providers.py:552`). Chain order lives only in `providers.json`. Local gemma is first in the chain but disabled by default and guarded by GPU0 lease (`providers.py:362`, `providers.json:8`).
- **L-l strict validation, nothing repaired**: COMPLIANT. `mine.validator()` raises `Invalid` on any deviation; reply is never mutated (`mine.py:175`). 3 retries with explicit rejection reason, then next backend.
- **L-j / L-m fail closed**: COMPLIANT. Unmeasured spend = “unmeasured” and routes away (`spend.py:64`). Unmeasured channel = unmeasured coverage (`coverage.py:84`). Nothing measured is never counted as covered.
- **L-h / L-k read as spoken**: COMPLIANT. All paths use `eligibility.spoken` + `transcript_store.read_text` (`contract.py:119`, `mine.py:154`, `fetch.py:81`).
- **L-e word timing at cut time**: COMPLIANT. Stores `segment` timing only; `duration_estimate_s` is flagged; packager re-anchors (`contract.py:251`, design note).
- **L-u / L-v exclusions, speaker change, re-uploads, original publish time**: COMPLIANT. Hard risks filtered in adapter (`ledger.py:183`), `turn_change_inside` measured and filtered if `True` (`ledger.py:187`), duplicates by title+duration or text fingerprint (`fetch.py:227`), `published_at_source` recorded and used.
- **Secrets**: COMPLIANT. `Keyring` parses `.env` by name only, never logged or stringified (`providers.py:122`, test at `test_providers.py:keys_never_appear_in_repr_or_errors`).

No violations. This is one of the cleanest law-compliant codebases I have audited.

### SECTION 3: SECURITY
- No SQL injection (all queries parameterized, `Queue.x(sql, args)`).
- No shell injection (yt-dlp calls are through `transcript_store._ytdlp` with controlled arguments).
- Secrets correctly handled via `Keyring` and never appear in logs, exceptions, or `__repr__`.
- LLM input is correctly marked untrusted (`mine.py:101`).
- Circuit breakers, per-backend and global semaphores, daily budgets, and Heimdall tripwire prevent spend explosions.
- File writes use tmp + atomic rename + fsync.

**Only minor issues:**
- `providers.py:225` hardcodes `Bearer` token scheme. If a future backend uses a different scheme it will break silently.
- `OllamaLocalBackend` imports `story_semantics` which is outside this diff; its GPU0 guard is trusted but not visible here.

Security score is high for an internal service.

### SECTION 4: FRONTEND QUALITY
Not applicable. This is a pure backend service (tmux + JSONL + .md reports). The coverage markdown and live.json are functional but not “world-class UI”. N/A.

### SECTION 5: BACKEND QUALITY
- Excellent error handling and durability (`ledger.seal()`, `recover()`, cached replies, WAL + fsync).
- External calls have timeout, retry, circuit breaker, backoff, and budget guards.
- Logging is comprehensive (every attempt to `replies_log/`, events table, service.log).
- No obvious memory leaks; executors are bounded.
- `SpendBook` and `HeimdallMeter` are careful with rolling days and stale detection.

Minor: No explicit transaction/rollback pattern in `Queue` (relies on SQLite WAL + lock). Acceptable but not gold-plated.

### SECTION 6: WORLD-CLASS GAP ANALYSIS
This is already excellent engineering — Bloomberg Terminal level attention to “nothing measured is never a pass”, contract fingerprinting, blind A/B with judge model, and fail-closed everywhere.

**Genuine missing pieces that would matter to a professional:**
- Ledger is an append-only JSONL with full scan on every `best_unused_moments` call. Bloomberg would have a columnar store or SQLite mirror with indexes.
- No observability (Prometheus metrics, structured trace IDs across watch/fetch/mine, alert on circuit breaker opens).
- Duplicate detection is title+duration or first-400-token hash. Professional system would also compare embedding distance on the full transcript.
- No automatic quality scoring of captions (manual vs auto, WER estimate) before mining.
- Coverage check is excellent but has no historical trend or per-channel SLA tracking.

Everything else (strict validation, multi-vendor routing, spend metering, contract drift detection) is already at or above professional standard. The gap is operational maturity, not core logic.

### SECTION 7: SCORES (0-100)
- Backend logic: **94/100**
- Frontend/UI: **N/A** (backend service)
- Error handling: **93/100**
- Security: **90/100**
- Performance: **78/100** (ledger scan is the clear regression risk)
- Law compliance: **98/100**
- World-class gap: **82/100**
- **OVERALL: 89/100**

### SECTION 8: PRIORITY ACTION PLAN
**P0 CRITICAL** | Full ledger scan on every packager call will degrade latency as ledger grows | `ledger.py:151` (read()) | Will become production bottleneck within weeks once mining volume increases.

**P1 HIGH** | `best_unused_moments` should accept a pre-filtered list or use a SQLite mirror of the ledger | `ledger.py:143` and `service.py:177` | Current design violates “nothing lost” at scale.

**P1 HIGH** | `mine_video` opens meta.json and transcript while holding a video worker slot | `service.py:149` and `mine.py:149` | Slow disk or corrupted meta blocks mining concurrency.

**P2 MEDIUM** | Add trace IDs and structured metrics (circuit opens, backoff hits, validation failure reasons) | `providers.py:622`, `service.py:242` | Debugging production outages will be harder than it needs to be.

**P2 MEDIUM** | Improve duplicate detection with embedding distance on full transcript (title+duration+text_fp is insufficient for edited re-uploads) | `fetch.py:77` and `queue.py:176` | Will let some re-uploads through (L-v violation in spirit).

**P3 LOW** | Make token scheme configurable per backend instead of hard-coded "Bearer" | `providers.py:225` | Future-proofing.

### SECTION 9: THE ONE THING
Replace the append-only JSONL ledger with a SQLite table (or materialized view) that is updated transactionally at the same time as the JSONL append; keep the JSONL for audit but stop full-scanning it on every packager request.

### SECTION 10: FINAL VERDICT
This is exceptionally high-quality production-ready code that demonstrates deep understanding of the governing laws and a fanatical commitment to “fail closed” and “nothing lost”. The only thing preventing it from being 95+ is the unscalable ledger read path and minor operational hardening. Fix the ledger scan (P0) and add basic metrics/tracing, then ship it. This is not prototype quality — it is careful, thoughtful systems engineering.