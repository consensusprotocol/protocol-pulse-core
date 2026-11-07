#!/usr/bin/env python3
"""scan.fetch_rss falls back to yt-dlp listing when YouTube RSS fails (2026-11-07 outage)."""
import os
import subprocess
import sys
import unittest
import urllib.error
import urllib.request
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scan  # noqa: E402


class TestRssFallback(unittest.TestCase):
    def test_http_error_uses_ytdlp_listing(self):
        out = "AAAAAAAAAAA\t1794013200\tFirst title\nBBBBBBBBBBB\tNA\tNo date\nCCCCCCCCCCC\t1793923200\tThird\n"
        with mock.patch.object(urllib.request, "urlopen", side_effect=urllib.error.HTTPError("u", 404, "nf", {}, None)), \
             mock.patch.object(subprocess, "run", return_value=subprocess.CompletedProcess([], 0, out, "")) as run:
            v = scan.fetch_rss("UCB6Q0S1gUHXMe5-Jjx0_laQ")
        self.assertEqual([x["video_id"] for x in v], ["AAAAAAAAAAA", "CCCCCCCCCCC"])   # undated entries skipped
        self.assertEqual(v[0]["published"], "2026-11-07T01:00:00+00:00")
        self.assertEqual(v[0]["published_source"], "yt-dlp approximate_date")
        self.assertIn("youtubetab:approximate_date", run.call_args[0][0])

    def test_ytdlp_failure_returns_empty_not_raise(self):
        with mock.patch.object(urllib.request, "urlopen", side_effect=urllib.error.URLError("down")), \
             mock.patch.object(subprocess, "run", side_effect=subprocess.TimeoutExpired("yt-dlp", 1)):
            self.assertEqual(scan.fetch_rss("UCx"), [])


if __name__ == "__main__":
    unittest.main()
