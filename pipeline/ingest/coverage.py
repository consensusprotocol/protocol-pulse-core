"""pipeline/ingest/coverage.py: the daily coverage check ("never miss the day's most relevant content" as a number).

An INDEPENDENT listing of every watched channel at check time (RSS when its canary answers, else the uploads
playlist; never the watcher's own queue) gives the videos published in the last `hours`. Each is matched to the
queue: mined (its moments, possibly none, are in the ledger) or not, with the reason. A channel whose listing fails is
UNMEASURED: its videos are never counted as covered (law L-m). Shorts are reported apart (never mined by policy).
"""
import json
import os
import time
from datetime import datetime, timezone

from . import config
from . import queue as Q
from . import watch

RSS_CACHE_S = 900             # YouTube's feeds answer Cache-Control: public, max-age=900 (measured 2026-11-12)

REASONS = {
    Q.SHORT: "a Short: never mined (policy, L-u)",
    Q.UPCOMING: "upcoming stream: not started",
    Q.LIVE: "stream still live / post-live: re-probed every 20 min",
    Q.CAPTIONS_PENDING: "no English captions yet: re-probed",
    Q.NO_CAPTIONS: "no English captions 48 h after publish: needs the pipeline's Whisper",
    Q.TOO_LONG: "longer than the 6 h VOD ceiling",
    Q.UNAVAILABLE: "unavailable (private / removed / members-only / age-gated)",
    Q.DUPLICATE: "re-upload of an earlier video",
    Q.OPTOUT: "channel opted out / no longer watched",
    Q.SEEN_OLD: "dated outside the 72 h window at probe",
    Q.DISCOVERED: "discovered, not yet probed",
    Q.PROBE_RETRY: "probe failed: retrying",
    Q.PROBING: "being probed",
    Q.TRANSCRIBED: "transcribed: waiting to be mined",
    Q.MINING: "being mined",
    Q.MINE_WAIT: "every back-end failed or refused: retrying",
}


def check(q, gate, hours=24, now_ts=None, rss=None, chans=None):
    now_ts = now_ts or time.time()
    if chans is None:
        _, chans = watch.registry()
    optout, oerr = watch.optouts()
    rss = watch.rss_canary(chans) if rss is None else rss
    rep = {"at": config.iso(), "hours": hours, "listing": "rss" if rss else "uploads_playlist", "channels": len(chans),
           "unmeasured_channels": [], "published": 0, "shorts": 0, "eligible": 0, "mined": 0, "missed": [],
           "per_channel": {}, "optout_error": oerr}
    for c in chans:
        cid, name = c["channel_id"], c.get("display_name")
        try:
            if rss:
                st, ents, _ = watch.rss_list(cid)
                ents = [{"video_id": e["video_id"], "title": e["title"], "ts": watch._parse_iso(e["published"]).timestamp(),
                         "url": e["url"]} for e in ents]
            else:
                ents = watch.playlist_list(gate, cid)
        except watch.ListError as e:
            rep["unmeasured_channels"].append({"channel": name, "channel_id": cid, "error": f"{e.kind}: {e.detail[:120]}"})
            continue
        pc = rep["per_channel"].setdefault(name, {"published": 0, "mined": 0, "missed": 0, "shorts": 0})
        for e in ents:
            v = q.video(e["video_id"])
            pts = (v or {}).get("published_ts") or e.get("ts")
            if pts is None or not (now_ts - hours * 3600 <= float(pts) <= now_ts + 600):
                continue
            rep["published"] += 1
            pc["published"] += 1
            state = (v or {}).get("state")
            is_short = state == Q.SHORT or "/shorts/" in (e.get("url") or "")
            if is_short:
                rep["shorts"] += 1
                pc["shorts"] += 1
                continue
            rep["eligible"] += 1
            if state in (Q.MINED, Q.MINED_PARTIAL):
                rep["mined"] += 1
                pc["mined"] += 1
                if state == Q.MINED_PARTIAL:
                    rep["missed"].append(_row(e, c, v, "mined partially: some windows failed on every back-end"))
                continue
            pc["missed"] += 1
            age_min = (now_ts - float(pts)) / 60
            if v is None and age_min * 60 <= config.POLL_S + config.POLL_JITTER_S + RSS_CACHE_S:
                why = (f"published {age_min:.0f} min ago: inside the discovery window (a {config.POLL_S // 60} min poll "
                       f"+ YouTube's RSS cache, max-age {RSS_CACHE_S // 60} min), not listed yet")
            elif v is None:
                why = "never discovered by the watcher (a watcher miss)"
            else:
                why = REASONS.get(state, state) + (f" ({v.get('reason')})" if v.get("reason") else "")
            rep["missed"].append(_row(e, c, v, why))
    rep["coverage"] = None if not rep["eligible"] else round(rep["mined"] / rep["eligible"], 4)
    rep["measured"] = not rep["unmeasured_channels"]
    return rep


def _row(e, c, v, why):
    return {"channel": c.get("display_name"), "video_id": e["video_id"], "title": (v or {}).get("title") or e.get("title"),
            "published_at": (v or {}).get("published_at") or (
                datetime.fromtimestamp(float(e["ts"]), timezone.utc).isoformat() if e.get("ts") else None),
            "state": (v or {}).get("state"), "reason": why}


def write(rep, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    day = rep["at"][:10]
    with open(os.path.join(out_dir, f"{day}.json"), "w") as f:
        json.dump(rep, f, indent=1)
    cov = "unmeasured" if rep["coverage"] is None else f"{rep['coverage'] * 100:.1f} %"
    md = [f"# Coverage {rep['at']} (last {rep['hours']} h, listing: {rep['listing']})", "",
          f"- partner videos published: {rep['published']} ({rep['shorts']} Shorts, never mined by policy)",
          f"- long-form videos: {rep['eligible']}; mined (in the ledger): {rep['mined']}; coverage {cov}",
          f"- channels unmeasured (listing failed): {len(rep['unmeasured_channels'])}"
          + (" -> this report is NOT a full measurement" if rep["unmeasured_channels"] else ""), "",
          "| channel | video | published | state | reason |", "|---|---|---|---|---|"]
    for m in rep["missed"]:
        md.append(f"| {m['channel']} | {m['video_id']} | {m['published_at']} | {m['state']} | {m['reason']} |")
    for u in rep["unmeasured_channels"]:
        md.append(f"| {u['channel']} | (listing failed) | | | {u['error']} |")
    with open(os.path.join(out_dir, f"{day}.md"), "w") as f:
        f.write("\n".join(md) + "\n")
    return os.path.join(out_dir, f"{day}.md")
