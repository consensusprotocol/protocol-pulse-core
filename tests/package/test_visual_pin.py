#!/usr/bin/env python3
"""RULING 70 (orchestrator 15:29 Nov 13): the pin-stage visual check (pipeline/visual_pin.py) and the router's vision
prompt (providers.is_vision / prompt_text, the xai_vision and Heimdall back-ends). Offline: no network, no model."""
import base64
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

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
         "lower_third": {"name": "Mark W. Yusko", "text": "Mark W. Yusko, Morgan Creek Capital"},
         "burned_in": [], "advertising": []}         # ruling 93: question 4; RULING 158 (2): question 5
STILL = dict(CLEAN, third_person={"shown": True, "how": "photo", "words_negative": True, "name_on_screen": "null",
                                  "finding": "a photo of a man beside the host while he says a CEO made a mistake"},
             on_screen_text=[{"text": "NVIDIA CEO SCANDAL", "asserts_beyond_words": True,
                              "why": "the words name no company"}])
M = {"moment_id": "m1", "video_id": "vid00000001", "start": 236.688, "end": 253.308, "text": "A CEO makes a mistake."}


class VFake(Fake):
    vision = True


class TestContract(unittest.TestCase):
    def test_the_stills_are_the_cut_in_one_every_second_and_the_last(self):    # 21:10 Nov 14: >= 1 frame a second
        self.assertEqual(VP.times(5.0), [0.0, 1.0, 2.0, 3.0, 4.0, 4.95])
        for dur in (5.0, 12.3, 16.62, 22.94, 35.0):                       # every span up to the 35 s ceiling
            ts = VP.times(dur)
            self.assertEqual((ts[0], ts[-1]), (0.0, round(dur - 0.05, 2)), dur)
            self.assertLessEqual(max(b - a for a, b in zip(ts, ts[1:])), 1.0 + 1e-9, dur)
        self.assertEqual(len(VP.times(22.94)), 24)                        # Blockware: 24 frames, not 8
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

    def test_ruling_93_burned_in_text_per_clip(self):
        item = lambda kind, **k: dict({"kind": kind, "text": "BITCOIN 74,512 | ETH 2,410", "whole_in_16x9": True,
                                       "in_9x16": "out", "covers_speaker": False}, **k)
        rec = lambda *items: dict(VP.check(dict(CLEAN, burned_in=list(items))), measured=True, version=VP.VERSION)
        self.assertIsNone(VP.layout_block(rec()))                                       # nothing burned in
        for kind in ("ticker", "crawl"):                                                # a ticker or crawl: never
            self.assertIn(f"a {kind}", VP.layout_block(rec(item(kind))))
        strap = item("lower_third", text="BILL MILLER IV | CIO, MILLER VALUE")
        for ok in (dict(strap, in_9x16="whole"), dict(strap, in_9x16="out"), dict(strap, kind="bug", in_9x16="whole")):
            self.assertIsNone(VP.layout_block(rec(ok)))                                 # eligible, and flagged
            self.assertEqual([f["kind"] for f in VP.flags(VP.check(dict(CLEAN, burned_in=[ok])))], ["burned_in"])
        for bad, word in ((dict(strap, in_9x16="cut"), "mid-word"), (dict(strap, covers_speaker=True), "covers"),
                          (dict(strap, whole_in_16x9=False), "not wholly inside")):
            self.assertIn(word, VP.layout_block(rec(bad)))                              # ... unless cut, covering,
        self.assertIn("not measured", VP.layout_block({"measured": False}))             # or not whole in the 16:9
        self.assertIn("not asked", VP.layout_block({"measured": True, "flags": []}))    # an earlier record: never
        for bad in ([{"kind": "banner", "text": "x", "whole_in_16x9": True, "in_9x16": "out", "covers_speaker": False}],
                    [dict(strap, in_9x16="partly")], [dict(strap, covers_speaker="no")], "none"):
            with self.assertRaises(ValueError):
                VP.check(dict(CLEAN, burned_in=bad))
        self.assertIn("burned_in", VP.sealed(rec(strap)))
        bug = VP.check(dict(CLEAN, burned_in=[dict(strap, kind="bug", text=None, in_9x16="whole")]))
        self.assertEqual(bug["burned_in"][0]["text"], "")                              # a wordless bug (C1, glm)
        many = [dict(strap, text=f"strap {i}", in_9x16="out") for i in range(VP.TEXTS_MAX + 3)] + [item("ticker")]
        v = VP.check(dict(CLEAN, burned_in=many))                                       # the ticker listed last
        self.assertEqual((len(v["burned_in"]), v["burned_in_truncated"]), (VP.TEXTS_MAX, 4))
        self.assertIn("a ticker", VP.layout_block(dict(v, measured=True, version=VP.VERSION)))   # never cut away
        self.assertIn("never asked for the source's burned captions or on-screen advertising",   # RULING 158 (2):
                      VP.layout_block(dict(v, measured=True, version="visual-3")))   # every clip asked again

    def test_ruling_93_amended_the_sources_burned_captions(self):
        """21:10 Nov 14: Blockware's captions ('SOLD MY ROTH IRA', '26 NO ROTH IRA NO 401K') were on the sheet, and
        visual-2's question told the model to leave subtitles out. A caption never makes a clip ineligible; cut by the
        9:16 it makes the clip 16:9-ONLY, held until the integrator's render can pass a 16:9-only pin."""
        q4 = VP.PROMPT.split("4. burned_in:")[1]
        self.assertNotIn("Not subtitles of the spoken words", q4)            # the cause, gone
        for words in ("BURNED-IN CAPTIONS", '"caption"', "EVERY frame", "face"):
            self.assertIn(words, q4)
        cap = lambda text, cut, at=(16.35, 19.62): {"kind": "caption", "text": text, "whole_in_16x9": True,
                                                   "in_9x16": cut, "covers_speaker": False, "at": list(at)}
        rec = lambda *items: dict(VP.check(dict(CLEAN, burned_in=list(items))), measured=True, version=VP.VERSION)
        blockware = rec(cap("SOLD MY ROTH IRA", "cut", (3.27,)), cap("26 NO ROTH IRA NO 401K", "cut"))
        self.assertEqual(VP.formats(blockware), ["16x9"])
        self.assertEqual([f["kind"] for f in VP.flags(blockware)], ["burned_caption", "burned_caption"])
        self.assertEqual(VP.flags(blockware)[1]["at"], [16.35, 19.62])
        with mock.patch.object(VP, "RENDER_16X9_ONLY", False):
            self.assertIn("16:9-only", VP.layout_block(blockware))           # held while the render cannot pass it
            self.assertNotIn("ticker", VP.layout_block(blockware))
        self.assertIsNone(VP.layout_block(blockware))                        # the integrator's release landed
        self.assertEqual(VP.formats(blockware), ["16x9"])                    # (c396c3c8): eligible, 16:9 only
        whole = rec(cap("FINANCIALLY INDEPENDENT BY 45", "whole"))
        self.assertIsNone(VP.formats(whole))                                 # a crop shows it whole: both formats
        self.assertIsNone(VP.layout_block(whole))
        self.assertIsNone(VP.formats(dict(blockware, measured=False)))
        self.assertEqual(VP.sealed(dict(blockware, formats=VP.formats(blockware)))["formats"], ["16x9"])
        for bad in ([dict(cap("x", "cut"), text="")], [dict(cap("x", "cut"), at="16.35")],
                    [dict(cap("x", "cut"), at=["16.35"])]):
            with self.assertRaises(ValueError):                             # a caption with no words, or bad times
                VP.check(dict(CLEAN, burned_in=bad))
        many = [cap(f"WHOLE CAPTION {i}", "whole") for i in range(VP.TEXTS_MAX + 2)] + [cap("CUT LAST", "cut")]
        kept = rec(*many)                                                    # audit 2131 C1 (glm): the cut caption
        self.assertEqual(VP.formats(kept), ["16x9"])                         # listed last survives TEXTS_MAX
        self.assertEqual(kept["burned_in"][0]["text"], "CUT LAST")
        old = dict(blockware, version="visual-2")
        self.assertIn("never asked for the source's burned captions", VP.layout_block(old))

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
        self.assertEqual(one - b.upper_usd("t", 0), P.RESERVE_MARGIN * P.IMAGE_TOKENS_UPPER)   # ruling 121: x 1.25
        self.assertEqual(P.Backend.prompt_tokens_reserve({"text": "t", "images": ["a"]}) -
                         P.Backend.prompt_tokens_reserve("t"), P.IMAGE_TOKENS_UPPER)         # each image: 6,000 tokens

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




FIX = os.path.join(HERE, "fixtures", "visual_ads")


def fixture(name):
    with open(os.path.join(FIX, name)) as f:
        return json.load(f)


class TestRuling158OnScreenAdvertising(unittest.TestCase):
    """RULING 158 (2) (orchestrator 23:12 ET Nov 23, STANDING, HARD, both sides): on-screen advertising refuses a clip in
    every format and role; the vision check asks it of every clip (question 5) and names what it saw; the show's own
    branding, ticker and lower third stay a 16:9 flag; unsure is an ad. Fixtures (fixtures/visual_ads): the Digital Asset
    News sheet of Nov 23 (ad47eab4, 575.6-586.6 s: the Kraken banner and the iTrustCapital panel; two of its frames),
    the model's real answers to visual-3 (it filed the banner as a 'ticker') and to visual-4 (Heimdall qwen), and two
    clean sheets' visual-4 answers (Yahoo Finance 96056caa, Simply Bitcoin 1cb16751)."""

    def test_the_kraken_banner_and_the_itrust_panel_refuse_in_every_format_and_role(self):
        v4 = fixture("v4_ad47eab4.json")["record"]
        why = VP.ad_block(v4)
        self.assertIn("KRAKEN", why)
        self.assertIn("CRYPTO IRA", why)
        self.assertIn("ruling 158 (2): on-screen advertising", VP.layout_block(v4))     # every role
        self.assertEqual((VP.graphics_only(v4), VP.crop_only(v4)), (None, None))      # never the 16:9 exception
        banner = dict(v4, advertising=[], burned_in=[x for x in v4["burned_in"] if x["kind"] == "ticker"])
        panel = dict(v4, advertising=[], burned_in=[x for x in v4["burned_in"] if x["kind"] == "bug"])
        self.assertIn("SIGN UP BONUS", VP.ad_block(banner))                            # each one alone refuses
        self.assertIn("CRYPTO IRA", VP.ad_block(panel))
        self.assertEqual((VP.graphics_only(panel), VP.layout_block(panel)[:9]), (None, "ruling 93"))
        bug = next(x for x in v4["burned_in"] if x["kind"] == "bug")
        cut = dict(panel, burned_in=[dict(bug, in_9x16="cut")])                        # the 9:16 crop's exception
        plain = dict(cut, burned_in=[dict(bug, in_9x16="cut", text="DIGITAL ASSET NEWS")])   # (ruling 123 (2))
        self.assertEqual((VP.crop_only(cut), bool(VP.crop_only(plain))), (None, True))   # never for an ad
        v3 = fixture("v3_ad47eab4.json")["record"]                                     # the record that sealed
        self.assertIn("never asked for", VP.layout_block(v3))                          # afd8977d: asked again now,
        self.assertIn("SIGN UP BONUS", VP.ad_block(v3))                                # and refused on its words
        for f in ("dan_ad47eab4_575.61s.jpg", "dan_ad47eab4_581.61s.jpg"):
            self.assertGreater(os.path.getsize(os.path.join(FIX, f)), 1000)

    def test_a_plain_price_ticker_and_the_shows_own_bug_only_flag(self):
        yahoo, sb = fixture("v4_96056caa.json")["record"], fixture("v4_1cb16751.json")["record"]
        self.assertEqual((VP.ad_block(yahoo), VP.graphics_only(yahoo)), (None, ["bug"]))   # 'THE DAILY WOLF': the
        self.assertEqual((VP.ad_block(sb), VP.layout_block(sb)), (None, None))             # show's own, a 16:9 flag
        tick = dict(fixture("v4_96056caa.json")["record"], burned_in=[{
            "kind": "ticker", "text": "S&P 500  Nasdaq  Bitcoin  Ethereum", "whole_in_16x9": True, "in_9x16": "cut",
            "covers_speaker": False}])
        self.assertIsNone(VP.ad_block(tick))
        self.assertEqual(VP.graphics_only(tick), ["ticker"])                           # a 16:9 flag (146 (1))
        for words in ("THE BLOCK REWARD HALVES", "GBTC TRADES AT A DISCOUNT", "SOLD MY ROTH IRA"):   # content
            self.assertIsNone(VP.ad_block(dict(tick, burned_in=[], on_screen_text=[
                {"text": words, "asserts_beyond_words": False, "why": ""}])), words)
        for words in ("GET A SIGN-UP BONUS AT KRAKEN", "USE CODE SATS FOR 10% OFF", "SPONSORED BY BITKEY",
                      "OPEN A CRYPTO IRA TODAY", "$100 FUNDING REWARD",                    # ad words, any kind;
                      "POWERED BY CASH APP", "Presented by Bitkey", "OFFICIAL PARTNER"):   # an event's sponsor wall
            self.assertTrue(VP.ad_block(dict(tick, burned_in=[], on_screen_text=[         # (the integrator's V1,
                {"text": words, "asserts_beyond_words": False, "why": ""}])), words)       # Nov 24: the Nov 11 stage)
        for words in ("BITCOIN 2024 NASHVILLE", "THE BLOCK REWARD HALVES"):                # an event's own name: not
            self.assertIsNone(VP.ad_block(dict(tick, burned_in=[], on_screen_text=[        # an ad by its words alone
                {"text": words, "asserts_beyond_words": False, "why": ""}])), words)
        cap = dict(tick, burned_in=[{"kind": "caption", "text": "OPEN A ROTH IRA", "whole_in_16x9": True,
                                     "in_9x16": "whole", "covers_speaker": False}])
        self.assertIsNone(VP.ad_block(cap))                    # a caption is the spoken words (the ad read's model)

    def test_every_clip_is_asked_and_an_answer_without_question_5_is_out_of_contract(self):
        with self.assertRaises(ValueError):
            VP.check({k: v for k, v in CLEAN.items() if k != "advertising"})
        for bad in ([{"text": "", "what": ""}], [{"text": 3, "what": "x"}], "none", [{"text": "x", "at": "1"}]):
            with self.assertRaises(ValueError):
                VP.check(dict(CLEAN, advertising=bad))
        v = VP.check(dict(CLEAN, advertising=[{"text": "", "what": "a QR code to an exchange", "at": [1.0]}]))
        rec = dict(v, measured=True, version=VP.VERSION)
        self.assertIn("a QR code to an exchange", VP.ad_block(rec))                    # unsure, listed: refused
        self.assertEqual(VP.sealed(rec)["advertising"], v["advertising"])             # named on the pin


if __name__ == "__main__":
    unittest.main()
