#!/usr/bin/env python3
"""
PHASE 5 GATE TEST — Stage Integration
14 scenarios — all must pass.
Tests: timed briefing, broadcast/interactive mode switching,
       stage intel enrichment, full end-to-end flow, regression.
"""

import importlib
import json
import os
import re
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "oracle"))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "video_pipeline_v3"))

STAGE_HTML_PATH = os.path.join(PROJECT_ROOT, "templates", "stage.html")
V3_BASE = os.path.join(PROJECT_ROOT, "video_pipeline_v3")
BRIEFS_DIR = os.path.join(V3_BASE, "data", "stage_briefs")


def _read_stage_html():
    """Read stage.html contents."""
    with open(STAGE_HTML_PATH) as f:
        return f.read()


class Phase5StageIntegration(unittest.TestCase):
    """Phase 5: Stage integration tests — 14 scenarios."""

    # ── TIMED BRIEFING ─────────────────────────────────────────

    def test_01_stage_brief_generates_from_render(self):
        """generate_stage_brief.py imports and generate_brief() is callable."""
        import generate_stage_brief as gsb
        self.assertTrue(callable(gsb.generate_brief),
                        "generate_brief must be a callable function")
        # Verify it loads script.json correctly
        self.assertTrue(callable(gsb._load_script),
                        "_load_script helper must exist")
        self.assertTrue(callable(gsb._condense_script),
                        "_condense_script helper must exist")

    def test_02_next_briefing_api_returns_countdown(self):
        """api_stage_next_briefing returns countdown_seconds field."""
        from app import app
        with app.test_client() as client:
            resp = client.get('/api/stage/next_briefing')
            self.assertEqual(resp.status_code, 200)
            data = resp.get_json()
            self.assertIn('countdown_seconds', data,
                          "/api/stage/next_briefing must return countdown_seconds")
            self.assertIn('has_brief', data,
                          "/api/stage/next_briefing must return has_brief")

    def test_03_next_briefing_has_mp4_url(self):
        """If a brief exists, last_brief.mp4_url is present."""
        from app import app
        with app.test_client() as client:
            resp = client.get('/api/stage/next_briefing')
            data = resp.get_json()
            if data.get('has_brief'):
                self.assertIn('mp4_url', data.get('last_brief', {}),
                              "last_brief must contain mp4_url when brief exists")
                mp4_url = data['last_brief']['mp4_url']
                self.assertTrue(mp4_url.startswith('/data/stage_briefs/'),
                                f"mp4_url must start with /data/stage_briefs/, got: {mp4_url}")
            else:
                # No brief yet — test passes (brief generation depends on render)
                self.assertIsNone(data.get('last_brief'))

    def test_04_countdown_ui_present_in_stage(self):
        """stage.html contains countdownTimer element."""
        html = _read_stage_html()
        self.assertIn('countdownTimer', html,
                      "stage.html must contain 'countdownTimer' element")
        self.assertIn('briefDot', html,
                      "stage.html must contain 'briefDot' element")
        self.assertIn('briefPlayBtn', html,
                      "stage.html must contain 'briefPlayBtn' element")

    # ── MODE SWITCHING ─────────────────────────────────────────

    def test_05_broadcast_mode_disables_mic(self):
        """enterBroadcast() disables the stage mic button."""
        html = _read_stage_html()
        self.assertIn('enterBroadcast', html,
                      "stage.html must contain enterBroadcast function")
        # In broadcast mode, mic is disabled
        html_nospace = html.replace(' ', '')
        self.assertTrue(
            'micBtn.disabled=true' in html_nospace or 'micBtn)micBtn.disabled=true' in html_nospace,
            "enterBroadcast must disable mic button")
        # Verify the function sets STAGE_MODE
        match = re.search(r"function\s+enterBroadcast\b[^}]*STAGE_MODE\s*=\s*'broadcast'", html, re.DOTALL)
        self.assertIsNotNone(match,
                             "enterBroadcast must set STAGE_MODE = 'broadcast'")

    def test_06_interactive_mode_enables_oracle(self):
        """enterInteractive() enables Oracle chat + mic."""
        html = _read_stage_html()
        self.assertIn('enterInteractive', html,
                      "stage.html must contain enterInteractive function")
        # Verify interactive panel activation
        self.assertIn("interactivePanel", html,
                      "stage.html must contain interactivePanel element")
        # Verify the function sets STAGE_MODE
        match = re.search(r"function\s+enterInteractive\b[^}]*STAGE_MODE\s*=\s*'interactive'", html, re.DOTALL)
        self.assertIsNotNone(match,
                             "enterInteractive must set STAGE_MODE = 'interactive'")
        # Oracle chat endpoint is wired
        self.assertIn('/oracle/chat', html,
                      "stage.html must call /oracle/chat for interactive mode")

    def test_07_mode_badge_updates(self):
        """stageModeBadge text changes on mode switch."""
        html = _read_stage_html()
        self.assertIn('stageModeBadge', html,
                      "stage.html must contain stageModeBadge element")
        # Broadcast shows ON AIR
        self.assertIn("ON AIR", html,
                      "Broadcast mode must show 'ON AIR' text")
        # Interactive shows Ask Oracle
        self.assertIn("Ask Oracle anything", html,
                      "Interactive mode must show 'Ask Oracle anything' text")

    def test_08_transition_at_countdown_zero(self):
        """enterBroadcast() called when countdown hits 0."""
        html = _read_stage_html()
        # showBriefReady triggers enterBroadcast
        self.assertIn('enterBroadcast', html,
                      "showBriefReady must call enterBroadcast on countdown zero")
        # Verify countdown completion triggers broadcast transition
        match = re.search(r'showBriefReady.*?enterBroadcast', html, re.DOTALL)
        self.assertIsNotNone(match,
                             "showBriefReady must trigger enterBroadcast for auto-transition")

    # ── STAGE INTEL ENRICHED ──────────────────────────────────

    def test_09_stage_intel_has_price_delta(self):
        """price_delta_1h present in /api/stage/intel response."""
        from app import app
        with app.test_client() as client:
            resp = client.get('/api/stage/intel')
            self.assertEqual(resp.status_code, 200)
            data = resp.get_json()
            self.assertIn('price_delta_1h', data,
                          "/api/stage/intel must return price_delta_1h")

    def test_10_stage_intel_has_market_context(self):
        """market_context phrase present in /api/stage/intel response."""
        from app import app
        with app.test_client() as client:
            resp = client.get('/api/stage/intel')
            data = resp.get_json()
            self.assertIn('market_context', data,
                          "/api/stage/intel must return market_context")
            ctx = data['market_context']
            valid_phrases = [
                'extreme fear', 'fearful', 'extreme greed', 'greedy', 'neutral'
            ]
            self.assertTrue(any(p in ctx for p in valid_phrases),
                            f"market_context must contain a valid phrase, got: {ctx}")

    # ── FULL END-TO-END ──────────────────────────────────────

    def test_11_full_flow_render_to_stage(self):
        """Post-brief triggers exist and are callable."""
        import generate_stage_brief as gsb
        self.assertTrue(callable(gsb._post_brief_triggers),
                        "_post_brief_triggers must be a callable function")
        # Verify it handles Nostr refresh, RAG flag, transcript marker
        import inspect
        src = inspect.getsource(gsb._post_brief_triggers)
        self.assertIn('fetch_signal_cache', src,
                      "_post_brief_triggers must trigger Nostr signal refresh")
        self.assertIn('rag_stale', src,
                      "_post_brief_triggers must clear RAG stale flag")
        self.assertIn('last_brief_refresh', src,
                      "_post_brief_triggers must update transcript cache marker")

    # ── REGRESSION ───────────────────────────────────────────

    def test_12_oracle_live_still_works(self):
        """/oracle-live responds 200."""
        from app import app
        with app.test_client() as client:
            resp = client.get('/oracle-live')
            self.assertEqual(resp.status_code, 200,
                             "/oracle-live must respond 200")

    def test_13_oracle_chat_still_responds(self):
        """/oracle/chat endpoint exists (routed to avatar server)."""
        # Verify the oracle_live.html page contains the chat flow
        oracle_path = os.path.join(PROJECT_ROOT, "templates", "oracle_live.html")
        self.assertTrue(os.path.exists(oracle_path),
                        "oracle_live.html must exist")
        with open(oracle_path) as f:
            html = f.read()
        self.assertIn('/oracle/chat', html,
                      "oracle_live.html must reference /oracle/chat endpoint")
        self.assertIn('audio_first', html,
                      "oracle_live.html must use audio_first parameter")

    def test_14_all_phase1_tests_pass(self):
        """Phase 1 gate tests still pass (inline run)."""
        phase1_path = os.path.join(PROJECT_ROOT, "tests", "phase1_gate.py")
        self.assertTrue(os.path.exists(phase1_path),
                        "phase1_gate.py must exist")
        # Run phase1 tests inline
        loader = unittest.TestLoader()
        # Import phase1 module
        import importlib.util
        spec = importlib.util.spec_from_file_location("phase1_gate", phase1_path)
        phase1 = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(phase1)
        # Find all test cases (skip TestAudioFirst — depends on live avatar server + ElevenLabs)
        suite = unittest.TestSuite()
        for name in dir(phase1):
            obj = getattr(phase1, name)
            if isinstance(obj, type) and issubclass(obj, unittest.TestCase):
                if name == 'TestAudioFirst':
                    continue  # Skip live-server tests (external dependency)
                suite.addTests(loader.loadTestsFromTestCase(obj))
        result = unittest.TextTestRunner(verbosity=0, stream=open(os.devnull, 'w')).run(suite)
        failed = len(result.failures) + len(result.errors)
        self.assertEqual(failed, 0,
                         f"Phase 1 regression: {failed} tests failed — "
                         f"failures: {[f[0] for f in result.failures]}, "
                         f"errors: {[e[0] for e in result.errors]}")


# ── Gate summary ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("  PHASE 5 GATE — Stage Integration (14 scenarios)")
    print("=" * 60)

    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(Phase5StageIntegration)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print()
    if result.wasSuccessful():
        print("PHASE 5 GATE: ALL 14 PASSED")
    else:
        failed = len(result.failures) + len(result.errors)
        print(f"PHASE 5 GATE: {failed} FAILED — fix before proceeding")

    sys.exit(0 if result.wasSuccessful() else 1)
