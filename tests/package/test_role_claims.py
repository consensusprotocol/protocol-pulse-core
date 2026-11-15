#!/usr/bin/env python3
"""The orchestrator, 21:10 ET Nov 14: Blockware's spotlight caption called the channel's own presenter "a guest". "A
caption may not assign a role the evidence does not show: 'a guest', 'the host', 'an analyst' are claims under L-v. Fix
the writer's instructions and add it to the fidelity gate's checks." Offline."""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "pipeline"))
import package as PK  # noqa: E402
import spotlight as SPOT  # noqa: E402
import vo_fidelity as VF  # noqa: E402

BLOCKWARE = {"m1": {"show": "Blockware Solutions", "speaker": None, "names": [], "video_id": "7BqLu-wzbU0",
                    "text": "On my 20th birthday, I sold every stock in my Roth IRA and put it all into Bitcoin."}}
MAN = {"channels": ["Blockware Solutions"], "date": "2026-11-14"}


def rules(text, slot="caption", segs=BLOCKWARE, cites=("m1",)):
    out = VF.check_deterministic(segs, [{"slot": slot, "text": text, "cites": list(cites)}], MAN)
    return [x["rule"] for x in out["violations"]]


class TestTheFidelityGate(unittest.TestCase):
    def test_blockwares_caption_fails_and_the_same_line_without_the_role_passes(self):
        self.assertIn("ROLE", rules("a guest sold his retirement stocks for bitcoin and skipped the usual path."))
        self.assertNotIn("ROLE", rules("he sold his retirement stocks for bitcoin and skipped the usual path."))

    def test_every_role_word_in_every_slot_needs_the_clips_own_words(self):
        for line in ("The host sold everything.", "an analyst sold his stocks", "Our guest went all in",
                     "A Wall Street strategist sold his IRA", "the co-host bought bitcoin", "Two experts disagree"):
            for slot in ("caption", "title", "comment", "closing"):
                self.assertIn("ROLE", rules(line, slot), (line, slot))

    def test_a_role_the_clip_states_is_no_claim_of_ours(self):
        segs = {"m1": {"show": "X", "speaker": None, "names": [], "video_id": "v",
                       "text": "I'm an analyst at a big bank and I think bitcoin wins."}}
        self.assertNotIn("ROLE", rules("an analyst thinks bitcoin wins", segs=segs))
        self.assertIn("ROLE", rules("an analyst thinks bitcoin wins", segs=segs, cites=()))   # not cited: no source
        self.assertIn("ROLE", rules("a guest thinks bitcoin wins", segs=segs))                # another role

    def test_a_show_or_channel_named_with_a_role_word_is_no_claim(self):     # audit 2131 C1 (glm)
        segs = {"m1": {"show": "Analyst Answers", "speaker": None, "names": [], "video_id": "v",
                       "text": "Bitcoin is a bearer asset."}}
        out = VF.check_deterministic(segs, [{"slot": "caption", "text": "From Analyst Answers: bitcoin as a bearer asset.",
                                             "cites": ["m1"]}], {"channels": ["Analyst Answers"], "date": "2026-11-14"})
        self.assertNotIn("ROLE", [x["rule"] for x in out["violations"]])
        self.assertIn("ROLE", rules("Our guests sold everything."))        # still a claim elsewhere

    def test_the_comparison_is_canonical(self):
        segs = {"m1": {"show": "X", "speaker": None, "names": [], "video_id": "v",
                       "text": "Analyst here. I think bitcoin wins."}}            # sentence-initial, capitalised
        self.assertNotIn("ROLE", rules("an ANALYST thinks bitcoin wins", segs=segs))
        self.assertIn("ROLE", rules("analysts think bitcoin wins", segs=segs))   # another word: a claim of ours

    def test_words_that_only_contain_a_role_are_not_roles(self):
        for line in ("He is hosting nothing.", "Ghosts of the old system.", "Anchoring on old prices fails."):
            self.assertNotIn("ROLE", rules(line), line)


class TestTheWriters(unittest.TestCase):
    def test_both_writers_are_told_never_to_give_a_role(self):
        for name, prompt in (("spotlight", SPOT.WRITE_SPOT), ("medley", PK.WRITE_LY)):
            self.assertIn("Never give anyone a ROLE", prompt, name)
            for word in ('"guest"', '"host"', '"analyst"'):
                self.assertIn(word, prompt, (name, word))


if __name__ == "__main__":
    unittest.main()
