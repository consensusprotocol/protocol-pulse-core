#!/usr/bin/env python3
"""LEAN (1) (the owner's assignment, 13:37 ET Nov 24, issue 1: "pipeline/package.py:4564-4698: line-up coherence is
evaluated before final audio-lock resolution. Corrected speech triggers expensive downstream rejudgment."): with
lean=True (the driver's path) the render's lock is asked for each angle's clips BEFORE its join table and any
clips-alone verdict (package._build's lock_first): a held clip never reaches a judged line-up; a corrected clip is
judged again on its words once, by its own gates; the line-ups are then judged on the final words once, and the
line-up stage's lock answer, already settled, makes nothing be judged again (lock_settled). A lock answer is reused only
for the exact span, transcript text, role, trim and rules / decoder (lock_precheck.answer).

The case: Scott Melker f47662e4's "FDX" the lock adopted as "FTX" (ruling 143, Nov 23), the rig of test_ruling_163;
build 171's own case (8b5ec831, "bitcoins" -> "bitcoiners") went the same way: its clips-alone verdict was made on the
transcript's words, then made again on the corrected words (and refused for money). Offline: every model stubbed."""
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
import lock_precheck as LP  # noqa: E402
import package as PK  # noqa: E402
import package_pin  # noqa: E402
import test_medley as TM  # noqa: E402
import test_ruling_163 as T163  # noqa: E402

X = "x" + PK.HEARD


def rig(lean, lock, n=2, **kw):
    r = T163.rig(n=n, lock_check=lock, **kw)
    r.build_kw = {"lean": lean}
    oe = r.out_edges                                     # the rig's OUT edge: every clip ends a thought (lean (2)'s
    r.out_edges = lambda *a, recover=False, **k: oe(*a, **k)   # recovery is test_lean_out_edge's)
    seq = r.__dict__.setdefault("seq", [])
    med = r.medley

    def medley(router, segs, ctx_, wv, seed=7, writer_family=None):
        seq.append(("medley", [m["moment_id"] for m in segs]))
        return med(router, segs, ctx_, wv, seed, writer_family)
    r.medley = medley
    return r, seq


def logged(check, seq):
    def f(segs):
        seq.append(("lock", [m["moment_id"] for m in segs]))
        return check(segs)
    return f


class TestTheLockSettlesTheWordsFirst(unittest.TestCase):
    def test_a_corrected_clip_is_judged_on_its_words_once_and_its_line_up_once(self):
        """MUST-PASS: the lock is asked before the first clips-alone verdict; x is judged again on "FTX" once (step A
        on both families once), the clips-alone verdict is asked ONCE and on "FTX", the line-up stage's lock answer is
        the one it was judged on (nothing judged again), and the pin seals FTX with the correction named."""
        r, seq = rig(True, None)
        r.lock_check = logged(T163.melker_lock(), seq)
        out = r.run()
        pk = out["package"]
        self.assertIsNotNone(pk, out.get("why_none"))
        kinds = [k for k, _ in seq]
        self.assertEqual(kinds[0], "lock")                               # the lock first
        self.assertEqual(seq[0][1], ["h", "x", "y", "z"])                # the angle's clips, its hook first
        meds = [ids for k, ids in seq if k == "medley"]
        self.assertEqual(len(meds), 1, seq)                              # one clips-alone verdict
        self.assertIn(X, meds[0])                                        # on the corrected words
        self.assertNotIn("x", meds[0])
        heard_screens = [name for name, ids in r.screens if X in ids]
        self.assertEqual(len(heard_screens), 2)                           # step A again: two families, once
        t = out["tried"][0]
        self.assertIn("lock_settled", t)
        self.assertNotIn("heard", t)                                     # rejudge_heard never ran at the line-up
        self.assertEqual(out["lock_first"][0]["corrected"], {"x": X})
        x = next(sg for sg in pk["segments"] if sg["moment_id"].startswith("x"))
        self.assertEqual((x["moment_id"], x["text"]), (X, T163.HEARD_FTX))
        for texts in r.write_texts:                                      # the writer read what the clip says
            self.assertIn(T163.HEARD_FTX, texts)
        self.assertEqual(LP.pin_problems(pk), [])                        # the lock covers the package as it stands
        pin = package_pin.to_pin(TM.spk(pk), "test")
        seg = next(sg for sg in pin["segments"] if sg["video_id"] == x["video_id"])
        self.assertEqual((seg["approved_text"], seg["transcript_corrected"]), (T163.HEARD_FTX, "fdx -> ftx"))

    def test_the_old_path_judges_the_line_up_twice(self):
        """The path as it was (lean=False): the clips-alone verdict on "FDX", the lock after it, then the same verdict
        again on "FTX": the downstream rejudgment issue 1 names."""
        r, seq = rig(False, None)
        r.lock_check = logged(T163.melker_lock(), seq)
        out = r.run()
        self.assertIsNotNone(out["package"], out.get("why_none"))
        meds = [ids for k, ids in seq if k == "medley"]
        self.assertEqual([k for k, _ in seq][:2], ["medley", "lock"])
        self.assertEqual(len(meds), 2)
        self.assertIn("x", meds[0])
        self.assertIn(X, meds[1])

    def test_a_clip_the_lock_holds_never_reaches_a_judged_line_up(self):
        """MUST-FAIL: the render would hold y: under lean it is out before any clips-alone verdict is paid (the old path
        judges a line-up holding it first, then re-lines)."""
        hold = TM.lock_stub({"y": ("hold", None)})
        r, seq = rig(True, None, n=3)
        r.lock_check = logged(hold, seq)
        out = r.run()
        meds = [ids for k, ids in seq if k == "medley"]
        self.assertTrue(meds)
        self.assertFalse([ids for ids in meds if "y" in ids], meds)
        self.assertIn("y", out["lock_first"][0]["held"])
        self.assertNotIn("y", [sg["moment_id"] for sg in (out["package"] or {}).get("segments") or []])
        r, seq = rig(False, None, n=3)                                   # the old path: judged first
        r.lock_check = logged(TM.lock_stub({"y": ("hold", None)}), seq)
        r.run()
        self.assertIn("y", [ids for k, ids in seq if k == "medley"][0])

    def test_a_corrected_clip_failing_its_own_gates_is_out_before_any_line_up(self):
        """MUST-FAIL: x's corrected words fail step A (SPEAKER_CHANGE): out under both ids before any clips-alone
        verdict; no line-up ever holds x or its corrected clip."""
        r, seq = rig(True, None, n=3, a_fail={("xai", X): ["SPEAKER_CHANGE"]})
        r.lock_check = logged(T163.melker_lock(), seq)
        out = r.run()
        self.assertIn("SPEAKER_CHANGE", out["lock_first"][0]["out"]["x"])
        for ids in [ids for k, ids in seq if k == "medley"]:
            self.assertFalse({"x", X} & set(ids), ids)
        ids = [sg["moment_id"] for sg in (out["package"] or {}).get("segments") or []]
        self.assertFalse({"x", X} & set(ids))

    def test_no_verdict_before_coherence_changes_nothing_and_the_line_up_asks_again(self):
        """No answer from the lock before coherence: the clips stay on the transcript's words (nothing is passed on a
        missing verdict); the line-up stage asks again and, with no answer there either, nothing is written."""
        r, seq = rig(True, None)
        r.lock_check = logged(TM.lock_stub(error=True), seq)
        out = r.run()
        self.assertIn("the line-up stage asks again", out["lock_first"][0]["why"])
        self.assertEqual(out["lock_first"][0]["corrected"], {})
        self.assertEqual(out["lock_first"][0]["held"], {})
        self.assertIsNone(out["package"])
        self.assertTrue(out.get("lock_stop"))                            # the line-up stage: no verdict, search stops
        self.assertEqual(r.write_calls, [])


class TestALockAnswerIsReusedOnlyWhenItsKeyIsTheSame(unittest.TestCase):
    """lock_precheck.answer: an answer on file serves a request only for the exact span (to the millisecond), the exact
    transcript text, the role, the trim fields and the current rules (and the decoder, in the file's name)."""

    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.d, True)
        self.seg = {"video_id": "v", "start": 10.0, "end": 20.5, "role": "clip", "approved_text": "the words"}
        e = {"rules": LP.RULES, "window": [10.0, 20.5], "role": "clip", "approved_text": "the words",
             "outcome": "no_difference", "at": "2026-11-24T18:00:00Z", "request_id": "r1"}
        with open(LP.result_file(self.seg, self.d), "w") as f:
            json.dump([e], f)

    def test_the_exact_key_is_served_and_any_other_is_not(self):
        self.assertEqual(LP.answer(self.seg, self.d)["request_id"], "r1")       # MUST-PASS: the same key
        for k, v in (("approved_text", "the word"), ("end", 20.6), ("start", 9.999), ("role", "hook"),
                     ("trimmed_leading", "and")):
            self.assertIsNone(LP.answer(dict(self.seg, **{k: v}), self.d), k)  # MUST-FAIL: any other key
        with open(LP.result_file(self.seg, self.d)) as f:
            e = json.load(f)[0]
        with open(LP.result_file(self.seg, self.d), "w") as f:
            json.dump([dict(e, rules="ruling 17")], f)                          # another rules version
        self.assertIsNone(LP.answer(self.seg, self.d))
        self.assertNotEqual(LP.result_file(self.seg, self.d),                   # another decoder: another file
                            LP.result_file(self.seg, self.d, decoder="0" * 64))


if __name__ == "__main__":
    unittest.main()
