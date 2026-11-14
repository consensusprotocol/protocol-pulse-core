#!/usr/bin/env python3
"""Ruling 68, the pin-stage ruling-17 pre-check, without a GPU or a paid call. The pre-check and the render share ONE
code path (pinned.acquire, validate_range, segment_lock). A decode request returns the render's lock text. An approved
text gets the render's own outcome: no difference, adopted, two readings, or HOLD (E-FAIL-081's shape: 'punch you' and
a dropped repeat). A render always comes first. One window per video, as acquire builds it. A repeat is answered with no
new spend. A failed download is an error, never a pass."""
import contextlib
import hashlib
import inspect
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

PIPELINE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PIPELINE)
import gpu0  # noqa: E402
import lock_precheck as LP  # noqa: E402
import pinned  # noqa: E402
import select_passages  # noqa: E402
import sentence_law as SL  # noqa: E402
from canon import canon_tokens  # noqa: E402

VID, START, END = "mKNAcOFMYD4", 755.454, 764.214
ATTESTED = ("My biggest fear is that I go to the bank and I punch in my code and the money's not there because the bank "
            "owns the money and they could just take it from me. And that's why that's why we Bitcoin.")
WORD_PASS = ("My biggest fear is that I go to the bank and I punch you my code and the money's not there because the bank "
             "owns the money and they could just take it from me. And that's why we Bitcoin.")


def words_of(text, t0=15.5, step=0.206):
    """The run's decode on the acquired window's clock (its download starts at round(START - 15) = 740 s): a word
    before the span, the span's words, a word after it."""
    out = [{"word": "second", "start": 14.0, "end": 14.4}, {"word": "biggest.", "start": 14.7, "end": 15.3}]
    out += [{"word": w, "start": round(t0 + i * step, 3), "end": round(t0 + i * step + 0.18, 3)}
            for i, w in enumerate(text.split())]
    return out + [{"word": "My", "start": 24.4, "end": 24.6}, {"word": "second", "start": 24.7, "end": 25.0}]


class Base(unittest.TestCase):
    run_text = ATTESTED            # what the render's decoder reads

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="lock_precheck_test_")
        self.downloads, self.decodes, self.heard = [], [], []
        self.scribe_text = self.run_text
        self.fail_download = False

        def download(video_id, start_s, end_s, run_dir, pad=15.0):
            self.downloads.append((video_id, start_s, end_s, run_dir))
            p = os.path.join(run_dir, "sources", f"{video_id}.mp4")
            if not self.fail_download and not os.path.exists(p):
                os.makedirs(os.path.dirname(p), exist_ok=True)
                with open(p, "wb") as f:
                    f.write(b"\0" * 100_001)
            return (p, float(round(max(0, start_s - pad)))) if os.path.exists(p) else (None, 0)

        def transcribe(source_path, video_id, run_dir):        # cached by path, as the real _whisper_transcribe
            p = os.path.join(run_dir, "transcripts", f"{video_id}.json")
            if os.path.exists(p):
                with open(p) as f:
                    return json.load(f)
            self.decodes.append(video_id)
            out = {"words": getattr(self, "run_words", None) or words_of(self.run_text), "language": "en",
                   "duration": 39.0}
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w") as f:
                json.dump(out, f)
            return out

        def scribe(src):
            self.heard.append(src)
            return getattr(self, "scribe_words", None) or words_of(self.scribe_text), 0.0078

        self.wants = mock.Mock(return_value=False)
        self.cut = {"pause_in": None, "pause_out": None, "cut_in": 15.2, "cut_out": 24.4, "cut_duration": 9.2,
                    "lead_in_pad_s": 0.0, "verified": True}               # ruling 73 (c): the render's cut, stubbed
        for p in (mock.patch.object(LP, "ROOT", self.root),
                  mock.patch.object(LP.sentence_law, "lock_cut", lambda src, words, lock, label: dict(self.cut)),
                  mock.patch.object(LP, "EXTRA", os.path.join(self.root, "extra")),    # never the builder's real dir
                  mock.patch.object(select_passages, "_download_window", download),
                  mock.patch.object(select_passages, "_whisper_transcribe", transcribe),
                  mock.patch.object(pinned, "_duration", lambda path: 39.0),
                  mock.patch.object(pinned, "_second_recogniser_words", scribe),
                  mock.patch.object(gpu0, "lease", lambda owner, wait_s=0.0: contextlib.nullcontext()),
                  mock.patch.object(gpu0, "release_all", lambda *a, **k: None),
                  mock.patch.object(LP.LJ, "render_wants_gpu0", self.wants)):
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(shutil.rmtree, self.root, True)

    def request(self, rid="r1", segments=None, **seg):
        s = dict({"video_id": VID, "start": START, "end": END, "role": "clip"}, **seg)
        os.makedirs(os.path.join(self.root, "requests"), exist_ok=True)
        with open(os.path.join(self.root, "requests", f"{rid}.json"), "w") as f:
            json.dump({"request_id": rid, "segments": segments or [s]}, f)

    def entry(self, approved_text=None, start=START, end=END, window=None):
        return LP.latest(VID, start, end, window=window, approved_text=approved_text)

    def log(self, m):
        pass


class TestOneCodePath(unittest.TestCase):
    def test_the_render_and_the_pre_check_make_the_lock_with_the_same_functions(self):
        src = inspect.getsource(pinned.build_edl)
        self.assertIn("segment_lock(s, a, v, log=log)", src)
        self.assertNotIn("adjudicate_lock(", src)               # no second path left in the render
        self.assertNotIn("make_lock(", src)
        seg = inspect.getsource(pinned.segment_lock)
        for f in ("L.make_lock(", "trimmed_lock(", "adjudicate_lock("):
            self.assertIn(f, seg)
        self.assertIn("pinned.acquire(", inspect.getsource(LP.decode))
        ans = inspect.getsource(LP.answer)
        self.assertIn("pinned.validate_range(s, a)", ans)
        self.assertIn("pinned.segment_lock(s, a, v, recognise=recognise", ans)

    def test_the_decoder_sha_covers_the_acquisition_decoder_and_lock_code(self):
        for name in ("select_passages.py", "punctuation.py", "pinned.py", "sentence_law.py", "canon.py", "gpu0.py"):
            self.assertIn(name, LP.CODE)
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        for name in LP.CODE:
            shutil.copy(os.path.join(PIPELINE, name), tmp)
        with mock.patch.object(LP, "PIPELINE", tmp):
            a = LP.decoder_sha()
            with open(os.path.join(tmp, "punctuation.py"), "a") as f:
                f.write("\n# changed\n")
            self.assertNotEqual(a, LP.decoder_sha())
        self.assertEqual(LP.decoder_sha(), a)


class TestOutcomes(Base):
    def test_a_decode_request_returns_the_render_lock_text(self):
        self.request()
        self.assertEqual(LP.serve_once(log=self.log), 1)
        e = self.entry()
        self.assertEqual(e["outcome"], "decoded")
        self.assertEqual(e["lock"]["text"], ATTESTED)            # the render's decode of the span, word for word
        self.assertEqual((e["lock"]["first_word"], e["lock"]["last_word"]), ("My", "Bitcoin."))
        self.assertEqual(e["window"], [START, END])
        self.assertEqual(e["offset"], 740.0)
        self.assertEqual((e["as_spoken"]["verdict"], e["rules"]), ("same", LP.RULES))   # ruling 72: every span
        self.assertEqual((e["scribe_usd"], len(self.heard)), (0.0078, 1))              # ONE reading per acquisition
        self.assertTrue(os.path.basename(LP.result_path(VID, START, END, LP.decoder_sha())).startswith(
            f"{VID}.755.454-764.214.{LP.decoder_sha()[:12]}"))
        self.assertTrue(os.path.exists(os.path.join(self.root, "requests", "done", "r1.json")))
        self.assertEqual([d[:3] for d in self.downloads], [(VID, START, END)] * 2)   # prefetch + acquire's cache hit
        self.assertEqual(self.decodes, [VID])

    def test_the_attested_text_meets_no_difference_and_one_reading(self):
        self.request(approved_text=ATTESTED.upper().replace(".", ""))      # canonical tokens equal
        LP.serve_once(log=self.log)
        e = self.entry(ATTESTED.upper().replace(".", ""))
        self.assertEqual((e["outcome"], e["as_spoken"]["verdict"]), ("no_difference", "same"), e)
        self.assertEqual((e["scribe_usd"], len(self.heard)), (0.0078, 1))

    def test_the_word_pass_text_holds_as_the_render_held_it(self):
        self.request(approved_text=WORD_PASS)
        LP.serve_once(log=self.log)
        e = self.entry(WORD_PASS)
        self.assertEqual(e["outcome"], "hold")
        self.assertIn("lock text not adjudicated (ruling 17)", e["reason"])
        self.assertIn("[['in', 'you'], [\"that's why\", '']] the second recogniser reads the run decode", e["reason"])
        self.assertEqual(e["scribe_usd"], 0.0078)                # the spend is recorded
        self.assertIsNone(e["lock"])


class TestAdoption(Base):
    run_text = ATTESTED.replace("punch in", "punch you")         # the decoder mishears one function word

    def test_adopted_when_the_second_recogniser_reads_the_approved_words(self):
        self.run_text = ATTESTED.replace("owns the money", "holds the money")   # a content word: ruling 17's
        self.scribe_text = ATTESTED                               # the second recogniser reads the approved words
        self.request(approved_text=ATTESTED)
        LP.serve_once(log=self.log)
        e = self.entry(ATTESTED)
        self.assertEqual(e["outcome"], "adopted", e)
        self.assertEqual(e["lock"]["text"], ATTESTED)             # the lock takes the approved text
        self.assertEqual(e["adjudication"]["verdict"], "approved")

    def test_ruling_84_b_one_function_word_the_lock_keeps_the_decodes_and_records_the_other(self):
        self.scribe_text = ATTESTED                               # it reads 'in' where the decode reads 'you'
        self.request(approved_text=ATTESTED)
        LP.serve_once(log=self.log)
        e = self.entry(ATTESTED)
        self.assertEqual((e["outcome"], e["spoken_text"]), ("adopt_spoken", ATTESTED), e)
        self.assertEqual(e["lock"]["text"], self.run_text)        # the render decode's word stays in the lock
        alt, = e["alternatives"]
        self.assertEqual((alt["readings"], alt["rule"][:13]), (["you", "in"], "ruling 84 (b)"))
        self.assertEqual((e["as_spoken"]["differences"], e["as_spoken"]["classes"]), ([["you", "in"]], [LP.ONE_FW]))

    def test_two_readings_when_it_reads_the_decode_on_one_token(self):
        self.scribe_text = self.run_text
        self.request(approved_text=ATTESTED)
        LP.serve_once(log=self.log)
        e = self.entry(ATTESTED)
        self.assertEqual(e["outcome"], "two_readings", e)
        self.assertEqual(e["adjudication"][0]["readings"], ["you", "in"])


class TestDiscipline(Base):
    def test_a_render_comes_first(self):
        self.request()
        self.wants.return_value = True                            # the flag is up before anything
        self.assertEqual(LP.serve_once(log=self.log), 0)
        self.assertEqual((self.downloads, self.decodes), ([], []))
        self.wants.return_value, self.wants.side_effect = None, [False, False, True]   # it goes up as the lease is taken
        self.assertEqual(LP.serve_once(log=self.log), 0)
        self.wants.side_effect = [False, False, False, True]      # before the first video's decode
        self.assertEqual(LP.serve_once(log=self.log), 0)
        self.assertEqual(self.decodes, [])
        self.assertEqual(len(LP.pending()), 1)                    # still pending, answered later
        self.wants.side_effect, self.wants.return_value = None, False
        self.assertEqual(LP.serve_once(log=self.log), 1)
        self.assertEqual(self.entry()["outcome"], "decoded")

    def test_malformed_requests_fail_with_why(self):
        os.makedirs(os.path.join(self.root, "requests"))
        for rid, body in (("a", {"request_id": "a", "segments": []}),
                          ("b", {"request_id": "b", "segments": [{"video_id": "x", "start": 5, "end": 4, "role": "intro"}]}),
                          ("c", {"request_id": "c", "segments": [{"video_id": VID, "start": 1, "end": 2, "role": "clip",
                                                                  "approved_text": " ", "trimmed_leading": "but"}]})):
            with open(os.path.join(self.root, "requests", f"{rid}.json"), "w") as f:
                json.dump(body, f)
        self.assertEqual(LP.serve_once(log=self.log), 3)
        why = {}
        for rid in "abc":
            with open(os.path.join(self.root, "requests", "failed", f"{rid}.json")) as f:
                why[rid] = " ".join(json.load(f)["why"])
        self.assertIn("non-empty list", why["a"])
        for w in ("not a YouTube id", "0 <= start < end", "'hook' or 'clip'"):
            self.assertIn(w, why["b"])
        for w in ("approved_text must be a non-empty string", "go together"):
            self.assertIn(w, why["c"])
        self.assertEqual((self.downloads, self.decodes), ([], []))

    def test_one_window_per_video_as_acquire_builds_it(self):
        a = {"video_id": VID, "start": START, "end": END, "role": "clip"}
        b = {"video_id": VID, "start": 700.0, "end": 710.0, "role": "hook"}
        self.request(segments=[b, a])
        LP.serve_once(log=self.log)
        self.assertEqual({d[:3] for d in self.downloads}, {(VID, 700.0, END)})
        self.assertEqual(self.decodes, [VID])                     # one decode for the video
        e = self.entry(window=(700.0, END))
        self.assertEqual(e["window"], [700.0, END])
        self.assertIsNone(self.entry())                            # not the single-span window's answer

    def test_a_repeat_is_answered_with_no_decode_and_no_spend(self):
        self.request("r1", approved_text=WORD_PASS)
        LP.serve_once(log=self.log)
        self.request("r2", approved_text=WORD_PASS)
        self.assertEqual(LP.serve_once(log=self.log), 1)
        es = LP._entries(LP.result_path(VID, START, END, LP.decoder_sha()))
        self.assertEqual([(e["request_id"], e["reused"]) for e in es], [("r1", False), ("r2", True)])
        self.assertEqual((len(self.heard), self.decodes), (1, [VID]))

    def test_the_reuse_key_is_every_field_the_answer_depends_on(self):
        self.request("r1")
        LP.serve_once(log=self.log)
        self.request("r2", role="hook")                           # role names a hold's tag: answered again
        self.request("r3", trimmed_leading="and", untrimmed_start=754.9)   # the trimmed lock differs: answered again
        self.request("r4")                                        # identical to r1: reused
        LP.serve_once(log=self.log)
        es = {e["request_id"]: e for e in LP._entries(LP.result_path(VID, START, END, LP.decoder_sha()))}
        self.assertEqual({k: (e["reused"], e["role"]) for k, e in es.items()},   # a cached one is answered first
                         {"r1": (False, "clip"), "r2": (False, "hook"), "r3": (False, "clip"), "r4": (True, "clip")})
        self.assertEqual((es["r3"]["trimmed_leading"], es["r3"]["untrimmed_start"], es["r3"]["outcome"]),
                         ("and", 754.9, "hold"))
        self.assertIn("trim", es["r3"]["reason"].lower())       # trimmed_lock's own refusal: no 'and' before the lock
        self.assertEqual(LP.latest(VID, START, END, role="hook")["request_id"], "r2")
        self.assertEqual(self.decodes, [VID])                    # one decode: the acquisition is cached

    def test_a_gpu0_stop_leaves_the_rest_pending_and_the_service_running(self):
        self.request("r1")
        LP.serve_once(log=self.log)                               # r1 decoded (its transcript cached)
        self.request("r2", start=700.0, end=710.0, role="hook")    # a new window: a new decode
        oom = mock.Mock(side_effect=gpu0.GpuOOM("CUDA out of memory"))
        with mock.patch.object(select_passages, "_whisper_transcribe", oom):
            self.assertEqual(LP.serve_once(log=self.log), 0)       # no crash out of the serve loop
        self.assertEqual([os.path.basename(p) for p in LP.pending()], ["r2.json"])
        self.assertIsNone(LP.latest(VID, 700.0, 710.0, role="hook"))   # nothing invented
        self.assertEqual(LP.serve_once(log=self.log), 1)            # asked again once GPU0 is back
        self.assertEqual(LP.latest(VID, 700.0, 710.0, role="hook")["outcome"], "decoded")

    def test_a_failed_download_is_an_error_never_a_pass(self):
        self.fail_download = True
        self.request(approved_text=ATTESTED)
        LP.serve_once(log=self.log)
        e = self.entry(ATTESTED)
        self.assertEqual(e["outcome"], "error")
        self.assertIn("did not download", e["reason"])
        self.assertIsNone(e["lock"])
        self.assertEqual(self.decodes, [])
        self.fail_download = False                                # an error is not reused: asked again, answered
        self.request("r2", approved_text=ATTESTED)
        LP.serve_once(log=self.log)
        self.assertEqual(self.entry(ATTESTED)["outcome"], "no_difference")


def spread(text, t0=15.5, t1=24.1, before=None):
    """text's words evenly over [t0, t1] on the acquired window's clock, after an optional (word, start, end)."""
    ws = text.split()
    step = (t1 - t0) / len(ws)
    out = [{"word": w, "start": round(t0 + i * step, 3), "end": round(t0 + i * step + 0.8 * step, 3)}
           for i, w in enumerate(ws)]
    return ([{"word": before[0], "start": before[1], "end": before[2]}] if before else []) + out


LOCKED = "When Bitcoin and an asset is going up, everyone loves it."
SPOKEN = "When, when Bitcoin and, and an asset is going up, everyone loves it."


class TestRuling72(Base):
    """RULING 72 (orchestrator '15:45'): the second recogniser against the lock on EVERY span."""

    def test_the_speakers_repeats_adopt_the_spoken_text(self):
        self.run_words = spread(LOCKED)
        self.scribe_words = spread(SPOKEN, before=("markets.", 14.3, 14.8))   # the last sentence, outside the window
        self.request(approved_text=LOCKED)
        LP.serve_once(log=self.log)
        e = self.entry(LOCKED)
        self.assertEqual((e["outcome"], e["spoken_text"]), ("adopt_spoken", SPOKEN), e)
        self.assertEqual(e["lock"]["text"], SPOKEN)               # the render's own ruling 17 adopted it
        self.assertEqual(e["adjudication"]["verdict"], "approved")
        self.assertEqual(sorted(d[1] for d in e["as_spoken"]["differences"]), ["and", "when"])
        self.assertEqual((e["scribe_usd"], len(self.heard)), (0.0078, 1))

    def test_spill_is_not_a_difference_but_the_render_must_still_adopt(self):
        self.run_words = spread(LOCKED)
        self.scribe_words = spread(SPOKEN, before=("markets.", 15.2, 15.4))   # inside adjudicate_lock's 0.3 s window
        self.request(approved_text=LOCKED)
        LP.serve_once(log=self.log)
        e = self.entry(LOCKED)
        self.assertEqual(e["as_spoken"]["verdict"], "adopt")      # 'markets.' left out as the neighbouring sentence
        self.assertEqual(e["as_spoken"]["text"], SPOKEN)
        self.assertEqual(e["outcome"], "hold")                    # ... but the render's ruling 17 refuses the edge
        self.assertIn("is not adopted by the render's ruling 17", e["reason"])
        self.assertIn("lock text not adjudicated (ruling 17)", e["reason"])

    def test_a_content_difference_holds_before_the_seal(self):
        self.run_words = spread("And that's why the price got high.")
        self.scribe_words = spread("And that's, that's why the bull, that's why the price got high.")
        self.request(approved_text="And that's why the price got high.")
        LP.serve_once(log=self.log)
        e = self.entry("And that's why the price got high.")
        self.assertEqual(e["outcome"], "hold")
        self.assertIn("ruling 72/84: the second recogniser reads the span differently", e["reason"])
        self.assertIn("bull", e["reason"])
        self.assertIsNone(e["lock"])

    def test_one_function_word_adopts_as_ruling_84_b_says(self):
        self.run_words = spread("I go to the bank and I punch in my code.")
        self.scribe_words = spread("I go to a bank and I punch in my code.")
        self.request(approved_text="I go to the bank and I punch in my code.")
        LP.serve_once(log=self.log)
        e = self.entry("I go to the bank and I punch in my code.")
        self.assertEqual((e["outcome"], e["spoken_text"]), ("adopt_spoken", "I go to a bank and I punch in my code."))
        self.assertEqual(e["as_spoken"]["differences"], [["the", "a"]])
        self.assertEqual(e["lock"]["text"], "I go to the bank and I punch in my code.")   # the decode's word kept
        self.assertEqual(e["alternatives"][0]["readings"], ["the", "a"])                 # the other recorded

    def test_one_paid_reading_per_acquisition(self):
        self.run_words = spread(ATTESTED)
        self.scribe_words = spread(ATTESTED)
        a = {"video_id": VID, "start": START, "end": 759.6, "role": "hook"}
        b = {"video_id": VID, "start": 759.9, "end": END, "role": "clip"}
        self.request(segments=[a, b])
        LP.serve_once(log=self.log)
        for s in (a, b):
            e = LP.latest(VID, s["start"], s["end"], window=(START, END))
            self.assertEqual((e["outcome"], e["as_spoken"]["verdict"]), ("decoded", "same"), e)
        self.assertEqual(len(self.heard), 1)

    def test_ruling_73_a_span_the_render_cannot_cut_holds_before_the_seal(self):
        self.cut = {"pause_in": None, "pause_out": None, "error": "locked sentence edges not cuttable: OUT: no cut "
                    "after the decoded end of the last locked word (ruling 73 a)"}
        self.request(approved_text=ATTESTED)
        LP.serve_once(log=self.log)
        e = self.entry(ATTESTED)
        self.assertEqual((e["outcome"], e["lock"]), ("hold", None), e)
        self.assertTrue(e["reason"].startswith("ruling 73: the render cannot cut this span: locked sentence edges"))
        self.assertIn("(ruling 73 a)", e["cut"]["error"])

    def test_ruling_73_a_passing_span_records_the_render_cut(self):
        self.request(approved_text=ATTESTED)
        LP.serve_once(log=self.log)
        e = self.entry(ATTESTED)
        self.assertEqual(e["outcome"], "no_difference")
        self.assertEqual((e["cut"]["cut_in"], e["cut"]["cut_out"], e["cut"]["error"]), (15.2, 24.4, None))

    def test_a_failed_second_reading_is_an_error_never_a_pass(self):
        def broken(src):
            raise KeyError("no recogniser key")
        with mock.patch.object(pinned, "_second_recogniser_words", broken):
            self.request(approved_text=ATTESTED)                  # ruling 17: no difference, so no reading there
            LP.serve_once(log=self.log)
        e = self.entry(ATTESTED)
        self.assertEqual((e["outcome"], e["lock"], e["as_spoken"]), ("error", None, None), e)
        self.assertIn("KeyError", e["reason"])
        self.request("r2", approved_text=ATTESTED)                # an error is not reused: asked again, answered
        LP.serve_once(log=self.log)
        e = self.entry(ATTESTED)
        self.assertEqual((e["request_id"], e["outcome"], e["reused"]), ("r2", "no_difference", False))

    def test_an_entry_under_other_rules_is_never_reused(self):
        out = LP.result_path(VID, START, END, LP.decoder_sha())
        os.makedirs(os.path.dirname(out))
        old = {"request_id": "r0", "video_id": VID, "start": START, "end": END, "role": "clip", "window": [START, END],
               "approved_text": ATTESTED, "trimmed_leading": None, "untrimmed_start": None, "outcome": "no_difference"}
        with open(out, "w") as f:
            json.dump([old], f)                                   # ruling 68's entry: no 'rules'
        self.request(approved_text=ATTESTED)
        LP.serve_once(log=self.log)
        e = self.entry(ATTESTED)
        self.assertEqual((e["request_id"], e["reused"], e["rules"]), ("r1", False, LP.RULES))


RUN84 = "I came to the conclusion that it will replace or will be replaced. So it will be replaced by Bitcoin."
SPOKEN84 = ("I came to the conclusion that, um, it will replace, uh, or will be replaced, or it will be replaced "
            "by Bitcoin.")


class TestRuling84(Base):
    """RULING 84 (orchestrator 2026-11-13 '20:40'): (a) fillers the second recogniser hears and Whisper drops adopt with
    the speaker's repetitions; (b) ONE function word read against the decode's one: the lock keeps the decode's word and
    records the other; two or more in one span hold; numbers, names, negations and content words hold."""

    def ask(self, run, heard, approved=None):
        shutil.rmtree(os.path.join(self.root, "work"), True)     # a fresh decode and reading per question
        self.run_words, self.scribe_words = spread(run), spread(heard)
        self.n = getattr(self, "n", 0) + 1
        self.request(f"r84_{self.n}", approved_text=approved or run)
        LP.serve_once(log=self.log)
        return self.entry(approved or run)

    def test_a_fillers_adopt_the_spoken_text(self):
        e = self.ask("So over time I came to the conclusion.", "So over time, um, I came to the conclusion.")
        self.assertEqual((e["outcome"], e["as_spoken"]["classes"]), ("adopt_spoken", ["filler"]), e)
        self.assertEqual(e["lock"]["text"], "So over time, um, I came to the conclusion.")     # ruling 17 adopted it
        self.assertEqual(e["adjudication"]["differences"], [["", "um"]])
        self.assertIsNone(e["alternatives"])

    def test_a_and_b_together_the_2012_builds_shape(self):
        e = self.ask(RUN84, SPOKEN84)
        self.assertEqual((e["outcome"], e["spoken_text"]), ("adopt_spoken", SPOKEN84), e)
        self.assertEqual(e["as_spoken"]["classes"], ["filler", "filler", LP.ONE_FW])
        self.assertEqual(e["lock"]["text"], SPOKEN84.replace("replaced, or it", "replaced, so it"))
        alt, = e["alternatives"]
        self.assertEqual(alt["readings"], ["so", "or"])
        self.assertEqual(canon_tokens(e["lock"]["text"])[alt["token_index"]], "so")
        self.assertEqual(e["adjudication"]["differences"], [["", "um"], ["", "uh"]])          # ruling 17's part

    def test_b_two_function_words_in_one_span_hold(self):
        e = self.ask("I go to the bank and I punch in my code.", "I go to a bank and I punch on my code.")
        self.assertEqual((e["outcome"], e["lock"]), ("hold", None), e)
        self.assertEqual(e["as_spoken"]["classes"], [LP.ONE_FW, LP.ONE_FW])
        self.assertIn("ruling 84 (b): two or more in one span hold", e["reason"])

    def test_any_other_substitution_holds(self):
        for run, heard in (("I went in the house today.", "I went into a house today."),     # two for two
                           ("The bank owns the money.", "The bank holds the money."),          # a content word
                           ("It took 15 years.", "It took 50 years."),                         # a number
                           ("You can do it.", "You can't do it.")):                            # a negation
            with self.subTest(run=run):
                e = self.ask(run, heard)
                self.assertEqual((e["outcome"], e["as_spoken"]["classes"]), ("hold", ["hold"]), e)

    def test_a_filler_only_the_lock_has_holds(self):                  # (a) is the second recogniser's fillers only
        e = self.ask("So um I came here today.", "So I came here today.")
        self.assertEqual((e["outcome"], e["as_spoken"]["classes"]), ("hold", ["hold"]), e)

    def test_a_filler_between_the_speakers_repeat_is_his_repetition(self):
        e = self.ask("Bitcoin and an asset is going up.", "Bitcoin and, uh, and an asset is going up.")
        self.assertEqual(e["outcome"], "adopt_spoken", e)
        self.assertEqual(e["as_spoken"]["classes"], ["immediate repetition"])

    def test_the_class_of_one_difference(self):
        c = LP.ruling84_class
        t = ("x", "x")
        self.assertEqual(c(["so", "i"], ["so", "um", "i"], ("insert", 1, 1, 1, 2), t), "filler")
        self.assertEqual(c(["so", "real"], ["or", "real"], ("replace", 0, 1, 0, 1), t), LP.ONE_FW)
        self.assertEqual(c(["so", "real"], ["uh", "or", "real"], ("replace", 0, 1, 0, 2), t), LP.ONE_FW)
        self.assertEqual(c(["so", "real"], ["so", "and", "real"], ("insert", 1, 1, 1, 2), t), "function word")
        self.assertIsNone(c(["the", "bull"], ["the", "bear"], ("replace", 1, 2, 1, 2), t))
        self.assertIsNone(c(["in", "the"], ["into", "a"], ("replace", 0, 2, 0, 2), t))
        self.assertIsNone(c(["um", "i"], ["i"], ("delete", 0, 1, 0, 0), t))
        self.assertEqual(LP.FILLERS, frozenset({"um", "uh", "er", "ah", "mm", "hmm"}))   # exactly the ruling's list


FX84 = os.path.join(PIPELINE, "fixtures", "ruling84")


def real_span(name):
    """A real span's cached inputs: the render decode of its acquisition window (the pre-check's work dir) and the
    second recogniser's paid reading of it, as the service read them. -> (segment, acquisition, reading, fixture)."""
    with open(os.path.join(FX84, name)) as f:
        fx = json.load(f)
    a = {"path": "unused.mp4", "offset": fx["offset"], "transcript": {"words": fx["transcript_words"]},
         "transcript_path": os.path.join(FX84, name), "provenance": {}}
    return fx["segment"], a, fx["second_recogniser_words"], fx


class TestRuling84MustFail(unittest.TestCase):
    """The orchestrator's must-fails on the real spans (no GPU, no paid call: the cached decode and reading)."""

    def lock(self, s, a, sw):
        with mock.patch.object(pinned, "_duration", lambda path: 1e6):
            return pinned.segment_lock(s, a, pinned.validate_range(s, a), recognise=lambda src: (sw, 0.0),
                                       log=lambda *_: None)

    def test_6058ee58_holds_on_the_old_rules_and_passes_on_the_new(self):
        import word_diff as WD
        s, a, sw, fx = real_span("uaHNzi-Kgr8_153.250-165.890.json")
        old = fx["old_entry"]                                     # the live service's answer at 01:28:05Z
        self.assertEqual((old["outcome"], old["rules"]), ("hold", "ruling 17 + ruling 72 + ruling 73"))
        self.assertEqual(old["as_spoken"]["differences"], [["", "um"], ["", "uh"], ["so", "or"]])
        words, lock = a["transcript"]["words"], self.lock(s, a, sw)
        L, S2, spoken = LP.reading(lock, words, sw)               # the old rule on the same inputs: ruling 67's class
        from difflib import SequenceMatcher
        ops = [o for o in SequenceMatcher(None, L, S2, autojunk=False).get_opcodes() if o[0] != "equal"]
        self.assertEqual([LP.carry_class(L, S2, o, (lock["text"], spoken)) for o in ops],
                         [None, None, "function word"])           # um, uh outside it: HOLD
        verdict, diffs, cls, text = LP.as_spoken(lock, words, sw)  # RULING 84
        self.assertEqual((verdict, diffs, cls), ("adopt", old["as_spoken"]["differences"], ["filler", "filler", LP.ONE_FW]))
        s2 = dict(s, approved_text=text)                          # the pre-check's adoption: the render's own lock
        new = self.lock(s2, a, sw)
        alt, = new["alternatives"]
        self.assertEqual((alt["readings"], canon_tokens(new["text"])[alt["token_index"]]), (["so", "or"], "so"))
        self.assertEqual(new["adjudication"]["differences"], [["", "um"], ["", "uh"]])
        self.assertEqual(SL.verify_lock(new), [])
        self.assertEqual(WD.diff(new["text"], text, alts=new["alternatives"]), [])   # G18 reads 'or': attested
        self.assertEqual({op for op, _, _ in WD.diff(new["text"], lock["text"], alts=new["alternatives"])},
                         {"delete"})                              # 'So' read, fillers dropped: omissions only

    def test_1b4a63d0s_hook_still_holds_as_ruling_67s_class_says(self):
        s, a, sw, _ = real_span("Sjb6lUiL0m4_3090.750-3109.870.json")
        words, lock = a["transcript"]["words"], self.lock(s, a, sw)
        verdict, diffs, cls, _ = LP.as_spoken(lock, words, sw)
        got = {d[1] or d[0]: k for d, k in zip(diffs, cls)}
        self.assertEqual(verdict, "hold")
        self.assertEqual((got["when"], got["and"]), ("immediate repetition", "immediate repetition"))
        self.assertEqual(got["that's why the bull that's"], "hold")   # a false start with a content word
        self.assertNotIn("filler", cls)
        self.assertNotIn(LP.ONE_FW, cls)


class TestBuildersDirectory(Base):
    """The builder may not write under the main tree: its requests are READ from its own directory, never touched."""

    def test_read_only_answered_once_per_content(self):
        os.makedirs(LP.EXTRA)
        p = os.path.join(LP.EXTRA, "b1.json")
        body = {"request_id": "b1", "segments": [{"video_id": VID, "start": START, "end": END, "role": "clip",
                                                  "approved_text": ATTESTED}]}
        with open(p, "w") as f:
            json.dump(body, f)
        before = (open(p, "rb").read(), os.stat(p).st_mtime_ns)
        self.assertEqual(LP.pending(), [p])
        self.assertEqual(LP.serve_once(log=self.log), 1)
        self.assertEqual((open(p, "rb").read(), os.stat(p).st_mtime_ns), before)      # never written, never moved
        self.assertEqual(LP.pending(), [])                                             # answered once for this content
        self.assertTrue(os.path.exists(os.path.join(self.root, "requests", "done", "extra.b1.json")))
        self.assertEqual(self.entry(ATTESTED)["outcome"], "no_difference")
        body["request_id"] = "b2"                                                      # the builder changes it
        with open(p, "w") as f:
            json.dump(body, f)
        self.assertEqual(LP.pending(), [p])
        self.assertEqual(LP.serve_once(log=self.log), 1)
        self.assertEqual([e["request_id"] for e in LP._entries(LP.result_path(VID, START, END, LP.decoder_sha()))],
                         ["b1", "b2"])

    def test_a_file_removed_after_it_was_listed_is_skipped_not_a_crash(self):
        os.makedirs(LP.EXTRA)
        p = os.path.join(LP.EXTRA, "gone.json")
        said = []
        with mock.patch.object(LP, "pending", lambda: [p]):      # listed, then removed by the builder before the read
            self.assertEqual(LP.serve_once(log=said.append), 0)  # no crash: the skip path ran
        self.assertEqual(said, ["  gone.json: not readable now (FileNotFoundError); the next pass sees it"])
        for d in ("answered", os.path.join("requests", "done"), os.path.join("requests", "failed")):
            self.assertFalse(os.path.exists(os.path.join(self.root, d)), d)   # not answered, not closed

    def test_a_malformed_request_there_is_recorded_here_and_left_alone(self):
        os.makedirs(LP.EXTRA)
        p = os.path.join(LP.EXTRA, "bad.json")
        with open(p, "w") as f:
            f.write("{not json")
        self.assertEqual(LP.serve_once(log=self.log), 1)
        self.assertTrue(os.path.exists(p))
        with open(os.path.join(self.root, "requests", "failed", "extra.bad.json")) as f:
            self.assertIn("not JSON", " ".join(json.load(f)["why"]))
        self.assertEqual(LP.pending(), [])


if __name__ == "__main__":
    unittest.main()
