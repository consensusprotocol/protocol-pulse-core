#!/usr/bin/env python3
"""pipeline/pinned.py — PINNED MODE: a thin entry point into the existing production factory.

AUTO cannot make a legal editorial decision -> a human supplies the decision (this JSON) ->
the SAME automated factory continues (run_fresh.py stages validate -> cut acceptance -> voice ->
prepare -> render 16:9 -> render 9:16 -> gates -> HOLD_FOR_HUMAN_APPROVAL).

This module is NOT an editorial subsystem, cutter, renderer or orchestrator. It only:
  1. validates a small pin JSON (schema below) — fail closed, never repairs;
  2. acquires sources with the existing helpers (select_passages._download_window +
     _whisper_transcribe, exactly as AUTO's select stage) or, for frozen local material,
     sha256-checked copies of the file and its transcript;
  3. validates each range against the source (ffprobe duration) and its transcript (speech present,
     no overlap) — it never extends, trims, snaps or "improves" a range, and never reads
     neighbouring sentences;
  4. writes the canonical edl.json + vertical_overrides.json in the exact shape
     select_passages.select_and_build_edl writes (VO from the same _generate_vo_script);
  5. provides the pinned cut table (exact human ranges, like run_isolated.write_pinned_cuts) that
     run_fresh.stage_cut then submits to the SAME cut acceptance (no auto-widen).

Pin JSON schema (protocol_pulse.pinned_story.v1):
{
  "schema": "protocol_pulse.pinned_story.v1",
  "story_id": "short id",                      # required
  "label": "short keyword label",              # required (EDL topic / VO keyword, as AUTO)
  "headline": "one line",                      # optional
  "approved_by": "PBX",                        # required: the human who made the decision
  "approved_at": "ISO-8601",                   # required
  "approval_ref": "where the approval is recorded",   # optional
  "reuses_v2f_material": false,                # optional; true only for the v2f integration proof
  "segments": [                                # exactly one hook, >= 1 clip, in playback order
    {"role": "hook" | "clip",
     "video_id": "11-char YouTube id",
     "channel": "display_name in pipeline/channels.json",
     "start": seconds, "end": seconds,
     "approved_text": "optional: the exact approved words of this range; if given it must match the
                       transcript (>= 0.8 token similarity) and sets the expected first/last words
                       that the shared edge-word check verifies",
     "time_coords": "youtube"      # seconds in the full YouTube video (source fetched as a window)
                  | "source_file", # seconds in the local source file given in "source"
     "source": {"kind": "youtube"}
             | {"kind": "local_file", "path": "repo-relative path", "sha256": "...",
                "transcript_path": "repo-relative path", "transcript_sha256": "..."}}
  ]
}
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(PIPELINE_DIR)
sys.path.insert(0, PIPELINE_DIR)
import sentence_law as L  # noqa: E402  (sentence law: selection locks, G16/G17)
CHANNELS_PATH = os.path.join(PIPELINE_DIR, "channels.json")

SCHEMA = "protocol_pulse.pinned_story.v1"
ROLES = ("hook", "clip")
COORDS = ("youtube", "source_file")
MIN_WORDS_IN_RANGE = 3
APPROVED_TEXT_MIN_RATIO = 0.8              # approved_text vs transcript words touching the range
FADE_IN_MS, FADE_OUT_MS = 20, 30           # the factory's M19 fades (cut.py / run_isolated)
_VID = re.compile(r"^[A-Za-z0-9_-]{11}$")


class PinError(Exception):
    """The pin is invalid. Fail closed; nothing is repaired."""


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                        "default=nw=1:nk=1", path], capture_output=True, text=True, timeout=60)
    try:
        return float(r.stdout.strip())
    except ValueError:
        raise PinError(f"ffprobe cannot read duration of {path}")


def _abs(p):
    return p if os.path.isabs(p) else os.path.join(REPO, p)


# ── 1. schema ──

def validate_schema(pin, registry=None):
    """Structural validation. Returns the registry record per segment. Raises PinError."""
    if registry is None:
        with open(CHANNELS_PATH) as f:
            registry = json.load(f)
    by_name = {c["display_name"]: c for c in registry}
    errs = []
    if pin.get("schema") != SCHEMA:
        errs.append(f"schema must be {SCHEMA!r}")
    for k in ("story_id", "label", "approved_by", "approved_at"):
        if not str(pin.get(k) or "").strip():
            errs.append(f"missing {k}")
    segs = pin.get("segments")
    if not isinstance(segs, list) or not segs:
        raise PinError("; ".join(errs + ["segments must be a non-empty list"]))
    roles = [s.get("role") for s in segs]
    if roles.count("hook") != 1:
        errs.append(f"exactly one hook required (got {roles.count('hook')})")
    if roles.count("clip") < 1:
        errs.append("at least one clip required")
    if roles and roles[0] != "hook":
        errs.append("the hook must be the first segment")
    if pin.get("machine_cuts") and not all(str(s.get("approved_text") or "").strip() for s in segs):
        # sentence law: a machine-built PIN carries the editor's selected sentences; the words are
        # located by text in the acquired transcript, never by window-offset arithmetic
        errs.append("machine_cuts PIN: every segment needs approved_text (the selected sentences)")
    recs = []
    for i, s in enumerate(segs):
        tag = f"segment {i} ({s.get('role')} {s.get('video_id')})"
        if s.get("role") not in ROLES:
            errs.append(f"{tag}: role must be one of {ROLES}")
        if not _VID.match(str(s.get("video_id", ""))):
            errs.append(f"{tag}: invalid video_id")
        ch = by_name.get(s.get("channel"))
        if ch is None or not ch.get("channel_id"):
            errs.append(f"{tag}: channel {s.get('channel')!r} is not a registered channel with an id")
        recs.append(ch)
        st, en = s.get("start"), s.get("end")
        if not all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in (st, en)):
            errs.append(f"{tag}: start/end must be numbers")
        elif not (0 <= st < en):
            errs.append(f"{tag}: need 0 <= start < end (got {st}, {en})")
        if s.get("time_coords") not in COORDS:
            errs.append(f"{tag}: time_coords must be one of {COORDS}")
        src = s.get("source") or {}
        if src.get("kind") == "youtube":
            if s.get("time_coords") != "youtube":
                errs.append(f"{tag}: a youtube source needs time_coords 'youtube'")
        elif src.get("kind") == "local_file":
            if s.get("time_coords") != "source_file":
                errs.append(f"{tag}: a local_file source needs time_coords 'source_file'")
            for k in ("path", "sha256", "transcript_path", "transcript_sha256"):
                if not src.get(k):
                    errs.append(f"{tag}: local_file source needs {k}")
        else:
            errs.append(f"{tag}: source.kind must be 'youtube' or 'local_file'")
    # one source per video id; no overlapping ranges within a video
    by_vid = {}
    for s in segs:
        by_vid.setdefault(s.get("video_id"), []).append(s)
    for vid, lst in by_vid.items():
        if len({json.dumps(x.get("source"), sort_keys=True) for x in lst}) > 1 or \
                len({x.get("time_coords") for x in lst}) > 1:
            errs.append(f"{vid}: all segments of one video must share source and time_coords")
        rng = sorted((x.get("start"), x.get("end")) for x in lst
                     if isinstance(x.get("start"), (int, float)) and isinstance(x.get("end"), (int, float)))
        for (a0, a1), (b0, b1) in zip(rng, rng[1:]):
            if b0 < a1:
                errs.append(f"{vid}: overlapping ranges {a0}-{a1} and {b0}-{b1}")
    if errs:
        raise PinError("; ".join(errs))
    return recs


# ── 2. acquisition (existing helpers only) ──

def acquire(pin, run_dir, log=print):
    """Returns {video_id: {"path", "offset", "transcript", "provenance"}}. Raises PinError."""
    from select_passages import _download_window, _whisper_transcribe
    os.makedirs(os.path.join(run_dir, "sources"), exist_ok=True)
    os.makedirs(os.path.join(run_dir, "transcripts"), exist_ok=True)
    out = {}
    for vid in dict.fromkeys(s["video_id"] for s in pin["segments"]):
        lst = [s for s in pin["segments"] if s["video_id"] == vid]
        src = lst[0]["source"]
        if src["kind"] == "local_file":
            p, t = _abs(src["path"]), _abs(src["transcript_path"])
            for path, want in ((p, src["sha256"]), (t, src["transcript_sha256"])):
                if not os.path.isfile(path):
                    raise PinError(f"{vid}: {path} not found")
                got = _sha256(path)
                if got != want:
                    raise PinError(f"{vid}: sha256 mismatch for {path}: {got} != {want}")
            dst = os.path.join(run_dir, "sources", f"{vid}.mp4")
            shutil.copyfile(p, dst)                       # a copy: frozen material is never linked
            tdst = os.path.join(run_dir, "transcripts", f"{vid}.json")
            shutil.copyfile(t, tdst)
            with open(tdst) as f:
                tr = json.load(f)
            out[vid] = {"path": dst, "offset": 0.0, "transcript": tr,
                        "provenance": {"kind": "local_file", "from": src["path"], "sha256": src["sha256"],
                                       "transcript_from": src["transcript_path"],
                                       "transcript_sha256": src["transcript_sha256"]}}
        else:
            lo, hi = min(s["start"] for s in lst), max(s["end"] for s in lst)
            res = _download_window(vid, lo, hi, run_dir)          # same call as AUTO's select stage
            if not res or not res[0]:
                raise PinError(f"{vid}: source download failed")
            path, offset = res
            tr = _whisper_transcribe(path, vid, run_dir)          # same call as AUTO's select stage
            if not tr:
                raise PinError(f"{vid}: transcription failed")
            out[vid] = {"path": path, "offset": float(offset), "transcript": tr,
                        "provenance": {"kind": "youtube_window", "window_offset_s": offset}}
        out[vid]["provenance"]["source_file_sha256"] = _sha256(out[vid]["path"])
        out[vid]["transcript_path"] = os.path.join(run_dir, "transcripts", f"{vid}.json")
        log(f"  {vid}: acquired ({out[vid]['provenance']['kind']})")
    return out


# ── 3. range validation (never modifies a range) ──

def validate_range(seg, acq):
    """Validate one pinned range against its source and transcript. Returns the facts derived
    from the transcript (words inside the range). Raises PinError. Never changes start/end."""
    start = seg["start"] - acq["offset"]
    end = seg["end"] - acq["offset"]
    dur = _duration(acq["path"])
    tag = f"{seg['role']} {seg['video_id']} {seg['start']}-{seg['end']}"
    if start < 0 or end > dur + 1e-6:
        raise PinError(f"{tag}: range outside the source file (file covers 0-{dur:.3f} s, "
                       f"window offset {acq['offset']} s)")
    words = acq["transcript"].get("words") or []
    # words lying entirely inside the range (a word in the boundary tail never counts)
    inside = [w for w in words if w["start"] >= start and w["end"] <= end]
    touching = [w for w in words if w["end"] > start and w["start"] < end]
    if len(inside) < MIN_WORDS_IN_RANGE:
        raise PinError(f"{tag}: transcript has {len(inside)} word(s) inside the range (need >= {MIN_WORDS_IN_RANGE})")
    straddle = [w for w in words if (w["start"] < start < w["end"]) or (w["start"] < end < w["end"])]
    out = {"start_file": round(start, 3), "end_file": round(end, 3), "source_duration": round(dur, 3),
           "words": inside, "text": " ".join(w["word"].strip() for w in inside),
           "first_word": inside[0]["word"].strip(), "last_word": inside[-1]["word"].strip(),
           "i0": words.index(inside[0]), "i1": words.index(inside[-1]),
           "transcript_word_straddles_boundary": [w["word"].strip() for w in straddle],
           "edge_words_from": "transcript words entirely inside the range"}
    approved = str(seg.get("approved_text") or "").strip()
    if approved:
        # the human-approved words for this exact range: must correspond to the source transcript
        from difflib import SequenceMatcher
        import canon                              # the one canonical form (orchestrator 2026-11-11 '21:10')
        norm = canon.canon_tokens
        a, t = norm(approved), norm(" ".join(w["word"] for w in touching))
        ratio = SequenceMatcher(None, a, t, autojunk=False).ratio()
        if ratio < APPROVED_TEXT_MIN_RATIO:
            raise PinError(f"{tag}: approved_text does not correspond to the transcript in this range "
                           f"(token similarity {ratio:.2f} < {APPROVED_TEXT_MIN_RATIO})")
        a = L.anchor(words, approved, t0=start - 3.0, t1=end + 3.0)
        if a is None:
            raise PinError(f"{tag}: approved_text edges not found as words in the transcript near the range")
        i0, i1, _ = a
        out.update(text=approved, first_word=words[i0]["word"].strip(), last_word=words[i1]["word"].strip(),
                   i0=i0, i1=i1, approved_text_similarity=round(ratio, 3),
                   edge_words_from="approved_text located by text in the transcript (sentence_law.anchor)")
    return out


# ── 3b. sentence-lock text adjudication (ruling 17, orchestrator 2026-11-12 '10:20') ──

LV2_NEGATIONS = frozenset({"not", "no", "never", "none", "nobody", "nothing", "neither", "nor", "cannot", "can't",
                           "won't", "don't", "doesn't", "didn't", "isn't", "aren't", "wasn't", "weren't", "shouldn't",
                           "wouldn't", "couldn't", "hasn't", "haven't", "hadn't"})


LV2_ORDINALS = frozenset({"first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth", "tenth",
                          "eleventh", "twelfth", "twentieth", "hundredth", "thousandth", "millionth", "billionth",
                          "half", "quarter", "double", "triple", "dozen"})


def _lv2_critical(tok, texts):
    """Law L-v 2: a number, a negation, or a name (in either text, a capitalised word that does not open a
    sentence; 'I' excepted). Conservative: a doubtful token is critical (it holds)."""
    if re.search(r"\d", tok) or tok in LV2_NEGATIONS or tok.endswith("n't") or tok in LV2_ORDINALS:
        return True                                    # any digit ('2nd', '1,000', '15%') or an ordinal is a number
    for t in texts:
        for m in re.finditer(r"[A-Za-z][A-Za-z'\u2019-]*", t or ""):
            w = m.group(0)
            if w.lower() == tok and w[0].isupper() and w != "I":
                before = t[:m.start()].rstrip()
                if before and before[-1] not in ".!?":
                    return True
    return False


def _second_recogniser_words(src_path):
    """The independent second recogniser (ElevenLabs scribe_v1) on the acquired window: words on its clock."""
    vp3 = os.path.join(os.path.dirname(PIPELINE_DIR), "video_pipeline_v3")    # relay.get_key, the key loader
    if vp3 not in sys.path:
        sys.path.insert(1, vp3)
    import second_recogniser
    words, _text, secs = second_recogniser.scribe_words(src_path)
    return words, round(secs / 60 * 0.012, 4)


def _token_word(words, i0, i1, a):
    """The index of the run word that carries canonical token a of the lock text; None when the per-word canonical
    forms do not add up to the lock text's (fail closed)."""
    import canon
    per = [canon.canon_tokens(str(words[j]["word"])) for j in range(i0, i1 + 1)]
    if [t for p in per for t in p] != canon.canon_tokens(" ".join(str(w["word"]).strip() for w in words[i0:i1 + 1])):
        return None                                  # audit batch34 F3: token for token, not only the count
    lens = [len(p) for p in per]
    k = 0
    for j, n in zip(range(i0, i1 + 1), lens):
        if k <= a < k + n:
            return j
        k += n
    return None


def adjudicate_lock(lock, src_path, words, recognise=None, log=print):
    """Ruling 17: the run's own decode (lock['text']) and the pin's approved text (lock['selected_text']) differ
    inside the locked span -> a difference on a number, a name or a negation always holds (law L-v 2); otherwise
    the independent second recogniser on the acquired window decides: when it reads the approved words at every
    difference, the lock takes the approved text (two independent decodes agree) and G18 compares the final against
    it; when it reads the run's decode, or neither, HOLD naming the three readings. No difference: the lock as is."""
    import canon
    from difflib import SequenceMatcher
    run_t, pin_t = lock["text"], lock["selected_text"]
    r, p = canon.canon_tokens(run_t), canon.canon_tokens(pin_t)
    ops = [o for o in SequenceMatcher(None, r, p, autojunk=False).get_opcodes() if o[0] != "equal"]
    if not ops:
        return lock
    tag = f"{lock['video_id']} words {lock['i0']}-{lock['i1']}"
    diffs = [[" ".join(r[a:b]), " ".join(p[c:d])] for _, a, b, c, d in ops]
    crit = sorted({t for _, a, b, c, d in ops for t in r[a:b] + p[c:d] if _lv2_critical(t, (run_t, pin_t))})
    if crit:
        raise PinError(f"{tag}: the run's decode and the approved text differ on a number, name or negation {crit} "
                       f"(law L-v 2: always holds) | run decode: {run_t!r} | approved: {pin_t!r}")
    t0, t1 = words[lock["i0"]]["start"] - 0.3, words[lock["i1"]]["end"] + 0.3
    sw, usd = (recognise or _second_recogniser_words)(src_path)
    sec_t = " ".join(str(w["word"]).strip() for w in sw
                     if t0 <= (float(w["start"]) + float(w["end"])) / 2 <= t1)
    s = canon.canon_tokens(sec_t)

    def amap(x, y):                                    # x index -> the y index the in-order alignment reads it as
        return {a + k: b + k for op, a, a2, b, _ in SequenceMatcher(None, x, y, autojunk=False).get_opcodes()
                if op == "equal" for k in range(a2 - a)}

    def reads(x, xmap, lo, hi):
        # the second recogniser reads x's words lo..hi-1 AT this position: they and one neighbour on each side are
        # all aligned and consecutive in its text (nothing else between them: a deletion is not 'a different word')
        idx = list(range(max(lo - 1, 0), min(hi + 1, len(x))))
        if not idx or not all(i in xmap for i in idx) or \
                not all(xmap[j] == xmap[i] + 1 for i, j in zip(idx, idx[1:])):
            return False
        # cycle-2 F1: at the span's start / end there is no neighbour: nothing may precede / follow it in the reading
        return (lo > 0 or xmap[idx[0]] == 0) and (hi < len(x) or xmap[idx[-1]] == len(s) - 1)
    pmap, rmap = amap(p, s), amap(r, s)
    pin_side = all(reads(p, pmap, c, d) for _, a, b, c, d in ops)
    run_side = all(reads(r, rmap, a, b) for _, a, b, c, d in ops)
    readings = {"run_decode": run_t, "approved": pin_t, "second_recogniser": sec_t}
    if not pin_side and run_side and len(ops) == 1 and ops[0][0] == "replace" and ops[0][2] - ops[0][1] == 1 \
            and ops[0][4] - ops[0][3] == 1:
        # ruling 18 ('10:36'): the decodes split on ONE non-critical token: the lock records both attested readings;
        # G18 passes the token only when the final reads one of them AND the clip's audio there is the source's
        _, a, _, c, _ = ops[0]
        wi = _token_word(words, lock["i0"], lock["i1"], a)
        if wi is None:
            raise PinError(f"{tag}: the ambiguous token cannot be located in the run's words (ruling 18: HOLD) | " +
                           " | ".join(f"{k}: {v!r}" for k, v in readings.items()))
        new = {k: v for k, v in lock.items() if k != "sha256"}
        new["alternatives"] = [{"rule": "ruling 18 (orchestrator 2026-11-12 '10:36')", "token_index": a,
                                "readings": [r[a], p[c]], "word_index": wi,
                                "source_span": [round(float(words[wi]["start"]), 3), round(float(words[wi]["end"]), 3)],
                                "recogniser": "elevenlabs:scribe_v1", "usd": usd, **readings}]
        new["sha256"] = L._lock_digest(new)
        log(f"  lock {tag}: one token heard as {r[a]!r} (run decode, second recogniser) or {p[c]!r} (approved): both "
            f"readings recorded (ruling 18)")
        return new
    if not pin_side:
        raise PinError(f"{tag}: lock text not adjudicated (ruling 17): at {diffs} the second recogniser reads "
                       f"{'the run decode' if run_side else 'neither'} | " +
                       " | ".join(f"{k}: {v!r}" for k, v in readings.items()))
    new = {k: v for k, v in lock.items() if k != "sha256"}
    new.update(text=pin_t, adjudication={"rule": "ruling 17 (orchestrator 2026-11-12 '10:20')", "verdict": "approved",
                                         "differences": diffs, "recogniser": "elevenlabs:scribe_v1", "usd": usd,
                                         **readings})
    new["sha256"] = L._lock_digest(new)
    log(f"  lock {tag}: run decode and approved text differ at {diffs}; the second recogniser reads the approved "
        f"words: the lock takes the approved text (ruling 17)")
    return new


# ── 4. canonical EDL (same shape as select_passages.select_and_build_edl) ──

def build_edl(pin, acq, registry=None, log=print):
    from select_passages import _generate_vo_script, build_vertical_overrides
    if registry is None:
        with open(CHANNELS_PATH) as f:
            registry = json.load(f)
    by_name = {c["display_name"]: c for c in registry}
    report, segs = [], []
    for s in pin["segments"]:
        a = acq[s["video_id"]]
        v = validate_range(s, a)
        ch = by_name[s["channel"]]
        lock = L.make_lock(s["video_id"], a["transcript"]["words"], v["i0"], v["i1"],
                           L.sha256_file(a["transcript_path"]), v["text"], [s["start"], s["end"]],
                           v.get("approved_text_similarity"),
                           "pinned approved_text" if s.get("approved_text") else "pinned exact range")
        if s.get("approved_text"):
            lock = adjudicate_lock(lock, a["path"], a["transcript"]["words"], log=log)    # ruling 17
        seg = {
            "video_id": s["video_id"],
            "channel": s["channel"],
            "handle": ch.get("yt_handle", ""),
            "video_title": s.get("video_title", ""),
            "text": v["text"],
            "first_word": v["first_word"],
            "last_word": v["last_word"],
            "word_start": round(a["transcript"]["words"][v["i0"]]["start"], 3),
            "word_end": round(a["transcript"]["words"][v["i1"]]["end"], 3),
            "duration": round(a["transcript"]["words"][v["i1"]]["end"] - a["transcript"]["words"][v["i0"]]["start"], 2),
            "time_coords": "source_file",
            "source_window_offset_s": round(a["offset"], 3),
            # the human decision, exact; the cut table is taken from here, never recomputed
            "pinned": {"start": v["start_file"], "end": v["end_file"], "input_start": s["start"],
                       "input_end": s["end"], "input_time_coords": s["time_coords"]},
            "cut_out": v["end_file"],
            "fade_out_ms": FADE_OUT_MS,
            "selection_lock": lock,
        }
        segs.append(seg)
        report.append({"role": s["role"], "video_id": s["video_id"], "channel": s["channel"],
                       "input": [s["start"], s["end"], s["time_coords"]],
                       "source_file_range": [v["start_file"], v["end_file"]],
                       "source_duration": v["source_duration"], "words_in_range": len(v["words"]),
                       "first_word": v["first_word"], "last_word": v["last_word"],
                       "transcript_word_straddles_boundary": v["transcript_word_straddles_boundary"],
                       "edge_words_from": v["edge_words_from"],
                       "approved_text_similarity": v.get("approved_text_similarity"),
                       "provenance": a["provenance"]})
    hook, clips = segs[0], segs[1:]
    for i, c in enumerate(clips, 1):
        c["index"] = i
    channels = sorted({x["channel"] for x in segs})
    has_mp = "moments_package" in pin           # pp-selectid R7: a moments-first package (law L-q) as the decision;
    mp = pin.get("moments_package")            # PRESENT = validated strictly (null or a non-object is refused)
    vo = _generate_vo_script(pin["label"], hook["text"], clips, channels)
    if has_mp:
        vo = moments_vo(mp, clips, pin["segments"])
    edl = {
        "topic": pin["label"],
        "angle": f"Pinned: {pin.get('headline') or pin['label']}",
        "hook": hook,
        "clips": clips,
        "vo": vo,
        "total_clip_duration": round(hook["duration"] + sum(c["duration"] for c in clips), 2),
        "mode": "pinned",
        "pinned_story_id": pin["story_id"],
    }
    if has_mp:                                 # law L-t: the ONE title and caption travel in the EDL, whose bytes the
        edl.update(title=mp["title"], caption=mp["caption"],      # release authorisation re-hashes before any send
                   package_type=mp.get("type"),                   # edl_rules R4: 'moments' has its own VO budget
                   moments_package_sha256=mp["package_sha256"],   # the packager's digest of its full record
                   moments_package_pin_sha256=hashlib.sha256(json.dumps(mp, sort_keys=True).encode()).hexdigest(),
                   moments_checks=mp["checks"],                   # ^ this render's own digest of what it renders
                   moments_sources_30s_before=list(mp["sources_30s_before"]))
    overrides = build_vertical_overrides(hook, clips, registry)
    return edl, overrides, report


def moments_vo(mp, clips, segments=None):
    """The package's VO, checked by its VO-fidelity and context-integrity gates (pipeline/package.py): the intro and
    the bridges, each after a clip (after the LAST clip too only for a package of type 'moments', law L-q, '06:00'), in
    the EDL's shape ({"text", "after_clip"}). Strict (cycle 1 of its
    audit): the package must be an object; both gate verdicts exactly true, and every other '*_ok' check too; title and
    caption non-empty strings; package_sha256 64 lowercase hex characters; edl_vo an object; intro null or a non-empty
    string; bridges a list of objects with non-empty string text and an INTEGER after_clip, strictly increasing, in
    1..last-1, or 1..last for type 'moments' (render16 / render_vertical key bridges by after_clip: an out-of-order or
    repeated index is refused, never re-sorted).
    Anything else is a PinError."""
    if not isinstance(mp, dict):
        raise PinError("moments_package is not an object")
    if segments is not None:                   # bound to THIS pin's segments (cycle 2: a package rides only its clips)
        links = mp.get("sources_30s_before")
        if not isinstance(links, list) or len(links) != len(segments) or not all(
                isinstance(u, str) and f"v={s['video_id']}" in u for u, s in zip(links, segments)):
            raise PinError("moments_package sources_30s_before must list one link per pin segment, in order, each to "
                           "that segment's video")
        first = mp.get("hook_first_words")
        if first is not None and (not isinstance(first, str) or not " ".join(
                str(segments[0].get("approved_text") or "").lower().split()).startswith(" ".join(first.lower().split()))):
            raise PinError("moments_package hook_first_words do not open the pin's hook")
    checks = mp.get("checks")
    if not isinstance(checks, dict) or checks.get("vo_fidelity_ok") is not True \
            or checks.get("context_integrity_ok") is not True:
        raise PinError("moments_package: the VO-fidelity and context-integrity gates did not both pass (each must be "
                       "exactly true)")
    if not all(isinstance(k, str) for k in checks):
        raise PinError("moments_package checks keys must be strings")
    failed = sorted(k for k, v in checks.items() if k.endswith("_ok") and v is not True)
    if failed:
        raise PinError(f"moments_package: checks not passed: {failed}")
    for k in ("title", "caption"):
        if not isinstance(mp.get(k), str) or not mp[k].strip():
            raise PinError(f"moments_package {k} must be a non-empty string")
    if not isinstance(mp.get("package_sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", mp["package_sha256"]):
        raise PinError("moments_package package_sha256 must be 64 lowercase hex characters")
    v = mp.get("edl_vo")
    if not isinstance(v, dict):
        raise PinError("moments_package edl_vo must be an object {intro, bridges}")
    if "intro" not in v or "bridges" not in v:
        raise PinError("moments_package edl_vo must state both intro and bridges (null / [] when there are none)")
    intro, bridges = v["intro"], v["bridges"]
    if intro is not None and (not isinstance(intro, str) or not intro.strip()):
        raise PinError("moments_package intro must be null or a non-empty string")
    if not isinstance(bridges, list):
        raise PinError("moments_package bridges must be a list")
    idx = sorted(c["index"] for c in clips)
    if not idx:
        raise PinError("moments_package: the pin has no clips")
    last, prev = idx[-1], 0
    top = last if mp.get("type") == "moments" else last - 1   # law L-q (orchestrator 2026-11-12 '06:00'): a package
    for b in bridges:                                          # of type 'moments' may close on a takeaway line after
        if not isinstance(b, dict) or not isinstance(b.get("text"), str) or not b["text"].strip():   # the LAST clip
            raise PinError(f"moments_package bridge {b!r}: needs non-empty text")      # (render16 / render_vertical
        a = b.get("after_clip")                                                       # play it before the shout-out)
        if type(a) is not int or a not in idx or a > top or a <= prev:
            raise PinError(f"moments_package bridge {b!r}: after_clip must be an integer clip index in 1..{top}, "
                           f"strictly increasing")
        prev = a
    return {"intro": intro, "bridges": [{"text": b["text"], "after_clip": b["after_clip"],   # law L-y 2: a bridge's
                                         **({"why": b["why"]} if "why" in b else {})}       # recorded reason,
                                        for b in bridges]}                                   # read by R11


def prepare(pin_path, run_dir, log=print):
    """Validate + acquire + build. Writes edl.json, vertical_overrides.json, PINNED_DECISION.json.
    Returns the PINNED_DECISION record. Raises PinError."""
    raw = open(pin_path, "rb").read()
    pin = json.loads(raw)
    with open(CHANNELS_PATH) as f:
        registry = json.load(f)
    validate_schema(pin, registry)
    acq = acquire(pin, run_dir, log=log)
    edl, overrides, report = build_edl(pin, acq, registry, log=log)
    with open(os.path.join(run_dir, "edl.json"), "w") as f:
        json.dump(edl, f, indent=2)
    with open(os.path.join(run_dir, "vertical_overrides.json"), "w") as f:
        json.dump(overrides, f, indent=2)
    # Optional human/model editorial judgment travels with the PIN but is kept
    # separate from the canonical EDL. stage_validate applies the shared gate.
    if isinstance(pin.get("editorial_review"), dict):
        with open(os.path.join(run_dir, "EDITORIAL_REVIEW.json"), "w") as f:
            json.dump(pin["editorial_review"], f, indent=2)
    rec = {"mode": "pinned", "pin_path": os.path.abspath(pin_path),
           "pin_sha256": hashlib.sha256(raw).hexdigest(), "pin": pin, "validation": report,
           "rule": "ranges are used exactly as supplied: never extended, trimmed, snapped or improved"}
    with open(os.path.join(run_dir, "PINNED_DECISION.json"), "w") as f:
        json.dump(rec, f, indent=2)
    for r in report:
        log(f"  {r['role']:4} {r['video_id']} {r['source_file_range'][0]:.3f}-{r['source_file_range'][1]:.3f} "
            f"'{r['first_word']}' ... '{r['last_word']}' ({r['words_in_range']} words)")
    return rec


# ── 5. pinned cut table (exact ranges; acceptance is run_fresh.stage_cut's existing check) ──

def write_pinned_cut_table(run_dir):
    """cuts_final.json from the pinned EDL ranges, exactly (no acoustic search, no widening).
    Same entry shape as cut.compute_all_cuts / run_isolated.write_pinned_cuts."""
    with open(os.path.join(run_dir, "edl.json")) as f:
        edl = json.load(f)
    if edl.get("mode") != "pinned":
        raise PinError("write_pinned_cut_table called on a non-pinned EDL")
    cuts = []
    for label, seg in [("hook", edl["hook"])] + [(f"clip_{c['index']:02d}", c) for c in edl["clips"]]:
        p = seg["pinned"]
        cuts.append({"clip_id": label, "video_id": seg["video_id"], "channel": seg.get("channel", ""),
                     "cut_in": p["start"], "cut_out": p["end"], "cut_duration": round(p["end"] - p["start"], 3),
                     "fade_out_ms": FADE_OUT_MS, "fade_in_ms": FADE_IN_MS,
                     "last_word_expected": seg.get("last_word", ""),
                     "first_word_expected": seg.get("first_word", ""),
                     "verified": True, "pinned": True})
    with open(os.path.join(run_dir, "cuts_final.json"), "w") as f:
        json.dump(cuts, f, indent=2)
    return cuts
