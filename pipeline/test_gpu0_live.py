#!/usr/bin/env python3
"""Law L-r item 5 on the real GPU0 (a GPU session: CUDA_VISIBLE_DEVICES=0; pipeline/conftest.py holds the GPU0 lease
for the session). Before each stage a real allocation sits on GPU0, and the stage refuses or recovers as the law says:
  - a FOREIGN allocation (a process that is not this run's) -> every stage kind HOLDs at once, naming its pid and MiB;
  - this run's OWN resident model -> the next stage's swap deletes it and the stage passes;
  - a real CUDA out-of-memory -> released, retried ONCE, both attempts in PROVENANCE; a second one HOLDs naming every
    GPU0 process.
TestBackToBack (PP_GPU0_LIVE=1, ~2 x 50 min, a committed clean tree): run_fresh env -> pinned -> ... -> render ->
gates twice back to back on the protected preview's PIN, printing both runs' per-stage GPU0 peak tables."""
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import time
import unittest

PIPELINE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(PIPELINE)
sys.path.insert(0, PIPELINE)
import gpu0  # noqa: E402

GPU = os.environ.get("CUDA_VISIBLE_DEVICES") == "0"
SOURCE = os.path.join(REPO, "references", "pulse_preview_2026-11-11", "sources", "RXTVaDsN11M.mp4")


def _wav(tmp, seconds=20):
    wav = os.path.join(tmp, "a.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "30", "-t", str(seconds), "-i", SOURCE, "-vn", "-ac", "1",
                    "-ar", "16000", wav], check=True, timeout=120)
    return wav


@unittest.skipUnless(GPU, "GPU0 session only (CUDA_VISIBLE_DEVICES=0)")
class Live(unittest.TestCase):
    def setUp(self):
        self.assertTrue(gpu0.held(), "the session must hold the GPU0 lease (pipeline/conftest.py)")
        gpu0.release_all()
        self.tmp = tempfile.mkdtemp(prefix="gpu0live_")
        self.wav = _wav(self.tmp)
        import run_fresh as rf
        self.rf = rf
        self.run_ = rf.Run(self.tmp)
        self.run_.sampler = gpu0.PeakSampler(interval_s=0.25).start()
        self.addCleanup(self.run_.sampler.stop)
        self.addCleanup(gpu0.release_all)

    def transcribe(self, name):
        segs, _ = gpu0.whisper(name).transcribe(self.wav, language="en", beam_size=5, word_timestamps=True,
                                                vad_filter=False)
        return sum(len(s.words or []) for s in segs)


class TestForeignAllocationIsRefused(Live):
    def test_every_stage_kind_holds_naming_the_foreign_process(self):
        flag = os.path.join(self.tmp, "allocated")
        code = ("import torch, time; x = torch.empty(int(2e9), dtype=torch.uint8, device='cuda:0'); "
                f"open({flag!r}, 'w').write('ok'); time.sleep(900)")
        # double fork: the allocator is NOT this process's descendant (a foreign job), and holds no lease descriptor
        out = subprocess.run(["setsid", "bash", "-c", f"{sys.executable} -c \"{code}\" >/dev/null 2>&1 & echo $!"],
                             capture_output=True, text=True, timeout=30, env={**os.environ, "CUDA_VISIBLE_DEVICES": "0"})
        pid = int(out.stdout.strip())

        def stop_allocator():                                         # we started it: stop it and wait until it is gone
            if os.path.exists(f"/proc/{pid}"):
                os.kill(pid, signal.SIGTERM)
            for _ in range(120):
                if not os.path.exists(f"/proc/{pid}") and all(p != pid for p, n, m in gpu0.processes()):
                    return
                time.sleep(0.5)
        self.addCleanup(stop_allocator)
        for _ in range(120):
            if os.path.exists(flag) and any(p == pid for p, n, m in gpu0.processes()):
                break
            time.sleep(0.5)
        else:
            self.fail("the foreign allocation never appeared on GPU0")
        stages = {"pinned": lambda: self.transcribe("large-v3"),
                  "review": lambda: gpu0.swap_to("ollama:gemma3:27b"),
                  "render": lambda: gpu0.swap_to("nvenc"),
                  "gates": lambda: self.transcribe("medium")}
        for name, fn in stages.items():
            with self.assertRaises(self.rf.Hold, msg=name) as cm:
                self.run_.stage(name, fn)
            msg = str(cm.exception)
            self.assertTrue(msg.startswith(f"infrastructure: {name}: GPU0 Gpu0Foreign"), msg)
            self.assertIn(f"pid {pid} ", msg)
        self.assertFalse(gpu0.whisper("large-v3").loaded)              # nothing was loaded next to it


class TestOwnResidentModelIsSwappedOut(Live):
    def test_the_next_stage_deletes_it_and_passes(self):
        import story_semantics as sm
        E = sm.Embedder()
        E.encode(["bitcoin " * 200] * 16)                              # resident on GPU0 before the stage
        self.assertTrue(E.model.loaded)
        n = self.run_.stage("pinned", lambda: self.transcribe("large-v3"))
        self.assertGreater(n, 10)
        self.assertFalse(E.model.loaded)                               # deleted by the swap
        ev = [e for e in gpu0.events() if e["key"] == "whisper:large-v3"][-1]
        self.assertIn("embedder", ev["unloaded"])
        print(f"\n  peaks MiB: {self.run_.sampler.peaks}")


class TestRealOutOfMemory(Live):
    def test_an_oom_caused_by_a_resident_model_is_recovered_by_releasing_it(self):
        """Load-bearing: the out-of-memory happens BECAUSE Whisper medium is resident and referenced from the failing
        frame; the retry can succeed only if the release really frees that model (traceback dropped, object deleted):
        release_all requires this process to hold no more than its CUDA context, and attempt 2 allocates the same
        amount, which only fits once the model is gone. With the model pinned, the release HOLDs."""
        import torch
        state = {}

        def stage():
            state["n"] = state.get("n", 0) + 1
            if state["n"] == 1:
                m = gpu0.whisper("medium")
                obj = m.get()                                          # resident, referenced from this frame
                used, total = gpu0.memory()
                state["mib"] = total - used + 1024                     # 1 GiB more than is free with it loaded
                with gpu0.guard("allocation next to a resident model"):
                    torch.empty(state["mib"] * 1024 * 1024, dtype=torch.uint8, device="cuda:0")
                return obj                                             # never reached
            x = torch.empty(state["mib"] * 1024 * 1024, dtype=torch.uint8, device="cuda:0")   # fits once it is gone
            del x
            return self.transcribe("medium")
        self.assertGreater(self.run_.stage("gates", stage), 10)
        log = self.run_.prov["gpu0_oom"]["gates"]
        self.assertEqual((state["n"], len(log), log[1]["outcome"]), (2, 2, "passed"))
        self.assertIn("out of memory", log[0]["error"].lower())
        self.assertIn("whisper:medium", log[0]["release"]["unloaded"])

    def test_two_out_of_memory_attempts_hold_naming_every_gpu0_process(self):
        import torch

        def always():
            with gpu0.guard("dummy allocation"):
                torch.empty(int(40e9), dtype=torch.uint8, device="cuda:0")
        with self.assertRaises(self.rf.Hold) as cm:
            self.run_.stage("render", always)
        msg = str(cm.exception)
        self.assertTrue(msg.startswith("infrastructure: render: CUDA out of memory twice"), msg)
        self.assertIn(f"pid {os.getpid()} ", msg)                     # every GPU0 process named (here: this one)
        self.assertEqual(len(self.run_.prov["gpu0_oom"]["render"]), 2)


class TestTheNov12Incident(Live):
    """runs/pinned_20261112_064032: gemma3:27b resident on GPU0, then Whisper. Replayed both ways."""

    def test_this_runs_editorial_model_is_swapped_out_before_whisper(self):
        import story_semantics as sm
        llm = sm.LocalLLM()
        llm._post("Reply with the JSON object {\"ok\": true}.", 20, seed=7)    # gemma3:27b resident (this run's)
        self.assertIn(sm.LLM_MODEL, gpu0.ollama_loaded())
        n = self.run_.stage("pinned", lambda: self.transcribe("large-v3"))
        self.assertGreater(n, 10)
        self.assertNotIn(sm.LLM_MODEL, gpu0.ollama_loaded())
        print(f"\n  peaks MiB: {self.run_.sampler.peaks}")

    def test_a_model_another_client_loaded_holds_the_run_and_is_not_touched(self):
        import json as _j
        import urllib.request
        import story_semantics as sm
        body = _j.dumps({"model": sm.LLM_MODEL, "prompt": "ok", "stream": False, "options": {"num_predict": 1}}).encode()
        urllib.request.urlopen(urllib.request.Request(f"http://{gpu0.OLLAMA_HOST}/api/generate", data=body,
                               headers={"Content-Type": "application/json"}), timeout=300).read()   # another client
        def unload_it():                                              # this test loaded it as 'another client'
            urllib.request.urlopen(urllib.request.Request(
                f"http://{gpu0.OLLAMA_HOST}/api/generate", data=_j.dumps({"model": sm.LLM_MODEL, "keep_alive": 0}).encode(),
                headers={"Content-Type": "application/json"}), timeout=120).read()
            for _ in range(120):
                if sm.LLM_MODEL not in gpu0.ollama_loaded():
                    return
                time.sleep(0.5)
        self.addCleanup(unload_it)
        with self.assertRaises(self.rf.Hold) as cm:
            self.run_.stage("pinned", lambda: self.transcribe("large-v3"))
        msg = str(cm.exception)
        self.assertIn(f"ollama model {sm.LLM_MODEL} (not requested by this run)", msg)
        self.assertIn(sm.LLM_MODEL, gpu0.ollama_loaded())             # nothing of it was unloaded


# the PBX-approved preview of Nov 11 (law L-d): local sources, every stage through render, gates and verify
PIN = os.path.join(REPO, "references", "pulse_preview_2026-11-11", "PIN.json")


@unittest.skipUnless(GPU and os.environ.get("PP_GPU0_LIVE") == "1", "PP_GPU0_LIVE=1: two full runs (~2 x 50 min)")
class TestBackToBack(unittest.TestCase):
    def test_two_runs_back_to_back_with_the_peak_table(self):
        """Two full runs of the protected preview's PIN back to back, nothing released between them: the second must
        find GPU0 as the first left it (its env stage refuses anything foreign), every stage must run and be sampled,
        and no stage may hold for a GPU0 cause."""
        fd = gpu0._own[gpu0.lease_path()]["file"].fileno()        # the session's lease: run_fresh inherits custody
        os.set_inheritable(fd, True)
        want = ["env", "pinned", "review", "validate", "cut", "sentence_law", "voice", "prepare", "layout", "render",
                "gates", "verify"]
        tables = []
        for i in (1, 2):
            r = subprocess.run([sys.executable, os.path.join(PIPELINE, "run_fresh.py"), "--pinned", PIN],
                               capture_output=True, text=True, timeout=4 * 3600, pass_fds=(fd,), cwd=PIPELINE)
            run_dir = re.search(r"=== FRESH-TOPIC RUN (\S+) ===", r.stdout).group(1)
            report = open(os.path.join(run_dir, "REPORT.md")).read()
            table = report[report.index("## GPU0 peak memory per stage"):].split("\n\n")[0]
            tables.append((run_dir, r.returncode, table))
            self.assertEqual(r.returncode, 0, (run_dir, r.stdout[-2000:]))      # the protected preview passes
            prov = json.load(open(os.path.join(run_dir, "PROVENANCE.json")))
            self.assertFalse(prov.get("gpu0_oom"), (run_dir, prov.get("gpu0_oom")))   # and needed no OOM retry
            stages = {st["name"]: st for st in json.load(open(os.path.join(run_dir, "status.json")))["stages"]}
            self.assertEqual([n for n in want if n not in stages], [], run_dir)
            for n in want:
                st = stages[n]
                self.assertEqual(st["status"], "passed", (run_dir, n, st.get("reason")))
                self.assertIsInstance(st.get("gpu0_peak_mib"), int, (run_dir, n))
        for run_dir, rc, table in tables:
            print(f"\n{run_dir} (exit {rc})\n{table}")

if __name__ == "__main__":
    unittest.main()
