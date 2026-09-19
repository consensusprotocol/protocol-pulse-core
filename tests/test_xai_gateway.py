#!/usr/bin/env python3
"""Unit tests for core/services/xai_gateway.py"""

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Load gateway by path to avoid import issues
BASE = Path(__file__).resolve().parent.parent
GW_PATH = BASE / "core" / "services" / "xai_gateway.py"
spec = importlib.util.spec_from_file_location("xai_gateway", str(GW_PATH))
gw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gw)


class TestBudgetCounters(unittest.TestCase):
    """Test budget tracking, daily reset, and limit enforcement."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.budget_path = Path(self.tmpdir) / "xai_budget.json"
        self.config_path = Path(self.tmpdir) / "xai_budget_config.json"
        self.alert_path = Path(self.tmpdir) / "xai_budget_alert.json"
        # Write test config
        self.config_path.write_text(json.dumps({
            "max_requests_per_day": 5,
            "max_search_calls_per_day": 2,
            "max_usd_per_day": 0.10,
            "enabled": True,
        }))
        # Patch paths
        self._patches = [
            patch.object(gw, 'BUDGET_PATH', self.budget_path),
            patch.object(gw, 'CONFIG_PATH', self.config_path),
            patch.object(gw, 'ALERT_PATH', self.alert_path),
            patch.object(gw, 'DATA_DIR', Path(self.tmpdir)),
            patch.object(gw, '_tg_sent_today', None),
        ]
        for p in self._patches:
            p.start()

    def tearDown(self):
        for p in self._patches:
            p.stop()
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_budget_starts_at_zero(self):
        budget = gw._load_budget()
        self.assertEqual(budget["requests"], 0)
        self.assertEqual(budget["search_calls"], 0)
        self.assertAlmostEqual(budget["est_usd"], 0.0)

    def test_daily_reset(self):
        # Write a budget from yesterday
        old = {
            "date": "2020-01-01",
            "requests": 999,
            "search_calls": 999,
            "est_usd": 99.99,
            "blocked_requests": 50,
            "errors_402": 10,
            "errors_429": 5,
        }
        self.budget_path.write_text(json.dumps(old))
        budget = gw._load_budget()
        # Should reset because date doesn't match today
        self.assertEqual(budget["requests"], 0)
        self.assertEqual(budget["search_calls"], 0)

    def test_request_limit_blocks(self):
        # Pre-fill budget to max
        budget = gw._load_budget()
        budget["requests"] = 5  # at limit
        gw._save_budget(budget)

        result = gw.chat(
            [{"role": "user", "content": "test"}],
            dry_run=True,
        )
        self.assertIsInstance(result, gw.BudgetExceeded)
        self.assertIn("max_requests_per_day", result.reason)

    def test_search_limit_blocks(self):
        budget = gw._load_budget()
        budget["search_calls"] = 2  # at limit
        gw._save_budget(budget)

        result = gw.chat(
            [{"role": "user", "content": "test"}],
            allow_search=True,
            search_tools=[{"type": "x_search"}],
            dry_run=True,
        )
        self.assertIsInstance(result, gw.BudgetExceeded)
        self.assertIn("max_search_calls_per_day", result.reason)

    def test_usd_limit_blocks(self):
        budget = gw._load_budget()
        budget["est_usd"] = 0.10  # at limit
        gw._save_budget(budget)

        result = gw.chat(
            [{"role": "user", "content": "test"}],
            dry_run=True,
        )
        self.assertIsInstance(result, gw.BudgetExceeded)
        self.assertIn("max_usd_per_day", result.reason)

    def test_dry_run_increments_counters(self):
        result = gw.chat(
            [{"role": "user", "content": "test"}],
            dry_run=True,
        )
        self.assertIsInstance(result, str)
        self.assertIn("DRY_RUN", result)

        budget = gw._load_budget()
        self.assertEqual(budget["requests"], 1)
        self.assertGreater(budget["est_usd"], 0)

    def test_search_gating_no_search_by_default(self):
        """Without allow_search=True, search tools should not be attached."""
        result = gw.chat(
            [{"role": "user", "content": "test"}],
            search_tools=[{"type": "web_search"}],  # passed but allow_search is False
            dry_run=True,
        )
        self.assertIsInstance(result, str)
        self.assertIn("search=0", result)

    def test_search_gating_with_allow(self):
        result = gw.chat(
            [{"role": "user", "content": "test"}],
            allow_search=True,
            search_tools=[{"type": "x_search"}],
            dry_run=True,
        )
        self.assertIsInstance(result, str)
        self.assertIn("search=1", result)

        budget = gw._load_budget()
        self.assertEqual(budget["search_calls"], 1)


class TestBudgetExceeded(unittest.TestCase):
    """Test BudgetExceeded result object behavior."""

    def test_falsy(self):
        be = gw.BudgetExceeded("test", {})
        self.assertFalse(bool(be))

    def test_has_reason(self):
        be = gw.BudgetExceeded("max_requests_per_day exceeded", {"requests": 400})
        self.assertEqual(be.reason, "max_requests_per_day exceeded")


class TestCostEstimation(unittest.TestCase):
    """Test token cost estimation."""

    def test_grok3_cost(self):
        cost = gw._estimate_cost("grok-3", 1000000, 0, 0)
        self.assertAlmostEqual(cost, 3.00, places=2)

    def test_grok3_output_cost(self):
        cost = gw._estimate_cost("grok-3", 0, 1000000, 0)
        self.assertAlmostEqual(cost, 15.00, places=2)

    def test_search_cost(self):
        cost = gw._estimate_cost("grok-3-mini-fast", 0, 0, 10)
        self.assertAlmostEqual(cost, 0.05, places=2)

    def test_unknown_model_uses_grok3(self):
        cost = gw._estimate_cost("grok-99", 1000000, 0, 0)
        self.assertAlmostEqual(cost, 3.00, places=2)


class TestStatus(unittest.TestCase):
    """Test status() for watchdog consumption."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self._patches = [
            patch.object(gw, 'BUDGET_PATH', Path(self.tmpdir) / "budget.json"),
            patch.object(gw, 'CONFIG_PATH', Path(self.tmpdir) / "config.json"),
            patch.object(gw, 'DATA_DIR', Path(self.tmpdir)),
        ]
        for p in self._patches:
            p.start()

    def tearDown(self):
        for p in self._patches:
            p.stop()
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_status_fields(self):
        s = gw.status()
        required_fields = [
            "date", "requests", "max_requests", "search_calls",
            "max_search_calls", "est_usd", "max_usd", "blocked",
            "enabled", "pct_requests", "pct_usd",
        ]
        for f in required_fields:
            self.assertIn(f, s, f"Missing field: {f}")


class TestResponsesEndpoint(unittest.TestCase):
    """Test the /v1/responses path."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self._patches = [
            patch.object(gw, 'BUDGET_PATH', Path(self.tmpdir) / "budget.json"),
            patch.object(gw, 'CONFIG_PATH', Path(self.tmpdir) / "config.json"),
            patch.object(gw, 'ALERT_PATH', Path(self.tmpdir) / "alert.json"),
            patch.object(gw, 'DATA_DIR', Path(self.tmpdir)),
            patch.object(gw, '_tg_sent_today', None),
        ]
        (Path(self.tmpdir) / "config.json").write_text(json.dumps({
            "max_requests_per_day": 10,
            "max_search_calls_per_day": 5,
            "max_usd_per_day": 1.00,
            "enabled": True,
        }))
        for p in self._patches:
            p.start()

    def tearDown(self):
        for p in self._patches:
            p.stop()
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_dry_run_responses(self):
        result = gw.responses("test prompt", dry_run=True)
        self.assertIsInstance(result, tuple)
        self.assertIn("DRY_RUN", result[0])


class TestDegradedFallback(unittest.TestCase):
    """Test that callers can check isinstance(result, BudgetExceeded)."""

    def test_isinstance_check(self):
        be = gw.BudgetExceeded("test", {})
        # Callers should be able to do:
        if isinstance(be, gw.BudgetExceeded):
            fallback = "used_cached_data"
        else:
            fallback = None
        self.assertEqual(fallback, "used_cached_data")

    def test_none_is_not_budget_exceeded(self):
        self.assertNotIsInstance(None, gw.BudgetExceeded)

    def test_string_is_not_budget_exceeded(self):
        self.assertNotIsInstance("response text", gw.BudgetExceeded)


if __name__ == "__main__":
    unittest.main()
