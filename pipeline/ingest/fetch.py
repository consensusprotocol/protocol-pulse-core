"""pipeline/ingest/fetch.py: probe one queued video and, once it is a captioned VOD, store its captions.

Captions go into the staging store through transcript_store's own writer (fetch_captions -> _make_record -> _store,
attempts via _log_attempt), so the record format is the pipeline's by construction. meta.json is written once, ONLY
when the video is a VOD with English captions listed or with the pipeline's own transcript (INGEST-FAIL-01: a meta
written while live froze 46 videos); meta_record() has every key transcript_store.ensure_meta writes
(tests/ingest/test_fetch.py checks parity) and dates a livestream VOD by its stream start (INGEST-FAIL-03). No Whisper,
no GPU.

THE PIPELINE'S OWN TRANSCRIPT (the orchestrator's 10:50 ET order of Nov 16, (1)): from 07:47 ET that day YouTube
answered HTTP 429 to every caption download from this machine, so no video reached the miner for three hours, while
the main tree's own transcript ingest (cron, every 30 min: captions, else Whisper on its GPU) had already transcribed
most of them. Before any caption download, and when a VOD lists no English captions, the video's record in the
pipeline's store (config.MAIN_STORE, READ ONLY) is taken when one passes every check (it names this video and this
channel; its segments hash to its transcript_sha256): copied byte for byte into this store, write-once, the copy
checked again. A caption 429 stops the captions only (transcript_store's own 30-minute caption breaker): the probe and
the listing, which YouTube still answered, go on, and a throttled video is tried again in CAPTION_THROTTLED_RETRY_S,
the pipeline's store looked at first each time.
"""
import glob
import hashlib
import json
import os
import shutil
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
FACT_KEYS = ("live_status", "duration", "timestamp", "release_timestamp", "upload_date")   # r121: what a real probe gives
NO_METADATA_RETRY_S = 900           # r121/r122: a probe answered with no fact at all (removed, private, not public
                                    # yet, or a moment's stub: CoinDesk yHuY9r30Oug, Nov 17) is tried every 15 min
                                    # inside its moments' life, then given up; never counted as waiting
CAPTION_THROTTLED_RETRY_S = 600     # a caption 429: tried again this soon (the pipeline's store is looked at first)
PIPELINE_RECHECK_S = 1800           # a VOD without English captions inside its moments' life: looked at this often
                                    # (the pipeline's transcript ingest runs every 30 min)
PIPELINE_SWEEP_S = 60               # the 13:05 ruling (Nov 16): each waiting video's record in the pipeline's store is
                                    # looked for this often, whatever its next try (pipeline_sweep)
PIPELINE_STORE = os.path.join(config.MAIN_STORE, "transcripts")     # the pipeline's own transcripts: READ ONLY
PIPELINE_CIRCUIT = os.path.join(config.MAIN_STORE, "state", "caption_circuit.json")   # its caption 429 breaker: read
                                    # only (both ingests download captions from this one machine)


def pipeline_captions_refused(now_ts):
    """True while the pipeline's own caption breaker is open (its ingest was answered HTTP 429 in the last 30 min):
    YouTube refuses this machine, so no caption download is tried here either. The pipeline writes that file only when
    it is refused, in place (transcript_store._open_circuit): a file that cannot be parsed and was written inside the
    breaker's own span is one being written now, so open (audit r118 c1, P0); an older unparsable one, or none, is
    not (a broken file never stops the captions for good)."""
    try:
        with open(PIPELINE_CIRCUIT) as f:
            return float(json.load(f).get("open_until", 0)) > now_ts
    except FileNotFoundError:
        return False
    except (OSError, ValueError, TypeError, AttributeError):
        try:
            return now_ts - os.path.getmtime(PIPELINE_CIRCUIT) < config.ts().CIRCUIT_MINUTES * 60
        except OSError:
            return False


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
    """(json, None) or (None, (kind, detail)). kind: age_gated | unavailable | no_metadata | rate_limited | error."""
    try:
        r = gate.run(["-J", "--skip-download", "--ignore-no-formats-error",
                      f"https://www.youtube.com/watch?v={video_id}"], timeout=120)
    except ListError as e:
        return None, (e.kind, e.detail)
    try:
        j = json.loads(r.stdout)
        if isinstance(j, dict) and j.get("id") == video_id:
            if not any(j.get(k) for k in FACT_KEYS):      # r121: yt-dlp's stub ("youtube video #<id>", every fact
                return None, ("no_metadata", "yt-dlp returned no fact about it (removed, private or not public yet)")
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
    """+10, +20, +40, +80 min, then every 2 h; inside the video's moments' life (config.EXPIRY_H) at most
    PIPELINE_RECHECK_S apart, so the pipeline's own transcript is taken within one run of its ingest."""
    d = config.CAPTION_RETRY_S[tries] if tries < len(config.CAPTION_RETRY_S) else 7200
    if published_ts is not None and now_ts - published_ts < config.EXPIRY_H * 3600:
        d = min(d, PIPELINE_RECHECK_S)
    return now_ts + d


def pipeline_transcript(vid, channel_id, root=None):
    """The video's best record in the pipeline's own transcript store (READ ONLY; transcript_store's rank: Whisper over
    manual over automatic captions) that names this video and this channel, is filed under its own method and whose
    segments hash to its transcript_sha256: (path, record), or None. A record failing any check is never taken."""
    ts = config.ts()
    ts._vdir(vid)                                     # the id's own check (ValueError): no path outside the store
    best = None
    for p in sorted(glob.glob(os.path.join(root or PIPELINE_STORE, vid, "transcript.*.json"))):
        try:
            with open(p) as f:
                rec = json.load(f)
            method = rec.get("transcript_method") if isinstance(rec, dict) else None
            ok = (isinstance(method, str) and os.path.basename(p) == f"transcript.{method.split(':')[0]}.json"
                  and rec.get("video_id") == vid and rec.get("channel_id") == channel_id
                  and isinstance(rec.get("segments"), list) and len(rec["segments"]) > 0
                  and ts.segments_sha256(rec["segments"]) == rec.get("transcript_sha256"))
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            ok = False
        if ok:
            rank = ts.METHOD_RANK.get(method.split(":")[0], 0)
            if best is None or rank > best[0]:
                best = (rank, p, rec)
    return (best[1], best[2]) if best else None


def take_pipeline_transcript(q, vid, channel_id, root=None, found=None):
    """The pipeline's own transcript (pipeline_transcript, or `found`: what the caller's own call returned) copied into
    this store byte for byte, write-once, the copy checked again before it is linked in: True when this store holds it
    (a record of that method already here is kept, never replaced). Said in the video's attempts log and as a queue
    event."""
    found = found or pipeline_transcript(vid, channel_id, root)
    if found is None:
        return False
    src, rec = found
    ts = config.ts()
    dst = os.path.join(ts._vdir(vid), os.path.basename(src))
    if os.path.exists(dst):
        return True
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    tmp = f"{dst}.{os.getpid()}.tmp"
    try:
        shutil.copyfile(src, tmp)
        with open(tmp) as f:
            got = json.load(f)
        if got.get("transcript_sha256") != rec["transcript_sha256"] or \
                ts.segments_sha256(got["segments"]) != rec["transcript_sha256"]:
            ts._log_attempt(vid, step="transcript", status="pipeline_store_copy_refused", source=src,
                            writer="pipeline.ingest")
            return False                              # the bytes copied are not the record checked: not taken
        try:
            os.link(tmp, dst)
        except FileExistsError:
            return True
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    ts._log_attempt(vid, step="transcript", status="taken_from_pipeline_store", source=src,
                    method=rec["transcript_method"], transcript_sha256=rec["transcript_sha256"],
                    acquired_at=rec.get("acquired_at"), writer="pipeline.ingest")
    q.event("pipeline_transcript", vid, channel_id, source=src, method=rec["transcript_method"],
            transcript_sha256=rec["transcript_sha256"], acquired_at=rec.get("acquired_at"))
    return True


def _zoned(s):
    """A time with its zone (ISO 8601, 'Z' read as UTC), else None: a time without its zone is no time."""
    try:
        d = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return d if d.tzinfo is not None else None


def pipeline_sweep(q, now_ts):
    """The orchestrator's 13:05 ruling of Nov 16 ("mine each video within 10 minutes of its transcript"): every video
    waiting on a transcript (probe_retry, captions_pending, and r120: a stream over, live_waiting with live_status
    post_live) inside its moments' life (config.EXPIRY_H) whose next try is later and whose record is in the
    pipeline's store (pipeline_transcript: every check) is made due now, whatever its own retry time; the fetch step
    then probes it and takes the record (a stream still live never: fetch.process). No YouTube request here (one glob, and a
    read of a record that is there). Returns the ids made due; each is a queue event.
    r125: a stream whose last probe still said is_live is made due ONCE when a record acquired after that probe (its
    row's state_at) lands: the pipeline transcribes a stream only once its own probe sees it over, so the fetch step
    probes it now instead of at its 20-min re-probe (Fox Business J0UvqtdsBmc, Nov 18: 462 s). Every probe rewrites
    state_at, so a stream still live is probed once per record, never in a loop, and never taken."""
    rows = q.rows("SELECT video_id, channel_id, state, live_status, state_at FROM videos WHERE (state IN (?, ?) OR "
                  "(state = ? AND live_status IN (?, ?)) OR (state = ? AND reason LIKE ?)) AND next_at > ? AND "
                  "COALESCE(published_ts, discovered_ts) >= ?",
                  (Q.PROBE_RETRY, Q.CAPTIONS_PENDING, Q.LIVE, "post_live", "is_live", Q.UNAVAILABLE, "no metadata:%",
                   now_ts, now_ts - config.EXPIRY_H * 3600))   # r122: the pipeline's record proves a stub's video exists
    due, why = [], {}
    for r in rows:
        try:
            found = pipeline_transcript(r["video_id"], r["channel_id"])
        except ValueError:                            # an id transcript_store refuses: never a path, never due here
            continue
        if found is None:
            continue
        if r["state"] == Q.LIVE and r["live_status"] == "is_live":     # r125: a record newer than the live probe
            got, probed = _zoned(found[1].get("acquired_at")), _zoned(r["state_at"])
            if got is None or probed is None or got <= probed:
                continue
            why[r["video_id"]] = {"live_status": "is_live", "acquired_at": got.isoformat(),   # audit r125 c1: the
                                  "probed_at": probed.isoformat()}                          # two times, on its event
        due.append(r["video_id"])
    if due:
        q.x(f"UPDATE videos SET next_at=? WHERE next_at > ? AND state IN (?, ?, ?, ?) AND video_id IN "
            f"({','.join('?' * len(due))})", (now_ts, now_ts, Q.PROBE_RETRY, Q.CAPTIONS_PENDING, Q.LIVE, Q.UNAVAILABLE)
            + tuple(due))
        for vid in due:
            q.event("pipeline_transcript_due", vid, None, **why.get(vid, {}))
    return due


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
        if kind == "no_metadata":                  # r121: off the waiting count; r122: given up only past its
            seen = v.get("published_ts") or v.get("discovered_ts") or now_ts    # moments' life (a count of tries
            final = now_ts - float(seen) > config.EXPIRY_H * 3600                 # holds its live re-probes too)
            q.set_state(vid, Q.UNAVAILABLE, next_at=now_ts + (10 ** 9 if final else NO_METADATA_RETRY_S),
                        tries=tries + 1, reason=f"no metadata: {detail}")
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
    found = pipeline_transcript(vid, chan["channel_id"]) if live == "post_live" else None   # read once (audit r120 c1)
    if live == "is_live" or (live == "post_live" and found is None):
        q.set_state(vid, Q.LIVE, next_at=now_ts + config.LIVE_REPROBE_S, tries=tries + 1,      # r120: a stream over
                    reason=f"{live}: re-probed every {config.LIVE_REPROBE_S // 60} min (meta.json not written)", **common)
        return Q.LIVE                    # (post_live) whose record the pipeline has goes on, through every check below
    if pub_ts is None:
        q.set_state(vid, Q.PROBE_RETRY, next_at=_retry_at(now_ts, tries), tries=tries + 1,
                    reason="no publish time measured", **common)
        return Q.PROBE_RETRY
    if now_ts - pub_ts > BACKFILL_H * 3600:
        q.set_state(vid, Q.SEEN_OLD, next_at=now_ts + 10 ** 9,
                    reason=f"published {pub}: older than the {BACKFILL_H} h window", **common)
        return Q.SEEN_OLD
    dur = j.get("duration")
    if live == "post_live" and not (isinstance(dur, (int, float)) and dur > 0):    # r120: a stream over, its VOD
        dur = common["duration"] = found[1].get("duration")                          # still processing: its length
                                                                                       # as the pipeline recorded it
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
    if take_pipeline_transcript(q, vid, chan["channel_id"], found=found):   # the pipeline's own transcript: no caption
        return _store_captions(q, gate, v, chan, j, common, tc, now_ts, tries)
    if live == "post_live":                  # r120: its record was not taken (the copy differed): wait for the VOD
        q.set_state(vid, Q.LIVE, next_at=now_ts + config.LIVE_REPROBE_S, tries=tries + 1, title_canon=tc,
                    reason=f"post_live: re-probed every {config.LIVE_REPROBE_S // 60} min (meta.json not written)",
                    **common)
        return Q.LIVE
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
        wait = gate.open_for()
        if wait > 0:                               # the yt-dlp breaker is open: no caption download either
            q.set_state(vid, Q.CAPTIONS_PENDING, next_at=now_ts + wait + 60, title_canon=tc,
                        reason=f"captions: the yt-dlp breaker is open for {wait:.0f} s", **common)
            return Q.CAPTIONS_PENDING
        if pipeline_captions_refused(now_ts):      # the pipeline's ingest was just refused: no request from here
            status, rec = "throttled", None
            ts._log_attempt(vid, step="captions", status=status, writer="pipeline.ingest",
                            why="the pipeline's own caption breaker is open (HTTP 429): no download tried")
        else:
            with gate.sem:
                status, rec = ts.fetch_captions(meta, os.path.join(paths["work"], "captions_tmp"))
            ts._log_attempt(vid, step="captions", status=status, writer="pipeline.ingest")
        if status != "ok":                         # a 429 stops the captions alone (transcript_store's own breaker):
            throttled = status == "throttled"      # never the probe's and the listing's gate (the 10:50 order (1))
            nxt = now_ts + CAPTION_THROTTLED_RETRY_S if throttled else \
                _caption_retry_at(now_ts, common["published_ts"], tries)
            q.set_state(vid, Q.CAPTIONS_PENDING, next_at=nxt, tries=tries + 1, title_canon=tc,
                        reason="captions throttled (HTTP 429; the pipeline's own transcript is looked for at each "
                               "retry)" if throttled else f"captions {status}", **common)
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
