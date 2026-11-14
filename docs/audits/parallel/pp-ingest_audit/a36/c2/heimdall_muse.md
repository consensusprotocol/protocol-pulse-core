# heimdall_muse (meta-models/muse-spark-open-816b-a42b, 286.3 s, $0.028, finish stop)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT: pp-ingest (A36 WIDEN, mine-hook/4)

## 1. WHAT DID THEY CATCH THAT I MISSED?

**Honest accounting:**

*   **GLM caught the rounding boundary explicitly.** I noted `n=-1` as debatable and `float n` as implicit contract, but GLM did the more useful work: tracing `episode_measure`'s `round(n/mins, 2)` through to the `>=0.3` comparison and quantifying the effective boundary as `[0.295, 0.305)`. I called the core logic "CORRECT" and moved on; GLM showed *why* the 1-decimal ruling and 2-decimal measurement interact safely. I should have done that.
*   **GLM caught the `max_n` vs `max_count` confusion risk.** I verified `is_conversation` and `stats.py` but did not walk `mine_window`'s `schema(k["key"], k["max_count"])` vs `PROMPTS[kind](..., max_h=n)` distinction. GLM did — and correctly concluded it's not a bug (sentences-per-hook vs hooks-per-window are different axes). I missed an opportunity to confirm the prompt and validator agree on `n`.
*   **GLM caught the `no segments` → `windows=[]` → no jobs path.** I noted `n=-1` never happens; GLM verified the more realistic edge: `episode_measure` returns `speaker_markers=0, turns_per_min=None` for no segments, `is_conversation` returns `True`, but `windows([])` returns `[]` so nothing is asked anyway — matching A40's note. I should have closed that loop.
*   **Qwen caught nothing I missed on the diff itself** — its correctness section is a correct but shallower restatement of mine. Its value was as a third independent confirmation that `spot_rows IS NOT NULL` and the log branch are correct.
*   **Nobody caught a P0/P1 I missed.** The consensus is real: all three reviewers independently verified the predicate table, the `bool`-is-`int` trap, and the `spot_rows` ground-truth improvement.

## 2. WHERE DO I AGREE OR DISAGREE?

| Finding | Verdict | Why |
|---------|---------|-----|
| **GLM: `is_conversation` correct on all 8+ inputs, `bool` check order matters** | **Agree** | I said the same. The `isinstance(n, bool)` before `isinstance(n, int)` is load-bearing; both of us verified it. |
| **GLM: rounding boundary `[0.295,0.305)` is defensible, immaterial ($0.006)** | **Agree** | I didn't quantify it; GLM did. The ruling's 0.3 is 1-decimal, measurement is 2-decimal — the interaction is documented in design 13 after C1-2. Not a bug. |
| **GLM: `max_n` propagation correct, `max_count` vs `max_n` not confused** | **Agree** | I missed this check; GLM's conclusion is right. `schema` uses `max_count` (sentences per hook, 3), prompt uses `max_h=n` (hooks per window, 5 or 3). |
| **GLM: `no segments` edge handled** | **Agree** | Correct and worth stating. My `n=-1` note was less useful than this. |
| **Muse (me): `stats.py` `spot_rows IS NOT NULL` superior to threshold proxy** | **Agree (self)** | All three agreed. Qwen and GLM independently confirmed. The `from . import mine` removal also eliminates circular-import risk — I noted this, others didn't. |
| **Muse (me): version bump + `hooks --rerun` + cache hit correct** | **Agree (self)** | All three agreed. Solo prompt unchanged → same `sha256(prompt)` → cache hit. |
| **Qwen: `service.py` log branch only reachable for marked solo** | **Agree** | I said the same: `srep is None and scrash is None` only when `is_conversation` is `False`, which only happens for `n>0 and t<0.3`. |
| **Consensus: C1-1 `rows_by_episode` bucket fix, C1-2 rounding doc** | **Agree** | Both fixed in 7c437fec. I flagged C1-1 as P3 in cycle 1; now resolved. |
| **Consensus: paid_route keeps 1.0 threshold (A42)** | **Agree** | Correctly out of scope. One config value if orchestrator wants alignment. |
| **Muse P1 "validate video_id before yt-dlp" — refuted** | **Agree (refuted)** | ID is inside `https://...watch?v=` URL, list arg, no shell. Listings are id-validated. |
| **GLM P2 SWITCH_RE expects "*-FIRST" up mode** | **Agree (recorded, pre-existing)** | Outside diff. Not a blocker. |

## 3. NEW FINDINGS FROM THIS REVIEW

**Nothing new that is a defect in the diff.** The combined analysis actually *reduces* the defect surface: three independent walkthroughs of the same predicate, plus the `max_n`/`max_count` and `no segments` paths GLM added, cover every branch I left implicit.

One thing worth stating explicitly for the record (not a bug, but the question the reviewers were asked):

**Q2 — "Anything else that read the old threshold?"** — Full sweep:

*   `mine.py:126` `HOOK_PROMPT_VERSION` bumped, `CONVERSATION_TPM` 1.0→0.3, `is_conversation` rewritten — **changed**.
*   `stats.py:109-127` — **changed** (threshold proxy → ground truth, buckets now use `mine.CONVERSATION_TPM`).
*   `service.py:427` — **changed** (log text).
*   `providers.json:97` `paid_route.conversation_tpm: 1.0` — **intentionally not changed** per A42. Correct.
*   `contract.py`, `ledger.py`, `queue.py`, `providers.py`, `spend.py`, `downsignal.py`, `purge.py`, `ab.py`, `flagcheck.py`, `watch.py`, `fetch.py`, `coverage.py` — **no reference to `CONVERSATION_TPM` or `is_conversation`**. Verified by search.
*   Builder's `pp-selectid` `spotlight.CONVERSATION_TPM` — separate repo, separate ruling (orchestrator gave builder matching ruling). Not this diff's responsibility.

**No stale reader of the old threshold remains.**

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|-----------|---------|---------|-------------|
| `mine.py:is_conversation` | 10/10 | 10/10 | Unchanged — three reviewers, full input table, `bool` trap, rounding boundary all verified |
| `mine.py:episode_measure` | 9/10 | 10/10 | GLM closed the `no segments` and `minutes==0` paths I left open; no defect |
| `mine.py:mine_window` prompt/validator agreement | 8/10 (not scored) | 10/10 | GLM verified `max_n` vs `max_count` not confused; I had not checked |
| `stats.py:hooks_12h` | 10/10 | 10/10 | Unchanged — ground truth metric, buckets now correct (C1-1 fixed) |
| `service.py:hook_video` log | 10/10 | 10/10 | Unchanged |
| `providers.json:paid_route` | 10/10 | 10/10 | Correctly untouched per A42 |
| Version bump + rerun + cache | 10/10 | 10/10 | Unchanged — all three agreed |
| **Overall diff** | **Ready to merge** | **Ready to merge** | No new defect; C1 fixes applied |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL — none.** No input is skipped that should be asked, or asked that should be skipped. No stale threshold reader. No security or data-loss issue in the diff.

**P1 HIGH — none in the diff.** Pre-existing P1s recorded in consensus (state+event transaction, queue-depth alerts) remain out of scope.

**P2 MEDIUM — none in the diff.** The `n=-1` and `float n` paths I noted in cycle 1 are unreachable (`episode_measure` always produces `int` via `sum(len(...))`) and correctly fail open to "asked" anyway.

**C1 fixes verified:**
*   C1-1 `rows_by_episode` buckets at 0.3 with outcome labels — **fixed in 7c437fec**.
*   C1-2 rounding documented in design 13 — **fixed**.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

This diff is correct as-is; the highest-leverage thing it already does is failing open to "asked" on every unmarked or unmeasurable episode, because at $0.006 a video the cost of asking is nothing and the cost of missing an interview is the whole point.

## 7. PRODUCTION READY?

**Yes.** Ship `c1141fff` (with `7c437fec` C1 fixes). No conditions.

*   `is_conversation` implements exactly "skip only a marked episode under 0.3" — verified on 13 parametrized inputs including `bool`, `str`, `None`, `{}`, boundary `0.3`/`0.29`, and Pompliano `0.97`.
*   No other file reads the old threshold; `paid_route` intentionally retains `1.0` per A42.
*   `mine-hook/4` + `hooks --rerun` re-queues the 12h window; unchanged solo prompts hit cache (same `sha256(prompt)`).
*   `spotlight_asked_videos` counts ground truth (`spot_rows IS NOT NULL`), not a threshold proxy.
*   Suite: `tests/ingest` 311 passed.