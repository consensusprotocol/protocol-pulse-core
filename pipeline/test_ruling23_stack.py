#!/usr/bin/env python3
"""Ruling 23 (a) (orchestrator 2026-11-12 '13:18'): for a 9:16 segment whose vertical layout is a STACK, V1's centring
question asks whether EACH face is centred in ITS OWN panel and no panel edge cuts through a face; the single-speaker
question applies only to single-speaker layouts. Fixture: the Nov 12 re-run's 9:16 shot frames (clip_02 stack2,
hook single), both Heimdall vision models.
must-pass  the untouched stack2 frame, told it is a stack
must-fail  the stack with its top face pushed into the panel edge; a single-speaker frame shifted off-centre
Run: cd ~/protocol_pulse && python3 -m pytest -q pipeline/test_ruling23_stack.py"""
import json
import os
import shutil
import sys
import tempfile
import unittest

PIPELINE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(PIPELINE)
sys.path.insert(0, PIPELINE)
import verify_pack as VP  # noqa: E402
import visual_check as VC  # noqa: E402

RUN = os.path.join(REPO, "runs", "pinned_20261112_165629")
STACK = os.path.join(RUN, "VERIFY", "shots_9x16", "shot_clip_02_0.jpg")
SINGLE = os.path.join(RUN, "VERIFY", "shots_9x16", "shot_hook_0.jpg")


class TestStackNote(unittest.TestCase):
    @unittest.skipUnless(os.path.exists(os.path.join(RUN, "edl.json")), "the Nov 12 re-run not on this machine")
    def test_the_stack_is_named_and_the_question_carries_the_rule(self):
        note = VP.stack_note(json.load(open(os.path.join(RUN, "edl.json"))))
        self.assertIn("9:16 STACK clip_02 (Natalie Brunell) 0.00-", note)
        self.assertIn("(stack2): two speakers in two panels, one above the other", note)
        self.assertNotIn("centred", note)                               # audit batch39 F2: the layout, not a verdict
        self.assertIn("each face centred in ITS OWN panel", dict(VC.CHECKLIST)["vertical_speaker_centred"])

    def test_no_stack_no_note_and_a_mixed_segment_names_only_its_stacked_span(self):
        self.assertEqual(VP.stack_note({"hook": {"vertical_layout": {"shots": [{"class": "single"}]}}, "clips": []}), "")
        mixed = {"hook": {"channel": "X", "vertical_layout": {"shots": [
            {"class": "single", "start": 0.0, "end": 3.0}, {"class": "stack2", "start": 3.0, "end": 6.5}]}}, "clips": []}
        self.assertEqual(VP.stack_note(mixed).strip(), "9:16 STACK hook (X) 3.00-6.50 s (stack2): two speakers in two "
                                                      "panels, one above the other")   # the single span is not named


def _route():
    try:
        VC._key()
        return True
    except Exception:
        return False


@unittest.skipUnless(os.path.exists(STACK) and os.path.exists(SINGLE) and _route(), "frames or the vision route missing")
class TestStackPanel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PIL import Image
        cls.tmp = tempfile.mkdtemp(prefix="r23_")
        st = Image.open(STACK).convert("RGB")
        w, h = st.size
        cut = st.copy()                                              # the top panel's face pushed into its edge
        top = st.crop((0, 0, w, h // 2))
        cut.paste(top.crop((int(w * 0.42), 0, w, h // 2)), (0, 0))
        cut.paste(top.crop((0, 0, int(w * 0.42), h // 2)), (w - int(w * 0.42), 0))
        cls.cut = os.path.join(cls.tmp, "stack_face_cut.jpg")
        cut.save(cls.cut, quality=92)
        si = Image.open(SINGLE).convert("RGB")
        off = Image.new("RGB", si.size, (0, 0, 0))
        off.paste(si, (int(si.width * 0.38), 0))                     # the single speaker shifted far right
        cls.off = os.path.join(cls.tmp, "single_off_centre.jpg")
        off.save(cls.off, quality=92)
        stack_note = VP.stack_note(json.load(open(os.path.join(RUN, "edl.json"))))   # exactly what verify_pack sends
        cls.ans = {}
        for name, path, note in (("stack", STACK, stack_note), ("stack_cut", cls.cut, stack_note), ("single_off", cls.off, "")):
            cls.ans[name] = {m: str(((VC.ask_vision(path, "9x16", note, model=m)[0] or {}).get("vertical_speaker_centred")
                                     or {}).get("answer") or "missing").strip().lower() for m in VC.VISION_MODELS}
        print("ruling 23 panel answers:", json.dumps(cls.ans))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_the_stack_told_as_a_stack_passes(self):
        self.assertTrue(all(a == "yes" for a in self.ans["stack"].values()), self.ans["stack"])

    def test_a_face_cut_by_the_panel_edge_and_an_off_centre_single_fail(self):
        for case in ("stack_cut", "single_off"):
            self.assertTrue(any(a != "yes" for a in self.ans[case].values()), (case, self.ans[case]))


if __name__ == "__main__":
    unittest.main()
