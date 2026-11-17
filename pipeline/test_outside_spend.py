#!/usr/bin/env python3
"""BATCH 101, RULING 131 (orchestrator 08:25 ET Nov 17): "every outside dollar your services spend (Scribe and any
other) is to be written into the day ledger the builder reads, so the day's $1.00 is one true number."
must-fail  each paid outside call writes ONE ledger line AT the vendor call site: ElevenLabs Scribe (the code's
           $0.012/min estimate, labelled), xAI's sign-off (its vendor-reported cost_in_usd_ticks; none reported ->
           unpriced, never a guess), ElevenLabs TTS (the input text's characters, unpriced: no USD rate in code); the
           line names the spending service; total() sums a day window given with an ET offset, reports unpriced lines
           apart, skips torn lines; a write that fails is printed and never raises
must-pass  a reused TTS stem (same text, voice, model) and a cached Scribe reading write nothing
Run: cd ~/protocol_pulse && python3 -m pytest -q pipeline/test_outside_spend.py"""
import io
import json
import os
import shutil
import sys
import tempfile
import types
import unittest
from unittest import mock

PIPELINE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PIPELINE)
import outside_spend as OS  # noqa: E402


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="outside_spend_test_")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.ledger = os.path.join(self.tmp, "spend", "integrator_outside.jsonl")
        for p in (mock.patch.object(OS, "LEDGER", self.ledger), mock.patch.object(OS, "SERVICE", "render")):
            p.start()
            self.addCleanup(p.stop)

    def lines(self):
        return OS.lines(self.ledger)


class TestLedger(Base):
    def test_one_line_per_call_names_the_service(self):
        OS.record("xai:grok-3-mini", 0.00042, "vendor-reported", units={"total_tokens": 900}, ref="r")
        d, = self.lines()
        self.assertEqual((d["service"], d["vendor"], d["usd"], d["basis"], d["units"], d["ref"]),
                         ("render", "xai:grok-3-mini", 0.00042, "vendor-reported", {"total_tokens": 900}, "r"))
        self.assertTrue(d["at"].endswith("Z"))

    def test_a_day_window_with_an_et_offset(self):
        os.makedirs(os.path.dirname(self.ledger))
        rows = [{"at": "2026-11-17T02:09:59Z", "usd": 1.0},       # 21:09:59 ET Nov 16: the day before
                {"at": "2026-11-17T02:10:00Z", "usd": 0.25},      # 21:10:00 ET: the day's first second
                {"at": "2026-11-17T14:00:00Z", "usd": None, "vendor": "elevenlabs:tts:eleven_v4"},
                {"at": "2026-11-18T02:09:59Z", "usd": 0.5},
                {"at": "2026-11-18T02:10:00Z", "usd": 2.0}]       # the next day
        with open(self.ledger, "w") as f:
            f.write("\n".join(json.dumps(r) for r in rows[:2]) + "\n{torn\n" +
                    "\n".join(json.dumps(r) for r in rows[2:]) + "\n")
        usd, inside, unpriced = OS.total("2026-11-16T21:10:00-05:00", "2026-11-17T21:10:00-05:00", self.ledger)
        self.assertEqual((usd, len(inside), [u["vendor"] for u in unpriced]), (0.75, 3, ["elevenlabs:tts:eleven_v4"]))

    def test_a_failed_write_is_printed_never_raised(self):
        with mock.patch.object(OS, "LEDGER", "/proc/no_such_dir/ledger.jsonl"), \
                mock.patch("sys.stdout", new_callable=io.StringIO) as out:
            line = OS.record("elevenlabs:scribe_v1", 0.004, "estimate")
        self.assertEqual(line["usd"], 0.004)
        self.assertIn("OUTSIDE SPEND NOT RECORDED", out.getvalue())


class TestScribe(Base):
    def test_the_vendor_call_writes_its_estimate(self):
        import second_recogniser as SR
        src = os.path.join(self.tmp, "w.mp4")
        open(src, "wb").close()

        def run(cmd, *a, **k):
            if cmd[0] == "ffprobe":
                return types.SimpleNamespace(stdout="40.0\n", returncode=0)
            open(cmd[cmd.index("-ar") + 2], "wb").close()             # ffmpeg writes the wav
            return types.SimpleNamespace(stdout="", returncode=0)
        reply = io.BytesIO(json.dumps({"text": "hi", "words": [{"text": "hi", "start": 0.1, "end": 0.3}]}).encode())
        relay = types.ModuleType("relay")
        relay.get_key = lambda name: "k"
        with mock.patch.object(SR.subprocess, "run", run), mock.patch.object(SR.urllib.request, "urlopen",
                                                                            lambda *a, **k: reply), \
                mock.patch.dict(sys.modules, {"relay": relay}):
            words, _, secs = SR.scribe_words(src)
        d, = self.lines()
        self.assertEqual((d["vendor"], d["usd"], d["units"], d["ref"], d["service"]),
                         ("elevenlabs:scribe_v1", 0.008, {"audio_s": 40.0}, "w.mp4", "render"))
        self.assertIn("estimate", d["basis"])


class TestSignoff(Base):
    def test_xai_reported_cost_is_the_line(self):
        import signoff
        signoff._spent({"usage": {"prompt_tokens": 700, "completion_tokens": 200, "total_tokens": 900,
                                  "cost_in_usd_ticks": 4_200_000}}, "seg")
        d, = self.lines()
        self.assertEqual((d["vendor"], d["usd"], d["units"]["total_tokens"]), ("xai:grok-3-mini", 0.00042, 900))
        self.assertTrue(d["basis"].startswith("vendor-reported"))

    def test_no_reported_cost_is_unpriced_never_guessed(self):
        import signoff
        for body in ({"usage": {"total_tokens": 900}}, {}, {"usage": {"cost_in_usd_ticks": True}}):
            signoff._spent(body, "seg")
        self.assertEqual([d["usd"] for d in self.lines()], [None, None, None])
        self.assertTrue(all(d["basis"].startswith("unpriced") for d in self.lines()))

    def test_every_round_of_the_generator_is_written(self):
        import signoff
        reply = {"choices": [{"message": {"content": "1. too short"}}], "usage": {"cost_in_usd_ticks": 10_000_000}}
        resp = mock.Mock(**{"json.return_value": reply, "raise_for_status.return_value": None})
        with mock.patch("requests.post", return_value=resp), mock.patch.object(signoff, "get_key", lambda n: "k"), \
                mock.patch.object(signoff, "_load_history", lambda: []), \
                mock.patch.object(signoff, "_load_reference", lambda: "ref"):
            with self.assertRaises(RuntimeError):                     # no valid line: STOP after 3 rounds
                signoff.generate_signoff("topic", ["A", "B"], "seg", max_rounds=3)
        self.assertEqual([d["usd"] for d in self.lines()], [0.001] * 3)


class TestTts(Base):
    def run_vo(self, text):
        import credit_rings  # noqa: F401  (imports cv2 BEFORE sys.modules is patched: cv2 cannot be imported twice)
        import vo
        seg = os.path.join(self.tmp, "seg")
        os.makedirs(seg, exist_ok=True)
        with open(os.path.join(seg, "edl.json"), "w") as f:
            json.dump({"vo": {"intro": text}, "clips": []}, f)
        calls = []

        class Client:
            def __init__(self, api_key):
                self.text_to_speech = self

            def convert(self, **k):
                calls.append(k["text"])
                return iter([b"\0\0" * 22050])                      # one second of audio
        el = types.ModuleType("elevenlabs")
        el.ElevenLabs = Client
        paths = {"vo_dir": os.path.join(seg, "vo_audio"), "edl_json": os.path.join(seg, "edl.json")}
        with mock.patch.object(vo, "resolve_paths", lambda d: paths), mock.patch.object(vo, "get_key", lambda n: "v"), \
                mock.patch.dict(sys.modules, {"elevenlabs": el}):
            vo.generate_vo(seg)
        return calls

    def test_a_generated_stem_writes_its_characters(self):
        text = "Bitcoin held its ground today."
        self.assertEqual(self.run_vo(text), [text])
        d, = self.lines()
        self.assertEqual((d["vendor"], d["usd"], d["units"]), ("elevenlabs:tts:eleven_v4", None, {"characters": len(text)}))
        self.assertTrue(d["basis"].startswith("unpriced"))

    def test_a_reused_stem_writes_nothing(self):
        text = "Bitcoin held its ground today."
        self.run_vo(text)
        self.assertEqual(self.run_vo(text), [])                      # same text, voice and model: reused, not paid
        self.assertEqual(len(self.lines()), 1)


if __name__ == "__main__":
    unittest.main()
