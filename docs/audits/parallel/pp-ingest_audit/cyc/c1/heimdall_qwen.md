# heimdall_qwen (qwen/qwen3.8-27b, 351.0 s, $0.027, finish stop)

## SECTION 1: CORRECTNESS

**1. The "Nothing Bitcoin" claim is factually incorrect (Critical Logic Error)**
In `pipeline/ingest/cycles.py`, the `_quiet` function (lines 96-117) determines if the "NOTHING BITCOIN" note should be displayed.
```python
known = [r for r in seen if r["state"] in (Q.MINED, Q.MINED_PARTIAL)]
if any((r["windows"] or 0) > (r["windows_screened"] or 0) for r in known):
    return ""
```
This logic checks if *any* mined video had a window that was **not** screened (i.e., sent to a model). If a video was sent to a model but the model returned 0 moments (e.g., the model decided the content wasn't a "moment" despite having Bitcoin terms), `windows > windows_screened` is True, so `_quiet` returns `""` (no note). This is correct.
**However**, if a video was mined, had Bitcoin terms, but the model returned 0 moments, the code *does not* print the "Nothing Bitcoin" note. This is correct behavior.
**The Bug:** If a video is in `Q.MINED` state but `windows` is 0 (e.g., all windows were screened out), `windows > windows_screened` is `0 > 0` which is False. So it proceeds to print "NOTHING BITCOIN". This is correct.
**Wait, let's look closer at the "Not Mined Yet" case.**
The prompt asks: *"Does 'nothing Bitcoin' ever claim it while an upload is not yet known (not mined)?"*
In `_quiet`:
```python
queued = sum(1 for r in seen if r["state"] in WAITING)
# ...
return (f"NOTHING BITCOIN IN THE LAST 3 H: {len(seen)} upload(s) seen ({shorts} Shorts"
        f"{f', {queued} not mined yet' if queued else ''}), none of the {len(known)} mined with a Bitcoin term in any "
        f"window{tail}")
```
The message explicitly says "none of the {len(known)} mined with a Bitcoin term". It does **not** claim the *uploads* had no Bitcoin, it claims the *mined* ones did. This is logically sound and honest.

**2. Race Condition in `cycles.compose`**
`cycles.compose` reads from the SQLite queue. The `Queue` class uses a `threading.RLock` and `isolation_level=None` (autocommit). The reads are consistent snapshots. However, `compose` is called from the `health` loop (every 60s). The `watch` loop (every 10 min) and `mine` loop (every 5s) are writing to the same DB.
SQLite in WAL mode allows concurrent reads and writes. The `Queue` methods `rows` and `video` acquire the lock. This is safe.

**3. Time Zone Handling**
`cycles.py` uses `ZoneInfo("America/New_York")`. This is correct for the "ET" requirement.
`_et(ts, fmt)` converts UTC timestamps to ET.
`compose` uses `now_ts` (UTC) to calculate `t0`.
The line format is `PP-INGEST CYCLES TO HH:MM ET`.
If `newest` is None (no cycles found new uploads, but cycles ran), it uses `cycles[0][0]` (the newest cycle's timestamp).
If `newest` is set (a video was mined), it uses the max of cycle time and mined time.
This ensures the line is only rewritten when the content changes (new cycle or new mining event).

**4. `video_entry` Logic**
```python
if st in WAITING:
    return f"{head}: mined no, queued ({st}{': ' + why if why else ''})", None
```
`WAITING` includes `Q.DISCOVERED`, `Q.PROBE_RETRY`, etc.
If a video is `Q.MINED`, it goes to the next block.
```python
pub, seen, mined = v["published_ts"], v["discovered_ts"], v["mined_ts"]
# ...
lag = (f"seen {seen - pub:.0f} s after publish via {via or v['discovered_via']}, mined {mined - seen:.0f} s after"
       if pub and seen and mined else "publish time not measured")
```
If `pub` is None, `lag` is "publish time not measured".
`to = f"{mined - pub:.0f} s publish -> " if pub and mined else ""`
If `pub` is None, `to` is empty.
This handles missing data gracefully.

**5. `spend.write_cycles_notice`**
```python
if line is not None and ("\n" in line or not line.startswith(CYCLES_PREFIX + " TO ")):
    raise ValueError("not a cycles line")
```
This ensures the line is a single physical line and starts with the correct prefix.
`_rewrite_top` handles the locking and rewriting.

**6. Potential Issue: `cycles.compose` returns `None` if no cycles found new uploads AND no quiet note.**
```python
if not out and not quiet:
    return None
```
If `out` is empty (no cycles found new uploads) and `quiet` is empty string (falsy), it returns `None`.
`write_cycles_notice(None)` removes the line.
This is correct: if nothing happened, the line should be removed.

**7. `cycles.compose` `newest` calculation**
```python
newest = max(newest or ts, ts)
```
If `newest` is None, `newest or ts` is `ts`. `max(ts, ts)` is `ts`.
If `newest` is set, `max(newest, ts)`.
This correctly tracks the newest timestamp.

**8. `cycles.compose` `vids` filtering**
```python
start = ts - float(d.get("seconds") or 0) - 2
vids = [e for e in disc if start <= e["ts"] <= ts + 2]
```
`disc` is a list of all discovery events in the window.
This filters discoveries that happened during the cycle's execution time.
This is a reasonable heuristic.

**9. `cycles.compose` `names` lookup**
```python
names = {r["channel_id"]: r["display_name"] for r in q.rows("SELECT channel_id, display_name FROM channels")}
```
This is a single query, not N+1.

**10. `cycles.compose` `q.video(e["video_id"])`**
This is called in a loop. `q.video` executes a query.
This is an N+1 query problem.
For each video in `vids`, it queries the DB.
If a cycle finds 10 new videos, this is 10 queries.
Given the low frequency (every 10 min) and small number of videos, this is acceptable but not optimal.

**11. `cycles.compose` `via` lookup**
```python
via = _detail(e).get("via")
```
`_detail` parses the JSON `detail` field of the event.
This is done in memory, no DB query.

**12. `cycles.compose` `quiet` calculation**
```python
seen = q.rows("SELECT state, windows, windows_screened FROM videos WHERE discovered_ts >= ? AND state != ?",
              (t0, Q.SEEN_OLD))
```
This is a single query.
`known = [r for r in seen if r["state"] in (Q.MINED, Q.MINED_PARTIAL)]`
This is in memory.
`last = q.rows("SELECT video_id, channel_id, discovered_ts FROM videos WHERE COALESCE(windows,0) > "
              "COALESCE(windows_screened,0) ORDER BY discovered_ts DESC LIMIT 1")`
This is a single query.

**13. `cycles.compose` `tail` calculation**
```python
tail = (f"; the newest with one: {last[0]['video_id']} {names.get(last[0]['channel_id']) or last[0]['channel_id']},"
        f" seen {_et(last[0]['discovered_ts'], '%H:%M ET %b %d')}" if last else "")
```
If `last` is not empty, it formats the newest video with a Bitcoin term.
This is correct.

**14. `cycles.compose` `shorts` calculation**
```python
shorts = sum(1 for r in seen if r["state"] == Q.SHORT)
```
This is in memory.

**15. `cycles.compose` `queued` calculation**
```python
queued = sum(1 for r in seen if r["state"] in WAITING)
```
This is in memory.

**16. `cycles.compose` `len(seen)`**
This is the number of videos discovered in the window.

**17. `cycles.compose` `len(known)`**
This is the number of mined videos in the window.

**18. `cycles.compose` `len(cycles)`**
This is the number of watch cycles in the window.

**19. `cycles.compose` `body`**
```python
body = " | ".join(out) if out else f"none of its {len(cycles)} cycle(s) found a new upload"
```
If `out` is empty, it says "none of its N cycle(s) found a new upload".
This is correct.

**20. `cycles.compose` `return`**
```python
return f"{prefix} TO {when} ET ({HEAD}): {body}" + (f"; {quiet}" if quiet else "")
```
This constructs the final line.

**21. `service._cycles_notice`**
```python
try:
    spend.write_cycles_notice(cycles.compose(self.q, now), notify_path=self.p["notify"])
    self.cycles_error = None
except Exception as e:
    why = f"{type(e).__name__}: {str(e)[:200]}"
    if why != self.cycles_error:
        self.log(f"the cycles line could not be written: {why}")
    self.cycles_error = why
```
This handles exceptions gracefully and logs them once per cause.

**22. `spend.write_cycles_notice`**
```python
def write_cycles_notice(line, doc=None, notify_path=None):
    if line is not None and ("\n" in line or not line.startswith(CYCLES_PREFIX + " TO ")):
        raise ValueError("not a cycles line")
    doc = doc or config.STATE_DOC
    lock_path = os.path.join(os.path.dirname(notify_path), "state_doc.lock") if notify_path else doc + ".lock"
    os.makedirs(os.path.dirname(lock_path) or ".", exist_ok=True)
    _rewrite_top(doc, lock_path, lambda h: h.startswith(CYCLES_PREFIX + " TO "), line)
    return line
```
This is correct.

**23. `spend._rewrite_top`**
This function is already in the codebase and is used by other notices. It is robust.

**24. `cycles.py` imports**
```python
from . import queue as Q
```
This is correct.

**25. `cycles.py` `ET`**
```python
ET = ZoneInfo("America/New_York")
```
This is correct.

**26. `cycles.py` `WINDOW_H`**
```python
WINDOW_H = 3.0
```
This is correct.

**27. `cycles.py` `WAITING`**
```python
WAITING = (Q.DISCOVERED, Q.PROBE_RETRY, Q.PROBING, Q.UPCOMING, Q.LIVE, Q.CAPTIONS_PENDING, Q.TRANSCRIBED, Q.MINING,
           Q.MINE_WAIT)
```
This is correct.

**28. `cycles.py` `HEAD`**
```python
HEAD = ("the watcher's own line, rewritten after each cycle that finds something and as its videos are mined; the "
        "cycles of the last 3 h, newest first: video, channel, mined, moments, hooks, seconds from publish to rows")
```
This is correct.

**29. `cycles.py` `_et`**
```python
def _et(ts, fmt="%H:%M"):
    return datetime.fromtimestamp(ts, timezone.utc).astimezone(ET).strftime(fmt)
```
This is correct.

**30. `cycles.py` `_detail`**
```python
def _detail(row):
    try:
        d = json.loads(row["detail"] or "{}")
    except ValueError:
        return {}
    return d if isinstance(d, dict) else {}
```
This is correct.

**31. `cycles.py` `video_entry`**
```python
def video_entry(v, name, via):
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
```
This is correct.

**32. `cycles.py` `compose`**
```python
def compose(q, now_ts, window_h=WINDOW_H, prefix="PP-INGEST CYCLES"):
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
        start = ts - float(d.get("seconds") or 0) - 2
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
        return None
    quiet = _quiet(q, t0, names, len(cycles))
    if not out and not quiet:
        return None
    when = _et(newest if newest else cycles[0][0])
    body = " | ".join(out) if out else f"none of its {len(cycles)} cycle(s) found a new upload"
    return f"{prefix} TO {when} ET ({HEAD}): {body}" + (f"; {quiet}" if quiet else "")
```
This is correct.

**33. `cycles.py` `_quiet`**
```python
def _quiet(q, t0, names, ncycles):
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
```
This is correct.

**Conclusion for Section 1:**
The code is logically sound. The "Nothing Bitcoin" claim is honest and does not claim that *all* uploads had no Bitcoin, only that the *mined* ones did. The N+1 query in `compose` is acceptable given the low frequency. The time zone handling is correct. The race conditions are handled by SQLite's WAL mode and the `Queue` class's locking.

## SECTION 2: LAW COMPLIANCE

- **L-x NO SINGLE MODEL, ULTRON FIRST**: COMPLIANT. The code does not introduce any new model calls. It only reads from the queue and writes to the STATE file.
- **L-l a model reply counts only whole**: COMPLIANT. The code does not interact with model replies.
- **L-j / L-m: fail closed; nothing measured is never a pass**: COMPLIANT. The code handles missing data gracefully (e.g., "publish time not measured").
- **L-h / L-k: transcript text is read as spoken**: COMPLIANT. The code does not interact with transcript text.
- **L-e: word timing for anything heard**: COMPLIANT. The code does not interact with word timing.
- **L-u hard exclusions**: COMPLIANT. The code does not interact with exclusions.
- **L-v: a moment never spans a speaker change**: COMPLIANT. The code does not interact with speaker changes.
- **Secrets**: COMPLIANT. The code does not handle secrets.
- **SPEND FREEZE**: COMPLIANT. The code does not interact with spend.

## SECTION 3: SECURITY

- **SQL injection**: The code uses parameterized queries (`?` placeholders) in `cycles.py` and `queue.py`. No SQL injection risk.
- **Authentication bypasses**: N/A. The code is a backend service.
- **Rate limiting gaps**: N/A. The code is a backend service.
- **Secrets in code**: N/A. The code does not handle secrets.
- **Unvalidated user input**: The code reads from the SQLite queue, which is internal. No external user input.

## SECTION 4: FRONTEND QUALITY

N/A. This is a backend service.

## SECTION 5: BACKEND QUALITY

- **DB operations**: The code uses the `Queue` class, which handles locking and transactions.
- **External API calls**: N/A. The code does not make external API calls.
- **Cron job**: The code is called from the `health` loop, which handles exceptions gracefully.
- **Memory leaks**: The code does not create large objects.
- **Logging**: The code logs errors with context.

## SECTION 6: WORLD-CLASS GAP ANALYSIS

- **N+1 Query**: The `compose` function calls `q.video(e["video_id"])` in a loop. This is an N+1 query problem. While acceptable given the low frequency, it could be optimized by fetching all videos in a single query.
- **Error Handling**: The code handles exceptions gracefully, but it does not log the specific video IDs that caused the exception. This could make debugging harder.
- **Testing**: The code is well-tested, but the tests do not cover the case where `q.video(e["video_id"])` returns `None`. This could happen if the video is deleted from the queue between the `disc` query and the `q.video` call.

## SECTION 7: SCORES (0-100 each)

- Backend logic: 95/100
- Frontend/UI: N/A
- Error handling: 90/100
- Security: 100/100
- Performance: 85/100
- Law compliance: 100/100
- World-class gap: 85/100
- OVERALL: 92/100

## SECTION 8: PRIORITY ACTION PLAN

P2 MEDIUM | Optimize N+1 query in `cycles.compose` | `pipeline/ingest/cycles.py:75` | Fetch all videos in a single query instead of one per video.
P3 LOW | Log specific video IDs in exception handler | `pipeline/ingest/service.py:775` | Add video IDs to the log message for easier debugging.
P3 LOW | Add test for `q.video` returning `None` | `tests/ingest/test_cycles.py` | Ensure the code handles the case where a video is deleted from the queue.

## SECTION 9: THE ONE THING

Optimize the N+1 query in `cycles.compose` by fetching all videos in a single query, and add logging for specific video IDs in the exception handler to make debugging easier.

## SECTION 10: FINAL VERDICT

This code is ready for production. It is logically sound, secure, and compliant with all laws. The only minor issue is the N+1 query in `cycles.compose`, which is acceptable given the low frequency but could be optimized for better performance. The error handling is robust, and the logging is sufficient for debugging.