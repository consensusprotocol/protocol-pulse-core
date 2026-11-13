#!/usr/bin/env python3
"""RULING 70 (orchestrator 15:29 Nov 13): the pin-stage visual check (pipeline/visual_pin.py) and the router's vision
prompt (providers.is_vision / prompt_text, the xai_vision and Heimdall back-ends). Offline: no network, no model."""
import base64
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "pipeline"))
sys.path.insert(0, os.path.join(REPO, "tests", "providers"))
import providers as P  # noqa: E402
import visual_pin as VP  # noqa: E402
from test_providers import Fake, router  # noqa: E402

CLEAN = {"third_person": {"shown": False, "how": "none", "words_negative": False, "name_on_screen": None,
                          "finding": "only the host on camera"},
         "on_screen_text": [{"text": "SIMPLY BITCOIN", "asserts_beyond_words": False, "why": "the show's name"}],
         "lower_third": {"name": "Mark W. Yusko", "text": "Mark W. Yusko, Morgan Creek Capital"}}
STILL = dict(CLEAN, third_person={"shown": True, "how": "photo", "words_negative": True, "name_on_screen": "null",
                                  "finding": "a photo of a man beside the host while he says a CEO made a mistake"},
             on_screen_text=[{"text": "NVIDIA CEO SCANDAL", "asserts_beyond_words": True,
                              "why": "the words name no company"}])
M = {"moment_id": "m1", "video_id": "vid00000001", "start": 236.688, "end": 253.308, "text": "A CEO makes a mistake."}


class VFake(Fake):
    vision = True


class TestContract(unittest.TestCase):
    def test_the_stills_are_the_cut_in_one_every_two_seconds_and_the_last(self):
        self.assertEqual(VP.times(16.62), [0.0, 2.37, 4.73, 7.1, 9.47, 11.84, 14.2, 16.57])   # evenly spaced
        self.assertEqual(VP.times(5.0), [0.0, 2.0, 4.0, 4.95])
        self.assertEqual(len(VP.times(60.0)), VP.TILES)

    def test_a_reply_in_contract_and_out_of_it(self):
        v = VP.check(STILL)
        self.assertIsNone(v["third_person"]["name_on_screen"])               # "null" text is no name
        self.assertEqual([f["kind"] for f in VP.flags(v)], ["third_person", "on_screen_text"])
        self.assertEqual(VP.flags(VP.check(CLEAN)), [])
        self.assertEqual(VP.check(CLEAN)["lower_third"]["name"], "Mark W. Yusko")
        for bad in (dict(CLEAN, extra=1), dict(CLEAN, third_person=dict(CLEAN["third_person"], how="video")),
                    dict(CLEAN, third_person=dict(CLEAN["third_person"], shown="yes")),
                    dict(CLEAN, on_screen_text=[{"text": "x"}]), dict(CLEAN, lower_third="Mark")):
            with self.assertRaises(ValueError):
                VP.check(bad)

    def test_a_third_person_finding_or_no_measure_blocks_the_hook_but_flags_never_reject(self):
        self.assertIsNone(VP.hook_block({"measured": True, "flags": VP.flags(VP.check(CLEAN))}))
        self.assertIsNone(VP.hook_block({"measured": True, "flags": [{"kind": "on_screen_text", "text": "x"}]}))
        why = VP.hook_block({"measured": True, "flags": VP.flags(VP.check(STILL))})
        self.assertIn("ruling 70", why)
        self.assertIn("a photo of a man beside the host", why)                 # what the sheet showed (C2)
        many = dict(CLEAN, on_screen_text=[{"text": f"t{i}", "asserts_beyond_words": i == 13, "why": "w"}
                                           for i in range(20)])
        v = VP.check(many)
        self.assertEqual((len(v["on_screen_text"]), v["on_screen_text_truncated"]), (VP.TEXTS_MAX, 8))
        self.assertEqual(v["on_screen_text"][0]["text"], "t13")                 # the asserting one is kept first
        self.assertIn("not measured", VP.hook_block({"measured": False}))
        self.assertIn("not measured", VP.hook_block(None))

    def test_the_cost_is_the_vendors_figure_and_an_estimate_is_labelled(self):
        class R:
            cached, usd = False, 0.37
        r = R()
        r.usage = {"in": 2760, "out": 6226, "usd_reported": 0.041144}
        self.assertEqual(VP.cost(r), {"usd": 0.041144, "usd_basis": "reported"})
        r.usage = {"in": 2760, "out": 6226}
        self.assertEqual(VP.cost(r), {"usd": 0.37, "usd_basis": "estimate"})
        r.cached = True
        self.assertEqual(VP.cost(r), {"usd": 0.0, "usd_basis": "cached"})

    def test_the_seal_never_holds_a_scratch_path_or_a_cost(self):
        s = VP.sealed({"version": "v", "measured": True, "flags": [], "third_person": {}, "on_screen_text": [],
                       "lower_third": {}, "backend": "b", "replayed": False, "usd": 0.01, "cached": True,
                       "usage": {"in": 1}, "sheet": {"name": "n.jpg", "sha256": "s", "times": [1.0], "path": "/tmp/x"}})
        self.assertEqual(s["sheet"], {"name": "n.jpg", "sha256": "s", "times": [1.0]})
        self.assertFalse({"usd", "cached", "usage"} & set(s))


class TestVisualFor(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.sheet = os.path.join(self.tmp.name, "visual_x.jpg")
        with open(self.sheet, "wb") as f:
            f.write(b"\xff\xd8 not a real jpeg")
        self.saved = VP.fetch, VP.sheet
        VP.fetch = lambda vid, s, e, wd: "/v.mp4"
        VP.sheet = lambda v, s, e, wd: (self.sheet, "ab" * 32, [236.69, 253.26])

    def tearDown(self):
        VP.fetch, VP.sheet = self.saved
        self.tmp.cleanup()

    def test_xai_first_then_heimdall_and_the_prompt_carries_the_sheet(self):
        x = VFake("xai_vision:grok-4.7", "xai_vision", fail="down")
        h = VFake("heimdall:qwen", "heimdall", answer=json.dumps(STILL))
        text_only = Fake("xai:grok", "xai", answer=json.dumps(CLEAN))     # no image input: never asked
        r = router(self.tmp.name, [text_only, x, h], {"visual_check": ["xai:grok", "xai_vision:grok-4.7",
                                                                       "heimdall:qwen"]})
        cache = {}
        rec = VP.visual_for(r, M, self.tmp.name, cache)
        self.assertTrue(rec["measured"])
        self.assertEqual((rec["backend"], text_only.calls, x.calls, h.calls), ("heimdall:qwen", 0, 1, 1))
        self.assertEqual([f["kind"] for f in rec["flags"]], ["third_person", "on_screen_text"])
        self.assertEqual(rec["sheet"]["sha256"], "ab" * 32)
        os.makedirs(os.path.join(self.tmp.name, "visual"), exist_ok=True)
        VP.sheet = lambda v, s, e, wd: (self.sheet, "ab" * 32, [236.69, 253.26])   # the same bytes again
        again = VP.visual_for(r, M, self.tmp.name, cache)                   # paid once: the cache
        self.assertTrue(again["cached"])
        self.assertEqual((again["usd"], h.calls), (0.0, 1))
        VP.sheet = lambda v, s, e, wd: (self.sheet, "cd" * 32, [236.69, 253.26])   # other bytes: judged afresh
        self.assertFalse(VP.visual_for(r, M, self.tmp.name, cache)["cached"])
        self.assertEqual(h.calls, 2)
        self.assertNotEqual(VP.key(M), VP.key(dict(M, text="other words")))   # the words are in the key

    def test_out_of_contract_twice_is_not_measured(self):
        h = VFake("heimdall:qwen", "heimdall", answer="a man is shown")
        r = router(self.tmp.name, [h], {"visual_check": ["heimdall:qwen", "heimdall:qwen"]})
        rec = VP.visual_for(r, M, self.tmp.name, {})
        self.assertFalse(rec["measured"])
        self.assertIn("two tries", rec["why"])
        self.assertIn("seed 7: out of contract", rec["why"])                    # both tries' reasons (C2)
        self.assertIn("then seed 8: out of contract", rec["why"])
        self.assertEqual(h.calls, 2)                                          # one retry, a new seed

    def test_no_sheet_is_not_measured_and_nothing_is_asked(self):
        VP.sheet = lambda *a: (_ for _ in ()).throw(OSError("ffmpeg"))
        h = VFake("heimdall:qwen", "heimdall", answer=json.dumps(CLEAN))
        r = router(self.tmp.name, [h], {"visual_check": ["heimdall:qwen", "heimdall:qwen"]})
        rec = VP.visual_for(r, M, self.tmp.name, {})
        self.assertEqual((rec["measured"], h.calls), (False, 0))


class TestVisionPrompt(unittest.TestCase):
    def test_the_recording_holds_the_images_sha_never_the_image(self):
        img = base64.b64encode(b"jpeg bytes").decode()
        prompt = {"text": "look", "images": [img]}
        self.assertTrue(P.is_vision(prompt))
        self.assertFalse(P.is_vision("look"))
        self.assertFalse(P.is_vision({"text": "look", "images": [""]}))
        self.assertIn("[image sha256=", P.prompt_text(prompt))
        self.assertNotIn(img, P.prompt_text(prompt))
        with tempfile.TemporaryDirectory() as d:
            h = VFake("heimdall:qwen", "heimdall", answer=json.dumps(CLEAN))
            r = router(d, [h], {"visual_check": ["heimdall:qwen", "heimdall:qwen"]}, record_dir=os.path.join(d, "rec"))
            r.call("visual_check", prompt, 100, 7)
            recs = [os.path.join(dp, f) for dp, _, fs in os.walk(os.path.join(d, "rec")) for f in fs]
            self.assertEqual(len(recs), 1)
            with open(recs[0]) as f:
                body = f.read()
            self.assertNotIn(img, body)
            self.assertIn("[image sha256=", body)
            self.assertEqual(r.call("visual_check", prompt, 100, 7).cached, True)   # the same bytes: served

    def test_the_upper_bound_counts_each_image(self):
        b = Fake("x:y", "openai", price=(1e6, 0))                             # $1 per input token
        one = b.upper_usd({"text": "t", "images": ["a"]}, 0)
        self.assertEqual(one - b.upper_usd("t", 0), P.IMAGE_TOKENS_UPPER)

    def test_the_heimdall_and_xai_vision_bodies(self):
        sent = []
        saved = P._http_json
        P._http_json = lambda url, body, headers, timeout: (sent.append((url, body)) or
                                                            {"choices": [{"message": {"content": "{}"}}],
                                                             "output_text": "{}", "usage": {}})
        try:
            h = P.HeimdallBackend("heimdall:qwen", {"model": "qwen", "base_url": "https://h.example/api/v1"}, "/x")
            h.key = lambda n: "k"
            h.complete({"text": "look", "images": ["QUJD"]}, 100, 7)
            x = P.XAIVisionBackend("xai_vision:grok-4.7", {"model": "grok-4.7"}, "/x")
            x.key = lambda n: "k"
            x.complete({"text": "look", "images": ["QUJD"]}, 100, 7)
            with self.assertRaises(P.RequestRejected):
                x.complete("text only", 100, 7)
        finally:
            P._http_json = saved
        user = sent[0][1]["messages"][1]["content"]
        self.assertEqual(user[1], {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,QUJD"}})
        self.assertEqual(sent[1][0], "https://api.x.ai/v1/responses")
        self.assertFalse(sent[1][1]["store"])
        self.assertEqual(sent[1][1]["input"][1]["content"][1],
                         {"type": "input_image", "image_url": "data:image/jpeg;base64,QUJD", "detail": "high"})


if __name__ == "__main__":
    unittest.main()
