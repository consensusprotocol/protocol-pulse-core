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
  "segments": [                                # exactly one hook, >= 1 clip, in playback order (a spotlight, law L-ab: ONE hook)
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
import time

PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(PIPELINE_DIR)
sys.path.insert(0, PIPELINE_DIR)
import sentence_law as L  # noqa: E402  (sentence law: selection locks, G16/G17)
CHANNELS_PATH = os.path.join(PIPELINE_DIR, "channels.json")

SCHEMA = "protocol_pulse.pinned_story.v1"
ROLES = ("hook", "clip")
COORDS = ("youtube", "source_file")
# law L-ab SPOTLIGHT (rulings 90 / 91 / 92, orchestrator 2026-11-13 '22:41' / '22:53'; the pin contract agreed with the
# builder): moments_package.shape 'spotlight' = ONE segment (role hook), no clips; edl_vo.closing null by default, a
# line (<= 12 words) only with the value verdict and its fidelity / context rows; the builder's sealed rows below.
SPOTLIGHT = "spotlight"
SPOTLIGHT_CLOSING_WORDS = 12
SPOTLIGHT_ROWS = ("spotlight_source", "hook_own", "stands_alone", "step_a_two_families", "visual", "window_12h",
                  "never_delivered", "one_per_channel_day", "precheck")
SPOTLIGHT_CLOSING_ROWS = ("closing_value", "closing_fidelity", "closing_context")


def is_spotlight(pin):
    mp = pin.get("moments_package")
    return isinstance(mp, dict) and mp.get("shape") == SPOTLIGHT
MIN_WORDS_IN_RANGE = 3
APPROVED_TEXT_MIN_RATIO = 0.8              # approved_text vs transcript words touching the range
FADE_IN_MS, FADE_OUT_MS = 20, 30           # the factory's M19 fades (cut.py / run_isolated)
_VID = re.compile(r"^[A-Za-z0-9_-]{11}$")


RECENCY_LIMIT_H = 24.0                      # law L-v 3 (amended '22:40'): on the RENDER clock


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
    if is_spotlight(pin):                                       # law L-ab (ruling 90): ONE moment, opening cold
        if len(segs) != 1:
            errs.append(f"a spotlight pin has exactly ONE segment, role hook (got {len(segs)}; ruling 90)")
    elif roles.count("clip") < 1:
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
        if "trimmed_leading" in s or "untrimmed_start" in s:          # ruling 33 part 2 (orchestrator '03:42')
            import canon
            tl, us = s.get("trimmed_leading"), s.get("untrimmed_start")
            tok = canon.canon_tokens(tl) if isinstance(tl, str) else []
            if len(tok) != 1 or tok[0] not in L.TRIMMABLE_LEADING:
                errs.append(f"{tag}: trimmed_leading must be ONE word, one of {sorted(L.TRIMMABLE_LEADING)}")
            if not isinstance(us, (int, float)) or isinstance(us, bool) or not isinstance(st, (int, float)) \
                    or not 0 <= us < st:
                errs.append(f"{tag}: untrimmed_start must be a number with 0 <= untrimmed_start < start")
            if not pin.get("machine_cuts"):
                errs.append(f"{tag}: trimmed_leading needs a machine_cuts pin (the cut is placed in the measured pause)")
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

def _utc_epoch(text):
    """Seconds since the epoch of an ISO 8601 time WITH its offset ('Z' or +hh:mm); None for anything else."""
    from datetime import datetime
    if not isinstance(text, str) or not text.strip():
        return None
    try:
        t = datetime.fromisoformat(text.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return t.timestamp() if t.tzinfo is not None else None


def recency_problems(pin, now=None):
    """Law L-v 3 on the RENDER clock (orchestrator 2026-11-12 '22:40'): a time_sensitive clip (recency words such as
    'right now', a current price level) whose source was published more than RECENCY_LIMIT_H before `now` (this
    render's own clock) holds the run. A machine-built moments pin states, inside its seal, time_sensitive (true /
    false) and source_published_at (ISO 8601 with its offset) on EVERY segment: a missing or malformed field, or a
    publish time in the future, is a problem too (fail closed). Any other pin (human, protected reference) is checked
    only where a segment states time_sensitive true. Returns ([problem], [per-segment record])."""
    now = time.time() if now is None else now
    moments = "moments_package" in pin
    problems, recs = [], []
    for i, s in enumerate(pin.get("segments") or []):
        tag = f"segment {i} ({s.get('role')} {s.get('video_id')})"
        ts, pub = s.get("time_sensitive"), s.get("source_published_at")
        if not moments and ts is not True:
            continue
        if type(ts) is not bool:
            problems.append(f"{tag}: time_sensitive must be true or false (law L-v 3)")
            continue
        t = _utc_epoch(pub)
        if t is None:
            problems.append(f"{tag}: source_published_at {pub!r} is not an ISO 8601 time with its offset (law L-v 3)")
            continue
        age_h = (now - t) / 3600.0
        recs.append({"segment": i, "video_id": s.get("video_id"), "time_sensitive": ts, "source_published_at": pub,
                     "age_h_at_render": round(age_h, 2)})
        if age_h < -0.25:
            problems.append(f"{tag}: source_published_at {pub} is {-age_h:.1f} h in the future of this render")
        elif ts and age_h > RECENCY_LIMIT_H:
            problems.append(f"{tag}: time-sensitive, its source was published {pub}, {age_h:.1f} h before this render "
                            f"(limit {RECENCY_LIMIT_H:.0f} h, law L-v 3)")
    return problems, recs


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
            prov = {"kind": "youtube_window", "window_offset_s": offset}
            if os.path.exists(path + ".post_live.json"):          # ruling 142 (3): cut from the whole stream
                prov = {"kind": "youtube_post_live", "window_offset_s": offset,
                        "post_live_offset_s": post_live_offset(vid, tr, float(offset))}      # HARD: raises PinError
            out[vid] = {"path": path, "offset": float(offset), "transcript": tr, "provenance": prov}
        out[vid]["provenance"]["source_file_sha256"] = _sha256(out[vid]["path"])
        out[vid]["transcript_path"] = os.path.join(run_dir, "transcripts", f"{vid}.json")
        log(f"  {vid}: acquired ({out[vid]['provenance']['kind']})")
    return out


POST_LIVE_MAX_OFFSET_S = 0.35    # ruling 142 (3): the decoders' own bias is about 0.1 s (measured); a trimmed stream
POST_LIVE_MIN_ALIGNED = 10       # shifts by seconds


def post_live_offset(vid, tr, offset):
    """RULING 142 (3): the HARD guard on a source cut from a post_live stream's whole download. The render's decode of the
    window (word times + offset = the source clock), aligned word by word with the word pass's record of that video
    that overlaps it most (data/editorial/transcripts/<id>/windows: the transcript's clock), must sit within
    POST_LIVE_MAX_OFFSET_S (median) on at least POST_LIVE_MIN_ALIGNED words; else PinError (the lock holds). -> the
    median offset in seconds."""
    import glob
    import statistics
    from difflib import SequenceMatcher
    import canon

    def tokens(ws, off):                           # (canonical token, the start of the word it begins in + off)
        ws = [w for w in ws if isinstance(w, dict) and "start" in w]
        return [(tok, float(ws[i]["start"]) + off) for tok, i, _ in canon.canon_spans([str(w.get("word") or "")
                                                                                         for w in ws])]
    try:
        mine = tokens(tr.get("words") or [], offset)
    except (TypeError, ValueError, AttributeError) as e:
        raise PinError(f"{vid}: post_live source: the decode's word times are unreadable ({type(e).__name__}): its "
                       f"clock cannot be checked (ruling 142 (3): HARD)")
    if not mine:
        raise PinError(f"{vid}: post_live source: the decode has no words to check its clock with (ruling 142 (3))")
    lo, hi, best = mine[0][1], mine[-1][1], None
    for p in glob.glob(os.path.join(REPO, "data", "editorial", "transcripts", vid, "windows", "*.json")):
        try:
            a, b = (float(x) for x in os.path.basename(p).split(".whisper")[0].split("-"))
        except ValueError:
            continue
        ov = min(b, hi) - max(a, lo)
        if ov > 0 and (best is None or ov > best[0]):
            best = (ov, p)
    if best is None:
        raise PinError(f"{vid}: post_live source: no transcript word timings overlap the window, so its clock cannot be "
                       f"checked (ruling 142 (3): HARD)")
    try:                                           # batch 111 cycle 1 (qwen F1): unreadable timings are a hold
        with open(best[1]) as f:
            rec = tokens(json.load(f).get("words") or [], 0.0)
    except (OSError, ValueError, TypeError, AttributeError) as e:
        raise PinError(f"{vid}: post_live source: the transcript's word timings are unreadable ({type(e).__name__}): "
                       f"its clock cannot be checked (ruling 142 (3): HARD)")
    sm = SequenceMatcher(None, [m[0] for m in mine], [r[0] for r in rec], autojunk=False)
    deltas = [mine[a + k][1] - rec[b + k][1] for op, a, a2, b, _ in sm.get_opcodes() if op == "equal"
              for k in range(a2 - a)]
    if len(deltas) < POST_LIVE_MIN_ALIGNED:
        raise PinError(f"{vid}: post_live source: only {len(deltas)} words align with the transcript's timings (needs "
                       f"{POST_LIVE_MIN_ALIGNED}): its clock cannot be checked (ruling 142 (3): HARD)")
    med = statistics.median(deltas)
    if abs(med) > POST_LIVE_MAX_OFFSET_S:
        raise PinError(f"{vid}: post_live source shifted {med:+.2f} s against the transcript's word timings (ruling 142 "
                       f"(3): within {POST_LIVE_MAX_OFFSET_S} s or the lock holds)")
    return round(med, 3)


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


# RULING 67's class words (the builder's pipeline/attest.py; moved here from lock_precheck for RULING 84, orchestrator
# 2026-11-13 '20:40', which adjudicate_lock applies too): English closed-class words, NO negation, number or ordinal.
FUNCTION_WORDS = frozenset("""
a an the this that these those that's this's there there's here here's
i you he she it we they me him her us them my your his its our their mine yours hers ours theirs
myself yourself himself herself itself ourselves themselves one's
i'm you're he's she's it's we're they're i've you've we've they've i'll you'll he'll she'll it'll we'll they'll
i'd you'd he'd she'd we'd they'd
in on at to of for from with by about into onto upon over under up down out off through as like than via per
and or but so because if then when while though although whether
is are was were be been being am do does did have has had will would can could shall should may might must
what which who whom whose why how where
""".split())
FILLERS = frozenset({"um", "uh", "er", "ah", "mm", "hmm"})      # ruling 84 (a): exactly the ruling's list, canon tokens


def one_function_word(x, y):
    """RULING 84 (b): x (the render decode's tokens) and y (the other recogniser's, its fillers aside) are ONE function
    word each, and differ: the 'one ambiguous token' of ruling 18."""
    return len(x) == len(y) == 1 and x != y and x[0] in FUNCTION_WORDS and y[0] in FUNCTION_WORDS


def _with_token(text, k, tok):
    """text with the one whole word that carries its canonical token k spelled tok (the word's own punctuation and
    initial capital kept); None when token k is not exactly one whole word of text (fail closed)."""
    import canon
    ws, want = text.split(), canon.canon_tokens(text)
    spans = canon.canon_spans(ws)
    if [t for t, _, _ in spans] != want or not 0 <= k < len(spans) or spans[k][1] != spans[k][2] or \
            sum(1 for _, f, l in spans if (f, l) == spans[k][1:]) != 1:
        return None
    m = re.fullmatch(r"(\W*)(.*?)(\W*)", ws[spans[k][1]])
    core = "I" if tok == "i" else tok[:1].upper() + tok[1:] if m.group(2)[:1].isupper() else tok
    ws[spans[k][1]] = m.group(1) + core + m.group(3)
    new, want[k] = " ".join(ws), tok
    return new if canon.canon_tokens(new) == want else None


def _lv2_critical(tok, texts):
    """Law L-v 2 / ruling 143 (1)'s MATERIAL word: a number, a negation, a name (in either text, a capitalised word
    that does not open a sentence; 'I' excepted) or a ticker (in either text, a word of two or more capitals, wherever
    it stands: 'IBIT'). Conservative: a doubtful token is critical."""
    if re.search(r"\d", tok) or tok in LV2_NEGATIONS or tok.endswith("n't") or tok in LV2_ORDINALS:
        return True                                    # any digit ('2nd', '1,000', '15%') or an ordinal is a number
    for t in texts:
        for m in re.finditer(r"[A-Za-z][A-Za-z'\u2019-]*", t or ""):
            w = m.group(0)
            if w.lower() == tok and w[0].isupper() and w != "I":
                before = t[:m.start()].rstrip()
                if (before and before[-1] not in ".!?") or (len(w) >= 2 and w.isupper()):
                    return True
    return False


AUDIO_SHARE_MIN = 0.85     # ruling 143 (4): two audio readings sharing less than this are the wrong audio (HARD)
AUDIO_APART_MIN = 3        # ... and only when more than this many words apart: a short span's one or two small words
#                            are not the wrong audio (the integrator's proposal; today's records span 27-75 words)


def audio_share(x, y):
    """Ruling 143 (4): the share of the run decode's words (x, canonical tokens) the second reading (y) heard, in
    order: matched / len(x). The second recogniser also writes the speaker's repeats and false starts ('When, when',
    'that's, that's why the bull- that's why') and the neighbouring sentence's words its window catches: none of that
    is the wrong audio, so the second reading's extra words never lower the share; the run's words it did not hear
    (another clip, truncated audio) do. Today's spans: 0.93-1.00; Scott Melker 1b4a63d0's disfluent hook 0.82 on the
    old two-way measure, all of it the speaker's repeats."""
    from difflib import SequenceMatcher
    x, y = list(x or []), list(y or [])
    if not x or not y:
        return 0.0
    return sum(m.size for m in SequenceMatcher(None, x, y, autojunk=False).get_matching_blocks()) / len(x)


def wrong_audio(x, y):
    """Ruling 143 (4) as applied: the second reading heard under AUDIO_SHARE_MIN of the run decode's words AND more
    than AUDIO_APART_MIN of them are missing (from 20 words up this is the 85 % rule itself). -> the share, or None
    (the same audio)."""
    x, y = list(x or []), list(y or [])
    share = audio_share(x, y)
    apart = len(x) - round(share * len(x))
    return share if share < AUDIO_SHARE_MIN and apart > AUDIO_APART_MIN else None


def material_pair(x, y, texts):
    """RULING 143 (1) (orchestrator 2026-11-17 '15:55'): a differing pair is MATERIAL when either side holds a
    number, a negation, a name whose letters differ after the canon, a ticker or a currency amount; a word-form
    pair (ruling 142 (2)) is not. Everything else is NON-MATERIAL: it never holds."""
    import canon
    return not canon.word_form(x, y) and any(_lv2_critical(t, texts) for t in list(x) + list(y))


RELISTEN_PAD_S = 1.5        # ruling 103: the token's word times, 1.5 s either side


def relisten_candidate(diffs, cls, texts):
    """RULING 103 (orchestrator 2026-11-14 '14:13', the targeted re-listen): the lock's ONE token a re-listen may
    decide, or None (the hold stands as it is). Only a hold whose two independent readings differ on exactly ONE
    number or name token: one difference in all, classed hold; the lock's side one token, the reading's at most one;
    a number or a name on either side (law L-v 2's test), never a negation (the ruling names numbers and names)."""
    if len(diffs) != 1 or list(cls) != ["hold"]:
        return None
    mine, theirs = diffs[0][0].split(), diffs[0][1].split()
    if len(mine) != 1 or len(theirs) > 1:
        return None
    if any(t in LV2_NEGATIONS or t.endswith("n't") for t in mine + theirs):
        return None
    if not any(_lv2_critical(t, texts) for t in mine + theirs):
        return None
    return mine[0]


def relisten_verdict(token, decoder_text, second_text):
    """RULING 103: the lock passes on its token only if BOTH short-window readings give it (after the canon: a plan's
    name is not its number). If either does not (still differing, or the two differing from each other), the hold is
    final. -> "pass" | "hold"."""
    import canon
    return "pass" if all(token in canon.canon_tokens(t or "") for t in (decoder_text, second_text)) else "hold"


def truncation_of(token, other):
    """RULING 105: `other` is `token` with only a NON-DIGIT suffix dropped ('401' of '401k'). Never a different number
    ('680' of '68000'), never a name (a token without a digit: 'never a different name'), never an empty reading."""
    return (bool(other) and other != token and token.startswith(other) and any(ch.isdigit() for ch in token)
            and not any(ch.isdigit() for ch in token[len(other):]))


def reading_at(lock_tokens, k, tokens):
    """The reading's canonical token(s) at the lock's token k, aligned by SequenceMatcher: the lock's own token where
    they match, the replacing token(s) joined where they differ, "" where the reading drops it."""
    from difflib import SequenceMatcher
    for tag, a, b, c, d in SequenceMatcher(None, lock_tokens, tokens, autojunk=False).get_opcodes():
        if a <= k < b:
            return lock_tokens[k] if tag == "equal" else " ".join(tokens[c:d])
    return ""


def reading_near(lock_tokens, k, tokens):
    """A SHORT window's reading at the lock's token k (a whole-span alignment can anchor a short window's edge words
    on the wrong part of the lock): the token itself if the reading has it, else the token right after the lock's left
    neighbours in the reading (two words, then one), else right before its right neighbours; "" when nothing anchors
    (fail closed: never a truncation)."""
    if lock_tokens[k] in tokens:
        return lock_tokens[k]
    mid = (len(tokens) - 1) / 2                      # the window is cut around the token: of repeated anchors (audit
    for n in (2, 1):                                 # batch 84 c1, glm), the one nearest the reading's middle
        if k - n >= 0:
            hits = [i + n for i in range(len(tokens) - n) if tokens[i:i + n] == lock_tokens[k - n:k]]
            if hits:
                return tokens[min(hits, key=lambda j: abs(j - mid))]
    for n in (2, 1):
        if k + 1 + n <= len(lock_tokens):
            hits = [i - 1 for i in range(1, len(tokens) - n + 1) if tokens[i:i + n] == lock_tokens[k + 1:k + 1 + n]]
            if hits:
                return tokens[min(hits, key=lambda j: abs(j - mid))]
    return ""


def unstable_second_reading(token, decoder_readings, second_readings):
    """RULING 105 (orchestrator 2026-11-14 '20:13'): the lock's token is adjudicated as the lock's only when (1) every
    decoder reading of it gives it, (2) the second recogniser's readings of the SAME audio differ among themselves with
    at least one giving it, and (3) every differing second reading is a truncation of it (truncation_of). Anything
    else stays a final hold: a stable disagreement, a different number, a different name. Readings are the tokens at
    the lock's place (reading_at). -> {"tests": {...}, "verdict": "pass" | "hold"}."""
    tests = {"decoder_stable": bool(decoder_readings) and all(r == token for r in decoder_readings),
             "second_unstable": token in second_readings and any(r != token for r in second_readings),
             "truncations_only": all(truncation_of(token, r) for r in second_readings if r != token)}
    return {"tests": tests, "verdict": "pass" if all(tests.values()) else "hold"}


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


MAJORITY_EDGE = 3          # ruling 131 (A): a pair the run decode wins sits at least this many tokens from both span ends


def _edge_distance(r, p, op):
    """RULING 131 (A): a differing pair's distance from the nearer end of the span, in the run decode's canonical tokens
    (the cut is placed on the run's words): min(a, len(r) - b). A pair with nothing on one side (an insertion or a
    deletion) inside a repetition ('that's why that's why') has several placements that give the same two texts (they
    cannot say which copy is the extra one): its distance is that of the placement furthest from the ends, sliding the
    pair only through the equal tokens beside it (each step: the token entering the pair equals the token leaving it)."""
    from difflib import SequenceMatcher
    tag, a, b, c, d = op = tuple(op)
    full = SequenceMatcher(None, r, p, autojunk=False).get_opcodes()
    shifts = [0]
    if tag in ("delete", "insert") and op in full:
        k = full.index(op)
        seq, x, y = (r, a, b) if tag == "delete" else (p, c, d)
        left = full[k - 1][2] - full[k - 1][1] if k > 0 and full[k - 1][0] == "equal" else 0
        right = full[k + 1][2] - full[k + 1][1] if k + 1 < len(full) and full[k + 1][0] == "equal" else 0
        n = 1
        while n <= left and seq[x - n] == seq[y - n]:
            shifts.append(-n)
            n += 1
        n = 1
        while n <= right and seq[x + n - 1] == seq[y + n - 1]:
            shifts.append(n)
            n += 1
    return max(min(a + n, len(r) - (b + n)) for n in shifts)


def _majority_text(r, p, ops, pairs, run_t, pin_t):
    """RULING 131 (A): the approved text with every pair that "took": "run" written in the run decode's words (the
    approved words of that pair replaced, deleted or the run's inserted), -> the text, or None when it cannot be written
    so that its canonical tokens are exactly the settled ones (fail closed: the lock then holds)."""
    import canon
    want, k = [], 0
    by_op = {(o[1], o[3]): x for o, x in zip(ops, pairs)}
    from difflib import SequenceMatcher
    for tag, a, b, c, d in SequenceMatcher(None, r, p, autojunk=False).get_opcodes():
        x = by_op.get((a, c)) if tag != "equal" else None
        want += r[a:b] if (x is not None and x["took"] == "run") else p[c:d]
    pw, rw = pin_t.split(), run_t.split()
    ps, rs = canon.canon_spans(pw), canon.canon_spans(rw)
    if [s[0] for s in ps] != p or [s[0] for s in rs] != r:
        return None
    out, w = [], 0                                     # w: the next approved word not yet written
    for o, x in zip(ops, pairs):
        if x["took"] != "run":
            continue
        _, a, b, c, d = o
        lo = ps[c][1] if c < len(ps) else len(pw)      # the approved words of the pair: [lo, hi)
        hi = ps[d - 1][2] + 1 if d > c else lo
        if lo < w or (d > c and (ps[c][1] != lo or any(ps[j][1] < lo or ps[j][2] >= hi for j in range(c, d)))):
            return None
        out += pw[w:lo] + (rw[rs[a][1]:rs[b - 1][2] + 1] if b > a else [])
        w = hi
    text = " ".join(out + pw[w:])
    return text if canon.canon_tokens(text) == want else None


def adjudicate_lock(lock, src_path, words, recognise=None, log=print):
    """Ruling 17: the run's own decode (lock['text']) and the pin's approved text (lock['selected_text']) differ
    inside the locked span -> a difference on a number, a name or a negation always holds (law L-v 2); otherwise
    the independent second recogniser on the acquired window decides: when it reads the approved words at every
    difference, the lock takes the approved text (two independent decodes agree) and G18 compares the final against
    it; when it reads the run's decode, or neither, HOLD naming the three readings. No difference: the lock as is.
    Ruling 84 (b): where it reads ONE function word against the decode's one, the lock keeps the decode's word and
    records the other reading (ruling 18's record); two or more such in one span HOLD.
    RULING 131 (orchestrator 2026-11-17 '08:25'):
    (B) a pair made only of 'dollars' right after a number, on either side, is no difference: a currency symbol is
        formatting ('$2 billion' = a spoken '2 billion'; canon.currency_free, G18's own rule). It is recorded in
        lock["currency_format"] (the release caption says 'currency format'), and nobody is asked about it.
    (A) when the second recogniser does not read the approved words at every remaining pair, two of the three
        readings (approved text, run decode, second recogniser) decide EACH pair: the approved reading where it reads
        the approved words; the run decode's where it reads the run's AND the pair is at least MAJORITY_EDGE tokens
        from both ends of the span. Anything else HOLDS: all three differ, or a run-side pair near an edge (ruling 18's
        one-token record stays for that case alone). A number, a name or a negation still holds before any vote (L-v 2).
        The lock text takes each pair's reading, and the adjudication records every pair's three readings, which two
        agreed and its distance from the nearest edge.
    RULING 143 (orchestrator 2026-11-17 '15:55') SUPERSEDES the L-v 2 hold before the vote, (A)'s edge rule and ruling
    18 / 84 (b)'s one-token records, pair by pair (material_pair):
    (2) a NON-MATERIAL pair never holds: the approved reading where the second recogniser reads it, else the run
        decode's (two of three, or all three differing: the run's, what the render cuts); more than 3 all-differing
        pairs in a clip add ONE soft flag (lock["small_words_unsettled"], read at validate);
    (3) a MATERIAL pair (a number, a negation, a name, a ticker or an amount): the two AUDIO readings (run decode and
        second recogniser) agreeing against the transcript seal the audio's reading (lock["transcript_corrected"], said
        in the note); disagreeing, HOLD;
    (4) HARD: the run decode and the second recogniser sharing under AUDIO_SHARE_MIN of their words (the wrong audio)."""
    import canon
    from difflib import SequenceMatcher
    run_t, pin_t = lock["text"], lock["selected_text"]
    r, p = canon.canon_tokens(run_t), canon.canon_tokens(pin_t)
    ops = [o for o in SequenceMatcher(None, r, p, autojunk=False).get_opcodes() if o[0] != "equal"]
    if not ops:
        return lock
    cur = [o for o in ops if all(canon.dollars_after_number(r, i) for i in range(o[1], o[2]))       # ruling 131 (B)
           and all(canon.dollars_after_number(p, j) for j in range(o[3], o[4]))]
    if cur:
        ops = [o for o in ops if o not in cur]
        lock = {k: v for k, v in lock.items() if k != "sha256"}
        lock["currency_format"] = [[" ".join(r[a:b]), " ".join(p[c:d])] for _, a, b, c, d in cur]
        lock["sha256"] = L._lock_digest(lock)
        log(f"  lock {lock['video_id']} words {lock['i0']}-{lock['i1']}: {lock['currency_format']} differ only by a "
            f"currency symbol: currency format (ruling 131 (B))")
        if not ops:
            return lock
    spell = [o for o in ops if canon.same_words(r[o[1]:o[2]], p[o[3]:o[4]])]       # ruling 135: spelling only
    if spell:
        ops = [o for o in ops if o not in spell]
        lock = {k: v for k, v in lock.items() if k != "sha256"}
        lock["spelling_only"] = [[" ".join(r[a:b]), " ".join(p[c:d])] for _, a, b, c, d in spell]
        lock["sha256"] = L._lock_digest(lock)
        log(f"  lock {lock['video_id']} words {lock['i0']}-{lock['i1']}: {lock['spelling_only']} differ only in "
            f"spelling, segmentation, a spoken reduction or non-lexical sounds: the same words (ruling 135)")
        if not ops:
            return lock
    tag = f"{lock['video_id']} words {lock['i0']}-{lock['i1']}"
    diffs = [[" ".join(r[a:b]), " ".join(p[c:d])] for _, a, b, c, d in ops]
    t0, t1 = words[lock["i0"]]["start"] - 0.3, words[lock["i1"]]["end"] + 0.3
    sw, usd = (recognise or _second_recogniser_words)(src_path)
    sec_t = " ".join(str(w["word"]).strip() for w in sw
                     if t0 <= (float(w["start"]) + float(w["end"])) / 2 <= t1)
    s = [x for x in canon.canon_tokens(sec_t) if not canon.nonlexical(x)]      # ruling 135 (d): fillers are not words
    readings = {"run_decode": run_t, "approved": pin_t, "second_recogniser": sec_t}
    share = audio_share(r, s)
    if wrong_audio(r, s) is not None:                  # ruling 143 (4): the wrong audio, not small words: HARD
        raise PinError(f"{tag}: the run decode and the second recogniser share {share:.0%} of their words (ruling 143 "
                       f"(4): under {AUDIO_SHARE_MIN:.0%} is the wrong audio) | " +
                       " | ".join(f"{k}: {v!r}" for k, v in readings.items()))

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
    pairs, held = [], []
    for _, a, b, c, d in ops:                          # RULING 143 (orchestrator 2026-11-17 '15:55'), pair by pair
        pin_ok, run_ok = reads(p, pmap, c, d), reads(r, rmap, a, b)
        material = material_pair(r[a:b], p[c:d], (run_t, pin_t, sec_t))
        if material:                                   # (3): the two AUDIO readings agree -> the audio's reading (the
            took = "run" if run_ok else None           # transcript was wrong); they disagree -> HOLD
        else:                                          # (2): never holds: two of three, else the run decode's (what
            took = "approved" if pin_ok else "run"     # the render cuts)
        pairs.append({"run": " ".join(r[a:b]), "approved": " ".join(p[c:d]), "material": material,
                      "second_reads": "both" if pin_ok and run_ok else "approved" if pin_ok else "run" if run_ok
                      else "neither", "took": took,
                      "agreed": (["approved", "second"] if took == "approved" else ["run", "second"] if run_ok
                                 else ["run"]) if took else None})
        if took is None:
            held.append(pairs[-1])
    if held:
        raise PinError(f"{tag}: lock text not adjudicated (ruling 143 (3)): at {[[x['run'], x['approved']] for x in held]} "
                       f"a material word (a number, a negation, a name, a ticker or an amount) on which the two audio "
                       f"readings disagree (the run decode against the second recogniser): HOLD | " +
                       " | ".join(f"{k}: {v!r}" for k, v in readings.items()))
    merged = _majority_text(r, p, ops, pairs, run_t, pin_t)
    if merged is None:                                 # (2): the settled small words cannot be written into the
        merged = run_t                                 # approved text: the run decode's text, what the render cuts
        for x in pairs:                                # (every material pair already took the run's reading)
            x["took"] = "run"
    corrected = [[x["approved"], x["run"]] for x in pairs if x["material"]]
    unsettled = sum(1 for x in pairs if not x["material"] and x["second_reads"] == "neither")
    new = {k: v for k, v in lock.items() if k != "sha256"}
    new.update(text=merged, adjudication={"rule": "ruling 143 (orchestrator 2026-11-17 '15:55')", "verdict": "settled",
                                          "pairs": pairs, "differences": diffs, "audio_share": round(share, 3),
                                          "recogniser": "elevenlabs:scribe_v1", "usd": usd, **readings})
    if corrected:                                      # (3): the note says it ('transcript corrected from the audio')
        new["transcript_corrected"] = corrected
    if unsettled:                                      # (2): more than 3 in one clip adds ONE soft flag (validate)
        new["small_words_unsettled"] = unsettled
    new["sha256"] = L._lock_digest(new)
    log(f"  lock {tag}: ruling 143 settles {[[x['run'], x['approved'], x['took']] for x in pairs]}"
        + (f"; transcript corrected from the audio at {corrected}" if corrected else "")
        + (f"; {unsettled} small word(s) all three readings differ on (the run decode's taken)" if unsettled else ""))
    return new


def trimmed_lock(lock, seg, words):
    """Ruling 33 part 2 (orchestrator 2026-11-13 '03:42'): the segment locks a whole sentence with ONE leading word left
    out (seg['trimmed_leading']; seg['untrimmed_start'] is where the untrimmed sentence starts, on the segment's clock).
    The run's own transcript must hold that word right before the lock (text, never time). The lock records it inside
    its digest; sentence_law plans the IN edge at the measured pause after it, and the cut table / G16 hold the clip
    when it cannot be cut cleanly."""
    import canon
    k = lock["i0"] - 1
    heard = words[k]["word"].strip() if k >= 0 else "<file head>"
    if k < 0 or canon.canon_tokens(heard) != canon.canon_tokens(seg["trimmed_leading"]):
        raise PinError(f"{lock['video_id']} words {lock['i0']}-{lock['i1']}: trimmed_leading "
                       f"{seg['trimmed_leading']!r} is not the word before the lock in the run's transcript ({heard!r}) "
                       f"(ruling 33 part 2)")
    new = {k2: v for k2, v in lock.items() if k2 != "sha256"}
    new["trimmed_leading"] = {"rule": "ruling 33 part 2 (orchestrator 2026-11-13 '03:42')", "word": heard,
                              "word_index": k, "untrimmed_start": seg["untrimmed_start"]}
    new["sha256"] = L._lock_digest(new)
    return new


# ── 4. canonical EDL (same shape as select_passages.select_and_build_edl) ──

def segment_lock(s, a, v, recognise=None, log=print):
    """One pin segment's selection lock exactly as the render makes it: make_lock over validate_range's facts v,
    trimmed_lock (ruling 33 part 2), adjudicate_lock (ruling 17). The one code path of build_edl and the pin-stage
    pre-check (ruling 68, pipeline/lock_precheck.py); recognise: adjudicate_lock's second recogniser (None: the real)."""
    lock = L.make_lock(s["video_id"], a["transcript"]["words"], v["i0"], v["i1"],
                       L.sha256_file(a["transcript_path"]), v["text"], [s["start"], s["end"]],
                       v.get("approved_text_similarity"),
                       "pinned approved_text" if s.get("approved_text") else "pinned exact range")
    if "trimmed_leading" in s:
        lock = trimmed_lock(lock, s, a["transcript"]["words"])                       # ruling 33 part 2
    if s.get("approved_text"):
        lock = adjudicate_lock(lock, a["path"], a["transcript"]["words"], recognise=recognise, log=log)  # ruling 17
    return lock


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
        lock = segment_lock(s, a, v, log=log)
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
                   moments_sources_30s_before=list(mp["sources_30s_before"]),
                   moments_bridge=mp.get("bridge"),               # law L-y 2: the one bridge's record, read by R11
                   moments_btc_screen=mp.get("btc_screen"),       # ruling 34: the miner's screen, read by validate
                   moments_gates=mp.get("gates"))                 # ruling 37: the sealed verdicts R1 reads
        if mp.get("shape") == SPOTLIGHT:       # law L-ab: the kind (edl_rules, G5, the editorial gate, the kit) and
            edl.update(package_shape=SPOTLIGHT, first_comment=mp["first_comment"])   # the first comment, verbatim
    overrides = build_vertical_overrides(hook, clips, registry)
    return edl, overrides, report


def _spotlight_vo(mp, v, clips):
    """Law L-ab (the contract agreed with the builder): a spotlight's VO and its sealed rows. No clips; edl_vo states
    intro null, bridges [] and closing: null (the default, ruling 91: the moment goes straight to the sign-off) or ONE
    line of at most SPOTLIGHT_CLOSING_WORDS words, kept only with closing_value / closing_fidelity / closing_context;
    every SPOTLIGHT_ROWS row exactly PASS and not replayed; first_comment a non-empty string. -> the EDL's vo: the
    closing line plays in the intro slot, after the moment (render16 / render_vertical: hook -> intro -> shout-out)."""
    if clips:
        raise PinError("a spotlight has no clips (law L-ab, ruling 90)")
    if any(k not in v for k in ("intro", "bridges", "closing")) or v["intro"] is not None or v["bridges"] != []:
        raise PinError("a spotlight's edl_vo states intro null, bridges [] and closing (law L-ab)")
    closing = v["closing"]
    if closing is not None and (not isinstance(closing, str) or not closing.strip()
                                or len(closing.split()) > SPOTLIGHT_CLOSING_WORDS):
        raise PinError(f"a spotlight's closing line is null or ONE line of at most {SPOTLIGHT_CLOSING_WORDS} words "
                       f"(ruling 91)")
    gates = mp.get("gates")
    need = SPOTLIGHT_ROWS + (SPOTLIGHT_CLOSING_ROWS if closing is not None else ())
    bad = [k for k in need if not (isinstance(gates, dict) and isinstance(gates.get(k), dict)
                                   and gates[k].get("status") == "PASS" and gates[k].get("replayed") is False)]
    if bad:
        raise PinError(f"a spotlight's sealed rows are not exactly PASS and live: {bad} (law L-ab; the closing rows "
                       f"by ruling 91)")
    if not isinstance(mp.get("first_comment"), str) or not mp["first_comment"].strip():
        raise PinError("a spotlight carries the builder's first comment (first_comment, a non-empty string)")
    return {"intro": closing, "bridges": []}


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
    if mp.get("shape") == SPOTLIGHT:
        return _spotlight_vo(mp, v, clips)
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
    return {"intro": intro, "bridges": [{"text": b["text"], "after_clip": b["after_clip"]} for b in bridges]}


def prepare(pin_path, run_dir, log=print):
    """Validate + acquire + build. Writes edl.json, vertical_overrides.json, PINNED_DECISION.json.
    Returns the PINNED_DECISION record. Raises PinError."""
    raw = open(pin_path, "rb").read()
    pin = json.loads(raw)
    with open(CHANNELS_PATH) as f:
        registry = json.load(f)
    validate_schema(pin, registry)
    checked_at = time.time()                                     # law L-v 3: the render's own clock, before any download
    stale, recency = recency_problems(pin, now=checked_at)
    if stale:
        raise PinError("law L-v 3 (render clock): " + "; ".join(stale))
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
           "recency": {"checked_at_epoch": round(checked_at, 1), "limit_h": RECENCY_LIMIT_H, "segments": recency},
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
