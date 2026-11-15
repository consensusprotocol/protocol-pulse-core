"""RULING 116 (orchestrator 15:30 ET Nov 15; Q3 on STATE 15:34, ruling 106's default APPLY): THE LINE-UP VERDICTS ON
A CALIBRATED BAR, the hook's method (ruling 115).

Today's clips-alone verdict (package.medley) and coherence verdict (package.coherence) failed PBX's own approved
line-ups on ONE rating of 3 (tests/package/proof/clips116/: the four approved line-ups, seeds 7, 8, 9, Grok, today's
prompts). A rating's FLOOR is the lowest value it took across them, never under 3: clips-alone, every clip after the
hook; coherence, every clip after the hook and the VO point. The through-line stays required and the flagged joins
stay at the law's one bridge (L-y 2): no approved line-up needed more.

The floors live in ONE sealed file, pipeline/lineup_calibration.json (hook_bar's seal), valid only for its rater, the
two prompts' versions (package.MEDLEY_VERSION, COHERENCE_VERSION) and its own valid_h (null: one fixed source). They
apply ONLY to a verdict the calibrated rater gave. Any other model's verdict, and every verdict while the file is
invalid, is judged on the STANDARD bar (package.COHERENCE_MIN), which is stricter: the calibrated bar passes no more
than PBX's approvals show passing. A package whose two verdicts both passed on it says so in its record and pin
(NOTE)."""
import os
from datetime import datetime, timedelta, timezone

import hook_bar as HB

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lineup_calibration.json")
VERDICTS = {"clips_alone": ("clip",), "coherence": ("clip", "vo_point")}   # each verdict's calibrated parts
FLOOR_MIN = HB.FLOOR_MIN            # 3: ruling 115's rule, applied the same way (ruling 116 (4))
NOTE = "line-up passed on the calibrated bar"


def floors_from(runs):
    """{verdict: {part: the lowest value it took across the runs, never under FLOOR_MIN}} and the parts stopped at
    FLOOR_MIN. runs: {verdict: [{"clips": {label: rating}, "vo_point": n (coherence)}, ...]} (the hook not among the
    clips). A run without its ratings measures nothing: ValueError."""
    fl, low = {}, []
    for verdict, parts in VERDICTS.items():
        rs = runs.get(verdict) or []
        if not rs:
            raise ValueError(f"no {verdict} run: the floors cannot be measured")
        fl[verdict] = {}
        for p in parts:
            vals = [min(r["clips"].values()) if p == "clip" else r.get(p) for r in rs if r.get("clips")]
            if len(vals) != len(rs) or any(type(v) is not int for v in vals):
                raise ValueError(f"a {verdict} run has no integer {p!r}: the floors cannot be measured")
            fl[verdict][p] = min(vals)
            if fl[verdict][p] < FLOOR_MIN:
                low.append(f"{verdict} {p} {fl[verdict][p]} (stopped at {FLOOR_MIN})")
                fl[verdict][p] = FLOOR_MIN
    return fl, low


def bar(versions, now=None, path=None):
    """The live bar: {"rater", "sha256", "clips_alone": {...}, "coherence": {...}} when the calibration is sealed, for
    exactly these prompt versions ({"clips_alone": v, "coherence": v}), not dated in the future, within its own valid_h,
    and no floor under FLOOR_MIN; else (None, why): every verdict is then judged on the standard bar."""
    cal, why = HB.load(path or PATH)
    if cal is None:
        return None, why.replace("hook calibration", "line-up calibration")
    if not isinstance(cal.get("rater"), str) or not cal["rater"]:
        return None, "the line-up calibration names no rater: refused"
    for verdict, want in versions.items():
        if (cal.get("question_versions") or {}).get(verdict) != want:
            return None, (f"the line-up calibration is for {verdict}'s question version "
                          f"{(cal.get('question_versions') or {}).get(verdict)!r}, not {want!r}: standard bar until it "
                          f"is re-run")
    try:
        at = datetime.fromisoformat(str(cal["measured_at"]))
        fl = {v: {p: int(cal["floors"][v][p]) for p in parts} for v, parts in VERDICTS.items()}
    except (KeyError, TypeError, ValueError, OverflowError):
        return None, "the line-up calibration has no readable measured_at or floors"
    if at.tzinfo is None:
        return None, "the line-up calibration's measured_at has no timezone: refused"
    age = (now or datetime.now(timezone.utc)) - at
    if age < -timedelta(minutes=HB.SKEW_MIN):
        return None, f"the line-up calibration's measured_at ({cal['measured_at']}) is in the future: refused"
    if "valid_h" not in cal:
        return None, "the line-up calibration names no valid_h (hours, or null for none): refused"
    vh = cal["valid_h"]
    if vh is not None:
        if type(vh) not in (int, float) or not 0 < vh <= HB.MAX_VALID_H:
            return None, f"the line-up calibration's valid_h {vh!r} is not a number of hours in range: refused"
        if age > timedelta(hours=vh):
            return None, f"the line-up calibration is over {vh:g} h old (measured {cal['measured_at']}): re-run it"
    if any(x < FLOOR_MIN for f in fl.values() for x in f.values()):
        return None, f"a floor under {FLOOR_MIN} in the line-up calibration: refused"
    return dict(fl, rater=cal["rater"], sha256=cal["sha256"], valid_h=vh), None


def floors_for(verdict, backend, live, standard):
    """(floors, "calibrated" | "standard") for one verdict given by `backend`: the calibrated floors only when the
    calibrated rater gave it and the bar is live; else the standard floors."""
    if live is not None and backend == live["rater"]:
        return dict(live[verdict]), "calibrated"
    return dict(standard[verdict]), "standard"


def text(live):
    if live is None:
        return "no valid line-up calibration: the standard bar for every verdict"
    c, k = live["clips_alone"], live["coherence"]
    return (f"the calibrated line-up bar (ruling 116): clips-alone every clip >= {c['clip']}; coherence every clip >= "
            f"{k['clip']} and the VO point >= {k['vo_point']}; on {live['rater']} only (calibration "
            f"{live['sha256'][:12]})")
