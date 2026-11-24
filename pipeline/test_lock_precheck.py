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
        self.downloads, self.decodes, self.heard, self.relistened, self.windows = [], [], [], [], []
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
            long = getattr(self, "run_words", None) or words_of(self.run_text)
            if video_id == "relisten":                         # ruling 103's short window: the decoder re-reads it
                self.relistened.append(("decoder", source_path))
                long = getattr(self, "short_decoder", None) or long
            out = {"words": long, "language": "en", "duration": 39.0}
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w") as f:
                json.dump(out, f)
            return out

        def scribe(src):
            self.heard.append(src)
            long = getattr(self, "scribe_words", None) or words_of(self.scribe_text)
            if os.path.basename(src) == "window.wav":            # ruling 103's short window: it re-hears it
                self.relistened.append(("second", src))
                return getattr(self, "short_second", None) or long, 0.0008
            return long, 0.0078

        def clip(src, t0, t1, rdir):                           # the short window's audio, stubbed (no ffmpeg)
            os.makedirs(rdir, exist_ok=True)
            p = os.path.join(rdir, "window.wav")
            open(p, "wb").close()
            self.windows.append((round(t0, 3), round(t1, 3)))
            return p

        self.wants = mock.Mock(return_value=False)
        self.cut = {"pause_in": None, "pause_out": None, "cut_in": 15.2, "cut_out": 24.4, "cut_duration": 9.2,
                    "lead_in_pad_s": 0.0, "verified": True}               # ruling 73 (c): the render's cut, stubbed
        import gpu0_want                                               # never the live /tmp/pulse_gpu0.want
        for p in (mock.patch.object(LP, "ROOT", self.root),
                  mock.patch.object(gpu0_want, "DIR", os.path.join(self.root, "want")),
                  mock.patch.object(LP.sentence_law, "lock_cut", lambda src, words, lock, label: dict(self.cut)),
                  mock.patch.object(LP, "EXTRA", os.path.join(self.root, "extra")),    # never the builder's real dir
                  mock.patch.object(select_passages, "_download_window", download),
                  mock.patch.object(select_passages, "_whisper_transcribe", transcribe),
                  mock.patch.object(pinned, "_duration", lambda path: 39.0),
                  mock.patch.object(pinned, "_second_recogniser_words", scribe),
                  mock.patch.object(LP, "relisten_clip", clip),
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

    def test_the_word_pass_text_is_settled_by_two_of_three_readings(self):     # ruling 143 (was 131 (A))
        self.request(approved_text=WORD_PASS)
        LP.serve_once(log=self.log)
        e = self.entry(WORD_PASS)
        self.assertEqual((e["outcome"], e["spoken_text"]), ("adopt_spoken", ATTESTED), e.get("reason"))
        self.assertTrue(e["adjudication"]["rule"].startswith("ruling 143"))
        self.assertEqual([(x["run"], x["approved"], x["took"]) for x in e["adjudication"]["pairs"]],
                         [("in", "you", "run"), ("that's why", "", "run")])
        self.assertEqual(e["lock"]["text"], ATTESTED)            # the lock the sealed text makes: nothing to settle
        self.assertIsNone(e["relock_adjudication"])
        self.assertEqual((e["scribe_usd"], len(self.heard)), (0.0078, 1))     # ONE paid reading, cached for the re-lock
class TestAdoption(Base):
    run_text = ATTESTED.replace("punch in", "punch you")         # the decoder mishears one function word

    def test_adopted_when_the_second_recogniser_reads_the_approved_words(self):
        self.run_text = ATTESTED.replace("owns the money", "holds the money")   # a small word: two of three
        self.scribe_text = ATTESTED                               # the second recogniser reads the approved words
        self.request(approved_text=ATTESTED)
        LP.serve_once(log=self.log)
        e = self.entry(ATTESTED)
        self.assertEqual(e["outcome"], "adopted", e)
        self.assertEqual(e["lock"]["text"], ATTESTED)             # the lock takes the approved text
        self.assertEqual(e["adjudication"]["verdict"], "settled")
    def test_one_function_word_takes_the_two_of_three_reading(self):         # ruling 143 (84 (b) kept the decode's)
        self.scribe_text = ATTESTED                               # it reads 'in' where the decode reads 'you'
        self.request(approved_text=ATTESTED)
        LP.serve_once(log=self.log)
        e = self.entry(ATTESTED)
        self.assertEqual(e["outcome"], "adopted", e)
        self.assertEqual(e["lock"]["text"], ATTESTED)             # approved + second against the decode
        self.assertIsNone(e.get("alternatives"))
    def test_one_mid_span_token_both_recognisers_read_is_settled(self):          # ruling 131 (A) (ruling 18's
        self.scribe_text = self.run_text                                          # record before it)
        self.request(approved_text=ATTESTED)
        LP.serve_once(log=self.log)
        e = self.entry(ATTESTED)
        self.assertEqual((e["outcome"], e["spoken_text"]), ("adopt_spoken", self.run_text), e.get("reason"))
        self.assertEqual([(x["run"], x["approved"], x["took"]) for x in e["adjudication"]["pairs"]],
                         [("you", "in", "run")])


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

    def test_order_1305_the_pre_check_wants_gpu0_while_a_decode_waits_and_is_done_after(self):
        """Orchestrator order '13:05' (R13): builds keep priority over Whisper. A decode waiting behind the ingest's
        Whisper pass raises the pre-check's want (Whisper gives GPU0 back at its next file boundary); answered, the
        want is gone."""
        import gpu0_want as W
        with mock.patch.object(W, "DIR", os.path.join(self.root, "want")):
            self.request("r1")
            busy = mock.Mock(side_effect=gpu0.LeaseBusy("the GPU0 lease is held by transcript_ingest (pid 1)"))
            with mock.patch.object(gpu0, "lease", busy):
                self.assertEqual(LP.serve_once(log=self.log), 0)
            self.assertEqual(W.wanted(), ["lock_precheck"])
            self.assertEqual(LP.serve_once(log=self.log), 1)                  # GPU0 back: decoded and answered
            self.assertEqual(W.wanted(), [])
            self.assertEqual(LP.serve_once(log=self.log), 0)                  # nothing pending
            self.assertEqual(W.wanted(), [])

    def test_order_1305_a_queue_emptied_elsewhere_clears_the_pre_checks_want_on_its_next_pass(self):
        import gpu0_want as W
        with mock.patch.object(W, "DIR", os.path.join(self.root, "want")):
            self.request("r1")
            busy = mock.Mock(side_effect=gpu0.LeaseBusy("held by transcript_ingest (pid 1)"))
            with mock.patch.object(gpu0, "lease", busy):
                self.assertEqual(LP.serve_once(log=self.log), 0)
            self.assertEqual(W.wanted(), ["lock_precheck"])
            for p in LP.pending():                                            # the request withdrawn
                os.remove(p)
            self.assertEqual(LP.serve_once(log=self.log), 0)
            self.assertEqual(W.wanted(), [])

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

    def test_the_speakers_repeats_never_hold_and_the_lock_stands(self):      # ruling 143 (2)
        self.run_words = spread(LOCKED)
        self.scribe_words = spread(SPOKEN, before=("markets.", 14.3, 14.8))   # the last sentence, outside the window
        self.request(approved_text=LOCKED)
        LP.serve_once(log=self.log)
        e = self.entry(LOCKED)
        self.assertEqual(e["outcome"], "no_difference", e)
        self.assertEqual(e["lock"]["text"], LOCKED)
        self.assertEqual(sorted(d[1] for d in e["as_spoken"]["differences"]), ["and", "when"])
        self.assertEqual(e["as_spoken"]["classes"], ["small", "small"])
        self.assertEqual((e["scribe_usd"], len(self.heard)), (0.0078, 1))
    def test_spill_is_not_a_difference_and_the_repeats_never_hold(self):    # ruling 143 (2)
        self.run_words = spread(LOCKED)
        self.scribe_words = spread(SPOKEN, before=("markets.", 15.2, 15.4))   # inside adjudicate_lock's 0.3 s window
        self.request(approved_text=LOCKED)
        LP.serve_once(log=self.log)
        e = self.entry(LOCKED)
        self.assertEqual(e["as_spoken"]["verdict"], "same")       # 'markets.' left out as the neighbouring sentence
        self.assertEqual(e["outcome"], "no_difference")
        self.assertEqual(e["lock"]["text"], LOCKED)
    def test_a_false_start_is_the_speakers_not_the_wrong_audio(self):        # ruling 143 (2) / (4) (it held)
        self.run_words = spread("And that's why the price got high.")
        self.scribe_words = spread("And that's, that's why the bull, that's why the price got high.")
        self.request(approved_text="And that's why the price got high.")
        LP.serve_once(log=self.log)
        e = self.entry("And that's why the price got high.")
        self.assertEqual(e["outcome"], "no_difference", e.get("reason"))   # every decoded word heard, in order
        self.assertEqual(set(e["as_spoken"]["classes"]), {"small"})
    def test_one_function_word_never_holds_and_the_lock_stands(self):        # ruling 143 (2)
        self.run_words = spread("I go to the bank and I punch in my code.")
        self.scribe_words = spread("I go to a bank and I punch in my code.")
        self.request(approved_text="I go to the bank and I punch in my code.")
        LP.serve_once(log=self.log)
        e = self.entry("I go to the bank and I punch in my code.")
        self.assertEqual(e["outcome"], "no_difference")           # the decode and the transcript against one reader
        self.assertEqual((e["as_spoken"]["differences"], e["as_spoken"]["classes"]), ([["the", "a"]], ["small"]))
        self.assertEqual(e["lock"]["text"], "I go to the bank and I punch in my code.")
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


class TestRuling162(Base):
    """RULING 162 (1) (orchestrator 07:45 ET Nov 24, from PBX): a clip never ends while the speaker is still
    mid-sentence; ruling 139's flag stays for the IN edge only. The pre-check holds a span whose OUT edge is a sentence
    edge, with the reason the builder acts on (extend the out point, ruling 104's tail), and a passing verdict made
    before the ruling is held when it is served again: no new decode, no new second reading."""
    OUT = "'and' does not end a sentence"

    def test_an_out_sentence_edge_holds_and_an_in_edge_alone_passes(self):
        self.cut = {**self.cut, "sentence_edge": {"in": "'not' does not end a sentence", "out": self.OUT}}
        self.request(approved_text=ATTESTED)
        LP.serve_once(log=self.log)
        e = self.entry(ATTESTED)
        self.assertEqual((e["outcome"], e["lock"]), ("hold", None), e)
        self.assertTrue(e["reason"].startswith("ruling 162 (1): the span ends while the speaker is still mid-sentence"))
        self.assertIn(self.OUT, e["reason"])
        self.assertIn("ruling 104's tail", e["reason"])
        self.assertEqual(e["cut"]["sentence_edge"], {"in": "'not' does not end a sentence", "out": self.OUT})

    def test_a_passing_verdict_made_before_the_ruling_is_held_when_served_again(self):
        self.request(approved_text=ATTESTED)
        LP.serve_once(log=self.log)
        out = LP.result_path(VID, START, END, LP.decoder_sha())
        es = json.load(open(out))
        self.assertEqual(es[-1]["outcome"], "no_difference")
        es[-1]["cut"]["sentence_edge"] = {"out": self.OUT}          # as the pre-check recorded it before ruling 162
        json.dump(es, open(out, "w"))
        decodes, heard = len(self.decodes), len(self.heard)
        self.request("r2", approved_text=ATTESTED)
        LP.serve_once(log=self.log)
        e = self.entry(ATTESTED)
        self.assertEqual((e["request_id"], e["reused"], e["outcome"], e["lock"]), ("r2", True, "hold", None), e)
        self.assertIn(self.OUT, e["reason"])
        self.assertEqual((len(self.decodes), len(self.heard)), (decodes, heard))    # no new spend
        es[-1]["cut"]["sentence_edge"] = {"in": "'not' does not end a sentence"}    # an IN edge alone stays a pass
        json.dump(es, open(out, "w"))
        self.request("r3", approved_text=ATTESTED)
        LP.serve_once(log=self.log)
        self.assertEqual((self.entry(ATTESTED)["request_id"], self.entry(ATTESTED)["outcome"]), ("r3", "no_difference"))


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

    def test_a_filler_only_the_second_recogniser_hears_is_not_a_difference(self):   # ruling 135 (d) (adopted
        e = self.ask("So over time I came to the conclusion.", "So over time, um, I came to the conclusion.")  # under 84)
        self.assertEqual((e["outcome"], e["as_spoken"]["verdict"], e["as_spoken"]["classes"]),
                         ("no_difference", "same", []), e)
        self.assertEqual(e["lock"]["text"], "So over time I came to the conclusion.")     # the decode's words stand
        self.assertIsNone(e["spoken_text"])

    def test_a_and_b_together_the_2012_builds_shape(self):                   # ruling 143 (2)
        e = self.ask(RUN84, SPOKEN84)
        self.assertNotEqual(e["outcome"], "hold", e)
        self.assertEqual(e["as_spoken"]["classes"], ["small"])         # ruling 135 (d): the fillers are not words
    def test_b_two_function_words_in_one_span_never_hold(self):              # ruling 143 (2) (84 (b) held them)
        e = self.ask("I go to the bank and I punch in my code.", "I go to a bank and I punch on my code.")
        self.assertNotEqual(e["outcome"], "hold", e)
        self.assertEqual(e["as_spoken"]["classes"], ["small", "small"])
    def test_a_material_substitution_holds_and_a_small_one_never(self):      # ruling 143 (2) / (3)
        for run, heard in (("It took 15 years.", "It took 50 years."),                         # a number
                           ("You can do it.", "You can't do it.")):                            # a negation
            with self.subTest(run=run):
                e = self.ask(run, heard)                       # the decode (= the transcript) against the second:
                self.assertEqual((e["outcome"], e["as_spoken"]["classes"]), ("hold", ["material"]), e)   # disagree
        for run, heard in (("I went in the house today.", "I went into a house today."),     # two small words
                           ("The bank owns the money.", "The bank holds the money.")):        # a content word
            with self.subTest(run=run):
                e = self.ask(run, heard)
                self.assertEqual((e["outcome"], e["as_spoken"]["classes"]), ("no_difference", ["small"]), e)
    def test_a_filler_only_the_lock_has_is_not_a_difference(self):     # ruling 135 (d) (it held under ruling 84)
        e = self.ask("So um I came here today.", "So I came here today.")
        self.assertEqual((e["outcome"], e["as_spoken"]["verdict"], e["as_spoken"]["classes"]),
                         ("no_difference", "same", []), e)

    def test_a_filler_between_the_speakers_repeat_never_holds(self):         # ruling 143 (2)
        e = self.ask("Bitcoin and an asset is going up.", "Bitcoin and, uh, and an asset is going up.")
        self.assertNotEqual(e["outcome"], "hold", e)
        self.assertEqual(e["as_spoken"]["classes"], ["small"])
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
        verdict, diffs, cls, text = LP.as_spoken(lock, words, sw)  # RULING 143: a small word never holds, the lock
        self.assertEqual((verdict, diffs, cls), ("same", [["so", "or"]], ["small"]))      # text stands
    def test_1b4a63d0s_hook_passes_under_ruling_143(self):                    # it held under rulings 67 / 84
        s, a, sw, _ = real_span("Sjb6lUiL0m4_3090.750-3109.870.json")
        words, lock = a["transcript"]["words"], self.lock(s, a, sw)
        L, S2, _ = LP.reading(lock, words, sw)
        self.assertGreaterEqual(pinned.audio_share(L, S2), pinned.AUDIO_SHARE_MIN)   # the right audio: its repeats
        verdict, diffs, cls, _ = LP.as_spoken(lock, words, sw)                       # are the speaker's
        self.assertEqual(verdict, "same")
        self.assertEqual(set(cls), {"small"})
        self.assertIn(["", "that's why the bull that's"], diffs)  # a false start with a content word: small
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


class TestRuling103(Base):
    """RULING 103 (orchestrator 2026-11-14 '14:13', the targeted re-listen): when ruling 72's comparison holds on ONE
    number or name token, BOTH recognisers re-read a short window around that token alone (its word times, 1.5 s
    either side); the lock passes on it only if both short readings give the lock's token, else the hold is final.
    Must-fail (the order): a real number disagreement ('68,000' against '86,000') still holds; '401k' against '401'
    passes only when both short readings say 401k."""
    RUN, HEARD = "I don't have a 401k.", "I don't have a 401 ,"

    def ask(self, run, heard, decoder=None, second=None):
        shutil.rmtree(os.path.join(self.root, "work"), True)
        shutil.rmtree(os.path.join(self.root, "results"), True)       # one question, one answer: never a reused entry
        self.run_words, self.scribe_words = spread(run), spread(heard)
        self.short_decoder = spread(decoder) if decoder else None
        self.short_second = spread(second) if second else None
        self.relistened, self.windows = [], []
        self.n = getattr(self, "n", 0) + 1
        self.request(f"r103_{self.n}", approved_text=run)
        LP.serve_once(log=self.log)
        return self.entry(run)

    def test_401k_passes_only_when_both_short_readings_say_401k(self):
        e = self.ask(self.RUN, self.HEARD, "have a 401k. I don't", "have a 401(k). I don't")
        self.assertEqual(e["outcome"], "no_difference", e)                 # the lock's own token stands
        self.assertEqual(e["lock"]["text"], self.RUN)
        self.assertEqual((e["as_spoken"]["verdict"], e["spoken_text"]), ("same", None))   # nothing adopted from scribe
        r = e["relisten"]
        self.assertEqual((r["token"], r["against"], r["verdict"]), ("401k", "401", "pass"))
        self.assertEqual((r["decoder_reading"], r["second_reading"]), ("have a 401k. I don't", "have a 401(k). I don't"))
        w = spread(self.RUN)[-1]                                          # '401k.': its word times, 1.5 s either side
        self.assertEqual(r["window"], [round(w["start"] - 1.5, 3), round(w["end"] + 1.5, 3)])
        self.assertEqual(sorted(k for k, _ in self.relistened), ["decoder", "second"])
        for decoder, second in (("have a 401k. I don't", "have a 401, I don't"),     # the second still hears 401
                                ("have a 401, I don't", "have a 401k. I don't"),     # the decoder now hears 401
                                ("have a 401, I don't", "have a 401, I don't")):     # both hear 401
            with self.subTest(decoder=decoder, second=second):
                e = self.ask(self.RUN, self.HEARD, decoder, second)
                self.assertEqual((e["outcome"], e["relisten"]["verdict"]), ("hold", "hold"), e)
                self.assertEqual((e["relisten"]["decoder_reading"], e["relisten"]["second_reading"]), (decoder, second))
                self.assertIn("ruling 103 re-listen of '401k'", e["reason"])
                self.assertIn("the hold is final", e["reason"])
                self.assertIsNone(e["lock"])

    def test_a_real_number_disagreement_still_holds_after_the_relisten(self):
        run, heard = "It cost them 68,000 dollars.", "It cost them 86,000 dollars."
        for decoder, second in (("cost them 68,000 dollars.", "cost them 86,000 dollars."),
                                ("cost them 86,000 dollars.", "cost them 86,000 dollars.")):
            with self.subTest(decoder=decoder, second=second):
                e = self.ask(run, heard, decoder, second)
                self.assertEqual(e["outcome"], "hold", e)
                self.assertIn("ruling 103 re-listen of '68000'", e["reason"])
                self.assertIn("86,000", e["reason"])
        e = self.ask(run, heard, "cost them 68,000 dollars.", "cost them 68,000 dollars.")   # only both re-reading
        self.assertEqual((e["outcome"], e["relisten"]["verdict"]), ("no_difference", "pass"), e)  # the lock's number

    def test_no_relisten_beyond_one_number_or_name_token(self):
        e = self.ask("It took 15 years in the house.", "It took 50 years into a house.")   # ruling 143: the small words
        self.assertEqual((e["outcome"], (e["relisten"] or {}).get("token")), ("hold", "15"), e)   # beside it never
        for run, heard in (("You can do it.", "You can't do it."),):                               # count: ONE number
            with self.subTest(run=run):                                                           # is re-listened
                e = self.ask(run, heard)
                self.assertEqual((e["outcome"], e["relisten"]), ("hold", None), e)         # a negation: never
                self.assertEqual(self.relistened, [])
                self.assertNotIn("ruling 103", e["reason"])
        e = self.ask("The bank owns the money.", "The bank holds the money.")             # a small word: no hold at all
        self.assertEqual((e["outcome"], e["relisten"]), ("no_difference", None), e)
    def test_no_gpu0_for_the_relisten_is_no_verdict_never_a_final_hold(self):
        self.wants.side_effect = lambda: bool(self.windows)              # a render asks once the window is cut
        e = self.ask(self.RUN, self.HEARD, "have a 401k. I don't", "have a 401k. I don't")
        self.assertEqual(e["outcome"], "error", e)                        # re-ask: no verdict
        self.assertIn("ruling 103: a render asked for GPU0", e["reason"])

    def test_the_spend_and_the_rules(self):
        e = self.ask(self.RUN, self.HEARD, "have a 401k. I don't", "have a 401k. I don't")
        self.assertEqual((e["relisten"]["scribe_usd"], e["scribe_usd"]), (0.0008, round(0.0078 + 0.0008, 4)))
        self.assertIn("ruling 103", e["rules"])
        self.assertEqual(pinned.RELISTEN_PAD_S, 1.5)


SRC = hashlib.sha256(b"\0" * 100_001).hexdigest()         # the fake download's bytes: the same audio as a planted past pass


class TestRuling105(Base):
    """RULING 105 (orchestrator 2026-11-14 '20:13'): across passes on the SAME audio, a number token is adjudicated as
    the lock's only when the decoder is stable, the second recogniser's readings differ among themselves with one
    giving the token, and every differing reading is a truncation ('401' of '401k'). Must-fail (the order): a stable
    disagreement, a different number ('68,000' / '86,000'), a different name."""
    RUN = "I don't have a 401k."

    def past(self, heard, src=SRC):
        p = LP.result_path(VID, START, END, "f" * 64)            # an earlier pass under another decoder sha
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as f:
            json.dump([{"at": "2026-11-14T18:51:07Z", "outcome": "hold", "source_file_sha256": src,
                        "as_spoken": {"text": heard}, "relisten": None}], f)

    def ask(self, run, heard, decoder=None, second=None):
        self.run_words, self.scribe_words = spread(run), spread(heard)
        self.short_decoder = spread(decoder) if decoder else None
        self.short_second = spread(second) if second else None
        self.request("r105", approved_text=run)
        LP.serve_once(log=self.log)
        return self.entry(run)

    def test_the_401k_history_adjudicates_as_the_lock(self):
        self.past("I don't have a 401 ,")                          # 13:51: the second recogniser read 401
        e = self.ask(self.RUN, self.RUN)                            # now it reads 401k: no difference
        u = e["unstable_second_reading"]
        self.assertEqual((e["outcome"], u["verdict"], u["token"]), ("no_difference", "pass", "401k"), e)
        self.assertEqual(sorted(d["token"] for d in u["second_readings"]), ["401", "401k"])
        self.assertTrue(all(u["tests"].values()))

    def test_a_hold_now_is_adjudicated_by_the_unstable_history(self):
        self.past(self.RUN)                                         # an earlier pass read 401k
        e = self.ask(self.RUN, "I don't have a 401 ,", "have a 401k. I don't", "have a 401, I don't")
        self.assertEqual((e["outcome"], e["relisten"]["verdict"]), ("no_difference", "hold"), e)   # 103 alone held
        self.assertEqual(e["unstable_second_reading"]["verdict"], "pass")

    def test_a_stable_disagreement_holds(self):
        self.past("I don't have a 401 ,")
        e = self.ask(self.RUN, "I don't have a 401 ,", "have a 401k. I don't", "have a 401, I don't")
        self.assertEqual((e["outcome"], e["unstable_second_reading"]["verdict"]), ("hold", "hold"), e)
        self.assertFalse(e["unstable_second_reading"]["tests"]["second_unstable"])
        self.assertIn("ruling 105", e["reason"])

    def test_a_different_number_holds_even_when_it_agrees_now(self):
        run = "It cost them 68,000 dollars."
        self.past("It cost them 86,000 dollars.")
        e = self.ask(run, run)
        self.assertEqual((e["outcome"], e["unstable_second_reading"]["verdict"]), ("hold", "hold"), e)
        self.assertFalse(e["unstable_second_reading"]["tests"]["truncations_only"])

    def test_a_different_name_holds_even_when_it_agrees_now(self):
        run = "Then I asked Saylor about it."
        self.past("Then I asked Taylor about it.")
        e = self.ask(run, run)
        self.assertEqual((e["outcome"], e["unstable_second_reading"]["verdict"]), ("hold", "hold"), e)

    def test_another_audio_is_not_history(self):
        self.past("I don't have a 401 ,", src="0" * 64)
        e = self.ask(self.RUN, self.RUN)
        self.assertEqual((e["outcome"], e["unstable_second_reading"]), ("no_difference", None), e)

    def test_a_repeated_anchor_reads_the_token_at_the_windows_middle(self):   # audit batch 84 c1 (glm)
        L = "i said a 401 and a 401k and a lot".split()
        self.assertEqual(pinned.reading_near(L, 6, "and a 401 and a 401 and a".split()), "401")     # middle occurrence
        self.assertEqual(pinned.reading_near(L, 6, "x y z".split()), "")                          # nothing anchors

    def test_the_truncation_rule(self):
        T = pinned.truncation_of
        self.assertEqual([T("401k", "401"), T("68000", "680"), T("saylor", "say"), T("401k", ""), T("403b", "403")],
                         [True, False, False, False, True])


if __name__ == "__main__":
    unittest.main()


class TestRuling131(Base):
    """RULING 131 (orchestrator 2026-11-17 '08:25') in the pre-check: (A) the sealed text takes each pair's two-of-three
    reading (outcome adopt_spoken, spoken_text the settled text, the render's own lock re-made with it as the pin's
    text); (B) a currency symbol is formatting, in the lock and in ruling 72's comparison alike."""
    RUN = ATTESTED.replace("I punch in my code", "I punch in a bunch of codes")
    PIN = ATTESTED.replace("I punch in my code", "I punch in a budget codes")

    def test_a_content_pair_read_as_the_run_is_sealed_as_spoken(self):
        self.run_text = self.RUN                                  # the second recogniser's own spelling differs: the
        self.scribe_text = self.RUN.lower().replace(".", "").replace(",", "")     # sealed text keeps the approved's
        self.request(approved_text=self.PIN)
        LP.serve_once(log=self.log)
        e = self.entry(self.PIN)
        self.assertEqual((e["outcome"], e["spoken_text"]), ("adopt_spoken", self.RUN), e.get("reason"))
        self.assertEqual([(x["run"], x["approved"], x["took"], x["agreed"]) for x in e["adjudication"]["pairs"]],
                         [("bunch of", "budget", "run", ["run", "second"])])
        self.assertEqual(e["lock"]["text"], self.RUN)

    def test_a_third_reading_takes_the_run_decode(self):                     # ruling 143 (2) (it held)
        self.run_text, self.scribe_text = self.RUN, self.RUN.replace("bunch of", "punch of")
        self.request(approved_text=self.PIN)
        LP.serve_once(log=self.log)
        e = self.entry(self.PIN)
        self.assertNotEqual(e["outcome"], "hold", e.get("reason"))
        self.assertEqual(e["adjudication"]["pairs"][0]["second_reads"], "neither")
    def test_a_currency_symbol_in_the_approved_text_is_no_difference(self):
        self.run_text = ATTESTED.replace("the money's not there", "the 2 billion is not there")
        self.scribe_text = self.run_text
        pin = ATTESTED.replace("the money's not there", "the $2 billion is not there")
        self.request(approved_text=pin)
        LP.serve_once(log=self.log)
        e = self.entry(pin)
        self.assertEqual((e["outcome"], e["as_spoken"]["verdict"]), ("no_difference", "same"), e.get("reason"))
        self.assertEqual(e["currency_format"], [["", "dollars"]])

    def test_a_currency_symbol_in_the_second_reading_is_no_difference(self):          # ruling 72's comparison
        self.run_text = ATTESTED.replace("the money's not there", "the 2 billion is not there")
        self.scribe_text = ATTESTED.replace("the money's not there", "the $2 billion is not there")
        self.request(approved_text=self.run_text)
        LP.serve_once(log=self.log)
        e = self.entry(self.run_text)
        self.assertEqual((e["outcome"], e["as_spoken"]["verdict"]), ("no_difference", "same"), e.get("reason"))


class TestReuseAcrossShas(Base):
    """BATCH 101 (ruling 131: nothing paid twice): under a new decoder code the second recogniser's reading of the SAME
    window (another decoder sha's work dir) is reused when it was taken at the same offset and reads as this decode
    does; ruling 77 purges the media, and a re-download need not byte-match it.
    must-fail  the same window read under another decoder code is not paid for again
    must-pay   a reading that reads otherwise (a changed video), one taken at another offset, another window's"""
    def earlier(self, text, offset=740.0, base=None, sha="0123456789ab"):
        d = os.path.join(self.root, "work", f"{base or f'{VID}.{START:.3f}-{END:.3f}'}.{sha}")
        os.makedirs(d, exist_ok=True)
        rec = {"source_file_sha256": "f" * 64, "usd": 0.0078, "words": words_of(text)}
        if offset is not None:
            rec["offset"] = offset
        with open(os.path.join(d, "second_recogniser.json"), "w") as f:
            json.dump(rec, f)
        return os.path.basename(d)

    def answered(self):
        self.request(approved_text=ATTESTED)
        LP.serve_once(log=self.log)
        return self.entry(ATTESTED)

    def test_the_same_window_read_under_another_code_is_not_paid_again(self):
        for offset in (740.0, None):                  # a reading from before batch 101 records no offset
            with self.subTest(offset=offset):
                shutil.rmtree(self.root, True)
                self.heard.clear()
                src = self.earlier(ATTESTED, offset=offset)
                e = self.answered()
                self.assertEqual((e["outcome"], e["scribe_usd"], self.heard), ("no_difference", 0.0, []), e)
                wd = LP.work_dir(VID, START, END, LP.decoder_sha())
                with open(os.path.join(wd, "second_recogniser.json")) as f:
                    c = json.load(f)
                self.assertEqual((c["reused_from"], c["usd"], c["offset"]), (src, 0.0, 740.0))

    def test_a_reading_of_other_words_is_paid_for(self):              # a changed video reads otherwise
        self.earlier("Nothing here is what the decoder heard in this window at all, a different talk entirely.")
        self.assertEqual((self.answered()["scribe_usd"], len(self.heard)), (0.0078, 1))

    def test_a_reading_taken_at_another_offset_is_paid_for(self):
        self.earlier(ATTESTED, offset=700.0)
        self.assertEqual((self.answered()["scribe_usd"], len(self.heard)), (0.0078, 1))

    def test_another_windows_reading_is_never_used(self):
        self.earlier(ATTESTED, base=f"{VID}.{START + 1:.3f}-{END:.3f}")
        self.assertEqual((self.answered()["scribe_usd"], len(self.heard)), (0.0078, 1))

    def test_the_service_names_itself_in_the_day_ledger(self):         # ruling 131
        import outside_spend
        with mock.patch.object(outside_spend, "SERVICE", "unknown"), mock.patch.object(LP, "serve_once",
                                                                                        lambda log=print: 0):
            LP.main(["once"])
            self.assertEqual(outside_spend.SERVICE, "lock_precheck")


class TestRuling135(Base):
    """RULING 135 in ruling 72's comparison: today's Natalie Brunell false start ('a h- low') and 'kinda' / 'kind of' are
    not differences (they held before); a real word the second recogniser alone hears still holds."""

    def test_a_false_start_fragment_is_not_a_word(self):
        self.scribe_text = ATTESTED.replace("punch in my code", "punch in my h- code")
        self.request(approved_text=ATTESTED)
        LP.serve_once(log=self.log)
        e = self.entry(ATTESTED)
        self.assertEqual((e["outcome"], e["as_spoken"]["verdict"]), ("no_difference", "same"), e.get("reason"))

    def test_kinda_is_kind_of(self):
        self.run_text = ATTESTED.replace("they could just take it", "they kind of could take it")
        self.scribe_text = self.run_text.replace("kind of", "kinda")
        self.request(approved_text=self.run_text)
        LP.serve_once(log=self.log)
        e = self.entry(self.run_text)
        self.assertEqual((e["outcome"], e["as_spoken"]["verdict"]), ("no_difference", "same"), e.get("reason"))

    def test_the_brand_spelled_three_ways_passes_and_is_recorded(self):
        self.run_text = ATTESTED.replace("the bank owns the money", "itrust capital owns the money")
        self.scribe_text = ATTESTED.replace("the bank owns the money", "iTrustCapital owns the money")
        pin = ATTESTED.replace("the bank owns the money", "I trust capital owns the money")
        self.request(approved_text=pin)
        LP.serve_once(log=self.log)
        e = self.entry(pin)
        self.assertEqual((e["outcome"], e["spelling_only"]), ("no_difference", [["itrust", "i trust"]]), e.get("reason"))

    def test_a_small_word_the_second_recogniser_alone_hears_never_holds(self):   # ruling 143 (2)
        self.scribe_text = ATTESTED.replace("punch in my code", "punch in my secret code")
        self.request(approved_text=ATTESTED)
        LP.serve_once(log=self.log)
        self.assertNotEqual(self.entry(ATTESTED)["outcome"], "hold")
class TestRuling135LoneLetter(Base):
    """Ruling 135 (d) + Heimdall batch 104 c2: a lone letter the LOCK carries (the decode and the approved text both hear
    it) is a word, not a stray sound: the second recogniser missing it is still a difference."""

    def test_a_letter_two_readings_hear_is_still_compared(self):
        self.run_text = ATTESTED.replace("punch in my code", "punch in my B code")
        self.scribe_text = ATTESTED
        self.request(approved_text=self.run_text)
        LP.serve_once(log=self.log)
        e = self.entry(self.run_text)
        self.assertNotEqual(e["as_spoken"]["verdict"], "same", e)
        self.assertIn(["b", ""], e["as_spoken"]["differences"])


class TestBatch109EmptySource(Base):
    """Batch 109 (the builder's 14:24 finding on ruling 141 (4)'s story): Bitcoin Magazine MeC8YEmUx_w was post_live,
    and its DASH section downloaded with no media (a 0 s container), so pinned.validate_range raised 'range outside the
    source file (file covers 0-0.000 s ...)' and the pre-check answered HOLD, a final verdict on words never heard. An
    empty window is outcome "error" (no verdict, never a pass), its broken file is dropped so the next request downloads
    afresh, and a real range fault on a file with media still holds. must-fail on the code before batch 109."""

    def test_an_empty_window_is_no_verdict_and_is_fetched_again(self):
        self.request(approved_text=ATTESTED)
        with mock.patch.object(pinned, "_duration", lambda path: 0.0):
            LP.serve_once(log=self.log)
        e = self.entry(ATTESTED)
        self.assertEqual(e["outcome"], "error")
        self.assertIn("downloaded empty", e["reason"])
        self.assertIsNone(e["lock"])
        wd = LP.work_dir(VID, START, END, LP.decoder_sha())
        self.assertFalse(os.path.exists(os.path.join(wd, "sources", f"{VID}.mp4")))     # never served again
        n = len(self.downloads)
        self.request("r2", approved_text=ATTESTED)                   # the video processed: asked again, answered
        LP.serve_once(log=self.log)
        self.assertEqual(self.entry(ATTESTED)["outcome"], "no_difference")
        self.assertGreater(len(self.downloads), n)

    def test_a_range_fault_on_a_file_with_media_still_holds(self):
        self.request(approved_text=ATTESTED)
        with mock.patch.object(pinned, "_duration", lambda path: 5.0):    # media, but the span lies past its end
            LP.serve_once(log=self.log)
        e = self.entry(ATTESTED)
        self.assertEqual(e["outcome"], "hold")
        self.assertIn("range outside the source file", e["reason"])


class TestRuling146(Base):
    """RULING 146 (2) (orchestrator 2026-11-18 '07:55'): G17a's quiet before the hook's first word is SOFT. The render's
    cut keeps a hook it cannot give 80 ms (lock_cut's hook_lead "short"); the pre-check records it for the builder's
    flag and never holds on it."""
    SHORT = "no legal cut in the pause keeps 80 ms of genuine quiet before the hook's first word (best 30 ms)"

    def test_a_hook_cut_short_of_80_ms_passes_and_is_recorded(self):
        self.cut = {**self.cut, "hook_lead": {"short": self.SHORT, "lead_ms": 30, "rule": "ruling 146 (2)"}}
        self.request(approved_text=ATTESTED, role="hook")
        LP.serve_once(log=self.log)
        e = self.entry(ATTESTED)
        self.assertEqual(e["outcome"], "no_difference", e)
        self.assertEqual((e["cut"]["cut_in"], e["cut"]["hook_lead_short"]), (15.2, self.SHORT))

    def test_a_clip_records_no_short_lead(self):
        self.request(approved_text=ATTESTED)
        LP.serve_once(log=self.log)
        self.assertIsNone(self.entry(ATTESTED)["cut"]["hook_lead_short"])


class TestRuling139(Base):
    """RULING 139 / 147 (3): a lock edge at a word boundary that is not a sentence edge passes the render's cut, marked;
    the pre-check records it for the builder's flag and never holds on it."""

    def test_a_sentence_edge_passes_and_is_recorded(self):
        self.cut = {**self.cut, "sentence_edge": {"in": "'not' does not end a sentence"}}
        self.request(approved_text=ATTESTED)
        LP.serve_once(log=self.log)
        e = self.entry(ATTESTED)
        self.assertEqual(e["outcome"], "no_difference", e)
        self.assertEqual(e["cut"]["sentence_edge"], {"in": "'not' does not end a sentence"})
