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
        r, seen = Fake(NO0, YES), []
        kept, rec = OE.pool(r, [m], sources, CTX,
                            admit=lambda v: seen.append((v["moment_id"], len(r.calls))) or (True, None))
        self.assertEqual(len(kept), 1)
        x = kept[0]
        self.assertEqual(seen, [(x["moment_id"], 1)])          # ITEM 3: admitted after its parent's question and
        #   BEFORE its own (the pool's rules, step A and the deterministic edge check, in the build)
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

    def test_a_changed_cut_or_transcript_voids_the_answer(self):
        """ITEM 3 (09:45 ET Nov 24): the answer is cached against the exact transcript, cut coordinates and prompt
        version (the rules file's sha: its prompt); a changed cut or transcript is asked again."""
        src, m, sources = case(k1=2)
        cache = {}
        OE.ask(Fake(YES), m, src, cache)
        for changed in (dict(m, end=m["end"] + 0.25), dict(m, start=m["start"] - 0.25), dict(m, text=m["text"] + " x")):
            r = Fake(YES)
            self.assertFalse(OE.ask(r, changed, src, cache)["cached"])
            self.assertEqual(len(r.calls), 1)
        r = Fake(YES)
        self.assertTrue(OE.ask(r, m, src, cache)["cached"])                  # the very same: no call
        self.assertEqual(r.calls, [])

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
        ok = lambda v: (True, None)
        kept, rec = OE.pool(Fake(NO0, NO_NONE), [m], sources, CTX, admit=ok)
        self.assertEqual(kept, [])
        self.assertIn("runs on too", rec["refused"][m["moment_id"]])
        kept, rec = OE.pool(Fake(NO0, P.ProviderError("down")), [m], sources, CTX, admit=ok)
        self.assertEqual((kept, list(rec["unverified"])), ([], [m["moment_id"]]))   # its extension unanswered
        for admit in (None, lambda v: (False, "the second recogniser: the OUT edge")):   # ITEM 3: no extension is
            r = Fake(NO0, YES)                                                    # asked without its own checks
            kept, rec = OE.pool(r, [m], sources, CTX, admit=admit)
            self.assertEqual((kept, len(r.calls)), ([], 1))                       # its question never asked
            self.assertIn("fails before its question", rec["refused"][m["moment_id"]])

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
        kept, rec = PK.out_edges(Fake(NO0, YES), [m], sources, CTX, admit=lambda v: (True, None))
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


class TestItem3MustFailFixtures(unittest.TestCase):
    """ITEM 3 (orchestrator 09:45 ET Nov 24, final): the three must-fail OUT edges, each DROPPED and by which check.
    'we hit a new' (Digital Asset News, cut at 578.95 s) and '...and everybody had the same story.' (Simply Bitcoin
    1cb16751: the second recogniser wrote 'story:') are DROPPED by EDGE_OUT, the deterministic check that runs first
    (docs/audits/parallel/item3_edge_out_fixtures: the real audio, recorded second-ear replies, replayed).
    'Let me read that again.' (ad47eab4) has a real full stop then 'Bitcoin', so EDGE_OUT passes it; the QUESTION,
    asked the build's way on its own window record and FROZEN here (the reply recorded at 09:55 ET Nov 24 from qwen@low,
    replayed: nothing is asked), answers that it runs on ("a setup that explicitly promises the re-reading delivered
    in sentence [0]"); a window record cannot be extended: REFUSED. A changed prompt (owner_rules) misses the frozen
    reply: no answer, UNVERIFIED, never a pass."""
    D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "item3_question")

    def test_let_me_read_that_again_is_refused_by_the_question_on_its_frozen_answer(self):
        import ledger_build as LB
        import proof_ly as PL
        fx = json.load(open(os.path.join(self.D, "moment.json")))
        m, wp = fx["moment"], fx["word_pass"]
        src, _, why = LB.window_source(m, wp, CTX, store=os.path.join(self.D, "store"))
        self.assertIsNotNone(src, why)
        self.assertTrue(m["text"].endswith("Let me read that again."))
        r = P.Router(chains=PL.chains("heimdall_first"), routing="heimdall_first",
                     record_dir=os.path.join(self.D, "replies"), replay=True)
        v = OE.ask(r, m, src, {})
        self.assertEqual((v["measured"], v["complete"], v["finishes_at"], v["backend"]),
                         (True, False, 0, "heimdall:qwen/qwen3.8-27b@low"), v)
        self.assertEqual(v["ks"], [])                                     # a window record: no extension
        kept, rec = OE.pool(r, [m], {m["source_key"]: src, m["video_id"]: src}, CTX, admit=lambda x: (True, None))
        self.assertEqual(kept, [])
        self.assertIn("cannot be extended", rec["refused"][m["moment_id"]])
        self.assertEqual(rec["unverified"], {})

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

    def test_the_question_comes_after_the_deterministic_edge_check(self):
        """ITEM 3 (09:45 ET Nov 24): "the deterministic edge check runs first": a clip the second recogniser's OUT edge
        refuses (CUTTABLE) is never asked the question."""
        import test_medley as TM
        from test_moments import pm
        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 13.0)]
        r = TM.Rig(ms, ["h", "x", "y"], [(True, [], None, TM.Rig.LINE)] * 2, [None] * 2, uncuttable={"z"})
        out = r.run()
        self.assertIsNotNone(out["package"], out.get("why_none"))
        self.assertTrue(r.out_edge_asked)
        self.assertNotIn("z", [mid for asked in r.out_edge_asked for mid in asked])

    def ext_rig(self, **kw):
        import test_medley as TM
        from test_moments import pm
        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]
        r = TM.Rig(ms, ["h", "x~ext", "y"], [(True, [], None, TM.Rig.LINE)] * 2, [None] * 2, **kw)
        r.out_edge_extend = {"x": "x~ext"}
        return r

    def test_an_extension_passes_step_a_and_the_edge_check_before_its_question(self):
        r = self.ext_rig()
        out = r.run()
        pk = out["package"]
        self.assertIsNotNone(pk, out.get("why_none"))
        self.assertEqual(r.admitted, [("x~ext", True, None)])
        self.assertIn("x~ext", [sg["moment_id"] for sg in pk["segments"]])
        self.assertNotIn("x", [sg["moment_id"] for sg in pk["segments"]])
        self.assertIn(["x~ext"], [ids for _, ids in r.screens])                 # step A asked of the extension
        r = self.ext_rig(uncuttable={"x~ext"})
        out = r.run()
        self.assertIsNone(out["package"])                                       # x was the third channel
        self.assertEqual(r.admitted[0][:2], ("x~ext", False))
        self.assertTrue(r.admitted[0][2].startswith("the second recogniser"), r.admitted[0][2])
        self.assertIn("fails before its question", out["out_edge"]["refused"]["x"])

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
    list of the channels; any spoken line of ours (intro, bridge, closing) never names a channel or lists. As amended by
    ITEM 2 (amendment B, orchestrator 09:35 ET Nov 24): "An in-house model writes, a different family judges, no paid
    rescue, no retry loop. No judge from another family awake means no line." The lexical checks (LISTING, ONE
    sentence, no digit the clips do not say) run in code before any model; no line is a valid close (one flag)."""
    GROK = "xai:grok-4.20-0309-reasoning"
    QWEN, DS = "heimdall:qwen/qwen3.8-27b", "heimdall:deepseek/deepseek-v4.1-flash"
    LAST_NIGHT = "Bitcoin, in the words of Simply Bitcoin, Digital Asset News and Yahoo Finance, in their own clips."
    CHANNELS = ("Simply Bitcoin", "Digital Asset News", "Yahoo Finance")

    @staticmethod
    def providers_tests():
        """tests/providers/test_providers.py, loaded by path: its Fake back-end, router() and stand-in rig."""
        import importlib.util
        spec = importlib.util.spec_from_file_location("providers_tests_162",
                                                      os.path.join(REPO, "tests", "providers", "test_providers.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def judges(self, d, down=()):
        """A router on the REAL chains (proof_ly.chains("heimdall_first")) for the closing line's judges, each back-end
        a fake with the real back-end's vendor, family and gateway; the families in `down` do not answer."""
        import proof_ly as PL
        tp = self.providers_tests()
        ch = PL.chains("heimdall_first")
        real = P.Router(chains=ch, routing="heimdall_first")
        roles = {k: ch[k] for k in ("fidelity_verdict", "coherence_verdict", "angle_write", "angle_write:closing")}
        fakes = []
        for n in dict.fromkeys(x for v in roles.values() for x in v):
            rb = real.backends[n]
            fb = tp.Fake(n, rb.vendor, answer='{"ok": 1}', family=rb.family,
                         fail="down (the test)" if rb.family in down else None)
            fb.gateway = P.gateway(rb)
            fakes.append(fb)
        r = tp.router(d, fakes, roles)
        r.chains.update(roles)
        return r

    def test_an_in_house_model_writes_it_and_no_paid_model_ever_does(self):
        """REPLACES 'the paid model writes it first and each rewrite goes down the chain' (ITEM 2: "An in-house model
        writes ... no paid rescue"): our closing line's writer list is the Heimdall writers alone; write_takeaway and the
        takeaway written by write_line ask for it as kind "closing"; a title keeps the writer chain."""
        import proof_ly as PL
        import test_medley as TM
        ch = PL.chains("heimdall_first")
        self.assertEqual(ch["angle_write:closing"], [w for w in PL.WRITERS if w.startswith("heimdall:")])
        self.assertEqual(ch["angle_write"], PL.WRITERS)                      # the angle itself: unchanged
        r = P.Router(chains=ch, routing="heimdall_first")
        self.assertEqual([n for n in r.chain("angle_write", "closing") if P.gateway(r.backends[n]) != "heimdall"], [])
        seen = []

        class R:
            def call(self, role, prompt, max_tokens=2000, seed=7, **k):
                seen.append((role, k.get("kind")))
                raise P.ProviderError("stop")
        segs, ctx = TM.TestWriteTakeaway.SEGS, E.Context(NOW, REG)
        fields = {"takeaway": {"text": "x", "cites": []}, "title": {"text": "t", "cites": []},
                  "caption": {"text": "c", "cites": []}}
        for f in (lambda: PK.write_takeaway(R(), TM.angle(["h", "x", "y"], "h"), segs, ctx, {}),
                  lambda: PK.write_line(R(), TM.angle(["h", "x", "y"], "h"), segs, ctx, {}, "takeaway", fields, [],
                                        limit="12-16 words"),
                  lambda: PK.write_line(R(), TM.angle(["h", "x", "y"], "h"), segs, ctx, {}, "title", fields, [])):
            with self.assertRaises(P.ProviderError):
                f()
        self.assertEqual(seen, [("angle_write", "closing"), ("angle_write", "closing"), ("angle_write", None)])

    def test_a_family_that_did_not_write_judges_it_on_ruling_96s_lists(self):
        """REPLACES 'a Heimdall family judges when the paid model wrote, and the reverse' (162 (2)'s chain extension is
        reverted with ITEM 2: no paid model writes the closing line). On the real chains (ruling 96's lists): fidelity
        and the value grade go to a family that did not write; with Grok down, the value grade's other family answers,
        and fidelity (qwen -> Grok) has none awake when qwen wrote: no judge, no line (never the writer's family)."""
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            r = self.judges(d)
            for wrote, fid, val in (("qwen", self.GROK, self.GROK), ("deepseek", self.QWEN, self.GROK)):
                w = {"avoid_vendor": {f"heimdall/{wrote}"}, "avoid_family": {wrote}}
                self.assertEqual(r.call("fidelity_verdict", "p", kind="closing", **w).backend, fid, wrote)
                self.assertEqual(r.call("coherence_verdict", "p", kind="value", **w).backend, val, wrote)
        with tempfile.TemporaryDirectory() as d:
            r = self.judges(d, down=("grok",))
            r.lx_soft = True                                                 # the never-empty pass
            w = {"avoid_vendor": {"heimdall/qwen"}, "avoid_family": {"qwen"}}
            self.assertEqual(r.call("coherence_verdict", "p", kind="value", **w).backend, self.DS)
            with self.assertRaises(P.ProviderError):
                r.call("fidelity_verdict", "p", kind="closing", **w)

    def test_no_judge_from_another_family_awake_means_no_line_never_a_stand_in(self):
        """ITEM 2: "No judge from another family awake means no line." In the never-empty pass (lx_soft) the stand-in
        judges of ruling 154 (1) never judge our closing line: with only the writer's own family left, the value grade
        (coherence_verdict, kind "value") and fidelity over a package carrying it (kind "closing") raise; the same call
        with no kind still takes the stand-in. package.takeaway_value and paid_gates ask with those kinds."""
        import tempfile
        tp = self.providers_tests()
        with tempfile.TemporaryDirectory() as d:
            r = tp.TestRuling154StandInJudge().rig(d, down=("grok", "deepseek", "gpt-oss"))   # qwen wrote; glm never
            r.chains["fidelity_verdict"] = ["xai:grok"]                                       # judges (ruling 119)
            r.lx_soft = True
            w = {"avoid_vendor": {"heimdall/qwen"}, "avoid_family": {"qwen"}}
            for role, kind in (("coherence_verdict", "value"), ("fidelity_verdict", "closing")):
                with self.assertRaises(P.ProviderError, msg=role):
                    r.call(role, "p", kind=kind, **w)
                a = r.call(role, "p", **w)                                    # no kind: the stand-in, as ruled
                self.assertEqual((a.backend, a.lx_soft["step"]), ("heimdall:qwen", 2), role)
        import test_medley as TM
        seen = []

        class R:
            def call(self, role, prompt, max_tokens=2000, seed=7, **k):
                seen.append((role, k.get("kind")))
                raise P.ProviderError("down")
        v = PK.takeaway_value(R(), TM.TestTakeawayValueVerdict.SEGS, E.Context(NOW, REG), "The floor held.",
                              {"heimdall/qwen"}, {"qwen"})
        self.assertEqual((seen, v["measured"], v["ok"]), ([("coherence_verdict", "value")], False, False))
        import concurrent.futures
        import context_integrity as CI
        import vo_fidelity as VF
        kinds = []
        segs = [{"moment_id": m, "label": m, "channel": c, "video_id": f"v{m}", "text": f"Bitcoin {m}."}
                for m, c in (("h", "A"), ("x", "B"), ("y", "C"))]
        with unittest.mock.patch.object(VF, "check", lambda *a, **k: kinds.append(k.get("kind")) or {"ok": True}), \
                unittest.mock.patch.object(CI, "check_contexts", lambda *a, **k: {"ok": True}), \
                unittest.mock.patch.object(CI, "contexts_from_sources", lambda *a, **k: {}), \
                concurrent.futures.ThreadPoolExecutor(2) as pool:
            for lines in ([{"slot": "title", "text": "t", "cites": []}, {"slot": "takeaway", "text": "x", "cites": []}],
                          [{"slot": "title", "text": "t", "cites": []}, {"slot": "caption", "text": "c", "cites": []}]):
                PK.paid_gates(None, {"segments": segs, "lines": lines}, {}, {m: {} for m in "hxy"}, [], NOW,
                              {"heimdall/qwen"}, {"qwen"}, pool)
        self.assertEqual(kinds, ["closing", None])                            # with our closing line: never a stand-in

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

    def test_last_nights_close_is_refused_by_the_lexical_check_with_zero_model_calls(self):
        """ITEM 2's test: last night's spoken close is rejected by the lexical check in code, before any model: with
        every model path recording and raising, owner_line_faults refuses it (LISTING: the three credited channels
        and the listing phrases) and no call is made; in a build its one write is refused before the value grade or
        any paid verdict, never written again, and the no-voice shape (no line) is the close."""
        calls = []

        def record_and_raise(*a, **k):
            calls.append(a[:2])
            raise P.ProviderError("a model was asked: the lexical check must ask none")
        pk = {"segments": [{"channel": c, "text": f"Bitcoin held, says {c}."} for c in self.CHANNELS],
              "lines": [{"slot": "title", "text": "Bitcoin at the bottom", "cites": []},
                        {"slot": "takeaway", "text": self.LAST_NIGHT, "cites": []}]}
        with unittest.mock.patch.object(P.Router, "call", record_and_raise), \
                unittest.mock.patch.object(P.Router, "_call", record_and_raise), \
                unittest.mock.patch.object(P, "call_parsed", record_and_raise):
            v = PK.owner_line_faults(pk)
        self.assertEqual(([x["rule"] for x in v], [x["slot"] for x in v]), (["LISTING"], ["takeaway"]))
        for said in [f"names '{c}'" for c in self.CHANNELS] + ["says 'in the words of'"]:
            self.assertIn(said, v[0]["detail"])
        self.assertEqual(calls, [])                                           # zero model calls
        import test_medley as TM
        from test_moments import pm
        ms = [pm("h", self.CHANNELS[0], 16.0), pm("x", self.CHANNELS[1], 16.0), pm("y", self.CHANNELS[2], 16.0)]
        rig = TM.Rig(ms, ["h", "x", "y"], TM.TestRuling91MedleyHalf.MED, [None, None],
                     takeaways=[self.LAST_NIGHT, TM.Rig.LINE])
        out = rig.run()
        first = out["tried"][0]["attempts"][0]
        self.assertIn("LISTING", [x["rule"] for x in first["violations"]])
        self.assertNotIn("verdict_classes", first)                           # no paid verdict judged it
        self.assertEqual((rig.value_calls, len(rig.write_calls), rig.takeaways), ([], 1, [TM.Rig.LINE]))
        pk = out["package"]
        self.assertIsNotNone(pk, out.get("why_none"))
        self.assertEqual([x["slot"] for x in pk["lines"]], ["title", "caption"])    # no line: a valid close
        self.assertTrue(TM.NV_FLAG_OK(pk["gates"]), pk["gates"])

    def test_a_digit_no_clip_says_is_refused(self):
        """ITEM 2's lexical rule: "no digit not in the clips". A number the closing line says must be one a clip says
        (its commas aside: '1000' is the clips' '1,000'); any other refuses (DIGIT), before any model."""
        segs = [{"channel": "Simply Bitcoin", "text": "Bitcoin fell 1,000 dollars below its high."},
                {"channel": "Yahoo Finance", "text": "Outflows hit 3.5 billion in 2 days."},
                {"channel": "Natalie Brunell", "text": "The floor held."}]
        faults = lambda text: PK.owner_line_faults({"segments": segs, "lines": [{"slot": "takeaway", "text": text}]})
        rules = lambda text: [v["rule"] for v in faults(text)]
        self.assertEqual(rules("The floor held, and a 1000 dollar drop did not break it."), [])
        self.assertEqual(rules("The floor held after 3.5 billion left in 2 days."), [])
        for text, new in (("The floor held at 55 thousand.", "55"), ("Watch 1,001 next.", "1,001"),
                          ("The floor held for 7 days.", "7"), ("Outflows of 3.6 billion did not break it.", "3.6")):
            self.assertEqual(rules(text), ["DIGIT"], text)
            self.assertIn(f"'{new}'", faults(text)[0]["detail"], text)
        self.assertEqual([v["rule"] for v in PK.owner_line_faults({"segments": segs, "lines": [
            {"slot": "title", "text": "Bitcoin at 55K"}]})], [])                 # a title is never spoken

    def test_no_line_passing_means_no_closing_line_and_one_flag(self):
        import test_medley as TM
        T = TM.TestRuling91MedleyHalf
        rig = TM.Rig(T.FITS, ["h", "x", "y"], T.MED, [None], values=T.LOST4, lines=T.ALONE)
        out = rig.run()
        pk = out["package"]
        self.assertIsNotNone(pk, out.get("why_none"))
        self.assertEqual([x["slot"] for x in pk["lines"]], ["title", "caption"])          # no closing line at all
        self.assertTrue(TM.NV_FLAG_OK(pk["gates"]), pk["gates"])
        self.assertEqual((len(rig.write_calls), len(rig.value_calls)), (1, 1))            # ITEM 2: one write, one judge
        self.assertEqual(len(rig.router.answers["angle_write"]), 3)                       # no write of it alone
        self.assertFalse([x for x in pk["lines"] if "in the words of" in x["text"].lower()])   # no plain line, ever
        import package_pin
        mp = package_pin.to_pin(TM.spk(pk), "test")["moments_package"]
        self.assertEqual(mp["review_flags"], [PK.NO_LINE_FLAG])
        self.assertEqual(mp["edl_vo"], {"intro": None, "bridges": []})

    def test_a_closing_line_that_lists_is_refused_unjudged_and_never_written_again(self):
        """REPLACES 'a closing line that lists is written again, told why' (ITEM 2: no retry loop): the listing line
        is refused by the lexical check, never judged by a model, never written again: no line (the no-voice shape,
        its one flag)."""
        import test_medley as TM
        T = TM.TestRuling91MedleyHalf
        listing = "Bitcoin at the bottom, in the words of A, B and C, in their own clips here."
        rig = TM.Rig(T.FITS, ["h", "x", "y"], T.MED, [None, None], takeaways=[listing, TM.Rig.LINE])
        out = rig.run()
        first = out["tried"][0]["attempts"][0]
        self.assertTrue([v for v in first.get("violations") or [] if v["rule"] == "LISTING"], first)
        self.assertNotIn("verdict_classes", first)                                  # no paid verdict judged it
        self.assertEqual((len(rig.write_calls), rig.value_calls, rig.takeaways), (1, [], [TM.Rig.LINE]))
        self.assertFalse([p for r, p in rig.prompts if r == "angle_write" and "was refused" in p])
        pk = out["package"]
        self.assertIsNotNone(pk, out.get("why_none"))
        self.assertEqual([x["slot"] for x in pk["lines"]], ["title", "caption"])
        self.assertTrue(TM.NV_FLAG_OK(pk["gates"]), pk["gates"])

if __name__ == "__main__":
    unittest.main()
