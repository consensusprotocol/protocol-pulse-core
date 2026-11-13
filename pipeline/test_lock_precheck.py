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

        def transcribe(source_path, video_id, run_dir):
            self.decodes.append(video_id)
            out = {"words": words_of(self.run_text), "language": "en", "duration": 39.0}
            p = os.path.join(run_dir, "transcripts", f"{video_id}.json")
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w") as f:
                json.dump(out, f)
            return out

        def scribe(src):
            self.heard.append(src)
            return words_of(self.scribe_text), 0.0078

        self.wants = mock.Mock(return_value=False)
        for p in (mock.patch.object(LP, "ROOT", self.root),
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
        self.assertEqual(e["scribe_usd"], 0)
        self.assertEqual(self.heard, [])
        self.assertTrue(os.path.basename(LP.result_path(VID, START, END, LP.decoder_sha())).startswith(
            f"{VID}.755.454-764.214.{LP.decoder_sha()[:12]}"))
        self.assertTrue(os.path.exists(os.path.join(self.root, "requests", "done", "r1.json")))
        self.assertEqual([d[:3] for d in self.downloads], [(VID, START, END)] * 2)   # prefetch + acquire's cache hit
        self.assertEqual(self.decodes, [VID])

    def test_the_attested_text_meets_no_difference_and_no_spend(self):
        self.request(approved_text=ATTESTED.upper().replace(".", ""))      # canonical tokens equal
        LP.serve_once(log=self.log)
        e = self.entry(ATTESTED.upper().replace(".", ""))
        self.assertEqual(e["outcome"], "no_difference", e)
        self.assertEqual((e["scribe_usd"], self.heard), (0, []))

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
        self.scribe_text = ATTESTED                               # the second recogniser reads the approved words
        self.request(approved_text=ATTESTED)
        LP.serve_once(log=self.log)
        e = self.entry(ATTESTED)
        self.assertEqual(e["outcome"], "adopted", e)
        self.assertEqual(e["lock"]["text"], ATTESTED)             # the lock takes the approved text
        self.assertEqual(e["adjudication"]["verdict"], "approved")

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


if __name__ == "__main__":
    unittest.main()
