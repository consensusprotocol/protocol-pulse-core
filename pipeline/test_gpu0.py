#!/usr/bin/env python3
"""Law L-r GPU0 NEVER SURPRISES A RUN (pipeline/gpu0.py): CPU tests with a private lease file and stubbed nvidia-smi /
Ollama readings, so they never touch GPU0. The GPU must-fails (a real allocation on GPU0 before a stage) and the
back-to-back runs with the per-stage peak table are pipeline/test_gpu0_live.py (GPU0, under the lease)."""
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from unittest import mock

PIPELINE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PIPELINE)
import gpu0  # noqa: E402


class Box(unittest.TestCase):
    """A private lease file, CUDA_VISIBLE_DEVICES=0, and a fake GPU0: memory / processes / Ollama are stubs."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="gpu0t_")
        self.env = mock.patch.dict(os.environ, {"PP_GPU0_LEASE": os.path.join(self.tmp, "lease"),
                                                "CUDA_VISIBLE_DEVICES": "0"})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.used = [100]                 # MiB used on the fake GPU0 (a list: tests change it)
        self.procs = []                   # fake GPU0 compute processes
        self.ollama = []                  # fake resident Ollama models
        self.unloaded = []
        for name, fn in (("memory", lambda: (self.used[0], 24564)), ("processes", lambda: list(self.procs)),
                         ("_ollama", lambda path, body=None, timeout=30: {"models": [{"name": n, "size_vram": 0}
                                                                                     for n in self.ollama]}),
                         ("_ollama_pids", lambda: {999999}),
                         ("_ollama_unload", self._unload)):
            p = mock.patch.object(gpu0, name, side_effect=fn)
            p.start()
            self.addCleanup(p.stop)
        saved = (list(gpu0._resident), dict(gpu0._models), list(gpu0._events), dict(gpu0._ollama_ours))
        gpu0._resident.clear()
        gpu0._models.clear()
        gpu0._ollama_ours.clear()

        def restore():
            gpu0._resident[:] = saved[0]
            gpu0._models.clear()
            gpu0._models.update(saved[1])
            gpu0._events[:] = saved[2]
            gpu0._ollama_ours.clear()
            gpu0._ollama_ours.update(saved[3])
        self.addCleanup(restore)

    def _unload(self, names, wait_s=60):
        self.ollama[:] = [n for n in self.ollama if n not in names]
        self.unloaded += list(names)
        for n in names:
            gpu0._ollama_ours.pop(n, None)
        return list(names)


class TestLease(Box):
    def test_no_lease_no_load_and_gpu0_only(self):
        with self.assertRaises(gpu0.LeaseMissing):
            gpu0.require("a load")
        with gpu0.lease("test"):
            gpu0.require("a load")
            with mock.patch.dict(os.environ, {"CUDA_VISIBLE_DEVICES": "0,1"}):
                with self.assertRaisesRegex(gpu0.LeaseMissing, "GPU1 is quarantined"):
                    gpu0.require("a load")
        self.assertFalse(gpu0.held())

    def test_held_is_a_check_never_an_acquisition(self):
        f = open(gpu0.lease_path(), "a+")                # this process has the file open, nobody holds the lock
        self.addCleanup(f.close)
        self.assertFalse(gpu0.held())
        self.assertIsNone(gpu0.holder())                 # still free: held() took nothing
        with gpu0.lease("t"):
            self.assertTrue(gpu0.held())

    def test_a_lease_is_released_by_its_last_holder_across_threads(self):
        import threading
        inside, leave_a, done_b = threading.Event(), threading.Event(), threading.Event()

        def a():
            with gpu0.lease("A"):
                inside.set()
                leave_a.wait(10)

        def b():
            inside.wait(10)
            with gpu0.lease("B"):
                leave_a.set()
                t.join(10)                                # A has left: B must still hold it
                self.assertTrue(gpu0.held())
                self.assertIsNotNone(gpu0.holder())
            done_b.set()
        t = threading.Thread(target=a)
        u = threading.Thread(target=b)
        t.start(); u.start(); u.join(20)
        self.assertTrue(done_b.is_set())
        self.assertIsNone(gpu0.holder())                  # released by the last one out

    def test_reentrant_and_busy_names_the_holder(self):
        with gpu0.lease("outer"):
            with gpu0.lease("inner"):
                self.assertTrue(gpu0.held())
            self.assertTrue(gpu0.held())
            code = textwrap.dedent(f"""
                import sys; sys.path.insert(0, {PIPELINE!r}); import gpu0
                try:
                    with gpu0.lease("second"): print("GOT")
                except gpu0.LeaseBusy as e: print("BUSY", e)""")
            out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=60).stdout
            self.assertIn("BUSY", out)
            self.assertIn("outer", out)                               # the holder is named
        self.assertIsNone(gpu0.holder())

    def test_an_inherited_descriptor_is_custody_a_reopened_one_is_not(self):
        with gpu0.lease("parent"):
            fd = gpu0._own[gpu0.lease_path()]["file"].fileno()
            os.set_inheritable(fd, True)
            code = f"import sys; sys.path.insert(0, {PIPELINE!r}); import gpu0; print(gpu0.held())"
            inherited = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=60,
                                       pass_fds=(fd,)).stdout.strip()
            reopened = subprocess.run([sys.executable, "-c", code + f"; f = open({gpu0.lease_path()!r}, 'a+'); "
                                       "print(gpu0.held())"], capture_output=True, text=True, timeout=60).stdout.split()
        self.assertEqual(inherited, "True")
        self.assertEqual(reopened, ["False", "False"])


class TestSwap(Box):
    def test_a_foreign_process_is_refused_and_named(self):
        self.procs[:] = [(424242, "python3", 4000)]
        with gpu0.lease("t"):
            with self.assertRaisesRegex(gpu0.Gpu0Foreign, "pid 424242 python3 4000 MiB"):
                gpu0.swap_to("whisper:large-v3")

    def test_everything_else_is_unloaded_and_the_memory_proven_free(self):
        built = []
        a = gpu0.model("embedder", lambda: built.append("embedder") or object())
        b = gpu0.whisper("medium")
        self.ollama[:] = ["gemma3:27b"]
        gpu0._ollama_ours["gemma3:27b"] = "resident"                     # this run asked for it earlier
        with gpu0.lease("t"):
            with mock.patch.object(b, "_build", lambda: built.append("medium") or object()):
                a.get()
                self.assertEqual(self.unloaded, ["gemma3:27b"])        # the Ollama model went first
                b.get()
            self.assertEqual(built, ["embedder", "medium"])
            self.assertFalse(a.loaded)                                 # one model at a time
            self.assertTrue(b.loaded)
            ev = gpu0.events()[-1]
            self.assertEqual((ev["key"], ev["unloaded"]), ("whisper:medium", ["embedder"]))

    def test_a_model_this_run_did_not_request_is_foreign_and_left_alone(self):
        self.ollama[:] = ["qwen3-coder:30b"]                            # another client's job on the shared Ollama
        with gpu0.lease("t"):
            with self.assertRaisesRegex(gpu0.Gpu0Foreign, "ollama model qwen3-coder:30b .not requested by this run."):
                gpu0.swap_to("whisper:large-v3")
        self.assertEqual((self.unloaded, self.ollama), ([], ["qwen3-coder:30b"]))   # nothing of it unloaded

    def test_memory_no_listed_process_accounts_for_is_foreign(self):
        self.used[0] = 9000                                              # e.g. a graphics client nvidia-smi does not list
        with gpu0.lease("t"):
            with self.assertRaisesRegex(gpu0.Gpu0Foreign, "no listed compute process accounts for 9000 MiB"):
                gpu0.swap_to("nvenc")

    def test_a_cached_model_is_no_licence_without_the_lease(self):
        m = gpu0.model("embedder", lambda: (lambda x: x * 2))
        with gpu0.lease("t"):
            self.assertEqual(m(21), 42)
        with self.assertRaises(gpu0.LeaseMissing):                      # loaded, but the lease is gone
            m(21)

    def test_a_stored_call_reresolves_and_objects_inside_never_escape(self):
        class Enc:
            name = "enc"
            inner = object()

            def embed(self, x):
                return x
        m = gpu0.model("resemblyzer", Enc)
        with gpu0.lease("t"):
            call = m.embed
            self.assertEqual(m.name, "enc")
            with self.assertRaisesRegex(AttributeError, "an object inside the model"):
                m.inner
            m.unload()                                                   # a later swap deleted it
            self.assertEqual(call(7), 7)                                 # the stored call loads it again
            self.assertTrue(m.loaded)

    def test_ownership_ends_when_the_model_is_seen_gone(self):
        with gpu0.lease("t"):
            gpu0.swap_to("ollama:gemma3:27b")
            self.assertEqual(gpu0._ollama_ours, {"gemma3:27b": "pending"})
            self.ollama[:] = ["gemma3:27b"]                              # our request loaded it
            gpu0.ollama_resident()
            self.assertEqual(gpu0._ollama_ours, {"gemma3:27b": "resident"})
            self.ollama[:] = []                                          # keep-alive expired: seen gone
            gpu0.ollama_resident()
            self.ollama[:] = ["gemma3:27b"]                              # another client loads the same name
            with self.assertRaisesRegex(gpu0.Gpu0Foreign, "not requested by this run"):
                gpu0.swap_to("whisper:medium")
        self.assertEqual(self.unloaded, [])                              # and it is never unloaded

    def test_leave_unloads_this_runs_models_and_nothing_foreign(self):
        m = gpu0.model("embedder", lambda: object())
        with gpu0.lease("t"):
            m.get()
            gpu0._ollama_ours["gemma3:27b"] = "resident"
            self.ollama[:] = ["gemma3:27b", "qwen3-coder:30b"]
            self.assertEqual(gpu0.leave(), ["gemma3:27b"])
        self.assertFalse(m.loaded)
        self.assertEqual((self.unloaded, self.ollama), (["gemma3:27b"], ["qwen3-coder:30b"]))

    def test_release_proves_this_process_let_go_of_its_model(self):
        self.procs[:] = [(os.getpid(), "python3", 2700)]                 # a pinned Whisper medium in this process
        self.used[0] = 2700
        with gpu0.lease("t"):
            with self.assertRaisesRegex(gpu0.Gpu0NotFree, "this process still holds 2700 MiB"):
                gpu0.release_all(wait_s=0, poll_s=0)
            self.procs[:] = [(os.getpid(), "python3", 400)]              # only its CUDA context left
            self.used[0] = 400
            self.assertEqual(gpu0.release_all(wait_s=0)["this_process_mib"], 400)

    def test_a_newcomer_is_never_unloaded_and_an_unreported_memory_proves_nothing(self):
        self.ollama[:] = ["qwen3-coder:30b"]                             # appeared after the foreign check
        with gpu0.lease("t"), mock.patch.object(gpu0, "_refuse_foreign", lambda what: None):
            gpu0.release_all(wait_s=0)
            self.assertEqual(self.unloaded, [])                          # not this run's: never unloaded
            self.procs[:] = [(os.getpid(), "python3", None)]
            with self.assertRaisesRegex(gpu0.Gpu0NotFree, "still holds None MiB"):
                gpu0.release_all(wait_s=0, poll_s=0)

    def test_a_finished_request_leaves_no_pending_ownership(self):
        with gpu0.lease("t"):
            gpu0.swap_to("ollama:gemma3:27b")                            # pending
            gpu0.ollama_settle("gemma3:27b")                             # the request ended (keep_alive 0): gone
            self.assertNotIn("gemma3:27b", gpu0._ollama_ours)
            self.ollama[:] = ["gemma3:27b"]                              # another client's later load
            with self.assertRaisesRegex(gpu0.Gpu0Foreign, "not requested by this run"):
                gpu0.swap_to("nvenc")

    def test_a_swap_that_fails_leaves_no_pending_claim(self):
        self.used[0] = 23000                                            # never free (an idle runner holds it)
        self.procs[:] = [(999999, "ollama", 22900)]
        with gpu0.lease("t"):
            with self.assertRaises(gpu0.Gpu0NotFree):
                gpu0.swap_to("ollama:gemma3:27b", wait_s=0, poll_s=0)
            self.assertNotIn("gemma3:27b", gpu0._ollama_ours)             # no request followed: no claim stays

    def test_decoding_continues_only_under_the_lease(self):
        it = gpu0.guard_iter(iter([1, 2]), "decode")
        with gpu0.lease("t"):
            self.assertEqual(next(it), 1)
        with self.assertRaises(gpu0.LeaseMissing):
            next(it)

    def test_memory_that_never_comes_free_is_a_stop_naming_every_process(self):
        self.used[0] = 22000
        self.procs[:] = [(999999, "ollama", 21000)]                  # the Ollama runner: ours, but not free
        need = gpu0.REQUIREMENT_MIB["whisper:large-v3"] + gpu0.MARGIN_MIB
        with gpu0.lease("t"):
            with self.assertRaisesRegex(gpu0.Gpu0NotFree, rf"needs {need} .*pid 999999 ollama 21000 MiB"):
                gpu0.swap_to("whisper:large-v3", wait_s=0, poll_s=0)

    def test_an_unknown_model_is_never_loaded(self):
        with gpu0.lease("t"):
            with self.assertRaisesRegex(gpu0.Gpu0NotFree, "no measured GPU0 requirement"):
                gpu0.swap_to("whisper:tiny")

    def test_the_model_already_resident_is_kept(self):
        self.ollama[:] = ["gemma3:27b"]
        gpu0._ollama_ours["gemma3:27b"] = "resident"
        self.procs[:] = [(999999, "ollama", 20500)]
        self.used[0] = 20600                                           # its own memory: not 'not free'
        with gpu0.lease("t"):
            ev = gpu0.swap_to("ollama:gemma3:27b", wait_s=0)
        self.assertEqual((ev["already_resident"], self.unloaded), (True, []))


class TestOutOfMemory(Box):
    def test_every_spelling_is_recognised_and_nothing_else(self):
        cpe = subprocess.CalledProcessError(1, ["ffmpeg"], stderr=b"OpenEncodeSessionEx failed: out of memory (10)")
        long_tail = subprocess.CalledProcessError(1, ["ffmpeg"], stderr=b"NV_ENC_ERR_OUT_OF_MEMORY\n" + b"x" * 20000)
        for e in (RuntimeError("CUDA failed with error out of memory"), cpe, long_tail,
                  type("OutOfMemoryError", (RuntimeError,), {})("CUDA"), RuntimeError("CUBLAS_STATUS_ALLOC_FAILED"),
                  RuntimeError("CUDNN_STATUS_ALLOC_FAILED"), RuntimeError("cudaMalloc failed: 2"),
                  RuntimeError("llama runner: unable to allocate CUDA0 buffer"),
                  RuntimeError("ggml: failed to allocate CUDA buffer of size 1024")):
            self.assertTrue(gpu0.is_oom(e), e)
        for e in (MemoryError(), OSError(12, "Cannot allocate memory"), RuntimeError("decoder failed"),
                  subprocess.CalledProcessError(1, ["ffmpeg"], stderr=b"Invalid data found")):
            self.assertFalse(gpu0.is_oom(e), e)

    def test_a_stop_passes_every_except_exception(self):
        def helper():                                    # the shape of select_passages._whisper_transcribe
            try:
                with gpu0.guard("whisper: transcribe"):
                    raise RuntimeError("CUDA failed with error out of memory")
            except Exception:
                return None                              # 'transcription failed' (E-FAIL-052)
        with self.assertRaisesRegex(gpu0.GpuOOM, "whisper: transcribe: CUDA out of memory"):
            helper()

    def test_a_finished_nvenc_subprocess_that_ran_out_of_memory_is_named(self):
        fail = subprocess.CompletedProcess(["ffmpeg"], 1, b"", b"[h264_nvenc] OpenEncodeSessionEx failed: out of memory (10)")
        with self.assertRaisesRegex(gpu0.GpuOOM, "render16 nvenc: out of memory"):
            gpu0.raise_if_oom(fail, "render16 nvenc")
        gpu0.raise_if_oom(subprocess.CompletedProcess(["ffmpeg"], 1, b"", b"Invalid data found"), "x")   # not OOM
        gpu0.raise_if_oom(subprocess.CompletedProcess(["ffmpeg"], 0, b"", b""), "x")                     # success

    def test_a_lazily_decoded_out_of_memory_is_converted_too(self):
        def segs():
            yield 1
            raise RuntimeError("CUDA failed with error out of memory")
        it = gpu0.guard_iter(segs(), "decode")
        with gpu0.lease("t"):
            self.assertEqual(next(it), 1)
            with self.assertRaises(gpu0.GpuOOM):
                next(it)

    def test_a_model_call_is_guarded_and_a_non_oom_error_is_unchanged(self):
        class Enc:
            def embed(self, x):
                if x == "oom":
                    raise RuntimeError("CUDA error: out of memory")
                raise ValueError("bad input")
        m = gpu0.model("resemblyzer", Enc)
        with gpu0.lease("t"):
            with self.assertRaises(gpu0.GpuOOM):
                m.embed("oom")
            with self.assertRaises(ValueError):
                m.embed("x")


class TestPeaks(Box):
    def test_the_peak_per_label(self):
        s = gpu0.PeakSampler(interval_s=3600)
        s.set("pinned")
        self.used[0] = 5000
        s._sample()
        self.used[0] = 300
        s.set("render")
        s.set(None)
        self.used[0] = 9999                              # outside any stage: attributed to none
        s._sample()
        self.assertEqual(s.peaks, {"pinned": 5000, "render": 300})


class TestStageRunner(Box):
    """run_fresh.Run._attempts: one bounded retry of an out-of-memory, both attempts in PROVENANCE, a second one a
    HOLD naming every GPU0 process; every other GPU0 stop a HOLD with its real cause."""

    def run_(self):
        import run_fresh as rf
        d = tempfile.mkdtemp(dir=self.tmp)
        return rf, rf.Run(d)

    def test_one_retry_then_success(self):
        rf, run = self.run_()
        calls = []

        def stage():
            calls.append(1)
            if len(calls) == 1:
                raise gpu0.GpuOOM("whisper:large-v3: transcribe: CUDA out of memory")
            return "ok"
        with mock.patch.object(gpu0, "release_all", return_value={"after": [18, 24564]}) as rel:
            self.assertEqual(run.stage("pinned", stage), "ok")
        self.assertEqual((len(calls), rel.call_count), (2, 1))
        log = run.prov["gpu0_oom"]["pinned"]
        self.assertEqual((len(log), log[0]["attempt"], log[0]["release"]), (2, 1, {"after": [18, 24564]}))
        self.assertEqual((log[1]["attempt"], log[1]["outcome"]), (2, "passed"))      # both attempts logged

    def test_a_second_out_of_memory_is_a_hold_naming_every_process(self):
        rf, run = self.run_()
        self.procs[:] = [(31337, "python3", 23000)]

        def stage():
            raise RuntimeError("CUDA failed with error out of memory")   # raw: recognised by the runner too
        with mock.patch.object(gpu0, "release_all", return_value={}):
            with self.assertRaises(rf.Hold) as cm:
                run.stage("gates", stage)
        msg = str(cm.exception)
        self.assertTrue(msg.startswith("infrastructure: gates: CUDA out of memory twice"), msg)
        self.assertIn("pid 31337 python3 23000 MiB", msg)
        self.assertEqual(len(run.prov["gpu0_oom"]["gates"]), 2)

    def test_a_failed_retry_keeps_the_out_of_memory_in_the_hold(self):
        rf, run = self.run_()
        n = []

        def stage():
            n.append(1)
            if len(n) == 1:
                raise gpu0.GpuOOM("whisper:medium: transcribe: CUDA out of memory")
            raise rf.Hold("cut acceptance failed")
        with mock.patch.object(gpu0, "release_all", return_value={}):
            with self.assertRaises(rf.Hold) as cm:
                run.stage("gates", stage)
        msg = str(cm.exception)
        self.assertTrue(msg.startswith("infrastructure: gates: CUDA out of memory on attempt 1"), msg)
        self.assertIn("the retry then held: cut acceptance failed", msg)

    def test_other_stops_hold_with_the_real_cause_and_ordinary_errors_are_not_retried(self):
        rf, run = self.run_()
        with self.assertRaisesRegex(rf.Hold, r"^infrastructure: render: GPU0 Gpu0Foreign: .*pid 7"):
            run.stage("render", lambda: (_ for _ in ()).throw(gpu0.Gpu0Foreign("held by pid 7 x 1 MiB")))
        n = []
        with self.assertRaisesRegex(rf.Hold, "ValueError: no"):
            run.stage("cut", lambda: n.append(1) or (_ for _ in ()).throw(ValueError("no")))
        self.assertEqual(n, [1])

    def test_e_fail_052_the_pinned_out_of_memory_is_reported_as_one(self):
        """Nov 12: Whisper's out-of-memory in the pinned stage read 'pinned decision rejected: R-iKNbc7-zk:
        transcription failed'. Now it reaches the HOLD as the out-of-memory it is (after one retry)."""
        rf, run = self.run_()
        import pinned
        import select_passages as sp

        class OOMWhisper:                                # what gpu0.whisper's guard makes of a CTranslate2 OOM
            def transcribe(self, *a, **k):
                with gpu0.guard("whisper:large-v3: transcribe"):
                    raise RuntimeError("CUDA failed with error out of memory")
        src = os.path.join(self.tmp, "src.mp4")
        open(src, "wb").write(b"x")
        seg = {"role": "hook", "video_id": "R-iKNbc7-zk", "start": 18.16, "end": 26.4, "source": {"kind": "youtube"}}
        with mock.patch.object(sp, "_download_window", return_value=(src, 0.0)), \
                mock.patch.object(gpu0, "whisper", return_value=OOMWhisper()), \
                mock.patch.object(gpu0, "release_all", return_value={}):
            with self.assertRaises(rf.Hold) as cm:
                run.stage("pinned", lambda: pinned.acquire({"segments": [seg]}, run.dir, log=lambda s: None))
        msg = str(cm.exception)
        self.assertTrue(msg.startswith("infrastructure: pinned: CUDA out of memory twice"), msg)
        self.assertNotIn("transcription failed", msg)
        self.assertNotIn("pinned decision rejected", msg)


class TestOllamaReadingsFailClosed(unittest.TestCase):
    def test_an_empty_or_malformed_answer_is_unreadable_never_nothing_resident(self):
        for body in ({}, [], {"models": None}, {"models": "x"}, {"models": [{"name": []}]}, {"models": [{}]}):
            with mock.patch.object(gpu0, "_ollama", return_value=body):
                with self.assertRaises(gpu0.Gpu0Unreadable, msg=repr(body)):
                    gpu0.ollama_resident()
        with mock.patch.object(gpu0, "_ollama", return_value={"models": []}):
            self.assertEqual(gpu0.ollama_resident(), [])


class TestReadingsFailClosed(unittest.TestCase):
    """The real parsers (no stubs of their own): a reading that cannot be read is a stop, never 'nothing there'."""

    def test_an_unparsable_nvidia_smi_line_is_unreadable_and_other_gpus_are_ignored(self):
        def smi(args, timeout=15):
            if "--query-gpu=uuid" in args:
                return "GPU-A\n"
            return "123, GPU-A, 500, /usr/bin/python3\n456, GPU-B, 900, ollama\n" + smi.extra
        smi.extra = ""
        with mock.patch.object(gpu0, "_smi", side_effect=smi):
            self.assertEqual(gpu0.processes(), [(123, "python3", 500)])
            smi.extra = "[Not Supported]\n"
            with self.assertRaises(gpu0.Gpu0Unreadable):
                gpu0.processes()

    def test_ss_failing_or_hiding_the_listener_pid_is_unreadable(self):
        with mock.patch.object(gpu0.subprocess, "run", return_value=subprocess.CompletedProcess([], 1, "", "boom")):
            with self.assertRaises(gpu0.Gpu0Unreadable):
                gpu0._ollama_pids()
        hidden = subprocess.CompletedProcess([], 0, "LISTEN 0 4096 127.0.0.1:11434 0.0.0.0:*\n", "")
        with mock.patch.object(gpu0.subprocess, "run", return_value=hidden):
            with self.assertRaisesRegex(gpu0.Gpu0Unreadable, "not visible to this user"):
                gpu0._ollama_pids()


class TestNoDirectLoaders(unittest.TestCase):
    """L-r item 2 by construction: in the code a run imports, nothing builds a GPU0 model, moves a tensor to CUDA or calls
    the GPU0 Ollama except through gpu0, and every function that encodes with NVENC swaps to it first."""
    import glob as _g
    # run_isolated.py is a protected file (Law 22, test_fresh.TestProtected): its NVENC encodes are swapped to at its
    # one pipeline caller (test_run_isolated_is_swapped_at_its_caller)
    FILES = sorted(f for f in _g.glob(os.path.join(PIPELINE, "*.py"))
                   if not os.path.basename(f).startswith("test_")
                   and os.path.basename(f) not in ("conftest.py", "gpu0.py", "measure_gpu0.py", "run_isolated.py")) + \
        [os.path.join(os.path.dirname(PIPELINE), "segment_v1", "qa_gates.py")]

    def test_no_model_is_built_outside_gpu0(self):
        """Deny-list over the code a run imports: model constructors, CUDA placement, .cuda(). The ONE allowance is the
        Embedder class in story_semantics.py (its weights load inside gpu0.model's build, its inputs move inside
        gpu0.guard)."""
        import ast
        import re
        pats = [r"WhisperModel\(", r"BatchedInferencePipeline\(", r"VoiceEncoder\(\)", r"\.to\(['\"]cuda", r"device=['\"]cuda",
                r"\.cuda\(\)", r"torch\.device\(['\"]cuda"]
        bad = []
        for f in self.FILES:
            src = open(f).read()
            allowed_lines = set()
            if os.path.basename(f) == "story_semantics.py":
                for n in ast.parse(src).body:
                    if isinstance(n, ast.ClassDef) and n.name == "Embedder":
                        allowed_lines |= set(range(n.lineno, n.end_lineno + 1))
            for pat in pats:
                for m in re.finditer(pat, src):
                    line = src.count("\n", 0, m.start()) + 1
                    text = src.splitlines()[line - 1].lstrip()
                    if not text.startswith("#") and line not in allowed_lines:
                        bad.append(f"{os.path.relpath(f, PIPELINE)}:{line}: {pat}")
        self.assertEqual(bad, [])

    def test_every_nvenc_encode_is_preceded_by_the_swap_and_its_oom_is_named(self):
        """AST, per function (nested ones included): the call gpu0.swap_to("nvenc") executes (a Call node, not a comment
        or string) on a line before the first statement that names h264_nvenc; and every subprocess.run of an NVENC
        command captures stderr and either raises on failure (check=True) or is passed to gpu0.raise_if_oom."""
        import ast
        bad = []
        for f in self.FILES:
            src = open(f).read()
            tree = ast.parse(src)
            for fn in [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]:
                body_nodes = [n for n in ast.walk(fn)]
                nv = [n.lineno for n in body_nodes if isinstance(n, ast.Constant) and n.value == "h264_nvenc"]
                if not nv:
                    continue
                swaps = [n.lineno for n in body_nodes if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                         and n.func.attr == "swap_to" and getattr(n.func.value, "id", "") == "gpu0"
                         and n.args and isinstance(n.args[0], ast.Constant) and n.args[0].value == "nvenc"]
                if not swaps or min(swaps) > min(nv):
                    bad.append(f"{os.path.relpath(f, PIPELINE)}: {fn.name}: no swap before line {min(nv)}")
                wrapped = {id(n.args[0]) for n in body_nodes if isinstance(n, ast.Call)
                           and isinstance(n.func, ast.Attribute) and n.func.attr == "raise_if_oom" and n.args}
                checked_targets = {n.args[0].id for n in body_nodes if isinstance(n, ast.Call)
                                   and isinstance(n.func, ast.Attribute) and n.func.attr == "raise_if_oom"
                                   and n.args and isinstance(n.args[0], ast.Name)}
                assigned = {id(n.value) for n in body_nodes if isinstance(n, ast.Assign) and isinstance(n.value, ast.Call)}
                for n in body_nodes:
                    if isinstance(n, ast.Assign) and isinstance(n.value, ast.Call):
                        call, target = n.value, (n.targets[0].id if isinstance(n.targets[0], ast.Name) else None)
                    elif isinstance(n, ast.Call) and id(n) not in assigned:
                        call, target = n, None
                    else:
                        continue
                    if not (isinstance(call.func, ast.Attribute) and call.func.attr == "run"
                            and getattr(call.func.value, "id", "") == "subprocess"):
                        continue
                    seg = ast.get_source_segment(src, call) or ""
                    if "h264_nvenc" not in seg:
                        continue
                    kw = {k.arg: k.value for k in call.keywords}
                    captured = "capture_output" in kw or "stderr" in kw
                    checked = isinstance(kw.get("check"), ast.Constant) and kw["check"].value is True
                    if not captured or not (checked or id(call) in wrapped or target in checked_targets):
                        bad.append(f"{os.path.relpath(f, PIPELINE)}:{call.lineno} {fn.name}: NVENC run whose OOM is "
                                   f"not named (captured={captured}, check={checked})")
        self.assertEqual(sorted(set(bad)), [])

    def test_run_isolated_is_swapped_at_its_caller(self):
        import ast
        src = open(os.path.join(PIPELINE, "run_fresh.py")).read()
        calls = [n for n in ast.walk(ast.parse(src)) if isinstance(n, ast.ImportFrom) and n.module == "run_isolated"
                 and any(a.name == "prerender_clips" for a in n.names)]
        self.assertTrue(calls and all(any(a.asname == "_prerender_isolated" for a in n.names if a.name ==
                                          "prerender_clips") for n in calls))
        fn = src[src.index("def prerender_clips(run_dir, table):"):]
        self.assertLess(fn.index('gpu0.swap_to("nvenc")'), fn.index("_prerender_isolated(run_dir, table)"))

    def test_the_gpu0_ollama_is_called_only_through_gpu0(self):
        """AST: a string naming the Ollama generate / chat endpoints appears only in LocalLLM._post (chat, after
        swap_to), story_semantics._unload (keep_alive 0) and preflight.check_ollama (after swap_to)."""
        import ast
        allowed = {("story_semantics.py", "_post"), ("story_semantics.py", "_unload"), ("preflight.py", "check_ollama")}
        bad = []
        for f in self.FILES:
            src = open(f).read()
            tree = ast.parse(src)
            spans = [(n.lineno, n.end_lineno, n.name) for n in ast.walk(tree)
                     if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
            for n in ast.walk(tree):
                if isinstance(n, (ast.Constant, ast.JoinedStr)):
                    text = n.value if isinstance(n, ast.Constant) else (ast.get_source_segment(src, n) or "")
                    if isinstance(text, str) and ("/api/generate" in text or "/api/chat" in text):
                        inner = [name for a, b, name in spans if a <= n.lineno <= b]
                        where = inner[-1] if inner else "<module>"
                        if (os.path.basename(f), where) not in allowed:
                            bad.append(f"{os.path.relpath(f, PIPELINE)}:{n.lineno} {where}")
        self.assertEqual(bad, [])


class TestPreflightLeavesGpu0AsFound(Box):
    def test_a_model_left_resident_or_memory_left_used_fails(self):
        import preflight
        self.assertTrue(preflight.left_as_found(100, [], wait_s=0)[0])
        self.ollama[:] = ["gemma3:27b"]
        ok, why = preflight.left_as_found(100, [], wait_s=0)
        self.assertFalse(ok)
        self.assertIn("gemma3:27b", why)
        self.ollama[:] = []
        self.used[0] = 20659
        ok, why = preflight.left_as_found(100, [], wait_s=0)
        self.assertEqual((ok, "left GPU0 at 20659 MiB (found at 100 MiB)" in why), (False, True))


if __name__ == "__main__":
    unittest.main()
