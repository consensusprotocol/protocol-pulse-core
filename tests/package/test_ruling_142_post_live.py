#!/usr/bin/env python3
"""RULING 142 (3) on the builder's side (orchestrator 14:32 ET Nov 17): a post_live YouTube stream (DASH segments only)
gives an EMPTY section download (MeC8YEmUx_w, 15:5x ET: 258 bytes, 0 s), so this side's word check
(transcript_truth.audio_window) and frame sheet (visual_pin.fetch) would fail closed on every clip of it. They now fetch
the whole stream once per video (the integrator's read-only cache first, batch 111), cut the window locally, and still
fail closed when even that holds no media. Offline: yt-dlp, ffmpeg and the duration probe are stubbed."""
import os
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "pipeline"))
import transcript_truth as TT  # noqa: E402
import visual_pin as VP  # noqa: E402

REAL_REPLACE = os.replace


class Media:
    """yt-dlp / ffmpeg stand-ins that write the files they would, and a duration table for media_seconds."""

    def __init__(self, section_s=0.0, cut_s=None, write_section=True):
        self.calls, self.section_s, self.cut_s, self.write_section = [], section_s, cut_s, write_section
        self.seconds = {}

    def run(self, cmd, **kw):
        self.calls.append(list(cmd))
        if cmd[0] == "yt-dlp":
            out = cmd[cmd.index("-o") + 1].replace("%(ext)s", "m4a" if "bestaudio" in cmd[cmd.index("-f") + 1]
                                                   else "mp4")
            if "--download-sections" in cmd:
                if self.write_section:
                    open(out, "w").write("x")
                    self.seconds[out] = self.section_s
            else:
                open(out, "w").write("whole")
                self.seconds[out] = 5700.0
        elif cmd[0] == "ffmpeg":
            out = cmd[-1]
            open(out, "w").write("cut")
            if "-ss" in cmd:                          # a cut from a whole stream
                self.seconds[out] = float(cmd[cmd.index("-t") + 1]) if self.cut_s is None else self.cut_s
            else:
                self.seconds[out] = 15.0
        return mock.Mock(returncode=0, stdout="", stderr="")

    def secs(self, path):
        return self.seconds.get(path, 0.0)

    def replace(self, src, dst):                       # a cut renamed into place keeps its duration
        REAL_REPLACE(src, dst)
        self.seconds[dst] = self.seconds.pop(src, 0.0)

    def wholes(self):
        return [c for c in self.calls if c[0] == "yt-dlp" and "--download-sections" not in c]


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d, self.cache = os.path.join(self.tmp.name, "w"), os.path.join(self.tmp.name, "theirs")
        os.makedirs(self.d)

    def tearDown(self):
        self.tmp.cleanup()

    def patched(self, m):
        return [mock.patch.object(TT.subprocess, "run", m.run), mock.patch.object(TT, "media_seconds", m.secs),
                mock.patch.object(TT, "POST_LIVE_CACHE", self.cache), mock.patch.object(os, "replace", m.replace)]

    def go(self, m, fn):
        ps = self.patched(m)
        for p in ps:
            p.start()
        try:
            return fn()
        finally:
            for p in ps:
                p.stop()


class TestTheWordChecksWindow(Base):
    def test_an_empty_section_is_cut_from_the_whole_stream_fetched_once(self):
        m = Media(section_s=0.0)
        wav, a = self.go(m, lambda: TT.audio_window("vid", 100.0, 110.0, self.d))
        self.assertEqual((a, m.secs(wav) > 0), (96.0, True))
        self.assertEqual(len(m.wholes()), 1)
        cut = [c for c in m.calls if c[0] == "ffmpeg"][-1]
        self.assertEqual((cut[cut.index("-ss") + 1], cut[cut.index("-t") + 1]), ("96.000", "15.500"))
        self.go(m, lambda: TT.audio_window("vid", 200.0, 210.0, self.d))         # another window: the same stream
        self.assertEqual(len(m.wholes()), 1)

    def test_the_integrators_cached_stream_is_read_first(self):
        os.makedirs(os.path.join(self.cache, "vid"))
        theirs = os.path.join(self.cache, "vid", "audio.m4a")
        open(theirs, "w").write("whole")
        m = Media(section_s=0.0)
        m.seconds[theirs] = 5700.0
        self.go(m, lambda: TT.audio_window("vid", 100.0, 110.0, self.d))
        self.assertEqual(m.wholes(), [])                                           # no download of our own
        self.assertIn(theirs, [c for c in m.calls if c[0] == "ffmpeg"][-1])

    def test_no_section_file_at_all_takes_the_whole_stream_too(self):
        m = Media(write_section=False)
        wav, _ = self.go(m, lambda: TT.audio_window("vid", 100.0, 110.0, self.d))
        self.assertTrue(m.secs(wav) > 0)
        self.assertEqual(len(m.wholes()), 1)

    def test_a_normal_section_is_used_as_before(self):
        m = Media(section_s=15.5)
        self.go(m, lambda: TT.audio_window("vid", 100.0, 110.0, self.d))
        self.assertEqual(m.wholes(), [])
        self.assertNotIn("-ss", [c for c in m.calls if c[0] == "ffmpeg"][-1])

    def test_a_cut_with_no_audio_fails_closed_and_is_never_kept(self):
        m = Media(section_s=0.0, cut_s=0.0)
        with self.assertRaises(OSError):
            self.go(m, lambda: TT.audio_window("vid", 100.0, 110.0, self.d))
        self.assertFalse([f for f in os.listdir(self.d) if f.endswith(".wav")])


class TestTheFrameSheetsVideo(Base):
    def test_an_empty_section_is_cut_from_the_whole_stream_and_kept(self):
        m = Media(section_s=0.0)
        v = self.go(m, lambda: VP.fetch("vid", 100.0, 110.0, self.d))
        self.assertTrue(v.endswith(".cut.mp4") and m.secs(v) > 0, v)
        cut = [c for c in m.calls if c[0] == "ffmpeg"][-1]
        self.assertEqual((cut[cut.index("-ss") + 1], cut[cut.index("-t") + 1]), ("100.000", "10.000"))
        self.assertIn("scale=-2:'min(480,ih)'", cut)                               # the sheet's <= 480p
        n = len(m.calls)
        self.assertEqual(self.go(m, lambda: VP.fetch("vid", 100.0, 110.0, self.d)), v)   # cut once, then kept
        self.assertEqual(len(m.calls), n)

    def test_a_partial_cut_left_behind_is_never_returned(self):
        """Audit 20261117_1556 C1 (qwen): an interrupted earlier cut must not stand for the span."""
        os.makedirs(os.path.join(self.d, "visual"))
        bad = os.path.join(self.d, "visual", "vid_100000_110000.cut.mp4")
        open(bad, "w").write("partial")                                  # 0 s by the duration table
        m = Media(section_s=0.0)
        v = self.go(m, lambda: VP.fetch("vid", 100.0, 110.0, self.d))
        self.assertEqual((v, m.secs(v)), (bad, 10.0))                        # re-cut, whole
        self.assertTrue([c for c in m.calls if c[0] == "ffmpeg"])

    def test_a_normal_section_is_returned_as_before(self):
        m = Media(section_s=10.0)
        v = self.go(m, lambda: VP.fetch("vid", 100.0, 110.0, self.d))
        self.assertTrue(v.endswith("vid_100000_110000.mp4"), v)
        self.assertEqual(m.wholes(), [])

    def test_a_cut_with_no_picture_fails_closed_and_is_never_kept(self):
        m = Media(section_s=0.0, cut_s=0.0)
        with self.assertRaises(OSError):
            self.go(m, lambda: VP.fetch("vid", 100.0, 110.0, self.d))
        self.assertFalse(os.path.exists(os.path.join(self.d, "visual", "vid_100000_110000.cut.mp4")))


if __name__ == "__main__":
    unittest.main()
