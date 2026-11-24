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
  RULING 131 (A) (orchestrator 08:25 ET Nov 17): when the entry's lock record ("adjudication") is under ruling 131
  (A), two of the three readings decided each pair and the spoken text is the lock's merged text. It is adopted only
  when this side's own re-check (attest.class_131, from the record's three readings) finds every pair decided the same
  way, every run-taken pair at least 3 tokens from both cut edges, no number, name or negation, and the spoken text
  the merged reading; anything else is a hold (fail closed). (B): currency format ('$2 billion' for a spoken
  '2 billion') is no difference. RULING 135: neither is a pair of the same words by canon.same_words (spelling,
  segmentation, the closed reductions, fillers and a stray consonant); this side's re-checks drop it where the
  render's lock and ruling 72's comparison do (attest.class_131, attest.class_84).
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
import canon as C

RULES = ("ruling 17 + ruling 72 + ruling 73 + ruling 84 + ruling 103 + ruling 105 + ruling 131 + ruling 135 + "
         "ruling 139 + ruling 142 + ruling 143 + ruling 146")   # RULING 153 (20:03 ET Nov 23): rulings 139 and 143
#   join the integrator's string (its lockstep message of 20:1x ET Nov 23, branch r143-material 36896978e)
             # RULING 146 (2): G17a's hook lead flags in the render's lock (batch 114)                         # RULING 142 (orchestrator 14:32 ET Nov 17): '24 -7' is no sign; a
#   possessive or plural ending is a word-form pair for 131 (A) (the integrator's batch 110 values, 14:5x ET). RULING 135
#   (orchestrator 10:50 ET Nov 17): the comparison canon (canon.same_words), the integrator's message of 10:5x Nov 17.
#   RULING 131
#   (orchestrator 08:25 ET Nov 17): (A) two of three readings, (B) currency format (the integrator's message of 08:2x
#   Nov 17); entries under the old RULES are never read. RULING 105 (orchestrator
#   20:13 Nov 14): the unstable second reading joins the rules (the integrator's messages of 20:5x-21:0x Nov 14).
#   RULING 103 (orchestrator 14:12 Nov 14): the
#   targeted re-listen joins the rules (the integrator's message of 14:3x Nov 14); entries under the old RULES are never
#   read. RULING 84 (orchestrator 20:41 Nov 13): the integrator's
#   RULES string (its message of 20:4x Nov 13). RULING 73 (live 18:43:08 Nov 13, merged 585b6da5 on the integrator's
DECODER = "9326604699a7"                      # side): the render's own cut placement joins the pre-check (a passing
#   entry carries "cut"; a span the render cannot cut holds: "ruling 73: the render cannot cut this span: ..."). RULING
#   84 changed the render's adjudicate_lock (pinned.py), so the decoder_sha changed: 962353613cb0e065008ab0405ca8550111ddd3ca3ba70f0ae65b4b77ab1876d8
#   (ruling 73's was 8a101f222598a4f725e7cf85626e90fb2fae35df8d81d3ff430469728114e1a7). RULING 90 (the integrator's
#   spotlight branches in pinned.py, merged fd5c9cc4 at 23:16 ET Nov 13; RULES unchanged; every medley span's decode,
#   lock and class unchanged, entries under the old sha not reused): c705b20ed80025af629856e6c34eb609834fef3f708b8614ca26749a4fc8088c
#   RULING 103 with the canon-401k fix (law L-k: '401k' is a plan's name, never 401000), landed together on the
#   integrator's side (canon-401k 373d0fed + 077407dc, audited batches 79 and 80): d1e155c642a6aaacd578ac5ad2f47c9cd1d71594c9913dc4f0f231fd6b2258ce
#   RULING 105 (the integrator's branch ruling105 d5bf9674, audited batch 84; both sides land in lockstep as with 103):
#   a4c307f78c94d1c4ee068b5c27862c79a90900880bb885fee68da616ce2a20d6
#   RULING 131 (A) + (B) (the integrator's branch r131-lock, audited; both sides land in lockstep as with 105): canon.py's
#   currency_free / dollars_after_number and adjudicate_lock's two of three readings:
#   ce72aefa342dcd94dd45d8b4bc96ec6477ec04c91914db2054403338d7559e60
#   RULING 135 (the comparison canon: canon.same_words; the integrator's branch r135-canon, audited; lockstep as with 131):
#   b52c9354d604ab2303a91e6e6e5f926990987d46448992579684934f62e9392d
#   RULING 142 (canon's '24 -7' and canon.word_form, adjudicate_lock's word-form exemption; the integrator's branch
#   r141-sign f02dd73c, audited; lockstep as with 135): fe809cb4e680a3bc5df49e4c397e79f6cf2277650ea02c05cf88b34ecc573ebd
#   RULING 142, the integrator's batches 111 (the post_live fallback, acquisition-side) + 112 (canon_spans reads '24' '-7,'
#   as '24' '7'; word_form takes the contraction [t + "'s"] / [t, 'is' | 'has']; branch r142-postlive 70e78551; one
#   lockstep): fc204e4a4385a1906ef858923936cd6d6ed3a65ea78f2007281e2d4945038e09
#   RULING 146 (2), the integrator's batch 114 (sentence_law.lock_cut: a hook lead under 80 ms FLAGS, never holds;
#   branch r146-g17a 90aa0486; sentence_law.py byte-identical): 50fa01b400bd4231e38a9a8b77f6a0df6f16a57d6f0e22de0eb376788f039256
#   RULING 153 (orchestrator 20:03 ET Nov 23): the integrator's batches 113 (ruling 143, the material-words lock), 116
#   (ruling 139 on the render lock), the ruling-145 allowance (gpu0.py) and 119 (post_live; no decoder file), ONE
#   lockstep (branch r143-material 36896978e; pinned.py, sentence_law.py and gpu0.py byte-identical):
#   9326604699a7756c18d887cd09bdb280f74d9c732bfb0e1235e4a9f3095850c9
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
    u = e.get("unstable_second_reading")
    if u is not None and (out in PASS or out == "adopt_spoken"):   # RULING 105: a pass (or an adoption) that rests
        bad = ruling_105_fails(u)                                  # on the readings across passes (glm, audit 2049 C1)
        if bad:                                       # this side's own check of the record disagrees: fail closed
            return {"verdict": "hold", "outcome": out, "why": f"ruling 105 (this side's check of the pre-check's "
                                                              f"record): {bad}"}
    if out in PASS:
        return {"verdict": "pass", "outcome": out, "why": why}
    if out == "hold":
        return {"verdict": "hold", "outcome": out, "why": why or "held (no reason given)"}
    if out != "adopt_spoken":
        return {"verdict": "error", "outcome": out, "why": f"no verdict: outcome {out!r} {why}".strip()}
    spoken, approved = e.get("spoken_text"), seg["approved_text"]
    if not isinstance(spoken, str) or not spoken.strip():
        return {"verdict": "error", "outcome": out, "why": "adopt_spoken without a spoken_text"}
    adj = e.get("adjudication")
    if isinstance(adj, dict) and str(adj.get("rule") or "").startswith(AT.RULE_143):   # RULING 143: the settlement
        diffs = AT.class_143(spoken, approved, adj)
        bad = [x for x in diffs if x["class"] is None]
        if bad:                                       # this side's re-check of the lock's record disagrees: fail closed
            return {"verdict": "hold", "outcome": out, "differences": diffs,
                    "why": "adopt_spoken under ruling 143, but by this side's attest.class_143 it holds: " +
                           str([[x["spoken"], x["approved"], x["why"]] for x in bad])[:300]}
        if not any(x["took"] == "run" for x in diffs):  # no pair took the run decode's reading: the approved text stands
            return {"verdict": "pass", "outcome": out, "why": "adopt_spoken under ruling 143 with no pair taking the "
                                                              "run decode's reading: the approved text stands"}
        return {"verdict": "adopt", "outcome": out, "why": why, "spoken_text": spoken, "differences": diffs,
                "adoption": AT.RULE_143,
                "transcript_corrected": [[x["approved"], x["spoken"]] for x in diffs if x.get("material") and
                                         x["took"] == "run"]}
    if isinstance(adj, dict) and str(adj.get("rule") or "").startswith(AT.RULE_131):   # RULING 131 (A): two of three
        diffs = AT.class_131(spoken, approved, adj)
        bad = [x for x in diffs if x["class"] is None]
        if bad:                                       # this side's re-check of the lock's record disagrees: fail closed
            return {"verdict": "hold", "outcome": out, "differences": diffs,
                    "why": "adopt_spoken under ruling 131 (A), but by this side's attest.class_131 it holds: " +
                           str([[x["spoken"], x["approved"], x["why"]] for x in bad])[:300]}
        if not any(x["took"] == "run" for x in diffs):  # no pair took the spoken reading: the approved text stands
            return {"verdict": "pass", "outcome": out, "why": "adopt_spoken under ruling 131 (A) with no pair taking "
                                                              "the run's reading: the approved text stands"}
        return {"verdict": "adopt", "outcome": out, "why": why, "spoken_text": spoken, "differences": diffs,
                "adoption": AT.RULE_131}
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
        rows.append(dict(s, **d, relisten=relisten_of(e), unstable_second_reading=unstable_of(e),
                         entry=None if e is None else {
            "request_id": e.get("request_id"), "at": e.get("at"), "outcome": e.get("outcome"),
            "lock_sha256": (e.get("lock") or {}).get("sha256") if isinstance(e.get("lock"), dict) else None,
            "file": os.path.basename(result_file(s, results_dir))}))
    errs = [f"{x['video_id']} {x['start']}-{x['end']}: {x['why']}" for x in rows if x["verdict"] == "error"]
    return {"ok": all(x["verdict"] in ("pass", "adopt") for x in rows), "request_id": sent, "segments": rows,
            "error": "; ".join(errs)[:600] or None}


def _canon(x):
    """A reading's canonical form through canon (the integrator's canon, byte-identical): '68,000' -> '68000', '401K'
    and '401(k)' -> '401k', 'forty-five' -> '45'. None for a non-string or a reading with no token (audit 2049 C1,
    qwen and glm: never a raw-string comparison, law L-k)."""
    return (C.canon(x) or None) if isinstance(x, str) else None


def _truncation(r, token):
    """RULING 105 (3): r is the lock's NUMBER token cut short: a prefix of it that keeps a digit and drops only a
    NON-DIGIT suffix ('401' of '401k'). A name (a token with no digit) never qualifies, nor does a dropped token ("")
    or a different number ('68000' of '86000')."""
    return (isinstance(r, str) and bool(r) and r != token and token.startswith(r) and any(ch.isdigit() for ch in r)
            and not any(ch.isdigit() for ch in token[len(r):]))


def ruling_105_fails(u):
    """RULING 105 (orchestrator 20:13 Nov 14), checked on THIS side from the record the pre-check sealed
    ("unstable_second_reading"), every token read through canon: the token is adjudicated as the lock's only when
    (1) the decoder read it the same on
    every pass, (2) the second recogniser's repeated readings of the same audio differ among themselves and one of
    them IS the token, and (3) every differing reading is a truncation of it. -> None when the record's pass holds on
    its own readings; else why not (a record that is not an object, the many-token form, a hold verdict, or any of the
    three not met: every one a hold, never a pass)."""
    if not isinstance(u, dict):
        return f"the record is not an object ({type(u).__name__})"
    if "tokens" in u or u.get("verdict") != "pass":
        return f"the record's verdict is {u.get('verdict')!r}" + (f" ({u.get('why')})" if u.get("why") else "")
    tok, dec, sec = _canon(u.get("token")), u.get("decoder_readings"), u.get("second_readings")
    if not (tok and any(ch.isdigit() for ch in tok)):
        return f"the token {u.get('token')!r} is not a number (a name never qualifies)"
    if not (isinstance(dec, list) and dec and isinstance(sec, list) and len(sec) >= 2):
        return "the record holds too few readings (the decoder's, and at least two of the second recogniser's)"
    dt = [_canon(x.get("token")) if isinstance(x, dict) else None for x in dec]       # every token canonical
    st = [_canon(x.get("token")) if isinstance(x, dict) else None for x in sec]
    if any(x != tok for x in dt):
        return f"(1) the decoder is not stable: {dt}"
    if len(set(st)) < 2 or tok not in st:
        return f"(2) the second recogniser is stable in its readings or never reads the token: {st}"
    odd = [x for x in st if x != tok and not _truncation(x, tok)]
    if odd:
        return f"(3) a differing reading is not a truncation of {tok!r}: {odd}"
    tests = u.get("tests")
    if not (isinstance(tests, dict) and all(tests.get(k) is True for k in
                                            ("decoder_stable", "second_unstable", "truncations_only"))):
        return f"the record's own tests do not all hold: {tests}"
    return None


def unstable_of(e):
    """RULING 105: the entry's unstable-second-reading record as it stands, or None (the entry's null, a missing key,
    or anything that is not an object). It is sealed onto the segment as it stands (apply; package_pin)."""
    r = (e or {}).get("unstable_second_reading") if isinstance(e, dict) else None
    return r if isinstance(r, dict) else None


def relisten_of(e):
    """RULING 103: the entry's targeted re-listen record as it stands (one per segment: the lock's token, its short
    window, both short readings, the verdict, scribe's cost), or None when no re-listen ran (the entry's null, a missing
    key, or anything that is not an object). It is sealed onto the segment as it stands (apply; package_pin)."""
    r = (e or {}).get("relisten") if isinstance(e, dict) else None
    return r if isinstance(r, dict) else None


def attested(row, run_rule=None):
    """The sealed record of an adopted text (package_pin.SEALED_LATER "attested"), as ruling 67's re-seal records it:
    ruling 84's class, or ruling 131 (A)'s two of three readings (row["adoption"])."""
    if row.get("adoption") == AT.RULE_143:
        rule = run_rule or ("ruling 143 (orchestrator 2026-11-17 '15:55', landed by ruling 153): adopt_spoken, the "
                            "render lock's settlement")
        carried = ("every verdict and gate of this line-up, judged on the text it replaces: each changed material word "
                   "(a number, a negation, a name, a ticker or an amount) is the reading the two audio readings agree "
                   "on (the run decode and the second recogniser; the transcript corrected from the audio), each small "
                   "word the approved reading the second recogniser reads or the run decode's, re-checked on this side "
                   "from the lock's record; no line quotes the changed words (marked on the release: 'transcript "
                   "corrected from the audio' where a material word changed)")
    elif row.get("adoption") == AT.RULE_131:
        rule = run_rule or "ruling 72 + ruling 131 (A) (08:25 ET Nov 17): adopt_spoken, two of the three readings agree"
        carried = ("every verdict and gate of this line-up, judged on the text it replaces: each changed pair is the "
                   "reading two of the three readings (the approved text, the render's run decode, the second "
                   "recogniser) agree on, re-checked on this side from the lock's record, at least 3 tokens from both "
                   "cut edges, never a number, a name or a negation; no line quotes the changed words (marked on the "
                   "release: 'word check settled by two of three readings')")
    else:
        rule = run_rule or "ruling 72 + ruling 84 (20:41 Nov 13): adopt_spoken, in ruling 84's class"
        carried = ("every verdict and gate of this line-up, judged on the text it replaces: each difference is in "
                   "ruling 84's class (a filler, one function word, or ruling 67's carry-over class for an insert "
                   "or a drop; checked on this side too), and no line quotes the changed words")
    return {"rule": rule, "was": row["approved_text"], "differences": row["differences"], "carried": carried,
            "render": {"precheck": row["entry"], "spoken_text": row["spoken_text"]}}


REJUDGED = ("RULING 163 (2)(b) (orchestrator 08:22 ET Nov 24): every verdict on this clip and on our lines was made "
            "again on the corrected words before sealing (step A on both families, the exclusion screen, the second "
            "pass and the OUT edge, vision, the clips-alone verdict, the context, fidelity and value)")


def corrected_words(approved, spoken):
    """RULING 163 (2)(a) (orchestrator 08:22 ET Nov 24: "when the lock replaces ANY word of the transcript with the
    audio's reading, material or not: it is always written on the pin ('transcript corrected from the audio: X -> Y')"):
    every word the adopted text changes, on the render's own canonical tokens (attest.diff, what the lock compares):
    the transcript's words, then the audio's ("(nothing)" for an insert or a drop). -> "X -> Y; ..." or None."""
    r, p, ops = AT.diff(spoken, approved)
    return "; ".join(f"{' '.join(p[c:d]) or '(nothing)'} -> {' '.join(r[a:b]) or '(nothing)'}"
                     for _tag, a, b, c, d in ops) or None


def heard_ok(row, seg):
    """RULING 163 (2)(b): a package segment already on the text the lock adopted for it (the build judged it again on
    those words, package.heard), not on the transcript's."""
    return row.get("verdict") == "adopt" and isinstance(row.get("spoken_text"), str) and \
        row["spoken_text"] == seg.get("text") and row.get("approved_text") != seg.get("text")


def quoting_lines(lines, row):
    """The lines that quote an adopted segment's changed words (ruling 67: such a line is re-gated first)."""
    r, p, ops = AT.diff(row["spoken_text"], row["approved_text"])
    return AT.quotes(lines, r, p, ops)


def apply(pk, pre):
    """The package as it will be sealed, from this line-up's pre-check: each adopted segment's text is the spoken text
    with its "attested" record, and the hook's first words follow its text. Refuses (ValueError) unless the pre-check
    passed and covers exactly the package's segments (video, start, end, approved text, in order), and when a line
    quotes an adopted segment's changed words (ruling 67: re-gated first). RULING 163 (2): a segment may already be on
    its adopted text (heard_ok: the build judged it again on those words; its record says so, "rejudged"), and every
    adopted segment carries "transcript_corrected" (corrected_words: sealed, package_pin.SEALED_LATER). -> pk (its
    segments are its own)."""
    rows, segs = pre.get("segments") or [], pk["segments"]
    if pre.get("ok") is not True:
        raise ValueError(f"the render's lock pre-check did not pass: {pre.get('error') or 'a segment holds'}")
    if len(rows) != len(segs) or any(
            r["video_id"] != s["video_id"] or r["start"] != round(float(s["start"]), 3) or
            r["end"] != round(float(s["end"]), 3) or (r["approved_text"] != s["text"] and not heard_ok(r, s))
            for r, s in zip(rows, segs)):
        raise ValueError("the lock pre-check does not cover exactly this package's segments")
    lines = [x["text"] for x in pk.get("lines") or []]
    for r, s in zip(rows, segs):
        if r["verdict"] == "adopt":
            q = quoting_lines(lines, r)
            if q:
                raise ValueError(f"ruling 67: these lines quote the changed words of {s['video_id']}: {q}")
            again = heard_ok(r, s)
            s["text"], s["attested"] = r["spoken_text"], dict(attested(r), **({"rejudged": REJUDGED} if again else {}))
            cw = corrected_words(r["approved_text"], r["spoken_text"])
            if cw:                                       # RULING 163 (2)(a): always on the pin
                s["transcript_corrected"] = cw
        if isinstance(r.get("relisten"), dict):          # RULING 103: "Record both short readings on the pin"
            s["relisten"] = json.loads(json.dumps(r["relisten"]))   # a copy as it stands (sealed: SEALED_LATER)
        if isinstance(r.get("unstable_second_reading"), dict):     # RULING 105: "All readings are recorded on the
            s["unstable_second_reading"] = json.loads(json.dumps(r["unstable_second_reading"]))   # pin" (sealed)
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
