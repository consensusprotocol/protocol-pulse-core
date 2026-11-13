#!/usr/bin/env python3
"""pipeline/house_style.py, ORCHESTRATOR RULING 6 (22:40 ET Nov 12): the house style of the title, the caption and the
takeaway (bridges get the rules shared by every surface). Must-fail and must-pass cases; the 41f29b1f pin's own lines
are the fixtures the ruling names. Offline, no model."""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "pipeline"))
import house_style as HS  # noqa: E402

PIN_41F29B1F = {   # the delivered medley's lines (tests/package/proof/fresh_20261112_050611/MOMENTS_PIN_LY.json)
    "caption": "A market that no single authority can switch off may be the most mispriced opportunity in finance, and "
               "that is the point this medley builds toward.",
    "title": "Bitcoin's overlooked value comes from a market no government owns",
    "takeaway": "What stands out is how rare it is for any asset to be priced by everyone and controlled by no one, which "
                "makes the usual political drama feel irrelevant.",
}


def ids(slot, text):
    return {v["detail"].split(":")[0] for v in HS.lint(slot, text)}


class TestTheDeliveredLines(unittest.TestCase):
    def test_the_41f29b1f_caption_fails_four_rules(self):
        got = ids("caption", PIN_41F29B1F["caption"])
        self.assertTrue({"caption-lowercase", "hedge", "self-reference", "money-word"} <= got, got)
        self.assertIn("caption-words", got)                     # 26 words, over 24
        self.assertGreaterEqual(len(got), 4)

    def test_the_41f29b1f_title_fails_possessive_and_length(self):
        self.assertEqual(ids("title", PIN_41F29B1F["title"]), {"title-possessive", "title-words"})

    def test_the_41f29b1f_takeaway_fails_opener_which_makes_and_length(self):
        self.assertEqual(ids("takeaway", PIN_41F29B1F["takeaway"]),
                         {"takeaway-opener", "which-makes", "takeaway-words"})

    def test_the_style_reference_fails_only_its_length(self):
        self.assertEqual(len(HS.STYLE_REFERENCE.split()), 24)
        self.assertEqual(ids("takeaway", HS.STYLE_REFERENCE), {"takeaway-words"})


class TestMustPass(unittest.TestCase):
    def test_plain_lines_pass(self):
        self.assertEqual(HS.lint("title", "The market no government owns"), [])
        self.assertEqual(HS.lint("caption", "no authority. that's the design."), [])
        self.assertEqual(HS.lint("bridge", "Next, on keys."), [])
        self.assertEqual(HS.lint("bridge_1", "Next, on keys."), [])
        self.assertEqual(HS.lint("intro", "Next, on keys."), [])
        self.assertEqual(HS.lint("takeaway", "No ruler. Just rules nobody gets to bend."), [])

    def test_pbx_s_own_caption_fails_only_the_sentence_count(self):
        self.assertEqual(ids("caption", "no authority. that's the design. three clips, links below."),
                         {"caption-sentences"})

    def test_no_false_hedges_and_no_false_possessives(self):
        for ok in ("the mayor spoke", "maybe not", "mighty rules", "the perhapsless case"):
            self.assertNotIn("hedge", ids("caption", ok), ok)
        self.assertNotIn("title-possessive", ids("title", "It's the market no government owns"))
        self.assertNotIn("title-possessive", ids("title", "That's the design"))
        self.assertIn("title-possessive", ids("title", "Bitcoin’s quiet edge"))      # a curly apostrophe too
        self.assertIn("title-possessive", ids("title", "Holders' real problem"))      # a plural possessive

    def test_a_one_letter_abbreviation_ends_no_sentence(self):
        self.assertEqual(HS.sentence_count("u.s. markets fell. bitcoin did not."), 2)
        self.assertEqual(HS.sentence_count("no authority"), 1)
        self.assertEqual(HS.sentence_count(""), 0)

    def test_money_words_are_stems_on_purpose(self):
        self.assertIn("money-word", ids("caption", "an investigation of the network"))    # deliberate: invest\w*
        self.assertNotIn("money-word", ids("caption", "a nonprofit keeps the code"))     # not a word start


class TestEveryRuleFails(unittest.TestCase):
    def test_hashtag_on_every_surface(self):
        for slot in ("title", "caption", "takeaway", "bridge"):
            self.assertIn("hashtag", ids(slot, "rules #bitcoin"), slot)
        self.assertNotIn("hashtag", ids("caption", "rule # one"))                        # a bare '#' is no tag

    def test_each_dash_form(self):
        for d in ("—", "–", " -- "):
            self.assertIn("em-dash", ids("caption", f"no ruler{d}just rules"), repr(d))
        self.assertNotIn("em-dash", ids("caption", "self-custody, no ruler"))             # a hyphen is fine

    def test_emoji(self):
        for e in ("\U0001F680", "⭐", "✅", "\U0001F1FA\U0001F1F8"):
            self.assertIn("emoji", ids("title", f"No ruler {e}"), repr(e))

    def test_every_hedge(self):
        for h in HS.HEDGES:
            self.assertIn("hedge", ids("takeaway", f"It {h} hold."), h)
            self.assertIn("hedge", ids("caption", f"it {h.upper()} hold."), h)          # case-insensitive

    def test_every_ai_phrase(self):
        for p in HS.AI_PHRASES:
            self.assertIn("ai-phrasing", ids("bridge", f"Here, {p} things."), p)
        self.assertIn("ai-phrasing", ids("bridge", "It’s worth noting the rules."))     # the curly apostrophe

    def test_every_self_reference(self):
        for p in HS.SELF_REFERENCE:
            self.assertIn("self-reference", ids("caption", f"look at {p} now."), p)

    def test_every_money_pattern(self):
        for word in ("opportunity", "opportunities", "invest", "investors", "profit", "profitable", "get rich",
                     "to the moon", "buy the dip", "financial advice"):
            self.assertIn("money-word", ids("caption", f"some {word} here."), word)

    def test_the_length_rules(self):
        self.assertIn("title-words", ids("title", " ".join(["word"] * (HS.TITLE_MAX_WORDS + 1))))
        self.assertNotIn("title-words", ids("title", " ".join(["word"] * HS.TITLE_MAX_WORDS)))
        self.assertIn("takeaway-words", ids("takeaway", " ".join(["word"] * (HS.TAKEAWAY_MAX_WORDS + 1))))
        self.assertNotIn("takeaway-words", ids("takeaway", " ".join(["word"] * HS.TAKEAWAY_MAX_WORDS)))
        self.assertIn("caption-words", ids("caption", " ".join(["word"] * (HS.CAPTION_MAX_WORDS + 1))))
        self.assertNotIn("caption-words", ids("caption", " ".join(["word"] * HS.CAPTION_MAX_WORDS)))
        self.assertIn("caption-lowercase", ids("caption", "no Ruler."))

    def test_every_opener_and_which_makes(self):
        for o in HS.TAKEAWAY_OPENERS:
            self.assertIn("takeaway-opener", ids("takeaway", f"\"{o.capitalize()}, the rules hold."), o)
            self.assertNotIn("takeaway-opener", ids("takeaway", f"The rules hold, {o}."), o)    # only as the opener
        self.assertIn("which-makes", ids("takeaway", "The rules hold, which makes it rare."))

    def test_every_rule_id_has_a_must_fail_case(self):
        fired = set()
        for slot, text in [("caption", PIN_41F29B1F["caption"]), ("title", PIN_41F29B1F["title"]),
                           ("takeaway", PIN_41F29B1F["takeaway"]), ("caption", "one. two. three."),
                           ("bridge", "#tag — \U0001F680 delve")]:
            fired |= ids(slot, text)
        self.assertEqual(fired, set(HS.RULE_IDS))


class TestTheInterface(unittest.TestCase):
    def test_violations_carry_the_slot_rule_and_a_rule_id_detail(self):
        for v in HS.lint("caption", PIN_41F29B1F["caption"]):
            self.assertEqual((v["slot"], v["rule"]), ("caption", "STYLE"))
            self.assertIn(v["detail"].split(":")[0], HS.RULE_IDS)
        self.assertEqual(len({v["detail"].split(":")[0] for v in HS.lint("caption", PIN_41F29B1F["caption"])}),
                         len(HS.lint("caption", PIN_41F29B1F["caption"])))             # one violation per rule id

    def test_lint_lines_keeps_each_line_s_own_slot_and_skips_the_rest(self):
        lines = [{"slot": "intro", "text": "Next — keys."}, {"slot": "bridge_1", "text": "maybe #keys"},
                 {"slot": "takeaway", "text": PIN_41F29B1F["takeaway"]}, {"slot": "title", "text": "Fine title"},
                 {"slot": "caption", "text": "fine caption."}, {"slot": "-", "text": "#ignored"}]
        got = [(v["slot"], v["detail"].split(":")[0]) for v in HS.lint_lines(lines)]
        self.assertIn(("intro", "em-dash"), got)
        self.assertIn(("bridge_1", "hashtag"), got)
        self.assertNotIn(("bridge_1", "hedge"), got)                                      # "maybe" is no hedge
        self.assertIn(("takeaway", "which-makes"), got)
        self.assertFalse([s for s, _ in got if s in ("title", "caption", "-")])

    def test_an_unknown_slot_is_refused(self):
        with self.assertRaises(ValueError):
            HS.lint("signoff", "Clips today from A.")

    def test_the_prompt_states_the_same_rules(self):
        p = HS.PROMPT_RULES
        for x in (str(HS.CAPTION_MAX_WORDS), str(HS.TITLE_MAX_WORDS), str(HS.TAKEAWAY_MAX_WORDS), HS.STYLE_REFERENCE,
                  "lowercase", "possessive", "which makes") + HS.HEDGES + HS.SELF_REFERENCE + HS.TAKEAWAY_OPENERS:
            self.assertIn(x, p, x)


if __name__ == "__main__":
    unittest.main()
