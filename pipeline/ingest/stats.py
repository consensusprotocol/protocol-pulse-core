"""pipeline/ingest/stats.py: the live numbers the STATE reports (from the queue; nothing estimated).

moments: per video, the distinct moment ids it has in the ledger (a partial history counted from the ledger itself).
usd_all_time_by_vendor: one indexed aggregate over every recorded call, each minute (cheap at ~1,000 calls a day; a
daily accumulator would be the next step at much higher volume)."""
import json
import os
import statistics
import time

from . import config
from . import queue as Q


def _pct(xs, p):
    xs = sorted(xs)
    if not xs:
        return None
    k = max(0, min(len(xs) - 1, int(round(p / 100 * (len(xs) - 1)))))
    return xs[k]


def live(q, meter=None, router=None, hours=24, now_ts=None):
    now_ts = now_ts or q.clock()
    t0 = now_ts - hours * 3600
    disc = q.rows("SELECT state, discovered_ts, discovered_via, first_sight FROM videos WHERE discovered_ts >= ?", (t0,))
    fresh = [d for d in disc if d["state"] != Q.SEEN_OLD]
    new = [d for d in fresh if not d["first_sight"]]          # uploads discovered after the channel's first listing
    span_h = max(1e-9, min(hours, (now_ts - min([d["discovered_ts"] for d in disc] or [now_ts])) / 3600))
    rows = q.rows("SELECT video_id, channel_id, published_ts, discovered_ts, transcribed_ts, mined_ts, moments, "
                  "miners, windows, windows_screened, windows_failed, mine_cost_usd, state, first_sight FROM videos "
                  "WHERE state IN (?,?) AND mined_ts >= ?", (Q.MINED, Q.MINED_PARTIAL, t0))
    mined = [m for m in rows if m["state"] == Q.MINED]         # a partial video is never counted as mined (B2)
    partial = [m for m in rows if m["state"] == Q.MINED_PARTIAL]
    live_m = [m for m in mined if not m["first_sight"]]       # latency is measured on live discoveries only
    pub_to_mined = [(m["mined_ts"] - m["published_ts"]) / 60 for m in live_m if m["published_ts"] and m["mined_ts"]]
    disc_to_mined = [(m["mined_ts"] - m["discovered_ts"]) / 60 for m in live_m if m["mined_ts"]]
    pub_to_disc = [(m["discovered_ts"] - m["published_ts"]) / 60 for m in live_m if m["published_ts"]]
    moments = [m["moments"] or 0 for m in rows]                # partial videos' moments are in the ledger too
    calls = q.rows("SELECT backend, kind, latency_s, cost_usd FROM calls WHERE ts >= ?", (t0,))
    if router is not None:
        cfg = router.cfg
    else:
        from . import providers
        cfg = providers.load_config()
    vendor_of = {bid: c.get("vendor") for bid, c in cfg["backends"].items()}
    by = {}
    for c in calls:
        b = by.setdefault(c["backend"], {"calls": 0, "ok": 0, "cache": 0, "errors": {}, "usd": 0.0, "lat": []})
        b["usd"] += c["cost_usd"] or 0.0
        if c["kind"] == "cache":
            b["cache"] += 1
            continue
        b["calls"] += 1
        if c["kind"] == "ok":
            b["ok"] += 1
            if c["latency_s"] is not None:
                b["lat"].append(c["latency_s"])
        else:
            b["errors"][c["kind"]] = b["errors"].get(c["kind"], 0) + 1
    backends = {}
    for k, b in by.items():
        backends[k] = {"calls": b["calls"], "ok": b["ok"], "cache_hits": b["cache"],
                       "error_rate": None if not b["calls"] else round(1 - b["ok"] / b["calls"], 4),
                       "errors": b["errors"], "usd_24h": round(b["usd"], 4),
                       "latency_p50_s": None if not b["lat"] else round(statistics.median(b["lat"]), 1),
                       "latency_p95_s": None if not b["lat"] else round(_pct(b["lat"], 95), 1)}
    states = {r["state"]: r["n"] for r in q.rows("SELECT state, COUNT(*) AS n FROM videos GROUP BY state")}
    out = {
        "at": config.iso(), "window_h": hours,
        "videos_seen": len(fresh), "videos_seen_per_hour": round(len(fresh) / span_h, 2),
        "new_uploads_seen": len(new), "new_uploads_per_hour": round(len(new) / span_h, 2),
        "backfill_seen": len(fresh) - len(new), "videos_mined_live": len(live_m),
        "videos_mined": len(mined), "videos_partial": len(partial), "moments": sum(moments),
        "moments_per_video": None if not moments else round(sum(moments) / len(moments), 2),
        "publish_to_mined_min": {"p50": None if not pub_to_mined else round(statistics.median(pub_to_mined), 1),
                                 "p90": None if not pub_to_mined else round(_pct(pub_to_mined, 90), 1),
                                 "n": len(pub_to_mined)},
        "publish_to_discovered_min": {"p50": None if not pub_to_disc else round(statistics.median(pub_to_disc), 1),
                                      "n": len(pub_to_disc)},
        "discovered_to_mined_min": {"p50": None if not disc_to_mined else round(statistics.median(disc_to_mined), 1),
                                    "p90": None if not disc_to_mined else round(_pct(disc_to_mined, 90), 1)},
        "backends": backends,
        "usd_24h_total": round(sum(b["usd_24h"] for b in backends.values()), 4),
        "usd_24h_by_vendor": _by_vendor({k: b["usd_24h"] for k, b in backends.items()}, vendor_of),
        "usd_all_time_by_vendor": _by_vendor({r["backend"]: r["usd"] or 0.0 for r in q.rows(
            "SELECT backend, SUM(COALESCE(cost_usd,0)) AS usd FROM calls GROUP BY backend")}, vendor_of),
        "spend_freeze": sorted((cfg.get("spend_freeze") or {}).get("vendors") or []),
        "mine_waiting_outage": q.rows("SELECT COUNT(*) AS n FROM videos WHERE state=? AND reason LIKE 'OUTAGE%'",
                                      (Q.MINE_WAIT,))[0]["n"],
        "queue_states": states,
        "spend_meter": meter.snapshot() if meter else None,
        "spend_meter_state": meter.state() if meter else None,
        "router": router.snapshot() if router else None,
    }
    metered = {bid for bid, c in cfg["backends"].items() if c.get("spend_meter")}
    hb = [b for k, b in backends.items() if k in metered]
    calls_h = sum(b["calls"] for b in hb)
    out["metered_label"] = (cfg.get("spend_meter") or {}).get("label")
    out["metered_error_rate"] = None if not calls_h else round(1 - sum(b["ok"] for b in hb) / calls_h, 4)
    out["metered_backends"] = sorted(metered)
    try:                                                # ruling 77: the rolling purge, as the watcher last ran it
        last = json.loads(q.kv_get("purge_last") or "null")
    except ValueError:
        last = None
    out["purge"] = {"expiry_h": config.EXPIRY_H, "last_pass": last,
                    "freed_total_bytes": float(q.kv_get("purge_freed_total") or 0)}
    h0 = (now_ts or time.time()) - config.EXPIRY_H * 3600           # ruling 80: the hook pass over the 12 h window
    hk = q.rows("SELECT COUNT(*) AS videos, SUM(hook_ts IS NOT NULL) AS done, SUM(COALESCE(hook_rows,0)) AS rows_, "
                "SUM(COALESCE(hook_cost_usd,0)) AS usd FROM videos WHERE state IN (?, ?) AND published_ts >= ?",
                (Q.MINED, Q.MINED_PARTIAL, h0))[0]
    out["hooks_12h"] = {"mined_videos": hk["videos"] or 0, "hook_pass_done": hk["done"] or 0,
                        "hook_rows": hk["rows_"] or 0, "usd": round(hk["usd"] or 0.0, 4)}
    return out


def _by_vendor(usd_by_backend, vendor_of):
    out = {}
    for bid, usd in usd_by_backend.items():
        v = vendor_of.get(bid) or f"unknown ({bid})"
        out[v] = round(out.get(v, 0.0) + (usd or 0.0), 4)
    return out


def write_live(q, path, **kw):
    s = live(q, **kw)
    tmp = path + ".tmp"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(tmp, "w") as f:
        json.dump(s, f, indent=1, default=str)
    os.replace(tmp, path)
    return s
