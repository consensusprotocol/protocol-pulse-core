# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261114_2155g
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 452 s finish=stop usage in 11814 / out 11173 usd_reported=0.001752 usd~0.203 (upper-bound price)

# Audit: pp-selectid — RULING 107 (1) "nothing new costs $0.00" guard

Scope: `tests/package/proof_ledger.py` (diff) + `tests/package/test_ruling_107_guard.py` (new, 213 lines). Reviewed against the four questions, the governing laws (M12 fail-closed, LAW 20, smallest diff), and the stated intent.

---

## Findings

### [P1] F1 — `nothing_new` returns after the *first* readable FINGERPRINT.json, so a newer finished build that wrote none masks the matching older one — but the docstring/decision semantics disagree with the test
`nothing_new` iterates newest→oldest and `return`s on the **first** directory that has a *readable* FINGERPRINT.json (the `continue` only fires on unreadable/missing). The test `test_only_the_newest_finished_build_counts` pins exactly this: `ledger_..._210000` (no FINGERPRINT) is passed over and `..._200000` (fingerprint "F") still decides. That's coherent — but consider the sequence: build A (fp=F, open_work=0) → build B (fp=G, finished, open_work=0) → build C (fp=F). C correctly does not match B. Now the *intended* semantics "the newest earlier FINISHED build decides" is what's implemented; fine. However, the skip path (`NOTHING_NEW` early return) writes **no** FINGERPRINT.json, so a long run of consecutive nothing-new builds keeps matching the same ancient build A. If A's *outputs* (registry, spotlights, scorer verdicts) were changed by any intervening process without changing the fingerprint inputs, C still skips. This is by design (fingerprint covers those), but note: the skip build's `delivered`/`pins` are hashed, yet the skip build itself delivers nothing — so the chain is stable. **Verdict: correct, but fragile-by-argument, not by construction.** Downgraded to P2-adjacent; the real defect is F2.

### [P1] F2 — Time-varying `now` inside the fingerprint: `due` uses `now`, and the end-of-build FINGERPRINT is written with the *start* `now`, so the next build's `now` always differs → the guard can never match unless the 6h candidate window aligns
`fingerprint` includes `"due": sorted([k, fresh] for k, _, fresh in CA.due(reg, now))`. `CA.due` presumably returns candidates whose 6h rest has expired *as of `now`*. Two consequences:
1. **Q3 answer:** `day_et` is ET-day-quantized (test pins 3h-later equality), good. But `due` is minute-resolution via `now`. A resting candidate with `until = T` flips to due at exactly `T`; any build after `T` (until the candidate is consumed) fingerprints differently than any build before `T`. That's *intended* (a due candidate is something new to judge — Q1 correctly catches it). Not a bug.
2. The real issue: the end-of-build FINGERPRINT (line 132-137) recomputes `fingerprint(pool, delivered, pins, since, now, reg)` with the **same** `now` as the start, but `reg` is the registry **as mutated by this build** (CA.seed applied at line ~621, *before* the end fingerprint). So the end fingerprint's `candidates`/`due` parts reflect post-build state, while the next build's start fingerprint also reads post-previous-build state. Consistent. But `now` at end == `now` at start of the *same* build, while the *next* build's `now` is later — `due` will differ whenever a candidate's `until` falls between the two builds' `now` values. The test `test_a_resting_candidate_coming_due_moves_it` pins this as *desired* (a due candidate = new work). So: not a defect, it's the design. **However** — `since.isoformat()` is hashed; `since` comes from `delivered_pins(PIN_PATHS)` which reads fixed files, so it's stable. OK.

Downgrade: this is really a P3 note. Let me re-examine for a true P1.

### [P1] F3 — `open_work` counts `"verdict": "error"` by string-searching a JSON dump: `json.dumps(res, default=str).count('"verdict": "error"')`
Three concrete failure modes:
1. **`default=str` + `indent`-less dump**: keys/values are serialized with `json.dumps`'s default separators, so `"verdict": "error"` (colon+space) matches only if the *value* is exactly the string `"error"`. If any verdict is stored as `"ERROR"`, `"Error"`, or an enum-`str` subclass that dumps differently, it's missed. Fragile but pinned by tests? The tests only exercise the exact lowercase form.
2. **False positives**: any *other* field whose *value* happens to be the string `"error"`... no — the pattern includes the key. But a nested record like `{"verdict": "error", ...}` inside a *text* field (e.g., a moment's `text` containing the literal substring `"verdict": "error"`) would be counted. Contrived; P3.
3. **The real one**: `open_work(res, sp)` is called at end-of-build with `(res, sp)`. In `main`, `res` is the package result and `sp` is... the diff shows `left = open_work(res, sp)` where `sp`'s provenance in the diff context is not shown (line 134: `left = open_work(res, sp)`). If `sp` is the *render lock* record, fine. But note the asymmetry: `open_work`'s first branch reads `pre.g

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 92 s finish=stop usage in 13198 / out 3302 usd_reported=0.004237 usd~0.089 (upper-bound price)

I have reviewed the diff for `tests/package/proof_ledger.py` and the new test file `tests/package/test_ruling_107_guard.py` against the RULING 107 (1) requirements and the provided "Governing Laws".

### Analysis

**1. Logic of `fingerprint` and `nothing_new`**
The core logic implements a "skip if unchanged" mechanism.
- `fingerprint()` hashes: moments, delivered/pins/since, ET day, code content, registry state (including due candidates), spotlights, directives, pre-check results, and scorer verdicts.
- `nothing_new()` scans previous ledger directories in reverse chronological order. It returns the name of the *first* (newest) previous build that has a `FINGERPRINT.json` matching the current fingerprint AND has `open_work == 0`.
- If `nothing_new` returns a name, `main()` writes `NOTHING_NEW.json` and exits with 0, skipping the router/model call.

**2. Potential Issues**

*   **[P1] `nothing_new` logic flaw: "Newest" vs "Any Matching"**
    The docstring for `nothing_new` says: *"the NEWEST earlier FINISHED build ... when its fingerprint is this build's and it left nothing undone"*.
    However, the implementation iterates through *all* previous builds (newest to oldest) and returns the *first* one that matches.
    
    Consider this scenario:
    1.  Build A (10:00) runs. Fingerprint `F1`. `open_work=0`. Writes `FINGERPRINT.json`.
    2.  Build B (11:00) runs. Inputs change slightly (e.g., a new moment arrives). Fingerprint `F2`. `open_work=0`. Writes `FINGERPRINT.json`.
    3.  Build C (12:00) runs. Inputs revert to state `F1` (e.g., the new moment was removed or the state is identical to 10:00 for some reason, or more likely, the "newest" logic is intended to prevent re-judging if the *current* state matches a *recent* successful run).
    
    Actually, the standard "idempotency" check usually compares against the *immediately preceding* state or the *last successful* state. The current implementation compares against *any* previous build.
    
    Let's look closer at the requirement: *"a build that judges nothing new must cost $0.00"*.
    If Build B (11:00) had `F2` and `open_work=0`, and Build C (12:00) has `F1` (same as A), `nothing_new` will find A (10:00) because B (11:00) doesn't match `F1`. It will skip C.
    Is this correct? If the state is identical to a previous successful build, re-judging is indeed redundant. The "Newest" in the docstring is slightly misleading if it skips intermediate non-matching builds, but the *behavior* (skip if state matches *any* previous clean build) is a valid optimization for idempotency.
    
    **However**, there is a subtle bug in the iteration logic of `nothing_new`:
    ```python
    for d in sorted(glob.glob(...), reverse=True):
        # ...
        if isinstance(prev, dict) and prev.get("fingerprint") == fp and prev.get("open_work") == 0:
            return os.path.basename(d)
        return None  # <--- THIS IS THE BUG
    return None
    ```
    The `return None` is inside the `for` loop, immediately after the `if` block. This means it only checks the **single newest** previous build. If the newest build doesn't match, it returns `None` immediately, ignoring older builds.
    
    Let's re-read the code carefully:
    ```python
    96 |     for d in sorted(glob.glob(os.path.join(proof_dir, "ledger_*")), reverse=True):
    97 |         if os.path.abspath(d) == os.path.abspath(out_dir):
    98 |             continue
    99 |         try:
   100 |             with open(os.path.join(d, FINGERPRINT)) as f:
   101 |                 prev = json.load(f)
   102 |         except (OSError, ValueError):
   103 |             continue
   104 |         if isinstance(prev, dict) and prev.get("fingerprint") == fp and prev.get("open_work") == 0:
   105 |             return os.path.basename(d)
   106 |         return None
   107 |     return None
    ```
    Yes, line 106 `return None` is inside the loop. This means `nothing_new` **only checks the single most recent previous build**.
    
    **Scenario for Failure:**
    1.  Build 1 (10:00): Fingerprint `F1`, `open_work=0`.
    2.  Build 2 (11:00): Fingerprint `F2` (changed), `open_work=0`.
    3.  Build 3 (12:00): Fingerprint `F1` (reverted to state of Build 1).
    
    `nothing_new` for Build 3 checks Build 2 (newest). Build 2 has `F2`. `F2 != F1`. The loop hits `return None`. Build 3 proceeds to run the model.
    
    Is this a violation? The ruling says "a build that judges nothing new". If the state is identical to Build 1, it is "nothing new" relative to the history. However, usually, these guards are "Last Run" guards. If the intent is "Skip if identical to the *last* run", then the code is correct. If the intent is "Skip if identical to *any* previous run", the code is buggy.
    
    Given the context of "Pre-merge quality gate" and "RULING 107 (1) ... a build that judges nothing 

## CLAUDE'S CYCLE 1 CONSENSUS
# Cycle 1 consensus: pp-selectid audit 20261114_2155g (ruling 107 (1): the guard that makes a no-news build $0.00)

Reviewers under ruling 107 (2): qwen3.8-27b and glm-5.3-flash. Both raised P0/P1s, so they agree and Grok was not
asked. Cost: $0.0060 vendor-reported.

IMPLEMENTED:
- qwen P1 (open_work by string search is fragile). It now walks the structure: _errors() counts every object anywhere
  whose "verdict" is "error". Tests: a nested error counts; a log string quoting the phrase does not.
- glm F4 (--routing decides which models judge, but was not in the fingerprint). fingerprint(..., routing=a.routing).
  Test: "today" and "heimdall_first" fingerprint differently. The config's routing mode is already in code_content
  (pipeline/model_providers.json).

REFUTED, with evidence:
- glm F11 ("the next build's pool depends on this build's outputs, so the guard never fires"). The pool comes from
  ledger_build.build_inputs over pp-ingest's ledger rows and the word records. This build's outputs (the pre-check
  answers, the scorer verdicts, the registry) never feed it. Measured: the same 157 moments were byte-identical in
  every field between builds ledger_20261114_183413 and _192056. The integrator's outputs are fingerprinted separately,
  as they stand at the END of the build that read them.
- glm F2 ("now makes the fingerprint time-varying"). Only CA.due(reg, now) reads now: the list of DUE candidates, not
  a time. It changes only when a candidate comes due, which is new work. The ET day changes at midnight, which is also
  new (the show date). Tests: three hours later the fingerprint is equal; a candidate coming due moves it.
- glm F1 / qwen (the newest decides). By design and as documented: the newest FINISHED build decides. A stopped or
  skipped build writes no FINGERPRINT.json and is passed over. Tested.
- glm F5 (a moment without video_id): every moment record has video_id (eligibility.Span / moments.record).
- glm F7: the test's registry has no resting candidate, by intent. The resting case has its own test.
- glm F3: superseded by the structural walk above.
- glm F6: the skip writes inputs.json and NOTHING_NEW.json and no package.json, by intent: no build ran.

Mutations: 9 of 9 killed (work left undone ignored; pool, code, day, due candidates or pre-check answers left out; the
driver never stopping; an older match counting; held work not counted).


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_20261114_2155g/C2_STEP.diff (375 lines)
```
   1 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
   2 | index 8e556dd..befaff1 100644
   3 | --- a/tests/package/proof_ledger.py
   4 | +++ b/tests/package/proof_ledger.py
   5 | @@ -20,6 +20,12 @@
   6 |  Writes tests/package/proof/ledger_<UTC stamp, to the second>/ (a run never writes into an existing one): inputs.json,
   7 |  package.json, package.log, step_a.json and, on a package, MOMENTS_PIN_LEDGER.json.
   8 |  
   9 | +RULING 107 (1) (orchestrator 20:20 ET Nov 14), "a build that judges nothing new must cost $0.00": a full build ends by
  10 | +writing FINGERPRINT.json (fingerprint(): its pool, deliveries, ET day, code by content, candidates and the integrator's
  11 | +outputs it read, as they stand at its end, with open_work(): what it left undone). The next build fingerprints its own
  12 | +inputs before any model is asked. When they equal the newest finished build's and that build left nothing undone, it
  13 | +writes NOTHING_NEW.json and stops: no router, no call, $0.00.
  14 | +
  15 |  RULING 66 (13:18; its standing part ruled 14:02), A PASSED LINE-UP IS KEPT: every build first tries the due
  16 |  candidates of the registry (tests/package/proof/CANDIDATES.json, seeded from the build records; pipeline/candidates.py),
  17 |  newest first, inside the 8 judged line-ups (a recorded verdict is free), each as package.build(candidate=...); only when
  18 | @@ -42,6 +48,7 @@ Usage: python3 tests/package/proof_ledger.py --delivered PIN [PIN ...] [--since
  19 |  """
  20 |  import argparse
  21 |  import glob
  22 | +import hashlib
  23 |  import json
  24 |  import os
  25 |  import sys
  26 | @@ -76,6 +83,94 @@ REGISTRY = os.path.join(HERE, "proof", "CANDIDATES.json")     # ruling 66: the c
  27 |  SPOTLIGHTS = os.path.join(HERE, "proof", "SPOTLIGHTS.json")   # ruling 90: one spotlight per channel per ET day
  28 |  DIRECTIVES = os.path.join(HERE, "proof", "RULING_104_DIRECTIVES.json")   # ruling 104: the orchestrator's directives
  29 |  STATE_MD = os.path.join(REPO, "docs", "audits", "parallel", "pp-selectid_STATE.md")   # ruling 87: a switch on line 1
  30 | +FINGERPRINT = "FINGERPRINT.json"     # RULING 107 (1): a finished build's inputs, written at its end for the next build
  31 | +NOTHING_NEW = "NOTHING_NEW.json"     # RULING 107 (1): a build that found nothing new and asked no model
  32 | +
  33 | +
  34 | +def _sha(x):
  35 | +    return hashlib.sha256(json.dumps(x, sort_keys=True, default=str).encode()).hexdigest()
  36 | +
  37 | +
  38 | +def _file_sha(path):
  39 | +    try:
  40 | +        with open(path, "rb") as f:
  41 | +            return hashlib.sha256(f.read()).hexdigest()
  42 | +    except OSError:
  43 | +        return None
  44 | +
  45 | +
  46 | +def code_content(repo=REPO, here=HERE):
  47 | +    """The build's code BY CONTENT: every pipeline/*.py and pipeline/*.json, and every driver module of tests/package
  48 | +    (not its tests). A STATE or data commit moves HEAD but changes no judgment, so HEAD is not in it."""
  49 | +    files = sorted(glob.glob(os.path.join(repo, "pipeline", "*.py")) + glob.glob(os.path.join(repo, "pipeline", "*.json"))
  50 | +                   + [f for f in glob.glob(os.path.join(here, "*.py")) if not os.path.basename(f).startswith("test_")])
  51 | +    h = hashlib.sha256()
  52 | +    for f in files:
  53 | +        with open(f, "rb") as fh:
  54 | +            h.update(os.path.relpath(f, repo).encode() + b"\0" + fh.read() + b"\0")
  55 | +    return h.hexdigest()
  56 | +
  57 | +
  58 | +def fingerprint(moments, delivered, pins, since, now, reg, routing=None):
  59 | +    """RULING 107 (1) (orchestrator 20:20 ET Nov 14): "a build that judges nothing new must cost $0.00". Everything a
  60 | +    build's judgments and outcome depend on: the pool's moment records (each with its words, span and sources), what
  61 | +    was delivered and since when, the ET day (the show date every step-A prompt carries), the code and its config BY
  62 | +    CONTENT, the candidate registry and which of its candidates are due now (ruling 66: a resting one comes due after
  63 | +    6 h), the ruling-90 spotlights record, the ruling-104 directives, and the outputs of the integrator's services this
  64 | +    build reads: the pre-check results for the pool's videos and the clip scorer's verdicts. -> (sha256, its parts)."""
  65 | +    vids = {m.get("video_id") for m in moments}
  66 | +    try:
  67 | +        res = sorted((n, os.path.getsize(os.path.join(LP.RESULTS, n)), os.path.getmtime(os.path.join(LP.RESULTS, n)))
  68 | +                     for n in os.listdir(LP.RESULTS) if n.split(".", 1)[0] in vids)
  69 | +    except OSError:
  70 | +        res = None
  71 | +    parts = {"moments": _sha(moments), "delivered": _sha([delivered, [p.get("story_id") for p in pins], since.isoformat()]),
  72 | +             "day_et": SPOT.et_day(now), "code": code_content(), "candidates": _sha(reg.get("candidates")),
  73 | +             "due": sorted([k, fresh] for k, _, fresh in CA.due(reg, now)),
  74 | +             "spotlights": _file_sha(SPOTLIGHTS), "directives": _file_sha(DIRECTIVES),
  75 | +             "precheck_results": _sha(res), "scorer_verdicts": _file_sha(PK.SCORER_VERDICTS),
  76 | +             "routing": routing}                 # --routing decides which models judge (audit 2155g C1, glm F4)
  77 | +    return _sha(parts), parts
  78 | +
  79 | +
  80 | +def _errors(x):
  81 | +    """The number of objects anywhere inside x whose "verdict" is "error" (a segment the render's lock gave no verdict on
  82 | +    in time, wherever the record nests it)."""
  83 | +    if isinstance(x, dict):
  84 | +        return int(x.get("verdict") == "error") + sum(_errors(v) for v in x.values())
  85 | +    if isinstance(x, (list, tuple)):
  86 | +        return sum(_errors(v) for v in x)
  87 | +    return 0
  88 | +
  89 | +
  90 | +def open_work(res, sp):
  91 | +    """RULING 107 (1): what a finished build left undone, which the next build must try again whatever its inputs:
  92 | +    the moments ruling 102 held (no leg answered), any segment the render's lock gave no verdict on in time, and any
  93 | +    visual check left unmeasured. -> int (0: nothing left)."""
  94 | +    pre, sp = (res or {}).get("prescreen") or {}, sp or {}
  95 | +    h = pre.get("held_102") or {}
  96 | +    held = len(h.get("first") or []) + len(h.get("second") or []) + len(sp.get("held_102") or [])
  97 | +    no_verdict = _errors(res) + _errors(sp)        # by structure, never a string search (audit 2155g C1, qwen)
  98 | +    vis = (res or {}).get("visual") or {}
  99 | +    return held + no_verdict + int(vis.get("unmeasured") or 0)
 100 | +
 101 | +
 102 | +def nothing_new(proof_dir, out_dir, fp):
 103 | +    """RULING 107 (1): the newest earlier FINISHED build (its FINGERPRINT.json) when its fingerprint is this build's and
 104 | +    it left nothing undone; else None. A build that stopped early writes none, and neither does a --from-candidate
 105 | +    one (it tries one line-up, not the pool), so neither can stand for a full build."""
 106 | +    for d in sorted(glob.glob(os.path.join(proof_dir, "ledger_*")), reverse=True):
 107 | +        if os.path.abspath(d) == os.path.abspath(out_dir):
 108 | +            continue
 109 | +        try:
 110 | +            with open(os.path.join(d, FINGERPRINT)) as f:
 111 | +                prev = json.load(f)
 112 | +        except (OSError, ValueError):
 113 | +            continue
 114 | +        if isinstance(prev, dict) and prev.get("fingerprint") == fp and prev.get("open_work") == 0:
 115 | +            return os.path.basename(d)
 116 | +        return None
 117 | +    return None
 118 |  
 119 |  
 120 |  def delivered_pins(paths):
 121 | @@ -316,6 +411,16 @@ def main(argv=None):
 122 |          json.dump({"since": since.isoformat(), "publish_window_h": a.hours, "delivered_pins": pins,
 123 |                     "adapter_report": rep, "inputs": inputs, "delivered": delivered, "moments": moments},
 124 |                    f, indent=1, default=str)
 125 | +    pool = json.loads(json.dumps(moments, default=str))   # RULING 107 (1): the pool as it came in, before any stage
 126 | +    fp, fp_parts = fingerprint(pool, delivered, pins, since, now, reg, a.routing)
 127 | +    same = None if cand is not None else nothing_new(os.path.join(HERE, "proof"), out_dir, fp)
 128 | +    if same:                                     # nothing new: no router, no model, $0.00 (ruling 107 (1))
 129 | +        with open(os.path.join(out_dir, NOTHING_NEW), "w") as f:
 130 | +            json.dump({"fingerprint": fp, "parts": fp_parts, "same_as": same, "at": now.isoformat()}, f, indent=1)
 131 | +        say(f"NOTHING NEW (ruling 107 (1)): this build's inputs are {same}'s (fingerprint {fp[:12]}), and that build "
 132 | +            f"left nothing undone: no model is asked, $0.00")
 133 | +        logf.close()
 134 | +        return 0
 135 |      rt = json.load(open(P.CONFIG)).get("routing") or {}
 136 |      routing = a.routing or rt.get("mode") or "today"
 137 |      shadow = None                                # RULING 86: Grok in shadow on the first heimdall_first pins
 138 | @@ -526,6 +631,12 @@ def main(argv=None):
 139 |              f"is written with registry false")           # applies this record's outcome (CA.seed)
 140 |      with open(os.path.join(out_dir, "package.json"), "w") as f:
 141 |          json.dump(res, f, indent=1, default=str)
 142 | +    if cand is None:                             # RULING 107 (1): the next build compares its inputs with these, as
 143 | +        fp_end, parts_end = fingerprint(pool, delivered, pins, since, now, reg, a.routing)   # at this build's END
 144 | +        left = open_work(res, sp)
 145 | +        with open(os.path.join(out_dir, FINGERPRINT), "w") as f:
 146 | +            json.dump({"fingerprint": fp_end, "parts": parts_end, "open_work": left, "build": name}, f, indent=1)
 147 | +        say(f"  RULING 107 (1): fingerprint {fp_end[:12]}, {left} item(s) left undone")
 148 |      logf.close()
 149 |      return 0
 150 |  
 151 | diff --git a/tests/package/test_ruling_107_guard.py b/tests/package/test_ruling_107_guard.py
 152 | new file mode 100644
 153 | index 0000000..ce0eade
 154 | --- /dev/null
 155 | +++ b/tests/package/test_ruling_107_guard.py
 156 | @@ -0,0 +1,218 @@
 157 | +#!/usr/bin/env python3
 158 | +"""RULING 107 (1) (orchestrator 20:20 ET Nov 14): "a build that judges nothing new must cost $0.00". The build driver
 159 | +fingerprints its inputs before any model is asked (proof_ledger.fingerprint), and stops with no router and no call
 160 | +when they equal the newest finished build's and that build left nothing undone (nothing_new, open_work). Offline:
 161 | +temporary proof directories; the driver test stubs the ledger reads and makes building a router an error."""
 162 | +import copy
 163 | +import io
 164 | +import json
 165 | +import os
 166 | +import sys
 167 | +import tempfile
 168 | +import unittest
 169 | +from datetime import datetime, timedelta, timezone
 170 | +from unittest import mock
 171 | +
 172 | +HERE = os.path.dirname(os.path.abspath(__file__))
 173 | +REPO = os.path.dirname(os.path.dirname(HERE))
 174 | +sys.path.insert(0, HERE)
 175 | +import proof_ledger as PLG  # noqa: E402
 176 | +
 177 | +NOW = datetime(2026, 11, 14, 22, 0, tzinfo=timezone.utc)                  # 17:00 ET
 178 | +POOL = [{"moment_id": "m1", "video_id": "vidZZZZZZZ1", "text": "Bitcoin is a bearer asset.", "start": 1.0, "end": 9.0},
 179 | +        {"moment_id": "m2", "video_id": "vidZZZZZZZ2", "text": "Self custody matters.", "start": 3.0, "end": 12.0}]
 180 | +PINS = [{"story_id": "s1"}]
 181 | +DELIVERED = [{"video_id": "old", "start": 0.0, "end": 5.0}]
 182 | +SINCE = datetime(2026, 11, 13, 3, 1, 9, tzinfo=timezone.utc)
 183 | +
 184 | +
 185 | +class Paths(unittest.TestCase):
 186 | +    """Every file the fingerprint reads, in a temporary directory."""
 187 | +
 188 | +    def setUp(self):
 189 | +        self.tmp = tempfile.TemporaryDirectory()
 190 | +        d = self.tmp.name
 191 | +        self.res, self.spot, self.dirs, self.scorer = (os.path.join(d, "results"), os.path.join(d, "SPOTLIGHTS.json"),
 192 | +                                                       os.path.join(d, "DIRECTIVES.json"), os.path.join(d, "latest.json"))
 193 | +        os.makedirs(self.res)
 194 | +        for p, body in ((self.spot, "[]"), (self.dirs, '{"directives": []}'), (self.scorer, '{"verdicts": {}}')):
 195 | +            open(p, "w").write(body)
 196 | +        self.patches = [mock.patch.object(PLG.LP, "RESULTS", self.res), mock.patch.object(PLG, "SPOTLIGHTS", self.spot),
 197 | +                        mock.patch.object(PLG, "DIRECTIVES", self.dirs),
 198 | +                        mock.patch.object(PLG.PK, "SCORER_VERDICTS", self.scorer)]
 199 | +        for p in self.patches:
 200 | +            p.start()
 201 | +
 202 | +    def tearDown(self):
 203 | +        for p in self.patches:
 204 | +            p.stop()
 205 | +        self.tmp.cleanup()
 206 | +
 207 | +    def fp(self, pool=POOL, delivered=DELIVERED, pins=PINS, since=SINCE, now=NOW, reg=None):
 208 | +        return PLG.fingerprint(pool, delivered, pins, since, now, reg or PLG.CA.new_registry())
 209 | +
 210 | +
 211 | +class TestFingerprint(Paths):
 212 | +    def test_the_same_inputs_give_the_same_fingerprint(self):
 213 | +        self.assertEqual(self.fp()[0], self.fp(pool=copy.deepcopy(POOL))[0])
 214 | +        later = NOW + timedelta(hours=3)                                     # still 14 Nov ET
 215 | +        self.assertEqual(self.fp()[0], self.fp(now=later)[0])
 216 | +
 217 | +    def test_every_input_moves_it(self):
 218 | +        base = self.fp()[0]
 219 | +        pool = copy.deepcopy(POOL)
 220 | +        pool[0]["text"] = "Bitcoin is a bearer instrument."
 221 | +        self.assertNotEqual(self.fp(pool=pool)[0], base, "a word of a moment")
 222 | +        self.assertNotEqual(self.fp(pool=POOL + [dict(POOL[0], moment_id="m3")])[0], base, "a new moment")
 223 | +        self.assertNotEqual(self.fp(delivered=DELIVERED + [{"video_id": "x", "start": 1, "end": 2}])[0], base,
 224 | +                            "a delivered span")
 225 | +        self.assertNotEqual(self.fp(pins=[{"story_id": "s2"}])[0], base, "a delivered pin")
 226 | +        self.assertNotEqual(self.fp(since=SINCE + timedelta(hours=1))[0], base, "since")
 227 | +        self.assertNotEqual(self.fp(now=NOW + timedelta(hours=8))[0], base, "the ET day (the show date)")   # 01:00 ET Nov 15
 228 | +        reg = PLG.CA.new_registry()
 229 | +        reg["candidates"]["a+b+c"] = {"lineup": ["a", "b", "c"], "source": "r", "index": 0, "state": "closed",
 230 | +                                      "found_at": "2026-11-14T10:00:00+00:00", "until": None, "fresh_used": False,
 231 | +                                      "history": []}
 232 | +        self.assertNotEqual(self.fp(reg=reg)[0], base, "the registry")
 233 | +        for path, body, what in ((self.spot, '[{"channel_id": "c"}]', "the spotlights record"),
 234 | +                                 (self.dirs, '{"directives": [{"parent": "x"}]}', "a directive"),
 235 | +                                 (self.scorer, '{"verdicts": {"t": 4}}', "the clip scorer's verdicts")):
 236 | +            was = open(path).read()
 237 | +            open(path, "w").write(body)
 238 | +            self.assertNotEqual(self.fp()[0], base, what)
 239 | +            open(path, "w").write(was)
 240 | +        self.assertEqual(self.fp()[0], base)
 241 | +        with mock.patch.object(PLG, "code_content", lambda *a, **k: "other code"):
 242 | +            self.assertNotEqual(self.fp()[0], base, "the code")
 243 | +        self.assertNotEqual(PLG.fingerprint(POOL, DELIVERED, PINS, SINCE, NOW, PLG.CA.new_registry(), "today")[0],
 244 | +                            PLG.fingerprint(POOL, DELIVERED, PINS, SINCE, NOW, PLG.CA.new_registry(), "heimdall_first")[0],
 245 | +                            "the routing")
 246 | +
 247 | +    def test_a_precheck_result_moves_it_only_for_a_video_of_the_pool(self):
 248 | +        base = self.fp()[0]
 249 | +        open(os.path.join(self.res, "otherVideo1.0.000-9.000.a4c307f78c94.json"), "w").write("[]")
 250 | +        self.assertEqual(self.fp()[0], base)                                 # another video's answer: not this pool
 251 | +        open(os.path.join(self.res, "vidZZZZZZZ1.1.000-9.000.a4c307f78c94.json"), "w").write("[]")
 252 | +        self.assertNotEqual(self.fp()[0], base)                              # an answer for the pool
 253 | +
 254 | +    def test_a_resting_candidate_coming_due_moves_it(self):
 255 | +        reg = PLG.CA.new_registry()
 256 | +        reg["candidates"]["a+b+c"] = {"lineup": ["a", "b", "c"], "source": "r", "index": 0, "state": "resting",
 257 | +                                      "found_at": "2026-11-14T10:00:00+00:00", "until": "2026-11-14T23:00:00+00:00",
 258 | +                                      "fresh_used": False, "history": []}
 259 | +        before, after = self.fp(reg=reg)[0], self.fp(reg=reg, now=NOW + timedelta(hours=1, minutes=30))[0]
 260 | +        self.assertNotEqual(before, after)                                   # 18:30 ET: its 6 h are over
 261 | +
 262 | +    def test_the_code_is_read_by_content_not_by_commit(self):
 263 | +        self.assertEqual(PLG.code_content(), PLG.code_content())
 264 | +        with tempfile.TemporaryDirectory() as d:
 265 | +            os.makedirs(os.path.join(d, "pipeline"))
 266 | +            os.makedirs(os.path.join(d, "drv"))
 267 | +            open(os.path.join(d, "pipeline", "a.py"), "w").write("x = 1\n")
 268 | +            open(os.path.join(d, "drv", "proof_x.py"), "w").write("y = 1\n")
 269 | +            open(os.path.join(d, "drv", "test_x.py"), "w").write("z = 1\n")
 270 | +            one = PLG.code_content(d, os.path.join(d, "drv"))
 271 | +            open(os.path.join(d, "drv", "test_x.py"), "w").write("z = 2\n")
 272 | +            self.assertEqual(PLG.code_content(d, os.path.join(d, "drv")), one)      # a test is not the build's code
 273 | +            open(os.path.join(d, "pipeline", "a.py"), "w").write("x = 2\n")
 274 | +            self.assertNotEqual(PLG.code_content(d, os.path.join(d, "drv")), one)
 275 | +
 276 | +
 277 | +class TestOpenWorkAndNothingNew(unittest.TestCase):
 278 | +    def test_open_work_counts_what_a_build_left_undone(self):
 279 | +        self.assertEqual(PLG.open_work({"prescreen": {}, "visual": {}}, {}), 0)
 280 | +        self.assertEqual(PLG.open_work({"prescreen": {"held_102": {"first": ["a"], "second": ["b", "c"]}}},
 281 | +                                       {"held_102": ["d"]}), 4)
 282 | +        self.assertEqual(PLG.open_work({"tried": [{"precheck": {"segments": [{"verdict": "error"}]}}]}, {}), 1)
 283 | +        self.assertEqual(PLG.open_work({}, {"lock_stop": {"segments": [{"verdict": "error"}]}}), 1)
 284 | +        self.assertEqual(PLG.open_work({"visual": {"unmeasured": 2}}, {}), 2)
 285 | +        self.assertEqual(PLG.open_work({"a": [{"b": {"verdict": "error"}}, {"verdict": "pass"}]}, {}), 1)   # nested
 286 | +        self.assertEqual(PLG.open_work({"why": 'a log line quoting "verdict": "error"'}, {}), 0)   # a string is no verdict
 287 | +
 288 | +    def test_only_the_newest_finished_build_counts(self):
 289 | +        with tempfile.TemporaryDirectory() as d:
 290 | +            def build(name, fp=None, left=0):
 291 | +                os.makedirs(os.path.join(d, name))
 292 | +                if fp is not None:
 293 | +                    json.dump({"fingerprint": fp, "open_work": left, "build": name},
 294 | +                              open(os.path.join(d, name, PLG.FINGERPRINT), "w"))
 295 | +            me = os.path.join(d, "ledger_20261114_230000")
 296 | +            self.assertIsNone(PLG.nothing_new(d, me, "F"))                  # no earlier build
 297 | +            build("ledger_20261114_200000", "F")
 298 | +            self.assertEqual(PLG.nothing_new(d, me, "F"), "ledger_20261114_200000")
 299 | +            build("ledger_20261114_210000")                                  # no FINGERPRINT (stopped, skipped, or a
 300 | +            self.assertEqual(PLG.nothing_new(d, me, "F"), "ledger_20261114_200000")   # candidate's): passed over
 301 | +            build("ledger_20261114_220000", "G")                             # the newest finished build differs
 302 | +            self.assertIsNone(PLG.nothing_new(d, me, "F"))
 303 | +            build("ledger_20261114_221000", "F", left=1)                     # the same, but it left work undone
 304 | +            self.assertIsNone(PLG.nothing_new(d, me, "F"))
 305 | +            os.makedirs(me)
 306 | +            json.dump({"fingerprint": "F", "open_work": 0}, open(os.path.join(me, PLG.FINGERPRINT), "w"))
 307 | +            self.assertIsNone(PLG.nothing_new(d, me, "F"))                   # never this build itself
 308 | +            build("ledger_20261114_222000", "F")
 309 | +            open(os.path.join(d, "ledger_20261114_222500", PLG.FINGERPRINT) if os.makedirs(
 310 | +                os.path.join(d, "ledger_20261114_222500")) is None else "", "w").write("{not json")
 311 | +            self.assertEqual(PLG.nothing_new(d, me, "F"), "ledger_20261114_222000")   # an unreadable one is passed
 312 | +
 313 | +
 314 | +class TestTheDriverAsksNoModel(Paths):
 315 | +    """The driver itself: with the newest finished build's fingerprint equal to this one's and nothing left undone, it
 316 | +    stops before any router exists (building one is an error here); with work left undone, it goes on to the router."""
 317 | +    PIN_PATHS = [os.path.join(HERE, "proof", "fresh_20261112_050611", n) for n in ("MOMENTS_PIN.json",
 318 | +                                                                                  "MOMENTS_PIN_LY.json")]
 319 | +
 320 | +    def run_driver(self, left):
 321 | +        proof = os.path.join(self.tmp.name, "drv", "proof")
 322 | +        os.makedirs(proof)
 323 | +        delivered, last, pins = PLG.delivered_pins(self.PIN_PATHS)
 324 | +        fp, _ = PLG.fingerprint(copy.deepcopy(POOL), delivered, pins, last, datetime.now(timezone.utc),
 325 | +                                PLG.CA.new_registry())
 326 | +        prev = os.path.join(proof, "ledger_20000101_000000")
 327 | +        os.makedirs(prev)
 328 | +        json.dump({"fingerprint": fp, "open_work": left, "build": "ledger_20000101_000000"},
 329 | +                  open(os.path.join(prev, PLG.FINGERPRINT), "w"))
 330 | +
 331 | +        class Built(Exception):
 332 | +            pass
 333 | +
 334 | +        def no_router(*a, **k):
 335 | +            raise Built("a router was built")
 336 | +        stubs = [mock.patch.object(PLG, "HERE", os.path.join(self.tmp.name, "drv")),
 337 | +                 mock.patch.object(PLG, "REGISTRY", os.path.join(proof, "CANDIDATES.json")),
 338 | +                 mock.patch.object(PLG.PS, "ledger_entries", lambda *a, **k: []),
 339 | +                 mock.patch.object(PLG.LB, "rows", lambda *a, **k: ([], {"excluded": {}})),
 340 | +                 mock.patch.object(PLG.LB, "word_pass_index", lambda *a, **k: ({}, {"rows": 0})),
 341 | +                 mock.patch.object(PLG.LB, "build_inputs", lambda *a, **k: (copy.deepcopy(POOL), {}, {})),
 342 | +                 mock.patch.object(PLG, "with_variants", lambda moments, *a, **k: moments),
 343 | +                 mock.patch.object(PLG, "build_router", no_router),
 344 | +                 mock.patch("sys.stdout", new=io.StringIO())]
 345 | +        for s in stubs:
 346 | +            s.start()
 347 | +        try:
 348 | +            try:
 349 | +                rc = PLG.main(["--delivered", *self.PIN_PATHS])
 350 | +            except Built:
 351 | +                rc = "router"
 352 | +        finally:
 353 | +            for s in stubs:
 354 | +                s.stop()
 355 | +        runs = sorted(n for n in os.listdir(proof) if n.startswith("ledger_") and n != "ledger_20000101_000000")
 356 | +        return rc, [os.path.join(proof, n) for n in runs]
 357 | +
 358 | +    def test_nothing_new_stops_before_any_router_and_costs_nothing(self):
 359 | +        rc, runs = self.run_driver(left=0)
 360 | +        self.assertEqual(rc, 0)
 361 | +        self.assertEqual(len(runs), 1)
 362 | +        rec = json.load(open(os.path.join(runs[0], PLG.NOTHING_NEW)))
 363 | +        self.assertEqual(rec["same_as"], "ledger_20000101_000000")
 364 | +        self.assertIn("NOTHING NEW (ruling 107 (1))", open(os.path.join(runs[0], "package.log")).read())
 365 | +        self.assertFalse(os.path.exists(os.path.join(runs[0], PLG.FINGERPRINT)))   # a skip never stands for a build
 366 | +
 367 | +    def test_work_left_undone_goes_on_to_the_router(self):
 368 | +        rc, runs = self.run_driver(left=1)
 369 | +        self.assertEqual(rc, "router")
 370 | +        self.assertFalse(os.path.exists(os.path.join(runs[0], PLG.NOTHING_NEW)))
 371 | +
 372 | +
 373 | +if __name__ == "__main__":
 374 | +    unittest.main()
 375 | 
```

---

pp-selectid, RULING 107 (1) (orchestrator 20:20 ET Nov 14): "a build that judges nothing new must cost $0.00 ... the
test proves it before the second build of the batch" (ruling 108, 21:20).

THE CHANGE (tests/package/proof_ledger.py, the build driver; tests/package/test_ruling_107_guard.py is new):
- fingerprint(moments, delivered, pins, since, now, reg) hashes what a build's judgments and outcome depend on:
  the pool's moment records; the delivered spans, pins and 'since'; the ET day (the show date every step-A prompt
  carries); the code BY CONTENT (every pipeline/*.py and *.json and the tests/package driver modules, not tests:
  code_content()); the candidate registry and which of its candidates are due now; the ruling-90 spotlights record;
  the ruling-104 directives; the integrator's pre-check result files for the pool's videos; the clip scorer's verdict
  file.
- open_work(res, sp) counts what a finished build left undone: ruling 102's held moments, any "verdict": "error"
  (no lock verdict in time), and unmeasured visual checks.
- nothing_new(proof_dir, out_dir, fp): the NEWEST earlier build with a FINGERPRINT.json decides. It matches only
  when its fingerprint equals this one's and it left nothing undone. A skipped build, a stopped build and a
  --from-candidate build write none.
- main(): after inputs.json, the pool is fingerprinted BEFORE any router exists. Nothing new: NOTHING_NEW.json is
  written and the build returns 0 with no router and no call ($0.00). A full build ends by writing FINGERPRINT.json
  with the inputs as they stand at its END (the registry, spotlights and the integrator's outputs it changed) and
  its open work.
UNCHANGED GUARDS: main() writes inputs.json before the guard; build_router is the only way a model is reached; the
registry is saved before package.json.
PLEASE CHECK: (1) Can the guard skip a build that has something new to judge (a new moment, a moment come due, an
answer that arrived, a code change, a new day, held work)? (2) Can it ever let a model call happen before it
decides? (3) Is anything time-varying in the fingerprint that would keep it from ever matching? (4) Do the tests pin
it, including the driver-level test that building a router is an error when nothing is new?


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
