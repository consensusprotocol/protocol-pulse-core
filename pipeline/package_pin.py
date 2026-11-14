#!/usr/bin/env python3
"""pipeline/package_pin.py — a pp.package/1 as the existing PINNED entry point's decision (pipeline/pinned.py, schema
protocol_pulse.pinned_story.v1), so the SAME factory downstream (validate -> cut -> sentence law -> voice -> render ->
gates -> release authorisation) renders a moments-first package.

- Every segment carries `approved_text` = the moment's exact words (its source sentences, verbatim) and the record's
  transcript sha256. The pin is `machine_cuts`, so the sentence law locates the words BY TEXT in the acquired
  transcript, never by offsets. Times are YouTube coordinates (the store record's own seconds in the full video).
- `approved_by` names the machine and REVIEW ONLY. No human approved this decision (law L-q).
- The package's VO (intro, bridges with the renderer's after_clip), title, caption and its GATE INVENTORY travel in
  `moments_package`, SEALED (audit p2 C1, the L-j pattern): `package_sha256` = seal() over exactly those bytes and the
  inventory. to_pin() REFUSES a package whose inventory is missing a required gate, holds anything but exactly "PASS",
  or rests on a replayed verdict (never deliverable, law L-j). REQUESTS R7's pinned.py patch recomputes the seal and
  refuses any pin whose bytes or gates differ from what was sealed.
- `cut_evidence` (orchestrator 06:45 C / ruling 7 (1)): per segment, the INDEPENDENT recogniser's own sentence
  boundary at the IN and the OUT (its words on either side, the model, the audio window), for the sentence law's
  ruling-7 check of an edge the primary decode leaves unpunctuated. Evidence, not a gate verdict: outside the seal.
- Writes nothing itself: to_pin() returns the dict; write_pin() writes it.
"""
import hashlib
import json
import os
import re
from datetime import datetime, timezone

SCHEMA = "protocol_pulse.pinned_story.v1"
REQUIRED_GATES = ("vo_fidelity_deterministic", "vo_fidelity_verdict", "duplicate", "price_now", "runtime", "r4",
                  "context_a", "context_b", "context_c", "exclusion", "second_pass", "cuttable", "coherence")
# L-y (20:30): the clips-alone verdict and the medley's shape; ruling 6 (22:40): PBX's copy rules on every line;
# hook_onset: G17a at the pin stage, after batch pin #1's render hold (01:39 ET Nov 13); stand_alone: the render's
# STAND_ALONE at the pin stage, after pin d2657bbe's hold at the integrator's validate (03:00 ET Nov 13)
MEDLEY_GATES = ("medley", "ly_shape", "house_style", "hook_onset", "stand_alone",
                "visual")                                  # ruling 70: every clip's sheet judged (flags sealed)


# RULING 90 (orchestrator 22:40 ET Nov 13; LAW since 22:52, amended by 91 and 92): the SPOTLIGHT, a second pin kind.
# Its contract, agreed with the integrator (22:44 ET): moments_package.shape "spotlight", ONE segment (role "hook"),
# edl_vo {"intro": null, "bridges": [], "closing": <one line, <= 12 words> or null}, signoff_expected naming that one
# channel, first_comment the WHOLE first comment (printed verbatim, nothing appended), and these gate rows, each exactly
# PASS and not replayed. No medley row applies (no join, no clips-alone verdict, no coherence of several clips, no L-y
# shape); the R4 of a spotlight is its 28-50 s runtime (the render's edl_rules R4 / G5), the "runtime" row.
SPOTLIGHT_GATES = ("vo_fidelity_deterministic", "vo_fidelity_verdict", "duplicate", "price_now", "runtime",
                   "context_a", "context_b", "context_c", "exclusion", "second_pass", "cuttable",
                   "house_style", "hook_onset", "stand_alone",          # it opens cold: the hook's own pin-stage rows
                   "spotlight_source",                                   # ruling 92: conversation, not reaction
                   "hook_own", "stands_alone",                           # ruling 90: >= 4 as an opener, >= 4 alone
                   "step_a_two_families", "visual", "window_12h", "never_delivered", "one_per_channel_day",
                   "precheck")                                           # rulings 68 / 72 / 73 / 84: pass or adopt
CLOSING_GATES = ("closing_value", "closing_fidelity", "closing_context")   # ruling 91: a non-null closing only with all
# RULING 91, its MEDLEY half ('22:53' Nov 13: "The same value verdict also applies to a MEDLEY's takeaway going
# forward"; the row agreed with the integrator 05:5x ET Nov 14): a medley carrying a takeaway (the VO line after the
# LAST clip) ships it only with this row exactly PASS, not replayed, its "text" the takeaway it judged (the render binds
# the row to the line it plays). A medley with no takeaway (L-y's no-voice shape) needs no row.
TAKEAWAY_GATES = ("takeaway_value",)
SPOT_RUNTIME_S = (28.0, 50.0)            # ruling 90: the moment, the closing line, sign-off, credits card and outro
SPOT_CLOSING_MAX_WORDS = 12              # ruling 90 / 91: at most ONE closing line of 12 words or fewer
CREDITS_LINE = "Credits \U0001F9E1"      # ruling 90: PBX's first-comment format, 'Credits' and the orange heart


def _closing(pk):
    """The spotlight's closing line in a package (pk["vo"]) or in a pin's moments_package (edl_vo), else None."""
    vo = (pk or {}).get("vo") if isinstance((pk or {}).get("vo"), dict) else (pk or {}).get("edl_vo")
    return (vo or {}).get("closing")


def takeaway_line(pk):
    """A medley's takeaway, the VO line after its LAST clip, else None (only a medley has one: bridge_slots). pk: a
    package (pk["vo"]: bridges with bridges_after_clip, the clips counted from pk["segments"]) or a pin's
    moments_package (edl_vo's last bridge, when vo_jobs names a "takeaway": to_pin writes it for exactly that line)."""
    if (pk or {}).get("shape") != "medley":
        return None
    vo = pk.get("vo")
    if isinstance(vo, dict):
        last = len(pk.get("segments") or []) - 1
        hit = [t for t, a in zip(vo.get("bridges") or [], vo.get("bridges_after_clip") or []) if a == last]
        return hit[-1] if hit else None
    ev = pk.get("edl_vo")
    if isinstance(ev, dict) and (pk.get("vo_jobs") or {}).get("takeaway") == "takeaway" and ev.get("bridges"):
        b = ev["bridges"][-1]
        return b.get("text") if isinstance(b, dict) else None
    return None


def required_gates(pk):
    """The rows a package's inventory must hold, each exactly PASS: REQUIRED_GATES, and for a medley (L-y) also the
    clips-alone verdict and the L-y shape, plus TAKEAWAY_GATES whenever it carries a takeaway (ruling 91, the medley
    half). A spotlight (ruling 90): SPOTLIGHT_GATES, plus CLOSING_GATES whenever its closing line is not null (ruling
    91). pk: a package, or a pin's moments_package."""
    shape = (pk or {}).get("shape")
    if shape == "spotlight":
        return SPOTLIGHT_GATES + (CLOSING_GATES if _closing(pk) is not None else ())
    return REQUIRED_GATES + (MEDLEY_GATES if shape == "medley" else ()) + \
        (TAKEAWAY_GATES if takeaway_line(pk) is not None else ())


def takeaway_problems(pk):
    """[why] for a medley whose takeaway_value row (ruling 91) did not judge exactly the takeaway that ships: the row's
    "text" must equal the line after the last clip, character for character (the render compares after strip(); this
    is stricter, so every pin passing here passes there). The row's status is gate_problems' (required_gates)."""
    t = takeaway_line(pk)
    if t is None:
        return []
    row = (pk.get("gates") or {}).get("takeaway_value")
    if not isinstance(row, dict) or not isinstance(row.get("text"), str) or row["text"] != t:
        return ["takeaway_value: the value verdict did not judge the takeaway that ships (ruling 91)"]
    return []


def first_comment_text(lines, tags):
    """RULING 90: the first comment in PBX's format, the WHOLE comment: the casual line(s), a blank line, 'Credits' and
    the orange heart, a blank line, the credits (verified X handles, or the untagged names). Code, never the model."""
    return f"{lines}\n\n{CREDITS_LINE}\n\n{' '.join(tags)}"


class PinRefused(Exception):
    """The package may not become a pinned decision."""


RECENCY_AT = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


def recency_problems(segments):
    """[why] for segments that do not state the recency facts the render clock checks (ruling 1, 22:40): every segment
    a bool "time_sensitive" and "source_published_at" as "YYYY-MM-DDTHH:MM:SSZ" (UTC) that parses."""
    from datetime import datetime
    out = []
    for i, s in enumerate(segments):
        if type(s.get("time_sensitive")) is not bool:
            out.append(f"segment {i}: time_sensitive must be true or false (got {s.get('time_sensitive')!r})")
        at = s.get("source_published_at")
        ok = isinstance(at, str) and bool(RECENCY_AT.match(at))
        if ok:
            try:
                datetime.strptime(at, "%Y-%m-%dT%H:%M:%SZ")
            except ValueError:
                ok = False
        if not ok:
            out.append(f"segment {i}: source_published_at must be YYYY-MM-DDTHH:MM:SSZ (got {at!r})")
    return out


SEALED_LATER = ("time_sensitive", "source_published_at",   # ruling 1 (22:40): the render clock checks L-v 3 on these
                "speaker",                                 # the 00:05 ET Nov 13 order, item 3
                "trimmed_leading", "untrimmed_start",      # ruling 33 part 2 (render merged 11e361cc): only when a word
                "scorer_pending",                          # is trimmed, so every other pin seals as before (ruling 49 a;
                                                           # retired by ruling 56: kept so its pins still recompute)
                "scorer_verdict",                          # ruling 56: the clip scorer's affirmation, only when sealed
                "attested",                                # ruling 67: the attested-text re-seal's record (re-sealed)
                "visual")                                  # ruling 70: the clip's visual record (flags, sheet sha)
TRIMMED_PER_PIN_MAX = 1                                    # ruling 49 (b): package.TRIMMED_PER_LINEUP_MAX. Kept a
                                                           # separate constant (a test holds them equal): the
                                                           # integrator's check_pin_only imports this module, which
                                                           # must never pull package.py into that process
TRIM_WORDS = ("but", "and", "so", "well", "now", "yeah")   # ruling 33: the ONE leading word a cut may trim
SCORER_MIN = 3.5                                           # = stand_alone.CLIP_MIN_SCORE (a test holds them equal)


WINDOW_H = 12.0          # RULING 76 (orchestrator 18:08 Nov 13): a clip only while its source is <= 12 h old on the
                         # RENDER clock; past it, expired for good (it superseded ruling 57's 72 h window)


def window_problems(segments, now=None):
    """RULING 76 (a) and (c): every segment's source was published within WINDOW_H of the render clock `now` (default:
    this moment, so the check is made again whenever a pin would go to render). An unknown or unreadable publish time
    is a problem (never assumed fresh), and so is a time without a zone: as eligibility._parse_time reads it, no
    measurement (audit 1810 C1). -> [why]."""
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:                               # audit 1810 C3: the render clock is never zoneless
        raise ValueError("the render clock needs a zone")
    out = []
    for s in segments or []:
        p = s.get("source_published_at") or s.get("published_at")
        try:
            t = datetime.fromisoformat(str(p).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            out.append(f"ruling 76: {s.get('video_id')}: no readable publish time ({p!r})")
            continue
        if t.tzinfo is None:
            out.append(f"ruling 76: {s.get('video_id')}: a publish time without a zone ({p!r}) is no measurement")
            continue
        age = (now - t).total_seconds() / 3600.0
        if age > WINDOW_H:
            out.append(f"ruling 76: {s.get('video_id')} was published {p}, {age:.1f} h before the render clock (over "
                       f"{WINDOW_H:g} h): expired")
    return out


def seal(segments, edl_vo, signoff, title, caption, gates, btc_screen=None, shape=None, first_comment=None):
    """sha256 over the gated bytes, in a canonical form both sides compute: the segments (video, start, end, the exact
    words, the transcript sha, and each SEALED_LATER field the segment carries), the VO the renderer will speak (intro,
    bridges with after_clip), the sign-off, the ONE title and caption (law L-t), and the gate inventory.
    A SEALED_LATER field enters the body only when the segment carries its key. Every pin sealed before that field
    existed then recomputes to its own package_sha256: the integrator's check recomputes seals with this module, and
    all 6 earlier pins in tests/package/proof failed under an always-present field. A new pin always carries them,
    because to_pin refuses one without (recency_problems, speaker_problems), and removing one changes the digest.
    btc_screen (ruling 34: the miner's about-Bitcoin screen the render applies, {"pattern", "source"}) enters the body
    only when given, so every pin sealed before it recomputes; a moments medley always carries it (screen_problems).
    RULING 90, the spotlight: for shape "spotlight" only, the body gains edl_vo's "closing" (null included), the
    shape and first_comment. A medley's body never holds them, so every pin sealed before the spotlight recomputes
    (pin_seal)."""
    def body_of(s):
        b = {"video_id": s["video_id"], "start": round(float(s["start"]), 3), "end": round(float(s["end"]), 3),
             "text": s["approved_text"], "transcript_sha256": s.get("transcript_sha256")}
        b.update({k: s[k] for k in SEALED_LATER if k in s})
        return b
    body = {"segments": [body_of(s) for s in segments],
            "vo": {"intro": edl_vo.get("intro"), "bridges": [{"text": b["text"], "after_clip": b["after_clip"]}
                                                             for b in edl_vo.get("bridges") or []]},
            "signoff": signoff, "title": title, "caption": caption, "gates": gates}
    if btc_screen is not None:
        body["btc_screen"] = btc_screen
    if shape == "spotlight":                               # ruling 90: the closing line, the kind and the comment,
        body["vo"]["closing"] = edl_vo.get("closing")      # sealed; keyed on the kind alone, so no medley's body
        body["shape"], body["first_comment"] = shape, first_comment   # can change (audit 2322 C1, glm)
    return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def pin_seal(pin):
    """The package_sha256 a pin's own bytes recompute to, exactly as to_pin sealed it, for every kind (a medley, the
    PBX MAX v3 shape, a spotlight): the readiness check's one call. Raises KeyError / TypeError on a pin without the
    sealed fields."""
    mp = pin["moments_package"]
    shape = mp.get("shape")
    return seal(pin["segments"], mp["edl_vo"], mp["signoff_expected"], mp["title"], mp["caption"], mp["gates"],
                mp.get("btc_screen"), shape="spotlight" if shape == "spotlight" else None,
                first_comment=mp.get("first_comment") if shape == "spotlight" else None)


def affirmed_verdict(s):
    """RULING 56 under RULING 60: True when the segment carries the render's own clip scorer's AFFIRMATION of exactly its
    text (approved_text in a pin, text in a package): scorer_verdict with affirmed true, kind "moments" and no event
    (the stand-alone judgment), threshold SCORER_MIN and a numeric score at or over it (the score alone,
    stand_alone.affirmed(moments=True)), a scorer_sha, and text_sha256 = the sha256 of the text's UTF-8 bytes."""
    v = s.get("scorer_verdict")
    num = lambda x: isinstance(x, (int, float)) and not isinstance(x, bool)
    text = s["approved_text"] if "approved_text" in s else s.get("text")
    return isinstance(v, dict) and v.get("affirmed") is True and v.get("kind") == "moments" and "event" in v and \
        v["event"] is None and num(v.get("score")) and v.get("threshold") == SCORER_MIN and v["score"] >= SCORER_MIN \
        and bool(v.get("scorer_sha")) and isinstance(text, str) and \
        v.get("text_sha256") == hashlib.sha256(text.encode("utf-8")).hexdigest()


def scorer_problems(segments):
    """[why] for segments that need the clip scorer and do not carry its affirmation (ruling 56: "seal only what it
    affirms"): every clip after the hook whose first word is a conjunction or a reply fragment (the render's
    stand_alone.check_edl asks its scorer for exactly these), and any segment carrying a scorer_verdict that is not an
    affirmation of exactly its text. A trimmed clip's affirmation is trim_problems'."""
    import stand_alone as SA
    out = []
    for i, s in enumerate(segments):
        text = s["approved_text"] if "approved_text" in s else s.get("text")
        w = SA._words(text)[:1]
        needs = i > 0 and bool(w) and (w[0] in SA.CONJUNCTIONS or w[0] in SA.REPLY_FRAGMENTS)
        if needs and not affirmed_verdict(s):
            out.append(f"segment {i}: opens on {w[0]!r}: the clip scorer's affirmation of its text must be sealed "
                       f"(ruling 56)")
        elif "scorer_verdict" in s and not affirmed_verdict(s):
            out.append(f"segment {i}: carries a clip-scorer verdict that does not affirm exactly its text (ruling 56)")
    return out


def trim_problems(segments):
    """[why] for segments whose trim does not match the render's contract (ruling 33 part 2; pinned.validate_schema
    refuses anything else): "trimmed_leading" and "untrimmed_start" both present or both absent; the trimmed word's
    canonical token one of TRIM_WORDS; 0 <= untrimmed_start < start. RULING 49 (b): at most TRIMMED_PER_PIN_MAX
    trimmed clips. RULING 56 ("seal only what it affirms", retiring 49 a's pending form): every trimmed clip carries
    the clip scorer's affirmation of its trimmed text (affirmed_verdict), and no segment carries scorer_pending."""
    import canon
    out = []
    n = sum("trimmed_leading" in s or "untrimmed_start" in s for s in segments)
    if n > TRIMMED_PER_PIN_MAX:
        out.append(f"{n} trimmed clips: at most {TRIMMED_PER_PIN_MAX} until the first is affirmed at validate "
                   f"(ruling 49 b)")
    for i, s in enumerate(segments):
        has_w, has_s = "trimmed_leading" in s, "untrimmed_start" in s
        if "scorer_pending" in s:
            out.append(f"segment {i}: scorer_pending is no longer sealed (ruling 56: seal only what the scorer "
                       f"affirms)")
        if not has_w and not has_s:
            continue
        if not affirmed_verdict(s):
            out.append(f"segment {i}: a trimmed clip must carry the clip scorer's affirmation of its trimmed text "
                       f"(ruling 56)")
        if has_w != has_s:
            out.append(f"segment {i}: trimmed_leading and untrimmed_start come together (ruling 33 part 2)")
            continue
        w, u, st = s["trimmed_leading"], s["untrimmed_start"], s.get("start")
        tok = canon.canon_tokens(w) if isinstance(w, str) else []          # exactly ONE canonical token: the
        if len(tok) != 1 or tok[0] not in TRIM_WORDS:                      # render's pinned.validate_schema
            out.append(f"segment {i}: trimmed_leading {w!r} must be ONE word, one of {'/'.join(TRIM_WORDS)}")
        num = lambda x: isinstance(x, (int, float)) and not isinstance(x, bool)
        if not num(u) or not num(st) or not 0 <= float(u) < float(st):   # never raises (audit 0530 C1, glm P0-8)
            out.append(f"segment {i}: untrimmed_start {u!r} must be a number with 0 <= it < start {st!r}")
    return out


def screen_problems(pk):
    """[why] for a moments medley that does not carry the screen its line-up was judged with (ruling 34). The render
    reads moments_package.btc_screen and, without it, applies the stricter every-segment rule, so a pin judged with
    the screen but sealed without it could be refused at render. A carried screen is {"pattern": a non-empty str of at
    most 500 characters that compiles with re.I, "source": a non-empty str}: the render's own acceptance
    (run_fresh.moments_screen)."""
    if pk.get("shape") not in ("medley", "spotlight"):    # ruling 90: a spotlight is judged with the screen too
        return []
    sc = pk.get("btc_screen")
    if not isinstance(sc, dict) or set(sc) != {"pattern", "source"}:
        return [f"btc_screen: a {pk.get('shape')} must carry {{pattern, source}} (ruling 34)"]
    pat, src = sc.get("pattern"), sc.get("source")
    if not isinstance(pat, str) or not pat.strip() or len(pat) > 500 or not isinstance(src, str) or not src.strip():
        return ["btc_screen: the pattern must be a non-empty str of at most 500 characters, with a source"]
    try:
        re.compile(pat, re.I)
    except re.error as e:
        return [f"btc_screen: the pattern does not compile ({e})"]
    judged = ((pk.get("gates") or {}).get("stand_alone") or {}).get("screen")
    if judged != pat:                  # the sealed screen IS the one the line-up passed with (audit 0426 C1, glm P1-1)
        return [f"btc_screen: the sealed pattern is not the one the stand_alone row judged with ({judged!r})"]
    return []


def speaker_problems(segments):
    """[why] for segments whose speaker record (speakers.attribute) is missing or malformed: the orchestrator's 00:05 ET
    Nov 13 order (item 3) has every pin carry, per segment, the speaker's name (or "unknown", never a guess) with its
    evidence. A named speaker needs the source line that names them and the basis that shows they speak the clip."""
    out = []
    for i, s in enumerate(segments):
        sp = s.get("speaker")
        if not isinstance(sp, dict) or not isinstance(sp.get("name"), str) or not sp["name"].strip():
            out.append(f'segment {i}: no speaker record (a name, or "unknown")')
        elif not isinstance(sp.get("people"), list) or type(sp.get("measured")) is not bool:
            out.append(f"segment {i}: the speaker record states no people list or no measured flag")
        elif not all(isinstance(p, dict) and isinstance(p.get("name"), str) and p["name"].strip() and
                     isinstance(p.get("line"), str) and p["line"].strip() and p.get("role") in ("host", "guest", "other")
                     for p in sp["people"]):
            out.append(f"segment {i}: a person without a name, a source line or a role")
        elif sp["name"] != "unknown" and sp["measured"] is not True:
            out.append(f"segment {i}: speaker {sp['name']!r} is named by a record that was not measured")   # C2 glm N1
        elif sp["name"] != "unknown" and not all(isinstance(sp.get(k), str) and sp[k].strip() for k in ("line", "basis")):
            out.append(f"segment {i}: speaker {sp['name']!r} is named without the source line and the basis")
        elif sp["name"] != "unknown" and not any(p["name"] == sp["name"] and p["line"] == sp["line"] and
                                                 p["role"] == sp.get("role") for p in sp["people"]):
            out.append(f"segment {i}: speaker {sp['name']!r} is not one of the people the source names, with that "
                       f"person's line and role")             # what speakers.check produces (audit 0007 C1 K1)
    return out


def gate_problems(gates, required=REQUIRED_GATES):
    """[why] for an inventory that does not authorise a pin (empty = every required gate exactly PASS, measured live)."""
    if not isinstance(gates, dict):
        return ["no gate inventory"]
    out = []
    for g in required:
        row = gates.get(g)
        if not isinstance(row, dict) or row.get("status") != "PASS":
            out.append(f"{g}: {(row or {}).get('status') if isinstance(row, dict) else 'missing'}")
        elif row.get("replayed") is not False:
            out.append(f"{g}: replayed or not stated (never deliverable, law L-j)")
    return out


def bridge_slots(pk):
    """The line slot of each VO bridge, in order: bridge_1, bridge_2 ...; in a medley (L-y) the line after the LAST clip
    is the "takeaway" and the one bridge before it is bridge_1."""
    vo = pk.get("vo") or {}
    after = list(vo.get("bridges_after_clip") or [])
    last = len(pk.get("segments") or []) - 1
    if pk.get("shape") == "medley":
        return ["takeaway" if a == last else f"bridge_{i + 1}" for i, a in enumerate(after)]
    return [f"bridge_{i + 1}" for i in range(len(vo.get("bridges") or []))]


def line_problems(pk):
    """The gated lines must BE the VO, title and caption that will be spoken and shown (audit C2 K3)."""
    by = {x.get("slot"): x.get("text") for x in pk.get("lines") or []}
    vo = pk.get("vo") or {}
    out = []
    if by.get("intro") != vo.get("intro"):
        out.append("intro")
    bridges, after = list(vo.get("bridges") or []), list(vo.get("bridges_after_clip") or [])
    slots = bridge_slots(pk)
    if len(bridges) != len(after) or any(by.get(s) != t for s, t in zip(slots, bridges)) or \
            any(k not in slots and (k.startswith("bridge_") or k == "takeaway") for k in by if k):
        out.append("bridges")
    for k in ("title", "caption"):
        if by.get(k) != pk.get(k):
            out.append(k)
    if pk.get("shape") == "spotlight":                    # ruling 90: the closing line and the first comment too
        if by.get("closing") != vo.get("closing"):
            out.append("closing")
        cr = pk.get("comment_credits") or {}
        com = by.get("comment")
        if not isinstance(com, str) or not com.strip() or not isinstance(cr.get("tags"), list) or \
                not all(isinstance(t, str) and t.strip() for t in cr["tags"]) or \
                pk.get("first_comment") != first_comment_text(com, cr["tags"]):
            out.append("first_comment")
    return out


def spotlight_problems(pk):
    """[why] for a spotlight that breaks the agreed contract (ruling 90): exactly ONE segment; no intro and no bridge;
    a closing line of at most SPOT_CLOSING_MAX_WORDS words, or null; a sign-off that names the segment's channel; a
    non-empty first comment; the runtime estimate inside SPOT_RUNTIME_S. Any other shape: none."""
    if pk.get("shape") != "spotlight":
        return []
    out = []
    segs = pk.get("segments") or []
    vo = pk.get("vo") or {}
    if len(segs) != 1:
        out.append(f"a spotlight has exactly one segment (got {len(segs)})")
    if vo.get("intro") is not None or vo.get("bridges") or vo.get("bridges_after_clip"):
        out.append("a spotlight has no intro and no bridge (ruling 90)")
    c = vo.get("closing")
    if c is not None and (not isinstance(c, str) or not c.strip() or len(c.split()) > SPOT_CLOSING_MAX_WORDS):
        out.append(f"the closing line must be null or 1-{SPOT_CLOSING_MAX_WORDS} words (ruling 90): {c!r}")
    ch = segs[0].get("channel") if len(segs) == 1 else None
    if not isinstance(ch, str) or not ch.strip() or ch not in str(vo.get("signoff") or ""):
        out.append(f"the sign-off must name the spotlight's one channel {ch!r} (ruling 90)")
    if not isinstance(pk.get("first_comment"), str) or not pk["first_comment"].strip():
        out.append("a spotlight carries its first comment (ruling 90)")
    rt = pk.get("runtime_s_estimate")
    if not isinstance(rt, (int, float)) or isinstance(rt, bool) or not SPOT_RUNTIME_S[0] <= rt <= SPOT_RUNTIME_S[1]:
        out.append(f"runtime estimate {rt!r} outside {SPOT_RUNTIME_S[0]:g}-{SPOT_RUNTIME_S[1]:g} s (ruling 90)")
    return out


def to_pin(pk, run_name):
    problems = gate_problems(pk.get("gates"), required_gates(pk)) + [f"{x}: the gated line differs from the one shipped"
                                                                     for x in line_problems(pk)] + \
        recency_problems(pk.get("segments") or []) + speaker_problems(pk.get("segments") or []) + \
        screen_problems(pk) + trim_problems(pk.get("segments") or []) + scorer_problems(pk.get("segments") or []) + \
        spotlight_problems(pk) + takeaway_problems(pk)
    if problems:
        raise PinRefused("the package's gates do not authorise a pin: " + "; ".join(problems))
    segs = []
    for i, s in enumerate(pk["segments"]):
        segs.append({"role": "hook" if i == 0 else "clip", "video_id": s["video_id"], "channel": s["channel"],
                     "start": round(float(s["start"]), 3), "end": round(float(s["end"]), 3),
                     "approved_text": s["text"], "transcript_sha256": s.get("transcript_sha256"),
                     "time_sensitive": s.get("time_sensitive"), "source_published_at": s.get("source_published_at"),
                     "speaker": s.get("speaker"),                     # 00:05 ET Nov 13 item 3 (sealed)
                     **{k: s[k] for k in ("trimmed_leading", "untrimmed_start", "scorer_verdict", "visual",
                                          "attested")      # rulings 68 / 72: an adopted spoken text, sealed
                        if k in s},
                     "time_coords": "youtube", "source": {"kind": "youtube"}})
    edl_vo = {"intro": pk["vo"]["intro"],
              "bridges": [{"text": t, "after_clip": a} for t, a in zip(pk["vo"]["bridges"], pk["vo"]["bridges_after_clip"])]}
    spot = pk.get("shape") == "spotlight"                 # ruling 90: the agreed contract
    if spot:
        edl_vo["closing"] = pk["vo"].get("closing")
    sha = seal(segs, edl_vo, pk["vo"]["signoff"], pk["title"], pk["caption"], pk["gates"], pk.get("btc_screen"),
               shape="spotlight" if spot else None, first_comment=pk["first_comment"] if spot else None)
    return {"schema": SCHEMA, "story_id": f"moments-{run_name}-{sha[:8]}",
            "label": "bitcoin", "headline": pk["title"],
            "approved_by": "machine:pp-selectid moments-first (REVIEW ONLY, not approved by a human)",
            "approved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "approval_ref": f"docs/audits/parallel/pp-selectid_STATE.md (top package, {run_name})",
            "machine_cuts": True, "segments": segs,
            "moments_package": {"schema": pk["schema"], "package_sha256": sha, "type": pk["type"],
                                "vo_kind": pk.get("vo_kind"), "edl_vo": edl_vo,
                                "signoff_expected": pk["vo"]["signoff"],
                                "title": pk["title"], "caption": pk["caption"],
                                "hook_first_words": pk["hook_first_words"],
                                "vo_jobs": {**({"intro": "context" if pk.get("shape") != "medley" else "connection"}
                                               if pk["vo"]["intro"] else {}),
                                            **{s: "takeaway" if s == "takeaway" else "connection"
                                               for s in bridge_slots(pk)},
                                            **({"closing": "closing"} if spot and edl_vo["closing"] is not None
                                               else {})},
                                "shape": pk.get("shape"),
                                "bridge": pk.get("bridge"),
                                "supply_exception": pk.get("supply_exception"),
                                "no_voice": pk.get("no_voice"),          # ruling 3 (22:40): why no VO line ships
                                "caption_fallback": bool(pk.get("caption_fallback")),   # ruling 65 (b): a placeholder
                                **({"first_comment": pk["first_comment"],              # ruling 90: sealed, printed
                                    "first_comment_credits": pk.get("comment_credits"),  # verbatim; who is tagged
                                    "spotlight": pk.get("spotlight")}                  # and why (outside the seal)
                                   if spot else {}),
                                "gates": pk["gates"],
                                **({"btc_screen": pk["btc_screen"]} if pk.get("btc_screen") is not None else {}),
                                "checks": {"vo_fidelity_ok": True, "context_integrity_ok": True,
                                           "derived_from": "gates (every required row exactly PASS, checked above)",
                                           "models": pk.get("models")},
                                "runtime_s_estimate": pk["runtime_s_estimate"],
                                "cut_evidence": pk.get("cut_evidence"),
                                "sources_30s_before": [s["url_30s_before"] for s in pk["segments"]]}}


def write_pin(pk, run_name, out_dir, name="MOMENTS_PIN.json"):
    pin = to_pin(pk, run_name)
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, name)
    with open(path, "w") as f:
        json.dump(pin, f, indent=1)
    return path, pin
