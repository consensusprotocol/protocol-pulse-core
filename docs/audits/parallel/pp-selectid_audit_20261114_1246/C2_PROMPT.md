# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261114_1246
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 821 s finish=length usage in 23727 / out 24000 usd~0.431 (upper-bound price)

<critical>
None. The core mechanisms (per-pair deadlines, read-only breaker, parallel confirm) are sound as specified.

<medium>
M1 — deadline_table.py:104 — deadline can exceed 300 s. `min(CEIL_S, max(FLOOR_S, FACTOR*q))` clamps correctly, but the *stored* `p90` is unclamped and `text()` (deadline_table.py:143) prints it; cosmetic only. However the real issue: `percentile()` (line 75-80) with `q=0.9` on n=3 gives k=(2)(0.9)=1.8, interpolating between ranks 1 and 2 — for glm's records (5,9,12) p90 = 9+0.8×3 = 11.4 → deadline 17.1→floor 60. Fine. But for a pair with exactly MIN_N=3 where two answers are near-identical outliers, p90 interpolates *between* them, not the max; a genuinely slow 3rd answer can be underweighted. Not a violation of ruling 100's letter ("p90 of the pair's answered calls") but worth noting: the ruling's intent (deepseek 272→300) holds.

M2 — deadline_table.py:116 — staleness window. `0 <= (now - at).total_seconds() < RECOMPUTE_S` — a table computed *in the future* (clock skew, or `computed_at` written by a machine ahead) fails `0 <=` and forces recompute; that's fail-safe, good. But a table exactly 24 h old (diff 24×3600=86400.0) is recomputed — correct. No bug.

M3 — package.py:287-297 — confirm-ahead thread vs. main prescreen. `ahead.result()` is awaited in `finally` *after* the main prescreen completes (line 291-297), so the parallel verdicts are merged into the shared cache before `second_screen` runs later (line 317). But: if the main `prescreen` raises, `finally` still awaits `ahead.result()` — good, no orphan thread. However `ahead_pool.shutdown()` is called without `wait=True`... actually `ThreadPoolExecutor.shutdown()` defaults `wait=True` in 3.9+; and `ahead.result()` already blocks. No leak. But note: if `plan["parallel"]` is True and `confirm_ahead` raises *before* `prescreen` inside it, the exception is caught (package.py:255-257) and reported as `error` — the build continues, the second screen just re-asks. Fail-open, not fail-closed, but ruling 101 says "Grok's call is then not saved" — the extra spend is still reported via `tally.usd` in the error path (line 256). Honest.

M4 — package.py:229-231 — leading-leg selection. The filter's leading leg skips `name in getattr(router, "down", {})` and `router.breaker_open(name)`, but does NOT skip a leg whose breaker *opens mid-build*. If glm's breaker opens after `step_a_plan` but before the first screen actually runs, the estimate (glm 60 s) is stale; the real wait is deepseek's 300 s. The plan already committed to parallel/sequential. Concrete: 21 new moments, glm leads, est 120 s → sequential; glm then misses twice → breaker opens → the first screen waits 2×300 s on deepseek = 10 min, not 2. The build still completes; only the *estimate* is wrong. Ruling 101's rule is evaluated at plan time, so this is compliant, but the printed `est_wait_s` can mislead.

M5 — package.py:208 — `_Tally.call` — `rep_usd` read via `getattr(rep, "usage", None) or {}` — if a reply's `usage` is a non-dict truthy (e.g. a list), `.get` raises. Concrete: a back-end returning `usage=[1,2]` → `(getattr(rep,"usage",None) or {}).get` → AttributeError inside `_Tally.call`, which propagates out of `confirm_ahead`'s try (package.py:252-257) → caught, reported as error, verdicts lost. Fail-open, spend under-reported. Low likelihood.

M6 — package.py:270 — `prewarm_used` requires `b2.vendor != b1.vendor AND b2.family != b1.family`. Under heimdall_first, Heimdall families are their own vendors (ruling 85), so a Grok confirm (vendor "xai", family "grok") vs. a Heimdall first verdict (vendor "heimdall/deepseek", family "deepseek") → both differ → counted. But if the first verdict's back-end is *Grok itself* (chain [glm, ds, Grok] — Grok is the third leg), `prewarm_used` correctly excludes it (b2.vendor == b1.vendor). Matches the ruling's "a moment whose first verdict came from Grok itself is screened off it as before." Correct.

M7 — providers.py:362 — `import deadline_table as DT` inside `role_deadline` — a per-call import; Python caches it, negligible. But `self.deadlines` may be `None` (test line 791: `self.router(None)`); `DT.deadline(None, ...)` returns None → falls back to gateway 120. Fail-safe. Good.

M8 — proof_ledger.py:427 — extra spend = `usd × (asked - used) / max(1, asked)`. If `asked=0` (no new moments but parallel somehow true — impossible since parallel requires >20 new), the guard `max(1, asked)` prevents div-by-zero. But if `confirm_ahead` errored, `par` has no `used` key → `par.get("used", 0) or 0` → 0, so extra = full `usd`. Honest.

M9 — test_medley.py:516 — `self.assertIsNone(rig.screen_deadlines[0])` for BOTH routings. Under "today" the old code also passed None (the old ternary: `{"batch":..., "deadline_s": SECOND_VERDICT_DEADLINE_S} if heimdall_first else {}`), so "today" was already None. The updated test now asserts None

## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 71 s finish=stop usage in 23183 / out 236 usd~0.122 (upper-bound price)

<medium>pipeline/package.py:286 (plan = step_a_plan(...)); concrete sequence: >20 new moments, leading leg=heimdall:ds (dl=300s from table row, breaker closed), rounds=4 (37 new, batch=2, workers=6) yields est_wait_s=1200 > 600 so parallel=True; if first prescreen raises before cleared computed, finally does ahead.result() but par["used"] never set (remains 0 in "parallel_101" dict written to output).</medium>
<medium>pipeline/deadline_table.py:235 (wait = rounds * dl if dl else 0.0); concrete sequence: leading leg has no row + no gateway verdict_deadline_s (e.g. grok on verdict role under heimdall_first), dl=None, wait=0 even if table row exists and p90*1.5 would be 180; plan["est_wait_s"]=0 forces sequential (matches ruling but estimate ignores table row).</medium>

SHIP: yes with conditions (document the unset-"used" edge and grok-leg wait=0 case in proof_ledger)

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 108 s finish=stop usage in 26291 / out 7223 usd~0.187 (upper-bound price)

I’ll walk through the diff against the rulings and the “unchanged code” facts, focusing on the four attack vectors.

### <critical> Findings

**1. Ruling 101 Parallelism Can Corrupt the Shared Step-A Cache (Race Condition)**
*   **File:** `pipeline/package.py` (lines 286-297 in diff, `build` function) and `pipeline/package.py` (`prescreen` / `_cache_put`).
*   **Sequence:**
    1.  `build` detects `plan["parallel"]` is True.
    2.  It submits `confirm_ahead` to a `ThreadPoolExecutor` (thread A).
    3.  It immediately calls `prescreen` for the first screen (thread B, the main build thread).
    4.  `confirm_ahead` calls `prescreen` with `kind="step_a_second"` and `cache=step_a_cache`.
    5.  The main `prescreen` calls `prescreen` with `kind="step_a_first"` and `cache=step_a_cache`.
    6.  Both threads execute `prescreen`. Inside `prescreen`, when a verdict is obtained, it calls `_cache_put` (or equivalent logic to merge into the shared cache file).
    7.  The prompt states: *"The cache is merged by _cache_put (:475) under CACHE_LOCK (:456), re-reading the file inside the lock, so two prescreens in one process cannot lose each other's verdicts."*
    8.  **However**, `confirm_ahead` uses a `_Tally` wrapper around the router. While `_Tally` proxies `call`, the `prescreen` function itself handles the cache I/O. If `CACHE_LOCK` is a global lock in `package.py`, this is safe. **BUT**, look at `confirm_ahead` (line 252): it passes `store=None`. The main `prescreen` (line 291) passes `store=store`.
    9.  The critical issue is not the lock, but the **keying**. The prompt says: *"Verdicts are cached... keyed by moment, text, context and prompt version, per back-end."*
    10. `confirm_ahead` runs `step_a_second`. The main screen runs `step_a_first`.
    11. If the cache key includes the `kind` (step_a_first vs step_a_second), they are distinct entries. If the cache key does *not* include the kind, but relies on the backend/vendor, there is a risk.
    12. Let's look closer at the "Unchanged Code" fact: *"package.second_screen (:682) calls prescreen per group... kind step_a_second... through the cache lookup it reuses a cached verdict from any back-end off those sets."*
    13. The `confirm_ahead` function (line 241) is designed to populate the cache *before* the second screen runs. It uses `kind="step_a_second"`.
    14. **The Race:** The main thread is running `step_a_first`. The background thread is running `step_a_second`. They are writing to the *same* `step_a_cache` file.
    15. The prompt asserts `_cache_put` is thread-safe via `CACHE_LOCK`. If this is true, the *file* integrity is preserved.
    16. **However**, there is a logical flaw in `confirm_ahead`'s exclusion logic. It excludes Heimdall vendors/families from the writer sets (`set(wv) | hv`, `set(wf) | hf`). This forces the `step_a_second` prescreen to use non-Heimdall backends (e.g., Grok).
    17. The main `step_a_first` prescreen uses the standard writer sets (`wv`, `wf`), which under `heimdall_first` routing, likely *includes* Heimdall backends (since Heimdall is the filter).
    18. So, Thread A writes Grok's `step_a_second` verdicts. Thread B writes Heimdall's `step_a_first` verdicts.
    19. Later, `second_screen` runs. It looks for `step_a_second` verdicts off the *first* verdict's vendor.
    20. If the first verdict was Heimdall (from Thread B), `second_screen` looks for a non-Heimdall `step_a_second` verdict. It finds the one written by Thread A (`confirm_ahead`).
    21. **Is this safe?** The prompt says: *"A clip passes only if BOTH pass (unchanged)."*
    22. **The Critical Bug:** `confirm_ahead` runs on **ALL** new moments (`plan["new"]`). The main `prescreen` also runs on **ALL** moments (`ms`).
    23. If a moment fails the `step_a_first` screen (Thread B), it is removed from `cleared`. It never reaches `second_screen`.
    24. However, `confirm_ahead` (Thread A) *already* spent money and time asking Grok for a `step_a_second` verdict on that moment, and wrote it to the cache.
    25. This is a **waste of spend** (reported as "extra spend"), but is it a **correctness** failure?
    26. The prompt says: *"Grok's call is then not saved, and you report the extra spend per build."* Wait, the ruling says *"Grok's call is then not saved"*? No, Ruling 101 says: *"Grok's call is then not saved"* is **NOT** in the text. The text says: *"Grok's call is then not saved"* is my misreading. Let's re-read Ruling 101: *"Grok's call is then not saved"* is **not** there. It says: *"Grok's call is then not saved"*... actually, the ruling says: *"Grok's call is then not saved"* is **incorrect**. The ruling says: *"Grok's call is then not saved"*... I am hallucinating the text.
    27. Let's look at the actual Ruling 101 text provided: *"Grok's call is then not saved"* is **not** in the text. The text says: *"Grok's call is then not saved"*...


## CLAUDE'S CYCLE 1 CONSENSUS
# Audit 20261114_1246 (the orchestrator's 12:16 rulings 100, deadlines follow the model, and 101, step A in parallel), cycle 1: consensus

Reviewers:
- grok-4.20: SHIP yes with conditions. Two <medium>, both documented edges (below), no code finding.
- qwen3.8-27b: SHIP no. One <critical> that resolves inside its own text, one <high> and one <medium>, both refuted
  below with the ruling's words and the code.
- glm-5.3-flash (821 s, finish=length at its 24,000 cap): no <critical>; 48 <medium> notes. One is a real
  defect (M27), fixed; three hardenings taken (M5, M11, M37). See the addendum at the end.

## grok's conditions (documented, no change)

- "If the first screen raises, par['used'] stays 0". Then the build itself raises: the exception leaves the `try`
  after the confirm-ahead is joined in `finally`, and no report line is printed for a build that did not finish. A 0
  can only be printed for a build that finished without reaching the second screen. In that case it is TRUE: no
  confirm-ahead verdict was used, and all of its spend is the extra.
- "A leading leg with no deadline (Grok) gives wait 0, so sequential". That is the ruling: the filter worth parallelising
  is Heimdall's slow one. When Grok leads the first screen it answers in its own time (median 46 s, n 268), and
  step_a_plan's docstring says so. The build's line then prints the leg ("on xai:grok") and the 0, so it reads plainly.

## Refuted, with evidence

- qwen <high>: "the ruling says 'Grok's call is then not saved', and the code saves Grok's verdicts to the cache".
  - The sentence is about money: "Grok's call is then not saved, and you report the extra spend per build".
  - The saving it names is the sequential order's: Grok is asked only on a filter pass, so a moment the filter fails
    costs no Grok call. In parallel that saving is not made, and the build reports what it cost
    (proof_ledger.ruling_101_line: usd x unused / asked).
  - The verdict itself goes to the shared step-A cache, because that is how the unchanged second screen reads it.
    Verdicts are paid once (ruling 58).
- qwen <medium>: "confirm_ahead can spend past ruling 48's cap with no mid-build check".
  - Every confirm-ahead call goes through Router.call: _Tally.call delegates to the router's own call. Before any paid
    call, Router.call reserves the call's upper bound (_reserve), which raises SpendLimit when spent + reserved + this
    call would pass the limit (unchanged code).
  - The cap is checked per call, in parallel threads alike (the reservation is under the ledger's lock).
- qwen <critical>: "the two prescreens race on the cache". Its own trace concedes the lock: _cache_put re-reads and
  merges under CACHE_LOCK.
  - What remains in its text is the "orphaned" Grok verdict on a moment the filter fails: exactly the extra spend that
    is reported.
  - Its reuse in a later build as that moment's FIRST verdict is not new. Grok's verdicts from the first screen's own
    fallback (the step_a

---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_20261114_1246/C2_STEP.diff (920 lines)
```
   1 | diff --git a/pipeline/circuit_breaker.py b/pipeline/circuit_breaker.py
   2 | index 868dc78..459d79d 100644
   3 | --- a/pipeline/circuit_breaker.py
   4 | +++ b/pipeline/circuit_breaker.py
   5 | @@ -112,6 +112,25 @@ def allow(name, path=STATE, now=None, hold_s=None):
   6 |          return True, "trial"
   7 |  
   8 |  
   9 | +def is_open(name, path=STATE, now=None):
  10 | +    """READ ONLY (it never claims a trial): would allow() skip `name` now? Its window open, or its one trial in flight.
  11 | +    RULING 101's estimate of the filter's wait reads it. An unreadable state skips nothing: False."""
  12 | +    now = _now(now)
  13 | +    try:
  14 | +        with _Locked(path):
  15 | +            s = _load(path)
  16 | +    except (BreakerUnreadable, OSError):
  17 | +        return False
  18 | +    m = s["models"].get(name)
  19 | +    until = _t(m.get("open_until")) if isinstance(m, dict) else None
  20 | +    if until is None:
  21 | +        return False
  22 | +    if now < until:
  23 | +        return True
  24 | +    ta, tu = _t(m.get("trial_at")), _t(m.get("trial_until"))
  25 | +    return ta is not None and now < (tu or ta + timedelta(seconds=TRIAL_HOLD_S))
  26 | +
  27 | +
  28 |  def record(name, outcome, path=STATE, now=None, deadline_s=None, seconds=None, tokens=None, max_out=None):
  29 |      """One live call's outcome: "answer", "miss" (its deadline passed) or "runaway" (more than RUNAWAY_X times the cap
  30 |      it was sent). -> the event for the evidence file ({"kind": "breaker_open" | "breaker_close", "model", "why",
  31 | diff --git a/pipeline/deadline_table.py b/pipeline/deadline_table.py
  32 | new file mode 100644
  33 | index 0000000..b2068d7
  34 | --- /dev/null
  35 | +++ b/pipeline/deadline_table.py
  36 | @@ -0,0 +1,118 @@
  37 | +"""RULING 100 (orchestrator 12:16 ET Nov 14): DEADLINES FOLLOW THE MODEL, NOT ONE NUMBER. Per (model, verdict type) the
  38 | +deadline is the recorded p90 of that pair's answered calls x FACTOR (1.5), floor FLOOR_S (60 s), ceiling CEIL_S (300 s),
  39 | +recomputed from the records daily; ruling 99's "two misses in a row" is against THAT deadline.
  40 | +
  41 | +- The records: this builder's recorded exchanges (providers.Router's record_dir: one JSON per ANSWERED call, with its
  42 | +  role, back-end and seconds). A pair with fewer than MIN_N answered calls has no row, and its gateway's configured
  43 | +  deadline stands (ruling 82's 120 s on Heimdall).
  44 | +- The table lives in a JSON file with its computed_at; load() recomputes it when it is missing, unreadable or older
  45 | +  than RECOMPUTE_S (a day); with no record dir it is computed (empty) and never saved over a good one. The Router
  46 | +  applies a verdict pair's row only where a deadline applies today (the caller's, or the gateway's configured one:
  47 | +  Heimdall), in place of that number; where none applies (Grok's second screen, a writer), none is added
  48 | +  (providers.Router.effective_deadline).
  49 | +- Measured at 12:2x ET Nov 14: deepseek's step A, 32 answers, median 166 s, p90 273 s -> 300 s (the ceiling); glm's step
  50 | +  A, 3 answers, p90 39 s -> 60 s (the floor), which its 483-532 s runs still miss."""
  51 | +import glob
  52 | +import json
  53 | +import math
  54 | +import os
  55 | +from datetime import datetime, timezone
  56 | +
  57 | +STATE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests", "package", "proof",
  58 | +                     "DEADLINE_TABLE.json")
  59 | +FACTOR, FLOOR_S, CEIL_S = 1.5, 60.0, 300.0      # ruling 100
  60 | +MIN_N = 3                                      # a pair needs this many answered calls for a row of its own
  61 | +RECOMPUTE_S = 24 * 3600                        # ruling 100: "recomputed from the records daily"
  62 | +RULE = "p90 of the pair's recorded answered calls x 1.5, floor 60 s, ceiling 300 s (ruling 100)"
  63 | +
  64 | +
  65 | +def _iso(t):
  66 | +    return t.strftime("%Y-%m-%dT%H:%M:%SZ")
  67 | +
  68 | +
  69 | +def _t(s):
  70 | +    try:
  71 | +        t = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
  72 | +    except (TypeError, ValueError):
  73 | +        return None
  74 | +    return t if t.tzinfo is not None else None
  75 | +
  76 | +
  77 | +def percentile(xs, q):
  78 | +    """Linear interpolation between the closest ranks (numpy's default)."""
  79 | +    xs = sorted(xs)
  80 | +    k = (len(xs) - 1) * q
  81 | +    lo, hi = math.floor(k), math.ceil(k)
  82 | +    return xs[lo] if lo == hi else xs[lo] + (xs[hi] - xs[lo]) * (k - lo)
  83 | +
  84 | +
  85 | +def compute(record_dir, now=None):
  86 | +    """-> {"computed_at", "rule", "rows": {"<back-end>|<role>": {"n", "p50", "p90", "deadline_s"}}} from every recorded
  87 | +    exchange in record_dir (a file that cannot be read, is not an object, or has no back-end, role or positive seconds,
  88 | +    is skipped). No record_dir: no rows (never the current directory's files)."""
  89 | +    now = now or datetime.now(timezone.utc)
  90 | +    seconds = {}
  91 | +    for p in glob.glob(os.path.join(record_dir, "*", "*.json")) if record_dir else ():
  92 | +        try:
  93 | +            with open(p) as f:
  94 | +                r = json.load(f)
  95 | +        except (OSError, ValueError):
  96 | +            continue
  97 | +        if not isinstance(r, dict):
  98 | +            continue
  99 | +        b, role, s = r.get("backend"), r.get("role"), r.get("seconds")
 100 | +        if isinstance(b, str) and isinstance(role, str) and isinstance(s, (int, float)) and not isinstance(s, bool) \
 101 | +                and math.isfinite(s) and s > 0:
 102 | +            seconds.setdefault(f"{b}|{role}", []).append(float(s))
 103 | +    rows = {}
 104 | +    for key, xs in sorted(seconds.items()):
 105 | +        if len(xs) < MIN_N:
 106 | +            continue
 107 | +        q = percentile(xs, 0.9)
 108 | +        rows[key] = {"n": len(xs), "p50": round(percentile(xs, 0.5), 1), "p90": round(q, 1),
 109 | +                     "deadline_s": round(min(CEIL_S, max(FLOOR_S, FACTOR * q)), 1)}
 110 | +    return {"computed_at": _iso(now), "rule": RULE, "rows": rows}
 111 | +
 112 | +
 113 | +def load(path=STATE, record_dir=None, now=None):
 114 | +    """The table: the saved one while it is younger than RECOMPUTE_S, else computed again from record_dir and saved
 115 | +    (a save that fails leaves the computed table in use). -> the table dict."""
 116 | +    now = now or datetime.now(timezone.utc)
 117 | +    try:
 118 | +        with open(path) as f:
 119 | +            t = json.load(f)
 120 | +        at = _t(t.get("computed_at")) if isinstance(t, dict) else None
 121 | +        if at is not None and 0 <= (now - at).total_seconds() < RECOMPUTE_S and isinstance(t.get("rows"), dict):
 122 | +            return t
 123 | +    except (OSError, ValueError):
 124 | +        pass
 125 | +    t = compute(record_dir, now)
 126 | +    if not record_dir:                                   # nothing to compute from: never overwrite a saved table
 127 | +        return t
 128 | +    try:
 129 | +        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
 130 | +        tmp = f"{path}.{os.getpid()}.tmp"
 131 | +        with open(tmp, "w") as f:
 132 | +            json.dump(t, f, indent=1)
 133 | +        os.replace(tmp, path)
 134 | +    except OSError:
 135 | +        pass
 136 | +    return t
 137 | +
 138 | +
 139 | +def deadline(table, backend, role):
 140 | +    """The pair's own deadline in seconds, inside FLOOR_S..CEIL_S whatever the file says (a hand-edited or older table
 141 | +    included: glm, audit 20261114_1246 C1), or None when the table has no row for it."""
 142 | +    row = ((table or {}).get("rows") or {}).get(f"{backend}|{role}") if isinstance(table, dict) else None
 143 | +    d = row.get("deadline_s") if isinstance(row, dict) else None
 144 | +    if not (isinstance(d, (int, float)) and not isinstance(d, bool) and math.isfinite(d) and d > 0):
 145 | +        return None
 146 | +    return min(CEIL_S, max(FLOOR_S, float(d)))
 147 | +
 148 | +
 149 | +def text(table, applies=None):
 150 | +    """The table in one line, for STATE (ruling 100: "say the table on STATE once"); applies(key) keeps the rows a
 151 | +    Router would use (the build passes the Heimdall verdict pairs)."""
 152 | +    rows = {k: v for k, v in ((table or {}).get("rows") or {}).items() if applies is None or applies(k)}
 153 | +    return "; ".join(f"{k.split('|')[0].split('/')[-1]} {k.split('|')[1]}: {v['deadline_s']:g} s (n {v['n']}, p50 "
 154 | +                     f"{v['p50']:g}, p90 {v['p90']:g})" for k, v in sorted(rows.items()))
 155 | diff --git a/pipeline/package.py b/pipeline/package.py
 156 | index d542ae5..7825b27 100644
 157 | --- a/pipeline/package.py
 158 | +++ b/pipeline/package.py
 159 | @@ -492,7 +492,7 @@ def src_of(x, sources):
 160 |  
 161 |  
 162 |  def prescreen(router, ms, sources, ctx, writer_vendor, writer_family=None, n=PRESCREEN_N, batch=PRESCREEN_BATCH,
 163 | -              store=None, log=print, cache=None, deadline_s=None, kind="step_a_first", failover=None):
 164 | +              store=None, log=print, cache=None, deadline_s=None, kind="step_a_first", failover=None, plan_only=False):
 165 |      """Step A (context only, package-independent by law L-s): ({moment_id: A item}, {moment_id: [failing rules]},
 166 |      {vendor}, {family}). RULING 58 (11:00 Nov 13): n None (the default) screens EVERY usable moment, the miner's best
 167 |      first (rank_score); a number keeps the old cap (distinct channels first). Each moment is paid for ONCE: a verdict
 168 | @@ -501,7 +501,8 @@ def prescreen(router, ms, sources, ctx, writer_vendor, writer_family=None, n=PRE
 169 |      context step A reads (its window, title, channel, publish time and the show date, so time words are judged again on
 170 |      a new show date) and the step-A prompt's version. The batches run in parallel (PRESCREEN_WORKERS), each with the
 171 |      seed of its place in the queue. Only a parsed verdict is stored: a call that fails is no verdict (law L-m), never
 172 | -    remembered. writer_vendor / writer_family: of the writers, so step A never runs on them."""
 173 | +    remembered. writer_vendor / writer_family: of the writers, so step A never runs on them. plan_only (ruling 101):
 174 | +    no call is made; -> the moments this screen would ask (no verdict in the ledger or the cache), nothing written."""
 175 |      import providers as P
 176 |      ranked = sorted(ms, key=lambda m: (-m["rank_score"], m["moment_id"]))
 177 |      if n is None:
 178 | @@ -539,6 +540,8 @@ def prescreen(router, ms, sources, ctx, writer_vendor, writer_family=None, n=PRE
 179 |              families.add(b.family)
 180 |          else:
 181 |              todo.append(m)
 182 | +    if plan_only:                                        # ruling 101: what this screen would ask, nothing asked
 183 | +        return todo
 184 |      chunks = [todo[i:i + batch] for i in range(0, len(todo), batch)]
 185 |  
 186 |      def screen(i, chunk):
 187 | @@ -578,11 +581,103 @@ def prescreen(router, ms, sources, ctx, writer_vendor, writer_family=None, n=PRE
 188 |  def first_bounds(router):
 189 |      """The kwargs of step A's FIRST screen. RULING 85: under heimdall_first the first verdict is a Heimdall family's,
 190 |      2 clips and 120 s a call (Heimdall needs a median 268 s on 8 clips); today it keeps its batches with no deadline.
 191 | -    One helper for both builds (the medley's and the spotlight's)."""
 192 | +    RULING 100 (12:16 Nov 14): the Router replaces the 120 s with each leg's own deadline where it has a row
 193 | +    (providers.Router.effective_deadline). One helper for both builds (the medley's and the spotlight's)."""
 194 |      return {"batch": SECOND_VERDICT_BATCH, "deadline_s": SECOND_VERDICT_DEADLINE_S} \
 195 |          if getattr(router, "routing", "today") == "heimdall_first" else {}
 196 |  
 197 |  
 198 | +STEP_A_PARALLEL_NEW = 20           # RULING 101 (12:16 Nov 14): over 20 new moments to screen, AND
 199 | +STEP_A_PARALLEL_WAIT_S = 600.0     # the filter would hold the build over 10 minutes: Grok's confirm goes in parallel
 200 | +
 201 | +
 202 | +class _Tally:
 203 | +    """A router seen through one task (ruling 101's confirm-ahead): every reply's vendor-reported dollars (else its
 204 | +    estimate) summed; everything else is the router's own."""
 205 | +
 206 | +    def __init__(self, router):
 207 | +        self._r, self.usd, self.calls = router, 0.0, 0
 208 | +        self._lock = threading.Lock()
 209 | +
 210 | +    def call(self, *a, **k):
 211 | +        rep = self._r.call(*a, **k)
 212 | +        u = getattr(rep, "usage", None)
 213 | +        rep_usd = u.get("usd_reported") if isinstance(u, dict) else None
 214 | +        with self._lock:
 215 | +            self.calls += 1
 216 | +            self.usd += float(rep_usd) if isinstance(rep_usd, (int, float)) else float(getattr(rep, "usd", 0) or 0)
 217 | +        return rep
 218 | +
 219 | +    def __getattr__(self, name):
 220 | +        return getattr(self._r, name)
 221 | +
 222 | +
 223 | +def _heimdall(b):
 224 | +    """A Heimdall back-end, under either routing (providers.gateway: "heimdall" for every Heimdall family)."""
 225 | +    import providers as P
 226 | +    return P.gateway(b) == "heimdall"
 227 | +
 228 | +
 229 | +def step_a_plan(router, ms, sources, ctx, wv, wf, store=None, cache=None, **first):
 230 | +    """RULING 101 (12:16 Nov 14): does step A ask the Heimdall filter and Grok's confirm IN PARALLEL? Yes when more than
 231 | +    STEP_A_PARALLEL_NEW moments are NEW to the first screen (no verdict in this build's ledger or the shared cache) AND
 232 | +    the filter would hold the build longer than STEP_A_PARALLEL_WAIT_S: its rounds (the new moments' batches over
 233 | +    PRESCREEN_WORKERS) x the deadline of the filter's leading leg (the step_a_first chain's first back-end off the
 234 | +    writers, not down and not breaker-open, at ruling 100's deadline for it: Router.effective_deadline). The filter is
 235 | +    Heimdall's: when no Heimdall family leads (Grok leads: every family is the writer's, down or breaker-open), the first
 236 | +    verdicts are Grok's own, which a confirm off Heimdall could never serve: sequential, whatever the wait.
 237 | +    -> {"parallel", "new": [moments], "n_new", "est_wait_s", "leg"}."""
 238 | +    new = prescreen(router, ms, sources, ctx, wv, wf, store=store, cache=cache, plan_only=True,
 239 | +                    **{k: v for k, v in first.items() if k in ("batch", "kind")})
 240 | +    if len(new) <= STEP_A_PARALLEL_NEW:                  # under the line: sequential whatever the wait
 241 | +        return {"parallel": False, "new": new, "n_new": len(new), "est_wait_s": None, "leg": None}
 242 | +    leg, dl, heim = None, None, False
 243 | +    for name in router.chain("context_verdict", kind="step_a_first"):
 244 | +        b = router.backends.get(name)
 245 | +        if b is None or b.vendor in set(wv) or b.family in set(wf) or name in getattr(router, "down", {}) or \
 246 | +                (hasattr(router, "breaker_open") and router.breaker_open(name)):
 247 | +            continue
 248 | +        leg, dl, heim = name, router.effective_deadline("context_verdict", b, first.get("deadline_s")), _heimdall(b)
 249 | +        break
 250 | +    batch = first.get("batch") or PRESCREEN_BATCH
 251 | +    rounds = math.ceil(math.ceil(len(new) / batch) / PRESCREEN_WORKERS) if new else 0
 252 | +    wait = rounds * dl if dl else 0.0
 253 | +    return {"parallel": heim and len(new) > STEP_A_PARALLEL_NEW and wait > STEP_A_PARALLEL_WAIT_S, "new": new,
 254 | +            "n_new": len(new), "est_wait_s": round(wait, 1), "leg": leg}
 255 | +
 256 | +
 257 | +def confirm_ahead(router, new, sources, ctx, wv, wf, log=print, cache=None):
 258 | +    """RULING 101: Grok's confirm asked AT ONCE on every new moment, beside the Heimdall filter: each one's step_a_second
 259 | +    verdict, off every Heimdall family and off the writers, into the step-A cache that the second screen reads later
 260 | +    (it then reuses the verdict off the first's vendor; 'a clip passes only if BOTH pass' is unchanged, and a moment
 261 | +    whose first verdict came from Grok itself is screened off it as before). -> {"asked", "verdicts", "usd", "calls",
 262 | +    "by": {moment id: back-end}}: the spend is reported per build (a verdict the second screen cannot use is extra)."""
 263 | +    hv = {b.vendor for b in router.backends.values() if _heimdall(b)}
 264 | +    hf = {b.family for b in router.backends.values() if _heimdall(b)}
 265 | +    tally = _Tally(router)
 266 | +    try:
 267 | +        got, _fails, _, _ = prescreen(tally, new, sources, ctx, set(wv) | hv, set(wf) | hf, n=len(new), store=None,
 268 | +                                      log=log, cache=cache, batch=PRESCREEN_BATCH, deadline_s=None,
 269 | +                                      kind="step_a_second", failover=True)
 270 | +    except Exception as e:                               # noqa: BLE001 (the sequential second screen still runs)
 271 | +        return {"asked": len(new), "verdicts": 0, "usd": round(tally.usd, 4), "calls": tally.calls,
 272 | +                "error": f"{type(e).__name__}: {str(e)[:160]}"}
 273 | +    return {"asked": len(new), "verdicts": len(got), "usd": round(tally.usd, 4), "calls": tally.calls,
 274 | +            "by": {mid: a.get("backend") for mid, a in got.items() if isinstance(a, dict)}}
 275 | +
 276 | +
 277 | +def prewarm_used(router, mids, a_by, pre_by):
 278 | +    """RULING 101: how many of `mids` (the moments reaching the second screen) the confirm-ahead served: it has a
 279 | +    verdict for the moment AND that verdict is off the moment's first verdict's vendor and family (the second screen
 280 | +    reads only such a verdict; a moment whose first verdict came from Grok itself is screened off it as before)."""
 281 | +    n = 0
 282 | +    for mid in mids:
 283 | +        b1 = router.backends.get((a_by.get(mid) or {}).get("backend"))
 284 | +        b2 = router.backends.get(pre_by.get(mid))
 285 | +        n += b1 is not None and b2 is not None and b2.vendor != b1.vendor and b2.family != b1.family
 286 | +    return n
 287 | +
 288 | +
 289 |  def _second_bounds(router):
 290 |      """(batch, deadline_s) of step A's second verdict. Today it is a Heimdall family's (ruling 82: 2 clips, 120 s a
 291 |      call). RULING 88 (c), under heimdall_first, it is Grok confirming a Heimdall pass: Grok's own batch (8 clips) and no
 292 | @@ -2386,9 +2481,21 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 293 |      ad_read = ad_read_out(ms, sources)                # the exclusion screen's free part, BEFORE the angle is built
 294 |      ms = [m for m in ms if m["moment_id"] not in ad_read]     # around a moment it refuses (the 03:39 build's hook)
 295 |      wv, wf = _writers(router)
 296 | -    a_by, fails, a_vendors, a_families = prescreen(router, ms, sources, ctx, wv, wf, store=store, log=log,
 297 | -                                                   cache=step_a_cache, kind="step_a_first",   # ruling 85 / 88 (c)
 298 | -                                                   **first_bounds(router))
 299 | +    fb = first_bounds(router)
 300 | +    plan = step_a_plan(router, ms, sources, ctx, wv, wf, store=store, cache=step_a_cache, **fb)   # RULING 101
 301 | +    ahead_pool = ThreadPoolExecutor(max_workers=1) if plan["parallel"] else None
 302 | +    ahead = ahead_pool.submit(confirm_ahead, router, plan["new"], sources, ctx, wv, wf, log, step_a_cache) \
 303 | +        if ahead_pool is not None else None              # Grok's confirm beside the Heimdall filter, at once
 304 | +    par = {**{k: plan[k] for k in ("parallel", "n_new", "est_wait_s", "leg")}, "used": 0}
 305 | +    try:
 306 | +        a_by, fails, a_vendors, a_families = prescreen(router, ms, sources, ctx, wv, wf, store=store, log=log,
 307 | +                                                       cache=step_a_cache, kind="step_a_first",   # ruling 85 / 88 (c)
 308 | +                                                       **fb)
 309 | +    finally:
 310 | +        if ahead is not None:
 311 | +            par.update(ahead.result())
 312 | +            ahead_pool.shutdown()
 313 | +    pre_by = par.pop("by", None) or {}                   # which back-end confirmed each moment ahead (not reported)
 314 |      cleared = {m["moment_id"]: m for m in ms if m["moment_id"] in a_by and not fails.get(m["moment_id"])}
 315 |      levels = current_levels(sources.values(), ctx)
 316 |      out = {"shape": "medley", "packages": [], "tried": [], "unusable": why, "usable": n_usable, "current_levels": levels,
 317 | @@ -2396,7 +2503,8 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 318 |             "reposted": reposted,
 319 |             "scorer": dict(scorer["record"], admitted=admitted, trims_affirmed=sorted(trims), trims_out=trim_out),
 320 |             "prescreen": {"screened": len(fails), "cleared": len(cleared),
 321 | -                         "failed": {mid: f for mid, f in fails.items() if f}}, "angles": [], "takeaways": [],
 322 | +                         "failed": {mid: f for mid, f in fails.items() if f}, "parallel_101": par},
 323 | +           "angles": [], "takeaways": [],
 324 |             "package": None}
 325 |      log(f"  {n_usable} usable, {len(reposted)} of them the same speech re-posted by a second channel (ruling 53: "
 326 |          f"the original publisher's kept), {len(no_role)} left out by the render's STAND_ALONE (an opener the clip scorer "
 327 | @@ -2487,6 +2595,7 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 328 |                        f"{b['why']}" for b in best) if openers else
 329 |              "no cleared, cuttable moment can open (hook eligibility, G17a, the render's hook rule)"))
 330 |          return out
 331 | +    par["used"] = prewarm_used(router, cleared, a_by, pre_by)    # ruling 101: the confirm-ahead verdicts it reads
 332 |      a_two, off_fail = second_screen(router, cleared, a_by, sources, ctx, log=log,
 333 |                                      cache=step_a_cache)                  # ORDER 06:22 item 45
 334 |      out["prescreen"]["second_vendor"] = {mid: f"PASS ({a_two[mid][1].get('backend')})" if mid in a_two else
 335 | diff --git a/pipeline/providers.py b/pipeline/providers.py
 336 | index 36ece53..1b9a14b 100644
 337 | --- a/pipeline/providers.py
 338 | +++ b/pipeline/providers.py
 339 | @@ -720,7 +720,7 @@ class Router:
 340 |      def __init__(self, config=CONFIG, env_path=None, record_dir=None, replay=False, spend_path=None, limit_usd=40.0,
 341 |                   local_llm=None, chains=None, limit_basis="estimate", deadline_log=None, slow_log_s=240.0,
 342 |                   routing=None, shadow=None, shadow_log=None, health=None, plan_b_chains=None, state_md=None,
 343 | -                 breakers=None):
 344 | +                 breakers=None, deadlines=None):
 345 |          with open(config) as f:
 346 |              self.config = json.load(f)
 347 |          rt = self.config.get("routing") or {}
 348 | @@ -759,6 +759,8 @@ class Router:
 349 |          # its deadline twice in a row, or runs past twice the cap it was sent, is skipped by every list for 30 minutes
 350 |          # (live calls only: a recorded reply, replay, probes and shadow calls never touch it)
 351 |          self.breakers, self.breaker_events = breakers, []
 352 | +        # RULING 100 (12:16 Nov 14): the per-(model, verdict type) deadlines (pipeline/deadline_table.py's table)
 353 | +        self.deadlines = deadlines
 354 |          if self.routing == "heimdall_first":      # RULING 85: the two-family rule is kept INSIDE Heimdall, so each of
 355 |              for b in self.backends.values():      # its families is its own maker for every vendor rule (law L-s); the
 356 |                  if isinstance(b, HeimdallBackend):     # gateway stays "heimdall" (gateway(b))
 357 | @@ -1005,7 +1007,7 @@ class Router:
 358 |      def role_deadline(self, role, b):
 359 |          """The 20:33 order (ruling 82's chain on the verdicts): a call of a verdict role on a back-end whose gateway
 360 |          names a deadline (model_providers.json routing.verdict_deadline_s, e.g. {"heimdall": 120}) gets it when the
 361 | -        caller sets none. -> seconds or None."""
 362 | +        caller sets none. -> seconds or None. (Ruling 100's per-model deadline: effective_deadline.)"""
 363 |          rt = self.config.get("routing") or {}
 364 |          bounded = set(rt.get("verdict_roles") or ())
 365 |          if self.routing == "today":                   # step A's first screen and step C keep no deadline today:
 366 | @@ -1015,6 +1017,20 @@ class Router:
 367 |          d = (rt.get("verdict_deadline_s") or {}).get(gateway(b))
 368 |          return float(d) if _num(d) and d > 0 else None
 369 |  
 370 | +    def effective_deadline(self, role, b, deadline_s=None):
 371 | +        """RULING 100 (12:16 Nov 14): DEADLINES FOLLOW THE MODEL, NOT ONE NUMBER. The deadline a live call of `role` on
 372 | +        `b` gets: where one applies (the caller's, else the role's: role_deadline), a verdict role takes the pair's own
 373 | +        row of the deadline table instead (p90 of its recorded answers x 1.5, 60-300 s), so step A's first screen keeps a
 374 | +        bound on every leg (deepseek 300 s, glm 60 s, Grok its own); without a row, the number that applied. Where no
 375 | +        deadline applies (a Heimdall-less second screen's Grok, any writer), none does now either. -> seconds or None."""
 376 | +        dl = deadline_s or self.role_deadline(role, b)
 377 | +        if dl and role in set((self.config.get("routing") or {}).get("verdict_roles") or ()):
 378 | +            import deadline_table as DT
 379 | +            own = DT.deadline(self.deadlines, b.name, role)
 380 | +            if own is not None:
 381 | +                dl = own
 382 | +        return dl
 383 | +
 384 |      def _breaker_live(self, role):
 385 |          """RULING 99: the breaker counts and skips only this builder's LIVE calls (never replay, a probe or a shadow)."""
 386 |          return bool(self.breakers) and not self.replay and not role.startswith(("probe87:", "shadow86:"))
 387 | @@ -1040,6 +1056,13 @@ class Router:
 388 |              return None
 389 |          return None if ok else why
 390 |  
 391 | +    def breaker_open(self, name):
 392 | +        """RULING 99, read only (ruling 101's wait estimate): whether a live call would skip `name` now."""
 393 | +        if not self.breakers:
 394 | +            return False
 395 | +        import circuit_breaker as CB
 396 | +        return CB.is_open(name, self.breakers)
 397 | +
 398 |      def _breaker(self, role, name, outcome, **kw):
 399 |          """RULING 99: one live call's outcome to the breaker; an open or a close is one line in the evidence file."""
 400 |          if not self._breaker_live(role):
 401 | @@ -1220,7 +1243,7 @@ class Router:
 402 |              if self.replay:
 403 |                  tried.append((name, "replay: not recorded"))
 404 |                  continue
 405 | -            dl = deadline_s or self.role_deadline(role, b)      # the caller's deadline, else the role's (20:33)
 406 | +            dl = self.effective_deadline(role, b, deadline_s)   # the caller's, else the role's (20:33): ruling 100's
 407 |              if dl and _num(b.spec.get("deadline_floor_s")):     # ruling 87: the local judge waits out a render
 408 |                  dl = max(dl, float(b.spec["deadline_floor_s"]))
 409 |              bwhy = self._breaker_allow(role, name, dl)          # ruling 99: an open breaker skips it; the next leads
 410 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
 411 | index ac9acba..b6bd9ae 100644
 412 | --- a/tests/package/proof_ledger.py
 413 | +++ b/tests/package/proof_ledger.py
 414 | @@ -58,6 +58,7 @@ import eligibility as E  # noqa: E402
 415 |  import candidates as CA  # noqa: E402
 416 |  import heimdall_health as HH  # noqa: E402
 417 |  import circuit_breaker as CB  # noqa: E402
 418 | +import deadline_table as DT  # noqa: E402
 419 |  import shadow86 as SH  # noqa: E402
 420 |  import ledger_build as LB  # noqa: E402
 421 |  import moments as M  # noqa: E402
 422 | @@ -104,12 +105,49 @@ def delivered_pins(paths):
 423 |  
 424 |  def build_router(routing, shadow, shadow_log):
 425 |      """The build's router: ruling 48's ledger and limit, the routing's chains (frozen legs out), the evidence file
 426 | -    (item 55), ruling 86's shadow, ruling 87's shared Heimdall health and Plan B chains, ruling 99's circuit breaker."""
 427 | +    (item 55), ruling 86's shadow, ruling 87's shared Heimdall health and Plan B chains, ruling 99's circuit breaker,
 428 | +    ruling 100's deadline table (recomputed daily from the build's own recorded answers)."""
 429 |      return P.Router(env_path=PS.ENV, record_dir=PL.REPLIES, spend_path=PL.SPEND, limit_usd=PL.LY_LIMIT_USD,
 430 |                      limit_basis=PL.LY_LIMIT_BASIS, chains=PL.chains(routing), deadline_log=PL.DEADLINE_LOG,
 431 |                      routing=routing, shadow=shadow, shadow_log=shadow_log,
 432 |                      health=HH.STATE, plan_b_chains=PL.plan_b_chains(), state_md=STATE_MD,      # ruling 87
 433 | -                    breakers=CB.STATE)                                                         # ruling 99
 434 | +                    breakers=CB.STATE,                                                         # ruling 99
 435 | +                    deadlines=DT.load(DT.STATE, PL.REPLIES))                                   # ruling 100
 436 | +
 437 | +
 438 | +def applied(router):
 439 | +    """RULING 100: which rows of the deadline table the build's router uses: a verdict pair on which a deadline applies
 440 | +    today, the role's (a gateway with a configured deadline: Heimdall) or the caller's (step A's first screen passes one
 441 | +    to every leg of its chain under heimdall_first, Grok's included: package.first_bounds). -> applies(key)."""
 442 | +    fb = PK.first_bounds(router).get("deadline_s")
 443 | +    first = set(router.chain("context_verdict", "step_a_first")) if fb else set()
 444 | +
 445 | +    def applies(key):
 446 | +        name, _, role = key.partition("|")
 447 | +        b = router.backends.get(name)
 448 | +        dl = fb if role == "context_verdict" and name in first else None
 449 | +        return b is not None and router.effective_deadline(role, b, dl) is not None and \
 450 | +            role in set((router.config.get("routing") or {}).get("verdict_roles") or ())
 451 | +    return applies
 452 | +
 453 | +
 454 | +def ruling_101_line(par):
 455 | +    """RULING 101 (12:16 Nov 14): the build's line on step A's order, with the extra spend when Grok's confirm ran in
 456 | +    parallel (its verdicts the second screen could not use: the dollars sequential would have saved). -> str or ""."""
 457 | +    if not par:
 458 | +        return ""
 459 | +    if par.get("parallel"):
 460 | +        asked = par.get("asked", 0) or 0
 461 | +        extra = (par.get("usd", 0) or 0) * (asked - (par.get("used", 0) or 0)) / max(1, asked)
 462 | +        return (f"  RULING 101 (step A in parallel): {par.get('n_new')} new moments; the filter ({par.get('leg')}) "
 463 | +                f"would have held the build about {(par.get('est_wait_s') or 0) / 60:.0f} min. Grok's confirm was asked "
 464 | +                f"on {asked} at once ({par.get('verdicts')} verdicts, ${par.get('usd', 0) or 0:.4f} vendor-reported); "
 465 | +                f"the second screen used {par.get('used')}, so about ${extra:.4f} was spent that sequential would have "
 466 | +                f"saved" + (f"; {par['error']}" if par.get("error") else ""))
 467 | +    wait = par.get("est_wait_s")
 468 | +    return (f"  RULING 101: step A sequential ({par.get('n_new')} new moments" +
 469 | +            (f"; the filter's wait about {wait / 60:.1f} min on {par.get('leg')})" if isinstance(wait, (int, float))
 470 | +             else f", not over {PK.STEP_A_PARALLEL_NEW})"))
 471 |  
 472 |  
 473 |  def main(argv=None):
 474 | @@ -207,6 +245,8 @@ def main(argv=None):
 475 |      router = build_router(routing, shadow, os.path.join(out_dir, "SHADOW86.jsonl"))
 476 |      say(f"  routing (ruling 85): {router.routing}; now {router.mode()} (ruling 87: the shared Heimdall health)"
 477 |          + (f"; SHADOW (ruling 86): {shadow}" if shadow else ""))
 478 | +    say(f"  RULING 100 (deadlines follow the model, table of {(router.deadlines or {}).get('computed_at')}): "
 479 | +        f"{DT.text(router.deadlines, applies=applied(router)) or 'no row applies: each gateway keeps its number'}")
 480 |      spent0 = router.spent()                      # ruling 48: the running total, vendor-reported (+ estimates where none)
 481 |      if spent0 >= PL.LY_STOP_USD:
 482 |          say(f"REFUSED (ruling 48): this order's ledger stands at ${spent0:.2f} vendor-reported (the estimate where a "
 483 | @@ -367,6 +407,9 @@ def main(argv=None):
 484 |          after = f"unreadable: {type(e).__name__}: {str(e)[:120]}"
 485 |      res["spend_ruling_48"] = {"before": round(spent0, 4), "after": after, "cap": PL.LY_LIMIT_USD,
 486 |                                "stop": PL.LY_STOP_USD, "basis": PL.LY_LIMIT_BASIS}
 487 | +    line101 = ruling_101_line((res.get("prescreen") or {}).get("parallel_101"))   # RULING 101: the extra spend
 488 | +    if line101:
 489 | +        say(line101)
 490 |      vis = res.get("visual") or {}
 491 |      say(f"  visual (ruling 70): {vis.get('calls', 0)} sheet(s) asked ({vis.get('unmeasured', 0)} not measured), "
 492 |          f"{vis.get('cached', 0)} cached, {vis.get('flags', 0)} flag(s); cost ${vis.get('usd_reported', 0):.4f} "
 493 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 494 | index fefacdc..2943c94 100644
 495 | --- a/tests/package/test_medley.py
 496 | +++ b/tests/package/test_medley.py
 497 | @@ -572,7 +572,9 @@ class Rig:
 498 |  
 499 |      def prescreen(self, router, ms, sources, ctx_, writer_vendor, writer_family=None, n=PK.PRESCREEN_N,
 500 |                    batch=PK.PRESCREEN_BATCH, store=None, log=print, cache=None, deadline_s=None, kind=None,
 501 | -                  failover=None):
 502 | +                  failover=None, plan_only=False):
 503 | +        if plan_only:                                      # ruling 101's plan: the moments new to the first screen
 504 | +            return [m for m in ms if m["moment_id"] in getattr(self, "plan_new", ())]
 505 |          self.screen_deadlines.append(deadline_s)           # ruling 82: which calls are bounded
 506 |          """Step A as the real prescreen calls it: on the first back-end off the given vendors and families
 507 |          (context_verdict: xai, then heimdall; a third vendor only for the rig); per (vendor, moment) failures."""
 508 | @@ -1257,6 +1259,25 @@ class TestRuling58StepAEveryCandidate(unittest.TestCase):
 509 |              self.assertEqual(sorted(sum((c[0] for c in calls), [])), ["m00", "m01", "m02"])   # never the writer's
 510 |              self.assertEqual({a["backend"] for a in a_by.values()}, {"heimdall:deepseek"})     # vendor's verdict
 511 |  
 512 | +    def test_ruling_101_plan_only_lists_what_the_screen_would_ask_and_asks_nothing(self):
 513 | +        import tempfile
 514 | +        ms, srcs = self.pool(10)
 515 | +        calls = []
 516 | +        self.fake(calls)
 517 | +        ids = lambda xs: sorted(m["moment_id"] for m in xs)
 518 | +        with tempfile.TemporaryDirectory() as d:
 519 | +            cache = os.path.join(d, "STEP_A_CACHE.json")
 520 | +            new = PK.prescreen(self.router(), ms, srcs, ctx(), {"heimdall"}, {"deepseek"}, cache=cache, plan_only=True)
 521 | +            self.assertEqual((ids(new), calls, os.path.exists(cache)), (ids(ms), [], False))   # all new, nothing asked
 522 | +            PK.prescreen(self.router(), ms[:6], srcs, ctx(), {"heimdall"}, {"deepseek"}, cache=cache)   # 6 paid for
 523 | +            calls.clear()
 524 | +            with open(cache) as f:
 525 | +                before = f.read()
 526 | +            new = PK.prescreen(self.router(), ms, srcs, ctx(), {"heimdall"}, {"deepseek"}, cache=cache, plan_only=True)
 527 | +            self.assertEqual(ids(new), ids(ms[6:]))                       # only the 4 the cache does not hold
 528 | +            with open(cache) as f:
 529 | +                self.assertEqual((calls, f.read()), ([], before))         # nothing asked, nothing written
 530 | +
 531 |      def test_a_failed_batch_is_no_verdict_never_cached_and_says_why(self):
 532 |          import tempfile
 533 |          ms, srcs = self.pool(10)
 534 | @@ -2529,7 +2550,8 @@ class TestOrder0622StepAFromBothVendors(unittest.TestCase):
 535 |  
 536 |      def test_ruling_85_the_first_screen_is_bounded_under_heimdall_first(self):
 537 |          """RULING 85: under heimdall_first the FIRST step-A verdict is a Heimdall family's, so it gets ruling 82's
 538 | -        bounds too (2 clips a call, 120 s); under today's routing it stays unbounded (Grok's), as before."""
 539 | +        bounds too (2 clips a call, 120 s); under today's routing it stays unbounded (Grok's), as before. RULING 100:
 540 | +        the Router holds each leg to its own row in place of the 120 s (Router.effective_deadline, test_deadline_table)."""
 541 |          batches = []
 542 |          for routing in ("today", "heimdall_first"):
 543 |              rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None],
 544 | @@ -2544,8 +2566,136 @@ class TestOrder0622StepAFromBothVendors(unittest.TestCase):
 545 |              rig.run()
 546 |              self.assertEqual(rig.screen_deadlines[0], None if routing == "today" else PK.SECOND_VERDICT_DEADLINE_S)
 547 |          self.assertEqual([b for r, b in batches if r == "heimdall_first"][0], PK.SECOND_VERDICT_BATCH)
 548 | +        self.assertEqual(PK.first_bounds(type("R", (), {"routing": "heimdall_first"})()),
 549 | +                         {"batch": PK.SECOND_VERDICT_BATCH, "deadline_s": PK.SECOND_VERDICT_DEADLINE_S})
 550 |          self.assertEqual([b for r, b in batches if r == "today"][0], PK.PRESCREEN_BATCH)
 551 |  
 552 | +    def test_ruling_101_the_plan_parallel_only_over_20_new_moments_and_10_minutes_of_filter(self):
 553 | +        """RULING 101 (12:16 Nov 14): parallel when the new moments are over 20 AND the filter would hold the build over
 554 | +        10 minutes: its rounds (batches over PRESCREEN_WORKERS) x the leading leg's deadline (ruling 100's, for the
 555 | +        first screen's 120 s), the leg the first off the writers and not breaker-open; when Grok leads (no Heimdall
 556 | +        family can), sequential whatever the wait."""
 557 | +        from unittest import mock
 558 | +
 559 | +        class B:
 560 | +            def __init__(self, vendor, family):
 561 | +                self.vendor, self.family, self.gateway = vendor, family, vendor.split("/")[0]
 562 | +
 563 | +        class R:
 564 | +            routing, down = "heimdall_first", {}
 565 | +
 566 | +            def __init__(self, open_=()):
 567 | +                self.backends = {"heimdall:glm": B("heimdall/glm", "glm"), "heimdall:ds": B("heimdall/deepseek",
 568 | +                                                                                          "deepseek"),
 569 | +                                 "xai:grok": B("xai", "grok")}
 570 | +                self.open_ = set(open_)
 571 | +
 572 | +            def chain(self, role, kind=None):
 573 | +                assert (role, kind) == ("context_verdict", "step_a_first")
 574 | +                return ["heimdall:glm", "heimdall:ds", "xai:grok"]
 575 | +
 576 | +            def effective_deadline(self, role, b, deadline_s=None):
 577 | +                assert (role, deadline_s) == ("context_verdict", PK.SECOND_VERDICT_DEADLINE_S)   # the first screen's
 578 | +                return {"glm": 60.0, "deepseek": 300.0, "grok": 118.1}.get(b.family)
 579 | +
 580 | +            def breaker_open(self, name):
 581 | +                return name in self.open_
 582 | +
 583 | +        def plan(n, router, wv=(), wf=()):
 584 | +            new = [{"moment_id": f"m{i}"} for i in range(n)]
 585 | +            with mock.patch.object(PK, "prescreen", lambda *a, plan_only=False, **k: new if plan_only else None):
 586 | +                return PK.step_a_plan(router, [], {}, None, set(wv), set(wf), **PK.first_bounds(router))
 587 | +        p = plan(20, R())                                                  # under the line: nothing else consulted
 588 | +        self.assertEqual((p["parallel"], p["n_new"], p["est_wait_s"], p["leg"]), (False, 20, None, None))
 589 | +        p = plan(21, R())                                  # glm leads: 11 batches of 2, 2 rounds x 60 s = 2 minutes
 590 | +        self.assertEqual((p["parallel"], p["est_wait_s"], p["leg"]), (False, 120.0, "heimdall:glm"))
 591 | +        p = plan(21, R(open_={"heimdall:glm"}))           # glm's breaker open: deepseek leads, 2 x 300 s = 10 minutes
 592 | +        self.assertEqual((p["parallel"], p["est_wait_s"], p["leg"]), (False, 600.0, "heimdall:ds"))   # not OVER 10
 593 | +        p = plan(37, R(open_={"heimdall:glm"}))           # 19 batches, 4 rounds x 300 s = 20 minutes
 594 | +        self.assertEqual((p["parallel"], p["est_wait_s"], p["leg"]), (True, 1200.0, "heimdall:ds"))
 595 | +        p = plan(37, R(open_={"heimdall:glm"}), wv={"heimdall/deepseek"})   # the writer's family: Grok leads,
 596 | +        self.assertEqual((p["parallel"], p["est_wait_s"], p["leg"]), (False, 472.4, "xai:grok"))   # 4 x 118.1 s
 597 | +        p = plan(80, R(open_={"heimdall:glm"}), wv={"heimdall/deepseek"})   # 40 batches, 7 rounds: over 10 minutes
 598 | +        self.assertEqual((p["parallel"], p["est_wait_s"], p["leg"]), (False, 826.7, "xai:grok"))   # but Grok leads
 599 | +        p = plan(80, R())                                                  # glm leads: 7 x 60 s, under 10 minutes
 600 | +        self.assertEqual((p["parallel"], p["est_wait_s"], p["leg"]), (False, 420.0, "heimdall:glm"))
 601 | +
 602 | +    def test_ruling_101_confirm_ahead_asks_off_every_heimdall_family_and_tallies_its_dollars(self):
 603 | +        from unittest import mock
 604 | +        import providers as P
 605 | +        hb = lambda name, fam: P.HeimdallBackend(name, {"model": fam, "family": fam, "base_url": "http://x"}, "/x")
 606 | +
 607 | +        class Rep:
 608 | +            def __init__(self, usd, reported):
 609 | +                self.usd, self.usage = usd, ({"usd_reported": reported} if reported is not None else {})
 610 | +
 611 | +        class R:
 612 | +            backends = {"heimdall:glm": hb("heimdall:glm", "glm"), "heimdall:ds": hb("heimdall:ds", "deepseek")}
 613 | +            replies = [Rep(0.5, 0.01), Rep(0.5, None)]
 614 | +
 615 | +            def call(self, *a, **k):
 616 | +                return self.replies.pop(0)
 617 | +        got = {}
 618 | +
 619 | +        def fake(router, new, sources, ctx_, wv, wf, n=None, kind=None, cache=None, **k):
 620 | +            got.update(wv=set(wv), wf=set(wf), kind=kind, n=n, cache=cache)
 621 | +            router.call("context_verdict", "p")
 622 | +            router.call("context_verdict", "q")
 623 | +            return {m["moment_id"]: {"backend": "xai:grok"} for m in new}, {}, set(), set()
 624 | +        with mock.patch.object(PK, "prescreen", fake):
 625 | +            res = PK.confirm_ahead(R(), [{"moment_id": "a"}, {"moment_id": "b"}], {}, None, {"openai"}, {"gpt"},
 626 | +                                   cache="/tmp/c")
 627 | +        self.assertEqual(got, {"wv": {"openai", "heimdall"}, "wf": {"gpt", "glm", "deepseek"}, "kind": "step_a_second",
 628 | +                               "n": 2, "cache": "/tmp/c"})       # off every Heimdall family and off the writers
 629 | +        self.assertEqual(res, {"asked": 2, "verdicts": 2, "usd": 0.51, "calls": 2,      # vendor-reported, else estimate
 630 | +                               "by": {"a": "xai:grok", "b": "xai:grok"}})
 631 | +
 632 | +    def test_ruling_101_in_a_build_grok_confirms_beside_the_filter_and_the_extra_is_reported(self):
 633 | +        """The plan says parallel: Grok's confirm (step_a_second) runs on every new moment ON ANOTHER THREAD while the
 634 | +        first screen runs; the second screen later reads the cache; the report counts what it used."""
 635 | +        import threading
 636 | +        from unittest import mock
 637 | +        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None],
 638 | +                  angle_from=("xai:grok", "xai", "grok"), write_from=("xai:grok", "xai", "grok"))
 639 | +        rig.router.routing = "heimdall_first"
 640 | +        rig.plan_new = {m["moment_id"] for m in self.MS}
 641 | +        rig.router.backends["heimdall:glm"] = type("B", (), {"vendor": "heimdall/glm", "family": "glm",
 642 | +                                                             "gateway": "heimdall"})()    # off the rig's writer
 643 | +        rig.router.chain = lambda role, kind=None: ["heimdall:glm", "xai:grok"]          # (heimdall, deepseek)
 644 | +        rig.router.effective_deadline = lambda role, b, deadline_s=None: 300.0 if b.family == "glm" else None
 645 | +        rig.router.breaker_open = lambda name: False
 646 | +        seen, pre = [], rig.prescreen
 647 | +
 648 | +        def spy(router_, ms, sources_, ctx_, writer_vendor, *a, kind=None, plan_only=False, **k):
 649 | +            if not plan_only:
 650 | +                seen.append((kind, set(writer_vendor), threading.get_ident()))
 651 | +            return pre(router_, ms, sources_, ctx_, writer_vendor, *a, kind=kind, plan_only=plan_only, **k)
 652 | +        rig.prescreen = spy
 653 | +        with mock.patch.object(PK, "STEP_A_PARALLEL_NEW", 1), mock.patch.object(PK, "STEP_A_PARALLEL_WAIT_S", 60.0):
 654 | +            out = rig.run()
 655 | +        par = out["prescreen"]["parallel_101"]
 656 | +        self.assertEqual((par["parallel"], par["n_new"], par["asked"], par["leg"]),
 657 | +                         (True, len(self.MS), len(self.MS), "heimdall:glm"))
 658 | +        main = threading.get_ident()
 659 | +        ahead = [t for k, wv, t in seen if k == "step_a_second" and wv == {"heimdall", "heimdall/glm"}]   # off every
 660 | +        # Heimdall family and the writers
 661 | +        self.assertEqual(len(ahead), 1)                                   # Grok's confirm: once,
 662 | +        self.assertNotEqual(ahead[0], main)                               # on its own thread,
 663 | +        self.assertIn(("step_a_first", {"heimdall"}, main), seen)         # beside the filter on the build's thread
 664 | +        self.assertEqual(par["used"], 0)              # here every first verdict is Grok's own: the second screen
 665 | +        self.assertEqual(rig.screens[-1][0], "heimdall:deepseek")         # screens off it as before
 666 | +
 667 | +    def test_ruling_101_used_counts_only_a_verdict_off_the_first(self):
 668 | +        class B:
 669 | +            def __init__(self, vendor, family):
 670 | +                self.vendor, self.family = vendor, family
 671 | +        r = type("R", (), {"backends": {"heimdall:ds": B("heimdall/deepseek", "deepseek"), "xai:grok": B("xai", "grok"),
 672 | +                                        "heimdall:glm": B("heimdall/glm", "glm")}})()
 673 | +        a_by = {"a": {"backend": "heimdall:ds"}, "b": {"backend": "xai:grok"}, "c": {"backend": "heimdall:glm"},
 674 | +                "d": {"backend": "heimdall:ds"}}
 675 | +        pre_by = {"a": "xai:grok", "b": "xai:grok", "c": "xai:grok"}      # d: no verdict ahead
 676 | +        self.assertEqual(PK.prewarm_used(r, ["a", "b", "c", "d"], a_by, pre_by), 2)   # a and c; b is Grok's own
 677 | +
 678 |      def test_ruling_88_grok_confirms_in_its_own_batches_under_heimdall_first(self):
 679 |          """RULING 88 (c): under heimdall_first the second step-A verdict is Grok confirming Heimdall's passes: Grok's own
 680 |          batch (8) and no deadline, the move-on rule kept; under today it stays a Heimdall family's (2 clips, 120 s)."""
 681 | diff --git a/tests/providers/test_circuit_breaker.py b/tests/providers/test_circuit_breaker.py
 682 | index 3cf2f24..fb13f11 100644
 683 | --- a/tests/providers/test_circuit_breaker.py
 684 | +++ b/tests/providers/test_circuit_breaker.py
 685 | @@ -121,6 +121,31 @@ class TestBreaker(unittest.TestCase):
 686 |              self.rec("slow", at(51))
 687 |  
 688 |  
 689 | +class TestReadOnly(unittest.TestCase):
 690 | +    """RULING 101's estimate reads the breakers without touching them (is_open never claims a trial)."""
 691 | +
 692 | +    def test_is_open_reads_and_never_claims(self):
 693 | +        with tempfile.TemporaryDirectory() as d:
 694 | +            state = os.path.join(d, "BREAKERS.json")
 695 | +            self.assertFalse(CB.is_open(GLM, state, now=at(0)))                     # no state: closed
 696 | +            CB.record(GLM, "miss", state, now=at(0))
 697 | +            CB.record(GLM, "miss", state, now=at(1))                                 # open until 15:31
 698 | +            self.assertTrue(CB.is_open(GLM, state, now=at(30, 59)))
 699 | +            before = open(state).read()
 700 | +            self.assertFalse(CB.is_open(GLM, state, now=at(31)))                    # the window passed: a call may
 701 | +            self.assertEqual(open(state).read(), before)                            # try it, and nothing was claimed
 702 | +            self.assertEqual(CB.allow(GLM, state, now=at(31), hold_s=180.0), (True, "trial"))
 703 | +            self.assertTrue(CB.is_open(GLM, state, now=at(33, 59)))                 # its one trial in flight
 704 | +            self.assertFalse(CB.is_open(GLM, state, now=at(34)))
 705 | +            with open(state, "w") as f:
 706 | +                f.write("{ broken")
 707 | +            self.assertFalse(CB.is_open(GLM, state, now=at(35)))                    # unreadable: skips nothing
 708 | +            r = router(d, [Fake(GLM, "heimdall", answer="x", family="glm")], {"c": [GLM]}, breakers=state)
 709 | +            self.assertFalse(r.breaker_open(GLM))
 710 | +            r.breakers = None
 711 | +            self.assertFalse(r.breaker_open(GLM))
 712 | +
 713 | +
 714 |  class TestRouterBreaker(unittest.TestCase):
 715 |      """providers.Router: live calls only. Two real deadline misses (P._within) open the breaker, the next family leads,
 716 |      and the open is one line in the evidence file."""
 717 | diff --git a/tests/providers/test_deadline_table.py b/tests/providers/test_deadline_table.py
 718 | new file mode 100644
 719 | index 0000000..ac2cb87
 720 | --- /dev/null
 721 | +++ b/tests/providers/test_deadline_table.py
 722 | @@ -0,0 +1,197 @@
 723 | +#!/usr/bin/env python3
 724 | +"""RULING 100 (orchestrator 12:16 ET Nov 14): DEADLINES FOLLOW THE MODEL (pipeline/deadline_table.py and its use in
 725 | +providers.Router.effective_deadline and the ledger build). Offline: temporary record dirs and table files."""
 726 | +import json
 727 | +import os
 728 | +import sys
 729 | +import tempfile
 730 | +import unittest
 731 | +from datetime import datetime, timedelta, timezone
 732 | +from unittest import mock
 733 | +
 734 | +HERE = os.path.dirname(os.path.abspath(__file__))
 735 | +REPO = os.path.dirname(os.path.dirname(HERE))
 736 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
 737 | +import deadline_table as DT  # noqa: E402
 738 | +import providers as P  # noqa: E402
 739 | +
 740 | +T0 = datetime(2026, 11, 14, 17, 0, tzinfo=timezone.utc)
 741 | +DS, GLM, GROK = "heimdall:deepseek/deepseek-v4.1-flash", "heimdall:z-ai/glm-5.3-flash", "xai:grok-4.20-0309-reasoning"
 742 | +
 743 | +
 744 | +def records(d, rows):
 745 | +    """rows: [(backend, role, seconds)] -> one recorded exchange each, as providers.Router._record writes them."""
 746 | +    for i, (b, role, s) in enumerate(rows):
 747 | +        os.makedirs(os.path.join(d, f"{i:02x}"[-2:]), exist_ok=True)
 748 | +        with open(os.path.join(d, f"{i:02x}"[-2:], f"{i:064x}.json"), "w") as f:
 749 | +            json.dump({"role": role, "backend": b, "seconds": s, "text": "{}"}, f)
 750 | +
 751 | +
 752 | +class TestTable(unittest.TestCase):
 753 | +    def setUp(self):
 754 | +        self.d = tempfile.TemporaryDirectory()
 755 | +        self.rec = os.path.join(self.d.name, "replies")
 756 | +
 757 | +    def tearDown(self):
 758 | +        self.d.cleanup()
 759 | +
 760 | +    def test_p90_times_one_and_a_half_inside_60_to_300_s(self):
 761 | +        records(self.rec, [(DS, "context_verdict", s) for s in (100, 120, 140, 160, 180, 200, 220, 240, 260, 280)]
 762 | +                + [(GLM, "context_verdict", s) for s in (5, 9, 12)]
 763 | +                + [("heimdall:qwen/qwen3.8-27b", "context_verdict", s) for s in (30, 40, 50, 60)]
 764 | +                + [("heimdall:slow/x", "context_verdict", s) for s in (400, 500, 600)]
 765 | +                + [(GROK, "coherence_verdict", s) for s in (10, 20)])          # two answers: no row of its own
 766 | +        t = DT.compute(self.rec, T0)
 767 | +        r = t["rows"]
 768 | +        self.assertEqual(r[f"{DS}|context_verdict"], {"n": 10, "p50": 190.0, "p90": 262.0, "deadline_s": 300.0})
 769 | +        self.assertEqual(r[f"{GLM}|context_verdict"]["deadline_s"], 60.0)                  # the floor
 770 | +        self.assertEqual(r["heimdall:qwen/qwen3.8-27b|context_verdict"]["deadline_s"], 85.5)   # 57 x 1.5
 771 | +        self.assertEqual(r["heimdall:slow/x|context_verdict"]["deadline_s"], 300.0)          # the ceiling
 772 | +        self.assertNotIn(f"{GROK}|coherence_verdict", r)                                       # under MIN_N
 773 | +        self.assertEqual((t["computed_at"], DT.deadline(t, DS, "context_verdict"), DT.deadline(t, GROK, "x")),
 774 | +                         ("2026-11-14T17:00:00Z", 300.0, None))
 775 | +
 776 | +    def test_a_record_that_cannot_be_read_or_has_no_positive_time_is_skipped(self):
 777 | +        records(self.rec, [(DS, "context_verdict", s) for s in (10, 20, 30)] +
 778 | +                [(DS, "context_verdict", bad) for bad in (0, -5, None, "slow", True)])
 779 | +        os.makedirs(os.path.join(self.rec, "zz"), exist_ok=True)
 780 | +        with open(os.path.join(self.rec, "zz", "broken.json"), "w") as f:
 781 | +            f.write("{ broken")
 782 | +        with open(os.path.join(self.rec, "zz", "nan.json"), "w") as f:
 783 | +            f.write('{"role": "context_verdict", "backend": "%s", "seconds": NaN}' % DS)
 784 | +        with open(os.path.join(self.rec, "zz", "list.json"), "w") as f:
 785 | +            f.write('[{"role": "context_verdict", "backend": "%s", "seconds": 5}]' % DS)   # not an object
 786 | +        self.assertEqual(DT.compute(self.rec, T0)["rows"][f"{DS}|context_verdict"]["n"], 3)
 787 | +        self.assertEqual(DT.deadline({"rows": {"a|b": {"deadline_s": "60"}}}, "a", "b"), None)   # no guess
 788 | +        self.assertEqual(DT.deadline(None, "a", "b"), None)
 789 | +        rows = {"rows": {"a|hi": {"deadline_s": 500}, "a|lo": {"deadline_s": 10}, "a|inf": {"deadline_s": float("inf")}}}
 790 | +        self.assertEqual([DT.deadline(rows, "a", r) for r in ("hi", "lo", "inf")], [300.0, 60.0, None])   # 60-300 s
 791 | +
 792 | +    def test_the_table_is_kept_a_day_then_recomputed_and_an_unreadable_one_is_recomputed(self):
 793 | +        path = os.path.join(self.d.name, "TABLE.json")
 794 | +        records(self.rec, [(DS, "context_verdict", s) for s in (100, 110, 120)])
 795 | +        first = DT.load(path, self.rec, T0)
 796 | +        self.assertTrue(os.path.exists(path))
 797 | +        records(self.rec, [(DS, "context_verdict", s) for s in (10, 10, 10, 10, 10, 10, 10)])
 798 | +        self.assertEqual(DT.load(path, self.rec, T0 + timedelta(hours=23)), first)          # within the day: kept
 799 | +        again = DT.load(path, self.rec, T0 + timedelta(hours=24, seconds=1))                # a day later: the records
 800 | +        self.assertNotEqual(again["rows"], first["rows"])
 801 | +        self.assertEqual(again["computed_at"], "2026-11-15T17:00:01Z")
 802 | +        with open(path, "w") as f:
 803 | +            f.write("{ broken")
 804 | +        self.assertEqual(DT.load(path, self.rec, T0 + timedelta(hours=25))["computed_at"], "2026-11-15T18:00:00Z")
 805 | +        self.assertIn("deepseek-v4.1-flash context_verdict:", DT.text(again))
 806 | +        self.assertEqual(DT.text(again, applies=lambda k: False), "")
 807 | +
 808 | +    def test_with_no_record_dir_a_saved_table_is_never_overwritten(self):
 809 | +        """glm, audit 20261114_1246 C1: a load with nothing to compute from (no record dir) gives an empty table (each
 810 | +        gateway keeps its number) and leaves the saved one as it was."""
 811 | +        path = os.path.join(self.d.name, "TABLE.json")
 812 | +        records(self.rec, [(DS, "context_verdict", s) for s in (100, 110, 120)])
 813 | +        DT.load(path, self.rec, T0)
 814 | +        with open(path) as f:
 815 | +            saved = f.read()
 816 | +        cwd = os.getcwd()
 817 | +        try:                                       # never the current directory's files (a record dir lives there)
 818 | +            os.chdir(self.rec)
 819 | +            records(os.path.join(self.rec, "x"), [(DS, "context_verdict", s) for s in (1, 2, 3)])
 820 | +            os.chdir(os.path.join(self.rec, "x"))
 821 | +            later = DT.load(path, None, T0 + timedelta(days=2))
 822 | +        finally:
 823 | +            os.chdir(cwd)
 824 | +        self.assertEqual(later["rows"], {})
 825 | +        with open(path) as f:
 826 | +            self.assertEqual(f.read(), saved)
 827 | +
 828 | +
 829 | +class TestRouter(unittest.TestCase):
 830 | +    """providers.Router.effective_deadline: where a deadline applies today (the caller's, else the role's: the gateway's
 831 | +    120 s on Heimdall), a verdict pair's own row replaces it; without a row, the number that applied; where none applies
 832 | +    (Grok with no caller deadline, any writer) none is added. role_deadline keeps the gateway's number."""
 833 | +
 834 | +    def router(self, table):
 835 | +        d = tempfile.mkdtemp()
 836 | +        cfg = os.path.join(d, "cfg.json")
 837 | +        json.dump({"schema": "pp.providers/1",
 838 | +                   "backends": {DS: {"vendor": "heimdall", "model": "deepseek", "family": "deepseek",
 839 | +                                     "base_url": "http://x"},
 840 | +                                GLM: {"vendor": "heimdall", "model": "glm", "family": "glm", "base_url": "http://x"},
 841 | +                                GROK: {"vendor": "xai", "model": "grok", "family": "grok"}},
 842 | +                   "roles": {"context_verdict": {"chain": [GLM, DS, GROK]}},
 843 | +                   "routing": {"mode": "heimdall_first", "verdict_roles": ["context_verdict"],
 844 | +                               "verdict_deadline_s": {"heimdall": 120}}}, open(cfg, "w"))
 845 | +        return P.Router(cfg, env_path="/nonexistent", deadlines=table)
 846 | +
 847 | +    TABLE = {"rows": {f"{DS}|context_verdict": {"n": 33, "p50": 165, "p90": 272, "deadline_s": 300.0},
 848 | +                      f"{GROK}|context_verdict": {"n": 268, "p50": 46, "p90": 80, "deadline_s": 120.7},
 849 | +                      f"{DS}|angle_write": {"n": 9, "p50": 20, "p90": 30, "deadline_s": 60.0}}}
 850 | +
 851 | +    def test_the_model_s_own_deadline_where_one_applies(self):
 852 | +        r = self.router(self.TABLE)
 853 | +        e = lambda role, name, dl=None: r.effective_deadline(role, r.backends[name], dl)
 854 | +        self.assertEqual(e("context_verdict", DS), 300.0)                   # the role's 120 s -> its own row
 855 | +        self.assertEqual(e("context_verdict", GLM), 120.0)                  # no row: the gateway's
 856 | +        self.assertIsNone(e("context_verdict", GROK))                       # none applies (no caller's): none added
 857 | +        self.assertEqual(e("context_verdict", GROK, 120.0), 120.7)          # the first screen's 120 s -> its own row
 858 | +        self.assertEqual(e("context_verdict", GLM, 120.0), 120.0)           # no row: the caller's
 859 | +        self.assertEqual(e("context_verdict", DS, 30.0), 300.0)             # a row replaces the caller's number too
 860 | +        self.assertEqual(e("angle_write", DS, 300.0), 300.0)                # a writer keeps its own (not a verdict)
 861 | +        self.assertIsNone(e("angle_write", DS))
 862 | +        self.assertEqual(self.router(None).effective_deadline("context_verdict", r.backends[DS]), 120.0)   # no table
 863 | +        self.assertEqual(r.role_deadline("context_verdict", r.backends[DS]), 120.0)   # the gateway's number, as before
 864 | +        self.assertIsNone(r.role_deadline("context_verdict", r.backends[GROK]))
 865 | +
 866 | +    def test_a_live_call_waits_its_own_deadline_and_the_breaker_measures_against_it(self):
 867 | +        """Router.call itself: the deadline the call is held to (and the breaker's miss is measured against: ruling 99)
 868 | +        is effective_deadline's; a recorded reply or replay never reaches it (unchanged)."""
 869 | +        r = self.router(self.TABLE)
 870 | +        held = []
 871 | +
 872 | +        def within(seconds, fn, on_abandon=None, on_late=None):
 873 | +            held.append(seconds)
 874 | +            return fn()
 875 | +        for b in r.backends.values():
 876 | +            b.complete = lambda prompt, mt, seed, system=None: ('{"ok": 1}', {"in": 1, "out": 1}, 0.1)
 877 | +        with mock.patch.object(P, "_within", within):
 878 | +            for chain, dl in (([DS], None), ([GROK], 120.0), ([GROK], None), ([GLM], None)):
 879 | +                r.chains["context_verdict"] = chain
 880 | +                r.call("context_verdict", "p", 100, 7, deadline_s=dl)
 881 | +            r.chains["angle_write"] = [DS]
 882 | +            r.call("angle_write", "p", 100, 7, deadline_s=300.0)
 883 | +        self.assertEqual(held, [300.0, 120.7, 120.0, 300.0])               # Grok with no deadline: not held at all
 884 | +
 885 | +    def test_the_build_router_loads_the_table_from_its_own_records(self):
 886 | +        sys.path.insert(0, os.path.join(REPO, "tests", "package"))
 887 | +        import proof_ledger as PLG
 888 | +        import proof_ly as PL
 889 | +        with tempfile.TemporaryDirectory() as d:
 890 | +            path = os.path.join(d, "DEADLINE_TABLE.json")
 891 | +            with mock.patch.object(DT, "STATE", path):
 892 | +                r = PLG.build_router("heimdall_first", None, os.path.join(d, "SHADOW86.jsonl"))
 893 | +            self.assertTrue(os.path.exists(path))
 894 | +            self.assertEqual(r.deadlines, DT.load(path, PL.REPLIES))
 895 | +        app = PLG.applied(r)
 896 | +        self.assertTrue(app(f"{GROK}|context_verdict"))           # the first screen's leg under heimdall_first
 897 | +        self.assertFalse(app(f"{GROK}|coherence_verdict"))        # no deadline applies: none added
 898 | +        self.assertFalse(app(f"{GROK}|shadow86:context_verdict"))           # not a verdict role
 899 | +        self.assertTrue(app("heimdall:deepseek/deepseek-v4.1-flash|context_verdict"))
 900 | +        self.assertTrue(app("heimdall:deepseek/deepseek-v4.1-flash|coherence_verdict"))   # the gateway's 120 s
 901 | +        self.assertFalse(app("heimdall:deepseek/deepseek-v4.1-flash|angle_write"))
 902 | +
 903 | +
 904 | +class TestTheBuildLine(unittest.TestCase):
 905 | +    def test_ruling_101_s_line_reports_the_extra_spend(self):
 906 | +        sys.path.insert(0, os.path.join(REPO, "tests", "package"))
 907 | +        import proof_ledger as PLG
 908 | +        self.assertEqual(PLG.ruling_101_line(None), "")
 909 | +        line = PLG.ruling_101_line({"parallel": True, "n_new": 37, "leg": DS, "est_wait_s": 1200.0, "asked": 37,
 910 | +                                    "verdicts": 36, "usd": 0.37, "used": 10})
 911 | +        self.assertIn("would have held the build about 20 min", line)
 912 | +        self.assertIn("the second screen used 10, so about $0.2700 was spent that sequential would have saved", line)
 913 | +        self.assertIn("about 2.0 min on", PLG.ruling_101_line({"parallel": False, "n_new": 21, "est_wait_s": 120.0,
 914 | +                                                               "leg": GLM}))
 915 | +        self.assertIn("not over 20", PLG.ruling_101_line({"parallel": False, "n_new": 4, "est_wait_s": None}))
 916 | +
 917 | +
 918 | +if __name__ == "__main__":
 919 | +    unittest.main()
 920 | 
```

---

You are auditing a change on branch pp-selectid (Protocol Pulse's moments-first video builder). Only state what you
can verify from the diff and the facts below; if uncertain, say so; do not guess. Be specific: file:line and a concrete
sequence that breaks it.

BACKGROUND (static):
- providers.Router.call walks a role's chain of model back-ends. A live call on a leg gets a deadline (the caller's
  deadline_s, else Router.role_deadline(role, backend)); at the deadline the leg is abandoned and the chain moves on.
  Ruling 99's circuit breaker skips a model for 30 minutes after it misses its deadline twice in a row.
- STEP A (law L-s) screens each moment's own context twice: the FIRST screen (package.prescreen, kind step_a_first,
  chain heimdall_first = [glm, deepseek, Grok], 2 clips a call) on every usable moment; later, on the moments that
  cleared, were cuttable and passed the hook rules, the SECOND screen (package.second_screen: kind step_a_second,
  chain [Grok, glm, deepseek], 8 clips a call) for a verdict OFF the first verdict's vendor and family. A clip passes
  only if BOTH pass. Verdicts are cached across builds in a shared step-A cache keyed by moment, text, context and
  prompt version, per back-end.
- Before this change: under heimdall_first the first screen passed an explicit flat deadline of 120 s
  (first_bounds -> SECOND_VERDICT_DEADLINE_S), and every other Heimdall verdict call got the gateway's 120 s
  (role_deadline). deepseek's recorded step A answers take median 165 s, p90 272 s (33 answers), so it "missed" its
  deadline on normal calls, its breaker opened, and at 12:24 and 12:40 ET two spotlight candidates with hooks rated
  4 died at the second screen with every leg unavailable (Grok was their first verdict's own vendor, glm's and
  deepseek's breakers open).

UNCHANGED CODE THIS CHANGE RELIES ON (not in the diff; verify against these facts, do not assume them away):
- providers.Router.call: `dl = deadline_s or self.role_deadline(role, b)` per leg; a recorded reply is served before
  any deadline or breaker applies; replay never makes a live call.
- package.prescreen (:494) builds each moment's context and cache key, takes a verdict from this build's store or the
  shared cache when one exists off the given writer vendor/family, and asks the rest in batches on PRESCREEN_WORKERS
  (6) threads. The cache is merged by _cache_put (:475) under CACHE_LOCK (:456), re-reading the file inside the lock,
  so two prescreens in one process cannot lose each other's verdicts.
- package.second_screen (:682) calls prescreen per group with writer sets = the FIRST verdict's (vendor, family) and
  kind step_a_second; through the cache lookup it reuses a cached verdict from any back-end off those sets.
- package._writers(router) returns the angle writer's (vendor, family); step A never runs on it.
- Under heimdall_first each Heimdall family is its own vendor ("heimdall/deepseek", "heimdall/glm"; ruling 85).

THE ORCHESTRATOR'S RULINGS (12:16 ET Nov 14), verbatim:
"100. DEADLINES FOLLOW THE MODEL, NOT ONE NUMBER. My 120 s (ruling 82) sits on top of deepseek's NORMAL step A time
(about 105 s recorded), so the breaker opened on a healthy model and Grok decided step A alone again. Per (model,
verdict type) the deadline is the recorded p90 of that pair's answered calls x 1.5, floor 60 s, ceiling 300 s,
recomputed from the records daily (say the table on STATE once). The breaker's 'two misses in a row' is against THAT
deadline. glm's recorded step A median was 45 s, so its 483-532 s today still trips it; deepseek at 105 s does not.
Close deepseek's breaker now by this rule.
101. STEP A ORDER WHILE HEIMDALL IS SLOW: the filter is worth its wait only if it saves more than it costs. Rule: step
A asks the Heimdall filter and Grok's confirm IN PARALLEL when the pool to screen is over 20 new moments and a build
would otherwise wait more than 10 minutes on the filter; a clip passes only if BOTH pass (unchanged); Grok's call is
then not saved, and you report the extra spend per build. Under 20 new moments, sequential as ruled (Heimdall first,
Grok only on a pass). Time to a video comes before the 18 cents."

THE CHANGE (the diff follows):
1. pipeline/deadline_table.py (new): from the build's recorded exchanges (one JSON per ANSWERED call: backend, role,
   seconds), per (backend, role) with at least MIN_N = 3 answers: p50, p90 and deadline = clamp(1.5 x p90, 60, 300).
   Saved with computed_at; load() reuses it for a day, else (or when unreadable) recomputes and saves.
   Measured now (the rows a Router applies): deepseek step A 300 s (n 33, p90 272); deepseek coherence 213 s; qwen step
   A 67 s; qwen coherence 60 s; glm step A 60 s (n 3, p90 39).
2. providers.Router(deadlines=table). role_deadline: where a deadline applies today (a verdict role on a gateway with
   a configured deadline: Heimdall), the pair's own row if it has one, else the gateway's 120 s; where none applies
   (Grok, a non-verdict role) none applies now, row or not. Router.breaker_open(name): a READ-ONLY breaker check
   (circuit_breaker.is_open, new: it never claims a trial).
3. package.first_bounds under heimdall_first: no flat deadline (deadline_s None, failover True, 2 clips a call kept),
   so each leg gets its own deadline from the Router.
4. Ruling 101 in package.build:
   - step_a_plan(): the moments NEW to the first screen (prescreen(plan_only=True): no verdict in the store or the
     cache; nothing asked, nothing written). Over STEP_A_PARALLEL_NEW (20) new, the estimated filter wait is rounds
     (ceil(new / batch) / PRESCREEN_WORKERS, rounded up) x the deadline of the filter's leading leg: the first leg of
     the step_a_first chain off the writers, not down this run and not breaker-open. The plan is parallel when that
     wait is over STEP_A_PARALLEL_WAIT_S (600 s); a leading leg with no deadline (Grok) is sequential.
   - When parallel, confirm_ahead() runs on its own thread BESIDE the first screen: prescreen(kind step_a_second) on
     every new moment with every Heimdall vendor and family added to the writer sets (so only a non-Heimdall leg, Grok,
     answers), into the shared cache. The later second screen is unchanged; it reads those verdicts from the cache
     where they are off the first verdict's vendor and family (a moment whose first verdict was Grok's own is
     screened off it as before).
   - The spend is tallied through a router view (_Tally: vendor-reported dollars, else the estimate).
     prewarm_used() counts the verdicts the second screen could use. The build prints the extra spend
     (usd x unused / asked) per build (proof_ledger.ruling_101_line).
5. tests/package/proof_ledger.py: the build router loads the table (DT.load, from its own record dir) and prints the
   rows it applies; the ruling-101 line per build.
6. Tests: test_deadline_table.py (new, 6), test_circuit_breaker.py (+1), test_medley.py (+5, one updated: the first
   screen passes no flat deadline). 22 mutations, each killed; 22 suites, 590 tests.

ATTACK:
(a) Ruling 100: can a pair's deadline come out under 60 or over 300? Can a row apply where no deadline applied before
    (Grok) or vanish where one did? A pair with 1-2 answers? A stale or unreadable table? Does the breaker now measure
    deepseek against 300 s, and glm against 60 s?
(b) The first screen with no flat deadline: can any leg now wait unbounded where it was bounded before? Failover kept?
(c) Ruling 101: can a clip now pass with only ONE screen's pass? Can the confirm-ahead's verdict be used against its own
    vendor (same vendor twice)? Can the two prescreens running at once corrupt the cache or the store? Is "new
    moments" counted right (cached ones excluded)? Is the 10-minute estimate sound, and what if the leading leg's
    breaker opens mid-build? Is the extra spend reported honestly?
(d) Anything else that could seal a wrong pin, starve a build, or spend past ruling 48's cap.

Answer with findings tagged <critical>, <high>, <medium> (file:line, a concrete sequence), then
"SHIP: yes / no / yes with conditions".

CHANGED AFTER CYCLE 1. Review the diff AS IT STANDS NOW. Items 2 and 3 of THE CHANGE are REPLACED by 2' and 3':
2'. providers.Router.effective_deadline(role, b, deadline_s) (new, providers.py:1020) gives the deadline a live call
    is held to. Router.call uses it (providers.py:1246, changed; the local judge's floor and the breaker follow it,
    unchanged).
    - Where a deadline applies (the caller's deadline_s, else role_deadline's gateway number), a VERDICT role's pair
      row of the table replaces it.
    - Without a row, the number that applied.
    - Where none applies, none is added (Grok with no caller deadline; any writer, whose own deadline is kept).
    - role_deadline (providers.py:1007) is back to its old text (the gateway's number).
3'. package.first_bounds is back to its old text: under heimdall_first {batch 2, deadline_s 120}. prescreen's failover
    default follows the deadline (package.py:551, unchanged).
    - So every first-screen leg keeps a bound: glm 60 s, deepseek 300 s, Grok its own row, 118.1 s.
    - The second screen under heimdall_first passes no deadline (_second_bounds, package.py:681, unchanged; ruling
      88 (c)), so its Grok leg stays unbounded as before.
Also changed:
- step_a_plan is parallel only when a HEIMDALL family leads the filter (package._heimdall: providers.gateway ==
  "heimdall"). confirm_ahead uses the same predicate.
- deadline_table: compute(None) reads no files, a record that is not an object is skipped, load() never saves
  without a record dir, and deadline() clamps any row to 60-300 s.
- proof_ledger.applied lists the rows the build uses.
CYCLE 2 ATTACK, in addition to (a)-(d):
(e) Does any leg now wait LONGER than its own row, or without a bound where it had one before this change?
(f) Can effective_deadline put a verdict row on a writer call, or on a probe?
(g) Can the parallel plan run when its confirm-ahead could serve no moment?


---

## CYCLE 2 INSTRUCTIONS

You've now seen what the other models said. This is your final review.

1. WHAT DID THEY CATCH THAT YOU MISSED?
   Review their findings. Be honest about what you overlooked.

2. WHERE DO YOU AGREE OR DISAGREE?
   For each of their key findings: agree / disagree / partially agree + why.

3. NEW FINDINGS FROM THIS REVIEW
   Anything the combined analysis revealed that nobody caught in Cycle 1?

4. REVISED SCORES
   Update your scores from Cycle 1. Did anything change your assessment?
   | Subsystem | Cycle 1 | Cycle 2 | Why changed |

5. FINAL PRIORITY LIST
   Your definitive list of what must change before this ships.
   P0 CRITICAL | P1 HIGH | P2 MEDIUM — cite file and line numbers.

6. THE SINGLE HIGHEST-LEVERAGE CHANGE
   After seeing everything — one sentence. What matters most?

7. PRODUCTION READY?
   Yes / No / Yes with conditions. State your conditions precisely.
