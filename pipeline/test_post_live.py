"""RULING 142 (3) (orchestrator 14:32 ET Nov 17), batch 111: a post_live stream (Bitcoin Magazine MeC8YEmUx_w today)
cannot be cut by yt-dlp --download-sections: its DASH section comes back with seconds of picture, no audio and a 0 s
container. The standing fallback: such a section is replaced by a local cut of the WHOLE stream (audio and video
downloaded once per video), and pinned.acquire checks that source's clock against the transcript's word timings, HARD:
the median offset of the render's decode against the word pass's record within 0.35 s on at least 10 words, else the
lock holds. must-fail on the code before batch 111 (no fallback, no guard)."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pinned as P  # noqa: E402
import select_passages as SP  # noqa: E402


def probe(fmt, aud):
    out = {"format": {"duration": str(fmt)},
           "streams": [{"codec_type": "video", "duration": "5.005"}] +
                      ([{"codec_type": "audio", "duration": str(aud)}] if aud is not None else [])}
    return mock.patch.object(SP.subprocess, "run",
                             return_value=subprocess.CompletedProcess([], 0, stdout=json.dumps(out), stderr=""))


class TestHasMedia(unittest.TestCase):
    def test_a_post_live_section_has_no_media(self):
        with probe(0.0, 0.023):                                  # MeC8YEmUx_w's section, as measured
            self.assertFalse(SP._has_media("x.mp4"))
        with probe(40.03, None):                                 # picture without audio
            self.assertFalse(SP._has_media("x.mp4"))
        with probe(40.03, 40.0):
            self.assertTrue(SP._has_media("x.mp4"))

    def test_an_unreadable_file_is_left_to_the_path_that_follows(self):      # as before batch 111
        with mock.patch.object(SP.subprocess, "run", side_effect=OSError("no ffprobe")):
            self.assertTrue(SP._has_media("x.mp4"))
        with mock.patch.object(SP.subprocess, "run",
                               return_value=subprocess.CompletedProcess([], 1, stdout="", stderr="Invalid data")):
            self.assertTrue(SP._has_media("x.mp4"))


class TestDownloadWindowFallback(unittest.TestCase):
    """A fake yt-dlp and ffmpeg: a section download writes a file WITHOUT media (the post_live signature); a whole-stream
    download and the local cut write files WITH media."""

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="post_live_")
        self.addCleanup(shutil.rmtree, self.d, True)
        self.calls, self.media = [], set()

        def run(cmd, **kw):
            self.calls.append(list(cmd))
            if cmd[0] == "yt-dlp":
                out = cmd[cmd.index("-o") + 1]
                os.makedirs(os.path.dirname(out), exist_ok=True)
                with open(out, "wb") as f:
                    f.write(b"\0" * (750_000 if "--download-sections" in cmd else 200_000))
                if "--download-sections" not in cmd:
                    self.media.add(out)
            elif cmd[0] == "ffmpeg":
                with open(cmd[-1], "wb") as f:
                    f.write(b"\0" * 300_000)
                self.media.add(cmd[-1])
            return subprocess.CompletedProcess(cmd, 0, "", "")
        for p in (mock.patch.object(SP.subprocess, "run", run),
                  mock.patch.object(SP, "_has_media", lambda path: path in self.media),
                  mock.patch.object(SP, "POST_LIVE_DIR", os.path.join(self.d, "cache"))):
            p.start()
            self.addCleanup(p.stop)

    def test_a_section_without_media_is_cut_from_the_whole_stream(self):
        path, off = SP._download_window("MeC8YEmUx_w", 5409.96, 5420.32, os.path.join(self.d, "run"))
        self.assertEqual(off, 5395.0)
        self.assertTrue(os.path.exists(path + ".post_live.json"))
        ytdl = [c for c in self.calls if c[0] == "yt-dlp"]
        self.assertEqual(len(ytdl), 3)                       # the section, then the whole audio and the whole video
        self.assertIn("--download-sections", ytdl[0])
        self.assertTrue(all("--download-sections" not in c for c in ytdl[1:]))
        cut = [c for c in self.calls if c[0] == "ffmpeg"]
        self.assertEqual(len(cut), 1)
        self.assertEqual(cut[0][cut[0].index("-ss") + 1], "5395.000")          # the file starts at the window's start
        self.assertEqual(cut[0][cut[0].index("-t") + 1], f"{5420.32 + 15 - 5395.0:.3f}")
        n = len(self.calls)                                  # another window of the same video: the stream is reused
        SP._download_window("MeC8YEmUx_w", 3767.8, 3770.04, os.path.join(self.d, "run2"))
        self.assertEqual([c[0] for c in self.calls[n:]], ["yt-dlp", "ffmpeg"])

    def test_a_cache_hit_probes_and_downloads_nothing(self):          # red-team F2: a valid cache hit is silent
        out = os.path.join(self.d, "run", "sources", "MeC8YEmUx_w.mp4")
        os.makedirs(os.path.dirname(out))
        with open(out, "wb") as f:
            f.write(b"\0" * 750_000)
        self.assertEqual(SP._download_window("MeC8YEmUx_w", 5409.96, 5420.32, os.path.join(self.d, "run")),
                         (out, 5395.0))
        self.assertEqual(self.calls, [])

    def test_a_section_with_media_is_used_as_before(self):
        with mock.patch.object(SP, "_has_media", lambda path: True):
            path, off = SP._download_window("RsCi56hEriU", 1590.932, 1597.172, os.path.join(self.d, "run"))
        self.assertEqual(off, 1576.0)
        self.assertFalse(os.path.exists(path + ".post_live.json"))
        self.assertEqual([c[0] for c in self.calls], ["yt-dlp"])

    def test_no_whole_stream_means_no_source(self):
        def run(cmd, **kw):
            self.calls.append(list(cmd))
            if "--download-sections" in cmd:
                out = cmd[cmd.index("-o") + 1]
                with open(out, "wb") as f:
                    f.write(b"\0" * 750_000)
            return subprocess.CompletedProcess(cmd, 1, "", "")      # the whole-stream download fails
        with mock.patch.object(SP.subprocess, "run", run):
            self.assertEqual(SP._download_window("MeC8YEmUx_w", 5409.96, 5420.32, os.path.join(self.d, "run")),
                             (None, 0))


class TestPostLiveOffset(unittest.TestCase):
    WORDS = ("Being able to use Bitcoin doesn't depend on whether the House or the Senate is red or blue because "
             "Bitcoin lives outside of the institutions").split()

    def setUp(self):
        self.repo = tempfile.mkdtemp(prefix="post_live_repo_")
        self.addCleanup(shutil.rmtree, self.repo, True)
        d = os.path.join(self.repo, "data", "editorial", "transcripts", "VID", "windows")
        os.makedirs(d)
        self.rec = [{"word": w, "start": round(100.0 + i * 0.4, 3), "end": round(100.3 + i * 0.4, 3)}
                    for i, w in enumerate(self.WORDS)]
        with open(os.path.join(d, "90.000-120.000.whisper_words_punct.json"), "w") as f:
            json.dump({"words": self.rec}, f)
        p = mock.patch.object(P, "REPO", self.repo)
        p.start()
        self.addCleanup(p.stop)

    def tr(self, shift, offset=95.0, n=None):
        return {"words": [{"word": w["word"], "start": w["start"] + shift - offset, "end": w["end"] + shift - offset}
                          for w in self.rec[:n]]}

    def test_the_decoders_own_bias_passes(self):
        self.assertAlmostEqual(P.post_live_offset("VID", self.tr(-0.1), 95.0), -0.1, places=3)

    def test_a_shifted_stream_holds(self):
        with self.assertRaises(P.PinError) as e:
            P.post_live_offset("VID", self.tr(2.0), 95.0)
        self.assertIn("shifted +2.00 s", str(e.exception))

    def test_no_record_or_too_few_words_holds(self):
        with self.assertRaises(P.PinError) as e:
            P.post_live_offset("OTHER", self.tr(0.0), 95.0)
        self.assertIn("no transcript word timings", str(e.exception))
        with self.assertRaises(P.PinError) as e:
            P.post_live_offset("VID", self.tr(0.0, n=5), 95.0)
        self.assertIn("only 5 words align", str(e.exception))
        with self.assertRaises(P.PinError):
            P.post_live_offset("VID", {"words": []}, 95.0)


class TestAcquireRoute(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="post_live_acq_")
        self.addCleanup(shutil.rmtree, self.d, True)
        self.src = os.path.join(self.d, "sources", "VID.mp4")
        os.makedirs(os.path.dirname(self.src))
        with open(self.src, "wb") as f:
            f.write(b"x" * 10)
        self.pin = {"segments": [{"video_id": "VID", "start": 100.0, "end": 106.0, "source": {"kind": "youtube"}}]}

    def acquire(self, guard):
        with mock.patch.object(SP, "_download_window", lambda *a, **k: (self.src, 85.0)), \
                mock.patch.object(SP, "_whisper_transcribe", lambda *a, **k: {"words": [{"word": "x", "start": 1.0}]}), \
                mock.patch.object(P, "post_live_offset", guard):
            return P.acquire(self.pin, self.d, log=lambda *_: None)

    def test_a_post_live_source_is_named_and_its_clock_checked(self):
        with open(self.src + ".post_live.json", "w") as f:
            f.write("{}")
        g = mock.Mock(return_value=-0.1)
        out = self.acquire(g)
        self.assertEqual((out["VID"]["provenance"]["kind"], out["VID"]["provenance"]["post_live_offset_s"]),
                         ("youtube_post_live", -0.1))
        g.assert_called_once()
        with self.assertRaises(P.PinError):
            self.acquire(mock.Mock(side_effect=P.PinError("VID: post_live source shifted +2.00 s")))

    def test_a_normal_window_is_not_checked(self):
        g = mock.Mock(return_value=0.0)
        out = self.acquire(g)
        self.assertEqual(out["VID"]["provenance"]["kind"], "youtube_window")
        g.assert_not_called()


if __name__ == "__main__":
    unittest.main()
