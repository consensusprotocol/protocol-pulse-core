#!/usr/bin/env python3
"""RULINGS 90-92 (orchestrator 22:40 / 22:52 ET Nov 13): the SPOTLIGHT pin kind, offline.

- The pin contract agreed with the integrator (22:44 ET): shape "spotlight", one hook segment, edl_vo with "closing",
  the whole first comment, the gate rows; the seal covers the closing line, the kind and the comment, and every pin
  sealed before it recomputes (pin_seal, and the integrator's exact call).
- The snap (ruling 32's, outward to the speaker's whole thought), ruling 92's source test, the writer's and the
  value verdict's contracts, PBX's comment format and the verified handles, the pool's free rules.
- package_for: the closing line ships only with every gate; any failure leaves no line (ruling 91).
- build(): the stages in order, the ALONE scorer's wait, the nearest moments when none qualifies.
"""
import copy
import glob
import json
import os
import shutil
import sys
import tempfile
import unittest
from datetime import timedelta
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "pipeline"))
sys.path.insert(0, os.path.join(REPO, "tests", "eligibility"))
sys.path.insert(0, os.path.join(REPO, "tests", "moments"))
sys.path.insert(0, HERE)
import eligibility as E  # noqa: E402
import moments as M  # noqa: E402
import package as PK  # noqa: E402
import package_pin as PP  # noqa: E402
import providers as P  # noqa: E402
import spotlight as SPOT  # noqa: E402
import visual_pin as VP  # noqa: E402
from test_eligibility import NOW, REG, source  # noqa: E402
from test_gates import Canned, a_item  # noqa: E402
from test_medley import sv  # noqa: E402
from test_moments import pm  # noqa: E402

TEXT = ("Bitcoin is the one money nobody can print more of, and that is exactly why people keep holding it through "
        "every single cycle we have seen so far, from the very first one to the one we are in right now today.")
GOOD = {"title": {"text": "The money nobody can print", "cites": []},
        "caption": {"text": "a clear case for a fixed supply.", "cites": []},
        "comment": {"text": "This one stuck with me.\nWorth the full listen.", "cites": []},
        "closing": {"text": "Scarcity only matters when nobody can quietly change it.", "cites": []}}


class B:
    def __init__(self, vendor, family):
        self.vendor, self.family = vendor, family


class Router(Canned):
    """Canned answers by role, with the back-ends the step-A verdicts name."""
    backends = {"fake:xai": B("xai", "grok"), "fake:heimdall": B("heimdall", "deepseek")}

    def __init__(self, **answers):
        super().__init__(**answers)
        self.down = set()


def moment(text=TEXT, dur=20.0, mid="m1", channel="DataDash", **kw):
    m = pm(mid, channel, dur)
    m.update(text=text, channel_name=channel, published_at=(NOW - timedelta(hours=2)).isoformat(),
             hook_onset={"pass": True, "measured": True, "lead_ms": 120, "cut_in": 1.0, "why": "quiet"},
             hook_rating={"scroll": 5, "alone": 4, "setup": 3, "rating": 4, "why": "a complete claim",
                          "backend": "fake:xai", "replayed": False},
             visual={"version": "visual-1", "measured": True, "flags": [], "backend": "fake:vis", "replayed": False,
                     "third_person": {"shown": False, "how": "none", "words_negative": False, "name_on_screen": None,
                                      "finding": "none"}, "on_screen_text": [],
                     "lower_third": {"name": None, "text": None}},
             scorer_verdict=sv(text, 4.0),
             spotlight_source={"ok": True, "why": "layout 'conversation'", "turns": {"measured": False},
                               "layout": {"measured": True, "layout": "conversation", "backend": "fake:vis",
                                          "replayed": False}})
    m.update(kw)
    return m


def two():
    return [dict(a_item("hook"), backend="fake:xai", replayed=False),
            dict(a_item("hook"), backend="fake:heimdall", replayed=False)]


def pre_of(m):
    return {"ok": True, "request_id": "r1", "segments": [{"video_id": m["video_id"], "start": round(m["start"], 3),
                                                          "end": round(m["end"], 3), "approved_text": m["text"],
                                                          "role": "hook", "verdict": "pass", "outcome": "pass"}]}


FID_OK = {"ok": True, "measured": True, "verdict": {"ok": True, "violations": []}, "violations": [],
          "backend": "fake:verdict", "replayed": False, "deterministic": {"ok": True, "violations": []}}
CX_OK = {"ok": True, "measured": True, "violations": [], "backends": {"B": "fake:b", "C": "fake:c"}, "replayed": False}
VALUE_YES = {"adds": "yes", "no_restate": "yes", "missed": "yes", "short": "yes", "why": "it names what is at stake"}


def unknown_speaker(router, pk, sources, log=print):
    for s in pk["segments"]:
        s["speaker"] = {"name": "unknown", "role": None, "line": None, "basis": None, "why": "test", "people": [],
                        "measured": True}
    return pk


def package(m=None, value=VALUE_YES, write=GOOD, cx=CX_OK, cx_base=CX_OK, fid=FID_OK, cfid=FID_OK, writes=None):
    """package_for on one moment with canned verdicts -> (pk, why, router, the context checks asked)."""
    m = m or moment()
    ctx = E.Context(NOW, REG)
    router = Router(angle_write=writes or [write], coherence_verdict=[value])
    asked = []

    def ci(router_, pk, contexts, *a, **k):
        asked.append(pk["vo"].get("intro"))
        return copy.deepcopy(cx if pk["vo"].get("intro") else cx_base)
    fids = []

    def vf(router_, segs, lines, *a, **k):
        fids.append([x["slot"] for x in lines])
        return copy.deepcopy(cfid if [x["slot"] for x in lines] == ["closing"] else fid)
    facts = {"now": NOW, "day": SPOT.et_day(NOW), "never_delivered": True, "one_per_channel_day": True}
    with mock.patch.object(SPOT.VF, "check", vf), mock.patch.object(SPOT.CI, "check_contexts", ci), \
            mock.patch.object(SPOT.CI, "contexts_from_sources", lambda pk, s, n: {}), \
            mock.patch.object(SPOT.P, "current_levels", lambda *a, **k: []):
        pk, why = SPOT.package_for(router, m, ctx, {}, two(), {"ok": True, "model": "fake:stt", "replayed": False,
                                                               "edges": {"cuttable": True}},
                                   {"verdict": "keep", "backend": "fake:excl", "replayed": False, "measured": True},
                                   pre_of(m), facts, log=lambda *a: None, handles_path=HANDLES, attribute=unknown_speaker)
    return pk, why, router, asked, fids


TMP = tempfile.mkdtemp(prefix="test_spotlight_")
HANDLES = os.path.join(TMP, "channels.json")              # a verified table of the integrator's shape (x_handle)


def setUpModule():
    with open(HANDLES, "w") as f:
        json.dump([{"display_name": "DataDash", "x_handle": "@Nicholas_Merten", "aliases": []},
                   {"display_name": "Natalie Brunell", "x_handle": "@natbrunell", "aliases": ["Natalie"]},
                   {"display_name": "Simply Bitcoin", "x_handle": "", "aliases": []}], f)


def tearDownModule():
    shutil.rmtree(TMP, ignore_errors=True)


class TestPinContract(unittest.TestCase):
    def test_required_rows_with_and_without_a_closing_line(self):
        self.assertEqual(PP.required_gates({"shape": "spotlight", "vo": {"closing": None}}), PP.SPOTLIGHT_GATES)
        self.assertEqual(PP.required_gates({"shape": "spotlight", "vo": {"closing": "A line."}}),
                         PP.SPOTLIGHT_GATES + PP.CLOSING_GATES)
        self.assertEqual(PP.required_gates({"shape": "spotlight", "edl_vo": {"closing": "A line."}}),   # a pin's
                         PP.SPOTLIGHT_GATES + PP.CLOSING_GATES)                                   # moments_package
        self.assertEqual(PP.required_gates({"shape": "medley"}), PP.REQUIRED_GATES + PP.MEDLEY_GATES)
        for g in ("spotlight_source", "hook_own", "stands_alone", "step_a_two_families", "visual", "window_12h",
                  "never_delivered", "one_per_channel_day", "precheck"):          # the keys agreed at 22:44 ET
            self.assertIn(g, PP.SPOTLIGHT_GATES)
        self.assertEqual(PP.CLOSING_GATES, ("closing_value", "closing_fidelity", "closing_context"))

    def test_every_pin_sealed_before_recomputes(self):
        pins = [p for p in glob.glob(os.path.join(HERE, "proof", "*", "*.json"))
                if os.path.basename(p).startswith("MOMENTS_PIN")]
        self.assertGreater(len(pins), 5)
        for p in pins:
            with open(p) as f:
                pin = json.load(f)
            mp = pin.get("moments_package")
            if not mp or "package_sha256" not in mp:
                continue
            self.assertEqual(PP.pin_seal(pin), mp["package_sha256"], p)
            self.assertEqual(PP.seal(pin["segments"], mp["edl_vo"], mp.get("signoff_expected"), mp["title"],   # the
                                     mp["caption"], mp["gates"], mp.get("btc_screen")), mp["package_sha256"], p)

    def test_a_spotlight_pin_seals_its_closing_kind_and_comment(self):
        pk, why, *_ = package()
        self.assertIsNone(why)
        pin = PP.to_pin(pk, "t")
        mp = pin["moments_package"]
        self.assertEqual(mp["shape"], "spotlight")
        self.assertEqual(len(pin["segments"]), 1)
        self.assertEqual(pin["segments"][0]["role"], "hook")
        self.assertEqual(mp["edl_vo"], {"intro": None, "bridges": [], "closing": GOOD["closing"]["text"]})
        self.assertEqual(mp["vo_jobs"], {"closing": "closing"})
        self.assertEqual(mp["first_comment"], pk["first_comment"])
        self.assertEqual(PP.pin_seal(pin), mp["package_sha256"])
        integrator = PP.seal(pin["segments"], mp["edl_vo"], mp.get("signoff_expected"), mp["title"], mp["caption"],
                             mp["gates"], mp.get("btc_screen"),
                             **({"shape": mp["shape"], "first_comment": mp["first_comment"]}
                                if mp.get("shape") == "spotlight" else {}))       # their exact call (23:1x ET)
        self.assertEqual(integrator, mp["package_sha256"])
        medley = {"segments": [], "edl_vo": {"intro": None, "bridges": [], "closing": None}, "signoff": "S"}
        self.assertEqual(PP.seal([], medley["edl_vo"], "S", "t", "c", {}),          # a medley's body never holds the
                         PP.seal([], {"intro": None, "bridges": []}, "S", "t", "c", {}))   # closing (C1, glm)
        for change in (lambda p: p["moments_package"]["edl_vo"].update(closing="Another line."),
                       lambda p: p["moments_package"].update(first_comment="x"),
                       lambda p: p["moments_package"].update(shape="medley")):
            p2 = copy.deepcopy(pin)
            change(p2)
            self.assertNotEqual(PP.pin_seal(p2), mp["package_sha256"])

    def test_the_contract_refuses_anything_else(self):
        pk, why, *_ = package()
        self.assertIsNone(why)
        cases = {
            "two segments": lambda p: p["segments"].append(dict(p["segments"][0], label="clip_01")),
            "an intro": lambda p: p["vo"].update(intro="Here is the thing."),
            "a bridge": lambda p: p["vo"].update(bridges=["Next."], bridges_after_clip=[1]),
            "a long closing": lambda p: (p["vo"].update(closing=" ".join(["word"] * 13)),
                                         next(x for x in p["lines"] if x["slot"] == "closing").update(
                                             text=" ".join(["word"] * 13))),
            "a comment that is not the gated one": lambda p: p.update(first_comment=p["first_comment"] + " extra"),
            "a runtime under 28 s": lambda p: p.update(runtime_s_estimate=27.9),
            "no source row": lambda p: p["gates"].pop("spotlight_source"),
            "a closing without its rows": lambda p: p["gates"].pop("closing_value"),
            "a replayed row": lambda p: p["gates"]["hook_own"].update(replayed=True),
            "no first comment": lambda p: p.pop("first_comment"),
        }
        for name, change in cases.items():
            p2 = copy.deepcopy(pk)
            change(p2)
            with self.assertRaises(PP.PinRefused, msg=name):
                PP.to_pin(p2, "t")

    def test_the_comment_format(self):
        self.assertEqual(PP.first_comment_text("Line one.\nLine two.", ["@a", "Some Name"]),
                         "Line one.\nLine two.\n\nCredits \U0001F9E1\n\n@a Some Name")


def snap_rig(sentences, k, marks=()):
    src = source(sentences, channel="DataDash", age_h=2.0, vid="vidS")
    ctx = E.Context(NOW, REG)
    sp = E.Span(src, k, k)
    m = M.record(sp, {"scores": dict(pm("x", "A", 1.0)["scores"]), "names_person": False, "risk": [],
                      "topics": ["price_action"], "reason": "r"}, ctx, M.judge(sp, ctx), {"by": "fake"})
    m["rank_score"] = 1.0
    caps = lambda vid: ([(t, "w", True) for t in marks] or None, {"file": "f", "sha256": "s"} if marks else None)
    return m, {"vidS": src}, ctx, caps


S5 = "Bitcoin keeps moving and people keep watching it closely today."      # 10 words: 3.3 s with its pause
S20 = " ".join(["Bitcoin"] + ["word"] * 63) + "."                              # 64 words: about 19.5 s
S33 = " ".join(["Bitcoin"] + ["word"] * 109) + "."                             # 110 words: about 33 s


class TestSnap(unittest.TestCase):
    def test_the_next_sentences_first_whole_and_never_padded(self):
        m, srcs, ctx, caps = snap_rig([S5, S5, S5, S5, S5, S5, S5], 2)
        v, why = SPOT.snap(m, srcs, ctx, caps)
        self.assertIsNone(why)
        self.assertEqual(v["spotlight_snap"]["was"], [2, 2])
        self.assertEqual(v["spotlight_snap"]["sentences"][0], 2)                # nothing before was needed
        self.assertGreaterEqual(v["duration_s"], SPOT.SNAP_TO_S)
        self.assertLess(v["duration_s"] - 3.3, SPOT.SNAP_TO_S)                 # one sentence fewer is too short
        self.assertNotEqual(v["moment_id"], m["moment_id"])                    # a NEW moment, judged as usual
        self.assertEqual(v["spotlight_snap"]["from"], m["moment_id"])
        self.assertIn("eligibility", v)

    def test_a_speaker_marker_after_turns_it_to_the_sentences_before(self):
        m, srcs, ctx, caps = snap_rig([S5, S5, S5, S5, S5, S5, S5], 4)
        t_next = srcs["vidS"].tokens[srcs["vidS"].sentences[5][0]]["start"]
        m, srcs, ctx, caps = snap_rig([S5, S5, S5, S5, S5, S5, S5], 4, marks=(t_next + 1.5,))
        v, why = SPOT.snap(m, srcs, ctx, caps)
        self.assertIsNone(why)
        self.assertEqual(v["spotlight_snap"]["sentences"][1], 4)                # never across the marker
        self.assertLess(v["spotlight_snap"]["sentences"][0], 4)

    def test_no_snap_past_35_s_or_past_the_record(self):
        m, srcs, ctx, caps = snap_rig([S20, S5, S20], 1)
        v, why = SPOT.snap(m, srcs, ctx, caps)                                 # 3.3 + 19.5 = 22.8 s: fine
        self.assertIsNone(why)
        m, srcs, ctx, caps = snap_rig([S5], 0)
        v, why = SPOT.snap(m, srcs, ctx, caps)
        self.assertIsNone(v)
        self.assertIn("the word record ends", why)
        m, srcs, ctx, caps = snap_rig([S33, S5, S33], 1)                     # either side runs past 35 s
        v, why = SPOT.snap(m, srcs, ctx, caps)
        self.assertIsNone(v)
        self.assertIn("over 35 s", why)
        m, srcs, ctx, caps = snap_rig([S5, S20, S5], 1)                       # long enough already: unchanged
        self.assertIs(SPOT.snap(m, srcs, ctx, caps)[0], m)


class TestSourceTest(unittest.TestCase):
    def lay(self, kind):
        return {"measured": True, "layout": kind, "why": "w", "backend": "b", "replayed": False}

    def test_conversation_or_first_hand_pass_and_recap_reaction_other_fail(self):
        unmarked = {"measured": False, "unmarked": True}
        for kind, want in (("conversation", True), ("first_hand", True), ("recap", False), ("reaction", False),
                           ("other", False)):
            self.assertEqual(SPOT.source_test(unmarked, self.lay(kind))[0], want, kind)

    def test_an_unmeasured_layout_is_never_a_pass(self):
        ok, why = SPOT.source_test({"measured": True, "turns": 30, "minutes": 10, "turns_per_min": 3.0},
                                   {"measured": False, "why": "no sheet"})
        self.assertFalse(ok)
        self.assertIn("not measured", why)

    def test_the_markers_only_make_it_stricter(self):
        solo = {"measured": True, "turns": 8, "minutes": 16.5, "turns_per_min": 0.48}     # Nov 13: L6H7538ogGs
        talk = {"measured": True, "turns": 20, "minutes": 16.8, "turns_per_min": 1.19}    # Nov 13: 3kV3nWC5SAY
        self.assertFalse(SPOT.source_test(solo, self.lay("conversation"))[0])
        self.assertTrue(SPOT.source_test(talk, self.lay("conversation"))[0])
        self.assertTrue(SPOT.source_test(solo, self.lay("first_hand"))[0])       # a keynote is one voice
        self.assertFalse(SPOT.source_test(talk, self.lay("recap"))[0])


class TestContracts(unittest.TestCase):
    def test_layout(self):
        self.assertEqual(SPOT.parse_layout('{"layout": "conversation", "people_on_screen": 2, "why": "two people"}')
                         ["layout"], "conversation")
        for bad in ('{"layout": "panel", "people_on_screen": 2, "why": "w"}',
                    '{"layout": "recap", "people_on_screen": "1", "why": "w"}',
                    '{"layout": "recap", "people_on_screen": 1}', "not json"):
            with self.assertRaises(ValueError):
                SPOT.parse_layout(bad)

    def test_write(self):
        got = SPOT.parse_write(json.dumps(dict(GOOD, title={"text": "T", "cites": ["m1"]})), "m1")
        self.assertEqual(got["title"]["cites"], ["m1"])
        self.assertIsNone(SPOT.parse_write(json.dumps(GOOD), "m1", closing_allowed=False)["closing"])
        self.assertIsNone(SPOT.parse_write(json.dumps(dict(GOOD, closing=None)), "m1")["closing"])
        for bad in (dict(GOOD, title={"text": "T", "cites": ["other"]}), {k: GOOD[k] for k in ("title", "caption")},
                    dict(GOOD, comment={"text": " ", "cites": []}), dict(GOOD, caption={"text": "x" * 221, "cites": []})):
            with self.assertRaises(ValueError):
                SPOT.parse_write(json.dumps(bad), "m1")

    def test_value_verdict_needs_four_clear_yeses_and_twelve_words(self):
        m = moment()
        r = Router(coherence_verdict=[VALUE_YES])
        v = SPOT.value_verdict(r, m, "Scarcity only matters when nobody can quietly change it.", "DataDash",
                               {"heimdall"}, {"deepseek"})
        self.assertTrue(v["ok"])
        self.assertEqual(r.calls[0], ("coherence_verdict", {"heimdall"}, {"deepseek"}))   # off the writer
        for ans in (dict(VALUE_YES, missed="no"), dict(VALUE_YES, adds="no")):
            self.assertFalse(SPOT.value_verdict(Router(coherence_verdict=[ans]), m, "A line.", "D", set(), set())["ok"])
        self.assertFalse(SPOT.value_verdict(Router(coherence_verdict=[VALUE_YES]), m, " ".join(["w"] * 13), "D",
                                            set(), set())["ok"])                 # code counts the words too
        r = Router(coherence_verdict=['{"adds": "maybe"}'])
        v = SPOT.value_verdict(r, m, "A line.", "D", set(), set())
        self.assertFalse(v["ok"])
        self.assertFalse(v["measured"])
        self.assertEqual(r.rejected, ["fake:coherence_verdict"])
        self.assertFalse(SPOT.value_verdict(Router(), m, "A line.", "D", set(), set())["ok"])   # no answer: no line

    def test_style_of_the_comment_and_the_closing(self):
        lint = lambda slot, text: [v["detail"].split(":")[0] for v in SPOT.style_lint([{"slot": slot, "text": text}])]
        self.assertEqual(lint("comment", "This one stuck with me.\nWorth the full listen."), [])
        self.assertIn("comment-lines", lint("comment", "One.\nTwo.\nThree."))
        self.assertIn("comment-words", lint("comment", " ".join(["word"] * 31)))
        self.assertIn("comment-credits", lint("comment", "Go follow @someone"))
        self.assertIn("comment-credits", lint("comment", "Credits to them."))
        self.assertIn("emoji", lint("comment", "So good \U0001F525"))
        self.assertIn("closing-words", lint("closing", " ".join(["word"] * 13)))


class TestCredits(unittest.TestCase):
    def test_verified_handles_only_and_untagged_names_said_so(self):
        cr = SPOT.credits("DataDash", {"name": "unknown", "measured": True}, HANDLES)
        self.assertEqual(cr["tags"], ["@Nicholas_Merten"])
        self.assertIn("no attested speaker", cr["speaker"]["untagged_why"])
        cr = SPOT.credits("Simply Bitcoin", {"name": "Natalie", "measured": True}, HANDLES)   # an alias
        self.assertEqual(cr["tags"], ["Simply Bitcoin", "@natbrunell"])
        self.assertIn("no verified X handle", cr["channel"]["untagged_why"])
        cr = SPOT.credits("DataDash", {"name": "Jane Guest", "measured": True}, HANDLES)
        self.assertEqual(cr["tags"], ["@Nicholas_Merten", "Jane Guest"])
        self.assertEqual(cr["speaker"]["untagged_why"], "not in the verified table")
        cr = SPOT.credits("DataDash", {"name": "Jane Guest", "measured": False}, HANDLES)     # never a guess
        self.assertEqual(cr["tags"], ["@Nicholas_Merten"])
        self.assertEqual(SPOT.credits("DataDash", None, "/nonexistent.json")["tags"], ["DataDash"])


class TestPool(unittest.TestCase):
    def test_one_per_channel_per_day_and_the_record_must_read(self):
        ctx = E.Context(NOW, REG)
        a, b = moment(mid="a", channel="A"), moment(mid="b", channel="B", text=TEXT.replace("money", "asset"))
        caps = lambda vid: (None, None)                                     # (two texts: one speech is one moment)
        got, why = SPOT.pool([a, b], {}, ctx, spotlit=[{"channel_id": "A", "day_et": SPOT.et_day(NOW)}],
                             captions_for=caps)
        self.assertEqual([m["moment_id"] for m in got], ["b"])
        self.assertIn("already has a spotlight", why["a"])
        got, _ = SPOT.pool([a, b], {}, ctx, spotlit=[{"channel_id": "A", "day_et": "2026-11-01"}], captions_for=caps)
        self.assertEqual(len(got), 2)                                       # another day
        got, why = SPOT.pool([a, b], {}, ctx, spotlit=None, captions_for=caps)
        self.assertEqual(got, [])
        self.assertIn("not measured", why["a"])

    def test_35_s_ceiling_and_the_cold_open(self):
        ctx = E.Context(NOW, REG)
        caps = lambda vid: (None, None)
        long_ok = moment(mid="l", dur=30.0, channel="A")
        too_long = moment(mid="t", dur=36.0, channel="B", text=TEXT.replace("money", "asset"))
        conj = moment(mid="c", channel="C", text="And " + TEXT.replace("money", "thing"))
        got, why = SPOT.pool([long_ok, too_long, conj], {}, ctx, spotlit=[], captions_for=caps)
        self.assertEqual([m["moment_id"] for m in got], ["l"])               # 30 s: a medley's 20 s does not bind
        self.assertIn("35.0 s", why["t"])
        self.assertIn("cannot open cold", why["c"])

    def test_the_record(self):
        p = os.path.join(TMP, "SPOTLIGHTS.json")
        try:
            self.assertEqual(SPOT.load_spotlit(p), [])
            SPOT.record_spotlit(p, {"channel_id": "A", "day_et": "2026-11-13"})
            self.assertEqual(SPOT.load_spotlit(p), [{"channel_id": "A", "day_et": "2026-11-13"}])
            with open(p, "w") as f:
                f.write("{")
            self.assertIsNone(SPOT.load_spotlit(p))
            with self.assertRaises(ValueError):
                SPOT.record_spotlit(p, {"channel_id": "B", "day_et": "2026-11-13"})
        finally:
            if os.path.exists(p):
                os.remove(p)


class TestPackageFor(unittest.TestCase):
    def test_the_closing_line_ships_only_with_every_gate(self):
        pk, why, router, asked, fids = package()
        self.assertIsNone(why)
        self.assertEqual(pk["vo"]["closing"], GOOD["closing"]["text"])
        self.assertEqual(PP.gate_problems(pk["gates"], PP.required_gates(pk)), [])
        for g in PP.CLOSING_GATES:
            self.assertEqual(pk["gates"][g]["status"], "PASS")
        self.assertEqual(asked, [GOOD["closing"]["text"]])                  # context judged WITH the line
        self.assertEqual(sorted(map(tuple, fids)), [("closing",), ("title", "caption", "comment")])
        self.assertNotIn("coherence", pk["gates"])
        self.assertNotIn("r4", pk["gates"])
        self.assertTrue(pk["first_comment"].startswith(GOOD["comment"]["text"] + "\n\nCredits \U0001F9E1\n\n"))
        self.assertTrue(pk["first_comment"].endswith("@Nicholas_Merten"))
        self.assertTrue(28.0 <= pk["runtime_s_estimate"] <= 50.0)

    def test_any_failure_leaves_no_line(self):
        for name, kw in (("the value verdict says no", {"value": dict(VALUE_YES, adds="no")}),
                         ("the value verdict is out of contract", {"value": '{"adds": 1}'}),
                         ("its fidelity fails", {"cfid": dict(FID_OK, ok=False, violations=[
                             {"slot": "closing", "rule": "COMMENTARY", "detail": "d"}])}),
                         ("context fails with it", {"cx": dict(CX_OK, ok=False, violations=[
                             {"rule": "NOT_ENTAILED"}])}),
                         ("it breaks the house style", {"write": dict(GOOD, closing={
                             "text": "Ultimately scarcity matters, which makes it rare.", "cites": []})})):
            pk, why, router, asked, fids = package(**kw)
            self.assertIsNone(why, name)
            self.assertIsNone(pk["vo"]["closing"], name)
            self.assertFalse(any(g in pk["gates"] for g in PP.CLOSING_GATES), name)
            self.assertEqual(PP.gate_problems(pk["gates"], PP.required_gates(pk)), [], name)
            self.assertEqual(asked[-1], None, name)                         # the package without it is judged
            self.assertFalse(pk["spotlight"]["closing"]["kept"], name)

    def test_the_precheck_row_needs_one_verdict_on_this_clip(self):
        m = moment()
        rows = lambda pre: SPOT.inventory(*package()[0:1], m, FID_OK, [], True, [], CX_OK, two()[0], two(),
                                          {"verdict": "keep", "measured": True, "replayed": False},
                                          {"ok": True, "edges": {"cuttable": True}}, pre,
                                          m["spotlight_source"], {"now": NOW, "day": "d", "never_delivered": True,
                                                                  "one_per_channel_day": True})["precheck"]["status"]
        self.assertEqual(rows(pre_of(m)), "PASS")
        self.assertEqual(rows(dict(pre_of(m), segments=[])), "NOT RUN")        # ok with no verdict: never a pass
        self.assertEqual(rows(dict(pre_of(m), segments=[dict(pre_of(m)["segments"][0], verdict="hold")])), "FAIL")

    def test_a_null_closing_is_the_default(self):
        pk, why, router, asked, fids = package(write=dict(GOOD, closing=None))
        self.assertIsNone(why)
        self.assertIsNone(pk["vo"]["closing"])
        self.assertEqual(router.calls.count(("coherence_verdict", None, None)), 0)
        self.assertNotIn("coherence_verdict", [c[0] for c in router.calls])     # no value verdict is asked

    def test_one_more_write_of_a_failing_title_never_of_the_closing(self):
        bad = dict(GOOD, title={"text": "The one money nobody can print more of today", "cites": []})   # 9 words
        second = dict(GOOD, closing={"text": "A different closing line here.", "cites": []})
        pk, why, router, *_ = package(writes=[bad, second])
        self.assertIsNone(why)
        self.assertEqual(pk["title"], GOOD["title"]["text"])
        self.assertEqual(pk["vo"]["closing"], GOOD["closing"]["text"])      # the first write's: one write
        pk, why, *_ = package(writes=[bad, bad])
        self.assertIsNone(pk)
        self.assertIn("both writes", why)

    def test_the_base_lines_must_pass_their_own_verdicts(self):
        pk, why, *_ = package(fid=dict(FID_OK, ok=False, violations=[{"slot": "title", "rule": "VERDICT_NO"}]))
        self.assertIsNone(pk)
        self.assertIn("VO fidelity", why)
        pk, why, *_ = package(value=dict(VALUE_YES, adds="no"), cx_base=dict(CX_OK, ok=False, violations=[
            {"rule": "STRONGER"}]))
        self.assertIsNone(pk)
        self.assertIn("context integrity", why)

    def test_step_a_off_the_writer_must_exist(self):
        m = moment()
        r = Router(angle_write=[GOOD])
        r.backends = {"fake:xai": B("fake", "grok"), "fake:heimdall": B("fake", "deepseek")}   # both on the writer
        pk, why = SPOT.package_for(r, m, E.Context(NOW, REG), {}, two(), {}, {}, pre_of(m), {}, log=lambda *a: None,
                                   attribute=unknown_speaker)
        self.assertIsNone(pk)
        self.assertIn("L-x", why)


class TestBuild(unittest.TestCase):
    """The stages in order on stubs: each stage's failure is recorded with how far the moment got."""

    def run_build(self, ms, ratings, alone=None, layout="conversation", poll=None, lock=None):
        ctx = E.Context(NOW, REG)
        calls = {}

        def prescreen(router, ms_, *a, **k):
            return {m["moment_id"]: dict(a_item("hook"), backend="fake:xai") for m in ms_}, \
                {m["moment_id"]: [] for m in ms_}, set(), set()

        def hook_ratings(router, ms_, *a, **k):
            return {m["moment_id"]: {"scroll": ratings[m["moment_id"]], "alone": 5, "setup": 3,
                                     "rating": ratings[m["moment_id"]], "why": "w", "backend": "fake:xai"}
                    for m in ms_}, None

        def second(router, cleared, a_by, *a, **k):
            return {mid: [a_by[mid], dict(a_item("hook"), backend="fake:heimdall")] for mid in cleared}, {}

        def package_for(router, m, ctx_, sources_, a_two, truth, exc, pre, facts, **k):
            calls.setdefault("package_for", []).append(m["moment_id"])
            calls.setdefault("facts", []).append(facts)
            return {"segments": [m], "shape": "spotlight"}, None
        idx = {m["moment_id"]: sv(m["text"], s) for m, s in zip(ms, alone or [4.0] * len(ms)) if s is not None}
        seq = list(poll or [])
        verdicts = lambda path, sha: (seq.pop(0) if seq else idx, {"read": True})
        stubs = [(SPOT.P, "prescreen", prescreen), (SPOT.P, "hook_ratings", hook_ratings),
                 (SPOT.P, "second_screen", second), (SPOT, "package_for", package_for),
                 (SPOT.P, "truth_for", lambda r, m, w, c: {"ok": True, "edges": {"cuttable": True}}),
                 (SPOT.P, "hook_onset_for", lambda m, s, w, c: {"pass": True, "measured": True}),
                 (SPOT.P, "scorer_verdicts", verdicts), (SPOT.P, "render_scorer_sha", lambda *a: "s" * 64),
                 (VP, "visual_for", lambda r, m, w, c: {"measured": True, "flags": [], "backend": "fake:vis"}),
                 (SPOT, "layout_for", lambda r, m, v, c: {"measured": True, "layout": layout, "why": "w"}),
                 (SPOT, "episode_turns", lambda vid, c=None: {"measured": False, "unmarked": True}),
                 (SPOT.P, "exclusion_for", lambda r, m, s, c: {"verdict": "keep"}),
                 (SPOT.P, "_writers", lambda r: (set(), set()))]
        patches = [mock.patch.object(o, n, f) for o, n, f in stubs]
        for p in patches:
            p.start()
        try:
            out = SPOT.build(Router(), ms, {}, ctx, work_dir="/tmp", scorer_verdicts_path="v.json",
                             lock_check=lock or (lambda segs: pre_of(segs[0])), spotlit=[],
                             sleep=lambda s: calls.setdefault("sleeps", []).append(s),
                             captions_for=lambda vid: (None, None), wait_s=600.0)
        finally:
            for p in patches:
                p.stop()
        return out, calls

    def test_the_best_qualifying_moment_goes_to_the_package(self):
        ms = [moment(mid="a", channel="A"), moment(mid="b", channel="B", text=TEXT.replace("money", "asset")),
              moment(mid="c", channel="C", text=TEXT.replace("money", "thing"))]
        out, calls = self.run_build(ms, {"a": 3, "b": 4, "c": 5}, alone=[4.0, 4.0, 3.0])
        self.assertEqual(calls["package_for"], ["b"])                      # c opens best but stands alone at 3
        self.assertIn("hook's own job rates 3", out["moments"]["a"]["out"])
        self.assertIn("ALONE scorer: 3.0", out["moments"]["c"]["out"])
        self.assertIsNotNone(out["package"])

    def test_it_waits_for_the_alone_scorer_and_reports_the_nearest(self):
        ms = [moment(mid="a", channel="A")]
        later = {"a": sv(TEXT, 4.0)}
        out, calls = self.run_build(ms, {"a": 4}, alone=[None], poll=[{}, {}, later])   # [0]: the build's start
        self.assertEqual(calls["package_for"], ["a"])
        self.assertEqual(len(calls["sleeps"]), 2)                       # the rating at poll 2 ends the wait there
        out, calls = self.run_build(ms, {"a": 4}, alone=[None], poll=[{}] * 30)
        self.assertEqual(len(calls["sleeps"]), int(600.0 // SPOT.SCORER_POLL_S))   # bounded: then no spotlight
        out, calls = self.run_build(ms, {"a": 4}, alone=[None], layout="recap")
        self.assertIsNone(out["package"])
        self.assertNotIn("package_for", calls)
        self.assertIn("no rating yet", out["moments"]["a"]["out"])
        self.assertEqual(out["near"][0]["moment_id"], "a")
        self.assertEqual(out["near"][0]["passed"][-1], "step A from the second family")

    def test_never_delivered_is_measured_again_at_the_package(self):
        ms = [moment(mid="a", channel="A")]
        out, calls = self.run_build(ms, {"a": 5})
        self.assertIs(calls["facts"][0]["never_delivered"], True)
        real, n = SPOT.P.usable, []

        def usable(ms_, *a, **k):                       # the pool keeps it; a delivered span appears before the package
            n.append(1)
            return real(ms_, *a, **k) if len(n) == 1 else ([], {ms_[0]["moment_id"]: "delivered"})
        with mock.patch.object(SPOT.P, "usable", usable):
            out, calls = self.run_build(ms, {"a": 5})
        self.assertIs(calls["facts"][0]["never_delivered"], False)

    def test_ruling_92_and_a_lock_with_no_verdict_stops(self):
        ms = [moment(mid="a", channel="A")]
        out, calls = self.run_build(ms, {"a": 5}, layout="reaction")
        self.assertIsNone(out["package"])
        self.assertIn("ruling 92", out["moments"]["a"]["out"])
        out, calls = self.run_build(ms, {"a": 5}, lock=lambda segs: {"ok": False, "segments": [], "error": "timeout"})
        self.assertIsNone(out["package"])
        self.assertIn("timeout", out["lock_stop"])


if __name__ == "__main__":
    unittest.main()
