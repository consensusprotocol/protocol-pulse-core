#!/usr/bin/env python3
"""transcript_ingest's Whisper pass under law L-r (no lease, no load), without network, GPU or a model.

The pass loads only while this process holds the GPU0 lease, and leaves it after Whisper is unloaded. A render's yield
flag stops the pass: the remaining videos wait for the next run. Orchestrator order '13:05' ET Nov 16 (pp-ingest's
request R13): a lease another owner holds, or a build's GPU0 service that wants the card (gpu0_want), is WAITED for.
The pass polls, holds nothing while it waits, and waits at most LEASE_WAIT_S in all; each attempt is non-blocking. A
build that wants GPU0 mid-pass gets it at the next file boundary, and Whisper goes on after it. Before the order, one
busy moment at the cron's start deferred every video for 30 minutes. main() sets the PCI bus order. From Nov 12 to
Nov 15, every cron run that needed Whisper died on gpu0.LeaseMissing (the pass never took the lease).

Each load in these tests runs the real gpu0.require, the store's own check before any Whisper load. The lease is
real, on the test's private file; a busy lease is held by ANOTHER process, the way the scorer or a render holds it."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

PIPELINE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PIPELINE)
import gpu0  # noqa: E402
import gpu0_want as W  # noqa: E402
import local_judge as LJ  # noqa: E402
import transcript_ingest as TI  # noqa: E402

HOLDER = """import fcntl, json, os, sys
f = open(sys.argv[1], "a+")
fcntl.flock(f, fcntl.LOCK_EX)
f.seek(0); f.truncate(); json.dump({"pid": os.getpid(), "owner": "pin-stage clip scorer", "since": 0}, f); f.flush()
print("held", flush=True)
sys.stdin.read()
"""
VIDS = ("v1", "v2", "v3")


def video(i):
    return {"video_id": f"v{i}", "rss": {}, "age_h": float(i),
            "channel": {"channel_id": f"UC{i}", "display_name": f"Channel {i}", "tier": 1}}


class TestWhisperPass(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="ti_")
        self.addCleanup(shutil.rmtree, self.tmp)
        self.lease = os.path.join(self.tmp, "gpu0.lease")
        self.flag = os.path.join(self.tmp, "gpu0.yield")
        self.loads, self.unloads = [], []

        def acquire(video_id, rss=None, channel=None, allow_whisper=True, try_captions=True, **k):
            if not allow_whisper:
                return None, "pending_whisper"                        # the caption pass: every video needs Whisper
            gpu0.require(f"whisper:test {video_id}")                   # the store's own L-r check, before any load
            self.loads.append(video_id)
            return {"video_id": video_id}, "whisper"

        def release():
            self.unloads.append(gpu0.held())                           # unloaded while the lease is still held?

        env = {"CUDA_VISIBLE_DEVICES": "0", "CUDA_DEVICE_ORDER": "PCI_BUS_ID", "PP_GPU0_LEASE": self.lease}
        for p in (mock.patch.object(TI, "universe", lambda hours, channels=None: [video(1), video(2), video(3)]),
                  mock.patch.object(TI, "production_running", lambda: False),
                  mock.patch.object(TI.ts, "acquire", acquire),
                  mock.patch.object(TI.ts, "ensure_meta", lambda vid, rss=None, channel=None: {"duration": 600}),
                  mock.patch.object(TI.ts, "caption_circuit_open", lambda: False),
                  mock.patch.object(TI.ts, "release_whisper", release),
                  mock.patch.object(TI.ts, "STATE_DIR", self.tmp),
                  mock.patch.object(LJ, "YIELD_FLAG", self.flag),
                  mock.patch.object(W, "DIR", os.path.join(self.tmp, "want")),
                  mock.patch.object(TI, "LEASE_WAIT_S", 0.5, create=True),     # the tests' own short wait
                  mock.patch.object(TI, "LEASE_POLL_S", 0.05, create=True),
                  mock.patch.dict(os.environ, env)):
            p.start()
            self.addCleanup(p.stop)

    def run_ingest(self):
        return TI.ingest(hours=72, max_whisper_hours=4, log=lambda s: None)

    def statuses(self, s):
        return [s["status"][v] for v in VIDS]

    def hold(self):
        p = subprocess.Popen([sys.executable, "-c", HOLDER, self.lease], stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, text=True)
        self.addCleanup(p.wait, 10)
        self.addCleanup(p.stdout.close)
        self.addCleanup(p.stdin.close)                                  # EOF: the holder leaves
        self.assertEqual(p.stdout.readline().strip(), "held")
        return p

    def lease_spy(self):
        taken, real = [], gpu0.lease
        return taken, mock.patch.object(gpu0, "lease", lambda *a, **k: taken.append((a, k)) or real(*a, **k))

    def test_whisper_loads_only_under_the_gpu0_lease_and_leaves_it_after_unloading(self):
        s = self.run_ingest()
        self.assertEqual(self.loads, list(VIDS))
        self.assertEqual(self.statuses(s), ["whisper"] * 3)
        self.assertEqual(self.unloads, [True])                         # once, before the lease went
        self.assertFalse(gpu0.held())
        self.assertIsNone(gpu0.holder())                               # the lease is free again
        with open(os.path.join(self.tmp, "ingest_runs.jsonl")) as f:
            self.assertEqual(json.loads(f.readlines()[-1])["counts"], {"whisper": 3})

    def test_an_uncontended_pass_takes_the_lease_once_and_never_blocks_on_it(self):
        taken, spy = self.lease_spy()
        with spy:
            self.run_ingest()
        self.assertEqual(len(taken), 1)
        self.assertEqual(taken[0][1].get("wait_s"), 0)

    def test_a_lease_held_past_the_wait_defers_every_video(self):
        self.hold()
        t0 = time.time()
        s = self.run_ingest()
        self.assertLess(time.time() - t0, 5)                           # the wait is bounded (LEASE_WAIT_S)
        self.assertEqual(self.loads, [])
        self.assertEqual(self.statuses(s), ["deferred_gpu0_busy"] * 3)
        self.assertEqual(self.unloads, [])                             # nothing taken, nothing to leave

    def release_later(self, holder, after=0.4):
        threading.Timer(after, holder.stdin.close).start()           # EOF: the other owner leaves

    def test_order_1305_a_lease_freed_while_waiting_lets_whisper_run(self):
        self.release_later(self.hold())
        with mock.patch.object(TI, "LEASE_WAIT_S", 10.0, create=True):
            s = self.run_ingest()
        self.assertEqual(self.statuses(s), ["whisper"] * 3)
        self.assertEqual(self.loads, list(VIDS))
        self.assertIsNone(gpu0.holder())

    def test_order_1305_a_build_wanting_gpu0_keeps_whisper_off_the_lease_until_done(self):
        W.want("stand_alone_scorer")
        cleared, attempts, real = [], [], gpu0.lease

        def done():
            cleared.append(time.time())
            W.done("stand_alone_scorer")
        threading.Timer(0.4, done).start()
        with mock.patch.object(TI, "LEASE_WAIT_S", 10.0, create=True), \
                mock.patch.object(gpu0, "lease", lambda *a, **k: attempts.append(time.time()) or real(*a, **k)):
            s = self.run_ingest()
        self.assertEqual(self.statuses(s), ["whisper"] * 3)
        self.assertTrue(attempts and cleared and min(attempts) >= cleared[0], (attempts, cleared))   # builds first

    def test_order_1305_a_build_wanting_gpu0_mid_pass_gets_it_at_the_next_file_boundary(self):
        inner, seen = TI.ts.acquire, []

        def acquire(video_id, **k):
            r = inner(video_id, **k)
            if k.get("allow_whisper") and video_id == "v1":            # the scorer's burst arrives during v1
                W.want("stand_alone_scorer")
                threading.Timer(0.2, lambda: seen.append((gpu0.held(), gpu0.holder()))).start()
                threading.Timer(0.4, W.done, ("stand_alone_scorer",)).start()
            return r
        taken, spy = self.lease_spy()
        with spy, mock.patch.object(TI.ts, "acquire", acquire), mock.patch.object(TI, "LEASE_WAIT_S", 10.0, create=True):
            s = self.run_ingest()
        self.assertEqual(self.statuses(s), ["whisper"] * 3)            # Whisper went on after the build
        self.assertEqual(self.unloads, [True, True])                   # unloaded at the boundary and at the end
        self.assertEqual(len(taken), 2)
        self.assertEqual(seen, [(False, None)])                        # during the build's turn GPU0 was free
        self.assertIsNone(gpu0.holder())

    def test_order_1305_a_build_wanting_gpu0_past_the_wait_defers_the_rest(self):
        W.want("stand_alone_scorer")                                    # fresh for FRESH_S, past the 0.5 s wait
        taken, spy = self.lease_spy()
        with spy:
            s = self.run_ingest()
        self.assertEqual(self.statuses(s), ["deferred_gpu0_busy"] * 3)
        self.assertEqual((self.loads, taken), ([], []))                # never even asked for the lease

    def test_order_1305_a_stale_want_does_not_hold_whisper_back(self):
        W.want("stand_alone_scorer")                                    # a scorer that died long ago
        old = time.time() - W.FRESH_S - 5
        os.utime(os.path.join(W.DIR, "stand_alone_scorer.json"), (old, old))
        taken, spy = self.lease_spy()
        with spy:
            s = self.run_ingest()
        self.assertEqual(self.statuses(s), ["whisper"] * 3)
        self.assertEqual(len(taken), 1)

    def test_order_1305_a_render_asking_while_whisper_waits_stops_the_pass_without_the_lease(self):
        self.hold()
        threading.Timer(0.3, lambda: open(self.flag, "w").close()).start()
        t0 = time.time()
        with mock.patch.object(TI, "LEASE_WAIT_S", 10.0, create=True):
            s = self.run_ingest()
        self.assertLess(time.time() - t0, 5)                           # it stops at once, not at the wait's end
        self.assertEqual(self.statuses(s), ["deferred_render_wants_gpu0"] * 3)
        self.assertEqual((self.loads, self.unloads), ([], []))

    def test_the_render_yield_flag_defers_the_pass_before_the_lease_is_taken(self):
        open(self.flag, "w").close()
        taken, spy = self.lease_spy()
        with spy:
            s = self.run_ingest()
        self.assertEqual((self.loads, taken), ([], []))
        self.assertEqual(self.statuses(s), ["deferred_render_wants_gpu0"] * 3)

    def test_a_flag_raised_mid_pass_stops_it_after_the_video_in_hand_and_leaves_the_lease(self):
        inner = TI.ts.acquire

        def acquire(video_id, **k):
            r = inner(video_id, **k)
            if k.get("allow_whisper") and video_id == "v1":
                open(self.flag, "w").close()                           # the launcher touches the flag during v1
            return r
        with mock.patch.object(TI.ts, "acquire", acquire):
            s = self.run_ingest()
        self.assertEqual(self.loads, ["v1"])
        self.assertEqual(self.statuses(s), ["whisper", "deferred_render_wants_gpu0", "deferred_render_wants_gpu0"])
        self.assertEqual(self.unloads, [True])
        self.assertIsNone(gpu0.holder())

    def test_a_refusal_inside_the_pass_still_unloads_whisper_and_leaves_the_lease(self):
        def oom(video_id, allow_whisper=True, **k):
            if not allow_whisper:
                return None, "pending_whisper"
            raise gpu0.GpuOOM("CUDA out of memory")
        with mock.patch.object(TI.ts, "acquire", oom):
            with self.assertRaises(gpu0.GpuOOM):
                self.run_ingest()
        self.assertEqual(self.unloads, [True])
        self.assertIsNone(gpu0.holder())

    def test_a_production_run_still_defers_the_pass_without_the_lease(self):
        taken, spy = self.lease_spy()
        with spy, mock.patch.object(TI, "production_running", lambda: True):
            s = self.run_ingest()
        self.assertEqual((self.loads, taken), ([], []))
        self.assertEqual(self.statuses(s), ["deferred_production_running"] * 3)


class TestMain(unittest.TestCase):
    def test_main_sets_the_pci_bus_order_before_the_ingest(self):
        tmp = tempfile.mkdtemp(prefix="ti_main_")
        self.addCleanup(shutil.rmtree, tmp)
        env = {k: v for k, v in os.environ.items() if k != "CUDA_DEVICE_ORDER"}
        env["CUDA_VISIBLE_DEVICES"] = "0"
        seen = []
        with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(TI.ts, "STATE_DIR", tmp), \
                mock.patch.object(TI, "ingest", lambda *a, **k: seen.append(os.environ.get("CUDA_DEVICE_ORDER"))), \
                mock.patch.object(sys, "argv", ["transcript_ingest.py", "--hours", "1"]):
            TI.main()
        self.assertEqual(seen, ["PCI_BUS_ID"])


if __name__ == "__main__":
    unittest.main()
