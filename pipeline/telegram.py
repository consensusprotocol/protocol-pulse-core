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
