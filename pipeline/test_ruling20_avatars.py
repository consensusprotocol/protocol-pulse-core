#!/usr/bin/env python3
"""Ruling 20 (orchestrator 2026-11-12 '11:28'): a channel's registered avatar may be its own monogram / logo
(pipeline/channels.json avatar_kind + avatar_text); V1's question then states it and asks whether the ring is round,
undistorted and shows THAT monogram. Fixture: the Nov 12 render's full-resolution 16:9 credits frame (Saifedean
Ammous's 'SA' monogram in the first ring), edited in its first ring.
must-pass  the untouched 'SA' monogram (both vision models 'yes')
must-fail  a thumbnail with headline text in that ring; a different monogram ('XY'); the ring squashed to an ellipse
           (V1 fails on any model's 'no'). Roundness stays measured by the ring mask too (credit_rings, DEC-11).
The vision panel is remote (Heimdall): the class is skipped when the route is not configured.
Run: cd ~/protocol_pulse && python3 -m pytest -q pipeline/test_ruling20_avatars.py"""
import json
import os
import shutil
import sys
import tempfile
import unittest

PIPELINE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(PIPELINE)
sys.path.insert(0, PIPELINE)
import credit_rings as CR  # noqa: E402
import verify_pack as VP  # noqa: E402
import visual_check as VC  # noqa: E402

FRAME = os.path.join(REPO, "runs", "pinned_20261112_135315", "VERIFY", "credits_16x9_1.jpg")
CHANNELS = ["Saifedean Ammous", "What Bitcoin Did", "Natalie Brunell"]


class TestAvatarNote(unittest.TestCase):
    def test_the_registry_marks_saifedean_and_the_note_states_it(self):
        reg = json.load(open(os.path.join(PIPELINE, "channels.json")))
        saif = next(e for e in reg if e["display_name"] == "Saifedean Ammous")
        self.assertEqual((saif["avatar_kind"], saif["avatar_text"]), ("monogram", "SA"))
        self.assertIn("Saifedean Ammous: its registered avatar is its own monogram showing 'SA'", VP.avatar_note(CHANNELS))
        self.assertEqual(VP.avatar_note(["What Bitcoin Did", "Natalie Brunell"]), "")      # photos: nothing stated
        self.assertIn("Exception (ruling 20)", dict(VC.CHECKLIST)["credits_round_and_match"])


def _route():
    try:
        VC._key()
        return True
    except Exception:
        return False


@unittest.skipUnless(os.path.exists(FRAME) and _route(), "Nov 12 credits frame or the vision route not available")
class TestRuling20Panel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PIL import Image, ImageDraw, ImageFont
        cls.tmp = tempfile.mkdtemp(prefix="r20_")
        img = Image.open(FRAME).convert("RGB")
        lay = CR.card_layout(img.width, img.height, 3)
        (cx, cy), r = lay["positions"][0], lay["ring_r"] - 8
        box = (cx - r, cy - r, cx + r, cy + r)
        mask = Image.new("L", (2 * r, 2 * r), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, 2 * r - 1, 2 * r - 1), fill=255)
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
            big = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 120)
        except OSError:
            font = big = ImageFont.load_default()
        cls.cases = {"pass": FRAME}
        thumb = Image.new("RGB", (2 * r, 2 * r), (30, 30, 60))           # a video thumbnail with headline text
        d = ImageDraw.Draw(thumb)
        d.rectangle((0, 0, 2 * r, 2 * r), fill=(200, 30, 30))
        d.text((12, 70), "BITCOIN", fill="yellow", font=font)
        d.text((12, 130), "CRASH!", fill="white", font=font)
        t = img.copy(); t.paste(thumb, box[:2], mask)
        cls.cases["thumbnail"] = os.path.join(cls.tmp, "thumbnail.jpg"); t.save(cls.cases["thumbnail"], quality=92)
        mono = Image.new("RGB", (2 * r, 2 * r), "white")                # a different monogram
        ImageDraw.Draw(mono).text((22, 50), "XY", fill=(232, 120, 40), font=big)
        m = img.copy(); m.paste(mono, box[:2], mask)
        cls.cases["wrong_monogram"] = os.path.join(cls.tmp, "wrong_monogram.jpg"); m.save(cls.cases["wrong_monogram"], quality=92)
        R = lay["outer_d"] // 2 + 4                                     # the ring and its avatar squashed to 55 %
        reg = img.crop((cx - R, cy - R, cx + R, cy + R))
        bg = img.getpixel((cx - R - 20, cy))
        q = img.copy(); ImageDraw.Draw(q).rectangle((cx - R, cy - R, cx + R, cy + R), fill=bg)
        sq = reg.resize((int(2 * R * 0.55), 2 * R))
        q.paste(sq, (cx - sq.width // 2, cy - R))
        cls.cases["squashed"] = os.path.join(cls.tmp, "squashed.jpg"); q.save(cls.cases["squashed"], quality=92)
        note = ("Channels whose clips appear in this video (from the edit decision list): Saifedean Ammous (hook), "
                "What Bitcoin Did (clip_01), Natalie Brunell (clip_02)." + VP.avatar_note(CHANNELS))
        cls.answers = {}
        for name, path in cls.cases.items():
            per = {m: VC.ask_vision(path, "16x9", "", model=m, channels_note=note)[0] for m in VC.VISION_MODELS}
            cls.answers[name] = {m: str(((a or {}).get("credits_round_and_match") or {}).get("answer") or "missing")
                                 .strip().lower() for m, a in per.items()}
        print("ruling 20 panel answers:", json.dumps(cls.answers))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_the_registered_monogram_passes(self):
        self.assertTrue(all(a == "yes" for a in self.answers["pass"].values()), self.answers["pass"])

    def test_a_thumbnail_a_wrong_monogram_and_a_squashed_ring_fail(self):
        for case in ("thumbnail", "wrong_monogram", "squashed"):
            self.assertTrue(any(a != "yes" for a in self.answers[case].values()), (case, self.answers[case]))


if __name__ == "__main__":
    unittest.main()
