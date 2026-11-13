#!/usr/bin/env python3
"""pipeline/speakers.py (ORCHESTRATOR 00:05 ET Nov 13, item 3): every pin segment names its speaker where the source
names the person, with the evidence; an unknown speaker is "unknown", never a guess. Offline: the verdict is canned,
and code checks every claim against the text."""
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "pipeline"))
sys.path.insert(0, os.path.join(REPO, "tests", "eligibility"))
import package_pin  # noqa: E402
import speakers as SP  # noqa: E402
from test_eligibility import source  # noqa: E402

META = {"exact_title": "Jeff Booth Warning: The Scenario Nobody in Bitcoin Wants to Talk About",
        "channel_name": "Natalie Brunell",
        "description": "Are we headed toward a future of abundance?\n"
                       "Jeff Booth joins me to revisit The Price of Tomorrow and explore how AI is shaping our future.\n"
                       "https://example.com/link\n"}
LINES = SP.source_lines(META)
SENTS = ["Jeff, you wrote about deflation years ago.", "What do you see now?",
         "When I wrote The Price of Tomorrow, I said technology is deflationary.",
         "Bitcoin lets that deflation reach everyone.", "That is the point."]


def verdict(name, basis, people=None):
    return {"people": people if people is not None else [
        {"name": "Jeff Booth", "role": "guest", "line": "Jeff Booth joins me to revisit The Price of Tomorrow"},
        {"name": "Natalie Brunell", "role": "host", "line": "channel: Natalie Brunell"}],
        "speaker": {"name": name, "basis": basis, "why": "w"}}


class Reply:
    def __init__(self, text):
        self.text, self.backend, self.replayed, self.usage, self.usd, self.seconds = text, "xai:grok", False, {}, 0, 0


class Canned:
    def __init__(self, text):
        self.text, self.calls, self.rejected = text, [], []

    def call(self, role, prompt, max_tokens=2000, seed=7, **k):
        self.calls.append((role, prompt))
        return Reply(self.text)

    def reject(self, r):
        self.rejected.append(r)


class TestSourceLinesAndContext(unittest.TestCase):
    def test_the_sources_own_lines_and_never_a_bare_link(self):
        self.assertEqual(LINES[:2], ["title: Jeff Booth Warning: The Scenario Nobody in Bitcoin Wants to Talk About",
                                     "channel: Natalie Brunell"])
        self.assertIn("Jeff Booth joins me to revisit The Price of Tomorrow and explore how AI is shaping our future.",
                      LINES)
        self.assertNotIn("https://example.com/link", LINES)
        self.assertEqual(SP.source_lines({}), [])

    def test_the_context_is_the_word_records_own_sentences_around_the_clip(self):
        before, clip, after = SP.context(source(SENTS), 2, 2, before=2, after=1)
        self.assertEqual((before, clip, after), (SENTS[0] + " " + SENTS[1], SENTS[2], SENTS[3]))


class TestCheck(unittest.TestCase):
    clip, around = SENTS[2], SENTS[0] + " " + SENTS[1]

    def test_a_person_stands_only_on_a_source_line_that_names_them_and_carries_the_whole_line(self):
        people = [{"name": "Jeff Booth", "role": "guest", "line": "Jeff Booth joins me to revisit"},     # part of a line
                  {"name": "Saifedean Ammous", "role": "guest", "line": "Saifedean Ammous joins me"},      # not a line
                  {"name": "Natalie Brunell", "role": "host", "line": "Jeff Booth joins me to revisit"},  # not her line
                  {"name": "jeff booth", "role": "guest", "line": "title: Jeff Booth Warning"}]           # twice
        rec = SP.check(verdict("unknown", "", people), LINES, self.clip, self.around)
        self.assertEqual([(p["name"], p["line"]) for p in rec["people"]], [
            ("Jeff Booth", "Jeff Booth joins me to revisit The Price of Tomorrow and explore how AI is shaping our "
                           "future.")])

    def test_a_speaker_is_named_only_on_a_basis_in_the_clip_or_the_transcript_around_it(self):
        rec = SP.check(verdict("Jeff Booth", "When I wrote The Price of Tomorrow"), LINES, self.clip, self.around)
        self.assertEqual((rec["name"], rec["role"], rec["basis"]), ("Jeff Booth", "guest",
                                                                    "When I wrote The Price of Tomorrow"))
        self.assertTrue(rec["line"].startswith("Jeff Booth joins me"))
        rec = SP.check(verdict("Jeff Booth", "jeff you wrote about deflation"), LINES, self.clip, self.around)
        self.assertEqual(rec["name"], "Jeff Booth")                  # case and punctuation aside, in the context

    def test_a_title_that_names_a_guest_never_names_the_clips_speaker(self):
        """A basis found only in the source's lines (the title, the description) does not show who speaks a clip."""
        for basis in ("Jeff Booth joins me to revisit", "title: Jeff Booth Warning"):
            rec = SP.check(verdict("Jeff Booth", basis), LINES, self.clip, self.around)
            self.assertEqual(rec["name"], "unknown", basis)
            self.assertIn("not 3+ words found in the clip", rec["why"])
            self.assertEqual([p["name"] for p in rec["people"]], ["Jeff Booth", "Natalie Brunell"])   # still tagged

    def test_a_short_basis_an_unnamed_person_or_an_invented_quote_is_unknown(self):
        for name, basis in (("Jeff Booth", "I wrote"), ("Saifedean Ammous", "When I wrote The Price of Tomorrow"),
                            ("Jeff Booth", "As I said on my own podcast yesterday")):
            rec = SP.check(verdict(name, basis), LINES, self.clip, self.around)
            self.assertEqual((rec["name"], rec["basis"], rec["line"]), ("unknown", None, None), (name, basis))

    def test_a_quote_or_a_name_matches_whole_words_only(self):
        """Audit 0007 C2 (grok P2-2): a normalised substring could start or end inside a word."""
        rec = SP.check(verdict("Jeff Booth", "hen I wrote The Price of"), LINES, self.clip, self.around)
        self.assertEqual(rec["name"], "unknown")                  # "hen" is the end of "When"
        people = [{"name": "Jeff Boot", "role": "guest", "line": "Jeff Booth joins me to revisit"}]
        self.assertEqual(SP.check(verdict("unknown", "", people), LINES, self.clip, self.around)["people"], [])

    def test_a_verdict_out_of_contract_raises(self):
        for bad in ([], {"people": {}, "speaker": {}}, {"people": [], "speaker": "Jeff"}):
            with self.assertRaises(ValueError):
                SP.check(bad, LINES, self.clip, self.around)


class TestAttribute(unittest.TestCase):
    seg = {"video_id": "vidA", "k0": 2, "k1": 2}

    def test_a_named_speaker_with_its_evidence_and_the_backend(self):
        r = Canned(json.dumps(verdict("Jeff Booth", "When I wrote The Price of Tomorrow")))
        rec = SP.attribute(r, self.seg, source(SENTS), META)
        self.assertEqual((rec["name"], rec["measured"], rec["backend"]), ("Jeff Booth", True, "xai:grok"))
        self.assertEqual(r.calls[0][0], "speaker_verdict")
        self.assertIn("<clip>" + SENTS[2] + "</clip>", r.calls[0][1])

    def test_a_reply_out_of_contract_is_unknown_not_measured_and_rejected(self):
        r = Canned("Jeff Booth, probably")
        rec = SP.attribute(r, self.seg, source(SENTS), META)
        self.assertEqual((rec["name"], rec["measured"]), ("unknown", False))
        self.assertTrue(rec["why"].startswith("not measured"))
        self.assertEqual(len(r.rejected), 1)

    def test_a_fenced_reply_is_read_and_any_failure_claims_no_name(self):
        """glm C1 P1-2: a ```json fence is read; glm C1 P1-1: Router.call re-raises a back-end's own error, and any
        failure is "unknown" with measured false, never a crash of the whole seal."""
        body = json.dumps(verdict("Jeff Booth", "When I wrote The Price of Tomorrow"))
        for text in ("```json\n" + body + "\n```", "Sure, here it is:\n```json\n" + body + "\n```\nDone."):
            self.assertEqual(SP.attribute(Canned(text), self.seg, source(SENTS), META)["name"], "Jeff Booth", text[:9])

        class Boom(Canned):
            def call(self, *a, **k):
                raise RuntimeError("a back-end's own error")
        rec = SP.attribute(Boom("{}"), self.seg, source(SENTS), META)
        self.assertEqual((rec["name"], rec["measured"]), ("unknown", False))
        self.assertIn("RuntimeError", rec["why"])

    def test_an_unmeasured_attribution_is_tried_once_more_with_a_new_seed(self):
        """Audit 0007 C1 K2: a failed call is retried once (seed 8); a second failure stays unknown, measured false."""
        class Flaky(Canned):
            def call(self, role, prompt, max_tokens=2000, seed=7, **k):
                self.calls.append((role, seed))
                if seed == 7:
                    raise RuntimeError("down")
                return Reply(self.text)
        r = Flaky(json.dumps(verdict("Jeff Booth", "When I wrote The Price of Tomorrow")))
        pk = {"segments": [dict(self.seg)]}
        SP.attribute_package(r, pk, {"vidA": source(SENTS)}, meta_for=lambda v: META, log=lambda s: None)
        self.assertEqual([c[1] for c in r.calls], [7, 8])
        self.assertEqual((pk["segments"][0]["speaker"]["name"], pk["segments"][0]["speaker"]["measured"]),
                         ("Jeff Booth", True))

    def test_no_source_lines_or_no_word_record_is_unknown_with_why(self):
        r = Canned("{}")
        self.assertEqual(SP.attribute(r, self.seg, source(SENTS), {})["why"],
                         "the source's title, channel and description are not in the store")
        self.assertEqual(SP.attribute(r, self.seg, None, META)["why"], "no word record for the clip's context")
        self.assertEqual(r.calls, [])                                # nothing to ask: no call is paid


class TestPinCarriesTheSpeaker(unittest.TestCase):
    def pk(self, sp):
        g = {k: {"status": "PASS", "replayed": False} for k in package_pin.REQUIRED_GATES}
        return {"schema": "pp.package/1", "type": "moments", "title": "T", "caption": "C", "hook_first_words": "Bitcoin is",
                "runtime_s_estimate": 62.0, "vo_kind": "written", "gates": g,
                "vo": {"intro": "I", "bridges": ["B"], "bridges_after_clip": [1], "signoff": "S"},
                "lines": [{"slot": "intro", "text": "I"}, {"slot": "bridge_1", "text": "B"},
                          {"slot": "title", "text": "T"}, {"slot": "caption", "text": "C"}],
                "segments": [{"video_id": v, "channel": "ch", "start": 1.0, "end": 9.0, "text": f"Bitcoin is {v}.",
                              "transcript_sha256": "t", "url_30s_before": "u", "time_sensitive": False,
                              "source_published_at": "2026-11-12T01:00:00Z", **({"speaker": sp} if sp else {})}
                             for v in ("aaaaaaaaaaa", "bbbbbbbbbbb")]}

    def test_the_pin_refuses_a_segment_without_a_speaker_record_or_a_named_one_without_evidence(self):
        jeff = {"name": "Jeff Booth", "role": "guest", "line": "Jeff Booth joins me"}
        named = {"name": "Jeff Booth", "role": "guest", "line": "Jeff Booth joins me", "basis": "When I wrote it",
                 "why": "", "people": [jeff], "measured": True}
        for sp in (None, {"name": ""}, {"name": "unknown", "people": []}, dict(named, basis=""), dict(named, line=None),
                   dict(named, people=[]),                                   # C1 K1: a name nobody in people holds
                   dict(named, line="Jeff Booth wrote a book"),               # not that person's line
                   dict(named, role="host"),                                  # not that person's role
                   dict(named, people=[dict(jeff, role="speaker")]),          # a role outside host / guest / other
                   dict(named, measured=False)):                              # C2 glm N1: a name nobody measured
            with self.assertRaises(package_pin.PinRefused, msg=sp):
                package_pin.to_pin(self.pk(sp), "r")
        pin = package_pin.to_pin(self.pk(named), "r")
        self.assertEqual([s["speaker"]["name"] for s in pin["segments"]], ["Jeff Booth", "Jeff Booth"])

    def test_the_speaker_is_inside_the_seal(self):
        unknown = {"name": "unknown", "role": None, "line": None, "basis": None, "why": "", "people": [],
                   "measured": True}
        pin = package_pin.to_pin(self.pk(unknown), "r")
        mp = pin["moments_package"]
        self.assertEqual(mp["package_sha256"], package_pin.seal(pin["segments"], mp["edl_vo"], mp["signoff_expected"],
                                                                 mp["title"], mp["caption"], mp["gates"]))
        segs = [dict(s, speaker=dict(s["speaker"], name="Jeff Booth")) for s in pin["segments"]]
        self.assertNotEqual(mp["package_sha256"], package_pin.seal(segs, mp["edl_vo"], mp["signoff_expected"],
                                                                    mp["title"], mp["caption"], mp["gates"]))

    def test_every_earlier_pin_still_recomputes_and_a_dropped_later_field_is_caught(self):
        """The integrator's pin check recomputes seals with THIS module (imported from the worktree). A field added
        to the seal later enters the body only when a segment carries its key: every earlier pin keeps its digest,
        and removing a sealed field from a new pin changes it."""
        import glob
        n = 0
        for p in glob.glob(os.path.join(HERE, "proof", "**", "MOMENTS_PIN*.json"), recursive=True):
            with open(p) as f:
                pin = json.load(f)
            mp = pin.get("moments_package") or {}
            if "package_sha256" not in mp:
                continue
            n += 1
            self.assertEqual(package_pin.seal(pin["segments"], mp["edl_vo"], mp.get("signoff_expected"), mp["title"],
                                              mp["caption"], mp["gates"], mp.get("btc_screen")),   # as check_pin_only
                             mp["package_sha256"], p)
        self.assertGreaterEqual(n, 6)                                    # 37c5b5f5, 41f29b1f and the four L-y pins
        unknown = {"name": "unknown", "role": None, "line": None, "basis": None, "why": "", "people": [],
                   "measured": True}
        pin = package_pin.to_pin(self.pk(unknown), "r")
        mp = pin["moments_package"]
        for k in package_pin.SEALED_LATER:
            if not any(k in sg for sg in pin["segments"]):      # a conditional field (the trim, ruling 33 part 2): its
                continue                                          # sealing is tested where a segment carries it
            segs = [{x: v for x, v in sg.items() if x != k} for sg in pin["segments"]]
            self.assertNotEqual(package_pin.seal(segs, mp["edl_vo"], mp["signoff_expected"], mp["title"],
                                                 mp["caption"], mp["gates"]), mp["package_sha256"], k)


if __name__ == "__main__":
    unittest.main()
