#!/usr/bin/env python3
"""Ruling 33 part 2 (orchestrator 2026-11-13 '03:42'): a clip may be locked with ONE leading word trimmed (but, and, so,
well, now, yeah). On a synthetic source (sin^2 word envelopes over a -66 dB noise bed):
must-pass  the IN edge is the measured quiet run after the trimmed word; the cut sits in it and the audio as cut opens
           in quiet; the cut table and G16 accept the trimmed lock
must-fail  a co-articulated trimmed word (no quiet between it and the next word); an untrimmed sentence that does not
           start a sentence; a word that is not one of the six or not the word before the lock; the audio as cut
           opening on sound; a cut outside the quiet run; the same lock WITHOUT trimmed_leading (whole sentences only)"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import numpy as np

PIPELINE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PIPELINE)
import sentence_law as L  # noqa: E402

SR = 48000


def sentence(words, t, names, gap_after=None):
    """Words of 0.25 s, abutting, from t; gap_after {index_in_sentence: seconds of quiet after that word}."""
    for i, n in enumerate(names):
        words.append({"word": n, "start": round(t, 3), "end": round(t + 0.25, 3)})
        t += 0.25 + (gap_after or {}).get(i, 0.0)
    return t


def render(path, words, dur, joined=()):
    """sin^2 envelope per word (a pair in `joined` shares ONE envelope: co-articulated, no dip between them)."""
    x = np.random.default_rng(7).normal(0, 0.0005, int(dur * SR))
    spans = [(w["start"], w["end"]) for w in words]
    for a, b in joined:
        spans[a] = (words[a]["start"], words[b]["end"])
        spans[b] = None
    for i, sp in enumerate(spans):
        if sp is None:
            continue
        a, b = int(round(sp[0] * SR)), int(round(sp[1] * SR))
        n = np.arange(b - a)
        x[a:b] += 0.1 * np.sin(np.pi * n / (b - a)) ** 2 * np.sin(2 * np.pi * (250 + 30 * (i % 3)) * n / SR)
    raw = (np.clip(x, -1, 1) * 32767).astype("<i2").tobytes()
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "s16le", "-ar", str(SR), "-ac", "1", "-i", "-", "-c:a",
                    "pcm_s16le", "-f", "wav", path], input=raw, check=True)


def fixture(tmp, quiet_after_but=0.20, joined=False, prev_terminal=True):
    """Sentence A (hook), sentence B = 'But' + 8 words (the trimmed clip), sentence C. Returns (words, src, i0, i1)."""
    words = []
    t = sentence(words, 0.5, [f"a{i}" for i in range(7)] + ["a7." if prev_terminal else "a7"])
    t += 0.4
    i_but = len(words)
    t = sentence(words, t, ["But"] + [f"b{i}" for i in range(1, 8)] + ["b8."], gap_after={0: quiet_after_but})
    i1 = len(words) - 1
    t += 0.4
    t = sentence(words, t, [f"c{i}" for i in range(7)] + ["c7."])
    src = os.path.join(tmp, "src.wav")
    render(src, words, t + 1.0, joined=[(i_but, i_but + 1)] if joined else ())
    return words, src, i_but + 1, i1


TRIM = {"word": "But"}


class TestTrimmedBoundary(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="trim_")
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def test_the_in_edge_is_the_measured_quiet_run_after_the_trimmed_word(self):
        words, src, i0, i1 = fixture(self.tmp)
        sa = L.SourceAudio(src)
        plan = L.edge_plan(sa, words, i0, i1, trimmed=TRIM)
        self.assertTrue(plan["ok"], plan)
        b = plan["in"]
        self.assertEqual((b["lexical"], b["trimmed_leading"], b["after_word"], b["before_word"]),
                         ("trimmed leading word (ruling 33 part 2)", "But", "But", "b1"))
        q = b["quiet_run"]
        self.assertGreater(q["ms"], 100)
        self.assertGreaterEqual(b["cut_lo"], q["start"] - 1e-9)                # the cut range IS the quiet run
        self.assertLessEqual(b["cut_hi"], q["end"] + 1e-9)
        cut = L.accepted_cut(src, plan, sa=sa)
        self.assertIsNotNone(cut)
        self.assertTrue(q["start"] - 1e-9 <= cut["cut_in"] <= q["end"] + 1e-9, (cut, q))
        ok, rec = L.trimmed_onset(src, cut["cut_in"], cut["fade_in_ms"])
        self.assertTrue(ok, rec)                                               # the audio as cut opens in quiet

    def test_without_trimmed_leading_the_same_span_is_not_a_whole_sentence(self):
        words, src, i0, i1 = fixture(self.tmp)
        plan = L.edge_plan(L.SourceAudio(src), words, i0, i1)
        self.assertFalse(plan["ok"])
        self.assertIn("'But' does not end a sentence", plan["in"]["reason"])

    def test_a_co_articulated_trimmed_word_cannot_be_cut_cleanly(self):
        words, src, i0, i1 = fixture(self.tmp, quiet_after_but=0.0, joined=True)
        plan = L.edge_plan(L.SourceAudio(src), words, i0, i1, trimmed=TRIM)
        self.assertFalse(plan["ok"])
        self.assertFalse(plan["in"]["valid"])
        self.assertIn("cannot be cut cleanly", plan["in"]["reason"])
        self.assertIn("co-articulated", plan["in"]["reason"])

    def test_the_untrimmed_sentence_must_start_a_sentence(self):
        words, src, i0, i1 = fixture(self.tmp, prev_terminal=False)
        plan = L.edge_plan(L.SourceAudio(src), words, i0, i1, trimmed=TRIM)
        self.assertFalse(plan["in"]["valid"])
        self.assertIn("does not start a sentence", plan["in"]["reason"])

    def test_only_one_of_the_six_and_only_the_word_before_the_lock(self):
        words, src, i0, i1 = fixture(self.tmp)
        sa = L.SourceAudio(src)
        for t in ({"word": "Because"}, {"word": "And"}, {"word": "But so"}, {"word": ""}, None):
            with self.subTest(trimmed=t):
                b = L.trimmed_boundary(sa, words, i0, t)
                self.assertFalse(b["valid"], b)
                self.assertIn("not the word before the lock", b["reason"])
        self.assertFalse(L.trimmed_boundary(sa, words, i0 + 1, TRIM)["valid"])   # 'b1' is not the trimmed word
        self.assertEqual(L.TRIMMABLE_LEADING, {"but", "and", "so", "well", "now", "yeah"})


class TestTrimmedCutTableAndG16(unittest.TestCase):
    """write_lock_cut_table and gate_g16 on a scratch run: a hook (sentence A, the file head) and clip_01 (sentence B
    with 'But' trimmed)."""

    def setUp(self):
        self.run = tempfile.mkdtemp(prefix="trim_run_")
        self.addCleanup(shutil.rmtree, self.run, True)

    def build(self, trimmed=True, **kw):
        for d in ("sources", "transcripts"):
            os.makedirs(os.path.join(self.run, d), exist_ok=True)
        words, src, i0, i1 = fixture(self.run, **kw)
        shutil.move(src, os.path.join(self.run, "sources", "vid_a.mp4"))
        tpath = os.path.join(self.run, "transcripts", "vid_a.json")
        with open(tpath, "w") as f:
            json.dump({"words": words}, f)
        tsha = L.sha256_file(tpath)

        def lock(a, b, trim=None):
            lk = L.make_lock("vid_a", words, a, b, tsha, " ".join(w["word"] for w in words[a:b + 1]))
            if trim:
                lk["trimmed_leading"] = {"word": trim, "word_index": a - 1}
                lk["sha256"] = L._lock_digest(lk)
            return lk
        edl = {"hook": {"video_id": "vid_a", "channel": "X", "selection_lock": lock(0, 7)},
               "clips": [{"index": 1, "video_id": "vid_a", "channel": "X",
                          "selection_lock": lock(i0, i1, "But" if trimmed else None)}]}
        with open(os.path.join(self.run, "edl.json"), "w") as f:
            json.dump(edl, f)
        return words, i0, i1

    def test_the_cut_table_and_g16_accept_a_clean_trimmed_lock(self):
        self.build()
        cuts = {c["clip_id"]: c for c in L.write_lock_cut_table(self.run)}
        c = cuts["clip_01"]
        self.assertTrue(c["verified"], c)
        self.assertTrue(c["trimmed_onset"]["ok"], c)
        ok, table = L.gate_g16(self.run)
        self.assertTrue(ok, table)
        row = table[1]
        self.assertEqual(row["in"]["lexical"], "trimmed leading word (ruling 33 part 2)")
        self.assertTrue(row["trimmed_onset"]["ok"])

    def test_a_co_articulated_trimmed_word_holds_with_the_reason_in_the_gate_text(self):
        self.build(quiet_after_but=0.0, joined=True)
        c = {c["clip_id"]: c for c in L.write_lock_cut_table(self.run)}["clip_01"]
        self.assertFalse(c["verified"])
        self.assertIn("'But' cannot be cut cleanly", c["error"])
        self.assertIn("co-articulated", c["error"])
        ok, table = L.gate_g16(self.run)
        self.assertFalse(ok)
        self.assertIn("cannot be cut cleanly", " ".join(table[1]["errors"]))

    def test_the_audio_as_cut_opening_on_sound_holds(self):
        self.build()
        with mock.patch.object(L, "hook_lead_at", lambda src, c, fade_ms=0: (0, 0.0)):
            c = {c["clip_id"]: c for c in L.write_lock_cut_table(self.run)}["clip_01"]
        self.assertFalse(c["verified"])
        self.assertIn("trimmed leading word (ruling 33 part 2): 'But' cannot be cut cleanly: the audio as cut", c["error"])
        self.assertFalse(c["trimmed_onset"]["ok"])

    def test_g16_refuses_a_trimmed_cut_outside_the_quiet_run_or_opening_on_sound(self):
        words, i0, i1 = self.build()
        L.write_lock_cut_table(self.run)
        path = os.path.join(self.run, "cuts_final.json")
        with open(path) as f:
            cuts = json.load(f)
        good = dict(cuts[1])
        # batch 58 C1 (glm, qwen): a point the OLD rule allows (inside the heard gap) but outside the quiet run: in the
        # trimmed word's decay, between the gap's start and the quiet run's start, clear of both by > EDGE_EPS_S
        b = L.edge_plan(L.SourceAudio(os.path.join(self.run, "sources", "vid_a.mp4")), words, i0, i1, trimmed=TRIM)["in"]
        g, q = b["word_gap"], b["quiet_run"]
        x = round((g["start"] + q["start"]) / 2, 3)
        self.assertTrue(g["start"] + L.EDGE_EPS_S < x < q["start"] - L.EDGE_EPS_S, (g, q, x))
        for bad in (x, round(words[i0 - 1]["start"] + 0.12, 3)):                  # ... and inside 'But' itself
            with self.subTest(cut_in=bad):
                cuts[1] = dict(good, cut_in=bad)
                with open(path, "w") as f:
                    json.dump(cuts, f)
                ok, table = L.gate_g16(self.run)
                self.assertFalse(ok)
                self.assertIn("outside the legal range", " ".join(table[1]["errors"]))
        cuts[1] = good
        with open(path, "w") as f:
            json.dump(cuts, f)
        with mock.patch.object(L, "hook_lead_at", lambda src, c, fade_ms=0: (0, 0.0)):
            ok, table = L.gate_g16(self.run)
        self.assertFalse(ok)
        self.assertIn("IN: trimmed leading word (ruling 33 part 2): 'But' cannot be cut cleanly", " ".join(table[1]["errors"]))

    def test_the_same_lock_without_trimmed_leading_holds_as_before(self):
        self.build(trimmed=False)
        c = {c["clip_id"]: c for c in L.write_lock_cut_table(self.run)}["clip_01"]
        self.assertFalse(c["verified"])
        self.assertIn("'But' does not end a sentence", c["error"])


class TestPinFields(unittest.TestCase):
    """pinned.validate_schema accepts trimmed_leading / untrimmed_start only as ruled; pinned.trimmed_lock binds the
    word to the run's own transcript and records it inside the lock's digest."""
    REG = [{"display_name": "X", "channel_id": "UCx"}]

    def pin(self, **clip):
        seg = {"video_id": "AAAAAAAAAAA", "channel": "X", "time_coords": "youtube", "source": {"kind": "youtube"}}
        return {"schema": "protocol_pulse.pinned_story.v1", "story_id": "s", "label": "bitcoin", "approved_by": "m",
                "approved_at": "2026-11-13T09:00:00+00:00", "machine_cuts": True,
                "segments": [dict(seg, role="hook", start=10.0, end=20.0, approved_text="Bitcoin is up today."),
                             dict(seg, video_id="BBBBBBBBBBB", role="clip", start=30.0, end=40.0,
                                  approved_text="we have rarely seen six red weeks.", **clip)]}

    def test_the_fields_as_ruled_pass_and_anything_else_is_refused(self):
        import pinned
        pinned.validate_schema(self.pin(trimmed_leading="But", untrimmed_start=29.6), self.REG)
        pinned.validate_schema(self.pin(trimmed_leading="yeah,", untrimmed_start=0), self.REG)
        bad = [({"trimmed_leading": "Because", "untrimmed_start": 29.6}, "trimmed_leading must be ONE word"),
               ({"trimmed_leading": "But so", "untrimmed_start": 29.6}, "trimmed_leading must be ONE word"),
               ({"trimmed_leading": 1, "untrimmed_start": 29.6}, "trimmed_leading must be ONE word"),
               ({"trimmed_leading": "But"}, "untrimmed_start must be a number"),
               ({"trimmed_leading": "But", "untrimmed_start": 30.0}, "untrimmed_start must be a number"),
               ({"trimmed_leading": "But", "untrimmed_start": True}, "untrimmed_start must be a number"),
               ({"untrimmed_start": 29.6}, "trimmed_leading must be ONE word")]
        for clip, why in bad:
            with self.subTest(clip=clip):
                with self.assertRaisesRegex(pinned.PinError, why):
                    pinned.validate_schema(self.pin(**clip), self.REG)
        p = self.pin(trimmed_leading="But", untrimmed_start=29.6)
        p["machine_cuts"] = False
        with self.assertRaisesRegex(pinned.PinError, "trimmed_leading needs a machine_cuts pin"):
            pinned.validate_schema(p, self.REG)

    def test_the_lock_records_the_word_heard_before_it_or_the_pin_is_refused(self):
        import pinned
        words = [{"word": w, "start": i * 0.3, "end": i * 0.3 + 0.25}
                 for i, w in enumerate(["Six", "weeks.", "But,", "we", "have", "rarely", "seen", "this."])]
        lock = L.make_lock("BBBBBBBBBBB", words, 3, 7, "ab" * 32, "we have rarely seen this.")
        new = pinned.trimmed_lock(lock, {"trimmed_leading": "But", "untrimmed_start": 29.6}, words)
        self.assertEqual({k: new["trimmed_leading"][k] for k in ("word", "word_index", "untrimmed_start")},
                         {"word": "But,", "word_index": 2, "untrimmed_start": 29.6})
        self.assertEqual(L.verify_lock(new), [])                                    # inside the digest
        tampered = dict(new, trimmed_leading=dict(new["trimmed_leading"], word="And"))
        self.assertIn("selection lock modified after selection (sha256 mismatch)", L.verify_lock(tampered))
        with self.assertRaisesRegex(pinned.PinError, r"trimmed_leading 'And' is not the word before the lock .*'But,'"):
            pinned.trimmed_lock(lock, {"trimmed_leading": "And", "untrimmed_start": 29.6}, words)
        # batch 58 cycle 2 (glm F1, 1 vote): ruling 17's adjudication rewrites the lock and keeps the record in its digest
        # (ruling 84 '20:40': 'this' / 'these' is one function word now, so the example's difference is a content word;
        # ruling 84 (b)'s record keeps the trimmed word too)
        for heard, text in (("heard", "we have rarely heard this."), ("these.", "we have rarely seen this.")):
            approved = dict(new, selected_text=text if heard == "heard" else "we have rarely seen these.")
            approved["sha256"] = L._lock_digest(approved)
            said = ["Six", "weeks.", "But,", "we", "have", "rarely"] + (["heard", "this."] if heard == "heard" else
                                                                        ["seen", "these."])
            sw = [{"word": w, "start": i * 0.3, "end": i * 0.3 + 0.25} for i, w in enumerate(said)]
            adj = pinned.adjudicate_lock(approved, "unused.mp4", words, recognise=lambda p: (sw, 0.0),
                                         log=lambda *a: None)
            self.assertEqual(adj["trimmed_leading"], new["trimmed_leading"])
            self.assertEqual((adj["text"], L.verify_lock(adj)), (text, []))
            self.assertEqual("alternatives" in adj, heard == "these.")
        head = L.make_lock("BBBBBBBBBBB", words, 0, 1, "ab" * 32, "Six weeks.")
        with self.assertRaisesRegex(pinned.PinError, "<file head>"):
            pinned.trimmed_lock(head, {"trimmed_leading": "But", "untrimmed_start": 0}, words)


class TestStandAloneScorer(unittest.TestCase):
    """The STAND_ALONE scorer must affirm the TRIMMED text of every trimmed segment, the hook included, at the
    unchanged threshold; an untrimmed segment is asked exactly as before."""
    TRIM = {"selection_lock": {"trimmed_leading": {"word": "But", "word_index": 4}}}

    def edl(self, hook_text="Bitcoin fell six weeks in a row.", clip_text="we have rarely seen six red weeks in bitcoin.",
            hook_trim=False, clip_trim=True):
        return {"hook": {"text": hook_text, "channel": "X", **(self.TRIM if hook_trim else {})},
                "clips": [{"index": 1, "text": clip_text, "channel": "Y", **(self.TRIM if clip_trim else {})}]}

    def check(self, edl, scores):
        import stand_alone as S
        asked = []

        def rate(passages):
            asked.extend(p["pid"] for p in passages)
            return {p["pid"]: scores[p["pid"]] for p in passages if p["pid"] in scores}
        return S.check_edl(edl, rate=rate), asked

    def test_a_trimmed_clip_is_scored_on_its_trimmed_text(self):
        out, asked = self.check(self.edl(), {"clip_01": (4.0, "stands alone", None)})
        self.assertEqual(asked, ["clip_01"])                       # 'we' alone would never ask the scorer
        self.assertTrue(out["ok"], out)
        self.assertIn("'But' trimmed; the clip scorer affirms the trimmed text", out["rows"][1]["opener"]["why"])
        for score, fault in ((3.4, None), (4.5, "starts_mid_thought")):
            with self.subTest(score=score, fault=fault):
                out, _ = self.check(self.edl(), {"clip_01": (score, "r", fault)})
                self.assertFalse(out["ok"])
                self.assertIn("does not affirm the trimmed text", out["rows"][1]["opener"]["why"])

    def test_no_scorer_verdict_fails_closed(self):
        import stand_alone as S
        out = S.check_edl(self.edl())
        self.assertFalse(out["ok"])
        self.assertIn("no clip-scorer verdict on the trimmed text (fail closed, ruling 33 part 2)",
                      out["rows"][1]["opener"]["why"])

    def test_a_trimmed_hook_is_scored_too_and_keeps_the_hook_opener_rule(self):
        out, asked = self.check(self.edl(hook_text="the price fell six weeks in a row in bitcoin.", hook_trim=True,
                                         clip_trim=False, clip_text="Bitcoin holders sold."),
                                {"hook": (4.0, "ok", None)})
        self.assertEqual(asked, ["hook"])
        self.assertTrue(out["ok"], out)
        out, _ = self.check(self.edl(hook_text="the price fell six weeks in bitcoin.", hook_trim=True, clip_trim=False,
                                     clip_text="Bitcoin holders sold."), {"hook": (3.0, "weak", None)})
        self.assertFalse(out["ok"])
        out, _ = self.check(self.edl(hook_text="we saw bitcoin fall six weeks.", hook_trim=True, clip_trim=False,
                                     clip_text="Bitcoin holders sold."), {"hook": (5.0, "ok", None)})
        self.assertFalse(out["ok"])                                # a pronoun still never opens a hook
        self.assertIn("hook opens on the pronoun 'we'", out["rows"][0]["opener"]["why"])

    def test_an_untrimmed_segment_is_asked_exactly_as_before(self):
        out, asked = self.check(self.edl(clip_trim=False), {})
        self.assertEqual(asked, [])
        self.assertTrue(out["ok"], out)


class TestFadeRetryPlansTheTrimmedEdge(unittest.TestCase):
    def test_the_retry_candidates_come_from_the_trimmed_plan(self):
        import run_fresh as rf
        rd = tempfile.mkdtemp(prefix="trim_retry_")
        self.addCleanup(shutil.rmtree, rd, True)
        os.makedirs(os.path.join(rd, "transcripts"))
        trim = {"word": "But", "word_index": 4}
        with open(os.path.join(rd, "edl.json"), "w") as f:
            json.dump({"hook": {"selection_lock": {"i0": 0, "i1": 3}},
                       "clips": [{"index": 1, "selection_lock": {"i0": 5, "i1": 9, "trimmed_leading": trim}}]}, f)
        with open(os.path.join(rd, "transcripts", "V.json"), "w") as f:
            json.dump({"words": []}, f)
        run = rf.Run(rd)
        run.mode, run.machine_cuts = "pinned", True
        c = {"clip_id": "clip_01", "video_id": "V", "cut_in": 3.0, "cut_out": 6.0, "cut_duration": 3.0}
        seen = []
        with mock.patch.object(rf.L, "edge_plan", lambda sa, w, i0, i1, trimmed=None: seen.append((i0, i1, trimmed)) or {}), \
                mock.patch.object(rf.L, "cut_candidates", return_value={"in": [], "out": []}), \
                mock.patch.object(rf.L, "SourceAudio", return_value=None):
            rf._retry_fade_edges(run, c, {"errors": ["fade-in missing (x)"]}, lambda *a: None,
                                 lambda *a: (False, {"errors": ["fade-in missing (x)"]}), 24, 20)
        self.assertEqual(seen, [(5, 9, trim)])

    def test_the_candidates_of_the_trimmed_plan_all_sit_in_the_quiet_run(self):        # batch 58 cycle 2 C1
        tmp = tempfile.mkdtemp(prefix="trim_cand_")
        self.addCleanup(shutil.rmtree, tmp, True)
        words, src, i0, i1 = fixture(tmp)
        plan = L.edge_plan(L.SourceAudio(src), words, i0, i1, trimmed=TRIM)
        q, cand = plan["in"]["quiet_run"], L.cut_candidates(src, plan)          # what the retry walks, unmocked
        self.assertTrue(cand["in"])
        self.assertTrue(all(q["start"] - 1e-9 <= x <= q["end"] + 1e-9 for x in cand["in"]), (q, cand["in"]))
        g = plan["in"]["word_gap"]                                              # the old range was wider: it is
        self.assertLess(g["start"], q["start"] - L.HOP_S)                      # the quiet run that narrows it


if __name__ == "__main__":
    unittest.main()
