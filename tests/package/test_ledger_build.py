#!/usr/bin/env python3
"""pipeline/ledger_build.py (ORCHESTRATOR 22:40 ruling 2): the medley built from the ingest ledger. Offline:
- re-anchoring a ledger row's TEXT in a word record and snapping it to that record's whole sentences;
- reading the store's word record (its sha checked, sentence-ready only);
- turning rows into the packager's moments (counted drops, no duplicate spans);
- the adapter's failures are raised, never read as an empty ledger."""
import contextlib
import hashlib
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
from test_eligibility import NOW, REG, source, tokens  # noqa: E402

SENTS = ["Bitcoin is a global free market.", "Nobody can stop Bitcoin from settling a payment.",
         "That is the whole design and it works every day.", "Bitcoin does not ask for permission.",
         "In 2009 Bitcoin started as a quiet experiment."]


@contextlib.contextmanager
def refused_only():
    """A refusal test's guard: a driver run that gets past its refusal block fails here, before it can write a proof
    dir or reach the network (16:45 Nov 13: a mutation check of a refusal test ran the driver on, in a scratch copy;
    it spent nothing, but only because that copy lacked a directory)."""
    with mock.patch("urllib.request.urlopen", side_effect=AssertionError("a refused run reached the network")), \
            mock.patch("os.makedirs", side_effect=AssertionError("a refused run went on to write a proof dir")):
        yield


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

    def test_a_caption_text_snaps_outward_to_the_records_whole_sentences(self):
        """Ruling 32 (02:45 ET Nov 13): any number of the speaker's own words is added, within 20 s, no speaker
        change; the added words are recorded."""
        sp, info = LB.reanchor(row("is a global free market."), self.src)              # 1 word short
        self.assertEqual(((sp.k0, sp.k1), info["snapped_words"]), ((0, 0), [1, 0]))
        self.assertEqual(info["added"], {"before": "Bitcoin", "after": ""})
        sp, info = LB.reanchor(row("design and it works every day."), self.src)         # 4 words: refused before 32
        self.assertEqual(((sp.k0, sp.k1), info["snapped_words"]), ((2, 2), [4, 0]))
        self.assertEqual(info["added"]["before"], "That is the whole")
        self.assertEqual(sp.text, E.spoken(self.src.tokens[sp.w0:sp.w1 + 1]))     # the word record's own words

    def test_a_snap_adds_the_speakers_own_negation_or_number_and_records_it(self):
        """Ruling 32 retires SNAP_GUARD (audit 2315 C1): 'can stop Bitcoin' snapped to 'Nobody can stop Bitcoin'
        restores what the speaker said. Step A, the exclusion verdict and L-v 2 judge the snapped span; the added
        words are on the record."""
        for text, before in (("can stop Bitcoin from settling a payment.", "Nobody"),
                             ("Bitcoin started as a quiet experiment.", "In 2009")):
            sp, info = LB.reanchor(row(text), self.src)
            self.assertIsNotNone(sp, text)
            self.assertEqual(info["added"]["before"], before)
        for word in ("Hardly", "Don\u2019t"):
            src = source([f"{word} anyone can stop Bitcoin from settling a payment.", "That is the plan."])
            sp, info = LB.reanchor(row("anyone can stop Bitcoin from settling a payment."), src)
            self.assertEqual(info["added"]["before"], word)

    def test_the_snap_limit_is_the_packagers_clip_limit(self):                 # audit 0332 C1, qwen P2-1
        import package as PK
        self.assertEqual(LB.SNAP_MAX_S, PK.SEG_MAX_S)

    def test_a_snap_longer_than_20_s_stays_out(self):
        long_ = "Bitcoin " + " ".join(["keeps"] * 72) + " settling payments."             # 75 words, 0.3 s each
        src = source([long_, "That is the plan."])
        a, b = src.sentences[0]
        self.assertGreater(src.tokens[b]["end"] - src.tokens[a]["start"], LB.SNAP_MAX_S)
        sp, why = LB.reanchor(row(" ".join(["keeps"] * 8) + " settling payments."), src)
        self.assertIsNone(sp)
        self.assertIn("> 20 s (ruling 32", why)
        sp, info = LB.reanchor(row(long_), src)                       # whole sentences: no snap, usable() measures it
        self.assertEqual(info["snapped_words"], [0, 0])

    def test_a_caption_speaker_marker_inside_the_snapped_span_keeps_the_row_out(self):
        a = self.src.tokens[self.src.sentences[1][0]]["start"]
        b = self.src.tokens[self.src.sentences[1][1]]["end"]
        cap = lambda *ts: type("Cap", (), {"tokens": [{"word": "&gt;&gt;", "start": x} for x in ts]})()
        text = "can stop Bitcoin from settling a payment."
        sp, why = LB.reanchor(row(text), self.src, cap=cap((a + b) / 2))
        self.assertIsNone(sp)
        self.assertIn("caption speaker marker", why)
        self.assertIsNone(LB.reanchor(row(text), self.src, cap=type("C", (), {"tokens": [
            {"word": ">>", "start": (a + b) / 2}]})())[0])                                # the raw form too
        for c in (cap(a + 0.5), cap(b - 0.5), None, cap()):        # at an edge, no record, no marker: L-v 2 decides
            self.assertIsNotNone(LB.reanchor(row(text), self.src, cap=c)[0])
        self.assertIsNotNone(LB.reanchor(row(SENTS[1]), self.src, cap=cap((a + b) / 2))[0])   # no snap: no read
        for x in (a + LB.MARKER_EDGE_S, b - LB.MARKER_EDGE_S):        # exactly 1.0 s from an edge: not inside (the
            self.assertIsNone(LB.marker_inside(cap(x), a, b))           # strict convention, audit 0332 C2 glm N1)
        self.assertEqual(LB.marker_inside(cap(a + LB.MARKER_EDGE_S + 0.01), a, b), a + LB.MARKER_EDGE_S + 0.01)

    def test_a_snapped_moment_counts_its_own_price_prediction(self):
        info = {"snapped_words": [4, 0]}
        self.assertEqual(LB.snap_risk("Bitcoin will hit 250,000 by 2030. It is coming.", info, []),
                         ["price_prediction"])
        self.assertEqual(LB.snap_risk("Bitcoin will hit 250,000 by 2030.", {"snapped_words": [0, 0]}, []), [])
        self.assertEqual(LB.snap_risk("Bitcoin is at 70,000 today.", info, ["time_sensitive"]), ["time_sensitive"])
        self.assertEqual(LB.snap_risk("Bitcoin will hit 250,000 by 2030.", info, ["price_prediction"]),
                         ["price_prediction"])
        with self.assertRaises(TypeError):                                     # a malformed row, never mangled
            LB.snap_risk("Bitcoin will hit 250,000 by 2030.", info, "price_prediction")

    def test_the_hit_is_measured_against_the_rows_own_caption_times(self):
        """glm C3 P1-3: a phrase said twice inside the search window would anchor on the earliest longest match; the
        offset of the hit from the row's caption times is recorded, so such a hit is visible."""
        a, b = self.src.sentences[1]
        t0, t1 = self.src.tokens[a]["start"], self.src.tokens[b]["end"]
        sp, info = LB.reanchor(row(SENTS[1], start=t0 + 2.0, end=t1 - 1.0), self.src)
        self.assertEqual(info["offset_s"], [-2.0, 1.0])
        self.assertEqual(LB.reanchor(row(SENTS[1]), self.src)[1]["offset_s"],      # glm C4 P2-8: said, not absent
                         "unmeasured: the row has no readable caption times")

    def test_text_cut_at_both_edges_snaps_and_text_that_is_not_there_is_dropped_with_why(self):
        sp, info = LB.reanchor(row("from settling a payment. That is the whole design"), self.src)  # 4 + 5 words cut
        self.assertEqual(((sp.k0, sp.k1), info["snapped_words"]), ((1, 2), [4, 5]))
        self.assertEqual(info["added"], {"before": "Nobody can stop Bitcoin", "after": "and it works every day."})
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

    def test_a_snapped_moment_carries_its_price_prediction_into_the_moment(self):     # audit 0332 C2, glm N2
        ctx = E.Context(NOW, REG)
        sents = ["Bitcoin is a global free market.", "Bitcoin will hit 250,000 by 2030 and it will happen fast.",
                 "That is the whole design and it works every day."]
        with tempfile.TemporaryDirectory() as d:
            self.store_with(d, "vidA", sents)
            ms, _, rep = LB.build_inputs([row("and it will happen fast.")], ctx, d, log=lambda s: None)
            self.assertEqual(len(ms), 1, rep["not_anchored"])
            self.assertEqual(ms[0]["mined"]["reanchored"]["snapped_words"], [6, 0])
            self.assertIn("price_prediction", ms[0]["risk"])                 # counted by the per-video cap (L-u)
            ms, _, _ = LB.build_inputs([row(sents[1])], ctx, d, log=lambda s: None)
            self.assertEqual(ms[0]["risk"], [])                               # not snapped: the miner's own flags

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
                              "transcript.whisper_words.json: not sentence-ready (law L-e); "
                              "no sentence-ready window record": 1})
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
            self.assertEqual(rep["no_word_record_videos"], {"vidZ": {"rows": 1, "why": "no word record in the store; "
                                                                                 "no sentence-ready window record"}})

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


SENTS_W = ["So we were talking about money before the break.", "Bitcoin is a global free market.",
           "Nobody can stop Bitcoin from settling a payment.", "That is the whole design and it works every day.",
           "Anyway, let us move on to the next question."]


def window_fixture(d, vid="vidW", w0=600.0, still=False, clock="youtube", caption=True, cap_from=0, cap_to=900,
                   duration=900.0, cap_gap=None):
    """A window record exactly as the word-pass worker's make_record writes it (words on the YouTube clock, segments
    from sentences_from_words, words_sha256, window, punctuation), its word_pass.jsonl row, and the full-video caption
    record the ledger mined from (unpunctuated lines over the whole video)."""
    words = [{"word": t["word"], "start": t["start"], "end": t["end"]} for t in tokens(SENTS_W, t0=w0 + 1.0)]
    segs = [{"start": round(x["start"], 3), "end": round(x["end"], 3), "text": x["text"].strip()}
            for x in ts.sentences_from_words(words)]
    w1 = round(words[-1]["end"] + 1.0, 3)
    rec = {"video_id": vid, "transcript_method": "whisper_words_punct", "segments": segs,
           "transcript_sha256": ts.segments_sha256(segs), "words": words,
           "words_sha256": hashlib.sha256(json.dumps([[w["word"], w["start"], w["end"]] for w in words],
                                                     ensure_ascii=False).encode()).hexdigest(),
           "punctuation": {"still_unpunctuated": still},
           "window": {"start_s": w0, "end_s": w1, "clock": clock, "offset_s": w0}}
    rel = f"transcripts/{vid}/windows/{w0:.3f}-{w1:.3f}.whisper_words_punct.json"
    os.makedirs(os.path.dirname(os.path.join(d, rel)), exist_ok=True)
    with open(os.path.join(d, rel), "w") as f:
        json.dump(rec, f)
    with open(os.path.join(d, rel), "rb") as f:
        sha = hashlib.sha256(f.read()).hexdigest()
    wp = {"moment_id": "W1", "video_id": vid, "window_record": rel, "record_sha256": sha, "sentence_ready": not still,
          "window": [w0, w1], "at": "2026-11-13T06:00:00+00:00"}
    cap = None
    if caption:
        lines = [{"start": float(t), "end": float(t + 5), "text": f"caption line {t} about money"}
                 for t in range(cap_from, cap_to, 5) if not (cap_gap and cap_gap[0] <= t < cap_gap[1])]
        cap = ts.segments_sha256(lines)
        with open(os.path.join(d, "transcripts", vid, "transcript.yt_auto.json"), "w") as f:
            json.dump({"video_id": vid, "transcript_method": "yt_auto", "segments": lines, "transcript_sha256": cap,
                       "duration": duration}, f)
    k = [i for i, t in enumerate(words) if t["word"] == "Nobody"][0]
    n = len(SENTS_W[2].split())
    r = dict(row(SENTS_W[2], start=words[k]["start"], end=words[k + n - 1]["end"], mid="W1", vid=vid),
             transcript_sha256=cap)
    return rel, wp, r, words


class TestWindowRecords(unittest.TestCase):
    """The integrator's word-pass worker (word-pass 514dd704): window records listed in moments/word_pass.jsonl."""

    def test_the_word_pass_index_reads_each_moments_last_ready_row_and_counts_the_rest(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "word_pass.jsonl")
            self.assertEqual(LB.word_pass_index(p)[0], {})                          # no file yet: no window record
            rows = [{"moment_id": "A", "window_record": None, "record_sha256": None, "sentence_ready": False,
                     "error": "word pass: boom"},
                    {"moment_id": "B", "window_record": "x", "record_sha256": "s", "sentence_ready": False},
                    {"moment_id": "C", "window_record": "x", "record_sha256": "s1", "sentence_ready": True},
                    {"moment_id": "C", "window_record": "y", "record_sha256": "s2", "sentence_ready": True,
                     "reused": True}]
            with open(p, "w") as f:
                f.write("\n".join(json.dumps(r) for r in rows) + "\nnot json\n")
            idx, rep = LB.word_pass_index(p)
            self.assertEqual(list(idx), ["C"])
            self.assertEqual(idx["C"]["record_sha256"], "s2")                       # the last row of a moment wins
            self.assertEqual((rep["failed"], rep["not_ready"], rep["ready"], rep["unreadable"]), (1, 1, 1, 1))

    def test_a_window_record_is_used_only_when_every_claim_checks_out(self):
        ctx = E.Context(NOW, REG)
        with tempfile.TemporaryDirectory() as d:
            rel, wp, r, words = window_fixture(d)
            src, path, why = LB.window_source(r, wp, ctx, d)
            self.assertIsNone(why)
            self.assertEqual((src.timing, src.file_head, src.window["start_s"]), ("word", False, 600.0))
            p = os.path.join(d, rel)
            with open(p) as f:
                good = json.load(f)

            def tampered(rec, **row_change):
                with open(p, "w") as f:
                    json.dump(rec, f)
                with open(p, "rb") as f:
                    sha = hashlib.sha256(f.read()).hexdigest()
                return LB.window_source(dict(r, **row_change.get("row", {})), dict(wp, record_sha256=sha), ctx, d)[2]
            w = [dict(x) for x in good["words"]]
            w[3]["start"] += 0.05                                     # an INTERIOR word's time: only words_sha256 sees it
            self.assertIn("words_sha256", tampered(dict(good, words=w)))
            self.assertIn("still unpunctuated", tampered(dict(good, punctuation={"still_unpunctuated": True})))
            self.assertIn("YouTube clock", tampered(dict(good, window=dict(good["window"], clock="window"))))
            self.assertIn("not inside the window", tampered(good, row={"start": 10.0, "end": 20.0}))
            self.assertIn("transcript_sha256", tampered(dict(good, transcript_sha256="0" * 64)))
            self.assertIn("not a punctuated word record", tampered(dict(good, transcript_method="whisper_words")))
            self.assertIn("names channel UCother", tampered(dict(good, channel_id="UCother")))
            segs = [dict(x) for x in good["segments"]]
            segs[1]["start"] = segs[1]["start"] + 0.5                     # a segment edge off its first word's time
            self.assertIn("do not spell", tampered(dict(good, segments=segs, transcript_sha256=ts.segments_sha256(segs))))
            with open(p, "w") as f:
                json.dump(good, f)
            self.assertIn("record_sha256", LB.window_source(r, dict(wp, record_sha256="0" * 64), ctx, d)[2])
            self.assertIn("not this video's window record",
                          LB.window_source(r, dict(wp, window_record="transcripts/vidW/x.json"), ctx, d)[2])

    def test_a_window_from_the_media_start_is_file_head(self):
        with tempfile.TemporaryDirectory() as d:
            rel, wp, r, words = window_fixture(d, w0=0.0)
            self.assertTrue(LB.window_source(r, wp, E.Context(NOW, REG), d)[0].file_head)

    def test_a_video_without_a_full_record_is_built_from_its_window_with_caption_context(self):
        import context_integrity as CI
        ctx = E.Context(NOW, REG)
        with tempfile.TemporaryDirectory() as d:
            rel, wp, r, words = window_fixture(d)
            far = dict(row("Bitcoin started as a quiet experiment.", start=100.0, end=104.0, mid="W2", vid="vidW"),
                       transcript_sha256=r["transcript_sha256"])               # no window record of its own
            ms, srcs, rep = LB.build_inputs([r, far], ctx, d, log=lambda s: None, word_pass={"W1": wp})
            self.assertEqual([m["mined"]["ledger_moment_id"] for m in ms], ["W1"])
            self.assertEqual(ms[0]["text"], SENTS_W[2])
            self.assertEqual((list(rep["not_anchored"]), rep["window_waiting"]), ([], 1))   # it waits for its own
            self.assertEqual(rep["window_records"], {"vidW": [rel]})
            self.assertEqual(ms[0]["source_key"], f"vidW@600.000-{wp['window'][1]:.3f}")   # one window per moment
            src = srcs[ms[0]["source_key"]]
            self.assertEqual(src.context_source.transcript_method, "yt_auto")
            text, win = CI._window_text(src, ms[0]["sentences"][0], ms[0]["sentences"][1], *ms[0]["words"])
            t0 = words[[w["word"] for w in words].index("Nobody")]["start"]
            self.assertLessEqual(win[0], t0 - CI.CONTEXT_BEFORE_S)                  # at least 90 s covered before
            self.assertGreater(win[0], t0 - CI.CONTEXT_BEFORE_S - 5.0)                  # (one caption line over)
            self.assertEqual(ms[0]["mined"]["window"]["record"], rel)                    # provenance in the moment
            self.assertEqual(ms[0]["mined"]["window"]["context_record"], "yt_auto")
            self.assertIn(f"caption line {int(t0 - 85) // 5 * 5} about money", text)   # the caption, 85 s before
            self.assertIn("<selected>" + SENTS_W[2] + "</selected>", text)            # the window's own words
            before, after = CI.context_around(src, ms[0]["sentences"][0], ms[0]["sentences"][1], *ms[0]["words"])
            self.assertIn("caption line", before)
            self.assertIn("caption line", after)

    def test_each_moment_reads_its_own_window_and_the_same_speech_twice_is_one_moment(self):
        """The 02:01 FRESH build kept ONE window per video and lost 63 of 74 rows. The worker writes a window around
        every moment, so each moment re-anchors in its OWN window (its source_key); two windows holding the same
        speech give one moment (the better-ranked row keeps it)."""
        ctx = E.Context(NOW, REG)
        with tempfile.TemporaryDirectory() as d:
            rel1, wp1, r1, words1 = window_fixture(d, w0=600.0)               # W1: "Nobody can stop Bitcoin ..."
            rel2, wp2, r2, words2 = window_fixture(d, w0=640.0)               # W2: the same sentences, 40 s later
            k = [w["word"] for w in words2].index("That")
            n = len(SENTS_W[3].split())
            r2 = dict(row(SENTS_W[3], start=words2[k]["start"], end=words2[k + n - 1]["end"], mid="W2", vid="vidW"),
                      transcript_sha256=r1["transcript_sha256"])
            wp2 = dict(wp2, moment_id="W2")
            r3 = dict(r1, moment_id="W3")                                    # W1's speech again (W1's window record)
            ms, srcs, rep = LB.build_inputs([r1, r2, r3], ctx, d, log=lambda s: None,
                                            word_pass={"W1": wp1, "W2": wp2, "W3": dict(wp1, moment_id="W3")})
            self.assertEqual(sorted(m["mined"]["ledger_moment_id"] for m in ms), ["W1", "W2"])
            keys = {m["mined"]["ledger_moment_id"]: m["source_key"] for m in ms}
            self.assertNotEqual(keys["W1"], keys["W2"])                       # two windows, two Sources
            self.assertEqual(set(srcs), set(keys.values()))
            self.assertEqual(rep["duplicates_of"], {"W3": "W1"})              # the same speech: one moment
            self.assertEqual((rep["videos"], rep["sources"]), (1, 2))
            import context_integrity as CI                                     # the gate reads each segment's own
            m2 = next(m for m in ms if m["mined"]["ledger_moment_id"] == "W2")  # window (package.src_of's key)
            seg = {"label": "clip_01", "video_id": "vidW", "source_key": m2["source_key"], "k0": m2["sentences"][0],
                   "k1": m2["sentences"][1], "words": m2["words"], "channel": "DataDash"}
            got = CI.contexts_from_sources({"segments": [seg]}, srcs)
            self.assertIn("<selected>" + SENTS_W[3] + "</selected>", got["clip_01"]["text"])
            self.assertIn("caption line", got["clip_01"]["text"])
            lost = dict(seg, source_key="vidW@1.000-2.000")                   # a key that is not in sources: the
            with self.assertRaises(KeyError):                                 # gate fails closed (one lookup rule,
                CI.contexts_from_sources({"segments": [lost]}, srcs)         # audit 0208 C1: glm, qwen) ...
            import speakers as SP                                             # ... and the speaker is "unknown",
            pk = {"segments": [dict(lost)]}                                   # not measured, with no call made
            SP.attribute_package(None, pk, srcs, meta_for=lambda v: {"exact_title": "t"}, log=lambda s: None)
            self.assertEqual((pk["segments"][0]["speaker"]["name"], pk["segments"][0]["speaker"]["measured"]),
                             ("unknown", False))

    def test_the_caption_coverage_is_measured_never_assumed(self):
        """Audit 0123 C1 (qwen, glm): a caption that stops short of 60 s after the clip (and short of the media's end),
        or starts after the 90 s before it (and not near the media's start), leaves the context unavailable."""
        import context_integrity as CI
        ctx = E.Context(NOW, REG)
        for kw, ok in (({"cap_to": 650}, False),                         # stops at 650 s; the clip ends ~616 s
                       ({"cap_to": 650, "duration": 660.0}, True),        # ... but 650 s is the media's end, nearly
                       ({"cap_from": 560}, False),                        # starts 560 s; 90 s before is ~526 s
                       ({}, True)):
            with tempfile.TemporaryDirectory() as d:
                rel, wp, r, words = window_fixture(d, **kw)
                ms, srcs, rep = LB.build_inputs([r], ctx, d, log=lambda s: None, word_pass={"W1": wp})
                m = ms[0]
                text, win = CI._window_text(srcs[m["source_key"]], m["sentences"][0], m["sentences"][1], *m["words"])
                self.assertEqual(text is not None, ok, kw)

    def test_a_wordless_stretch_inside_the_window_is_bridged_to_reach_the_marks(self):
        """Audit 0123 C2 (grok P2-1, glm N1): the words must reach 90 s back and 60 s on, as window() does for a
        full-video record, across a stretch with no words (music) inside the window."""
        import context_integrity as CI
        ctx = E.Context(NOW, REG)
        with tempfile.TemporaryDirectory() as d:
            rel, wp, r, words = window_fixture(d, cap_gap=(515, 585))        # nothing said from 515 s to 585 s
            ms, srcs, rep = LB.build_inputs([r], ctx, d, log=lambda s: None, word_pass={"W1": wp})
            m = ms[0]
            t0 = words[[w["word"] for w in words].index("Nobody")]["start"]
            text, win = CI._window_text(srcs[m["source_key"]], m["sentences"][0], m["sentences"][1], *m["words"])
            self.assertLessEqual(win[0], t0 - CI.CONTEXT_BEFORE_S)          # it reaches past the gap
            self.assertLess(win[0], 515.0)                                     # a word from before the gap ...
            self.assertTrue(text.startswith("money caption line 585"))        # ... ("money", the last word of line 510)
            self.assertGreaterEqual(win[1], m["end"] + CI.CONTEXT_AFTER_S)

    def test_the_ledgers_own_record_is_found_and_differing_matches_are_ambiguous(self):
        """The first FRESH build: 8 of 16 window videos had their caption record only in the ledger's store
        (pp-ingest's), not in main's. A copy with the same words is one record; same-sha matches whose words differ
        are ambiguous (audit 0123 C1, glm P0-1), so there is no context."""
        ctx = E.Context(NOW, REG)
        with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as led:
            rel, wp, r, words = window_fixture(d)
            src = os.path.join(d, "transcripts", "vidW", "transcript.yt_auto.json")
            os.makedirs(os.path.join(led, "transcripts", "vidW"))
            with open(src) as f:
                cap = json.load(f)
            os.remove(src)                                                   # only in the ledger's store
            with open(os.path.join(led, "transcripts", "vidW", "transcript.yt_auto.json"), "w") as f:
                json.dump(cap, f)
            self.assertIsNone(LB.caption_source(r, ctx, d)[0])                  # main's store alone: none
            cs, where = LB.caption_source(r, ctx, d, led)
            self.assertEqual((cs.transcript_method, where), ("yt_auto", "ledger/transcript.yt_auto.json"))
            with open(src, "w") as f:                                         # the same record in main's store too
                json.dump(cap, f)
            self.assertEqual(LB.caption_source(r, ctx, d, led)[1], "main/transcript.yt_auto.json")
            odd = dict(cap, words=[{"word": "other", "start": 1.0, "end": 1.5}])    # same segments sha, other words
            with open(os.path.join(d, "transcripts", "vidW", "transcript.yt_manual.json"), "w") as g:
                json.dump(odd, g)
            cs, why = LB.caption_source(r, ctx, d, led)
            self.assertIsNone(cs)
            self.assertIn("ambiguous", why)
            os.remove(os.path.join(d, "transcripts", "vidW", "transcript.yt_manual.json"))
            with open(src, "w") as f:                                        # glm C2 N2: unreadable is said, not
                f.write("{not json")                                         # "no record matches" alone
            self.assertIn("1 transcript file(s) could not be read", LB.caption_source(r, E.Context(NOW, REG), d)[1])

    def test_a_moment_without_context_never_poisons_its_step_a_batch(self):
        """The first FRESH build: one window moment without a caption record in a step-A batch made the batch's call
        fail, and EVERY moment in it was marked unavailable (0 cleared in 0 s). Now that moment alone is not cleared."""
        import context_integrity as CI
        import package as PK
        ctx = E.Context(NOW, REG)
        with tempfile.TemporaryDirectory() as d:
            rel, wp, r, words = window_fixture(d, caption=False)              # a window without its caption
            TestWordSourceAndInputs.store_with(self, d, "vidA", SENTS)        # a full-video record, other channel
            ra = dict(row(SENTS[1], mid="A1", vid="vidA"), channel_id="UCother", channel_name="Other")
            ms, srcs, rep = LB.build_inputs([r, ra], ctx, d, log=lambda s: None, word_pass={"W1": wp})
            self.assertEqual(sorted(m["mined"]["ledger_moment_id"] for m in ms), ["A1", "W1"])
            sent = []

            def step_a(router, contexts, *a, **k):
                sent.append(sorted(contexts))
                return {mid: dict(sent=True) for mid in contexts}, "xai:grok"
            saved, CI.step_a = CI.step_a, step_a
            try:
                router = type("R", (), {"backends": {}})()
                a_by, fails, v, f = PK.prescreen(router, ms, srcs, ctx, "heimdall", log=lambda s: None)
            finally:
                CI.step_a = saved
            mid_w = next(m["moment_id"] for m in ms if m["mined"]["ledger_moment_id"] == "W1")
            mid_a = next(m["moment_id"] for m in ms if m["mined"]["ledger_moment_id"] == "A1")
            self.assertEqual(sent, [[mid_a]])                                  # the batch still went out
            self.assertTrue(fails[mid_w][0].startswith("CONTEXT_UNAVAILABLE"))
            self.assertIn(mid_a, a_by)

    def test_the_exclusion_verdict_reads_the_caption_context(self):
        """glm C1 P2-7: the normal path, measured: the verdict's prompt carries the caption's words around the clip."""
        import package as PK

        class Canned:
            def __init__(self):
                self.prompts = []

            def call(self, role, prompt, max_tokens=2000, seed=7, **k):
                self.prompts.append(prompt)
                return type("R", (), {"text": json.dumps({"risks": [], "about_bitcoin": "yes", "why": "ok"}),
                                      "backend": "xai:grok", "replayed": False})()

            def reject(self, r):
                pass
        with tempfile.TemporaryDirectory() as d:
            rel, wp, r, words = window_fixture(d)
            ms, srcs, rep = LB.build_inputs([r], E.Context(NOW, REG), d, log=lambda s: None, word_pass={"W1": wp})
            router = Canned()
            ex = PK.exclusion_for(router, ms[0], srcs, {})
            self.assertEqual((ex["verdict"], ex["measured"]), ("keep", True))
            self.assertIn("caption line", router.prompts[0])

    def test_a_window_without_its_caption_record_has_no_context_and_fails_closed(self):
        import context_integrity as CI
        import package as PK
        ctx = E.Context(NOW, REG)
        with tempfile.TemporaryDirectory() as d:
            rel, wp, r, words = window_fixture(d, caption=False)
            ms, srcs, rep = LB.build_inputs([r], ctx, d, log=lambda s: None, word_pass={"W1": wp})
            self.assertEqual(rep["no_caption_context"], {"vidW": "no record in the store matches the row's "
                                                                  "transcript_sha256"})
            m = ms[0]
            self.assertEqual(CI._window_text(srcs[m["source_key"]], m["sentences"][0], m["sentences"][1], *m["words"]),
                             (None, None))                                 # step A: unavailable, never cleared
            ex = PK.exclusion_for(None, m, srcs, {})                       # no model call is made
            self.assertEqual((ex["verdict"], ex["measured"]), ("exclude", False))


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
        with tempfile.TemporaryDirectory() as d, mock.patch("sys.stderr", new=io.StringIO()), refused_only():
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

    def test_a_malformed_candidate_registry_refuses_the_run_before_anything_is_written(self):
        """Ruling 66 (audit 1420b C1: grok, qwen, glm): the registry is read, seeded and its times read (CA.due) in
        the refusal block: a malformed stored time refuses the run (exit 2) and nothing is written."""
        sys.path.insert(0, HERE)
        import proof_ledger as PLG
        pins = [os.path.join(HERE, "proof", "fresh_20261112_050611", n) for n in ("MOMENTS_PIN.json",
                                                                                 "MOMENTS_PIN_LY.json")]
        proof = os.path.join(HERE, "proof")
        before = sorted(n for n in os.listdir(proof) if n.startswith("ledger_") or n == "CANDIDATES.json")
        with tempfile.TemporaryDirectory() as d, mock.patch("sys.stderr", new=io.StringIO()) as err, refused_only():
            reg = os.path.join(d, "CANDIDATES.json")
            with open(reg, "w") as f:
                json.dump({"records": [], "candidates": {"x+y+z": {
                    "lineup": ["x", "y", "z"], "source": "r", "index": 0, "found_at": "tomorrow", "state": "open",
                    "until": None, "fresh_used": False, "history": []}}}, f)
            with open(reg) as f:
                was = f.read()
            with mock.patch.object(PLG, "REGISTRY", reg):
                self.assertEqual(PLG.main(["--delivered", *pins]), 2)
            self.assertIn("registry", err.getvalue())
            with open(reg) as f:
                self.assertEqual(f.read(), was)                                     # never rewritten
            for bad in (None, ["x", "y"]):                      # a line-up the search could not leave alone
                with open(reg, "w") as f:
                    json.dump({"records": [], "candidates": {"x+y+z": {
                        "lineup": bad, "source": "r", "index": 0, "found_at": "2026-11-13T19:00:00+00:00",
                        "state": "open", "until": None, "fresh_used": False, "history": []}}}, f)
                with open(reg) as f:
                    was = f.read()
                with mock.patch.object(PLG, "REGISTRY", reg):
                    self.assertEqual(PLG.main(["--delivered", *pins]), 2, bad)
                self.assertIn("matching its key", err.getvalue())
                with open(reg) as f:
                    self.assertEqual(f.read(), was)
        self.assertEqual(sorted(n for n in os.listdir(proof) if n.startswith("ledger_") or n == "CANDIDATES.json"),
                         before)

    def test_ruling_82_the_context_verdict_chain(self):
        """RULING 82 (20:02 Nov 13): with the frozen legs out, step A's chain is xAI first, then the three Heimdall
        models in the ruled order; glm-5.3-flash is a Heimdall back-end of its own family."""
        sys.path.insert(0, HERE)
        import proof_ly as PL
        self.assertEqual(PL.chains()["context_verdict"], ["xai:grok-4.20-0309-reasoning",
                                                          "heimdall:deepseek/deepseek-v4.1-flash",
                                                          "heimdall:z-ai/glm-5.3-flash", "heimdall:qwen/qwen3.8-27b"])
        with open(os.path.join(REPO, "pipeline", "model_providers.json")) as f:
            glm = json.load(f)["backends"]["heimdall:z-ai/glm-5.3-flash"]
        self.assertEqual((glm["vendor"], glm["family"], glm["model"]), ("heimdall", "glm", "z-ai/glm-5.3-flash"))

    def test_ruling_76_the_window_is_never_widened_and_delivered_spans_carry_their_text(self):
        """RULING 76 (18:08 Nov 13): --hours over 12 refuses the run before anything is written; the delivered spans
        carry the approved text, for the same-speech rule."""
        sys.path.insert(0, HERE)
        import proof_ledger as PLG
        pins = [os.path.join(HERE, "proof", "fresh_20261112_050611", n) for n in ("MOMENTS_PIN.json",
                                                                                 "MOMENTS_PIN_LY.json")]
        with mock.patch("sys.stderr", new=io.StringIO()) as err, refused_only():
            for h in ("12.5", "72", "0", "-1"):
                self.assertEqual(PLG.main(["--delivered", *pins, "--hours", h]), 2, h)
            self.assertIn("REFUSED (ruling 76)", err.getvalue())
            for h in ("12", "6"):                       # audit 1810 C1 (glm P2-1): the bound itself is accepted; the run
                with self.assertRaises(AssertionError) as cm:   # goes on, and the guard stops it at the proof dir
                    PLG.main(["--delivered", *pins, "--hours", h])
                self.assertIn("went on to write a proof dir", str(cm.exception))
        spans, _, _ = PLG.delivered_pins(pins)
        self.assertTrue(all(isinstance(s["text"], str) and s["text"] for s in spans))
        for p in pins:                                   # audit 1810 C3 (glm P1-2): the CLIP's own approved words, never
            with open(p) as f:                           # a VO line, title or caption
                pin = json.load(f)
            mp = pin["moments_package"]
            vo = {mp["title"], mp["caption"], (mp.get("edl_vo") or {}).get("intro")} | {
                b.get("text") for b in (mp.get("edl_vo") or {}).get("bridges") or []}
            for seg in pin["segments"]:
                self.assertIn(seg["approved_text"], [s["text"] for s in spans if s["video_id"] == seg["video_id"] and
                                                     s["start"] == float(seg["start"])])
                self.assertNotIn(seg["approved_text"], vo)

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



class TestRuling85NoXai(unittest.TestCase):
    """RULINGS 85 + 88 (22:15 Nov 13), on the real config and the real Router's skip rule (no model is called):
    the lists per verdict type under heimdall_first; with xAI answering nothing and deepseek writing, every type
    still has a family off the writer, and step A's two verdicts come from two families. The gap ruling 96 left
    (coherence had Grok with deepseek alone behind it, so with deepseek writing and xAI down it had no family) is
    closed by the orchestrator's 06:12 rulings: glm is coherence's LAST fallback; clips-alone has NO Heimdall fallback
    (Grok, then Plan B's other outside family, Gemini, else it fails closed); qwen is struck from step A."""

    @staticmethod
    def pl():
        sys.path.insert(0, HERE)
        import proof_ly as PL
        return PL

    def pick(self, r, role, av=(), af=(), am=(), kind=None):
        PL = self.pl()
        for name in r.chain(role, kind):
            b = r.backends.get(name)
            if b is not None and r._skip(name, b, set(av), set(am), set(af)) is None and not \
                    name.startswith(PL.FROZEN):
                return name
        return None

    def test_ruling_96s_lists_and_xai_answering_nothing(self):
        """RULING 96 (01:40 ET Nov 14), final until re-measured, on ruling 88's structure, as the orchestrator's 06:12
        rulings amend it: (1) glm last for coherence, no Heimdall model for clips-alone; (2) qwen struck from step A."""
        PL = self.pl()
        X, DS, G, Q = ("xai:grok-4.20-0309-reasoning", "heimdall:deepseek/deepseek-v4.1-flash",
                       "heimdall:z-ai/glm-5.3-flash", "heimdall:qwen/qwen3.8-27b")
        GEM = "google:gemini-2.5-pro"
        ch = PL.chains("heimdall_first")
        self.assertEqual(ch["fidelity_verdict"], [G, Q, X])                       # 96: glm -> qwen -> Grok
        self.assertEqual(ch["exclusion_verdict"], [G, DS, X])                      # 96: glm -> deepseek -> Grok
        self.assertEqual(ch["context_verdict:step_a_first"], [G, DS, X])           # 06:12 (2): glm -> deepseek, no qwen
        self.assertEqual(ch["context_verdict:step_a_second"], [X, G, DS])          # (c) Grok confirms; 06:12 (2)
        self.assertEqual(ch["context_verdict"], [G, DS, X])                        # the role's default: no qwen either
        self.assertNotIn(Q, [b for k, v in ch.items() if k.startswith("context_verdict:step_a") for b in v])
        self.assertEqual(ch["coherence_verdict:hook"], [Q, G, DS, X])              # 88 (b) / 96: the hook moved
        self.assertEqual(ch["context_verdict:step_c"], [X, G, DS])                 # (b) / (e): no qwen
        self.assertEqual(ch["coherence_verdict:coherence"], [X, DS, G])           # 06:12 (1): glm the LAST fallback
        self.assertEqual(ch["coherence_verdict:clips_alone"], [X, GEM])           # 06:12 (1): no Heimdall model
        today = PL.chains("today")                                                 # (d) and (e) hold today too
        self.assertEqual((today["coherence_verdict:coherence"], today["context_verdict:step_c"]), ([X, DS], [X, DS, G]))
        r = PL.P.Router(env_path="/nonexistent", routing="heimdall_first", chains=ch)
        for n in [n for n in r.backends if n.startswith("xai")]:
            r.down[n] = "xAI answers nothing (the test)"
        w = r.backends[DS]                                                         # the writer
        got = {(role, kind): self.pick(r, role, {w.vendor}, {w.family}, kind=kind) for role, kind in (
            ("fidelity_verdict", None), ("exclusion_verdict", None), ("speaker_verdict", None),
            ("viewer_takeaway", None), ("context_verdict", "step_c"), ("coherence_verdict", "hook"),
            ("coherence_verdict", "clips_alone"), ("coherence_verdict", "coherence"))}
        self.assertEqual(got, {("fidelity_verdict", None): G, ("exclusion_verdict", None): G,
                               ("speaker_verdict", None): G, ("viewer_takeaway", None): G,
                               ("context_verdict", "step_c"): G, ("coherence_verdict", "hook"): Q,
                               ("coherence_verdict", "clips_alone"): GEM,          # Plan B's other outside family
                               ("coherence_verdict", "coherence"): G})            # the gap is closed: glm, last
        r.down[GEM] = "Gemini answers nothing (the test)"
        self.assertIsNone(self.pick(r, "coherence_verdict", {w.vendor}, {w.family}, kind="clips_alone"))   # closed
        r.down[G] = "glm answers nothing (the test)"
        self.assertIsNone(self.pick(r, "coherence_verdict", {w.vendor}, {w.family}, kind="coherence"))     # closed
        del r.down[G], r.down[GEM]
        first = self.pick(r, "context_verdict", {w.vendor}, {w.family}, kind="step_a_first")
        fb = r.backends[first]
        second = self.pick(r, "context_verdict", {fb.vendor}, {fb.family}, kind="step_a_second")
        self.assertEqual((first, second), (G, DS))                                 # two Heimdall families, Grok down
        r.down.clear()
        second = self.pick(r, "context_verdict", {fb.vendor}, {fb.family}, kind="step_a_second")
        self.assertEqual(second, X)                                                # (c): Grok confirms when it answers

if __name__ == "__main__":
    unittest.main()
