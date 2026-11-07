#!/usr/bin/env python3
"""Tests for the transcript-first editorial layer (PBX 2026-11-06 requirements):
  1. differently worded transcripts are identified as the same event      (real bge + GPU0 LLM)
  2. identical loose words do not create false story identity              (real bge + GPU0 LLM)
  3. a caption HTTP 429 switches acquisition to Whisper, never "no transcript"
  4. transcript chunks cannot lose source URL / video ID provenance
  5. layout-ineligible sources may contribute editorial evidence but never become clips
Run: CUDA_VISIBLE_DEVICES=0 python3 -m pytest pipeline/test_editorial.py -v
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

PIPELINE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PIPELINE)

import transcript_store as ts  # noqa: E402

HAVE_GPU = os.environ.get("CUDA_VISIBLE_DEVICES") == "0"
REG = {c["display_name"]: c for c in json.load(open(os.path.join(PIPELINE, "channels.json")))}


class TempStore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="edstore_")
        self._saved = (ts.STORE_DIR, ts.TRANSCRIPTS_DIR, ts.STATE_DIR, ts.MEDIA_DIR)
        ts.STORE_DIR = self.tmp
        ts.TRANSCRIPTS_DIR = os.path.join(self.tmp, "transcripts")
        ts.STATE_DIR = os.path.join(self.tmp, "state")
        ts.MEDIA_DIR = os.path.join(self.tmp, "media")
        import story_semantics as sm
        self._emb = sm.EMB_DIR
        sm.EMB_DIR = os.path.join(self.tmp, "emb")

    def tearDown(self):
        ts.STORE_DIR, ts.TRANSCRIPTS_DIR, ts.STATE_DIR, ts.MEDIA_DIR = self._saved
        import story_semantics as sm
        sm.EMB_DIR = self._emb
        shutil.rmtree(self.tmp, ignore_errors=True)

    def meta(self, vid, channel="BTC Sessions", title="t"):
        c = REG[channel]
        m = {"schema": 1, "video_id": vid, "canonical_url": ts.canonical_url(vid),
             "channel_id": c["channel_id"], "channel_name": channel, "exact_title": title,
             "published_at": "2026-11-06T00:00:00+00:00", "duration": 600, "live_status": "not_live",
             "captions_manual": [], "captions_auto_en": ["en-orig"]}
        os.makedirs(ts._vdir(vid), exist_ok=True)
        ts._write_once(os.path.join(ts._vdir(vid), "meta.json"), m)
        return m


# ── 3. caption 429 -> Whisper ──

class TestCaption429SwitchesToWhisper(TempStore):
    def test_429_is_path_switch_and_opens_circuit(self):
        calls = []

        def fake_ytdlp(args, timeout=120):
            calls.append(args)
            return subprocess.CompletedProcess(args, 1, "", "ERROR: Unable to download video subtitles "
                                               "for 'en-orig': HTTP Error 429: Too Many Requests")
        orig = (ts._ytdlp, ts.CAPTION_BACKOFF_S, ts.download_audio)
        ts._ytdlp, ts.CAPTION_BACKOFF_S = fake_ytdlp, (0, 0, 0)
        audio = os.path.join(self.tmp, "a.m4a")

        def fake_dl(vid):
            open(audio, "wb").write(b"fake audio " + vid.encode())
            return audio
        ts.download_audio = fake_dl
        fake_tx = lambda path: ([{"start": 0.0, "end": 4.0, "text": "Congress flipped."}], "fake-whisper")
        try:
            self.meta("AAAAAAAAAAA")
            rec, st = ts.acquire("AAAAAAAAAAA", transcribe_fn=fake_tx)
            self.assertEqual(st, "whisper")
            self.assertIsNotNone(rec)
            self.assertEqual(rec["transcript_method"], "whisper")
            self.assertTrue(rec["media_sha256"])
            self.assertTrue(ts.caption_circuit_open())
            n = len(calls)
            self.meta("BBBBBBBBBBB")
            rec2, st2 = ts.acquire("BBBBBBBBBBB", transcribe_fn=fake_tx)
            self.assertEqual(st2, "whisper")
            self.assertEqual(len(calls), n, "open circuit must skip YouTube captions entirely")
            log = open(os.path.join(ts._vdir("AAAAAAAAAAA"), "attempts.jsonl")).read()
            self.assertIn('"throttled"', log)
        finally:
            ts._ytdlp, ts.CAPTION_BACKOFF_S, ts.download_audio = orig

    def test_cached_transcript_never_retranscribed(self):
        self.meta("CCCCCCCCCCC")
        rec = ts._make_record(ts.ensure_meta("CCCCCCCCCCC"), "yt_auto:en-orig", "yt",
                              [{"start": 0, "end": 3, "text": "hello there."}])
        ts._store(rec)
        boom = lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not transcribe"))
        r, st = ts.acquire("CCCCCCCCCCC", transcribe_fn=boom, caption_fn=boom)
        self.assertEqual(st, "cached")


# ── 4. provenance ──

class TestChunkProvenance(TempStore):
    def test_chunks_carry_source_identity(self):
        m = self.meta("DDDDDDDDDDD", channel="The Bitcoin Layer", title="Why Stocks Really Crashed Today")
        segs = [{"start": i * 5.0, "end": i * 5.0 + 4.8, "text": f"sentence {i}."} for i in range(40)]
        ts._store(ts._make_record(m, "whisper", "fw", segs))
        rec = ts.canonical_transcript("DDDDDDDDDDD")
        cs = ts.chunks(rec)
        self.assertGreater(len(cs), 2)
        for c in cs:
            for k in ts.PROVENANCE_FIELDS:
                self.assertIn(k, c)
            self.assertEqual(c["video_id"], "DDDDDDDDDDD")
            self.assertEqual(c["canonical_url"], "https://www.youtube.com/watch?v=DDDDDDDDDDD")
            self.assertEqual(c["channel_id"], REG["The Bitcoin Layer"]["channel_id"])
            self.assertEqual(c["exact_title"], "Why Stocks Really Crashed Today")
            self.assertEqual(c["transcript_sha256"], rec["transcript_sha256"])
            vid, a, b = ts.parse_chunk_id(c["chunk_id"])
            self.assertEqual((vid, a, b), ("DDDDDDDDDDD", round(c["start"], 3), round(c["end"], 3)))

    def test_records_are_immutable_and_tamper_evident(self):
        m = self.meta("EEEEEEEEEEE")
        rec = ts._make_record(m, "whisper", "fw", [{"start": 0, "end": 2, "text": "a b c."}])
        p = ts._store(rec)
        with self.assertRaises(FileExistsError):
            ts._store(rec)
        d = json.load(open(p))
        d["segments"][0]["text"] = "tampered."
        os.chmod(p, 0o644)
        json.dump(d, open(p, "w"))
        with self.assertRaises(ts.AcquisitionError):
            ts.canonical_transcript("EEEEEEEEEEE")


# ── 1 & 2. semantic identity (real models) ──

@unittest.skipUnless(HAVE_GPU, "needs CUDA_VISIBLE_DEVICES=0")
class TestSemanticIdentity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import story_semantics as sm
        cls.sm = sm
        cls.E = sm.Embedder()
        cls.L = sm.LocalLLM().start()
        cls.q_mid = sm.derive_story_query(cls.L, {
            "headline": "Crypto ETFs see over half a billion dollars in outflows amid post-midterm market",
            "summary": "Spot bitcoin ETFs saw outflows as markets digested the U.S. midterm election results.",
            "source_domain": "theblock.co"}, "2026-11-06")
        cls.q_block = sm.derive_story_query(cls.L, {
            "headline": "Jack Dorsey's Block (XYZ) Sets Aside $764 Million for DOJ Settlement",
            "summary": "Block disclosed a reserve for a settlement with the Department of Justice.",
            "source_domain": "coindesk.com"}, "2026-11-06")
        cls.q_bull = sm.derive_story_query(cls.L, {
            "headline": "Bull Bitcoin Becomes First Exchange to Add Payjoin Privacy Deposits",
            "summary": "Canadian exchange Bull Bitcoin added Payjoin support.",
            "source_domain": "bitcoinmagazine.com"}, "2026-11-06")

    @classmethod
    def tearDownClass(cls):
        cls.L.stop()

    def ex(self, vid, text):
        return [{"chunk_id": f"{vid}:0-30000", "text": text}]

    def test_differently_worded_transcripts_same_event(self):
        a = ("Republicans lost both chambers on Tuesday night, so Congress flips and the crypto market "
             "structure bill now depends on the new Democratic majority.")
        b = ("After the midterms the House and the Senate both went to the Democrats, and that changes "
             "the odds for any Bitcoin legislation next year.")
        va, vb = self.E.encode([a, b])
        self.assertGreater(float(va @ vb), 0.6)
        for vid, t in (("VIDA0000001", a), ("VIDB0000001", b)):
            r = self.sm.adjudicate(self.L, self.q_mid, {"title": "x", "channel": "x"}, self.ex(vid, t))
            self.assertTrue(r["counted_as_same_event"], r)

    def test_loose_word_collisions_do_not_create_identity(self):
        fire = ("Fireblocks CEO Michael Shaulov talks about the open transaction layer and how custody "
                "infrastructure is evolving for institutions.")
        self.assertFalse(any(p.search(fire) for p in self.sm.alias_patterns(self.q_block)))
        r = self.sm.adjudicate(self.L, self.q_block, {"title": "Fireblocks CEO", "channel": "CoinDesk"},
                               self.ex("VIDC0000001", fire))
        self.assertFalse(r["counted_as_same_event"], r)
        bull = ("Is the AI boom keeping Bitcoin from its next bull run? Capital is flowing to AI stocks "
                "instead of bitcoin, and that is why the bull market stalled.")
        r = self.sm.adjudicate(self.L, self.q_bull, {"title": "AI boom vs bull run", "channel": "CoinDesk"},
                               self.ex("VIDD0000001", bull))
        self.assertFalse(r["counted_as_same_event"], r)

    def test_hallucinated_quote_is_not_counted(self):
        r = self.sm.adjudicate(self.L, self.q_mid, {"title": "x", "channel": "x"},
                               self.ex("VIDE0000001", "Gold rallied as the dollar weakened today."))
        self.assertFalse(r["counted_as_same_event"])


# ── 5. layout gate ──

def _words_record(meta, sentences):
    words, t = [], 1.0
    for s in sentences:
        for w in s.split():
            words.append({"word": w, "start": round(t, 3), "end": round(t + 0.28, 3)})
            t += 0.31
        t += 0.4
    rec = ts._make_record(meta, "whisper_words", "fake words", ts.sentences_from_words(words),
                          extra={"words": words})
    ts._store(rec)


MID_A = [
    "The midterm results are in and Democrats now control both the House and the Senate.",
    "That flip means the crypto market structure bill that passed the House last summer is effectively dead in this Congress and will have to start again next year.",
    "For Bitcoin specifically the bigger question is whether the strategic reserve executive order survives oversight hearings from a hostile committee chair.",
    "Markets reacted immediately with spot Bitcoin ETFs seeing heavy outflows the morning after the vote.",
] * 3
MID_B = [
    "Tuesday's election handed Democrats the House and the Senate, and crypto policy is now in limbo.",
    "Lobbyists spent more than two hundred million dollars on these midterms and most of the candidates they backed lost their races on election night.",
    "The practical effect for Bitcoin holders is that tax reporting rules and stablecoin legislation get rewritten by a very different committee next year.",
    "I think the market is overreacting, because none of this changes the supply schedule or the fundamental demand for Bitcoin.",
] * 3
MID_C = [
    "On our show today the midterm elections flipped Congress to the Democrats and that is a big deal for Bitcoin policy.",
    "Several pro-crypto senators lost their seats on election night, which changes who chairs the banking committee next year.",
] * 4
OFF = ["Today we review three hardware wallets and compare their screens, batteries and price."] * 8


@unittest.skipUnless(HAVE_GPU, "needs CUDA_VISIBLE_DEVICES=0")
class TestLayoutGate(TempStore):
    def test_pending_source_can_become_a_clip_via_letterbox_policy(self):
        import editorial_select as es
        appr_a, appr_b, pending = "The Bitcoin Layer", "Bitcoin Magazine", "What Bitcoin Did"
        self.assertEqual(REG[appr_a]["layout_status"], "approved")
        self.assertEqual(REG[appr_b]["layout_status"], "approved")
        self.assertNotEqual(REG[pending]["layout_status"], "approved")
        vids = {"MIDAAAAAAA1": (appr_a, MID_A), "MIDBBBBBBB1": (appr_b, MID_B),
                "MIDCCCCCCC1": (pending, MID_C), "OFFDDDDDDD1": (appr_a, OFF)}
        uni = []
        for vid, (ch, sents) in vids.items():
            _words_record(self.meta(vid, channel=ch, title=f"{ch} show"), sents)
            uni.append({"video_id": vid, "rss": {"title": f"{ch} show",
                        "published": "2026-11-06T00:00:00+00:00"}, "channel": REG[ch], "age_h": 6.0})
        stories = {"generated_at": "2026-11-06T00:00:00Z", "stories": [
            {"rank": 1, "overall_score": 55, "headline": "Democrats win both chambers in US midterms, "
             "putting crypto legislation and Bitcoin policy in doubt", "summary": "The 2026 midterm "
             "elections flipped the House and Senate.", "source_domain": "politico.com",
             "freshness_minutes": 300, "independent_corroboration": 1, "unexpectedness": 2, "tension": 2}]}
        sp = os.path.join(self.tmp, "stories.json")
        json.dump(stories, open(sp, "w"))
        run_dir = os.path.join(self.tmp, "run")
        os.makedirs(run_dir)
        label, rec = es.select_story(run_dir, log=lambda s: None, universe_fn=lambda h: uni,
                                     stories_path=sp, topup=False)
        sel = json.load(open(os.path.join(run_dir, "TOPIC_SELECTION.json")))
        cand = [c for c in sel["candidates"] if c.get("decision") == "producible"][0]
        counted = {v["channel"] for v in cand["coverage"]["verdicts"] if v["counted_as_same_event"]}
        self.assertIn(pending, counted, "pending channel must contribute editorial evidence")
        chosen = json.load(open(os.path.join(run_dir, "passages.json")))["chosen"]
        self.assertTrue(chosen)
        self.assertTrue({p["channel"] for p in chosen} <= {appr_a, appr_b, pending})
        self.assertNotIn("OFFDDDDDDD1", {p["video_id"] for p in chosen})
        for p in chosen:
            self.assertTrue(p["canonical_url"].endswith(p["video_id"]))
            self.assertTrue(p["source_chunk_id"].startswith(p["video_id"] + ":"))


if __name__ == "__main__":
    unittest.main()
