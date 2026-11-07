#!/usr/bin/env python3
"""Tests: verified adjacent clip windows + AUTO's local four-law review (PBX 2026-11-06 23:45).

Must fail if:
  * a quote sentence is rejected solely for being short when a verified adjacent sentence would
    make it legal;
  * filler VO is accepted;
  * a sequence without progression reaches cut.
GPU tests (real gemma3:27b on GPU0) run when GPU_TESTS=1.

Run: cd ~/protocol_pulse && python3 -m pytest -q pipeline/test_window_review.py
     GPU_TESTS=1 CUDA_VISIBLE_DEVICES=0 python3 -m pytest -q pipeline/test_window_review.py
"""
import copy
import json
import os
import shutil
import sys
import tempfile
import unittest

PIPELINE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(PIPELINE)
sys.path.insert(0, PIPELINE)

import editorial_select as es  # noqa: E402
import editorial_gate as eg  # noqa: E402
import editorial_review as er  # noqa: E402
import transcript_store as ts  # noqa: E402

GPU = os.environ.get("GPU_TESTS") == "1"
FIX = os.path.join(REPO, "references", "editorial_failures", "2026-11-06_false_stale_binance",
                   "run3_binance_fixture.json")
V2F_EDL = os.path.join(REPO, "references", "v2f_2026-11-06", "run", "edl.json")
FILLER = "This story is unfolding right now."


def words_for(sentences, t0=0.0, step=0.5):
    out, t = [], t0
    for s in sentences:
        for w in s.split():
            out.append({"word": w, "start": round(t, 3), "end": round(t + 0.4, 3)})
            t += step
        t += 0.3
    return out


SENTS = ["Markets were quiet in early trading today.",                               # 0 prev
         "The exchange lost six billion dollars to hackers overnight.",              # 1 quote (~4.5 s)
         "Regulators asked banks to report any exposure by Friday morning.",         # 2 next
         "Two stablecoin issuers froze funds linked to the stolen coins.",           # 3
         "Anyway, our sponsor this week makes great hardware wallets for everyone."]  # 4 off-topic


def setup_case():
    ws = words_for(SENTS)
    sents = es._word_sentences(ws)
    a = es.align_quote("The exchange lost six billion dollars to hackers overnight", ws, 0, 1000)
    return ws, sents, a


class TestVerifiedAdjacentExpansion(unittest.TestCase):
    def test_short_quote_becomes_legal_with_verified_adjacent_sentences(self):
        ws, sents, a = setup_case()
        old, why, _ = es.anchored_window(ws, sents, a, es.CLIP_MIN_S, es.CLIP_MAX_S)
        self.assertIsNone(old)
        self.assertIn("minimum", why)                       # the old rule kills it for length alone
        seen = []
        w, why, span = es.expanded_window(ws, sents, a, es.CLIP_MIN_S, es.CLIP_MAX_S,
                                          lambda t: (seen.append(t) or True, "SUPPORTS"))
        self.assertIsNotNone(w, why)
        self.assertTrue(es.CLIP_MIN_S <= w["duration"] <= es.CLIP_MAX_S, w["duration"])
        self.assertIn("lost six billion dollars", w["text"])
        self.assertNotIn("sponsor", w["text"])
        self.assertEqual(span["added_sentences"], len(seen))  # every added sentence was checked
        self.assertTrue(all(c["on_event"] for c in span["expansion"] if c["on_event"] is not None))

    def test_first_failing_sentence_stops_expansion(self):
        ws, sents, a = setup_case()
        calls = []

        def checker(t):
            calls.append(t)
            return ("Regulators" not in t, "TOPIC_ONLY" if "Regulators" in t else "SUPPORTS")
        w, why, span = es.expanded_window(ws, sents, a, es.CLIP_MIN_S, es.CLIP_MAX_S, checker)
        self.assertIsNone(w)
        self.assertIn("expansion stopped", why)
        self.assertEqual(len(calls), 1, calls)               # nothing is checked after the first failure
        self.assertNotIn("Regulators", span["last_sentence"])
        self.assertEqual(span["added_sentences"], 0)

    def test_never_exceeds_maximum_and_never_pads_off_event(self):
        ws, sents, a = setup_case()
        w, why, span = es.expanded_window(ws, sents, a, 40.0, 45.0, lambda t: ("sponsor" not in t, "x"))
        self.assertIsNone(w)
        self.assertNotIn("sponsor", " ".join(c["sentence"] for c in span["expansion"] if c["on_event"]))
        w, why, span = es.expanded_window(ws, sents, a, es.CLIP_MIN_S, 14.0, lambda t: (True, "SUPPORTS"))
        if w:
            self.assertLessEqual(w["duration"], 14.0)

    def test_boundary_still_enforced(self):
        sents_txt = ["and then the exchange said more about it all.", SENTS[1], SENTS[2], SENTS[3]]
        ws = words_for(sents_txt)
        sents = es._word_sentences(ws)
        a = es.align_quote("The exchange lost six billion dollars to hackers overnight", ws, 0, 1000)
        w, why, span = es.expanded_window(ws, sents, a, 18.0, 25.0, lambda t: (True, "SUPPORTS"))
        self.assertIsNone(w)
        self.assertIn("start rejected", why)


class FakeReviewer:
    model = "gemma3:27b"

    def __init__(self, out=None, raise_parse=False):
        self.out, self.raise_parse, self.prompts = out, raise_parse, []

    def chat_json(self, prompt, max_tokens=700, validate=None, attempts=3):
        import story_semantics as sm
        self.prompts.append(prompt)
        if self.raise_parse:
            raise sm.LLMParseError("bad json", ["{"])
        if validate:
            err = validate(self.out)
            if err:
                raise sm.LLMParseError(err, [json.dumps(self.out)])
        return copy.deepcopy(self.out)


def good_review(edl, progresses=True, vo_jobs=None):
    return {"clips": [{"index": c["index"], "adds_type": "fact", "adds": "adds a new fact",
                       "adds_new_information": True} for c in edl["clips"]],
            "vo_jobs": vo_jobs or {},
            "takeaway": {"text": "Concrete takeaway.", "concrete": True, "supported": True},
            "sequence": {"hook": "h", "development": "d", "payoff": "p", "progresses": progresses},
            "inconclusive": False}


def v2f_edl(intro=None):
    import select_passages as sp
    e = json.load(open(V2F_EDL))
    chs = sorted({e["hook"]["channel"]} | {c["channel"] for c in e["clips"]})
    e["vo"] = sp._generate_vo_script("dollar hegemony", e["hook"]["text"], e["clips"], chs)
    if intro:
        e["vo"]["intro"] = intro
    return e


@unittest.skipUnless(os.path.exists(V2F_EDL), "v2f reference EDL not present")
class TestLocalReviewAndGate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="review_test_")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_review_shape_provenance_and_positive_control(self):
        edl = v2f_edl()
        r = er.write_review(FakeReviewer(good_review(edl)), edl, self.tmp)
        self.assertEqual(r["review_type"], "model")
        self.assertTrue(r["reviewed_by"].endswith("@ultron-local"))
        self.assertIs(r["external_model_used"], False)
        self.assertEqual(eg.run_gate(self.tmp, edl)["verdict"], "READY_FOR_RENDER")

    def test_filler_vo_is_never_accepted_even_if_the_model_affirms_it(self):
        edl = v2f_edl(intro=FILLER)
        out = good_review(edl, vo_jobs={"intro": {"job": "context", "why": "sets the scene", "earned": True}})
        er.write_review(FakeReviewer(out), edl, self.tmp)
        g = eg.run_gate(self.tmp, edl)
        self.assertEqual(g["verdict"], "HOLD")
        self.assertFalse(g["laws"]["LAW_2_VO_HAS_A_JOB"]["pass"])

    def test_sequence_without_progression_never_reaches_cut(self):
        import run_fresh as rf
        edl = v2f_edl()
        json.dump(edl, open(os.path.join(self.tmp, "edl.json"), "w"))
        er.write_review(FakeReviewer(good_review(edl, progresses=False)), edl, self.tmp)
        run = rf.Run(self.tmp)
        with self.assertRaises(rf.Hold) as cm:
            rf.stage_validate(run)                            # validate runs before cut; it must stop here
        self.assertIn("LAW_4_SEQUENCE_PROGRESSES", str(cm.exception))
        src = open(rf.__file__).read()
        order = [src.index(f'run.stage("{s}"') for s in ("select", "review", "validate", "cut")]
        self.assertEqual(order, sorted(order))

    def test_inconclusive_or_unparseable_review_holds(self):
        edl = v2f_edl()
        for llm in (FakeReviewer(raise_parse=True),
                    FakeReviewer({"inconclusive": True, "inconclusive_reason": "cannot judge"})):
            r = er.write_review(llm, edl, self.tmp)
            self.assertTrue(r["inconclusive"])
            self.assertEqual(eg.run_gate(self.tmp, edl)["verdict"], "HOLD")

    def test_missing_review_holds(self):
        self.assertEqual(eg.run_gate(self.tmp, v2f_edl())["verdict"], "HOLD")


@unittest.skipUnless(GPU and os.path.exists(FIX), "GPU_TESTS=1 and the run-3 fixture required")
class TestRealMaterialGPU(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import story_semantics as sm
        cls.L = sm.LocalLLM().start()
        cls.F = json.load(open(FIX))

    @classmethod
    def tearDownClass(cls):
        cls.L.stop()

    def test_real_binance_short_quotes_now_legal_or_explicit_hold(self):
        q = self.F["binance"]["query"]
        cache, results = {}, {}
        for v in self.F["binance_verdicts"]:
            if not (v["counted_as_same_event"] and v["layout_eligible"]):
                continue
            ws = self.F["words"][v["video_id"]]["words"]
            spans = [ts.parse_chunk_id(x)[1:] for x in v["supporting_chunk_ids"]]
            a = es.align_quote(v["evidence_quote"], ws, min(s for s, _ in spans) - 30, max(e for _, e in spans) + 30)
            sents = es._word_sentences(ws)
            old, _, old_span = es.anchored_window(ws, sents, a, es.CLIP_MIN_S, es.CLIP_MAX_S)
            self.assertIsNone(old)                            # 4.5-9.7 s under the old rule
            w, why, span = es.expanded_window(ws, sents, a, es.CLIP_MIN_S, es.CLIP_MAX_S,
                                              lambda t: es.sentence_on_event(self.L, q, t, cache))
            results[v["channel"]] = (w, why, span)
            if w is None:
                self.assertTrue(why)                          # explicit reason
            else:
                self.assertTrue(es.CLIP_MIN_S <= w["duration"] <= es.CLIP_MAX_S)
            added = [c for c in span["expansion"] if c["on_event"]]
            self.assertEqual(len(added), span["added_sentences"])
        self.assertEqual(len(results), 3)
        print("\nREAL BINANCE WINDOWS:")
        for ch, (w, why, span) in results.items():
            print(f"  {ch}: {span['start']:.2f}-{span['end']:.2f} ({span['duration']} s) "
                  f"{'LEGAL' if w else 'HOLD: ' + why}")
            for c in span["expansion"]:
                print(f"     {c['direction']}: {c['on_event']} | {c['detail'][:90]} | {c['sentence'][:80]}")

    def test_real_local_review_is_complete(self):
        edl = v2f_edl()
        tmp = tempfile.mkdtemp()
        try:
            r = er.write_review(self.L, edl, tmp)
            g = eg.run_gate(tmp, edl)
            self.assertFalse(r.get("inconclusive"), r.get("inconclusive_reason"))
            self.assertTrue(g["laws"]["L0_REVIEW"]["pass"])
            print("\nREAL V2F REVIEW GATE:", g["verdict"], {k: v["pass"] for k, v in g["laws"].items()})
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
