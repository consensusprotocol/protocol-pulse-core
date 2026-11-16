#!/usr/bin/env python3
"""pipeline/stand_alone_floor.py: ruling 119 (1)'s CALIBRATED FLOOR for the stand-alone clip scorer, at the render's
validate. This is the integrator's half; the builder's half is package_pin's. The two land together, on the
orchestrator's yes (ruling 106: it loosens an integrity gate).

MEASURED (docs/audits/ruling119/APPROVED_CLIPS_SCORER.json, 08:28-08:33 ET Nov 16): asked alone, PBX's approved clips
take scores down to 2.0, and the scorer repeats every score exactly. The floor is the lowest score an approved clip
takes, never under 3: 3.0. The builder seals a clip under the bar (3.0 <= score < 3.5) only under the measured scorer
code and weights, and marks the pin outside the seal:
  moments_package.stand_alone_bar = {"note": telegram's line, "floor": 3.0, "scorer_sha": the full measured sha,
                                     "segments": [places in the pin's segments list, 0 = the hook], "ruling": "119"}.

AT VALIDATE: stand_alone.check_edl asks its scorer and reads the 3.5 bar, unchanged. stand_alone.py and
story_semantics.py are never touched here: the scorer's code sha hashes both files, and the floor is bound to it.
apply() then re-reads, for EXACTLY the marked segments, an opener the scorer refused only for its score. It asks the
unchanged stand_alone.opener (and trimmed_opener for a trimmed segment) again, with the score AT the bar and the
scorer's own fault. That must pass, and the scorer's real score must be >= FLOOR. All of this applies only when:
  - the pin record's package is the EDL's (the seal);
  - the running scorer code is the measured one (the full sha, exact);
  - the running weights are the measured ones (the full Ollama digest, exact).
Otherwise nothing changes: fail closed, and the 3.5 HOLD stands. apply() never touches the topic test, or an opener
that failed for another reason (a hook's conjunction, no verdict at all). It refuses a malformed mark (ValueError: the
caller HOLDs) and never reads part of one."""
import json
import os

KEY = "stand_alone_bar"
FLOOR = 3.0
RULING = "119"
FIELDS = ("floor", "note", "ruling", "scorer_sha", "segments")
MEASURED_SCORER_SHA = "edd54964a5ab15f4a17d74ecbe40bcbccf2fdf2818df97881e8f7039a4721f53"   # stand_alone_scorer.scorer_sha
MEASURED_DIGEST = "a418f5838eaf7fe2cfe0a3046c8384b68ba43a4435542c942f9db00a5f342203"       # gemma3:27b on the GPU0 Ollama


def note():
    """The mark's one line: telegram's (the drop prints it), so the two can never differ."""
    import telegram
    return {key: line for key, line, _ in telegram.BAR_MARKS}[KEY]


def mark(mp, n_segments):
    """The pin's stand-alone mark, checked whole: None when the package carries none, else the mark. ValueError on
    anything that is not exactly ruling 119's mark for a pin of n_segments segments."""
    if not isinstance(mp, dict) or KEY not in mp:
        return None
    m = mp[KEY]
    if not isinstance(m, dict) or sorted(m) != sorted(FIELDS):
        raise ValueError(f"{KEY} is not ruling {RULING}'s mark: its fields are "
                         f"{sorted(m) if isinstance(m, dict) else type(m).__name__}, not {list(FIELDS)}")
    floor = m["floor"]
    if m["note"] != note() or m["ruling"] != RULING or isinstance(floor, bool) or \
            not isinstance(floor, (int, float)) or floor != FLOOR or m["scorer_sha"] != MEASURED_SCORER_SHA:
        raise ValueError(f"{KEY} is not ruling {RULING}'s mark (note, floor {FLOOR}, the measured scorer code): "
                         f"{json.dumps(m)[:240]}")
    places = m["segments"]
    if not isinstance(places, list) or not places or \
            not all(isinstance(p, int) and not isinstance(p, bool) and 0 <= p < n_segments for p in places) or \
            len(set(places)) != len(places):
        raise ValueError(f"{KEY} segments must be distinct places among the pin's {n_segments} segments: {places!r}")
    return m


def labels(m):
    """The marked places as validate names them: place 0 is the hook, place i the EDL's clip i (pinned.build_edl)."""
    return ["hook" if p == 0 else f"clip_{p:02d}" for p in m["segments"]]


def running_scorer_sha():
    import stand_alone_scorer
    return stand_alone_scorer.scorer_sha()


def running_digest():
    import story_semantics as sm
    return sm.model_digest(sm.LLM_HOST, sm.LLM_MODEL)


def apply(sa, edl, run_dir, scorer_sha=None, digest=None):
    """check_edl's result (sa) with ruling 119 (1)'s floor applied to exactly the pin's marked segments (module doc).
    A marked pin adds sa["calibrated_floor"] = {mark, segments, scorer_sha, digest, applied[, not_applied]}. ValueError:
    an unreadable pin record, a malformed mark, or a marked package that is not the EDL's. scorer_sha / digest: callables
    for tests; by default the running scorer code's sha and the GPU0 Ollama's digest of gemma3:27b."""
    import stand_alone as SA
    path = os.path.join(run_dir, "PINNED_DECISION.json")
    if not os.path.exists(path):
        return sa                                                # no pin record (an auto run): no mark
    try:
        with open(path) as f:
            pin = json.load(f)["pin"]
        mp, n = pin.get("moments_package"), len(pin["segments"])
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as e:
        raise ValueError(f"{KEY}: the pin record cannot say whether the package was marked "
                         f"({type(e).__name__}: {e})") from None
    m = mark(mp, n)
    if m is None:
        return sa
    sha = mp.get("package_sha256")
    if not (isinstance(sha, str) and sha and sha == edl.get("moments_package_sha256")):
        raise ValueError(f"{KEY}: the marked package in PINNED_DECISION.json is not the EDL's")
    code, weights = (scorer_sha or running_scorer_sha)(), (digest or running_digest)()
    rec = sa["calibrated_floor"] = {"mark": m, "segments": labels(m), "scorer_sha": code, "digest": weights,
                                    "applied": []}
    if code != MEASURED_SCORER_SHA or weights != MEASURED_DIGEST:
        rec["not_applied"] = (f"the running scorer is not the measured one (code {str(code)[:12]}, weights "
                              f"{str(weights)[:12]}; measured {MEASURED_SCORER_SHA[:12]} / {MEASURED_DIGEST[:12]}): "
                              f"the 3.5 bar alone")
        return sa
    segs = {"hook": edl["hook"], **{f"clip_{c['index']:02d}": c for c in edl.get("clips", [])}}
    for r in sa["rows"]:
        v = r.get("scorer")
        if r["segment"] not in rec["segments"] or r["opener"]["pass"] or not isinstance(v, dict):
            continue
        score, fault = v.get("score"), v.get("fault")
        if isinstance(score, bool) or not isinstance(score, (int, float)) or not FLOOR <= score < SA.CLIP_MIN_SCORE:
            continue
        s = segs[r["segment"]]
        ok, _ = SA.opener("hook" if r["segment"] == "hook" else "clip", s.get("text"), SA.CLIP_MIN_SCORE, fault, True)
        if ok and SA.trimmed_word(s):
            ok, _ = SA.trimmed_opener(SA.trimmed_word(s), SA.CLIP_MIN_SCORE, fault, True)
        if not ok:                                               # it fails for another reason than its score
            continue
        r["opener"] = {"pass": True, "why": f"{r['opener']['why']}; AFFIRMED on ruling 119 (1)'s calibrated floor "
                                           f"({FLOOR}) for this marked segment, under the measured scorer code and "
                                           f"weights"}
        r["pass"] = r["topic"]["pass"]
        rec["applied"].append(r["segment"])
    sa["ok"] = all(r["pass"] for r in sa["rows"]) and sa.get("medley_names_bitcoin", {"pass": True})["pass"]
    return sa
