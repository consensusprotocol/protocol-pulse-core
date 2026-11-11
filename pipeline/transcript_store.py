#!/usr/bin/env python3
"""pipeline/transcript_store.py — canonical transcript cache (editorial layer).

LAW: titles/metadata are discovery hints; transcripts establish story identity.
Every transcript and every derived chunk carries immutable attribution to its source.

Layout (data/editorial/transcripts/<video_id>/):
  meta.json                         video metadata (RSS + yt-dlp), written once, refreshed only
                                    by appending to meta_history
  transcript.<method>.json          IMMUTABLE transcript record, one per acquisition method
                                    (never overwritten; a better method adds a new file)
  attempts.jsonl                    acquisition attempt log (caption 429s, failures, skips)

Acquisition policy (acquire()):
  1. existing valid cached transcript  -> reuse (never re-transcribe)
  2. native captions (manual > auto 'en-orig' > auto 'en') with backoff
  3. captions unavailable / HTTP 429 / error -> local faster-whisper on GPU0
     (a caption 429 is a PATH SWITCH, never "no transcript"); a 429 opens a caption
     circuit breaker so later videos go straight to Whisper instead of hammering YouTube
  4. cache permanently

Chunks: deterministic windows over the canonical transcript, id '<video_id>:<start_ms>-<end_ms>',
each chunk inheriting the full source identity + transcript_sha256.
"""
import glob
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone

PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(PIPELINE_DIR)
STORE_DIR = os.environ.get("PP_EDITORIAL_STORE", os.path.join(REPO, "data", "editorial"))
TRANSCRIPTS_DIR = os.path.join(STORE_DIR, "transcripts")
MEDIA_DIR = os.path.join(STORE_DIR, "media_tmp")
STATE_DIR = os.path.join(STORE_DIR, "state")
COOKIES = os.path.join(REPO, "data", "yt_cookies.txt")

SCHEMA = 1
WHISPER_MODEL = "distil-large-v3"           # editorial understanding (49x realtime batched)
WHISPER_BATCH = 16
MAX_DURATION_S = 3 * 3600                   # same VOD ceiling as scan.py
CAPTION_BACKOFF_S = (0, 8, 20)
CIRCUIT_MINUTES = 30
CHUNK_MIN_S, CHUNK_MAX_S = 30.0, 60.0

METHOD_RANK = {"whisper_words": 4, "whisper": 3, "yt_manual": 2, "yt_auto": 1}
PROVENANCE_FIELDS = ("video_id", "canonical_url", "channel_id", "channel_name", "exact_title",
                     "published_at", "duration", "transcript_method", "transcript_model",
                     "transcript_sha256")


class AcquisitionError(Exception):
    pass


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def canonical_url(video_id):
    return f"https://www.youtube.com/watch?v={video_id}"


def _vdir(video_id):
    if not re.fullmatch(r"[A-Za-z0-9_-]{6,20}", video_id or ""):
        raise ValueError(f"invalid video_id {video_id!r}")
    return os.path.join(TRANSCRIPTS_DIR, video_id)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def segments_sha256(segments):
    canon = json.dumps([[round(s["start"], 3), round(s["end"], 3), s["text"]] for s in segments],
                       ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def _write_once(path, obj):
    if os.path.exists(path):
        raise FileExistsError(f"immutable record exists: {path}")
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f, indent=1, ensure_ascii=False)
    os.link(tmp, path)          # fails if path appeared meanwhile
    os.unlink(tmp)


def _log_attempt(video_id, **kw):
    os.makedirs(_vdir(video_id), exist_ok=True)
    with open(os.path.join(_vdir(video_id), "attempts.jsonl"), "a") as f:
        f.write(json.dumps({"at": now_iso(), **kw}) + "\n")


# ── metadata ──

def _ytdlp(args, timeout=120):
    cmd = ["yt-dlp", "--no-warnings"]
    if os.path.exists(COOKIES):
        cmd += ["--cookies", COOKIES]
    return subprocess.run(cmd + args, capture_output=True, text=True, timeout=timeout)


def ensure_meta(video_id, rss=None, channel=None):
    """Video identity. rss = {'title','published'} from the channel feed (exact title and
    publish timestamp); channel = registry entry. Returns meta dict."""
    path = os.path.join(_vdir(video_id), "meta.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    r = _ytdlp(["-J", "--skip-download", canonical_url(video_id)])
    try:
        j = json.loads(r.stdout)
    except Exception:
        j = None
    if not isinstance(j, dict):
        _log_attempt(video_id, step="meta", status="unavailable", error=(r.stderr or "")[-300:])
        raise AcquisitionError(f"metadata unavailable for {video_id}: {(r.stderr or '')[-300:]}")
    meta = {
        "schema": SCHEMA, "video_id": video_id, "canonical_url": canonical_url(video_id),
        "channel_id": j.get("channel_id") or (channel or {}).get("channel_id"),
        "channel_name": (channel or {}).get("display_name") or j.get("channel"),
        "channel_name_youtube": j.get("channel"),
        "exact_title": (rss or {}).get("title") or j.get("title"),
        "title_youtube": j.get("title"),
        "published_at": (rss or {}).get("published") or (
            datetime.fromtimestamp(j["timestamp"], timezone.utc).isoformat() if j.get("timestamp") else None),
        "published_at_source": "youtube_rss" if (rss or {}).get("published") else "yt-dlp timestamp",
        "duration": j.get("duration"), "live_status": j.get("live_status"),
        "description": (j.get("description") or "")[:4000],
        "captions_manual": sorted((j.get("subtitles") or {}).keys()),
        "captions_auto_en": sorted(k for k in (j.get("automatic_captions") or {}) if k in ("en", "en-orig")),
        "metadata_fetched_at": now_iso(), "metadata_tool": "yt-dlp -J",
    }
    os.makedirs(_vdir(video_id), exist_ok=True)
    _write_once(path, meta)
    return meta


# ── transcript records ──

def transcript_records(video_id):
    out = []
    for p in sorted(glob.glob(os.path.join(_vdir(video_id), "transcript.*.json"))):
        with open(p) as f:
            rec = json.load(f)
        if segments_sha256(rec["segments"]) != rec["transcript_sha256"]:
            raise AcquisitionError(f"transcript hash mismatch: {p}")
        rec["_file_sha256"] = sha256_file(p)
        rec["_path"] = p
        out.append(rec)
    return out


def canonical_transcript(video_id):
    """Best available record (whisper > manual captions > auto captions) or None."""
    if not os.path.isdir(_vdir(video_id)):
        return None
    recs = transcript_records(video_id)
    if not recs:
        return None
    return max(recs, key=lambda r: METHOD_RANK.get(r["transcript_method"].split(":")[0], 0))


def _make_record(meta, method, model, segments, language="en", media_sha256=None, extra=None):
    segs = [{"start": round(float(s["start"]), 3), "end": round(float(s["end"]), 3),
             "text": s["text"].strip()} for s in segments if s["text"].strip()]
    if not segs:
        raise AcquisitionError("empty transcript")
    if not (meta.get("channel_id") and meta.get("channel_name")):  # every record carries its source identity
        raise AcquisitionError(f"no channel identity for {meta.get('video_id')}: pass the video's meta.json")
    rec = {"schema": SCHEMA}
    for k in ("video_id", "canonical_url", "channel_id", "channel_name", "exact_title",
              "published_at", "duration"):
        rec[k] = meta.get(k)
    rec.update(transcript_method=method, transcript_model=model, language=language,
               acquired_at=now_iso(), media_sha256=media_sha256, segments=segs,
               transcript_sha256=segments_sha256(segs), **(extra or {}))
    return rec


def _store(rec):
    slug = rec["transcript_method"].split(":")[0]
    path = os.path.join(_vdir(rec["video_id"]), f"transcript.{slug}.json")
    _write_once(path, rec)
    return path


# ── captions ──

def _circuit_path():
    return os.path.join(STATE_DIR, "caption_circuit.json")


def caption_circuit_open():
    try:
        with open(_circuit_path()) as f:
            return time.time() < json.load(f).get("open_until", 0)
    except Exception:
        return False


def _open_circuit(reason):
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(_circuit_path(), "w") as f:
        json.dump({"open_until": time.time() + CIRCUIT_MINUTES * 60, "reason": reason,
                   "opened_at": now_iso()}, f)


def parse_vtt(path):
    """VTT -> segments. Removes inline timing tags and YouTube's rolling duplicate lines."""
    segs, last = [], None
    with open(path, encoding="utf-8", errors="ignore") as f:
        blocks = re.split(r"\n\s*\n", f.read())
    for b in blocks:
        lines = b.strip().split("\n")
        for i, ln in enumerate(lines):
            m = re.match(r"(\d+:\d{2}:\d{2}\.\d{3})\s*-->\s*(\d+:\d{2}:\d{2}\.\d{3})", ln)
            if not m:
                continue
            def sec(t):
                h, mm, s = t.split(":")
                return int(h) * 3600 + int(mm) * 60 + float(s)
            new = []
            for t in lines[i + 1:]:
                t = re.sub(r"<[^>]+>", "", t).strip()
                if t and t != last and t not in new:
                    new.append(t)
            for t in new:
                segs.append({"start": sec(m.group(1)), "end": sec(m.group(2)), "text": t})
                last = t
            break
    return segs


def fetch_captions(meta, work_dir):
    """Returns (status, record_or_None). status: ok | unavailable | throttled | error."""
    vid = meta["video_id"]
    if meta.get("captions_manual") and any(k.startswith("en") for k in meta["captions_manual"]):
        lang = next(k for k in meta["captions_manual"] if k.startswith("en"))
        flag, method = "--write-subs", "yt_manual"
    elif meta.get("captions_auto_en"):
        lang = "en-orig" if "en-orig" in meta["captions_auto_en"] else "en"
        flag, method = "--write-auto-subs", "yt_auto"
    else:
        return "unavailable", None
    if caption_circuit_open():
        return "throttled", None
    os.makedirs(work_dir, exist_ok=True)
    out = os.path.join(work_dir, vid)
    err = ""
    for wait in CAPTION_BACKOFF_S:
        time.sleep(wait)
        for f in glob.glob(out + ".*.vtt"):
            os.unlink(f)
        r = _ytdlp(["--skip-download", flag, "--sub-langs", lang, "--sub-format", "vtt",
                    "-o", out, canonical_url(vid)])
        files = glob.glob(out + ".*.vtt")
        if files:
            segs = parse_vtt(files[0])
            rec = _make_record(meta, f"{method}:{lang}", f"youtube captions ({flag[8:]}, {lang})",
                               segs, extra={"caption_file_sha256": sha256_file(files[0])})
            return "ok", rec
        err = (r.stderr or "")[-400:]
        if "429" not in err:
            return "error", None
    _open_circuit(f"HTTP 429 on {vid}: {err[-120:]}")
    return "throttled", None


# ── whisper ──

_WHISPER = None
LAST_ERROR = {}          # video_id -> last acquisition error string (infra vs editorial triage)


def release_whisper():
    """Drop the Whisper model and free its GPU memory (E5). Returns GPU0 used MiB after."""
    global _WHISPER
    _WHISPER = None
    import gc
    gc.collect()
    try:
        out = subprocess.run(["nvidia-smi", "-i", "0", "--query-gpu=memory.used",
                              "--format=csv,noheader,nounits"], capture_output=True, text=True).stdout
        return int(out.strip())
    except Exception:
        return None


def _whisper():
    global _WHISPER
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "0":
        raise AcquisitionError("Whisper requires CUDA_VISIBLE_DEVICES=0 (GPU1 quarantined)")
    if _WHISPER is None:
        from faster_whisper import WhisperModel, BatchedInferencePipeline
        _WHISPER = BatchedInferencePipeline(
            model=WhisperModel(WHISPER_MODEL, device="cuda", compute_type="float16"))
    return _WHISPER


def whisper_model_id():
    import faster_whisper
    return (f"faster-whisper {faster_whisper.__version__} {WHISPER_MODEL} float16 "
            f"batched{WHISPER_BATCH} lang=en")


def download_audio(video_id):
    os.makedirs(MEDIA_DIR, exist_ok=True)
    out = os.path.join(MEDIA_DIR, f"{video_id}.%(ext)s")
    r = _ytdlp(["-f", "bestaudio[ext=m4a]/bestaudio", "-o", out, canonical_url(video_id)],
               timeout=900)
    files = [f for f in glob.glob(os.path.join(MEDIA_DIR, f"{video_id}.*")) if not f.endswith(".part")]
    if not files:
        raise AcquisitionError(f"audio download failed: {(r.stderr or '')[-300:]}")
    return files[0]


def sentences_from_words(words):
    """Sentence segments from word timestamps (split after . ! ?)."""
    segs, cur = [], []
    for w in words:
        cur.append(w)
        if w["word"].rstrip().endswith((".", "!", "?")):
            segs.append({"start": cur[0]["start"], "end": cur[-1]["end"],
                         "text": " ".join(x["word"].strip() for x in cur)})
            cur = []
    if cur:
        segs.append({"start": cur[0]["start"], "end": cur[-1]["end"],
                     "text": " ".join(x["word"].strip() for x in cur)})
    return segs


def whisper_transcribe(meta, transcribe_fn=None, words=False):
    """words=False: VAD-batched segments (editorial understanding).
    words=True : word timestamps -> sentence segments (clip-quality passages), method whisper_words."""
    audio = download_audio(meta["video_id"])
    try:
        media_sha = sha256_file(audio)
        extra = {"media_file": os.path.basename(audio), "media_bytes": os.path.getsize(audio)}
        if transcribe_fn is not None:
            segs, model = transcribe_fn(audio)
        elif words:
            it, _ = _whisper().transcribe(audio, language="en", batch_size=WHISPER_BATCH,
                                          word_timestamps=True)
            ws = [{"word": w.word.strip(), "start": round(w.start, 3), "end": round(w.end, 3)}
                  for s in it for w in (s.words or [])]
            segs = sentences_from_words(ws)
            model = whisper_model_id() + " word_timestamps"
            extra["words"] = ws
        else:
            it, _ = _whisper().transcribe(audio, language="en", batch_size=WHISPER_BATCH)
            segs = [{"start": s.start, "end": s.end, "text": s.text} for s in it]
            model = whisper_model_id()
        return _make_record(meta, "whisper_words" if words else "whisper", model, segs,
                            media_sha256=media_sha, extra=extra)
    finally:
        try:
            os.unlink(audio)
        except OSError:
            pass


# ── policy ──

def acquire(video_id, rss=None, channel=None, allow_whisper=True, prefer_words=False,
            transcribe_fn=None, caption_fn=None, try_captions=True):
    """Acquisition policy. Returns (record_or_None, status). Never re-transcribes.
    try_captions=False skips the caption step (used for the Whisper pass after a caption pass
    already failed, so YouTube is not asked twice). prefer_words=True guarantees a
    word-timestamped Whisper record (clip-quality stage), created at most once per video."""
    LAST_ERROR.pop(video_id, None)
    rec = canonical_transcript(video_id)
    if rec and (not prefer_words or rec["transcript_method"] == "whisper_words"):
        return rec, "cached"
    prefer_whisper = prefer_words
    meta = ensure_meta(video_id, rss=rss, channel=channel)
    if meta.get("duration") and meta["duration"] > MAX_DURATION_S:
        _log_attempt(video_id, step="skip", reason=f"duration {meta['duration']}s > {MAX_DURATION_S}s")
        return rec, "skipped_too_long"
    if meta.get("live_status") in ("is_live", "is_upcoming"):
        _log_attempt(video_id, step="skip", reason=f"live_status {meta['live_status']}")
        return rec, "skipped_live"
    if not rec and not prefer_whisper and try_captions:
        status, crec = (caption_fn or fetch_captions)(meta, os.path.join(STATE_DIR, "captions_tmp"))
        _log_attempt(video_id, step="captions", status=status)
        if status == "ok":
            _store(crec)
            return canonical_transcript(video_id), "captions"
        # unavailable / throttled / error -> path switch to Whisper
    if not allow_whisper:
        return rec, "pending_whisper"
    try:
        wrec = whisper_transcribe(meta, transcribe_fn=transcribe_fn, words=prefer_words)
    except Exception as e:
        LAST_ERROR[video_id] = f"{type(e).__name__}: {e}"[-400:]
        _log_attempt(video_id, step="whisper", status="error", error=str(e)[-300:])
        if "out of memory" in str(e).lower():
            release_whisper()          # never keep a half-initialised model around
        return rec, "whisper_failed"
    _store(wrec)
    _log_attempt(video_id, step="whisper", status="ok", model=wrec["transcript_model"])
    return canonical_transcript(video_id), "whisper"


# ── chunks ──

def chunk_id(video_id, start, end):
    return f"{video_id}:{int(round(start * 1000))}-{int(round(end * 1000))}"


def chunks(rec):
    """Deterministic ~30-60 s chunks; every chunk carries the full source identity. A record written without
    its channel identity (four hand-made whisper_words records of 2026-11-10 crashed 4b run 1's clustering
    on a None channel) takes the missing fields from the video's meta.json, its identity record (never overriding
    a field the record has); without BOTH channel fields after that, or with an unreadable meta.json, the record
    yields no chunks (fail closed: unidentified text is no channel's evidence)."""
    if not rec.get("video_id"):
        return []                                   # no video identity at all: fail closed
    prov = {k: rec.get(k) for k in PROVENANCE_FIELDS}
    if any(v is None for v in prov.values()):       # fill only what the record lacks, never override it
        try:
            with open(os.path.join(_vdir(rec["video_id"]), "meta.json")) as f:
                m = json.load(f)
        except (OSError, ValueError):               # absent / unreadable / corrupt: nothing to fill from
            m = {}
        if isinstance(m, dict):
            prov.update({k: m[k] for k in PROVENANCE_FIELDS if prov.get(k) is None and m.get(k) is not None})
    if not (prov.get("channel_id") and prov.get("channel_name")):
        return []                                   # fail closed: every chunk carries BOTH channel fields
    out, cur = [], []
    def flush():
        if cur:
            s, e = cur[0]["start"], cur[-1]["end"]
            out.append({**prov, "chunk_id": chunk_id(rec["video_id"], s, e), "start": s, "end": e,
                        "text": " ".join(x["text"] for x in cur)})
    for seg in rec["segments"]:
        if cur and seg["end"] - cur[0]["start"] > CHUNK_MAX_S:
            flush()
            cur = []
        cur.append(seg)
        if cur[-1]["end"] - cur[0]["start"] >= CHUNK_MIN_S:
            flush()
            cur = []
    flush()
    return out


def parse_chunk_id(cid):
    m = re.fullmatch(r"([A-Za-z0-9_-]+):(\d+)-(\d+)", cid)
    if not m:
        raise ValueError(cid)
    return m.group(1), int(m.group(2)) / 1000, int(m.group(3)) / 1000
