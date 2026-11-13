#!/usr/bin/env python3
"""Law L-r as 'EVERY GPU HAS ONE OWNER AT A TIME' (PBX 2026-11-12, the GPU1 quarantine lifted; orchestrator '22:50'):
the gpu0 module's lease, swap and foreign rules per GPU. Must-fail (the order's three): two loads that cannot coexist on
one GPU are serialised by the lease and never land on a full GPU; a GPU1 caller without the GPU1 lease is refused; a
foreign process is waited out, then held with its name. Also: the gpu0 API is unchanged (test_gpu0, 45 tests); a named
co-tenant within its cap is not foreign, over it is; keys pinned to GPU1 never load on GPU0; ollama_call asks with
keep_alive 0, confirms the unload and leaves the lease free; the peak sampler keeps a table per GPU. CPU only: fake
nvidia-smi / Ollama readings (test_gpu0.Box), real flocks and real processes."""
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gpu0  # noqa: E402
from test_gpu0 import Box  # noqa: E402


class Gpu1Box(Box):
    """test_gpu0.Box plus a private GPU1 lease file and a recording Ollama fake."""

    def setUp(self):
        super().setUp()
        self.env1 = mock.patch.dict(os.environ, {"PP_GPU1_LEASE": os.path.join(self.tmp, "lease1")})
        self.env1.start()
        self.addCleanup(self.env1.stop)
        self.asked = []
        saved1 = dict(gpu0._ollama_ours_by[1])
        gpu0._ollama_ours_by[1].clear()
        self.addCleanup(lambda: (gpu0._ollama_ours_by[1].clear(), gpu0._ollama_ours_by[1].update(saved1)))

        def ollama(path, body=None, timeout=30):
            if path == "/api/ps":
                return {"models": [{"name": n, "size_vram": 0} for n in self.ollama]}
            self.asked.append((gpu0.current_gpu(), path, dict(body or {})))
            if body and body.get("model") and body["model"] not in self.ollama:
                self.ollama.append(body["model"])                     # the request loads it ...
            return {"message": {"content": "ok"}}
        p = mock.patch.object(gpu0, "_ollama", side_effect=ollama)
        p.start()
        self.addCleanup(p.stop)

    def hold_lease_in_another_process(self, seconds):
        """A real second process that takes the GPU1 lease (flock) and holds it for `seconds`."""
        path = os.environ["PP_GPU1_LEASE"]
        code = ("import fcntl, json, os, sys, time; f = open(sys.argv[1], 'a+'); fcntl.flock(f, fcntl.LOCK_EX); "
                "f.seek(0); f.truncate(); json.dump({'pid': os.getpid(), 'owner': 'word-pass worker (test)'}, f); "
                "f.flush(); print('held', flush=True); time.sleep(float(sys.argv[2]))")
        p = subprocess.Popen([sys.executable, "-c", code, path, str(seconds)], stdout=subprocess.PIPE, text=True)
        self.addCleanup(p.kill)
        self.assertEqual(p.stdout.readline().strip(), "held")
        return p


class TestSerialisedNeverOOM(Gpu1Box):
    def test_a_second_load_waits_for_the_lease_holder_and_then_runs(self):
        holder = self.hold_lease_in_another_process(1.5)
        t0 = time.time()
        gpu0.ollama_call(1, "qwen3-coder:30b", "/api/chat", {"messages": []}, "watchdog health (test)", wait_s=30)
        self.assertGreaterEqual(time.time() - t0, 1.0)                 # it waited for the other process to leave
        self.assertEqual(holder.wait(timeout=5), 0)
        self.assertEqual([(g, b["model"], b["keep_alive"]) for g, _, b in self.asked], [(1, "qwen3-coder:30b", 0)])

    def test_a_busy_lease_is_a_LeaseBusy_naming_the_holder_never_a_concurrent_load(self):
        self.hold_lease_in_another_process(30)
        with self.assertRaisesRegex(gpu0.LeaseBusy, "GPU1 lease is held by word-pass worker \\(test\\)"):
            gpu0.ollama_call(1, "qwen3-coder:30b", "/api/chat", {"messages": []}, "watchdog health (test)", wait_s=0.5)
        self.assertEqual(self.asked, [])                               # nothing asked of the Ollama

    def test_a_full_gpu_is_never_loaded_into(self):
        self.used[0] = 23000                                           # the GPU's own Ollama still holds 23 GB
        self.procs[:] = [(999999, "ollama", 23000)]                    # (accounted for: not foreign, just not free)
        with self.assertRaisesRegex(gpu0.Gpu0NotFree, "GPU1 has 1564 MiB free 1.0s after the swap"):
            gpu0.ollama_call(1, "qwen3-coder:30b", "/api/chat", {"messages": []}, "t", wait_s=1)
        self.assertEqual(self.asked, [])

        def freed():
            self.procs[:] = [(999999, "ollama", 200)]
            self.used[0] = 300
        threading.Timer(0.5, freed).start()                            # ... it frees: the load proceeds
        gpu0.ollama_call(1, "qwen3-coder:30b", "/api/chat", {"messages": []}, "t", wait_s=5)
        self.assertEqual(len(self.asked), 1)

    def test_two_threads_of_one_process_are_serialised_too(self):
        inside, overlap = [0], [False]
        real = gpu0._ollama.side_effect

        def slow(path, body=None, timeout=30):
            if path != "/api/ps":
                inside[0] += 1
                overlap[0] = overlap[0] or inside[0] > 1
                time.sleep(0.3)
                inside[0] -= 1
            return real(path, body, timeout)
        gpu0._ollama.side_effect = slow
        ts = [threading.Thread(target=gpu0.ollama_call, args=(1, "qwen3-coder:30b", "/api/chat", {}, f"site {i}"),
                               kwargs={"wait_s": 10}) for i in range(3)]
        [t.start() for t in ts]
        [t.join(timeout=20) for t in ts]
        self.assertFalse(overlap[0])
        self.assertEqual(len(self.asked), 3)


class TestGpu1NeedsItsLease(Gpu1Box):
    def test_a_gpu1_load_without_the_gpu1_lease_is_refused(self):
        """Audit batch 45 B (consensus): no lease is refused; holding only GPU0's lease is still refused; holding GPU1's
        lease the same load proceeds (the refusal is the lease, nothing else)."""
        import contextlib
        with mock.patch.dict(os.environ, {"CUDA_VISIBLE_DEVICES": "1"}):
            self.assertEqual(gpu0.current_gpu(), 1)
            with self.assertRaisesRegex(gpu0.LeaseMissing, "a GPU1 load without the GPU1 lease"):
                gpu0.swap_to("whisper:large-v3")
            stack = contextlib.ExitStack()
            with gpu0._on(0):
                stack.enter_context(gpu0.lease("holding GPU0 only"))
            with stack:
                with gpu0._on(0):
                    self.assertTrue(gpu0.held())                       # GPU0's lease IS held here ...
                self.assertFalse(gpu0.held())                          # ... GPU1's is not
                with self.assertRaisesRegex(gpu0.LeaseMissing, "a GPU1 load without the GPU1 lease"):
                    gpu0.swap_to("ollama:qwen3-coder:30b")
                with self.assertRaisesRegex(gpu0.LeaseMissing, "a GPU1 load without the GPU1 lease"):
                    gpu0.swap_to("whisper:large-v3")
            with gpu0.lease("the word-pass worker (test)"):            # the positive control
                ev = gpu0.swap_to("whisper:large-v3")
                self.assertEqual(ev["gpu"], 1)

    def test_a_process_works_on_one_gpu(self):
        with gpu0.lease("t"):                                          # a GPU0 process ...
            with self.assertRaisesRegex(gpu0.LeaseMissing, "this caller works on GPU0"):
                gpu0.swap_to("whisper:large-v3", gpu=1)                # ... cannot swap onto GPU1
        with mock.patch.dict(os.environ, {"CUDA_VISIBLE_DEVICES": "0,1"}), self.assertRaisesRegex(
                gpu0.LeaseMissing, "one GPU per process"):
            gpu0.require("whisper:large-v3")

    def test_each_gpu_has_its_own_lease_file(self):
        self.assertNotEqual(gpu0.lease_path(), os.path.realpath(os.environ["PP_GPU1_LEASE"]))
        with gpu0._on(1):
            self.assertEqual(gpu0.lease_path(), os.path.realpath(os.environ["PP_GPU1_LEASE"]))
        with mock.patch.dict(os.environ, {"PP_GPU1_LEASE": ""}):
            os.environ.pop("PP_GPU1_LEASE")
            with gpu0._on(1):
                self.assertEqual(gpu0.lease_path(), "/tmp/pulse_gpu1.lease")
        with self.assertRaises(gpu0.LeaseMissing):
            with gpu0._on(2):
                pass


class TestForeignWaitedOutThenNamed(Gpu1Box):
    def test_a_foreign_gpu1_process_is_waited_out_then_held_by_name(self):
        self.procs[:] = [(424242, "python3", 9000)]
        with mock.patch.object(gpu0, "FOREIGN_WAIT_S", 0.4), mock.patch.object(gpu0, "FOREIGN_POLL_S", 0.05), \
                self.assertRaisesRegex(gpu0.Gpu0Foreign, "GPU1 is used by something that is not this run's.*pid 424242 "
                                                         "python3 9000 MiB"):
            gpu0.ollama_call(1, "qwen3-coder:30b", "/api/chat", {}, "t", wait_s=5)
        self.assertEqual(self.asked, [])
        ev = [e for e in gpu0.events() if e.get("key") == "foreign_wait"][-1]
        self.assertEqual((ev["gpu"], ev["left"]), (1, False))

    def test_a_foreign_process_that_leaves_during_the_wait_is_not_held(self):
        self.procs[:] = [(424242, "python3", 9000)]
        threading.Timer(0.2, lambda: self.procs.clear()).start()
        with mock.patch.object(gpu0, "FOREIGN_WAIT_S", 5), mock.patch.object(gpu0, "FOREIGN_POLL_S", 0.05):
            gpu0.ollama_call(1, "qwen3-coder:30b", "/api/chat", {}, "t", wait_s=5)
        self.assertEqual(len(self.asked), 1)


class TestCoTenantAndPinnedKeys(Gpu1Box):
    def test_the_website_within_its_cap_is_a_co_tenant_over_it_foreign(self):
        out = subprocess.run(["setsid", "sh", "-c", f"{sys.executable} -c 'import time; time.sleep(30)' -m waitress "
                              f"app:app >/dev/null 2>&1 & echo $!"], capture_output=True, text=True, timeout=10)
        pid = int(out.stdout.strip())                                  # double-forked: NOT a descendant of this process

        class Site:
            pass
        site = Site()
        site.pid = pid
        self.addCleanup(lambda: os.kill(pid, 9))
        t0 = time.time()                                               # its own argv once it has exec'd
        while b"waitress" not in open(f"/proc/{pid}/cmdline", "rb").read() and time.time() - t0 < 5:
            time.sleep(0.02)
        self.assertNotIn(pid, gpu0._descendants())
        with gpu0._on(1):
            self.procs[:] = [(site.pid, "python3", 480)]
            self.assertEqual(gpu0.foreign(), [])
            self.procs[:] = [(site.pid, "python3", 2048)]
            self.assertEqual([p for p, _, _ in gpu0.foreign()], [site.pid])
            self.procs[:] = [(site.pid, "python3", None)]
            self.assertEqual([p for p, _, _ in gpu0.foreign()], [site.pid])
        with gpu0._on(0):                                              # no co-tenant is named on GPU0
            self.procs[:] = [(site.pid, "python3", 480)]
            self.assertEqual([p for p, _, _ in gpu0.foreign()], [site.pid])

    def test_a_key_pinned_to_gpu1_never_loads_on_gpu0(self):
        with gpu0.lease("t"):
            with self.assertRaisesRegex(gpu0.Gpu0NotFree, "pinned to GPU1 by the layout"):
                gpu0.swap_to("ollama:deepseek-coder-v2:16b")
        self.assertEqual(gpu0.ON_GPU, {"ollama:qwen3-coder:30b": 1, "ollama:deepseek-coder-v2:16b": 1})


class TestOllamaCallLeavesTheGpuAsFound(Gpu1Box):
    def test_keep_alive_0_the_unload_confirmed_the_lease_free(self):
        out = gpu0.ollama_call(1, "qwen3-coder:30b", "/api/chat", {"messages": [{"role": "user", "content": "x"}],
                                                                    "stream": False}, "t")
        self.assertEqual(out, {"message": {"content": "ok"}})
        g, path, body = self.asked[0]
        self.assertEqual((g, path, body["model"], body["keep_alive"], body["stream"]), (1, "/api/chat", "qwen3-coder:30b",
                                                                                       0, False))
        self.assertIn("qwen3-coder:30b", self.unloaded)                 # confirmed gone before the lease went
        self.assertEqual(self.ollama, [])
        with gpu0._on(1):
            self.assertIsNone(gpu0.holder())
        self.assertEqual(gpu0.current_gpu(), 0)                        # the caller's own GPU is unchanged


class TestPeaksPerGpu(Gpu1Box):
    def test_the_sampler_keeps_a_table_per_gpu(self):
        s = gpu0.PeakSampler(interval_s=0.05).start()
        s.set("render")
        time.sleep(0.15)
        peaks = s.stop()
        self.assertEqual(set(s.peaks_by_gpu), {0, 1})
        self.assertEqual(s.peaks_by_gpu[0]["render"], peaks["render"])
        self.assertIn("render", s.peaks_by_gpu[1])


if __name__ == "__main__":
    unittest.main(verbosity=2)
