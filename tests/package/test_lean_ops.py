#!/usr/bin/env python3
"""R2 + R3 (build 172, the owner's 15:25 ET Nov 24 order): tests/package/lean/lean_ops.py, offline. No command is
run: every state-changing command goes to a stub runner (or, in a dry run, nowhere), the clock is a fake one, every
folder a temporary one; git's network read (ls-remote) and tmux are stubbed.
  R3  ONE deadline: the build is handed its share (--deadline-at, and `timeout` at the share), the render only the
      time left before the delivery's share, the delivery the rest; a stage stopped at its limit is DEADLINE_STOPPED on
      the build's one outcome line; nothing starts once the time is used up;
  R2  a dry run executes nothing and creates nothing, yet prints every command; no experimental command line holds a
      production watchdog marker or names Book Terminal; restore stops only the two experimental sessions, by exact
      name, is safe to run twice, and compares production with the snapshot taken at start."""
import contextlib
import io
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path[:0] = [os.path.join(REPO, "pipeline"), HERE, os.path.join(HERE, "lean")]
import lean_ops as LO  # noqa: E402
import outcomes as OC  # noqa: E402


class Clock:
    def __init__(self, t):
        self.t = t

    def __call__(self):
        return self.t


class Base(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.d, True)
        self.p = LO.paths(os.path.join(self.d, "run"))
        self.outcomes = os.path.join(self.d, "outcomes.jsonl")
        self.said = []
        prod = os.path.join(self.d, "production")                       # B1: production's ledgers: empty stand-ins
        os.makedirs(prod)
        for patch in (mock.patch.dict(os.environ, {"PP_SPEND_LEDGER_DIR": os.path.join(self.d, "spend"),
                                                   "PP_SPEND_PROD_BUILDER": prod,
                                                   "PP_SPEND_PROD_OUTSIDE": os.path.join(prod, "outside.jsonl"),
                                                   "PP_SPEND_PROD_RUNS": "no-production-run-in-tests"}),
                      mock.patch.object(OC, "OUTCOMES", self.outcomes),
                      mock.patch.object(LO, "INGEST_DB", os.path.join(self.d, "no_ingest", "queue.sqlite")),
                      mock.patch.object(LO, "head_pushed", lambda root, branch: ("a" * 40, "a" * 40)),
                      mock.patch.object(LO, "tree_clean", lambda root, dirs=None: (True, []))):
            patch.start()
            self.addCleanup(patch.stop)


class TheOneDeadline(Base):
    """The launch with a fake clock: each stage's command carries `timeout <the time left>`, and its end is recorded."""

    def launch(self, build_s, render_s, render_rc, pin=True, deadline_s=2700):
        clock, cmds = Clock(1_800_000_000.0), []
        rec = os.path.join(self.d, "ledger_20261125_030000")

        def run(cmd, env, timeout, log):
            cmds.append((cmd, env, timeout))
            if "proof_ledger.py" in " ".join(cmd):      # the build: writes its record, its pin and its one line
                os.makedirs(rec, exist_ok=True)
                with open(cmd[cmd.index("--out-dir-file") + 1], "w") as f:
                    f.write(rec)
                if pin:
                    with open(os.path.join(rec, "MOMENTS_PIN_LEDGER.json"), "w") as f:
                        json.dump({"story_id": "S-00000001", "moments_package": {"package_sha256": "b" * 64}}, f)
                OC.record_build(rec, rc=0)
                clock.t += build_s
                return 0
            if "pulse_check_run.sh" in " ".join(cmd):   # the render
                with open(log, "w") as f:
                    f.write("=== FRESH-TOPIC RUN /home/ultron/protocol_pulse/runs/pinned_x ===\n")
                clock.t += render_s
                return render_rc
            clock.t += 5                                 # the delivery
            return 0
        o = LO.Ops(False, clock=clock, run=run, out=self.said.append, p=self.p)
        with mock.patch.object(LO, "preconditions", lambda *a, **k: True), \
                mock.patch("ceiling_seed.main", lambda argv: 0):
            rc = LO.launch(o, 172, deadline_s)
        return rc, cmds, clock, OC.lines(self.outcomes)

    @staticmethod
    def limit(cmd):
        return int(cmd[cmd.index("timeout") + 3])        # timeout --signal=TERM --kill-after=N <LIMIT> ...

    def test_each_stage_is_handed_only_the_time_left(self):
        """MUST-PASS: 2700 s; the build uses 1200 s of its 1500 s share: the render is handed 2580 - 1200 = 1380 s,
        and stopped at it (124): DEADLINE_STOPPED at "render"; nothing is delivered; the launch ends inside 2700 s
        (plus the stop's grace)."""
        rc, cmds, clock, ls = self.launch(1200, 1380, OC.DEADLINE_EXIT)
        (b, benv, _), (r, renv, _) = cmds
        self.assertEqual(len(cmds), 2)                                   # no delivery
        self.assertEqual(self.limit(b), 1500 + LO.GRACE_S)              # the driver stops itself at its share
        self.assertEqual(b[b.index("--deadline-at") + 1], f"{1_800_000_000 + 1500}")
        self.assertEqual(self.limit(r), 1380)
        self.assertEqual((benv["PP_SPEND_CEILING"], renv["PP_SPEND_CEILING"]), ("1", "1"))   # R1 for both
        x, = ls
        self.assertEqual((x["outcome"], x["stage"], x["seconds"]["render"]), ("DEADLINE_STOPPED", "render", 1380.0))
        self.assertLessEqual(clock.t - 1_800_000_000, 2700)

    def test_a_render_that_releases_is_delivered_in_the_rest(self):
        rc, cmds, clock, ls = self.launch(900, 1500, 0)
        self.assertEqual(len(cmds), 3)
        self.assertEqual(self.limit(cmds[2][0]), 2700 - 900 - 1500)
        self.assertIn("LEAN BUILD 172: EXPERIMENTAL", " ".join(cmds[2][0]))
        x, = ls
        self.assertEqual((x["outcome"], x["render"]["exit"], x["delivery"]["exit"]), ("SEALED", 0, 0))

    def test_no_pin_no_render(self):
        rc, cmds, _, ls = self.launch(1500, 0, 0, pin=False)
        self.assertEqual(len(cmds), 1)

    def test_no_time_left_nothing_starts(self):
        """The build used the whole budget before its pin: the render is not started, and the line says so."""
        rc, cmds, _, ls = self.launch(2600, 0, 0)
        self.assertEqual(len(cmds), 1)
        self.assertEqual((ls[0]["outcome"], ls[0]["stage"]), ("DEADLINE_STOPPED", "render"))

    def test_the_shares(self):
        s = LO.shares(1000.0, 2700)
        self.assertEqual((s["build_at"], s["render_at"], s["deadline_at"]), (2500.0, 3580.0, 3700.0))
        s = LO.shares(1000.0, 900)                       # a short budget: the build never eats the delivery's share
        self.assertEqual(s["build_at"], 1000.0 + 900 - LO.DELIVERY_SHARE_S)
        s = LO.shares(1000.0, 6000)                      # build 172's one-build exception: the slowest measured render
        self.assertEqual((s["build_at"], s["render_at"]), (1000.0 + 1929, 1000.0 + 5880))   # (3951 s) still fits
        self.assertEqual(LO.DEADLINE_S, 2700)            # the default stays the product's target

    def test_an_expired_deadline_never_starts_the_delivery(self):
        """B3 (b), MUST-FAIL: the render ends AFTER the deadline (its 1380 s share plus the stop's grace: 2730 s on the
        fake clock) with exit 0: the check immediately before the delivery, on the same clock, starts nothing; the
        line says DEADLINE_STOPPED at "delivery"."""
        rc, cmds, clock, ls = self.launch(1200, 1530, 0)
        self.assertEqual(len(cmds), 2)                                   # the build and the render: no delivery
        self.assertGreater(clock.t - 1_800_000_000, 2700)
        x, = ls
        self.assertEqual((x["outcome"], x["stage"], x["delivery"]["exit"]), ("DEADLINE_STOPPED", "delivery",
                                                                            OC.DEADLINE_EXIT))

    def test_too_little_time_left_never_starts_the_delivery(self):
        """B3 (b): 20 s left (under the delivery's 30 s minimum; the one measured delivery took 18 s): not started."""
        rc, cmds, clock, ls = self.launch(1200, 1480, 0)
        self.assertEqual(len(cmds), 2)
        self.assertEqual(ls[0]["outcome"], "DEADLINE_STOPPED")
        rc, cmds, clock, ls = self.launch(1200, 1460, 0)                 # 40 s left: delivered, handed the 40 s
        self.assertEqual((len(cmds), self.limit(cmds[2][0])), (3, 40))


class TheDryRun(Base):
    def test_a_dry_run_executes_nothing_creates_nothing_and_prints_every_command(self):
        def forbidden(*a, **k):
            raise AssertionError("a dry run ran a command")
        o = LO.Ops(True, run=forbidden, out=self.said.append, p=self.p)
        real = LO.sh

        def sh(cmd, **k):                                # the experimental sessions are not up; every other read is
            return (1, "") if cmd[:2] == ["tmux", "has-session"] else real(cmd, **k)      # real (reads only)
        with mock.patch.object(LO, "sh", sh):
            self.assertIn(LO.start(o), (0, 2))
            LO.launch(o, 172, 2700)
            LO.restore(o)
        self.assertFalse(os.path.exists(self.p["run"]))
        self.assertFalse(os.path.exists(os.path.join(self.d, "spend")))
        text = "\n".join(self.said)
        for what in ("the release copy", "the experimental lockcheck", "the experimental scorer", "the build",
                     "the render", "the delivery"):
            self.assertIn(f"WOULD RUN {what}", text)
        self.assertNotIn("\n  RUN ", text)

    def test_no_experimental_command_holds_a_watchdog_marker_or_names_book_terminal(self):
        tops = LO.tops()
        lines = [" ".join(LO.tmux_cmd(self.p, n, LO.env_instance(self.p, n, "build172"), tops)) for n in LO.SESSIONS]
        lines.append(" ".join(LO.in_ns(self.p, "render", ["bash", "scripts/pulse_check_run.sh"], tops)))
        bk = LO.book()                                                  # discovered now, never hard-coded
        self.assertTrue(bk["sessions"] or bk["worktrees"], bk)
        for line in lines:
            for m in LO.MARKERS:
                self.assertNotIn(m, line)
            for b in bk["worktrees"] + bk["branches"] + bk["sessions"]:
                self.assertNotIn(b, line)
            self.assertTrue(any(o in line for o in LO.OURS))           # restore can find what it started
        self.assertEqual(sorted(LO.SESSIONS.values()), ["pipeline_lean_lockcheck", "pipeline_lean_scorer"])

    def test_the_namespace_keeps_every_live_tree_read_only(self):
        s = LO.ns_script(self.p, "render", LO.tops())
        for t in LO.RO_TREES:
            self.assertIn(f"mount -o remount,bind,ro {t};", s)
        self.assertIn(f"mount --bind {self.p['release']} {LO.LIVE_MAIN}", s)
        self.assertIn(f"mount -o remount,bind,ro {LO.LIVE_MAIN}/{LO.KEYFILE}", s)
        self.assertNotIn("upperdir=/home/ultron/protocol_pulse", s)                    # every write lands in RUN
        self.assertNotIn("upperdir=/home/ultron/worktrees", s)


class TheRestore(Base):
    def test_restore_stops_only_its_own_sessions_and_is_safe_twice(self):
        live = {"pipeline_lean_lockcheck", "pipeline_lean_scorer"}
        ran = []

        def sh(cmd, **k):
            if cmd[:2] == ["tmux", "has-session"]:
                return (0, "") if cmd[-1].lstrip("=") in live else (1, "")
            return (0, "")

        def run(cmd, env, timeout, log):
            ran.append(cmd)
            live.discard(cmd[-1].lstrip("="))
            return 0
        snap = {"processes": {"scorer": [[1, "9", "x"]]}, "sessions": ["pipeline_pp_lean"], "panes": {}, "trees": {},
                "crontab": "c", "keyfile_stat": [1, 2], "spend": {"f": "h"}}
        os.makedirs(self.p["run"])
        with open(self.p["before"], "w") as f:
            json.dump(snap, f)
        with mock.patch.object(LO, "sh", sh), mock.patch.object(LO, "snapshot", lambda: dict(snap)):
            o = LO.Ops(False, run=run, out=self.said.append, p=self.p)
            self.assertEqual(LO.restore(o), 0)
            self.assertEqual(sorted(c[-1] for c in ran), ["=pipeline_lean_lockcheck", "=pipeline_lean_scorer"])
            self.assertIn("  PRODUCTION AS BEFORE", self.said)
            self.assertEqual(LO.restore(o), 0)                           # twice: nothing to stop, nothing changes
        self.assertEqual(len(ran), 2)
        self.assertTrue(all(c[:3] == ["tmux", "kill-session", "-t"] for c in ran))

    def test_compare_names_what_changed(self):
        b = {"processes": {"scorer": [[1, "9", "x"]]}, "sessions": ["a"], "panes": {"a": ["1"]}, "trees": {"t": 1},
             "crontab": "c", "keyfile_stat": [1, 2], "spend": {"f": "h"}}
        bad, notes = LO.compare(b, dict(b, spend={"f": "h2"}))
        self.assertEqual((bad, len(notes)), ([], 1))                      # production's own spend: a note
        bad, _ = LO.compare(b, dict(b, processes={"scorer": [[2, "10", "x"]]}))
        self.assertEqual(len(bad), 1)                                     # a production service gone or restarted
        bad, _ = LO.compare(b, dict(b, crontab="d"))
        self.assertEqual(len(bad), 1)
        b2 = dict(b, trees={LO.LIVE_MAIN: {"head": "a"}, os.path.join(LO.WORKTREES, "book-terminal"): {"head": "b"}})
        bad, notes = LO.compare(b2, dict(b2, trees={LO.LIVE_MAIN: {"head": "a"}, os.path.join(LO.WORKTREES, "book-terminal"): {"head": "c"}}))
        self.assertEqual((bad, len(notes)), ([], 1))                   # another session's commit: a note
        bad, _ = LO.compare(b2, dict(b2, trees={LO.LIVE_MAIN: {"head": "x"}, os.path.join(LO.WORKTREES, "book-terminal"): {"head": "b"}}))
        self.assertEqual(len(bad), 1)                                     # the live tree moved: named


SNAP = {"processes": {"scorer": [[1, "9", "x"]]}, "sessions": ["pipeline_pp_lean"], "panes": {}, "trees": {},
        "crontab": "c", "keyfile_stat": [1, 2], "spend": {"f": "h"}}


def _sh_down(cmd, **k):
    """tmux: no experimental session is up; every other read: an empty success (nothing real is asked)."""
    return (1, "") if cmd[:2] == ["tmux", "has-session"] else (0, "")


class Live(Base):
    """A LIVE (not dry) start / run whose every state-changing command goes to a stub runner (no tmux, no git, no cp,
    no build, no render), production's snapshot a constant, the seed the real SC.init_day on a temporary ledger."""

    def setUp(self):
        super().setUp()
        self.events = []
        for patch in (mock.patch.object(LO, "sh", _sh_down), mock.patch.object(LO, "snapshot", lambda: dict(SNAP)),
                      mock.patch.object(LO, "release_copy_cmds", lambda p, sha: (
                          [["git", "clone", "stub"]], (os.path.join(self.d, "alternates"), "x"))),
                      mock.patch("ceiling_seed.main", self.seed)):
            patch.start()
            self.addCleanup(patch.stop)

    def seed(self, argv):
        import spend_ceiling as SC
        self.events.append(("seed", list(argv)))
        if "--write" in argv and not getattr(self, "seed_writes_nothing", False):
            SC.init_day({"builder:pp-selectid": 0.25}, 0, by="test seed")
        return 0

    def runner(self, cmd, env, timeout, log):
        self.events.append(("cmd", cmd[:4]))
        return 0


class TheLedgerComesFirst(Live):
    def test_start_initializes_the_ledger_before_any_service(self):
        """B1 (a), MUST-PASS: `start` writes the ledger (the seed, --write) BEFORE the first service's tmux command, and
        checks it again immediately before each service."""
        o = LO.Ops(False, run=self.runner, out=self.said.append, p=self.p)
        with mock.patch.object(LO, "preconditions", lambda *a, **k: True):
            self.assertEqual(LO.start(o), 0)
        order = [e[0] if e[0] == "seed" else e[1][1] for e in self.events]
        first_tmux = order.index("new-session")
        self.assertIn("seed", order[:first_tmux])
        self.assertEqual(sum(1 for x in self.said if "the one ledger checked before the experimental" in x), 2)
        import spend_ceiling as SC
        st = SC.peek()
        self.assertTrue(st["exists"] and st["init"] and not st["stop"])

    def test_a_service_start_before_the_ledger_is_initialized_is_refused(self):
        """B1 (a), MUST-FAIL: the ledger-init writes nothing (or the ledger is gone): no service is started (no tmux
        command at all), and ledger_ready refuses directly."""
        self.seed_writes_nothing = True
        o = LO.Ops(False, run=self.runner, out=self.said.append, p=self.p)
        with mock.patch.object(LO, "preconditions", lambda *a, **k: True):
            self.assertEqual(LO.start(o), 2)
        self.assertFalse([e for e in self.events if e[0] == "cmd" and e[1][:2] == ["tmux", "new-session"]])
        self.assertTrue(any("REFUSED" in x and "not initialized" in x or "does not exist" in x for x in self.said))
        self.assertFalse(LO.ledger_ready(o, "a service"))

    def test_each_service_checks_the_ledger_itself(self):
        """B1 (a), MUST-FAIL: the ledger-init reports success but no initialized ledger is there when a service is
        about to start (removed, or never written): the service's own check refuses it; no tmux command runs."""
        o = LO.Ops(False, run=self.runner, out=self.said.append, p=self.p)
        with mock.patch.object(LO, "preconditions", lambda *a, **k: True), \
                mock.patch.object(LO, "ledger_init", lambda o_: True):
            self.assertEqual(LO.start(o), 2)
        self.assertFalse([e for e in self.events if e[0] == "cmd" and e[1][:2] == ["tmux", "new-session"]])
        self.assertTrue(any(x.startswith("REFUSED: the experimental lockcheck not started") for x in self.said))

    def test_the_dry_run_shows_the_order(self):
        o = LO.Ops(True, run=None, out=self.said.append, p=self.p)
        with mock.patch.object(LO, "preconditions", lambda *a, **k: True):
            LO.start(o)
        text = "\n".join(self.said)
        self.assertLess(text.index("LEDGER-INIT"), text.index("WOULD RUN the experimental lockcheck"))
        self.assertFalse(os.path.exists(self.p["run"]))


class TheServicesComeUpFirst(Base):
    def test_the_launch_waits_for_each_service_s_own_heartbeat(self):
        """`run` launches only when BOTH experimental sessions are up with their OWN first heartbeat (one service's beat
        never stands in for the other's); not up within the wait: refused, and the run still restores."""
        up = {"=pipeline_lean_lockcheck", "=pipeline_lean_scorer"}

        def sh(cmd, **k):
            return (0, "") if cmd[:2] == ["tmux", "has-session"] and cmd[-1] in up else (1, "")
        os.makedirs(self.p["beats"])
        o = LO.Ops(False, out=self.said.append, p=self.p)
        with mock.patch.object(LO, "sh", sh):
            open(os.path.join(self.p["beats"], "scorer.json"), "w").close()
            self.assertFalse(LO.services_ready(o, wait_s=0.5))          # the lock service has not beaten yet
            open(os.path.join(self.p["beats"], "lock_precheck.json"), "w").close()
            self.assertTrue(LO.services_ready(o, wait_s=0.5))
            up.discard("=pipeline_lean_scorer")
            self.assertFalse(LO.services_ready(o, wait_s=0.5))          # a session gone: not ready
        said, runs = [], []
        with mock.patch.object(LO, "sh", _sh_down), mock.patch.object(LO, "snapshot", lambda: dict(SNAP)), \
                mock.patch.object(LO, "preconditions", lambda *a, **k: True), \
                mock.patch.object(LO, "release_copy_cmds", lambda p, sha: ([], (os.path.join(self.d, "alt"), "x"))), \
                mock.patch.object(LO, "services_ready", lambda o_: False), \
                mock.patch.object(LO, "launch", lambda *a, **k: runs.append(1) or 0), \
                mock.patch("ceiling_seed.main", lambda argv: (__import__("spend_ceiling").init_day({}, 0, by="t")
                                                              and 0)):
            o = LO.Ops(False, run=lambda *a: 0, out=said.append, p=self.p)
            o.guard_argv = lambda pid, st, dl: ["true"]
            self.assertEqual(LO.run(o, 172, 6000), 2)
        self.assertEqual(runs, [])                                       # no launch
        self.assertTrue(any("RESTORE (live)" in x for x in said))


class ThePreflight(Base):
    def lines(self, **kw):
        o = LO.Ops(True, out=self.said.append, p=self.p)
        with mock.patch.object(LO, "sh", _sh_down):
            LO.preconditions(o, "build172", **kw)
        return self.said

    def test_a_production_build_or_render_running_refuses_the_launch(self):
        with mock.patch("spend_ceiling.production_running", lambda fresh=False: [(4242, "bash pulse_check_run.sh")]):
            said = self.lines(launch=False)
        self.assertTrue(any(x.startswith("  [FAIL] no production build or render running") for x in said), said)

    def test_a_test_only_override_refuses_a_live_run(self):
        said = self.lines(launch=False)                                   # this test sets PP_SPEND_LEDGER_DIR
        self.assertTrue(any(x.startswith("  [FAIL] no test-only override") for x in said))

    def test_the_run_must_end_inside_its_spend_day(self):
        from datetime import datetime as DT
        t0 = DT(2026, 11, 25, 19, 45, tzinfo=LO.SC.DAY_ET).timestamp()    # 19:45 ET + 6000 s passes 21:10 ET
        with mock.patch.object(LO, "assets_check", lambda out: (True, ["stub"])):
            said = self.lines(launch=True, t0=t0, deadline_s=6000)
        self.assertTrue(any(x.startswith("  [FAIL] the deadline ends inside the spend day") for x in said), said)
        self.said.clear()
        t0 = DT(2026, 11, 25, 9, 30, tzinfo=LO.SC.DAY_ET).timestamp()
        with mock.patch.object(LO, "assets_check", lambda out: (True, ["stub"])):
            said = self.lines(launch=True, t0=t0, deadline_s=6000)
        self.assertTrue(any(x.startswith("  [PASS] the deadline ends inside the spend day") for x in said), said)

    def test_the_assets_are_checked_by_path_and_size(self):
        """B3 (a): present at its size passes; missing, another size, or under a folder the namespace takes from git
        only (pipeline/, scripts/), fails."""
        f = os.path.join(self.d, "music.mp3")
        with open(f, "wb") as fo:
            fo.write(b"x" * 10)
        inv = os.path.join(self.d, "ASSETS.json")
        for files, ok in (([{"path": f, "size": 10}], True), ([{"path": f, "size": 11}], False),
                          ([{"path": f + ".gone", "size": 10}], False),
                          ([{"path": os.path.join(LO.LIVE_MAIN, "pipeline", "channels.json"), "size": None}], False)):
            with open(inv, "w") as fo:
                json.dump({"files": files, "taken_at": "test"}, fo)
            with mock.patch.object(LO, "ASSETS", inv):
                self.assertEqual(LO.assets_check(print)[0], ok, files)


HARNESS = r'''
import json, os, signal, sys, time
d, mode = sys.argv[1], sys.argv[2]
sys.path[:0] = [os.path.join({repo!r}, "pipeline"), os.path.join({repo!r}, "tests", "package"),
                os.path.join({repo!r}, "tests", "package", "lean")]
from unittest import mock
import lean_ops as LO, spend_ceiling as SC
p = LO.paths(os.path.join(d, "run"))
said = open(os.path.join(d, "said.txt"), "a")
def out(x):
    said.write(x + "\n"); said.flush()
def sh(cmd, **k):
    return (1, "") if cmd[:2] == ["tmux", "has-session"] else (0, "")
SNAP = {{"processes": {{}}, "sessions": [], "panes": {{}}, "trees": {{}}, "crontab": "c", "keyfile_stat": [1, 2],
        "spend": {{}}}}
def seed(argv):
    if "--write" in argv:
        SC.init_day({{}}, 0, by="harness")
    return 0
o = None
def run(cmd, env, timeout, log):
    if "proof_ledger.py" in " ".join(cmd):                 # the build: a real process in a session of its own
        if mode == "error":
            raise RuntimeError("a stage could not start")
        return o._exec(["bash", "-c", "echo $$ > " + os.path.join(d, "stage.pid") + "; exec sleep 120"], None, None,
                       None)
    return 0
with mock.patch.object(LO, "preconditions", lambda *a, **k: mode != "refused"), mock.patch.object(LO, "sh", sh), \
        mock.patch.object(LO, "snapshot", lambda: dict(SNAP)), \
        mock.patch.object(LO, "head_pushed", lambda r, b: ("a" * 40, "a" * 40)), \
        mock.patch.object(LO, "release_copy_cmds", lambda p_, sha: ([], (os.path.join(d, "alt"), "x"))), \
        mock.patch.object(LO, "INGEST_DB", os.path.join(d, "none.sqlite")), \
        mock.patch.object(LO, "services_ready", lambda o_: True), \
        mock.patch("ceiling_seed.main", seed):
    o = LO.Ops(False, run=run, out=out, p=p)
    o.guard_argv = lambda pid, st, dl: [sys.executable, "-B", __file__, d, "guard", str(pid), str(st)]
    if mode == "guard":
        sys.exit(LO.guard(o, int(sys.argv[3]), sys.argv[4], None, poll=0.2))
    sys.exit(LO.run(o, 172, 6000))
'''


class TheExitPaths(Base):
    """B3 (c): the one command restores on EVERY exit path. A harness (this repo's lean_ops.py, every state-changing
    command a stub; the build a real `sleep` in a session of its own) is run as its own process and ended each way."""

    def harness(self, mode="run"):
        h = os.path.join(self.d, "harness.py")
        with open(h, "w") as f:
            f.write(HARNESS.format(repo=REPO))
        env = dict(os.environ, PP_SPEND_LEDGER_DIR=os.path.join(self.d, "spend"))
        proc = subprocess.Popen([sys.executable, "-B", h, self.d, mode], env=env, stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        self.addCleanup(self.reap, proc)                  # a test that fails midway leaves no harness, stage or guard
        return proc

    def reap(self, proc):
        if proc.poll() is None:
            proc.kill()
            proc.communicate(timeout=30)
        try:
            LO.kill_session(int(open(os.path.join(self.d, "stage.pid")).read()), grace=1.0)
        except (OSError, ValueError):
            pass
        end = time.time() + 10                            # its guard ends once the launcher is gone (or it restores)
        while time.time() < end and any(f"{self.d}/harness.py" in " ".join(LO.SC._argv(int(x)))
                                        for x in os.listdir("/proc") if x.isdigit()):
            time.sleep(0.2)

    def wait_for(self, path, s=30.0):
        end = time.time() + s
        while time.time() < end and not os.path.exists(path):
            time.sleep(0.1)
        return os.path.exists(path)

    def log_text(self):
        try:
            return open(os.path.join(self.d, "said.txt")).read()
        except OSError:
            return ""

    @staticmethod
    def alive(pid):
        st = LO.proc_start(pid)
        if st is None:
            return False
        with open(f"/proc/{pid}/stat") as f:
            return f.read().rsplit(")", 1)[1].split()[0] != "Z"

    def ended_by(self, sig):
        h = self.harness()
        stage = os.path.join(self.d, "stage.pid")
        self.assertTrue(self.wait_for(stage), self.log_text()[-2000:])
        time.sleep(0.3)
        spid = int(open(stage).read())
        self.assertTrue(self.alive(spid))
        h.send_signal(sig)
        out, _ = h.communicate(timeout=90)
        text = self.log_text()
        self.assertEqual(h.returncode, 128 + sig, text[-1500:] + out[-500:])
        self.assertIn(f"STOPPED by signal {signal.Signals(sig).name}", text)
        self.assertIn("RESTORE (live)", text)
        self.assertIn("PRODUCTION AS BEFORE", text)
        self.assertFalse(self.alive(spid))                               # the stage's session was stopped
        self.assertTrue(os.path.exists(LO.restored_marker(LO.paths(os.path.join(self.d, "run")), h.pid)))

    def test_sigterm(self):
        self.ended_by(signal.SIGTERM)

    def test_sigint(self):
        self.ended_by(signal.SIGINT)

    def test_sighup(self):
        self.ended_by(signal.SIGHUP)

    def test_sigkill_the_guard_restores(self):
        """MUST-PASS: the launcher is killed (SIGKILL: no handler, no finally): the detached guard sees it gone without
        its restore marker, stops the stage it left running, and restores."""
        h = self.harness()
        stage = os.path.join(self.d, "stage.pid")
        self.assertTrue(self.wait_for(stage), self.log_text()[-2000:])
        time.sleep(0.5)
        spid = int(open(stage).read())
        h.kill()
        h.communicate(timeout=30)
        marker = LO.restored_marker(LO.paths(os.path.join(self.d, "run")), h.pid)
        self.assertTrue(self.wait_for(marker, 60), self.log_text()[-2000:])
        text = self.log_text()
        self.assertIn("gone WITHOUT restoring (killed): RESTORE", text)
        self.assertIn("PRODUCTION AS BEFORE", text)
        end = time.time() + 30
        while time.time() < end and self.alive(spid):
            time.sleep(0.2)
        self.assertFalse(self.alive(spid))

    def test_success_refusal_and_error_each_restore(self):
        for mode, rc in (("refused", 2), ("error", 1)):
            shutil.rmtree(os.path.join(self.d, "run"), True)
            open(os.path.join(self.d, "said.txt"), "w").close()
            h = self.harness(mode)
            out, _ = h.communicate(timeout=90)
            text = self.log_text()
            self.assertEqual(h.returncode, rc, mode + text[-1500:] + out[-500:])
            self.assertIn("RESTORE (live)", text, mode)
            self.assertTrue(os.path.exists(LO.restored_marker(LO.paths(os.path.join(self.d, "run")), h.pid)), mode)

    def test_the_launch_s_own_ends_restore_in_process(self):
        """Success and the deadline (the build exits 124): the restore runs once, after the launch."""
        for build_rc in (0, OC.DEADLINE_EXIT):
            said, calls = [], []

            def run(cmd, env, timeout, log, rc=build_rc):
                calls.append(cmd[:3])
                return rc
            with mock.patch.object(LO, "sh", _sh_down), mock.patch.object(LO, "snapshot", lambda: dict(SNAP)), \
                    mock.patch.object(LO, "preconditions", lambda *a, **k: True), \
                    mock.patch.object(LO, "release_copy_cmds", lambda p, sha: ([], (os.path.join(self.d, "alt"), "x"))), \
                    mock.patch.object(LO, "restore", wraps=LO.restore) as rs, \
                    mock.patch.object(LO, "services_ready", lambda o_: True), \
                    mock.patch("ceiling_seed.main", lambda argv: (__import__("spend_ceiling").init_day({}, 0, by="t")
                                                                  and 0)):
                o = LO.Ops(False, run=run, out=said.append, p=self.p)
                o.guard_argv = lambda pid, st, dl: ["true"]
                LO.run(o, 172, 6000)
            self.assertEqual(rs.call_count, 1, build_rc)
            self.assertTrue(any("RUN ENDING" in x for x in said))


class TheDetach(Base):
    def test_the_one_command_detaches_from_the_terminal_and_names_its_log(self):
        probe = os.path.join(self.d, "probe.py")
        facts = os.path.join(self.d, "facts.json")
        with open(probe, "w") as f:
            f.write(textwrap.dedent(f'''
                import json, os, sys
                st0, dn = os.fstat(0), os.stat("/dev/null")
                json.dump({{"pid": os.getpid(), "sid": os.getsid(0), "tty": os.isatty(0),
                           "devnull": (st0.st_dev, st0.st_ino) == (dn.st_dev, dn.st_ino), "argv": sys.argv}},
                          open({facts!r}, "w"))
            '''))
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            self.assertEqual(LO.detach(["run", "--build-no", "172", "--deadline-s", "6000"], self.p, entry=probe), 0)
        end = time.time() + 20
        while time.time() < end and not os.path.exists(facts):
            time.sleep(0.1)
        f = json.load(open(facts))
        self.assertEqual(f["sid"], f["pid"])                              # its own session: no controlling terminal
        self.assertEqual((f["tty"], f["devnull"]), (False, True))         # stdin is /dev/null
        log = f["argv"][f["argv"].index("--log") + 1]
        self.assertIn("--foreground", f["argv"])
        self.assertIn(f"LOG: {log}", printed.getvalue())
        self.assertTrue(os.path.exists(log))


class TheIngestionLine(Base):
    def test_ingestion_s_own_spend_is_read_from_a_copy_and_never_in_the_ceiling(self):
        """B1 (c): the miner's calls inside the window, from its own ledger (a WAL database still held open by its
        writer, as live): summed by back-end from a COPY; the live folder gains no file; the line says NEVER."""
        import sqlite3
        dbdir = os.path.join(self.d, "ingest")
        os.makedirs(dbdir)
        db = os.path.join(dbdir, "queue.sqlite")
        con = sqlite3.connect(db)
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("CREATE TABLE calls (id INTEGER PRIMARY KEY, at TEXT, ts REAL, role TEXT, backend TEXT, "
                    "cost_usd REAL)")
        con.commit()
        for ts, b, usd in ((100.0, "heimdall_qwen27b", 0.01), (150.0, "heimdall_qwen27b", 0.02),
                           (160.0, "xai_paid", 0.05), (300.0, "heimdall_qwen27b", 0.04)):
            con.execute("INSERT INTO calls (at, ts, role, backend, cost_usd) VALUES ('x', ?, 'mine', ?, ?)",
                        (ts, b, usd))
        con.commit()                                                     # in the WAL: the writer keeps it open
        before = sorted(os.listdir(dbdir))
        by = LO.ingest_spend(120.0, 200.0, db=db, scratch=self.d)
        self.assertEqual(by, {"heimdall_qwen27b": [1, 0.02], "xai_paid": [1, 0.05]})
        self.assertEqual(sorted(os.listdir(dbdir)), before)
        con.close()
        o = LO.Ops(False, clock=lambda: 200.0, out=self.said.append, p=self.p)
        o.window = (120.0, 200.0)
        with mock.patch.object(LO, "INGEST_DB", db):
            line = LO.ingest_line(o)
        self.assertIn("INGESTION (separate, NEVER in the $1.50): $0.0700 in 2 calls", line)
        self.assertIn("xai_paid", line)


if __name__ == "__main__":
    unittest.main()
