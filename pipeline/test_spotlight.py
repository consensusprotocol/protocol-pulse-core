#!/usr/bin/env python3
"""Law L-ab SPOTLIGHT (rulings 90 / 91 / 92, orchestrator 2026-11-13 '22:41' / '22:53'), the render side beyond the pin
and the EDL rules (test_pinned.TestSpotlight, test_edl_rules.TestSpotlightRules): G5's 28-50 s window from the EDL's
kind (a medley keeps 58-72 s); the editorial gate's medley laws (LAW 1 post-hook clips, LAW 4 progression) do not bind
one moment while L0 / LAW 2 / LAW 3 still do; the publishing kit carries the builder's first comment VERBATIM with
nothing appended and the pass-path caption names a SPOTLIGHT candidate, a demonstration; the sign-off asks for one clip
from one channel (a medley's prompt is byte-identical); the credits card puts one channel in the middle of both formats.
No GPU (CUDA_VISIBLE_DEVICES=), no network.
Run: cd ~/protocol_pulse && CUDA_VISIBLE_DEVICES= python3 -m pytest -q pipeline/test_spotlight.py"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

PIPELINE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(PIPELINE)
sys.path.insert(0, PIPELINE)
sys.path.insert(1, os.path.join(REPO, "segment_v1"))
sys.path.insert(2, os.path.join(REPO, "video_pipeline_v3"))
import credit_rings  # noqa: E402
import editorial_gate  # noqa: E402
import qa_gates  # noqa: E402
import telegram  # noqa: E402

CH = "Natalie Brunell"
FIRST = "the part nobody says out loud.\n\nCredits \U0001F9E1\n\n@natbrunell"


def spot_edl(**kw):
    e = {"topic": "bitcoin", "package_type": "moments", "package_shape": "spotlight", "mode": "pinned",
         "moments_package_sha256": "cd" * 32, "title": "The rules nobody can bend", "caption": "one take. no filter.",
         "hook": {"video_id": "AAAAAAAAAA1", "channel": CH, "duration": 21.4, "text": "Bitcoin is the rules."},
         "clips": [], "vo": {"intro": None, "bridges": []}, "first_comment": FIRST}
    e.update(kw)
    return e


class TestG5Window(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="spot_g5_")
        self.addCleanup(shutil.rmtree, self.d)

    def edl_file(self, edl):
        p = os.path.join(self.d, "edl.json")
        with open(p, "w") as f:
            json.dump(edl, f)
        return p

    def test_the_window_follows_the_edls_kind(self):
        self.assertEqual(qa_gates.g5_window(self.edl_file(spot_edl())), ((28.0, 50.0), (28.0, 50.0)))
        medley = qa_gates.G5_DURATION_ACCEPT_S, qa_gates.G5_DURATION_TARGET_S
        self.assertEqual(medley, ((58.0, 72.0), (60.0, 70.0)))                     # ruling 12, unchanged
        for edl in (spot_edl(package_shape="medley"), spot_edl(package_type="story"), {"x": 1}):
            self.assertEqual(qa_gates.g5_window(self.edl_file(edl)), medley)
        self.assertEqual(qa_gates.g5_window(None), medley)
        self.assertEqual(qa_gates.g5_window(os.path.join(self.d, "missing.json")), medley)

    def test_a_34_s_final_passes_as_a_spotlight_and_fails_as_a_medley(self):
        mp4 = os.path.join(self.d, "final.mp4")                                    # a CPU encode, no GPU
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=black:s=320x180:r=24:d=34",
                        "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", "34", "-c:v", "libx264",
                        "-preset", "ultrafast", "-c:a", "aac", "-shortest", mp4], check=True, timeout=120)
        _, spot = qa_gates.gate_g5(mp4, "16x9", window=qa_gates.g5_window(self.edl_file(spot_edl())))
        _, medley = qa_gates.gate_g5(mp4, "16x9")
        self.assertTrue(spot["dur_ok"])
        self.assertNotIn("duration_deviation", spot)
        self.assertFalse(medley["dur_ok"])


REVIEW = {"reviewed_by": "local model", "review_type": "model", "clips": None, "vo_jobs": {},
          "takeaway": {"text": "No ruler, just rules.", "concrete": True, "supported": True}, "sequence": None}


class TestEditorialGate(unittest.TestCase):
    def test_the_medley_laws_do_not_bind_one_moment(self):
        laws = editorial_gate.evaluate_editorial_gate(spot_edl(), dict(REVIEW))["laws"]
        for law in ("L0_REVIEW", "LAW_1_NEW_INFORMATION", "LAW_2_VO_HAS_A_JOB", "LAW_3_CONCRETE_TAKEAWAY",
                    "LAW_4_SEQUENCE_PROGRESSES"):
            self.assertTrue(laws[law]["pass"], (law, laws[law]))

    def test_the_same_review_holds_a_medley_and_a_spotlight_still_needs_its_takeaway_and_line_job(self):
        laws = editorial_gate.evaluate_editorial_gate(spot_edl(package_shape="medley"), dict(REVIEW))["laws"]
        self.assertEqual((laws["LAW_1_NEW_INFORMATION"]["pass"], laws["LAW_4_SEQUENCE_PROGRESSES"]["pass"]),
                         (False, False))
        laws = editorial_gate.evaluate_editorial_gate(spot_edl(), dict(REVIEW, takeaway=None))["laws"]
        self.assertFalse(laws["LAW_3_CONCRETE_TAKEAWAY"]["pass"])                # LAW 3 still binds a spotlight
        line = spot_edl(vo={"intro": "Nobody voted for these rules.", "bridges": []})
        laws = editorial_gate.evaluate_editorial_gate(line, dict(REVIEW))["laws"]
        self.assertFalse(laws["LAW_2_VO_HAS_A_JOB"]["pass"])                      # a closing line needs its job


class TestKit(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="spot_kit_")
        self.addCleanup(shutil.rmtree, self.d)
        self.reg = {CH: {"display_name": CH, "yt_handle": "@NatalieBrunell", "url": "https://youtube.com/@x"}}

    def test_the_first_comment_is_the_builders_verbatim_and_nothing_is_appended(self):
        kit = telegram.publish_kit(self.d, snap={"edl": spot_edl(), "registry": self.reg})
        self.assertTrue(kit.endswith("FIRST COMMENT:\n" + FIRST), kit[-200:])
        self.assertNotIn("credits: @NatalieBrunell", kit)
        medley = telegram.publish_kit(self.d, snap={"edl": spot_edl(package_shape="medley"), "registry": self.reg})
        self.assertTrue(medley.endswith("FIRST COMMENT:\ncredits: @NatalieBrunell\n" + telegram.ORANGE_HEART))

    def test_the_pass_path_caption_names_a_spotlight_demonstration(self):
        att = {"rows": {}}
        cap = telegram.build_caption(self.d, "16x9", att, snap={"edl": spot_edl(), "registry": self.reg})
        self.assertTrue(cap.startswith(telegram.SPOTLIGHT_HEAD + " | " + telegram.HOLD_OK), cap[:200])
        self.assertIn("DEMONSTRATION", cap.splitlines()[0])
        medley = telegram.build_caption(self.d, "16x9", att, snap={"edl": spot_edl(package_shape="medley"),
                                                                   "registry": self.reg})
        self.assertTrue(medley.startswith(telegram.HOLD_OK))


class TestSignoffAndCard(unittest.TestCase):
    def test_one_channel_asks_for_one_clip_and_a_medley_prompt_is_unchanged(self):
        import signoff
        self.assertEqual(signoff.MEDLEY_REGISTERS, '''A) Credit-first: "Clips today from [channels]. Go follow them. Links below."
B) Gratitude-first: "Big thanks to [channels] for today's clips. Follow them all, links below."
C) Call-to-action-first: "Go follow [channels]. Today's clips came from them. Links below."''')
        self.assertIn("Today's clip is from [channel]", signoff.ONE_CHANNEL_REGISTERS)
        self.assertNotIn("clips", signoff.ONE_CHANNEL_REGISTERS)

    def test_one_channel_sits_in_the_middle_of_both_formats(self):
        for (w, h), centre in (((1920, 1080), (960, 510)), ((1080, 1920), (540, 913))):
            lay = credit_rings.card_layout(w, h, 1)
            self.assertEqual(lay["positions"], [centre], (w, h))
            self.assertEqual(lay["positions"][0][0], w // 2)                      # horizontally centred


if __name__ == "__main__":
    unittest.main()
