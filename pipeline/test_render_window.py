#!/usr/bin/env python3
"""The verifier's rows 13 and 18 (docs/audits/FIX_VERIFICATION_2026-11-24.md): the render re-checked neither ruling
76's 12 hours on its own clock nor the cap of 3 kinds of review flag (rulings 136 (2) / 155 (1) / 159), so
scripts/integrator/check_pin_only.py said READY on pin afd8977d (sources 14-19 h old at 08:00 ET Nov 24; 5 kinds).
Now: check_pin_only refuses both, judged by the builder's own package_pin.window_problems / review_problems on the
render clock; the launcher runs it before anything is locked or started for a pinned run, whoever launches; and the
render's stage_pinned re-checks the 12 hours on its own clock before any download. Real data: afd8977d's frozen pin.
Run: cd ~/protocol_pulse && python3 -m pytest -q pipeline/test_render_window.py"""
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock

PIPELINE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(PIPELINE)
sys.path.insert(0, PIPELINE)
import run_fresh as RF  # noqa: E402

PIN = "/home/ultron/protocol_pulse/data/moments_pins/MOMENTS_PIN_LEDGER_033614.json"   # afd8977d, read only
BUILDER = "/home/ultron/worktrees/pp-selectid/pipeline/package_pin.py"
SEALED = dt.datetime(2026, 11, 24, 3, 36, 14, tzinfo=dt.timezone.utc)   # its seal: sources 5.0-9.6 h old
UTC = dt.timezone.utc


def check_pin_only():
    sys.path.insert(0, os.path.join(REPO, "scripts", "integrator"))
    try:
        import check_pin_only as C
    finally:
        sys.path.remove(os.path.join(REPO, "scripts", "integrator"))
    return C


@unittest.skipUnless(os.path.exists(PIN) and os.path.exists(BUILDER), "afd8977d's pin or the builder's package_pin")
class TestReadiness(unittest.TestCase):
    def test_row_13_an_expired_pin_is_not_ready(self):
        C = check_pin_only()
        ok, msg = C.main(PIN, now=SEALED + dt.timedelta(hours=3))        # its oldest source passes 12 h
        self.assertFalse(ok)
        self.assertTrue(msg.startswith("window: ruling 76: duqpCH2snqE was published 2026-11-23T18:00:37Z"), msg)
        self.assertNotIn("0shaXx_n870", msg)                             # the two younger ones are still in time
        ok, msg = C.main(PIN)                                            # the real clock: all three expired
        self.assertFalse(ok)
        self.assertEqual(msg.count("expired"), 3, msg)

    def test_row_18_more_than_3_kinds_is_not_ready_and_nothing_else_refuses_it(self):
        C = check_pin_only()
        ok, msg = C.main(PIN, now=SEALED)
        self.assertEqual((ok, msg), (False, "review flags: 5 kinds of review flag, over 3 (rulings 136 (2) / 155 (1) "
                                            "/ 159)"))
        pp = C.builder_pin()
        quiet = types.SimpleNamespace(**{k: getattr(pp, k) for k in dir(pp) if not k.startswith("__")})
        quiet.review_problems = lambda mp: []
        with mock.patch.object(C, "builder_pin", return_value=quiet):    # control: the kinds alone refused it
            ok, msg = C.main(PIN, now=SEALED)
        self.assertTrue(ok, msg)
        self.assertTrue(msg.startswith("READY (pin only) afd8977d143eb66a"), msg)

    def test_the_render_clock_has_a_zone(self):
        C = check_pin_only()
        with self.assertRaises(ValueError):
            C.main(PIN, now=dt.datetime(2026, 11, 24, 3, 36, 14))


@unittest.skipUnless(os.path.exists(PIN), "afd8977d's pin")
class TestLauncher(unittest.TestCase):
    def test_a_pin_that_is_not_ready_starts_nothing(self):
        d = tempfile.mkdtemp(prefix="r160_launch_")
        self.addCleanup(shutil.rmtree, d, True)
        pin = os.path.join(d, "pin.json")
        shutil.copy(PIN, pin)
        env = {k: v for k, v in os.environ.items() if k not in ("TMUX", "TMUX_PANE")}
        before = subprocess.run(["tmux", "ls"], capture_output=True, text=True).stdout.count("pipeline_pulse_check_")
        r = subprocess.run(["bash", os.path.join(REPO, "scripts", "pulse_check_run.sh"), "--pinned", pin],
                           capture_output=True, text=True, timeout=120, env=env)
        after = subprocess.run(["tmux", "ls"], capture_output=True, text=True).stdout.count("pipeline_pulse_check_")
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        self.assertIn("window: ruling 76:", r.stdout)
        self.assertIn("the pin is not READY", r.stderr)
        self.assertNotIn("started in tmux session", r.stdout)
        self.assertEqual(after, before)


class TestRenderClock(unittest.TestCase):
    NOW = dt.datetime(2026, 11, 24, 13, 0, tzinfo=UTC)
    CASES = [[{"video_id": "a", "source_published_at": "2026-11-24T02:00:00Z"}],              # 11.0 h: in time
             [{"video_id": "b", "source_published_at": "2026-11-24T00:54:00Z"}],              # 12.1 h: expired
             [{"video_id": "c", "published_at": "2026-11-24T05:00:00+00:00"}],                # the other key
             [{"video_id": "d", "source_published_at": "2026-11-24T05:00:00"}],               # no zone
             [{"video_id": "e"}], [{"video_id": "f", "source_published_at": "yesterday"}], []]

    @unittest.skipUnless(os.path.exists(BUILDER), "the builder's package_pin")
    def test_the_render_judges_the_window_as_the_builder_does(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("pp_pin_r160", BUILDER)
        pp = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(pp)
        self.assertEqual(RF.WINDOW_H, pp.WINDOW_H)
        for segs in self.CASES:
            self.assertEqual(RF.window_problems(segs, self.NOW), pp.window_problems(segs, self.NOW), segs)
        self.assertEqual([bool(RF.window_problems(s, self.NOW)) for s in self.CASES],
                         [False, True, False, True, True, True, False])
        with self.assertRaises(ValueError):
            RF.window_problems(self.CASES[0], self.NOW.replace(tzinfo=None))

    def stage(self, pin_body, ready=(True, "READY (stub)")):
        """stage_pinned on a pin file with pin_ready stubbed; -> the Hold's text, or 'reached GPU0'."""
        d = tempfile.mkdtemp(prefix="r160_stage_")
        self.addCleanup(shutil.rmtree, d, True)
        pin = os.path.join(d, "pin.json")
        with open(pin, "w") as f:
            f.write(pin_body if isinstance(pin_body, str) else json.dumps(pin_body))
        run = types.SimpleNamespace(dir=d, prov={}, status={})

        class Reached(Exception):
            pass
        with mock.patch.object(RF, "free_gpu0_for_whisper", side_effect=Reached), \
                mock.patch.object(RF, "pin_ready", return_value=ready), \
                mock.patch("datetime.datetime", wraps=dt.datetime) as clock:
            clock.now.return_value = self.NOW
            try:
                RF.stage_pinned(run, pin)
            except RF.Hold as h:
                return str(h)
            except Reached:
                return "reached GPU0"
        return "returned"

    def test_stage_pinned_holds_before_gpu0_and_any_download(self):
        self.assertEqual(self.stage({"segments": self.CASES[0]}), "reached GPU0")      # ready and in time
        got = self.stage({"segments": self.CASES[1]})
        self.assertTrue(got.startswith("pinned decision rejected: ruling 76, the render clock: ruling 76: b was"), got)
        got = self.stage({"segments": self.CASES[0]}, ready=(False, "review flags: 5 kinds of review flag, over 3"))
        self.assertEqual(got, "pinned decision rejected: not READY (scripts/integrator/check_pin_only.py): review "
                              "flags: 5 kinds of review flag, over 3")
        got = self.stage("{not json")
        self.assertTrue(got.startswith("pinned decision rejected: the pin is not readable (JSONDecodeError"), got)

    @unittest.skipUnless(os.path.exists(PIN) and os.path.exists(BUILDER), "afd8977d's pin or the builder's package_pin")
    def test_the_render_runs_the_readiness_check_itself(self):
        """run_fresh.py started without the launcher: pin_ready runs check_pin_only in its own process on the real pin
        (the builder's package_pin, the real clock): afd8977d's sources are past 12 h."""
        ok, why = RF.pin_ready(PIN)
        self.assertFalse(ok)
        self.assertTrue(why.startswith("window: ruling 76: 0shaXx_n870 was published"), why)
        d = tempfile.mkdtemp(prefix="r160_real_")
        self.addCleanup(shutil.rmtree, d, True)
        with mock.patch.object(RF, "free_gpu0_for_whisper", side_effect=AssertionError("GPU0 reached")):
            with self.assertRaises(RF.Hold) as cm:
                RF.stage_pinned(types.SimpleNamespace(dir=d, prov={}, status={}), PIN)
        self.assertIn("not READY (scripts/integrator/check_pin_only.py): window: ruling 76", str(cm.exception))
        ok, why = RF.pin_ready(os.path.join(d, "no_such_pin.json"))
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()
