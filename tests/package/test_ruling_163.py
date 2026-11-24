#!/usr/bin/env python3
"""RULING 163 (2)(a)(b) (orchestrator 08:22 ET Nov 24), THE BUILDER'S HALF: "when the lock replaces ANY word of the
transcript with the audio's reading, material or not: (a) it is always written on the pin ('transcript corrected from
the audio: X -> Y'); (b) every verdict made on that clip's old text (step A, context, fidelity of our lines, value) is
RE-MADE on the corrected text before sealing: a verdict on words the clip does not say is not a verdict."

(a) lock_precheck.corrected_words / apply: every adopted segment carries "transcript_corrected" (sealed,
    package_pin.SEALED_LATER). (b) package.heard / _build's rejudge_heard: right after the lock pre-check, a corrected
clip takes its new words under an id of its own and is judged again (step A on both families, the OUT edge, the
exclusion screen, the second pass, vision, the hook's rating, the clips-alone verdict); the writes, the context checks
(context_integrity._window_text reads its "heard" words), fidelity and value then read its segment's words. A spotlight
whose words the lock corrects is not made this build (fail closed: its verdicts are never made again in place).
The case: Scott Melker f47662e4 (DVKuBD7WB6Y, 1549.7-1564.3 s), the transcript's "FDX" the lock adopted as "FTX" under
ruling 143 (Nov 23; the verifier's row 19 drill)."""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
for _p in ("pipeline", "tests/package", "tests/eligibility", "tests/moments"):
    sys.path.insert(0, os.path.join(REPO, _p))
import attest as AT  # noqa: E402
import context_integrity as CI  # noqa: E402
import eligibility as E  # noqa: E402
import lock_precheck as LP  # noqa: E402
import moments as M  # noqa: E402
import package as PK  # noqa: E402
import package_pin  # noqa: E402
import providers as P  # noqa: E402
import test_medley as TM  # noqa: E402
from test_eligibility import NOW, REG, source  # noqa: E402
from test_moments import pm  # noqa: E402

MELKER = ("I don't know if you guys realize this, but when Bitcoin hit 55,000 overnight on Saturday was four years to "
          "the day of the low of the last Bitcoin bear market for FDX. to the exact day.")       # f47662e48ecb4dc31582
HEARD_FTX = MELKER.replace("FDX", "FTX")
CTX = E.Context(NOW, REG)


def melker_lock(spoken=HEARD_FTX, calls=None):
    """The render's lock pre-check as it answered f47662e4 on Nov 23 (ruling 143: the two audio readings agree on
    'FTX'): x adopted, every other clip passing."""
    def check(segs):
        if calls is not None:
            calls.append([m["moment_id"] for m in segs])
        rows = []
        for m, s in zip(segs, LP.segments_of(segs)):
            if m["moment_id"] == "x":
                rows.append(dict(s, verdict="adopt", outcome="adopt_spoken", why="ruling 143", spoken_text=spoken,
                                 adoption=AT.RULE_143, entry={"request_id": "r", "outcome": "adopt_spoken"},
                                 differences=[{"approved": "fdx", "spoken": "ftx", "took": "run", "material": True,
                                               "class": "ruling 143: the two audio readings agree"}]))
            else:
                rows.append(dict(s, verdict="pass", outcome="no_difference", why="",
                                 entry={"request_id": "r", "outcome": "no_difference"}))
        return {"ok": True, "request_id": "r", "segments": rows, "error": None}
    return check


def rig(n=1, **kw):
    ms = [pm("h", "A", 12.0), dict(pm("x", "B", 14.0), text=MELKER), pm("y", "C", 13.0), pm("z", "D", 14.0)]
    return TM.Rig(ms, ["h", "x", "y", "z"], [(True, [], None, TM.Rig.LINE)] * n, [None] * n, **kw)


class TestTheWords(unittest.TestCase):
    def test_every_changed_word_material_or_not(self):
        self.assertEqual(LP.corrected_words(MELKER, HEARD_FTX), "fdx -> ftx")
        self.assertEqual(LP.corrected_words("it was a good day", "it was the good day"), "a -> the")
        self.assertEqual(LP.corrected_words("it was a good day", "it was a very good day"), "(nothing) -> very")
        self.assertEqual(LP.corrected_words("it was a good day", "it was good day"), "a -> (nothing)")
        self.assertIsNone(LP.corrected_words(MELKER, MELKER))

    def test_the_clip_on_its_heard_words_keeps_no_verdict_of_the_old_ones(self):
        m = dict(pm("x", "B", 14.0), text=MELKER, visual={"measured": True}, step_a_flags=["REFERENT_OUTSIDE"],
                 hook_rating={"rating": 5}, out_edge={"complete": True}, hook_onset={"pass": True})
        row = {"verdict": "adopt", "approved_text": MELKER, "spoken_text": HEARD_FTX}
        cm = PK.heard(m, row)
        self.assertEqual((cm["moment_id"], cm["text"]), ("x" + PK.HEARD, HEARD_FTX))
        self.assertEqual(cm["heard"], {"from": "x", "text": HEARD_FTX, "was": MELKER, "corrected": "fdx -> ftx"})
        for k in ("visual", "step_a_flags", "hook_rating", "out_edge"):
            self.assertNotIn(k, cm)                                      # made again on the corrected words
        self.assertEqual(cm["hook_onset"], {"pass": True})               # the audio's own measure stays
        self.assertEqual(m["text"], MELKER)                              # the pool's moment is untouched
        for bad in (dict(row, verdict="pass"), dict(row, approved_text="another text"), dict(row, spoken_text=MELKER),
                    None, dict(row, spoken_text=None)):
            self.assertIsNone(PK.heard(m, bad), bad)


class TestTheContextReadsTheHeardWords(unittest.TestCase):
    """Step A and the context checks build each clip's words from the SOURCE's tokens (the transcript): a corrected
    clip's "heard" words stand in the <selected> marks instead."""

    def setUp(self):
        self.src = source(["Here is what happened this weekend.", MELKER, "Nobody saw it coming."], vid="DVKuBD7WB6Y")
        sp = E.Span(self.src, 1, 1)
        self.m = M.record(sp, {"scores": {k: 3 for k in M.AXES}, "names_person": False, "risk": [],
                               "topics": ["bitcoin"], "reason": "r"}, CTX, M.judge(sp, CTX), {})
        self.m["source_key"] = "DVKuBD7WB6Y"
        self.m["rank_score"] = M.rank_score(self.m)

    def test_the_window_shows_what_the_clip_says(self):
        k0, k1, (w0, w1) = self.m["sentences"][0], self.m["sentences"][1], self.m["words"]
        said = self.m["text"].replace("FDX", "FTX")                     # the source splits "... FDX." from "to the
        old, _ = CI._window_text(self.src, k0, k1, w0, w1)               # exact day.": the clip is its first part
        new, _ = CI._window_text(self.src, k0, k1, w0, w1, selected=said)
        self.assertIn("for FDX.</selected>", old)
        self.assertNotIn("FDX", new)
        self.assertIn("for FTX.</selected> to the exact day.", new)
        self.assertIn("Here is what happened this weekend.", new)      # the context around it unchanged
        seg = {"label": "clip_01", "k0": k0, "k1": k1, "words": [w0, w1], "channel": "Scott Melker",
               "video_id": "DVKuBD7WB6Y", "source_key": "DVKuBD7WB6Y",
               "heard": {"text": said}}
        got = CI.contexts_from_sources({"segments": [seg]}, {"DVKuBD7WB6Y": self.src}, NOW)
        self.assertIn("FTX", got["clip_01"]["text"])
        self.assertNotIn("FDX", got["clip_01"]["text"])

    def test_step_a_is_asked_on_the_heard_words_under_a_key_of_its_own(self):
        cm = PK.heard(self.m, {"verdict": "adopt", "approved_text": self.m["text"],
                               "spoken_text": self.m["text"].replace("FDX", "FTX")})
        seen = []

        class R:
            backends, down = {}, set()

            def call(self, role, prompt, *a, **k):
                seen.append(prompt)
                raise P.ProviderError("recorded the prompt only")
        PK.prescreen(R(), [cm], {"DVKuBD7WB6Y": self.src}, CTX, set(), set(), n=1, log=lambda s: None)
        self.assertTrue(seen)
        self.assertIn("bear market for FTX.</selected> to the exact day.", seen[0])
        self.assertNotIn("FDX", seen[0])
        ctx_ = {"text": "w", "title": "", "channel": "c", "window": None, "published": "", "show_date": "d"}
        self.assertNotEqual(PK.step_a_key(cm, ctx_), PK.step_a_key(self.m, ctx_))   # never the old text's verdict


class TestTheBuild(unittest.TestCase):
    def test_the_melker_clip_is_judged_again_on_ftx_and_the_pin_says_so(self):
        calls = []
        r = rig(lock_check=melker_lock(calls=calls))
        out = r.run()
        pk = out["package"]
        self.assertIsNotNone(pk, out.get("why_none"))
        x = next(sg for sg in pk["segments"] if sg["moment_id"].startswith("x"))
        self.assertEqual((x["moment_id"], x["text"], x["heard"]["corrected"]), ("x" + PK.HEARD, HEARD_FTX, "fdx -> ftx"))
        heard_screens = [name for name, ids in r.screens if "x" + PK.HEARD in ids]
        self.assertEqual(len(heard_screens), 2)                           # step A again: the first family, the second
        self.assertNotEqual(heard_screens[0], heard_screens[1])
        self.assertIn("x" + PK.HEARD, r.visual_calls)                      # vision on its words (ruling 70)
        self.assertEqual(r.medley_calls[-1][1], "x" + PK.HEARD)            # the clips-alone verdict again
        for texts in r.write_texts:                                        # the writer, fidelity, context and value
            self.assertIn(HEARD_FTX, texts)                                # read what the clip says, never "FDX"
        for segs in r.paid_seen:
            self.assertEqual([sg["text"] for sg in segs if sg["moment_id"].startswith("x")], [HEARD_FTX])
            self.assertEqual([sg.get("heard", {}).get("text") for sg in segs if sg["moment_id"].startswith("x")],
                             [HEARD_FTX])
        for v in r.value_calls:
            self.assertIn(HEARD_FTX, v["texts"])
        self.assertNotIn(MELKER, sum(r.write_texts, []) + sum((v["texts"] for v in r.value_calls), []))
        pin = package_pin.to_pin(TM.spk(pk), "test")
        seg = next(sg for sg in pin["segments"] if sg["video_id"] == x["video_id"])
        self.assertEqual((seg["approved_text"], seg["transcript_corrected"]), (HEARD_FTX, "fdx -> ftx"))
        self.assertEqual(seg["attested"]["was"], MELKER)
        self.assertIn("RULING 163 (2)(b)", seg["attested"]["rejudged"])
        mp = pin["moments_package"]
        self.assertEqual(package_pin.seal(pin["segments"], mp["edl_vo"], mp["signoff_expected"], mp["title"],
                                          mp["caption"], mp["gates"], mp.get("btc_screen")), mp["package_sha256"])
        bare = [{k: v for k, v in sg.items() if k != "transcript_corrected"} for sg in pin["segments"]]
        self.assertNotEqual(package_pin.seal(bare, mp["edl_vo"], mp["signoff_expected"], mp["title"], mp["caption"],
                                             mp["gates"], mp.get("btc_screen")), mp["package_sha256"])   # sealed
        self.assertEqual(LP.pin_problems(pk), [])

    def test_a_function_word_the_lock_adopts_is_judged_again_and_written_too(self):
        said = "Bitcoin was the good bet for anyone who waited out the whole drop."
        ms = [pm("h", "A", 12.0), dict(pm("x", "B", 14.0), text=said.replace("the good bet", "a good bet")),
              pm("y", "C", 13.0), pm("z", "D", 14.0)]
        r = TM.Rig(ms, ["h", "x", "y", "z"], [(True, [], None, TM.Rig.LINE)], [None],
                   lock_check=TM.lock_stub({"x": ("adopt_spoken", said)}))
        out = r.run()
        pk = out["package"]
        self.assertIsNotNone(pk, out.get("why_none"))
        self.assertIn("x" + PK.HEARD, sum((ids for _, ids in r.screens), []))
        pin = package_pin.to_pin(TM.spk(pk), "test")
        self.assertIn("a -> the", [sg.get("transcript_corrected") for sg in pin["segments"]])

    def test_a_hard_step_a_on_the_heard_words_puts_the_clip_out_under_both_ids(self):
        calls = []
        r = rig(n=2, lock_check=melker_lock(calls=calls), a_fail={("xai", "x" + PK.HEARD): ["SPEAKER_CHANGE"]})
        out = r.run()
        pk = out["package"]
        ids = [sg["moment_id"] for sg in (pk or {}).get("segments") or []]
        self.assertFalse([i for i in ids if i.startswith("x")])              # never on either id
        tried = [t for t in out.get("tried") or [] if t.get("heard")]
        self.assertTrue(tried)
        self.assertIn("SPEAKER_CHANGE", tried[0]["heard"]["x"]["out"])
        self.assertIn("ruling 163 (2)(b)", tried[0]["why"])
        self.assertTrue(len(calls) >= 2, calls)                             # out for good under BOTH ids: no later
        self.assertFalse([ids for ids in calls[1:] if "x" in ids or "x" + PK.HEARD in ids], calls)   # line-up

    def test_no_correction_nothing_is_asked_again_and_no_field_is_sealed(self):
        r = rig(lock_check=TM.lock_stub())
        out = r.run()
        pk = out["package"]
        self.assertIsNotNone(pk, out.get("why_none"))
        self.assertFalse([1 for _, ids in r.screens if any(PK.HEARD in i for i in ids)])
        pin = package_pin.to_pin(TM.spk(pk), "test")
        self.assertFalse([sg for sg in pin["segments"] if "transcript_corrected" in sg or "attested" in sg])


class TestEveryPathAndCheck(unittest.TestCase):
    def test_the_no_voice_path_asks_the_lock_on_the_transcript_s_words_and_judges_again(self):
        """Ruling 91's no-voice line-up has its own lock pre-check: it is asked with x on the transcript's words (a lock
        asked on words it corrected itself finds no difference, and the record would be lost), adopts again, and x is
        judged again: the no-voice pin carries the correction too."""
        calls = []
        ms = [pm("h", "A", 16.0), dict(pm("x", "B", 16.0), text=MELKER), pm("y", "C", 16.0)]
        r = TM.Rig(ms, ["h", "x", "y"], [(True, [], None, TM.Rig.LINE)], [None], lock_check=melker_lock(calls=calls),
                   values=[{"adds": "no", "why": "it restates clip_02"}])
        out = r.run()
        pk = out["package"]
        self.assertIsNotNone(pk, out.get("why_none"))
        self.assertIn("ruling 91", pk["no_voice"]["why"])
        self.assertEqual(calls, [["h", "x", "y"], ["h", "x", "y"]])         # both pre-checks on the transcript's words
        x = next(sg for sg in pk["segments"] if sg["moment_id"].startswith("x"))
        self.assertEqual((x["moment_id"], x["heard"]["text"]), ("x" + PK.HEARD, HEARD_FTX))   # judged again there too
        pin = package_pin.to_pin(TM.spk(pk), "test")
        seg = next(sg for sg in pin["segments"] if sg["video_id"] == x["video_id"])
        self.assertEqual((seg["transcript_corrected"], seg["approved_text"]), ("fdx -> ftx", HEARD_FTX))
        self.assertIn("rejudged", seg["attested"])

    def test_a_line_up_re_formed_with_a_corrected_clip_asks_the_lock_on_the_transcript_s_words(self):
        """A re-screen after the write fails y (the rig's third vendor): the line-up is re-formed by a swap that keeps
        x on its corrected words; its new lock pre-check is asked with x on the transcript's words, adopts again, and
        the pin keeps the correction (a lock asked on FTX itself would find no difference: the record lost)."""
        calls = []
        ms = [pm("h", "A", 12.0), dict(pm("x", "B", 14.0), text=MELKER), pm("y", "C", 13.0), pm("z", "D", 14.0)]
        r = TM.Rig(ms, ["h", "x", "y", "z"], [(True, [], None, TM.Rig.LINE)] * 2, [None] * 2,
                   angle_from=("xai:grok", "xai", "grok"), a_fail={("openai", "y"): ["REFERENT_OUTSIDE"]},
                   lock_check=melker_lock(calls=calls))
        out = r.run()
        pk = out["package"]
        self.assertIsNotNone(pk, out.get("why_none"))
        self.assertEqual([sg["moment_id"] for sg in pk["segments"]], ["h", "x" + PK.HEARD, "z"])
        self.assertEqual(calls, [["h", "x", "y"], ["h", "x", "z"]])
        pin = package_pin.to_pin(TM.spk(pk), "test")
        self.assertIn("fdx -> ftx", [sg.get("transcript_corrected") for sg in pin["segments"]])

    def test_a_corrected_hook_is_rated_again_on_its_words(self):
        said = "Bitcoin h the x."                                         # one function word more: ruling 84's class
        r = rig(lock_check=TM.lock_stub({"h": ("adopt_spoken", said)}))
        out = r.run()
        pk = out["package"]
        self.assertIsNotNone(pk, out.get("why_none"))
        self.assertEqual(pk["segments"][0]["moment_id"], "h" + PK.HEARD)
        self.assertIn(["h" + PK.HEARD], r.hook_calls)                     # its own rating on the bar, again
        self.assertEqual(pk["segments"][0]["text"], said)

    def test_the_out_edge_and_the_exclusion_screen_judge_the_heard_words(self):
        for kw in ({"excluded": {"x" + PK.HEARD}}, {}):
            r = rig(n=2, lock_check=melker_lock(), **kw)
            if not kw:
                r.out_edge_refused = {"x" + PK.HEARD}                     # RULING 162 (1) on the corrected words
            out = r.run()
            ids = [sg["moment_id"] for sg in (out["package"] or {}).get("segments") or []]
            self.assertFalse([i for i in ids if i.startswith("x")], kw)
            heard_ = [t["heard"]["x"]["out"] for t in out.get("tried") or [] if t.get("heard")]
            self.assertTrue(heard_, kw)
            self.assertIn("exclusion" if kw else "OUT edge", heard_[0])


class TestApply(unittest.TestCase):
    def rows(self, spoken=HEARD_FTX):
        seg = {"video_id": "DVKuBD7WB6Y", "start": 1549.673, "end": 1564.313}
        row = dict(seg, approved_text=MELKER, verdict="adopt", outcome="adopt_spoken", spoken_text=spoken,
                   adoption=AT.RULE_143, entry={"request_id": "r"}, differences=[])
        return seg, {"ok": True, "request_id": "r", "segments": [row]}

    def test_a_segment_on_the_heard_words_seals_with_its_record(self):
        seg, pre = self.rows()
        pk = LP.apply({"segments": [dict(seg, text=HEARD_FTX)], "lines": []}, pre)
        s = pk["segments"][0]
        self.assertEqual((s["text"], s["transcript_corrected"], s["attested"]["was"]), (HEARD_FTX, "fdx -> ftx", MELKER))
        self.assertIn("rejudged", s["attested"])
        old = LP.apply({"segments": [dict(seg, text=MELKER)], "lines": []}, pre)["segments"][0]   # the old path:
        self.assertEqual((old["text"], old["transcript_corrected"]), (HEARD_FTX, "fdx -> ftx"))   # written too,
        self.assertNotIn("rejudged", old["attested"])                                              # never "rejudged"
        with self.assertRaises(ValueError):                                                       # a third text
            LP.apply({"segments": [dict(seg, text=MELKER.replace("FDX", "FTC"))], "lines": []}, pre)


class TestTheSpotlight(unittest.TestCase):
    def test_a_spotlight_whose_words_the_lock_corrects_is_not_made(self):
        import test_spotlight as TS
        ms = [TS.moment(mid="b", channel="B")]
        adopted = lambda segs: {"ok": True, "request_id": "r", "segments": [dict(
            TS.pre_of(segs[0])["segments"][0], verdict="adopt", outcome="adopt_spoken",
            spoken_text=segs[0]["text"].replace("money", "asset"), adoption=AT.RULE_143, differences=[],
            entry={"request_id": "r"})]}
        out, calls = TS.TestBuild().run_build(ms, {"b": 4}, lock=adopted)
        self.assertNotIn("package_for", calls)
        self.assertIsNone(out["package"])
        self.assertIn("ruling 163 (2)(b)", out["moments"]["b"]["out"])
        out, calls = TS.TestBuild().run_build(ms, {"b": 4})                  # no correction: as before
        self.assertEqual(calls["package_for"], ["b"])


if __name__ == "__main__":
    unittest.main()
