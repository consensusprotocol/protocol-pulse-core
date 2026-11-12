"""pipeline/ingest/watch.py: list every registered partner / guest channel for new uploads.

RSS first (feeds/videos.xml with If-None-Match / If-Modified-Since); it answered 404 for every channel on 2026-11-07
and 2026-11-12, so one canary channel decides each 30 min whether RSS is in use. The fallback is the channel's uploads
playlist (UU + id[2:]): one request lists regular uploads, livestreams and Shorts with live_status and duration
(INGEST-FAIL-02: the /videos tab has neither streams nor Shorts). Every yt-dlp process goes through YouTubeGate: at
most YTDLP_CONCURRENCY at once, and a rate-limit / bot-check answer pauses all of them (10, 20, 40, 60 min).
"""
import json
import os
import subprocess
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from xml.etree import ElementTree

from . import config
from . import queue as Q

YT_NS = "http://www.youtube.com/xml/schemas/2015"
ATOM_NS = "http://www.w3.org/2005/Atom"
RATE_LIMIT_MARKS = ("HTTP Error 429", "Too Many Requests", "confirm you're not a bot", "confirm you’re not a bot",
                    "Sign in to confirm you")
BACKFILL_H = 72              # first sight of a channel: uploads older than this are recorded as seen, not processed


class ListError(Exception):
    def __init__(self, kind, detail=""):
        super().__init__(f"{kind}: {detail}"[:400])
        self.kind, self.detail = kind, detail


class YouTubeGate:
    def __init__(self, slots=config.YTDLP_CONCURRENCY, clock=time.time, sleep=time.sleep):
        self.sem = threading.BoundedSemaphore(slots)
        self.clock, self.sleep = clock, sleep
        self.lock = threading.Lock()
        self.until, self.trips = 0.0, 0
        self.last_trip = None

    def open_for(self):
        with self.lock:
            return max(0.0, self.until - self.clock())

    def trip(self, why):
        with self.lock:
            self.trips += 1
            self.until = self.clock() + min(600 * 2 ** (self.trips - 1), 3600)
            self.last_trip = (config.iso(), why[:200])

    def calm(self):
        with self.lock:
            self.trips = max(0, self.trips - 1)

    def run(self, args, timeout=120):
        """yt-dlp with the store's flags (cookies when the store has them); raises ListError('rate_limited') while
        the breaker is open or when YouTube answers a rate limit / bot check."""
        if self.open_for() > 0:
            raise ListError("rate_limited", f"yt-dlp breaker open for {self.open_for():.0f} s")
        with self.sem:
            r = config.ts()._ytdlp(args, timeout=timeout)
        err = r.stderr or ""
        if any(m in err for m in RATE_LIMIT_MARKS):
            self.trip(err[-200:])
            raise ListError("rate_limited", err[-300:])
        return r


def _ts_iso(t):
    return datetime.fromtimestamp(float(t), timezone.utc).isoformat() if t is not None else None


def _parse_iso(s):
    try:
        d = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        return d if d.tzinfo else None
    except (TypeError, ValueError):
        return None


def rss_list(cid, etag=None, last_modified=None, timeout=15):
    """('not_modified', [], headers) | ('ok', entries, headers). entries: video_id, title, published (aware ISO),
    url. Raises ListError."""
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={cid}"
    h = {"User-Agent": "Mozilla/5.0 (pp-ingest)"}
    if etag:
        h["If-None-Match"] = etag
    if last_modified:
        h["If-Modified-Since"] = last_modified
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=timeout) as r:
            body, headers = r.read(), dict(r.headers)
    except urllib.error.HTTPError as e:
        if e.code == 304:
            return "not_modified", [], dict(e.headers or {})
        raise ListError(f"rss_http_{e.code}", url)
    except (urllib.error.URLError, OSError) as e:
        raise ListError("rss_network", str(e)[:200])
    try:
        root = ElementTree.fromstring(body)
    except ElementTree.ParseError as e:
        raise ListError("rss_parse", str(e)[:200])
    out = []
    for e in root.findall(f"{{{ATOM_NS}}}entry"):
        vid, title, pub = e.find(f"{{{YT_NS}}}videoId"), e.find(f"{{{ATOM_NS}}}title"), e.find(f"{{{ATOM_NS}}}published")
        link = e.find(f"{{{ATOM_NS}}}link")
        if vid is None or not (vid.text or "").strip() or pub is None or _parse_iso(pub.text) is None:
            continue
        out.append({"video_id": vid.text.strip(), "title": (title.text or "").strip() if title is not None else "",
                    "published": pub.text.strip(), "url": link.get("href", "") if link is not None else ""})
    return "ok", out, headers


def uploads_url(cid):
    if not (isinstance(cid, str) and cid.startswith("UC") and len(cid) == 24):
        raise ListError("bad_channel_id", repr(cid))
    return f"https://www.youtube.com/playlist?list=UU{cid[2:]}"


def playlist_list(gate, cid, n=config.LIST_N, timeout=120):
    """The uploads playlist, newest first: video_id, title, ts (approximate epoch), live_status, duration, url."""
    r = gate.run(["-J", "--flat-playlist", "--playlist-end", str(n), "--extractor-args",
                  "youtubetab:approximate_date", uploads_url(cid)], timeout=timeout)
    try:
        j = json.loads(r.stdout)
    except ValueError:
        raise ListError("playlist_unreadable", (r.stderr or "")[-300:])
    if not isinstance(j, dict) or not isinstance(j.get("entries"), list):
        raise ListError("playlist_unreadable", "no entries")
    if j.get("channel_id") and j["channel_id"] != cid:
        raise ListError("channel_mismatch", f"playlist channel {j.get('channel_id')} != {cid}")
    out = []
    for e in j["entries"]:
        if not isinstance(e, dict) or not e.get("id"):
            continue
        out.append({"video_id": e["id"], "title": e.get("title") or "", "ts": e.get("timestamp"),
                    "live_status": e.get("live_status"), "duration": e.get("duration"), "url": e.get("url")})
    return out


def registry():
    """(full registry list, watched channels): enabled with a channel id = transcript_ingest.editorial_channels.
    PP_INGEST_CHANNELS (comma-separated slugs or channel ids) narrows the watched set for drills and tests."""
    with open(config.REGISTRY_PATH) as f:
        reg = json.load(f)
    chans = [c for c in reg if c.get("enabled", True) and c.get("channel_id")]
    only = {x.strip() for x in os.environ.get("PP_INGEST_CHANNELS", "").split(",") if x.strip()}
    if only:
        chans = [c for c in chans if c.get("slug") in only or c["channel_id"] in only]
    return reg, chans


def optouts():
    """(set of channel ids, error). Absent file = nobody opted out. Unreadable or unknown shape = error: the caller
    pauses fetching and mining (fail closed: any channel could be the one that opted out)."""
    try:
        with open(config.OPTOUT_PATH) as f:
            j = json.load(f)
    except FileNotFoundError:
        return set(), None
    except (OSError, ValueError) as e:
        return set(), f"optout.json unreadable: {type(e).__name__}: {e}"
    ids = j.get("channel_ids") if isinstance(j, dict) else j
    if not isinstance(ids, list) or not all(isinstance(x, str) for x in ids):
        return set(), "optout.json: expected a list of channel ids (or {'channel_ids': [...]})"
    return set(ids), None


def poll_channel(q, gate, chan, rss_mode, now_ts=None, backfill_h=BACKFILL_H):
    """List one channel and queue its new uploads. Returns {'new': n, 'source': ..., 'error': ...}."""
    cid = chan["channel_id"]
    q.ensure_channel(chan)
    row = q.channel(cid)
    now_ts = now_ts or q.clock()
    if row["backoff_until"] and row["backoff_until"] > now_ts:
        return {"new": 0, "source": None, "error": "backoff", "skipped": True}
    first_sight = row["listed"] == 0
    entries, source, upd = None, None, {}
    err = None
    if rss_mode:
        try:
            status, ents, headers = rss_list(cid, row.get("etag"), row.get("last_modified"))
            source = "rss"
            upd.update(etag=headers.get("ETag") or row.get("etag"),
                       last_modified=headers.get("Last-Modified") or row.get("last_modified"))
            entries = [] if status == "not_modified" else [
                {"video_id": e["video_id"], "title": e["title"], "ts": _parse_iso(e["published"]).timestamp(),
                 "published": e["published"], "live_status": None, "duration": None, "url": e["url"]}
                for e in ents]
        except ListError as e:
            err = f"{e.kind}"
    if entries is None:
        try:
            entries, source = playlist_list(gate, cid), "uploads_playlist"
        except ListError as e:
            err = f"{err + '; ' if err else ''}{e.kind}: {e.detail[:160]}"
    if entries is None:
        n = (row["consecutive_errors"] or 0) + 1
        q.channel_update(cid, last_poll_at=config.iso(), consecutive_errors=n, last_error=err,
                         backoff_until=now_ts + min(60 * 2 ** n, 3600))
        q.event("list_error", None, cid, error=err, consecutive=n)
        return {"new": 0, "source": None, "error": err}
    new = 0
    newest = row.get("newest_published")
    for e in entries:
        ts_ = e.get("ts")
        old = first_sight and ts_ is not None and now_ts - float(ts_) > backfill_h * 3600
        state, reason = (Q.SEEN_OLD, f"listed at first sight, older than {backfill_h} h") if old else (Q.DISCOVERED, None)
        if "/shorts/" in (e.get("url") or ""):
            state, reason = Q.SHORT, "listed as a Short (/shorts/ link)"
        if q.add_video(e["video_id"], cid, e.get("title"), source, ts_, e.get("live_status"), e.get("duration"),
                       e.get("url"), state=state, reason=reason, first_sight=first_sight):
            new += 1
        p = e.get("published") or _ts_iso(ts_)
        if p and (newest is None or p > newest):
            newest = p
    q.channel_update(cid, last_poll_at=config.iso(), last_ok_at=config.iso(), last_source=source,
                     consecutive_errors=0, backoff_until=0, last_error=None, newest_published=newest,
                     listed=(row["listed"] or 0) + len(entries), **upd)
    return {"new": new, "source": source, "error": None, "listed": len(entries)}


def rss_canary(chans):
    """True when RSS answers 200 for the first watched channel (one request)."""
    for c in chans[:1]:
        try:
            status, _, _ = rss_list(c["channel_id"])
            return status in ("ok", "not_modified")
        except ListError:
            return False
    return False
