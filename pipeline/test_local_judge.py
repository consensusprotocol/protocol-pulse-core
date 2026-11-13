#!/usr/bin/env python3
"""The GPU0 local judge (orchestrator 2026-11-13 '07:28' item 2), without a GPU: the recorded prompts it replays (the
three families, the night's cutoff, one job per prompt with every vendor answer kept); the GPU0 discipline (a render's
yield flag stops the next call, a held lease is waited out, every batch releases GPU0 even when a call fails, a GPU
stop is never swallowed, a stopped replay resumes); and the comparison read with the builder's own rules (in its own
process, as it runs)."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

PIPELINE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PIPELINE)
import local_judge as J  # noqa: E402


def rec(d, name, prompt, text, at="2026-11-13T05:00:00Z", backend="xai:grok", max_tokens=1200, seed=7):
    os.makedirs(os.path.join(d, name[:2]), exist_ok=True)
    with open(os.path.join(d, name[:2], name + ".json"), "w") as f:
        json.dump({"role": "x", "backend": backend, "prompt": prompt, "text": text, "recorded_at": at,
                   "max_tokens": max_tokens, "seed": seed}, f)


class TestRecorded(unittest.TestCase):
    def test_three_families_since_the_cutoff_one_job_per_prompt(self):
        d = tempfile.mkdtemp(prefix="lj_rec_")
        self.addCleanup(shutil.rmtree, d)
        rec(d, "aa1", "You watch a short video made ONLY of these clips ...", "{}")
        rec(d, "aa2", "You watch a short video made ONLY of these clips ...", "{}", backend="heimdall:x")  # same prompt
        rec(d, "bb1", "You are the editor of PBX MAX: ...", "{}")
        rec(d, "cc1", "You read  transcripts of Bitcoin videos.\nFor each EXCERPT below", "{}")  # whitespace-normalised
        rec(d, "dd1", "You are PBX MAX, the host of ...", "{}")                                   # a writer: not judged
        rec(d, "ee1", "You watch a 60-second video. Here is everything ...", "{}")                 # coherence: not here
        rec(d, "ff1", "You watch a short video made ONLY of these clips (old)", "{}", at="2026-11-12T20:00:00Z")
        jobs = J.recorded(since="2026-11-13T04:00", replies=d)
        self.assertEqual([j["family"] for j in jobs], ["clips_alone", "angle", "step_a"])
        self.assertEqual(sorted(v["backend"] for v in jobs[0]["vendor"]), ["heimdall:x", "xai:grok"])


class FakeLLM:
    def __init__(self, model=None):
        self.digest, self.asked = "d1", []

    def start(self):
        return self

    def _post(self, prompt, max_tokens, seed):
        self.asked.append(prompt)
        if prompt == "boom":
            raise RuntimeError("bad request")
        return '{"ok": true}'


class TestRun(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="lj_run_")
        self.addCleanup(shutil.rmtree, self.d)
        self.out = os.path.join(self.d, "a.jsonl")
        self.flag = os.path.join(self.d, "yield")
        self.jobs = [{"id": f"j{i}", "family": "clips_alone", "prompt": f"p{i}", "max_tokens": 100, "seed": 7}
                     for i in range(5)]
        import gpu0
        self.gpu0 = gpu0
        self.released, self.llms = [], []

        def llm(model=None):
            self.llms.append(FakeLLM(model))
            return self.llms[-1]
        self.p = [mock.patch.object(J, "YIELD_FLAG", self.flag),
                  mock.patch.object(gpu0, "lease", mock.MagicMock()),
                  mock.patch.object(gpu0, "release_all", lambda: self.released.append(1)),
                  mock.patch("story_semantics.LocalLLM", llm),
                  mock.patch.object(J.time, "sleep", lambda s: None)]
        for x in self.p:
            x.start()
            self.addCleanup(x.stop)

    def answers(self):
        with open(self.out) as f:
            return [json.loads(l) for l in f if l.strip()]

    def test_every_job_once_in_batches_each_ending_with_gpu0_released(self):
        self.assertEqual(J.run(self.jobs, self.out, batch=2, log=lambda *a: None), 5)
        self.assertEqual([a["id"] for a in self.answers()], ["j0", "j1", "j2", "j3", "j4"])
        self.assertEqual(len(self.released), 3)                        # 2 + 2 + 1: GPU0 released after each batch
        self.assertEqual(J.run(self.jobs, self.out, batch=2, log=lambda *a: None), 0)   # resumes: nothing twice

    def test_a_render_yield_flag_stops_the_next_call(self):
        calls = []

        def post(prompt, max_tokens, seed):
            calls.append(prompt)
            if prompt == "p1":
                open(self.flag, "w").close()                           # a render asks while p1 runs
            return "{}"
        n = [0]

        def sleep(s):                                                  # the render ends: the flag goes
            n[0] += 1
            os.remove(self.flag)
        with mock.patch.object(FakeLLM, "_post", lambda self_, p, m, s: post(p, m, s)), \
                mock.patch.object(J.time, "sleep", sleep):
            J.run(self.jobs, self.out, batch=8, log=lambda *a: None)
        self.assertEqual(calls, ["p0", "p1", "p2", "p3", "p4"])
        self.assertEqual(n[0], 1)                                      # it waited once, with p2 not yet asked
        self.assertEqual(len(self.released), 2)                        # the batch ended (GPU0 released) at the flag

    def test_a_busy_lease_is_waited_out_and_a_failed_call_is_recorded_not_retried(self):
        tries = []

        def lease(owner, wait_s=0):
            tries.append(1)
            if len(tries) == 1:
                raise self.gpu0.LeaseBusy("held by a render")
            return mock.MagicMock()
        jobs = self.jobs[:2] + [dict(self.jobs[2], prompt="boom")]
        with mock.patch.object(self.gpu0, "lease", lease):
            J.run(jobs, self.out, batch=8, log=lambda *a: None)
        got = {a["id"]: a for a in self.answers()}
        self.assertEqual(len(tries), 2)
        self.assertIn("bad request", got["j2"]["error"])
        self.assertIsNone(got["j2"]["text"])
        self.assertEqual(sum(len(l.asked) for l in self.llms), 3)

    def test_a_gpu_stop_is_never_swallowed_and_gpu0_is_still_released(self):
        post = mock.Mock(side_effect=['{"ok": 1}', self.gpu0.GpuOOM("cuda oom")])
        with mock.patch.object(FakeLLM, "_post", lambda self_, p, m, s: post(p, m, s)):
            with self.assertRaises(self.gpu0.GpuOOM):
                J.run(self.jobs, self.out, batch=8, log=lambda *a: None)
        self.assertEqual(len(self.released), 1)
        self.assertEqual([a["id"] for a in self.answers()], ["j0"])     # the answer before the stop survives

    def test_a_failed_call_is_asked_again_by_the_next_run_only_and_a_truncated_line_is_skipped(self):   # batch 61 C2
        boom = [dict(self.jobs[0], prompt="boom")]
        J.run(boom, self.out, batch=8, log=lambda *a: None)
        self.assertEqual(sum(len(l.asked) for l in self.llms), 1)      # once in this run: no spin
        with open(self.out, "a") as f:
            f.write('{"id": "j9", "text"')                              # a crash mid-write
        self.assertEqual(J.done_ids(self.out), set())
        J.run(boom, self.out, batch=8, log=lambda *a: None)
        self.assertEqual(sum(len(l.asked) for l in self.llms), 2)      # the next run asks it again

    def test_a_render_asking_while_the_lease_is_taken_gets_it_back_with_nothing_loaded(self):   # batch 61 C1
        flag, seen = self.flag, []

        class Lease:
            def __enter__(self_):
                if not seen:
                    open(flag, "w").close()                            # the render asks in between
                seen.append(1)

            def __exit__(self_, *a):
                return False

        def sleep(s):
            if os.path.exists(flag):
                os.remove(flag)
        with mock.patch.object(self.gpu0, "lease", lambda owner, wait_s=0: Lease()), \
                mock.patch.object(J.time, "sleep", sleep):
            J.run(self.jobs[:1], self.out, batch=8, log=lambda *a: None)
        self.assertEqual(len(seen), 2)                                 # taken, given back, taken again later
        self.assertEqual(len(self.llms), 1)                            # nothing loaded the first time
        self.assertEqual(len(self.released), 1)


class TestCompare(unittest.TestCase):
    """The comparison runs in its own process (the builder's modules first on its path), exactly as it is used."""

    def test_verdicts_read_with_the_builders_rules(self):
        d = tempfile.mkdtemp(prefix="lj_cmp_")
        self.addCleanup(shutil.rmtree, d)
        ex = lambda lb, **k: dict({"label": lb, "speaker_changes_inside": "no", "view": "own_sincere", "referents": [],
                                    "conditions": [], "retraction": "none", "time_ok": "yes", "proposition": "p",
                                    "certainty": "certain", "speaker_is": "host", "speaker_evidence": ""}, **k)
        a_prompt = 'You read transcripts <excerpt label="m1" x>t</excerpt><excerpt label="m2" x>t</excerpt>'
        clips = 'CLIP label="hook" (on screen: A): "x"\nCLIP label="clip_01" (on screen: B): "y"'
        med = lambda ok_join, r: json.dumps({"through_line": "Bitcoin holds while the crowd swings", "clips":
                                             {"hook": 5, "clip_01": r}, "joins": {"hook -> clip_01": {"followable": ok_join, "why": "w"}}})
        jobs = [{"id": "A", "family": "step_a", "prompt": a_prompt, "vendor": [{"backend": "v", "text": json.dumps(
                    {"excerpts": [ex("m1"), ex("m2", retraction="partial")]})}]},
                {"id": "C", "family": "clips_alone", "prompt": clips, "vendor": [{"backend": "v", "text": med(True, 4)}]},
                {"id": "D", "family": "clips_alone", "prompt": clips, "vendor": [{"backend": "v", "text": med(True, 5)}]}]
        local = [{"id": "A", "seconds": 1, "text": json.dumps({"excerpts": [ex("m1", view="attributed"), ex("m2")]})},
                 {"id": "C", "seconds": 1, "text": med(True, 2)},
                 {"id": "D", "seconds": 1, "text": "not json"}]
        ans = os.path.join(d, "a.jsonl")
        with open(ans + ".jobs.json", "w") as f:
            json.dump(jobs, f)
        with open(ans, "w") as f:
            f.write("".join(json.dumps(x) + "\n" for x in local))
        r = subprocess.run([sys.executable, os.path.join(PIPELINE, "local_judge_compare.py"), ans, os.path.join(d, "R")],
                           capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stderr[-800:])
        rep = json.load(open(os.path.join(d, "R.json")))
        a = rep["step_a"]
        self.assertEqual((a["moments"], a["same_verdict"], a["same_rules"]), (2, 0, 0))
        self.assertEqual([x["label"] for x in a["local_fail_vendor_pass"]], ["m1"])            # the costly direction
        self.assertEqual([(x["label"], x["vendor_rules"]) for x in a["local_pass_vendor_fail"]], [("m2", ["RETRACTION"])])
        c = rep["clips_alone"]
        self.assertEqual((c["verdicts"], c["same_ok"], len(c["local_fail_vendor_pass"])), (1, 0, 1))
        self.assertEqual([x["id"] for x in c["local_out_of_contract"]], ["D"])
        self.assertEqual(rep["prefilter_rules"]["clips_alone"]["a local clip rating <= 2"], {"saved": 0, "lost": 1})
        self.assertEqual(rep["prefilter_rules"]["step_a"]["local fails NOT_OWN_SINCERE"], {"saved": 0, "lost": 1})


if __name__ == "__main__":
    unittest.main()
