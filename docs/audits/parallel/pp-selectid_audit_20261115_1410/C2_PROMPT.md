# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261115_1410
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 38 s finish=stop usage in 41609 / out 1491 usd_reported=0.064637 usd~0.245 (upper-bound price)

**CODE AUDIT: pp-selectid-20261115_1410 (RULING 115 (1)+(2) — Calibrated Hook Bar)**

The diff implements the verbatim order: hook job asked **ALONE** (one call per candidate) at production seed 7 by Grok only (`coherence_verdict:hook` list reduced to that single backend in every routing), with floors derived from the five PBX-approved hooks in `ALONE_TEST.json` (scroll=3, alone=4, setup=3 after applying the "never below 3" rule). The sealed `hook_calibration.json` (sha256 over canonical body, measured_at, rater, question_version, asking="alone") is the single source of truth. `hook_bar.bar()` / `passes()` / `text()` enforce validity, rater match, 24 h freshness, and "every part >= its floor by the calibrated rater". `hook_own()` now returns `passes` (used by `_can_open`, `medley`, `coherence`, `last_clip_only`, spotlight opener stage and its gate row). The hook slot in coherence/medley/ruling-62 verdicts uses the bar (not `COHERENCE_MIN=4`); clips after the hook keep the original `>=4` rule. qwen shadows every hook (role:kind lookup, own shadow chain) but never decides. The mark (`hook_bar_mark()`) is placed **outside** the package seal and pin seal, carried to Telegram note.

All governing laws were checked:

- **SENTENCE LAW / SNAP LIMIT / NEIGHBOUR / ONSET/TAIL / L-b / L-c / L-e / L-g / L-h / L-k / L-l**: untouched (no transcript, punctuation, cut-point, edge-word, or ASR changes).
- **SELECTION LOCK / L-d PROTECTED PREVIEW / LAW 22 (v2f byte-identical re-render)**: the calibration floors were deliberately taken from the protected preview + approved moments; `can_open` / `hook_order` / `lineup_for` logic is unchanged except for the new `passes` flag. v2f reference continues to pass (its hook meets the new floors).
- **L-f CHANNELS FIRST / L-i THE CLAIM IS THE EVENT**: untouched (editorial_select / story_semantics path is upstream and not modified).
- **L-a SIGN-OFF NAMES ALL / CREDITS / L-j RELEASE IS AUTHORISED ON THESE BYTES**: the added `hook_bar` dict lives **outside** the seal (`package_pin.to_pin` explicitly excludes it from `pin_seal`; `release_auth` still sees exact REQUIRED gates on final bytes). MONITORING rows remain non-deciding.
- **M12 FAIL CLOSED / LAW 20 / M2**: no gate was reclassified. No valid calibration, missing part, wrong rater, stale file, hand-edited sha, or out-of-contract reply → no hook passes. One candidate error does not stop the others being asked; first error is returned.
- **L-m (mentioned in ruling)**: explicit ("no rating = no hook").
- **ONE CANONICAL FORM (L-k)**: no new string comparisons outside `canon.py`.
- **Smallest diff / no new renderer/compositor/selector (M1) / GPU0 only**: one new 134-line module (`hook_bar.py`), calibration file, and targeted edits to rating, verdict, and logging paths. No renderer changes.

**Test coverage** is excellent: `test_hook_bar.py` (sealing, staleness, floors-below-3, hand-edit, add_example, live calibration cross-check against `ALONE_TEST.json`), `conftest.py` rig (pinned floors for all other tests, `real_hook_bar=True` for the live-file test), updated `test_medley`, `test_spotlight`, `test_ledger_build`, `test_hook112`, `test_providers`. 687/687 package+providers tests pass; 31/31 mutations killed. Shadow, kind-specific chain, "one error does not stop others", mark outside seal, and "setup now counts" are explicitly exercised. Production hook list is now Grok-only; qwen shadow is recorded but non-deciding.

**Findings**

[P1] The order explicitly says "Nothing else about the hook path changes (may-open rules, G17a, step A, CUTTABLE stay)". The implementation changed coherence/medley min calculation (exclude hook label) and `last_clip_only` (require `own["passes"]` separately). While this is *necessary* for a scroll=3 floor to be usable in medley (otherwise every passing hook would fail `>= COHERENCE_MIN`), it is a larger semantic diff than the ruling permitted. This should have been flagged for PBX confirmation before the audit package. (The comment "this is the one reading of 'nothing else changes' we took" acknowledges the tension but does not resolve it.)

[P2] `hook_bar.bar(..., rater=None)` skips the rater check, yet `passes()` still requires exact backend match against the calibration's rater. This is correct for `hook_live_bar()` but creates an asymmetric contract that is easy to misuse if another caller passes a non-None rater that does not match. Add an explicit comment or make the rater check mandatory when a non-None value is supplied.

[P2] `providers._shadow_of` and `_shadow_ask` now accept a `kind` parameter and build a dedicated chain `"shadow86:coherence_verdict:hook"`. The shadow log records `"kind"`, which is good. However, the shadow thread still uses the *deciding* reply's `cached` / `replayed` flags for the shadow record. A cached Grok decision will suppress 

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 112 s finish=stop usage in 47164 / out 6385 usd_reported=0.006746 usd~0.237 (upper-bound price)

I will begin by analyzing the code changes against the provided "Governing Laws" and the specific requirements of Ruling 115.

### 1. Analysis of `pipeline/hook_bar.py`

**Logic Check:**
- `floors_from`: Calculates the minimum value for each part (`scroll`, `alone`, `setup`) across approved hooks. Enforces `FLOOR_MIN = 3`.
- `load`: Verifies SHA256 integrity.
- `bar`: Checks validity (rater, question version, seed, asking, age < 24h).
- `passes`: Checks if a specific rating record meets the floors and was rated by the correct backend.

**Potential Issue 1: Type Checking in `floors_from`**
```python
if not vals or any(type(v) is not int for v in vals):
    raise ValueError(...)
```
This correctly rejects floats and booleans (since `type(True) is not int` is `False` in Python? No, `type(True) is int` is `False` because `bool` is a subclass of `int` but `type(True)` is `bool`). Wait, `isinstance(True, int)` is `True`, but `type(True) is int` is `False`. So `type(v) is not int` will be `True` for booleans, causing a `ValueError`. This is good, strict fail-closed behavior.

**Potential Issue 2: `passes` Logic**
```python
short = [f"{p} {rec.get(p)} < {live['floors'][p]}" for p in PARTS
         if type(rec.get(p)) is not int or rec[p] < live['floors'][p]]
```
If `rec.get(p)` is `None` (missing key), `type(None) is not int` is `True`, so it adds to `short`. This is correct fail-closed.
If `rec.get(p)` is a float (e.g., 4.0), `type(4.0) is not int` is `True`, so it fails. This is consistent with `floors_from`.

### 2. Analysis of `pipeline/package.py`

**Change: `hook_ratings`**
- Previously: One batched call for all candidates.
- Now: One call per candidate (`for m in todo`).
- `HOOK_VERSION` is updated to include `HOOK_ASKING`. This invalidates old caches.
- Error handling: If one candidate fails, `err` is set, but the loop continues for other candidates. This matches the requirement "a candidate whose chain is spent has no rating... the others are still asked".

**Change: `hook_own`**
- Returns `passes` based on `hook_bar.passes`.
- `rating` is still `min(scroll, alone)` for ordering.
- `short` contains the reason for failure.

**Change: `_can_open`**
- Uses `own["passes"]` instead of `own["rating"] >= HOOK_MIN`.
- This correctly implements the "calibrated bar" logic.

**Change: `medley` and `coherence`**
- The hook's rating is excluded from the `min(...) >= COHERENCE_MIN` check.
- `ok = own is not None and own["passes"] and _line_ok(v["through_line"]) and min([x for lb, x in v["clips"].items() if lb != labs[0]] + [v["vo_point"]]) >= COHERENCE_MIN`
- This ensures the hook passes its *own* bar (floors), while clips pass the *coherence* bar (min 4). This aligns with the "reading of 'nothing else changes'" note in the prompt.

**Change: `last_clip_only`**
- Checks `own["passes"]` for the hook.
- Checks `x < COHERENCE_MIN` for clips (excluding the hook).
- This is consistent.

### 3. Analysis of `pipeline/spotlight.py`

**Change: `inventory`**
- `rows["hook_own"]` uses `own["passes"]`.
- Includes `setup` and `bar` in the row data.

**Change: `build`**
- Filters moments where `own["passes"]` is True.
- Logs the calibrated bar text.

### 4. Analysis of `pipeline/providers.py`

**Change: Shadow Logic**
- `_shadow_of` now accepts `kind`.
- `_shadow_ask` uses `kind` to determine the shadow chain.
- `call` passes `kind` to `_shadow_ask`.
- This allows `coherence_verdict:hook` to have a specific shadow (qwen) while other `coherence_verdict` calls use the general shadow (Grok).

### 5. Analysis of `pipeline/model_providers.json`

- `coherence_verdict:hook` is set to `["xai:grok-4.20-0309-reasoning"]` in all routings.
- This ensures only Grok rates hooks.

### 6. Analysis of Tests

**`tests/package/conftest.py`**
- Patches `package._live_bar` to return a fixed rig bar.
- This isolates tests from the live calibration file.

**`tests/package/test_hook_bar.py`**
- Tests `floors_from`, `load`, `bar`, `passes`, `add_example`.
- Verifies SHA256 integrity.
- Verifies staleness.
- Verifies that a hand-edit breaks the seal.

**`tests/package/test_medley.py`**
- Updates `SEGS` to include `backend` in `hook_rating`.
- Tests that a hook with `scroll: 3, alone: 4, setup: 3` passes (meets floors).
- Tests that a hook with `scroll: 2` fails.
- Tests that a hook rated by a different backend fails.

**`tests/package/test_spotlight.py`**
- Updates `moment` helper to include `backend`.
- Tests `inventory` row for `hook_own`.
- Tests `build` filtering.

**`tests/providers/test_providers.py`**
- Tests shadow routing for `kind="hook"`.

### 7. Critical Review & Findings

**Finding 1: [P1] `hook_bar.py` `bar()` function does not validate `floors` structure before use.**
In `bar()`:
```python
fl = {p: int(cal["floors"][p]) for p in PARTS}
```
If `cal["floors"]` is missing a key (e.g., `setup`), this raises `KeyError`, w

## CLAUDE'S CYCLE 1 CONSENSUS
# C1 CONSENSUS — pp-selectid audit 20261115_1410 (ruling 115 (1)+(2), the calibrated hook bar)

Reviewers: qwen3.8-27b (P1_OR_WORSE: 1); glm-5.3-flash ran out of its 24,000 output tokens before its last line
(finish=length: no P1 count), so the driver asked Grok (P1_OR_WORSE: 1). Cycle 1: $0.0757 vendor-reported.

THE P1s:
1. qwen [P1] "a calibration whose measured_at lies in the future stays valid past its 24 h (now - at is negative)".
   FIXED: bar() refuses a measured_at more than SKEW_MIN (5) minutes ahead of now ("is in the future: refused").
   AND, found while fixing it (glm raised it too, as a P2): a measured_at with NO timezone made `now - at` raise
   TypeError outside the parse's try, so bar() would have crashed a build instead of failing closed. FIXED: refused
   with a reason ("has no timezone"). One new test covers both (a 4-minute skew still passes; 6 minutes does not; a
   naive time is refused and never raises). Mutations B10 / B11 killed.
2. Grok [P1] "the order says nothing else about the hook path changes; the hook's slot in the two verdicts and in
   ruling 62 changed". This is the reading the QUESTION named for the reviewers. It is kept and goes to the
   orchestrator on STATE line 1 as the reading taken: with a scroll floor of 3, a hook that PASSES the calibrated bar
   would fail every line-up if its own rating (3) still sat inside the min >= COHERENCE_MIN (4); the bar would then
   pass hooks that can never open a medley. The clips AFTER the hook and the VO point keep COHERENCE_MIN; the
   may-open rules, G17a, step A and CUTTABLE are untouched. Not a code defect.

glm's findings (from the part of its review that came back), the ones acted on:
3. glm "a rating cached by one model answers for the moment whatever the hook list says: after a calibration onto a
   new rater with the same question, every cached rating fails the rater check and is never asked again (no hook
   could ever pass)". FIXED: hook_ratings serves a cached rating ONLY from a back-end on today's hook list
   (router.chain("coherence_verdict", "hook")); a rating by any other model is asked again by today's rater. A
   stand-in router without chain() keeps the old behaviour. New test (on the list: served; off it: asked again);
   mutation P13 killed.
4. glm "the seed is not in the cache key". FIXED: HOOK_VERSION now hashes the question, the asking AND the seed
   (HOOKS_PROMPT + HOOK_ASKING + "seed 7"), and hook_ratings uses the cache only at production's seed (another seed
   neither reads nor writes it). The calibration's question_version is relabelled to the new value (e3cba8d92551,
   with a note; re-sealed, sha fb964eb15a24...): the measured asking is the same bytes (HOOKS_PROMPT, one candidate,
   seed 7). New test; mutations P10b / P14 killed.
5. glm "the spotlight's pin path: does it carry the mark?". It does: proof_ledger writes SPOTLIGHT_PIN.json through
   package_pin.write_pin -> to_pin (package_pin.py:511), the same to_pin, whose `spot` branch

---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_20261115_1410/C2_STEP.diff (1658 lines)
```
   1 | diff --git a/pipeline/hook_bar.py b/pipeline/hook_bar.py
   2 | new file mode 100644
   3 | index 0000000..d29c497
   4 | --- /dev/null
   5 | +++ b/pipeline/hook_bar.py
   6 | @@ -0,0 +1,140 @@
   7 | +"""RULING 115 (orchestrator 13:24 ET Nov 15): THE HOOK BAR IS DEFINED BY PBX'S APPROVALS.
   8 | +
   9 | +The hook job (package.hook_ratings) asks each candidate ALONE, at production's seed, on the calibrated rater (Grok).
  10 | +A hook passes when EACH of its three parts (scroll, alone, setup) is at least that part's FLOOR. A floor is the lowest
  11 | +value the part took across PBX's approved hooks, under that same asking (the source: tests/package/proof/hook113/
  12 | +ALONE_TEST.json). No floor is set below 3: the order stops a lower one at 3, and the builder reports it.
  13 | +
  14 | +The floors live in ONE calibration file, pipeline/hook_calibration.json, with its sha256. It is valid only for its
  15 | +rater, its question version (package.HOOK_VERSION), its seed and its asking ("alone"), and for 24 h after it was
  16 | +measured (ruling 113 (2): again on any change, and once a day). An invalid or stale file passes NO hook, and the
  17 | +build says why in one line (fail closed, law L-m).
  18 | +A package sealed on this bar says so in its record (NOTE). PBX's approve or reject of it is appended to the file
  19 | +(add_example), so the approved set grows.
  20 | +"""
  21 | +import copy
  22 | +import hashlib
  23 | +import json
  24 | +import os
  25 | +from datetime import datetime, timedelta, timezone
  26 | +
  27 | +PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hook_calibration.json")
  28 | +PARTS = ("scroll", "alone", "setup")
  29 | +FLOOR_MIN = 3                       # the order: "If any floor comes out below 3, stop at 3 for that part and tell me."
  30 | +VALID_H = 24.0                      # ruling 113 (2): "once a day"
  31 | +SKEW_MIN = 5.0                      # a measured_at at most this many minutes ahead of now (clock skew) is accepted
  32 | +NOTE = "hook passed on the calibrated bar"
  33 | +
  34 | +
  35 | +def body_sha(cal):
  36 | +    """The sha256 of the calibration's canonical JSON without its own "sha256" key."""
  37 | +    b = {k: v for k, v in cal.items() if k != "sha256"}
  38 | +    return hashlib.sha256(json.dumps(b, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
  39 | +
  40 | +
  41 | +def floors_from(approved):
  42 | +    """{part: the lowest value it takes across the approved hooks' parts, never below FLOOR_MIN} and the parts that
  43 | +    came out below FLOOR_MIN (the order wants those told)."""
  44 | +    fl, low = {}, []
  45 | +    for p in PARTS:
  46 | +        vals = [a.get(p) for a in approved]
  47 | +        if not vals or any(type(v) is not int for v in vals):
  48 | +            raise ValueError(f"an approved hook has no integer {p!r}: the floors cannot be measured")
  49 | +        fl[p] = min(vals)
  50 | +        if fl[p] < FLOOR_MIN:
  51 | +            low.append(f"{p} {fl[p]} (stopped at {FLOOR_MIN})")
  52 | +            fl[p] = FLOOR_MIN
  53 | +    return fl, low
  54 | +
  55 | +
  56 | +def load(path=PATH):
  57 | +    """The calibration as written, or None with why (missing, unreadable, or its sha does not match its body)."""
  58 | +    try:
  59 | +        with open(path) as f:
  60 | +            cal = json.load(f)
  61 | +    except (OSError, ValueError) as e:
  62 | +        return None, f"the hook calibration cannot be read ({type(e).__name__}: {str(e)[:120]})"
  63 | +    if not isinstance(cal, dict) or cal.get("sha256") != body_sha(cal):
  64 | +        return None, "the hook calibration's sha256 does not match its body (edited by hand?)"
  65 | +    return cal, None
  66 | +
  67 | +
  68 | +def bar(rater, question_version, seed, now=None, path=PATH):
  69 | +    """The live bar: {"floors", "sha256", "rater", ...} when the calibration is valid for exactly this question
  70 | +    version and seed (and this rater, when one is named; passes() checks each rating's own back-end), and is under
  71 | +    VALID_H old; else (None, why), and no hook passes."""
  72 | +    cal, why = load(path)
  73 | +    if cal is None:
  74 | +        return None, why
  75 | +    for k, want in (("rater", rater), ("question_version", question_version), ("seed", seed), ("asking", "alone")):
  76 | +        if k == "rater" and want is None:
  77 | +            continue
  78 | +        if cal.get(k) != want:
  79 | +            return None, f"the hook calibration is for {k} {cal.get(k)!r}, not {want!r}: no hook passes until it is re-run"
  80 | +    try:
  81 | +        at = datetime.fromisoformat(str(cal["measured_at"]))
  82 | +        fl = {p: int(cal["floors"][p]) for p in PARTS}
  83 | +    except (KeyError, TypeError, ValueError):
  84 | +        return None, "the hook calibration has no readable measured_at or floors"
  85 | +    if at.tzinfo is None:                # a naive time cannot be compared with now (audit 20261115_1410)
  86 | +        return None, "the hook calibration's measured_at has no timezone: refused"
  87 | +    age = (now or datetime.now(timezone.utc)) - at
  88 | +    if age < -timedelta(minutes=SKEW_MIN):   # measured "in the future" would stretch the 24 h (audit 1410 C1, qwen)
  89 | +        return None, f"the hook calibration's measured_at ({cal['measured_at']}) is in the future: refused"
  90 | +    if age > timedelta(hours=VALID_H):
  91 | +        return None, f"the hook calibration is over {VALID_H:g} h old (measured {cal['measured_at']}): re-run it"
  92 | +    if any(v < FLOOR_MIN for v in fl.values()):
  93 | +        return None, f"a floor under {FLOOR_MIN} in the hook calibration: refused"
  94 | +    return {"floors": fl, "sha256": cal["sha256"], "rater": cal["rater"], "question_version": cal["question_version"],
  95 | +            "seed": cal["seed"], "measured_at": cal["measured_at"]}, None
  96 | +
  97 | +
  98 | +def passes(rec, live):
  99 | +    """(passes, why) for one hook rating record {"scroll", "alone", "setup", "backend", ...} on the live bar."""
 100 | +    if live is None:
 101 | +        return False, "no valid hook calibration"
 102 | +    if rec.get("backend") != live["rater"]:
 103 | +        return False, f"rated by {rec.get('backend')}, but the bar is calibrated on {live['rater']}"
 104 | +    short = [f"{p} {rec.get(p)} < {live['floors'][p]}" for p in PARTS
 105 | +             if type(rec.get(p)) is not int or rec[p] < live["floors"][p]]
 106 | +    return (not short), ("; ".join(short) or None)
 107 | +
 108 | +
 109 | +def text(live):
 110 | +    """The bar in one line, for every build line and record."""
 111 | +    if live is None:
 112 | +        return "no valid hook calibration: no hook passes"
 113 | +    f = live["floors"]
 114 | +    return (f"the calibrated hook bar (ruling 115): scroll >= {f['scroll']}, alone >= {f['alone']}, setup >= "
 115 | +            f"{f['setup']}, on {live['rater']} asked alone at seed {live['seed']} (calibration {live['sha256'][:12]})")
 116 | +
 117 | +
 118 | +def write(cal, path=PATH):
 119 | +    """Seal and write a calibration (its sha256 over its body), .tmp then rename."""
 120 | +    cal = dict(cal)
 121 | +    cal["sha256"] = body_sha(cal)
 122 | +    tmp = path + ".tmp"
 123 | +    with open(tmp, "w") as f:
 124 | +        json.dump(cal, f, indent=1, sort_keys=True)
 125 | +        f.write("\n")
 126 | +    os.replace(tmp, path)
 127 | +    return cal
 128 | +
 129 | +
 130 | +def add_example(story_id, verdict, hook, reason=None, path=PATH, now=None):
 131 | +    """RULING 115 (2): PBX's approve or reject of a package sealed on this bar, appended as an example (approved =
 132 | +    positive, rejected = negative with his reason). The floors are NOT re-derived here: a new floor comes from the
 133 | +    next calibration run, which asks every approved hook again. -> the calibration as written."""
 134 | +    if verdict not in ("approved", "rejected"):
 135 | +        raise ValueError("verdict is 'approved' or 'rejected'")
 136 | +    if verdict == "rejected" and not reason:
 137 | +        raise ValueError("a rejection carries PBX's reason")
 138 | +    cal, why = load(path)
 139 | +    if cal is None:
 140 | +        raise ValueError(why)
 141 | +    cal = copy.deepcopy(cal)
 142 | +    cal.setdefault("examples", []).append({
 143 | +        "story_id": story_id, "verdict": verdict, "reason": reason,
 144 | +        "hook": {k: hook.get(k) for k in ("moment_id", "text", "channel", *PARTS, "backend")},
 145 | +        "at": (now or datetime.now(timezone.utc)).isoformat(timespec="seconds")})
 146 | +    return write(cal, path)
 147 | diff --git a/pipeline/hook_calibration.json b/pipeline/hook_calibration.json
 148 | new file mode 100644
 149 | index 0000000..4c606ad
 150 | --- /dev/null
 151 | +++ b/pipeline/hook_calibration.json
 152 | @@ -0,0 +1,86 @@
 153 | +{
 154 | + "approved": [
 155 | +  {
 156 | +   "alone": 4,
 157 | +   "approved": "the protected preview (references/pulse_preview_2026-11-11, PBX 2026-11-11)",
 158 | +   "backend": "xai:grok-4.20-0309-reasoning",
 159 | +   "channel": "DataDash",
 160 | +   "how": "asked alone at seed 7",
 161 | +   "ref": "ref-preview",
 162 | +   "scroll": 3,
 163 | +   "setup": 3,
 164 | +   "text": "Bitcoin has now seen a 16 % decline from the overall high from $88 ,000, touching down towards about $73 ,400, $500, give or take.",
 165 | +   "video_id": "RXTVaDsN11M",
 166 | +   "why": "lacks dramatic punch in first seconds"
 167 | +  },
 168 | +  {
 169 | +   "alone": 5,
 170 | +   "approved": "moments-fresh_20261112_050611-37c5b5f5",
 171 | +   "backend": "xai:grok-4.20-0309-reasoning",
 172 | +   "channel": "Saifedean Ammous",
 173 | +   "how": "asked alone at seed 7",
 174 | +   "ref": "ref-37c5b5f5",
 175 | +   "scroll": 3,
 176 | +   "setup": 4,
 177 | +   "text": "Bitcoin does not have any authority that allows people to take the wealth of others. If some people end up with more Bitcoin, that's because they chose to do that.",
 178 | +   "video_id": "vgsSZ4mAHfQ",
 179 | +   "why": "first 2-3s lack punch to stop scroll"
 180 | +  },
 181 | +  {
 182 | +   "alone": 5,
 183 | +   "approved": "moments-fresh_20261112_050611-41f29b1f",
 184 | +   "backend": "xai:grok-4.20-0309-reasoning",
 185 | +   "channel": "Natalie Brunell",
 186 | +   "how": "asked alone at seed 7",
 187 | +   "ref": "ref-41f29b1f",
 188 | +   "scroll": 3,
 189 | +   "setup": 4,
 190 | +   "text": "Bitcoin imposes a global free market for the first time ever.",
 191 | +   "video_id": "wdk5JZ9hPzs",
 192 | +   "why": "first seconds lack strong grab to halt scroll"
 193 | +  },
 194 | +  {
 195 | +   "alone": 5,
 196 | +   "approved": "moments-ledger_20261113_183302-0c68b589",
 197 | +   "backend": "xai:grok-4.20-0309-reasoning",
 198 | +   "channel": "Simply Bitcoin",
 199 | +   "how": "asked alone at seed 7 once more, unrecorded: the first answer was out of contract",
 200 | +   "ref": "ref-0c68b589",
 201 | +   "scroll": 3,
 202 | +   "setup": 4,
 203 | +   "text": "A CEO makes a personal mistake in shareholders pay. A government mismanages its currencies. and its savers pay. Bitcoin's rules aren't kept by a single executive or a single central bank. They're enforced by thousands of independent computers running the same code. No CEO, no compromise, no committee to debate.",
 204 | +   "video_id": "DcUbBkyeh9M",
 205 | +   "why": "first seconds too dry to halt scrolls"
 206 | +  },
 207 | +  {
 208 | +   "alone": 5,
 209 | +   "approved": "moments-ledger_20261113_215708-13949b7c",
 210 | +   "backend": "xai:grok-4.20-0309-reasoning",
 211 | +   "channel": "Simply Bitcoin",
 212 | +   "how": "asked alone at seed 7 once more, unrecorded: the first answer was out of contract",
 213 | +   "ref": "ref-13949b7c",
 214 | +   "scroll": 3,
 215 | +   "setup": 4,
 216 | +   "text": "Currencies are often born for political reasons, but fail for economic reasons. Bitcoin launched in January of 2009. It's never been renamed. It's never gone into another currency. It's never been redenominated or reissued.",
 217 | +   "video_id": "DcUbBkyeh9M",
 218 | +   "why": "dry academic opener lacks scroll-stopping punch"
 219 | +  }
 220 | + ],
 221 | + "asking": "alone",
 222 | + "examples": [],
 223 | + "floors": {
 224 | +  "alone": 4,
 225 | +  "scroll": 3,
 226 | +  "setup": 3
 227 | + },
 228 | + "floors_below_3": [],
 229 | + "measured_at": "2026-11-15T18:07:52+00:00",
 230 | + "question_version": "e3cba8d92551",
 231 | + "question_version_note": "package.HOOK_VERSION: the hook question (HOOKS_PROMPT), the asking (alone, one candidate a call) and the seed (7). Relabelled from bfdf74078d5e when the seed joined the version (audit 20261115_1410 C1, glm): the measured asking is the same.",
 232 | + "rater": "xai:grok-4.20-0309-reasoning",
 233 | + "rule": "a hook passes when EACH of scroll / alone / setup is at least its floor; a floor is the lowest value the part takes across the approved hooks under this asking, never below 3",
 234 | + "ruling": "115 (orchestrator 13:24 ET Nov 15): the hook bar is defined by PBX's approvals",
 235 | + "seed": 7,
 236 | + "sha256": "fb964eb15a242b3ee7e385ce383546baa74e303d5009529eeab3cc18f313320b",
 237 | + "source": "tests/package/proof/hook113/ALONE_TEST.json"
 238 | +}
 239 | diff --git a/pipeline/model_providers.json b/pipeline/model_providers.json
 240 | index 535c340..c071828 100644
 241 | --- a/pipeline/model_providers.json
 242 | +++ b/pipeline/model_providers.json
 243 | @@ -370,9 +370,6 @@
 244 |      "heimdall:deepseek/deepseek-v4.1-flash"
 245 |     ],
 246 |     "coherence_verdict:hook": [
 247 | -    "heimdall:qwen/qwen3.8-27b",
 248 | -    "heimdall:z-ai/glm-5.3-flash",
 249 | -    "heimdall:deepseek/deepseek-v4.1-flash",
 250 |      "xai:grok-4.20-0309-reasoning"
 251 |     ],
 252 |     "coherence_verdict:clips_alone": [
 253 | @@ -393,6 +390,9 @@
 254 |      "anthropic:claude-opus-5-5",
 255 |      "local_judge:gemma3:27b"
 256 |     ],
 257 | +   "coherence_verdict:hook": [
 258 | +    "xai:grok-4.20-0309-reasoning"
 259 | +   ],
 260 |     "coherence_verdict": [
 261 |      "xai:grok-4.20-0309-reasoning",
 262 |      "google:gemini-2.5-pro",
 263 | @@ -457,9 +457,13 @@
 264 |      "xai:grok-4.20-0309-reasoning",
 265 |      "heimdall:deepseek/deepseek-v4.1-flash",
 266 |      "heimdall:z-ai/glm-5.3-flash"
 267 | +   ],
 268 | +   "coherence_verdict:hook": [
 269 | +    "xai:grok-4.20-0309-reasoning"
 270 |     ]
 271 |    },
 272 |    "ruling_88": "RULING 88 (orchestrator 22:15 Nov 13), from the replay's interim, the full table to confirm: (a) fidelity and exclusion on Heimdall now (two families, Grok last); (b) step C and the hook rating move when the full table holds the interim's 98-100 % (Grok first until then); (c) step A: Heimdall FIRST, a clip Heimdall refuses is refused and Grok is never asked, a clip Heimdall passes goes to Grok to confirm; (d) clips-alone and coherence keep Grok, glm out of both; (e) qwen never decides coherence or step C. THE FULL TABLE (01:06 ET Nov 14, 884 rows): (b) holds for the hook rating (qwen 100 % of 15 units, glm 100 % of 11, deepseek 96 %): it moved, qwen -> glm -> deepseek -> Grok; it does not hold for step C (glm 97 %, deepseek 96 %; qwen 98 % but barred by (e)): Grok first.",
 273 | +  "ruling_115": "RULING 115 (orchestrator 13:24 ET Nov 15), amending 85 / 88 / 96 for the HOOK only: the hook job is asked ALONE (one candidate a call) at production's seed by GROK, and Grok alone, in every routing (heimdall_first, today, plan_b): the calibrated floors (pipeline/hook_calibration.json, hook_bar.py) are Grok's, so no other model may decide a hook while Grok is out (no rating = no hook, law L-m). qwen answers every hook in SHADOW (recorded, never deciding; proof_ledger: shadow 'coherence_verdict:hook'). A hook passes when each of scroll / alone / setup is at least its floor.",
 274 |    "ruling_96": "RULING 96 (orchestrator 01:40 ET Nov 14), FINAL until re-measured: HOOK qwen -> glm -> deepseek -> Grok; FIDELITY glm -> qwen -> Grok; EXCLUSION glm -> deepseek -> Grok; STEP A the Heimdall verdict first as the filter (glm first for speed: 45 s median against deepseek's 277 s; deepseek second; qwen third as failover, before Grok), Grok confirms what passes; STEP C, CLIPS-ALONE, COHERENCE, STEP B, SPEAKER, VISION: Grok first. qwen is never first where it failed an anchor. Re-run the replay monthly or when a Heimdall model changes; a type goes back to Grok first if its agreement falls under Grok's own self-agreement.",
 275 |    "ruling_0612": "ORCHESTRATOR RULINGS 06:12 ET Nov 14 (the builder's two routing questions): (1) THE COHERENCE GAP: glm is coherence's LAST fallback, after Grok and after ruling 96's deepseek, which stays second (glm agreed with Grok on 94 % of the replay's coherence decisions, with one anchor failure in the whole table); an out-of-contract glm answer is no verdict (providers.call_parsed moves on, and after glm the chain is spent: fail closed). CLIPS-ALONE has NO Heimdall fallback (52-62 % on the replay): with Grok down it goes to Plan B's other outside family (Gemini's fenced key; OpenAI and Anthropic are frozen legs here; in Plan B mode the router already reads Plan B's coherence list, Grok -> Gemini -> OpenAI -> Anthropic), else it fails closed. (2) QWEN IS STRUCK FROM STEP A (mostly errors; 9 of 43 refusals let through): the first screen glm -> deepseek -> Grok, Grok's confirmation Grok -> glm -> deepseek, and the role's default list (no live caller: every step-A call names its kind) as the first screen. NOT CHANGED: the coherence role's default list (Grok -> deepseek), which the spotlight's closing-line and the medley's takeaway value verdicts use: the replay has no data for them (the orchestrator is asked, STATE 06:14, question B). Every other list is ruling 96's, unchanged.",
 276 |    "ruling_102": "RULING 102 (orchestrator 13:02 ET Nov 14): STEP_A_UNAVAILABLE MUST NEVER END A CLIP. Step A's second family, in order: Heimdall deepseek (its own deadline, ruling 100) -> Heimdall glm -> GEMINI through the fenced key -> the local gemma3:27b on GPU0 through the integrator's judge service (ruling 87's last resort, recorded as such on the pin and on STATE line 1). Grok stays first (ruling 88 (c): Grok confirms a Heimdall pass); the second verdict is still off the first verdict's vendor and family. The first leg that ANSWERS gives the second verdict; an unavailable leg moves on at once, it is never a refusal and never cached. Only if no leg answers is the clip held for THIS build (STEP_A_HELD, not refused), and retried next build."
 277 | diff --git a/pipeline/package.py b/pipeline/package.py
 278 | index 08c0035..c2849af 100644
 279 | --- a/pipeline/package.py
 280 | +++ b/pipeline/package.py
 281 | @@ -9,8 +9,9 @@ usable()      moments a package may use: on screen eligible (word timing, law L-
 282 |  prescreen()   step A of law L-s on EVERY usable moment's own context (ruling 58), ONCE per moment (package-independent):
 283 |                this build's ledger (`store`) and the step-A cache every build shares (`cache`: moment id + text sha +
 284 |                context sha + the step-A prompt); never recomputed
 285 | -hook_ratings() RULING 59: the hook question of ruling 52 on every cleared, cuttable moment that can open, ONE batched
 286 | -              call, cached; only a hook rated >= HOOK_MIN opens, and the angles are written FOR the passing hooks
 287 | +hook_ratings() RULING 59: the hook question of ruling 52 on every cleared, cuttable moment that can open, cached;
 288 | +              RULING 115: each candidate asked ALONE (one call each) and only a hook on the calibrated bar (hook_bar:
 289 | +              every part at least its floor, by the calibrated rater) opens; the angles are written FOR the passing hooks
 290 |  ANGLES        role angle_write: up to MAX_ANGLES one-sentence angles, each backed by 3-8 cleared moments from >= 3
 291 |                channels (one clip per channel, L-u), listed in PLAY ORDER (L-y 3)
 292 |  lineup_for()  code: the hook + 2-4 clips for one angle in the proposer's play order, every segment from a different
 293 | @@ -82,7 +83,8 @@ SHORT_CLIP_S = 8.0                 # a clip under ~8 s is a penalty unless it is
 294 |  MAX_ANGLES = 3                     # orchestrator 05:30: at most 3 angles x 2 writes
 295 |  WRITES = 2
 296 |  COHERENCE_MIN = 4                  # the blind coherence verdict: every rating >= 4 and a through-line, else next angle
 297 | -HOOK_MIN = COHERENCE_MIN           # RULING 59 (b): only a moment rated >= 4 on the hook's own job may open a line-up
 298 | +HOOK_MIN = COHERENCE_MIN           # RULING 59 (b), until ruling 115: a moment rated >= 4 on the hook's own job opened a
 299 | +#   line-up; ruling 115's calibrated bar decides now (hook_own "passes"). replay85's agreement rule still reads it.
 300 |  BUDGET_WALL_S = 900.0              # orchestrator 22:40 ruling 5 (Heimdall as the writer; was 05:25 item 5's 360 s x2):
 301 |  BUDGET_USD_REPORTED = 1.50         # per package 15 min wall and $1.50 by the vendors' OWN reported cost,
 302 |  BUDGET_USD_ESTIMATE = 5.00         # with the price-table estimate (it over-states ~7x) only as a hard ceiling
 303 | @@ -857,25 +859,43 @@ the opener of a video; the candidates are not compared with each other and never
 304 |  For EACH candidate: """ + HOOK_QUESTION + """
 305 |  Give "why": a few words on the candidate's weakest part.
 306 |  Return ONLY this JSON object: {{"hooks": {{{keys}}}}}"""   # ruling 59 (a): ruling 52's ONE hook question, per candidate
 307 | -HOOK_VERSION = hashlib.sha256(HOOKS_PROMPT.encode()).hexdigest()[:12]   # a cached rating is for exactly this question
 308 | -
 309 | -
 310 | -def hook_ratings(router, ms, ctx, writer_vendor, writer_family=None, cache=None, seed=7):
 311 | -    """RULING 59 (a): the hook question of ruling 52 (HOOK_QUESTION: scroll / alone / setup, each 1-5) asked of EVERY
 312 | -    given moment ALONE, in ONE batched call (coherence_verdict, never the writers' vendor or family), each rating
 313 | -    DERIVED as the lowest part (HOOK_RULE). Cached (`cache`, shared by every build) by the moment id, the sha256 of its
 314 | -    text and the question's version: a moment is rated once, by a back-end off the writers. A reply out of contract
 315 | -    moves on to the next model of the chain (providers.call_parsed, ruling 82 as the 20:33 order extends it). ->
 316 | -    ({moment id: {"scroll", "alone", "setup", "rating", "why", "backend", "cached"}}, the error or None).
 317 | -    A moment the call did not rate has no rating (law L-m: never a pass)."""
 318 | +HOOK_ASKING = "alone: one candidate a call (ruling 115)"   # ruling 115: the hook job asks each candidate ALONE
 319 | +HOOK_SEED = 7                      # production's seed for the hook job (the calibration law's seed, ruling 113 (2))
 320 | +HOOK_VERSION = hashlib.sha256((HOOKS_PROMPT + "\n" + HOOK_ASKING + f"\nseed {HOOK_SEED}").encode()).hexdigest()[:12]
 321 | +#   a cached rating is for exactly this question, this asking AND this seed (audit 20261115_1410 C1, glm): the batched
 322 | +#   ratings of before (dd497beb6930) never answer, nor would ratings asked at another seed
 323 | +
 324 | +
 325 | +def hook_live_bar():
 326 | +    """RULING 115: the calibrated hook bar for this question version and seed (hook_bar.bar), or (None, why)."""
 327 | +    import hook_bar as HB
 328 | +    return HB.bar(None, HOOK_VERSION, HOOK_SEED, path=HB.PATH)
 329 | +
 330 | +
 331 | +def hook_ratings(router, ms, ctx, writer_vendor, writer_family=None, cache=None, seed=HOOK_SEED):
 332 | +    """RULING 59 (a) / RULING 115: the hook question of ruling 52 (HOOK_QUESTION: scroll / alone / setup, each 1-5) asked
 333 | +    of EVERY given moment ALONE: ONE call per candidate (ruling 115: the asking the calibration measured; a batch moved
 334 | +    single ratings, 41f29b1f's from 3 alone to 5 among the approved hooks), on coherence_verdict's hook list (ruling
 335 | +    115: Grok; never the writers' vendor or family). Cached (`cache`, shared by every build) by the moment id, the
 336 | +    sha256 of its text and the question version (HOOK_VERSION carries the asking): a moment is rated once, by a back-end
 337 | +    off the writers. A reply out of contract moves on to the next model of the chain (providers.call_parsed, ruling 82
 338 | +    as the 20:33 order extends it). Whether a rated hook may open is hook_own's: the calibrated floors (ruling 115).
 339 | +    -> ({moment id: {"scroll", "alone", "setup", "rating", "why", "backend", "cached"}}, the first error or None).
 340 | +    A moment no call rated has no rating (law L-m: never a pass)."""
 341 |      import providers as P
 342 |      wv, wf = P._as_set(writer_vendor), P._as_set(writer_family)
 343 |      off = lambda name: (lambda b: b is not None and b.vendor not in wv and b.family not in wf)(router.backends.get(name))
 344 | +    try:                                         # audit 20261115_1410 C1 (glm): only a back-end on TODAY's hook list
 345 | +        listed = set(router.chain("coherence_verdict", "hook"))   # answers from the cache, so a rater change re-asks
 346 | +    except (AttributeError, P.ProviderError):    # every hook (a rating by a model off the list can never pass the
 347 | +        listed = None                            # bar); a stand-in router without chain(): as before
 348 | +    cache = cache if seed == HOOK_SEED else None  # the cache holds production's seed only (the key's version has it)
 349 |      cdb, out, todo = _load_cache(cache), {}, []
 350 |      key = lambda m: f"{m['moment_id']}:{text_sha(m['text'])}:{HOOK_VERSION}"
 351 |      for m in ms:
 352 |          rec = next((x for name, x in sorted((cdb.get(key(m)) or {}).items())
 353 | -                    if isinstance(x, dict) and off(name) and x.get("backend") == name), None)
 354 | +                    if isinstance(x, dict) and off(name) and x.get("backend") == name and
 355 | +                    (listed is None or name in listed)), None)
 356 |          if rec is not None and all(isinstance(rec.get(k), int) for k in HOOK_PARTS):
 357 |              out[m["moment_id"]] = dict(rec, rating=min(rec[k] for k in HOOK_OWN), rule=HOOK_OWN_RULE,
 358 |                                         cached=True)          # ruling 61: the own-job rating is scroll / alone
 359 | @@ -883,12 +903,8 @@ def hook_ratings(router, ms, ctx, writer_vendor, writer_family=None, cache=None,
 360 |              todo.append(m)
 361 |      if not todo:
 362 |          return out, None
 363 | -    ids = [m["moment_id"] for m in todo]
 364 | -    cands = "\n".join(f'CANDIDATE id="{m["moment_id"]}" (on screen: {CI._q(_name(m, ctx), 80)}): '
 365 | -                      f'"{CI._q(m["text"], 900)}"' for m in todo)
 366 | -    keys = ", ".join(f'"{i}": {{"scroll": 1, "alone": 1, "setup": 1, "why": "..."}}' for i in ids)
 367 |  
 368 | -    def parse(text):
 369 | +    def parse(text, ids):
 370 |          v = json.loads(text.strip())
 371 |          h = v["hooks"] if isinstance(v, dict) and set(v) == {"hooks"} else None
 372 |          if not isinstance(h, dict) or set(h) != set(ids) or any(
 373 | @@ -896,21 +912,25 @@ def hook_ratings(router, ms, ctx, writer_vendor, writer_family=None, cache=None,
 374 |                  any(type(x[k]) is not int or not 1 <= x[k] <= 5 for k in HOOK_PARTS) for x in h.values()):
 375 |              raise ValueError("hook ratings out of contract")
 376 |          return h
 377 | -    try:                                         # the 20:33 order: an answer out of contract moves on to the next
 378 | -        r, h = P.call_parsed(router, "coherence_verdict", HOOKS_PROMPT.format(hooks=cands, keys=keys), parse,
 379 | -                             600 + 150 * len(ids), seed, avoid_vendor=writer_vendor, avoid_family=writer_family,
 380 | -                             kind="hook")                                # ruling 88: the hook rating's own list
 381 | -    except (P.ProviderError, P.SpendLimit, ValueError, TypeError, KeyError) as e:   # (it was one re-ask of the same
 382 | -        return out, f"{type(e).__name__}: {str(e)[:200]}"     # model) unavailable, all out of contract, or the guard
 383 | -    new = {}
 384 | -    for m in todo:
 385 | -        x = h[m["moment_id"]]
 386 | +    new, err = {}, None
 387 | +    for m in todo:                               # RULING 115: ALONE, one candidate a call (the calibration's asking)
 388 | +        mid = m["moment_id"]
 389 | +        cand = f'CANDIDATE id="{mid}" (on screen: {CI._q(_name(m, ctx), 80)}): "{CI._q(m["text"], 900)}"'
 390 | +        keys = f'"{mid}": {{"scroll": 1, "alone": 1, "setup": 1, "why": "..."}}'
 391 | +        try:                                     # the 20:33 order: an answer out of contract moves on to the next
 392 | +            r, h = P.call_parsed(router, "coherence_verdict", HOOKS_PROMPT.format(hooks=cand, keys=keys),
 393 | +                                 lambda t, i=(mid,): parse(t, i), 600 + 150, seed, avoid_vendor=writer_vendor,
 394 | +                                 avoid_family=writer_family, kind="hook")   # ruling 88: the hook rating's own list
 395 | +        except (P.ProviderError, P.SpendLimit, ValueError, TypeError, KeyError) as e:   # this candidate has no rating
 396 | +            err = err or f"{type(e).__name__}: {str(e)[:200]}"       # (law L-m); the others are still asked
 397 | +            continue
 398 | +        x = h[mid]
 399 |          rec = {**{k: x[k] for k in HOOK_PARTS}, "rating": min(x[k] for k in HOOK_OWN), "why": x["why"][:300],
 400 | -               "backend": r.backend, "rule": HOOK_OWN_RULE}           # ruling 61: scroll / alone
 401 | -        out[m["moment_id"]] = dict(rec, cached=False, replayed=bool(getattr(r, "replayed", False)))
 402 | +               "backend": r.backend, "rule": HOOK_OWN_RULE}           # the rating orders hooks; hook_own decides
 403 | +        out[mid] = dict(rec, cached=False, replayed=bool(getattr(r, "replayed", False)))
 404 |          new[key(m)] = {r.backend: rec}
 405 |      _cache_put(cache, new)
 406 | -    return out, None
 407 | +    return out, err
 408 |  
 409 |  TAKEAWAY_SAID = ("The takeaway may characterise what the clips SAID, never what WILL happen. Two kinds were refused: a "
 410 |                   "forecast or a permanence claim stated as fact ('Bitcoin outlasts politics.'), and a superlative that "
 411 | @@ -1380,15 +1400,46 @@ def no_role_on_screen(m):
 412 |                                          "with no clip scorer at the pin stage") + f": {c_why}; {h_why}")
 413 |  
 414 |  
 415 | +_LIVE = {}
 416 | +
 417 | +
 418 | +def _live_bar():
 419 | +    """The calibrated bar, read once per state of the calibration file (its mtime) and per minute: a build reads it a
 420 | +    few times, and a calibration that ages past its 24 h mid-build stops passing hooks within the minute."""
 421 | +    import hook_bar as HB
 422 | +    try:
 423 | +        k = (os.stat(HB.PATH).st_mtime_ns, int(time.time() // 60))
 424 | +    except OSError:
 425 | +        k = (None, int(time.time() // 60))
 426 | +    if k not in _LIVE:
 427 | +        _LIVE.clear()
 428 | +        _LIVE[k] = hook_live_bar()
 429 | +    return _LIVE[k]
 430 | +
 431 | +
 432 | +def hook_bar_mark():
 433 | +    """RULING 115 (2): what a package sealed on the calibrated bar carries in its record (and its pin, outside the seal):
 434 | +    the plain line for the Telegram note, the floors and the calibration's sha."""
 435 | +    import hook_bar as HB
 436 | +    live, why = _live_bar()
 437 | +    return {"note": HB.NOTE, "bar": HB.text(live), "floors": (live or {}).get("floors"),
 438 | +            "calibration_sha256": (live or {}).get("sha256"), "ruling": "115"}
 439 | +
 440 | +
 441 |  def hook_own(m):
 442 | -    """RULING 61 (12:00): a hook's OWN-JOB rating, the cached one ruling 59 gave it ("hook_rating"): {"scroll",
 443 | -    "alone", "rating": the lower of the two, "source", "rule"}. 'Sets up what follows' is not part of it: it is judged
 444 | -    at the hook -> clip_01 join. None when the moment carries no complete rating (then it never opens, law L-m)."""
 445 | +    """RULING 61 / RULING 115: a hook's OWN-JOB rating, the cached one ruling 59 gave it ("hook_rating"): {"scroll",
 446 | +    "alone", "setup", "rating": the lower of scroll and alone (it ORDERS hooks), "passes": RULING 115, every part at
 447 | +    least its calibrated floor, rated by the calibrated rater (hook_bar.passes), "short": why not, "bar": the bar in one
 448 | +    line, "source", "rule"}. None when the record lacks a part (then it never opens, law L-m)."""
 449 | +    import hook_bar as HB
 450 |      r = (m or {}).get("hook_rating") or {}
 451 | -    parts = {k: r.get(k) for k in HOOK_OWN}
 452 | +    parts = {k: r.get(k) for k in HOOK_PARTS}
 453 |      if not all(isinstance(x, int) and not isinstance(x, bool) for x in parts.values()):
 454 |          return None
 455 | -    return dict(parts, rating=min(parts.values()), source="the hook's cached own-job rating (ruling 61)",
 456 | +    live, why = _live_bar()
 457 | +    ok, short = HB.passes(dict(parts, backend=r.get("backend")), live)
 458 | +    return dict(parts, rating=min(parts[k] for k in HOOK_OWN), passes=ok, short=why if live is None else short,
 459 | +                bar=HB.text(live), source="the hook's cached own-job rating (ruling 61), on the calibrated bar (ruling 115)",
 460 |                  rule=HOOK_OWN_RULE)
 461 |  
 462 |  
 463 | @@ -1417,8 +1468,9 @@ def third_opener(m):
 464 |  def _can_open(m, pending_verdict=False):
 465 |      """Whether a moment may OPEN a line-up: hook-eligible, its hook onset measured and passed (G17a), a first word the
 466 |      render's STAND_ALONE takes for a hook (stand_alone.opener), and, once the build has rated the pool's hooks (RULING
 467 | -    59: build() sets "hook_rating" on every cleared moment before any line-up), rated >= HOOK_MIN on the hook's own job
 468 | -    (an unmeasured rating is never a pass, law L-m). A moment without the key is judged as before ruling 59."""
 469 | +    59: build() sets "hook_rating" on every cleared moment before any line-up), passing the calibrated hook bar on the
 470 | +    hook's own job (ruling 115: hook_own "passes"; an unmeasured rating is never a pass, law L-m). A moment without
 471 | +    the key is judged as before ruling 59."""
 472 |      import stand_alone as SA
 473 |      v = verdict_of(m)                                    # RULING 94 (b): the scorer's verdict on its current text
 474 |      sc = (v["score"], v["fault"]) if v else (None, None)
 475 | @@ -1432,8 +1484,8 @@ def _can_open(m, pending_verdict=False):
 476 |          return False
 477 |      if "hook_rating" not in m:
 478 |          return True                                      # not rated yet: judged as before ruling 59
 479 | -    own = hook_own(m)                                    # ruling 61: scroll / alone, the cached own-job rating
 480 | -    return own is not None and own["rating"] >= HOOK_MIN
 481 | +    own = hook_own(m)                                    # ruling 115: every part at least its calibrated floor
 482 | +    return own is not None and own["passes"]
 483 |  
 484 |  
 485 |  def hook_order(ms):
 486 | @@ -1522,7 +1574,7 @@ def placement(m):
 487 |      eligibility and a passed hook onset (G17a) it cannot open. Under SHORT_CLIP_S it may not play mid-line-up: the
 488 |      short-clip rule binds the clips AFTER the hook only, so a short clip that can open may be the hook or the LAST clip,
 489 |      and one that cannot open only the LAST (the 08:46 build: a 7.26 s opener was the only formable hook). RULING 59:
 490 | -    "may open" is can_open(): once the pool's hooks are rated, only a hook rated >= HOOK_MIN opens."""
 491 | +    "may open" is can_open(): once the pool's hooks are rated, only a hook on the calibrated bar opens (ruling 115)."""
 492 |      opens = can_open(m)
 493 |      if m["duration_s"] < SHORT_CLIP_S:
 494 |          return f" | under {SHORT_CLIP_S:.0f} s: " + ("only the hook or the LAST clip" if opens else "only the LAST clip")
 495 | @@ -1688,8 +1740,9 @@ def coherence(router, pk, writer_vendor, seed=7, writer_family=None, hook=None):
 496 |      v = dict(v, clips={**({labs[0]: own["rating"]} if own else {}), **v["clips"]},
 497 |               hook_own=own or {"rating": None, "why": "the hook carries no cached own-job rating (ruling 61): "
 498 |                                                       "fail closed"})
 499 | -    ok = own is not None and _line_ok(v["through_line"]) and \
 500 | -        min(list(v["clips"].values()) + [v["vo_point"]]) >= COHERENCE_MIN
 501 | +    ok = own is not None and own["passes"] and _line_ok(v["through_line"]) and \
 502 | +        min([x for lb, x in v["clips"].items() if lb != labs[0]] + [v["vo_point"]]) >= COHERENCE_MIN   # ruling 115:
 503 | +    #   the hook's slot is its calibrated bar, every clip after it and the VO point COHERENCE_MIN, as before
 504 |      return ok, dict(v, backend=r.backend, measured=True, replayed=bool(getattr(r, "replayed", False)))
 505 |  
 506 |  
 507 | @@ -1749,22 +1802,26 @@ def medley(router, segs, ctx, writer_vendor, seed=7, writer_family=None):
 508 |               hook_own=own or {"rating": None, "why": "the hook carries no cached own-job rating (ruling 61): "
 509 |                                                       "fail closed"})
 510 |      flagged = [j for j in js if v["joins"][j]["followable"] is False]
 511 | -    ok = own is not None and _line_ok(v["through_line"]) and min(v["clips"].values()) >= COHERENCE_MIN and \
 512 | -        len(flagged) <= LY_MAX_BRIDGES
 513 | +    ok = own is not None and own["passes"] and _line_ok(v["through_line"]) and \
 514 | +        min(x for lb, x in v["clips"].items() if lb != labs[0]) >= COHERENCE_MIN and len(flagged) <= LY_MAX_BRIDGES
 515 | +    #   ruling 115: the hook's slot is its calibrated bar; every clip after it COHERENCE_MIN, as before
 516 |      return ok, dict(v, flagged=flagged, backend=r.backend, measured=True,
 517 |                      replayed=bool(getattr(r, "replayed", False)), cached=bool(getattr(r, "cached", False)))
 518 |  
 519 |  
 520 |  def last_clip_only(segs, med):
 521 |      """RULING 62 (12:00): whether a clips-alone failure is its LAST clip's alone: measured, the through-line stated,
 522 | -    every other rating (the hook's cached one included) >= COHERENCE_MIN, the last clip's under it, and no more than
 523 | -    LY_MAX_BRIDGES flagged joins once the join into the last clip goes with it."""
 524 | +    the hook passing its calibrated bar (ruling 115: hook_own of the line-up's own hook, as medley() judges it), every
 525 | +    clip after it but the last >= COHERENCE_MIN, the last clip's under it, and no more than LY_MAX_BRIDGES flagged
 526 | +    joins once the join into the last clip goes with it."""
 527 |      labs = labels(len(segs))
 528 |      cl = med.get("clips") or {}
 529 |      if not med.get("measured") or not _line_ok(med.get("through_line")) or labs[-1] not in cl or labs[0] not in cl:
 530 |          return False
 531 |      rest = [j for j in med.get("flagged") or [] if j != joins(labs)[-1]]
 532 | -    return [lb for lb, x in cl.items() if x < COHERENCE_MIN] == [labs[-1]] and len(rest) <= LY_MAX_BRIDGES
 533 | +    own = hook_own(segs[0])                              # ruling 115: the hook passes by its calibrated bar
 534 | +    return own is not None and own["passes"] and [lb for lb, x in cl.items() if lb != labs[0] and x < COHERENCE_MIN] \
 535 | +        == [labs[-1]] and len(rest) <= LY_MAX_BRIDGES
 536 |  
 537 |  
 538 |  def reorder(segs, bad_pairs, judged, repeat_ok=False):
 539 | @@ -2422,8 +2479,9 @@ def load_candidate(record, index=None, source=""):
 540 |  
 541 |  def candidate_lineup(router, candidate, cleared, now):
 542 |      """RULING 66: the candidate's line-up as THIS build's pool holds it, or why it is closed. Every clip must still be
 543 | -    cleared (a clip delivered, aged out or failing a gate closes it), its hook must still open (its cached rating >=
 544 | -    HOOK_MIN, G17a), and exactly its clips, in its order, must still form a line-up under lineup_for's own rules
 545 | +    cleared (a clip delivered, aged out or failing a gate closes it), its hook must still open (its cached rating on
 546 | +    the calibrated bar, ruling 115; G17a), and exactly its clips, in its order, must still form a line-up under
 547 | +    lineup_for's own rules
 548 |      (the seconds, the channels, price predictions, short clips, trims, the render's STAND_ALONE).
 549 |      -> (segs, None) or (None, why)."""
 550 |      ids = list(candidate["lineup"])
 551 | @@ -2433,7 +2491,7 @@ def candidate_lineup(router, candidate, cleared, now):
 552 |      if gone:
 553 |          return None, f"no longer cleared in this pool (delivered, aged out, or a gate fails): {gone}"
 554 |      if not can_open(cleared[ids[0]]):
 555 | -        return None, f"its hook no longer opens (rating >= {HOOK_MIN} and G17a): {ids[0]}"
 556 | +        return None, f"its hook no longer opens (the calibrated hook bar and G17a): {ids[0]}"
 557 |      segs = lineup_for(dict(candidate["angle"], moments=ids), cleared, clips=(len(ids) - 1, len(ids) - 1),
 558 |                        repeat_ok=candidate.get("supply_exception") is not None, need_onset=True,
 559 |                        need_stand_alone=True, now=now, hook_only=True)
 560 | @@ -2456,11 +2514,11 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 561 |      scorer_verdicts_path / scorer_candidates_path / build_name (ruling 56, scorer_pass): the integrator's verdicts of the
 562 |      render's clip scorer to read, and where to write the next pass's candidates (None: neither).
 563 |      RULING 59, HOOK FIRST: once the pool is screened, every cleared, cuttable moment that can open is rated on the hook's
 564 | -    own job in one batched call (hook_ratings); only a hook rated >= HOOK_MIN opens; with none, the build stops there
 565 | -    ('no hook in the pool', the three best listed) before the second screen, the angles and any line-up. The angle
 566 | +    own job (hook_ratings; ruling 115: each alone); only a hook on the calibrated bar opens; with none, the build stops
 567 | +    there ('no hook in the pool', the three best listed) before the second screen, the angles and any line-up. The angle
 568 |      writer is given THE HOOKS and writes each angle FOR one; the angles are tried best hook first (ruling 57's
 569 |      freshness next), each line-up opens on its angle's own hook and never swaps it.
 570 | -    RULING 70, THE VISUAL CHECK (visual_pin): every hook rated >= HOOK_MIN is seen right after the ratings, before any
 571 | +    RULING 70, THE VISUAL CHECK (visual_pin): every hook on the bar is seen right after the ratings, before any
 572 |      angle is asked (a hook whose sheet shows a third person while its words make a negative claim, or that is not
 573 |      measured, may not open: can_open); every clip of a line-up that passes the clips-alone verdict is seen before any
 574 |      write (not measured: dropped and re-lined, law L-m). Findings are sealed as FLAGS on the segment, never a reject by
 575 | @@ -2642,7 +2700,7 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 576 |          m.pop("hook_rating", None)                                       # cache's), never one carried in
 577 |      openers = {mid: m for mid, m in cleared.items() if can_open(m)}      # RULING 59 (a): every one that can open,
 578 |      rated, hook_err = hook_ratings(router, list(openers.values()), ctx, wv, wf, cache=hook_cache) if openers else \
 579 | -        ({}, None)                                                        # one batched call, cached
 580 | +        ({}, None)                                                        # each alone (ruling 115), cached
 581 |      for mid, m in cleared.items():                                       # (b): the rating gates every opening now
 582 |          m["hook_rating"] = rated.get(mid) or {"rating": None, "why": (f"not rated: {hook_err}" if mid in openers else
 583 |                                                                        "cannot open (hook eligibility, G17a or the "
 584 | @@ -2663,16 +2721,20 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 585 |              + (f" ({'; '.join(f'{k}: {v[:90]}' for k, v in blocked.items())})" if blocked else "")
 586 |              + f" ({time.time() - t0:.0f} s)")
 587 |      best = [hook_line(m, ctx) for m in hook_order([m for mid, m in openers.items() if mid in rated])[:3]]
 588 | -    out["hook_pool"] = {"can_open": len(openers), "rated": len(rated), "error": hook_err, "min": HOOK_MIN,
 589 | +    import hook_bar as HB
 590 | +    live, live_why = _live_bar()                         # RULING 115: the calibrated bar, named in every build line
 591 | +    out["hook_pool"] = {"can_open": len(openers), "rated": len(rated), "error": hook_err, "bar": HB.text(live),
 592 | +                        "bar_floors": (live or {}).get("floors"), "bar_sha256": (live or {}).get("sha256"),
 593 | +                        "bar_invalid": live_why,
 594 |                          "ratings": {mid: rated[mid] for mid in sorted(rated)}, "best": best,
 595 |                          "passing": [m["moment_id"] for m in hook_order([m for m in cleared.values() if can_open(m)])],
 596 |                          "visual_blocked": blocked}
 597 | -    log(f"  hooks (ruling 59): {len(openers)} can open, {len(rated)} rated, {len(out['hook_pool']['passing'])} rated >= "
 598 | -        f"{HOOK_MIN} on the hook's own job" + (f"; NOT RATED: {hook_err}" if hook_err else "") +
 599 | -        f" ({time.time() - t0:.0f} s)")
 600 | +    log(f"  hooks (ruling 59): {len(openers)} can open, {len(rated)} rated, {len(out['hook_pool']['passing'])} pass "
 601 | +        f"{HB.text(live)}" + (f" [{live_why}]" if live_why else "") + (f"; NOT RATED: {hook_err}" if hook_err else "")
 602 | +        + f" ({time.time() - t0:.0f} s)")
 603 |      if not out["hook_pool"]["passing"]:                                  # (d): no line-up is paid for
 604 |          out["why_none"] = ("no hook in the pool (ruling 59 d): " + (
 605 | -            f"none of the {len(openers)} moments that can open rates >= {HOOK_MIN} on the hook's own job" +
 606 | +            f"none of the {len(openers)} moments that can open passes {HB.text(live)}" +
 607 |              (f" ({len(openers) - len(rated)} not rated: {hook_err})" if hook_err else "") + "; the best: " +
 608 |              "; ".join(f"{b['channel']} {b['rating']} (scroll {b['scroll']}, alone {b['alone']}, setup {b['setup']}): "
 609 |                        f"{b['why']}" for b in best) if openers else
 610 | @@ -2702,7 +2764,7 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 611 |          return out
 612 |      passing = hook_order([m for m in cleared.values() if can_open(m)])    # ruling 59: the passing hooks still
 613 |      if not passing:                                                        # cleared after the second screen
 614 | -        out["why_none"] = ("no hook in the pool (ruling 59 d): every hook rated >= " + str(HOOK_MIN) + " failed the "
 615 | +        out["why_none"] = ("no hook in the pool (ruling 59 d): every hook that passed the calibrated bar failed the "
 616 |                             "second vendor's step A: " + "; ".join(out["prescreen"]["second_vendor"].get(mid, "?")
 617 |                                                                      for mid in out["hook_pool"]["passing"]))
 618 |          return out
 619 | @@ -3458,6 +3520,8 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 620 |              if out["packages"] or out.get("budget_stop") or out.get("lock_stop") or over_budget(ai):
 621 |                  break
 622 |      out["package"] = out["packages"][0] if out["packages"] else None
 623 | +    if out["package"]:                                   # RULING 115 (2): a package sealed on the calibrated bar says so
 624 | +        out["package"]["hook_bar"] = hook_bar_mark()
 625 |      if candidate is not None:                             # RULING 66: what became of the candidate
 626 |          t_ = next((t for t in out["tried"] if t.get("candidate") is not None), {})
 627 |          out["candidate"]["result"] = t_.get("result") or t_.get("why") or out.get("why_none") or "not tried"
 628 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
 629 | index 1f409cf..03990bc 100644
 630 | --- a/pipeline/package_pin.py
 631 | +++ b/pipeline/package_pin.py
 632 | @@ -495,6 +495,8 @@ def to_pin(pk, run_name):
 633 |                                      "spotlight": pk.get("spotlight")}                  # and why (outside the seal)
 634 |                                     if spot else {}),
 635 |                                  "gates": pk["gates"],
 636 | +                                **({"hook_bar": pk["hook_bar"]} if pk.get("hook_bar") else {}),   # ruling 115 (2): the
 637 | +                                #   calibrated hook bar's plain line for the Telegram note, floors and sha (outside the seal)
 638 |                                  **({"btc_screen": pk["btc_screen"]} if pk.get("btc_screen") is not None else {}),
 639 |                                  **({"formats": fmts} if fmts is not None else {}),   # ruling 93 amended (sealed)
 640 |                                  "checks": {"vo_fidelity_ok": True, "context_integrity_ok": True,
 641 | diff --git a/pipeline/providers.py b/pipeline/providers.py
 642 | index 36ca761..5e2c2cb 100644
 643 | --- a/pipeline/providers.py
 644 | +++ b/pipeline/providers.py
 645 | @@ -1213,24 +1213,29 @@ class Router:
 646 |                      self.down[n] = was
 647 |          return ok
 648 |  
 649 | -    def _shadow_of(self, role):
 650 | -        return self.shadow.get(role) or self.shadow.get("*")
 651 | +    def _shadow_of(self, role, kind=None):
 652 | +        """RULING 86, and RULING 115 for a verdict type: "<role>:<kind>" first (the hook job's qwen), then the role,
 653 | +        then "*"."""
 654 | +        return (self.shadow.get(f"{role}:{kind}") if kind else None) or self.shadow.get(role) or self.shadow.get("*")
 655 |  
 656 | -    def _shadow_ask(self, role, prompt, max_tokens, seed, system, deciding):
 657 | +    def _shadow_ask(self, role, prompt, max_tokens, seed, system, deciding, kind=None):
 658 |          """RULING 86: ask the role's shadow back-end the same prompt, in a thread; one JSON line to shadow_log per
 659 | -        verdict with both answers. Never raises into the build and never decides."""
 660 | +        verdict with both answers. Never raises into the build and never decides. A verdict type's own shadow (RULING
 661 | +        115) is asked on a chain of its own ("shadow86:<role>:<kind>"), so it never takes another shadow's chain."""
 662 |          import threading
 663 | -        name = self._shadow_of(role)
 664 | -        self.chains.setdefault(f"shadow86:{role}", [name])
 665 | +        name = self._shadow_of(role, kind)
 666 | +        own = f"shadow86:{role}:{kind}" if kind and self.shadow.get(f"{role}:{kind}") else f"shadow86:{role}"
 667 | +        self.chains.setdefault(own, [name])
 668 |  
 669 |          def run():
 670 | -            rec = {"role": role, "prompt": prompt_text(prompt), "images": len(prompt["images"]) if is_vision(prompt)
 671 | +            rec = {"role": role, "kind": kind, "prompt": prompt_text(prompt),
 672 | +                   "images": len(prompt["images"]) if is_vision(prompt)
 673 |                     else 0, "max_tokens": max_tokens, "seed": seed, "system": system,
 674 |                     "deciding": {"backend": deciding.backend, "vendor": deciding.vendor, "text": deciding.text,
 675 |                                  "cached": bool(getattr(deciding, "cached", False))}}
 676 |              t0 = time.time()
 677 |              try:
 678 | -                r = self.call(f"shadow86:{role}", prompt, max_tokens, seed, system=system)
 679 | +                r = self.call(own, prompt, max_tokens, seed, system=system)
 680 |                  rec["shadow"] = {"backend": r.backend, "text": r.text, "seconds": round(time.time() - t0, 2),
 681 |                                   "cached": bool(getattr(r, "cached", False)),
 682 |                                   "usd_reported": (r.usage or {}).get("usd_reported"), "usd_estimate": r.usd}
 683 | @@ -1314,8 +1319,8 @@ class Router:
 684 |                      rec = json.load(f)
 685 |                  out = Reply(rec["text"], name, b.vendor, rec.get("seconds", 0.0), rec.get("usage") or {},
 686 |                              rec.get("usd", 0.0), self.replay, tried, notices, b.family, not self.replay, path)
 687 | -                if self.shadow and role in SHADOW_ROLES and self._shadow_of(role) not in (None, name):
 688 | -                    self._shadow_ask(role, prompt, max_tokens, seed, system, out)  # ruling 86: a recorded verdict too
 689 | +                if self.shadow and role in SHADOW_ROLES and self._shadow_of(role, kind) not in (None, name):
 690 | +                    self._shadow_ask(role, prompt, max_tokens, seed, system, out, kind)   # ruling 86: recorded too
 691 |                  return out
 692 |              if self.replay:
 693 |                  tried.append((name, "replay: not recorded"))
 694 | @@ -1410,8 +1415,8 @@ class Router:
 695 |                  recorded = path
 696 |              out = Reply(text, name, b.vendor, round(secs, 2), usage, usd, False, tried, notices, b.family, False,
 697 |                          recorded)
 698 | -            if self.shadow and role in SHADOW_ROLES and self._shadow_of(role) not in (None, name):
 699 | -                self._shadow_ask(role, prompt, max_tokens, seed, system, out)     # ruling 86: asked, never deciding
 700 | +            if self.shadow and role in SHADOW_ROLES and self._shadow_of(role, kind) not in (None, name):
 701 | +                self._shadow_ask(role, prompt, max_tokens, seed, system, out, kind)   # ruling 86: never deciding
 702 |              return out
 703 |          if self.replay:
 704 |              raise ReplayMiss(f"{role}: no recorded exchange ({tried})")
 705 | diff --git a/pipeline/spotlight.py b/pipeline/spotlight.py
 706 | index c945ced..c45473d 100644
 707 | --- a/pipeline/spotlight.py
 708 | +++ b/pipeline/spotlight.py
 709 | @@ -55,7 +55,7 @@ RUNTIME_S = PP.SPOT_RUNTIME_S          # ruling 90: total 28 to 50 s (the render
 710 |  SNAP_TO_S = round(max(SPOT_S[0], RUNTIME_S[0] - P.FINAL_TAIL_S), 2)
 711 |  #   13.7 s: the factory's tail (sign-off, credits card, outro, edges) is 14.3 s, so with no closing line (ruling 91's
 712 |  #   default) a shorter clip cannot reach 28 s. A moment shorter than this is snapped; it is never padded.
 713 | -HOOK_MIN = 4                           # ruling 90: >= 4 on the hook's own job (package.hook_own: scroll / alone)
 714 | +#   The opener's own job: ruling 90's ">= 4" (HOOK_MIN) is ruling 115's calibrated bar now (package.hook_own "passes").
 715 |  ALONE_MIN = 4.0                        # ruling 90: >= 4 standing alone, by the ALONE scorer (its scale is 1-5)
 716 |  CLOSING_MAX_WORDS = PP.SPOT_CLOSING_MAX_WORDS   # 12
 717 |  COMMENT_MAX_LINES = 2                  # ruling 90: "one or two short casual lines"
 718 | @@ -738,10 +738,12 @@ def inventory(pk, m, fid, dup, rt_ok, style, cx, a_off, a_two, exc, truth, pre,
 719 |                            by_rule="ruling 90: the visual check clean (no ruling-70 flag, not blocked as a hook, and "
 720 |                                    "eligible on its frames under ruling 93; a ruling-93 burned_in flag is listed)")
 721 |      own, hr = P.hook_own(m), m.get("hook_rating") or {}
 722 | -    rows["hook_own"] = _row(own is not None and own["rating"] >= HOOK_MIN, hr.get("backend"),
 723 | +    rows["hook_own"] = _row(own is not None and own["passes"], hr.get("backend"),
 724 |                              bool(hr.get("replayed", False)), measured=own is not None,
 725 |                              rating=(own or {}).get("rating"), scroll=hr.get("scroll"), alone=hr.get("alone"),
 726 | -                            why=hr.get("why"), min=HOOK_MIN, rule="ruling 90: >= 4 on the hook's own job (ruling 61)")
 727 | +                            setup=hr.get("setup"), why=hr.get("why"), bar=(own or {}).get("bar"),
 728 | +                            rule="ruling 115: every part (scroll, alone, setup) at least its calibrated floor, rated "
 729 | +                                 "by the calibrated rater")
 730 |      sv = P.verdict_of(m)
 731 |      rows["stands_alone"] = _row(sv is not None and float(sv["score"]) >= ALONE_MIN,
 732 |                                  f"the ALONE scorer ({(sv or {}).get('model')}, the render's stand_alone scorer as the "
 733 | @@ -818,8 +820,8 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 734 |      stage and why it stopped), "finalists", "near", "why_none", ...}. The stages run cheapest first, each on what the
 735 |      one before passed; every verdict is the medley's own and cached or recorded across builds: step A
 736 |      (package.prescreen), L-v 2 and CUTTABLE (truth_for), G17a (hook_onset_for), the render's hook rules and the hook's
 737 | -    own-job rating (package._can_open, hook_ratings: >= HOOK_MIN), the visual check clean (visual_pin: measured, no
 738 | -    flag, not blocked as a hook), step A from the second family (package.second_screen), the ALONE scorer >= ALONE_MIN
 739 | +    own-job rating (package._can_open, hook_ratings: ruling 115's calibrated bar), the visual check clean
 740 | +    (visual_pin: measured, no flag, not blocked as a hook), step A from the second family (package.second_screen), the ALONE scorer >= ALONE_MIN
 741 |      (a moment with no rating yet waits up to wait_s for the integrator's pass, polling the verdicts file), ruling 92's
 742 |      source test; then, best first (rank_key), up to `finalists` moments: the exclusion verdict, the render's lock
 743 |      pre-check (lock_check; no verdict stops the search, as in a medley build) and package_for(). lock_check None: no
 744 | @@ -907,10 +909,11 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 745 |          m["hook_rating"] = rated.get(mid) or {"rating": None, "why": f"not rated: {herr}"}
 746 |          own = P.hook_own(m)
 747 |          rec[mid]["hook_own"] = (own or {}).get("rating")
 748 | -        if own is not None and own["rating"] >= HOOK_MIN:
 749 | +        rec[mid]["hook_passes"] = bool((own or {}).get("passes"))   # ruling 115: the bar's verdict (glm, audit 1410)
 750 | +        if own is not None and own["passes"]:              # ruling 115: the calibrated bar
 751 |              strong[mid] = m
 752 |          else:
 753 | -            stop(mid, f"the hook's own job rates {(own or {}).get('rating')} (needs {HOOK_MIN}): "
 754 | +            stop(mid, f"the hook's own job: {(own or {}).get('short') or 'not rated'} ({(own or {}).get('bar')}): "
 755 |                        f"{m['hook_rating'].get('why')}")
 756 |      passed(strong, 4)
 757 |      vcache = VP.load_cache(visual_cache) if visual_cache else {}
 758 | @@ -988,7 +991,7 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 759 |      ranked = sorted(ok_src, key=rank_key)
 760 |      out["finalists"] = [m["moment_id"] for m in ranked]
 761 |      log(f"  SPOTLIGHT: {len(cleared)} cleared step A, {len(cut)} cuttable, {len(openers)} open cold, {len(strong)} "
 762 | -        f"rate >= {HOOK_MIN} as an opener, {len(clean)} clean, {len(both)} two families, {len(fine)} ALONE >= "
 763 | +        f"pass the calibrated hook bar as an opener, {len(clean)} clean, {len(both)} two families, {len(fine)} ALONE >= "
 764 |          f"{ALONE_MIN:g}, {len(ranked)} from a conversation ({time.time() - t0:.0f} s)")
 765 |      exc_cache = {}
 766 |      for m in ranked[:finalists]:
 767 | @@ -1020,6 +1023,7 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 768 |          if pk is not None:
 769 |              pk["seconds"] = round(time.time() - t0, 1)
 770 |              out["package"] = pk
 771 | +            pk["hook_bar"] = P.hook_bar_mark()          # RULING 115 (2): sealed on the calibrated bar, said so
 772 |              rec[mid]["out"] = "PACKAGE"
 773 |              break
 774 |          stop(mid, why_p)
 775 | diff --git a/tests/package/conftest.py b/tests/package/conftest.py
 776 | new file mode 100644
 777 | index 0000000..0e67912
 778 | --- /dev/null
 779 | +++ b/tests/package/conftest.py
 780 | @@ -0,0 +1,32 @@
 781 | +"""RULING 115: THE RIGS' HOOK BAR. Every test under tests/package judges hooks on a calibrated bar whose floors are
 782 | +PINNED here: the floors ruling 115's calibration measured at 13:07 ET Nov 15 (scroll 3, alone 4, setup 3), for the
 783 | +rigs' own rater name, "xai:grok". A daily re-calibration may move production's floors; it never moves a rig's
 784 | +verdict. The fixture patches only package._live_bar: hook_bar's own functions, which tests/package/test_hook_bar.py
 785 | +tests on files of its own (and that the live file's floors are derived from their source), are never touched. A test
 786 | +class that needs production's calibration file sets `real_hook_bar = True`."""
 787 | +import os
 788 | +import sys
 789 | +
 790 | +import pytest
 791 | +
 792 | +HERE = os.path.dirname(os.path.abspath(__file__))
 793 | +sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "pipeline"))
 794 | +import package as PK  # noqa: E402
 795 | +
 796 | +RIG_RATER = "xai:grok"
 797 | +RIG_FLOORS = {"scroll": 3, "alone": 4, "setup": 3}
 798 | +
 799 | +
 800 | +def rig_bar():
 801 | +    return {"floors": dict(RIG_FLOORS), "sha256": "t" * 64, "rater": RIG_RATER,
 802 | +            "question_version": PK.HOOK_VERSION, "seed": PK.HOOK_SEED, "measured_at": "2026-11-15T18:07:52+00:00"}
 803 | +
 804 | +
 805 | +@pytest.fixture(autouse=True)
 806 | +def _rig_hook_bar(request, monkeypatch):
 807 | +    if getattr(request.cls, "real_hook_bar", False):
 808 | +        yield
 809 | +        return
 810 | +    bar = rig_bar()
 811 | +    monkeypatch.setattr(PK, "_live_bar", lambda: (bar, None))
 812 | +    yield
 813 | diff --git a/tests/package/hook112.py b/tests/package/hook112.py
 814 | index 61686b4..6d1a84a 100644
 815 | --- a/tests/package/hook112.py
 816 | +++ b/tests/package/hook112.py
 817 | @@ -388,11 +388,16 @@ def ref_moments(refs=REFS):
 818 |      return out
 819 |  
 820 |  
 821 | -def heimdall_hook_chain(router):
 822 | -    """Ruling 88's hook list as production reads it, with every non-Heimdall back-end removed (the order: Heimdall
 823 | +RULING_96_HOOK = ("heimdall:qwen/qwen3.8-27b", "heimdall:z-ai/glm-5.3-flash", "heimdall:deepseek/deepseek-v4.1-flash")
 824 | +#   ruling 96's hook list without Grok: the Heimdall list ruling 112 measured. Production's hook list is Grok ALONE since
 825 | +#   ruling 115 (the calibrated rater), so the driver names its Heimdall list instead of reading production's.
 826 | +
 827 | +
 828 | +def heimdall_hook_chain(router, names=None):
 829 | +    """`names` (default: the router's own hook list) with every non-Heimdall back-end removed, in order (Heimdall
 830 |      only). Refused when none is left."""
 831 | -    chain = [n for n in router.chain("coherence_verdict", "hook")   # a Heimdall back-end's vendor is "heimdall/<family>"
 832 | -             if str(getattr(router.backends.get(n), "vendor", "")).split("/")[0] == "heimdall"]
 833 | +    chain = [n for n in (names or router.chain("coherence_verdict", "hook"))   # a Heimdall back-end's vendor is
 834 | +             if str(getattr(router.backends.get(n), "vendor", "")).split("/")[0] == "heimdall"]   # "heimdall/<family>"
 835 |      if not chain:
 836 |          raise RuntimeError("refused: ruling 88's hook list has no Heimdall back-end")
 837 |      return chain
 838 | @@ -405,13 +410,15 @@ def registry(path=os.path.join(REPO, "pipeline", "channels.json")):
 839 |          return json.load(f)
 840 |  
 841 |  
 842 | -def build_router(spend_path=SPEND, record_dir=None):
 843 | +def build_router(spend_path=SPEND, record_dir=None, hook_chain=RULING_96_HOOK):
 844 | +    """The driver's router: Heimdall only for the hook job (`hook_chain`, filtered to Heimdall), ruling 48's ledger
 845 | +    on reported spend under LIMIT_USD."""
 846 |      import deadline_table as DT
 847 |      import providers as P
 848 |      import replay85 as R
 849 |      r = P.Router(env_path=R.ENV, record_dir=record_dir, spend_path=spend_path, limit_usd=LIMIT_USD,
 850 |                   limit_basis="reported", routing="heimdall_first", deadlines=DT.load(DT.STATE, None))
 851 | -    r.chains["coherence_verdict:hook"] = heimdall_hook_chain(r)
 852 | +    r.chains["coherence_verdict:hook"] = heimdall_hook_chain(r, list(hook_chain))
 853 |      return r
 854 |  
 855 |  
 856 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
 857 | index 2f200ba..881884a 100644
 858 | --- a/tests/package/proof_ledger.py
 859 | +++ b/tests/package/proof_ledger.py
 860 | @@ -70,6 +70,7 @@ import shadow86 as SH  # noqa: E402
 861 |  import ledger_build as LB  # noqa: E402
 862 |  import moments as M  # noqa: E402
 863 |  import package as PK  # noqa: E402
 864 | +import hook_bar as HB  # noqa: E402
 865 |  import package_pin  # noqa: E402
 866 |  import proof_ly as PL  # noqa: E402
 867 |  import proof_saved_runs as PS  # noqa: E402
 868 | @@ -155,6 +156,19 @@ def open_work(res, sp):
 869 |      return held + no_verdict + int(vis.get("unmeasured") or 0)
 870 |  
 871 |  
 872 | +HOOK_SHADOW = {"coherence_verdict:hook": "heimdall:qwen/qwen3.8-27b"}   # RULING 115: recorded, never deciding
 873 | +
 874 | +
 875 | +def build_shadow(routing, rt, streak):
 876 | +    """The build's shadow back-ends: RULING 86, Grok (routing.shadow) on the first heimdall_first pins, until
 877 | +    `shadow_until_clean_pins` clean pins in a row (`streak`: a callable, read only under heimdall_first); RULING 115,
 878 | +    qwen on every hook, in every build. Recorded, never deciding."""
 879 | +    shadow = None
 880 | +    if routing == "heimdall_first" and streak() < int(rt.get("shadow_until_clean_pins") or 3):
 881 | +        shadow = rt.get("shadow") or None
 882 | +    return dict(shadow or {}, **HOOK_SHADOW)
 883 | +
 884 | +
 885 |  def nothing_new(proof_dir, out_dir, fp):
 886 |      """RULING 107 (1): the newest earlier FINISHED build (its FINGERPRINT.json) when its fingerprint is this build's and
 887 |      it left nothing undone; else None. A build that stopped early writes none, and neither does a --from-candidate
 888 | @@ -431,12 +445,13 @@ def main(argv=None):
 889 |          return 0
 890 |      rt = json.load(open(P.CONFIG)).get("routing") or {}
 891 |      routing = a.routing or rt.get("mode") or "today"
 892 | -    shadow = None                                # RULING 86: Grok in shadow on the first heimdall_first pins
 893 | -    if routing == "heimdall_first" and SH.clean_streak() < int(rt.get("shadow_until_clean_pins") or 3):
 894 | -        shadow = rt.get("shadow") or None
 895 | +    shadow = build_shadow(routing, rt, SH.clean_streak)   # RULING 86 (Grok) / RULING 115 (qwen on every hook)
 896 |      router = build_router(routing, shadow, os.path.join(out_dir, "SHADOW86.jsonl"))
 897 |      say(f"  routing (ruling 85): {router.routing}; now {router.mode()} (ruling 87: the shared Heimdall health)"
 898 | -        + (f"; SHADOW (ruling 86): {shadow}" if shadow else ""))
 899 | +        + (f"; SHADOW (ruling 86 / 115): {shadow}" if shadow else ""))
 900 | +    live, live_why = PK.hook_live_bar()          # RULING 115: the bar in every build line, its floors and its sha
 901 | +    say(f"  RULING 115: {HB.text(live)}; the hook list {router.chain('coherence_verdict', 'hook')}"
 902 | +        + (f" [{live_why}]" if live_why else ""))
 903 |      say(f"  RULING 100 (deadlines follow the model, table of {(router.deadlines or {}).get('computed_at')}): "
 904 |          f"{DT.text(router.deadlines, applies=applied(router)) or 'no row applies: each gateway keeps its number'}")
 905 |      spent0 = router.spent()                      # ruling 48: the running total, vendor-reported (+ estimates where none)
 906 | diff --git a/tests/package/test_hook112.py b/tests/package/test_hook112.py
 907 | index 57161c8..3a5a376 100644
 908 | --- a/tests/package/test_hook112.py
 909 | +++ b/tests/package/test_hook112.py
 910 | @@ -215,7 +215,10 @@ class TestTheCalibration(unittest.TestCase):
 911 |          chain = r.chain("coherence_verdict", "hook")
 912 |          self.assertTrue(chain and all(r.backends[n].vendor.split("/")[0] == "heimdall" for n in chain), chain)
 913 |          self.assertNotIn("xai:grok-4.20-0309-reasoning", chain)
 914 | -        self.assertEqual(chain[0], "heimdall:qwen/qwen3.8-27b")       # ruling 88's order, Grok removed
 915 | +        self.assertEqual(chain[0], "heimdall:qwen/qwen3.8-27b")       # ruling 96's order, Grok removed
 916 | +        with tempfile.TemporaryDirectory() as d:                      # production's list (Grok alone, ruling 115)
 917 | +            with self.assertRaises(RuntimeError):                     # has no Heimdall back-end: refused, never Grok
 918 | +                H.build_router(spend_path=os.path.join(d, "SPEND.json"), hook_chain=("xai:grok-4.20-0309-reasoning",))
 919 |          self.assertEqual((r.limit_usd, r.limit_basis), (H.LIMIT_USD, "reported"))
 920 |  
 921 |      def test_heimdall_only_and_refused_without_one(self):
 922 | diff --git a/tests/package/test_hook_bar.py b/tests/package/test_hook_bar.py
 923 | new file mode 100644
 924 | index 0000000..8ab44e2
 925 | --- /dev/null
 926 | +++ b/tests/package/test_hook_bar.py
 927 | @@ -0,0 +1,255 @@
 928 | +#!/usr/bin/env python3
 929 | +"""RULING 115 (orchestrator 13:24 ET Nov 15): THE CALIBRATED HOOK BAR (pipeline/hook_bar.py). A hook passes when each of
 930 | +scroll / alone / setup is at least the LOWEST value that part takes across PBX's approved hooks under the same asking
 931 | +(ALONE, production's seed, Grok); no floor under 3; one sealed calibration file, valid for its rater, question version,
 932 | +seed and asking, for 24 h; a package sealed on it says so; PBX's verdicts on such packages are appended as examples.
 933 | +The live file is checked against its source and against production's hook job."""
 934 | +import copy
 935 | +import json
 936 | +import os
 937 | +import sys
 938 | +import tempfile
 939 | +import unittest
 940 | +from datetime import datetime, timedelta, timezone
 941 | +
 942 | +HERE = os.path.dirname(os.path.abspath(__file__))
 943 | +REPO = os.path.dirname(os.path.dirname(HERE))
 944 | +for _p in ("pipeline", "tests/package"):
 945 | +    sys.path.insert(0, os.path.join(REPO, _p))
 946 | +import hook_bar as HB  # noqa: E402
 947 | +import package as PK  # noqa: E402
 948 | +import package_pin as PP  # noqa: E402
 949 | +
 950 | +AT = datetime(2026, 11, 15, 18, 7, 52, tzinfo=timezone.utc)
 951 | +G = "xai:grok-4.20-0309-reasoning"
 952 | +Q = "heimdall:qwen/qwen3.8-27b"
 953 | +
 954 | +
 955 | +def approved(*parts):
 956 | +    return [{"ref": f"ref-{i}", "scroll": s, "alone": a, "setup": u, "backend": G} for i, (s, a, u) in enumerate(parts)]
 957 | +
 958 | +
 959 | +def cal(parts=((3, 4, 3), (3, 5, 4), (4, 5, 4)), **kw):
 960 | +    ap = approved(*parts)
 961 | +    fl, low = HB.floors_from(ap)
 962 | +    return dict({"rater": G, "asking": "alone", "seed": 7, "question_version": "qv", "measured_at": AT.isoformat(),
 963 | +                 "approved": ap, "floors": fl, "floors_below_3": low, "examples": []}, **kw)
 964 | +
 965 | +
 966 | +class TestFloors(unittest.TestCase):
 967 | +    def test_each_floor_is_its_parts_lowest_value_across_the_approved_hooks(self):
 968 | +        self.assertEqual(HB.floors_from(approved((3, 4, 3), (3, 5, 4), (4, 5, 4))),
 969 | +                         ({"scroll": 3, "alone": 4, "setup": 3}, []))
 970 | +        self.assertEqual(HB.floors_from(approved((5, 5, 5), (4, 5, 5))), ({"scroll": 4, "alone": 5, "setup": 5}, []))
 971 | +
 972 | +    def test_a_floor_under_3_stops_at_3_and_is_told(self):
 973 | +        fl, low = HB.floors_from(approved((2, 5, 4), (3, 1, 4)))
 974 | +        self.assertEqual(fl, {"scroll": 3, "alone": 3, "setup": 4})
 975 | +        self.assertEqual(low, ["scroll 2 (stopped at 3)", "alone 1 (stopped at 3)"])
 976 | +
 977 | +    def test_a_part_missing_or_not_an_integer_measures_nothing(self):
 978 | +        for bad in ([{"scroll": 3, "alone": 4}], [{"scroll": 3, "alone": 4, "setup": 3.0}],
 979 | +                    [{"scroll": True, "alone": 4, "setup": 3}], []):
 980 | +            with self.assertRaises(ValueError):
 981 | +                HB.floors_from(bad)
 982 | +
 983 | +
 984 | +class TestTheFile(unittest.TestCase):
 985 | +    def setUp(self):
 986 | +        self.d = tempfile.TemporaryDirectory()
 987 | +        self.path = os.path.join(self.d.name, "hook_calibration.json")
 988 | +
 989 | +    def tearDown(self):
 990 | +        self.d.cleanup()
 991 | +
 992 | +    def bar(self, now=AT + timedelta(hours=1), **kw):
 993 | +        a = dict(dict(rater=None, question_version="qv", seed=7), **kw)
 994 | +        return HB.bar(a["rater"], a["question_version"], a["seed"], now=now, path=self.path)
 995 | +
 996 | +    def test_written_sealed_and_read_back_as_the_live_bar(self):
 997 | +        c = HB.write(cal(), self.path)
 998 | +        self.assertEqual(c["sha256"], HB.body_sha(c))
 999 | +        live, why = self.bar()
1000 | +        self.assertIsNone(why)
1001 | +        self.assertEqual((live["floors"], live["rater"], live["sha256"]),
1002 | +                         ({"scroll": 3, "alone": 4, "setup": 3}, G, c["sha256"]))
1003 | +        self.assertIn(f"scroll >= 3, alone >= 4, setup >= 3, on {G} asked alone at seed 7 (calibration "
1004 | +                      f"{c['sha256'][:12]})", HB.text(live))
1005 | +
1006 | +    def test_a_hand_edit_breaks_the_seal_and_no_hook_passes(self):
1007 | +        HB.write(cal(), self.path)
1008 | +        with open(self.path) as f:
1009 | +            c = json.load(f)
1010 | +        c["floors"]["alone"] = 3                                          # edited, not re-sealed
1011 | +        with open(self.path, "w") as f:
1012 | +            json.dump(c, f)
1013 | +        live, why = self.bar()
1014 | +        self.assertIsNone(live)
1015 | +        self.assertIn("sha256 does not match", why)
1016 | +        self.assertEqual(HB.passes({"scroll": 5, "alone": 5, "setup": 5, "backend": G}, live),
1017 | +                         (False, "no valid hook calibration"))
1018 | +        self.assertEqual(HB.text(live), "no valid hook calibration: no hook passes")
1019 | +
1020 | +    def test_missing_or_unreadable_is_no_bar(self):
1021 | +        live, why = self.bar()
1022 | +        self.assertIsNone(live)
1023 | +        self.assertIn("cannot be read", why)
1024 | +        with open(self.path, "w") as f:
1025 | +            f.write("{not json")
1026 | +        self.assertIsNone(self.bar()[0])
1027 | +
1028 | +    def test_valid_only_for_its_question_version_seed_asking_and_rater(self):
1029 | +        HB.write(cal(), self.path)
1030 | +        self.assertIsNotNone(self.bar(rater=G)[0])
1031 | +        for kw in ({"question_version": "another"}, {"seed": 8}, {"rater": Q}):
1032 | +            live, why = self.bar(**kw)
1033 | +            self.assertIsNone(live, kw)
1034 | +            self.assertIn("no hook passes until it is re-run", why)
1035 | +        HB.write(cal(asking="batched"), self.path)                         # the batch moved single ratings
1036 | +        self.assertIsNone(self.bar()[0])
1037 | +
1038 | +    def test_once_a_day_a_stale_calibration_passes_nothing(self):
1039 | +        HB.write(cal(), self.path)
1040 | +        self.assertIsNotNone(self.bar(now=AT + timedelta(hours=23, minutes=59))[0])
1041 | +        live, why = self.bar(now=AT + timedelta(hours=24, minutes=1))
1042 | +        self.assertIsNone(live)
1043 | +        self.assertIn("over 24 h old", why)
1044 | +
1045 | +    def test_a_future_or_naive_measured_at_passes_nothing(self):
1046 | +        """Audit 20261115_1410 C1 (qwen): a calibration "measured" ahead of now would stretch its 24 h; a time with no
1047 | +        timezone cannot be compared with now (it must never raise into a build)."""
1048 | +        HB.write(cal(), self.path)
1049 | +        self.assertIsNotNone(self.bar(now=AT - timedelta(minutes=4))[0])  # clock skew inside 5 min
1050 | +        live, why = self.bar(now=AT - timedelta(minutes=6))
1051 | +        self.assertIsNone(live)
1052 | +        self.assertIn("is in the future", why)
1053 | +        HB.write(cal(measured_at="2026-11-15T18:07:52"), self.path)
1054 | +        live, why = self.bar()
1055 | +        self.assertIsNone(live)
1056 | +        self.assertIn("no timezone", why)
1057 | +
1058 | +    def test_a_floor_under_3_in_the_file_is_refused(self):
1059 | +        HB.write(cal(floors={"scroll": 2, "alone": 4, "setup": 3}), self.path)
1060 | +        live, why = self.bar()
1061 | +        self.assertIsNone(live)
1062 | +        self.assertIn("a floor under 3", why)
1063 | +
1064 | +
1065 | +class TestPasses(unittest.TestCase):
1066 | +    LIVE = {"floors": {"scroll": 3, "alone": 4, "setup": 3}, "rater": G, "sha256": "s" * 64, "seed": 7}
1067 | +
1068 | +    def ok(self, s, a, u, b=G):
1069 | +        return HB.passes({"scroll": s, "alone": a, "setup": u, "backend": b}, self.LIVE)
1070 | +
1071 | +    def test_every_part_at_least_its_floor_by_the_calibrated_rater(self):
1072 | +        self.assertEqual(self.ok(3, 4, 3), (True, None))                  # at every floor
1073 | +        self.assertEqual(self.ok(5, 5, 5), (True, None))
1074 | +        self.assertEqual(self.ok(2, 4, 3), (False, "scroll 2 < 3"))
1075 | +        self.assertEqual(self.ok(3, 3, 3), (False, "alone 3 < 4"))
1076 | +        self.assertEqual(self.ok(3, 4, 2), (False, "setup 2 < 3"))
1077 | +        self.assertEqual(self.ok(2, 3, 2), (False, "scroll 2 < 3; alone 3 < 4; setup 2 < 3"))
1078 | +        self.assertEqual(self.ok(5, 5, 5, Q), (False, f"rated by {Q}, but the bar is calibrated on {G}"))
1079 | +        self.assertFalse(HB.passes({"scroll": 5, "alone": 5, "backend": G}, self.LIVE)[0])           # a part missing
1080 | +        self.assertFalse(HB.passes({"scroll": 5, "alone": 5, "setup": True, "backend": G}, self.LIVE)[0])
1081 | +
1082 | +
1083 | +class TestExamples(unittest.TestCase):
1084 | +    """RULING 115 (2): PBX's approve or reject of a package sealed on the bar is appended as an example."""
1085 | +
1086 | +    def test_approved_and_rejected_with_his_reason_appended_sealed_and_the_floors_unchanged(self):
1087 | +        with tempfile.TemporaryDirectory() as d:
1088 | +            path = os.path.join(d, "c.json")
1089 | +            HB.write(cal(), path)
1090 | +            hook = {"moment_id": "m1", "text": "Bitcoin t.", "channel": "A", "scroll": 3, "alone": 4, "setup": 3,
1091 | +                    "backend": G, "extra": 1}
1092 | +            HB.add_example("story-1", "approved", hook, path=path, now=AT)
1093 | +            c = HB.add_example("story-2", "rejected", hook, reason="the opener is mid-sentence", path=path, now=AT)
1094 | +            self.assertEqual([(e["story_id"], e["verdict"], e["reason"]) for e in c["examples"]],
1095 | +                             [("story-1", "approved", None), ("story-2", "rejected", "the opener is mid-sentence")])
1096 | +            self.assertNotIn("extra", c["examples"][0]["hook"])
1097 | +            self.assertEqual(HB.load(path)[0], c)                          # sealed
1098 | +            self.assertEqual(c["floors"], cal()["floors"])                  # a new floor comes from the next run
1099 | +            for verdict, reason in (("rejected", None), ("maybe", "r")):    # a rejection carries his reason
1100 | +                with self.assertRaises(ValueError):
1101 | +                    HB.add_example("story-3", verdict, hook, reason=reason, path=path)
1102 | +            self.assertEqual(len(HB.load(path)[0]["examples"]), 2)
1103 | +
1104 | +
1105 | +class TestTheMark(unittest.TestCase):
1106 | +    """RULING 115 (2): a package sealed on the bar says so in its record and in its pin, in one plain line, outside
1107 | +    the seal (the integrator prints it in the Telegram note)."""
1108 | +
1109 | +    def test_the_pin_carries_the_line_outside_the_seal(self):
1110 | +        import test_angles as TA
1111 | +        base = TA.TestPinAndTruth.pk(None)
1112 | +        plain = PP.to_pin(copy.deepcopy(base), "r")
1113 | +        self.assertNotIn("hook_bar", plain["moments_package"])
1114 | +        pin = PP.to_pin(dict(copy.deepcopy(base), hook_bar=PK.hook_bar_mark()), "r")
1115 | +        mp = pin["moments_package"]
1116 | +        self.assertEqual((mp["hook_bar"]["note"], mp["hook_bar"]["floors"], mp["hook_bar"]["ruling"]),
1117 | +                         ("hook passed on the calibrated bar", {"scroll": 3, "alone": 4, "setup": 3}, "115"))
1118 | +        self.assertEqual(mp["package_sha256"], plain["moments_package"]["package_sha256"])   # outside the seal
1119 | +        self.assertEqual(PP.pin_seal(pin), mp["package_sha256"])
1120 | +
1121 | +
1122 | +class TestTheLiveCache(unittest.TestCase):
1123 | +    """package._live_bar: the bar is read once per state of the file and per minute (so a calibration that ages past
1124 | +    its 24 h mid-build stops passing hooks within the minute), and again as soon as the file changes."""
1125 | +    real_hook_bar = True
1126 | +
1127 | +    def test_read_once_a_minute_and_again_when_the_file_changes(self):
1128 | +        import types
1129 | +        from unittest import mock
1130 | +        with tempfile.TemporaryDirectory() as d:
1131 | +            path = os.path.join(d, "c.json")
1132 | +            now = datetime.now(timezone.utc)
1133 | +            HB.write(cal(question_version=PK.HOOK_VERSION, seed=PK.HOOK_SEED, measured_at=now.isoformat()), path)
1134 | +            t, reads, real = [1000.0 * 60], [], PK.hook_live_bar
1135 | +            with mock.patch.object(HB, "PATH", path), mock.patch.object(PK, "time", types.SimpleNamespace(
1136 | +                    time=lambda: t[0])), mock.patch.object(PK, "hook_live_bar", lambda: (reads.append(1), real())[1]):
1137 | +                PK._LIVE.clear()
1138 | +                live, why = PK._live_bar()
1139 | +                self.assertEqual((live["floors"], why, len(reads)), ({"scroll": 3, "alone": 4, "setup": 3}, None, 1))
1140 | +                PK._live_bar()
1141 | +                self.assertEqual(len(reads), 1)                               # the same minute, the same file
1142 | +                t[0] += 61
1143 | +                PK._live_bar()
1144 | +                self.assertEqual(len(reads), 2)                               # a new minute: read again
1145 | +                HB.write(cal(question_version="another", measured_at=now.isoformat()), path)
1146 | +                os.utime(path, ns=(1, 1))                                      # the file changed (its mtime moved)
1147 | +                live, why = PK._live_bar()
1148 | +                self.assertEqual((live, len(reads)), (None, 3))               # read at once: no hook passes
1149 | +                self.assertIn("no hook passes until it is re-run", why)
1150 | +            PK._LIVE.clear()
1151 | +
1152 | +
1153 | +class TestTheLiveCalibration(unittest.TestCase):
1154 | +    """The calibration production reads (pipeline/hook_calibration.json): its floors are derived from their source
1155 | +    (tests/package/proof/hook113/ALONE_TEST.json: Grok asked alone at seed 7; the two out-of-contract first answers
1156 | +    asked once more), and it is for production's question version, seed and hook list."""
1157 | +    real_hook_bar = True
1158 | +
1159 | +    def test_its_floors_are_its_sources_lowest_parts(self):
1160 | +        c, why = HB.load()
1161 | +        self.assertIsNone(why)
1162 | +        with open(os.path.join(REPO, "tests", "package", "proof", "hook113", "ALONE_TEST.json")) as f:
1163 | +            src = json.load(f)
1164 | +        grok = dict(src["models"][c["rater"]], **src["retries"])          # a retry answers for an out-of-contract ask
1165 | +        self.assertEqual(sorted(a["ref"] for a in c["approved"]), sorted(grok))
1166 | +        for a in c["approved"]:
1167 | +            self.assertEqual({p: a[p] for p in HB.PARTS}, {p: grok[a["ref"]][p] for p in HB.PARTS}, a["ref"])
1168 | +            self.assertEqual(grok[a["ref"]]["backend"], c["rater"])
1169 | +        self.assertEqual(HB.floors_from(c["approved"]), (c["floors"], c["floors_below_3"]))
1170 | +        self.assertEqual((c["seed"], c["asking"]), (src["seed"], "alone"))
1171 | +
1172 | +    def test_it_is_for_productions_question_seed_and_hook_list(self):
1173 | +        import providers as P
1174 | +        c, _ = HB.load()
1175 | +        self.assertEqual((c["question_version"], c["seed"]), (PK.HOOK_VERSION, PK.HOOK_SEED))
1176 | +        for routing in P.ROUTINGS:
1177 | +            r = P.Router(env_path="/nonexistent", routing=routing)
1178 | +            self.assertEqual(r.chain("coherence_verdict", "hook"), [c["rater"]], routing)
1179 | +
1180 | +
1181 | +if __name__ == "__main__":
1182 | +    unittest.main()
1183 | diff --git a/tests/package/test_ledger_build.py b/tests/package/test_ledger_build.py
1184 | index 5a109eb..2a117a7 100644
1185 | --- a/tests/package/test_ledger_build.py
1186 | +++ b/tests/package/test_ledger_build.py
1187 | @@ -903,6 +903,24 @@ class TestRuling85NoXai(unittest.TestCase):
1188 |                  return name
1189 |          return None
1190 |  
1191 | +    def test_ruling_115_qwen_shadows_every_hook_in_every_build(self):
1192 | +        """RULING 115: qwen answers every hook in shadow (recorded, never deciding), with ruling 86's Grok shadow on the
1193 | +        first heimdall_first pins and without it after; the streak is read only under heimdall_first."""
1194 | +        import proof_ledger as PLG
1195 | +        X, Q = "xai:grok-4.20-0309-reasoning", "heimdall:qwen/qwen3.8-27b"
1196 | +        rt = {"shadow": {"*": X}, "shadow_until_clean_pins": 3}
1197 | +        hook = {"coherence_verdict:hook": Q}
1198 | +        self.assertEqual(PLG.build_shadow("heimdall_first", rt, lambda: 0), {"*": X, **hook})
1199 | +        self.assertEqual(PLG.build_shadow("heimdall_first", rt, lambda: 3), hook)
1200 | +
1201 | +        def never():
1202 | +            raise AssertionError("the streak is read under heimdall_first only")
1203 | +        self.assertEqual(PLG.build_shadow("today", rt, never), hook)
1204 | +        r = self.pl().P.Router(env_path="/nonexistent", routing="heimdall_first",
1205 | +                               shadow=PLG.build_shadow("heimdall_first", rt, lambda: 0))
1206 | +        self.assertEqual((r._shadow_of("coherence_verdict", "hook"), r._shadow_of("coherence_verdict", "coherence")),
1207 | +                         (Q, X))                                       # the router reads them as ruled
1208 | +
1209 |      def test_ruling_96s_lists_and_xai_answering_nothing(self):
1210 |          """RULING 96 (01:40 ET Nov 14), final until re-measured, on ruling 88's structure, as the orchestrator's 06:12
1211 |          rulings amend it: (1) glm last for coherence, no Heimdall model for clips-alone; (2) qwen struck from step A."""
1212 | @@ -918,12 +936,15 @@ class TestRuling85NoXai(unittest.TestCase):
1213 |          #   confirms; RULING 102 (13:02 Nov 14): then deepseek, glm, Gemini, the local judge (ruling 87's last resort)
1214 |          self.assertEqual(ch["context_verdict"], [G, DS, X])                        # the role's default: no qwen either
1215 |          self.assertNotIn(Q, [b for k, v in ch.items() if k.startswith("context_verdict:step_a") for b in v])
1216 | -        self.assertEqual(ch["coherence_verdict:hook"], [Q, G, DS, X])              # 88 (b) / 96: the hook moved
1217 | +        self.assertEqual(ch["coherence_verdict:hook"], [X])                        # RULING 115 (amends 88 (b) / 96 for
1218 | +        #   the hook): Grok ALONE, the rater the calibrated floors are measured on (qwen in shadow, never deciding)
1219 |          self.assertEqual(ch["context_verdict:step_c"], [X, G, DS])                 # (b) / (e): no qwen
1220 |          self.assertEqual(ch["coherence_verdict:coherence"], [X, DS, G])           # 06:12 (1): glm the LAST fallback
1221 |          self.assertEqual(ch["coherence_verdict:clips_alone"], [X, GEM])           # 06:12 (1): no Heimdall model
1222 |          today = PL.chains("today")                                                 # (d) and (e) hold today too
1223 |          self.assertEqual((today["coherence_verdict:coherence"], today["context_verdict:step_c"]), ([X, DS], [X, DS, G]))
1224 | +        self.assertEqual((today["coherence_verdict:hook"], PL.plan_b_chains()["coherence_verdict:hook"]), ([X], [X]))
1225 | +        #   RULING 115: the hook is Grok's alone in every routing (no uncalibrated rating is ever cached as a hook's)
1226 |          r = PL.P.Router(env_path="/nonexistent", routing="heimdall_first", chains=ch)
1227 |          for n in [n for n in r.backends if n.startswith("xai")]:
1228 |              r.down[n] = "xAI answers nothing (the test)"
1229 | @@ -934,7 +955,8 @@ class TestRuling85NoXai(unittest.TestCase):
1230 |              ("coherence_verdict", "clips_alone"), ("coherence_verdict", "coherence"))}
1231 |          self.assertEqual(got, {("fidelity_verdict", None): G, ("exclusion_verdict", None): G,
1232 |                                 ("speaker_verdict", None): G, ("viewer_takeaway", None): G,
1233 | -                               ("context_verdict", "step_c"): G, ("coherence_verdict", "hook"): Q,
1234 | +                               ("context_verdict", "step_c"): G, ("coherence_verdict", "hook"): None,   # ruling 115:
1235 | +                               #   no other model decides a hook while Grok is out (no rating = no hook, law L-m)
1236 |                                 ("coherence_verdict", "clips_alone"): GEM,          # Plan B's other outside family
1237 |                                 ("coherence_verdict", "coherence"): G})            # the gap is closed: glm, last
1238 |          r.down[GEM] = "Gemini answers nothing (the test)"
1239 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
1240 | index 5e7aa2f..1db0c92 100644
1241 | --- a/tests/package/test_medley.py
1242 | +++ b/tests/package/test_medley.py
1243 | @@ -156,8 +156,8 @@ class TestMedleyLineup(unittest.TestCase):
1244 |  
1245 |  
1246 |  class TestClipsAloneVerdict(unittest.TestCase):
1247 | -    SEGS = [dict(pm("h", "A", 12.0), hook_rating={"scroll": 5, "alone": 4, "setup": 2}), pm("x", "B", 14.0),
1248 | -            pm("y", "C", 13.0)]
1249 | +    SEGS = [dict(pm("h", "A", 12.0), hook_rating={"scroll": 5, "alone": 4, "setup": 3, "backend": "xai:grok"}),
1250 | +            pm("x", "B", 14.0), pm("y", "C", 13.0)]   # ruling 115: rated by the rigs' calibrated rater (conftest)
1251 |      LABS = ["hook", "clip_01", "clip_02"]
1252 |  
1253 |      def run_it(self, reply):
1254 | @@ -190,7 +190,10 @@ class TestClipsAloneVerdict(unittest.TestCase):
1255 |          self.assertFalse(self.run_it(reply(self.LABS, line="Bitcoin."))[0])
1256 |          self.assertFalse(self.run_it(reply(self.LABS, ratings={"clip_02": 3}))[0])
1257 |  
1258 | -    def test_ruling_61_the_hook_is_rated_once_its_cached_own_job_rating_stands(self):
1259 | +    def test_ruling_61_115_the_hook_is_rated_once_and_passes_by_its_calibrated_bar(self):
1260 | +        """Ruling 61: the hook is not rated in the line-up's verdict; its cached own-job rating stands. Ruling 115:
1261 | +        it passes when EACH part is at least its calibrated floor (the rigs': scroll 3, alone 4, setup 3), rated by
1262 | +        the calibrated rater; its slot is judged by that bar, never by COHERENCE_MIN; the clips keep their bar."""
1263 |          prompts = []
1264 |          r = Canned(coherence_verdict=[reply(self.LABS)])
1265 |          call = r.call
1266 | @@ -198,15 +201,25 @@ class TestClipsAloneVerdict(unittest.TestCase):
1267 |          ok, v = PK.medley(r, self.SEGS, E.Context(NOW, REG), {"heimdall"}, writer_family={"deepseek"})
1268 |          self.assertTrue(ok)
1269 |          self.assertEqual(v["clips"], {"hook": 4, "clip_01": 5, "clip_02": 5})   # min(scroll 5, alone 4), cached
1270 | -        self.assertEqual((v["hook_own"]["scroll"], v["hook_own"]["alone"], v["hook_own"]["rating"]), (5, 4, 4))
1271 | +        self.assertEqual(tuple(v["hook_own"][k] for k in ("scroll", "alone", "setup", "rating", "passes")),
1272 | +                         (5, 4, 3, 4, True))
1273 |          self.assertNotIn(PK.HOOK_QUESTION, prompts[0])                         # never re-asked per line-up
1274 |          self.assertIn("NOT rated here", prompts[0])
1275 |          self.assertIn('"hook -> clip_01"', prompts[0])                         # 'sets up': the hook's own join
1276 |          self.assertNotIn('"hook": 1', prompts[0])
1277 |          self.assertIn('"clip_01": 1, "clip_02": 1', prompts[0])
1278 | -        low = [dict(self.SEGS[0], hook_rating={"scroll": 3, "alone": 5, "setup": 5}), *self.SEGS[1:]]
1279 | -        ok, v = PK.medley(Canned(coherence_verdict=[reply(self.LABS)]), low, E.Context(NOW, REG), set())
1280 | -        self.assertFalse(ok)                                                   # its cached rating is under the bar
1281 | +        run = lambda hr: PK.medley(Canned(coherence_verdict=[reply(self.LABS)]),
1282 | +                                   [dict(self.SEGS[0], hook_rating=hr), *self.SEGS[1:]], E.Context(NOW, REG), set())
1283 | +        ok, v = run({"scroll": 3, "alone": 4, "setup": 3, "backend": "xai:grok"})   # every part AT its floor
1284 | +        self.assertEqual((ok, v["clips"]["hook"], v["hook_own"]["passes"]), (True, 3, True))   # 3 < COHERENCE_MIN
1285 | +        for hr in ({"scroll": 2, "alone": 5, "setup": 5, "backend": "xai:grok"},   # one part under its floor
1286 | +                   {"scroll": 5, "alone": 3, "setup": 5, "backend": "xai:grok"},
1287 | +                   {"scroll": 5, "alone": 5, "setup": 2, "backend": "xai:grok"},   # setup counts (ruling 115)
1288 | +                   {"scroll": 5, "alone": 5, "setup": 5, "backend": "heimdall:qwen/qwen3.8-27b"},   # not the rater
1289 | +                   {"scroll": 5, "alone": 5, "backend": "xai:grok"}):              # a part missing: fail closed
1290 | +            ok, v = run(hr)
1291 | +            self.assertFalse(ok, hr)
1292 | +            self.assertIs(v["hook_own"].get("passes", False), False)
1293 |          ok, v = PK.medley(Canned(coherence_verdict=[reply(self.LABS)]), [pm("h", "A", 12.0), *self.SEGS[1:]],
1294 |                            E.Context(NOW, REG), set())
1295 |          self.assertFalse(ok)                                                   # no cached rating: fail closed
1296 | @@ -238,7 +251,7 @@ class TestCoherenceHookRatedOnce(unittest.TestCase):
1297 |             "segments": [{"label": "hook", "channel": "A", "text": "Bitcoin a."},
1298 |                          {"label": "clip_01", "channel": "B", "text": "Bitcoin b."},
1299 |                          {"label": "clip_02", "channel": "C", "text": "Bitcoin c."}]}
1300 | -    HOOK = dict(pm("h", "A", 12.0), hook_rating={"scroll": 5, "alone": 4, "setup": 2})
1301 | +    HOOK = dict(pm("h", "A", 12.0), hook_rating={"scroll": 5, "alone": 4, "setup": 3, "backend": "xai:grok"})
1302 |  
1303 |      def reply(self, clips=None, vo=5, line="Nobody can change the rules of Bitcoin."):
1304 |          return {"through_line": line, "clips": dict({"clip_01": 5, "clip_02": 5}, **(clips or {})), "vo_point": vo}
1305 | @@ -264,6 +277,14 @@ class TestCoherenceHookRatedOnce(unittest.TestCase):
1306 |          self.assertFalse(self.run_it(self.reply(vo=3))[0])
1307 |          self.assertFalse(self.run_it(self.reply(), hook=pm("h", "A", 12.0))[0])   # no cached rating: fail closed
1308 |          self.assertFalse(self.run_it(self.reply(), hook=dict(self.HOOK, hook_rating={"scroll": 3, "alone": 5}))[0])
1309 | +        G = "xai:grok"                                        # ruling 115: the hook's slot is its calibrated bar
1310 | +        ok, v, _, _ = self.run_it(self.reply(), hook=dict(self.HOOK, hook_rating={"scroll": 3, "alone": 4,
1311 | +                                                                                     "setup": 3, "backend": G}))
1312 | +        self.assertEqual((ok, v["clips"]["hook"]), (True, 3))
1313 | +        for hr in ({"scroll": 5, "alone": 5, "setup": 2, "backend": G}, {"scroll": 5, "alone": 3, "setup": 5,
1314 | +                                                                         "backend": G},
1315 | +                   {"scroll": 5, "alone": 5, "setup": 5, "backend": "heimdall:qwen/qwen3.8-27b"}):
1316 | +            self.assertFalse(self.run_it(self.reply(), hook=dict(self.HOOK, hook_rating=hr))[0], hr)
1317 |  
1318 |      def test_out_of_contract_is_not_measured(self):
1319 |          good = self.reply()
1320 | @@ -1299,8 +1320,9 @@ class TestRuling58StepAEveryCandidate(unittest.TestCase):
1321 |  
1322 |  class TestRuling59HookFirst(unittest.TestCase):
1323 |      """RULING 59 (11:00): HOOK FIRST. Every cleared, cuttable moment that can open is rated on the hook's own job (ruling
1324 | -    52's question) in one batched call, cached; only a hook rated >= 4 opens; the angles are written FOR the passing
1325 | -    hooks and tried best hook first; with no passing hook the build stops before any line-up, listing the best three."""
1326 | +    52's question), cached; the angles are written FOR the passing hooks and tried best hook first; with no passing
1327 | +    hook the build stops before any line-up, listing the best three. RULING 115: each candidate is asked ALONE (one
1328 | +    call a candidate), and a hook passes when each of its parts is at least its calibrated floor (the rigs': conftest)."""
1329 |  
1330 |      def canned(self, *replies):
1331 |          c = Canned(coherence_verdict=list(replies))
1332 | @@ -1308,37 +1330,90 @@ class TestRuling59HookFirst(unittest.TestCase):
1333 |          c.backends = {"fake:coherence_verdict": B("fake", "fake")}
1334 |          return c
1335 |  
1336 | -    def test_one_batched_call_rates_every_hook_and_the_rating_is_derived_and_cached(self):
1337 | -        import tempfile
1338 | +    def test_each_candidate_is_asked_alone_one_call_each_and_the_rating_is_derived_and_cached(self):
1339 | +        from unittest import mock
1340 |          ms = [pm("a", "A", 12.0), pm("b", "B", 12.0)]
1341 | -        reply = {"hooks": {"a": {"scroll": 5, "alone": 4, "setup": 5, "why": "w a"},
1342 | -                           "b": {"scroll": 5, "alone": 2, "setup": 5, "why": "needs what came before"}}}
1343 | +        ra = {"hooks": {"a": {"scroll": 5, "alone": 4, "setup": 5, "why": "w a"}}}
1344 | +        rb = {"hooks": {"b": {"scroll": 5, "alone": 2, "setup": 5, "why": "needs what came before"}}}
1345 |          with tempfile.TemporaryDirectory() as d:
1346 |              cache = os.path.join(d, "HOOK_CACHE.json")
1347 | -            c = self.canned(reply)
1348 | +            c = self.canned(ra, rb)
1349 |              got, err = PK.hook_ratings(c, ms, ctx(), {"heimdall"}, {"deepseek"}, cache=cache)
1350 |              self.assertIsNone(err)
1351 | -            self.assertEqual(c.calls, [("coherence_verdict", {"heimdall"}, {"deepseek"})])   # ONE call, off the writers
1352 | -            self.assertEqual((got["a"]["rating"], got["b"]["rating"]), (4, 2))   # the lowest part (ruling 52)
1353 | -            self.assertEqual(got["b"]["why"], "needs what came before")
1354 | +            self.assertEqual(c.calls, [("coherence_verdict", {"heimdall"}, {"deepseek"})] * 2)   # ONE call EACH (ruling
1355 | +            #   115: the asking the calibration measured), off the writers
1356 | +            self.assertEqual((got["a"]["rating"], got["b"]["rating"]), (4, 2))   # scroll / alone: it ORDERS hooks
1357 | +            self.assertEqual((got["a"]["setup"], got["b"]["why"]), (5, "needs what came before"))   # every part kept
1358 |              again, err = PK.hook_ratings(self.canned(), ms, ctx(), {"heimdall"}, {"deepseek"}, cache=cache)
1359 |              self.assertEqual((err, again["a"]["rating"], again["a"]["cached"]), (None, 4, True))   # no call at all
1360 |              new = [dict(ms[0], text="Bitcoin is a new text now."), ms[1]]
1361 |              c = self.canned({"hooks": {"a": {"scroll": 3, "alone": 3, "setup": 3, "why": "w"}}})
1362 |              got, _ = PK.hook_ratings(c, new, ctx(), {"heimdall"}, {"deepseek"}, cache=cache)
1363 |              self.assertEqual((len(c.calls), got["a"]["rating"], got["b"]["cached"]), (1, 3, True))   # its new text only
1364 | +            with mock.patch.object(PK, "HOOK_VERSION", "another-asking"):   # a rating cached under another question
1365 | +                c = self.canned(ra, rb)                                      # or asking never answers (the batched
1366 | +                got, _ = PK.hook_ratings(c, ms, ctx(), {"heimdall"}, {"deepseek"}, cache=cache)   # ratings of before)
1367 | +                self.assertEqual((len(c.calls), got["a"]["cached"], got["b"]["cached"]), (2, False, False))
1368 | +
1369 | +    def test_the_cache_answers_only_for_todays_hook_list_and_production_seed(self):
1370 | +        """Audit 20261115_1410 C1 (glm): a rating cached by a model that is NOT on today's hook list is asked again (a
1371 | +        rater change re-asks every hook: a rating off the list can never pass the bar); a rating asked at another
1372 | +        seed never reads or writes the cache (the key's version carries production's seed)."""
1373 | +        ms = [pm("a", "A", 12.0)]
1374 | +        ra = {"hooks": {"a": {"scroll": 5, "alone": 4, "setup": 5, "why": "w"}}}
1375 | +        with tempfile.TemporaryDirectory() as d:
1376 | +            cache = os.path.join(d, "HOOK_CACHE.json")
1377 | +            c = self.canned(ra)
1378 | +            c.chain = lambda role, kind=None: ["fake:coherence_verdict"]
1379 | +            PK.hook_ratings(c, ms, ctx(), set(), set(), cache=cache)            # cached by fake:coherence_verdict
1380 | +            c = self.canned()
1381 | +            c.chain = lambda role, kind=None: ["fake:coherence_verdict"]
1382 | +            got, err = PK.hook_ratings(c, ms, ctx(), set(), set(), cache=cache)
1383 | +            self.assertEqual((err, got["a"]["cached"], c.calls), (None, True, []))   # on the list: served
1384 | +            c = self.canned(ra)
1385 | +            c.chain = lambda role, kind=None: ["xai:another-rater"]
1386 | +            got, err = PK.hook_ratings(c, ms, ctx(), set(), set(), cache=cache)
1387 | +            self.assertEqual((got["a"]["cached"], len(c.calls)), (False, 1))    # off today's list: asked again
1388 | +            before = open(cache).read()
1389 | +            c = self.canned({"hooks": {"b": {"scroll": 5, "alone": 4, "setup": 5, "why": "w"}}})
1390 | +            got, _ = PK.hook_ratings(c, [pm("b", "B", 12.0)], ctx(), set(), set(), cache=cache, seed=PK.HOOK_SEED + 1)
1391 | +            self.assertEqual((len(c.calls), open(cache).read()), (1, before))   # another seed: never written
1392 | +            c = self.canned(ra)
1393 | +            got, _ = PK.hook_ratings(c, ms, ctx(), set(), set(), cache=cache, seed=PK.HOOK_SEED + 1)
1394 | +            self.assertEqual((got["a"]["cached"], len(c.calls)), (False, 1))   # ... and never read
1395 | +
1396 | +    def test_a_candidate_left_unrated_never_stops_the_others_being_asked(self):
1397 | +        """RULING 115: one call a candidate; a candidate whose chain is spent has no rating (law L-m), the others are
1398 | +        still asked, and the first error is returned."""
1399 | +        import providers as P
1400 | +        ms = [pm("a", "A", 12.0), pm("b", "B", 12.0)]
1401 | +        c = self.canned()
1402 | +        asked = []
1403 | +
1404 | +        def call(role, prompt, *a, **k):
1405 | +            asked.append(re.findall(r'CANDIDATE id="(\w+)"', prompt))
1406 | +            if 'CANDIDATE id="a"' in prompt:
1407 | +                raise P.ProviderError("coherence_verdict: every back-end unavailable")
1408 | +            return P.Reply(json.dumps({"hooks": {"b": {"scroll": 4, "alone": 4, "setup": 4, "why": "w"}}}),
1409 | +                           "fake:coherence_verdict", "fake")
1410 | +        c.call = call
1411 | +        got, err = PK.hook_ratings(c, ms, ctx(), set(), set())
1412 | +        self.assertEqual((asked, sorted(got), got["b"]["rating"]), ([["a"], ["b"]], ["b"], 4))
1413 | +        self.assertIn("ProviderError: coherence_verdict: every back-end unavailable", err)
1414 |  
1415 |      def test_the_prompt_asks_ruling_52s_question_of_each_candidate_alone(self):
1416 |          ms = [pm("a", "A", 12.0), pm("b", "B", 12.0)]
1417 |          prompts = []
1418 | -        c = self.canned({"hooks": {k: {"scroll": 5, "alone": 5, "setup": 5, "why": "w"} for k in "ab"}})
1419 | +        c = self.canned(*({"hooks": {k: {"scroll": 5, "alone": 5, "setup": 5, "why": "w"}}} for k in "ab"))
1420 |          call = c.call
1421 |          c.call = lambda role, prompt, *a, **k: (prompts.append(prompt), call(role, prompt, *a, **k))[1]
1422 |          PK.hook_ratings(c, ms, ctx(), set(), set())
1423 | -        self.assertIn(PK.HOOK_QUESTION, prompts[0])                       # ONE definition of the hook's job
1424 | -        self.assertIn('CANDIDATE id="a"', prompts[0])
1425 | -        self.assertIn('CANDIDATE id="b"', prompts[0])
1426 | -        self.assertIn("Judge each one ALONE", prompts[0])
1427 | +        self.assertEqual(len(prompts), 2)                                 # ruling 115: ONE candidate a call
1428 | +        for p, me, other in ((prompts[0], "a", "b"), (prompts[1], "b", "a")):
1429 | +            self.assertIn(PK.HOOK_QUESTION, p)                            # ONE definition of the hook's job
1430 | +            self.assertIn(f'CANDIDATE id="{me}"', p)
1431 | +            self.assertNotIn(f'CANDIDATE id="{other}"', p)
1432 | +            self.assertIn("Judge each one ALONE", p)
1433 |  
1434 |      def chained(self, *replies):
1435 |          """A canned chain: each call is answered by the next model (fake:1, fake:2, ...), and a model the caller
1436 | @@ -1375,27 +1450,40 @@ class TestRuling59HookFirst(unittest.TestCase):
1437 |          self.assertEqual(got, {})
1438 |          self.assertIn("ProviderError", err)
1439 |  
1440 | -    def test_only_a_hook_rated_4_or_more_opens(self):
1441 | +    def test_only_a_hook_on_its_calibrated_bar_opens(self):
1442 | +        """RULING 115: a rated hook opens when EACH part is at least its calibrated floor (the rigs': scroll 3, alone 4,
1443 | +        setup 3) and the calibrated rater rated it; with no valid calibration no rated hook opens (fail closed)."""
1444 | +        from unittest import mock
1445 |          m = dict(pm("a", "A", 12.0), hook_onset={"pass": True})
1446 |          self.assertTrue(PK.can_open(m))                                   # not rated yet: as before ruling 59
1447 | -        for (sc, al, se), ok in (((4, 4, 1), True), ((5, 4, 5), True), ((3, 5, 5), False), ((5, 3, 5), False)):
1448 | -            r = dict(m, hook_rating={"scroll": sc, "alone": al, "setup": se})
1449 | -            self.assertEqual(PK.can_open(r), ok, (sc, al, se))           # ruling 61: scroll / alone, never setup
1450 | +        G = "xai:grok"
1451 | +        for (sc, al, se), ok in (((3, 4, 3), True), ((5, 4, 5), True), ((2, 5, 5), False), ((5, 3, 5), False),
1452 | +                                 ((5, 5, 2), False)):                     # setup counts now (ruling 115)
1453 | +            r = dict(m, hook_rating={"scroll": sc, "alone": al, "setup": se, "backend": G})
1454 | +            self.assertEqual(PK.can_open(r), ok, (sc, al, se))
1455 |              self.assertEqual(PK.placement(r), "" if ok else " | cannot open (never the hook)")
1456 | -        for bad in (None, {"rating": 5}, {"scroll": True, "alone": 5}, {"scroll": 5.0, "alone": 5}):
1457 | +        top = dict(m, hook_rating={"scroll": 5, "alone": 5, "setup": 5, "backend": G})
1458 | +        self.assertFalse(PK.can_open(dict(top, hook_rating=dict(top["hook_rating"],
1459 | +                                                                backend="heimdall:qwen/qwen3.8-27b"))))   # off the rater
1460 | +        for bad in (None, {"rating": 5}, {"scroll": True, "alone": 5, "setup": 5, "backend": G},
1461 | +                    {"scroll": 5.0, "alone": 5, "setup": 5, "backend": G}, {"scroll": 5, "alone": 5, "backend": G}):
1462 |              self.assertFalse(PK.can_open(dict(m, hook_rating=bad)), bad)
1463 | -        self.assertFalse(PK.can_open(dict(m, text="And Bitcoin is money.")))   # the render's hook rule
1464 | -        low = dict(m, hook_rating={"scroll": 3, "alone": 4, "setup": 4})
1465 | +        self.assertFalse(PK.can_open(dict(top, text="And Bitcoin is money.")))   # the render's hook rule
1466 | +        low = dict(m, hook_rating={"scroll": 5, "alone": 3, "setup": 4, "backend": G})
1467 |          self.assertFalse(PK.lineup_ok([low, pm("x", "B", 14.0), pm("y", "C", 13.0)])[0])
1468 | +        with mock.patch.object(PK, "_live_bar", lambda: (None, "the hook calibration is over 24 h old: re-run it")):
1469 | +            self.assertFalse(PK.can_open(top))                             # no valid calibration: no hook passes
1470 | +            self.assertEqual(PK.hook_own(top)["short"], "the hook calibration is over 24 h old: re-run it")
1471 |  
1472 |      def test_a_line_up_opens_on_its_angles_own_hook_and_never_swaps_it(self):
1473 | -        ms = [dict(pm(k, k.upper(), d), hook_onset={"pass": True}, hook_rating={"scroll": 5, "alone": 5, "setup": 5})
1474 | +        ms = [dict(pm(k, k.upper(), d), hook_onset={"pass": True}, hook_rating={"scroll": 5, "alone": 5, "setup": 5,
1475 | +                                                                                 "backend": "xai:grok"})
1476 |                for k, d in (("a", 12.0), ("b", 14.0), ("c", 13.0), ("d", 13.0))]
1477 |          by = {m["moment_id"]: m for m in ms}
1478 |          by["b"]["scores"] = dict(by["b"]["scores"], hook_first_2s=99)     # a stronger opener elsewhere
1479 |          segs = PK.lineup_for(angle(["b", "a", "c", "d"], "a"), by, need_onset=True, hook_only=True)
1480 |          self.assertEqual(segs[0]["moment_id"], "a")
1481 | -        low = dict(by, a=dict(by["a"], hook_rating={"scroll": 3, "alone": 5, "setup": 5}))
1482 | +        low = dict(by, a=dict(by["a"], hook_rating={"scroll": 5, "alone": 3, "setup": 5, "backend": "xai:grok"}))
1483 |          self.assertIsNone(PK.lineup_for(angle(["b", "a", "c", "d"], "a"), low, need_onset=True, hook_only=True))
1484 |          self.assertEqual(PK.lineup_for(angle(["b", "a", "c", "d"], "a"), low, need_onset=True)[0]["moment_id"], "b")
1485 |          self.assertEqual(PK.swap_lineup(segs, {"a"}, by, keep_hook=True), (None, None))
1486 | @@ -1408,13 +1496,15 @@ class TestRuling59HookFirst(unittest.TestCase):
1487 |      def test_no_hook_in_the_pool_stops_before_the_second_screen_and_lists_the_best_three(self):
1488 |          ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 13.0)]
1489 |          rig = Rig(ms, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None],
1490 | -                  hooks={"h": (3, 4, 4), "x": (2, 5, 5), "y": (4, 3, 4), "z": (1, 1, 1)})
1491 | +                  hooks={"h": (3, 4, 2), "x": (2, 5, 5), "y": (4, 3, 4), "z": (1, 1, 1)})   # each under ONE floor
1492 |          out = rig.run()
1493 |          self.assertIsNone(out["package"])
1494 |          self.assertTrue(out["why_none"].startswith("no hook in the pool (ruling 59 d): none of the 4 moments"))
1495 | -        self.assertEqual([b["moment_id"] for b in out["hook_pool"]["best"]], ["h", "y", "x"])
1496 | +        self.assertIn("passes the calibrated hook bar (ruling 115): scroll >= 3, alone >= 4, setup >= 3", out["why_none"])
1497 | +        self.assertEqual([b["moment_id"] for b in out["hook_pool"]["best"]], ["y", "h", "x"])   # rating, then parts
1498 |          self.assertEqual([b["rating"] for b in out["hook_pool"]["best"]], [3, 3, 2])
1499 | -        self.assertIn("A 3 (scroll 3, alone 4, setup 4): why h", out["why_none"])
1500 | +        self.assertIn("A 3 (scroll 3, alone 4, setup 2): why h", out["why_none"])   # setup alone held h back
1501 | +        self.assertEqual(out["hook_pool"]["bar_floors"], {"scroll": 3, "alone": 4, "setup": 3})
1502 |          self.assertEqual(rig.medley_calls, [])
1503 |          self.assertNotIn("angle_write", rig.events)                     # no angle, no line-up paid for
1504 |          self.assertEqual(len(rig.screens), 1)                            # and no second screen
1505 | @@ -1426,7 +1516,7 @@ class TestRuling59HookFirst(unittest.TestCase):
1506 |      def test_the_writer_is_given_the_passing_hooks_and_the_best_hook_goes_first(self):
1507 |          ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 13.0)]
1508 |          rig = Rig(ms, [["h", "x", "y", "z"], ["x", "h", "y", "z"]], [(True, [], None, Rig.LINE)], [None],
1509 | -                  hooks={"h": (4, 4, 4), "x": (5, 5, 5), "y": (3, 3, 3), "z": (3, 4, 5)})
1510 | +                  hooks={"h": (4, 4, 4), "x": (5, 5, 5), "y": (3, 3, 3), "z": (3, 3, 5)})
1511 |          out = rig.run()
1512 |          p = next(p for r, p in rig.prompts if r == "angle_write")
1513 |          self.assertIn("THE HOOKS", p)
1514 | @@ -1438,6 +1528,8 @@ class TestRuling59HookFirst(unittest.TestCase):
1515 |          self.assertEqual(rig.medley_calls[0][0], "x")                   # the x angle, though the writer gave it second
1516 |          self.assertEqual(out["hook_pool"]["passing"], ["x", "h"])
1517 |          self.assertIsNotNone(out["package"])
1518 | +        self.assertEqual((out["package"]["hook_bar"]["note"], out["package"]["hook_bar"]["floors"]),   # ruling 115 (2)
1519 | +                         ("hook passed on the calibrated bar", {"scroll": 3, "alone": 4, "setup": 3}))
1520 |  
1521 |      def test_an_angle_not_written_for_a_passing_hook_is_out_of_contract(self):
1522 |          ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 13.0)]
1523 | @@ -1688,6 +1780,19 @@ class TestRulings6264Search(unittest.TestCase):
1524 |          self.assertIn("ruling 62", out["tried"][0]["why"])
1525 |          self.assertIsNotNone(out["package"])
1526 |  
1527 | +    def test_ruling_62_only_with_a_hook_on_its_calibrated_bar(self):
1528 | +        """RULING 115: 'only the last clip fails' needs the line-up's own hook on its calibrated bar (its slot is never
1529 | +        COHERENCE_MIN's: a scroll-3 hook at every floor counts as passing)."""
1530 | +        segs = [dict(pm("h", "A", 12.0), hook_rating={"scroll": 3, "alone": 4, "setup": 3, "backend": "xai:grok"}),
1531 | +                pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 9.0)]
1532 | +        med = dict(verdict(PK.labels(4), ratings={"hook": 3, "clip_03": 2}), measured=True, flagged=[])
1533 | +        self.assertTrue(PK.last_clip_only(segs, med))
1534 | +        for hr in ({"scroll": 5, "alone": 3, "setup": 5, "backend": "xai:grok"},
1535 | +                   {"scroll": 5, "alone": 5, "setup": 5, "backend": "heimdall:qwen/qwen3.8-27b"}, None):
1536 | +            bad = [dict(segs[0], hook_rating=hr), *segs[1:]]
1537 | +            self.assertFalse(PK.last_clip_only(bad, med), hr)                 # the hook fails: never "only the last"
1538 | +        self.assertFalse(PK.last_clip_only(segs, dict(med, clips=dict(med["clips"], clip_01=3))))   # two clips fail
1539 | +
1540 |      def test_ruling_62_under_the_floor_swaps_as_now(self):
1541 |          ms = [self.fresh("h", "A", 12.0), self.fresh("x", "B", 10.0), self.fresh("y", "C", 10.0),
1542 |                self.fresh("z", "D", 9.0)]                                    # without z: 32 s, under 36.7
1543 | diff --git a/tests/package/test_spotlight.py b/tests/package/test_spotlight.py
1544 | index 64517b8..0ec537b 100644
1545 | --- a/tests/package/test_spotlight.py
1546 | +++ b/tests/package/test_spotlight.py
1547 | @@ -65,7 +65,7 @@ def moment(text=TEXT, dur=20.0, mid="m1", channel="DataDash", **kw):
1548 |      m.update(text=text, channel_name=channel, published_at=(NOW - timedelta(hours=2)).isoformat(),
1549 |               hook_onset={"pass": True, "measured": True, "lead_ms": 120, "cut_in": 1.0, "why": "quiet"},
1550 |               hook_rating={"scroll": 5, "alone": 4, "setup": 3, "rating": 4, "why": "a complete claim",
1551 | -                          "backend": "fake:xai", "replayed": False},
1552 | +                          "backend": "xai:grok", "replayed": False},   # the conftest's calibrated rater (ruling 115)
1553 |               visual={"version": VP.VERSION, "measured": True, "flags": [], "backend": "fake:vis", "replayed": False,
1554 |                       "third_person": {"shown": False, "how": "none", "words_negative": False, "name_on_screen": None,
1555 |                                        "finding": "none"}, "on_screen_text": [],
1556 | @@ -183,6 +183,9 @@ class TestPinContract(unittest.TestCase):
1557 |          self.assertEqual(mp["first_comment"], pk["first_comment"])
1558 |          self.assertEqual(mp["gates"]["spotlight_source"]["format"], "CONVERSATION")   # 21:10 Nov 14: WHICH passed,
1559 |          self.assertEqual(PP.pin_seal(pin), mp["package_sha256"])                      # inside the seal
1560 | +        marked = PP.to_pin(dict(pk, hook_bar=SPOT.P.hook_bar_mark()), "t")["moments_package"]   # ruling 115 (2):
1561 | +        self.assertEqual(marked["hook_bar"]["note"], "hook passed on the calibrated bar")     # the spotlight's pin
1562 | +        self.assertEqual(marked["package_sha256"], mp["package_sha256"])                      # too, outside the seal
1563 |          integrator = PP.seal(pin["segments"], mp["edl_vo"], mp.get("signoff_expected"), mp["title"], mp["caption"],
1564 |                               mp["gates"], mp.get("btc_screen"),
1565 |                               **({"shape": mp["shape"], "first_comment": mp["first_comment"]}
1566 | @@ -618,6 +621,24 @@ class TestPackageFor(unittest.TestCase):
1567 |              self.assertEqual(asked[-1], None, name)                         # the package without it is judged
1568 |              self.assertFalse(pk["spotlight"]["closing"]["kept"], name)
1569 |  
1570 | +    def test_ruling_115_the_hook_own_row_is_the_calibrated_bar(self):
1571 | +        """RULING 115: the opener's row passes when each part is at least its calibrated floor (the rigs': scroll 3,
1572 | +        alone 4, setup 3), by the calibrated rater; ruling 90's ">= 4" (the scroll-and-alone rating) no longer decides."""
1573 | +        def row(scroll, alone, setup, backend="xai:grok"):
1574 | +            m = moment(hook_rating={"scroll": scroll, "alone": alone, "setup": setup, "rating": min(scroll, alone),
1575 | +                                    "why": "w", "backend": backend, "replayed": False})
1576 | +            return SPOT.inventory(*package()[0:1], m, FID_OK, [], True, [], CX_OK, two()[0], two(),
1577 | +                                  {"verdict": "keep", "measured": True, "replayed": False},
1578 | +                                  {"ok": True, "edges": {"cuttable": True}}, pre_of(m), m["spotlight_source"],
1579 | +                                  {"now": NOW, "day": "d", "never_delivered": True,
1580 | +                                   "one_per_channel_day": True})["hook_own"]
1581 | +        r = row(3, 4, 3)                                                    # rating 3: ruling 90 failed it
1582 | +        self.assertEqual((r["status"], r["rating"], r["setup"]), ("PASS", 3, 3))
1583 | +        self.assertIn("scroll >= 3, alone >= 4, setup >= 3", r["bar"])
1584 | +        for parts in ((5, 3, 5), (5, 5, 2), (2, 5, 5)):
1585 | +            self.assertEqual(row(*parts)["status"], "FAIL", parts)
1586 | +        self.assertEqual(row(5, 5, 5, "heimdall:qwen/qwen3.8-27b")["status"], "FAIL")   # off the calibrated rater
1587 | +
1588 |      def test_the_precheck_row_needs_one_verdict_on_this_clip(self):
1589 |          m = moment()
1590 |          rows = lambda pre: SPOT.inventory(*package()[0:1], m, FID_OK, [], True, [], CX_OK, two()[0], two(),
1591 | @@ -681,7 +702,7 @@ class TestBuild(unittest.TestCase):
1592 |  
1593 |          def hook_ratings(router, ms_, *a, **k):
1594 |              return {m["moment_id"]: {"scroll": ratings[m["moment_id"]], "alone": 5, "setup": 3,
1595 | -                                     "rating": ratings[m["moment_id"]], "why": "w", "backend": "fake:xai"}
1596 | +                                     "rating": ratings[m["moment_id"]], "why": "w", "backend": "xai:grok"}
1597 |                      for m in ms_}, None
1598 |  
1599 |          def second(router, cleared, a_by, *a, **k):
1600 | @@ -723,11 +744,20 @@ class TestBuild(unittest.TestCase):
1601 |      def test_the_best_qualifying_moment_goes_to_the_package(self):
1602 |          ms = [moment(mid="a", channel="A"), moment(mid="b", channel="B", text=TEXT.replace("money", "asset")),
1603 |                moment(mid="c", channel="C", text=TEXT.replace("money", "thing"))]
1604 | -        out, calls = self.run_build(ms, {"a": 3, "b": 4, "c": 5}, alone=[4.0, 4.0, 3.0])
1605 | +        out, calls = self.run_build(ms, {"a": 2, "b": 4, "c": 5}, alone=[4.0, 4.0, 3.0])
1606 |          self.assertEqual(calls["package_for"], ["b"])                      # c opens best but stands alone at 3
1607 | -        self.assertIn("hook's own job rates 3", out["moments"]["a"]["out"])
1608 | +        self.assertEqual((out["moments"]["a"]["hook_passes"], out["moments"]["b"]["hook_passes"]), (False, True))
1609 | +        self.assertIn("the hook's own job: scroll 2 < 3 (the calibrated hook bar (ruling 115): scroll >= 3, alone >= 4, "
1610 | +                      "setup >= 3", out["moments"]["a"]["out"])               # ruling 115: under ONE part's floor
1611 |          self.assertIn("ALONE scorer: 3.0", out["moments"]["c"]["out"])
1612 |          self.assertIsNotNone(out["package"])
1613 | +        self.assertEqual(out["package"]["hook_bar"]["note"], "hook passed on the calibrated bar")   # ruling 115 (2)
1614 | +
1615 | +    def test_ruling_115_an_opener_at_every_floor_goes_to_the_package(self):
1616 | +        """Scroll 3, alone 5, setup 3: under ruling 90 (rating >= 4) it stopped; on the calibrated bar it passes."""
1617 | +        out, calls = self.run_build([moment(mid="a", channel="A")], {"a": 3})
1618 | +        self.assertEqual(calls["package_for"], ["a"])
1619 | +        self.assertIsNotNone(out["package"])
1620 |  
1621 |      def test_ruling_92_amended_zero_changes_near_the_clip_stops_before_any_vision_call(self):
1622 |          """09:03 Nov 14: the markers refuse alone only when the episode is marked and shows ZERO speaker changes in the
1623 | diff --git a/tests/providers/test_providers.py b/tests/providers/test_providers.py
1624 | index 7d9e0a6..d27acc2 100644
1625 | --- a/tests/providers/test_providers.py
1626 | +++ b/tests/providers/test_providers.py
1627 | @@ -672,5 +672,30 @@ class TestRuling86Shadow(TestRuling85Routing):
1628 |              with self.assertRaises(ValueError):
1629 |                  P.Router(self.cfg(d), env_path="/nonexistent", shadow={"*": "xai:nope"})
1630 |  
1631 | +    def test_ruling_115_a_verdict_types_own_shadow_asked_on_a_chain_of_its_own(self):
1632 | +        """RULING 115: the hook job (Grok decides) is shadowed by qwen, keyed "<role>:<kind>", on a chain of its own;
1633 | +        every other verdict of the role keeps the role's ("*") shadow; each record names its kind."""
1634 | +        import tempfile
1635 | +        with tempfile.TemporaryDirectory() as d:
1636 | +            r = P.Router(self.cfg(d), env_path="/nonexistent", routing="heimdall_first",
1637 | +                         shadow={"*": "xai:grok", "coherence_verdict:hook": "heimdall:qwen"},
1638 | +                         shadow_log=os.path.join(d, "SHADOW.jsonl"), chains={"coherence_verdict:hook": ["xai:grok"]})
1639 | +            fs = self.fakes()
1640 | +            for b in fs:
1641 | +                if b.vendor == "heimdall":
1642 | +                    b.gateway, b.vendor = b.vendor, f"heimdall/{b.family}"
1643 | +            r.backends = {b.name: b for b in fs}
1644 | +            self.assertEqual(r.call("coherence_verdict", "the hook", 500, 7, kind="hook").backend, "xai:grok")
1645 | +            self.assertEqual(r.call("coherence_verdict", "a line-up", 500, 7, kind="coherence").backend,
1646 | +                             "heimdall:deepseek")
1647 | +            self.assertEqual(r.shadow_wait(5), 0)
1648 | +            got = sorted((x["kind"], x["prompt"], x["deciding"]["backend"], x["shadow"]["backend"])
1649 | +                         for x in self.lines(d))
1650 | +            self.assertEqual(got, [("coherence", "a line-up", "heimdall:deepseek", "xai:grok"),
1651 | +                                   ("hook", "the hook", "xai:grok", "heimdall:qwen")])
1652 | +            self.assertEqual((r.chain("shadow86:coherence_verdict:hook"), r.chain("shadow86:coherence_verdict")),
1653 | +                             (["heimdall:qwen"], ["xai:grok"]))
1654 | +            self.assertEqual((r.backends["heimdall:qwen"].calls, r.backends["xai:grok"].calls), (1, 2))
1655 | +
1656 |  if __name__ == "__main__":
1657 |      unittest.main()
1658 | 
```

---

pp-selectid: RULING 115 (orchestrator 13:24 ET Nov 15) (1) + (2), THE CALIBRATED HOOK BAR. Production code: a new
pipeline/hook_bar.py and pipeline/hook_calibration.json; pipeline/package.py, spotlight.py, package_pin.py,
providers.py and model_providers.json; the build driver tests/package/proof_ledger.py; ruling 112's driver
tests/package/hook112.py. Tests: a new tests/package/conftest.py and test_hook_bar.py, and updated test_medley,
test_spotlight, test_ledger_build, test_hook112 and tests/providers/test_providers.py.

THE ORDER, verbatim in its parts:
(1) "INTERIM BAR, LIVE AS SOON AS AUDITED, BOTH PATHS (medley hook and spotlight opener): the hook job is asked ALONE
    at production's seed by GROK (qwen in shadow). A hook passes when EACH of its three parts (scroll, alone, setup)
    is at least the LOWEST value that part takes across the five approved hooks under that same asking (ALONE_TEST.json
    is the source; write the three floors into one calibration file with its sha, and name them in every build line).
    Nothing else about the hook path changes (may-open rules, G17a, step A, CUTTABLE stay). If any floor comes out
    below 3, stop at 3 for that part and tell me."
(2) "MARK IT: a package sealed on the interim bar says so in its record and in the Telegram note in one plain line
    ("hook passed on the calibrated bar"); PBX's approve or reject of it is appended to the calibration file as a new
    example (approved = positive, rejected = negative with his reason)."
Ruling 113 (2), which (1) builds on: the calibration "runs before a rater takes the job, again on any change of
model, question version or seed, and once a day; a rater that fails it does not rate, and the build says so in one
line".

WHAT THE CHANGE DOES:
- hook_bar.py: floors_from (each part's minimum over the approved hooks; a floor under 3 is stopped at 3 and listed);
  write / load (the file sealed by the sha256 of its canonical body; a hand edit fails the seal); bar (valid only for
  its question version, seed, asking "alone", rater when named, and under 24 h old; else None and why: NO hook
  passes); passes (each part >= its floor AND the rating's back-end is the calibrated rater); text (the bar in one
  line); add_example ((2): approved, or rejected with a reason; the floors are not re-derived there).
- hook_calibration.json: Grok (xai:grok-4.20-0309-reasoning), asked alone at seed 7, question version bfdf74078d5e
  (= package.HOOK_VERSION), measured 18:07:52 UTC. The five approved hooks' parts from ALONE_TEST.json (the two
  whose first answer was out of contract: the retry asked once more, alone, seed 7). Floors scroll 3, alone 4,
  setup 3; none under 3.
- package.hook_ratings: ONE call per candidate (was one batched call), max_tokens 750, seed HOOK_SEED 7. This is the
  calibration's own asking: hook112.calibrate called hook_ratings with ONE reference per call, so the prompt (HOOKS_PROMPT
  with one CANDIDATE and its one key), max_tokens (600 + 150 x 1) and seed are the same bytes. HOOK_VERSION now
  hashes HOOKS_PROMPT + HOOK_ASKING, so no batched rating cached before answers. A candidate whose chain is spent has
  no rating; the others are still asked; the first error is returned.
- package.hook_own: adds "setup", "passes" (hook_bar.passes on the live bar), "short", "bar". The rating
  (min(scroll, alone)) still ORDERS hooks (hook_order); "passes" decides: _can_open, medley(), coherence(),
  last_clip_only (ruling 62) and the spotlight's opener stage and its "hook_own" gate row.
- In medley() and coherence() the hook's own rating used to sit INSIDE the min >= COHERENCE_MIN (4) over the clips.
  With a scroll floor of 3, a hook that passes the bar would then fail every line-up, so the hook's slot is judged by
  the calibrated bar and the min runs over the clips AFTER the hook (and the VO point) as before. This is the one
  reading of "nothing else changes" we took; please say if you read it otherwise.
- The hook list "coherence_verdict:hook" is Grok ALONE in every routing (heimdall_first, today, plan_b): the floors
  are Grok's, so a failover model's rating could never pass (and, cached, would answer for that moment). Grok down =
  no rating = no hook (law L-m), asked again next build. qwen answers every hook in SHADOW (proof_ledger.build_shadow;
  providers._shadow_of / _shadow_ask look up "<role>:<kind>" first and ask it on a chain of its own).
- (2) the mark: package.hook_bar_mark() -> {"note": "hook passed on the calibrated bar", "bar", "floors",
  "calibration_sha256", "ruling": "115"}, set on a built medley package and a built spotlight package, and carried
  into the pin's moments_package OUTSIDE the seal (package_pin.to_pin), for the integrator's Telegram note.

UNCHANGED GUARDS THE CHANGE LEANS ON (outside the hunks; line numbers in the changed tree):
- package._can_open (package.py:1460-1481): hook eligibility, G17a (hook_onset "pass"), stand_alone.opener; only
  then the rating. "hook_rating" absent = not rated yet (before the build rates).
- package.build (package.py:2691-2699): every cleared moment's carried rating is popped, the openers are rated, and
  EVERY cleared moment then gets "hook_rating": the rating, or {"rating": None, "why": "not rated: ..."}; hook_own of
  that is None, so an unrated hook never opens. spotlight.build does the same (spotlight.py:905-917).
- _load_cache(None) is {} (package.py:499-507: open(None) raises TypeError, caught); _cache_put(None, ...) returns
  at once (package.py:510-513).
- providers.call_parsed (providers.py:690-716): an answer out of contract moves on to the next model; with a
  one-model list the chain is then spent: ProviderError, caught per candidate in hook_ratings.
- providers.Router.chain (providers.py:794-811): this router's overrides, then the routing's per-type list, then the
  role's chain. proof_ledger builds with --routing heimdall_first (proof_ly.chains, tests/package/proof_ly.py:76).
- Router._shadow_ask runs in a thread and never raises into the build; the shadow never decides (providers.py:1221+).
- package_pin.seal (package_pin.py:200) takes segments, edl_vo, signoff, title, caption, gates, btc_screen, shape,
  first_comment, ...: not "hook_bar", so the mark is outside the seal (to_pin :469).

TESTS: 687 pass in tests/package + tests/providers; all 37 suite files of the handoff pass, one process each. 31 of 31
mutations killed after a control run (the unmutated copy passes): the rater check, a part AT its floor, min vs max,
the stop at 3, staleness, the question version, the seal, a rejection's reason, a floor under 3 in the file; the old
bar in _can_open, the hook back in either min, either verdict ignoring the bar, ruling 62, one error stopping the
others, the mark (medley, spotlight, pin), the invalid calibration's why, the version without the asking, a batch,
setup left out; the spotlight's opener and gate row on the old bar; the three hook lists; the kind's shadow (lookup
and chain); hook112's driver reading production's Grok-only list; no qwen shadow in a build.

PLEASE CHECK: (1) that a hook passes ONLY with every part at least its floor, rated by the calibrated rater, under
a valid (sealed, matching, fresh) calibration, on both paths; (2) that the floors in hook_calibration.json are the
source's minimums and that production's asking is byte-for-byte the calibration's; (3) the reading of "nothing else
changes" above (the hook's slot in the two verdicts and in ruling 62); (4) that no other model can rate a hook, and
that qwen's shadow can never decide; (5) the mark: on a sealed package and its pin only, outside the seal; (6) the
tests.


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
