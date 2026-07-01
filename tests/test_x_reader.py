"""Offline unit tests for services/x_reader.py — no network calls."""
import json
import os
import sys
import tempfile
import time
import unittest
from unittest import mock

sys.path.insert(0, os.path.expanduser("~/protocol_pulse"))
from services import x_reader  # noqa: E402


class TestParsing(unittest.TestCase):
    def test_parse_plain_array(self):
        self.assertEqual(x_reader.parse_json_block('[{"a":1}]'), [{"a": 1}])

    def test_parse_fenced(self):
        t = "```json\n[{\"a\": 1}]\n```"
        self.assertEqual(x_reader.parse_json_block(t), [{"a": 1}])

    def test_parse_with_preamble(self):
        t = "Here are the posts:\n[{\"a\": 1}, {\"b\": 2}]\nHope that helps."
        self.assertEqual(x_reader.parse_json_block(t), [{"a": 1}, {"b": 2}])

    def test_parse_object(self):
        t = 'blah {"sentiment": "bullish", "n": [1,2]} blah'
        self.assertEqual(x_reader.parse_json_block(t)["sentiment"], "bullish")

    def test_parse_garbage(self):
        self.assertIsNone(x_reader.parse_json_block("no json here"))
        self.assertIsNone(x_reader.parse_json_block(""))

    def test_extract_post_id(self):
        self.assertEqual(
            x_reader.extract_post_id("https://x.com/saylor/status/123456"),
            "123456")
        self.assertEqual(x_reader.extract_post_id("https://x.com/saylor"), "")
        self.assertEqual(x_reader.extract_post_id(None), "")


class TestCache(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self._orig = x_reader.CACHE_DIR
        x_reader.CACHE_DIR = self.tmp

    def tearDown(self):
        x_reader.CACHE_DIR = self._orig

    def test_roundtrip_and_ttl(self):
        key = x_reader._cache_key("posts", {"h": ["a"]})
        x_reader._cache_put(key, [{"x": 1}])
        self.assertEqual(x_reader._cache_get(key, ttl=60), [{"x": 1}])
        # expire it
        path = os.path.join(self.tmp, key + ".json")
        old = time.time() - 9999
        os.utime(path, (old, old))
        self.assertIsNone(x_reader._cache_get(key, ttl=60))

    def test_key_stability(self):
        a = x_reader._cache_key("posts", {"h": ["a"], "n": 1})
        b = x_reader._cache_key("posts", {"n": 1, "h": ["a"]})
        self.assertEqual(a, b)


class TestGating(unittest.TestCase):
    def test_disabled_returns_empty(self):
        with mock.patch.object(x_reader, "_load_config",
                               return_value={**x_reader.DEFAULT_CONFIG,
                                             "enabled": False}):
            self.assertEqual(x_reader.get_top_posts(["saylor"]), [])
            self.assertIsNone(
                x_reader.get_reactions("https://x.com/a/status/1"))

    def test_degraded_rejected(self):
        with mock.patch.object(x_reader, "_load_config",
                               return_value={**x_reader.DEFAULT_CONFIG,
                                             "enabled": True}), \
             mock.patch.object(x_reader, "_call_xsearch",
                               return_value=(None, [], {})):
            self.assertEqual(x_reader.get_top_posts(["saylor"]), [])

    def test_posts_filtered_to_requested_handles_and_status_urls(self):
        fake_text = json.dumps([
            {"author": "saylor", "url": "https://x.com/saylor/status/111",
             "text": "btc", "likes": 5, "reply_sentiment": "bullish"},
            {"author": "randomguy", "url": "https://x.com/randomguy/status/2",
             "text": "spam", "likes": 999, "reply_sentiment": "neutral"},
            {"author": "saylor", "url": "https://x.com/saylor",  # no id
             "text": "bad url", "likes": 1, "reply_sentiment": "neutral"},
        ])
        with mock.patch.object(x_reader, "_load_config",
                               return_value={**x_reader.DEFAULT_CONFIG,
                                             "enabled": True}), \
             mock.patch.object(x_reader, "_cache_get", return_value=None), \
             mock.patch.object(x_reader, "_cache_put"), \
             mock.patch.object(x_reader, "_call_xsearch",
                               return_value=(fake_text, ["c1"], {})):
            posts = x_reader.get_top_posts(["saylor"], limit=10)
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0]["post_id"], "111")
        self.assertEqual(posts[0]["engagement"], 5)

    def test_reactions_radar_shape(self):
        fake = json.dumps({
            "sentiment": "mixed",
            "top_reply_themes": ["etf", "fees"],
            "representative_replies": [
                {"author": "@bob", "likes": "12", "text": "nice"}]})
        with mock.patch.object(x_reader, "_load_config",
                               return_value={**x_reader.DEFAULT_CONFIG,
                                             "enabled": True}), \
             mock.patch.object(x_reader, "_cache_get", return_value=None), \
             mock.patch.object(x_reader, "_cache_put"), \
             mock.patch.object(x_reader, "_call_xsearch",
                               return_value=(fake, ["c1"], {})):
            rx = x_reader.get_reactions("https://x.com/saylor/status/111")
        self.assertEqual(rx["sentiment"], "mixed")
        r = rx["representative_replies"][0]
        # exact keys comment_radar.synthesize() consumes
        self.assertEqual(set(r.keys()), {"author", "likes", "text"})
        self.assertEqual(r["author"], "bob")
        self.assertEqual(r["likes"], 12)


if __name__ == "__main__":
    unittest.main(verbosity=2)
