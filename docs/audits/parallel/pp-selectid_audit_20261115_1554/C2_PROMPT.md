# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261115_1554
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 38 s finish=stop usage in 24041 / out 762 usd_reported=0.043174 usd~0.139 (upper-bound price)

**CODE AUDIT: pp-selectid-20261115_1554 (RULING 116 / lineup calibration)**

**Summary**  
The patch implements Ruling 116 exactly as ordered: a per-rater calibrated floor derived from the lowest rating PBX gave any approved line-up (never below 3), applied only to the calibrated rater (Grok), with all other back-ends and any invalid calibration falling back to the stricter STANDARD_LINEUP (COHERENCE_MIN=4). The hook slot remains on its own calibrated bar (Ruling 115). All sites that compute `min(...)` over clip ratings now correctly exclude the hook and read the verdict-specific floor. The mark is emitted only when both verdicts used the calibrated bar and is placed outside the seal. Tests are comprehensive, mutation coverage is complete, and the live calibration file is validated against its source data.

The change is orthogonal to SENTENCE LAW, SELECTION LOCK, SNAP LIMIT, NEIGHBOUR, ONSET/TAIL, CREDITS, L-a through L-l, M2, M12, and LAW 22. No renderer, selector, or release-auth path is touched. GPU0-only and smallest-diff constraints are satisfied (the new module is the direct analogue of `hook_bar.py`).

**Findings**

[P2] `lineup_bar.bar()` performs a `datetime.fromisoformat` followed by manual `tzinfo` check, then a separate future-date check using `HB.SKEW_MIN`. This duplicates logic already present in `hook_bar.py`. A shared helper would reduce maintenance surface. (Does not affect correctness or fail-closed behavior.)

[P2] `lineup_calibration.json` embeds full `through_line` strings, story IDs, and pin paths for four specific packages. While the test in `TestTheLiveCalibration` proves the floors match the source runs, the file is now a de-facto content dependency. Any future prompt change (new `MEDLEY_VERSION` / `COHERENCE_VERSION`) forces a full re-calibration run even if the underlying rating distribution is unchanged. Consider storing only the minimal rating vectors + seed list.

[P3] Repeated parenthetical "(ruling 116 (Q3, ruling 106's default APPLY))" appears 12 times across comments, docstrings, and test strings. After the first explanatory block the qualifier can be shortened to "(R116)" without loss of traceability.

[P3] `TestRuling116LineupBar.test_ruling_63_reorders_a_line_up_whose_hook_sits_at_its_floors` and the takeaway test use `mock.patch.object(PK, "_live_lineup_bar", ...)` on one code path and `mock.patch.object(PK, "COHERENCE_MIN", ...)` on the other. The two patching styles are inconsistent and make the "standard bar" case harder to read. A single context manager or fixture parameter would improve clarity.

[P3] Nit: `floors_for()` returns a tuple `(floors_dict, which_str, sha_or_None)`. The call sites immediately unpack into three variables, but the third is only used when `which == "calibrated"`. A small namedtuple or dataclass would make the data flow self-documenting.

No violations of fail-closed rules (M12), no gate reclassification outside the explicit Ruling 116 calibration, no leakage of hook rating into post-hook `min()` after the fixes, and no impact on protected preview / v2f byte-identity. All must-fail/must-pass cases listed in the governing laws remain satisfied because this patch does not touch sentence law, punctuation restoration, channel clustering, canon, or release authorization.

P1_OR_WORSE: 0

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 194 s finish=stop usage in 27667 / out 4552 usd_reported=0.004532 usd~0.151 (upper-bound price)

I will analyze the code changes for `RULING 116` (Calibrated Line-Up Bar) against the provided laws and the specific "PLEASE CHECK" items.

### Analysis of `pipeline/lineup_bar.py`

1.  **`floors_from` Logic**:
    *   It calculates the minimum rating for each part (`clip`, `vo_point`) across the provided runs.
    *   It enforces `FLOOR_MIN` (3).
    *   It raises `ValueError` if runs are missing or ratings are not integers.
    *   *Observation*: The logic `vals = [min(r["clips"].values()) if p == "clip" else r.get(p) for r in rs if r.get("clips")]` correctly isolates the "clip" minimums and "vo_point" values. The check `if len(vals) != len(rs)` ensures every run contributed a value. This looks robust.

2.  **`bar` Logic**:
    *   Loads the calibration file via `HB.load` (hook_bar's seal mechanism).
    *   Checks `rater` is a non-empty string.
    *   Checks `question_versions` match the current `MEDLEY_VERSION` and `COHERENCE_VERSION`.
    *   Checks `measured_at` is valid (timezone, not in future).
    *   Checks `valid_h` (null means no expiry, otherwise checks age).
    *   Checks floors are >= `FLOOR_MIN`.
    *   *Observation*: This correctly implements the "fail closed" requirement (M12). If any check fails, it returns `(None, why)`, forcing the caller to use the standard bar.

3.  **`floors_for` Logic**:
    *   Returns calibrated floors only if `live` is not None AND `backend == live["rater"]`.
    *   Otherwise, returns standard floors.
    *   *Observation*: This strictly enforces that *only* the calibrated rater gets the relaxed bar. Any other model (Plan B, etc.) gets the stricter standard bar. This satisfies Check (1).

### Analysis of `pipeline/package.py` Changes

1.  **`_live_lineup_bar`**:
    *   Caches the result of `LB.bar` based on file mtime and minute.
    *   *Observation*: Standard caching pattern, consistent with `_live_bar`.

2.  **`lineup_floors`**:
    *   Retrieves the live bar and calls `LB.floors_for`.
    *   Returns `(floors, which_bar, sha256_or_None)`.
    *   *Observation*: Correctly propagates the "which bar" info for logging/marking.

3.  **`medley` and `coherence` Functions**:
    *   **`medley`**:
        *   `fl, which, csha = lineup_floors("clips_alone", r.backend)`
        *   `ok = ... and min(x for lb, x in v["clips"].items() if lb != labs[0]) >= fl["clip"] ...`
        *   *Critical Check*: Does it exclude the hook? `labs[0]` is the hook label. The min is taken over `v["clips"].items()` where `lb != labs[0]`. This correctly excludes the hook from the line-up floor check. The hook is judged by its own bar (ruling 115) via `own["passes"]`.
        *   *Observation*: This satisfies Check (2) for `medley`.
    *   **`coherence`**:
        *   `fl, which, csha = lineup_floors("coherence", r.backend)`
        *   `ok = ... and min(x for lb, x in v["clips"].items() if lb != labs[0]) >= fl["clip"] and v["vo_point"] >= fl["vo_point"]`
        *   *Critical Check*: Excludes hook from clip min. Checks `vo_point` against `fl["vo_point"]`.
        *   *Observation*: This satisfies Check (2) for `coherence`.

4.  **`last_clip_only` (Ruling 62)**:
    *   `floor = (med.get("floors") or STANDARD_LINEUP["clips_alone"])["clip"]`
    *   `return ... [lb for lb, x in cl.items() if lb != labs[0] and x < floor] == [labs[-1]] ...`
    *   *Observation*: Uses the verdict's own floors. Excludes hook. Correct.

5.  **`build` Function (Ruling 63 Reorder & Weak Clips)**:
    *   **Reorder Condition**:
        *   `floor = (med.get("floors") or STANDARD_LINEUP["clips_alone"])["clip"]`
        *   `if ... min(x for lb, x in cl.items() if lb != labs[0]) >= floor ...`
        *   *Observation*: Previously, this likely used `COHERENCE_MIN` and included the hook in the min (or didn't exclude it properly if the hook rating was low). Now it explicitly excludes the hook and uses the dynamic floor. This fixes the "hook at its floors blocking reorder" issue mentioned in the description.
    *   **Weak Clips Calculation**:
        *   `weak = {by_lab[lb]["moment_id"] for lb, x in cl.items() if lb in by_lab and x < floor}`
        *   *Observation*: Uses the dynamic floor.
    *   **Hook Weakness**:
        *   `hook_weak = (med.get("hook_own") or {}).get("passes") is not True`
        *   *Observation*: Correctly delegates hook judgment to its own bar (ruling 115), not the line-up bar.

6.  **`build` Function (Coherence Failure Handling)**:
    *   **Takeaway Rewrite Condition**:
        *   `cfl = coh.get("floors") or STANDARD_LINEUP["coherence"]`
        *   `if ... coh["vo_point"] < cfl["vo_point"] and (coh.get("hook_own") or {}).get("passes") is True and min(x for lb, x in coh["clips"].items() if lb != "hook") >= cfl["clip"] ...`
        *   *Observation*:
            *   Checks `vo_point` against calibrated/standard floor.
            *   Checks hook passes its *

## CLAUDE'S CYCLE 1 CONSENSUS
# C1 CONSENSUS — pp-selectid audit 20261115_1554 (RULING 116 Q3: the calibrated line-up bar)

Reviewers: qwen3.8-27b (P1_OR_WORSE: 0; its "[P1]" headings are the QUESTION's checks, each verified); glm-5.3-flash
FAILED (RemoteDisconnected: no answer), so the driver asked Grok (0). Cycle 1: $0.0477 vendor-reported. No P1.

qwen verified each check: the floors only for the calibrated rater's verdicts (floors_for), every site that judges the
line-up ratings excludes the hook's slot and reads the verdict's own floors (medley, coherence, last_clip_only, the
ruling-63 reorder, the two weak-clip sets, the takeaway-only rewrite), the file's floors from the source, the mark
outside the seal.

ACTED ON:
- qwen [P2] "the takeaway-only rewrite names the hook's label as the string 'hook'": it now reads the package's own
  first segment label (pk["segments"][0]["label"]), as every other site reads labs[0]. Tests pass (225); mutation L8 (the
  hook's rating back inside that min) re-aimed at the new text and KILLED after a control run.

NOT CHANGED:
- Grok [P2] "the timestamp checks duplicate hook_bar's": kept side by side on purpose (each file's refusal names its
  own calibration); both are tested the same way.
- Grok [P2] "the file carries the approved runs in full (through-lines, story ids)": they are its source, as the hook
  file carries its approved hooks; the live-file test derives the floors from proof/clips116 on every run, so a hand
  edit or a stale copy fails it. A new prompt version needs a new measurement either way (the floors are only valid
  for the question they were measured under).
- Grok [P3] (wording, the two patching styles in the two-bar tests, a namedtuple): noted.
- qwen [P2] "STANDARD_LINEUP / valid_h / the rig": as designed and tested (the standard bar is COHERENCE_MIN for every
  part; valid_h null and its refusals are hook_bar's rule; the rig now answers as production does).


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_20261115_1554/C2_STEP.diff (1000 lines)
```
   1 | diff --git a/pipeline/lineup_bar.py b/pipeline/lineup_bar.py
   2 | new file mode 100644
   3 | index 0000000..b95489e
   4 | --- /dev/null
   5 | +++ b/pipeline/lineup_bar.py
   6 | @@ -0,0 +1,99 @@
   7 | +"""RULING 116 (orchestrator 15:30 ET Nov 15; Q3 on STATE 15:34, ruling 106's default APPLY): THE LINE-UP VERDICTS ON
   8 | +A CALIBRATED BAR, the hook's method (ruling 115).
   9 | +
  10 | +Today's clips-alone verdict (package.medley) and coherence verdict (package.coherence) failed PBX's own approved
  11 | +line-ups on ONE rating of 3 (tests/package/proof/clips116/: the four approved line-ups, seeds 7, 8, 9, Grok, today's
  12 | +prompts). A rating's FLOOR is the lowest value it took across them, never under 3: clips-alone, every clip after the
  13 | +hook; coherence, every clip after the hook and the VO point. The through-line stays required and the flagged joins
  14 | +stay at the law's one bridge (L-y 2): no approved line-up needed more.
  15 | +
  16 | +The floors live in ONE sealed file, pipeline/lineup_calibration.json (hook_bar's seal), valid only for its rater, the
  17 | +two prompts' versions (package.MEDLEY_VERSION, COHERENCE_VERSION) and its own valid_h (null: one fixed source). They
  18 | +apply ONLY to a verdict the calibrated rater gave. Any other model's verdict, and every verdict while the file is
  19 | +invalid, is judged on the STANDARD bar (package.COHERENCE_MIN), which is stricter: the calibrated bar passes no more
  20 | +than PBX's approvals show passing. A package whose two verdicts both passed on it says so in its record and pin
  21 | +(NOTE)."""
  22 | +import os
  23 | +from datetime import datetime, timedelta, timezone
  24 | +
  25 | +import hook_bar as HB
  26 | +
  27 | +PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lineup_calibration.json")
  28 | +VERDICTS = {"clips_alone": ("clip",), "coherence": ("clip", "vo_point")}   # each verdict's calibrated parts
  29 | +FLOOR_MIN = HB.FLOOR_MIN            # 3: ruling 115's rule, applied the same way (ruling 116 (4))
  30 | +NOTE = "line-up passed on the calibrated bar"
  31 | +
  32 | +
  33 | +def floors_from(runs):
  34 | +    """{verdict: {part: the lowest value it took across the runs, never under FLOOR_MIN}} and the parts stopped at
  35 | +    FLOOR_MIN. runs: {verdict: [{"clips": {label: rating}, "vo_point": n (coherence)}, ...]} (the hook not among the
  36 | +    clips). A run without its ratings measures nothing: ValueError."""
  37 | +    fl, low = {}, []
  38 | +    for verdict, parts in VERDICTS.items():
  39 | +        rs = runs.get(verdict) or []
  40 | +        if not rs:
  41 | +            raise ValueError(f"no {verdict} run: the floors cannot be measured")
  42 | +        fl[verdict] = {}
  43 | +        for p in parts:
  44 | +            vals = [min(r["clips"].values()) if p == "clip" else r.get(p) for r in rs if r.get("clips")]
  45 | +            if len(vals) != len(rs) or any(type(v) is not int for v in vals):
  46 | +                raise ValueError(f"a {verdict} run has no integer {p!r}: the floors cannot be measured")
  47 | +            fl[verdict][p] = min(vals)
  48 | +            if fl[verdict][p] < FLOOR_MIN:
  49 | +                low.append(f"{verdict} {p} {fl[verdict][p]} (stopped at {FLOOR_MIN})")
  50 | +                fl[verdict][p] = FLOOR_MIN
  51 | +    return fl, low
  52 | +
  53 | +
  54 | +def bar(versions, now=None, path=None):
  55 | +    """The live bar: {"rater", "sha256", "clips_alone": {...}, "coherence": {...}} when the calibration is sealed, for
  56 | +    exactly these prompt versions ({"clips_alone": v, "coherence": v}), not dated in the future, within its own valid_h,
  57 | +    and no floor under FLOOR_MIN; else (None, why): every verdict is then judged on the standard bar."""
  58 | +    cal, why = HB.load(path or PATH)
  59 | +    if cal is None:
  60 | +        return None, why.replace("hook calibration", "line-up calibration")
  61 | +    if not isinstance(cal.get("rater"), str) or not cal["rater"]:
  62 | +        return None, "the line-up calibration names no rater: refused"
  63 | +    for verdict, want in versions.items():
  64 | +        if (cal.get("question_versions") or {}).get(verdict) != want:
  65 | +            return None, (f"the line-up calibration is for {verdict}'s question version "
  66 | +                          f"{(cal.get('question_versions') or {}).get(verdict)!r}, not {want!r}: standard bar until it "
  67 | +                          f"is re-run")
  68 | +    try:
  69 | +        at = datetime.fromisoformat(str(cal["measured_at"]))
  70 | +        fl = {v: {p: int(cal["floors"][v][p]) for p in parts} for v, parts in VERDICTS.items()}
  71 | +    except (KeyError, TypeError, ValueError, OverflowError):
  72 | +        return None, "the line-up calibration has no readable measured_at or floors"
  73 | +    if at.tzinfo is None:
  74 | +        return None, "the line-up calibration's measured_at has no timezone: refused"
  75 | +    age = (now or datetime.now(timezone.utc)) - at
  76 | +    if age < -timedelta(minutes=HB.SKEW_MIN):
  77 | +        return None, f"the line-up calibration's measured_at ({cal['measured_at']}) is in the future: refused"
  78 | +    if "valid_h" not in cal:
  79 | +        return None, "the line-up calibration names no valid_h (hours, or null for none): refused"
  80 | +    vh = cal["valid_h"]
  81 | +    if vh is not None:
  82 | +        if type(vh) not in (int, float) or not 0 < vh <= HB.MAX_VALID_H:
  83 | +            return None, f"the line-up calibration's valid_h {vh!r} is not a number of hours in range: refused"
  84 | +        if age > timedelta(hours=vh):
  85 | +            return None, f"the line-up calibration is over {vh:g} h old (measured {cal['measured_at']}): re-run it"
  86 | +    if any(x < FLOOR_MIN for f in fl.values() for x in f.values()):
  87 | +        return None, f"a floor under {FLOOR_MIN} in the line-up calibration: refused"
  88 | +    return dict(fl, rater=cal["rater"], sha256=cal["sha256"], valid_h=vh), None
  89 | +
  90 | +
  91 | +def floors_for(verdict, backend, live, standard):
  92 | +    """(floors, "calibrated" | "standard") for one verdict given by `backend`: the calibrated floors only when the
  93 | +    calibrated rater gave it and the bar is live; else the standard floors."""
  94 | +    if live is not None and backend == live["rater"]:
  95 | +        return dict(live[verdict]), "calibrated"
  96 | +    return dict(standard[verdict]), "standard"
  97 | +
  98 | +
  99 | +def text(live):
 100 | +    if live is None:
 101 | +        return "no valid line-up calibration: the standard bar for every verdict"
 102 | +    c, k = live["clips_alone"], live["coherence"]
 103 | +    return (f"the calibrated line-up bar (ruling 116): clips-alone every clip >= {c['clip']}; coherence every clip >= "
 104 | +            f"{k['clip']} and the VO point >= {k['vo_point']}; on {live['rater']} only (calibration "
 105 | +            f"{live['sha256'][:12]})")
 106 | diff --git a/pipeline/lineup_calibration.json b/pipeline/lineup_calibration.json
 107 | new file mode 100644
 108 | index 0000000..205e249
 109 | --- /dev/null
 110 | +++ b/pipeline/lineup_calibration.json
 111 | @@ -0,0 +1,314 @@
 112 | +{
 113 | + "approved": {
 114 | +  "0c68b589": {
 115 | +   "clips_alone": [
 116 | +    {
 117 | +     "clips": {
 118 | +      "clip_01": 4,
 119 | +      "clip_02": 4
 120 | +     },
 121 | +     "flagged": [],
 122 | +     "passed_today": true,
 123 | +     "seed": 7,
 124 | +     "through_line": "Bitcoin provides financial freedom and security as a decentralized alternative to banks and governments that can mismanage or seize funds."
 125 | +    },
 126 | +    {
 127 | +     "clips": {
 128 | +      "clip_01": 4,
 129 | +      "clip_02": 4
 130 | +     },
 131 | +     "flagged": [],
 132 | +     "passed_today": true,
 133 | +     "seed": 8,
 134 | +     "through_line": "Bitcoin provides financial freedom and security by removing centralized control from governments, banks, and executives."
 135 | +    },
 136 | +    {
 137 | +     "clips": {
 138 | +      "clip_01": 4,
 139 | +      "clip_02": 4
 140 | +     },
 141 | +     "flagged": [],
 142 | +     "passed_today": true,
 143 | +     "seed": 9,
 144 | +     "through_line": "Bitcoin provides financial freedom and security by removing centralized control and risks from banks, governments, and single points of failure."
 145 | +    }
 146 | +   ],
 147 | +   "coherence": [
 148 | +    {
 149 | +     "clips": {
 150 | +      "clip_01": 5,
 151 | +      "clip_02": 3
 152 | +     },
 153 | +     "passed_today": false,
 154 | +     "seed": 7,
 155 | +     "through_line": "Bitcoin is not a partisan issue because no single owner or CEO controls its rules which are instead enforced by thousands of independent computers, providing financial freedom and liberty.",
 156 | +     "vo_point": 3
 157 | +    },
 158 | +    {
 159 | +     "clips": {
 160 | +      "clip_01": 4,
 161 | +      "clip_02": 3
 162 | +     },
 163 | +     "passed_today": false,
 164 | +     "seed": 8,
 165 | +     "through_line": "Bitcoin provides financial freedom and liberty because no single owner controls the network, with rules enforced by thousands of independent computers instead of a CEO, committee, or government.",
 166 | +     "vo_point": 3
 167 | +    },
 168 | +    {
 169 | +     "clips": {
 170 | +      "clip_01": 4,
 171 | +      "clip_02": 3
 172 | +     },
 173 | +     "passed_today": false,
 174 | +     "seed": 9,
 175 | +     "through_line": "No single owner controls the bitcoin network, making it a non-partisan provider of financial freedom and liberty unlike centralized banks.",
 176 | +     "vo_point": 4
 177 | +    }
 178 | +   ],
 179 | +   "label": "the published medley",
 180 | +   "pin": "ledger_20261113_183302/MOMENTS_PIN_ATTESTED.json",
 181 | +   "story_id": "moments-ledger_20261113_183302-0c68b589"
 182 | +  },
 183 | +  "13949b7c": {
 184 | +   "clips_alone": [
 185 | +    {
 186 | +     "clips": {
 187 | +      "clip_01": 3,
 188 | +      "clip_02": 4
 189 | +     },
 190 | +     "flagged": [
 191 | +      "hook -> clip_01"
 192 | +     ],
 193 | +     "passed_today": false,
 194 | +     "seed": 7,
 195 | +     "through_line": "Bitcoin shows economic resilience compared to traditional assets and attracts flowing capital."
 196 | +    },
 197 | +    {
 198 | +     "clips": {
 199 | +      "clip_01": 4,
 200 | +      "clip_02": 3
 201 | +     },
 202 | +     "flagged": [
 203 | +      "hook -> clip_01"
 204 | +     ],
 205 | +     "passed_today": false,
 206 | +     "seed": 8,
 207 | +     "through_line": "Bitcoin shows economic resilience versus traditional assets by holding value better and attracting capital flows."
 208 | +    },
 209 | +    {
 210 | +     "clips": {
 211 | +      "clip_01": 4,
 212 | +      "clip_02": 4
 213 | +     },
 214 | +     "flagged": [],
 215 | +     "passed_today": true,
 216 | +     "seed": 9,
 217 | +     "through_line": "Bitcoin demonstrates economic resilience by outperforming traditional assets and attracting capital flows from stocks, treasuries, and industry."
 218 | +    }
 219 | +   ],
 220 | +   "coherence": [
 221 | +    {
 222 | +     "clips": {
 223 | +      "clip_01": 5,
 224 | +      "clip_02": 4
 225 | +     },
 226 | +     "passed_today": true,
 227 | +     "seed": 7,
 228 | +     "through_line": "Bitcoin is a maturing asset whose durability and resilience in surviving market cycles better than tech stocks earns trust and draws capital flows.",
 229 | +     "vo_point": 4
 230 | +    },
 231 | +    {
 232 | +     "clips": {
 233 | +      "clip_01": 5,
 234 | +      "clip_02": 4
 235 | +     },
 236 | +     "passed_today": true,
 237 | +     "seed": 8,
 238 | +     "through_line": "Bitcoin demonstrates maturation as a durable asset by showing greater resilience than tech stocks in market drops while attracting capital flows from treasuries and the industry.",
 239 | +     "vo_point": 4
 240 | +    },
 241 | +    {
 242 | +     "clips": {
 243 | +      "clip_01": 5,
 244 | +      "clip_02": 4
 245 | +     },
 246 | +     "passed_today": true,
 247 | +     "seed": 9,
 248 | +     "through_line": "Bitcoin demonstrates maturation as a resilient asset by outlasting tech stock volatility and attracting capital flows from treasuries and industry.",
 249 | +     "vo_point": 4
 250 | +    }
 251 | +   ],
 252 | +   "label": "the sealed medley (approved 17:14 ET Nov 13)",
 253 | +   "pin": "ledger_20261113_215708/MOMENTS_PIN_LEDGER.json",
 254 | +   "story_id": "moments-ledger_20261113_215708-13949b7c"
 255 | +  },
 256 | +  "37c5b5f5": {
 257 | +   "clips_alone": [
 258 | +    {
 259 | +     "clips": {
 260 | +      "clip_01": 4,
 261 | +      "clip_02": 5
 262 | +     },
 263 | +     "flagged": [],
 264 | +     "passed_today": true,
 265 | +     "seed": 7,
 266 | +     "through_line": "Bitcoin operates independently of government authorities, enabling a true global free market."
 267 | +    },
 268 | +    {
 269 | +     "clips": {
 270 | +      "clip_01": 4,
 271 | +      "clip_02": 5
 272 | +     },
 273 | +     "flagged": [],
 274 | +     "passed_today": true,
 275 | +     "seed": 8,
 276 | +     "through_line": "Bitcoin operates independently of government authority and politics, enabling a true global free market."
 277 | +    },
 278 | +    {
 279 | +     "clips": {
 280 | +      "clip_01": 4,
 281 | +      "clip_02": 5
 282 | +     },
 283 | +     "flagged": [],
 284 | +     "passed_today": true,
 285 | +     "seed": 9,
 286 | +     "through_line": "Bitcoin operates independently of government and political authority, enabling a voluntary global free market."
 287 | +    }
 288 | +   ],
 289 | +   "coherence": [
 290 | +    {
 291 | +     "clips": {
 292 | +      "clip_01": 5,
 293 | +      "clip_02": 4
 294 | +     },
 295 | +     "passed_today": true,
 296 | +     "seed": 7,
 297 | +     "through_line": "Bitcoin has no authority by design rather than flaw, enabling a rulerless global free market with fixed rules that cannot be bent.",
 298 | +     "vo_point": 4
 299 | +    },
 300 | +    {
 301 | +     "clips": {
 302 | +      "clip_01": 5,
 303 | +      "clip_02": 4
 304 | +     },
 305 | +     "passed_today": true,
 306 | +     "seed": 8,
 307 | +     "through_line": "Bitcoin has no authority by design rather than as a flaw, enabling a rulerless system with unbending rules and a global free market.",
 308 | +     "vo_point": 4
 309 | +    },
 310 | +    {
 311 | +     "clips": {
 312 | +      "clip_01": 5,
 313 | +      "clip_02": 4
 314 | +     },
 315 | +     "passed_today": true,
 316 | +     "seed": 9,
 317 | +     "through_line": "Bitcoin is designed without any central authority or ruler, which is a feature not a flaw as it enables unbending rules and a global free market independent of politicians.",
 318 | +     "vo_point": 4
 319 | +    }
 320 | +   ],
 321 | +   "label": "the moments reference",
 322 | +   "pin": "fresh_20261112_050611/MOMENTS_PIN.json",
 323 | +   "story_id": "moments-fresh_20261112_050611-37c5b5f5"
 324 | +  },
 325 | +  "41f29b1f": {
 326 | +   "clips_alone": [
 327 | +    {
 328 | +     "clips": {
 329 | +      "clip_01": 4,
 330 | +      "clip_02": 3
 331 | +     },
 332 | +     "flagged": [],
 333 | +     "passed_today": false,
 334 | +     "seed": 7,
 335 | +     "through_line": "Bitcoin enables a global free market independent of politics and is highly undervalued."
 336 | +    },
 337 | +    {
 338 | +     "clips": {
 339 | +      "clip_01": 4,
 340 | +      "clip_02": 4
 341 | +     },
 342 | +     "flagged": [],
 343 | +     "passed_today": true,
 344 | +     "seed": 8,
 345 | +     "through_line": "Bitcoin enables a global free market by operating independently of political control and is significantly undervalued."
 346 | +    },
 347 | +    {
 348 | +     "clips": {
 349 | +      "clip_01": 4,
 350 | +      "clip_02": 3
 351 | +     },
 352 | +     "flagged": [],
 353 | +     "passed_today": false,
 354 | +     "seed": 9,
 355 | +     "through_line": "Bitcoin enables a global free market by operating independently of governments and is highly undervalued."
 356 | +    }
 357 | +   ],
 358 | +   "coherence": [
 359 | +    {
 360 | +     "clips": {
 361 | +      "clip_01": 4,
 362 | +      "clip_02": 3
 363 | +     },
 364 | +     "passed_today": false,
 365 | +     "seed": 7,
 366 | +     "through_line": "Bitcoin's overlooked value comes from creating a free global market that no government owns or can control, making political factors irrelevant and the asset undervalued.",
 367 | +     "vo_point": 4
 368 | +    },
 369 | +    {
 370 | +     "clips": {
 371 | +      "clip_01": 4,
 372 | +      "clip_02": 4
 373 | +     },
 374 | +     "passed_today": true,
 375 | +     "seed": 8,
 376 | +     "through_line": "Bitcoin's overlooked value stems from it being a free global market priced by everyone but controlled by no government, making political drama irrelevant and the asset highly undervalued.",
 377 | +     "vo_point": 4
 378 | +    },
 379 | +    {
 380 | +     "clips": {
 381 | +      "clip_01": 5,
 382 | +      "clip_02": 4
 383 | +     },
 384 | +     "passed_today": true,
 385 | +     "seed": 9,
 386 | +     "through_line": "Bitcoin's overlooked value comes from creating a free global market that no government owns or can control, making it independent of political drama and significantly undervalued.",
 387 | +     "vo_point": 4
 388 | +    }
 389 | +   ],
 390 | +   "label": "the protected medley",
 391 | +   "pin": "fresh_20261112_050611/MOMENTS_PIN_LY.json",
 392 | +   "story_id": "moments-fresh_20261112_050611-41f29b1f"
 393 | +  }
 394 | + },
 395 | + "floors": {
 396 | +  "clips_alone": {
 397 | +   "clip": 3
 398 | +  },
 399 | +  "coherence": {
 400 | +   "clip": 3,
 401 | +   "vo_point": 3
 402 | +  }
 403 | + },
 404 | + "floors_below_3": [],
 405 | + "how": "package.medley / package.coherence as production asks them, on the four approved line-ups as sealed in their pins, the hook on its calibrated bar (ruling 115), seeds 7, 8, 9",
 406 | + "joins_note": "at most one flagged join stays (L-y 2: one bridge); no approved line-up had more",
 407 | + "measured_at": "2026-11-15T20:31:20+00:00",
 408 | + "question_versions": {
 409 | +  "clips_alone": "0d410578ad75",
 410 | +  "coherence": "39e821a734ec"
 411 | + },
 412 | + "rater": "xai:grok-4.20-0309-reasoning",
 413 | + "seeds": [
 414 | +  7,
 415 | +  8,
 416 | +  9
 417 | + ],
 418 | + "sha256": "02440fd4e0c570fdd539938e141ec1cb0ef6549c9d37efbb8cb673387123fa11",
 419 | + "source": [
 420 | +  "tests/package/proof/clips116/CALIBRATION.json",
 421 | +  "tests/package/proof/clips116/COHERENCE.json"
 422 | + ],
 423 | + "valid_h": null,
 424 | + "valid_h_note": "ruling 116 (Q3, applied the hook's way, ruling 115): the floors come from ONE fixed source, tests/package/proof/clips116/ (CALIBRATION.json, COHERENCE.json), so they do not expire"
 425 | +}
 426 | diff --git a/pipeline/package.py b/pipeline/package.py
 427 | index 1afb4a7..6be44e4 100644
 428 | --- a/pipeline/package.py
 429 | +++ b/pipeline/package.py
 430 | @@ -1011,6 +1011,11 @@ rated here, its own job was judged on its own).
 431 |  3) Rate 1-5 whether the voice-over makes a point that the clips support (5 = a clear point, fully supported;
 432 |     1 = no point, or a point the clips do not support).
 433 |  Return ONLY this JSON object: {{"through_line": "...", "clips": {{{clip_keys}}}, "vo_point": 1}}"""
 434 | +MEDLEY_VERSION = hashlib.sha256(MEDLEY_PROMPT.encode()).hexdigest()[:12]         # RULING 116: the line-up bar is
 435 | +COHERENCE_VERSION = hashlib.sha256(COHERENCE_PROMPT.encode()).hexdigest()[:12]   # valid for exactly these questions
 436 | +STANDARD_LINEUP = {"clips_alone": {"clip": COHERENCE_MIN}, "coherence": {"clip": COHERENCE_MIN,
 437 | +                                                                         "vo_point": COHERENCE_MIN}}
 438 | +#   the standard bar: every verdict not given by the calibrated rater, and every verdict while the file is invalid
 439 |  
 440 |  
 441 |  def current_levels(sources, ctx, hours=24.0):
 442 | @@ -1439,6 +1444,43 @@ def _live_bar():
 443 |      return _LIVE[k]
 444 |  
 445 |  
 446 | +_LIVE_LINEUP = {}
 447 | +
 448 | +
 449 | +def _live_lineup_bar():
 450 | +    """RULING 116: the calibrated line-up bar (lineup_bar.bar for this build's two prompt versions), read once per state
 451 | +    of its file and per minute, like the hook's."""
 452 | +    import lineup_bar as LB
 453 | +    try:
 454 | +        k = (os.stat(LB.PATH).st_mtime_ns, int(time.time() // 60))
 455 | +    except OSError:
 456 | +        k = (None, int(time.time() // 60))
 457 | +    if k not in _LIVE_LINEUP:
 458 | +        _LIVE_LINEUP.clear()
 459 | +        _LIVE_LINEUP[k] = LB.bar({"clips_alone": MEDLEY_VERSION, "coherence": COHERENCE_VERSION})
 460 | +    return _LIVE_LINEUP[k]
 461 | +
 462 | +
 463 | +def lineup_floors(verdict, backend):
 464 | +    """RULING 116: (floors, which bar, the calibration's sha or None) for one line-up verdict given by `backend`: the
 465 | +    calibrated floors only when the calibrated rater gave it; else the standard bar (STANDARD_LINEUP)."""
 466 | +    import lineup_bar as LB
 467 | +    live, _ = _live_lineup_bar()
 468 | +    fl, which = LB.floors_for(verdict, backend, live, STANDARD_LINEUP)
 469 | +    return fl, which, (live or {}).get("sha256") if which == "calibrated" else None
 470 | +
 471 | +
 472 | +def lineup_bar_mark(med, coh):
 473 | +    """RULING 116 (Q3): what a package whose clips-alone AND coherence verdicts both passed on the calibrated bar carries
 474 | +    in its record and pin (outside the seal): the plain line, each verdict's floors and the calibration's sha, as they
 475 | +    were when it was judged. None when either verdict was judged on the standard bar."""
 476 | +    import lineup_bar as LB
 477 | +    if (med or {}).get("bar") != "calibrated" or (coh or {}).get("bar") != "calibrated":
 478 | +        return None
 479 | +    return {"note": LB.NOTE, "floors": {"clips_alone": med.get("floors"), "coherence": coh.get("floors")},
 480 | +            "calibration_sha256": med.get("calibration_sha256"), "ruling": "116"}
 481 | +
 482 | +
 483 |  def hook_bar_mark(live=None):
 484 |      """RULING 115 (2): what a package sealed on the calibrated bar carries in its record (and its pin, outside the seal):
 485 |      the plain line for the Telegram note, the floors and the calibration's sha. `live`: the bar the build judged its
 486 | @@ -1764,10 +1806,12 @@ def coherence(router, pk, writer_vendor, seed=7, writer_family=None, hook=None):
 487 |      v = dict(v, clips={**({labs[0]: own["rating"]} if own else {}), **v["clips"]},
 488 |               hook_own=own or {"rating": None, "why": "the hook carries no cached own-job rating (ruling 61): "
 489 |                                                       "fail closed"})
 490 | +    fl, which, csha = lineup_floors("coherence", r.backend)    # RULING 116: the calibrated rater's floors, or standard
 491 |      ok = own is not None and own["passes"] and _line_ok(v["through_line"]) and \
 492 | -        min([x for lb, x in v["clips"].items() if lb != labs[0]] + [v["vo_point"]]) >= COHERENCE_MIN   # ruling 115:
 493 | -    #   the hook's slot is its calibrated bar, every clip after it and the VO point COHERENCE_MIN, as before
 494 | -    return ok, dict(v, backend=r.backend, measured=True, replayed=bool(getattr(r, "replayed", False)))
 495 | +        min(x for lb, x in v["clips"].items() if lb != labs[0]) >= fl["clip"] and v["vo_point"] >= fl["vo_point"]
 496 | +    #   ruling 115: the hook's slot is its calibrated bar; the clips after it and the VO point the line-up bar's
 497 | +    return ok, dict(v, backend=r.backend, measured=True, bar=which, floors=fl, calibration_sha256=csha,
 498 | +                    replayed=bool(getattr(r, "replayed", False)))
 499 |  
 500 |  
 501 |  def _lineup_block(segs, ctx, a_by):
 502 | @@ -1826,11 +1870,13 @@ def medley(router, segs, ctx, writer_vendor, seed=7, writer_family=None):
 503 |               hook_own=own or {"rating": None, "why": "the hook carries no cached own-job rating (ruling 61): "
 504 |                                                       "fail closed"})
 505 |      flagged = [j for j in js if v["joins"][j]["followable"] is False]
 506 | +    fl, which, csha = lineup_floors("clips_alone", r.backend)   # RULING 116: the calibrated rater's floors, or standard
 507 |      ok = own is not None and own["passes"] and _line_ok(v["through_line"]) and \
 508 | -        min(x for lb, x in v["clips"].items() if lb != labs[0]) >= COHERENCE_MIN and len(flagged) <= LY_MAX_BRIDGES
 509 | -    #   ruling 115: the hook's slot is its calibrated bar; every clip after it COHERENCE_MIN, as before
 510 | -    return ok, dict(v, flagged=flagged, backend=r.backend, measured=True,
 511 | -                    replayed=bool(getattr(r, "replayed", False)), cached=bool(getattr(r, "cached", False)))
 512 | +        min(x for lb, x in v["clips"].items() if lb != labs[0]) >= fl["clip"] and len(flagged) <= LY_MAX_BRIDGES
 513 | +    #   ruling 115: the hook's slot is its calibrated bar; every clip after it the line-up bar's floor (ruling 116)
 514 | +    return ok, dict(v, flagged=flagged, backend=r.backend, measured=True, bar=which, floors=fl,
 515 | +                    calibration_sha256=csha, replayed=bool(getattr(r, "replayed", False)),
 516 | +                    cached=bool(getattr(r, "cached", False)))
 517 |  
 518 |  
 519 |  def last_clip_only(segs, med):
 520 | @@ -1844,7 +1890,8 @@ def last_clip_only(segs, med):
 521 |          return False
 522 |      rest = [j for j in med.get("flagged") or [] if j != joins(labs)[-1]]
 523 |      own = hook_own(segs[0])                              # ruling 115: the hook passes by its calibrated bar
 524 | -    return own is not None and own["passes"] and [lb for lb, x in cl.items() if lb != labs[0] and x < COHERENCE_MIN] \
 525 | +    floor = (med.get("floors") or STANDARD_LINEUP["clips_alone"])["clip"]   # ruling 116: the verdict's own bar
 526 | +    return own is not None and own["passes"] and [lb for lb, x in cl.items() if lb != labs[0] and x < floor] \
 527 |          == [labs[-1]] and len(rest) <= LY_MAX_BRIDGES
 528 |  
 529 |  
 530 | @@ -3167,8 +3214,11 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 531 |                          rec["why"] = (f"ruling 62: only the last clip fails ({cl.get(labs[-1])}): retried without it, "
 532 |                                        f"the seconds floor still met, before any swap")
 533 |                          continue
 534 | +                    floor = (med.get("floors") or STANDARD_LINEUP["clips_alone"])["clip"]   # ruling 116
 535 |                      if med.get("measured") and _line_ok(med.get("through_line")) and labs[0] in cl and \
 536 | -                            min(cl.values()) >= COHERENCE_MIN and len(med.get("flagged") or []) > LY_MAX_BRIDGES:
 537 | +                            (med.get("hook_own") or {}).get("passes") is True and \
 538 | +                            min(x for lb, x in cl.items() if lb != labs[0]) >= floor and \
 539 | +                            len(med.get("flagged") or []) > LY_MAX_BRIDGES:   # ruling 115: the hook's slot is its bar
 540 |                          order = reorder(segs, bad_pairs, judged, repeat_ok=exception is not None)
 541 |                          if order is not None:                 # RULING 63: joins before swaps
 542 |                              swapped = order
 543 | @@ -3176,10 +3226,10 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 544 |                                            f"flagged: the same clips reordered, before any swap")
 545 |                              continue
 546 |                      weak = {by_lab[lb]["moment_id"] for lb, x in cl.items()
 547 | -                            if lb in by_lab and x < COHERENCE_MIN}      # ruling 61: the hook's is its cached rating
 548 | +                            if lb in by_lab and x < floor}      # ruling 116: the verdict's own floor
 549 |                      if len(med.get("flagged") or []) > LY_MAX_BRIDGES:
 550 |                          weak |= {by_lab[j.split(" -> ")[1]]["moment_id"] for j in med["flagged"][1:]}
 551 | -                    hook_weak = segs[0]["moment_id"] in weak
 552 | +                    hook_weak = (med.get("hook_own") or {}).get("passes") is not True   # ruling 115: its own bar
 553 |                      weak.discard(segs[0]["moment_id"])    # ruling 59 (c): the line-up is built AROUND its hook
 554 |                      if not med.get("measured") or not weak:
 555 |                          rec["why"] = ("the hook carries no own-job rating at the bar (ruling 61); the angle is written "
 556 | @@ -3480,9 +3530,12 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 557 |                                              last_resort=pin_last_resort(pk))      # RULING 102: on the pin
 558 |                      if not ok_c:
 559 |                          tl = coh.get("through_line") if isinstance(coh.get("through_line"), str) else ""
 560 | +                        cfl = coh.get("floors") or STANDARD_LINEUP["coherence"]   # ruling 116: its own bar
 561 |                          if coh.get("measured") and type(coh.get("vo_point")) is int and \
 562 | -                                coh["vo_point"] < COHERENCE_MIN and min(coh["clips"].values()) >= COHERENCE_MIN and \
 563 | -                                len(tl.split()) >= 4 and not NO_LINE.search(tl):
 564 | +                                coh["vo_point"] < cfl["vo_point"] and (coh.get("hook_own") or {}).get("passes") is True \
 565 | +                                and min(x for lb, x in coh["clips"].items() if lb != pk["segments"][0]["label"]) >= \
 566 | +                                cfl["clip"] and \
 567 | +                                len(tl.split()) >= 4 and not NO_LINE.search(tl):   # ruling 115: the hook's slot
 568 |                              take_failed += 1                  # the takeaway's point failed its coherence gate
 569 |                              extra = _redo([{"slot": "takeaway", "rule": "COHERENCE", "detail":
 570 |                                              f"a blind viewer rated the takeaway's point {coh['vo_point']} of 5 for "
 571 | @@ -3493,7 +3546,7 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 572 |                              t_alone, last_fid, last_rw65 = True, fid, bool(att.get("rewrite"))
 573 |                              continue                          # the clips hold; only the takeaway's point is weak
 574 |                          weak = {sg["moment_id"] for sg in pk["segments"][1:]
 575 | -                                if (coh.get("clips") or {}).get(sg["label"], COHERENCE_MIN) < COHERENCE_MIN}
 576 | +                                if (coh.get("clips") or {}).get(sg["label"], cfl["clip"]) < cfl["clip"]}
 577 |                          dropped |= weak
 578 |                          relined = bool(weak)
 579 |                          rec["why"] = ("coherence with the takeaway below 4 or no through-line: " +
 580 | @@ -3546,6 +3599,9 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 581 |      out["package"] = out["packages"][0] if out["packages"] else None
 582 |      if out["package"]:                                   # RULING 115 (2): a package sealed on the calibrated bar says so
 583 |          out["package"]["hook_bar"] = hook_bar_mark(live)   # the bar its hooks were judged on (the hook stage's)
 584 | +        lm = lineup_bar_mark(*(lambda c: (c.get("medley"), c.get("coherence")))(out["package"].get("checks") or {}))
 585 | +        if lm:                                           # RULING 116 (Q3): and its line-up, when both verdicts were
 586 | +            out["package"]["lineup_bar"] = lm            # judged on the calibrated line-up bar
 587 |      if candidate is not None:                             # RULING 66: what became of the candidate
 588 |          t_ = next((t for t in out["tried"] if t.get("candidate") is not None), {})
 589 |          out["candidate"]["result"] = t_.get("result") or t_.get("why") or out.get("why_none") or "not tried"
 590 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
 591 | index 03990bc..99f6cae 100644
 592 | --- a/pipeline/package_pin.py
 593 | +++ b/pipeline/package_pin.py
 594 | @@ -497,6 +497,8 @@ def to_pin(pk, run_name):
 595 |                                  "gates": pk["gates"],
 596 |                                  **({"hook_bar": pk["hook_bar"]} if pk.get("hook_bar") else {}),   # ruling 115 (2): the
 597 |                                  #   calibrated hook bar's plain line for the Telegram note, floors and sha (outside the seal)
 598 | +                                **({"lineup_bar": pk["lineup_bar"]} if pk.get("lineup_bar") else {}),   # ruling 116 (Q3):
 599 | +                                #   the line-up's, when both its verdicts passed on the calibrated bar (outside the seal)
 600 |                                  **({"btc_screen": pk["btc_screen"]} if pk.get("btc_screen") is not None else {}),
 601 |                                  **({"formats": fmts} if fmts is not None else {}),   # ruling 93 amended (sealed)
 602 |                                  "checks": {"vo_fidelity_ok": True, "context_integrity_ok": True,
 603 | diff --git a/tests/package/conftest.py b/tests/package/conftest.py
 604 | index 0e67912..09cdbb7 100644
 605 | --- a/tests/package/conftest.py
 606 | +++ b/tests/package/conftest.py
 607 | @@ -3,7 +3,9 @@ PINNED here: the floors ruling 115's calibration measured at 13:07 ET Nov 15 (sc
 608 |  rigs' own rater name, "xai:grok". A daily re-calibration may move production's floors; it never moves a rig's
 609 |  verdict. The fixture patches only package._live_bar: hook_bar's own functions, which tests/package/test_hook_bar.py
 610 |  tests on files of its own (and that the live file's floors are derived from their source), are never touched. A test
 611 | -class that needs production's calibration file sets `real_hook_bar = True`."""
 612 | +class that needs production's calibration file sets `real_hook_bar = True`. RULING 116: the same for the line-up bar
 613 | +(package._live_lineup_bar): RIG_LINEUP's floors (every clip after the hook >= 3, the VO point >= 3) for the rigs'
 614 | +rater, so a rig verdict given as "xai:grok" is judged on the calibrated bar and any other back-end on the standard."""
 615 |  import os
 616 |  import sys
 617 |  
 618 | @@ -15,6 +17,7 @@ import package as PK  # noqa: E402
 619 |  
 620 |  RIG_RATER = "xai:grok"
 621 |  RIG_FLOORS = {"scroll": 3, "alone": 4, "setup": 3}
 622 | +RIG_LINEUP = {"clips_alone": {"clip": 3}, "coherence": {"clip": 3, "vo_point": 3}}   # RULING 116's floors, pinned
 623 |  
 624 |  
 625 |  def rig_bar():
 626 | @@ -22,11 +25,16 @@ def rig_bar():
 627 |              "question_version": PK.HOOK_VERSION, "seed": PK.HOOK_SEED, "measured_at": "2026-11-15T18:07:52+00:00"}
 628 |  
 629 |  
 630 | +def rig_lineup_bar():
 631 | +    return dict({k: dict(v) for k, v in RIG_LINEUP.items()}, rater=RIG_RATER, sha256="l" * 64, valid_h=None)
 632 | +
 633 | +
 634 |  @pytest.fixture(autouse=True)
 635 |  def _rig_hook_bar(request, monkeypatch):
 636 |      if getattr(request.cls, "real_hook_bar", False):
 637 |          yield
 638 |          return
 639 | -    bar = rig_bar()
 640 | +    bar, lbar = rig_bar(), rig_lineup_bar()
 641 |      monkeypatch.setattr(PK, "_live_bar", lambda: (bar, None))
 642 | +    monkeypatch.setattr(PK, "_live_lineup_bar", lambda: (lbar, None))   # ruling 116: the rigs' line-up bar
 643 |      yield
 644 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
 645 | index 881884a..e4d2206 100644
 646 | --- a/tests/package/proof_ledger.py
 647 | +++ b/tests/package/proof_ledger.py
 648 | @@ -452,6 +452,9 @@ def main(argv=None):
 649 |      live, live_why = PK.hook_live_bar()          # RULING 115: the bar in every build line, its floors and its sha
 650 |      say(f"  RULING 115: {HB.text(live)}; the hook list {router.chain('coherence_verdict', 'hook')}"
 651 |          + (f" [{live_why}]" if live_why else ""))
 652 | +    import lineup_bar as LNB                     # RULING 116: the line-up bar, named in every build line too
 653 | +    lbar, lbar_why = PK._live_lineup_bar()
 654 | +    say(f"  RULING 116: {LNB.text(lbar)}" + (f" [{lbar_why}]" if lbar_why else ""))
 655 |      say(f"  RULING 100 (deadlines follow the model, table of {(router.deadlines or {}).get('computed_at')}): "
 656 |          f"{DT.text(router.deadlines, applies=applied(router)) or 'no row applies: each gateway keeps its number'}")
 657 |      spent0 = router.spent()                      # ruling 48: the running total, vendor-reported (+ estimates where none)
 658 | diff --git a/tests/package/test_lineup_bar.py b/tests/package/test_lineup_bar.py
 659 | new file mode 100644
 660 | index 0000000..86a63d3
 661 | --- /dev/null
 662 | +++ b/tests/package/test_lineup_bar.py
 663 | @@ -0,0 +1,158 @@
 664 | +#!/usr/bin/env python3
 665 | +"""RULING 116 (Q3, ruling 106's default APPLY): THE CALIBRATED LINE-UP BAR (pipeline/lineup_bar.py). Each verdict's
 666 | +parts (clips-alone: every clip after the hook; coherence: every clip after the hook and the VO point) are at least the
 667 | +lowest value they took on PBX's four approved line-ups (seeds 7, 8, 9, Grok), never under 3; ONLY for a verdict the
 668 | +calibrated rater gave; every other verdict, and every verdict while the file is invalid, stays on the standard bar."""
 669 | +import copy
 670 | +import json
 671 | +import os
 672 | +import sys
 673 | +import tempfile
 674 | +import unittest
 675 | +from datetime import datetime, timedelta, timezone
 676 | +
 677 | +HERE = os.path.dirname(os.path.abspath(__file__))
 678 | +REPO = os.path.dirname(os.path.dirname(HERE))
 679 | +for _p in ("pipeline", "tests/package"):
 680 | +    sys.path.insert(0, os.path.join(REPO, _p))
 681 | +import hook_bar as HB  # noqa: E402
 682 | +import lineup_bar as LB  # noqa: E402
 683 | +import package as PK  # noqa: E402
 684 | +import package_pin as PP  # noqa: E402
 685 | +
 686 | +AT = datetime(2026, 11, 15, 20, 33, 0, tzinfo=timezone.utc)
 687 | +G = "xai:grok-4.20-0309-reasoning"
 688 | +V = {"clips_alone": "mv", "coherence": "cv"}
 689 | +
 690 | +
 691 | +def runs(ca=((4, 3), (4, 4)), co=(((5, 3), 3), ((4, 4), 4))):
 692 | +    return {"clips_alone": [{"clips": {"clip_01": a, "clip_02": b}} for a, b in ca],
 693 | +            "coherence": [{"clips": {"clip_01": a, "clip_02": b}, "vo_point": v} for (a, b), v in co]}
 694 | +
 695 | +
 696 | +def cal(**kw):
 697 | +    fl, low = LB.floors_from(runs())
 698 | +    return dict({"rater": G, "question_versions": dict(V), "measured_at": AT.isoformat(), "valid_h": None,
 699 | +                 "floors": fl, "floors_below_3": low}, **kw)
 700 | +
 701 | +
 702 | +class TestFloors(unittest.TestCase):
 703 | +    def test_each_part_is_its_lowest_value_never_under_3(self):
 704 | +        self.assertEqual(LB.floors_from(runs()), ({"clips_alone": {"clip": 3}, "coherence": {"clip": 3, "vo_point": 3}},
 705 | +                                                  []))
 706 | +        fl, low = LB.floors_from(runs(ca=((4, 4), (5, 4)), co=(((5, 4), 4), ((4, 4), 5))))
 707 | +        self.assertEqual(fl, {"clips_alone": {"clip": 4}, "coherence": {"clip": 4, "vo_point": 4}})
 708 | +        fl, low = LB.floors_from(runs(ca=((2, 4),), co=(((4, 4), 1),)))
 709 | +        self.assertEqual((fl["clips_alone"]["clip"], fl["coherence"]["vo_point"]), (3, 3))
 710 | +        self.assertEqual(low, ["clips_alone clip 2 (stopped at 3)", "coherence vo_point 1 (stopped at 3)"])
 711 | +
 712 | +    def test_a_run_without_its_ratings_measures_nothing(self):
 713 | +        for bad in ({"clips_alone": [], "coherence": runs()["coherence"]},
 714 | +                    dict(runs(), coherence=[{"clips": {"clip_01": 4}}]),
 715 | +                    dict(runs(), clips_alone=[{"clips": {}}])):
 716 | +            with self.assertRaises(ValueError):
 717 | +                LB.floors_from(bad)
 718 | +
 719 | +
 720 | +class TestTheFile(unittest.TestCase):
 721 | +    def setUp(self):
 722 | +        self.d = tempfile.TemporaryDirectory()
 723 | +        self.path = os.path.join(self.d.name, "lineup_calibration.json")
 724 | +
 725 | +    def tearDown(self):
 726 | +        self.d.cleanup()
 727 | +
 728 | +    def test_valid_only_sealed_for_its_versions_and_rater_and_within_its_validity(self):
 729 | +        HB.write(cal(), self.path)
 730 | +        live, why = LB.bar(V, now=AT + timedelta(days=30), path=self.path)          # valid_h null: no expiry
 731 | +        self.assertEqual((live["clips_alone"], live["coherence"], live["rater"], why),
 732 | +                         ({"clip": 3}, {"clip": 3, "vo_point": 3}, G, None))
 733 | +        self.assertIn("clips-alone every clip >= 3; coherence every clip >= 3 and the VO point >= 3", LB.text(live))
 734 | +        for k, v in (("clips_alone", "another"), ("coherence", "another")):
 735 | +            live, why = LB.bar(dict(V, **{k: v}), now=AT, path=self.path)
 736 | +            self.assertIsNone(live)
 737 | +            self.assertIn("standard bar until it is re-run", why)
 738 | +        bad = (cal(rater=""), cal(valid_h=24), cal(measured_at="2026-11-15T20:33:00"),
 739 | +               cal(floors={"clips_alone": {"clip": 2}, "coherence": {"clip": 3, "vo_point": 3}}))
 740 | +        for c in bad:
 741 | +            HB.write(c, self.path)
 742 | +            self.assertIsNone(LB.bar(V, now=AT + timedelta(days=2), path=self.path)[0], c.get("valid_h"))
 743 | +        c = cal()
 744 | +        del c["valid_h"]
 745 | +        HB.write(c, self.path)
 746 | +        self.assertIn("names no valid_h", LB.bar(V, now=AT, path=self.path)[1])
 747 | +        HB.write(cal(), self.path)
 748 | +        live, why = LB.bar(V, now=AT - timedelta(minutes=6), path=self.path)
 749 | +        self.assertIn("in the future", why)
 750 | +        with open(self.path) as f:
 751 | +            body = json.load(f)
 752 | +        body["floors"]["clips_alone"]["clip"] = 2                                 # a hand edit: the seal breaks
 753 | +        with open(self.path, "w") as f:
 754 | +            json.dump(body, f)
 755 | +        self.assertIsNone(LB.bar(V, now=AT, path=self.path)[0])
 756 | +
 757 | +    def test_the_floors_only_for_the_calibrated_raters_own_verdict(self):
 758 | +        HB.write(cal(), self.path)
 759 | +        live, _ = LB.bar(V, now=AT, path=self.path)
 760 | +        std = PK.STANDARD_LINEUP
 761 | +        self.assertEqual(LB.floors_for("coherence", G, live, std), ({"clip": 3, "vo_point": 3}, "calibrated"))
 762 | +        self.assertEqual(LB.floors_for("coherence", "heimdall:deepseek/deepseek-v4.1-flash", live, std),
 763 | +                         ({"clip": 4, "vo_point": 4}, "standard"))
 764 | +        self.assertEqual(LB.floors_for("clips_alone", G, None, std), ({"clip": 4}, "standard"))   # no valid bar
 765 | +
 766 | +
 767 | +class TestTheMark(unittest.TestCase):
 768 | +    """Q3: a package whose two verdicts both passed on the calibrated bar says so in its record and pin, outside the
 769 | +    seal; one judged on the standard bar carries no mark."""
 770 | +
 771 | +    def test_both_verdicts_calibrated_or_no_mark_and_the_pin_carries_it_outside_the_seal(self):
 772 | +        import test_angles as TA
 773 | +        med = {"bar": "calibrated", "floors": {"clip": 3}, "calibration_sha256": "l" * 64}
 774 | +        coh = {"bar": "calibrated", "floors": {"clip": 3, "vo_point": 3}, "calibration_sha256": "l" * 64}
 775 | +        m = PK.lineup_bar_mark(med, coh)
 776 | +        self.assertEqual((m["note"], m["floors"], m["ruling"]),
 777 | +                         ("line-up passed on the calibrated bar", {"clips_alone": {"clip": 3},
 778 | +                                                                   "coherence": {"clip": 3, "vo_point": 3}}, "116"))
 779 | +        self.assertIsNone(PK.lineup_bar_mark(dict(med, bar="standard"), coh))
 780 | +        self.assertIsNone(PK.lineup_bar_mark(med, None))
 781 | +        base = TA.TestPinAndTruth.pk(None)
 782 | +        plain = PP.to_pin(copy.deepcopy(base), "r")["moments_package"]
 783 | +        marked = PP.to_pin(dict(copy.deepcopy(base), lineup_bar=m), "r")["moments_package"]
 784 | +        self.assertNotIn("lineup_bar", plain)
 785 | +        self.assertEqual(marked["lineup_bar"]["note"], "line-up passed on the calibrated bar")
 786 | +        self.assertEqual(marked["package_sha256"], plain["package_sha256"])        # outside the seal
 787 | +
 788 | +
 789 | +class TestTheLiveCalibration(unittest.TestCase):
 790 | +    """The file production reads (pipeline/lineup_calibration.json): its floors derive from their source
 791 | +    (tests/package/proof/clips116/), it is valid for production's two prompts, its rater is the first of both
 792 | +    verdicts' production lists, and it does not expire."""
 793 | +    real_hook_bar = True
 794 | +
 795 | +    def test_its_floors_are_its_sources_lowest_ratings(self):
 796 | +        c, why = HB.load(LB.PATH)
 797 | +        self.assertIsNone(why)
 798 | +        proof = os.path.join(REPO, "tests", "package", "proof", "clips116")
 799 | +        with open(os.path.join(proof, "CALIBRATION.json")) as f:
 800 | +            ca = json.load(f)
 801 | +        with open(os.path.join(proof, "COHERENCE.json")) as f:
 802 | +            co = json.load(f)
 803 | +        src = {"clips_alone": [r for x in ca["lineups"].values() for r in x["runs"]],
 804 | +               "coherence": [r for x in co["packages"].values() for r in x["runs"]]}
 805 | +        self.assertTrue(all(r.get("backend") == c["rater"] for v in src.values() for r in v))
 806 | +        self.assertEqual(LB.floors_from(src), (c["floors"], c["floors_below_3"]))
 807 | +        self.assertEqual(max(len(r["flagged"]) for r in src["clips_alone"]), PK.LY_MAX_BRIDGES)   # joins: the law's
 808 | +
 809 | +    def test_it_is_live_for_production_and_does_not_expire(self):
 810 | +        import providers as P
 811 | +        c, _ = HB.load(LB.PATH)
 812 | +        versions = {"clips_alone": PK.MEDLEY_VERSION, "coherence": PK.COHERENCE_VERSION}
 813 | +        live, why = LB.bar(versions, now=datetime.fromisoformat(c["measured_at"]) + timedelta(days=30))
 814 | +        self.assertEqual((live is not None, why), (True, None))
 815 | +        r = P.Router(env_path="/nonexistent", routing="heimdall_first")
 816 | +        for kind in ("clips_alone", "coherence"):
 817 | +            self.assertEqual(r.chain("coherence_verdict", kind)[0], c["rater"], kind)
 818 | +
 819 | +
 820 | +if __name__ == "__main__":
 821 | +    unittest.main()
 822 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 823 | index 33db082..62c59db 100644
 824 | --- a/tests/package/test_medley.py
 825 | +++ b/tests/package/test_medley.py
 826 | @@ -552,8 +552,9 @@ class Rig:
 827 |                   spend=None, no_hook=(), a_fail=None, unavailable=(), angle_from=None, write_from=None,
 828 |                   trim_fail=(), hooks=None, hook_err=None, verdicts=None, follow_up=None, fids=None, lines=None,
 829 |                   cached=False, candidate=None, visuals=None, registered=None, lock_check=None, values=None,
 830 | -                 real_value=False, caption=None):
 831 | +                 real_value=False, caption=None, coherences=None):
 832 |          import providers as P
 833 | +        self.coherences = list(coherences or [])         # RULING 116: (ok, every clip's rating, the VO point) in order
 834 |          self.values, self.value_calls = list(values or []), []   # ruling 91: the value verdicts' answers, in order
 835 |          self.real_value = real_value                       # ruling 91: package.takeaway_value itself, on the router
 836 |          self.caption = caption or "nobody bends these rules"   # 07:30 (C): a caption that fails its own gates
 837 | @@ -630,14 +631,33 @@ class Rig:
 838 |                                     "why": f"why {m['moment_id']}", "backend": "xai:grok", "cached": False}
 839 |          return out, None
 840 |  
 841 | +    def coherence(self, router, pk, *a, **k):
 842 | +        """As the real coherence() answers: the clips after the hook and the VO point (self.coherences, default all 5
 843 | +        and a pass), the hook's slot its own rating, and the line-up bar it was judged on (ruling 116)."""
 844 | +        own = PK.hook_own(k.get("hook"))
 845 | +        ok, clip, vo = self.coherences.pop(0) if self.coherences else (True, 5, 5)
 846 | +        fl, which, csha = PK.lineup_floors("coherence", "xai:grok")
 847 | +        segs = pk["segments"]
 848 | +        return ok, {"through_line": "Nobody gets to bend the rules.",
 849 | +                    "clips": dict({segs[0]["label"]: (own or {}).get("rating")}, **{sg["label"]: clip for sg in segs[1:]}),
 850 | +                    "vo_point": vo, "backend": "xai:grok", "measured": True, "replayed": False,
 851 | +                    "hook_own": own or {"rating": None}, "floors": fl, "bar": which, "calibration_sha256": csha}
 852 | +
 853 |      def medley(self, router, segs, ctx_, wv, seed=7, writer_family=None):
 854 | +        """As the real medley() answers: the verdict, its flagged joins, the hook's own-job record (ruling 115) and
 855 | +        the line-up bar it was judged on (ruling 116: the rigs' rater, so the calibrated floors)."""
 856 |          self.medley_calls.append([m["moment_id"] for m in segs])
 857 |          self.seeds.append(("medley", seed))
 858 |          ok, flagged, ratings, line = self.medleys.pop(0)
 859 |          labs = PK.labels(len(segs))
 860 |          v = verdict(labs, flagged, ratings, line)
 861 | +        own = PK.hook_own(segs[0])
 862 | +        if "hook" not in (ratings or {}):                  # the hook's slot holds its own rating, as medley() writes it
 863 | +            v["clips"]["hook"] = (own or {}).get("rating")
 864 | +        fl, which, csha = PK.lineup_floors("clips_alone", "xai:grok")
 865 |          return ok, dict(v, flagged=list(flagged), backend="xai:grok", measured=True, replayed=False,
 866 | -                        cached=self.cached)
 867 | +                        cached=self.cached, hook_own=own or {"rating": None},
 868 | +                        bar=which, floors=fl, calibration_sha256=csha)
 869 |  
 870 |      def write(self, router, angle_, segs, ctx_, a_by, join=None, extra="", seed=7, avoid_vendor=None, other=()):
 871 |          if join is not None and not other and PK.bridge_budget(sum(m["duration_s"] for m in segs)) is None:
 872 | @@ -709,10 +729,7 @@ class Rig:
 873 |              "hook_onset_for": self.onset,
 874 |              "hook_ratings": self.rate_hooks,
 875 |              "takeaway_value": self.value,                  # ruling 91 (medley half)
 876 | -            "coherence": lambda router, pk, *a, **k: (True, {"through_line": "Nobody gets to bend the rules.",
 877 | -                                                             "clips": {sg["label"]: 5 for sg in pk["segments"]},
 878 | -                                                             "vo_point": 5, "backend": "xai:grok", "measured": True,
 879 | -                                                             "replayed": False}),
 880 | +            "coherence": self.coherence,
 881 |          }
 882 |          if self.real_value:                                # ruling 91: the real verdict, on the fake router
 883 |              del stubs["takeaway_value"]
 884 | @@ -1583,6 +1600,115 @@ class TestRuling59HookFirst(unittest.TestCase):
 885 |          self.assertEqual(rig.medley_calls, [])
 886 |  
 887 |  
 888 | +class TestRuling116LineupBar(unittest.TestCase):
 889 | +    """RULING 116 (Q3, ruling 106's default APPLY): the clips-alone and coherence verdicts judged on the calibrated
 890 | +    line-up bar (the rigs': every clip after the hook >= 3, the VO point >= 3) when the calibrated rater gave them, on
 891 | +    the standard bar (>= 4) otherwise; the hook's slot is its own bar everywhere (ruling 115)."""
 892 | +    LABS = ["hook", "clip_01", "clip_02"]
 893 | +    SEGS = [dict(pm("h", "A", 12.0), hook_rating={"scroll": 3, "alone": 4, "setup": 3, "backend": "xai:grok"}),
 894 | +            pm("x", "B", 14.0), pm("y", "C", 13.0)]
 895 | +
 896 | +    @staticmethod
 897 | +    def router(reply, backend):
 898 | +        import providers as P
 899 | +        r = Canned(coherence_verdict=[reply])
 900 | +        call = r.call
 901 | +
 902 | +        def as_backend(role, *a, **k):
 903 | +            x = call(role, *a, **k)
 904 | +            return P.Reply(x.text, backend, backend.split(":")[0])
 905 | +        r.call = as_backend
 906 | +        return r
 907 | +
 908 | +    def test_clips_alone_a_clip_at_3_passes_only_on_the_calibrated_raters_verdict(self):
 909 | +        rep = reply(self.LABS, ratings={"clip_02": 3})
 910 | +        ok, v = PK.medley(self.router(rep, "xai:grok"), self.SEGS, E.Context(NOW, REG), set())
 911 | +        self.assertEqual((ok, v["bar"], v["floors"], v["clips"]["hook"]), (True, "calibrated", {"clip": 3}, 3))
 912 | +        ok, v = PK.medley(self.router(rep, "google:gemini-2.5-pro"), self.SEGS, E.Context(NOW, REG), set())
 913 | +        self.assertEqual((ok, v["bar"], v["floors"]), (False, "standard", {"clip": 4}))     # Plan B: the standard bar
 914 | +        ok, v = PK.medley(self.router(reply(self.LABS, ratings={"clip_02": 2}), "xai:grok"), self.SEGS,
 915 | +                          E.Context(NOW, REG), set())
 916 | +        self.assertFalse(ok)                                                             # under the floor
 917 | +        ok, v = PK.medley(self.router(reply(self.LABS, flagged=["hook -> clip_01", "clip_01 -> clip_02"]),
 918 | +                                      "xai:grok"), self.SEGS, E.Context(NOW, REG), set())
 919 | +        self.assertFalse(ok)                                                             # joins: the law's one
 920 | +        ok, v = PK.medley(self.router(reply(self.LABS, line="none"), "xai:grok"), self.SEGS, E.Context(NOW, REG), set())
 921 | +        self.assertFalse(ok)                                                             # a through-line, always
 922 | +
 923 | +    def test_coherence_a_clip_or_vo_point_at_3_passes_only_on_the_calibrated_raters_verdict(self):
 924 | +        pk = {"title": "t", "caption": "c", "vo": {"intro": None, "bridges": ["No ruler, just rules."],
 925 | +                                                  "bridges_after_clip": [2], "signoff": "S"},
 926 | +              "segments": [{"label": lb, "channel": ch, "text": f"Bitcoin {lb}."}
 927 | +                           for lb, ch in zip(self.LABS, "ABC")]}
 928 | +        rep = {"through_line": "Nobody can change the rules of Bitcoin.", "clips": {"clip_01": 3, "clip_02": 4},
 929 | +               "vo_point": 3}
 930 | +        ok, v = PK.coherence(self.router(rep, "xai:grok"), pk, set(), hook=self.SEGS[0])
 931 | +        self.assertEqual((ok, v["bar"], v["floors"]), (True, "calibrated", {"clip": 3, "vo_point": 3}))
 932 | +        ok, v = PK.coherence(self.router(rep, "heimdall:deepseek/deepseek-v4.1-flash"), pk, set(), hook=self.SEGS[0])
 933 | +        self.assertEqual((ok, v["bar"]), (False, "standard"))
 934 | +        ok, v = PK.coherence(self.router(dict(rep, vo_point=2), "xai:grok"), pk, set(), hook=self.SEGS[0])
 935 | +        self.assertFalse(ok)
 936 | +
 937 | +    def test_ruling_62_reads_the_verdicts_own_floor(self):
 938 | +        segs = self.SEGS + [pm("z", "D", 9.0)]
 939 | +        med = dict(verdict(PK.labels(4), ratings={"hook": 3, "clip_01": 3, "clip_02": 3, "clip_03": 2}),
 940 | +                   measured=True, flagged=[], floors={"clip": 3})
 941 | +        self.assertTrue(PK.last_clip_only(segs, med))                                   # only the last under 3
 942 | +        self.assertFalse(PK.last_clip_only(segs, dict(med, floors={"clip": 4})))        # the standard bar: all fail
 943 | +        self.assertFalse(PK.last_clip_only(segs, {k: x for k, x in med.items() if k != "floors"}))   # no floors: 4
 944 | +
 945 | +    def test_ruling_63_reorders_a_line_up_whose_hook_sits_at_its_floors(self):
 946 | +        """The hook's own rating (3, at its floors) never blocks ruling 63: the clips after it pass and two joins
 947 | +        are flagged, so the same clips are reordered (before ruling 115 / 116 the hook's 3 sat in the min)."""
 948 | +        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]
 949 | +        from unittest import mock
 950 | +        for bar in ("calibrated", "standard"):            # the standard bar's floor 4 is where the hook's 3 blocked
 951 | +            with mock.patch.object(PK, "_live_lineup_bar", lambda: (None, "none")) if bar == "standard" else \
 952 | +                    mock.patch.object(PK, "COHERENCE_MIN", PK.COHERENCE_MIN):
 953 | +                rig = Rig(ms, ["h", "x", "y"], [(False, ["hook -> clip_01", "clip_01 -> clip_02"], None, Rig.LINE),
 954 | +                                                (True, [], None, Rig.LINE)], [None], hooks={"h": (3, 4, 3)})
 955 | +                out = rig.run()
 956 | +            self.assertEqual(rig.medley_calls, [["h", "x", "y"], ["h", "y", "x"]], bar)
 957 | +            self.assertIn("ruling 63", out["tried"][0]["why"], bar)
 958 | +            self.assertIsNotNone(out["package"], bar)
 959 | +
 960 | +    def test_the_takeaway_alone_is_rewritten_when_only_its_point_is_weak_with_a_hook_at_its_floors(self):
 961 | +        """Coherence fails on the VO point alone (2), the clips pass the calibrated floor and the hook sits at its
 962 | +        floors (rating 3): the takeaway is written again (it was the next angle while the hook's 3 sat in the min)."""
 963 | +        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]
 964 | +        from unittest import mock
 965 | +        for bar, clip in (("calibrated", 3), ("standard", 4)):   # the standard bar's 4: the hook's 3 blocked it
 966 | +            with mock.patch.object(PK, "_live_lineup_bar", lambda: (None, "none")) if bar == "standard" else \
 967 | +                    mock.patch.object(PK, "COHERENCE_MIN", PK.COHERENCE_MIN):
 968 | +                rig = Rig(ms, ["h", "x", "y"], [(True, [], None, Rig.LINE)], [None, None], hooks={"h": (3, 4, 3)},
 969 | +                          coherences=[(False, clip, 2), (True, 4, 4)])
 970 | +                out = rig.run()
 971 | +            self.assertEqual(len(rig.write_calls), 2, bar)                               # the takeaway again
 972 | +            self.assertIsNotNone(out["package"], bar)
 973 | +
 974 | +    def test_after_a_failed_verdict_only_the_clips_under_its_own_floor_are_swapped(self):
 975 | +        """A clip at 3 passes the calibrated floor: when the line-up fails on another clip (2), only that one is
 976 | +        dropped and swapped, never the clip at 3."""
 977 | +        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]
 978 | +        rig = Rig(ms, ["h", "x", "y"], [(False, [], {"clip_01": 3, "clip_02": 2}, Rig.LINE)], [None])
 979 | +        out = rig.run()
 980 | +        self.assertIn("dropped ['y']", out["tried"][0]["why"])
 981 | +
 982 | +    def test_the_mark_on_a_package_whose_two_verdicts_passed_on_the_calibrated_bar(self):
 983 | +        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]
 984 | +        rig = Rig(ms, ["h", "x", "y"], [(True, [], None, Rig.LINE)], [None])
 985 | +        out = rig.run()
 986 | +        self.assertEqual((out["package"]["lineup_bar"]["note"], out["package"]["lineup_bar"]["floors"]),
 987 | +                         ("line-up passed on the calibrated bar", {"clips_alone": {"clip": 3},
 988 | +                                                                   "coherence": {"clip": 3, "vo_point": 3}}))
 989 | +        from unittest import mock
 990 | +        with mock.patch.object(PK, "_live_lineup_bar", lambda: (None, "no valid line-up calibration")):
 991 | +            rig = Rig(ms, ["h", "x", "y"], [(True, [], None, Rig.LINE)], [None])
 992 | +            out = rig.run()
 993 | +        self.assertIsNotNone(out["package"])
 994 | +        self.assertNotIn("lineup_bar", out["package"])                                  # the standard bar: no mark
 995 | +
 996 | +
 997 |  class TestRuling56Scorer(unittest.TestCase):
 998 |      """RULING 56 (09:59): the render's own STAND_ALONE clip scorer, asked at the pin stage by the integrator's service
 999 |      about every moment left out as an opener it would have to affirm, untrimmed and trimmed; only what it affirms is
1000 | 
```

---

pp-selectid: RULING 116 (orchestrator 15:30 ET Nov 15) (4), STATE Q3 (15:34 ET; ruling 106's default APPLY at 15:54):
THE LINE-UP VERDICTS ON A CALIBRATED BAR. New: pipeline/lineup_bar.py, pipeline/lineup_calibration.json,
tests/package/test_lineup_bar.py. Changed: pipeline/package.py, pipeline/package_pin.py, tests/package/proof_ledger.py,
tests/package/conftest.py, tests/package/test_medley.py.

THE ORDER (ruling 116 (4)), verbatim: "IF (1) shows approved line-ups failing: propose the calibrated floors the same
way as ruling 115 (each part at least the lowest value across PBX's approved line-ups under the same asking), and put
the question to me with DEFAULT IN 20 MIN: APPLY the calibrated floors, audit-first, marked in the pin and in the
Telegram note in one plain line like the hook's, then rebuild."
(1) showed it (tests/package/proof/clips116/REPORT.md, committed 7a5c0362): today's clips-alone verdict fails the
protected 41f29b1f at seeds 7 and 9 and the sealed 13949b7c at 7 and 8; today's coherence verdict fails the PUBLISHED
0c68b589 at all three seeds and 41f29b1f at 7; every failure is one rating of 3; no approved line-up had more than one
flagged join; every asking stated a through-line.

THE CHANGE:
- lineup_bar.floors_from: each verdict's parts (clips-alone: the lowest clip after the hook; coherence: the lowest clip
  after the hook and the VO point) at their lowest across the approved runs, never under 3 (ruling 115's rule). The
  flagged-join allowance is NOT calibrated: it stays the law's one bridge (L-y 2; LY_MAX_BRIDGES), and no approved
  line-up needed more. The through-line stays required.
- lineup_calibration.json: rater Grok; the two prompts' versions (package.MEDLEY_VERSION / COHERENCE_VERSION: sha256
  of MEDLEY_PROMPT / COHERENCE_PROMPT); the approved runs as measured (pins, seeds, ratings, flagged joins,
  through-lines); floors clips-alone clip 3, coherence clip 3 and VO point 3; valid_h null (one fixed source, like
  the hook's); sealed with hook_bar's seal (hook_bar.write / load).
- lineup_bar.bar(versions): valid only sealed, naming a rater, for exactly these two versions, measured_at with a
  timezone and not in the future, its own valid_h, no floor under 3; else (None, why).
- lineup_bar.floors_for(verdict, backend, live, standard): the calibrated floors ONLY for a verdict the calibrated
  rater gave; every other back-end (Plan B's Gemini for clips-alone, deepseek / glm for coherence) and every verdict
  while the file is invalid gets the STANDARD bar (package.STANDARD_LINEUP: COHERENCE_MIN 4), which is stricter.
- package.medley / coherence: ok uses that verdict's floors (the clips after the hook; the VO point); the hook's slot is
  its own bar (ruling 115), unchanged; each verdict records "bar", "floors" and "calibration_sha256".
- Every place that judges those ratings reads the VERDICT'S OWN floors and leaves the hook's slot to its bar:
  last_clip_only (ruling 62); build()'s ruling-63 reorder (it read min(cl.values()) with the hook's own rating inside:
  a hook at its floors, rating 3, blocked a reorder: the ruling-115 site I missed); the weak clips swapped after a
  failed verdict; the takeaway-only rewrite after a failed coherence verdict (it read min(coh["clips"].values()) with
  the hook's 3 inside: the second missed site) and the weak clips there.
- The mark: lineup_bar_mark(med, coh) -> {"note": "line-up passed on the calibrated bar", "floors",
  "calibration_sha256", "ruling": "116"} ONLY when both verdicts of the package were judged on the calibrated bar (from
  what each verdict recorded when it was judged), set on the built package; package_pin.to_pin carries it OUTSIDE the
  seal, like hook_bar.
- proof_ledger names the line-up bar in every build line.

UNCHANGED GUARDS: hook_bar.load / write (the seal, pipeline/hook_bar.py:51-58, 120-129); hook_own (the hook's own
bar, pipeline/package.py); providers.Router.chain (the clips-alone list heimdall_first is Grok -> Gemini; coherence's
Grok -> deepseek -> glm: model_providers.json routing.heimdall_first, unchanged); package_pin.seal's arguments
(package_pin.py:200: the mark is not among them).

TESTS: test_lineup_bar (7): floors (lowest, stopped at 3, a run without ratings refused); the file (sealed, versions,
rater, valid_h, future, a hand edit); floors_for (the rater's verdict only); the mark (both verdicts, or none) and the
pin (outside the seal); the LIVE file's floors derived from proof/clips116 and live for production's versions, its
rater the first of both verdicts' production lists. test_medley TestRuling116LineupBar (7): clips-alone and coherence
on the calibrated rater's verdict vs another back-end's; ruling 62 on the verdict's own floor; ruling 63 reorders a
line-up whose hook sits at its floors (on BOTH bars: the standard bar's 4 is where the hook's 3 used to block); the
takeaway-only rewrite with such a hook (both bars); after a failed verdict only the clips under its floor are
swapped; the mark on a calibrated package and none on a standard one. The rig now answers as production does (the
hook's slot its own rating; the bar and floors in each verdict; coherence results configurable). All 40 suite files
pass (796 tests before the last test, 797 with it). Mutations after a control run: 13 of 13 killed.

PLEASE CHECK: (1) that the floors apply only to the calibrated rater's own verdicts and that everything else stays on
the stricter standard bar; (2) that no site still judges a line-up on COHERENCE_MIN with the hook's own rating inside;
(3) that the floors in the file are the source's minimums and the joins allowance the law's; (4) the mark: both
verdicts calibrated, outside the seal; (5) the tests.


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
