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
        """This pin is refused today for more than its kinds: the builder's out_edge row (Nov 24) and ruling 162 (2)'s
        exact-PASS value verdict (its closing line's was FLAGGED). Both are stubbed to pass, so the test isolates the
        kinds wiring."""
        C = check_pin_only()
        pp = C.builder_pin()
        sealed = types.SimpleNamespace(**{k: getattr(pp, k) for k in dir(pp) if not k.startswith("__")})
        sealed.gate_problems = lambda gates, required=None: []
        stub = mock.patch.object(C.edl_rules, "takeaway_value", return_value=(True, "stub"))
        stub.start()
        self.addCleanup(stub.stop)
        with mock.patch.object(C, "builder_pin", return_value=sealed):
            ok, msg = C.main(PIN, now=SEALED)
        self.assertEqual((ok, msg), (False, "review flags: 5 kinds of review flag, over 3 (rulings 136 (2) / 155 (1) "
                                            "/ 159)"))
        quiet = types.SimpleNamespace(**vars(sealed))
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


class TestRenderStage(unittest.TestCase):
    """stage_pinned asks pin_ready (check_pin_only in its own process: the builder's window_problems and
    review_problems, no copy here) before GPU0 or any download, and holds on its answer."""

    def stage(self, ready):
        d = tempfile.mkdtemp(prefix="r160_stage_")
        self.addCleanup(shutil.rmtree, d, True)
        pin = os.path.join(d, "pin.json")
        with open(pin, "w") as f:
            json.dump({"segments": []}, f)

        class Reached(Exception):
            pass
        with mock.patch.object(RF, "free_gpu0_for_whisper", side_effect=Reached), \
                mock.patch.object(RF, "pin_ready", return_value=ready):
            try:
                RF.stage_pinned(types.SimpleNamespace(dir=d, prov={}, status={}), pin)
            except RF.Hold as h:
                return str(h)
            except Reached:
                return "reached GPU0"
        return "returned"

    def test_stage_pinned_holds_on_the_readiness_before_gpu0(self):
        self.assertEqual(self.stage((True, "READY (pin only) ...")), "reached GPU0")
        for why in ("window: ruling 76: b was published 2026-11-24T00:54:00Z, 12.1 h before the render clock (over 12 "
                    "h): expired", "review flags: 5 kinds of review flag, over 3 (rulings 136 (2) / 155 (1) / 159)"):
            self.assertEqual(self.stage((False, why)),
                             f"pinned decision rejected: not READY (scripts/integrator/check_pin_only.py): {why}")

    def test_item_7_the_renders_own_lock_swapping_a_meaning_word_holds(self):
        """ITEM 7: the render's lock (pinned.prepare) adopting the audio's word on a meaning pair ('bought' read as
        'sold'): what the seal refuses, the render refuses, at the pin stage."""
        import pinned
        d = tempfile.mkdtemp(prefix="r160_item7_")
        self.addCleanup(shutil.rmtree, d, True)
        swapped = {"hook": {"selection_lock": {"adjudication": {"pairs": [{"run": "sold", "approved": "bought",
                                                                            "took": "run", "material": False}]}}},
                   "clips": [{"index": 1, "selection_lock": {}}]}

        def prepare(pin_path, run_dir, log=print):
            with open(os.path.join(run_dir, "edl.json"), "w") as f:
                json.dump(swapped, f)
            return {"pin": {"moments_package": {}}, "pin_sha256": "0" * 64, "validation": {}}
        run = types.SimpleNamespace(dir=d, prov={}, status={})
        with mock.patch.object(RF, "pin_admissible", return_value=(True, "READY")), \
                mock.patch.object(RF, "free_gpu0_for_whisper"), mock.patch.object(RF, "prefetch_post_live"), \
                mock.patch.object(pinned, "prepare", prepare):
            with self.assertRaises(RF.Hold) as cm:
                RF.stage_pinned(run, os.path.join(d, "pin.json"))
        self.assertIn("item 7 (no silent meaning swap)", str(cm.exception))
        self.assertIn("'hook': [['bought', 'sold']]", str(cm.exception))

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
        self.assertFalse(RF.pin_ready(os.path.join(d, "no_such_pin.json"))[0])   # unreadable: not READY


if __name__ == "__main__":
    unittest.main()
