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
import json
import os
import shutil
import sys
import tempfile
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
        for patch in (mock.patch.dict(os.environ, {"PP_SPEND_LEDGER_DIR": os.path.join(self.d, "spend")}),
                      mock.patch.object(OC, "OUTCOMES", self.outcomes),
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
        for line in lines:
            for m in LO.MARKERS:
                self.assertNotIn(m, line)
            for b in LO.BOOK.values():
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
        b2 = dict(b, trees={LO.LIVE_MAIN: {"head": "a"}, LO.BOOK["worktree"]: {"head": "b"}})
        bad, notes = LO.compare(b2, dict(b2, trees={LO.LIVE_MAIN: {"head": "a"}, LO.BOOK["worktree"]: {"head": "c"}}))
        self.assertEqual((bad, len(notes)), ([], 1))                   # another session's commit: a note
        bad, _ = LO.compare(b2, dict(b2, trees={LO.LIVE_MAIN: {"head": "x"}, LO.BOOK["worktree"]: {"head": "b"}}))
        self.assertEqual(len(bad), 1)                                     # the live tree moved: named


if __name__ == "__main__":
    unittest.main()
