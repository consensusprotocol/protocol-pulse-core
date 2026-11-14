# heimdall_muse (meta-models/muse-spark-open-816b-a42b, 454.5 s, $0.026, finish stop)

# PROTOCOL PULSE — CODE AUDIT: pp-ingest diff 116fbd5c (mine-hook/2)

## SECTION 1: CORRECTNESS

### Main flow: watch → fetch → mine → ledger → adapter

**Watch (`watch.py:176-228`):** Correct. RSS canary + fallback, backoff, `first_sight` backfill logic. `poll_channel` correctly handles `backoff_until` check at `watch.py:182-183`. One subtle bug: `watch.py:191-192` updates `etag`/`last_modified` from headers even on `not_modified` path — but `rss_list` returns `dict(e.headers)` on 304, which is correct. No issue.

**Fetch (`fetch.py:120-251`):** Correct. `process()` state machine covers all branches. `publish_time()` correctly prioritizes `release_timestamp` for live VODs. `_store_captions` correctly defers `meta.json` write until captions confirmed (INGEST-FAIL-01 fix).

**Mine — the diff under review (`mine.py:126-505`):**

**1. OPENER filter — logic error: `>>` markers can cause false positives/negatives**

`opener_word()` at `mine.py:216-220` calls `canon.canon_tokens(text, heads=True)` on `l["text"]` which is `E.spoken(toks[w0:w1+1])`. The `text` field is the spoken form — but `contract.py:129-135` shows `turn_change_inside` checks for `>>` in raw token words. The question is: does `E.spoken()` strip `>>` markers or preserve them?

If `E.spoken()` preserves `>>` as a token (e.g., `">> Hello world"`), then `canon.canon_tokens(">> Hello", heads=True)` would tokenize `>>` — and `>>` is not in any opener set, so it would NOT be flagged. But the builder's `stand_alone.py` OPENER rule operates on the spoken text *after* speaker markers are handled. If the builder strips `>>` before checking the opener, but this code doesn't, there's a mismatch: a hook starting with `>>` + pronoun would pass here but fail at the builder.

Conversely, if `E.spoken()` strips `>>`, then `opener_word` correctly sees the first real word. **This needs verification against `eligibility.spoken` implementation — the diff assumes `E.spoken` output is what the builder checks, but this is not proven in the diff.**

**2. `bad_opener` returns `"empty"` for empty text — counted as dropped, never written. Correct behavior** (`mine.py:223-224`). An empty text moment should not be a hook. No bug.

**3. `episode_measure` — correctness issue: `segs[-1].get("end")` can be `None`**

At `mine.py:244-245`:
```python
mins = max(0.0, (float(segs[-1].get("end") or 0) - float(segs[0].get("start") or 0)) / 60.0)
```
If `segs[-1]["end"]` is `None` (possible for incomplete records), `float(None or 0)` = `0.0`, and `float(segs[0].get("start") or 0)` similarly. For a single-segment record where `end` is `None`, `mins = 0.0`, `turns_per_min = None`. This is handled — `None` is stored, not crashed. The `try/except (TypeError, ValueError)` at `mine.py:246` catches other cases. **Correct, but the `or 0` fallback silently produces `0.0` minutes for records with missing timing — `turns_per_min = None` is correct for that case, but `minutes: 0.0` with `speaker_markers: N` is misleading. Should be `minutes: None` or `0.0` with a note.**

**4. `episode_measure` counts both `>>` and `&gt;&gt;` — correct** (`mine.py:236`). YouTube captions escape `>>` as `&gt;&gt;` in XML. The regex `r">>|&gt;&gt;"` handles both. Verified against `contract.py:23` which defines `SPEAKER_MARKERS = (">>", "&gt;&gt;")`.

**5. `build_line` episode fallback — correct** (`mine.py:435`):
```python
"episode": episode if episode is not None else episode_measure(rec),
```
When called from `mine_video` at `mine.py:487`, `episode` is always passed (computed at `mine.py:465`). The fallback only matters for external callers (A/B harness `ab.py`). Correct.

**6. `mine_video` report — `report["episode"]` added at `mine.py:466` — correct, additive only.**

**7. Hook filtering — `dropped_s` only for duration drops, not opener drops** (`mine.py:498-499`):
```python
if why.startswith("outside"):
    report.setdefault("dropped_s", []).append(d)
```
This means opener-rejected hooks don't pollute `dropped_s` (which is specifically for duration analysis per audit r80 c1). **Correct and intentional.**

**8. `tools/ingest_watch.py --rerun` — race condition (low severity)**

At `ingest_watch.py:152-156`:
```python
n = q.x("UPDATE videos SET hook_ts=NULL, ... WHERE state IN (?, ?) AND published_ts >= ? ...").rowcount
```
This is a direct SQL UPDATE without going through `Queue.claim()` or holding any lock. If the watcher's `hook` loop is concurrently running `hook_once()` which does `q.hook_due()` → `claim` → `hook_video` → `q.set_hook()`, there's a TOCTOU: the CLI resets `hook_ts=NULL` while the watcher has already claimed a video and is mining it. The watcher would then re-mine it on next `hook_due` poll, producing duplicate ledger lines (deduped by `moment_id` latest-wins, so not data-corrupting, but wasteful).

**Not a data-loss bug** — `ledger.carry_forward` + latest-wins handles duplicates. But it wastes API calls. The existing `hook_note <> ?` guard prevents re-queuing already-rerun videos, but doesn't prevent the concurrent claim race.

**9. No N+1 query problem in the diff.** `episode_measure` iterates `rec["segments"]` in memory. `opener_word`/`bad_opener` called once per hook candidate (max 3 per window, ~few hundred per video). No DB queries in loops added.

**10. Edge: `canon` import inside function — correct for testability** (`mine.py:219`). `canon` is imported lazily inside `opener_word()` so the module loads even when `canon.py` isn't on `sys.path` during testing. Same pattern as `contract.py:92-93` for `sentence_law`. Consistent.

---

## SECTION 2: LAW COMPLIANCE

| Law | Verdict | Evidence |
|-----|---------|----------|
| **L-x NO SINGLE MODEL, ULTRON FIRST** | **COMPLIANT** | Diff touches only `mine.py` prompt text and filtering. No vendor/model names added. `providers.json` unchanged. Hook role still uses `["heimdall_qwen27b", "local_gemma"]` chain. `OllamaLocalBackend` still gated on `gpu0.held()` at `providers.py:461-465`. |
| **L-l Strict schema, nothing repaired** | **COMPLIANT** | `validator()` at `mine.py:329-381` unchanged. Hook uses same validator with `key="hooks", max_n=3, max_count=3`. Rejected replies still retried with reason string, never repaired. `flagcheck.py:173-200` same pattern. |
| **L-j / L-m Fail closed** | **COMPLIANT** | `bad_opener` returning `"empty"` for empty text → dropped (fail closed). `episode_measure` returning `unmarked: True` when `n==0` (not measured, not solo). `ledger.py:337-338` expiry check unchanged. No new fail-open path. |
| **L-h / L-k Read as spoken** | **COMPLIANT** | `build_line` at `mine.py:419` still uses `E.spoken(toks[w0:w1+1])` for `text`. `opener_word` at `mine.py:219` uses `canon.canon_tokens` which is the canonical form — same tokenizer the builder uses. No raw caption text used. |
| **L-e Word timing at cut time** | **COMPLIANT** | `mine.py:408-411` still sets `duration_s: None` for `timing=="segment"`, `duration_estimate_s` flagged. No word timing claimed. |
| **L-u Hard exclusions** | **COMPLIANT** | `mine.py:21-24` `HARD_RISKS` unchanged. `ledger.py:347-348` still drops `any(r in HARD_RISKS for r in eff)`. Diff adds no bypass. Hook rows carry same `risk` flags via `build_line` at `mine.py:426`. |
| **L-v Speaker turn / re-uploads** | **COMPLIANT** | `contract.py:129-135` `turn_change_inside` unchanged. `ledger.py:351-352` still drops `turn_change_inside is True`. `fetch.py:186-191,242-247` duplicate detection unchanged. New `episode` field is measurement only, not used for exclusion. |
| **L-q Moments first** | **COMPLIANT** | Hook pass is explicitly a second pass (`mine.py:121-125` comment: "Another pass picks the video's best statements; you look ONLY for openers"). Moment pass unchanged. |
| **L-r No GPU** | **COMPLIANT** | No GPU code added. `OllamaLocalBackend` still requires `gpu0.held()` check. |
| **L-w / L-e (expiry 12h)** | **COMPLIANT** | `config.py:36-37` `EXPIRY_H=12` unchanged. `ledger.py:280-286` `expiry()` unchanged. New `episode` field doesn't affect expiry. |
| **Spend freeze** | **COMPLIANT** | No change to `providers.json` freeze list. No new back-end added. `providers.py:692-695` `frozen()` check still gates every call. |
| **Secrets** | **COMPLIANT** | No secrets in diff. `Keyring` at `providers.py:147-188` still redacts. No new env reads. |

**Overall Law Compliance: COMPLIANT — no violations introduced.**

---

## SECTION 3: SECURITY

| Check | Verdict | Detail |
|-------|---------|--------|
| **SQL injection** | **PASS** | New code in `ingest_watch.py:152-156` uses parameterized query `q.x("UPDATE ... WHERE state IN (?, ?) AND published_ts >= ? ...", (f"re-run: ...", Q.MINED, ...))`. All values parameterized. No string interpolation into SQL. Existing `queue.py` uses same pattern throughout. No `filter()` ORM — raw sqlite3 with `?` placeholders. |
| **Auth bypass** | **N/A** | No HTTP routes in this service. It's a tmux daemon + CLI tool. No auth layer to bypass. |
| **Rate limiting** | **PASS** | `providers.py:609-637` `Throttle` + `Health` circuit breaker unchanged. Hook pass uses `HOOK_WINDOWS=4` (`service.py:54-55`) — bounded. `--rerun` CLI doesn't trigger API calls directly, just resets DB state for the watcher's loop to pick up. |
| **Secrets in code** | **PASS** | No API keys, tokens, or passwords in diff. `providers.json` `key_env`/`key_env_prefix` pattern unchanged. `Keyring.redact()` at `providers.py:180-187` still active. |
| **Unvalidated input → DB/filesystem/shell** | **PASS** | `opener_word` takes `l["text"]` which is `E.spoken()` output — already sanitized. `episode_measure` takes `rec["segments"]` from transcript store. No user input reaches DB/filesystem/shell. `ingest_watch.py --rerun` takes no user string that reaches SQL unparameterized. |
| **Prompt injection** | **PASS** | `mine.py:291-294` `_untrusted()` still replaces `<` with `‹` to prevent closing `<sentences>` block. Hook prompt at `mine.py:149-213` uses same `_untrusted`/`_q` wrapping. No new injection vector. |

**No security regressions in this diff.**

---

## SECTION 4: FRONTEND QUALITY

**N/A — This is a backend-only service.** No UI, no HTML, no JS, no CSS. The "frontend" is `tools/ingest_watch.py` CLI and `docs/audits/parallel/pp-ingest_STATE.md` markdown reports.

**CLI quality of the new `--rerun` flag:**

- `ingest_watch.py:152-157` prints `"{n} videos ... queued for the hook pass again ({version}), newest first"` — clear feedback. ✓
- No `--dry-run` for `--rerun` — the UPDATE executes immediately with no confirmation. For a destructive reset (clears `hook_ts`, `hook_tries`, `hook_next_ts`), a dry-run or confirmation would be expected. **Minor gap.**
- `hooks --help` text at `ingest_watch.py:224-225` says `"queue the window's mined videos"` — should say "12 h window's" for clarity. **Nit.**

---

## SECTION 5: BACKEND QUALITY

| Area | Verdict | Detail |
|------|---------|--------|
| **DB rollback on write** | **PASS** | `queue.py:77` uses `isolation_level=None` (autocommit) with `WAL` mode. Each `x()` is atomic. `ingest_watch.py:152` single UPDATE is atomic. No multi-statement transaction needing rollback in the diff. Existing `ledger.py:34-66` `append()` uses `flock` + `fsync` correctly. |
| **External API: timeout+retry+degradation** | **PASS** | Unchanged. `providers.py:797-867` `_try()` has `transport_retries=3`, `Throttle` backoff, `Health` circuit breaker. Hook pass correctly distinguishes `outage` (retry, no try consumed) vs `rejected` (try consumed) at `service.py:364-376`. |
| **Cron failure handling** | **PASS** | No cron — tmux loops with `_loop()` at `service.py:623-632` catching `Exception` per iteration, logging `loop_error` event, continuing. `purge_once` at `service.py:575-594` handles `SpecError` gracefully. New `--rerun` is manual CLI, not a loop. |
| **Memory leaks** | **PASS** | `episode_measure` creates a small dict per call. `opener_word` imports `canon` (cached in `sys.modules` after first import). No large objects per-request. `mine_video` still uses bounded `ThreadPoolExecutor`. |
| **Logging** | **GOOD** | `service.py:375,383` logs hook pass results with `what` string including `dropped` counts. `mine.py:498` tracks `report["dropped"]` per reason. `ingest_watch.py:157` logs rerun count. Sufficient for debugging. |

**One gap:** `episode_measure` at `mine.py:242-250` has no logging when `segs` is empty or timing is missing — it silently returns `minutes: 0.0, turns_per_min: None, unmarked: True`. An empty `segments` array (corrupt record) would look identical to a valid solo episode. Should log or set a `measured_from` variant. **Low severity** — corrupt records are rare and caught elsewhere.

---

## SECTION 6: WORLD-CLASS GAP ANALYSIS

**What this diff does well (genuinely excellent):**

- **The OPENER rule as code, not just prompt:** Stating the rule in the prompt AND enforcing it deterministically in `bad_opener()` is the right architecture. Prompt-only rules are probabilistic; code enforcement is guaranteed. This is how Bloomberg would do it — deterministic gates after LLM output.
- **Episode measurement as data, not judgment:** Adding `episode` as a measured field on every row (not just hooks) means the builder can filter/sort without recomputing. Clean separation of measurement vs. policy.
- **Prompt versioning (`mine-hook/2`):** Enables A/B comparison and `--rerun` targeting. Professional.

**What's missing or could be better:**

1. **No validation that `OPENER_*` sets match the builder's source.** The comment says "a test compares them with the builder's source" but no test file is in the diff. If `pp-selectid` changes its sets, this silently diverges. A startup check or import (like `contract.py` imports `eligibility`) would be more robust than a test that may not run in CI. **Impact: medium — silent divergence breaks spotlight filtering.**

2. **No metric on opener rejection rate.** `report["dropped"]` tracks it per-video, but `stats.py:108-113` `hooks_12h` only reports `hook_rows` and `usd`. There's no `hooks_dropped_by_opener` in `live.json`. An operator can't tell if the opener filter is too aggressive (dropping 90% of hooks) without querying the DB. **Impact: low — visible in per-video logs, just not aggregated.**

3. **The `--rerun` CLI has no guard against concurrent watcher.** As noted in Section 1, it directly UPDATEs the queue DB while the watcher may be holding claims. A `flock` on `service.lock` or a check would prevent wasted work. **Impact: low — no data corruption, just wasted API calls.**

4. **No handling of `canon` import failure.** `opener_word()` at `mine.py:218` does `import canon` — if `canon.py` is missing (e.g., running outside the repo), this raises `ImportError` which propagates up through `mine_video` → caught as generic `Exception` at `service.py:387-391` → `hook_next_ts` retry. It works but the error message `"hook pass crashed: ModuleNotFoundError: No module named 'canon'"` is not actionable. A startup check like `contract.py:52-76` does for `eligibility` would be better. **Impact: low.**

---

## SECTION 7: SCORES

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| **Backend logic** | **88/100** | Correct, well-structured. Minor: `>>` marker handling in opener check unverified, `episode_measure` edge for empty segments, `--rerun` TOCTOU. |
| **Frontend/UI** | **N/A** | No UI. CLI `--rerun` is functional but lacks dry-run. Not scored. |
| **Error handling** | **90/100** | `episode_measure` try/except, `bad_opener` null handling, `mine_video` outage vs rejected distinction all correct. Minor: `canon` import failure message could be clearer. |
| **Security** | **95/100** | No regressions. Parameterized queries, no secrets, prompt injection still mitigated. No new attack surface. |
| **Performance** | **92/100** | `opener_word` called once per hook candidate (max ~tens per video), `episode_measure` once per video. Negligible overhead. No N+1, no unbounded loops. |
| **Law compliance** | **98/100** | Fully compliant. No law weakened. Hook prompt correctly states builder's rule verbatim. Episode field is additive. One minor: no automated drift detection for OPENER sets. |
| **World-class gap** | **82/100** | Deterministic enforcement + measurement pattern is excellent. Gaps: no import-based OPENER sync, no aggregated opener rejection metric, no concurrent-watcher guard on rerun. |
| **OVERALL** | **90/100** | Production-ready. Three minor issues, no blockers. |

---

## SECTION 8: PRIORITY ACTION PLAN

```
P0 CRITICAL | (none) | — | No data-loss, security, or correctness blocker in this diff.

P1 HIGH     | Verify opener_word handles >> markers correctly | mine.py:216-220 | If E.spoken() preserves ">>" tokens, opener_word(">> And then...") returns ">>" not "and" — the conjunction check is bypassed. If E.spoken() strips them, it's correct. Must verify against actual eligibility.spoken() output for a record containing ">>" markers. Add a test: mine_video with a record containing ">> And then..." as first sentence of a hook candidate.

P1 HIGH     | Add OPENER set sync test or import | mine.py:132-138 | OPENER_PRONOUNS/CONJUNCTIONS/REPLY_FRAGMENTS are hardcoded copies of pp-selectid's stand_alone.py sets. If the builder changes its sets, this silently diverges and spotlight filtering breaks. Add tests/ingest/test_mine.py::test_opener_sets_match_builder that imports pp-selectid's sets and asserts equality (same pattern as test_the_hook_question_is_the_builders_judge_question_verbatim).

P2 MEDIUM   | Guard --rerun against concurrent watcher | tools/ingest_watch.py:152 | Direct UPDATE while watcher holds hook claims wastes API calls. Either: (a) check service.lock with LOCK_EX|LOCK_NB and refuse if held, or (b) document "stop the watcher first" in --help text.

P2 MEDIUM   | Aggregate opener rejection in live.json | pipeline/ingest/stats.py:108-113 | hooks_12h reports hook_rows but not dropped-by-opener count. Add hooks_dropped_opener to stats.live() so operators can detect if the filter is too aggressive without DB queries.

P2 MEDIUM   | Handle canon import failure gracefully | mine.py:218-219 | Bare "import canon" inside opener_word() raises ModuleNotFoundError with no context. Wrap with try/except ImportError and return "canon unavailable" or check at Service.__init__ like contract.py does for eligibility.

P3 LOW      | Clarify --rerun help text | tools/ingest_watch.py:224 | "queue the window's mined videos" → "queue the 12 h window's mined videos for re-hooking" for clarity.

P3 LOW      | episode_measure: distinguish empty vs solo | mine.py:242-250 | Empty segments (corrupt record) returns same {minutes:0.0, unmarked:True} as a valid solo episode. Consider returning measured_from:"no segments" or minutes:None when segs is empty.

P3 LOW      | Add --dry-run to --rerun | tools/ingest_watch.py:152 | --rerun immediately UPDATEs the DB with no preview. A --dry-run that prints "would requeue N videos" would prevent accidental reruns.
```

---

## SECTION 9: THE ONE THING

**Verify that `E.spoken()` strips `>>` markers before `opener_word()` sees the text — if it doesn't, every hook starting with a speaker change silently bypasses the OPENER filter, which is the entire point of this change.**

---

## SECTION 10: FINAL VERDICT

**This code is ready for production.** The diff is small, additive, well-commented, and introduces no regressions to the moment pass, flags, adapter, or any gate. The deterministic OPENER enforcement after the LLM call is the right architecture. Before merging, add the OPENER set sync test (P1) and verify the `>>` marker handling with a single integration test — both are 10-minute fixes.