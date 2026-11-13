#!/usr/bin/env python3
"""RULING 67 (orchestrator 14:02 Nov 13): re-seal a pin the render HELD at ruling 17 with the ATTESTED text of the
clip it held (pipeline/attest.py). CPU only, no model call; every input is read only.

usage: reseal_attested.py PIN RUN_DIR BUILD_DIR
  PIN        the sealed pin the render held
  RUN_DIR    the render's run that held it: PROVENANCE.json names the pin file it rendered (its seal must be PIN's);
             status.json's one hold reads "<video> words <i0>-<i1>: lock text not adjudicated (ruling 17): ... the
             second recogniser reads the run decode"; transcripts/<video>.json holds the run's decoded words
  BUILD_DIR  the build that sealed PIN: its package.json holds this side's own second recogniser (scribe_v1) reading
             of that clip, recorded live by law L-v 2

Writes MOMENTS_PIN_ATTESTED.json beside PIN (never over an existing file). Refuses (exit 2, nothing written) unless:
the render's hold says its second recogniser reads the run decode; this side's second recogniser reads the run decode
at every difference too; every difference is in ruling 67's carry-over class (a function word, or an immediate
repetition of the speaker's own words; never a number, a name or a negation); no line quotes the changed words; and
the attested text's canonical tokens are the run decode's, so no ruling-17 difference is left. The re-sealed segment
carries "attested" (package_pin.SEALED_LATER: sealed): the text it replaced, the exact diff with each difference's
class, and that the pin's verdicts and gates carry over."""
import copy
import json
import os
import re
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "pipeline"))
import attest as AT  # noqa: E402
import package_pin  # noqa: E402

HOLD = re.compile(r"(?P<vid>[A-Za-z0-9_-]{11}) words (?P<i0>\d+)-(?P<i1>\d+): lock text not adjudicated \(ruling 17\): "
                  r"at .*? the second recogniser reads the run decode \|")


def reseal(pin, run_dir, build_rec, build_dir="", now=None):
    """-> (the re-sealed pin, a summary). Raises ValueError with the reason (fail closed)."""
    mp = pin["moments_package"]
    args = lambda segs: (segs, mp["edl_vo"], mp.get("signoff_expected"), mp["title"], mp["caption"], mp["gates"],
                         mp.get("btc_screen"))
    if package_pin.seal(*args(pin["segments"])) != mp["package_sha256"]:
        raise ValueError("the pin does not recompute to its own seal with this package_pin")
    prov = open(os.path.join(run_dir, "PROVENANCE.json")).read()
    m = re.search(r"--pinned (\S+?\.json)", prov)
    if not m:
        raise ValueError("the run's PROVENANCE names no pinned file")
    with open(m.group(1)) as f:
        if json.load(f)["moments_package"]["package_sha256"] != mp["package_sha256"]:
            raise ValueError(f"the run rendered another pin ({m.group(1)})")
    with open(os.path.join(run_dir, "status.json")) as f:
        holds = [h for h in json.load(f).get("holds") or [] if HOLD.search(str(h))]
    if len(holds) != 1:
        raise ValueError(f"{len(holds)} ruling-17 holds where the second recogniser reads the run decode (need 1)")
    h = HOLD.search(str(holds[0]))
    vid, i0, i1 = h["vid"], int(h["i0"]), int(h["i1"])
    idx = [i for i, s in enumerate(pin["segments"]) if s["video_id"] == vid]
    if len(idx) != 1:
        raise ValueError(f"{len(idx)} segments on {vid} (need 1)")
    seg = pin["segments"][idx[0]]
    with open(os.path.join(run_dir, "transcripts", f"{vid}.json")) as f:
        words = [str(w["word"]) for w in json.load(f)["words"][i0:i1 + 1]]
    run_t, pin_t = " ".join(w.strip() for w in words), seg["approved_text"]
    r, p, ops = AT.diff(run_t, pin_t)
    if not ops:
        raise ValueError("the approved text already reads the run decode")
    classes = [AT.carry_class(r, p, o, (run_t, pin_t)) for o in ops]
    if None in classes:
        raise ValueError("ruling 67: a differing token is a number, a name, a negation or a content word: step A "
                         "(both vendors) and the stand-alone verdict are re-judged first: " +
                         str([[" ".join(r[a:b]), " ".join(p[c:d])] for (_, a, b, c, d), k in zip(ops, classes)
                              if k is None]))
    near = [t for tr in build_rec.get("tried") or [] for at in tr.get("attempts") or []
            for t in (at.get("second_pass") or {}).values() if t.get("video_id") == vid]
    sp = [t for t in near if abs(float(t.get("start", -1)) - float(seg["start"])) < 0.0015
          and abs(float(t.get("end", -1)) - float(seg["end"])) < 0.0015]          # audit 1400 C2: within 1.5 ms
    if not sp or sp[0].get("replayed") is not False or not sp[0].get("second_pass_text"):
        raise ValueError(f"this side's second recogniser has no live reading of {vid} {seg['start']}-{seg['end']} in "
                         f"the build record (its readings of {vid}: "
                         f"{sorted({(t.get('start'), t.get('end'), t.get('replayed')) for t in near}, key=str)})")
    s = AT.canon.canon_tokens(sp[0]["second_pass_text"])
    if not all(AT.reads(r, s, a, b) for _, a, b, _c, _d in ops):
        raise ValueError("this side's second recogniser does not read the run decode at every difference")
    text = AT.attested_text(pin_t, words)
    lines = [x["text"] for x in mp["edl_vo"].get("bridges") or []] + \
        ([mp["edl_vo"]["intro"]] if mp["edl_vo"].get("intro") else []) + [mp["title"], mp["caption"]]
    q = AT.quotes(lines, r, p, ops)
    if q:
        raise ValueError(f"ruling 67: these lines quote the changed words and are re-gated first: {q}")
    out = copy.deepcopy(pin)
    diffs = [{"run": " ".join(r[a:b]), "approved": " ".join(p[c:d]), "class": k}
             for (_, a, b, c, d), k in zip(ops, classes)]
    out["segments"][idx[0]].update(approved_text=text, attested={
        "rule": "ruling 67 (orchestrator 14:02 Nov 13): the attested-text re-seal",
        "was": pin_t, "differences": diffs,
        "carried": "every verdict and gate this pin was sealed with, judged on the text it replaces: each difference "
                   "is in ruling 67's carry-over class, and no line quotes the changed words",
        "render": {"run": os.path.basename(os.path.normpath(run_dir)), "words": [i0, i1], "decode": run_t},
        "second_recogniser": {"model": sp[0].get("model"), "text": sp[0]["second_pass_text"], "record": build_dir}})
    sha = package_pin.seal(*args(out["segments"]))
    old = mp["package_sha256"]
    at = (now or datetime.now(timezone.utc)).isoformat(timespec="seconds")
    out["story_id"] = re.sub(r"-[0-9a-f]{8}$", "-" + sha[:8], pin["story_id"])
    out["approved_at"] = at
    out["approval_ref"] = f"{pin.get('approval_ref')}; re-sealed under ruling 67 (the attested text of {vid})"
    out["moments_package"].update(package_sha256=sha, resealed={"of": pin["story_id"], "package_sha256": old,
                                                                 "rule": "ruling 67", "at": at})
    return out, {"segment": idx[0], "video_id": vid, "differences": diffs, "text": text, "was": pin_t,
                 "story_id": out["story_id"], "package_sha256": sha}


def main(argv=None):
    a = argv if argv is not None else sys.argv[1:]
    if len(a) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    pin_path, run_dir, build_dir = a
    dest = os.path.join(os.path.dirname(os.path.abspath(pin_path)), "MOMENTS_PIN_ATTESTED.json")
    try:
        if os.path.exists(dest):
            raise ValueError(f"{dest} exists (never written over)")
        with open(pin_path) as f:
            pin = json.load(f)
        with open(os.path.join(build_dir, "package.json")) as f:
            rec = json.load(f)
        out, summary = reseal(pin, run_dir, rec, os.path.relpath(os.path.abspath(build_dir), REPO))
    except (OSError, ValueError, KeyError, TypeError) as e:
        print(f"REFUSED (ruling 67): {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    with open(dest, "x") as f:
        json.dump(out, f, indent=1)
    print(json.dumps(dict(summary, path=os.path.relpath(dest, REPO)), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
