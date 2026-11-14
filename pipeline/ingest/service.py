"""pipeline/ingest/service.py: the long-running watcher (tmux pipeline_pp_ingest_watch; no cron).

Loops (threads, one process):
  watch   every POLL_S (+- jitter): list every watched channel, queue new uploads
  fetch   every 10 s: probe due videos, store captions (yt-dlp gate: 3 at once, rate-limit breaker)
  mine    every 5 s: mine transcribed videos (3 videos at once; their windows share one executor whose real
          concurrency is bounded per back-end and globally by providers.Router), append moments, mark mined
  health  every 60 s: Heimdall spend meter (every 10 min), live numbers (ingest/live.json), the daily coverage check
  hook    every 5 s (ruling 80): the HOOK PASS, a second mining question over the same windows (mine.HOOK_PROMPT),
          on mined videos published in the last 12 h, newest first (2 videos at once): the current window's backfill
          at start, then every new upload once its moment pass is done; its rows are moments with role_hint "hook"
  purge   every purge.json every_s (600 s; ruling 77, no cron): media of videos published more than 12 h ago is
          deleted from the targets purge.json names, never a delivered video's (purge.py); the ledger keeps every row
Nothing is dropped (integrator B2; orchestrator 05:30 "if both are down, queue the videos and mine later"):
  - a pass whose failed windows found every back-end down, refusing or skipped (frozen, disabled, budget, circuit
    open) is an OUTAGE: the video waits (mine_waiting) and is retried every MINE_RETRY_S without using a try, for as
    long as the outage lasts;
  - a pass whose back-ends answered and were REJECTED for some window (invalid, refused, empty) uses a try; after
    MINE_CONTENT_PASSES the good windows' moments go to the ledger and the video is mined_partial, retried every
    MINE_PARTIAL_RETRY_S until MINE_HORIZON_S after publish, and never counted as mined (coverage, stats).
Validated replies are cached, so a retry or a restart re-asks only what failed. One service per store (an flock on
<store>/ingest/service.lock): a second `run` or `once` on the same store is refused. Stop with SIGINT / SIGTERM.
"""
import fcntl
import json
import os
import random
import signal
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from . import config, coverage, fetch, ledger, mine, providers, purge, spend, stats, watch
from . import queue as Q
from .contract import ContractUnavailable

MINE_RETRY_S = 600             # a pass with failed windows (an outage, or a rejected pass under the limit) waits this
MINE_CONTENT_PASSES = 3        # passes with REJECTED windows before the good windows' moments go to the ledger
MINE_PARTIAL_RETRY_S = 6 * 3600
MINE_HORIZON_S = 72 * 3600     # a partial video is retried until 72 h after publish (the watcher's backfill horizon)
COVERAGE_HOUR_UTC = 11         # 06:00 ET
COVERAGE_RETRY_S = 3600        # a report with an unmeasured channel is tried again (the same day) after this
OUTAGE_NOTICE_S = 1800         # videos waiting on an outage this long: one line at the top of STATE (a NOTIFY)
IDLE_RELEASE_S = 120           # no mining due this long: the local model (if any) leaves GPU0 (B3; c2: no thrash)
PURGE_NOTICE_S = 1800          # the purge unable to run safely this long: one line at the top of STATE (ruling 77)
HOOK_HORIZON_S = config.EXPIRY_H * 3600   # ruling 80: the hook pass runs on videos whose moments are still usable
HOOK_VIDEOS = 2                # videos in their hook pass at once
HOOK_WINDOWS = 4               # hook windows in flight at once, all hook passes together: the moment passes of new
                               # uploads keep the rest of the back-end's slots (audit r80 c1, glm: no starvation)
HOOK_RETRY_S = 600             # a hook pass with failed windows is tried again (stored replies make it cheap)
HOOK_TRIES = 3                 # passes with REJECTED windows before the hooks of the good windows are written


class ServiceBusy(RuntimeError):
    """Another pp-ingest service holds this store."""


class Service:
    def __init__(self, providers_path=None, log=None, clock=time.time, backends=None, gate=None,
                 keyring=None, sleep=time.sleep):
        self.p = config.paths()                         # the store transcript_store is bound to (config.ts)
        for k in ("ingest", "moments", "replies", "replies_log", "coverage", "work", "transcripts", "purge"):
            os.makedirs(self.p[k], exist_ok=True)
        self._hold_store()                              # one service per store, before anything is recovered
        config.ts()                                     # binds transcript_store to this store, or StoreGuard
        self.clock = clock
        self.log = log or self._log
        self._log_path = os.path.join(self.p["ingest"], "logs", "service.log")
        os.makedirs(os.path.dirname(self._log_path), exist_ok=True)
        self.q = Q.Queue(self.p["queue"], clock=clock)
        self.gate = gate or watch.YouTubeGate(clock=clock)
        self.providers_path = providers_path
        self.cfg = providers.load_config(providers_path)
        self.spendbook = providers.SpendBook(loader=self.q.spend_by_day, clock=clock)
        self._rlog_lock = threading.Lock()
        self.overrides = providers.Overrides(os.path.join(self.p["ingest"], "overrides.json"),
                                             on_change=self._override_change)
        self.router = providers.Router(self.cfg, keyring=keyring, spend=self.spendbook,
                                       on_attempt=self._on_attempt, cache_dir=self.p["replies"], clock=clock,
                                       sleep=sleep, backends=backends, overrides=self.overrides)
        mc = self.cfg["spend_meter"]
        self.meter = spend.CreditMeter(mc, self.router.backends[mc["backend"]], clock=clock,
                                       on_change=self._meter_change)
        self.router.meter = self.meter
        self.executor = ThreadPoolExecutor(max_workers=int(self.cfg["global"]["max_inflight"]),
                                           thread_name_prefix="win")
        self.videos = ThreadPoolExecutor(max_workers=3, thread_name_prefix="vid")
        self.hooks = ThreadPoolExecutor(max_workers=HOOK_VIDEOS, thread_name_prefix="hook")
        self.hook_windows = ThreadPoolExecutor(max_workers=HOOK_WINDOWS, thread_name_prefix="hookwin")
        self.inflight, self.hook_inflight = set(), set()
        self.ilock, self.hlock = threading.Lock(), threading.Lock()
        self.wlock = threading.Lock()                   # every ledger append of this service (carry_forward + append)
        self.stop = threading.Event()
        self.rss_mode, self.rss_checked = False, 0.0
        self.cycle = None
        self.last_measure = 0.0
        if ledger.seal(self.p["ledger"]):
            self.q.event("ledger_sealed", None, None, path=self.p["ledger"])
        self.q.recover()
        try:
            self.purge_spec, self.purge_error = purge.load_spec(), None
        except Exception as e:                          # a refused spec deletes nothing, and says so every pass
            self.purge_spec, self.purge_error = None, f"{type(e).__name__}: {e}"

    def _hold_store(self):
        path = os.path.join(self.p["ingest"], "service.lock")
        f = open(path, "a+")
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            f.seek(0)
            who = f.read()[:200].strip()
            f.close()
            raise ServiceBusy(f"another pp-ingest service holds {path} ({who or 'no record'}): one service per store")
        f.seek(0)
        f.truncate()
        f.write(json.dumps({"pid": os.getpid(), "since": config.iso()}))
        f.flush()
        self._store_lock = f

    def close(self):
        """Release the executors and the store (tests, `once`)."""
        self.videos.shutdown(wait=True)
        self.executor.shutdown(wait=True)
        self.router.release()
        f, self._store_lock = getattr(self, "_store_lock", None), None
        if f is not None:
            f.close()

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
        refused = [bid for bid, o in (new or {}).items() if isinstance(o, dict) and o.get("base_url") and
                   not providers.override_allowed(o["base_url"], (self.cfg["backends"].get(bid) or {}).get("base_url"))]
        self.q.event("overrides", None, None, old=old, new=new, refused=refused)
        self.log(f"runtime overrides changed: {old} -> {new}" +
                 (f"; REFUSED (only this machine or the configured host): {refused}" if refused else ""))

    def _meter_change(self, state, snap):
        try:
            spend.write_state_notice(state, snap, notify_path=self.p["notify"], label=self.meter.label)
        except OSError as e:
            self.log(f"STATE notice not written: {e}")
        self.q.event("spend_meter", None, None, state=state, **snap)
        self.log(f"spend meter ({self.meter.label}): {state} {snap}")

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
            except BaseException as e:                    # never renamed; the video is not left `probing` (glm C8)
                self.q.set_state(v["video_id"], Q.PROBE_RETRY, next_at=self.clock() + 900,
                                 reason=f"fetch stopped: {type(e).__name__}: {e}"[:300])
                self.q.event("fetch_stop", v["video_id"], v["channel_id"], error=traceback.format_exc()[-2000:])
                raise
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
            cost = self.q.rows("SELECT SUM(COALESCE(cost_usd,0)) AS usd FROM calls WHERE video_id=? AND "
                               "COALESCE(role, 'mine')='mine'", (vid,))[0]["usd"]
            self._settle(v, chan, lines, rep, cost, t0)
        except ContractUnavailable as e:
            self.q.set_state(vid, Q.MINE_WAIT, next_at=self.clock() + MINE_RETRY_S, reason=f"contract unavailable: {e}")
            self.log(f"mine {vid}: contract unavailable: {e}")
        except Exception as e:
            self.q.set_state(vid, Q.MINE_WAIT, next_at=self.clock() + MINE_RETRY_S,
                             reason=f"mining crashed: {type(e).__name__}: {e}"[:300])
            self.q.event("mine_crash", vid, v.get("channel_id"), error=traceback.format_exc()[-2000:])
            self.log(f"mine {vid}: crashed {type(e).__name__}: {e}")
        except BaseException as e:                        # e.g. a GPU0 stop: never renamed, but the video is not
            self.q.set_state(vid, Q.MINE_WAIT, next_at=self.clock() + MINE_RETRY_S,      # left claimed
                             reason=f"mining stopped: {type(e).__name__}: {e}"[:300])
            self.q.event("mine_stop", vid, v.get("channel_id"), error=traceback.format_exc()[-2000:])
            self.log(f"mine {vid}: stopped {type(e).__name__}: {e}")
            raise
        finally:
            with self.ilock:
                self.inflight.discard(vid)

    def _append(self, v, lines):
        """Every ledger append of the service, under one lock: each line carries the flags (and the hook hint) of the
        video's earlier lines for the same moment (ledger.carry_forward), so a later pass (the hook pass, a re-mine)
        never drops what an earlier one flagged; the read and the append are one step for this process (ruling 80)."""
        if not lines:
            return 0
        since = datetime.fromtimestamp(float(v.get("discovered_ts") or self.clock()) - 86400, timezone.utc)
        with self.wlock:
            ledger.carry_forward(lines, ledger.video_lines(self.p["ledger"], v["video_id"], since))
            return ledger.append(self.p["ledger"], lines, stamp=config.iso)

    def _ledger_count(self, v):
        """Distinct moment ids of the video in the ledger, read from a day before its discovery (its lines cannot be
        older): the count a partial history leaves, never the last pass's alone (freeze audit c2)."""
        since = datetime.fromtimestamp(float(v.get("discovered_ts") or self.clock()) - 86400, timezone.utc)
        return len(ledger.video_moment_ids(self.p["ledger"], v["video_id"], since))

    def _settle(self, v, chan, lines, rep, cost, t0):
        """The video's state after one mining pass (see the module docstring)."""
        vid, now = v["video_id"], self.clock()
        failed = rep["failed"]
        rejected = [f for f in failed if not f["outage"]]
        passes = int(v.get("mine_tries") or 0) + (1 if rejected else 0)
        was_partial = v.get("state") == Q.MINED_PARTIAL
        common = dict(miners=json.dumps(rep["miners"]), windows=rep["windows"], windows_screened=rep["screened"],
                      windows_failed=len(failed), mine_cost_usd=cost, mine_tries=passes)
        what = (f"{len(lines)} moments, windows {rep['windows']} (screened {rep['screened']}, failed {len(failed)}: "
                f"{len(rejected)} rejected, {len(failed) - len(rejected)} outage), miners {rep['miners']}, "
                f"${(cost or 0):.4f}, {now - t0:.0f} s")
        if not failed:
            self._append(v, lines)                        # a partial video's earlier lines appear again: the latest
                                                          # wins, carrying every earlier flag (ruling 80)
            n = self._ledger_count(v) if (was_partial or v.get("moments") is not None) else len(lines)
            self.q.set_state(vid, Q.MINED, next_at=now + 10 ** 9, moments=n, mined_at=config.iso(),
                             mined_ts=now, reason=None, **common)
            self.log(f"mine {vid} ({chan.get('display_name')}): {what}")
            return
        why = json.dumps(failed[0]["tried"])[:300]
        if was_partial or (rejected and passes >= MINE_CONTENT_PASSES):
            if lines:                                     # every pass that mined windows: its lines, the latest win
                self._append(v, lines)                    # (freeze audit c1, glm C2), carrying earlier flags
            moments = self._ledger_count(v)               # the video's distinct moments in the ledger (c2 consensus)
            pub = v.get("published_ts") or v.get("discovered_ts") or now
            nxt = now + MINE_PARTIAL_RETRY_S if now < float(pub) + MINE_HORIZON_S else now + 10 ** 9
            self.q.set_state(vid, Q.MINED_PARTIAL, next_at=nxt, moments=moments, mined_at=config.iso(),
                             mined_ts=now, reason=f"{len(failed)} window(s) not mined ({len(rejected)} rejected on every "
                             f"back-end after {passes} passes): retried every {MINE_PARTIAL_RETRY_S // 3600} h until "
                             f"{MINE_HORIZON_S // 3600} h after publish; {why}", **common)
            self.log(f"mine {vid} ({chan.get('display_name')}): PARTIAL {what}")
            return
        if rejected:
            reason = (f"{len(rejected)} window(s) rejected on every back-end (pass {passes} of {MINE_CONTENT_PASSES})"
                      f"{' and ' + str(len(failed) - len(rejected)) + ' in an outage' if len(failed) > len(rejected) else ''}"
                      f": retry in {MINE_RETRY_S // 60} min; {why}")
        else:
            reason = (f"OUTAGE: every back-end down, refusing or skipped for {len(failed)} window(s); waiting, no try "
                      f"used (retry in {MINE_RETRY_S // 60} min); {why}")
        self.q.set_state(vid, Q.MINE_WAIT, next_at=now + MINE_RETRY_S, reason=reason[:600], **common)
        self.log(f"mine {vid} ({chan.get('display_name')}): waiting: {what}")

    def hook_video(self, v):
        """RULING 80: the hook pass on one mined video: the hook question over the same windows; its rows (moments
        with role_hint "hook", 4-14 s) go to the ledger with every earlier flag carried. A pass with failed windows is
        retried (an outage uses no try); after HOOK_TRIES passes with rejected windows the good windows' hooks are
        written. Videos published more than 12 h ago are never hook-mined: their moments are expired."""
        vid, t0 = v["video_id"], self.clock()
        try:
            ts = config.ts()
            rec = ts.canonical_transcript(vid)
            with open(os.path.join(ts._vdir(vid), "meta.json")) as f:
                meta = json.load(f)
            reg, chans = watch.registry()
            chan = next((c for c in chans if c["channel_id"] == v["channel_id"]), None)
            optout, oerr = watch.optouts()
            if oerr:
                self.q.set_hook(vid, hook_next_ts=self.clock() + HOOK_RETRY_S, hook_note=f"opt-out list: {oerr}"[:300])
                return
            if chan is None or v["channel_id"] in optout:
                self.q.set_hook(vid, hook_ts=self.clock(), hook_rows=0, hook_note="channel opted out or not watched")
                return
            src = {"discovered_via": v.get("discovered_via"), "live_status": v.get("live_status"),
                   "media_type": v.get("media_type"), "published_at_source": v.get("published_source"),
                   "duplicate_of": v.get("duplicate_of"), "canonical_url": ts.canonical_url(vid)}
            lines, rep = mine.mine_video(self.router, self.hook_windows, rec, meta, chan, reg,
                                         datetime.now(timezone.utc), self.cycle, extra_source=src, kind="hook")
            cost = self.q.rows("SELECT SUM(COALESCE(cost_usd,0)) AS usd FROM calls WHERE video_id=? AND role='hook'",
                               (vid,))[0]["usd"] or 0.0
            failed = rep["failed"]
            rejected = [f for f in failed if not f["outage"]]
            tries = int(v.get("hook_tries") or 0) + (1 if rejected else 0)
            what = (f"{len(lines)} hook rows, windows {rep['windows']} (screened {rep['screened']}, failed "
                    f"{len(failed)}: {len(rejected)} rejected), dropped {rep['dropped'] or 0}"
                    f"{' ' + str(rep.get('dropped_s')) if rep.get('dropped_s') else ''}, ${cost:.4f} for the "
                    f"video's hook passes so far, {self.clock() - t0:.0f} s")
            if failed and tries < HOOK_TRIES:
                self.q.set_hook(vid, hook_next_ts=self.clock() + HOOK_RETRY_S, hook_tries=tries, hook_cost_usd=cost,
                                hook_note=("OUTAGE: " if not rejected else "") + f"{len(failed)} window(s) failed; "
                                f"retry in {HOOK_RETRY_S // 60} min: {json.dumps(failed[0]['tried'])[:200]}")
                self.log(f"hooks {vid} ({(chan or {}).get('display_name')}): waiting: {what}")
                return
            self._append(v, lines)
            self.q.set_hook(vid, hook_ts=self.clock(), hook_rows=len(lines), hook_cost_usd=cost, hook_tries=tries,
                            hook_next_ts=None, hook_note=(f"{len(failed)} window(s) failed after {tries} passes"
                                                          if failed else None))
            self.q.event("hooks", vid, v.get("channel_id"), rows=len(lines), windows=rep["windows"],
                         screened=rep["screened"], failed=len(failed), dropped=rep["dropped"], cost=cost)
            self.log(f"hooks {vid} ({chan.get('display_name')}): {what}")
        except ContractUnavailable as e:
            self.q.set_hook(vid, hook_next_ts=self.clock() + HOOK_RETRY_S, hook_note=f"contract unavailable: {e}"[:300])
            self.log(f"hooks {vid}: contract unavailable: {e}")
        except Exception as e:
            self.q.set_hook(vid, hook_next_ts=self.clock() + HOOK_RETRY_S,
                            hook_note=f"hook pass crashed: {type(e).__name__}: {e}"[:300])
            self.q.event("hook_crash", vid, v.get("channel_id"), error=traceback.format_exc()[-2000:])
            self.log(f"hooks {vid}: crashed {type(e).__name__}: {e}")
        finally:
            with self.hlock:
                self.hook_inflight.discard(vid)

    def hook_once(self, wait=False):
        """Ruling 80: start the hook pass on the newest due videos (mined, published in the last 12 h)."""
        started = []
        with self.hlock:
            free = HOOK_VIDEOS - len(self.hook_inflight)
        if free <= 0:
            return 0
        for v in self.q.hook_due(HOOK_HORIZON_S, HOOK_VIDEOS * 2):
            with self.hlock:
                if v["video_id"] in self.hook_inflight or len(self.hook_inflight) >= HOOK_VIDEOS:
                    continue
                self.hook_inflight.add(v["video_id"])
            try:
                started.append(self.hooks.submit(self.hook_video, v))
            except RuntimeError:                          # the pool is shut down (the service is stopping): the video
                with self.hlock:                          # is not left marked in flight (audit r80 c2, glm / muse P2)
                    self.hook_inflight.discard(v["video_id"])
                raise
        if wait:
            for f in started:
                f.result()
        return len(started)

    def mine_once(self, wait=False):
        started = []
        with self.ilock:
            free = 3 - len(self.inflight)
        if free <= 0:
            return 0
        if free == 3 and not self.q.due(Q.MINE_DUE, 1):
            if self.clock() - getattr(self, "_last_mining", 0.0) >= IDLE_RELEASE_S:
                self.router.release()                     # idle: the local model (if any) leaves GPU0 (B3)
            return 0
        self._last_mining = self.clock()
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
        if now - self.last_measure >= float(self.cfg["spend_meter"]["measure_every_s"]):
            self.meter.measure()
            self.last_measure = now
        s = stats.write_live(self.q, self.p["live"], meter=self.meter, router=self.router)
        self._outage_notice(now)
        day = config.iso()[:10]
        hour = datetime.now(timezone.utc).hour
        if force_coverage or (hour >= COVERAGE_HOUR_UTC and self.q.kv_get("coverage_day") != day and
                              now >= float(self.q.kv_get("coverage_next_try") or 0)):
            rep = coverage.check(self.q, self.gate, rss=self.rss_mode)
            path = coverage.write(rep, self.p["coverage"])
            if rep["measured"]:
                self.q.kv_set("coverage_day", day)
            else:                                         # a channel's listing failed: the day's report is tried
                self.q.kv_set("coverage_next_try", str(now + COVERAGE_RETRY_S))   # again (muse P1)
            self.q.event("coverage", None, None, path=path, coverage=rep["coverage"], eligible=rep["eligible"],
                         mined=rep["mined"], unmeasured=len(rep["unmeasured_channels"]))
            self.log(f"coverage: {rep['mined']}/{rep['eligible']} mined, {len(rep['missed'])} listed with reasons, "
                     f"{len(rep['unmeasured_channels'])} channels unmeasured -> {path}")
        return s

    def _purge_blocked(self, why):
        """A purge that cannot run safely: once it has lasted PURGE_NOTICE_S, a line at the top of STATE (audit r77
        c1, muse P1); cleared by the first pass that runs."""
        now = self.clock()
        if why is None:
            if self.q.kv_get("purge_blocked_since"):
                self.q.kv_set("purge_blocked_since", "")
                spend.write_purge_notice(None, None, notify_path=self.p["notify"])
            return
        since = float(self.q.kv_get("purge_blocked_since") or 0) or now
        self.q.kv_set("purge_blocked_since", str(since))
        if now - since >= PURGE_NOTICE_S:
            try:                                          # a STATE file that cannot be written: logged, never the
                spend.write_purge_notice(why[:300], datetime.fromtimestamp(since, timezone.utc).strftime(   # pass's
                    "%Y-%m-%dT%H:%M:%SZ"), notify_path=self.p["notify"])                               # bookkeeping
            except OSError as e:
                self.log(f"purge: the STATE notice could not be written: {type(e).__name__}: {e}")

    def purge_once(self, dry_run=False):
        """Ruling 77: one pass of the rolling purge of expired media (purge.py), in this process's own loop."""
        if self.purge_spec is None:
            self.log(f"purge: not run, its spec is refused ({self.purge_error}); nothing deleted")
            self._purge_blocked(f"its spec is refused ({self.purge_error})")
            return None
        rep = purge.run_pass(self.purge_spec, q=self.q, dry_run=dry_run, log_dir=self.p["purge"])
        if not dry_run:
            self._purge_blocked(rep.get("refused"))
        if not dry_run:
            total = float(self.q.kv_get("purge_freed_total") or 0) + rep.get("freed_bytes", 0)
            self.q.kv_set("purge_freed_total", str(total))
            self.q.kv_set("purge_last", json.dumps({
                "at": rep["at"], "freed_bytes": rep.get("freed_bytes", 0), "refused": rep.get("refused"),
                "deleted": rep["deleted"], "kept": rep["kept"], "delivered_videos": rep["delivered_videos"],
                "seconds": rep.get("seconds")}))
            self.q.event("purge", None, None, freed=rep.get("freed_bytes", 0), refused=rep.get("refused"))
        if rep.get("freed_bytes") or rep.get("refused") or dry_run:
            self.log(purge.summary(rep))
        return rep

    def _outage_notice(self, now):
        """Videos waiting on an outage of every mine back-end for over OUTAGE_NOTICE_S: one line at the top of STATE,
        removed when none waits (orchestrator 05:30: they are mined later; freeze audit c1, muse: visible without
        polling)."""
        n = self.q.rows("SELECT COUNT(*) AS n FROM videos WHERE state=? AND reason LIKE 'OUTAGE%'",
                        (Q.MINE_WAIT,))[0]["n"]
        since = self.q.kv_get("outage_since")
        if n and not since:
            self.q.kv_set("outage_since", str(now))
            self.q.event("outage", None, None, waiting=n)
        elif not n and since:
            self.q.kv_set("outage_since", "")
            self.q.event("outage_over", None, None, lasted_s=round(now - float(since)))
            self.log(f"outage over after {now - float(since):.0f} s: every waiting video is being mined")
        noticed = self.q.kv_get("outage_noticed") == "1"
        if n and since and now - float(since) >= OUTAGE_NOTICE_S:
            line = spend.write_outage_notice(n, datetime.fromtimestamp(float(since), timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"), notify_path=self.p["notify"])
            if not noticed:
                self.log(line)
                self.q.kv_set("outage_noticed", "1")
        elif not n and noticed:
            spend.write_outage_notice(0, None, notify_path=self.p["notify"])
            self.q.kv_set("outage_noticed", "0")

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
        return {bid: {"model": b.model, "vendor": self.router.vendor(bid), "enabled": b.enabled(),
                      "frozen": self.router.frozen(bid), "base": getattr(b, "base", None)}
                for bid, b in self.router.backends.items() if bid in self.router.chain("mine")}

    def run(self):
        fz = sorted(providers.frozen_vendors(self.cfg))
        self.log(f"pp-ingest service: store {self.p['root']}, mine chain {self.router.chain('mine')} (callable now: "
                 f"{self.router.effective('mine')}), spend freeze {fz}, back-ends {self.describe()}")
        self.q.event("start", None, None, pid=os.getpid(), chain=self.router.chain("mine"),
                     effective=self.router.effective("mine"), spend_freeze=fz, backends=self.describe())
        if len(self.router.effective("mine")) < 2:
            self.log(f"WARNING: {len(self.router.effective('mine'))} callable mine back-end(s): when it is down the "
                     "videos wait in the queue and are mined when it returns (orchestrator 05:30: never a paid frontier "
                     "fallback); nothing is dropped")
        self.meter.measure()
        self.last_measure = self.clock()
        threads = [threading.Thread(target=self._loop, args=a, daemon=True, name=a[0]) for a in (
            ("watch", self.watch_once, config.POLL_S, config.POLL_JITTER_S),
            ("fetch", self.fetch_once, 10.0),
            ("mine", self.mine_once, 5.0),
            ("hook", self.hook_once, 5.0),
            ("health", self.health_once, 60.0),
            ("purge", self.purge_once, float((self.purge_spec or {}).get("every_s", 600))))]
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
        self.q.event("stop", None, None, pid=os.getpid())
        self.close()
        self.log("stopped")
