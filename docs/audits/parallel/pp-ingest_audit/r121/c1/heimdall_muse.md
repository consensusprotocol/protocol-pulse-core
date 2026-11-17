# heimdall_muse (meta-models/muse-spark-open-816b-a42b, 201.0 s, $0.004, finish stop)

# PROTOCOL PULSE: CODE AUDIT — r121 (pp-ingest DIFF ONLY)

**Branch:** `pp-ingest` @ `5c9ce2b6` | **Files under review:** `pipeline/ingest/fetch.py`, `tests/ingest/test_r121.py` | **Ruling:** 107(2) — DIFF only

---

### SECTION 1: CORRECTNESS

**Claimed flow:** `fetch.probe()` detects yt-dlp stub (id matches but all `FACT_KEYS` empty) → returns `("no_metadata", ...)` → `fetch.process()` maps to `Q.UNAVAILABLE` with hourly retry, capped at 6 tries, never counted in `stall.WAITING`.

**Step-by-step walk:**

1.  **`fetch.probe` gate call — CORRECT:** `gate.run(["-J", "--skip-download", "--ignore-no-formats-error", f"https://...{video_id}"], timeout=120)` at `fetch.py:131-132`. Timeout present. URL is constructed from internal `video_id`, not user input.

2.  **Stub detection — CORRECT but FRAGILE:** `fetch.py:141` `if not any(j.get(k) for k in FACT_KEYS)`. This correctly identifies the observed stub where `live_status=None, duration=None, timestamp=None, release_timestamp=None, upload_date=None`. The `j.get(k)` truthiness check means `0`, `""`, `None`, `False` all count as absent. For these 5 keys this is correct — a real `duration=0` would be falsy but YouTube never returns 0-duration VODs; `live_status=""` is not a valid YouTube value. Logic holds.

3.  **Non-stub passthrough — CORRECT:** `fetch.py:142` `return j, None` only reached if at least one FACT_KEY is truthy. Verified by `test_r121.py:38-44`: `is_upcoming` with `release_timestamp` → `Q.UPCOMING`; VOD with `upload_date` → `Q.PROBE_RETRY` with old reason. This satisfies "What to check: Any probe with one fact keeps its old path."

4.  **State transition — CORRECT:** `fetch.py:273-276`:
    ```python
    final = tries + 1 >= NO_METADATA_MAX_TRIES  # 6
    q.set_state(vid, Q.UNAVAILABLE, next_at=now_ts + (10**9 if final else NO_METADATA_RETRY_S), tries=tries+1, ...)
    ```
    Matches spec: hourly retry (`3600s`), give-up after 6, `10**9` sentinel for terminal. Consistent with existing `UNAVAILABLE` pattern at `fetch.py:278-280` (4 tries, 6h interval).

5.  **Stall exclusion — CORRECT by construction:** `Q.UNAVAILABLE` is not in `stall.WAITING` (unchanged code, per design note). `test_r121.py:47-52` explicitly asserts `chk["waiting"] == [] and chk["stalled"] is False` after stub → UNAVAILABLE. Verified.

6.  **Retry cadence claim "no more often than before" — CORRECT:** Old path was `PROBE_RETRY_S` capped at `3600s` (`fetch.py:37`). New path is `NO_METADATA_RETRY_S = 3600` (`fetch.py:38`). Identical ceiling. No regression.

**Edge cases / silent failures:**

*   **Empty DB / bad input:** `probe()` handles `json.loads` failure via `except ValueError: pass` → falls through to existing error handling (not in diff, but structure preserved). No crash on empty stdout.
*   **API timeout:** `gate.run(..., timeout=120)` will raise; caught by outer `try` at `fetch.py:130` (inferred from diff context `try: r = gate.run`).
*   **Race condition:** `q.set_state` is a single UPDATE; no read-modify-write race beyond existing queue design. No new race introduced — this diff is purely branching logic inside `process()`.
*   **N+1:** No loop, no DB query inside loop. Single `set_state` per invocation.
*   **Logic error — `any(j.get(k) for k in FACT_KEYS)` vs `any(k in j and j[k] ...)`:** Current code treats `j = {"id": vid, "live_status": 0}` as stub. In practice YouTube never emits `0` for these keys, so not a production bug, but strictly the check should be `j.get(k) is not None` if `duration=0` were possible. **Not a blocker** — documented as intentional truthiness check, and test helper `H.probe_json` uses `None` for absent.
*   **Missing `FACT_KEYS` coverage — POTENTIAL FALSE NEGATIVE:** If YouTube/yt-dlp adds a new fact field (e.g., `availability`) and removes one of the 5, a real video could be misclassified as stub. Mitigated by choosing 5 orthogonal keys spanning live/VOD/timestamp domains. Acceptable risk; the alternative (allowlist title prefix `"youtube video #"`) would be more brittle.

**Verdict on correctness: DOES WHAT IT CLAIMS.** 3 new tests cover the 3 invariants (hourly retry + give-up, non-stub passthrough, stall exclusion). Mutations M44-M47 killed.

---

### SECTION 2: LAW COMPLIANCE

| Law | Verdict | Evidence |
|-----|---------|----------|
| **BUILD: continuous ingest (~10m, ETag/backoff, ledger, re-upload dedup, Shorts/live handled, durable queue, staging captions, Heimdall mining ≤20 in-flight, $460 cap 90% notify, append-only ledger, coverage check, blind A/B)** | **COMPLIANT** | Diff does not touch ingest cadence, queue durability, caption staging, mining, ledger, or A/B. It *improves* BUILD compliance by preventing stall false-positives that would mask real ingest failures. `NO_METADATA_RETRY_S=3600` preserves "video that turns public is still seen within hour." |
| **L-x NO SINGLE MODEL, ULTRON FIRST (provider interface ≥2 backends, local default, no GPU use here)** | **COMPLIANT** | No model/provider code touched. `fetch.py` is yt-dlp metadata only. No GPU lease acquired. |
| **L-l strict schema, nothing repaired; L-j/L-m fail closed** | **COMPLIANT** | Stub is now explicitly `UNAVAILABLE` (fail closed), not repaired into a fake probe. No schema repair. |
| **L-h/L-k canonical transcript form, never rewrite stored records** | **COMPLIANT** | No transcript code touched. |
| **L-e word timing at cut time** | **COMPLIANT** | Not in scope. |
| **L-u hard exclusions before ranking; L-v no speaker-span; re-upload excluded; time-sensitive needs publish time** | **COMPLIANT** | Stub has no publish time → correctly excluded from mining (UNAVAILABLE, not mined). Does not weaken L-u/L-v. |
| **Secrets: keys by name from env file, never logged** | **COMPLIANT** | No secrets handling in diff. `detail[-200:]` truncation at `fetch.py:271` and `detail` passthrough at `fetch.py:275` contain only yt-dlp error strings, not keys. |
| **SPEND FREEZE (no paid frontier vendors; Heimdall → local only; queue if both down; 90% tripwire NOTIFY never halt)** | **COMPLIANT** | No vendor calls added. `fetch.py` calls only `gate.run` (yt-dlp subprocess). No OpenAI/Anthropic/xAI/Google invocation. |

**No violations detected in this diff.**

---

### SECTION 3: SECURITY

*   **SQL injection:** No raw SQL in diff. `q.set_state` and `q.x("UPDATE videos SET ...", (param,))` in tests use parameterized queries. `video_id` is interpolated only into a URL string for `gate.run`, not SQL. **PASS.**
*   **Authentication bypass:** No routes, no auth surface in `pipeline/ingest/fetch.py`. **N/A.**
*   **Rate limiting gaps:** `gate.run` is yt-dlp subprocess, not paid API. No new paid API consumption. Existing `PROBE_RETRY_S` backoff preserved. `NO_METADATA_RETRY_S=3600` is *less* aggressive than prior hourly cap, so no exhaustion risk. **PASS.**
*   **Secrets in code:** No hardcoded keys, tokens, passwords. `FACT_KEYS`, `NO_METADATA_RETRY_S`, `NO_METADATA_MAX_TRIES` are constants, not secrets. **PASS.**
*   **Unvalidated input → DB/filesystem/shell:** `video_id` flows to `f"https://www.youtube.com/watch?v={video_id}"` → `gate.run([...])`. `video_id` originates from RSS/yt-dlp discovery, not user input. Even if adversarial, `gate.run` receives it as a single argv element (not shell-interpolated). No shell injection. No filesystem write. **PASS.**
*   **Log injection / secret leak:** `reason=f"no metadata: {detail}"` at `fetch.py:275` — `detail` is the static string `"yt-dlp returned no fact about it (removed, private or not public yet)"` from `fetch.py:141`. No user data, no secret. Safe.

**Security score: No new attack surface.**

---

### SECTION 4: FRONTEND QUALITY

**N/A — No frontend code in diff.** `pipeline/ingest/fetch.py` is backend ingest; `tests/ingest/test_r121.py` is backend test. No UI, no JS, no CSS, no viewport, no async loading states to evaluate.

If this audit template requires a score, it is **NOT APPLICABLE**, not a failure. The change correctly has no UI impact — stall line suppression is observed via `STATE` file / `stall.check` output, not a web UI.

---

### SECTION 5: BACKEND QUALITY

*   **DB operations — try/except with rollback:** `q.set_state` is the only write. Existing queue implementation (not in diff) is assumed to handle transactions — this diff does not add a new write path that bypasses it. No new `try/except` needed at this layer; `probe()` already has `try/except ValueError`. **ACCEPTABLE.**
*   **External API calls — timeout + retry + graceful degradation:** `gate.run(..., timeout=120)` has timeout. Retry is via `Q.UNAVAILABLE` with `next_at` scheduling (hourly, 6 tries). Degradation is graceful: stub → UNAVAILABLE, not crash, not infinite loop. **PASS.**
*   **Cron job failure handling:** Ingest is continuous (~10m cadence, per BUILD law). This fix *prevents* a cron stall false-alarm that would have paged overnight. No new crash path. **PASS.**
*   **Memory leaks:** No large objects, no per-request allocation, no cache. Constants only. **PASS.**
*   **Logging / debuggability:** `reason=f"no metadata: {detail}"` at `fetch.py:275` is stored in `videos.reason` and visible in queue inspection. Distinguishes from `"no publish time measured"` and `"Video unavailable"` — critical for debugging. The `detail` string includes the yt-dlp diagnosis. **GOOD** — would be *better* with `video_id` in reason, but `videos.video_id` is already the row key, so redundant.
*   **Constants hygiene:** `FACT_KEYS`, `NO_METADATA_RETRY_S`, `NO_METADATA_MAX_TRIES` at `fetch.py:37-39` are top-level, named, with `r121` comments. Discoverable, tunable. **GOOD.**

**One nit:** `fetch.py:141` comment says `"youtube video #<id>"` but the code does not check title — it checks fact absence. Comment is accurate as *description* of stub, not as *logic*, but could mislead future reader into thinking title is checked. Minor.

---

### SECTION 6: WORLD-CLASS GAP ANALYSIS

This is a **surgical bugfix**, not a feature. Judged as such, it is excellent. World-class gaps are *outside* this diff, but worth noting for pp-ingest overall:

*   **Already excellent:** Root-cause analysis in commit message is Bloomberg-grade — exact video IDs, exact yt-dlp command, exact stall timestamp, exact retry interval math. Mutation testing (M44-M47 4/4 killed) is above industry standard. Test helper `stub()` faithfully reproduces the real yt-dlp stub shape.
*   **Missing — observability (P2):** No metric/counter increment for `no_metadata` vs `unavailable` vs `age_gated`. At scale, operator cannot distinguish "YouTube removed 50 videos" from "yt-dlp broke" without querying `videos.reason LIKE 'no metadata%'`. A `stats.inc("fetch.no_metadata")` would make dashboards world-class. **Not a blocker for this diff.**
*   **Missing — yt-dlp version pin awareness (P3):** Stub shape (`"youtube video #<id>"` title, all facts None) is yt-dlp-version-dependent. If yt-dlp changes stub format to include `live_status="is_upcoming"` with null timestamps, this heuristic breaks. A defensive comment linking to yt-dlp issue/version would help. **Polish.**
*   **Not missing:** Retry cap (6 tries = 6 hours) is well-chosen — covers transient "not public yet" (scheduled premiere delay) without infinite retry. Matches `UNAVAILABLE_MAX_TRIES=4` pattern but slightly higher because "not public yet" is more likely to resolve than "Private video."

**This diff itself has no material world-class gap.** It is the kind of fix Coinbase Advanced *wishes* it had shipped before its overnight pager storm.

---

### SECTION 7: SCORES (0-100 each)

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| **Backend logic** | **96/100** | Correct, minimal, well-tested. -4 for truthiness vs `is not None` pedantry and title-comment vs fact-check slight mismatch. |
| **Frontend/UI** | **N/A** | No frontend in scope. If forced: 100 — correctly has no UI impact. |
| **Error handling** | **94/100** | Fail-closed, bounded retry, terminal give-up, stall exclusion. -6 for no explicit log line at `no_metadata` detection (relies on DB reason only). |
| **Security** | **100/100** | No new surface, no secrets, no injection, no paid API. |
| **Performance** | **100/100** | One `any()` over 5 keys per probe. Zero overhead. Fixes infinite hourly wake-ups that wasted cycles. |
| **Law compliance** | **100/100** | All BUILD + L-* + SPEND FREEZE laws satisfied. No violations. |
| **World-class gap** | **92/100** | Surgical, well-documented, mutation-tested. -8 for missing metric counter and yt-dlp version pin note (outside diff scope). |
| **OVERALL** | **97/100** | Production-ready. Ship it. |

---

### SECTION 8: PRIORITY ACTION PLAN

No P0 or P1 issues in this diff. All items below are enhancements, not blockers.

| Priority | What | File:Line | Why |
|----------|------|-----------|-----|
| **P2 MEDIUM** | Add `metrics.inc("fetch.no_metadata")` or structured log on stub detection | `pipeline/ingest/fetch.py:141-142` | Operator cannot alert on stub-rate spike (e.g., yt-dlp breakage vs normal removals) without DB query; metric enables dashboard + pager distinction |
| **P2 MEDIUM** | Change `any(j.get(k) for k in FACT_KEYS)` to `any(j.get(k) is not None for k in FACT_KEYS)` | `pipeline/ingest/fetch.py:141` | Future-proofs against `duration=0` or `live_status=""` being valid falsy values; current truthiness check is correct today but semantically imprecise |
| **P3 LOW** | Add yt-dlp version + stub shape link to comment | `pipeline/ingest/fetch.py:37-38` | Stub format is yt-dlp-version-dependent; without version pin note, future maintainer won't know when heuristic needs revisiting |
| **P3 LOW** | Clarify comment: fact-absence is the signal, title is just description | `pipeline/ingest/fetch.py:141` | Comment `yt-dlp's stub ("youtube video #<id>", every fact` could be misread as title-check; reword to `// stub has no FACT_KEYS, regardless of title` |
| **P3 LOW** | Consider unifying `NO_METADATA_MAX_TRIES=6` and `UNAVAILABLE_MAX_TRIES=4` rationale in one comment block | `pipeline/ingest/fetch.py:35-39` | Two similar constants with different caps (4 vs 6) deserve a one-line rationale delta to prevent future "why not 4?" churn |

---

### SECTION 9: THE ONE THING

**You fixed the right bug with the smallest possible change and proved it with the right tests — now add a metric so the next stub-shape change pages you before the stall line does.**

---

### SECTION 10: FINAL VERDICT

**Ready for production. Ship as-is.** This is a textbook incident-driven fix: precise root cause (yt-dlp stub → infinite `PROBE_RETRY`), minimal diff (7 lines of logic), correct retry semantics (hourly, capped, never waiting), and tests that lock all three invariants. No law violations, no security surface, no performance regression. The only pre-merge ask is optional: a metric counter for observability.
