#!/usr/bin/env python3
"""
PHASE 2 GATE TEST — Oracle Intelligence Depth
20 technical edge-case questions — 18/20 must be answered correctly.
Tests: RAG retrieval, confidence calibration, live intel injection.
"""

import os
import sys
import json
import unittest
import time

# Ensure project root is on path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "oracle"))


# ── Test 1: RAG retrieval accuracy ───────────────────────────────────────

EDGE_CASES = [
    ("What's the difference between Coldcard Q and Mk4?",
     ["q", "mk4", "nfc", "qr", "air-gap", "qwerty", "keyboard", "screen"]),
    ("My Sparrow shows unconfirmed — is it stuck?",
     ["mempool", "rbf", "cpfp", "fee", "stuck", "unconfirmed", "sat"]),
    ("Can I use my Coldcard with BlueWallet on iPhone?",
     ["psbt", "watch-only", "sign", "air-gap", "qr", "bluewallet"]),
    ("What is a UTXO and why does it matter for privacy?",
     ["unspent", "output", "coin control", "privacy", "trace", "utxo"]),
    ("What's the difference between SegWit and Taproot?",
     ["segwit", "taproot", "schnorr", "signature", "fee", "bc1q", "bc1p"]),
    ("How do I set up inbound liquidity on Lightning?",
     ["inbound", "channel", "capacity", "open", "peer", "liquidity", "lightning"]),
    ("What is a passphrase and is it the same as my PIN?",
     ["passphrase", "pin", "different", "25th word", "seed", "wallet", "separate"]),
    ("How do I verify my Coldcard received my Bitcoin?",
     ["mempool", "address", "verify", "node", "explorer", "sparrow"]),
    ("What is coin control and when should I use it?",
     ["utxo", "coin control", "privacy", "change", "sparrow", "freeze"]),
    ("Is it safe to use a hardware wallet with a passphrase and multisig?",
     ["multisig", "passphrase", "backup", "seed", "quorum", "key"]),
    ("What is RBF and CPFP and when do I use each?",
     ["replace", "fee", "stuck", "bump", "parent", "child", "rbf", "cpfp"]),
    ("How do I connect Sparrow to my Umbrel node?",
     ["sparrow", "server", "umbrel", "electr", "50001", "bitcoin core", "ip"]),
    ("What's the difference between a hot wallet and cold wallet?",
     ["online", "offline", "keys", "connected", "air", "hardware", "cold"]),
    ("How do I set up BTCPay Server for my business?",
     ["btcpay", "invoice", "node", "merchant", "lightning", "umbrel", "payment"]),
    ("What is the mempool and how do I check if my transaction is stuck?",
     ["mempool", "unconfirmed", "fee", "explorer", "sat", "vbyte", "waiting"]),
    ("What is xpub and should I share it with anyone?",
     ["xpub", "watch-only", "privacy", "public", "never", "address", "balance"]),
    ("How do I do a coinjoin for privacy?",
     ["coinjoin", "wasabi", "joinmarket", "utxo", "privacy", "mix"]),
    ("What's the best way to DCA without KYC?",
     ["peer", "kyc", "bisq", "robosats", "privacy", "p2p", "decentralized"]),
    ("How does Lightning routing work?",
     ["route", "hop", "channel", "fee", "path", "payment", "forward"]),
    ("What is a watch-only wallet?",
     ["xpub", "receive", "watch", "no keys", "monitor", "balance", "address"]),
]


class TestRAGRetrieval(unittest.TestCase):
    """RAG must return relevant chunks for each edge case question."""

    @classmethod
    def setUpClass(cls):
        from oracle_rag import retrieve, build_index, _chunks
        if not _chunks:
            build_index()
        cls.retrieve = staticmethod(retrieve)

    def _check_rag(self, query, expected_keywords, idx):
        results = self.retrieve(query, top_k=3)
        self.assertTrue(len(results) > 0, f"Q{idx}: No RAG results for: {query}")
        combined = " ".join(r["text"].lower() for r in results)
        hits = sum(1 for kw in expected_keywords if kw.lower() in combined)
        self.assertGreaterEqual(
            hits, 2,
            f"Q{idx}: Only {hits} keyword hits for '{query}'. "
            f"Expected >=2 from {expected_keywords}"
        )


def _make_rag_test(idx, query, keywords):
    def test(self):
        self._check_rag(query, keywords, idx)
    test.__doc__ = f"Q{idx+1}: {query[:50]}"
    return test


# Dynamically generate 20 test methods
for _i, (_q, _kw) in enumerate(EDGE_CASES):
    setattr(TestRAGRetrieval, f"test_rag_q{_i+1:02d}", _make_rag_test(_i, _q, _kw))


# ── Test 2: Confidence calibration in system prompt ──────────────────────

class TestConfidenceCalibration(unittest.TestCase):
    """System prompt must contain confidence calibration rules."""

    def test_calibration_in_prompt(self):
        """System prompt has CONFIDENCE CALIBRATION section."""
        from oracle_dialogue_engine import _SYSTEM_PROMPT
        self.assertIn("CONFIDENCE CALIBRATION", _SYSTEM_PROMPT)

    def test_price_prediction_decline(self):
        """System prompt tells Oracle to decline price predictions."""
        from oracle_dialogue_engine import _SYSTEM_PROMPT
        self.assertIn("don't predict prices", _SYSTEM_PROMPT.lower())

    def test_not_certain_phrase(self):
        """System prompt includes 'not certain' hedge for unknowns."""
        from oracle_dialogue_engine import _SYSTEM_PROMPT
        self.assertIn("not certain", _SYSTEM_PROMPT.lower())

    def test_tax_disclaimer(self):
        """System prompt has tax/legal disclaimer."""
        from oracle_dialogue_engine import _SYSTEM_PROMPT
        self.assertIn("tax advisor", _SYSTEM_PROMPT.lower())


# ── Test 3: Enhanced get_live_intel ──────────────────────────────────────

class TestLiveIntel(unittest.TestCase):
    """get_live_intel() must return price delta and market context fields."""

    @classmethod
    def setUpClass(cls):
        from oracle_dialogue_engine import get_live_intel
        cls.intel = get_live_intel()

    def test_price_float_present(self):
        """Live intel returns a price_float."""
        # May fail if API is down, so skip gracefully
        if "price_float" not in self.intel:
            self.skipTest("Coinbase API unavailable")
        self.assertIsInstance(self.intel["price_float"], float)

    def test_market_context_present(self):
        """Live intel includes market_context phrase."""
        self.assertIn("market_context", self.intel)
        self.assertIn("market", self.intel["market_context"])

    def test_market_context_valid_phrases(self):
        """Market context is one of the expected phrases."""
        valid = ["extreme fear", "fearful", "extreme greed", "greedy", "neutral"]
        ctx = self.intel.get("market_context", "")
        self.assertTrue(any(v in ctx for v in valid), f"Unexpected market_context: {ctx}")


# ── Test 4: RAG injection into generate_response context ─────────────────

class TestRAGInjection(unittest.TestCase):
    """generate_response must include RAG context in the prompt."""

    def test_rag_import_in_engine(self):
        """oracle_dialogue_engine.py imports oracle_rag.retrieve."""
        import inspect
        from oracle_dialogue_engine import generate_response
        source = inspect.getsource(generate_response)
        self.assertIn("oracle_rag", source)
        self.assertIn("retrieve", source)
        self.assertIn("RELEVANT KNOWLEDGE", source)

    def test_price_delta_injection(self):
        """generate_response context builder references price_delta_spoken."""
        import inspect
        from oracle_dialogue_engine import generate_response
        source = inspect.getsource(generate_response)
        self.assertIn("price_delta_spoken", source)

    def test_top_signal_injection(self):
        """generate_response context builder references top_signal."""
        import inspect
        from oracle_dialogue_engine import generate_response
        source = inspect.getsource(generate_response)
        self.assertIn("top_signal", source)


# ── Test 5: Knowledge base files exist ───────────────────────────────────

class TestKnowledgeBase(unittest.TestCase):
    """Knowledge base directory and files must exist."""

    KB_DIR = os.path.join(PROJECT_ROOT, "oracle", "knowledge_base")

    def test_kb_dir_exists(self):
        """oracle/knowledge_base/ directory exists."""
        self.assertTrue(os.path.isdir(self.KB_DIR))

    def test_bitcoin_faq_exists(self):
        """bitcoin_faq.json exists and has chunks."""
        path = os.path.join(self.KB_DIR, "bitcoin_faq.json")
        self.assertTrue(os.path.exists(path))
        data = json.load(open(path))
        self.assertGreater(len(data.get("chunks", [])), 10)

    def test_hardware_docs_exists(self):
        """hardware_docs.json exists and has chunks."""
        path = os.path.join(self.KB_DIR, "hardware_docs.json")
        self.assertTrue(os.path.exists(path))
        data = json.load(open(path))
        self.assertGreater(len(data.get("chunks", [])), 5)

    def test_chunk_format(self):
        """Each chunk has title, source, and text fields."""
        for fname in ["bitcoin_faq.json", "hardware_docs.json"]:
            path = os.path.join(self.KB_DIR, fname)
            data = json.load(open(path))
            for chunk in data.get("chunks", []):
                self.assertIn("title", chunk, f"Missing title in {fname}")
                self.assertIn("source", chunk, f"Missing source in {fname}")
                self.assertIn("text", chunk, f"Missing text in {fname}")
                self.assertGreater(len(chunk["text"]), 50, f"Chunk too short in {fname}")


# ── Phase 1 regression ──────────────────────────────────────────────────

class TestPhase1Regression(unittest.TestCase):
    """Phase 1 features must still work."""

    def test_phoneme_map_has_phase1_entries(self):
        """Phase 1 pronunciation entries still present."""
        from oracle_dialogue_engine import PHONEME_MAP
        # Check a few Phase 1 additions
        phase1_keys = [r'\bUTXO\b', r'\bPSBT\b', r'\bSegWit\b', r'\bCPFP\b', r'\bRBF\b']
        for k in phase1_keys:
            self.assertIn(k, PHONEME_MAP, f"Missing Phase 1 phoneme: {k}")

    def test_word_cap_still_32(self):
        """MAX_RESPONSE_WORDS is still 32."""
        from oracle_dialogue_engine import MAX_RESPONSE_WORDS
        self.assertEqual(MAX_RESPONSE_WORDS, 32)

    def test_setup_flows_intact(self):
        """All device setup flows still exist."""
        from oracle_dialogue_engine import _SETUP_STEPS
        for device in ["coldcard", "trezor", "ledger", "umbrel", "bitcoincore", "bitaxe"]:
            self.assertIn(device, _SETUP_STEPS, f"Missing setup flow: {device}")


if __name__ == "__main__":
    print("=" * 60)
    print("PHASE 2 GATE TEST — Oracle Intelligence Depth")
    print("=" * 60)
    unittest.main(verbosity=2)
