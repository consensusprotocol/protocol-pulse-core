#!/usr/bin/env python3
"""The pin-stage clip scorer (orchestrator 2026-11-13 '09:58' item 56), without a GPU: validate and the pin stage share
ONE code path (stand_alone.clip_scorer / affirmed); a request gets one scorer call, the same prompt validate builds, and
one verdict per passage in a file keyed by moment id + text sha256 + scorer code sha; malformed requests and
unparseable replies are never affirmed; GPU0 is taken per batch of 8 and given back to a render."""
import hashlib
import inspect
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

PIPELINE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PIPELINE)
import run_fresh as rf  # noqa: E402
import stand_alone as SA  # noqa: E402
import stand_alone_scorer as SS  # noqa: E402


class FakeLLM:
    model, digest = "gemma3:27b", "dg"

    def __init__(self, scores=None, broken=False):
        self.scores, self.broken, self.prompts = scores or {}, broken, []

    def chat_json(self, prompt, max_tokens=700, validate=None):
        self.prompts.append(prompt)
        if self.broken:
            raise __import__("story_semantics").LLMParseError("unparseable", ["x"])
        out = {"ratings": [{"id": pid, "score": s, "reason": "r", "fault": f} for pid, (s, f) in self.scores.items()]}
        if validate:
            validate(out)
        return out


def req(rid="r1", event="Pinned: Bitcoin holds", **kw):
    ps = kw["passages"] if "passages" in kw else [{"moment_id": "m1", "pid": "clip_01", "channel": "A", "duration": 9.4,
                                                  "text": "But we have rarely seen six red weeks."},
                                                 {"moment_id": "m2", "pid": "clip_02", "channel": "B", "duration": 12.0,
                                                  "text": "So the cycle repeats."}]
    return {"request_id": rid, "event": event, "passages": ps}


class TestOneCodePath(unittest.TestCase):
    def test_validate_asks_the_shared_scorer_and_threshold(self):
        src = inspect.getsource(rf.stage_validate)
        self.assertIn("stand_alone.clip_scorer(", src)
        self.assertNotIn("rate_passages(", src)                       # nothing of its own left in validate
        self.assertIn('moments="moments_package_sha256" in edl', src)   # ruling 60: a moments pin, alone only
        for f in (SA.opener, SA.trimmed_opener):
            self.assertIn("affirmed(score, fault, moments)", inspect.getsource(f))

    def test_the_threshold(self):
        cases = ((3.5, "none"), (3.4, "none"), (5, "starts_mid_thought"), (None, None), (4.0, "unspecified"))
        self.assertEqual([SA.affirmed(s, f) for s, f in cases], [True, False, False, False, True])        # story
        self.assertEqual([SA.affirmed(s, f, moments=True) for s, f in cases], [True, False, True, False, True])

    def test_ruling_60_the_moments_prompt_judges_standing_alone_only_and_the_story_prompt_is_unchanged(self):
        import story_semantics as sm
        self.assertNotIn("{event}", sm.ALONE_PROMPT)
        self.assertNotIn("off_topic", sm.ALONE_PROMPT)
        self.assertIn("does a viewer who hears only this clip understand what is being claimed", sm.ALONE_PROMPT)
        self.assertIn("is never this fault", sm.ALONE_PROMPT)                 # no fixed penalty for an opener word
        self.assertTrue(sm.CLIP_PROMPT.startswith("You pick clips for a short Bitcoin news video about this event:"))
        self.assertIn("{event}", sm.CLIP_PROMPT)
        ps = [{"pid": "clip_01", "channel": "A", "duration": 9.0, "text": "But we hold."}]
        m, st = FakeLLM({"clip_01": (4.0, "starts_mid_thought")}), FakeLLM({"clip_01": (4.0, "none")})
        SA.clip_scorer("Pinned: X", llm=m, moments=True)(ps)
        SA.clip_scorer("Pinned: X", llm=st)(ps)
        self.assertNotIn("EVENT:", m.prompts[0])
        self.assertIn("EVENT: Pinned: X", st.prompts[0])
        chk = SA.check_edl({"hook": {"text": "Bitcoin is money.", "channel": "H"},
                            "clips": [{"index": 1, "text": "But we hold bitcoin.", "channel": "A"}]},
                           rate=lambda p: {"clip_01": (4.0, "x", "starts_mid_thought")}, moments=True)
        self.assertTrue(chk["rows"][1]["opener"]["pass"], chk)              # the score decides for a moments pin
        chk = SA.check_edl({"hook": {"text": "Bitcoin is money.", "channel": "H"},
                            "clips": [{"index": 1, "text": "But we hold bitcoin.", "channel": "A"}]},
                           rate=lambda p: {"clip_01": (4.0, "x", "starts_mid_thought")})
        self.assertFalse(chk["rows"][1]["opener"]["pass"], chk)             # the story path keeps its rule

    def test_the_service_asks_the_byte_identical_prompt_validate_asks(self):
        r = req()
        ps = [{k: p[k] for k in ("pid", "channel", "duration", "text")} for p in r["passages"]]
        validate_llm = FakeLLM({"clip_01": (4.0, "none")})
        SA.clip_scorer(r["event"], llm=validate_llm)(ps)               # what stage_validate's rate() sends
        svc = FakeLLM({"clip_01": (4.0, "none")})
        rec = SS.Recording(svc)
        SA.clip_scorer(r["event"], llm=rec)([dict(p) for p in r["passages"]])
        self.assertEqual(rec.prompts, validate_llm.prompts)          # moment_id never reaches the prompt


class TestService(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="sas_")
        self.addCleanup(shutil.rmtree, self.root)
        os.makedirs(os.path.join(self.root, "requests"))
        self.p = mock.patch.object(SS, "ROOT", self.root)
        self.p.start()
        self.addCleanup(self.p.stop)

    def put(self, r, name=None):
        path = os.path.join(self.root, "requests", (name or r["request_id"]) + ".json")
        with open(path, "w") as f:
            json.dump(r, f)
        return path

    def test_one_call_one_verdict_per_passage_keyed_and_the_request_done(self):
        llm = FakeLLM({"clip_01": (4.0, "none"), "clip_02": (3.0, "starts_mid_thought")})
        SS.answer(self.put(req()), llm, "ab" * 32, log=lambda *a: None)
        self.assertEqual(len(llm.prompts), 1)                          # the passages scored together
        t1 = "But we have rarely seen six red weeks."
        path = os.path.join(self.root, "results", f"m1.{hashlib.sha256(t1.encode()).hexdigest()[:16]}.{'ab' * 6}.json")
        v = json.load(open(path))
        self.assertEqual(len(v), 1)
        self.assertEqual((v[0]["score"], v[0]["affirmed"], v[0]["threshold"], v[0]["pid"], v[0]["event"]),
                         (4.0, True, 3.5, "clip_01", "Pinned: Bitcoin holds"))
        self.assertEqual(v[0]["prompt_sha256"], hashlib.sha256(llm.prompts[0].encode()).hexdigest())
        v2 = json.load(open(SS.result_path("m2", "So the cycle repeats.", "ab" * 32)))
        self.assertEqual((v2[0]["score"], v2[0]["affirmed"]), (3.0, False))
        self.assertTrue(os.path.exists(os.path.join(self.root, "requests", "done", "r1.json")))
        SS.answer(self.put(req(rid="r2", event="Pinned: another headline")), llm, "ab" * 32, log=lambda *a: None)
        self.assertEqual([e["event"] for e in json.load(open(path))], ["Pinned: Bitcoin holds", "Pinned: another headline"])

    def test_an_unparseable_reply_or_a_missing_rating_is_never_affirmed(self):
        SS.answer(self.put(req()), FakeLLM(broken=True), "cd" * 32, log=lambda *a: None)
        v = json.load(open(SS.result_path("m1", "But we have rarely seen six red weeks.", "cd" * 32)))
        self.assertEqual((v[0]["score"], v[0]["affirmed"]), (None, False))
        self.assertIn("unparseable", v[0]["error"])
        SS.answer(self.put(req(rid="r3")), FakeLLM({"clip_01": (5.0, "none")}), "cd" * 32, log=lambda *a: None)
        v = json.load(open(SS.result_path("m2", "So the cycle repeats.", "cd" * 32)))
        self.assertEqual((v[-1]["score"], v[-1]["affirmed"], v[-1]["error"]),
                         (None, False, "no rating for this pid in the reply"))

    def test_a_malformed_request_is_refused_with_why_and_never_scored(self):
        bad = [({"request_id": "../x", "event": "e", "passages": req()["passages"]}, "request_id"),
               (req(event=""), "event"), (req(passages=[]), "passages"),
               (req(passages=[dict(req()["passages"][0], duration="9")]), "duration"),
               (req(passages=[req()["passages"][0], req()["passages"][0]]), "pids must be distinct"),
               (req(passages=[dict(req()["passages"][0], moment_id="a/b")]), "moment_id"),
               (dict(req(), kind="moments"), "carries no event"), (dict(req(), kind="x"), "kind must be")]
        llm = FakeLLM()
        for i, (r, why) in enumerate(bad):
            with self.subTest(why=why):
                SS.answer(self.put(r, name=f"bad{i}"), llm, "ef" * 32, log=lambda *a: None)
                got = json.load(open(os.path.join(self.root, "requests", "failed", f"bad{i}.json")))
                self.assertIn(why, " ".join(got["why"]))
        self.assertEqual(llm.prompts, [])
        self.assertFalse(os.path.exists(os.path.join(self.root, "results")))


class TestCandidates(unittest.TestCase):
    """The builder's file contract (pp-selectid 09:59): their candidates in, their verdicts shape out."""

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="sas_c_")
        self.addCleanup(shutil.rmtree, self.root)
        os.makedirs(os.path.join(self.root, "requests"))
        self.p = mock.patch.object(SS, "ROOT", self.root)
        self.p.start()
        self.addCleanup(self.p.stop)
        sha = lambda t: hashlib.sha256(t.encode()).hexdigest()
        self.texts = {"m1": "But we hold.", "m1~trim": "we hold.", "m2": "So it goes.", "m3": "And then."}
        self.c = {"generated_at": "2026-11-13T15:00:00Z", "build": "ledger_x", "candidates": [
            {"pid": "m1", "channel": "A", "duration": 4.0, "text": self.texts["m1"], "text_sha256": sha(self.texts["m1"])},
            {"pid": "m1~trim", "channel": "A", "duration": 3.6, "text": self.texts["m1~trim"],
             "text_sha256": sha(self.texts["m1~trim"]), "trimmed_leading": "But"},
            {"pid": "m2", "channel": "B", "duration": 5.0, "text": self.texts["m2"], "text_sha256": "0" * 64},
            {"pid": "m3", "channel": "C", "duration": 2.0, "text": self.texts["m3"], "text_sha256": sha(self.texts["m3"])}]}
        self.path = os.path.join(self.root, "cands.json")
        with open(self.path, "w") as f:
            json.dump(self.c, f)

    def test_one_moments_request_per_candidate_no_event_a_bad_sha_refused_a_rated_one_reused(self):
        prior = SS.result_path("m3", self.texts["m3"], "ab" * 32)
        os.makedirs(os.path.dirname(prior))
        with open(prior, "w") as f:
            json.dump([{"kind": "moments", "event": None, "score": 4.5, "fault": "none", "affirmed": True}], f)
        c, refused = SS.enqueue_candidates(self.path, "ab" * 32)
        self.assertEqual(refused, {"m2": "text_sha256 is not the sha256 of text"})
        reqs = {json.load(open(p))["passages"][0]["moment_id"]: json.load(open(p)) for p in SS.pending()}
        self.assertEqual(sorted(reqs), ["m1", "m1~trim"])                 # m3 rated before: reused
        self.assertEqual({(r["kind"], r.get("event")) for r in reqs.values()}, {("moments", None)})
        self.assertEqual(reqs["m1~trim"]["passages"][0]["pid"], "clip_01")
        self.assertEqual(SS.problems(reqs["m1~trim"]), [])

    def test_the_verdicts_file_in_the_builders_shape(self):
        c, refused = SS.enqueue_candidates(self.path, "ab" * 32)
        llm = FakeLLM({"clip_01": (4.0, "none")})
        for p in SS.pending():
            if ".m3." not in p:                                       # m3 left unanswered: "not rated"
                SS.answer(p, llm, "ab" * 32, log=lambda *a: None)
        out = json.load(open(SS.write_verdicts(c, refused, "ab" * 32, self.path)))
        v = out["verdicts"]
        self.assertEqual((v["m1"]["affirmed"], v["m1"]["score"], v["m1~trim"]["affirmed"]), (True, 4.0, True))
        self.assertEqual((v["m2"]["affirmed"], v["m2"]["error"]), (False, "text_sha256 is not the sha256 of text"))
        self.assertEqual((v["m3"]["affirmed"], v["m3"]["error"]), (False, "not rated"))
        self.assertEqual((out["affirmed"], out["scorer"]["event"], out["scorer"]["kind"], out["scorer"]["threshold"]),
                         (2, None, "moments", 3.5))
        self.assertEqual(v["m1"]["text_sha256"], self.c["candidates"][0]["text_sha256"])
        self.assertTrue(os.path.exists(os.path.join(self.root, "verdicts", "latest.json")))

    def test_latest_prefers_a_scored_entry_for_the_event(self):
        p = SS.result_path("m1", "t", "ab" * 32)
        os.makedirs(os.path.dirname(p))
        with open(p, "w") as f:
            json.dump([{"kind": "moments", "event": None, "score": 4.0}, {"kind": "moments", "event": None, "score": None},
                       {"event": "Pinned: other", "score": 2.0}], f)               # an old entry: kind story
        self.assertEqual(SS.latest("m1", "t", "ab" * 32)["score"], 4.0)
        self.assertEqual(SS.latest("m1", "t", "ab" * 32, "story", "Pinned: other")["score"], 2.0)
        self.assertIsNone(SS.latest("m1", "t", "ab" * 32, "story", "Pinned: none"))


class TestGpu0(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="sas_g_")
        self.addCleanup(shutil.rmtree, self.root)
        os.makedirs(os.path.join(self.root, "requests"))
        self.flag = os.path.join(self.root, "yield")
        import gpu0
        self.gpu0, self.released, self.loaded = gpu0, [], []
        llm = FakeLLM({"clip_01": (4.0, "none"), "clip_02": (4.0, "none")})
        llm.start = lambda: llm
        for x in [mock.patch.object(SS, "ROOT", self.root), mock.patch.object(SS.LJ, "YIELD_FLAG", self.flag),
                  mock.patch.object(gpu0, "lease", mock.MagicMock()),
                  mock.patch.object(gpu0, "release_all", lambda: self.released.append(1)),
                  mock.patch("story_semantics.LocalLLM", lambda: self.loaded.append(1) or llm)]:
            x.start()
            self.addCleanup(x.stop)
        for i in range(10):
            with open(os.path.join(self.root, "requests", f"r{i:02d}.json"), "w") as f:
                json.dump(req(rid=f"r{i:02d}"), f)

    def test_eight_per_lease_then_gpu0_released(self):
        self.assertEqual(SS.serve_once(log=lambda *a: None), 8)
        self.assertEqual((len(self.released), len(SS.pending())), (1, 2))
        self.assertEqual(SS.serve_once(log=lambda *a: None), 2)
        self.assertEqual(len(self.released), 2)

    def test_a_render_asking_gets_gpu0_first(self):
        open(self.flag, "w").close()
        self.assertEqual(SS.serve_once(log=lambda *a: None), 0)       # not even the lease
        self.assertEqual(self.loaded, [])
        os.remove(self.flag)

        class Lease:                                                   # the render asks while the lease is taken
            def __enter__(s):
                open(self.flag, "w").close()

            def __exit__(s, *a):
                return False
        with mock.patch.object(self.gpu0, "lease", lambda owner, wait_s=0: Lease()):
            self.assertEqual(SS.serve_once(log=lambda *a: None), 0)
        self.assertEqual((self.loaded, self.released), ([], []))     # nothing loaded, nothing to release


if __name__ == "__main__":
    unittest.main()
