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
    edl = {
        "topic": pin["label"],
        "angle": f"Pinned: {pin.get('headline') or pin['label']}",
        "hook": hook,
        "clips": clips,
        "vo": _generate_vo_script(pin["label"], hook["text"], clips, channels),
        "total_clip_duration": round(hook["duration"] + sum(c["duration"] for c in clips), 2),
        "mode": "pinned",
        "pinned_story_id": pin["story_id"],
    }
    overrides = build_vertical_overrides(hook, clips, registry)
    return edl, overrides, report


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
