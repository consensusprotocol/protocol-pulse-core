#!/usr/bin/env python3
"""RULING 104 (orchestrator 14:12 ET Nov 14), THE TAIL-SIDE TWIN (pipeline/tail_variant.py and its use in the ledger
build and the spotlight): a variant ENDING at an earlier sentence boundary of the mined moment, when that keeps it lawful
(a held word after the boundary, a tail the cut cannot make, the seconds ceiling); a new span that faces every gate,
recorded as derived from its parent row. The case: Blockware Solutions 06d34e15, held on "401k".
Offline: word-timed test sources, a temporary results directory."""
import copy
import json
import os
import sys
import tempfile
import unittest
import unittest.mock

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
for _p in ("pipeline", "tests/package", "tests/eligibility"):
    sys.path.insert(0, os.path.join(REPO, _p))
import eligibility as E  # noqa: E402
import lock_precheck as LP  # noqa: E402
import moments as M  # noqa: E402
import proof_ledger as PLG  # noqa: E402
import spotlight as SPOT  # noqa: E402
import tail_variant as TV  # noqa: E402
import test_spotlight as TS  # noqa: E402
from test_eligibility import NOW, REG, source  # noqa: E402

SENTENCES = ["On my 20th birthday, I sold every stock in my Roth IRA and put it all into Bitcoin.",
             "That ended up being one of the best financial decisions I've ever made, but not for the reason most "
             "people think.",
             "I'm 26 now, and I still don't use my Roth IRA.",
             "I don't have a 401k.",
             "I don't own a single share of any index fund, and I'm on pace to be financially independent by 45."]
CTX = E.Context(NOW, REG)
META = {"scores": {"contempt_outrage": 0, "hook_first_2s": 5, "quotable": 4, "stakes": 5, "stance": 4,     # the real
                   "stands_alone": 5, "surprising_fact": 4},                                         # row's, build 11
        "names_person": False, "risk": [], "topics": ["bitcoin"], "reason": "Strong personal narrative hook"}


def parent(src, k0=0, k1=4, vid="7BqLu-wzbU0"):
    sp = E.Span(src, k0, k1)
    m = M.record(sp, META, CTX, M.judge(sp, CTX), {"ledger_moment_id": "06d34e155feae654ee56"})
    m["rank_score"] = M.rank_score(m)
    m["source_key"] = vid
    return m


def blockware():
    src = source(SENTENCES, vid="7BqLu-wzbU0")
    return src, parent(src)


def hold(m, at="2026-11-14T19:51:07Z", spoken=None, reason="ruling 72/84: ... at [['401k', '401']]",
         outcome="hold", role="hook", text=None, rules=None):
    return {"rules": LP.RULES if rules is None else rules,
            "request_id": "pp-selectid.ledger_x.1", "video_id": m["video_id"], "start": m["start"], "end": m["end"],
            "window": [round(m["start"], 3), round(m["end"], 3)], "role": role,
            "approved_text": m["text"] if text is None else text, "outcome": outcome, "reason": reason, "at": at,
            "as_spoken": {"verdict": outcome, "text": m["text"].replace("401k.", "401 ,") if spoken is None
                          else spoken}}


def put(d, m, entries, decoder=LP.DECODER):
    p = os.path.join(d, f"{m['video_id']}.{round(m['start'], 3):.3f}-{round(m['end'], 3):.3f}.{decoder}.json")
    with open(p, "w") as f:
        json.dump(entries, f)


class TestTheVariant(unittest.TestCase):
    def test_it_ends_at_the_boundary_is_a_new_span_and_names_its_parent(self):
        src, m = blockware()
        v = TV.variant(m, src, 2, CTX, "a held word")
        self.assertEqual(v["text"], " ".join(SENTENCES[:3]))
        self.assertEqual((v["sentences"], v["start"], v["end"]), ([0, 2], m["start"], src.tokens[src.sentences[2][1]]["end"]))
        self.assertNotEqual(v["moment_id"], m["moment_id"])                            # its own id
        self.assertEqual(v["moment_id"], M.record(E.Span(src, 0, 2), META, CTX, M.judge(E.Span(src, 0, 2), CTX),
                                                  {})["moment_id"])                    # the span's own
        d = v["derived_from"]
        self.assertEqual((d["ruling"], d["from"], d["ledger_moment_id"], d["sentences"], d["was"]),
                         (104, m["moment_id"], "06d34e155feae654ee56", [0, 2], [0, 4]))
        self.assertEqual(d["left_out"], " ".join(SENTENCES[3:]))
        self.assertEqual(v["mined"]["derived_from"], d)                                 # in its mined record too
        self.assertEqual((v["source_key"], v["scores"], v["topics"]), (m["source_key"], m["scores"], m["topics"]))
        self.assertEqual(set(v["eligibility"]), {"hook", "clip"})                       # judged afresh on its span
        for k in (4, 5, -1, "2"):
            with self.assertRaises(ValueError):
                TV.variant(m, src, k, CTX, "x")


class TestTheHeldWord(unittest.TestCase):
    def test_the_401k_hold_is_placed_on_its_word_from_the_texts(self):
        src, m = blockware()
        i = TV.held_word(m, src, hold(m))
        self.assertEqual(src.tokens[i]["word"], "401k.")
        self.assertEqual(i, src.sentences[3][0] + 4)                                   # "I don't have a 401k."

    def test_a_difference_inside_ruling_84_s_class_is_passed_over(self):
        """A one-function-word substitution earlier in the span is in ruling 84's class: the held word is still 401k."""
        src, m = blockware()
        spoken = m["text"].replace("one of the best", "one of a best").replace("401k.", "401 ,")
        self.assertEqual(src.tokens[TV.held_word(m, src, hold(m, spoken=spoken))]["word"], "401k.")

    def test_an_insert_before_the_hold_cannot_be_placed_so_no_variant(self):
        """The second reading inserts a number in the FIRST sentence and differs on 401k: no variant can leave the
        insert out, so the word is not placed (no variant), never the later 401k."""
        src, m = blockware()
        spoken = m["text"].replace("into Bitcoin.", "into Bitcoin 21.").replace("401k.", "401 ,")
        self.assertIsNone(TV.held_word(m, src, hold(m, spoken=spoken)))

    def test_what_cannot_be_placed_gives_none(self):
        src, m = blockware()
        self.assertIsNone(TV.held_word(m, src, hold(m, spoken="")))                          # no second reading
        self.assertIsNone(TV.held_word(m, src, dict(hold(m), as_spoken=None)))
        self.assertIsNone(TV.held_word(m, src, hold(m, spoken=m["text"].replace("401k.", "401k, um,"))))  # a filler
        self.assertIsNone(TV.held_word(m, src, hold(m, spoken=m["text"].replace("Bitcoin.", "Bitcoin 21."))))  # inserted


class TestTheHolds(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.addCleanup(self.d.cleanup)

    def test_the_newest_hold_on_the_exact_span_under_the_current_decoder_and_rules(self):
        src, m = blockware()
        self.assertIsNone(TV.holds(m, self.d.name))
        put(self.d.name, m, [hold(m, at="2026-11-14T20:00:00Z", reason="an older decoder")], decoder="c705b20ed800")
        self.assertIsNone(TV.holds(m, self.d.name))                                     # never read: not final now
        put(self.d.name, m, [hold(m, at="2026-11-14T18:00:00Z", reason="old"),
                             hold(m, at="2026-11-14T20:30:00Z", reason="older rules",
                                  rules="ruling 17 + ruling 72 + ruling 73 + ruling 84"),   # never read
                             hold(m, at="2026-11-14T18:51:07Z", reason="new"),
                             hold(m, outcome="no_difference", at="2026-11-14T18:30:00Z"),       # an older pass
                             hold(m, at="2026-11-14T19:30:00Z", text="another text"),           # another span's text
                             dict(hold(m, at="2026-11-14T19:31:00Z"), window=[0.0, 9.0])])      # another window
        self.assertEqual(TV.holds(m, self.d.name)["reason"], "new")
        passed = tempfile.TemporaryDirectory()                                           # a NEWER pass: not held now
        self.addCleanup(passed.cleanup)
        put(passed.name, m, [hold(m, at="2026-11-14T18:51:07Z"), hold(m, outcome="no_difference",
                                                                   at="2026-11-14T19:00:00Z")])
        self.assertIsNone(TV.holds(m, passed.name))
        clip = tempfile.TemporaryDirectory()                                            # held as a medley clip
        self.addCleanup(clip.cleanup)
        put(clip.name, m, [hold(m, role="clip", reason="as a clip")])
        self.assertEqual(TV.holds(m, clip.name)["reason"], "as a clip")
        put(clip.name, m, [hold(m, role="clip", reason="as a clip", at="2026-11-14T19:00:00Z"),
                           hold(m, role="hook", reason="as a hook, newer", at="2026-11-14T19:10:00Z")])
        self.assertEqual(TV.holds(m, clip.name)["reason"], "as a hook, newer")      # the newest of the two roles
        with open(os.path.join(self.d.name, f"{m['video_id']}.0.000-1.000.c705b20ed800.json"), "w") as f:
            f.write("{ broken")                                                                  # never read: another span
        self.assertEqual(TV.holds(m, self.d.name)["reason"], "new")


class TestThePool(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.addCleanup(self.d.cleanup)

    def pool(self, ms, sources, ceil_s=35.0):
        vs, notes, replaced = TV.for_pool(ms, sources, CTX, self.d.name, ceil_s)
        self.replaced = replaced
        return vs, notes

    def test_blockware_held_on_401k_gives_the_variant_ending_before_it(self):
        src, m = blockware()
        put(self.d.name, m, [hold(m)])
        vs, notes = self.pool([m], {"7BqLu-wzbU0": src})
        self.assertEqual([v["text"] for v in vs], [" ".join(SENTENCES[:3])])     # "...I still don't use my Roth IRA."
        self.assertIn("a held word after the boundary: '401k.'", vs[0]["derived_from"]["why"])
        self.assertIn(vs[0]["moment_id"], notes[m["moment_id"]])
        self.assertEqual(self.replaced, {m["moment_id"]})                              # its hold is final

    def test_a_cut_the_render_cannot_make_drops_the_last_sentence(self):
        src, m = blockware()
        put(self.d.name, m, [hold(m, reason="ruling 73: the render cannot cut this span: the OUT edge")])
        vs, _ = self.pool([m], {"7BqLu-wzbU0": src})
        self.assertEqual(vs[0]["sentences"], [0, 3])

    def test_the_seconds_ceiling_gives_the_longest_variant_within_it(self):
        src, m = blockware()
        limit = src.tokens[src.sentences[2][1]]["end"] - m["start"] + 0.01           # sentences 0-2 fit, 0-3 do not
        vs, _ = self.pool([m], {"7BqLu-wzbU0": src}, ceil_s=limit)
        self.assertEqual(vs[0]["sentences"], [0, 2])
        self.assertIn("the seconds ceiling", vs[0]["derived_from"]["why"])
        self.assertEqual(self.replaced, set())                                          # the parent stays beside it
        put(self.d.name, m, [hold(m, reason="ruling 73: the render cannot cut this span")])   # both: the shorter
        vs, _ = self.pool([m], {"7BqLu-wzbU0": src}, ceil_s=limit)
        self.assertEqual(vs[0]["sentences"], [0, 2])
        self.assertIn("a tail the cut cannot make", vs[0]["derived_from"]["why"])

    def test_no_variant_where_none_keeps_it_lawful(self):
        src, m = blockware()
        put(self.d.name, m, [hold(m, spoken=m["text"].replace("20th", "21st"))])       # held in its FIRST sentence
        vs, notes = self.pool([m], {"7BqLu-wzbU0": src})
        self.assertEqual((vs, notes[m["moment_id"]]), ([], "no variant: the held word is in its first sentence"))
        limit = src.tokens[src.sentences[2][1]]["end"] - m["start"] + 0.01            # and over the ceiling too:
        vs, notes = self.pool([m], {"7BqLu-wzbU0": src}, ceil_s=limit)                 # no ceiling variant either
        self.assertEqual((vs, notes[m["moment_id"]], self.replaced),                   # (it would keep the held
                         ([], "no variant: the held word is in its first sentence", set()))   # word: qwen C2)
        one = parent(src, 2, 2)                                                           # one sentence: no boundary
        put(self.d.name, one, [hold(one)])
        self.assertEqual(self.pool([one], {"7BqLu-wzbU0": src}), ([], {}))
        self.assertEqual(self.pool([m], {}), ([], {m["moment_id"]: "no variant: its word record is not in this build"}))
        clean = blockware()[1]                                                            # no hold, under the ceiling
        clean["start"] += 0.0005                                                          # (another span on file)
        self.assertEqual(self.pool([clean], {"7BqLu-wzbU0": src}), ([], {}))

    def test_a_variant_already_in_the_pool_is_not_added_twice(self):
        src, m = blockware()
        put(self.d.name, m, [hold(m)])
        v = TV.variant(m, src, 2, CTX, "x")
        vs, notes = self.pool([m, v], {"7BqLu-wzbU0": src})
        self.assertEqual(vs, [])
        self.assertIn("already in the pool", notes[m["moment_id"]])

    def test_the_ledger_build_replaces_a_held_parent_and_keeps_one_over_the_ceiling(self):
        src, m = blockware()
        other = parent(src, 3, 4)                                                         # another moment, no trigger
        put(self.d.name, m, [hold(m)])
        inputs, said = {}, []
        out = PLG.with_variants([m, other], {"7BqLu-wzbU0": src}, CTX, inputs, said.append, results_dir=self.d.name)
        self.assertEqual([x["moment_id"] for x in out], [other["moment_id"], inputs["ruling_104"]["variants"][0]])
        self.assertEqual(out[1]["text"], " ".join(SENTENCES[:3]))
        self.assertEqual(inputs["ruling_104"]["replaced"], [m["moment_id"]])
        self.assertIn("1 variant(s) in the pool, 1 held parent(s) replaced", said[0])
        limit = src.tokens[src.sentences[2][1]]["end"] - m["start"] + 0.01
        clean = tempfile.TemporaryDirectory()
        self.addCleanup(clean.cleanup)
        with unittest.mock.patch.object(SPOT, "SPOT_S", (12.0, limit)):                # over the ceiling: beside it
            out = PLG.with_variants([m], {"7BqLu-wzbU0": src}, CTX, {}, said.append, results_dir=clean.name)
        self.assertEqual([x["sentences"] for x in out], [[0, 4], [0, 2]])


class TestTheSpotlight(unittest.TestCase):
    def test_a_variant_is_never_snapped_outward(self):
        src, m = blockware()
        short = TV.variant(m, src, 1, CTX, "x")                                          # two sentences, under 13.7 s
        self.assertLess(short["duration_s"], SPOT.SNAP_TO_S)
        caps = lambda vid: ([], None)
        v, why = SPOT.snap(short, {"7BqLu-wzbU0": src}, CTX, captions_for=caps)
        self.assertIsNone(v)
        self.assertIn("never snapped outward", why)
        plain = dict(short)
        plain.pop("derived_from")
        v, _ = SPOT.snap(plain, {"7BqLu-wzbU0": src}, CTX, captions_for=caps)         # any other moment: snapped
        self.assertIsNotNone(v)
        long_ = TV.variant(m, src, 2, CTX, "x")
        self.assertGreaterEqual(long_["duration_s"], SPOT.SNAP_TO_S)
        self.assertIs(SPOT.snap(long_, {"7BqLu-wzbU0": src}, CTX, captions_for=caps)[0], long_)

    def test_the_spotlight_pin_records_where_the_variant_came_from(self):
        m = TS.moment()
        pk, why, *_ = TS.package(m=m)
        self.assertIsNone(why)
        self.assertNotIn("derived_from", pk["spotlight"])                               # every other pin as before
        d = {"ruling": 104, "from": "06d34e155feae654ee56", "sentences": [0, 2], "was": [0, 4], "why": "x"}
        pk, why, *_ = TS.package(m=dict(copy.deepcopy(m), derived_from=d))
        self.assertIsNone(why)
        self.assertEqual(pk["spotlight"]["derived_from"], d)


if __name__ == "__main__":
    unittest.main()
