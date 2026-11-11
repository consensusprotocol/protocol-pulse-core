#!/usr/bin/env python3
"""Mission 4a / DEC-8 delivery contract: 'HOLD FOR APPROVAL - all gates passed, no waivers' only when every
gate row of both formats is PASS and the automated verification pack is complete; otherwise 'REVIEW ONLY'
with the failing list. Both aspects, real dimensions; safe frames named in the 9:16 caption. No network:
the sender is injected. Run: cd ~/protocol_pulse && python3 -m pytest -q pipeline/test_telegram_delivery.py"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

PIPELINE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PIPELINE)

import telegram as TG  # noqa: E402

ROWS = {"16x9": {"G1_voice": "PASS", "G11_parity(run_gates)": "NOT RUN BY run_gates (no horiz) — see G11 below",
                 "G16_sentence_boundary": "PASS", "G18_word_for_word": "PASS"},
        "9x16": {"G1_voice": "PASS", "G11_parity(run_gates)": "NOT RUN BY run_gates (no horiz) — see G11 below",
                 "G11_parity": "PASS", "G4s_layout_truth": "PASS", "G18_word_for_word": "PASS"}}


class TestDelivery(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.media = tempfile.mkdtemp(prefix="tgm_")
        for name, (w, h) in (("segment.mp4", (1920, 1080)), ("segment_vertical.mp4", (1080, 1920)),
                             ("wrong.mp4", (1280, 720))):
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=black:s={w}x{h}:r=24:d=1",
                            "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
                            os.path.join(cls.media, name)], check=True)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.media, ignore_errors=True)

    def run_dir(self, rows=ROWS, pack_complete=True, flagged=False):
        rd = tempfile.mkdtemp(prefix="tgr_")
        self.addCleanup(shutil.rmtree, rd, True)
        os.makedirs(os.path.join(rd, "out"))
        os.makedirs(os.path.join(rd, "VERIFY"))
        for name in ("segment.mp4", "segment_vertical.mp4"):
            shutil.copy(os.path.join(self.media, name), os.path.join(rd, "out", name))
        json.dump({"rows": rows}, open(os.path.join(rd, "GATE_REPORT.json"), "w"))
        json.dump({"complete": pack_complete}, open(os.path.join(rd, "VERIFY", "VERIFICATION.json"), "w"))
        shot = {"start": 0.0, "end": 9.4, "class": "screen" if flagged else "single", "flagged": flagged}
        json.dump({"topic": "Bitcoin price dip",
                   "hook": {"channel": "Yahoo Finance", "vertical_layout": {"shots": [shot], "flagged": flagged}},
                   "clips": [{"index": 1, "channel": "Natalie Brunell",
                              "vertical_layout": {"shots": [dict(shot, **{"class": "single", "flagged": False})],
                                                  "flagged": False}}]},
                  open(os.path.join(rd, "edl.json"), "w"))
        return rd

    def deliver(self, rd, option=None):
        sent = []
        rec = TG.deliver_run(rd, option=option, send=lambda kind, path, fields: sent.append(
            (kind, os.path.basename(path), fields)) or len(sent))
        return rec, sent

    def test_all_pass_with_complete_pack_is_hold_for_approval_in_both_aspects(self):
        rd = self.run_dir()
        rec, sent = self.deliver(rd)
        vids = [s for s in sent if s[0] == "video"]
        self.assertEqual([(s[1], s[2]["width"], s[2]["height"]) for s in vids],
                         [("segment.mp4", 1920, 1080), ("segment_vertical.mp4", 1080, 1920)])
        for s in vids:
            self.assertTrue(s[2]["caption"].startswith(TG.HOLD_OK), s[2]["caption"])
            self.assertNotIn("Failing", s[2]["caption"])
        written = json.load(open(os.path.join(rd, "TELEGRAM_DELIVERY.json")))
        self.assertEqual([m["format"] for m in written["messages"] if "format" in m], ["16x9", "9x16"])

    def test_any_failing_row_is_review_only_with_the_list(self):
        rows = json.loads(json.dumps(ROWS))
        rows["9x16"]["G4s_layout_truth"] = "FAIL"
        _, sent = self.deliver(self.run_dir(rows))
        cap = sent[0][2]["caption"]
        self.assertTrue(cap.startswith("REVIEW ONLY - 1 failing"), cap)
        self.assertIn("G4s_layout_truth (9x16): FAIL", cap)

    def test_a_waiver_is_not_a_pass(self):
        rows = json.loads(json.dumps(ROWS))
        rows["16x9"]["G8_sharpness"] = "FLAG/LIMITED (absolute floor vs soft source)"
        _, sent = self.deliver(self.run_dir(rows))
        self.assertTrue(sent[0][2]["caption"].startswith("REVIEW ONLY"), sent[0][2]["caption"])
        self.assertIn("G8_sharpness (16x9): FLAG/LIMITED", sent[0][2]["caption"])

    def test_incomplete_verification_pack_is_review_only(self):
        _, sent = self.deliver(self.run_dir(pack_complete=False))
        self.assertIn("verification pack missing or incomplete", sent[0][2]["caption"])
        self.assertTrue(sent[0][2]["caption"].startswith("REVIEW ONLY"))

    def test_safe_frame_is_named_in_the_vertical_caption(self):
        _, sent = self.deliver(self.run_dir(flagged=True))
        vert = [s for s in sent if s[1] == "segment_vertical.mp4"][0][2]["caption"]
        self.assertIn("9:16 SAFE FRAME hook (Yahoo Finance): layout=screen 0.00-9.40 s", vert)

    def test_option_label_comes_first(self):
        _, sent = self.deliver(self.run_dir(), option="B")
        self.assertTrue(sent[0][2]["caption"].startswith("OPTION B (transition choice"), sent[0][2]["caption"])

    def test_one_contact_sheet_per_format_with_the_main_drop_only(self):
        from PIL import Image
        rd = self.run_dir()
        os.makedirs(os.path.join(rd, "qa"), exist_ok=True)
        Image.new("RGB", (1920, 2600)).save(os.path.join(rd, "qa", "contact_sheet_16x9.jpg"))
        Image.new("RGB", (6000, 4500)).save(os.path.join(rd, "qa", "contact_sheet_9x16.jpg"))   # too big for a photo
        _, sent = self.deliver(rd)
        self.assertEqual([(s[0], s[1]) for s in sent if s[0] not in ("video", "message")],
                         [("photo", "contact_sheet_16x9.jpg"), ("document", "contact_sheet_9x16.jpg")])
        sent2 = []
        TG.deliver_run(rd, option="A", sheets=False, send=lambda k, p, f: sent2.append(k) or 1)
        self.assertEqual(sent2, ["video", "video"])

    def test_the_release_drop_ends_with_the_publishing_kit(self):
        # orchestrator 2026-11-11 15:30: a suggested title, a description crediting and linking every source,
        # and the first-comment line "credits:" + every creator's @handle, a line break, the orange heart alone
        rd = self.run_dir()
        _, sent = self.deliver(rd)
        self.assertEqual(sent[-1][0], "message")
        kit = sent[-1][2]["text"]
        self.assertIn("SUGGESTED TITLE: Bitcoin price dip", kit)
        self.assertIn("- Yahoo Finance @YahooFinance: https://www.youtube.com/@YahooFinance", kit)
        self.assertIn("- Natalie Brunell @nataliebrunell: https://www.youtube.com/@nataliebrunell", kit)
        self.assertTrue(kit.endswith("credits: @YahooFinance @nataliebrunell\n\U0001F9E1"), kit[-80:])
        _, sent_opt = self.deliver(rd, option="B")
        self.assertNotIn("message", [s[0] for s in sent_opt])         # transition options carry no kit

    def test_the_caption_carries_the_duration(self):
        rd = self.run_dir()
        _, sent = self.deliver(rd)
        self.assertIn(" s", sent[0][2]["caption"].split("\n")[1])

    def test_photo_limits_at_their_boundaries(self):
        """Audit M1: size (PHOTO_MAX_BYTES), width + height (10000) and aspect ratio (20) boundaries."""
        from unittest import mock
        from PIL import Image
        tmp = tempfile.mkdtemp(prefix="photo_")
        self.addCleanup(shutil.rmtree, tmp, True)

        def img(w, h):
            p = os.path.join(tmp, f"{w}x{h}.jpg")
            Image.new("RGB", (w, h)).save(p)
            return p
        self.assertTrue(TG._photo_ok(img(5000, 5000)))                      # w + h == 10000
        self.assertFalse(TG._photo_ok(img(5000, 5001)))
        self.assertTrue(TG._photo_ok(img(4000, 200)))                       # ratio == 20
        self.assertFalse(TG._photo_ok(img(4001, 200)))
        p = img(100, 100)
        with mock.patch("os.path.getsize", return_value=TG.PHOTO_MAX_BYTES):
            self.assertTrue(TG._photo_ok(p))
        with mock.patch("os.path.getsize", return_value=TG.PHOTO_MAX_BYTES + 1):
            self.assertFalse(TG._photo_ok(p))
        bad = os.path.join(tmp, "truncated.jpg")
        open(bad, "wb").write(b"\xff\xd8\xff")                          # not an image: document, not a crash
        self.assertFalse(TG._photo_ok(bad))

    def test_wrong_dimensions_stop(self):
        rd = self.run_dir()
        shutil.copy(os.path.join(self.media, "wrong.mp4"), os.path.join(rd, "out", "segment.mp4"))
        with self.assertRaises(RuntimeError):
            self.deliver(rd)


if __name__ == "__main__":
    unittest.main()
