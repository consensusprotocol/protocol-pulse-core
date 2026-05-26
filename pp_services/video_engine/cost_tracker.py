"""
COST OPTIMIZATION + BUDGET TRACKING
=====================================
Track every API call's cost, implement token budgets per stage,
cost-per-episode tracking, and budget overrun alerts.

Usage:
    from pp_services.video_engine.cost_tracker import CostTracker, CostDashboard
    tracker = CostTracker()
    tracker.record("grok_triage", provider="xai", tokens_in=5000, tokens_out=2000)
    tracker.check_budget("grok_triage")
    dashboard = CostDashboard()
    dashboard.get_episode_cost("2026-02-25")
"""

import os
import json
import sqlite3
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger("CostTracker")

DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "video_engine" / "cost_tracking.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# ─── Pricing Models (per 1K tokens or per unit) ───
PRICING = {
    "xai": {
        "name": "xAI / Grok",
        "input_per_1k": 0.005,
        "output_per_1k": 0.015,
    },
    "anthropic": {
        "name": "Anthropic / Claude",
        "models": {
            "claude-sonnet-4-20250514": {"input_per_1k": 0.003, "output_per_1k": 0.015},
            "claude-opus-4-6": {"input_per_1k": 0.015, "output_per_1k": 0.075},
            "claude-haiku-4-5-20251001": {"input_per_1k": 0.001, "output_per_1k": 0.005},
        },
        "default": {"input_per_1k": 0.003, "output_per_1k": 0.015},
    },
    "openai": {
        "name": "OpenAI",
        "models": {
            "gpt-4o": {"input_per_1k": 0.005, "output_per_1k": 0.015},
            "gpt-4o-mini": {"input_per_1k": 0.00015, "output_per_1k": 0.0006},
        },
        "default": {"input_per_1k": 0.005, "output_per_1k": 0.015},
    },
    "gemini": {
        "name": "Google Gemini",
        "input_per_1k": 0.00035,
        "output_per_1k": 0.001,
    },
    "elevenlabs": {
        "name": "ElevenLabs",
        "per_character": 0.00003,   # ~$30 per 1M characters
    },
    "whisper": {
        "name": "Whisper (local GPU)",
        "per_minute": 0.0,          # Free on local GPU
    },
    "assemblyai": {
        "name": "AssemblyAI",
        "per_minute": 0.00025,      # ~$0.25 per hour
    },
}

# Stage budgets (max cost per single run)
STAGE_BUDGETS = {
    "source_ingestion": 0.50,    # Transcription costs
    "grok_triage": 2.00,         # xAI tokens
    "clustering": 0.10,          # Local computation
    "claude_director": 3.00,     # Claude tokens
    "qa_review": 1.00,           # Review tokens
    "narration": 5.00,           # ElevenLabs voice
    "assembly": 0.50,            # GPU time
    "distribution_pack": 0.50,   # Formatting
    "article_generation": 1.00,  # Per article
    "x_engagement": 0.50,        # Tweet generation
    "council": 5.00,             # Multi-model consensus
}


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_cost_db():
    """Initialize cost tracking database."""
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS api_calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            episode_date TEXT,
            stage TEXT NOT NULL,
            provider TEXT NOT NULL,
            model TEXT,
            tokens_in INTEGER DEFAULT 0,
            tokens_out INTEGER DEFAULT 0,
            characters INTEGER DEFAULT 0,
            minutes REAL DEFAULT 0,
            cost_usd REAL NOT NULL DEFAULT 0,
            metadata TEXT DEFAULT '{}',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS episode_costs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL UNIQUE,
            total_cost REAL DEFAULT 0,
            cost_breakdown TEXT DEFAULT '{}',
            stages_completed INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT
        );

        CREATE TABLE IF NOT EXISTS budget_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stage TEXT NOT NULL,
            budget_limit REAL NOT NULL,
            actual_cost REAL NOT NULL,
            overage_pct REAL NOT NULL,
            episode_date TEXT,
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_calls_date ON api_calls(episode_date);
        CREATE INDEX IF NOT EXISTS idx_calls_stage ON api_calls(stage);
        CREATE INDEX IF NOT EXISTS idx_calls_provider ON api_calls(provider);
        CREATE INDEX IF NOT EXISTS idx_ep_date ON episode_costs(date);
    """)
    conn.commit()
    conn.close()


init_cost_db()


class CostTracker:
    """Track and manage API costs in real-time."""

    def __init__(self, episode_date: str = None):
        self.episode_date = episode_date or datetime.utcnow().strftime("%Y-%m-%d")

    def record(self, stage: str, provider: str,
               tokens_in: int = 0, tokens_out: int = 0,
               characters: int = 0, minutes: float = 0,
               model: str = None, metadata: Dict = None) -> float:
        """Record an API call and return its cost."""
        cost = self._calculate_cost(
            provider, tokens_in, tokens_out, characters, minutes, model)

        conn = _get_conn()
        conn.execute(
            """INSERT INTO api_calls
               (episode_date, stage, provider, model, tokens_in, tokens_out,
                characters, minutes, cost_usd, metadata, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (self.episode_date, stage, provider, model or "",
             tokens_in, tokens_out, characters, minutes,
             cost, json.dumps(metadata or {}),
             datetime.utcnow().isoformat())
        )
        conn.commit()
        conn.close()

        logger.debug(f"Cost: {stage}/{provider} = ${cost:.4f}")
        return cost

    def _calculate_cost(self, provider: str, tokens_in: int,
                       tokens_out: int, characters: int,
                       minutes: float, model: str = None) -> float:
        """Calculate cost based on pricing model."""
        pricing = PRICING.get(provider, {})

        # ElevenLabs — character-based
        if provider == "elevenlabs":
            return characters * pricing.get("per_character", 0.00003)

        # Whisper/AssemblyAI — minute-based
        if provider in ("whisper", "assemblyai"):
            return minutes * pricing.get("per_minute", 0)

        # Token-based providers
        if model and "models" in pricing:
            model_pricing = pricing["models"].get(model, pricing.get("default", {}))
        else:
            model_pricing = pricing

        input_rate = model_pricing.get("input_per_1k", 0)
        output_rate = model_pricing.get("output_per_1k", 0)

        return (tokens_in * input_rate + tokens_out * output_rate) / 1000

    def check_budget(self, stage: str) -> Dict:
        """Check if stage is within budget.

        Returns: {"within_budget": bool, "spent": float, "budget": float, "remaining": float}
        """
        budget = STAGE_BUDGETS.get(stage, 10.0)

        conn = _get_conn()
        row = conn.execute(
            """SELECT COALESCE(SUM(cost_usd), 0) as total
               FROM api_calls
               WHERE episode_date = ? AND stage = ?""",
            (self.episode_date, stage)
        ).fetchone()
        conn.close()

        spent = row["total"] if row else 0
        remaining = budget - spent
        within_budget = spent <= budget

        if not within_budget:
            self._record_budget_alert(stage, budget, spent)

        return {
            "stage": stage,
            "within_budget": within_budget,
            "spent": round(spent, 4),
            "budget": budget,
            "remaining": round(remaining, 4),
            "overage_pct": round((spent / budget - 1) * 100, 1) if spent > budget else 0
        }

    def _record_budget_alert(self, stage: str, budget: float, actual: float):
        """Record a budget overrun alert."""
        overage = (actual / budget - 1) * 100
        conn = _get_conn()
        conn.execute(
            """INSERT INTO budget_alerts
               (stage, budget_limit, actual_cost, overage_pct, episode_date, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (stage, budget, actual, overage, self.episode_date,
             datetime.utcnow().isoformat())
        )
        conn.commit()
        conn.close()
        logger.warning(f"BUDGET ALERT: {stage} spent ${actual:.2f} "
                      f"(budget ${budget:.2f}, +{overage:.0f}%)")

    def get_episode_summary(self) -> Dict:
        """Get cost summary for current episode."""
        conn = _get_conn()

        # By stage
        by_stage = conn.execute(
            """SELECT stage, SUM(cost_usd) as cost,
                      SUM(tokens_in) as tok_in, SUM(tokens_out) as tok_out,
                      SUM(characters) as chars, COUNT(*) as calls
               FROM api_calls WHERE episode_date = ?
               GROUP BY stage ORDER BY cost DESC""",
            (self.episode_date,)
        ).fetchall()

        # By provider
        by_provider = conn.execute(
            """SELECT provider, SUM(cost_usd) as cost, COUNT(*) as calls
               FROM api_calls WHERE episode_date = ?
               GROUP BY provider ORDER BY cost DESC""",
            (self.episode_date,)
        ).fetchall()

        total = sum(r["cost"] for r in by_stage)
        conn.close()

        return {
            "episode_date": self.episode_date,
            "total_cost": round(total, 4),
            "by_stage": [{
                "stage": r["stage"],
                "cost": round(r["cost"], 4),
                "tokens_in": r["tok_in"],
                "tokens_out": r["tok_out"],
                "characters": r["chars"],
                "api_calls": r["calls"],
                "budget": STAGE_BUDGETS.get(r["stage"], 10.0),
            } for r in by_stage],
            "by_provider": [{
                "provider": r["provider"],
                "cost": round(r["cost"], 4),
                "api_calls": r["calls"],
            } for r in by_provider],
        }


class CostDashboard:
    """Cost analytics dashboard data provider."""

    def get_episode_cost(self, date: str) -> Dict:
        """Get detailed cost breakdown for an episode."""
        tracker = CostTracker(episode_date=date)
        return tracker.get_episode_summary()

    def get_cost_trend(self, days: int = 30) -> List[Dict]:
        """Get cost trend over recent days."""
        conn = _get_conn()
        cutoff = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
        rows = conn.execute(
            """SELECT episode_date, SUM(cost_usd) as daily_cost,
                      COUNT(DISTINCT stage) as stages,
                      COUNT(*) as total_calls
               FROM api_calls
               WHERE episode_date >= ?
               GROUP BY episode_date
               ORDER BY episode_date DESC""",
            (cutoff,)
        ).fetchall()
        conn.close()

        return [{
            "date": r["episode_date"],
            "cost": round(r["daily_cost"], 2),
            "stages": r["stages"],
            "api_calls": r["total_calls"],
        } for r in rows]

    def get_provider_breakdown(self, days: int = 30) -> Dict:
        """Get cost breakdown by provider over recent days."""
        conn = _get_conn()
        cutoff = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
        rows = conn.execute(
            """SELECT provider,
                      SUM(cost_usd) as total_cost,
                      SUM(tokens_in) as total_tok_in,
                      SUM(tokens_out) as total_tok_out,
                      SUM(characters) as total_chars,
                      COUNT(*) as total_calls
               FROM api_calls
               WHERE episode_date >= ?
               GROUP BY provider
               ORDER BY total_cost DESC""",
            (cutoff,)
        ).fetchall()
        conn.close()

        return {
            "period_days": days,
            "providers": [{
                "provider": r["provider"],
                "name": PRICING.get(r["provider"], {}).get("name", r["provider"]),
                "total_cost": round(r["total_cost"], 2),
                "tokens_in": r["total_tok_in"],
                "tokens_out": r["total_tok_out"],
                "characters": r["total_chars"],
                "api_calls": r["total_calls"],
            } for r in rows]
        }

    def get_budget_alerts(self, days: int = 7) -> List[Dict]:
        """Get recent budget alert history."""
        conn = _get_conn()
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        rows = conn.execute(
            """SELECT * FROM budget_alerts
               WHERE created_at > ?
               ORDER BY created_at DESC""",
            (cutoff,)
        ).fetchall()
        conn.close()

        return [{
            "stage": r["stage"],
            "budget": r["budget_limit"],
            "actual": round(r["actual_cost"], 2),
            "overage_pct": round(r["overage_pct"], 1),
            "date": r["episode_date"],
            "timestamp": r["created_at"],
        } for r in rows]

    def get_optimization_suggestions(self) -> List[Dict]:
        """Analyze costs and suggest optimizations."""
        suggestions = []

        # Check last 7 days of data
        conn = _get_conn()
        cutoff = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")

        # Find expensive stages
        expensive = conn.execute(
            """SELECT stage, AVG(cost_usd) as avg_cost,
                      AVG(tokens_in + tokens_out) as avg_tokens
               FROM api_calls
               WHERE episode_date >= ?
               GROUP BY stage
               HAVING avg_cost > 1.0
               ORDER BY avg_cost DESC""",
            (cutoff,)
        ).fetchall()

        for r in expensive:
            suggestions.append({
                "type": "expensive_stage",
                "stage": r["stage"],
                "avg_cost": round(r["avg_cost"], 2),
                "avg_tokens": int(r["avg_tokens"]),
                "suggestion": f"Consider using a smaller model or shorter prompts for {r['stage']} "
                             f"(avg ${r['avg_cost']:.2f}/run, {int(r['avg_tokens'])} tokens)"
            })

        # Check for underutilized stages
        underutilized = conn.execute(
            """SELECT stage, COUNT(*) as calls,
                      SUM(cost_usd) as total
               FROM api_calls
               WHERE episode_date >= ?
               GROUP BY stage
               HAVING calls > 10 AND total / calls < 0.01""",
            (cutoff,)
        ).fetchall()

        for r in underutilized:
            suggestions.append({
                "type": "low_value_calls",
                "stage": r["stage"],
                "calls": r["calls"],
                "total_cost": round(r["total"], 4),
                "suggestion": f"{r['stage']} makes many low-value API calls "
                             f"({r['calls']} calls, ${r['total']:.2f} total). "
                             f"Consider batching or caching."
            })

        conn.close()
        return suggestions
