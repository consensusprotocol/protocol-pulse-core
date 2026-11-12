"""pipeline/ingest/service.py: the long-running watcher (tmux pipeline_pp_ingest_watch; no cron).

Loops (threads, one process):
  watch   every POLL_S (+- jitter): list every watched channel, queue new uploads
  fetch   every 10 s: probe due videos, store captions (yt-dlp gate: 3 at once, rate-limit breaker)
  mine    every 5 s: mine transcribed videos (3 videos at once; their windows share one executor whose real
          concurrency is bounded per back-end and globally by providers.Router), append moments, mark mined
  health  every 60 s: Heimdall spend meter (every 10 min), live numbers (ingest/live.json), the daily coverage check
Nothing is dropped: a video whose windows failed on every back-end waits (mine_waiting) and is retried; validated
replies are cached, so a retry or a restart re-asks only what failed. Stop with SIGINT / SIGTERM.
"""
import json
import os
import random
import signal
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from . import config, coverage, fetch, ledger, mine, providers, spend, stats, watch
from . import queue as Q
from .contract import ContractUnavailable

MINE_MAX_TRIES = 8             # a video that keeps failing on every back-end becomes mined_partial after this
MINE_RETRY_S = 600
COVERAGE_HOUR_UTC = 11         # 06:00 ET


class Service:
    def __init__(self, providers_path=None, lease=None, log=None, clock=time.time, backends=None, gate=None,
                 keyring=None, sleep=time.sleep):
        self.p = config.paths()                         # the store transcript_store is bound to (config.ts)
        for k in ("ingest", "moments", "replies", "replies_log", "coverage", "work", "transcripts"):
            os.makedirs(self.p[k], exist_ok=True)
        config.ts()                                     # binds transcript_store to this store, or StoreGuard
        self.clock = clock
        self.log = log or self._log
        self._log_path = os.path.join(self.p["ingest"], "logs", "service.log")
        os.makedirs(os.path.dirname(self._log_path), exist_ok=True)
        self.q = Q.Queue(self.p["queue"], clock=clock)
        self.gate = gate or watch.YouTubeGate(clock=clock)
        self.cfg = providers.load_config(providers_path)
        self.spendbook = providers.SpendBook(loader=self.q.spend_by_day, clock=clock)
        self._rlog_lock = threading.Lock()
        self.overrides = providers.Overrides(os.path.join(self.p["ingest"], "overrides.json"),
                                             on_change=self._override_change)
        self.router = providers.Router(self.cfg, keyring=keyring, lease=lease, spend=self.spendbook,
                                       on_attempt=self._on_attempt, cache_dir=self.p["replies"], clock=clock,
                                       sleep=sleep, backends=backends, overrides=self.overrides)
        mc = self.cfg["heimdall_meter"]
        self.meter = spend.HeimdallMeter(mc, self.router.backends[mc["backend"]], clock=clock,
                                         on_change=self._meter_change)
        self.router.meter = self.meter
        self.executor = ThreadPoolExecutor(max_workers=int(self.cfg["global"]["max_inflight"]),
                                           thread_name_prefix="win")
        self.videos = ThreadPoolExecutor(max_workers=3, thread_name_prefix="vid")
        self.inflight = set()
        self.ilock = threading.Lock()
        self.stop = threading.Event()
        self.rss_mode, self.rss_checked = False, 0.0
        self.cycle = None
        self.last_measure = 0.0
        if ledger.seal(self.p["ledger"]):
            self.q.event("ledger_sealed", None, None, path=self.p["ledger"])
        self.q.recover()

    # ── recording ──

    def _log(self, s):
        line = f"{config.iso()[:19]}Z {s}"
        print(line, flush=True)
        try:
            with open(self._log_path, "a") as f:
                f.write(line + "\n")
        except OSError:
            pass

    def _on_attempt(self, rec):
        self.q.call(rec)
        day = config.iso()[:10]
        line = json.dumps(dict(rec, at=config.iso()), default=str, ensure_ascii=False)
        with self._rlog_lock:
            with open(os.path.join(self.p["replies_log"], f"{day}.jsonl"), "a") as f:
                f.write(line + "\n")

    def _override_change(self, old, new):
        self.q.event("overrides", None, None, old=old, new=new)
        self.log(f"runtime overrides changed: {old} -> {new}")

    def _meter_change(self, state, snap):
        try:
            spend.write_state_notice(state, snap, notify_path=self.p["notify"])
        except OSError as e:
            self.log(f"STATE notice not written: {e}")
        self.q.event("heimdall_meter", None, None, state=state, **snap)
        self.log(f"heimdall meter: {state} {snap}")

    # ── watch ──

    def watch_once(self):
        reg, chans = watch.registry()
        t0 = self.clock()
        self.cycle = "ingest-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%MZ")
        if t0 - self.rss_checked >= config.RSS_CANARY_S:
            was, self.rss_mode, self.rss_checked = self.rss_mode, watch.rss_canary(chans), t0
            if was != self.rss_mode:
                self.q.event("rss_mode", None, None, rss=self.rss_mode)
        res = {"channels": len(chans), "new": 0, "errors": 0, "sources": {}}
        with ThreadPoolExecutor(max_workers=4, thread_name_prefix="list") as ex:
            for r in ex.map(lambda c: watch.poll_channel(self.q, self.gate, c, self.rss_mode), chans):
                res["new"] += r["new"]
                res["errors"] += 1 if r.get("error") and not r.get("skipped") else 0
                if r.get("source"):
                    res["sources"][r["source"]] = res["sources"].get(r["source"], 0) + 1
        res["seconds"] = round(self.clock() - t0, 1)
        self.q.event("watch_cycle", None, None, cycle=self.cycle, **res)
        self.log(f"watch {self.cycle}: {res}")
        return res

    # ── fetch ──

    def fetch_once(self, limit=10):
        optout, oerr = watch.optouts()
        if oerr:
            self.q.event("paused", None, None, why=oerr)
            self.log(f"fetch paused: {oerr}")
            return 0
        reg, chans = watch.registry()
        by = {c["channel_id"]: c for c in chans}

        def one(v):
            try:
                st = fetch.process(self.q, self.gate, v, by.get(v["channel_id"]), optout)
            except Exception as e:
                self.q.set_state(v["video_id"], Q.PROBE_RETRY, next_at=self.clock() + 900,
                                 tries=int(v.get("tries") or 0) + 1, reason=f"fetch crashed: {type(e).__name__}: {e}"[:300])
                self.q.event("fetch_crash", v["video_id"], v["channel_id"], error=traceback.format_exc()[-2000:])
                st = Q.PROBE_RETRY
            if st in (Q.TRANSCRIBED, Q.SHORT, Q.LIVE, Q.NO_CAPTIONS, Q.DUPLICATE, Q.TOO_LONG):
                self.log(f"fetch {v['video_id']} ({by.get(v['channel_id'], {}).get('display_name')}): {st}")
            return st
        claimed = [v for v in self.q.due(Q.FETCH_DUE, limit)
                   if not self.stop.is_set() and self.q.claim(v["video_id"], (v["state"],), Q.PROBING)]
        with ThreadPoolExecutor(max_workers=config.YTDLP_CONCURRENCY, thread_name_prefix="fetch") as ex:
            list(ex.map(one, claimed))           # the yt-dlp gate bounds YouTube at YTDLP_CONCURRENCY processes
        return len(claimed)

    # ── mine ──

    def mine_video(self, v):
        vid = v["video_id"]
        try:
            ts = config.ts()
            rec = ts.canonical_transcript(vid)
            with open(os.path.join(ts._vdir(vid), "meta.json")) as f:
                meta = json.load(f)
            reg, chans = watch.registry()
            chan = next((c for c in chans if c["channel_id"] == v["channel_id"]), None)
            optout, oerr = watch.optouts()
            if oerr or chan is None or v["channel_id"] in optout:
                self.q.set_state(vid, Q.OPTOUT if not oerr else Q.MINE_WAIT,
                                 next_at=self.clock() + (10 ** 9 if not oerr else MINE_RETRY_S),
                                 reason=oerr or "channel opted out or no longer watched")
                return
            src = {"discovered_via": v.get("discovered_via"), "live_status": v.get("live_status"),
                   "media_type": v.get("media_type"), "published_at_source": v.get("published_source"),
                   "duplicate_of": v.get("duplicate_of"), "canonical_url": ts.canonical_url(vid)}
            t0 = self.clock()
            lines, rep = mine.mine_video(self.router, self.executor, rec, meta, chan, reg,
                                         datetime.now(timezone.utc), self.cycle, extra_source=src)
            tries = int(v.get("mine_tries") or 0) + 1
            cost = self.q.rows("SELECT SUM(COALESCE(cost_usd,0)) AS usd FROM calls WHERE video_id=?", (vid,))[0]["usd"]
            common = dict(miners=json.dumps(rep["miners"]), windows=rep["windows"], windows_screened=rep["screened"],
                          windows_failed=len(rep["failed"]), mine_cost_usd=cost, mine_tries=tries)
            if rep["failed"] and tries < MINE_MAX_TRIES:
                self.q.set_state(vid, Q.MINE_WAIT, next_at=self.clock() + MINE_RETRY_S,
                                 reason=f"{len(rep['failed'])} window(s) failed on every back-end: "
                                        f"{json.dumps(rep['failed'][0]['tried'])[:300]}", **common)
                self.log(f"mine {vid}: {len(rep['failed'])}/{rep['windows']} windows failed on every back-end; retry")
                return
            ledger.append(self.p["ledger"], lines)
            st = Q.MINED_PARTIAL if rep["failed"] else Q.MINED
            self.q.set_state(vid, st, next_at=self.clock() + 10 ** 9, moments=len(lines), mined_at=config.iso(),
                             mined_ts=self.clock(), reason=None if not rep["failed"] else
                             f"{len(rep['failed'])} window(s) failed on every back-end after {tries} passes", **common)
            self.log(f"mine {vid} ({chan.get('display_name')}): {len(lines)} moments, windows {rep['windows']} "
                     f"(screened {rep['screened']}, failed {len(rep['failed'])}), miners {rep['miners']}, "
                     f"${(cost or 0):.4f}, {self.clock() - t0:.0f} s")
        except ContractUnavailable as e:
            self.q.set_state(vid, Q.MINE_WAIT, next_at=self.clock() + MINE_RETRY_S, reason=f"contract unavailable: {e}")
            self.log(f"mine {vid}: contract unavailable: {e}")
        except Exception as e:
            self.q.set_state(vid, Q.MINE_WAIT, next_at=self.clock() + MINE_RETRY_S,
                             reason=f"mining crashed: {type(e).__name__}: {e}"[:300])
            self.q.event("mine_crash", vid, v.get("channel_id"), error=traceback.format_exc()[-2000:])
            self.log(f"mine {vid}: crashed {type(e).__name__}: {e}")
        finally:
            with self.ilock:
                self.inflight.discard(vid)

    def mine_once(self, wait=False):
        started = []
        with self.ilock:
            free = 3 - len(self.inflight)
        if free <= 0:
            return 0
        for v in self.q.due(Q.MINE_DUE, free):
            if not self.q.claim(v["video_id"], Q.MINE_DUE, Q.MINING):
                continue
            with self.ilock:
                self.inflight.add(v["video_id"])
            started.append(self.videos.submit(self.mine_video, v))
        if wait:
            for f in started:
                f.result()
        return len(started)

    # ── health ──

    def health_once(self, force_coverage=False):
        now = self.clock()
        if now - self.last_measure >= float(self.cfg["heimdall_meter"]["measure_every_s"]):
            self.meter.measure()
            self.last_measure = now
        s = stats.write_live(self.q, self.p["live"], meter=self.meter, router=self.router)
        day = config.iso()[:10]
        hour = datetime.now(timezone.utc).hour
        if force_coverage or (hour == COVERAGE_HOUR_UTC and self.q.kv_get("coverage_day") != day):
            rep = coverage.check(self.q, self.gate, rss=self.rss_mode)
            path = coverage.write(rep, self.p["coverage"])
            self.q.kv_set("coverage_day", day)
            self.q.event("coverage", None, None, path=path, coverage=rep["coverage"], eligible=rep["eligible"],
                         mined=rep["mined"], unmeasured=len(rep["unmeasured_channels"]))
            self.log(f"coverage: {rep['mined']}/{rep['eligible']} mined, {len(rep['missed'])} listed with reasons, "
                     f"{len(rep['unmeasured_channels'])} channels unmeasured -> {path}")
        return s

    # ── run ──

    def _loop(self, name, fn, every, jitter=0.0):
        while not self.stop.is_set():
            t0 = self.clock()
            try:
                fn()
            except Exception as e:
                self.q.event("loop_error", None, None, loop=name, error=traceback.format_exc()[-2000:])
                self.log(f"{name} loop error: {type(e).__name__}: {e}")
            delay = every + (random.uniform(-jitter, jitter) if jitter else 0.0) - (self.clock() - t0)
            self.stop.wait(max(1.0, delay))

    def describe(self):
        return {bid: {"model": b.model, "enabled": b.enabled(), "base": getattr(b, "base", None)}
                for bid, b in self.router.backends.items() if bid in self.router.chain("mine")}

    def run(self):
        self.log(f"pp-ingest service: store {self.p['root']}, mine chain {self.router.chain('mine')}, "
                 f"back-ends {self.describe()}")
        self.q.event("start", None, None, pid=os.getpid(), chain=self.router.chain("mine"), backends=self.describe())
        self.meter.measure()
        self.last_measure = self.clock()
        threads = [threading.Thread(target=self._loop, args=a, daemon=True, name=a[0]) for a in (
            ("watch", self.watch_once, config.POLL_S, config.POLL_JITTER_S),
            ("fetch", self.fetch_once, 10.0),
            ("mine", self.mine_once, 5.0),
            ("health", self.health_once, 60.0))]
        for t in threads:
            t.start()

        def _stop(*_):
            self.log("stop requested")
            self.stop.set()
        signal.signal(signal.SIGINT, _stop)
        signal.signal(signal.SIGTERM, _stop)
        while not self.stop.is_set():
            self.stop.wait(1.0)
        for t in threads:
            t.join(timeout=30)
        self.videos.shutdown(wait=True)
        self.executor.shutdown(wait=True)
        self.q.event("stop", None, None, pid=os.getpid())
        self.log("stopped")
