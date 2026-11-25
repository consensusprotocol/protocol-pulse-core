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

REAL_OWNER = LO.ollama_owner                       # the tests of it call it against a stand-in; Base stubs it


def _no_owner(p, name, port=LO.OLLAMA_PORT, write=True):
    return {"port": port, "pid": None, "why": "stubbed in a test: the real Ollama is never read"}


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
                      mock.patch.object(LO, "leftovers", lambda: []),       # a test never signals a real process
                      mock.patch.object(LO, "ollama_owner", _no_owner),      # nor reads production's Ollama
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

    def test_the_render_s_namespace_gets_the_owner_recorded_first(self):
        seen = []
        with mock.patch.object(LO, "ollama_owner", lambda p, name, port=LO.OLLAMA_PORT, write=True:
                               seen.append(("owner", name, len(self.said))) or _no_owner(p, name)):
            rc, cmds, clock, ls = self.launch(600, 600, 0)
        self.assertEqual([x[1] for x in seen], ["render"])
        i = next(i for i, x in enumerate(self.said) if "RUN the render" in x)
        self.assertLess(seen[0][2], i)                                   # recorded before the render's command

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
        lines = [" ".join(LO.tmux_cmd(self.p, n)) + "\n" + LO.service_script(self.p, n, LO.env_instance(
            self.p, n, "build172"), tops) for n in LO.SESSIONS]          # the tmux command and its start file
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


LEANTEST = {"lockcheck": "pipeline_leantest_t_lockcheck", "scorer": "pipeline_leantest_t_scorer"}   # never the proof's


class TheStartupCommand(Base):
    """The 11:08 ET Nov 25 start, refused at once: tmux 3.2a refuses a command over its 16 KB message ("command too
    long"); the lockcheck's whole start line was its tmux command (22,156 bytes), and start sent tmux's error to
    /dev/null. Now the start line is a file and tmux is handed `bash <the file>`, its output in RUN/logs."""

    def test_the_tmux_command_is_short_and_the_start_file_holds_the_service(self):
        """MUST-FAIL on f71e01c85 (the start line WAS the tmux command): each service's tmux command stays far under
        tmux's limit even for a long run folder; the start file holds the whole start line, which is over it."""
        p = LO.paths("/var/tmp/" + "r" * 200)
        td = LO.tops()
        for n, s in LO.SESSIONS.items():
            cmd = LO.tmux_cmd(p, n)
            self.assertLess(sum(len(x.encode()) + 1 for x in cmd), 1000)
            script = LO.service_script(p, n, LO.env_instance(p, n, "build172"), td)
            self.assertGreater(len(script.encode()), LO.TMUX_MAX)     # what tmux refused at 11:08 ET
            self.assertEqual(cmd[:7], ["tmux", "new-session", "-d", "-s", s, "-c", p["run"]])
            self.assertEqual(cmd[7], f"exec bash {LO.service_file(p, n)} </dev/null 2>>{LO.service_log(p, n)}")
            self.assertEqual(cmd[8:], [";", "set-option", "-w", "-t", f"={s}:", "remain-on-exit", "on"])
            self.assertTrue(script.startswith("set -o pipefail\n{\n"))
            self.assertTrue(script.endswith(f"}} 2>&1 | tee -a {LO.service_log(p, n)}\n"))
            self.assertEqual(len([x for x in script.split("\n") if "scripts/lean/serve.py" in x]), 1)

    def test_offline_means_no_network_no_key_and_nothing_to_serve(self):
        """The startup proof's mode (never the one command's): unshare --net, the key files bound from /dev/null,
        empty request folders and no candidates file, the scratch run's ledger and GPU0 want flags."""
        td = LO.tops()
        live = LO.service_script(self.p, "lockcheck", LO.env_instance(self.p, "lockcheck", "b"), td)
        off = LO.service_script(self.p, "lockcheck", LO.env_instance(self.p, "lockcheck", "b", True), td, True)
        self.assertNotIn("--net", live)
        self.assertIn("unshare --user --map-root-user --mount --net bash", off)
        self.assertIn(f"mount --bind /dev/null {LO.LIVE_MAIN}/{LO.KEYFILE};", off)
        self.assertIn(f"mount --bind /dev/null {LO.LIVE_MAIN}/config/api_keys.json;", off)
        self.assertNotIn(f"ns/live_main/{LO.KEYFILE} ", off)
        self.assertIn(f"PP_LOCK_PRECHECK_EXTRA={self.p['run']}/offline/lock_requests", off)
        self.assertIn(f"PP_SPEND_LEDGER_DIR={self.p['run']}/pp_spend", off)
        self.assertIn(f"PP_GPU0_WANT_DIR={self.p['run']}/offline/gpu0_want", off)
        sc = LO.service_script(self.p, "scorer", LO.env_instance(self.p, "scorer", "b", True), td, True)
        self.assertIn(f"--candidates {self.p['run']}/offline/no_candidates.json", sc)
        self.assertFalse(LO.Ops(True).offline)                         # the one command never sets it


@unittest.skipUnless(shutil.which("tmux") and shutil.which("unshare"), "needs tmux and unshare")
class TheStartupErrorsAreKept(Base):
    """REAL tmux sessions (pipeline_leantest_*), started by `start` itself, OFFLINE (unshare --net, the keys from
    /dev/null; no service can start: the namespace fails first, or tmux refuses); every other command a stub. Whatever
    stops a service at its start lands in its own log under RUN/logs and is printed into the run log; its pane is kept
    until `restore`."""

    def setUp(self):
        super().setUp()
        for patch in (mock.patch.object(LO, "SESSIONS", dict(LEANTEST)),
                      mock.patch.object(LO, "preconditions", lambda *a, **k: True),
                      mock.patch.object(LO, "snapshot", lambda: dict(SNAP)),
                      mock.patch.object(LO, "release_copy_cmds", lambda p, sha: ([], (os.path.join(self.d, "alt"), "x"))),
                      mock.patch.object(LO, "prepare_ns", lambda p, name, td: None),   # no mount points: a mount fails
                      mock.patch("ceiling_seed.main", lambda argv: (__import__("spend_ceiling").init_day({}, 0, by="t")
                                                                    and 0))):
            patch.start()
            self.addCleanup(patch.stop)
        self.addCleanup(self.kill)
        self.o = LO.Ops(False, run=self.runner, out=self.said.append, p=self.p, offline=True)

    def runner(self, cmd, env, timeout, log):
        """tmux for real (its own error into `log`); the copies and seeds: stubs."""
        return self.o._exec(cmd, env, timeout, log) if cmd[0] == "tmux" else 0

    def kill(self):
        for s in LEANTEST.values():
            subprocess.run(["tmux", "kill-session", "-t", f"={s}"], capture_output=True)

    def test_a_service_failing_at_a_mount_leaves_its_error_in_the_run_log(self):
        self.assertEqual(LO.start(self.o, "t"), 0)                    # tmux took both short commands
        self.assertFalse(LO.services_ready(self.o, wait_s=30))
        text = "\n".join(self.said)
        self.assertIn("mount point does not exist", text)              # the mount script's own error, in the run log
        self.assertRegex(text, r"REFUSED: the experimental (lockcheck|scorer) ENDED \(exit 32\)")
        with open(LO.service_log(self.p, "lockcheck")) as f:
            log = f.read()
        self.assertIn("lockcheck: START", log)
        self.assertIn("lockcheck: ENDED, exit 32", log)
        self.assertEqual(LO.pane_state(LEANTEST["lockcheck"]), (False, "32"))   # the pane is kept ...
        self.assertEqual(LO.restore(self.o), 0)
        self.assertIsNone(LO.pane_state(LEANTEST["lockcheck"]))         # ... until restore

    def test_tmux_s_own_refusal_is_in_the_run_log(self):
        """The 11:08 ET failure itself through the new start: a tmux command over tmux's limit; tmux's own message is
        in the service's log and printed into the run log; no session is left."""
        real = LO.tmux_cmd

        def too_long(p, name):
            cmd = real(p, name)
            cmd[7] += " #" + "x" * 20000
            return cmd
        with mock.patch.object(LO, "tmux_cmd", too_long):
            self.assertEqual(LO.start(self.o, "t"), 1)
        text = "\n".join(self.said)
        self.assertIn("FAILED to start lockcheck: tmux exit 1", text)
        self.assertIn("    | command too long", text)
        self.assertIsNone(LO.pane_state(LEANTEST["lockcheck"]))


STANDIN = r"""
import http.server, json, socketserver, sys
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        b = json.dumps({"models": [{"name": "gemma3:27b", "digest": "stand-in"}]}).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers()
        self.wfile.write(b)
    def log_message(self, *a):
        pass
socketserver.TCPServer.allow_reuse_address = True
s = socketserver.TCPServer(("127.0.0.1", int(sys.argv[1])), H)
print(s.server_address[1], flush=True)
s.serve_forever()
"""
CHECK = r"""
import json, sys
sys.path.insert(0, sys.argv[1])
import story_semantics as sm, gpu0
host = "127.0.0.1:" + sys.argv[2]
gpu0.OLLAMA_HOSTS[0] = host
out = {}
try:
    llm = sm.LocalLLM(host=host).start()
    out["start"] = ["accepted", llm.serve_pid, llm.serve_env]
except BaseException as e:
    out["start"] = ["refused", f"{type(e).__name__}: {e}"]
try:
    out["ollama_pids"] = ["accepted", sorted(gpu0._ollama_pids())]
except BaseException as e:
    out["ollama_pids"] = ["refused", f"{type(e).__name__}: {e}"]
print(json.dumps(out))
"""
RELEASE_PIPELINE = os.path.join(LO.RELEASE_WT, "pipeline")


@unittest.skipUnless(shutil.which("unshare") and shutil.which("ss") and os.path.isfile(
    os.path.join(RELEASE_PIPELINE, "story_semantics.py")), "needs unshare, ss and the lean-release worktree")
class TheOllamaOwner(Base):
    """12:08 ET Nov 25: inside the services' user namespace the kernel hides another namespace's process's fd links and
    environment: `ss -p` names no owner of 127.0.0.1:11434 and /proc/<pid>/environ is unreadable, so the scorer said
    "no Ollama listening". The owner is read OUTSIDE (ollama_owner) and presented inside (owner_bridge, the lines
    ns_script carries). REAL namespaces, the RELEASE's own checks (story_semantics.LocalLLM.start, gpu0._ollama_pids,
    unchanged), a stand-in listener in place of Ollama (no model, no GPU, nothing outside 127.0.0.1)."""

    def standin(self, cvd, port=0, extra=None):
        env = dict({k: v for k, v in os.environ.items() if k != "OLLAMA_HOST"}, CUDA_VISIBLE_DEVICES=cvd,
                   **(extra or {}))                              # only what the test gives it
        proc = subprocess.Popen([sys.executable, "-c", STANDIN, str(port)], env=env, stdout=subprocess.PIPE,
                                text=True, start_new_session=True)
        self.addCleanup(self.end, proc)
        return proc, int(proc.stdout.readline())

    @staticmethod
    def end(proc):
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait()

    def check(self, port):
        """The release's checks, inside a user + mount namespace that carries owner_bridge (host network: the stand-in
        listens on the host's 127.0.0.1)."""
        r = subprocess.run(["unshare", "--user", "--map-root-user", "--mount", "bash", "-c",
                            "set -e; " + LO.owner_bridge(self.p, "t") + '; exec "$@"', "lean-ns",
                            sys.executable, "-c", CHECK, RELEASE_PIPELINE, str(port)],
                           capture_output=True, text=True, timeout=120,
                           env=dict(os.environ, CUDA_VISIBLE_DEVICES="0"))
        self.assertEqual(r.returncode, 0, r.stderr[-2000:])
        return json.loads(r.stdout.strip().splitlines()[-1])

    def test_the_owner_read_outside_is_seen_inside_and_accepted(self):
        proc, port = self.standin("0")
        out = self.check(port)                                          # MUST-FAIL without the bridge: 12:08 ET
        self.assertEqual(out["start"], ["refused", f"RuntimeError: no Ollama listening on 127.0.0.1:{port}"])
        self.assertEqual(out["ollama_pids"][0], "refused")
        self.assertIn("pid is not visible", out["ollama_pids"][1])
        rec = REAL_OWNER(self.p, "t", port=port)
        self.assertEqual((rec["pid"], rec["env"]["CUDA_VISIBLE_DEVICES"]), (proc.pid, "0"))
        out = self.check(port)
        self.assertEqual(out["start"], ["accepted", proc.pid, {"CUDA_VISIBLE_DEVICES": "0", "OLLAMA_HOST": None}])
        self.assertEqual(out["ollama_pids"], ["accepted", [proc.pid]])

    def test_an_owner_not_gpu0_only_is_still_refused(self):
        proc, port = self.standin("1")
        REAL_OWNER(self.p, "t", port=port)
        out = self.check(port)
        self.assertEqual(out["start"], ["refused", f"RuntimeError: Ollama on 127.0.0.1:{port} (pid {proc.pid}) is not "
                                                   f"GPU0-only: CUDA_VISIBLE_DEVICES=1"])

    def test_nothing_listening_is_still_refused(self):
        proc, port = self.standin("0")
        REAL_OWNER(self.p, "t", port=port)
        self.end(proc)                                                   # recorded, then gone: nothing listens
        out = self.check(port)
        self.assertEqual(out["start"], ["refused", f"RuntimeError: no Ollama listening on 127.0.0.1:{port}"])
        self.assertEqual(out["ollama_pids"], ["accepted", []])          # gpu0's own answer: no Ollama process
        self.assertEqual(REAL_OWNER(self.p, "t2", port=port)["why"], "nothing listens")

    def test_an_owner_that_cannot_be_identified_is_not_accepted(self):
        """The recorded pid is not the process that is there now (its start time differs: a restarted Ollama), or the
        listener now is another process's: nothing is presented, and both checks refuse."""
        proc, port = self.standin("0")
        REAL_OWNER(self.p, "t", port=port)
        with open(os.path.join(LO.owner_dir(self.p, "t"), "start"), "w") as f:
            f.write("1")                                                 # another process instance than the one live
        out = self.check(port)
        self.assertEqual(out["start"], ["refused", f"RuntimeError: no Ollama listening on 127.0.0.1:{port}"])
        self.assertIn("pid is not visible", out["ollama_pids"][1])
        self.end(proc)                                                   # a new listener on the same port, not recorded
        proc2, _ = self.standin("0", port=port)
        REAL_OWNER(self.p, "x", port=port)                               # (the record of ANOTHER namespace)
        out = self.check(port)
        self.assertEqual(out["start"], ["refused", f"RuntimeError: no Ollama listening on 127.0.0.1:{port}"])

    def test_only_the_two_variables_the_check_reads_are_copied(self):
        proc, port = self.standin("0", extra={"PP_TEST_SECRET_TOKEN": "never-copied", "OLLAMA_HOST": "127.0.0.1:1"})
        rec = REAL_OWNER(self.p, "t", port=port)
        with open(os.path.join(LO.owner_dir(self.p, "t"), "environ"), "rb") as f:
            self.assertEqual(f.read(), b"CUDA_VISIBLE_DEVICES=0\0OLLAMA_HOST=127.0.0.1:1\0")
        self.assertNotIn("never-copied", json.dumps(rec))

    def test_every_namespace_carries_the_bridge(self):
        self.assertIn(LO.owner_bridge(self.p, "scorer"), LO.ns_script(self.p, "scorer", LO.tops()))
        self.assertIn(LO.owner_bridge(self.p, "render"), LO.ns_script(self.p, "render", LO.tops(), offline=True))


class TheOwnerIsRecordedFirst(Live):
    def test_start_records_the_owner_before_each_service(self):
        o = LO.Ops(False, run=self.runner, out=self.said.append, p=self.p)
        with mock.patch.object(LO, "preconditions", lambda *a, **k: True), \
                mock.patch.object(LO, "ollama_owner", lambda p, name, port=LO.OLLAMA_PORT, write=True:
                                  self.events.append(("owner", name)) or _no_owner(p, name)):
            self.assertEqual(LO.start(o), 0)
        order = [e[1] if e[0] == "owner" else e[1][1] for e in self.events if e[0] in ("owner", "cmd")]
        self.assertEqual([x for x in order if x in ("lockcheck", "scorer", "new-session")],
                         ["lockcheck", "new-session", "scorer", "new-session"])


class TheServicesComeUpFirst(Base):
    def test_the_launch_waits_for_each_service_s_own_heartbeat(self):
        """`run` launches only when BOTH experimental sessions are up with their OWN first heartbeat (one service's beat
        never stands in for the other's); not up within the wait: refused, and the run still restores."""
        up = {"=pipeline_lean_lockcheck", "=pipeline_lean_scorer"}

        def sh(cmd, **k):                              # tmux list-panes: "0 " for a pane whose process is alive
            return (0, "0 \n") if cmd[:2] == ["tmux", "list-panes"] and cmd[cmd.index("-t") + 1] in up else (1, "")
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


class OnlyOurProcesses(Base):
    def test_restore_stops_only_whole_argument_matches(self):
        """restore's leftover scan: our namespace wrapper and our services, matched on WHOLE arguments; never a shell or
        a grep that merely mentions the markers, another tool's wrapper, or the launcher (2026-11-25: the substring
        match it had stopped an offline namespace check whose wrapper was named lean-ns-check)."""
        yes = (["bash", "-c", "set -e; mount ...", "lean-ns", "python3", "scripts/lean/serve.py", "lockcheck"],
               ["env", "--unset=PP_LEAN_RUN", "A=1", "unshare", "--user", "--mount", "bash", "-c", "x", "lean-ns", "y"],
               ["python3", "scripts/lean/serve.py", "scorer", "--candidates", "c.json"])
        no = (["bash", "-c", "set -e; mount ...", "lean-ns-check", "python3", "-m", "pytest"],
              ["grep", "-rn", "lean-ns", "docs"], ["bash", "-c", "echo lean-ns scripts/lean/serve.py"],
              ["python3", "-B", "tests/package/lean/lean_ops.py", "restore"], ["less", "scripts/lean/serve.py"])
        self.assertTrue(all(LO.ours_argv(a) for a in yes))
        self.assertFalse(any(LO.ours_argv(a) for a in no))


class OneRunAtATime(Base):
    def test_a_second_run_while_one_is_live_is_refused_and_restores_nothing(self):
        """MUST-FAIL: the one command typed twice: the second copy finds RUN.lock held by the live run and refuses at
        once: no ledger-init, no start, and NO restore (a restore would stop the live run's services)."""
        holder = subprocess.Popen([sys.executable, "-c", textwrap.dedent(f'''
            import fcntl, os, sys, time
            os.makedirs({self.p["run"]!r}, exist_ok=True)
            f = open(os.path.join({self.p["run"]!r}, "RUN.lock"), "a+")
            fcntl.flock(f, fcntl.LOCK_EX); print("HELD", flush=True); time.sleep(30)''')],
            stdout=subprocess.PIPE, text=True, start_new_session=True)
        self.addCleanup(lambda: (holder.kill(), holder.wait()))
        self.assertEqual(holder.stdout.readline().strip(), "HELD")
        said = []
        with mock.patch.object(LO, "restore") as rs, mock.patch.object(LO, "start") as st, \
                mock.patch.object(LO, "spawn_guard") as sg:
            o = LO.Ops(False, out=said.append, p=self.p)
            self.assertEqual(LO.run(o, 172, 6000), 2)
        self.assertEqual((rs.call_count, st.call_count, sg.call_count), (0, 0, 0))
        self.assertTrue(any("another run holds" in x for x in said))
        holder.kill()
        holder.wait()
        self.assertIsNotNone(LO.run_lock(self.p))                         # free once that run has ended


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

    def test_a_service_whose_process_ended_is_not_up(self):
        """A pane kept after its process ended (remain-on-exit, until restore) is not a service up: the launch's
        preflight fails it, even with both heartbeats fresh."""
        def sh(cmd, **k):
            return (0, "1 32\n") if cmd[:2] == ["tmux", "list-panes"] else _sh_down(cmd, **k)
        os.makedirs(self.p["beats"])
        for f in LO.BEAT_FILES.values():
            open(os.path.join(self.p["beats"], f), "w").close()
        o = LO.Ops(True, out=self.said.append, p=self.p)
        with mock.patch.object(LO, "sh", sh), mock.patch.object(LO, "assets_check", lambda out: (True, ["stub"])):
            LO.preconditions(o, "build172", launch=True)
        for n in LO.SESSIONS:
            self.assertTrue(any(x.startswith(f"  [FAIL] experimental {n} up") and "ENDED (exit 32)" in x
                                for x in self.said), self.said)

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
        mock.patch.object(LO, "leftovers", lambda: []), \
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
            self.reap(h)                                  # its guard gone before the next case reuses the folder
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
