"""pipeline/ingest/cycles.py: the orchestrator's standing order of 08:15 ET Nov 14 ("From now on line 1 carries, after
each cycle that finds something: video, channel, mined yes/no, moments, hooks, seconds from publish to rows") and its
note of 09:02 (say so when the cycles find nothing Bitcoin in 3 hours), written by the watcher itself.

compose() reads the watcher's own queue (the watch_cycle and discovered events, the video rows) for the cycles of the
last WINDOW_H hours that found a new upload, newest first, one entry per video. The line's time is that of the newest
cycle or change it reports, never the clock's, so the watcher (spend.write_cycles_notice, from its health loop)
rewrites STATE only when something changed."""
import json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from . import queue as Q

ET = ZoneInfo("America/New_York")
WINDOW_H = 3.0
TRANSCRIPT_LAG_S = 600       # the 13:05 ruling of Nov 16: "mine each video within 10 minutes of its transcript"
MAX_CHARS = 12000             # the line's ceiling: the window's oldest cycles beyond it are counted, not listed
TITLE_CHARS = 40              # a video's title, shortened (a video id alone is not something a reader recognizes)
WAITING = (Q.DISCOVERED, Q.PROBE_RETRY, Q.PROBING, Q.UPCOMING, Q.LIVE, Q.CAPTIONS_PENDING, Q.TRANSCRIBED, Q.MINING,
           Q.MINE_WAIT)
HEAD = ("the watcher's own line, rewritten after each cycle that finds something and as its videos are mined; the "
        "cycles of the last 3 h, newest first: video, channel, mined, moments, hooks, seconds from publish to rows")


def _one(s, n=None):
    """One physical line of text, at most n characters: a reason can carry yt-dlp's multi-line stderr (audit cyc c1,
    glm P0: one newline made the writer refuse the line on every pass)."""
    t = " ".join(str(s or "").split())
    return t if n is None or len(t) <= n else t[:n - 3] + "..."


def _videos(q, ids):
    """The video rows of `ids`, one query per 500 (audit cyc c1: one query per video before)."""
    ids, out = sorted(ids), []
    for i in range(0, len(ids), 500):
        chunk = ids[i:i + 500]
        out += q.rows(f"SELECT * FROM videos WHERE video_id IN ({','.join('?' * len(chunk))})", tuple(chunk))
    return {r["video_id"]: r for r in out}


def _et(ts, fmt="%H:%M"):
    return datetime.fromtimestamp(ts, timezone.utc).astimezone(ET).strftime(fmt)


def _detail(row):
    try:
        d = json.loads(row["detail"] or "{}")
    except ValueError:
        return {}
    return d if isinstance(d, dict) else {}


def video_entry(v, name, via):
    """One video: what became of it (-> (text, the time of its newest change or None))."""
    head = f"{v['video_id']} {_one(name)} \"{_one(v['title'], TITLE_CHARS)}\""
    st, why = v["state"], _one(v["reason"], 120)
    if st == Q.SHORT:
        return f"{head}: a Short, never mined (A2), no rows", None
    if st in WAITING:
        return f"{head}: mined no, queued ({st}{': ' + why if why else ''})", None
    if st not in (Q.MINED, Q.MINED_PARTIAL):
        return f"{head}: mined no ({st}{': ' + why if why else ''})", None
    pub, seen, mined = v["published_ts"], v["discovered_ts"], v["mined_ts"]
    at = f"{_et(mined)} ET" if mined else "(its time not recorded)"
    hooks = "hook pass pending" if not v["hook_ts"] else (
        f"{v['hook_rows'] or 0} hooks" + (f" + {v['spot_rows']} spotlights" if v["spot_rows"] else ""))
    lag = (f"seen {seen - pub:.0f} s after publish via {via or v['discovered_via']}, mined {mined - seen:.0f} s after"
           if pub and seen and mined else "publish time not measured")
    to = f"{mined - pub:.0f} s publish -> " if pub and mined else ""
    tlag = v["transcript_lag_s"] if "transcript_lag_s" in v.keys() else None   # the 13:05 ruling (Nov 16)
    if tlag is not None:
        to += f"{tlag:.0f} s transcript{' (LATE)' if tlag > TRANSCRIPT_LAG_S else ''} -> "
    partial = " (partial)" if st == Q.MINED_PARTIAL else ""
    if v["moments"]:
        text = f"{head}: mined yes{partial} {at}, {v['moments']} moments, {hooks}, {to}rows ({lag})"
    else:
        w, ws = v["windows"] or 0, v["windows_screened"] or 0
        why0 = (f"all {w} window(s) without a Bitcoin term: screened before any model call" if ws >= w else
                f"{w - ws} window(s) asked, nothing returned")
        text = f"{head}: mined yes{partial} {at}, 0 moments, {hooks} ({why0}); {to}mined ({lag})"
    return text, max([t for t in (mined, v["hook_ts"]) if t] or [None]) if (mined or v["hook_ts"]) else None


def compose(q, now_ts, window_h=WINDOW_H, prefix="PP-INGEST CYCLES", max_chars=MAX_CHARS):
    """The line (one physical line, at most max_chars), or None when no cycle ran in the window (the watcher stopped:
    nothing to report). A window whose cycles found nothing new says so (audit cyc c1, glm P0: it vanished)."""
    t0 = now_ts - window_h * 3600
    cycles = [(r["ts"], _detail(r)) for r in q.rows(
        "SELECT ts, detail FROM events WHERE kind='watch_cycle' AND ts >= ? ORDER BY ts DESC", (t0,))]
    if not cycles:
        return None
    disc = q.rows("SELECT ts, video_id, channel_id, detail FROM events WHERE kind='discovered' AND ts >= ? ORDER BY ts",
                  (t0 - 600,))
    rows = _videos(q, {e["video_id"] for e in disc})
    names = {r["channel_id"]: r["display_name"] for r in q.rows("SELECT channel_id, display_name FROM channels")}
    out, newest = [], None
    for ts, d in cycles:
        n = d.get("new") or 0
        if not n:
            continue
        start = ts - float(d.get("seconds") or 0) - 2              # the discoveries of this cycle (its own events)
        evs = [e for e in disc if start <= e["ts"] <= ts + 2]
        newest = max(newest or ts, ts)
        parts, backfill = [], 0
        for e in evs:
            v = rows.get(e["video_id"])
            if v is None:
                continue
            if v["state"] == Q.SEEN_OLD:                           # a channel's first listing: older uploads, recorded
                backfill += 1                                      # as seen, never mined (counted, not listed)
                continue
            try:
                text, changed = video_entry(v, names.get(e["channel_id"]) or e["channel_id"], _detail(e).get("via"))
            except Exception as x:                                 # noqa: BLE001 (audit cyc c2, minimax N2: one row
                text, changed = (f"{e['video_id']}: its row could not be read ({type(x).__name__})", None)  # never
                                                                   # loses the whole line)
            parts.append(f"({len(parts) + 1}) {text}")
            if changed:
                newest = max(newest, changed)
        body = "; ".join(parts) + (f"{'; ' if parts else ''}{backfill} older upload(s) recorded at a channel's first "
                                   "listing (backfill, never mined)" if backfill else "")
        found = "" if len(evs) == n else f" ({len(evs)} found in its events)"    # audit cyc c1 (muse): said, not hidden
        out.append(f"{_et(ts)} ET cycle, {n} new{found}: " + (body or "its discoveries not found in the events"))
    quiet = _quiet(q, t0, names, len(cycles))
    head = f"{prefix} TO {_et(newest if newest else cycles[0][0])} ET ({HEAD}): "   # a quiet window: its newest cycle
    tail = f"; {quiet}" if quiet else ""
    dropped = 0
    while len(out) > 1 and len(head) + len(" | ".join(out)) + len(tail) + 80 > max_chars:
        out.pop()                                                  # the window's oldest cycle first
        dropped += 1
    body = (" | ".join(out) + (f" | ({dropped} older cycle(s) of the window not shown: the line's ceiling)"
                               if dropped else "")) if out else f"none of its {len(cycles)} cycle(s) found a new upload"
    return _one(head + body + tail, max_chars)                     # the ceiling is hard (audit cyc c2: one huge cycle)


def _quiet(q, t0, names, ncycles):
    """The 09:02 note, when none of the window's uploads that were mined had a Bitcoin term in any window (all screened
    before any model call); '' when one had. Uploads not mined yet are counted apart: their windows are not known."""
    seen = q.rows("SELECT state, windows, windows_screened FROM videos WHERE discovered_ts >= ? AND state != ?",
                  (t0, Q.SEEN_OLD))
    known = [r for r in seen if r["state"] in (Q.MINED, Q.MINED_PARTIAL)]
    if any((r["windows"] or 0) > (r["windows_screened"] or 0) for r in known):
        return ""
    shorts = sum(1 for r in seen if r["state"] == Q.SHORT)
    queued = sum(1 for r in seen if r["state"] in WAITING)
    other = len(seen) - len(known) - shorts - queued          # duplicates, no captions, too long, opt-outs (audit cyc
    last = q.rows("SELECT video_id, channel_id, title, discovered_ts FROM videos WHERE COALESCE(windows,0) > "   # c1)
                  "COALESCE(windows_screened,0) ORDER BY discovered_ts DESC LIMIT 1")
    name = _one(names.get(last[0]["channel_id"]) or last[0]["channel_id"]) if last else ""
    tail = (f"; the newest upload with one, before this window: {last[0]['video_id']} {name} "
            f"\"{_one(last[0]['title'], TITLE_CHARS)}\", seen {_et(last[0]['discovered_ts'], '%H:%M ET %b %d')}"
            if last else "")
    if not seen:
        return f"NOTHING BITCOIN IN THE LAST 3 H: no new upload in {ncycles} cycle(s){tail}"
    kinds = ", ".join(f"{k} {w}" for k, w in ((shorts, "Shorts"), (queued, "not mined yet"), (other, "not minable"))
                      if k)
    title = ("NOTHING BITCOIN IN THE LAST 3 H" if not queued else     # uploads not mined yet are not known: the
             f"NOTHING BITCOIN AMONG THE {len(known)} MINED IN THE LAST 3 H ({queued} NOT MINED YET)")   # head says so
    return (f"{title}: {len(seen)} upload(s) seen{f' ({kinds})' if kinds else ''}, none of the {len(known)} mined with a "
            f"Bitcoin term in any window{tail}")


def quiet_head(q, now_ts, window_h=WINDOW_H):
    """The 3-hour note's head alone ("NOTHING BITCOIN IN THE LAST 3 H", or "... AMONG THE K MINED ..."), for STATE line 1
    (ruling 108's batch line; the orchestrator's 21:22 order: Sunday's light uploads, said on line 1); '' when the
    window had Bitcoin, or when no cycle ran in it (the watcher stopped: nothing measured is never read as quiet)."""
    t0 = now_ts - window_h * 3600
    if not q.rows("SELECT 1 AS x FROM events WHERE kind='watch_cycle' AND ts >= ? LIMIT 1", (t0,)):
        return ""
    return _quiet(q, t0, {}, 0).split(":", 1)[0]
