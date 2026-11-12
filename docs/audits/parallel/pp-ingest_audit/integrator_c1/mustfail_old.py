"""Reproduce the integrator's B1, B2, B4 and the discarded-flags finding on the OLD code (753dec1d export).
Run: PYTHONDONTWRITEBYTECODE=1 PP_INGEST_STORE=<scratch store> python3 -I mustfail_old.py <export dir>"""
import json
import os
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

OLD = sys.argv[1]
sys.path.insert(0, OLD)
sys.path.insert(0, os.path.join(OLD, "tests", "ingest"))
import helpers as H                                   # noqa: E402  (the old helpers)
from pipeline.ingest import config, coverage, ledger, mine, providers, service, spend, watch   # noqa: E402
from pipeline.ingest import queue as Q                # noqa: E402
from pipeline.ingest.providers import BackendError    # noqa: E402

out = {}
OK = json.dumps({"ok": True})


def v_ok(c):
    if json.loads(c) != {"ok": True}:
        raise providers.Invalid("no")
    return True


# B1: tripped meter + only the metered back-end in the chain -> the chain halts
h = H.FakeBackend("h", [OK], cfg={"spend_meter": "heimdall"}, usage_total=95.0)
r = H.make_router([h])
r.meter = spend.HeimdallMeter(H.router_cfg(["h"])["heimdall_meter"], h)
r.meter.measure()
try:
    r.run("mine", "p", None, v_ok)
    out["B1"] = "no halt (not reproduced)"
except providers.AllBackendsFailed as e:
    out["B1"] = f"HALTED at 90 % with the metered back-end alone: {e.tried}; calls made: {len(h.calls)}"
h2 = H.FakeBackend("h2", [OK], cfg={"spend_meter": "heimdall"}, usage_total=RuntimeError("credits down"))
r2 = H.make_router([h2])
r2.meter = spend.HeimdallMeter(H.router_cfg(["h2"])["heimdall_meter"], h2)
r2.meter.measure()
try:
    r2.run("mine", "p", None, v_ok)
    out["B1_unmeasured"] = "no halt"
except providers.AllBackendsFailed as e:
    out["B1_unmeasured"] = f"HALTED when merely unmeasured: {e.tried}"

# B4: an age-gated video trips the global breaker and is requeued
ts = config.ts()
age = "ERROR: [youtube] abc: Sign in to confirm your age. This video may be inappropriate for some users."
ts._ytdlp = lambda args, timeout=120: subprocess.CompletedProcess(args, 1, "", age)
g = watch.YouTubeGate(clock=lambda: 1000.0)
try:
    g.run(["-J", "x"])
    out["B4"] = "no trip"
except watch.ListError as e:
    out["B4"] = f"age gate read as a RATE LIMIT: kind={e.kind}, breaker trips={g.trips}, open for {g.open_for():.0f} s; " \
                f"calm() callers in watch.py/fetch.py: {open(os.path.join(OLD, 'pipeline/ingest/watch.py')).read().count('.calm(') + open(os.path.join(OLD, 'pipeline/ingest/fetch.py')).read().count('.calm(')}"

# flags of a repeated range: the second observation's flags are discarded
rec, meta = H.caption_record(H.vid(), n_rep=12)


def fn(prompt):
    ids = H.offered_ids(prompt)
    if ids[0] == 34:
        return H.reply([H.moment(34, 35, risk=["ad_read"], names_person=True, altcoin=True)])
    ms = [H.moment(ids[0], ids[1])]
    if 34 in ids and 35 in ids:
        ms.append(H.moment(34, 35))
    return H.reply(ms)


rr = H.make_router([H.FakeBackend("primary", fn=fn)])
with ThreadPoolExecutor(1) as ex:
    lines, rep = mine.mine_video(rr, ex, rec, meta, H.CHAN, [H.CHAN], datetime.now(timezone.utc), "c", use_cache=False)
dup = next(l for l in lines if tuple(l["sentences"]) == (34, 35))
out["flags"] = f"observations={dup['mined']['observations']} risk={dup['risk']} names_person={dup['names_person']} " \
               f"altcoin={dup['flags_ext']['altcoin']} (the second observation flagged ad_read / names_person / altcoin)"

# B2: both back-ends down for 8 passes -> mined_partial, never due again, counted as mined by coverage
p = config.paths()
watch.registry = lambda: ([H.CHAN], [H.CHAN])
watch.rss_canary = lambda chans: False
service.spend.write_state_notice = lambda *a, **k: None
ts.fetch_captions = lambda meta, work: ("ok", ts._make_record(meta, "yt_auto:en-orig", "youtube captions (auto-subs, en-orig)",
                                         H.caption_record(meta["video_id"], n_rep=8, lead=[f"Bitcoin show {meta['video_id']} {i}." for i in range(30)])[0]["segments"]))
cfg = H.router_cfg(["primary", "fallback"])
cfg["backends"]["primary"]["spend_meter"] = "heimdall"
cpath = os.path.join(tempfile.mkdtemp(), "providers.json")
open(cpath, "w").write(json.dumps(cfg))
now = time.time()
vid = H.vid("e")
listing = {H.CHAN["channel_id"]: {"channel_id": H.CHAN["channel_id"], "entries": [
    {"id": vid, "title": f"Bitcoin {vid}", "timestamp": now - 1800, "live_status": None, "duration": 900,
     "url": f"https://www.youtube.com/watch?v={vid}"}]}}
gate = H.FakeGate(listing=listing, probes={vid: H.probe_json(vid, timestamp=now - 1800, title=f"Bitcoin {vid}")})
down = lambda p_: BackendError("network", "down")      # noqa: E731
backends = {"primary": H.FakeBackend("primary", fn=down, cfg={"spend_meter": "heimdall"}, usage_total=1.0),
            "fallback": H.FakeBackend("fallback", fn=lambda p_: BackendError("overloaded", "busy"))}
s = service.Service(providers_path=cpath, backends=backends, gate=gate, log=lambda m: None,
                    keyring=providers.Keyring("/nonexistent"), sleep=lambda x: None)
s.meter.measure()
s.watch_once()
while s.fetch_once(limit=20):
    pass
for i in range(service.MINE_MAX_TRIES):
    s.q.x("UPDATE videos SET next_at=0 WHERE state=?", (Q.MINE_WAIT,))
    for hh in s.router.health.values():
        hh.open_until = 0.0
    while s.mine_once(wait=True):
        pass
row = s.q.video(vid)
rep = coverage.check(s.q, gate, hours=24, rss=False, chans=[H.CHAN])
out["B2"] = (f"after {service.MINE_MAX_TRIES} passes of a pure outage (= {service.MINE_MAX_TRIES * service.MINE_RETRY_S // 60} "
             f"min): state={row['state']}, next_at in {(row['next_at'] - time.time()) / 86400 / 365:.0f} years, "
             f"ledger lines={len(ledger.read(s.p['ledger'])[0])}, coverage counts it mined: {rep['mined']}/{rep['eligible']}")
print(json.dumps(out, indent=1))
