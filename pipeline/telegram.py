#!/usr/bin/env python3
"""pipeline/telegram.py — the ONE path for review drops to the approval chat (never publishing).

Red-team 2026-11-11 (A): a drop is sent only when release_auth.authorise(run_dir) passes: the run's attestation is
ALL_PASS, deliverable, and every bound file (both finals, EDL, manifests, gate report, verification pack, contact
sheets) still has its attested sha256. There is no other send path: the legacy send_telegram_preview (guards on
VERIFIED_BY_ORCHESTRATOR / gate_results_*.json / GATE_FAIL.txt, 16:9 only, "gates PASS") is removed, and a run
that is not authorised is never sent (no REVIEW ONLY drop; a HOLD's run dir is its record, orchestrator 08:30).
Ad-hoc requests.post / curl sends are FORBIDDEN (M16).
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def send_telegram_preview(*_a, **_k):
    """Removed (red-team A, GPT-gates F03 / Claude-gates X5 / C3): the legacy entry point trusted
    VERIFIED_BY_ORCHESTRATOR, a truthy all_pass and GATE_FAIL.txt. Every drop goes through deliver_run."""
    raise RuntimeError("STOP: send_telegram_preview is removed; use telegram.deliver_run (release_auth.authorise)")


# ==============================================================
# run_fresh drops (mission 4a / DEC-8; red-team A 2026-11-11): authorised runs only, both aspects
# ==============================================================

HOLD_OK = "HOLD FOR APPROVAL - all release gates passed, no waivers"
CAPTION_MAX = 1024                       # Telegram caption limit
TEXT_MAX = 4096                          # Telegram sendMessage limit
VIDEO_MAX_BYTES = 49_000_000             # Bot API upload limit is 50 MB; checked BEFORE the first send (X1)
DIMS = {"16x9": (1920, 1080), "9x16": (1080, 1920)}
FINALS = {"16x9": "out/segment.mp4", "9x16": "out/segment_vertical.mp4"}


def _fit(text, limit):
    """text within limit characters, the cut marked (Claude-gates X3: the marker is counted)."""
    sfx = " ...(see GATE_REPORT)"
    return text if len(text) <= limit else text[:limit - len(sfx)] + sfx


def snapshot(run_dir, att):
    """The metadata a drop is built from, read ONCE as bytes and verified against the attestation before it is
    parsed (cycle-2 #3: the EDL and the gate report were re-read after authorisation): {"edl", "report",
    "registry"}. Raises when any of them changed."""
    import hashlib
    out = {}
    for key, rel in (("edl", "edl.json"), ("report", "GATE_REPORT.json")):
        with open(os.path.join(run_dir, rel), "rb") as f:
            b = f.read()
        if hashlib.sha256(b).hexdigest() != (att.get("files") or {}).get(rel):
            raise RuntimeError(f"STOP: {rel} changed after it was authorised")
        out[key] = json.loads(b)
    with open(REGISTRY, "rb") as f:
        b = f.read()
    if hashlib.sha256(b).hexdigest() != att.get("registry_sha256"):
        raise RuntimeError("STOP: the channel registry changed after the run was authorised")
    out["registry"] = {e.get("display_name"): e for e in json.loads(b)}
    return out


REGISTRY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "channels.json")


def build_caption(run_dir, fmt, att, option=None, duration=None, snap=None):
    """The caption of an AUTHORISED run: verdict line first; the MONITORING rows that did not pass are listed as
    reported, not release-deciding (addendum '22:15' item 4). snap: the verified snapshot (deliver_run)."""
    import release_auth
    import vertical_layout
    edl = (snap or snapshot(run_dir, att))["edl"]
    mon = release_auth.monitoring_report(att.get("rows") or {}).get(fmt) or {}
    head = HOLD_OK + (f" | {len(mon)} MONITORING check(s) NOT passed (not release-deciding)" if mon else "")
    if option:
        head = f"OPTION {option} (transition choice) | {head}"
    lines = [head, f"{os.path.basename(os.path.normpath(run_dir))} | {fmt} {DIMS[fmt][0]}x{DIMS[fmt][1]}"
             + (f" | {duration:.1f} s" if duration else ""),
             f"Story: {edl.get('topic', '')}",
             "Clips: " + ", ".join([edl["hook"].get("channel", "?")] + [c.get("channel", "?") for c in edl.get("clips", [])])]
    if mon:                                  # claude-fable audit batch 16 #1: never 'all passed' with a failure unsaid
        lines.insert(1, "Monitoring (reported, not release-deciding): " + "; ".join(f"{k} {v}" for k, v in mon.items()))
    note = vertical_layout.layout_note(edl) if fmt == "9x16" else ""
    if note:
        lines.append(note)
    return _fit("\n".join(lines), CAPTION_MAX)


def _dims(path):
    import subprocess
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=width,height:format=duration", "-of", "json", path],
                       capture_output=True, text=True, check=True, timeout=30)
    j = json.loads(r.stdout)
    return int(j["streams"][0]["width"]), int(j["streams"][0]["height"]), float(j["format"]["duration"])


def _numeric_claims(tokens):
    """(sign, value, unit) for every number in canonical tokens: the sign from a 'minus' / 'plus' right before it,
    the unit from a 'dollars' / 'percent' right after it."""
    import re
    out = []
    for k, t in enumerate(tokens):
        if re.fullmatch(r"\d+(\.\d+)?|ord\d+", t):        # ordinals too: an invented 'November 8th' (E-FAIL-038)
            sign = tokens[k - 1] if k and tokens[k - 1] in ("minus", "plus") else None
            unit = tokens[k + 1] if k + 1 < len(tokens) and tokens[k + 1] in ("dollars", "percent") else None
            out.append((sign, t, unit))
    return out


UP = {"rise", "rises", "rose", "risen", "rising", "up", "gain", "gains", "gained", "surge", "surges", "surged", "jump",
      "jumps", "jumped", "climb", "climbs", "climbed", "higher", "rally", "rallies", "rallied", "inflow", "inflows"}
DOWN = {"fall", "falls", "fell", "fallen", "falling", "down", "drop", "drops", "dropped", "decline", "declines",
        "declined", "plunge", "plunges", "plunged", "slide", "slides", "slid", "lower", "sank", "sinks", "outflow",
        "outflows", "loss", "losses", "lost"}


NAME_STOP = UP | DOWN | set("""a an the this that these those it its it's as at by for from in into of on onto to with
without after before over under above below amid and or but nor so yet if than then why how what when where who whom
which while is are was were be been being has have had do does did will would can could may might must shall should
new old big biggest top says said sees saw hits hit sets set gets got makes made takes took faces eyes nears tops
breaks broke holds held shows showed sheds shed adds added cuts cut posts posted buys bought sells sold plans warns
calls amid as week weekly month monthly year daily day today now just more most less least first last next record""".split())


def _clauses(text):
    import re
    return [c for c in re.split(r"[.;!?:]+\s+|[.;!?]+$|\s+[-\u2013\u2014]\s+(?=\D)|\n", text or "") if c.strip()]


def headline_numbers_said(run_dir, snap=None):
    """Claude-gates T13 / GPT audit batch 16 #7 / cycle-2 #8: every number in the headline the drop shows (caption
    story line, suggested title) is SAID in the attested final, IN CONTEXT, in BOTH formats: some clause of G18's
    readings of that format's final contains the claim with the same sign and no conflicting unit (a reading
    without 'dollars' is whisper's '$' habit; 'percent' must be heard as percent), every proper name of the
    headline clause (its capitalised words, the first included, but not function words, direction words or common
    headline verbs: NAME_STOP), and a direction word of the same direction when
    the headline clause has one (rose / fell ...). Returns the headline claims that are not said; no readings =
    all. snap: the verified snapshot (deliver_run); without it the files are read (tests)."""
    import canon
    import re
    if snap is None:
        with open(os.path.join(run_dir, "edl.json")) as f:
            edl = json.load(f)
        with open(os.path.join(run_dir, "GATE_REPORT.json")) as f:
            report = json.load(f)
    else:
        edl, report = snap["edl"], snap["report"]
    g18 = report.get("G18") or {}
    reads = {fmt: [canon.canon_tokens(c) for r in (g18.get(fmt) or []) if isinstance(r, dict)
                   for c in _clauses(r.get("heard") or "")] for fmt in ("16x9", "9x16")}
    missing = []
    for head in (edl.get("headline"), edl.get("topic")):
        for clause in _clauses(head or ""):
            claims = _numeric_claims(canon.canon_tokens(clause))
            if not claims:
                continue
            names = {t for w in clause.split() if re.match(r"[A-Z]", w.strip("'\"(")) and not re.search(r"\d", w)
                     for t in canon.canon_tokens(w) if t not in NAME_STOP}      # the subject is usually the FIRST word
            toks = set(canon.canon_tokens(clause))
            pol = "up" if toks & UP and not toks & DOWN else "down" if toks & DOWN and not toks & UP else None
            for sign, value, unit in claims:
                def said_in(rc):
                    rs = set(rc)
                    ok_claim = any(v == value and s == sign and (u == unit or (unit == "dollars" and u is None)
                                                                 or (unit is None and u != "percent"))
                                   for s, v, u in _numeric_claims(rc))
                    ok_dir = pol is None or (rs & (UP if pol == "up" else DOWN)) and not rs & (DOWN if pol == "up" else UP)
                    return ok_claim and names <= rs and bool(ok_dir)
                if not all(any(said_in(rc) for rc in reads[fmt]) for fmt in ("16x9", "9x16")):
                    missing.append(" ".join(x for x in (sign, value, unit) if x))
    return sorted(set(missing))


def _plan(run_dir, option, sheets, att, snap=None):
    """Every message of the drop, built and checked BEFORE anything is sent (X1 / X4 / T13): the two finals at
    their real dimensions and size, the contact sheets, and (release drop) the publishing kit."""
    plan = []
    snap = snap or snapshot(run_dir, att)
    bad = headline_numbers_said(run_dir, snap)
    if bad:
        raise RuntimeError(f"STOP: the headline states numbers the video does not say: {bad}")
    for fmt, rel in FINALS.items():
        path = os.path.join(run_dir, rel)
        w, h, dur = _dims(path)
        if (w, h) != DIMS[fmt]:
            raise RuntimeError(f"STOP: {fmt} final is {w}x{h}, expected {DIMS[fmt][0]}x{DIMS[fmt][1]}")
        if os.path.getsize(path) > VIDEO_MAX_BYTES:
            raise RuntimeError(f"STOP: {fmt} final is {os.path.getsize(path)} bytes > {VIDEO_MAX_BYTES} (Bot API limit)")
        plan.append({"key": f"video:{fmt}", "kind": "video", "path": path, "rel": rel, "format": fmt,
                     "fields": {"caption": build_caption(run_dir, fmt, att, option, duration=dur, snap=snap), "width": w,
                                "height": h, "duration": int(round(dur)), "supports_streaming": "true"}})
    for fmt in (("16x9", "9x16") if sheets else ()):        # one contact sheet of the finished video per format
        rel = f"qa/contact_sheet_{fmt}.jpg"
        p = os.path.join(run_dir, rel)
        kind = "photo" if _photo_ok(p) else "document"
        if kind == "document" and os.path.getsize(p) > VIDEO_MAX_BYTES:
            raise RuntimeError(f"STOP: {rel} is too large for a document send")
        plan.append({"key": f"sheet:{fmt}", "kind": kind, "path": p, "rel": rel, "sheet": os.path.basename(p),
                     "fields": {"caption": f"contact sheet {fmt}: 2 s stills, +-3 frames at every boundary, "
                                           f"full-resolution credits" + (" and segment first frames" if fmt == "9x16" else "")}})
    if not option:                          # the publishing kit (orchestrator 2026-11-11 15:30), same thread
        kit = publish_kit(run_dir, snap)
        if len(kit) > TEXT_MAX:
            raise RuntimeError(f"STOP: publishing kit is {len(kit)} characters > {TEXT_MAX}")
        plan.append({"key": "kit", "kind": "message", "path": "", "rel": None, "kit": kit, "fields": {"text": kit}})
    return plan


def deliver_run(run_dir, option=None, send=None, sheets=True):
    """Send an AUTHORISED run's two finals to the approval chat (never publishing), each with its caption, plus
    (sheets=True) both contact sheets and (release drop) the publishing kit. send(kind, path, fields, data=bytes)
    -> message_id (tests inject it).
      - release_auth.authorise first: not authorised = nothing is sent (raises with the reasons)
      - every payload is built and checked against Telegram's limits before the first send
      - each file is read ONCE into memory, those bytes are hashed against the attestation, and exactly those
        bytes are uploaded (the path is never reopened: GPT audit batch 16 #2)
      - TELEGRAM_DELIVERY[_<option>].json (one delivery at a time per run: an exclusive lock) records each message
        as IN FLIGHT, durably, BEFORE its request; success replaces it with the message id, a definite refusal
        (SendRejected) clears it; anything else leaves it unknown. A rerun resumes after the last sent message,
        never resends one in flight or unknown (GPT audit batch 16 #3), and a complete drop is never repeated."""
    import fcntl
    import hashlib
    import release_auth
    send = send or _send_bot_api
    ok, why, att = release_auth.authorise(run_dir)
    if not ok:
        raise RuntimeError("STOP: not authorised for release: " + "; ".join(why))
    rpath = os.path.join(run_dir, f"TELEGRAM_DELIVERY{'_' + option if option else ''}.json")
    lock = open(os.path.join(run_dir, "TELEGRAM_DELIVERY.lock"), "w")     # ONE lock per run, any option (cycle-2 #1)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        raise RuntimeError(f"STOP: another delivery of {run_dir} is running") from None
    import glob
    for other in sorted(glob.glob(os.path.join(run_dir, "TELEGRAM_DELIVERY*.json"))):   # the run's whole ledger
        if other == rpath:
            continue
        o = json.load(open(other))
        if o.get("status") == "complete" or o.get("unknown") or o.get("in_flight") or o.get("messages"):
            raise RuntimeError(f"STOP: these finals were already (partly) sent by {os.path.basename(other)}")
    att_sha = release_auth.sha256(os.path.join(run_dir, "ATTESTATION.json"))
    record = {"option": option, "authorised": True, "attestation_sha256": att_sha, "status": "in_progress",
              "messages": [], "unknown": [], "in_flight": None}
    if os.path.exists(rpath):
        record = json.load(open(rpath))
        if record.get("status") == "complete":
            raise RuntimeError(f"STOP: already delivered: {rpath}")
        if record.get("attestation_sha256") != att_sha:
            raise RuntimeError("STOP: a partial delivery of another attestation exists; reconcile it by hand")
        if record.get("unknown") or record.get("in_flight"):
            raise RuntimeError(f"STOP: outcome unknown for {record.get('unknown') or [record.get('in_flight')]}; "
                               "reconcile in the chat before resending")
    sent = {m.get("key") for m in record["messages"]}
    snap = snapshot(run_dir, att)                    # the metadata, verified once, used for every message

    def save():
        tmp = rpath + ".tmp"
        with open(tmp, "w") as f:
            json.dump(record, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, rpath)
        dfd = os.open(os.path.dirname(rpath) or ".", os.O_RDONLY)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    plan = [item for item in _plan(run_dir, option, sheets, att, snap) if item["key"] not in sent]
    payload = {}
    for item in plan:                                # EVERY payload read and verified BEFORE the first send, so a
        if item["rel"]:                              # changed 9:16 can never follow a sent 16:9 (cycle 2 F7)
            with open(item["path"], "rb") as f:
                payload[item["key"]] = f.read()
            if hashlib.sha256(payload[item["key"]]).hexdigest() != (att.get("files") or {}).get(item["rel"]):
                raise RuntimeError(f"STOP: {item['rel']} changed after it was authorised")
    for item in plan:
        data = payload.get(item["key"])
        record["in_flight"] = item["key"]
        save()                                       # durable BEFORE the request
        try:
            mid = send(item["kind"], item["path"], item["fields"], data=data)
        except SendRejected:
            record["in_flight"] = None                # Telegram said no: nothing was sent; a rerun may retry it
            save()
            raise
        except Exception:
            record["unknown"].append(item["key"])     # the request may have reached Telegram
            record["in_flight"] = None
            save()
            raise
        m = {"key": item["key"], "message_id": mid}
        if item["kind"] == "video":
            m.update(format=item["format"], caption=item["fields"]["caption"],
                     sha256=hashlib.sha256(data).hexdigest())
        elif item["key"].startswith("sheet:"):
            m.update(sheet=item["sheet"], **{"as": item["kind"]})
        else:
            m.update(publish_kit=item["kit"])
        record["messages"].append(m)
        record["in_flight"] = None
        save()
    record["status"] = "complete"
    save()
    return record


ORANGE_HEART = "\U0001F9E1"


def publish_kit(run_dir, snap=None):
    """Suggested title, a description crediting and linking every source channel (its channel page and the exact
    video the clip came from), and the first-comment credit line in PBX's fixed format: "credits:" then every
    creator's @handle, a line break, then the orange heart on its own line. Nothing is published."""
    import credit_rings
    if snap is None:                                 # tests; deliver_run always passes the verified snapshot
        with open(os.path.join(run_dir, "edl.json")) as f:
            edl = json.load(f)
        with open(REGISTRY) as f:
            reg = {e.get("display_name"): e for e in json.load(f)}
    else:
        edl, reg = snap["edl"], snap["registry"]
    credited = credit_rings.credit_channels(edl)
    vids = {}
    for seg in [edl.get("hook") or {}] + list(edl.get("clips") or []):
        if seg.get("channel") and seg.get("video_id"):
            vids.setdefault(seg["channel"], [])
            if seg["video_id"] not in vids[seg["channel"]]:
                vids[seg["channel"]].append(seg["video_id"])
    headline = (edl.get("headline") or edl.get("topic") or "").strip().rstrip(".")
    lines = [f"SUGGESTED TITLE: {headline} | Pulse Check", "", "DESCRIPTION:",
             f"{headline}. Every clip in this Pulse Check is a creator's own words; go follow them:"]
    missing = [ch for ch in credited if not (reg.get(ch, {}).get("yt_handle") and reg.get(ch, {}).get("url")
                                             and vids.get(ch))]
    if not credited or missing:                      # Claude-gates X4: never a bare name or an empty link
        raise RuntimeError(f"STOP: publishing kit incomplete (handle / url / source video): {missing or 'no credits'}")
    for ch in credited:
        e = reg[ch]
        src = ", ".join(f"https://www.youtube.com/watch?v={v}" for v in vids[ch])
        lines.append(f"- {ch} {e['yt_handle']}: {e['url']} (clip from {src})")
    handles = " ".join(reg[ch]["yt_handle"] for ch in credited)
    lines += ["", "FIRST COMMENT:", f"credits: {handles}", ORANGE_HEART]
    return "\n".join(lines)


PHOTO_MAX_BYTES = 9_500_000     # Telegram sendPhoto takes <= 10 MB; the margin keeps a near-limit sheet from a
                                # rejected send. Above it the sheet goes as a document: it still arrives, full size.


def _photo_ok(path):
    """Telegram sendPhoto limits: <= 10 MB (PHOTO_MAX_BYTES, with margin), width + height <= 10000,
    aspect ratio <= 20."""
    from PIL import Image
    try:
        w, h = Image.open(path).size
    except Exception:                       # unreadable image: send it as a document (never lose the delivery record)
        return False
    return os.path.getsize(path) <= PHOTO_MAX_BYTES and w + h <= 10000 and max(w, h) / max(1, min(w, h)) <= 20


class SendRejected(RuntimeError):
    """Telegram answered and refused the message: it was NOT sent (a rerun may send it)."""


def _send_bot_api(kind, path, fields, data=None):
    """One sendVideo / sendPhoto / sendDocument / sendMessage to the approval chat (M16 path). Credentials never
    printed: a network error is re-raised by type only (its text carries the URL with the token, Claude-gates X2);
    a refusal from Telegram raises SendRejected; anything else (timeout, connection, unreadable answer) means the
    outcome is unknown and the caller must not resend it automatically."""
    import requests
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "video_pipeline_v3"))
    from relay import get_key
    tok, chat = get_key("TELEGRAM_BOT_TOKEN"), get_key("TELEGRAM_CHAT_ID")
    if not tok or not chat:
        raise SendRejected("STOP: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set")
    method, field = {"video": ("sendVideo", "video"), "photo": ("sendPhoto", "photo"),
                     "document": ("sendDocument", "document"), "message": ("sendMessage", None)}[kind]
    if field is not None and data is None:      # a definite non-send, decided before any request (cycle 2 F7)
        raise SendRejected("STOP: no payload bytes for a file send")
    try:
        if field is None:                       # plain text in the same chat (the publishing kit)
            resp = requests.post(f"https://api.telegram.org/bot{tok}/{method}", data={"chat_id": chat, **fields},
                                 timeout=60)
        else:                                   # exactly the bytes deliver_run hashed (never the path again)
            resp = requests.post(f"https://api.telegram.org/bot{tok}/{method}", data={"chat_id": chat, **fields},
                                 files={field: (os.path.basename(path), data)}, timeout=600)
        data = resp.json()
    except Exception as e:
        raise RuntimeError(f"STOP: Telegram {method}: outcome unknown ({type(e).__name__})") from None
    # only an exact success or an EXPLICIT refusal is a known outcome (cycle-2 #2: '{}' from a proxy is not a refusal)
    if isinstance(data, dict) and data.get("ok") is True and isinstance(data.get("result"), dict) \
            and type(data["result"].get("message_id")) is int:
        return data["result"]["message_id"]
    if isinstance(data, dict) and data.get("ok") is False and type(data.get("error_code")) is int:
        raise SendRejected(f"STOP: Telegram {method} refused: {data.get('error_code')} {data.get('description')}")
    raise RuntimeError(f"STOP: Telegram {method}: outcome unknown (unrecognised answer)")


# ==============================================================
# REVIEW DROP (orchestrator order 2026-11-12 '13:06'; law L-j unchanged): an engineering REVIEW of a run that is NOT
# a pass, beside the release path and never part of it. GPT audit batch 16: "Unverified material can go to a clearly
# labelled engineering review destination. It must not carry the production PASS label." A review drop never creates
# or implies a release authorisation (deliver_run still requires release_auth.authorise).
# ==============================================================

REVIEW_HEAD = "REVIEW ONLY - NOT A PASS - not for publishing"
# content-integrity rows: a run that fails any of them is never dropped, not even for review. V1 (two vision models)
# is droppable ONLY when every failing V1 item is a SPLIT (one model yes, one no; ruling 23 '13:18'); both-no, a
# missing answer, or a failing credits item whose measured ring geometry (G15_credits, DEC-11) is not PASS refuse.
REVIEW_NOT_DROPPABLE = ("G16_sentence_boundary", "G17_onset_tail", "G12_credits", "G15_credits",
                        "G20_signoff_names_all", "V1_visual_checklist")


G20_DROP_RATIO = 0.75   # the review-drop amendment (orchestrator 2026-11-12 '23:20'): the decoder's spelling of a name


def _g20_spelling(run_dir, fmt):
    """The review-drop amendment to G20 (orchestrator 2026-11-12 '23:20'): (droppable, description) for a G20 row that is
    not PASS. Droppable ONLY when the sign-off SCRIPT names every credited channel (the strict pre-render reading, never
    phonetic), nothing was heard that is not credited, and each missing name's closest same-length stretch of the
    decode is at least G20_DROP_RATIO similar to the name or one of its registry aliases: then the only mismatch is the
    decoder's spelling, and both strings are quoted. A name absent from the script is never droppable."""
    from difflib import SequenceMatcher
    import gates as G
    try:
        with open(os.path.join(run_dir, "GATE_REPORT.json")) as f:
            d = json.load(f)[f"G20_{fmt}"]
        with open(os.path.join(run_dir, "vo_audio", "VO_MANIFEST.json")) as f:
            script = json.load(f)["signoff"]["text"]
        with open(REGISTRY) as f:
            reg = json.load(f)
        credited, missing, extra = list(d["credited"]), list(d["missing"]), list(d["extra"])
        t = G._g20_norm(d["transcript"])
    except (OSError, ValueError, KeyError, TypeError) as e:
        return False, f"the G20 evidence is not readable ({type(e).__name__}: {e})"
    if not credited or not missing or extra or not t:
        return False, f"credited {credited}, missing {missing}, heard but not credited {extra}"
    named = G.spoken_channels(script, reg, credited)
    if named != set(credited):
        return False, f"the sign-off script does not name {sorted(set(credited) - named)}: never droppable"
    forms = {e["display_name"]: [e["display_name"]] + list(e.get("aliases") or []) for e in reg}
    desc = []
    for name in missing:
        best = (0.0, "", name)
        for form in forms.get(name, [name]):
            n = G._g20_norm(form)
            for j in range(max(1, len(t) - len(n) + 1)):
                r = SequenceMatcher(None, n, t[j:j + len(n)]).ratio()
                if r > best[0]:
                    best = (r, t[j:j + len(n)], form)
        if best[0] < G20_DROP_RATIO:
            return False, (f"'{name}': the decode's closest stretch '{best[1]}' is {best[0]:.2f} similar to "
                           f"'{best[2]}' (< {G20_DROP_RATIO}): not a spelling")
        desc.append(f"the script says '{best[2]}', the decoder wrote '{best[1]}' ({best[0]:.2f})")
    return True, "decoder spelling only: " + "; ".join(desc)


def _v1_split(run_dir, fmt, rows):
    """Ruling 23: (droppable, description) for a V1 row that is not PASS, from VERIFY/VERIFICATION.json."""
    try:
        with open(os.path.join(run_dir, "VERIFY", "VERIFICATION.json")) as f:
            vis = (json.load(f).get("visual") or {}).get(fmt) or {}
    except (OSError, ValueError):
        return False, "VERIFICATION.json not readable"
    per = vis.get("per_model") or {}
    if len(per) < 2:
        return False, "fewer than two vision models answered"
    items, desc = {}, []
    for m, d in per.items():                                       # the checklist, per model
        for k, a in (d.get("rows") or {}).items():
            items.setdefault(("checklist", k), {})[m] = (bool(a.get("ok")), str(a.get("answer")), a.get("why") or "")
    for part, key in (("letterbox_per_shot", "shots"), ("boundaries", "cuts")):   # per shot / per boundary
        for e in (vis.get(part) or {}).get(key) or []:
            if isinstance(e, dict) and e.get("ok") is False:
                name = e.get("boundary") or f"{e.get('label')}#{e.get('shot')}"
                # the item failed; its question's polarity is per item ('no' can be the good answer), so a
                # split here is the two models DISAGREEING (cycle-2 F2)
                items[(part, name)] = {m: (None, str(a), "") for m, a in (e.get("answers") or {}).items()}
    failing = {k: v for k, v in items.items() if any(ok is not True for ok, _, _ in v.values())}
    if not failing:                                   # cycle-2 F1: a non-PASS V1 with nothing readable never drops
        return False, "V1 is not PASS but no failing item can be read"
    for (part, name), ans in sorted(failing.items()):
        said = {a.strip().lower() for _, a, _ in ans.values()}
        if part == "checklist":
            yes = [m for m, (ok, a, _) in ans.items() if ok]
            no = [m for m, (ok, a, _) in ans.items() if not ok and a.strip().lower() == "no"]
            split = bool(yes) and len(yes) + len(no) == len(ans) and bool(no)
        else:
            split = said == {"yes", "no"} and len(ans) >= 2
        if not split:
            return False, f"{name}: not a split ({'; '.join(f'{m} {a}' for m, (ok, a, _) in ans.items())})"
        if name == "credits_round_and_match" and rows.get("G15_credits") != "PASS":
            return False, f"{name}: the measured ring geometry (G15_credits) is {rows.get('G15_credits')}"
        desc.append(f"split on {name}: " + "; ".join(f"{m} '{a}'" + (f" (\"{w[:220]}\")" if w else "")
                                                     for m, (ok, a, w) in sorted(ans.items())))
    try:
        with open(os.path.join(run_dir, "VERTICAL_LAYOUT.json")) as f:
            lay = json.load(f)
        layouts = ", ".join(f"{k} {','.join(sorted({s.get('class') for s in v.get('shots') or []}))}"
                            for k, v in lay.items() if isinstance(v, dict) and v.get("shots"))
        if fmt == "9x16" and layouts:
            desc.append(f"9:16 layouts: {layouts}")
    except (OSError, ValueError):
        pass
    return True, " | ".join(desc)


def _review_forbidden(text):
    """The wording a review drop may never carry (its own head excepted): PASS as a verdict, CANDIDATE FOR APPROVAL,
    approved."""
    import re
    body = text.replace(REVIEW_HEAD, "")
    hits = [m.group(0) for rx in (r"(?i)\bPASS(ED)?\b", r"(?i)CANDIDATE FOR APPROVAL", r"(?i)\bapproved\b")
            for m in re.finditer(rx, body)]
    return hits


def _row_reason(rep, fmt, row, note):
    """One measured line for a REQUIRED row that is not PASS (its note when the gate wrote one)."""
    if row == "G18_word_for_word":
        bad = [r for r in rep.get("G18", {}).get(fmt) or [] if isinstance(r, dict) and not r.get("pass")]
        def words(op, a, b):
            return {"delete": f"the final's decode omits '{a}'", "insert": f"the final's decode adds '{b}'",
                    "start": f"starts '{b}' where the lock starts '{a}'", "end": f"ends '{b}' where the lock ends '{a}'"
                    }.get(op, f"'{a}' heard as '{b}'")
        return "; ".join(f"{r.get('segment')}: " + (r.get("error") or ", ".join(
            words(op, a, b) for op, a, b in (r.get("edges") or []) + (r.get("identity") or [])) or
            ("the token's audio is not the source's" if r.get("acoustic_mismatch") else "see GATE_REPORT")) for r in bad) \
            or "see GATE_REPORT.json"
    if row == "G3c_acoustic_tail":
        lc = (rep.get("L-c") or {}).get(fmt) or {}
        edges = lc.get("g3c_failed_edges") or []
        proof = lc.get("final_proof") or {}
        return "; ".join(f"{seg} {side} edge: acoustic onset on the final; not proved by L-c "
                         f"({((proof.get(seg) or {}).get(side) or {}).get('why', 'no proof')})"
                         + _edge_levels(rep.get("_run_dir"), fmt, seg, side) for seg, side in edges) \
            or (note or "see GATE_REPORT.json")
    return str(note) if note else "see GATE_REPORT.json"


def _edge_levels(run_dir, fmt, seg, side, span=0.4):
    """The measured level over a clip edge's last / first `span` s: the prepared clip (speech stem) vs the final."""
    try:
        import numpy as np
        import sentence_law as L
        with open(os.path.join(run_dir, "qa", f"concat_manifest_{fmt}.json")) as f:
            sg = {s["label"]: s for s in json.load(f)["segments"]}[seg]
        prep = os.path.join(run_dir, "qa", (f"final_{seg}.mp4" if fmt == "16x9" else f"vert_{seg}.mp4"))
        dur = float(sg["end"]) - float(sg["start"])
        t0 = dur - span - 0.05 if side == "out" else 0.05
        _, dp = L.SourceAudio(prep).sl(t0, t0 + span)
        _, df = L.SourceAudio(os.path.join(run_dir, FINALS[fmt])).sl(float(sg["start"]) + t0, float(sg["start"]) + t0 + span)
        return (f"; measured over the clip's {'last' if side == 'out' else 'first'} {span} s: prepared clip median "
                f"{np.median(dp):.1f} dB, final median {np.median(df):.1f} dB")
    except Exception:
        return ""


def review_nonpass(run_dir):
    """[(format, row, verdict, reason)] for every REQUIRED row (release_auth's inventory) that is not exactly
    PASS, from the run's GATE_REPORT.json; refuses without one."""
    import release_auth
    p = os.path.join(run_dir, "GATE_REPORT.json")
    if not os.path.exists(p):
        raise RuntimeError("STOP: review drop: no GATE_REPORT.json for this run")
    with open(p) as f:
        rep = json.load(f)
    rep["_run_dir"] = run_dir
    out = []
    for fmt in ("16x9", "9x16"):
        rows = (rep.get("rows") or {}).get(fmt) or {}
        notes = (rep.get("notes") or {}).get(fmt) or {}
        for k in sorted(release_auth.INVENTORY[fmt]):
            v = rows.get(k, "MISSING")
            if v != "PASS":
                out.append((fmt, k, str(v), _row_reason(rep, fmt, k, notes.get(k))))
    return out


def review_texts(run_dir, nonpass, digests):
    """The video captions and the review note, generated here and nowhere else (the caller cannot edit them):
    the head first, then every non-pass REQUIRED row, the files' sha256, run id, HEAD, title, caption, the
    per-clip source links and the deviations."""
    with open(os.path.join(run_dir, "edl.json")) as f:
        edl = json.load(f)
    head = ""
    try:
        with open(os.path.join(run_dir, "PROVENANCE.json")) as f:
            prov = json.load(f)
        head = str((prov.get("code") or {}).get("git_head") or prov.get("launch_revision") or "")
    except (OSError, ValueError):
        pass
    run_id = os.path.basename(os.path.abspath(run_dir).rstrip("/"))
    rows = ", ".join(sorted({f"{k} {v}" for _, k, v, _ in nonpass})) or "none"
    caps = {fmt: _fit(f"{REVIEW_HEAD}\nNot passing (required): {rows}\nrun {run_id} | {fmt} sha256 {digests[fmt]}"
                      f"\nReasons, links and deviations: the review note in this chat.", CAPTION_MAX)
            for fmt in FINALS}
    segs = [("hook", edl.get("hook") or {})] + [(f"clip {c.get('index', i + 1)}", c)
                                                 for i, c in enumerate(edl.get("clips") or [])]
    links = edl.get("moments_sources_30s_before") or []
    lines = [REVIEW_HEAD, "", "Required rows NOT passing (verbatim, with the measured reason):"]
    lines += [f"- {fmt} {k} {v}: {why}" for fmt, k, v, why in nonpass] or ["- none"]
    lines += ["", f"Run {run_id} | HEAD {head or 'not recorded'}",
              f"16:9 sha256 {digests['16x9']}", f"9:16 sha256 {digests['9x16']}", "",
              f"Title: {edl.get('title')}", f"Caption: {edl.get('caption')}", "", "Sources (~30 s before each clip):"]
    for i, (role, s) in enumerate(segs):
        link = links[i] if isinstance(links, list) and i < len(links) else \
            f"https://www.youtube.com/watch?v={s.get('video_id')}"
        lines.append(f"- {role}: {s.get('channel')} | {s.get('duration')} s of locked words | {link}")
    dev = []
    for fmt, rel in FINALS.items():
        try:
            d = _dims(os.path.join(run_dir, rel))[2]
            if not 60.0 <= d <= 70.0:
                dev.append(f"{fmt} runtime {d:.3f} s, outside the 60-70 s format target (ruling 12: 58-72 accepted)")
        except Exception:
            dev.append(f"{fmt} runtime not measured")
    for i, (role, s) in enumerate(segs):
        lo, hi = (8.0, 12.0) if i == 0 else (12.0, 20.0)
        dur = s.get("duration")
        if isinstance(dur, (int, float)) and not lo <= dur <= hi:
            dev.append(f"{role}: {dur} s of locked words, outside the {lo:.0f}-{hi:.0f} s taste target (L-o)")
        for alt in (s.get("selection_lock") or {}).get("alternatives") or []:
            dev.append(f"{role}: one unstressed word heard as " + " or ".join(f"'{r}'" for r in alt.get("readings") or [])
                       + " by different transcribers; audio is the speaker's own, unedited (ruling 18)")
    try:
        with open(os.path.join(run_dir, "vo_audio", "VO_MANIFEST.json")) as f:
            spoken = ((json.load(f).get("signoff") or {}).get("text") or "").strip()
        if spoken:
            dev.append(f"sign-off spoken: the renderer's template \"{spoken}\" (ruling 15)")
    except (OSError, ValueError):
        pass
    lines += ["", "Deviations:"] + ([f"- {d}" for d in dev] or ["- none"])
    return caps, "\n".join(lines)


def review_drop(run_dir, send=None):
    """Send a run that is NOT authorised for release to the approval chat as an engineering REVIEW (order
    '13:06'): both finals + the review note. Refuses (nothing sent) without GATE_REPORT.json, when a
    content-integrity row (REVIEW_NOT_DROPPABLE) is not PASS, when any text would carry PASS-as-verdict wording,
    'CANDIDATE FOR APPROVAL' or 'approved', or when this run was already review-dropped. Writes REVIEW_DROP.json
    (what was sent, to which chat, the message ids). Never writes or reads the release ledger."""
    import hashlib
    send = send or _send_bot_api
    nonpass = review_nonpass(run_dir)
    with open(os.path.join(run_dir, "GATE_REPORT.json")) as f:
        rep_rows = json.load(f).get("rows") or {}
    v1, g20 = {}, {}
    for i, (fmt, k, v, why) in enumerate(nonpass):              # ruling 23: a V1 split is droppable, quoted
        if k == "V1_visual_checklist":
            v1[fmt] = _v1_split(run_dir, fmt, rep_rows.get(fmt) or {})
            nonpass[i] = (fmt, k, v, v1[fmt][1])
        elif k == "G20_signoff_names_all":                      # amendment '23:20': the decoder's spelling only
            g20[fmt] = _g20_spelling(run_dir, fmt)
            nonpass[i] = (fmt, k, v, g20[fmt][1])
    special = {"V1_visual_checklist": v1, "G20_signoff_names_all": g20}
    blocked = sorted({f"{fmt} {k} {v}" + (f" ({special[k][fmt][1]})" if k in special else "")
                      for fmt, k, v, _ in nonpass if k in REVIEW_NOT_DROPPABLE
                      and not (k in special and special[k].get(fmt, (False,))[0])})
    if blocked:
        raise RuntimeError("STOP: review drop refused: content-integrity rows not passing: " + ", ".join(blocked))
    rpath = os.path.join(run_dir, "REVIEW_DROP.json")
    if os.path.exists(rpath):
        raise RuntimeError("STOP: this run was already review-dropped (REVIEW_DROP.json exists)")
    payload, digests = {}, {}
    for fmt, rel in FINALS.items():
        p = os.path.join(run_dir, rel)
        if os.path.getsize(p) > VIDEO_MAX_BYTES:
            raise RuntimeError(f"STOP: {fmt} final is {os.path.getsize(p)} bytes > {VIDEO_MAX_BYTES} (Bot API limit)")
        with open(p, "rb") as f:
            payload[fmt] = f.read()                    # read once; exactly these bytes are hashed and sent
        digests[fmt] = hashlib.sha256(payload[fmt]).hexdigest()
    caps, note = review_texts(run_dir, nonpass, digests)
    for t in list(caps.values()) + [note]:
        if not t.startswith(REVIEW_HEAD):
            raise RuntimeError("STOP: review drop text does not begin with the review head")
        bad = _review_forbidden(t)
        if bad:
            raise RuntimeError(f"STOP: review drop refused: forbidden wording {sorted(set(bad))}")
    if len(note) > TEXT_MAX:
        raise RuntimeError(f"STOP: review note is {len(note)} characters > {TEXT_MAX}")
    rec = {"kind": "review_drop", "label": REVIEW_HEAD, "rule": "orchestrator order 2026-11-12 '13:06'",
           "chat": "the approval chat (TELEGRAM_CHAT_ID)", "nonpass": [list(x) for x in nonpass],
           "sha256": digests, "texts": {"captions": caps, "note": note}, "messages": []}
    try:
        for fmt, rel in FINALS.items():
            w, h, dur = _dims(os.path.join(run_dir, rel))
            mid = send("video", os.path.join(run_dir, rel), {"caption": caps[fmt], "width": w, "height": h,
                                                            "duration": int(round(dur)), "supports_streaming": "true"},
                       data=payload[fmt])
            rec["messages"].append({"key": f"video:{fmt}", "message_id": mid})
        mid = send("message", "", {"text": note})
        rec["messages"].append({"key": "note", "message_id": mid})
        rec["status"] = "complete"
    finally:
        with open(rpath, "w") as f:                    # whatever was sent is recorded, even on a failure midway
            json.dump(rec, f, indent=1)
    return rec
