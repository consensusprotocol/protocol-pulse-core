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
WAITING = (Q.DISCOVERED, Q.PROBE_RETRY, Q.PROBING, Q.UPCOMING, Q.LIVE, Q.CAPTIONS_PENDING, Q.TRANSCRIBED, Q.MINING,
           Q.MINE_WAIT)
HEAD = ("the watcher's own line, rewritten after each cycle that finds something and as its videos are mined; the "
        "cycles of the last 3 h, newest first: video, channel, mined, moments, hooks, seconds from publish to rows")


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
    head = f"{v['video_id']} {name}"
    st, why = v["state"], (v["reason"] or "")[:120]
    if st == Q.SHORT:
        return f"{head}: a Short, never mined (A2), no rows", None
    if st in WAITING:
        return f"{head}: mined no, queued ({st}{': ' + why if why else ''})", None
    if st not in (Q.MINED, Q.MINED_PARTIAL):
        return f"{head}: mined no ({st}{': ' + why if why else ''})", None
    pub, seen, mined = v["published_ts"], v["discovered_ts"], v["mined_ts"]
    hooks = "hook pass pending" if not v["hook_ts"] else (
        f"{v['hook_rows'] or 0} hooks" + (f" + {v['spot_rows']} spotlights" if v["spot_rows"] else ""))
    lag = (f"seen {seen - pub:.0f} s after publish via {via or v['discovered_via']}, mined {mined - seen:.0f} s after"
           if pub and seen and mined else "publish time not measured")
    to = f"{mined - pub:.0f} s publish -> " if pub and mined else ""
    partial = " (partial)" if st == Q.MINED_PARTIAL else ""
    if v["moments"]:
        text = f"{head}: mined yes{partial} {_et(mined)} ET, {v['moments']} moments, {hooks}, {to}rows ({lag})"
    else:
        w, ws = v["windows"] or 0, v["windows_screened"] or 0
        why0 = (f"all {w} window(s) without a Bitcoin term: screened before any model call" if ws >= w else
                f"{w - ws} window(s) asked, nothing returned")
        text = f"{head}: mined yes{partial} {_et(mined)} ET, 0 moments, {hooks} ({why0}); {to}mined ({lag})"
    return text, max(t for t in (mined, v["hook_ts"]) if t)


def compose(q, now_ts, window_h=WINDOW_H, prefix="PP-INGEST CYCLES"):
    """The line (one physical line), or None when no cycle of the window found a new upload and the 09:02 note does
    not apply either."""
    t0 = now_ts - window_h * 3600
    cycles = [(r["ts"], _detail(r)) for r in q.rows("SELECT ts, detail FROM events WHERE kind='watch_cycle' AND ts >= ? "
                                                    "ORDER BY ts DESC", (t0,))]
    disc = q.rows("SELECT ts, video_id, channel_id, detail FROM events WHERE kind='discovered' AND ts >= ? ORDER BY ts",
                  (t0 - 600,))
    names = {r["channel_id"]: r["display_name"] for r in q.rows("SELECT channel_id, display_name FROM channels")}
    out, newest = [], None
    for ts, d in cycles:
        n = d.get("new") or 0
        if not n:
            continue
        start = ts - float(d.get("seconds") or 0) - 2              # the discoveries of this cycle (its own events)
        vids = [e for e in disc if start <= e["ts"] <= ts + 2]
        newest = max(newest or ts, ts)
        parts = []
        for i, e in enumerate(vids, 1):
            v = q.video(e["video_id"])
            if v is None:
                continue
            text, changed = video_entry(v, names.get(e["channel_id"]) or e["channel_id"], _detail(e).get("via"))
            parts.append(f"({i}) {text}")
            if changed:
                newest = max(newest, changed)
        out.append(f"{_et(ts)} ET cycle, {n} new: " + ("; ".join(parts) or "its discoveries not found in the events"))
    if not cycles:
        return None                                  # no cycle ran in the window: nothing to report
    quiet = _quiet(q, t0, names, len(cycles))
    if not out and not quiet:
        return None
    when = _et(newest if newest else cycles[0][0])   # a quiet window: its newest cycle (rewritten once a cycle)
    body = " | ".join(out) if out else f"none of its {len(cycles)} cycle(s) found a new upload"
    return f"{prefix} TO {when} ET ({HEAD}): {body}" + (f"; {quiet}" if quiet else "")


def _quiet(q, t0, names, ncycles):
    """The 09:02 note, when none of the window's uploads that were mined had a Bitcoin term in any window (all screened
    before any model call); '' when one had. Uploads not mined yet are counted apart: their windows are not known."""
    seen = q.rows("SELECT state, windows, windows_screened FROM videos WHERE discovered_ts >= ? AND state != ?",
                  (t0, Q.SEEN_OLD))
    known = [r for r in seen if r["state"] in (Q.MINED, Q.MINED_PARTIAL)]
    if any((r["windows"] or 0) > (r["windows_screened"] or 0) for r in known):
        return ""
    queued = sum(1 for r in seen if r["state"] in WAITING)
    last = q.rows("SELECT video_id, channel_id, discovered_ts FROM videos WHERE COALESCE(windows,0) > "
                  "COALESCE(windows_screened,0) ORDER BY discovered_ts DESC LIMIT 1")
    tail = (f"; the newest with one: {last[0]['video_id']} {names.get(last[0]['channel_id']) or last[0]['channel_id']},"
            f" seen {_et(last[0]['discovered_ts'], '%H:%M ET %b %d')}" if last else "")
    shorts = sum(1 for r in seen if r["state"] == Q.SHORT)
    if not seen:
        return f"NOTHING BITCOIN IN THE LAST 3 H: no new upload in {ncycles} cycle(s){tail}"
    return (f"NOTHING BITCOIN IN THE LAST 3 H: {len(seen)} upload(s) seen ({shorts} Shorts"
            f"{f', {queued} not mined yet' if queued else ''}), none of the {len(known)} mined with a Bitcoin term in any "
            f"window{tail}")
