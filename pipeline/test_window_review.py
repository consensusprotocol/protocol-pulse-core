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
import re
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

    def test_failed_next_sentence_still_offers_previous_to_the_checker(self):
        ws, sents, a = setup_case()
        calls = []

        def checker(t):
            calls.append(t)
            return ("Regulators" not in t, "TOPIC_ONLY" if "Regulators" in t else "SUPPORTS")
        w, why, span = es.expanded_window(ws, sents, a, es.CLIP_MIN_S, es.CLIP_MAX_S, checker)
        self.assertEqual(calls, [SENTS[2], SENTS[0]])         # next fails -> previous still offered
        self.assertEqual(span["first_sentence"], SENTS[0])    # verified previous sentence included
        self.assertNotIn("Regulators", span["last_sentence"])  # failed sentence never included
        self.assertEqual(span["added_sentences"], 1)
        self.assertIsNone(w)                                  # still short: explicit HOLD reason
        self.assertIn("next sentence not verified", why)

    def test_both_directions_failing_stops_and_nothing_beyond_is_checked(self):
        ws, sents, a = setup_case()
        calls = []
        w, why, span = es.expanded_window(ws, sents, a, es.CLIP_MIN_S, es.CLIP_MAX_S,
                                          lambda t: (calls.append(t) or False, "UNRELATED"))
        self.assertIsNone(w)
        self.assertEqual(calls, [SENTS[2], SENTS[0]])         # never jumps past a failed sentence
        self.assertEqual(span["added_sentences"], 0)
        self.assertIn("next sentence not verified", why)
        self.assertIn("prev sentence not verified", why)

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
        # 1d: three sentences reach 12 s; the lower-case 'and' start is still rejected
        w, why, span = es.expanded_window(ws, sents, a, 12.0, 25.0, lambda t: (True, "SUPPORTS"))
        self.assertIsNone(w)
        self.assertIn("start rejected", why)


class TestHooksUseVerifiedExpansion(unittest.TestCase):
    @unittest.skipUnless(os.path.exists(FIX), "run-3 fixture required")
    def test_hooks_and_clips_both_use_verified_adjacent_expansion(self):
        import re
        import test_editorial_robust as ter
        F = json.load(open(FIX))
        reg = {c["channel_id"]: c for c in ter.REG.values() if c.get("channel_id")}
        same = [v for v in F["binance_verdicts"] if v["counted_as_same_event"] and v["layout_eligible"]]
        words = {vid: (w, "cached") for vid, w in F["words"].items()}

        class Rater:
            model = "fake"

            def chat_json(self, prompt, max_tokens=700, validate=None, attempts=3):
                return {"ratings": [{"id": i, "score": 3, "reason": "x"}
                                    for i in re.findall(r'<excerpt id="(p\d+)"', prompt)]}
        seen = []
        orig_e, orig_a = es.expanded_window, es.anchored_window

        def rec(ws, sents, anc, lo, hi, on_event):
            seen.append(lo)
            return orig_e(ws, sents, anc, lo, hi, lambda t: (False, "test: not on-event"))
        es.expanded_window = rec
        es.anchored_window = lambda *a, **k: (_ for _ in ()).throw(AssertionError("quote-only path used"))
        try:
            es._clip_quality({"query": F["binance"]["query"], "headline": F["binance"]["headline"]}, same,
                             ter.FakeEmbedder(), Rater(), reg, words, log=lambda s: None)
        finally:
            es.expanded_window, es.anchored_window = orig_e, orig_a
        self.assertIn(es.HOOK_MIN_S, seen)
        self.assertIn(es.CLIP_MIN_S, seen)

    def test_short_hook_quote_becomes_legal_with_a_verified_adjacent_sentence(self):
        ws, sents, a = setup_case()
        old, why, _ = es.anchored_window(ws, sents, a, es.HOOK_MIN_S, es.HOOK_MAX_S)
        self.assertIsNone(old)
        self.assertIn("minimum", why)
        w, why, span = es.expanded_window(ws, sents, a, es.HOOK_MIN_S, es.HOOK_MAX_S, lambda t: (True, "SUPPORTS"))
        self.assertIsNotNone(w, why)
        self.assertTrue(es.HOOK_MIN_S <= w["duration"] <= es.HOOK_MAX_S, w["duration"])
        self.assertIn("lost six billion dollars", w["text"])


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


# ── D2 / D3 (PBX 2026-11-09), deterministic: prompt-routed fake model, synthetic word timestamps ──

class RoutedLLM:
    """Adjudication returns `second_quote` if it is inside a shown excerpt; the verifier (also the
    adjacent-sentence checker) says SUPPORTS only for `on_event` sentences; the rater scores each
    passage with rate(text) -> (score, fault)."""
    model = "fake"

    def __init__(self, on_event, second_quote=None, rate=None, reactions=None):
        import story_semantics as sm
        self.sm, self.on_event = sm, {sm._norm(s) for s in on_event}
        self.reactions = self.on_event if reactions is None else {sm._norm(s) for s in reactions}
        self.second_quote, self.rate, self.prompts = second_quote, rate or (lambda t: (5, "none")), []

    def chat_json(self, prompt, max_tokens=700, validate=None, attempts=3):
        sm = self.sm
        self.prompts.append(prompt)
        if prompt.startswith("You verify whether"):
            hit = [i for i, t in re.findall(r'<excerpt id="([^"]+)">(.*?)</excerpt>', prompt, re.S)
                   if self.second_quote and sm._norm(self.second_quote) in sm._norm(t)]
            if not hit:
                return {"verdict": "UNRELATED", "supporting_chunk_ids": [], "evidence_quote": "", "reason": "fake"}
            return {"verdict": "CURRENT_EVENT", "supporting_chunk_ids": hit[:1],
                    "evidence_quote": self.second_quote, "confidence": 0.9, "reason": "fake"}
        if prompt.startswith("Decide whether a QUOTE"):
            q = re.search(r'<excerpt id="quote">(.*?)</excerpt>', prompt, re.S).group(1)
            return {"support": "SUPPORTS" if sm._norm(q) in self.on_event else "TOPIC_ONLY", "reason": "fake"}
        if prompt.startswith("You check ONE SENTENCE"):                 # D4 reaction / consequence verifier
            t = re.search(r'<excerpt id="sentence">(.*?)</excerpt>', prompt, re.S).group(1)
            return {"label": sm.REACTION_OK if sm._norm(t) in self.reactions else "NEW_SUBJECT", "reason": "fake"}
        if prompt.startswith("You pick clips"):
            out = []
            for pid, text in re.findall(r'<excerpt id="(p\d+r?)"[^>]*>(.*?)</excerpt>', prompt, re.S):
                s, f = self.rate(text)
                out.append({"id": pid, "score": s, "fault": f, "reason": "fake"})
            return {"ratings": out}
        raise AssertionError("unexpected prompt: " + prompt[:60])

    def verified_texts(self):
        return ([m.group(1) for p in self.prompts if p.startswith("Decide whether a QUOTE")
                 for m in [re.search(r'<excerpt id="quote">(.*?)</excerpt>', p, re.S)]] +
                [m.group(1) for p in self.prompts if p.startswith("You check ONE SENTENCE")
                 for m in [re.search(r'<excerpt id="sentence">(.*?)</excerpt>', p, re.S)]])


def _source(vid, channel, sentences, quote_idx, chunk_bounds):
    """One counted verdict + word record for a synthetic video. chunk_bounds = [(s0, s1), ...] sentence
    index ranges per retrieved excerpt; the quote is sentence `quote_idx` without its full stop."""
    import test_editorial_robust as ter
    ws = words_for(sentences)
    sents = es._word_sentences(ws)
    ex = []
    for s0, s1 in chunk_bounds:
        t0, t1 = ws[sents[s0][0]]["start"], ws[sents[s1][1]]["end"]
        ex.append({"chunk_id": ts.chunk_id(vid, t0, t1), "start": t0, "end": t1,
                   "text": " ".join(sentences[s0:s1 + 1])})
    q = sentences[quote_idx].rstrip(".")
    cid = next(x["chunk_id"] for x in ex if q in x["text"])
    v = {"video_id": vid, "channel": channel, "channel_id": ter.REG[channel]["channel_id"],
         "layout_eligible": True, "counted_as_same_event": True, "evidence_quote": q,
         "supporting_chunk_ids": [cid], "excerpts": ex, "title": f"{channel} show",
         "published_at": "2026-11-08T12:00:00+00:00", "canonical_url": ts.canonical_url(vid)}
    return v, ({"words": ws, "transcript_sha256": "sha-" + vid, "transcript_method": "whisper_words"}, "cached")


A = ["Good morning everyone and welcome back to the show.",                                                  # 0
     "Binance lost six billion dollars to hackers overnight in the largest exchange theft anyone has ever recorded.",  # 1 q1
     "Anyway our sponsor this week makes great hardware wallets for everyone listening at home.",            # 2
     "Let me also tell you about the weather here because it has been really nice lately.",                 # 3
     "We had a great barbecue with the family and the kids loved every minute of it.",                      # 4
     "Okay back to the news now and the bigger picture for the market this week.",                          # 5
     "Regulators ordered every American bank to report its exposure to the Binance hack before Friday morning arrives.",  # 6 q2
     "The exchange says customer withdrawals will resume within forty eight hours once the audit of the hot wallets ends.",  # 7
     "Thanks for watching and do not forget to subscribe to the channel for more."]                          # 8
B = ["Welcome back to the program everyone.",
     "The Binance hack drained six billion dollars from hot wallets and nobody saw it coming at all.",       # q
     "Federal regulators are now asking banks how much exposure they have to the exchange after the theft.",
     "That is all for today so thanks for tuning in."]
ON_EVENT = [A[1], A[6], A[7], B[1], B[2]]
QUERY = {"query": {"underlying_event": "Hackers stole six billion dollars from the Binance exchange",
                   "action": "hack", "affected_object": "Binance exchange",
                   "entities": [{"name": "Binance", "aliases": []}]},
         "headline": "Binance hacked for six billion dollars"}


class TestD2TwoVerifiedWindowsPerVideo(unittest.TestCase):
    def setUp(self):
        import test_editorial_robust as ter
        self.ter = ter
        self.reg = {c["channel_id"]: c for c in ter.REG.values() if c.get("channel_id")}
        self.va, wa = _source("VIDAAAAAAA1", "The Bitcoin Layer", A, 1, [(0, 3), (4, 6), (7, 8)])
        self.vb, wb = _source("VIDBBBBBBB1", "Bitcoin Magazine", B, 1, [(0, 3)])
        self.words = {"VIDAAAAAAA1": wa, "VIDBBBBBBB1": wb}

    def cq(self, llm):
        return es._clip_quality(QUERY, [self.va, self.vb], self.ter.FakeEmbedder(), llm, self.reg,
                                self.words, log=lambda s: None, today="2026-11-09")

    def test_two_window_source_makes_a_two_video_story_producible(self):
        """Positive: video A carries two independently verified quotes far apart -> two windows."""
        cq = self.cq(RoutedLLM(ON_EVENT, second_quote=A[6].rstrip(".")))
        a1 = [x for x in cq["anchors"] if x["video_id"] == "VIDAAAAAAA1"]
        self.assertEqual([x["quote_index"] for x in a1], [1, 2])
        self.assertEqual(a1[0]["second_quote"], "verified")
        self.assertTrue(cq["producible"], cq["reason"])
        chosen_a = sorted((p["start"], p["end"]) for p in cq["chosen"] if p["video_id"] == "VIDAAAAAAA1")
        self.assertEqual(len(chosen_a), 2, cq["chosen"])
        self.assertLessEqual(chosen_a[0][1], chosen_a[1][0])          # R2: no passage reuse
        self.assertTrue(any(A[1][:20] in p["text"] for p in cq["chosen"]))
        self.assertTrue(any(A[6][:20] in p["text"] for p in cq["chosen"]))

    def test_second_quote_must_pass_the_same_verification(self):
        """Negative: the second quote is CURRENT_EVENT and verbatim, but the independent verifier says
        TOPIC_ONLY -> no second window; one window per video cannot make hook + 2 clips here."""
        cq = self.cq(RoutedLLM([s for s in ON_EVENT if s != A[6]], second_quote=A[6].rstrip(".")))
        a1 = [x for x in cq["anchors"] if x["video_id"] == "VIDAAAAAAA1"]
        self.assertEqual([x["quote_index"] for x in a1], [1])
        self.assertTrue(a1[0]["second_quote"].startswith("second quote not verified"), a1[0]["second_quote"])
        self.assertFalse(cq["producible"])

    def test_r2_hook_and_clip_never_share_a_passage(self):
        """Negative (R2): each video has one verified quote whose hook and clip windows overlap;
        hook + 2 clips would need a passage twice, so the story is not producible."""
        self.va, _ = _source("VIDAAAAAAA1", "The Bitcoin Layer", A, 6, [(0, 3), (4, 6), (7, 8)])
        cq = self.cq(RoutedLLM(ON_EVENT))                               # no second quote anywhere
        kinds = sorted(p["kind"] for p in cq["candidates"] if p["video_id"] == "VIDAAAAAAA1")
        self.assertEqual(kinds, ["clip", "hook"])                       # both windows exist ...
        self.assertFalse(cq["producible"], cq.get("chosen"))            # ... but never both in one video

    def test_second_window_never_reuses_the_first_passage(self):
        """Negative (R2): a second 'verified' quote on the first quote's passage yields no new window."""
        orig = es.second_verified_quote
        es.second_verified_quote = lambda llm, q, v, today="": (
            (dict(v), None) if v["video_id"] == "VIDAAAAAAA1" else (None, "none"))
        try:
            cq = self.cq(RoutedLLM(ON_EVENT))
        finally:
            es.second_verified_quote = orig
        a2 = [x for x in cq["anchors"] if x["video_id"] == "VIDAAAAAAA1" and x["quote_index"] == 2][0]
        self.assertTrue(all(str(w).startswith("deduped") or str(w).startswith("none")
                            for w in a2["windows"].values()), a2["windows"])
        self.assertFalse(cq["producible"])
        for i, p in enumerate(cq["chosen"]):
            for o in cq["chosen"][i + 1:]:
                self.assertFalse(p["video_id"] == o["video_id"] and not (p["end"] <= o["start"] or p["start"] >= o["end"]))


C = ["Binance confirmed the hack this morning.",                                                       # 0 (1d: fits 20 s)
     "It means six billion dollars of customer money left the exchange in one night and nobody stopped it.",  # 1 quote
     "Withdrawals stayed frozen for hours while the exchange tried to find the hole.",                       # 2
     "Thanks for watching and see you all tomorrow on the stream."]                                          # 3


class TestD3BoundaryRepair(unittest.TestCase):
    def setUp(self):
        import test_editorial_robust as ter
        self.ter = ter
        self.reg = {c["channel_id"]: c for c in ter.REG.values() if c.get("channel_id")}
        self.vc, wc = _source("VIDCCCCCCC1", "The Bitcoin Layer", C, 1, [(0, 3)])
        self.words = {"VIDCCCCCCC1": wc}

    def cq(self, llm):
        return es._clip_quality(QUERY, [self.vc], self.ter.FakeEmbedder(), llm, self.reg, self.words,
                                log=lambda s: None, today="2026-11-09")

    @staticmethod
    def rate(fault):
        return lambda t: ((3, fault) if t.startswith("It means") else
                          (4.5, "none") if t.startswith("Binance confirmed") else (5, "none"))

    def test_mid_thought_window_passes_after_verified_repair(self):
        """Positive: the clip 'It means ... hole.' is rated 3 for starting mid-thought; the previous
        sentence is verified on-event, so it is added (19.2 s <= 20, 1d budget) and the re-rated window (4.5)
        clears the unchanged 3.5 floor. The hook version cannot grow past 12 s and stays rejected."""
        llm = RoutedLLM([C[0], C[1], C[2]], rate=self.rate("starts_mid_thought"))
        cq = self.cq(llm)
        reps = {r["kind"]: r for r in cq["boundary_repairs"]}
        self.assertEqual(reps["clip"]["result"], "repaired; re-rated")
        self.assertEqual((reps["clip"]["score_before"], reps["clip"]["score_after"]), (3, 4.5))
        self.assertEqual(reps["clip"]["span"]["added_sentences"], 1)
        self.assertEqual(reps["clip"]["span"]["expansion"][0]["sentence"], C[0])
        self.assertIn("would exceed 12.0 s", reps["hook"]["result"])
        fixed = [p for p in cq["candidates"] if p.get("repaired_from")]
        self.assertEqual(len(fixed), 1)
        self.assertEqual((fixed[0]["kind"], fixed[0]["start"]), ("clip", 0.0))
        self.assertGreaterEqual(fixed[0]["clip_score"], es.CLIP_MIN_SCORE)
        self.assertTrue(fixed[0]["text"].startswith("Binance confirmed") and fixed[0]["text"].endswith("hole."))

    def test_off_topic_window_is_never_repaired(self):
        """Negative: the same window rated 3 as off_topic stays rejected; nothing is added or re-rated."""
        llm = RoutedLLM([C[0], C[1], C[2]], rate=self.rate("off_topic"))
        cq = self.cq(llm)
        self.assertEqual(cq["boundary_repairs"], [])
        self.assertFalse([p for p in cq["candidates"] if p.get("repaired_from")])
        self.assertNotIn(C[0], llm.verified_texts())                   # the checker never saw C0
        self.assertFalse(cq["producible"])

    def test_repaired_window_still_below_the_floor_stays_rejected(self):
        """D3: 'rejected only if it still fails after repair' - one repair, one re-rating, no second try."""
        llm = RoutedLLM([C[0], C[1], C[2]],
                        rate=lambda t: (3, "starts_mid_thought") if t.startswith(("It means", "Binance confirmed"))
                        else (5, "none"))
        cq = self.cq(llm)
        fixed = [p for p in cq["candidates"] if p.get("repaired_from")]
        self.assertEqual(len(fixed), 1)
        self.assertLess(fixed[0]["clip_score"], es.CLIP_MIN_SCORE)
        self.assertEqual(sorted(r["kind"] for r in cq["boundary_repairs"]), ["clip", "hook"])   # no repair of a repair
        self.assertFalse(cq["producible"])

    def test_failed_checker_closes_the_repair(self):
        """Negative: boundary fault, but the previous sentence is not verified on-event -> rejected."""
        llm = RoutedLLM([C[1], C[2]], rate=self.rate("starts_mid_thought"))
        cq = self.cq(llm)
        reps = {r["kind"]: r for r in cq["boundary_repairs"]}
        self.assertTrue(reps["clip"]["result"].startswith("boundary repair: prev sentence not verified on-event"),
                        reps["clip"]["result"])
        self.assertFalse([p for p in cq["candidates"] if p.get("repaired_from")])


FIX4 = os.path.join(REPO, "references", "editorial_failures", "2026-11-07_adjacent_reaction",
                    "adjacent_reaction_fixture.json")


def _fixture_case(vid):
    """Real words + verified anchor of one fresh_20261107_080503 Binance case (build_fixture.py)."""
    F = json.load(open(FIX4))
    c = F["cases"][vid]
    ws = c["words"]
    sents = es._word_sentences(ws)
    spans = [ts.parse_chunk_id(x)[1:] for x in c["supporting_chunk_ids"]]
    a = es.align_quote(c["evidence_quote"], ws, max(0, min(s for s, _ in spans) - 30), max(e for _, e in spans) + 30)
    si = next(i for i, (x, y) in enumerate(sents) if x <= a["w1"] <= y)
    nxt = " ".join(w["word"].strip() for w in ws[sents[si + 1][0]:sents[si + 1][1] + 1])
    return F["query"], ws, sents, a, es._anchor_text(ws, sents, a["w0"], a["w1"]), nxt


class TestD4AdjacentReaction(unittest.TestCase):
    """D4 (PBX 2026-11-09 01:34): an adjacent sentence joins a window only if (a) it refers back to the
    verified event or shares an entity/number with the anchor, (b) it starts within 8 s of the anchor
    boundary it extends, (c) an independent verifier returns SAME_EVENT_REACTION_OR_CONSEQUENCE;
    NEW_SUBJECT / OTHER_EVENT are hard rejects; at most two per direction."""

    def test_verifier_prompt_is_pinned_to_the_d4_question(self):
        import story_semantics as sm
        self.assertEqual(sm.REACTION_QUESTION,
                         "is this sentence a reaction to or consequence of the same verified event?")
        self.assertEqual(sm.REACTION_LABELS, ("SAME_EVENT_REACTION_OR_CONSEQUENCE", "NEW_SUBJECT", "OTHER_EVENT"))
        self.assertEqual(sm.REACTION_OK, sm.REACTION_LABELS[0])
        p = sm.REACTION_PROMPT
        self.assertIn("Answer exactly this question: " + sm.REACTION_QUESTION, p)
        for lab in sm.REACTION_LABELS:
            self.assertIn(f'"{lab}"', p)
        for w in ("related", "relevant", "similar", "topic", "restate", "supports"):
            self.assertNotIn(w, p.lower(), f"verifier prompt drifted toward a similarity/restatement gate: {w!r}")
        llm = RoutedLLM([])
        sm.verify_reaction(llm, {"underlying_event": "E"}, "Anchor sentence here.", "Some sentence here.")
        self.assertIn(sm.REACTION_QUESTION, llm.prompts[-1])
        self.assertIn('<excerpt id="sentence">Some sentence here.</excerpt>', llm.prompts[-1])

    def test_window_never_exceeds_three_sentences(self):
        # 1d (2026-11-11): one to three whole sentences; the total binds before the D4 per-direction cap
        txt = ["It hurt.", "It hurt more.", "It hurt again.", SENTS[1], "This is bad.", "This is worse.", "This is the worst."]
        ws = words_for(txt)
        a = es.align_quote(SENTS[1].rstrip("."), ws, 0, 1000)
        calls = []
        w, why, span = es.expanded_window(ws, es._word_sentences(ws), a, 60.0, 80.0, lambda t: (calls.append(t) or True, "ok"))
        self.assertEqual(sorted(c["direction"] for c in span["expansion"] if c["on_event"]), ["next", "prev"])
        self.assertEqual(sum("sentences; direction closed" in c["detail"] for c in span["expansion"]), 2)
        self.assertLessEqual(span["n_sentences"], 3)
        self.assertNotIn(txt[0], calls)
        self.assertNotIn(txt[6], calls)

    def test_sentence_starting_more_than_8_s_from_the_anchor_is_never_checked(self):
        txt = [SENTS[1], "This is a long reaction sentence that keeps going and going and going for a while.",
               "And that hurts everyone."]
        ws = words_for(txt)
        a = es.align_quote(SENTS[1].rstrip("."), ws, 0, 1000)
        calls = []
        w, why, span = es.expanded_window(ws, es._word_sentences(ws), a, 60.0, 80.0, lambda t: (calls.append(t) or True, "ok"))
        self.assertEqual(calls, [txt[1]])
        self.assertTrue(any("from the anchor boundary" in c["detail"] for c in span["expansion"]), span["expansion"])

    def test_reaction_extends_the_window_where_the_restatement_checker_could_not(self):
        """The host states the event in one short sentence, then reacts. The reaction is not a
        restatement (verify_support says TOPIC_ONLY) but it is a reaction to the same event, so D4
        admits it and the hook reaches a legal 8-12 s."""
        import test_editorial_robust as ter
        R = ["Welcome back to the show everyone.",
             "Binance lost six billion dollars to hackers overnight.",
             "That is a disaster for every customer who kept their coins on that exchange.",
             "Anyway our sponsor this week makes great hardware wallets."]
        v, wr = _source("VIDRRRRRRR1", "The Bitcoin Layer", R, 1, [(0, 3)])
        reg = {c["channel_id"]: c for c in ter.REG.values() if c.get("channel_id")}
        llm = RoutedLLM([R[1]], reactions=[R[2]])
        cq = es._clip_quality(QUERY, [v], ter.FakeEmbedder(), llm, reg, {"VIDRRRRRRR1": wr},
                              log=lambda s: None, today="2026-11-09")
        hooks = [p for p in cq["candidates"] if p["kind"] == "hook"]
        self.assertEqual(len(hooks), 1, cq["anchors"])
        self.assertTrue(hooks[0]["text"].startswith("Binance lost") and hooks[0]["text"].endswith("exchange."))
        self.assertTrue(es.HOOK_MIN_S <= hooks[0]["duration"] <= es.HOOK_MAX_S, hooks[0]["duration"])
        self.assertFalse(es.sentence_on_event(llm, QUERY["query"], R[2])[0])   # the old checker rejects it

    @unittest.skipUnless(os.path.exists(FIX4), "D4 fixture required")
    def test_negative_market_commentary_without_reference_still_fails(self):
        """Negative (2), real CoinTelegraph L9tzgg6PXi8: anchor 'We've just had the Binance hack last week.';
        neighbours 'Look, Bitcoin holding around $80,000.' and 'We've had the midterm elections today.'
        have no backward reference, shared entity or number: rejected at (a), no verifier call."""
        q, ws, sents, a, at, nxt = _fixture_case("L9tzgg6PXi8")
        llm = RoutedLLM([])
        for lo, hi in ((es.HOOK_MIN_S, es.HOOK_MAX_S), (es.CLIP_MIN_S, es.CLIP_MAX_S)):
            w, why, span = es.expanded_window(ws, sents, a, lo, hi, lambda t: es.adjacent_admissible(llm, q, at, t))
            self.assertIsNone(w)
            checked = [c for c in span["expansion"] if c["on_event"] is not None]
            self.assertTrue(checked)
            self.assertTrue(all(not c["on_event"] and c["detail"].startswith("no backward reference") for c in checked), checked)
            self.assertIn("Bitcoin holding around", " | ".join(c["sentence"] for c in checked))
        self.assertEqual(llm.prompts, [])

    @unittest.skipUnless(os.path.exists(FIX4), "D4 fixture required")
    def test_negative_different_news_item_is_a_hard_reject(self):
        """Negative (3), real Scott Melker y0SjcqQPdpA: after the Binance / Fed-OCC anchor the host says
        'And then we got an update on that CFDC perp story.' It passes (a) only lexically ('that');
        the verifier's NEW_SUBJECT is a hard reject."""
        q, ws, sents, a, at, nxt = _fixture_case("y0SjcqQPdpA")
        self.assertIn("CFDC perp story", nxt)
        self.assertIn("that", es.backward_reference(nxt, at, q))
        llm = RoutedLLM([])                       # the fake verifier answers NEW_SUBJECT for this sentence
        ok, detail = es.adjacent_admissible(llm, q, at, nxt)
        self.assertFalse(ok)
        self.assertTrue(detail.startswith("NEW_SUBJECT"), detail)
        self.assertEqual(sum(p.startswith("You check ONE SENTENCE") for p in llm.prompts), 1)


class TestD4aInterjectionTransparency(unittest.TestCase):
    """D4a (PBX 2026-11-09 ~02:05): content-free interjections are transparent to rule (a): skipped
    for the deictic/entity/number check, not counted toward the two-sentence cap, and they do not
    close the direction. The 8 s bound and the independent SAME_EVENT verifier still apply to whatever
    window results."""

    @unittest.skipUnless(os.path.exists(FIX4), "D4 fixture required")
    def test_positive_080503_btc_sessions_interjection_then_reaction_assembles_hook(self):
        """The BTC Sessions 9La50F_lmd0 case from fresh_20261107_080503: anchor 'CZ's the stolen
        stuff from Binance is also in there now.' (2.80 s) is followed by 'Oh.' (interjection) then
        'That's like a pittance ... chump change.' (reaction with 'that' backward ref). With D4a the
        interjection is transparent and the reaction produces a legal 8-12 s hook."""
        q, ws, sents, a, at, _ = _fixture_case("9La50F_lmd0")
        # The mock verifier accepts reactions (sentences with "that" backward ref to the event)
        si = next(i for i, (x, y) in enumerate(sents) if x <= a["w1"] <= y)
        oh_text = " ".join(w["word"].strip() for w in ws[sents[si + 1][0]:sents[si + 1][1] + 1])
        self.assertIn(oh_text.strip().lower().rstrip("."), es.INTERJECTIONS)
        # "That's like a pittance..." has a backward reference via "that"
        pittance = " ".join(w["word"].strip() for w in ws[sents[si + 2][0]:sents[si + 2][1] + 1])
        self.assertIsNotNone(es.backward_reference(pittance, at, q))
        calls = []

        def checker(text):
            calls.append(text)
            return (True, "SAME_EVENT_REACTION_OR_CONSEQUENCE: mock")
        w, why, span = es.expanded_window(ws, sents, a, es.HOOK_MIN_S, es.HOOK_MAX_S, checker)
        self.assertIsNotNone(w, f"hook should be legal; got: {why}")
        self.assertTrue(es.HOOK_MIN_S <= w["duration"] <= es.HOOK_MAX_S, w["duration"])
        # "Oh." was NOT sent to the checker (transparent)
        self.assertNotIn(oh_text, calls, "interjection must not be sent to the verifier")
        # The interjection is in the expansion log as transparent
        intj_entries = [c for c in span["expansion"] if "interjection" in (c.get("detail") or "")]
        self.assertTrue(intj_entries, "interjection must be logged as transparent")

    def test_interjection_does_not_count_toward_cap_and_does_not_close_direction(self):
        """An interjection 'Oh.' between the anchor and a real reaction does not consume a cap slot.
        With cap=2, anchor + Oh + reaction1 + reaction2 should admit both reactions (2 real sentences)
        plus the transparent interjection."""
        txt = [SENTS[1],             # 0: anchor
               "Oh.",                 # 1: interjection (transparent)
               "That is terrible.",   # 2: reaction 1
               "It hurts everyone.",  # 3: reaction 2
               "And now for something completely different."]   # 4: would be cap=3
        ws = words_for(txt)
        sents_l = es._word_sentences(ws)
        a = es.align_quote(SENTS[1].rstrip("."), ws, 0, 1000)
        calls = []
        w, why, span = es.expanded_window(ws, sents_l, a, 60.0, 80.0,
                                          lambda t: (calls.append(t) or True, "ok"))
        # "Oh." was NOT sent to the checker
        self.assertNotIn("Oh.", calls, "interjection must not be sent to the verifier")
        # Both real reactions were checked
        self.assertIn(txt[2], calls)
        self.assertIn(txt[3], calls)
        # 1d: anchor + 2 real reactions = 3 counted sentences (the interjection is transparent);
        # txt[4] would be a 4th counted sentence and closes the direction
        real_next = [c for c in span["expansion"] if c["direction"] == "next" and c["on_event"] is True]
        self.assertEqual(len(real_next), 2)
        cap_entries = [c for c in span["expansion"] if "sentences; direction closed" in c["detail"]]
        self.assertTrue(cap_entries, "a closing entry must appear for the 4th counted sentence")

    def test_interjection_alone_does_not_make_a_window_legal(self):
        """An interjection next to a short anchor does not, by itself, make the window long enough."""
        txt = ["Oh.", SENTS[1], "Wow."]
        ws = words_for(txt, step=0.5)
        sents_l = es._word_sentences(ws)
        a = es.align_quote(SENTS[1].rstrip("."), ws, 0, 1000)
        calls = []
        w, why, span = es.expanded_window(ws, sents_l, a, 20.0, 25.0,
                                          lambda t: (calls.append(t) or True, "ok"))
        self.assertIsNone(w)
        self.assertNotIn("Oh.", calls)
        self.assertNotIn("Wow.", calls)


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
