"""RULING 68 (orchestrator 14:02 Nov 13) and RULING 72 (live 17:17 Nov 13 on the integrator's side): the render's own
ruling-17 lock, asked BEFORE any write is paid for a line-up and before its pin is sealed. Ruling 68: "When it exists,
your approved text comes from it."

The integrator's service runs the render's acquisition, decode and lock (pinned.acquire, validate_range,
pinned.segment_lock) on the segments of a request. Under ruling 72 it compares the second recogniser with the lock on
every span.

Requests: this worktree's tests/package/proof/lock_requests/ (<name>.tmp, then rename). The service only reads there,
and answers each name and content once.

Results: read only, in /home/ultron/protocol_pulse/data/lock_precheck/results/
<video_id>.<start %.3f>-<end %.3f>.<decoder[:12]>.json. Each file is a list. The answer is the newest entry (by "at")
that meets all of these:
- rules == RULES ("ruling 17 + ruling 72 + ruling 73 + ruling 84" since ruling 84; an answer under any other rules string,
  or in a file named for another decoder, is not valid for the render's code and is never read);
- its window is the segment's [start, end];
- its role, approved_text, trimmed_leading and untrimmed_start equal the request's.
Entries without "rules" are ruling 68's, from before, and are never read.

Outcomes:
- no_difference, adopted, two_readings: pass. The approved text stands.
- adopt_spoken: the text to seal is "spoken_text", already through the render's validate_range + segment_lock. It is
  adopted only when this side's own check agrees that every difference is in ruling 84's class (attest.class_84,
  the integrator's class: a filler the second recogniser heard, ONE 1-for-1 function word, else ruling 67's
  carry-over class for an insert or a drop; never a number, a name or a negation). Otherwise it is a hold (fail
  closed). Under ruling 84 (b) the spoken text holds the second recogniser's reading of the one function word; the
  render's lock keeps its decode's word and records the other reading (the entry's "alternatives").
- hold: the clip may not be used with that text. The reason says why.
- error, an outcome this module does not know, or no answer in time: no verdict. Never a pass (law L-m). A request
  is sent again rather than reusing an error.

The text a pin seals is the approved text, or the adopted spoken text with an "attested" record
(package_pin.SEALED_LATER), as ruling 67's re-seal records it."""
import json
import os
import re
import time
from datetime import datetime, timezone

import attest as AT

RULES = "ruling 17 + ruling 72 + ruling 73 + ruling 84"   # RULING 84 (orchestrator 20:41 Nov 13): the integrator's
#   RULES string (its message of 20:4x Nov 13). RULING 73 (live 18:43:08 Nov 13, merged 585b6da5 on the integrator's
DECODER = "962353613cb0"                      # side): the render's own cut placement joins the pre-check (a passing
#   entry carries "cut"; a span the render cannot cut holds: "ruling 73: the render cannot cut this span: ..."). RULING
#   84 changes the render's adjudicate_lock (pinned.py), so the decoder_sha changed again: 962353613cb0e065008ab0405ca8550111ddd3ca3ba70f0ae65b4b77ab1876d8
#   (ruling 73's was 8a101f222598a4f725e7cf85626e90fb2fae35df8d81d3ff430469728114e1a7)
RESULTS = "/home/ultron/protocol_pulse/data/lock_precheck/results"        # the integrator's; read only
REQUESTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests", "package", "proof",
                        "lock_requests")      # this worktree's; the service only reads it
PASS = frozenset(("no_difference", "adopted", "two_readings"))
TRIM = ("trimmed_leading", "untrimmed_start")
ID_RE = re.compile(r"[A-Za-z0-9_.:~-]{1,120}")
TIMEOUT_S = 1200.0                            # a fresh line-up takes about 2-2.5 min; the service yields to renders
POLL_S = 10.0
OLDEST = datetime.min.replace(tzinfo=timezone.utc)


def segments_of(segs):
    """The request's segments, exactly as package_pin.to_pin will carry them from this line-up: role (the hook first),
    start and end rounded to the millisecond, the moment's text as approved_text, and both trim fields when the
    moment is trimmed (package._package copies them then)."""
    out = []
    for i, m in enumerate(segs):
        s = {"video_id": str(m["video_id"]), "start": round(float(m["start"]), 3), "end": round(float(m["end"]), 3),
             "role": "hook" if i == 0 else "clip", "approved_text": m["text"]}
        if m.get("trimmed_leading"):
            s.update({k: m[k] for k in TRIM})
        out.append(s)
    return out


def result_file(seg, results_dir=RESULTS, decoder=DECODER):
    return os.path.join(results_dir, f"{seg['video_id']}.{seg['start']:.3f}-{seg['end']:.3f}.{decoder[:12]}.json")


def _at(s):
    try:
        t = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return OLDEST
    return t if t.tzinfo is not None else t.replace(tzinfo=timezone.utc)


def _matches(e, seg):
    w = e.get("window")
    try:
        win = [round(float(w[0]), 3), round(float(w[1]), 3)] if isinstance(w, list) and len(w) == 2 else None
    except (TypeError, ValueError):
        win = None
    return (e.get("rules") == RULES and win == [seg["start"], seg["end"]] and e.get("role") == seg["role"] and
            e.get("approved_text") == seg["approved_text"] and all(e.get(k) == seg.get(k) for k in TRIM))


def answer(seg, results_dir=RESULTS, request_id=None):
    """The newest matching entry (by "at", then file order), only `request_id`'s when given; None when there is none
    or the file cannot be read (no answer is never a pass)."""
    try:
        with open(result_file(seg, results_dir)) as f:
            entries = json.load(f)
    except (OSError, ValueError):
        return None
    best = None
    for k, e in enumerate(entries if isinstance(entries, list) else []):
        if isinstance(e, dict) and _matches(e, seg) and (request_id is None or e.get("request_id") == request_id):
            key = (_at(e.get("at")), k)
            if best is None or key >= best[0]:
                best = (key, e)
    return best[1] if best else None


def send(segments, request_id, requests_dir=REQUESTS):
    """Write the WHOLE line-up as one request: <request_id>.tmp, then renamed to <request_id>.json. Never over an
    existing request (the service answers each name and content once)."""
    if not isinstance(request_id, str) or not ID_RE.fullmatch(request_id):
        raise ValueError(f"a request_id is 1-120 of [A-Za-z0-9_.:~-]: {request_id!r}")
    os.makedirs(requests_dir, exist_ok=True)
    final = os.path.join(requests_dir, request_id + ".json")
    tmp = os.path.join(requests_dir, request_id + ".tmp")
    if os.path.exists(final) or os.path.exists(tmp):
        raise FileExistsError(f"{final} (or its .tmp) exists: a request is never written over")
    with open(tmp, "x") as f:
        json.dump({"request_id": request_id, "segments": segments}, f, indent=1)
    os.rename(tmp, final)
    return final


def decide(seg, e):
    """One segment's verdict from its answer -> {"verdict": "pass" | "adopt" | "hold" | "error", "outcome", "why",
    and for an adoption "spoken_text" and "differences"}."""
    if e is None:
        return {"verdict": "error", "outcome": None, "why": "no answer from the render's lock in time (law L-m)"}
    out, why = e.get("outcome"), str(e.get("reason") or "")[:400]
    if out in PASS:
        return {"verdict": "pass", "outcome": out, "why": why}
    if out == "hold":
        return {"verdict": "hold", "outcome": out, "why": why or "held (no reason given)"}
    if out != "adopt_spoken":
        return {"verdict": "error", "outcome": out, "why": f"no verdict: outcome {out!r} {why}".strip()}
    spoken, approved = e.get("spoken_text"), seg["approved_text"]
    if not isinstance(spoken, str) or not spoken.strip():
        return {"verdict": "error", "outcome": out, "why": "adopt_spoken without a spoken_text"}
    diffs = AT.class_84(spoken, approved)
    if not diffs:                                     # the same canonical words: the approved text stands
        return {"verdict": "pass", "outcome": out, "why": "adopt_spoken with no canonical difference"}
    if any(x["class"] is None for x in diffs):        # this side's ruling-84 check disagrees: fail closed
        return {"verdict": "hold", "outcome": out, "differences": diffs,
                "why": "adopt_spoken, but by this side's attest.class_84 a difference is outside ruling 84's "
                       "class: " + str([[x["spoken"], x["approved"]] for x in diffs if x["class"] is None])[:300]}
    return {"verdict": "adopt", "outcome": out, "why": why, "spoken_text": spoken, "differences": diffs}


def check(segs, request_id, requests_dir=REQUESTS, results_dir=RESULTS, timeout_s=TIMEOUT_S, poll_s=POLL_S,
          clock=time.time, sleep=time.sleep, log=print):
    """The render's lock for this line-up. An answer already on file is used (never an error), else the whole line-up
    is sent and its answers awaited. -> {"ok": every segment passes or is adopted, "request_id": the one sent or None,
    "segments": [request segment + decide() + the answer's "entry" ref], "error": why no verdict, or None}."""
    req = segments_of(segs)
    got = [answer(s, results_dir) for s in req]
    sent = None
    if any(e is None or e.get("outcome") not in PASS | {"adopt_spoken", "hold"} for e in got):
        sent = request_id
        send(req, request_id, requests_dir)
        log(f"    ruling 72: the lock pre-check asked ({request_id}, {len(req)} segment(s))")
        deadline = clock() + timeout_s
        while True:
            got = [answer(s, results_dir, request_id) for s in req]
            if all(e is not None for e in got) or clock() >= deadline:
                break
            sleep(poll_s)
    rows = []
    for s, e in zip(req, got):
        d = decide(s, e)
        rows.append(dict(s, **d, entry=None if e is None else {
            "request_id": e.get("request_id"), "at": e.get("at"), "outcome": e.get("outcome"),
            "lock_sha256": (e.get("lock") or {}).get("sha256") if isinstance(e.get("lock"), dict) else None,
            "file": os.path.basename(result_file(s, results_dir))}))
    errs = [f"{x['video_id']} {x['start']}-{x['end']}: {x['why']}" for x in rows if x["verdict"] == "error"]
    return {"ok": all(x["verdict"] in ("pass", "adopt") for x in rows), "request_id": sent, "segments": rows,
            "error": "; ".join(errs)[:600] or None}


def attested(row, run_rule="ruling 72 + ruling 84 (20:41 Nov 13): adopt_spoken, in ruling 84's class"):
    """The sealed record of an adopted text (package_pin.SEALED_LATER "attested"), as ruling 67's re-seal records it."""
    return {"rule": run_rule, "was": row["approved_text"], "differences": row["differences"],
            "carried": "every verdict and gate of this line-up, judged on the text it replaces: each difference is in "
                       "ruling 84's class (a filler, one function word, or ruling 67's carry-over class for an insert "
                       "or a drop; checked on this side too), and no line quotes the changed words",
            "render": {"precheck": row["entry"], "spoken_text": row["spoken_text"]}}


def quoting_lines(lines, row):
    """The lines that quote an adopted segment's changed words (ruling 67: such a line is re-gated first)."""
    r, p, ops = AT.diff(row["spoken_text"], row["approved_text"])
    return AT.quotes(lines, r, p, ops)


def apply(pk, pre):
    """The package as it will be sealed, from this line-up's pre-check: each adopted segment's text is the spoken text
    with its "attested" record, and the hook's first words follow its text. Refuses (ValueError) unless the pre-check
    passed and covers exactly the package's segments (video, start, end, approved text, in order), and when a line
    quotes an adopted segment's changed words (ruling 67: re-gated first). -> pk (its segments are its own)."""
    rows, segs = pre.get("segments") or [], pk["segments"]
    if pre.get("ok") is not True:
        raise ValueError(f"the render's lock pre-check did not pass: {pre.get('error') or 'a segment holds'}")
    if len(rows) != len(segs) or any(
            r["video_id"] != s["video_id"] or r["start"] != round(float(s["start"]), 3) or
            r["end"] != round(float(s["end"]), 3) or r["approved_text"] != s["text"] for r, s in zip(rows, segs)):
        raise ValueError("the lock pre-check does not cover exactly this package's segments")
    lines = [x["text"] for x in pk.get("lines") or []]
    for r, s in zip(rows, segs):
        if r["verdict"] == "adopt":
            q = quoting_lines(lines, r)
            if q:
                raise ValueError(f"ruling 67: these lines quote the changed words of {s['video_id']}: {q}")
            s["text"], s["attested"] = r["spoken_text"], attested(r)
    pk["hook_first_words"] = " ".join(segs[0]["text"].split()[:8])      # as package._package derives it
    pk["precheck"] = {"ok": True, "request_id": pre.get("request_id"),
                      "segments": [dict({k: r.get(k) for k in ("video_id", "start", "end", "role", "verdict", "outcome",
                                                               "entry")}, text=s["text"])   # the text the lock passed
                                   for r, s in zip(rows, segs)]}
    return pk


def failed(e):
    """A pre-check that raised (a request that could not be written, an answer that could not be decided): no
    verdict, never a pass (law L-m). -> the shape check() returns (audit 1744 C1)."""
    return {"ok": False, "request_id": None, "segments": [], "error": f"{type(e).__name__}: {str(e)[:300]}"}


def pin_problems(pk):
    """The pin stage's own check (ruling 68): a package is sealed only with a passing pre-check that covers exactly its
    segments as they now stand (an adopted text included). -> [why]."""
    pre = pk.get("precheck") or {}
    rows, segs = pre.get("segments") or [], pk.get("segments") or []
    if pre.get("ok") is not True:
        return ["ruling 68: no passing lock pre-check on this package"]
    if len(rows) != len(segs) or any(r.get("video_id") != s.get("video_id") or
                                     r.get("start") != round(float(s.get("start")), 3) or
                                     r.get("end") != round(float(s.get("end")), 3) or
                                     r.get("verdict") not in ("pass", "adopt") or
                                     r.get("text") != s.get("text") for r, s in zip(rows, segs)):   # audit 1744 C1
        return ["ruling 68: the lock pre-check does not cover this package's segments as they now stand"]
    return []
