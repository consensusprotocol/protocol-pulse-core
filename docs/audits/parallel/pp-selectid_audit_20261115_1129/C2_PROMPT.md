# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261115_1129
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 235 s finish=stop usage in 20514 / out 6496 usd_reported=0.001441 usd~0.159 (upper-bound price)

# Audit: pp-selectid — RULING 112 hook scarcity diagnosis (hook112.py + test_hook112.py)

Scope: 2 new files, 726 LOC. Read-only diagnosis driver + offline tests. No pipeline/ changes, so the governing laws are mostly inherited; I flag where the driver's *reading* of records could misstate a law-governed fact.

---

## Findings

### [P1] F1 — `medley_trace` stage ordering: `ratings` beats `second_pass`/`trim_cut`/`onset` failures, but the `elif` chain can misplace a moment that *failed* the second pass yet also has a rating
Lines 119–154. The chain is: `unusable → no_role → ad → reposted → failed → ratings → second_pass(≠PASS) → trim_cut → onset(≠PASS) → onset+hp.error → onset → 3-channel → pool`. Because `ratings` is checked **before** `second`/`trim_cut`/`onset`, a moment that appears in `hook_pool.ratings` *and* in `prescreen.second_pass` with a non-PASS value is placed at stage 5/6 ("rated by the hook job") even though its second pass failed. Is that wrong? In `package.build` the ratings are only written for moments that passed the second pass, so in practice the record is consistent — but the driver's contract is "place each moment where package.build actually stopped it," and the record, not the invariant, is the evidence. If a build ever wrote a rating for a moment whose second-pass row is a stale FAIL (e.g. the moment was retried and the prescreen dict retains the old FAIL while ratings got the new entry), the funnel counts it as rated when the record says it never opened. Same for `trim_cut` FAIL + rating. **Fix:** check the later stages first, or assert consistency. Severity: P1 (a wrong funnel count is the deliverable of part 1).

Wait — re-examine: in `package.build` the prescreen dicts are cumulative across the build; a moment retried... Actually the test at line 549 asserts `t: 3` (trim_cut FAIL) while `t` is also in `hook_onset` PASS — the chain checks `trim_cut` before `onset`, so a FAIL in `trim_cut` masks an onset PASS. Is that the true stop? In `package.build`, `trim_cut` is written only when the moment reached the trim/cut stage; if it's in `hook_onset` with PASS, it *passed* the onset check, so a `trim_cut` FAIL entry means the *cut* failed after the onset passed — stage 3 is right. But the test's `o` case: `onset["o"] = "FAIL: 0 ms of genuine quiet"` → stage 3, yet `o` is also in `trim_cut`? No — `trim_cut` only has `t`. So the masking question is: does `package.build` write `trim_cut` for every moment that reached it, including ones that then passed? If `trim_cut` records only failures, the chain's `elif mid in trim_cut` before the onset checks is correct. If it records outcomes for all, a PASS in `trim_cut` would be misread as a stop at stage 3. The driver's docstring says "trim_cut" holds "no trimmed cut was reached" — failures only. OK, downgrade: the ordering is defensible, but it's **undocumented** which of these dicts are failure-only vs outcome maps. The test at 549 (`o: 3` from an onset FAIL) vs `x: 3` ("cannot open") shows `onset` holds both PASS and FAIL. So `trim_cut`'s semantics (failure-only?) is load-bearing and unstated. **Downgrade to P2:** the trace's correctness rests on undocumented record semantics (`trim_cut` failure-only, `second_pass`/`onset` outcome maps, `ratings` implies it opened).

### [P2] F2 — `spotlight_trace` stage-0 "step A" detection is string-matching on `out`
Line 173: `stepa = st == 0 and (str(why).startswith("step A") or "no verdict (law L-m)" in str(why))`. The spotlight's stage-0 stops are free screens *unless* they're step A's; the driver distinguishes them by the *prose* of `out`. If `spotlight.build` ever changes the wording ("step A: ..."), the funnel silently reclassifies step-A stops as free-screen stops (stage 0 vs 1) — a wrong funnel. The test at 571 pins `"step A: REFERENT_OUTSIDE"` and `"no verdict (law L-m)"` — good, but the coupling is to prose, not to a field. P2: prefer a structured field or at least a comment citing the exact producer line (the driver cites :858 for the ALONE gate, good, but not the step-A wording's producer).

### [P3] F3 — `reason_class` regexes: `STAND_ALONE with the clip scorer|STAND_ALONE` — the first alternative is dead
Line 73: `(r"STAND_ALONE with the clip scorer|STAND_ALONE", "STAND_ALONE opener rule")`. Since the second alternative matches any occurrence of "STAND_ALONE", the first alternative can never be reached... actually in Python `re.search` with alternation, the *leftmost* alternative wins at the same position, but since the second matches a superset, the first is only useful if... it's not useful: any string containing "STAND_AALONE with the clip scorer" also contains "STAND_ALONE", so the first alternative is redundant, not dead — the *class* is the same either way ("STAND_ALONE opener rule"). But the docstring of the order says the topic rule (ruling 34) is a *di

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 113 s finish=stop usage in 22600 / out 8042 usd_reported=0.006785 usd~0.188 (upper-bound price)

I will begin by analyzing the provided code against the governing laws and the specific instructions in the "PLEASE CHECK" section.

### Analysis of `tests/package/hook112.py`

**1. Read-Only Compliance (Law M12 / Instruction 5)**
The code claims to be read-only on build records, hook cache, and pp-ingest databases.
- `build_records`: Uses `json.load(open(...))`. Read-only.
- `hook_pass`: Connects to SQLite with `sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)`. This enforces read-only mode at the driver level.
- `calibrate`: Uses `router.spent()` and `rate(...)`. The `rate` function is `package.hook_ratings`. The instruction states `cache=None` is passed.
    - *Check*: Does `package.hook_ratings` write to disk if `cache=None`? The prompt says: "`_load_cache(None)` is `{}` ... and `_cache_put(None, ...)` returns at once ... so the production HOOK_CACHE.json is neither read nor written." This relies on the behavior of `package.py` (not provided, but described). Assuming the description is accurate, this is safe.
    - *Spend Ledger*: `build_router` creates a `Router` with `spend_path=SPEND` (`tests/package/proof/SPEND_H112.json`). This is a *new* file in the test/proof directory, not the production spend ledger. This is acceptable for a diagnostic tool that needs to track its own cost.
    - *Record Dir*: `record_dir=os.path.join(OUT, "replies")`. This writes model replies to `tests/package/proof/hook112/replies`. This is a write operation, but it is within the test/proof output directory, which is standard for capturing evidence. It does not modify source code or production data.

**2. Heimdall-Only Compliance (Instruction 4)**
- `heimdall_hook_chain`: Filters `router.chain("coherence_verdict", "hook")` to keep only backends where `vendor.split("/")[0] == "heimdall"`.
- `build_router`: Sets `r.chains["coherence_verdict:hook"] = heimdall_hook_chain(r)`.
- *Potential Issue*: Does `providers.Router` allow other chains to be used? The calibration only calls `rate(router, refs, ctx, wv, wf, cache=None, seed=s)`. `rate` is `package.hook_ratings`. If `hook_ratings` internally uses other chains (e.g., for fallback or different roles), it might bypass the Heimdall-only restriction. However, the prompt states: "The hook job as it stands today (package.hook_ratings ... unchanged) ... runs on Heimdall only: the hook chain of ruling 88 ... with every non-Heimdall back-end removed". This implies `hook_ratings` specifically uses the `coherence_verdict:hook` chain. If `hook_ratings` uses other chains (e.g., `angle_write`), those are not restricted by `heimdall_hook_chain`.
    - *Check*: `calibrate` passes `wv, wf` (writers' vendor/family) to `rate`. `package._writers(router)` is used to avoid the writers. This is a standard production pattern.
    - *Risk*: If `hook_ratings` falls back to a non-Heimdall model for *other* reasons (e.g., if the Heimdall model fails), does it respect the "Heimdall only" constraint? The code removes non-Heimdall backends from the *chain*. If the chain is empty, it raises `RuntimeError`. If the chain has only Heimdall backends, and one fails, does the router try the next in the chain (which is also Heimdall) or fall back to a default? `providers.Router` behavior is not fully visible, but typically it iterates the chain. Since the chain is filtered to Heimdall only, it should stay within Heimdall.

**3. Funnel Logic (Instruction 1 & 2)**
- `medley_trace`: Maps moments to stages 0-6.
    - Stage 0: `unusable`, `no_role`, `ad_read`, `reposted`.
    - Stage 1: `prescreen.failed`.
    - Stage 2: `prescreen.second_pass` != "PASS".
    - Stage 3: `prescreen.trim_cut` or `prescreen.hook_onset` != "PASS".
    - Stage 4: `prescreen.hook_onset` == "PASS" but `hook_pool.error` exists.
    - Stage 5: `hook_pool.ratings` exists but `own_rating` < 4.
    - Stage 6: `hook_pool.ratings` exists and `own_rating` >= 4.
    - *Logic Check*:
        - `elif mid in onset and onset[mid] != "PASS":` -> Stage 3.
        - `elif mid in onset and hp.get("error"):` -> Stage 4.
        - `elif mid in onset:` -> Stage 3 ("cannot open"). Wait, if `onset[mid]` is "PASS", it goes to the next `elif`.
        - The order of `elif`s matters.
            1. `mid in unusable`...
            2. `mid in failed`...
            3. `mid in ratings`... (Stage 5/6)
            4. `mid in second and second[mid] != "PASS"`... (Stage 2)
            5. `mid in trim_cut`... (Stage 3)
            6. `mid in onset and onset[mid] != "PASS"`... (Stage 3)
            7. `mid in onset and hp.get("error")`... (Stage 4)
            8. `mid in onset`... (Stage 3, "cannot open")
        - *Issue*: If a moment is in `ratings`, it is caught at step 3. It does not matter if it also failed `onset` or `second_pass`. This is correct because `ratings` implies it passed the previous gates.
        - *Issue*: If a moment is in `

## CLAUDE'S CYCLE 1 CONSENSUS
# C1 CONSENSUS — pp-selectid audit 20261115_1129 (ruling 112's diagnosis driver, tests/package/hook112.py)

Reviewers: qwen3.8-27b (P1_OR_WORSE: 1) and glm-5.3-flash (P1_OR_WORSE: 1). Both raise a P1, so they agree on the
count and Grok was not asked. Cycle 1: $0.0082 vendor-reported.

THE TWO P1s:
1. qwen [P1] "a moment that passed G17a but was not rated (no error) should be stage 4, 'may open'". NOT A DEFECT: "may
   open" is package.can_open (pipeline/package.py:1417), which is hook eligibility AND G17a AND the render's opener
   rule. A moment that passes G17a but fails another of them never reaches "may open"; it stops before it, where the
   driver puts it, with "cannot open (hook eligibility or the render's opener rule)". The test already covers this
   case (moment "x" in test_each_moment_stops_where_its_record_says: stage 3, "cannot open"). The STAGES comment now
   says what "may open" means.
2. glm [P1] "medley_trace reads the rating before the second-pass / trim-cut / G17a failures; the order rests on
   undocumented record semantics". FIXED: every failure is now checked before the rating. A rated moment passed all of
   them (package.build rates ONLY its openers, :2643-2645), so it still reaches the rating. A record holding both a
   failure and a rating for one id would now stop at the failure. A new test builds that inconsistent record (stage 2,
   "L-v 2 FAIL"); mutation H16 (the rating first) is killed.

THE P2 / P3s:
3. glm [P2] "the hook pass's 'a model was called' is a heuristic (cost > 0 or >= 1 s)". FIXED with pp-ingest's own
   record: its `calls` table logs every hook-pass call (role hook / spotlight; kinds ok, invalid, cache). An event
   counts as called when such a call exists for its video since that video's previous event. The heuristic stays only
   for a database without `calls`. New test; mutation H17 killed. On the real data the classes move by one event
   (261 / 43 / 13).
4. glm [P2] "cache keys split on ':'". FIXED: rsplit(":", 2) on "<moment id>:<text sha>:<version>".
5. glm [P2] "a missing reference kills the whole run". FIXED: ref_moments records an unreadable reference with its error;
   the others are calibrated and parts (1), (3) and (4) still run. New test; mutation H18 killed.
6. glm [P3] "a ledger row without a moment id". FIXED: skipped (tested: a row with moment_id null).
7. glm [P2] "the stop is checked before each seed, so the last call could pass the cap". The cap still holds: the router's
   own limit is the order's $0.30 (providers.Router reserves each call's list-price upper bound and refuses one that
   would pass it). The $0.25 stop is ours, below it.
8. glm [P2] "spotlight step-A detection matches the text of `out`". The text is code-written: spotlight.build writes
   "step A: ..." or "no verdict (law L-m)" for exactly that stop (pipeline/spotlight.py, the `stop(...)` after the
   prescreen). It is the record's only encoding of the stage. No change.
9. glm [P2] "held-back counts: a moment he

---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_20261115_1129/C2_STEP.diff (784 lines)
```
   1 | diff --git a/tests/package/hook112.py b/tests/package/hook112.py
   2 | new file mode 100644
   3 | index 0000000..fdba4ba
   4 | --- /dev/null
   5 | +++ b/tests/package/hook112.py
   6 | @@ -0,0 +1,514 @@
   7 | +#!/usr/bin/env python3
   8 | +"""RULING 112 (orchestrator 11:15 ET Nov 15): THE HOOK SCARCITY DIAGNOSIS. No bar, gate or routing changes.
   9 | +
  10 | +Read-only on every build record (tests/package/proof/ledger_*), the hook cache, pp-ingest's ledger and its queue
  11 | +database (opened mode=ro). The ONE paid part is the calibration (part 2): the hook job as it stands today
  12 | +(package.hook_ratings and package.HOOKS_PROMPT, unchanged) on the approved hooks. It runs on Heimdall only: the hook
  13 | +chain of ruling 88 (coherence_verdict:hook) with every non-Heimdall back-end removed, and no shadow. It uses its own
  14 | +spend ledger, a stop below the order's cap, and no cache (fresh ratings; the production cache is neither read nor
  15 | +written).
  16 | +
  17 | +-> tests/package/proof/hook112/:
  18 | +- FUNNEL.json (1): per build, and per DISTINCT moment, how far each one got toward the hook job and what stopped it.
  19 | +- CALIBRATION.json (2).
  20 | +- NEAR_MISSES.json (3).
  21 | +- HOOK_PASS.json (4).
  22 | +- REPORT.md.
  23 | +Usage: python3 -B tests/package/hook112.py [--no-calibration] [--hours 48] [--since 2026-11-13T16:15:00+00:00]"""
  24 | +import argparse
  25 | +import collections
  26 | +import glob
  27 | +import json
  28 | +import os
  29 | +import re
  30 | +import sqlite3
  31 | +import sys
  32 | +from datetime import datetime, timedelta, timezone
  33 | +
  34 | +HERE = os.path.dirname(os.path.abspath(__file__))
  35 | +REPO = os.path.dirname(os.path.dirname(HERE))
  36 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
  37 | +sys.path.insert(0, HERE)
  38 | +
  39 | +PROOF = os.path.join(HERE, "proof")
  40 | +OUT = os.path.join(PROOF, "hook112")
  41 | +SPEND = os.path.join(PROOF, "SPEND_H112.json")
  42 | +LIMIT_USD, STOP_USD = 0.30, 0.25          # the order's cap; no call starts at or over the stop
  43 | +SEEDS = (7, 8, 9)                        # 7 is production's; 8 and 9 show how stable a rating is
  44 | +INGEST = os.environ.get("PP_INGEST_ROOT", "/home/ultron/worktrees/pp-ingest")
  45 | +QUEUE_DB = os.path.join(INGEST, "data", "editorial", "ingest", "queue.sqlite")
  46 | +LEDGER = os.path.join(INGEST, "data", "editorial", "moments", "moment_ledger.jsonl")
  47 | +REFS = [("preview", "the protected preview (L-d, PBX 2026-11-11)",
  48 | +         os.path.join(REPO, "references", "pulse_preview_2026-11-11", "PIN.json")),
  49 | +        ("37c5b5f5", "the protected moments reference 37c5b5f5",
  50 | +         os.path.join(PROOF, "fresh_20261112_050611", "MOMENTS_PIN.json")),
  51 | +        ("41f29b1f", "the protected medley reference 41f29b1f",
  52 | +         os.path.join(PROOF, "fresh_20261112_050611", "MOMENTS_PIN_LY.json")),
  53 | +        ("0c68b589", "the published medley 0c68b589",
  54 | +         os.path.join(PROOF, "ledger_20261113_183302", "MOMENTS_PIN_ATTESTED.json")),
  55 | +        ("13949b7c", "the last sealed medley 13949b7c (delivered as a pass 17:14 ET Nov 13)",
  56 | +         os.path.join(PROOF, "ledger_20261113_215708", "MOMENTS_PIN_LEDGER.json"))]
  57 | +
  58 | +# THE COMMON STAGES toward the hook job, on which both paths (the medley's and the spotlight's) are placed. "may open"
  59 | +# is package.can_open: hook eligibility AND G17a AND the render's opener rule (pipeline/package.py:1417); a moment
  60 | +# that passes G17a but fails another of them stops before it.
  61 | +STAGES = ("in a pool", "passed the free screens", "cleared step A", "passed the second pass and CUTTABLE",
  62 | +          "may open", "rated by the hook job", "rated >= 4")
  63 | +
  64 | +
  65 | +def base(mid):
  66 | +    """A variant (~trim, ~tail) is its moment's speech: one distinct moment."""
  67 | +    return str(mid).split("~")[0]
  68 | +
  69 | +
  70 | +def reason_class(why):
  71 | +    """A short, stable class for a free-text reason (the full texts stay in FUNNEL.json)."""
  72 | +    w = str(why or "")
  73 | +    for pat, cls in ((r"over the 20\.0 s", "over the medley's 20 s"), (r"over the 35\.0 s", "over the spotlight's 35 s"),
  74 | +                     (r"topic rule", "STAND_ALONE topic rule (ruling 34)"),
  75 | +                     (r"STAND_ALONE with the clip scorer|STAND_ALONE", "STAND_ALONE opener rule"),
  76 | +                     (r"ALONE scorer", "the ALONE scorer below 4 (ruling 109, free)"),
  77 | +                     (r"not eligible on screen", "not eligible on screen (opener)"),
  78 | +                     (r"genuine quiet|G17a", "G17a: no genuine quiet before the onset"),
  79 | +                     (r"second pass disagrees|L-v 2 FAIL", "L-v 2: the second pass disagrees"),
  80 | +                     (r"not cuttable", "not cuttable at an edge"), (r"NOT MEASURED", "not measured"),
  81 | +                     (r"cannot open", "cannot open (hook eligibility or the render's opener rule)"),
  82 | +                     (r"ad-read|ad_read", "ad-read marker"), (r"time.sensitive|ruling 76", "stale or time words"),
  83 | +                     (r"speaker", "speaker rule"), (r"fewer than 3 channels|channel\(s\) after the free stages",
  84 | +                                                     "the medley's 3-channel rule"),
  85 | +                     (r"re-posted|ruling 53", "re-posted by a second channel (ruling 53)"),
  86 | +                     (r"not rated", "not rated (the hook call failed)")):
  87 | +        if re.search(pat, w):
  88 | +            return cls
  89 | +    m = re.match(r"step A: ([A-Z_]+)", w)
  90 | +    if m:
  91 | +        return "step A: " + m.group(1)
  92 | +    return w[:60] or "unknown"
  93 | +
  94 | +
  95 | +def build_records(proof=PROOF, since=None):
  96 | +    """[(name, package.json, inputs.json)] of every finished build whose dir name (UTC) is >= since."""
  97 | +    out = []
  98 | +    for d in sorted(glob.glob(os.path.join(proof, "ledger_*"))):
  99 | +        name = os.path.basename(d)
 100 | +        if since and name < since:
 101 | +            continue
 102 | +        try:
 103 | +            with open(os.path.join(d, "package.json")) as f:
 104 | +                pk = json.load(f)
 105 | +            with open(os.path.join(d, "inputs.json")) as f:
 106 | +                inp = json.load(f)
 107 | +        except (OSError, ValueError):
 108 | +            continue
 109 | +        out.append((name, pk, inp))
 110 | +    return out
 111 | +
 112 | +
 113 | +def medley_trace(pk, inp):
 114 | +    """{moment id: (common stage reached, why it stopped there or None, rating record or None)} for the medley path."""
 115 | +    pre = pk.get("prescreen") or {}
 116 | +    hp = pk.get("hook_pool") or {}
 117 | +    ratings = hp.get("ratings") or {}
 118 | +    unusable, no_role, ad = pk.get("unusable") or {}, pk.get("no_role") or {}, pk.get("ad_read") or {}
 119 | +    reposted = pk.get("reposted") or {}
 120 | +    failed, second, onset = pre.get("failed") or {}, pre.get("second_pass") or {}, pre.get("hook_onset") or {}
 121 | +    trim_cut = pre.get("trim_cut") or {}
 122 | +    pool = [m.get("moment_id") for m in inp.get("moments") or [] if isinstance(m, dict)]
 123 | +    ids = list(dict.fromkeys(pool + list(failed) + list(second) + list(onset) + list(ratings) +
 124 | +                             list((pk.get("trimmed") or {}).values())))
 125 | +    went_on = "second_pass" in pre                     # the medley passed the 3-channel rule on the cleared moments
 126 | +    out = {}
 127 | +    for mid in ids:
 128 | +        if mid in unusable:
 129 | +            out[mid] = (0, unusable[mid], None)
 130 | +        elif mid in no_role:
 131 | +            out[mid] = (0, no_role[mid], None)
 132 | +        elif mid in ad:
 133 | +            out[mid] = (0, ad[mid], None)
 134 | +        elif mid in reposted:
 135 | +            out[mid] = (0, f"re-posted by a second channel (ruling 53): {reposted[mid]}", None)
 136 | +        elif mid in failed:
 137 | +            out[mid] = (1, "step A: " + "; ".join(failed[mid]), None)
 138 | +        elif mid in second and second[mid] != "PASS":    # every failure before the rating: package.build rates ONLY
 139 | +            out[mid] = (2, second[mid], None)            # its openers (pipeline/package.py:2643-2645), so a record
 140 | +        elif mid in trim_cut:                            # never holds both; were it to, the failure is the stop
 141 | +            out[mid] = (3, trim_cut[mid], None)
 142 | +        elif mid in onset and onset[mid] != "PASS":
 143 | +            out[mid] = (3, onset[mid], None)
 144 | +        elif mid in ratings:
 145 | +            r = ratings[mid]
 146 | +            own = own_rating(r)                        # as it stands today (ruling 61), as the near misses read it
 147 | +            ge4 = isinstance(own, int) and own >= 4
 148 | +            out[mid] = (6 if ge4 else 5, None if ge4 else f"rated {own}", r)
 149 | +        elif mid in onset and hp.get("error"):
 150 | +            out[mid] = (4, f"not rated (the hook call failed): {hp['error']}", None)
 151 | +        elif mid in onset:
 152 | +            out[mid] = (3, "cannot open (hook eligibility or the render's opener rule)", None)
 153 | +        elif not went_on and mid in pool and pre.get("cleared") is not None and mid not in failed and \
 154 | +                (pre.get("screened") or 0) > 0:
 155 | +            out[mid] = (2, "the medley ended at its 3-channel rule (fewer than 3 channels cleared step A)", None)
 156 | +        elif mid in pool:
 157 | +            out[mid] = (1, pk.get("why_none") or "the medley ended before step A", None)
 158 | +    return out
 159 | +
 160 | +
 161 | +def spotlight_trace(pk):
 162 | +    """{moment id: (common stage, why or None, hook_own or None)} for the spotlight path, its widened spans under the
 163 | +    moment they came from."""
 164 | +    sp = pk.get("spotlight") or {}
 165 | +    pool = sp.get("pool") or {}
 166 | +    snapped = {k: (v or {}).get("from") for k, v in (pool.get("snapped") or {}).items() if isinstance(v, dict)}
 167 | +    out = {}
 168 | +    for mid, why in (dict(pool.get("out") or {})).items():
 169 | +        out[snapped.get(mid, mid)] = (0, why, None)
 170 | +    for mid, m in (sp.get("moments") or {}).items():
 171 | +        if not isinstance(m, dict):
 172 | +            continue
 173 | +        st, why, own = int(m.get("stage") or 0), m.get("out"), m.get("hook_own")
 174 | +        if own is not None:
 175 | +            c = (6, None, own) if own >= 4 else (5, why, own)
 176 | +        else:
 177 | +            stepa = st == 0 and (str(why).startswith("step A") or "no verdict (law L-m)" in str(why))
 178 | +            c = {0: (1 if stepa else 0, why, None), 1: (2, why, None), 2: (3, why, None)}.get(st, (4, why, None))
 179 | +        k = snapped.get(mid, mid)
 180 | +        if k not in out or c[0] > out[k][0]:
 181 | +            out[k] = c
 182 | +    return out
 183 | +
 184 | +
 185 | +def funnel(records):
 186 | +    """Per build counts on the common stages, and the distinct roll-up: every moment (by base id) at its furthest
 187 | +    stage over every build and both paths, with the reason it stopped there."""
 188 | +    per_build, best = [], {}
 189 | +    for name, pk, inp in records:
 190 | +        md, st = medley_trace(pk, inp), spotlight_trace(pk)
 191 | +        row = {"build": name, "pool": len(inp.get("moments") or []), "why_none": str(pk.get("why_none") or "")[:200]}
 192 | +        for path, tr in (("medley", md), ("spotlight", st)):
 193 | +            row[path] = {s: sum(1 for c in tr.values() if c[0] >= i) for i, s in enumerate(STAGES)}
 194 | +        per_build.append(row)
 195 | +        for tr in (md, st):
 196 | +            for mid, c in tr.items():
 197 | +                k = base(mid)
 198 | +                if k not in best or c[0] >= best[k][0]:      # a tie keeps the LATEST build's reason
 199 | +                    best[k] = (c[0], c[1], name)
 200 | +    stops = collections.defaultdict(collections.Counter)
 201 | +    for k, (stage, why, _) in best.items():
 202 | +        if stage < 5:
 203 | +            stops[STAGES[stage + 1]][reason_class(why)] += 1
 204 | +    return {"builds": per_build, "distinct": len(best),
 205 | +            "distinct_by_stage": {s: sum(1 for c in best.values() if c[0] >= i) for i, s in enumerate(STAGES)},
 206 | +            "never_rated_stopped_before": {s: dict(c.most_common()) for s, c in stops.items()},
 207 | +            "furthest": {k: {"stage": STAGES[c[0]], "why": c[1], "build": c[2]} for k, c in sorted(best.items())}}
 208 | +
 209 | +
 210 | +def ledger_of(records):
 211 | +    """{build moment id: pp-ingest's ledger moment id}: a build re-anchors each ledger row and gives the moment an id
 212 | +    of its own (mined.ledger_moment_id keeps the row's); a variant (~trim, ~tail) and a spotlight's widened span
 213 | +    (pool.snapped[...]["from"]) map to the moment they came from."""
 214 | +    out = {}
 215 | +    for _, pk, inp in records:
 216 | +        for m in inp.get("moments") or []:
 217 | +            if isinstance(m, dict) and m.get("moment_id"):
 218 | +                lid = (m.get("mined") or {}).get("ledger_moment_id")
 219 | +                if lid:
 220 | +                    out[m["moment_id"]] = lid
 221 | +        for new, v in ((((pk.get("spotlight") or {}).get("pool") or {}).get("snapped")) or {}).items():
 222 | +            if isinstance(v, dict) and v.get("from"):
 223 | +                out.setdefault(new, v["from"])
 224 | +    def resolve(v, depth=0):                         # widened span -> its moment (maybe a variant) -> the ledger row
 225 | +        if depth < 4 and v in out and out[v] != v:
 226 | +            return resolve(out[v], depth + 1)
 227 | +        if depth < 4 and base(v) != v:
 228 | +            return resolve(base(v), depth + 1)
 229 | +        return v
 230 | +    return {k: resolve(v) for k, v in out.items()}
 231 | +
 232 | +
 233 | +def ledger_id(mid, lmap):
 234 | +    return lmap.get(mid) or lmap.get(base(mid)) or base(mid)
 235 | +
 236 | +
 237 | +def own_rating(r):
 238 | +    """The own-job rating as it stands today (ruling 61): the lower of scroll and alone; the recorded one when the
 239 | +    parts are missing."""
 240 | +    if isinstance(r.get("scroll"), int) and isinstance(r.get("alone"), int):
 241 | +        return min(r["scroll"], r["alone"])
 242 | +    return r.get("rating")
 243 | +
 244 | +
 245 | +def all_ratings(records, cache):
 246 | +    """{(moment id, rater): rating record with its text and the builds that used it}: the medley's records, and the
 247 | +    spotlight's own-job ratings completed from the hook cache (same moment id; the parts are the cache's)."""
 248 | +    texts = {}
 249 | +    for _, pk, inp in records:
 250 | +        for m in inp.get("moments") or []:
 251 | +            if isinstance(m, dict) and m.get("moment_id"):
 252 | +                texts.setdefault(m["moment_id"], m.get("text") or "")
 253 | +        for mid, m in ((pk.get("spotlight") or {}).get("moments") or {}).items():
 254 | +            if isinstance(m, dict):
 255 | +                texts.setdefault(mid, m.get("text") or "")
 256 | +    by_id = collections.defaultdict(list)
 257 | +    for key, recs in (cache or {}).items():
 258 | +        for rater, rec in (recs or {}).items():
 259 | +            by_id[key.rsplit(":", 2)[0]].append((rater, rec))       # "<moment id>:<text sha>:<version>"
 260 | +    out = {}
 261 | +    for name, pk, _ in records:
 262 | +        for mid, r in (((pk.get("hook_pool") or {}).get("ratings")) or {}).items():
 263 | +            k = (mid, r.get("backend"))
 264 | +            out.setdefault(k, dict({p: r.get(p) for p in ("scroll", "alone", "setup", "why")}, rating=own_rating(r),
 265 | +                                   rating_recorded=r.get("rating"), moment_id=mid, rater=r.get("backend"),
 266 | +                                   text=texts.get(mid, ""), builds=[]))
 267 | +            out[k]["builds"].append(name)
 268 | +        for mid, m in (((pk.get("spotlight") or {}).get("moments")) or {}).items():
 269 | +            if not isinstance(m, dict) or m.get("hook_own") is None:
 270 | +                continue
 271 | +            for rater, rec in by_id.get(mid, []) or [(None, {})]:
 272 | +                k = (mid, rater)
 273 | +                out.setdefault(k, dict({p: rec.get(p) for p in ("scroll", "alone", "setup", "why")},
 274 | +                                       rating=own_rating(dict(rec, rating=m.get("hook_own"))),
 275 | +                                       rating_recorded=m.get("hook_own"), moment_id=mid, rater=rater,
 276 | +                                       text=texts.get(mid, ""), builds=[]))
 277 | +                out[k]["builds"].append(name)
 278 | +    return out
 279 | +
 280 | +
 281 | +def snapped_map(records):
 282 | +    """{a spotlight's widened span id: the moment id it came from}, over every build."""
 283 | +    out = {}
 284 | +    for _, pk, _ in records:
 285 | +        for new, v in ((((pk.get("spotlight") or {}).get("pool") or {}).get("snapped")) or {}).items():
 286 | +            if isinstance(v, dict) and v.get("from"):
 287 | +                out[new] = v["from"]
 288 | +    return out
 289 | +
 290 | +
 291 | +def near_misses(ratings, n=10, fold=None):
 292 | +    """The n highest-rated hooks (rating, then the sum of the three parts), one per moment, and which part holds a
 293 | +    3 back from a 4. The rating is the own-job rating (ruling 61: the lower of scroll and alone)."""
 294 | +    best, fold = {}, fold or {}
 295 | +    for r in ratings.values():
 296 | +        if not isinstance(r.get("rating"), int):
 297 | +            continue
 298 | +        k = base(fold.get(r["moment_id"], r["moment_id"]))
 299 | +        key = (r["rating"], sum(int(r.get(p) or 0) for p in ("scroll", "alone", "setup")))
 300 | +        if k not in best or key > best[k][0]:
 301 | +            best[k] = (key, r)
 302 | +    top = [r for _, r in sorted(best.values(), key=lambda x: (-x[0][0], -x[0][1], x[1]["moment_id"]))[:n]]
 303 | +    threes = [r for _, r in best.values() if r["rating"] == 3]
 304 | +    held = collections.Counter()
 305 | +    for r in threes:
 306 | +        for p in ("scroll", "alone"):
 307 | +            if r.get(p) == 3:
 308 | +                held[p] += 1
 309 | +        if isinstance(r.get("setup"), int) and r["setup"] <= 3:
 310 | +            held["setup (not in the own-job rating since ruling 61)"] += 1
 311 | +    hist = collections.Counter(r["rating"] for _, r in best.values())
 312 | +    return {"top": top, "rated_distinct": len(best), "ratings": dict(sorted(hist.items())), "threes": len(threes),
 313 | +            "threes_held_back_by": dict(held.most_common())}
 314 | +
 315 | +
 316 | +def never_in_pool(lid, inputs_report):
 317 | +    """Why a ledger row gave no moment, from a build's own inputs report (ledger_build.build_inputs)."""
 318 | +    rep = inputs_report or {}
 319 | +    if lid in set(((rep.get("word_pass") or {}).get("refused")) or ()):
 320 | +        return "refused by the word pass (not sentence-ready; never re-worked)"
 321 | +    if lid in (rep.get("not_anchored") or {}):
 322 | +        return "did not re-anchor: " + str(rep["not_anchored"][lid])[:120]
 323 | +    if lid in (rep.get("duplicates_of") or {}):
 324 | +        return "a duplicate of " + str(rep["duplicates_of"][lid])
 325 | +    return "no moment in the latest build (not in its 12-h ledger, or no word record)"
 326 | +
 327 | +
 328 | +def hook_pass(db_path=QUEUE_DB, since_ts=None, videos=(), ledger=LEDGER, rated_ids=(), furthest=None,
 329 | +              inputs_report=None):
 330 | +    """Ruling 80's hook pass, from pp-ingest's own queue (read-only): its events since since_ts, classed; the given
 331 | +    videos' events and hook rows; whether any of their hook rows reached the hook job (rated_ids: LEDGER ids), and
 332 | +    how far each got (furthest: {ledger id: {"stage", "why"}})."""
 333 | +    db = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
 334 | +    db.row_factory = sqlite3.Row
 335 | +    ev = db.execute("SELECT e.at, e.ts, e.video_id, e.detail, c.display_name AS channel, v.title, v.moments "
 336 | +                    "FROM events e LEFT JOIN videos v ON v.video_id = e.video_id "
 337 | +                    "LEFT JOIN channels c ON c.channel_id = e.channel_id WHERE e.kind = 'hooks' AND e.ts >= ? "
 338 | +                    "ORDER BY e.ts", (since_ts or 0,)).fetchall()
 339 | +    has_calls = bool(db.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'calls'").fetchone())
 340 | +    classes, per_channel, mine, last_ts = collections.Counter(), collections.defaultdict(collections.Counter), [], {}
 341 | +    for r in ev:
 342 | +        d = json.loads(r["detail"] or "{}")
 343 | +        if has_calls:                                  # the hook pass's own calls since this video's previous event
 344 | +            called = bool(db.execute("SELECT 1 FROM calls WHERE video_id = ? AND role IN ('hook', 'spotlight') "
 345 | +                                     "AND ts > ? AND ts <= ? LIMIT 1",
 346 | +                                     (r["video_id"], last_ts.get(r["video_id"], 0.0), r["ts"])).fetchone())
 347 | +        else:                                          # no calls table: its cost or its time says so
 348 | +            called = bool((d.get("cost") or 0) > 0 or (d.get("seconds_hook") or 0) >= 1)
 349 | +        last_ts[r["video_id"]] = r["ts"]
 350 | +        cls = ("wrote rows" if d.get("rows") else "0 rows") + (", a model called" if called else ", no model call")
 351 | +        classes[cls] += 1
 352 | +        per_channel[r["channel"] or "?"][cls] += 1
 353 | +        if r["video_id"] in videos:
 354 | +            mine.append({"at": r["at"], "video_id": r["video_id"], "channel": r["channel"], "title": r["title"],
 355 | +                         "moments": r["moments"], **d})
 356 | +    hook_rows = collections.defaultdict(list)
 357 | +    try:
 358 | +        with open(ledger) as f:
 359 | +            for line in f:
 360 | +                try:
 361 | +                    row = json.loads(line)
 362 | +                except ValueError:
 363 | +                    continue
 364 | +                if isinstance(row, dict) and row.get("video_id") in videos and row.get("moment_id") and \
 365 | +                        (row.get("mined") or {}).get("pass") == "hook":
 366 | +                    hook_rows[row["video_id"]].append(row.get("moment_id"))
 367 | +    except OSError:
 368 | +        pass
 369 | +    reached = {v: sorted(set(ids) & set(rated_ids)) for v, ids in hook_rows.items()}
 370 | +    how_far = {v: {i: (furthest or {}).get(i) or {"stage": "never in a build's pool",
 371 | +                                                    "why": never_in_pool(i, inputs_report)} for i in ids}
 372 | +               for v, ids in hook_rows.items()}
 373 | +    return {"events": len(ev), "classes": dict(classes.most_common()),
 374 | +            "per_channel": {c: dict(x) for c, x in sorted(per_channel.items())}, "today": mine,
 375 | +            "hook_rows": {v: len(ids) for v, ids in hook_rows.items()}, "hook_rows_rated": reached,
 376 | +            "hook_rows_furthest": how_far}
 377 | +
 378 | +
 379 | +def ref_moments(refs=REFS):
 380 | +    """The approved hooks as the hook job reads a moment: an id of their own (so no production cache entry can
 381 | +    answer for them), the approved text verbatim, and the channel's name on screen."""
 382 | +    out = []
 383 | +    for key, label, path in refs:
 384 | +        try:
 385 | +            with open(path) as f:
 386 | +                seg = json.load(f)["segments"][0]
 387 | +        except (OSError, ValueError, KeyError, IndexError, TypeError) as e:   # recorded; the others are still asked
 388 | +            out.append({"moment_id": f"ref-{key}", "label": label, "error": f"{type(e).__name__}: {e}"})
 389 | +            continue
 390 | +        out.append({"moment_id": f"ref-{key}", "text": seg.get("approved_text") or seg.get("text") or "",
 391 | +                    "channel_id": f"ref:{seg.get('video_id')}", "channel_name": seg.get("channel") or "?",
 392 | +                    "label": label, "video_id": seg.get("video_id"),
 393 | +                    "seconds": round(float(seg.get("end") or 0) - float(seg.get("start") or 0), 2)})
 394 | +    return out
 395 | +
 396 | +
 397 | +def heimdall_hook_chain(router):
 398 | +    """Ruling 88's hook list as production reads it, with every non-Heimdall back-end removed (the order: Heimdall
 399 | +    only). Refused when none is left."""
 400 | +    chain = [n for n in router.chain("coherence_verdict", "hook")   # a Heimdall back-end's vendor is "heimdall/<family>"
 401 | +             if str(getattr(router.backends.get(n), "vendor", "")).split("/")[0] == "heimdall"]
 402 | +    if not chain:
 403 | +        raise RuntimeError("refused: ruling 88's hook list has no Heimdall back-end")
 404 | +    return chain
 405 | +
 406 | +
 407 | +def build_router(spend_path=SPEND, record_dir=None):
 408 | +    import deadline_table as DT
 409 | +    import providers as P
 410 | +    import replay85 as R
 411 | +    r = P.Router(env_path=R.ENV, record_dir=record_dir, spend_path=spend_path, limit_usd=LIMIT_USD,
 412 | +                 limit_basis="reported", routing="heimdall_first", deadlines=DT.load(DT.STATE, None))
 413 | +    r.chains["coherence_verdict:hook"] = heimdall_hook_chain(r)
 414 | +    return r
 415 | +
 416 | +
 417 | +def calibrate(router, refs, ctx, seeds=SEEDS, stop_usd=STOP_USD, rate=None):
 418 | +    """The hook job as it stands today (package.hook_ratings, cache None) on the approved hooks, once per seed, as
 419 | +    production asks it: avoiding the writers' vendor and family (package._writers). A call is made only under the
 420 | +    stop. -> [{"seed", "ratings": {id: record} or {}, "error"}]."""
 421 | +    import package as PK
 422 | +    rate = rate or PK.hook_ratings
 423 | +    wv, wf = PK._writers(router)
 424 | +    runs = []
 425 | +    for s in seeds:
 426 | +        if router.spent() >= stop_usd:
 427 | +            runs.append({"seed": s, "ratings": {}, "error": f"stopped: ${router.spent():.4f} spent (stop "
 428 | +                                                            f"${stop_usd:.2f})"})
 429 | +            continue
 430 | +        got, err = rate(router, refs, ctx, wv, wf, cache=None, seed=s)
 431 | +        runs.append({"seed": s, "ratings": got, "error": err, "writers": [sorted(wv), sorted(wf)]})
 432 | +    return runs
 433 | +
 434 | +
 435 | +def report(fun, cal, nm, hp):
 436 | +    L = ["# RULING 112: THE HOOK SCARCITY DIAGNOSIS", ""]
 437 | +    L += ["## (1) THE FUNNEL (the last 48 h of builds)", "",
 438 | +          f"{len(fun['builds'])} builds; {fun['distinct']} distinct moments (a variant is its moment).", "",
 439 | +          "| stage | distinct moments that reached it |", "|---|---|"]
 440 | +    L += [f"| {s} | {n} |" for s, n in fun["distinct_by_stage"].items()]
 441 | +    L += ["", "Never rated by the hook job, by the stage that stopped them (reason classes):", ""]
 442 | +    for s, c in fun["never_rated_stopped_before"].items():
 443 | +        L.append(f"- before \"{s}\": " + "; ".join(f"{k} {n}" for k, n in c.items()))
 444 | +    L += ["", "Per build (medley / spotlight: in a pool, may open, rated, rated >= 4):", ""]
 445 | +    for b in fun["builds"]:
 446 | +        m, s = b["medley"], b["spotlight"]
 447 | +        L.append(f"- {b['build']}: medley {m['in a pool']} / {m['may open']} / {m['rated by the hook job']} / "
 448 | +                 f"{m['rated >= 4']}; spotlight {s['in a pool']} / {s['may open']} / {s['rated by the hook job']} / "
 449 | +                 f"{s['rated >= 4']}")
 450 | +    L += ["", "## (2) CALIBRATION (the hook job as it stands today, Heimdall only, no cache)", ""]
 451 | +    for run in cal.get("runs") or []:
 452 | +        L.append(f"- seed {run['seed']}: " + ("; ".join(
 453 | +            f"{k}: {r.get('rating')} (scroll {r.get('scroll')}, alone {r.get('alone')}, setup {r.get('setup')}; "
 454 | +            f"{r.get('backend')})" for k, r in (run.get("ratings") or {}).items()) or f"NO RATING: {run.get('error')}"))
 455 | +    L += ["", "## (3) THE NEAR MISSES", "",
 456 | +          f"{nm['rated_distinct']} distinct moments rated; ratings {nm['ratings']}; rated 3: {nm['threes']}, held back "
 457 | +          f"by {nm['threes_held_back_by']}", ""]
 458 | +    for r in nm["top"]:
 459 | +        L.append(f"- {r['rating']} (scroll {r.get('scroll')}, alone {r.get('alone')}, setup {r.get('setup')}; "
 460 | +                 f"{r.get('rater')}) {r['moment_id']}: \"{(r.get('text') or '')[:160]}\" -- {r.get('why')}")
 461 | +    L += ["", "## (4) THE HOOK-MINING PASS (ruling 80)", "", f"{hp['events']} events: {hp['classes']}", ""]
 462 | +    for e in hp["today"]:
 463 | +        L.append(f"- {e['at'][:16]} {e['channel']} {e['video_id']}: windows {e.get('windows')}, screened "
 464 | +                 f"{e.get('screened')}, rows {e.get('rows')}, spotlight rows {e.get('spotlight_rows')}, dropped "
 465 | +                 f"{e.get('dropped')}")
 466 | +    L += [f"- hook rows in the ledger: {hp['hook_rows']}; of them rated by the hook job: {hp['hook_rows_rated']}"]
 467 | +    return "\n".join(L) + "\n"
 468 | +
 469 | +
 470 | +def main(argv=None):
 471 | +    ap = argparse.ArgumentParser()
 472 | +    ap.add_argument("--hours", type=float, default=48.0)
 473 | +    ap.add_argument("--no-calibration", action="store_true")
 474 | +    ap.add_argument("--since", help="the window's start, ISO with a zone (default: --hours before now); the order's "
 475 | +                                    "48 h end at the order's own time")
 476 | +    a = ap.parse_args(argv)
 477 | +    now = datetime.now(timezone.utc)
 478 | +    start = datetime.fromisoformat(a.since) if a.since else now - timedelta(hours=a.hours)
 479 | +    if start.tzinfo is None:
 480 | +        raise SystemExit("refused: --since has no time zone")
 481 | +    since = start.astimezone(timezone.utc).strftime("ledger_%Y%m%d_%H%M%S")
 482 | +    os.makedirs(OUT, exist_ok=True)
 483 | +    recs = build_records(PROOF, since)
 484 | +    fun = funnel(recs)
 485 | +    with open(os.path.join(PROOF, "HOOK_CACHE.json")) as f:
 486 | +        cache = json.load(f)
 487 | +    rts = all_ratings(recs, cache)
 488 | +    nm = near_misses(rts, fold=snapped_map(recs))
 489 | +    today = sorted({m.get("video_id") for m in (recs[-1][2].get("moments") or [])} if recs else set())
 490 | +    lmap = ledger_of(recs)
 491 | +    rated_ids = {ledger_id(k[0], lmap) for k in rts}
 492 | +    by_ledger = {}
 493 | +    for k, v in fun["furthest"].items():                 # the furthest stage of each moment, by its ledger id
 494 | +        lid = ledger_id(k, lmap)
 495 | +        if lid not in by_ledger or STAGES.index(v["stage"]) > STAGES.index(by_ledger[lid]["stage"]):
 496 | +            by_ledger[lid] = v
 497 | +    hp = hook_pass(QUEUE_DB, start.timestamp(), today, LEDGER, rated_ids, by_ledger,
 498 | +                   (recs[-1][2].get("inputs") if recs else None))
 499 | +    cal = {"refs": [], "runs": [], "skipped": a.no_calibration}
 500 | +    if not a.no_calibration:
 501 | +        import eligibility as E
 502 | +        import proof_saved_runs as PS
 503 | +        refs = ref_moments()
 504 | +        router = build_router(SPEND, os.path.join(OUT, "replies"))
 505 | +        ok = [r for r in refs if not r.get("error")]
 506 | +        cal = {"refs": refs, "chain": router.chain("coherence_verdict", "hook"),
 507 | +               "runs": calibrate(router, ok, E.Context(now, PS.REG)), "spent_usd": round(router.spent(), 6)}
 508 | +    for fname, obj in (("FUNNEL.json", fun), ("CALIBRATION.json", cal), ("NEAR_MISSES.json", nm),
 509 | +                       ("HOOK_PASS.json", hp)):
 510 | +        with open(os.path.join(OUT, fname), "w") as f:
 511 | +            json.dump(obj, f, indent=1, default=str)
 512 | +    with open(os.path.join(OUT, "REPORT.md"), "w") as f:
 513 | +        f.write(report(fun, cal, nm, hp))
 514 | +    print(f"ruling 112: {len(recs)} builds since {since}; {fun['distinct']} distinct moments; "
 515 | +          f"{nm['rated_distinct']} rated; calibration {'skipped' if a.no_calibration else cal.get('spent_usd')}")
 516 | +    return 0
 517 | +
 518 | +
 519 | +if __name__ == "__main__":
 520 | +    sys.exit(main())
 521 | diff --git a/tests/package/test_hook112.py b/tests/package/test_hook112.py
 522 | new file mode 100644
 523 | index 0000000..cead604
 524 | --- /dev/null
 525 | +++ b/tests/package/test_hook112.py
 526 | @@ -0,0 +1,257 @@
 527 | +#!/usr/bin/env python3
 528 | +"""RULING 112's diagnosis driver (tests/package/hook112.py), offline: where each moment stopped on the way to the hook
 529 | +job (both paths), the distinct roll-up, the near misses and the part that holds a 3 back, pp-ingest's hook pass read
 530 | +from a database of the same shape, and the calibration's guards (Heimdall only, no cache, the stop)."""
 531 | +import json
 532 | +import os
 533 | +import sqlite3
 534 | +import sys
 535 | +import tempfile
 536 | +import unittest
 537 | +
 538 | +HERE = os.path.dirname(os.path.abspath(__file__))
 539 | +REPO = os.path.dirname(os.path.dirname(HERE))
 540 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
 541 | +sys.path.insert(0, HERE)
 542 | +import hook112 as H  # noqa: E402
 543 | +
 544 | +
 545 | +def medley_pk(why_none=None, went_on=True, hook_error=None):
 546 | +    pre = {"screened": 9, "cleared": 6, "failed": {"f": ["REFERENT_OUTSIDE"]}}
 547 | +    if went_on:
 548 | +        pre.update(second_pass={"c": "L-v 2 FAIL", "t": "PASS", "o": "PASS", "x": "PASS", "r3": "PASS", "r4": "PASS"},
 549 | +                   hook_onset={"t": "PASS", "o": "FAIL: 0 ms of genuine quiet", "x": "PASS", "r3": "PASS",
 550 | +                               "r4": "PASS"},
 551 | +                   trim_cut={"t": "FAIL: no trimmed cut was reached"})
 552 | +    return {"unusable": {"u": "22.9 s: over the 20.0 s per source video (L-u) or unmeasured"},
 553 | +            "no_role": {"n": "the render's STAND_ALONE topic rule with the pin's screen (ruling 34)"},
 554 | +            "ad_read": {"a": "an ad-read marker"}, "reposted": {"p": "q"}, "prescreen": pre, "why_none": why_none,
 555 | +            "hook_pool": {"error": hook_error, "ratings": {} if not went_on else {
 556 | +                "r3": {"scroll": 3, "alone": 5, "setup": 4, "rating": 3, "why": "slow start"},
 557 | +                "r4": {"scroll": 4, "alone": 5, "setup": 2, "rating": 2, "why": "old rule: setup counted"}}}}
 558 | +
 559 | +
 560 | +def inputs(ids):
 561 | +    return {"moments": [{"moment_id": i, "text": f"text {i}", "mined": {"ledger_moment_id": f"L{i}"}} for i in ids]}
 562 | +
 563 | +
 564 | +POOL = ["u", "n", "a", "p", "f", "c", "t", "o", "x", "r3", "r4", "s"]
 565 | +
 566 | +
 567 | +class TestTheMedleyTrace(unittest.TestCase):
 568 | +
 569 | +    def test_each_moment_stops_where_its_record_says(self):
 570 | +        tr = H.medley_trace(medley_pk(), inputs(POOL))
 571 | +        got = {k: v[0] for k, v in tr.items()}
 572 | +        self.assertEqual(got, {"u": 0, "n": 0, "a": 0, "p": 0, "f": 1, "c": 2, "t": 3, "o": 3, "x": 3, "r3": 5,
 573 | +                               "r4": 6, "s": 1})
 574 | +        self.assertIn("cannot open", tr["x"][1])                       # passed G17a, never rated: it cannot open
 575 | +        self.assertEqual(tr["r3"][1], "rated 3")
 576 | +        self.assertIsNone(tr["r4"][1])          # today's rule: the lower of scroll / alone (4), not the recorded 2
 577 | +
 578 | +    def test_a_failure_is_the_stop_even_beside_a_rating(self):
 579 | +        pk = medley_pk()                                   # a record package.build never writes: both, for one id
 580 | +        pk["hook_pool"]["ratings"]["c"] = {"scroll": 5, "alone": 5, "setup": 5, "rating": 5, "why": "w"}
 581 | +        self.assertEqual(H.medley_trace(pk, inputs(POOL))["c"][:2], (2, "L-v 2 FAIL"))
 582 | +
 583 | +    def test_the_3_channel_rule_and_a_failed_hook_call(self):
 584 | +        tr = H.medley_trace(medley_pk("6 moments cleared step A from fewer than 3 channels", went_on=False),
 585 | +                            inputs(POOL))
 586 | +        self.assertEqual((tr["t"][0], tr["f"][0]), (2, 1))           # cleared, then the medley ended
 587 | +        self.assertIn("3-channel rule", tr["t"][1])
 588 | +        tr = H.medley_trace(medley_pk(hook_error="ProviderError: no back-end"), inputs(POOL))
 589 | +        self.assertEqual(tr["x"][0], 4)                                # it may open; the call failed: not rated
 590 | +        self.assertIn("not rated", tr["x"][1])
 591 | +
 592 | +
 593 | +class TestTheSpotlightTrace(unittest.TestCase):
 594 | +
 595 | +    def test_free_screens_step_a_and_the_hook(self):
 596 | +        pk = {"spotlight": {"pool": {"out": {"long": "35.6 s: over the 35.0 s per source video"},
 597 | +                                     "snapped": {"w1": {"from": "m1"}}},
 598 | +                            "moments": {"al": {"stage": 0, "out": "the ALONE scorer: 2.0 (needs 4) (ruling 109)"},
 599 | +                                        "sa": {"stage": 0, "out": "step A: REFERENT_OUTSIDE"},
 600 | +                                        "lv": {"stage": 1, "out": "L-v 2 / CUTTABLE: the second pass disagrees"},
 601 | +                                        "co": {"stage": 2, "out": "it cannot open cold: G17a"},
 602 | +                                        "w1": {"stage": 3, "out": "the hook's own job rates 3", "hook_own": 3},
 603 | +                                        "h4": {"stage": 5, "out": "the visual check", "hook_own": 4}}}}
 604 | +        tr = H.spotlight_trace(pk)
 605 | +        self.assertEqual({k: v[0] for k, v in tr.items()},
 606 | +                         {"long": 0, "al": 0, "sa": 1, "lv": 2, "co": 3, "m1": 5, "h4": 6})   # w1 is m1's span
 607 | +
 608 | +
 609 | +class TestTheRollUp(unittest.TestCase):
 610 | +
 611 | +    def test_the_furthest_stage_over_builds_a_tie_keeps_the_latest_reason_and_variants_fold(self):
 612 | +        b1 = (medley_pk(), inputs(POOL))
 613 | +        pk2 = medley_pk()
 614 | +        pk2["prescreen"]["failed"] = {"f": ["CONDITION_OUTSIDE"]}       # the same stage, a newer reason
 615 | +        pk2["prescreen"]["second_pass"]["c~trim"] = "PASS"
 616 | +        pk2["prescreen"]["hook_onset"]["c~trim"] = "PASS"
 617 | +        pk2["hook_pool"]["ratings"]["c~trim"] = {"scroll": 2, "alone": 4, "setup": 2, "rating": 2, "why": "w"}
 618 | +        fu = H.funnel([("ledger_1", *b1), ("ledger_2", pk2, inputs(POOL))])
 619 | +        self.assertEqual(fu["furthest"]["f"]["why"], "step A: CONDITION_OUTSIDE")
 620 | +        self.assertEqual(fu["furthest"]["c"]["stage"], "rated by the hook job")   # its ~trim variant was rated
 621 | +        self.assertEqual((fu["distinct"], fu["distinct_by_stage"]["rated >= 4"]), (12, 1))
 622 | +        self.assertEqual(fu["never_rated_stopped_before"]["cleared step A"],      # s: in the pool, no stage record
 623 | +                         {"step A: CONDITION_OUTSIDE": 1, "the medley ended before step A": 1})
 624 | +
 625 | +
 626 | +class TestTheNearMisses(unittest.TestCase):
 627 | +
 628 | +    def test_ranked_one_per_moment_on_todays_rule_and_the_part_that_holds_a_3(self):
 629 | +        rs = {("a", "q"): {"moment_id": "a", "scroll": 4, "alone": 5, "setup": 5, "rating": 4},
 630 | +              ("a~trim", "q"): {"moment_id": "a~trim", "scroll": 4, "alone": 4, "setup": 4, "rating": 4},
 631 | +              ("w", "q"): {"moment_id": "w", "scroll": 5, "alone": 5, "setup": 5, "rating": 5},   # a span of b
 632 | +              ("b", "q"): {"moment_id": "b", "scroll": 3, "alone": 5, "setup": 3, "rating": 3},
 633 | +              ("c", "q"): {"moment_id": "c", "scroll": 3, "alone": 3, "setup": 5, "rating": 3},
 634 | +              ("d", "q"): {"moment_id": "d", "scroll": 2, "alone": 4, "setup": 4, "rating": 2},
 635 | +              ("e", "q"): {"moment_id": "e", "scroll": 3, "alone": 4, "setup": 3, "rating": 3}}
 636 | +        nm = H.near_misses(rs, n=3, fold={"w": "b"})
 637 | +        self.assertEqual([r["moment_id"] for r in nm["top"]], ["w", "a", "c"])   # b's best is its span w
 638 | +        self.assertEqual((nm["rated_distinct"], nm["threes"]), (5, 2))
 639 | +        self.assertEqual(nm["threes_held_back_by"], {"scroll": 2, "alone": 1,      # setup is shown apart: not a part
 640 | +                                                     "setup (not in the own-job rating since ruling 61)": 1})
 641 | +        self.assertEqual(H.own_rating({"scroll": 4, "alone": 5, "setup": 2, "rating": 2}), 4)   # ruling 61
 642 | +
 643 | +
 644 | +class TestTheHookPass(unittest.TestCase):
 645 | +
 646 | +    def db(self, d):
 647 | +        p = os.path.join(d, "queue.sqlite")
 648 | +        db = sqlite3.connect(p)
 649 | +        db.executescript("CREATE TABLE events (id INTEGER, at TEXT, ts REAL, video_id TEXT, channel_id TEXT, kind TEXT, "
 650 | +                         "detail TEXT); CREATE TABLE videos (video_id TEXT, title TEXT, moments INTEGER); "
 651 | +                         "CREATE TABLE channels (channel_id TEXT, display_name TEXT);")
 652 | +        db.executemany("INSERT INTO events VALUES (?, ?, ?, ?, ?, ?, ?)", [
 653 | +            (1, "2026-11-15T13:24:51", 100.0, "bl", "cb", "hooks", json.dumps({"rows": 0, "windows": 4, "cost": 0.0,
 654 | +                                                                               "seconds_hook": 0.1})),
 655 | +            (2, "2026-11-15T15:05:56", 200.0, "v1", "cm", "hooks", json.dumps({"rows": 2, "windows": 18, "cost": 0.004,
 656 | +                                                                               "seconds_hook": 9.0})),
 657 | +            (3, "2026-11-15T15:06:00", 210.0, "v2", "cm", "hooks", json.dumps({"rows": 0, "windows": 3, "cost": 0.001,
 658 | +                                                                               "seconds_hook": 4.0})),
 659 | +            (4, "2026-11-13T00:00:00", 1.0, "old", "cb", "hooks", json.dumps({"rows": 0}))])
 660 | +        db.executemany("INSERT INTO channels VALUES (?, ?)", [("cb", "Bloomberg Television"), ("cm", "Magazine")])
 661 | +        db.executemany("INSERT INTO videos VALUES (?, ?, ?)", [("bl", "IPO", 0), ("v1", "BTC", 29), ("v2", "BTC2", 3)])
 662 | +        db.commit()
 663 | +        db.close()
 664 | +        return p
 665 | +
 666 | +    def test_classes_the_given_videos_and_whether_their_hook_rows_reached_the_job(self):
 667 | +        with tempfile.TemporaryDirectory() as d:
 668 | +            led = os.path.join(d, "ledger.jsonl")
 669 | +            with open(led, "w") as f:
 670 | +                for mid, ps in (("h1", "hook"), ("h2", "hook"), ("m1", "moment"), ("h3", "hook"), (None, "hook")):
 671 | +                    f.write(json.dumps({"moment_id": mid, "video_id": "v1", "mined": {"pass": ps}}) + "\n")
 672 | +            hp = H.hook_pass(self.db(d), 50.0, ["v1"], led, rated_ids={"h1", "m1"},
 673 | +                             furthest={"h2": {"stage": "cleared step A", "why": "not cuttable"}},
 674 | +                             inputs_report={"word_pass": {"refused": ["h3"]}})
 675 | +        self.assertEqual(hp["classes"], {"0 rows, no model call": 1, "wrote rows, a model called": 1,
 676 | +                                         "0 rows, a model called": 1})        # the old event is outside the window
 677 | +        self.assertEqual(hp["per_channel"]["Bloomberg Television"], {"0 rows, no model call": 1})
 678 | +        self.assertEqual([e["video_id"] for e in hp["today"]], ["v1"])
 679 | +        self.assertEqual((hp["hook_rows"], hp["hook_rows_rated"]), ({"v1": 3}, {"v1": ["h1"]}))
 680 | +        self.assertEqual(hp["hook_rows_furthest"]["v1"]["h2"]["why"], "not cuttable")
 681 | +        self.assertIn("refused by the word pass", hp["hook_rows_furthest"]["v1"]["h3"]["why"])
 682 | +
 683 | +    def test_the_hook_pass_own_calls_decide_whether_a_model_was_called(self):
 684 | +        with tempfile.TemporaryDirectory() as d:
 685 | +            p = self.db(d)
 686 | +            db = sqlite3.connect(p)
 687 | +            db.execute("CREATE TABLE calls (id INTEGER, ts REAL, video_id TEXT, role TEXT, kind TEXT)")
 688 | +            db.executemany("INSERT INTO calls VALUES (?, ?, ?, ?, ?)", [(1, 90.0, "bl", "hook", "ok"),   # bl: asked
 689 | +                                                                        (2, 205.0, "v2", "mine", "ok")])  # not a hook
 690 | +            db.commit()
 691 | +            db.close()
 692 | +            hp = H.hook_pass(p, 50.0, [], os.path.join(d, "none.jsonl"))
 693 | +        self.assertEqual(hp["classes"], {"0 rows, a model called": 1, "wrote rows, no model call": 1,
 694 | +                                         "0 rows, no model call": 1})    # its calls, not the event's cost or time
 695 | +
 696 | +    def test_a_read_only_database_file_serves(self):
 697 | +        with tempfile.TemporaryDirectory() as d:
 698 | +            p = self.db(d)
 699 | +            os.chmod(p, 0o444)                        # a writer would fail to open a read-only file for writing
 700 | +            try:
 701 | +                self.assertEqual(H.hook_pass(p, 0.0, [], os.path.join(d, "none.jsonl"))["events"], 4)
 702 | +            finally:
 703 | +                os.chmod(p, 0o644)
 704 | +
 705 | +
 706 | +class TestTheLedgerIds(unittest.TestCase):
 707 | +
 708 | +    def test_a_span_a_variant_and_a_moment_resolve_to_the_ledger_row(self):
 709 | +        pk = {"spotlight": {"pool": {"snapped": {"w1": {"from": "m1~trim"}, "w2": {"from": "m2"}}}}}
 710 | +        inp = {"moments": [{"moment_id": "m1", "mined": {"ledger_moment_id": "L1"}},
 711 | +                           {"moment_id": "m2", "mined": {"ledger_moment_id": "L2"}}]}
 712 | +        lmap = H.ledger_of([("ledger_1", pk, inp)])
 713 | +        self.assertEqual([H.ledger_id(i, lmap) for i in ("w1", "w2", "m1", "m1~trim", "zz")],
 714 | +                         ["L1", "L2", "L1", "L1", "zz"])
 715 | +
 716 | +
 717 | +class B:
 718 | +    def __init__(self, vendor):
 719 | +        self.vendor, self.family = vendor, vendor
 720 | +
 721 | +
 722 | +class FakeRouter:
 723 | +    def __init__(self, chain, spent=0.0):
 724 | +        self._chain, self._spent, self.down, self.chains = chain, spent, set(), {}
 725 | +        self.backends = {"heimdall:qwen": B("heimdall/qwen"), "heimdall:glm": B("heimdall/glm"), "xai:grok": B("xai"),
 726 | +                         "openai:gpt": B("openai")}          # the vendors as providers.HeimdallBackend gives them
 727 | +
 728 | +    def chain(self, role, kind=None):
 729 | +        return list(self.chains.get(f"{role}:{kind}") or (["openai:gpt"] if role == "angle_write" else self._chain))
 730 | +
 731 | +    def spent(self):
 732 | +        return self._spent
 733 | +
 734 | +
 735 | +class TestTheCalibration(unittest.TestCase):
 736 | +
 737 | +    def test_the_drivers_router_asks_the_hook_job_on_heimdall_only(self):
 738 | +        with tempfile.TemporaryDirectory() as d:
 739 | +            r = H.build_router(spend_path=os.path.join(d, "SPEND.json"))
 740 | +        chain = r.chain("coherence_verdict", "hook")
 741 | +        self.assertTrue(chain and all(r.backends[n].vendor.split("/")[0] == "heimdall" for n in chain), chain)
 742 | +        self.assertNotIn("xai:grok-4.20-0309-reasoning", chain)
 743 | +        self.assertEqual(chain[0], "heimdall:qwen/qwen3.8-27b")       # ruling 88's order, Grok removed
 744 | +        self.assertEqual((r.limit_usd, r.limit_basis), (H.LIMIT_USD, "reported"))
 745 | +
 746 | +    def test_heimdall_only_and_refused_without_one(self):
 747 | +        self.assertEqual(H.heimdall_hook_chain(FakeRouter(["heimdall:qwen", "xai:grok", "heimdall:glm"])),
 748 | +                         ["heimdall:qwen", "heimdall:glm"])
 749 | +        with self.assertRaises(RuntimeError):
 750 | +            H.heimdall_hook_chain(FakeRouter(["xai:grok"]))
 751 | +
 752 | +    def test_production_writers_no_cache_every_seed_and_the_stop(self):
 753 | +        asked = []
 754 | +
 755 | +        def rate(router, ms, ctx, wv, wf, cache="unset", seed=None):
 756 | +            asked.append((cache, seed, sorted(wv)))
 757 | +            return {m["moment_id"]: {"rating": 4} for m in ms}, None
 758 | +        refs = [{"moment_id": "ref-a", "text": "t"}]
 759 | +        runs = H.calibrate(FakeRouter(["heimdall:qwen"]), refs, None, seeds=(7, 8), stop_usd=0.25, rate=rate)
 760 | +        self.assertEqual(asked, [(None, 7, ["openai"]), (None, 8, ["openai"])])   # no cache; the writers' vendor
 761 | +        self.assertEqual([r["seed"] for r in runs], [7, 8])
 762 | +        asked.clear()
 763 | +        runs = H.calibrate(FakeRouter(["heimdall:qwen"], spent=0.25), refs, None, seeds=(7,), stop_usd=0.25,
 764 | +                           rate=rate)
 765 | +        self.assertEqual((asked, runs[0]["ratings"]), ([], {}))                  # at the stop: no call
 766 | +        self.assertIn("stopped", runs[0]["error"])
 767 | +
 768 | +    def test_a_missing_reference_is_recorded_and_the_rest_are_kept(self):
 769 | +        refs = H.ref_moments([("gone", "a reference that is not there", "/nonexistent/PIN.json")] + H.REFS[:1])
 770 | +        self.assertEqual((refs[0]["moment_id"], "error" in refs[0], refs[1]["moment_id"]),
 771 | +                         ("ref-gone", True, "ref-preview"))
 772 | +        self.assertTrue(refs[1]["text"])
 773 | +
 774 | +    def test_the_approved_hooks_get_ids_no_production_cache_entry_can_answer(self):
 775 | +        refs = H.ref_moments()
 776 | +        self.assertEqual([r["moment_id"] for r in refs], [f"ref-{k}" for k, _, _ in H.REFS])
 777 | +        cache = json.load(open(os.path.join(H.PROOF, "HOOK_CACHE.json")))
 778 | +        self.assertFalse(any(k.split(":")[0].startswith("ref-") for k in cache))
 779 | +        self.assertTrue(all(r["text"] for r in refs))
 780 | +
 781 | +
 782 | +if __name__ == "__main__":
 783 | +    unittest.main()
 784 | 
```

---

pp-selectid: RULING 112 (orchestrator 11:15 ET Nov 15), THE HOOK SCARCITY DIAGNOSIS. A new driver,
tests/package/hook112.py, and its tests. No bar, gate or routing changes; nothing in pipeline/ is touched.

THE ORDER, in short: before anyone touches the hook bar, find whether the supply is truly weak or the path to a hook
is too narrow. Heimdall only, cap $0.30. The parts:
(1) the funnel for the last 48 h of builds: pool -> allowed to open (with the exclusions by reason) -> rated by the
    hook job -> rated >= 4; how many DISTINCT moments were ever rated, and how many never were, and what removed them;
(2) calibration: the hook job as it stands today on the approved hooks (the protected preview, 37c5b5f5, 41f29b1f,
    the published 0c68b589); an approved hook rated below 4 means rater drift;
(3) the 10 best hooks of the 48 h with their parts and reason, and which part most often holds a 3 back from a 4;
(4) pp-ingest's hook-mining pass (ruling 80) for today's videos;
(5) a recommendation (written by hand from the outputs; not code).

THE DRIVER, READ-ONLY EXCEPT PART (2):
- build_records: every tests/package/proof/ledger_*/package.json and inputs.json since a cutoff.
- medley_trace / spotlight_trace place each moment on ONE scale of 7 stages ("in a pool" ... "rated >= 4") from each
  build's own record:
  - the medley: unusable, no_role, ad_read, reposted, prescreen.failed / second_pass / hook_onset / trim_cut, and
    hook_pool.ratings. These are written by package.build: the second pass at :2617, G17a, then
    `openers = {... if can_open(m)}` at :2643, hook_pool at :2666 (pipeline/package.py, UNCHANGED).
  - the spotlight: pool.out, and moments[*].stage / out / hook_own (spotlight.build :813, UNCHANGED). A stage-0 stop
    is a free screen unless it is step A's (ruling 109's ALONE gate stops at stage 0 BEFORE step A, :858). A
    widened span (pool.snapped) counts as the moment it came from.
- funnel: per build, and DISTINCT moments (a ~trim / ~tail variant is its moment) at their furthest stage over every
  build and both paths. A tie keeps the LATEST build's reason. Classes of the reasons for the never-rated.
- all_ratings + near_misses: every hook rating in the window (the medley's hook_pool.ratings; the spotlight's
  hook_own, completed from HOOK_CACHE.json by moment id), on TODAY's rule. That rule is own_rating, the lower of
  scroll and alone (ruling 61; package.hook_own :1383): an early record that stored a three-part rating is read on
  today's rule. One entry per moment, ranked by rating and then the sum of the parts. "Held back": among those
  rated 3, which part is at 3 (setup is shown apart; it is not in the rating since ruling 61).
- ledger_of / ledger_id: a build gives each re-anchored moment its OWN id (0 of 57 equal their ledger id in
  ledger_20261115_151621); mined.ledger_moment_id maps back, and snapped spans and variants resolve through it.
- hook_pass: pp-ingest's queue database opened with mode=ro (sqlite URI), its 'hooks' events (classed: rows or not,
  a model called or not), the given videos' events, their hook rows in pp-ingest's ledger (read), and how far each
  got in our builds (never_in_pool: the latest build's own inputs report: word-pass refusal, no re-anchor, or a
  duplicate).

THE PAID PART, (2) calibrate:
- package.hook_ratings (:863, UNCHANGED) with cache=None. _load_cache(None) is {} (:497; open(None) raises TypeError,
  caught) and _cache_put(None, ...) returns at once (:508), so the production HOOK_CACHE.json is neither read nor
  written.
- The approved hooks get ids "ref-<key>", so no cached rating can answer for them.
- Asked as production asks: avoiding package._writers(router)'s vendor and family, once per seed (7 is production's;
  8 and 9 show stability).
- The router (build_router) is providers.Router under heimdall_first, built DIRECTLY: not proof_ledger.build_router,
  so no ruling-86 shadow (Grok). Its own spend ledger is tests/package/proof/SPEND_H112.json, limit $0.30 (the
  order's cap); no call starts at or over STOP_USD $0.25.
- Its hook list (ruling 88, "coherence_verdict:hook", providers.Router.chain :794) is production's with every
  non-Heimdall back-end removed: heimdall_hook_chain keeps a back-end whose vendor is "heimdall/<family>" (that is
  how providers.HeimdallBackend names it), and refuses when none is left. Today's list is qwen, glm, deepseek;
  Grok is dropped.

TESTS: tests/package/test_hook112.py (12), offline. Both traces stage by stage. The roll-up's furthest stage, the
latest reason on a tie, and folded variants. The near misses on today's rule, folded, with the held-back counts. The
hook pass over a database and ledger of the same shape. The ledger-id resolution. A REAL Router built by
build_router: its hook chain is Heimdall only, qwen first, no Grok. The calibration's guards: no cache, production's
writers, every seed, no call at the stop, refusal without a Heimdall back-end, and the reference ids absent from
the production cache. 15 of 15 mutations killed after a control run (the unmutated copy passes all 12). Suites: 697
pass.

PLEASE CHECK: (1) that both traces place every moment where package.build and spotlight.build actually stopped it (the
cited lines); (2) the roll-up, the tie rule, and the ledger-id mapping; (3) the near misses' rule and the held-back
count; (4) that the calibration can reach no non-Heimdall back-end, no shadow, and no production cache or spend
ledger, and stops under the cap; (5) that the hook pass and every other read cannot write to pp-ingest's or the
main tree's files; (6) the tests.


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


Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
