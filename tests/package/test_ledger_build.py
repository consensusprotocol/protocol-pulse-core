#!/usr/bin/env python3
"""pipeline/ledger_build.py (ORCHESTRATOR 22:40 ruling 2): the medley built from the ingest ledger. Offline:
- re-anchoring a ledger row's TEXT in a word record and snapping it to that record's whole sentences;
- reading the store's word record (its sha checked, sentence-ready only);
- turning rows into the packager's moments (counted drops, no duplicate spans);
- the adapter's failures are raised, never read as an empty ledger."""
import io
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "pipeline"))
sys.path.insert(0, os.path.join(REPO, "tests", "eligibility"))
import eligibility as E  # noqa: E402
import ledger_build as LB  # noqa: E402
import transcript_store as ts  # noqa: E402
from test_eligibility import NOW, REG, source  # noqa: E402

SENTS = ["Bitcoin is a global free market.", "Nobody can stop Bitcoin from settling a payment.",
         "That is the whole design and it works every day.", "Bitcoin does not ask for permission.",
         "In 2009 Bitcoin started as a quiet experiment."]


def row(text, start=None, end=None, mid="L1", vid="vidA"):
    return {"moment_id": mid, "video_id": vid, "channel_id": "UCdd", "channel_name": "DataDash", "text": text,
            "start": start, "end": end, "published_at": NOW.isoformat(), "title": "t",
            "scores": {"contempt_outrage": 0, "hook_first_2s": 3, "quotable": 3, "stakes": 3, "stance": 3,
                       "stands_alone": 4, "surprising_fact": 2},
            "risk": [], "topics": [], "reason": "r", "names_person": False,
            "mined": {"by": "qwen/qwen3.8-27b@heimdall_qwen27b", "at": NOW.isoformat()}}


class TestReanchor(unittest.TestCase):
    def setUp(self):
        self.src = source(SENTS)

    def test_whole_sentences_anchor_exactly(self):
        sp, info = LB.reanchor(row(SENTS[1] + " " + SENTS[2]), self.src)
        self.assertEqual((sp.k0, sp.k1), (1, 2))
        self.assertEqual(info["snapped_words"], [0, 0])
        self.assertEqual(sp.text, E.spoken(self.src.tokens[sp.w0:sp.w1 + 1]))     # the word record's own words

    def test_a_caption_text_snaps_to_the_records_whole_sentences_within_the_limit(self):
        sp, info = LB.reanchor(row("is a global free market."), self.src)              # 1 word short: snaps
        self.assertEqual(((sp.k0, sp.k1), info["snapped_words"]), ((0, 0), [1, 0]))
        sp, info = LB.reanchor(row("whole design and it works every day."), self.src)  # exactly 3 words: snaps
        self.assertEqual(((sp.k0, sp.k1), info["snapped_words"]), ((2, 2), [3, 0]))
        sp, why = LB.reanchor(row("design and it works every day."), self.src)         # 4 words: refused
        self.assertIsNone(sp)
        self.assertIn("not whole sentences", why)

    def test_a_snap_never_adds_a_negation_or_a_number(self):
        """Audit 2315 C1 (grok P1, glm P1-1): 'can stop Bitcoin' snapped to 'Nobody can stop Bitcoin' flips the
        claim the ledger scored; '... started as a quiet experiment' snapped to 'In 2009 ...' adds a number."""
        for text, word in (("can stop Bitcoin from settling a payment.", "Nobody"),
                           ("Bitcoin started as a quiet experiment.", "2009")):
            sp, why = LB.reanchor(row(text), self.src)
            self.assertIsNone(sp, text)
            self.assertIn(word, why)

    def test_a_snap_never_adds_a_near_negation(self):
        """qwen C3: 'Hardly anyone can stop Bitcoin' flips 'anyone can stop Bitcoin'."""
        for word in ("Hardly", "Scarcely", "Barely", "Rarely", "Seldom"):
            src = source([f"{word} anyone can stop Bitcoin from settling a payment.", "That is the plan."])
            sp, why = LB.reanchor(row("anyone can stop Bitcoin from settling a payment."), src)
            self.assertIsNone(sp, word)
            self.assertIn(word, why)

    def test_the_hit_is_measured_against_the_rows_own_caption_times(self):
        """glm C3 P1-3: a phrase said twice inside the search window would anchor on the earliest longest match; the
        offset of the hit from the row's caption times is recorded, so such a hit is visible."""
        a, b = self.src.sentences[1]
        t0, t1 = self.src.tokens[a]["start"], self.src.tokens[b]["end"]
        sp, info = LB.reanchor(row(SENTS[1], start=t0 + 2.0, end=t1 - 1.0), self.src)
        self.assertEqual(info["offset_s"], [-2.0, 1.0])
        self.assertEqual(LB.reanchor(row(SENTS[1]), self.src)[1]["offset_s"],      # glm C4 P2-8: said, not absent
                         "unmeasured: the row has no readable caption times")

    def test_a_typographic_apostrophe_does_not_hide_a_negation(self):
        """glm C2 N-3: 'Don\u2019t' (U+2019) is the negation 'Don't' to the guard."""
        for apostrophe in ("\u2019", "'"):
            src = source([f"Don{apostrophe}t sell your Bitcoin to anyone today.", "That is the plan."])
            sp, why = LB.reanchor(row("sell your Bitcoin to anyone today."), src)
            self.assertIsNone(sp, apostrophe)
            self.assertIn("negation", why)

    def test_text_that_is_not_whole_sentences_or_not_there_is_dropped_with_why(self):
        sp, why = LB.reanchor(row("from settling a payment. That is the whole design"), self.src)  # 4 + 5 words cut
        self.assertIsNone(sp)
        self.assertIn("not whole sentences", why)
        sp, why = LB.reanchor(row("Ethereum is a world computer for everyone."), self.src)
        self.assertIsNone(sp)
        self.assertIn("does not anchor", why)


class TestWordSourceAndInputs(unittest.TestCase):
    def store_with(self, d, vid, sentences, break_sha=False, method="whisper_words_punct", no_sha=False):
        src = source(sentences, vid=vid, method=method)
        segs = [{"start": src.tokens[a]["start"], "end": src.tokens[b]["end"],
                 "text": E.spoken(src.tokens[a:b + 1]),
                 "words": [{"word": t["word"], "start": t["start"], "end": t["end"]} for t in src.tokens[a:b + 1]]}
                for a, b in src.sentences]
        rec = {"segments": segs, "transcript_method": method, "video_id": vid,                     # the store's word
               "words": [{"word": t["word"], "start": t["start"], "end": t["end"]} for t in src.tokens]}  # record shape
        if not no_sha:
            rec["transcript_sha256"] = "x" * 64 if break_sha else ts.segments_sha256(segs)
        os.makedirs(os.path.join(d, "transcripts", vid), exist_ok=True)
        with open(os.path.join(d, "transcripts", vid, f"transcript.{method}.json"), "w") as f:
            json.dump(rec, f)
        return src

    def test_a_record_whose_sha_does_not_match_its_segments_is_never_read(self):
        ctx = E.Context(NOW, REG)
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(LB.word_source(row(SENTS[0]), ctx, d), (None, None, ["no word record in the store"]))
            self.store_with(d, "vidA", SENTS, break_sha=True)
            self.assertEqual(LB.word_source(row(SENTS[0]), ctx, d),
                             (None, None, ["transcript.whisper_words_punct.json: its segments do not match its "
                                           "transcript_sha256"]))
            self.store_with(d, "vidA", SENTS, no_sha=True)                      # glm C2: no sha at all is no match
            self.assertIsNone(LB.word_source(row(SENTS[0]), ctx, d)[0])
            self.store_with(d, "vidA", SENTS)
            src, path, passed_over = LB.word_source(row(SENTS[0]), ctx, d)
            self.assertIsNotNone(src)
            self.assertEqual((src.timing, passed_over), ("word", []))
            p = os.path.join(d, "transcripts", "vidA", "transcript.whisper_words_punct.json")
            with open(p) as f:                             # glm C1 P2-10: a segment edited AFTER its sha was taken
                rec = json.load(f)
            rec["segments"][1]["text"] = "Somebody can stop Bitcoin from settling a payment."
            with open(p, "w") as f:
                json.dump(rec, f)
            self.assertIsNone(LB.word_source(row(SENTS[0]), ctx, d)[0])

    def test_a_record_whose_words_do_not_spell_its_segments_is_never_read(self):
        """glm C3 (a): segments_sha256 covers the segments only, and the clip is cut from rec["words"]. A word list
        edited after the sha (text, or a segment's first or last word's time) is never read."""
        ctx = E.Context(NOW, REG)
        p = None
        for edit in ("text", "time", "extra"):
            with tempfile.TemporaryDirectory() as d:
                self.store_with(d, "vidA", SENTS)
                p = os.path.join(d, "transcripts", "vidA", "transcript.whisper_words_punct.json")
                self.assertIsNotNone(LB.word_source(row(SENTS[0]), ctx, d)[0])           # intact: read
                with open(p) as f:
                    rec = json.load(f)
                w = rec["words"][len(SENTS[0].split()) + 1]                              # "can", in sentence 1
                if edit == "text":
                    w["word"] = "cannot"                                                 # the claim flips
                elif edit == "time":
                    rec["words"][len(SENTS[0].split())]["start"] += 0.5                  # sentence 1's first word
                else:
                    rec["words"].append({"word": "really.", "start": 99.0, "end": 99.4})
                with open(p, "w") as f:
                    json.dump(rec, f)
                src, path, passed_over = LB.word_source(row(SENTS[0]), ctx, d)
                self.assertIsNone(src, edit)
                self.assertIn("do not spell its sha-checked segments", passed_over[0])

    def test_a_corrupt_record_is_passed_over_never_a_crash(self):
        """qwen C4: a record that is not an object, segments that cannot be hashed, or a word list with a stray
        non-object crashed the build (AttributeError / TypeError); each is now a named why."""
        ctx = E.Context(NOW, REG)
        with tempfile.TemporaryDirectory() as d:
            self.store_with(d, "vidA", SENTS)
            punct = os.path.join(d, "transcripts", "vidA", "transcript.whisper_words_punct.json")
            plain = os.path.join(d, "transcripts", "vidA", "transcript.whisper_words.json")
            with open(punct) as f:
                good = json.load(f)
            with open(punct, "w") as f:
                json.dump([1, 2, 3], f)
            with open(plain, "w") as f:
                json.dump(dict(good, segments="abc"), f)
            self.assertEqual(LB.word_source(row(SENTS[0]), ctx, d),
                             (None, None, ["transcript.whisper_words_punct.json: not a record (a JSON list)",
                                           "transcript.whisper_words.json: its segments cannot be hashed"]))
            with open(plain, "w") as f:
                json.dump(dict(good, words=good["words"] + ["oops"]), f)              # the sha still matches
            self.assertEqual(LB.word_source(row(SENTS[0]), ctx, d)[2][1],
                             "transcript.whisper_words.json: its words do not spell its sha-checked segments "
                             "(its words are not a list of objects)")

    def test_a_record_that_names_another_channel_is_passed_over(self):
        """glm C4 P2-1: the store record's own identity, when it names one, must be the ledger row's."""
        ctx = E.Context(NOW, REG)
        with tempfile.TemporaryDirectory() as d:
            self.store_with(d, "vidA", SENTS)                                    # names no channel: the row's stands
            self.assertIsNotNone(LB.word_source(row(SENTS[0]), ctx, d)[0])
            p = os.path.join(d, "transcripts", "vidA", "transcript.whisper_words_punct.json")
            with open(p) as f:
                rec = json.load(f)
            for cid, read in (("UCdd", True), ("UCother", False)):
                with open(p, "w") as f:
                    json.dump(dict(rec, channel_id=cid), f)
                src, _, passed_over = LB.word_source(row(SENTS[0]), ctx, d)
                self.assertEqual(src is not None, read, cid)
            self.assertEqual(passed_over, ["transcript.whisper_words_punct.json: it names channel UCother, the "
                                           "ledger row UCdd"])

    def test_only_the_stores_two_word_record_slots_are_read_in_a_fixed_order(self):
        """glm C3 P1-2: the order is total (punctuated, then verbatim), never the file system's; another name is no
        slot of the store's."""
        ctx = E.Context(NOW, REG)
        with tempfile.TemporaryDirectory() as d:
            self.store_with(d, "vidA", SENTS)
            os.rename(os.path.join(d, "transcripts", "vidA", "transcript.whisper_words_punct.json"),
                      os.path.join(d, "transcripts", "vidA", "transcript.whisper_words_punct_v2.json"))
            self.assertEqual(LB.word_source(row(SENTS[0]), ctx, d), (None, None, ["no word record in the store"]))
        self.assertEqual(LB.WORD_RECORDS, ("transcript.whisper_words_punct.json", "transcript.whisper_words.json"))

    def test_the_punctuated_record_is_read_first(self):
        """qwen C1 P0-1 / glm C1 P0-2: "punct" sorts first (key False < True); the verbatim record only as a fallback."""
        ctx = E.Context(NOW, REG)
        with tempfile.TemporaryDirectory() as d:
            self.store_with(d, "vidA", SENTS)                                   # transcript.whisper_words_punct.json
            punct = os.path.join(d, "transcripts", "vidA", "transcript.whisper_words_punct.json")
            plain = os.path.join(d, "transcripts", "vidA", "transcript.whisper_words.json")
            import shutil
            shutil.copy(punct, plain)                                           # both valid, both sentence-ready
            self.assertTrue(LB.word_source(row(SENTS[0]), ctx, d)[1].endswith("transcript.whisper_words_punct.json"))
            os.remove(punct)
            self.assertTrue(LB.word_source(row(SENTS[0]), ctx, d)[1].endswith("transcript.whisper_words.json"))

    def test_every_record_passed_over_is_named_and_a_fallback_shows(self):
        """Audit 2315 C2 (grok, qwen, glm): the reason was the LAST failure only, and a punctuated record rejected
        before a verbatim one was used left no trace."""
        ctx = E.Context(NOW, REG)
        unpunctuated = [" ".join(["bitcoin moves when the market moves"] * 12)]   # 72 words, no stop: not ready
        self.assertFalse(E.sentence_ready(source(unpunctuated, vid="vidA", method="whisper_words")))
        with tempfile.TemporaryDirectory() as d:
            self.store_with(d, "vidA", SENTS, break_sha=True)
            self.store_with(d, "vidA", unpunctuated, method="whisper_words")
            self.assertEqual(LB.word_source(row(SENTS[0]), ctx, d)[2],
                             ["transcript.whisper_words_punct.json: its segments do not match its transcript_sha256",
                              "transcript.whisper_words.json: not sentence-ready (law L-e)"])
            ms, _, rep = LB.build_inputs([row(SENTS[0])], ctx, d, log=lambda s: None)
            self.assertEqual(ms, [])
            self.assertEqual(rep["no_word_record_why"],
                             {"transcript.whisper_words_punct.json: its segments do not match its transcript_sha256; "
                              "transcript.whisper_words.json: not sentence-ready (law L-e)": 1})
            self.store_with(d, "vidA", SENTS, method="whisper_words")           # a verbatim record that IS ready
            ms, _, rep = LB.build_inputs([row(SENTS[0])], ctx, d, log=lambda s: None)
            self.assertEqual(len(ms), 1)
            self.assertEqual(rep["fallbacks"], {"vidA": {
                "used": "transcript.whisper_words.json",
                "passed_over": ["transcript.whisper_words_punct.json: its segments do not match its transcript_sha256"]}})

    def test_a_video_whose_rows_name_two_channels_is_dropped_whole(self):
        """Audit 2315 C2 (qwen P1, glm P1): one uploader per video is checked, never taken from the first row."""
        ctx = E.Context(NOW, REG)
        with tempfile.TemporaryDirectory() as d:
            self.store_with(d, "vidA", SENTS)
            other = dict(row(SENTS[2], mid="L2"), channel_id="UCother")
            ms, _, rep = LB.build_inputs([row(SENTS[0], mid="L1"), other], ctx, d, log=lambda s: None)
            self.assertEqual(ms, [])
            self.assertEqual(rep["channel_conflict"], {"vidA": {"rows": 2, "channel_ids": ["UCdd", "UCother"]}})

    def test_a_row_without_an_id_is_counted_never_a_crash(self):
        """qwen C3, glm C3 P1-4: a row without video_id crashed the grouping; two rows without moment_id took one key."""
        ctx = E.Context(NOW, REG)
        with tempfile.TemporaryDirectory() as d:
            self.store_with(d, "vidA", SENTS)
            rows = [row(SENTS[0], mid="L1"), {k: v for k, v in row(SENTS[1], mid="L2").items() if k != "video_id"},
                    {k: v for k, v in row(SENTS[2]).items() if k != "moment_id"},
                    {k: v for k, v in row(SENTS[3]).items() if k != "moment_id"}, "not a row"]
            ms, _, rep = LB.build_inputs(rows, ctx, d, log=lambda s: None)
            self.assertEqual([m["mined"]["ledger_moment_id"] for m in ms], ["L1"])
            self.assertEqual(sorted(rep["malformed"]), ["L2", "row 2", "row 3", "row 4"])
            ms, _, rep = LB.build_inputs([row(SENTS[0], vid="vidZ")], ctx, d, log=lambda s: None)
            self.assertEqual(rep["no_word_record_videos"], {"vidZ": {"rows": 1, "why": "no word record in the store"}})

    def test_rows_become_the_packagers_moments_with_every_drop_counted(self):
        ctx = E.Context(NOW, REG)
        with tempfile.TemporaryDirectory() as d:
            self.store_with(d, "vidA", SENTS)
            rows = [row(SENTS[0], mid="L1"), row(SENTS[0], mid="L2"),               # the same span twice
                    row("Ethereum is a world computer for everyone.", mid="L3"),  # does not anchor
                    row(SENTS[0], mid="L4", vid="vidZ"),                            # no word record for vidZ
                    {k: v for k, v in row(SENTS[3], mid="L5").items() if k != "scores"}]   # malformed: counted
            ms, srcs, rep = LB.build_inputs(rows, ctx, d, log=lambda s: None)
            self.assertEqual((rep["moments"], rep["duplicates"], rep["no_word_record"]), (1, 1, 1))
            self.assertEqual(rep["duplicates_of"], {"L2": "L1"})                 # glm C4 P2-5: the drop is named
            self.assertEqual(list(rep["not_anchored"]), ["L3"])
            self.assertEqual(list(rep["malformed"]), ["L5"])                   # glm C1 P1-8: never a crash
            m = ms[0]
            self.assertEqual(m["mined"]["ledger_moment_id"], "L1")
            self.assertEqual(m["scores"], rows[0]["scores"])                  # the ledger's judgment kept (glm P2-6)
            self.assertEqual(m["text"], SENTS[0])
            self.assertEqual(m["timing"], "word")
            self.assertIn("rank_score", m)
            self.assertEqual(set(srcs), {"vidA"})


class TestAdapter(unittest.TestCase):
    def test_a_failing_or_refusing_adapter_raises_never_an_empty_ledger(self):
        from datetime import timedelta
        fail = mock.Mock(returncode=1, stderr="Traceback ... boom", stdout="")
        with mock.patch("subprocess.run", return_value=fail):
            with self.assertRaises(RuntimeError):
                LB.rows(NOW - timedelta(hours=72), NOW)
        refused = mock.Mock(returncode=0, stderr="", stdout=json.dumps(
            {"rows": [], "report": {"contract": "unavailable: StoreGuard"}}))
        with mock.patch("subprocess.run", return_value=refused):
            with self.assertRaises(RuntimeError) as cm:
                LB.rows(NOW - timedelta(hours=72), NOW)
            self.assertIn("refused", str(cm.exception))
        ok = mock.Mock(returncode=0, stderr="", stdout=json.dumps({"rows": [{"moment_id": "x"}], "report": {}}))
        with mock.patch("subprocess.run", return_value=ok):
            self.assertEqual(LB.rows(NOW - timedelta(hours=72), NOW)[0], [{"moment_id": "x"}])
        import subprocess                                                    # glm C2 N-5: every failure is RuntimeError
        with mock.patch("subprocess.run", side_effect=subprocess.TimeoutExpired("python3", 300)):
            with self.assertRaises(RuntimeError) as cm:
                LB.rows(NOW - timedelta(hours=72), NOW)
            self.assertIn("did not answer", str(cm.exception))
        for stdout in ("", "not json", "[]", json.dumps({"rows": {}, "report": {}}), json.dumps({"report": {}})):
            with mock.patch("subprocess.run", return_value=mock.Mock(returncode=0, stderr="", stdout=stdout)):
                with self.assertRaises(RuntimeError, msg=stdout) as cm:
                    LB.rows(NOW - timedelta(hours=72), NOW)
                self.assertIn("cannot be read", str(cm.exception))
        empty = mock.Mock(returncode=0, stderr="", stdout=json.dumps(       # grok C1 P0 (reframed): a real empty read
            {"rows": [], "report": {"excluded": {"delivered in the previous 24 h": 3}}}))
        with mock.patch("subprocess.run", return_value=empty):
            rows, rep = LB.rows(NOW - timedelta(hours=72), NOW)
            self.assertEqual((rows, rep["excluded"]), ([], {"delivered in the previous 24 h": 3}))


class TestDriverRefuses(unittest.TestCase):
    def test_the_driver_reads_the_delivered_pins_before_writing_and_refuses_a_bad_one(self):
        """Audit 2315 C2 (grok, qwen, glm): no hard-coded delivered pins; a pin that cannot be read, has no clip or no
        zoned approved_at refuses the run (exit 2) before any proof dir exists; 'since' defaults to the newest
        delivered pin's approved_at (ruling 2: "best_unused_moments since the last delivered video")."""
        sys.path.insert(0, HERE)
        import proof_ledger as PLG
        pins = [os.path.join(HERE, "proof", "fresh_20261112_050611", n) for n in ("MOMENTS_PIN.json",
                                                                                 "MOMENTS_PIN_LY.json")]
        spans, newest, info = PLG.delivered_pins(pins)
        self.assertEqual(newest.isoformat(), "2026-11-13T03:01:09+00:00")              # the 41f29b1f medley
        self.assertEqual(len(spans), sum(i["clips"] for i in info))
        proof = os.path.join(HERE, "proof")
        before = sorted(n for n in os.listdir(proof) if n.startswith("ledger_"))
        with tempfile.TemporaryDirectory() as d, mock.patch("sys.stderr", new=io.StringIO()):
            with open(pins[1]) as f:
                pin = json.load(f)
            for name, bad in (("naive.json", dict(pin, approved_at="2026-11-13T03:01:09")),
                              ("empty.json", dict(pin, segments=[]))):
                with open(os.path.join(d, name), "w") as f:
                    json.dump(bad, f)
            for argv in (["--delivered", os.path.join(d, "missing.json")],
                         ["--delivered", os.path.join(d, "naive.json")],
                         ["--delivered", os.path.join(d, "empty.json")],
                         ["--delivered", *pins, "--since", "2099-01-01T00:00:00+00:00"],
                         ["--delivered", *pins, "--since", "2026-11-13T03:01:09"]):
                self.assertEqual(PLG.main(argv), 2, argv)
            with self.assertRaises(SystemExit):
                PLG.main([])                                                            # --delivered is required
            nostart = dict(pin, segments=[{k: v for k, v in pin["segments"][0].items() if k != "start"}])
            with open(os.path.join(d, "nostart.json"), "w") as f:
                json.dump(nostart, f)
            with self.assertRaises(ValueError) as cm:                                   # glm C3 P2-3: which pin
                PLG.delivered_pins([pins[0], os.path.join(d, "nostart.json")])
            self.assertIn("nostart.json", str(cm.exception))
        self.assertEqual(sorted(n for n in os.listdir(proof) if n.startswith("ledger_")), before)

    def test_a_moment_overlapping_any_delivered_span_is_out_whatever_the_pins_age(self):
        """Audit 2315 C3 K7 (grok, glm): the adapter's delivered_ids (ledger moment ids, 24 h) stay empty: tonight's
        pins carry no ledger id. L-p is carried by package.usable, which drops any moment that overlaps a delivered
        span of the same video, and the driver passes every delivered pin's spans, whatever the pin's age."""
        sys.path.insert(0, HERE)
        import package as PK
        import proof_ledger as PLG
        with open(os.path.join(HERE, "proof", "fresh_20261112_050611", "MOMENTS_PIN_LY.json")) as f:
            pin = json.load(f)
        old = dict(pin, approved_at="2026-10-01T00:00:00+00:00",
                   segments=[dict(pin["segments"][0], video_id="vidA", start=15.0, end=25.0)])
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "old.json"), "w") as f:
                json.dump(old, f)
            spans, _, _ = PLG.delivered_pins([os.path.join(d, "old.json")])
        m = {"moment_id": "m1", "video_id": "vidA", "channel_id": "UCdd", "on_screen_ok": True, "duration_s": 8.0,
             "published_at": NOW.isoformat(), "text": SENTS[0]}
        for start, end, out in ((20.0, 28.0, True), (10.0, 16.0, True), (25.0, 33.0, False), (5.0, 15.0, False)):
            ok, why = PK.usable([dict(m, start=start, end=end)], E.Context(NOW, REG), delivered=spans)
            self.assertEqual("m1" in why, out, (start, end))
            if out:
                self.assertIn("overlaps a delivered moment", why["m1"])


if __name__ == "__main__":
    unittest.main()
