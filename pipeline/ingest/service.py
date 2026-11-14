"""pipeline/ingest/service.py: the long-running watcher (tmux pipeline_pp_ingest_watch; no cron).

Loops (threads, one process):
  watch   every POLL_S (+- jitter): list every watched channel, queue new uploads
  fetch   every 10 s: probe due videos, store captions (yt-dlp gate: 3 at once, rate-limit breaker)
  mine    every 5 s: mine transcribed videos (3 videos at once; their windows share one executor whose real
          concurrency is bounded per back-end and globally by providers.Router), append moments, mark mined.
          Ruling 98: while the shared signal's paid route is open (Heimdall down 20 min), only NEW uploads (the last
          6 h; conversations first, then newest) are mined, on the paid role under its daily cap; when the signal is
          back, the paid route's videos still inside 12 h are mined again on the mine role (flags of both kept)
  health  every 60 s: Heimdall spend meter (every 10 min), live numbers (ingest/live.json), the daily coverage check
  hook    every 5 s (ruling 80): the HOOK PASS, a second mining question over the same windows (mine.HOOK_PROMPT),
          on mined videos published in the last 12 h, newest first (2 videos at once): the current window's backfill
          at start, then every new upload once its moment pass is done; its rows are moments with role_hint "hook";
          in a conversation episode up to 5 a window, plus the spotlight question's rows (role_hint "spotlight",
          12-35 s: the orchestrator's 08:15 ruling 2, Nov 14)
  check   every 30 s (ruling 40 P1): the second model's narrow question on every imperative / single_source_breaking
          flag of a moment still usable (published in the last 12 h, newest first) that has no answer that counts; the
          answers go into a new line of the moment (risk_checks); the adapter releases such a flag only on "no". The
          checker is calibrated daily inside this loop (16 short questions per back-end, the loop waits for it), and
          at a start unless the last live calibration is under a day old and passed (then its result is kept: no
          quote asked), every question put to the model live, never answered from a stored reply (F1, Nov 14); a
          question not answered is asked again (flagcheck.CALIBRATION_ROUNDS); when no back-end passed and one still
          could (a question unanswered, none wrong; or the calibration crashed) the calibration is tried again after
          CHECK_RETRY_S, not a day later, the wait doubling while it keeps failing (up to a day)
  purge   every purge.json every_s (600 s; ruling 77, no cron): media of videos published more than 12 h ago is
          deleted from the targets purge.json names, never a delivered video's (purge.py); the ledger keeps every row
  signal  every 5 s (ruling 87, when providers.json has down_signal): the ONE shared 'Heimdall down' signal
          (downsignal.py over pp-selectid pipeline/heimdall_health.py): every real Heimdall call noted, the 15-minute
          rule on the clock, the probe while one is due, every switch on STATE line 1. The miner's Plan B under the
          spend freeze is queue and wait: nothing here changes what the miner calls
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
from datetime import datetime, timedelta, timezone

from . import config, coverage, downsignal, fetch, flagcheck, ledger, mine, providers, purge, spend, stats, watch
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
CHECK_EVERY_S = 30             # ruling 40 P1: the second-model check loop
CHECK_ROWS = 8                 # rows started per loop
CHECK_INFLIGHT = 4             # rows being checked at once (their questions are short; Heimdall stays under ~20)
CHECK_RETRY_S = 600            # a question nobody answered is asked again after this (the flag stands meanwhile)
CHECK_RECALIBRATE_S = 86400    # the checker is re-calibrated on the known quotes once a day (and at a start whose
                               # last live calibration is a day old or failed: _reuse_calibration),
                               # asked live (F1); after CHECK_RETRY_S instead when none passed and one still could,
                               # the wait doubling while it keeps failing (up to a day)


class ServiceBusy(RuntimeError):
    """Another pp-ingest service holds this store."""


def check_roles(cfg):
    """Every mining question (mine.KINDS) and the second-model check (flagcheck.ROLE) need their role in the provider
    config; a missing one stops the start (the 08:15 ruling 2 added the spotlight question: asked without its role,
    every pass of it would crash; audit hk3 c1, glm: the check's calibration would crash-loop the same way)."""
    missing = sorted(({k["role"] for k in mine.KINDS.values()} | {flagcheck.ROLE}) - set(cfg["roles"]))
    if missing:
        raise ValueError(f"providers.json has no role {missing}: every mining question and the second-model check "
                         "need one (mine.KINDS, flagcheck.ROLE)")


class Service:
    def __init__(self, providers_path=None, log=None, clock=time.time, backends=None, gate=None,
                 keyring=None, sleep=time.sleep, signal_module=None, signal_state=None):
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
        check_roles(self.cfg)
        self.spendbook = providers.SpendBook(loader=self.q.spend_by_day, clock=clock)
        self._rlog_lock = threading.Lock()
        self.overrides = providers.Overrides(os.path.join(self.p["ingest"], "overrides.json"),
                                             on_change=self._override_change)
        self.hsig = None                                # ruling 87 (set below; _on_attempt reads it)
        self.router = providers.Router(self.cfg, keyring=keyring, spend=self.spendbook,
                                       on_attempt=self._on_attempt, cache_dir=self.p["replies"], clock=clock,
                                       sleep=sleep, backends=backends, overrides=self.overrides,
                                       role_spend=self.q.role_spend_since)         # ruling 98: the route's cap
        if self.cfg.get("down_signal"):
            self.hsig = downsignal.DownSignal(self.cfg, self.router, self.overrides, self.q, self.p, clock=clock,
                                              log=self.log, module_path=signal_module, state_path=signal_state)
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
        self._conv = {}                                 # ruling 98: video id -> a conversation (caption turns)
        self.ilock, self.hlock = threading.Lock(), threading.Lock()
        self.wlock = threading.Lock()                   # every ledger append of this service (carry_forward + append)
        self.checks = ThreadPoolExecutor(max_workers=CHECK_INFLIGHT, thread_name_prefix="check")
        self.check_inflight, self.check_next, self.clock_lock = set(), {}, threading.Lock()
        self.check_allowed, self.check_calibrated = None, 0.0
        self.check_recal_s = CHECK_RECALIBRATE_S        # the wait before the next calibration (set by each one)
        self._reuse_tried = False                       # the start's one look at the stored live calibration
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
        if self.hsig is not None:
            self.hsig.noted(rec)                        # O(1); the signal thread writes the shared file
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

    def mine_video(self, v, role=None):
        vid, route = v["video_id"], role or "mine"
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
                                         datetime.now(timezone.utc), self.cycle, extra_source=src, role=route)
            cost = self.q.rows("SELECT SUM(COALESCE(cost_usd,0)) AS usd FROM calls WHERE video_id=? AND "
                               "COALESCE(role, 'mine')=?", (vid, route))[0]["usd"]
            self._settle(v, chan, lines, rep, cost, t0, route=route)
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

    def _settle(self, v, chan, lines, rep, cost, t0, route="mine"):
        """The video's state after one mining pass (see the module docstring); route: the role that mined it."""
        vid, now = v["video_id"], self.clock()
        failed = rep["failed"]
        rejected = [f for f in failed if not f["outage"]]
        passes = int(v.get("mine_tries") or 0) + (1 if rejected else 0)
        was_partial = v.get("state") == Q.MINED_PARTIAL
        common = dict(miners=json.dumps(rep["miners"]), windows=rep["windows"], windows_screened=rep["screened"],
                      windows_failed=len(failed), mine_cost_usd=cost, mine_tries=passes, mine_route=route)
        if route == (self.cfg.get("paid_route") or {}).get("role"):
            common["recheck_ts"] = None                   # mined on the paid route again: its Heimdall re-mine is due
                                                          # again once the signal is back (audit r98 c1, muse)
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
        with role_hint "hook", 4-14 s) go to the ledger with every earlier flag carried. The 08:15 ruling 2 (Nov 14,
        ruling 92 (b) + (c)): in a conversation episode (mine.is_conversation) the hook question allows up to 5 a
        window and the spotlight question is asked too (rows with role_hint "spotlight", 12-35 s). A pass with failed
        windows (either question) is retried (an outage uses no try); after HOOK_TRIES passes with rejected windows the
        good windows' rows are written. Videos published more than 12 h ago are never hook-mined: their moments are
        expired."""
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
            t_hook = self.clock() - t0
            spot, srep, scrash = [], None, None    # the 08:15 ruling 2 (c): the spotlight question, conversations only
            ep = rep.get("episode") or {}
            if mine.is_conversation(ep):
                try:
                    spot, srep = mine.mine_video(self.router, self.hook_windows, rec, meta, chan, reg,
                                                 datetime.now(timezone.utc), self.cycle, extra_source=src,
                                                 kind="spotlight")
                except ContractUnavailable:
                    raise                          # the contract: the whole pass waits, as before
                except Exception as e:             # audit hk3 c2 (all three): a spotlight question that CRASHES never
                    scrash = f"{type(e).__name__}: {e}"[:300]   # holds back the hook rows: they are written below,
                    self.q.event("spotlight_crash", vid, v.get("channel_id"),   # the pass is marked, and
                                 error=traceback.format_exc()[-2000:])        # hooks --rerun asks it again
            t_spot = self.clock() - t0 - t_hook
            cost = self.q.rows("SELECT SUM(COALESCE(cost_usd,0)) AS usd FROM calls WHERE video_id=? AND role IN "
                               "('hook', 'spotlight')", (vid,))[0]["usd"] or 0.0
            failed = rep["failed"] + (srep["failed"] if srep else [])
            rejected = [f for f in failed if not f["outage"]]
            tries = int(v.get("hook_tries") or 0) + (1 if rejected else 0)
            split = (f"hook {len(rep['failed'])}, spotlight {len(srep['failed'])}" if srep is not None else
                     f"hook {len(rep['failed'])}")              # which question failed (audit hk3 c1, glm)
            sp = (f"{len(spot)} spotlight rows (dropped {srep['dropped'] or 0})" if srep is not None else
                  f"the spotlight question CRASHED ({scrash}): the hook rows are written" if scrash else
                  f"no spotlight question (a marked solo episode: {ep.get('speaker_markers')} markers, "
                  f"{ep.get('turns_per_min')} turns / min)")
            what = (f"{len(lines)} hook rows (up to {rep['max_n']} a window), {sp}, windows {rep['windows']} "
                    f"(screened {rep['screened']}, failed {len(failed)}: {len(rejected)} rejected; {split}), "
                    f"dropped {rep['dropped'] or 0}{' ' + str(rep.get('dropped_s')) if rep.get('dropped_s') else ''}, "
                    f"${cost:.4f} for the video's hook passes so far, {self.clock() - t0:.0f} s (hook question "
                    f"{t_hook:.0f} s, spotlight {t_spot:.0f} s)")
            if failed and tries < HOOK_TRIES:
                self.q.set_hook(vid, hook_next_ts=self.clock() + HOOK_RETRY_S, hook_tries=tries, hook_cost_usd=cost,
                                hook_note=("OUTAGE: " if not rejected else "") + f"{len(failed)} window(s) failed "
                                f"({split}); retry in {HOOK_RETRY_S // 60} min: {json.dumps(failed[0]['tried'])[:200]}")
                self.log(f"hooks {vid} ({(chan or {}).get('display_name')}): waiting: {what}")
                return
            self._append(v, lines + spot)
            self.q.set_hook(vid, episode_markers=ep.get("speaker_markers"), episode_tpm=ep.get("turns_per_min"))
            notes = ([f"{len(failed)} window(s) failed after {tries} passes ({split})"] if failed else []) + (
                [f"the spotlight question crashed: {scrash}"] if scrash else [])
            self.q.set_hook(vid, hook_ts=self.clock(), hook_rows=len(lines), hook_cost_usd=cost, hook_tries=tries,
                            hook_version=(f"{mine.HOOK_PROMPT_VERSION} (spotlight crashed)" if scrash else
                                          mine.HOOK_PROMPT_VERSION),       # a crashed spotlight: the suffix makes
                                                                           # --rerun (version <> current) ask again
                            spot_rows=len(spot) if srep is not None else None,
                            hook_next_ts=None, hook_note="; ".join(notes) or None)
            self.q.event("hooks", vid, v.get("channel_id"), rows=len(lines), spotlight_rows=len(spot),
                         conversation=mine.is_conversation(ep), max_n=rep["max_n"],
                         max_n_spotlight=(srep or {}).get("max_n"), windows=rep["windows"],
                         screened=rep["screened"], failed=len(failed), failed_hook=len(rep["failed"]),
                         failed_spotlight=len(srep["failed"]) if srep is not None else None,
                         dropped=rep["dropped"], spotlight_dropped=(srep or {}).get("dropped"),
                         spotlight_crash=scrash, seconds_hook=round(t_hook, 1), seconds_spotlight=round(t_spot, 1),
                         cost=cost)
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

    def check_row(self, l, flags, miner):
        """RULING 40 P1: the second model's question for each flag; the measured answers go into a new line of the
        moment (under the append lock, carrying everything earlier). A question nobody answered is asked again later;
        its flag stands meanwhile (fail closed)."""
        key = l["moment_id"]
        try:
            got = {}
            for f in flags:
                ans = flagcheck.ask(self.router, l, f, miner, allowed=self.check_allowed, sharpened=False)
                rec = flagcheck.record(ans, version=flagcheck.PROMPT_VERSION)
                if rec is not None:
                    got[f] = rec
                elif "no checker" in str(ans.get("unmeasured")):          # never silent (audit r40p1 c2, glm)
                    self.log(f"check {key}: {f} not asked: {ans['unmeasured']}")
            if len(got) < len(flags):
                with self.clock_lock:
                    self.check_next[key] = self.clock() + CHECK_RETRY_S
            if got:
                new = json.loads(json.dumps(l))
                new.setdefault("risk_checks", {}).update(got)
                v = self.q.video(l["video_id"]) or {"video_id": l["video_id"], "discovered_ts": self.clock()}
                self._append(v, [new])
                self.q.event("flagcheck", l["video_id"], l.get("channel_id"), moment_id=key,
                             answers={f: c["answer"] for f, c in got.items()},
                             released=[f for f, c in got.items() if c["answer"] == "no"])
                self.log(f"check {key} ({l.get('channel_name')}): " + ", ".join(
                    f"{f} {c['answer']}" + (" (released: the models disagree)" if c["answer"] == "no" else "")
                    for f, c in got.items()) + (f"; unanswered {sorted(set(flags) - set(got))}" if len(got) <
                                                len(flags) else ""))
        except Exception as e:
            with self.clock_lock:
                self.check_next[key] = self.clock() + CHECK_RETRY_S
            self.q.event("check_crash", l.get("video_id"), l.get("channel_id"), error=traceback.format_exc()[-2000:])
            self.log(f"check {key}: crashed {type(e).__name__}: {e}")
        finally:
            with self.clock_lock:
                self.check_inflight.discard(key)

    def _calibrate_checkers(self):
        """RULING 40 P1's calibration (F1, Nov 14: every quote asked live): sets check_allowed, check_calibrated and
        the wait before the next one (check_recal_s); stores the result (queue kv 'check_calibration', live.json)."""
        asked, t0, crash = config.iso(), self.clock(), None
        try:
            allowed, cal = flagcheck.watcher_checkers(self.router)
        except Exception as e:                   # audit f1 c1 (glm): a calibration that crashes after its live calls
            allowed, cal = [], None              # must not run again every 30 s; nothing measured: nobody answers
            self.q.event("check_calibration_crash", None, None, error=traceback.format_exc()[-2000:])
            crash = f"{type(e).__name__}: {e}"[:300]
        secs = self.clock() - t0
        self.check_allowed, self.check_calibrated = allowed, self.clock()
        # when no back-end passed and one still could (a question unanswered, none answered wrong; the calibration
        # crashed; or no back-end could be called at all, which asks nothing: audit f1 c2, muse), an outage at
        # calibration time must not bar the checkers for a day: tried again after CHECK_RETRY_S, the wait doubling
        # while it keeps failing (a checker that keeps failing costs a few calibrations a day); a pass, or every
        # back-end answering a quote wrong, waits for the daily one
        could = cal is None or not cal or [b for b, c in cal.items() if c["unmeasured"] and not c["wrong"]]
        if allowed or not could:
            self.check_recal_s = CHECK_RECALIBRATE_S
        elif self.check_recal_s >= CHECK_RECALIBRATE_S:
            self.check_recal_s = CHECK_RETRY_S
        else:
            self.check_recal_s = min(CHECK_RECALIBRATE_S, 2 * self.check_recal_s)
        nxt = f"next calibration in {self.check_recal_s:.0f} s"
        if cal is None:
            self.q.kv_set("check_calibration", json.dumps({}))
            self.log(f"check: calibration crashed after {secs:.0f} s: {crash}; every flag stands; {nxt}")
            return
        sha = flagcheck.calibration_sha()                 # what was measured (the reuse gate: audit reuse c2)
        self.q.kv_set("check_calibration", json.dumps({b: dict(
            {k: c[k] for k in ("model", "right", "of", "unmeasured")}, asked_at=asked, seconds=round(secs, 1),
            prompts_sha=sha,
            wrong=[{"flag": w["flag"], "gold": w["gold"], "answer": w["answer"], "text": w["text"][:80]}
                   for w in c["wrong"]]) for b, c in cal.items()}))     # asked_at: the calibration's start
        got = [(b, c["right"], c["of"], c["unmeasured"]) for b, c in cal.items()]
        wrong = [(b, w["flag"], w["gold"], w["answer"]) for b, c in cal.items() for w in c["wrong"]]
        self.log(f"check: calibration (asked live, {secs:.0f} s) {got} (right, answered, unanswered)"
                 + (f"; wrong (back-end, flag, expected, answered) {wrong}" if wrong else "")
                 + f"; allowed to answer: {allowed or 'none (every flag stands)'}; {nxt}")

    def _reuse_calibration(self):
        """At start only: a restart within CHECK_RECALIBRATE_S of the last LIVE calibration keeps its measured result
        instead of asking the 32 quotes again (F1 holds: that result was asked live, with its asked_at; nothing comes
        from the reply cache). Reused only when the stored calibration names exactly the role's callable back-ends with
        their current models, was measured on the same prompts (prompts_sha: flagcheck.calibration_sha, audit reuse
        c2), carries one asked_at (the live calibration's start) that is under a day old, and let at least one
        back-end answer every quote right; anything else (a failed or outage calibration, an old record without
        asked_at or prompts_sha, a changed model) is asked live as before. Because only a passed calibration is
        reused, the wait is reset to the daily one here: an outage calibration's shorter retry (CHECK_RETRY_S) is never
        skipped by a reuse, and relaxing the 'one passed' gate would break that (audit reuse c2, glm). Why (09:16 ET
        Nov 14): each restart's live calibration ended on muse's 502s, and on a quiet watcher that dangling failure
        became a false plan_b 15 minutes later. -> True when reused."""
        try:
            cal = json.loads(self.q.kv_get("check_calibration") or "null")
        except ValueError:
            cal = None
        eff, t, allowed, why = self.router.effective(flagcheck.ROLE), None, [], None
        if not isinstance(cal, dict) or not cal:
            why = "none stored"
        elif set(cal) != set(eff) or not all(isinstance(c, dict) and c.get("model") == self.router.backends[b].model
                                             for b, c in cal.items()):
            why = "its back-ends or models are not the role's now"
        elif any(c.get("prompts_sha") != flagcheck.calibration_sha() for c in cal.values()):
            why = "measured on other prompts, or before they were recorded"
        else:
            asked = {c.get("asked_at") for c in cal.values()}
            t = config.aware(asked.pop()) if len(asked) == 1 else None
            if t is None:
                why = "no single zoned asked_at (a record of the cached era)"
            elif not 0 <= self.clock() - t.timestamp() < CHECK_RECALIBRATE_S:
                why = f"asked {(self.clock() - t.timestamp()) / 3600:.1f} h ago"      # (negative: the clock went back)
            else:
                n = len(flagcheck.watcher_probes())
                allowed = [b for b in eff if cal[b].get("of") == n and cal[b].get("right") == n and
                           not cal[b].get("unmeasured")]
                why = None if allowed else "no back-end passed it"
        if why:                                              # audit reuse c1 (muse): a refusal is said, with its why
            self.log(f"check: the stored calibration is not reused ({why}): asked live now")
            return False
        self.check_allowed, self.check_calibrated, self.check_recal_s = allowed, t.timestamp(), CHECK_RECALIBRATE_S
        self.q.event("check_calibration_reused", None, None, asked_at=t.isoformat(), allowed=allowed)
        self.log(f"check: calibration reused (asked live at {t.isoformat()[:19]}Z, "
                 f"{(self.clock() - t.timestamp()) / 3600:.1f} h ago): allowed to answer: {allowed}; next calibration in "
                 f"{CHECK_RECALIBRATE_S - (self.clock() - t.timestamp()):.0f} s")
        return True

    def check_once(self, wait=False):
        """RULING 40 P1: start the second-model check on the newest still-usable moments whose imperative /
        single_source_breaking flag has no answer that counts. Only back-ends that answer every calibration quote
        right may answer (none: nothing is checked, every flag stands)."""
        if self.check_allowed is None and not self._reuse_tried:
            self._reuse_tried = True                       # at start only: a live calibration under a day old is kept
            self._reuse_calibration()
        if self.check_allowed is None or self.clock() - self.check_calibrated >= self.check_recal_s:
            self._calibrate_checkers()
        if not self.check_allowed:
            return 0
        try:                                              # nothing new in the ledger and no retry due: no re-read
            st = os.stat(self.p["ledger"])                # (audit r40p1 c1, glm)
            seen = (st.st_size, st.st_mtime_ns)
        except OSError:
            seen = None
        with self.clock_lock:
            due = min(self.check_next.values(), default=float("inf"))
        if seen is not None and seen == getattr(self, "_check_seen", None) and self.clock() < due:
            return 0
        now = datetime.now(timezone.utc)
        lines = ledger.read(self.p["ledger"], from_time=now - timedelta(hours=config.EXPIRY_H, days=1))[0]
        latest, miners = {}, {}
        for l in lines:
            latest[l["moment_id"]] = l
            b, m = miners.setdefault(l["video_id"], (set(), set()))
            b.add((l.get("mined") or {}).get("backend"))
            m.add((l.get("mined") or {}).get("model"))
        todo = []
        with self.clock_lock:
            for key, l in latest.items():
                exp = ledger.expiry(l)
                if exp is None or now >= exp or key in self.check_inflight or \
                        self.check_next.get(key, 0) > self.clock():
                    continue
                flags = [f for f in ledger.RELEASE_ON_CHECK if f in l["risk"] and ledger.check_valid(l, f) is None]
                if flags:
                    todo.append((str(l.get("published_at") or ""), key, l, flags))
            todo.sort(key=lambda x: (x[0], x[1]), reverse=True)                       # newest first
            if len(todo) <= CHECK_INFLIGHT - len(self.check_inflight):
                self._check_seen = seen                   # everything due is being started: the next loop may skip
            room = CHECK_INFLIGHT - len(self.check_inflight)
            todo = todo[:max(0, min(CHECK_ROWS, room))]
            for _, key, _, _ in todo:
                self.check_inflight.add(key)
        started = [self.checks.submit(self.check_row, l, flags, miners[l["video_id"]]) for _, _, l, flags in todo]
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
        pr = self.cfg.get("paid_route")
        paid = bool(pr) and self.hsig is not None and self.hsig.paid_open
        if pr and self.hsig is not None and not paid:
            self._queue_rechecks(pr)
        if free == 3 and not self.q.due(Q.MINE_DUE, 1):
            if self.clock() - getattr(self, "_last_mining", 0.0) >= IDLE_RELEASE_S:
                self.router.release()                     # idle: the local model (if any) leaves GPU0 (B3)
            return 0
        self._last_mining = self.clock()
        for v in (self._paid_due(pr, free) if paid else self.q.due(Q.MINE_DUE, free)):
            if not self.q.claim(v["video_id"], Q.MINE_DUE, Q.MINING):
                continue
            with self.ilock:
                self.inflight.add(v["video_id"])
            started.append(self.videos.submit(self.mine_video, v, pr["role"] if paid else None))
        if wait:
            for f in started:
                f.result()
        return len(started)

    def _paid_due(self, pr, limit):
        """Ruling 98, the paid route: only NEW uploads (published inside new_within_s), conversations first (the
        caption turns per minute, ruling 92's measure), then newest; every older video waits for Heimdall (no
        backfill)."""
        now = self.clock()
        vs = [v for v in self.q.due(Q.MINE_DUE, 200) if (v.get("published_ts") or 0) >= now - float(pr["new_within_s"])]
        if len(self._conv) > 5000:
            self._conv.clear()

        def conv(v):
            vid = v["video_id"]
            if vid not in self._conv:
                try:
                    tpm = mine.episode_measure(config.ts().canonical_transcript(vid)).get("turns_per_min")
                except Exception as e:                    # noqa: BLE001 (unmeasured: not a conversation, still mined;
                    tpm = None                            # said once: audit r98 c1)
                    self.log(f"ruling 98: {vid}'s caption turns not measured ({type(e).__name__}: {e}): mined after "
                             "the conversations")
                self._conv[vid] = tpm is not None and tpm >= float(pr["conversation_tpm"])
            return self._conv[vid]
        vs.sort(key=lambda v: (conv(v), v.get("published_ts") or 0), reverse=True)
        return vs[:limit]

    def _queue_rechecks(self, pr):
        """Ruling 98: once the signal is back, each video the paid route mined that is still inside recheck_within_s
        is mined again on the mine role, once; every moment both passes found carries the flags of both
        (ledger.carry_forward), so a flag either model set stands."""
        if not self.hsig.signal_back():
            return
        for v in self.q.recheck_due(pr["role"], float(pr["recheck_within_s"]), limit=20):
            self.q.set_state(v["video_id"], Q.TRANSCRIBED, next_at=self.clock(), recheck_ts=self.clock(),
                             reason=f"ruling 98: mined again on the mine role (its rows came from {pr['role']})")
            self.q.event("recheck_queued", v["video_id"], v.get("channel_id"), route=pr["role"])
            self.log(f"ruling 98: {v['video_id']} queued to be mined again on the mine role")

    # ── health ──

    def health_once(self, force_coverage=False):
        now = self.clock()
        if now - self.last_measure >= float(self.cfg["spend_meter"]["measure_every_s"]):
            self.meter.measure()
            self.last_measure = now
        if self.hsig is not None:
            try:
                self.hsig.check_notice()
            except OSError as e:
                self.log(f"ruling 87: the STATE notice could not be written: {type(e).__name__}: {e}")
        s = stats.write_live(self.q, self.p["live"], meter=self.meter, router=self.router,
                             signal=self.hsig.snapshot() if self.hsig is not None else None)
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
                try:                                      # the notice goes first, then the record (a STATE file
                    spend.write_purge_notice(None, None, notify_path=self.p["notify"])   # that cannot be read keeps
                except OSError as e:                      # both, tried again next pass: audit r87 C1-5)
                    self.log(f"purge: the STATE notice could not be removed: {type(e).__name__}: {e}")
                    return
                self.q.kv_set("purge_blocked_since", "")
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
                "one_copy_per_delivery": rep.get("one_copy_per_delivery"),    # A19 in live.json (audit a19 c2)
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
        try:                                              # a STATE file that cannot be read is never rewritten:
            if n and since and now - float(since) >= OUTAGE_NOTICE_S:      # logged, tried again next minute
                line = spend.write_outage_notice(n, datetime.fromtimestamp(float(since), timezone.utc).strftime(
                    "%Y-%m-%dT%H:%M:%SZ"), notify_path=self.p["notify"])
                if not noticed:
                    self.log(line)
                    self.q.kv_set("outage_noticed", "1")
            elif not n and noticed:
                spend.write_outage_notice(0, None, notify_path=self.p["notify"])
                self.q.kv_set("outage_noticed", "0")
        except OSError as e:
            self.log(f"the outage notice could not be written: {type(e).__name__}: {e}")

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
        if self.hsig is not None:
            sg = self.hsig.snapshot()
            self.log("ruling 87: the shared down signal " + (
                f"wired to {sg['state_file']} (evidence {sg['evidence']}); "
                f"the miner's Plan B: {sg['miner_plan_b']}" if sg["wired"] else f"NOT READ: {sg['not_read']}"))
        if len(self.router.effective("mine")) < 2:
            self.log(f"WARNING: {len(self.router.effective('mine'))} callable mine back-end(s): when it is down the "
                     "videos wait in the queue and are mined when it returns (orchestrator 05:30: the mine role never "
                     "falls back to a paid frontier vendor; ruling 98's capped paid route is a separate role); nothing "
                     "is dropped")
        self.meter.measure()
        self.last_measure = self.clock()
        threads = [threading.Thread(target=self._loop, args=a, daemon=True, name=a[0]) for a in (
            ("watch", self.watch_once, config.POLL_S, config.POLL_JITTER_S),
            ("fetch", self.fetch_once, 10.0),
            ("mine", self.mine_once, 5.0),
            ("hook", self.hook_once, 5.0),
            ("check", self.check_once, CHECK_EVERY_S),
            ("health", self.health_once, 60.0),
            ("purge", self.purge_once, float((self.purge_spec or {}).get("every_s", 600))))] + (
            [threading.Thread(target=self._loop, args=("signal", self.hsig.tick, downsignal.SIGNAL_EVERY_S),
                              daemon=True, name="signal")] if self.hsig is not None else [])
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
