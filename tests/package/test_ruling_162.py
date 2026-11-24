#!/usr/bin/env python3
"""RULING 162 (orchestrator 07:45 ET Nov 24, from PBX's review of pin afd8977d at 07:37), STANDING, BOTH SIDES.

(1) A CLIP NEVER ENDS WHILE THE SPEAKER IS STILL MID-SENTENCE: pipeline/out_edge.py asks the integrator's ONE question
(owner_rules.out_edge, the render's model and settings) of every pool moment; a clip whose thought runs on is EXTENDED to
the sentence that finishes it (tail_variant.extend: a new span, every gate again) or REFUSED; no answer is UNVERIFIED
(ruling 160 (2a)). The OUT edge of the recogniser's CUTTABLE check is HARD too (package.soft_edges: the IN edge only).
The case: the opener of pin afd8977d (Simply Bitcoin 1cb16751, 0shaXx_n870), "Stocks had fallen seven days in a row,
Bitcoin was on its way to 55K, and everybody had the same story." -- the source goes on "The AI bubble had finally
popped, and a full market crash was coming Monday morning." (the integrator's finding, 07:5x ET Nov 24).
Offline: word-timed test sources (0.3 s a word), a fake router; owner_rules.py is the integrator's real file."""
import hashlib
import json
import os
import sys
import types
import unittest
import unittest.mock

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
for _p in ("pipeline", "tests/package", "tests/eligibility"):
    sys.path.insert(0, os.path.join(REPO, _p))
import eligibility as E  # noqa: E402
import moments as M  # noqa: E402
import out_edge as OE  # noqa: E402
import package as PK  # noqa: E402
import providers as P  # noqa: E402
import tail_variant as TV  # noqa: E402
from test_eligibility import NOW, REG, source  # noqa: E402

CTX = E.Context(NOW, REG)
OPENER = ("Stocks had fallen seven days in a row, Bitcoin was on its way to 55K, and everybody had the same "
          "story.")
SENTENCES = ["Everybody was scared that whole week.", OPENER,
             "The AI bubble had finally popped, and a full market crash was coming Monday morning.",
             "That is not what happened.", "Bitcoin bounced off the bottom instead."]
META = {"scores": {"contempt_outrage": 0, "hook_first_2s": 5, "quotable": 4, "stakes": 5, "stance": 4,
                   "stands_alone": 5, "surprising_fact": 4},
        "names_person": False, "risk": [], "topics": ["bitcoin"], "reason": "a hook"}
VID = "0shaXx_n870"


def moment(src, k0=1, k1=1):
    sp = E.Span(src, k0, k1)
    m = M.record(sp, META, CTX, M.judge(sp, CTX), {"ledger_moment_id": "1cb1675158fd53f1033a"})
    m["rank_score"] = M.rank_score(m)
    m["source_key"] = VID
    return m


def case(sentences=SENTENCES, k0=1, k1=1):
    src = source(sentences, channel="Simply Bitcoin", vid=VID)
    return src, moment(src, k0, k1), {VID: src}


class Fake:
    """The router as owner_rules.out_edge calls it: router.call(role, prompt, max_tokens=, seed=, **kw) -> .text,
    .backend. answers: dicts (replied as JSON), strings (replied as they are) or exceptions (raised), in order."""
    def __init__(self, *answers):
        self.answers, self.calls = list(answers), []

    def call(self, role, prompt, max_tokens=2000, seed=7, **kw):
        self.calls.append({"role": role, "prompt": prompt, "max_tokens": max_tokens, "seed": seed, **kw})
        a = self.answers.pop(0)
        if isinstance(a, BaseException):
            raise a
        return types.SimpleNamespace(text=a if isinstance(a, str) else json.dumps(a),
                                     backend="heimdall:qwen/qwen3.8-27b@low")


NO0 = {"complete": "no", "finishes_at": 0, "why": "'the same story' is told by the next sentence"}
YES = {"complete": "yes", "finishes_at": None, "why": "the thought is complete"}
NO_NONE = {"complete": "no", "finishes_at": None, "why": "the thought runs on past every listed sentence"}


class TestTheRulesFile(unittest.TestCase):
    def test_it_is_loaded_by_path_from_the_bytes_hashed(self):
        mod, sha = OE.rules()
        with open(OE.OWNER_RULES, "rb") as f:
            self.assertEqual(sha, hashlib.sha256(f.read()).hexdigest())
        self.assertTrue(mod.VERSION.startswith("owner_rules"))
        self.assertEqual(mod.__name__, f"owner_rules_{sha[:12]}")          # never the name of a module of this tree
        self.assertIs(OE.rules()[0], mod)                                     # loaded once per file content
        self.assertNotIn("owner_rules", sys.modules)

    def test_no_file_no_question_every_clip_unverified(self):
        src, m, sources = case()
        kept, rec = OE.pool(Fake(), [m], sources, CTX, path="/nonexistent/owner_rules.py")
        self.assertEqual(kept, [])
        self.assertIn("UNVERIFIED", rec["unverified"][m["moment_id"]])
        self.assertEqual(rec["refused"], {})                                  # never a refusal (ruling 160 (2a))


class TestTheOutEdge(unittest.TestCase):
    def test_the_afd8977d_opener_is_extended_to_the_sentence_that_finishes_it(self):
        src, m, sources = case()
        r = Fake(NO0, YES)
        kept, rec = OE.pool(r, [m], sources, CTX)
        self.assertEqual(len(kept), 1)
        x = kept[0]
        self.assertNotEqual(x["moment_id"], m["moment_id"])                    # a new span, its own id
        self.assertEqual((x["sentences"], x["start"]), ([1, 2], m["start"]))   # the IN edge unchanged
        self.assertEqual(x["text"], OPENER + " " + SENTENCES[2])
        d = x["derived_from"]
        self.assertEqual((d["ruling"], d["from"], d["was"], d["added"]), ("162 (1)", m["moment_id"], [1, 1],
                                                                          SENTENCES[2]))
        self.assertEqual((x["out_edge"]["complete"], x["out_edge"]["measured"]), (True, True))
        self.assertEqual(rec["extended"], {m["moment_id"]: x["moment_id"]})
        self.assertEqual(rec["refused"], {})
        first, second = r.calls
        self.assertEqual((first["role"], first["seed"], first["deadline_s"]), ("out_edge", 7, OE.DEADLINE_S))
        self.assertIn("everybody had the same story.", first["prompt"])     # the clip, then what follows it
        self.assertIn("[0] The AI bubble had finally popped", first["prompt"])
        self.assertIn("Everybody was scared that whole week.", first["prompt"])   # before: context only
        self.assertIn("[0] That is not what happened.", second["prompt"])    # the extension asked on its OWN edge

    def test_a_complete_clip_stays_with_its_verdict_and_is_asked_once(self):
        src, m, sources = case(k1=2)                                         # it ends where the thought ends
        cache, r = {}, Fake(YES)
        kept, rec = OE.pool(r, [m], sources, CTX)
        self.assertEqual([k["moment_id"] for k in kept], [m["moment_id"]])
        self.assertEqual(set(kept[0]["out_edge"]), {"complete", "why", "backend", "measured", "version", "sha256"})
        self.assertEqual(rec["complete"], [m["moment_id"]])
        v = OE.ask(Fake(YES), m, src, cache)
        self.assertEqual(len(cache), 1)
        again = OE.ask(Fake(), m, src, cache)                                # a recorded verdict: no call at all
        self.assertTrue(again["cached"])
        self.assertEqual(again["complete"], v["complete"])

    def test_no_answer_is_unverified_never_cached_never_a_refusal(self):
        src, m, sources = case()
        for err in (P.ProviderError("every back-end unavailable"), P.ReplayMiss("not recorded")):
            cache = {}
            v = OE.ask(Fake(err), m, src, cache)
            self.assertEqual((v["measured"], v["complete"], cache), (False, None, {}))
            kept, rec = OE.pool(Fake(err), [m], sources, CTX)
            self.assertEqual((kept, rec["refused"]), ([], {}))
            self.assertIn(m["moment_id"], rec["unverified"])
        kept, rec = OE.pool(Fake("I think it is fine"), [m], sources, CTX)   # an unreadable reply: no answer
        self.assertEqual((kept, list(rec["unverified"])), ([], [m["moment_id"]]))
        with self.assertRaises(P.SpendLimit):                                # the spend stop is never swallowed
            OE.ask(Fake(P.SpendLimit("the day's cap")), m, src, {})

    def test_runs_on_with_nothing_to_finish_it_or_an_extension_that_runs_on_is_refused(self):
        src, m, sources = case()
        kept, rec = OE.pool(Fake(NO_NONE), [m], sources, CTX)
        self.assertEqual(kept, [])
        self.assertIn("no following sentence", rec["refused"][m["moment_id"]])
        kept, rec = OE.pool(Fake(NO0, NO_NONE), [m], sources, CTX)
        self.assertEqual(kept, [])
        self.assertIn("runs on too", rec["refused"][m["moment_id"]])
        kept, rec = OE.pool(Fake(NO0, P.ProviderError("down")), [m], sources, CTX)
        self.assertEqual((kept, list(rec["unverified"])), ([], [m["moment_id"]]))   # its extension unanswered

    def test_a_clip_cut_inside_a_sentence_is_never_extended(self):
        src, m, sources = case()
        cut = dict(m, words=[m["words"][0] + 1, m["words"][1]], moment_id=m["moment_id"] + "~trim")   # a trimmed IN
        before, nxt, ks = OE.around(cut, src)
        self.assertEqual((nxt[0], ks), (SENTENCES[2], []))
        kept, rec = OE.pool(Fake(NO0), [cut], sources, CTX)
        self.assertEqual(kept, [])
        self.assertIn("cannot be extended", rec["refused"][cut["moment_id"]])
        with self.assertRaises(ValueError):
            TV.extend(cut, src, 2, CTX, "x")
        for k in (1, 0, 5, True, "2"):
            with self.assertRaises(ValueError):
                TV.extend(m, src, k, CTX, "x")

    def test_the_extension_meets_the_pool_rules_or_its_parent_is_refused(self):
        long_next = " ".join(["and the selling went on"] * 14) + " until Monday."   # ~21 s more: past the 20 s clip
        src, m, sources = case(SENTENCES[:2] + [long_next[0].upper() + long_next[1:]] + SENTENCES[3:])
        kept, rec = PK.out_edges(Fake(NO0, YES), [m], sources, CTX)
        self.assertEqual(kept, [])
        self.assertIn("breaks a pool rule", rec["refused"][m["moment_id"]])
        self.assertEqual(rec["extended"], {})


class TestTheRenderSWay(unittest.TestCase):
    """The out-edge question goes to ONE model, the render's way (owner_rules.HeimdallText): the user message only,
    temperature 0, reasoning effort low, 2,000 tokens; every other Heimdall call is as before."""

    def body(self, name):
        r = P.Router()
        sent = []
        with unittest.mock.patch.object(P, "_http_json", lambda url, body, headers, timeout: sent.append(body) or {
                "choices": [{"message": {"content": "{}"}}], "usage": {}}), \
                unittest.mock.patch.object(type(r.backends[name]), "key", lambda self, n: "k"):
            r.backends[name].complete("Q", 2000, 7)
        return sent[0]

    def test_the_role_and_its_back_end(self):
        r = P.Router()
        self.assertEqual(r.chain("out_edge"), ["heimdall:qwen/qwen3.8-27b@low"])
        b = self.body("heimdall:qwen/qwen3.8-27b@low")
        self.assertEqual((b["messages"], b["reasoning"], b["max_tokens"], b["temperature"], b["model"]),
                         ([{"role": "user", "content": "Q"}], {"effort": "low"}, 2000, 0, "qwen/qwen3.8-27b"))
        old = self.body("heimdall:qwen/qwen3.8-27b")
        self.assertEqual((old["messages"][0]["role"], "reasoning" in old), ("system", False))


class TestTheBuild(unittest.TestCase):
    def rig(self, **kw):
        import test_medley as TM
        from test_moments import pm
        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]
        r = TM.Rig(ms, ["h", "x", "y"], [(True, [], None, TM.Rig.LINE)] * 2, [None] * 2)
        for k, v in kw.items():
            setattr(r, k, v)
        return r

    def test_every_clip_of_a_package_ends_a_thought_on_its_sealed_row(self):
        out = self.rig().run()
        pk = out["package"]
        self.assertIsNotNone(pk, out.get("why_none"))
        row = pk["gates"]["out_edge"]
        self.assertEqual((row["status"], row["n"], sorted(row["verdicts"])), ("PASS", 3, ["clip_01", "clip_02", "hook"]))
        self.assertEqual(row["version"], ["owner_rules 1 (ruling 162, 2026-11-24)"])
        self.assertEqual(out["out_edge"]["asked"], 3)

    def test_a_clip_that_runs_on_or_got_no_answer_never_plays(self):
        for kw in ({"out_edge_refused": {"x"}}, {"out_edge_unverified": {"x"}}):
            out = self.rig(**kw).run()
            self.assertIsNone(out["package"], kw)                         # x was the third channel

    def test_a_package_without_the_verdicts_never_seals(self):
        r = self.rig()
        r.out_edges = lambda router, ms, *a, **k: (list(ms), {"asked": 0, "complete": [], "extended": {},
                                                              "refused": {}, "unverified": {}})
        self.assertIsNone(r.run()["package"])                             # the row NOT RUN: package_pin.REQUIRED_GATES refuses it

    def test_the_row(self):
        ok = dict(__import__("test_medley").Rig.OUT_EDGE_OK)
        base = __import__("test_ruling_137").TestTheStepARow().base()
        self.assertEqual(PK.inventory(**base, out_edge=[ok, ok])["out_edge"]["status"], "PASS")
        self.assertEqual(PK.inventory(**base, out_edge=[ok, dict(ok, complete=False)])["out_edge"]["status"], "FAIL")
        self.assertEqual(PK.inventory(**base, out_edge=[ok, None])["out_edge"]["status"], "NOT RUN")
        self.assertNotIn("out_edge", PK.inventory(**base))                 # the row only where the build asked


class TestTheSpotlight(unittest.TestCase):
    """RULING 162 (1) holds for a spotlight too: its pool passes out_edges (seg_max 35 s), and a spotlight whose clip
    carries no complete verdict is refused at its gates (package_pin.SPOTLIGHT_GATES)."""

    def test_no_verdict_no_spotlight(self):
        import test_spotlight as TS
        pk, why, *_ = TS.package(m=TS.moment())
        self.assertIsNotNone(pk, why)
        self.assertEqual(pk["gates"]["out_edge"]["status"], "PASS")
        for v in (None, dict(TS.OUT_EDGE_OK, complete=False), dict(TS.OUT_EDGE_OK, measured=False)):
            pk, why, *_ = TS.package(m=TS.moment(out_edge=v))
            self.assertIsNone(pk, v)
            self.assertIn("out_edge", why)



class TestTheClosingLine(unittest.TestCase):
    """RULING 162 (2) (orchestrator 07:45 ET Nov 24, from PBX's review of afd8977d: "my VO ... is literally just me
    saying all the clips that were featured ... Let's never do that again"): OUR CLOSING VO LINE MUST ADD VALUE, never a
    list of the channels. The paid model writes it first, then the Heimdall families, up to 4 writes, each told why; a
    Heimdall family judges fidelity and value when the paid model wrote, and the reverse; no line passing both means NO
    closing line, one flag. Any spoken line of ours (intro, bridge, closing) never names a channel or lists."""
    GROK = "xai:grok-4.20-0309-reasoning"
    HEIM = ["heimdall:qwen/qwen3.8-27b", "heimdall:deepseek/deepseek-v4.1-flash", "heimdall:openai/gpt-oss-20b",
            "heimdall:google/gemma-4-31b-it", "heimdall:minimax/minimax-m3.1-flash"]

    def test_the_paid_model_writes_it_first_and_each_rewrite_goes_down_the_chain(self):
        import proof_ly as PL
        import test_medley as TM
        ch = PL.chains("heimdall_first")
        self.assertEqual(ch["angle_write:closing"], PL.WRITERS[-1:] + PL.WRITERS[:-1])
        self.assertEqual(ch["angle_write:closing"][0], self.GROK)
        self.assertEqual(ch["angle_write"], PL.WRITERS)                      # the angle itself: Heimdall first
        seen = []

        class R:
            def call(self, role, prompt, max_tokens=2000, seed=7, **k):
                seen.append((role, k.get("kind"), k.get("avoid_model")))
                raise P.ProviderError("stop")
        segs, ctx = TM.TestWriteTakeaway.SEGS, E.Context(NOW, REG)
        fields = {"takeaway": {"text": "x", "cites": []}, "title": {"text": "t", "cites": []},
                  "caption": {"text": "c", "cites": []}}
        for f in (lambda: PK.write_takeaway(R(), TM.angle(["h", "x", "y"], "h"), segs, ctx, {},
                                            avoid_model={self.GROK}),
                  lambda: PK.write_line(R(), TM.angle(["h", "x", "y"], "h"), segs, ctx, {}, "takeaway", fields, [],
                                        avoid_model={self.GROK, "heimdall:qwen/qwen3.8-27b"}, limit="12-16 words"),
                  lambda: PK.write_line(R(), TM.angle(["h", "x", "y"], "h"), segs, ctx, {}, "title", fields, [])):
            with self.assertRaises(P.ProviderError):
                f()
        self.assertEqual(seen, [("angle_write", "closing", {self.GROK}),
                                ("angle_write", "closing", {self.GROK, "heimdall:qwen/qwen3.8-27b"}),
                                ("angle_write", None, None)])                # the title: the writer chain as before

    def test_a_heimdall_family_judges_when_the_paid_model_wrote_and_the_reverse(self):
        import proof_ly as PL
        ch = PL.chains("heimdall_first")
        for role in ("fidelity_verdict", "coherence_verdict"):              # fidelity, and the value grade's role
            self.assertEqual(ch[role][0], self.GROK, role)
            self.assertEqual(set(ch[role][1:]), set(self.HEIM), role)
        r = P.Router(chains=ch, routing="heimdall_first")              # each family its own maker
        for role in ("fidelity_verdict", "coherence_verdict"):
            names = r.chain(role)
            off = lambda av, af: [n for n in names if r.backends[n].vendor not in av and r.backends[n].family not in af]
            self.assertEqual(r.backends[off({"xai"}, set())[0]].vendor.split("/")[0], "heimdall")   # paid wrote
            self.assertEqual(off({"heimdall/deepseek"}, {"deepseek"})[0], self.GROK)               # the reverse

    def test_the_prompts_ask_for_one_sentence_that_names_no_one(self):
        for t in (PK.WRITE_LY, PK.TAKEAWAY_LIMIT):
            self.assertIn("ONE sentence", t)
            self.assertIn("the pattern across the clips", t)
            self.assertIn("what to watch", t)
        self.assertIn("NEVER names a\n  channel, a show or a speaker", PK.WRITE_LY)
        self.assertIn("never names a channel, a show or a speaker", PK.TAKEAWAY_LIMIT)

    def test_our_spoken_lines_never_name_a_channel_or_list(self):
        segs = [{"channel": "Simply Bitcoin"}, {"channel": "Natalie Brunell"}, {"channel": "Yahoo Finance"}]
        ok = "The floor held because sellers ran out of reasons to sell."
        rules = lambda slot, text: [v["rule"] for v in PK.owner_line_faults({"segments": segs, "lines": [
            {"slot": slot, "text": text}]})]
        self.assertEqual(rules("takeaway", ok), [])
        for text in ("Simply Bitcoin saw the floor hold.", "Bitcoin, in their own words.",
                     "Natalie Brunell's warning is the one to watch.", "Three takes on the same bottom.",
                     "As these clips show, the floor held."):
            self.assertEqual(rules("takeaway", text), ["LISTING"], text)
        self.assertEqual(rules("takeaway", "The floor held. Watch Monday."), ["ONE_SENTENCE"])
        self.assertEqual(rules("bridge", "Next, Yahoo Finance."), ["LISTING"])          # the old plain bridge
        self.assertEqual(rules("intro", "In the words of Simply Bitcoin."), ["LISTING"])
        self.assertEqual(rules("title", "Simply Bitcoin on the bottom"), [])            # never spoken: not checked
        with unittest.mock.patch.object(OE, "OWNER_RULES", "/nonexistent/owner_rules.py"):
            self.assertEqual(rules("takeaway", ok), ["LISTING"])                         # no rules file: fails closed

    def test_no_line_passing_means_no_closing_line_and_one_flag(self):
        import test_medley as TM
        T = TM.TestRuling91MedleyHalf
        rig = TM.Rig(T.FITS, ["h", "x", "y"], T.MED, [None], values=T.LOST4, lines=T.ALONE)
        out = rig.run()
        pk = out["package"]
        self.assertIsNotNone(pk, out.get("why_none"))
        self.assertEqual([x["slot"] for x in pk["lines"]], ["title", "caption"])          # no closing line at all
        self.assertTrue(TM.NV_FLAG_OK(pk["gates"]), pk["gates"])
        self.assertEqual(len(rig.value_calls), 4)                                         # the write and 3 alone
        self.assertFalse([x for x in pk["lines"] if "in the words of" in x["text"].lower()])   # no plain line, ever
        import package_pin
        mp = package_pin.to_pin(TM.spk(pk), "test")["moments_package"]
        self.assertEqual(mp["review_flags"], [PK.NO_LINE_FLAG])
        self.assertEqual(mp["edl_vo"], {"intro": None, "bridges": []})

    def test_a_closing_line_that_lists_is_written_again_told_why(self):
        import test_medley as TM
        listing = "Bitcoin at the bottom, in the words of A, B and C, in their own clips here."
        rig = TM.Rig(TM.TestRuling91MedleyHalf.SHORT, ["h", "x", "y"], TM.TestRuling91MedleyHalf.MED, [None, None],
                     takeaways=[listing])
        out = rig.run()
        pk = out["package"]
        self.assertIsNotNone(pk, out.get("why_none"))
        self.assertEqual(next(x["text"] for x in pk["lines"] if x["slot"] == "takeaway"), TM.Rig.LINE)
        first = out["tried"][0]["attempts"][0]
        self.assertTrue([v for v in first.get("violations") or [] if v["rule"] == "LISTING"], first)
        self.assertNotIn("no_closing_line", pk["gates"])
        self.assertEqual(pk["gates"]["takeaway_value"]["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
