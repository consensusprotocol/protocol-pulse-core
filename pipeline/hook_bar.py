"""RULING 115 (orchestrator 13:24 ET Nov 15): THE HOOK BAR IS DEFINED BY PBX'S APPROVALS.

The hook job (package.hook_ratings) asks each candidate ALONE, at production's seed, on the calibrated rater (Grok).
A hook passes when EACH of its three parts (scroll, alone, setup) is at least that part's FLOOR. A floor is the lowest
value the part took across PBX's approved hooks, under that same asking (the source: tests/package/proof/hook113/
ALONE_TEST.json). No floor is set below 3: the order stops a lower one at 3, and the builder reports it.

The floors live in ONE calibration file, pipeline/hook_calibration.json, with its sha256. It is valid only for its
rater, its question version (package.HOOK_VERSION), its seed and its asking ("alone"), and for as long as the FILE
says: "valid_h" hours after it was measured, or null for no expiry. Ruling 115's interim bar is null: its floors come
from ONE fixed source (ALONE_TEST.json), and ruling 113 (2)'s once-a-day law is measured against ruling 115 (3)'s
question version, not this one; a calibration under that law will carry its 24. A file that names no "valid_h" is
refused. An invalid or stale file passes NO hook, and the build says why in one line (fail closed, law L-m).
A package sealed on this bar says so in its record (NOTE). PBX's approve or reject of it is appended to the file
(add_example), so the approved set grows.
"""
import copy
import hashlib
import json
import os
from datetime import datetime, timedelta, timezone

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hook_calibration.json")
PARTS = ("scroll", "alone", "setup")
FLOOR_MIN = 3                       # the order: "If any floor comes out below 3, stop at 3 for that part and tell me."
SKEW_MIN = 5.0                      # a measured_at at most this many minutes ahead of now (clock skew) is accepted
MAX_VALID_H = 24.0 * 366             # a valid_h above a year is refused (and stays far inside timedelta's range)
NOTE = "hook passed on the calibrated bar"


def body_sha(cal):
    """The sha256 of the calibration's canonical JSON without its own "sha256" key."""
    b = {k: v for k, v in cal.items() if k != "sha256"}
    return hashlib.sha256(json.dumps(b, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def floors_from(approved):
    """{part: the lowest value it takes across the approved hooks' parts, never below FLOOR_MIN} and the parts that
    came out below FLOOR_MIN (the order wants those told)."""
    fl, low = {}, []
    for p in PARTS:
        vals = [a.get(p) for a in approved]
        if not vals or any(type(v) is not int for v in vals):
            raise ValueError(f"an approved hook has no integer {p!r}: the floors cannot be measured")
        fl[p] = min(vals)
        if fl[p] < FLOOR_MIN:
            low.append(f"{p} {fl[p]} (stopped at {FLOOR_MIN})")
            fl[p] = FLOOR_MIN
    return fl, low


def load(path=PATH):
    """The calibration as written, or None with why (missing, unreadable, or its sha does not match its body)."""
    try:
        with open(path) as f:
            cal = json.load(f)
    except (OSError, ValueError) as e:
        return None, f"the hook calibration cannot be read ({type(e).__name__}: {str(e)[:120]})"
    if not isinstance(cal, dict) or cal.get("sha256") != body_sha(cal):
        return None, "the hook calibration's sha256 does not match its body (edited by hand?)"
    return cal, None


def bar(rater, question_version, seed, now=None, path=PATH):
    """The live bar: {"floors", "sha256", "rater", ...} when the calibration is valid for exactly this question
    version and seed (and this rater, when one is named; passes() checks each rating's own back-end), and is within
    its own "valid_h" (null: no expiry); else (None, why), and no hook passes."""
    cal, why = load(path)
    if cal is None:
        return None, why
    for k, want in (("rater", rater), ("question_version", question_version), ("seed", seed), ("asking", "alone")):
        if k == "rater" and want is None:
            continue
        if cal.get(k) != want:
            return None, f"the hook calibration is for {k} {cal.get(k)!r}, not {want!r}: no hook passes until it is re-run"
    try:
        at = datetime.fromisoformat(str(cal["measured_at"]))
        fl = {p: int(cal["floors"][p]) for p in PARTS}
    except (KeyError, TypeError, ValueError, OverflowError):   # Infinity / NaN floors too (audit 1459 C1, deepseek)
        return None, "the hook calibration has no readable measured_at or floors"
    if at.tzinfo is None:                # a naive time cannot be compared with now (audit 20261115_1410)
        return None, "the hook calibration's measured_at has no timezone: refused"
    age = (now or datetime.now(timezone.utc)) - at
    if age < -timedelta(minutes=SKEW_MIN):   # measured "in the future" would stretch its validity (audit 1410 C1, qwen)
        return None, f"the hook calibration's measured_at ({cal['measured_at']}) is in the future: refused"
    if "valid_h" not in cal:                 # explicit: never a calibration valid forever by an omission
        return None, "the hook calibration names no valid_h (hours, or null for none): refused"
    vh = cal["valid_h"]
    if vh is not None:
        if type(vh) not in (int, float) or not 0 < vh <= MAX_VALID_H:   # NaN and +-Infinity fail the range too:
            return None, (f"the hook calibration's valid_h {vh!r} is not a number of hours in (0, "   # they never
                          f"{MAX_VALID_H:g}]: refused")       # reach timedelta (audit 1459 C1, deepseek)
        if age > timedelta(hours=vh):
            return None, f"the hook calibration is over {vh:g} h old (measured {cal['measured_at']}): re-run it"
    if any(v < FLOOR_MIN for v in fl.values()):
        return None, f"a floor under {FLOOR_MIN} in the hook calibration: refused"
    return {"floors": fl, "sha256": cal["sha256"], "rater": cal["rater"], "question_version": cal["question_version"],
            "seed": cal["seed"], "measured_at": cal["measured_at"], "valid_h": vh}, None


def passes(rec, live):
    """(passes, why) for one hook rating record {"scroll", "alone", "setup", "backend", ...} on the live bar."""
    if live is None:
        return False, "no valid hook calibration"
    if rec.get("backend") != live["rater"]:
        return False, f"rated by {rec.get('backend')}, but the bar is calibrated on {live['rater']}"
    short = [f"{p} {rec.get(p)} < {live['floors'][p]}" for p in PARTS
             if type(rec.get(p)) is not int or rec[p] < live["floors"][p]]
    return (not short), ("; ".join(short) or None)


def text(live):
    """The bar in one line, for every build line and record."""
    if live is None:
        return "no valid hook calibration: no hook passes"
    f = live["floors"]
    return (f"the calibrated hook bar (ruling 115): scroll >= {f['scroll']}, alone >= {f['alone']}, setup >= "
            f"{f['setup']}, on {live['rater']} asked alone at seed {live['seed']} (calibration {live['sha256'][:12]})")


def write(cal, path=PATH):
    """Seal and write a calibration (its sha256 over its body), .tmp then rename."""
    cal = dict(cal)
    cal["sha256"] = body_sha(cal)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(cal, f, indent=1, sort_keys=True)
        f.write("\n")
    os.replace(tmp, path)
    return cal


def add_example(story_id, verdict, hook, reason=None, path=PATH, now=None):
    """RULING 115 (2): PBX's approve or reject of a package sealed on this bar, appended as an example (approved =
    positive, rejected = negative with his reason). The floors are NOT re-derived here: a new floor comes from the
    next calibration run, which asks every approved hook again. -> the calibration as written."""
    if verdict not in ("approved", "rejected"):
        raise ValueError("verdict is 'approved' or 'rejected'")
    if verdict == "rejected" and not reason:
        raise ValueError("a rejection carries PBX's reason")
    cal, why = load(path)
    if cal is None:
        raise ValueError(why)
    cal = copy.deepcopy(cal)
    cal.setdefault("examples", []).append({
        "story_id": story_id, "verdict": verdict, "reason": reason,
        "hook": {k: hook.get(k) for k in ("moment_id", "text", "channel", *PARTS, "backend")},
        "at": (now or datetime.now(timezone.utc)).isoformat(timespec="seconds")})
    return write(cal, path)
