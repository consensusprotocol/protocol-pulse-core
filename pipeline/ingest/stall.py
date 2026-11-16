"""pipeline/ingest/stall.py: THE SELF-CHECK (the orchestrator's 10:50 ET order of Nov 16, (4)): "if videos are
waiting and nothing has been mined for 30 minutes, write it on line 1 and act; do not sit idle at the prompt".

WAITING  a video inside its moments' life (config.EXPIRY_H from its publish, or from its discovery while the publish
         time is not measured yet) in a state that leads to mining: discovered, probing, probe_retry, captions_pending,
         transcribed, mining, mine_waiting; and (r120) a stream that is over but still processing (live_waiting with
         live_status post_live). An upcoming stream or one still live is not waiting (nothing to mine before it ends);
         a Short, a duplicate or any other terminal state never is.
STALLED  something waits and nothing was mined for STALL_S: the later of the newest mined video's time and the oldest
         waiting video's discovery is at least STALL_S old (a video that came in a minute ago is no stall).
LINE     "MINING STALLED SINCE HH:MM ET: n VIDEO(S) WAITING, NOTHING MINED FOR 30 MIN OR MORE: k <why>, ...; ACTED HH:MM
         ET: m MADE DUE NOW ..." at the front of STATE line 1 (spend.write_stall_notice, after the batch spend and an
         alarm), its text stable while the stall lasts; removed when it ends.
ACT      when the stall is found, and again every STALL_S while it lasts: every waiting video in a retry state whose
         next try is later is made due now (the fetch step looks in the pipeline's own transcript store first, then
         probes; the miner takes what is transcribed). Each act is an event and a log line (Service._stall_notice).
"""
from collections import Counter
from datetime import datetime
from zoneinfo import ZoneInfo

from . import config
from . import queue as Q
from .spend import STALL_PREFIX

STALL_S = 1800
WAITING = (Q.DISCOVERED, Q.PROBING, Q.PROBE_RETRY, Q.CAPTIONS_PENDING, Q.TRANSCRIBED, Q.MINING, Q.MINE_WAIT)
RETRYABLE = (Q.DISCOVERED, Q.PROBE_RETRY, Q.CAPTIONS_PENDING, Q.MINE_WAIT, Q.LIVE)   # never one in flight; LIVE
                                                                                   # rows here are post_live ones only
ET = ZoneInfo("America/New_York")


def why(state, reason):
    """What one waiting video waits on, in a few words (from its state and the reason the queue recorded)."""
    r = reason or ""
    if state == Q.CAPTIONS_PENDING:
        if r.startswith("captions throttled"):
            return "CAPTIONS REFUSED BY YOUTUBE (HTTP 429)"
        if r.startswith("captions: the yt-dlp breaker"):
            return "CAPTIONS BEHIND THE YT-DLP BREAKER"
        if r.startswith("VOD without English captions"):
            return "NO ENGLISH CAPTIONS YET"
        return "CAPTIONS TO RETRY"
    if state == Q.PROBE_RETRY:
        return "PROBE BEHIND THE YT-DLP BREAKER" if r.startswith("rate_limited") else "PROBE TO RETRY"
    if state in (Q.DISCOVERED, Q.PROBING):
        return "NOT PROBED YET"
    if state in (Q.TRANSCRIBED, Q.MINING):
        return "TRANSCRIBED, BEING MINED"
    if state == Q.MINE_WAIT:
        return "NO MODEL OF THE CHAIN ANSWERED" if r.startswith("OUTAGE") else "MINING TO RETRY"
    if state == Q.LIVE:
        return "STREAM OVER, ITS VIDEO STILL PROCESSING"
    return state.upper()


def check(q, now, expiry_h=None, stall_s=STALL_S):
    """{'stalled', 'waiting' (rows), 'since' (when the stall clock started; None when nothing waits), 'last_mined'}."""
    horizon = now - float(config.EXPIRY_H if expiry_h is None else expiry_h) * 3600
    marks = ",".join("?" * len(WAITING))
    rows = q.rows(f"SELECT video_id, state, reason, next_at, discovered_ts FROM videos WHERE (state IN ({marks}) OR "
                  "(state = ? AND live_status = ?)) AND COALESCE(published_ts, discovered_ts) >= ?",
                  tuple(WAITING) + (Q.LIVE, "post_live", horizon))
    last = q.rows("SELECT MAX(mined_ts) AS t FROM videos WHERE state IN (?, ?)", (Q.MINED, Q.MINED_PARTIAL))[0]["t"]
    if not rows:
        return {"stalled": False, "waiting": [], "since": None, "last_mined": last}
    since = max(float(last or 0.0), min(float(r["discovered_ts"]) for r in rows))
    return {"stalled": now - since >= stall_s, "waiting": rows, "since": since, "last_mined": last}


def act(q, chk, now):
    """Every waiting video in a retry state whose next try is later: due now. Returns how many."""
    ids = [r["video_id"] for r in chk["waiting"] if r["state"] in RETRYABLE and float(r["next_at"] or 0) > now]
    if ids:
        q.x(f"UPDATE videos SET next_at=? WHERE next_at > ? AND state IN ({','.join('?' * len(RETRYABLE))}) AND "
            f"video_id IN ({','.join('?' * len(ids))})", (now, now) + tuple(RETRYABLE) + tuple(ids))
    return len(ids)


def _hm(t, now):
    d = datetime.fromtimestamp(t, ET)
    same_day = d.date() == datetime.fromtimestamp(now, ET).date()
    return d.strftime("%H:%M ET") + ("" if same_day else d.strftime(" %b %d").upper())


def line(chk, now, acted_at=None, acted_n=0, stall_s=STALL_S):
    """The STATE line-1 notice for a stall (stable while it lasts: no running count of minutes)."""
    n = len(chk["waiting"])
    parts = ", ".join(f"{k} {w}" for w, k in sorted(Counter(why(r["state"], r["reason"]) for r in chk["waiting"])
                                                    .items(), key=lambda kv: (-kv[1], kv[0])))
    acted = (f"; ACTED {_hm(acted_at, now)}: {acted_n} MADE DUE NOW (THE PIPELINE'S OWN TRANSCRIPTS LOOKED FOR FIRST)"
             if acted_at is not None else "")
    return (f"{STALL_PREFIX}{_hm(chk['since'], now)}: {n} VIDEO(S) WAITING, NOTHING MINED FOR {int(stall_s // 60)} MIN "
            f"OR MORE: {parts}{acted}")
