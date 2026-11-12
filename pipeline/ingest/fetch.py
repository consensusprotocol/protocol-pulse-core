"""pipeline/ingest/fetch.py: probe one queued video and, once it is a captioned VOD, store its captions.

Captions go into the staging store through transcript_store's own writer (fetch_captions -> _make_record -> _store,
attempts via _log_attempt), so the record format is the pipeline's by construction. meta.json is written once, ONLY
when the video is a VOD with English captions listed (INGEST-FAIL-01: a meta written while live froze 46 videos);
meta_record() has every key transcript_store.ensure_meta writes (tests/ingest/test_fetch.py checks parity) and dates a
livestream VOD by its stream start (INGEST-FAIL-03). No Whisper, no GPU.
"""
import hashlib
import json
import os
from datetime import datetime, timezone

from . import config
from . import queue as Q
from .watch import AGE_GATE_MARKS, BACKFILL_H, ListError

UNAVAILABLE_MARKS = ("Private video", "Video unavailable", "This video has been removed", "members-only",
                     "Join this channel", "This video is no longer available",
                     "account associated with this video has been terminated")
UNAVAILABLE_RETRY_S = 6 * 3600
UNAVAILABLE_MAX_TRIES = 4
PROBE_RETRY_S = (300, 900, 1800, 3600)


def _dt(epoch):
    return datetime.fromtimestamp(float(epoch), timezone.utc) if isinstance(epoch, (int, float)) else None


def publish_time(j, rss_published=None):
    """(aware ISO, source): a livestream VOD is dated by its stream start (release_timestamp); an upload by RSS when
    listed there, else yt-dlp's timestamp. None when nothing is measured."""
    if j.get("live_status") in ("was_live", "post_live", "is_live") and _dt(j.get("release_timestamp")):
        return _dt(j["release_timestamp"]).isoformat(), "yt-dlp release_timestamp (stream start)"
    if rss_published:
        return rss_published, "youtube_rss"
    if _dt(j.get("timestamp")):
        return _dt(j["timestamp"]).isoformat(), "yt-dlp timestamp"
    if _dt(j.get("release_timestamp")):
        return _dt(j["release_timestamp"]).isoformat(), "yt-dlp release_timestamp"
    return None, None


def captions_listed(j):
    manual = sorted((j.get("subtitles") or {}).keys())
    auto = sorted(k for k in (j.get("automatic_captions") or {}) if k in ("en", "en-orig"))
    return manual, auto


def meta_record(j, chan, published_at, published_source, rss_title=None):
    """transcript_store.ensure_meta's record (same keys, same derivations) plus release_timestamp, timestamp,
    media_type and the writer's name."""
    ts = config.ts()
    manual, auto = captions_listed(j)
    vid = j["id"]
    return {
        "schema": ts.SCHEMA, "video_id": vid, "canonical_url": ts.canonical_url(vid),
        "channel_id": j.get("channel_id") or chan.get("channel_id"),
        "channel_name": chan.get("display_name") or j.get("channel"),
        "channel_name_youtube": j.get("channel"),
        "exact_title": rss_title or j.get("title"), "title_youtube": j.get("title"),
        "published_at": published_at, "published_at_source": published_source,
        "duration": j.get("duration"), "live_status": j.get("live_status"),
        "description": (j.get("description") or "")[:4000],
        "captions_manual": manual, "captions_auto_en": auto,
        "metadata_fetched_at": ts.now_iso(), "metadata_tool": "yt-dlp -J",
        "release_timestamp": j.get("release_timestamp"), "timestamp": j.get("timestamp"),
        "media_type": j.get("media_type"), "written_by": "pipeline.ingest.fetch",
    }


def title_canon(title):
    import canon
    return " ".join(canon.canon_tokens(title or ""))


def text_fingerprint(rec):
    """sha256 of the WHOLE record read as spoken (canonical tokens): a re-upload of the same speech. Not a prefix
    (audit cycle 2 consensus, three reviewers): a prefix would call every video of a channel with a long standard intro
    or sponsor read a re-upload of its first one and never mine it."""
    import canon
    ts = config.ts()
    toks = canon.canon_tokens(ts.read_text(" ".join(s["text"] for s in rec["segments"])))
    if len(toks) < 50:
        return None                          # too little text to call two videos the same
    return hashlib.sha256(" ".join(toks).encode()).hexdigest()[:32]


def probe(gate, video_id):
    """(json, None) or (None, (kind, detail)). kind: age_gated | unavailable | rate_limited | error."""
    try:
        r = gate.run(["-J", "--skip-download", "--ignore-no-formats-error",
                      f"https://www.youtube.com/watch?v={video_id}"], timeout=120)
    except ListError as e:
        return None, (e.kind, e.detail)
    try:
        j = json.loads(r.stdout)
        if isinstance(j, dict) and j.get("id") == video_id:
            return j, None
    except ValueError:
        pass
    err = (r.stderr or "")[-400:]
    if any(m in err for m in AGE_GATE_MARKS):
        return None, ("age_gated", err)
    if any(m in err for m in UNAVAILABLE_MARKS):
        return None, ("unavailable", err)
    return None, ("error", err or f"yt-dlp rc {r.returncode}")


def _retry_at(now_ts, tries):
    return now_ts + PROBE_RETRY_S[min(tries, len(PROBE_RETRY_S) - 1)]


def _caption_retry_at(now_ts, published_ts, tries):
    if tries < len(config.CAPTION_RETRY_S):
        return now_ts + config.CAPTION_RETRY_S[tries]
    return now_ts + 7200


def process(q, gate, v, chan, optout, now_ts=None):
    """Advance one due video by one step. Returns the new state."""
    now_ts = now_ts or q.clock()
    vid, tries = v["video_id"], int(v.get("tries") or 0)
    if chan is None:
        q.set_state(vid, Q.OPTOUT, next_at=now_ts + 10 ** 9, reason="channel no longer watched (registry)")
        return Q.OPTOUT
    if chan["channel_id"] in optout:
        q.set_state(vid, Q.OPTOUT, next_at=now_ts + 10 ** 9, reason="channel in pipeline/optout.json")
        return Q.OPTOUT
    j, err = probe(gate, vid)
    if err:
        kind, detail = err
        if kind == "age_gated":                    # terminal: this store signs in nowhere (integrator B4)
            q.set_state(vid, Q.UNAVAILABLE, next_at=now_ts + 10 ** 9, tries=tries + 1,
                        reason=f"age-gated (needs a signed-in session): {detail[-200:]}")
            return Q.UNAVAILABLE
        if kind == "unavailable":
            final = tries + 1 >= UNAVAILABLE_MAX_TRIES
            q.set_state(vid, Q.UNAVAILABLE, next_at=now_ts + (10 ** 9 if final else UNAVAILABLE_RETRY_S),
                        tries=tries + 1, reason=f"yt-dlp: {detail[-200:]}")
            return Q.UNAVAILABLE
        q.set_state(vid, Q.PROBE_RETRY, next_at=now_ts + (gate.open_for() or 0) + PROBE_RETRY_S[0]
                    if kind == "rate_limited" else _retry_at(now_ts, tries), tries=tries + 1,
                    reason=f"{kind}: {detail[-200:]}")
        return Q.PROBE_RETRY
    if j.get("channel_id") and j["channel_id"] != chan["channel_id"]:
        q.set_state(vid, Q.UNAVAILABLE, next_at=now_ts + 10 ** 9,
                    reason=f"channel mismatch: video belongs to {j.get('channel_id')}")
        return Q.UNAVAILABLE
    rss_pub = _dt(v.get("listing_ts")).isoformat() if v.get("discovered_via") == "rss" and _dt(v.get("listing_ts")) \
        else None
    pub, pub_src = publish_time(j, rss_published=rss_pub)
    pub_ts = datetime.fromisoformat(pub).timestamp() if pub else None
    live, media = j.get("live_status"), j.get("media_type")
    common = dict(published_at=pub, published_ts=pub_ts, published_source=pub_src, media_type=media,
                  live_status=live, duration=j.get("duration"), title=v.get("title") or j.get("title"))
    if media == "short":
        q.set_state(vid, Q.SHORT, next_at=now_ts + 10 ** 9, reason="a Short: never mined (L-u)", **common)
        return Q.SHORT
    if live == "is_upcoming":
        start = j.get("release_timestamp")
        nxt = max(float(start) + 900, now_ts + 600) if isinstance(start, (int, float)) else now_ts + config.UPCOMING_REPROBE_S
        q.set_state(vid, Q.UPCOMING, next_at=nxt, tries=tries + 1, reason=f"upcoming (scheduled {pub})", **common)
        return Q.UPCOMING
    if live in ("is_live", "post_live"):
        q.set_state(vid, Q.LIVE, next_at=now_ts + config.LIVE_REPROBE_S, tries=tries + 1,
                    reason=f"{live}: re-probed every {config.LIVE_REPROBE_S // 60} min (meta.json not written)", **common)
        return Q.LIVE
    if pub_ts is None:
        q.set_state(vid, Q.PROBE_RETRY, next_at=_retry_at(now_ts, tries), tries=tries + 1,
                    reason="no publish time measured", **common)
        return Q.PROBE_RETRY
    if now_ts - pub_ts > BACKFILL_H * 3600:
        q.set_state(vid, Q.SEEN_OLD, next_at=now_ts + 10 ** 9,
                    reason=f"published {pub}: older than the {BACKFILL_H} h window", **common)
        return Q.SEEN_OLD
    dur = j.get("duration")
    if not isinstance(dur, (int, float)) or dur <= 0:
        q.set_state(vid, Q.PROBE_RETRY, next_at=_retry_at(now_ts, tries), tries=tries + 1,
                    reason="no duration measured", **common)
        return Q.PROBE_RETRY
    if dur > config.VOD_MAX_S:
        q.set_state(vid, Q.TOO_LONG, next_at=now_ts + 10 ** 9,
                    reason=f"duration {dur:.0f} s > {config.VOD_MAX_S} s", **common)
        return Q.TOO_LONG
    tc = title_canon(j.get("title"))
    dup, why = q.find_duplicate(vid, title_canon=tc, duration=dur)
    if dup:
        q.set_state(vid, Q.DUPLICATE, next_at=now_ts + 10 ** 9, duplicate_of=dup, title_canon=tc,
                    reason=f"re-upload of {dup}: {why}", **common)
        return Q.DUPLICATE
    manual, auto = captions_listed(j)
    if not (any(k.startswith("en") for k in manual) or auto):
        if now_ts - pub_ts > config.CAPTION_DEADLINE_H * 3600:
            q.set_state(vid, Q.NO_CAPTIONS, next_at=now_ts + 10 ** 9, title_canon=tc,
                        reason=f"no English captions {config.CAPTION_DEADLINE_H} h after publish (needs the pipeline's "
                               "Whisper)", **common)
            return Q.NO_CAPTIONS
        q.set_state(vid, Q.CAPTIONS_PENDING, next_at=_caption_retry_at(now_ts, pub_ts, tries), tries=tries + 1,
                    title_canon=tc, reason="VOD without English captions yet", **common)
        return Q.CAPTIONS_PENDING
    return _store_captions(q, gate, v, chan, j, common, tc, now_ts, tries)


def _store_captions(q, gate, v, chan, j, common, tc, now_ts, tries):
    ts = config.ts()
    vid = v["video_id"]
    paths = config.paths()
    vdir = ts._vdir(vid)
    os.makedirs(vdir, exist_ok=True)
    mpath = os.path.join(vdir, "meta.json")
    if os.path.exists(mpath):
        with open(mpath) as f:
            meta = json.load(f)
    else:
        meta = meta_record(j, chan, common["published_at"], common["published_source"],
                           rss_title=v.get("title") if v.get("discovered_via") == "rss" else None)
    existing = ts.canonical_transcript(vid)
    if existing is None:
        with gate.sem:
            status, rec = ts.fetch_captions(meta, os.path.join(paths["work"], "captions_tmp"))
        ts._log_attempt(vid, step="captions", status=status, writer="pipeline.ingest")
        if status != "ok":
            nxt = now_ts + 1800 if status == "throttled" else _caption_retry_at(now_ts, common["published_ts"], tries)
            q.set_state(vid, Q.CAPTIONS_PENDING, next_at=nxt, tries=tries + 1, title_canon=tc,
                        reason=f"captions {status}", **common)
            return Q.CAPTIONS_PENDING
        if not os.path.exists(mpath):
            ts._write_once(mpath, meta)
        ts._store(rec)
        existing = ts.canonical_transcript(vid)
    elif not os.path.exists(mpath):
        ts._write_once(mpath, meta)
    fp = text_fingerprint(existing)
    dup, why = q.find_duplicate(vid, text_fp=fp)
    if dup:
        q.set_state(vid, Q.DUPLICATE, next_at=now_ts + 10 ** 9, duplicate_of=dup, title_canon=tc, text_fp=fp,
                    transcript_sha256=existing["transcript_sha256"], transcript_method=existing["transcript_method"],
                    reason=f"re-upload of {dup}: {why}", **common)
        return Q.DUPLICATE
    q.set_state(vid, Q.TRANSCRIBED, next_at=now_ts, title_canon=tc, text_fp=fp,
                transcript_sha256=existing["transcript_sha256"], transcript_method=existing["transcript_method"],
                transcribed_at=config.iso(), transcribed_ts=now_ts, reason=None, **common)
    return Q.TRANSCRIBED
