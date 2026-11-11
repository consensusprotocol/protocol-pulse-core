#!/usr/bin/env python3
"""Law L-a (orchestrator 2026-11-11 15:30 / PBX): the sign-off voiceover names every channel on the credits card;
the spoken set, the card set and the clips used are identical. Gate G20 SIGNOFF_NAMES_ALL.
must-fail  the PBX-approved preview (references/pulse_preview_2026-11-11): its sign-off names Natalie Brunell,
           Yahoo Finance and Bitcoin Magazine, the card also credits DataDash (the hook)
must-pass  the frozen v2f reference (its sign-off names all three credited channels)
generator  vo.generate_vo passes the card's channel list (hook first) to the sign-off; a stem is keyed by
           (text, voice, model), so a different channel list never reuses it
Run: cd ~/protocol_pulse && CUDA_VISIBLE_DEVICES=0 python3 -m pytest -q pipeline/test_g20_signoff.py"""
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

PIPELINE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(PIPELINE)
sys.path.insert(0, PIPELINE)
import credit_rings as CR  # noqa: E402
import gates as G  # noqa: E402

PREVIEW = os.path.join(REPO, "references", "pulse_preview_2026-11-11")
V2F = os.path.join(REPO, "references", "v2f_2026-11-06", "run")


def _segs(run_dir):
    return json.load(open(os.path.join(run_dir, "qa", "concat_manifest_16x9.json")))["segments"]


class TestG20(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="g20_")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    @unittest.skipUnless(os.path.isdir(PREVIEW), "protected preview reference not on this machine")
    def test_the_preview_sign_off_misses_the_hook_channel(self):
        credited = CR.credit_channels(json.load(open(os.path.join(PREVIEW, "edl.json"))))
        self.assertEqual(credited, ["DataDash", "Natalie Brunell", "Yahoo Finance", "Bitcoin Magazine"])
        ok, d = G.gate_g20(os.path.join(PREVIEW, "out", "segment.mp4"), _segs(PREVIEW), credited, self.tmp)
        self.assertFalse(ok, d)
        self.assertEqual((d["missing"], d["extra"]), (["DataDash"], []), d)

    @unittest.skipUnless(os.path.isdir(V2F), "frozen v2f reference not on this machine")
    def test_v2f_sign_off_names_every_credited_channel(self):
        credited = CR.credit_channels(json.load(open(os.path.join(V2F, "edl.json"))))
        ok, d = G.gate_g20(os.path.join(V2F, "out", "segment.mp4"), _segs(V2F), credited, self.tmp)
        self.assertTrue(ok, d)

    def test_matching_is_space_insensitive_and_tolerates_one_misheard_letter(self):
        reg = [{"display_name": "DataDash"}, {"display_name": "Natalie Brunell"}, {"display_name": "Yahoo Finance"},
               {"display_name": "The Bitcoin Layer", "aliases": ["bitcoin lair"]}]
        credited = ["DataDash", "Natalie Brunell", "The Bitcoin Layer"]
        heard = G.spoken_channels("Thanks to Data Dash, Natalie Brunel and the Bitcoin Lair. Follow them.", reg, credited)
        self.assertEqual(heard, set(credited))
        reg2 = reg + [{"display_name": "Bitcoin Magazine"}, {"display_name": "Bitcoin Magazine Pro"}]
        self.assertEqual(G.spoken_channels("Clips from Bitcoin Magazine, go follow them.", reg2, ["Bitcoin Magazine"]),
                         {"Bitcoin Magazine"})                     # a similar non-credited name is not heard
        self.assertEqual(G.spoken_channels("Thanks to Yahoo Finance.", reg, ["DataDash"]), {"Yahoo Finance"})

    def test_no_shoutout_or_no_credited_channels_fails_closed(self):
        ok, _ = G.gate_g20("unused.mp4", [{"label": "hook", "type": "talking_head", "start": 0, "end": 1}],
                           ["DataDash"], self.tmp)
        self.assertFalse(ok)
        ok, _ = G.gate_g20("unused.mp4", [{"label": "shoutout", "type": "shoutout", "start": 0, "end": 1}], [], self.tmp)
        self.assertFalse(ok)


class TestSignoffGenerator(unittest.TestCase):
    """vo.generate_vo: the sign-off generator gets the card's channels, hook first; stems keyed by the script."""

    def test_the_hook_channel_is_named_and_a_new_list_gets_a_new_stem(self):
        import vo
        tmp = tempfile.mkdtemp(prefix="vo_")
        self.addCleanup(shutil.rmtree, tmp, True)
        os.makedirs(os.path.join(tmp, "vo_audio"))
        edl = {"topic": "t", "hook": {"channel": "DataDash"}, "vo": {},
               "clips": [{"index": 1, "channel": "Natalie Brunell"}, {"index": 2, "channel": "Yahoo Finance"}]}
        json.dump(edl, open(os.path.join(tmp, "edl.json"), "w"))
        seen = []

        def fake_signoff(topic, names, segment_id):
            seen.append(list(names))
            return "Thanks to " + ", ".join(names) + ". Go follow them for more, links below."
        client = mock.MagicMock()
        client.text_to_speech.convert.return_value = [b"\x00\x00" * 2205]
        with mock.patch.object(vo, "get_key", lambda k: "x"), \
                mock.patch.dict(sys.modules, {"elevenlabs": mock.MagicMock(ElevenLabs=lambda api_key: client)}), \
                mock.patch("signoff.generate_signoff", fake_signoff), \
                mock.patch.object(vo, "resolve_paths", lambda d: {"vo_dir": os.path.join(d, "vo_audio"),
                                                                  "edl_json": os.path.join(d, "edl.json")}):
            m1 = vo.generate_vo(tmp)
            edl["clips"].append({"index": 3, "channel": "Bitcoin Magazine"})
            json.dump(edl, open(os.path.join(tmp, "edl.json"), "w"))
            m2 = vo.generate_vo(tmp)
        self.assertEqual(seen[0], ["DataDash", "Natalie Brunell", "Yahoo Finance"])
        self.assertEqual(seen[1], ["DataDash", "Natalie Brunell", "Yahoo Finance", "Bitcoin Magazine"])
        self.assertNotEqual(m1["signoff"]["stem_wav"], m2["signoff"]["stem_wav"])


if __name__ == "__main__":
    unittest.main()
