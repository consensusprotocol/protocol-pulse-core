"""
MONITORING + ALERTING SYSTEM
==============================
Comprehensive observability for the Protocol Pulse content pipeline.

Tracks:
  - Pipeline success/failure rates
  - API costs per run (by stage, by provider)
  - GPU utilization
  - Response times per stage
  - Error rates by stage
  - Anomaly detection (cost spikes, unusual failures)

Alerts via:
  - Discord webhook
  - Telegram bot

Reports:
  - Daily summary
  - Weekly cost analysis
  - Anomaly alerts in real-time

Usage:
    from pp_services.video_engine.monitoring import PipelineMonitor
    monitor = PipelineMonitor()
    monitor.record_run(result)
    monitor.daily_summary()
    monitor.weekly_cost_report()
"""

import os
import json
import sqlite3
import logging
import statistics
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("PipelineMonitor")

DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "video_engine" / "monitoring.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


# ─── Database Schema ───

def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_monitoring_db():
    """Initialize monitoring database."""
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS pipeline_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            status TEXT NOT NULL,
            dry_run INTEGER DEFAULT 0,
            runtime_seconds REAL DEFAULT 0,
            total_cost REAL DEFAULT 0,
            stages_completed INTEGER DEFAULT 0,
            stages_failed INTEGER DEFAULT 0,
            stages_skipped INTEGER DEFAULT 0,
            dead_letters INTEGER DEFAULT 0,
            error TEXT,
            metadata TEXT DEFAULT '{}',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS stage_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER NOT NULL,
            stage_name TEXT NOT NULL,
            status TEXT NOT NULL,
            duration_seconds REAL DEFAULT 0,
            attempts INTEGER DEFAULT 1,
            cost_estimate REAL DEFAULT 0,
            error TEXT,
            metadata TEXT DEFAULT '{}',
            created_at TEXT NOT NULL,
            FOREIGN KEY (run_id) REFERENCES pipeline_runs(id)
        );

        CREATE TABLE IF NOT EXISTS api_costs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER NOT NULL,
            provider TEXT NOT NULL,
            tokens_in INTEGER DEFAULT 0,
            tokens_out INTEGER DEFAULT 0,
            characters INTEGER DEFAULT 0,
            cost_usd REAL DEFAULT 0,
            stage TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (run_id) REFERENCES pipeline_runs(id)
        );

        CREATE TABLE IF NOT EXISTS health_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            severity TEXT NOT NULL DEFAULT 'info',
            title TEXT NOT NULL,
            detail TEXT,
            metadata TEXT DEFAULT '{}',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS anomalies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            anomaly_type TEXT NOT NULL,
            severity TEXT NOT NULL DEFAULT 'warning',
            description TEXT NOT NULL,
            metric_name TEXT,
            expected_value REAL,
            actual_value REAL,
            resolved INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_runs_date ON pipeline_runs(date);
        CREATE INDEX IF NOT EXISTS idx_runs_status ON pipeline_runs(status);
        CREATE INDEX IF NOT EXISTS idx_stage_run ON stage_metrics(run_id);
        CREATE INDEX IF NOT EXISTS idx_costs_run ON api_costs(run_id);
        CREATE INDEX IF NOT EXISTS idx_health_time ON health_events(created_at);
        CREATE INDEX IF NOT EXISTS idx_anomalies_type ON anomalies(anomaly_type);
    """)
    conn.commit()
    conn.close()


# Initialize on import
init_monitoring_db()


# ─── Pipeline Monitor ───

class PipelineMonitor:
    """Central monitoring and metrics collection."""

    def __init__(self):
        self._conn = None

    def _get_conn(self) -> sqlite3.Connection:
        if not self._conn:
            self._conn = _get_conn()
        return self._conn

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    # ─── Recording ───

    def record_run(self, result: Dict) -> int:
        """Record a complete pipeline run result."""
        conn = self._get_conn()
        now = datetime.utcnow().isoformat()

        stages = result.get("stages", {})
        if not isinstance(stages, dict):
            stages = {}

        completed = sum(1 for s in stages.values()
                       if s.get("status") == "success")
        failed = sum(1 for s in stages.values()
                    if s.get("status") in ("failed", "dead_letter"))
        skipped = sum(1 for s in stages.values()
                     if s.get("status") == "skipped")

        cost_summary = result.get("cost_summary", {})

        try:
            cursor = conn.execute(
                """INSERT INTO pipeline_runs
                   (date, status, dry_run, runtime_seconds, total_cost,
                    stages_completed, stages_failed, stages_skipped,
                    dead_letters, error, metadata, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    result.get("date", ""),
                    result.get("status", "unknown"),
                    1 if result.get("dry_run") else 0,
                    result.get("runtime_seconds", 0),
                    cost_summary.get("total_cost", 0),
                    completed, failed, skipped,
                    len(result.get("dead_letters", [])),
                    result.get("error", ""),
                    json.dumps(result.get("cost_summary", {})),
                    now
                )
            )
            run_id = cursor.lastrowid

            # Record stage metrics
            for stage_name, stage_data in stages.items():
                conn.execute(
                    """INSERT INTO stage_metrics
                       (run_id, stage_name, status, duration_seconds,
                        attempts, cost_estimate, error, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        run_id,
                        stage_name,
                        stage_data.get("status", "unknown"),
                        stage_data.get("duration", 0),
                        stage_data.get("attempts", 1),
                        stage_data.get("cost_estimate", 0),
                        stage_data.get("error", ""),
                        now
                    )
                )

            # Record API costs
            stage_costs = cost_summary.get("stage_costs", {})
            for stage, cost in stage_costs.items():
                if cost > 0:
                    conn.execute(
                        """INSERT INTO api_costs
                           (run_id, provider, cost_usd, stage, created_at)
                           VALUES (?, ?, ?, ?, ?)""",
                        (run_id, "mixed", cost, stage, now)
                    )

            conn.commit()
        except Exception:
            conn.rollback()
            raise

        # Run anomaly detection (outside transaction — non-critical)
        try:
            self._check_anomalies(run_id, result)
        except Exception as e:
            logger.warning(f"Anomaly detection failed for run {run_id}: {e}")

        logger.info(f"Run recorded: id={run_id}, status={result.get('status')}")
        return run_id

    def record_health_event(self, event_type: str, title: str,
                           detail: str = "", severity: str = "info",
                           metadata: Dict = None):
        """Record a health event."""
        conn = self._get_conn()
        conn.execute(
            """INSERT INTO health_events
               (event_type, severity, title, detail, metadata, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (event_type, severity, title, detail,
             json.dumps(metadata or {}),
             datetime.utcnow().isoformat())
        )
        conn.commit()

    # ─── Querying ───

    def get_success_rate(self, days: int = 7) -> Dict:
        """Get pipeline success/failure rate over recent days."""
        conn = self._get_conn()
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        rows = conn.execute(
            """SELECT status, COUNT(*) as count
               FROM pipeline_runs
               WHERE created_at > ? AND dry_run = 0
               GROUP BY status""",
            (cutoff,)
        ).fetchall()

        total = sum(r["count"] for r in rows)
        status_counts = {r["status"]: r["count"] for r in rows}
        success = status_counts.get("complete", 0)

        return {
            "period_days": days,
            "total_runs": total,
            "success": success,
            "failed": status_counts.get("failed", 0) + status_counts.get("error", 0),
            "success_rate": round(success / total * 100, 1) if total else 0,
            "status_breakdown": status_counts
        }

    def get_stage_error_rates(self, days: int = 7) -> List[Dict]:
        """Get error rates by stage over recent days."""
        conn = self._get_conn()
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        rows = conn.execute(
            """SELECT stage_name,
                      COUNT(*) as total,
                      SUM(CASE WHEN status IN ('failed', 'dead_letter') THEN 1 ELSE 0 END) as failures,
                      AVG(duration_seconds) as avg_duration,
                      AVG(attempts) as avg_attempts
               FROM stage_metrics
               WHERE created_at > ?
               GROUP BY stage_name
               ORDER BY failures DESC""",
            (cutoff,)
        ).fetchall()

        return [{
            "stage": r["stage_name"],
            "total_runs": r["total"],
            "failures": r["failures"],
            "error_rate": round(r["failures"] / r["total"] * 100, 1) if r["total"] else 0,
            "avg_duration": round(r["avg_duration"], 1) if r["avg_duration"] else 0,
            "avg_attempts": round(r["avg_attempts"], 1) if r["avg_attempts"] else 0,
        } for r in rows]

    def get_cost_by_day(self, days: int = 30) -> List[Dict]:
        """Get daily cost breakdown."""
        conn = self._get_conn()
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        rows = conn.execute(
            """SELECT date, SUM(total_cost) as daily_cost,
                      COUNT(*) as runs
               FROM pipeline_runs
               WHERE created_at > ? AND dry_run = 0
               GROUP BY date
               ORDER BY date DESC""",
            (cutoff,)
        ).fetchall()

        return [{
            "date": r["date"],
            "cost": round(r["daily_cost"], 2),
            "runs": r["runs"]
        } for r in rows]

    def get_cost_by_stage(self, days: int = 30) -> List[Dict]:
        """Get cost breakdown by stage."""
        conn = self._get_conn()
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        rows = conn.execute(
            """SELECT stage, SUM(cost_usd) as total_cost,
                      COUNT(*) as count, AVG(cost_usd) as avg_cost
               FROM api_costs
               WHERE created_at > ?
               GROUP BY stage
               ORDER BY total_cost DESC""",
            (cutoff,)
        ).fetchall()

        return [{
            "stage": r["stage"],
            "total_cost": round(r["total_cost"], 2),
            "count": r["count"],
            "avg_cost": round(r["avg_cost"], 3)
        } for r in rows]

    def get_response_times(self, days: int = 7) -> Dict:
        """Get response time statistics per stage."""
        conn = self._get_conn()
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        rows = conn.execute(
            """SELECT stage_name,
                      MIN(duration_seconds) as min_dur,
                      MAX(duration_seconds) as max_dur,
                      AVG(duration_seconds) as avg_dur
               FROM stage_metrics
               WHERE created_at > ? AND status = 'success'
               GROUP BY stage_name
               ORDER BY avg_dur DESC""",
            (cutoff,)
        ).fetchall()

        return {r["stage_name"]: {
            "min": round(r["min_dur"], 1),
            "max": round(r["max_dur"], 1),
            "avg": round(r["avg_dur"], 1)
        } for r in rows}

    # ─── Anomaly Detection ───

    def _check_anomalies(self, run_id: int, result: Dict):
        """Run anomaly detection on the latest run."""
        conn = self._get_conn()
        now = datetime.utcnow().isoformat()

        # 1. Cost anomaly — 3x higher than 7-day average
        cost = result.get("cost_summary", {}).get("total_cost", 0)
        if cost > 0:
            rows = conn.execute(
                """SELECT AVG(total_cost) as avg_cost, COUNT(*) as n
                   FROM pipeline_runs
                   WHERE dry_run = 0 AND total_cost > 0
                   AND id < ?
                   ORDER BY created_at DESC LIMIT 7""",
                (run_id,)
            ).fetchone()

            if rows and rows["avg_cost"] and rows["n"] >= 3:
                avg = rows["avg_cost"]
                if cost > avg * 3:
                    self._record_anomaly(
                        "cost_spike", "warning",
                        f"Run cost ${cost:.2f} is {cost/avg:.1f}x the 7-day average (${avg:.2f})",
                        "total_cost", avg, cost
                    )

        # 2. Runtime anomaly — 2x longer than average
        runtime = result.get("runtime_seconds", 0)
        if runtime > 0:
            rows = conn.execute(
                """SELECT AVG(runtime_seconds) as avg_rt
                   FROM pipeline_runs
                   WHERE dry_run = 0 AND runtime_seconds > 0
                   AND id < ?
                   ORDER BY created_at DESC LIMIT 7""",
                (run_id,)
            ).fetchone()

            if rows and rows["avg_rt"] and rows["avg_rt"] > 0:
                avg_rt = rows["avg_rt"]
                if runtime > avg_rt * 2:
                    self._record_anomaly(
                        "runtime_spike", "info",
                        f"Runtime {runtime:.0f}s is {runtime/avg_rt:.1f}x the average ({avg_rt:.0f}s)",
                        "runtime_seconds", avg_rt, runtime
                    )

        # 3. Consecutive failure detection
        recent = conn.execute(
            """SELECT status FROM pipeline_runs
               WHERE dry_run = 0
               ORDER BY created_at DESC LIMIT 3"""
        ).fetchall()

        if len(recent) >= 3 and all(
            r["status"] in ("failed", "error") for r in recent
        ):
            self._record_anomaly(
                "consecutive_failures", "critical",
                "3 consecutive pipeline failures detected",
                "failure_streak", 0, 3
            )

    def _record_anomaly(self, anomaly_type: str, severity: str,
                       description: str, metric: str,
                       expected: float, actual: float):
        """Record an anomaly (with deduplication)."""
        conn = self._get_conn()
        # Prevent duplicate anomalies within the same hour
        cutoff = (datetime.utcnow() - timedelta(hours=1)).isoformat()
        existing = conn.execute(
            """SELECT COUNT(*) FROM anomalies
               WHERE anomaly_type = ? AND metric_name = ?
               AND created_at > ?""",
            (anomaly_type, metric, cutoff)
        ).fetchone()[0]
        if existing > 0:
            logger.debug(f"Skipping duplicate anomaly: {anomaly_type}/{metric}")
            return
        conn.execute(
            """INSERT INTO anomalies
               (anomaly_type, severity, description, metric_name,
                expected_value, actual_value, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (anomaly_type, severity, description, metric,
             expected, actual, datetime.utcnow().isoformat())
        )
        conn.commit()
        logger.warning(f"ANOMALY [{severity}]: {description}")

        # Send alert for critical/warning anomalies
        if severity in ("critical", "warning"):
            self._send_anomaly_alert(anomaly_type, severity, description)

    def _send_anomaly_alert(self, anomaly_type: str, severity: str,
                           description: str):
        """Send anomaly alert via Discord/Telegram."""
        try:
            from pp_services.video_engine.pipeline_alerts import send_alert
            level_map = {"critical": "error", "warning": "warning", "info": "info"}
            send_alert(
                f"Anomaly Detected: {anomaly_type}",
                description,
                level=level_map.get(severity, "info"),
                fields={"Type": anomaly_type, "Severity": severity}
            )
        except Exception as e:
            logger.warning(f"Failed to send anomaly alert: {e}")

    # ─── Reports ───

    def daily_summary(self, date: str = None) -> Dict:
        """Generate daily summary report."""
        date = date or datetime.utcnow().strftime("%Y-%m-%d")
        conn = self._get_conn()

        # Get runs for the day
        runs = conn.execute(
            """SELECT * FROM pipeline_runs
               WHERE date = ? ORDER BY created_at""",
            (date,)
        ).fetchall()

        if not runs:
            return {"date": date, "status": "no_runs"}

        total_cost = sum(r["total_cost"] for r in runs)
        total_runtime = sum(r["runtime_seconds"] for r in runs)
        success_count = sum(1 for r in runs if r["status"] == "complete")

        # Stage error breakdown
        stage_errors = conn.execute(
            """SELECT sm.stage_name, COUNT(*) as failures
               FROM stage_metrics sm
               JOIN pipeline_runs pr ON sm.run_id = pr.id
               WHERE pr.date = ? AND sm.status IN ('failed', 'dead_letter')
               GROUP BY sm.stage_name
               ORDER BY failures DESC""",
            (date,)
        ).fetchall()

        # Anomalies
        anomalies = conn.execute(
            """SELECT anomaly_type, severity, description, metric_name,
                      expected_value, actual_value, created_at
               FROM anomalies
               WHERE DATE(created_at) = ?
               ORDER BY created_at""",
            (date,)
        ).fetchall()

        summary = {
            "date": date,
            "runs": len(runs),
            "success": success_count,
            "failed": len(runs) - success_count,
            "total_cost": round(total_cost, 2),
            "total_runtime_seconds": round(total_runtime, 0),
            "stage_errors": [{
                "stage": r["stage_name"],
                "failures": r["failures"]
            } for r in stage_errors],
            "anomalies": [{
                "type": a["anomaly_type"],
                "severity": a["severity"],
                "description": a["description"]
            } for a in anomalies]
        }

        return summary

    def weekly_cost_report(self) -> Dict:
        """Generate weekly cost analysis."""
        conn = self._get_conn()
        cutoff = (datetime.utcnow() - timedelta(days=7)).isoformat()

        # Daily costs
        daily = conn.execute(
            """SELECT date, SUM(total_cost) as cost, COUNT(*) as runs
               FROM pipeline_runs
               WHERE created_at > ? AND dry_run = 0
               GROUP BY date ORDER BY date""",
            (cutoff,)
        ).fetchall()

        costs = [r["cost"] for r in daily if r["cost"] > 0]

        # Stage cost breakdown
        by_stage = conn.execute(
            """SELECT ac.stage, SUM(ac.cost_usd) as total
               FROM api_costs ac
               JOIN pipeline_runs pr ON ac.run_id = pr.id
               WHERE pr.created_at > ?
               GROUP BY ac.stage
               ORDER BY total DESC""",
            (cutoff,)
        ).fetchall()

        report = {
            "period": "7 days",
            "total_cost": round(sum(costs), 2),
            "avg_daily_cost": round(statistics.mean(costs), 2) if costs else 0,
            "max_daily_cost": round(max(costs), 2) if costs else 0,
            "min_daily_cost": round(min(costs), 2) if costs else 0,
            "daily_breakdown": [{
                "date": r["date"],
                "cost": round(r["cost"], 2),
                "runs": r["runs"]
            } for r in daily],
            "stage_breakdown": [{
                "stage": r["stage"],
                "cost": round(r["total"], 2)
            } for r in by_stage],
            "total_runs": sum(r["runs"] for r in daily),
        }

        return report

    def send_daily_summary_alert(self, date: str = None):
        """Send daily summary via Discord/Telegram."""
        summary = self.daily_summary(date)
        if summary.get("status") == "no_runs":
            return

        try:
            from pp_services.video_engine.pipeline_alerts import send_alert

            msg = (
                f"Runs: {summary['runs']} "
                f"({summary['success']} success, {summary['failed']} failed)\n"
                f"Cost: ${summary['total_cost']:.2f}\n"
                f"Runtime: {summary['total_runtime_seconds']:.0f}s"
            )

            if summary.get("stage_errors"):
                msg += "\n\nStage Errors:"
                for se in summary["stage_errors"][:5]:
                    msg += f"\n  {se['stage']}: {se['failures']} failures"

            if summary.get("anomalies"):
                msg += f"\n\nAnomalies: {len(summary['anomalies'])}"
                for a in summary["anomalies"][:3]:
                    msg += f"\n  [{a['severity']}] {a['description'][:80]}"

            send_alert(
                f"Daily Pipeline Summary — {summary['date']}",
                msg,
                level="info" if summary["failed"] == 0 else "warning",
                fields={
                    "Success Rate": f"{summary['success']}/{summary['runs']}",
                    "Cost": f"${summary['total_cost']:.2f}",
                    "Runtime": f"{summary['total_runtime_seconds']:.0f}s"
                }
            )
        except Exception as e:
            logger.warning(f"Failed to send daily summary alert: {e}")

    def send_weekly_cost_alert(self):
        """Send weekly cost report via Discord/Telegram."""
        report = self.weekly_cost_report()

        try:
            from pp_services.video_engine.pipeline_alerts import send_alert

            msg = (
                f"Total: ${report['total_cost']:.2f} "
                f"(avg ${report['avg_daily_cost']:.2f}/day)\n"
                f"Runs: {report['total_runs']}\n"
                f"Range: ${report['min_daily_cost']:.2f} - ${report['max_daily_cost']:.2f}"
            )

            if report.get("stage_breakdown"):
                msg += "\n\nTop Cost Stages:"
                for sb in report["stage_breakdown"][:5]:
                    msg += f"\n  {sb['stage']}: ${sb['cost']:.2f}"

            send_alert(
                "Weekly Cost Report",
                msg,
                level="info",
                fields={
                    "Total": f"${report['total_cost']:.2f}",
                    "Avg/Day": f"${report['avg_daily_cost']:.2f}",
                    "Runs": str(report['total_runs'])
                }
            )
        except Exception as e:
            logger.warning(f"Failed to send weekly cost alert: {e}")


# ─── GPU Monitor ───

class GPUMonitor:
    """Monitor GPU utilization on Ultron."""

    @staticmethod
    def get_gpu_stats() -> List[Dict]:
        """Get GPU utilization stats using nvidia-smi."""
        try:
            import subprocess
            result = subprocess.run(
                ["nvidia-smi",
                 "--query-gpu=index,name,utilization.gpu,utilization.memory,"
                 "memory.total,memory.used,temperature.gpu",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                return []

            gpus = []
            for line in result.stdout.strip().split("\n"):
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 7:
                    gpus.append({
                        "index": int(parts[0]),
                        "name": parts[1],
                        "gpu_util_pct": float(parts[2]),
                        "memory_util_pct": float(parts[3]),
                        "memory_total_mb": float(parts[4]),
                        "memory_used_mb": float(parts[5]),
                        "temperature_c": float(parts[6])
                    })
            return gpus
        except Exception as e:
            logger.debug(f"GPU stats unavailable: {e}")
            return []

    @staticmethod
    def check_gpu_health() -> Dict:
        """Check GPU health status."""
        gpus = GPUMonitor.get_gpu_stats()
        if not gpus:
            return {"available": False, "message": "No GPUs detected"}

        issues = []
        for gpu in gpus:
            if gpu["temperature_c"] > 85:
                issues.append(f"GPU {gpu['index']} temp high: {gpu['temperature_c']}C")
            if gpu["memory_util_pct"] > 95:
                issues.append(f"GPU {gpu['index']} memory near full: {gpu['memory_util_pct']}%")

        return {
            "available": True,
            "gpu_count": len(gpus),
            "gpus": gpus,
            "healthy": len(issues) == 0,
            "issues": issues
        }


# ─── Dashboard Data Provider ───

class DashboardDataProvider:
    """Provide data for monitoring dashboard widgets."""

    def __init__(self):
        self.monitor = PipelineMonitor()
        self.gpu_monitor = GPUMonitor()

    def get_overview(self) -> Dict:
        """Get complete monitoring overview."""
        return {
            "success_rate_7d": self.monitor.get_success_rate(7),
            "success_rate_30d": self.monitor.get_success_rate(30),
            "cost_daily": self.monitor.get_cost_by_day(7),
            "cost_by_stage": self.monitor.get_cost_by_stage(30),
            "stage_errors": self.monitor.get_stage_error_rates(7),
            "response_times": self.monitor.get_response_times(7),
            "gpu_status": self.gpu_monitor.check_gpu_health(),
            "today_summary": self.monitor.daily_summary(),
        }

    def get_health_status(self) -> Dict:
        """Get system health status for health check endpoint."""
        success = self.monitor.get_success_rate(1)
        gpu = self.gpu_monitor.check_gpu_health()

        # Determine overall health
        status = "healthy"
        issues = []

        if success.get("total_runs", 0) > 0 and success.get("success_rate", 100) < 50:
            status = "degraded"
            issues.append("Low success rate today")

        if gpu.get("available") and not gpu.get("healthy", True):
            status = "degraded"
            issues.extend(gpu.get("issues", []))

        return {
            "status": status,
            "pipeline": success,
            "gpu": gpu,
            "issues": issues,
            "checked_at": datetime.utcnow().isoformat()
        }

    def close(self):
        self.monitor.close()
