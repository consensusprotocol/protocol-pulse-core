#!/usr/bin/env python3
"""LEAN (2) (the owner's assignment, 13:37 ET Nov 24, issue 2: "pipeline/out_edge.py:161-172,270-271: certain transcript
representations prohibit extension despite available following context"; the orchestrator: "where following context
exists, a window-record clip may be extended to the sentence that finishes the thought, as a NEW span that faces every
gate and the lock again; bounded; otherwise shortened to the previous complete thought if it still passes the floor;
otherwise dropped. Re-anchoring likewise bounded, every modified span re-gated").

out_edge.pool(recover=True) (package._build lean=True):
  (a) EXTENDED / RE-ANCHORED to the end of the listed sentence the checker says finishes the thought: on a window record
      too, its cut sentence's own end too; never the window record's LAST sentence; only the AFTER_N sentences the
      checker read; the new span through admit() (the pool's rules and 20 s clip, step A, the second recogniser; lean:
      the exclusion screen's free part) and the question again on its own edge;
  (b) else SHORTENED once, to the end of its previous sentence, kept only at SHORT_CLIP_S or more, through admit() and
      the question again;
  (c) else REFUSED. No answer anywhere: UNVERIFIED (never a pass).
The cases are real: build 171's CoinTelegraph 16473cca and item 3's Digital Asset News ad47eab4, each on its window
record (frozen read-only from the store) and its recorded answer (no model is asked); the rest on word-timed test
sources (0.3 s a word). The rules file is the release revision build 171 ran (f9992cfc4, sha d509ad194f42)."""
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
for _p in ("pipeline", "tests/package", "tests/eligibility", "tests/moments"):
    sys.path.insert(0, os.path.join(REPO, _p))
import eligibility as E  # noqa: E402
import ledger_build as LB  # noqa: E402
import out_edge as OE  # noqa: E402
import package as PK  # noqa: E402
import providers as P  # noqa: E402
import proof_ly as PL  # noqa: E402
import tail_variant as TV  # noqa: E402
import test_ruling_162 as T162  # noqa: E402

D = os.path.join(HERE, "fixtures", "lean_out_edge")
ITEM3 = os.path.join(HERE, "fixtures", "item3_question")
RULES = os.path.join(D, "owner_rules_f9992cfc4.py")              # build 171's release revision's file (sha d509ad19)
CTX = T162.CTX


def window(sentences, k0=1, k1=1):
    """A test source marked as a window record (around() reads only that it is one)."""
    src, m, sources = T162.case(sentences, k0, k1)
    src.window = {"start_s": 0.0, "end_s": 999.0, "record": "w", "words_sha256": "w", "record_sha256": "w"}
    return src, m, sources


class Admit:
    """admit() as the build's: records every new span it is given; ok unless `no` names a reason."""
    def __init__(self, no=None):
        self.seen, self.no = [], no

    def __call__(self, v):
        self.seen.append(v)
        return (False, self.no) if self.no else (True, None)


class Cached(unittest.TestCase):
    def cache_file(self, entries):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        p = os.path.join(d, "OUT_EDGE_CACHE.json")
        with open(p, "w") as f:
            json.dump(entries, f)
        return p


class TestBuild171sWindowClip(Cached):
    def setUp(self):
        fx = json.load(open(os.path.join(D, "moment_171.json")))
        self.m, wp, self.cache = fx["moment"], fx["word_pass"], fx["out_edge_cache"]
        self.src, _, why = LB.window_source(self.m, wp, CTX, store=os.path.join(D, "store"))
        self.assertIsNotNone(self.src, why)
        self.sources = {self.m["source_key"]: self.src, self.m["video_id"]: self.src}

    def test_the_old_path_refused_it_on_its_own_answer(self):
        """As build 171 recorded: 'the clip cannot be extended (cut inside a sentence, or a window record)'; the answer
        is build 171's own (cached): nothing is asked."""
        r = T162.Fake()
        kept, rec = OE.pool(r, [self.m], self.sources, CTX, cache_path=self.cache_file(self.cache),
                            admit=Admit(), path=RULES)
        self.assertEqual((kept, r.calls), ([], []))
        self.assertIn("cannot be extended (cut inside a sentence, or a window record)", rec["refused"][self.m["moment_id"]])

    def test_lean_extends_it_to_the_sentence_that_finishes_its_thought(self):
        """MUST-PASS: the same cached answer (finishes_at 0: "It's not boring then.") now extends it, inside the window
        (sentence 15 of 29); the new span is admitted (its own gates) and asked the question on its own edge."""
        r, adm = T162.Fake(T162.YES), Admit()
        kept, rec = OE.pool(r, [self.m], self.sources, CTX, cache_path=self.cache_file(self.cache), admit=adm,
                            path=RULES, recover=True)
        self.assertEqual(len(kept), 1, rec)
        x = kept[0]
        self.assertEqual(rec["extended"], {self.m["moment_id"]: x["moment_id"]})
        self.assertNotEqual(x["moment_id"], self.m["moment_id"])          # a NEW span
        self.assertTrue(x["text"].endswith("It's not boring then."), x["text"][-80:])
        self.assertTrue(x["text"].startswith(self.m["text"][:40]))         # its IN edge kept
        self.assertEqual(x["derived_from"]["added"], "It's not boring then.")
        self.assertEqual([v["moment_id"] for v in adm.seen], [x["moment_id"]])   # every gate again, before its
        self.assertEqual(len(r.calls), 1)                                  # question; the parent's answer was reused
        self.assertIn("It's not boring then.", r.calls[0]["prompt"])

    def test_unanswered_offline_its_new_edge_is_open_work_never_a_pass(self):
        """Offline, the extension's own question has no recorded answer: UNVERIFIED (out of this build, asked again
        next build), never kept, never refused. Its answer needs a live model (listed as not verifiable offline)."""
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        r = P.Router(chains=PL.chains("heimdall_first"), routing="heimdall_first", record_dir=d, replay=True)
        kept, rec = OE.pool(r, [self.m], self.sources, CTX, cache_path=self.cache_file(self.cache), admit=Admit(),
                            path=RULES, recover=True)
        self.assertEqual((kept, rec["refused"]), ([], {}))
        self.assertIn("got no answer", rec["unverified"][self.m["moment_id"]])


class TestItem3sWindowClip(unittest.TestCase):
    def test_let_me_read_that_again_is_extended_by_its_frozen_answer_under_lean(self):
        """Item 3's must-fail clip, refused as 'a window record cannot be extended': under lean its frozen answer
        (sentence 0 finishes it) extends it inside its window; its new edge's own answer is not recorded: UNVERIFIED."""
        fx = json.load(open(os.path.join(ITEM3, "moment.json")))
        m, wp = fx["moment"], fx["word_pass"]
        src, _, why = LB.window_source(m, wp, CTX, store=os.path.join(ITEM3, "store"))
        self.assertIsNotNone(src, why)
        r = P.Router(chains=PL.chains("heimdall_first"), routing="heimdall_first",
                     record_dir=os.path.join(ITEM3, "replies"), replay=True)
        adm = Admit()
        kept, rec = OE.pool(r, [m], {m["source_key"]: src, m["video_id"]: src}, CTX, admit=adm, recover=True)
        self.assertEqual(kept, [])
        self.assertEqual(len(adm.seen), 1)                                 # the extension was made and gated
        self.assertTrue(adm.seen[0]["text"].endswith("Bitcoin bottom four years ago to the exact day."))
        self.assertIn("got no answer", rec["unverified"][m["moment_id"]])  # open work, never a pass


class TestTheBounds(unittest.TestCase):
    def test_never_the_window_records_last_sentence(self):
        """MUST-FAIL: the sentence that would finish it is the window's last (the decode may have cut it): no extension;
        one sentence long, it cannot be shortened either: refused."""
        sentences = T162.SENTENCES[:3]                                     # the clip (1), then the window's last (2)
        src, m, sources = window(sentences)
        self.assertEqual(OE.around(m, src, True)[2], [None])
        adm = Admit()
        kept, rec = OE.pool(T162.Fake(T162.NO0), [m], sources, CTX, admit=adm, recover=True, path=RULES)
        self.assertEqual((kept, adm.seen), ([], []))
        self.assertIn("window record's last sentence", rec["refused"][m["moment_id"]])
        self.assertIn("cannot be shortened", rec["refused"][m["moment_id"]])

    def test_only_what_the_checker_read(self):
        src, m, sources = window(T162.SENTENCES + ["One more.", "And more."])
        before, nxt, ks = OE.around(m, src, True)
        self.assertEqual(len(nxt), OE.AFTER_N)                             # never past the AFTER_N sentences asked
        self.assertEqual(len(ks), len(nxt))
        self.assertEqual(ks, [2, 3, 4])

    def test_an_out_edge_cut_inside_its_sentence_is_re_anchored_to_its_end(self):
        """MUST-PASS: the clip stops inside its own last sentence (IN edge at its start): the checker's sentence 0 is
        the rest of that sentence: the OUT edge moves to the sentence's end (a new span, gated, asked again)."""
        src, m, sources = T162.case()
        cut = dict(m, words=[m["words"][0], m["words"][1] - 3], moment_id=m["moment_id"] + "~cut")
        cut["text"] = E.spoken(src.tokens[cut["words"][0]:cut["words"][1] + 1])
        self.assertEqual(OE.around(cut, src, True)[2][0], cut["sentences"][1])   # its own sentence's end
        adm = Admit()
        kept, rec = OE.pool(T162.Fake(T162.NO0, T162.YES), [cut], sources, CTX, admit=adm, recover=True, path=RULES)
        self.assertEqual(len(kept), 1, rec)
        self.assertEqual(kept[0]["text"], T162.OPENER)                     # the whole sentence, nothing more
        kept, rec = OE.pool(T162.Fake(T162.NO0), [cut], sources, CTX, admit=Admit(), path=RULES)   # the old path
        self.assertEqual(kept, [])

    def test_a_clip_cut_inside_its_first_sentence_is_never_extended_or_shortened(self):
        """MUST-FAIL: a trimmed IN edge: no whole-sentence span keeps it: refused, as before."""
        src, m, sources = T162.case(k0=1, k1=2)
        cut = dict(m, words=[m["words"][0] + 1, m["words"][1]], moment_id=m["moment_id"] + "~trim")
        self.assertEqual(OE.around(cut, src, True)[2], [None, None])
        adm = Admit()
        kept, rec = OE.pool(T162.Fake(T162.NO0), [cut], sources, CTX, admit=adm, recover=True, path=RULES)
        self.assertEqual((kept, adm.seen), ([], []))
        self.assertIn("cannot be shortened", rec["refused"][cut["moment_id"]])
        with self.assertRaises(ValueError):
            TV.extend(cut, src, 3, CTX, "x")


class TestShortened(unittest.TestCase):
    def two(self):
        long = ("Everybody had been saying for days now on every show and every stream that the bottom was in, that "
                "the worst was behind us and the selling was finally done.")          # 30 words: 9 s
        return T162.case([T162.SENTENCES[0], long, T162.OPENER] + T162.SENTENCES[2:], k0=1, k1=2)

    def test_runs_on_and_cannot_be_extended_it_is_shortened_to_its_previous_sentence(self):
        """MUST-PASS: nothing listed finishes its last sentence's thought: the clip ends at its previous sentence
        instead, a new span (gated, asked again), kept when that sentence ends the thought."""
        src, m, sources = self.two()
        adm = Admit()
        kept, rec = OE.pool(T162.Fake(T162.NO_NONE, T162.YES), [m], sources, CTX, admit=adm, recover=True,
                            path=RULES, floor_s=PK.SHORT_CLIP_S)
        self.assertEqual(len(kept), 1, rec)
        x = kept[0]
        self.assertEqual(rec["shortened"], {m["moment_id"]: x["moment_id"]})
        self.assertTrue(x["text"].endswith("the selling was finally done."), x["text"])
        self.assertEqual(x["derived_from"]["how"], "shortened (lean 2)")
        self.assertEqual([v["moment_id"] for v in adm.seen], [x["moment_id"]])
        self.assertGreaterEqual(x["duration_s"], PK.SHORT_CLIP_S)
        kept, rec = OE.pool(T162.Fake(T162.NO_NONE), [m], sources, CTX, admit=Admit(), path=RULES)   # the old path
        self.assertEqual(kept, [])

    def test_a_shortened_clip_under_the_floor_or_running_on_too_is_dropped(self):
        """MUST-FAIL: under the floor (never asked), or its own edge runs on too, or its gates refuse it: dropped."""
        src, m, sources = self.two()
        kept, rec = OE.pool(T162.Fake(T162.NO_NONE), [m], sources, CTX, admit=Admit(), recover=True, path=RULES,
                            floor_s=60.0)
        self.assertEqual(kept, [])
        self.assertIn("under the 60 s floor", rec["refused"][m["moment_id"]])
        kept, rec = OE.pool(T162.Fake(T162.NO_NONE, T162.NO_NONE), [m], sources, CTX, admit=Admit(), recover=True,
                            path=RULES, floor_s=PK.SHORT_CLIP_S)
        self.assertEqual(kept, [])
        self.assertIn("runs on too", rec["refused"][m["moment_id"]])
        kept, rec = OE.pool(T162.Fake(T162.NO_NONE), [m], sources, CTX, admit=Admit("step A: SPEAKER_CHANGE"),
                            recover=True, path=RULES, floor_s=PK.SHORT_CLIP_S)
        self.assertEqual(kept, [])
        self.assertIn("fails before its question: step A: SPEAKER_CHANGE", rec["refused"][m["moment_id"]])
        r = T162.Fake(T162.NO_NONE, P.ProviderError("down"))
        kept, rec = OE.pool(r, [m], sources, CTX, admit=Admit(), recover=True, path=RULES, floor_s=PK.SHORT_CLIP_S)
        self.assertEqual((kept, rec["refused"]), ([], {}))                 # no answer: UNVERIFIED, never a pass
        self.assertIn("got no answer", rec["unverified"][m["moment_id"]])


class TestTheExclusionScreenOnANewSpan(unittest.TestCase):
    def test_an_extension_that_adds_an_ad_read_is_refused_by_the_free_screen(self):
        """MUST-FAIL: the lean admit() runs the exclusion screen's free part on every new span: an extension whose added
        sentence is a sponsor read is refused there (its parent passes)."""
        ad = "This episode is sponsored by Kraken, the exchange I trust."
        src, m, sources = T162.case([T162.SENTENCES[0], T162.OPENER, ad, "Back to Bitcoin now."])
        self.assertEqual(PK.ad_read_out([m], sources), {})
        x = TV.extend(m, src, 2, CTX, "test")
        why = PK.ad_read_out([x], sources).get(x["moment_id"])
        self.assertTrue(why and not why.endswith("in the sentence before it"), why)


if __name__ == "__main__":
    unittest.main()
