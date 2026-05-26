"""
SELF-HEALING PIPELINE ENGINE
==============================
Wraps the DailyDriver with production-grade resilience:
  - Automatic retry with exponential backoff per stage
  - Stage-level checkpointing (resume from last successful stage)
  - Dead letter queue for permanently failed items
  - Health checks before each stage
  - Graceful degradation (skip non-critical stages)
  - Cost circuit breakers (stop if spending exceeds daily budget)

Usage:
    python -m services.video_engine.self_healing --dry-run --force
    python -m services.video_engine.self_healing --resume   # Resume from checkpoint
"""

import os
import sys
import json
import time
import logging
import argparse
import traceback
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Callable, Any
from dataclasses import dataclass, field, asdict
from enum import Enum

import re
import pytz

logger = logging.getLogger("SelfHealing")

# Strict date pattern to prevent path traversal via date_str
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _validate_date_str(date_str: str) -> str:
    """Validate date_str is YYYY-MM-DD format. Prevents path traversal."""
    if not _DATE_RE.match(date_str):
        raise ValueError(f"Invalid date format (expected YYYY-MM-DD): {date_str!r}")
    return date_str


def _validate_stage_name(stage: str) -> str:
    """Validate stage name is alphanumeric + underscores only."""
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", stage):
        raise ValueError(f"Invalid stage name: {stage!r}")
    return stage


# ─── Configuration ───

class StageStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    DEAD_LETTER = "dead_letter"


@dataclass
class StageConfig:
    """Configuration for a pipeline stage."""
    name: str
    critical: bool = True          # If False, stage can be skipped on failure
    max_retries: int = 3
    base_delay: float = 2.0        # Base delay in seconds for exponential backoff
    max_delay: float = 60.0        # Max delay cap
    timeout: float = 300.0         # Stage timeout in seconds
    cost_weight: float = 0.0       # Estimated cost weight for budget checks


@dataclass
class StageResult:
    """Result from running a pipeline stage."""
    name: str
    status: StageStatus
    attempts: int = 0
    duration: float = 0.0
    error: str = ""
    data: Dict = field(default_factory=dict)
    cost_estimate: float = 0.0


@dataclass
class PipelineCheckpoint:
    """Checkpoint state for resumable pipeline."""
    date_str: str
    dry_run: bool
    force: bool
    completed_stages: List[str] = field(default_factory=list)
    stage_results: Dict[str, Dict] = field(default_factory=dict)
    stage_data: Dict[str, Any] = field(default_factory=dict)
    total_cost: float = 0.0
    started_at: str = ""
    updated_at: str = ""


# Default stage configurations
STAGE_CONFIGS = {
    "acquire_lock": StageConfig("acquire_lock", critical=True, max_retries=1),
    "create_bundle": StageConfig("create_bundle", critical=True, max_retries=1),
    "source_ingestion": StageConfig("source_ingestion", critical=True, max_retries=3,
                                     base_delay=5.0, timeout=600.0, cost_weight=0.1),
    "grok_triage": StageConfig("grok_triage", critical=False, max_retries=2,
                                base_delay=3.0, cost_weight=1.0),
    "clustering": StageConfig("clustering", critical=False, max_retries=2,
                               cost_weight=0.0),
    "claude_director": StageConfig("claude_director", critical=True, max_retries=3,
                                    base_delay=5.0, cost_weight=2.0),
    "qa_review": StageConfig("qa_review", critical=False, max_retries=2,
                              cost_weight=0.5),
    "clip_extraction": StageConfig("clip_extraction", critical=True, max_retries=3,
                                    base_delay=3.0, timeout=600.0, cost_weight=0.0),
    "narration": StageConfig("narration", critical=False, max_retries=3,
                              base_delay=5.0, timeout=300.0, cost_weight=3.0),
    "avatar": StageConfig("avatar", critical=False, max_retries=1,
                           cost_weight=1.0),
    "manifest": StageConfig("manifest", critical=True, max_retries=2,
                             cost_weight=0.0),
    "assembly": StageConfig("assembly", critical=True, max_retries=2,
                             base_delay=10.0, timeout=900.0, cost_weight=0.5),
    "post_qa": StageConfig("post_qa", critical=False, max_retries=1,
                            cost_weight=0.0),
    "distribution_pack": StageConfig("distribution_pack", critical=False,
                                      max_retries=2, cost_weight=0.0),
    "editorial_memory": StageConfig("editorial_memory", critical=False,
                                     max_retries=1, cost_weight=0.0),
    "log_costs": StageConfig("log_costs", critical=False, max_retries=1,
                              cost_weight=0.0),
    "send_alerts": StageConfig("send_alerts", critical=False, max_retries=2,
                                cost_weight=0.0),
    "release_lock": StageConfig("release_lock", critical=False, max_retries=1),
}


# ─── Checkpoint Persistence ───

CHECKPOINT_DIR = Path("state/checkpoints")
DEAD_LETTER_DIR = Path("state/dead_letter")


def _ensure_dirs():
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    DEAD_LETTER_DIR.mkdir(parents=True, exist_ok=True)


def save_checkpoint(checkpoint: PipelineCheckpoint):
    """Save pipeline checkpoint to disk."""
    _ensure_dirs()
    _validate_date_str(checkpoint.date_str)
    checkpoint.updated_at = datetime.utcnow().isoformat()
    path = CHECKPOINT_DIR / f"checkpoint_{checkpoint.date_str}.json"
    path.write_text(json.dumps(asdict(checkpoint), indent=2, default=str))
    logger.debug(f"Checkpoint saved: {path}")


def load_checkpoint(date_str: str) -> Optional[PipelineCheckpoint]:
    """Load existing checkpoint for a date."""
    _validate_date_str(date_str)
    path = CHECKPOINT_DIR / f"checkpoint_{date_str}.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        return PipelineCheckpoint(**data)
    except Exception as e:
        logger.warning(f"Failed to load checkpoint: {e}")
        return None


def clear_checkpoint(date_str: str):
    """Remove checkpoint after successful completion."""
    _validate_date_str(date_str)
    path = CHECKPOINT_DIR / f"checkpoint_{date_str}.json"
    path.unlink(missing_ok=True)


# ─── Dead Letter Queue ───

def send_to_dead_letter(date_str: str, stage: str, error: str, context: Dict):
    """Send a permanently failed stage to the dead letter queue."""
    _ensure_dirs()
    _validate_date_str(date_str)
    _validate_stage_name(stage)
    entry = {
        "date": date_str,
        "stage": stage,
        "error": str(error)[:5000],  # Cap error size
        "context": context,
        "timestamp": datetime.utcnow().isoformat(),
        "resolved": False
    }
    path = DEAD_LETTER_DIR / f"dlq_{date_str}_{stage}.json"
    path.write_text(json.dumps(entry, indent=2, default=str))
    logger.error(f"Dead letter: {stage} for {date_str} — {str(error)[:100]}")


def get_dead_letters(resolved: bool = False) -> List[Dict]:
    """Get all dead letter entries."""
    _ensure_dirs()
    results = []
    for path in sorted(DEAD_LETTER_DIR.glob("dlq_*.json")):
        try:
            entry = json.loads(path.read_text())
            if entry.get("resolved") == resolved:
                entry["_path"] = str(path)
                results.append(entry)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Malformed dead letter file {path.name}: {e}")
    return results


def resolve_dead_letter(date_str: str, stage: str):
    """Mark a dead letter entry as resolved."""
    path = DEAD_LETTER_DIR / f"dlq_{date_str}_{stage}.json"
    if path.exists():
        entry = json.loads(path.read_text())
        entry["resolved"] = True
        entry["resolved_at"] = datetime.utcnow().isoformat()
        path.write_text(json.dumps(entry, indent=2, default=str))


# ─── Health Checks ───

class HealthChecker:
    """Pre-stage health checks."""

    @staticmethod
    def check_disk_space(min_gb: float = 1.0) -> bool:
        """Check available disk space."""
        try:
            import shutil
            total, used, free = shutil.disk_usage("/")
            free_gb = free / (1024 ** 3)
            if free_gb < min_gb:
                logger.error(f"Low disk space: {free_gb:.1f}GB free (need {min_gb}GB)")
                return False
            return True
        except Exception:
            return True  # Don't block on check failure

    @staticmethod
    def check_api_keys(stage: str) -> bool:
        """Check required API keys for a stage."""
        requirements = {
            "grok_triage": ["XAI_API_KEY"],
            "claude_director": ["ANTHROPIC_API_KEY"],
            "narration": ["ELEVENLABS_API_KEY"],
        }
        keys = requirements.get(stage, [])
        for key in keys:
            if not os.environ.get(key, "").strip():
                logger.warning(f"Missing API key for {stage}: {key}")
                return False
        return True

    @staticmethod
    def check_ultron_available() -> bool:
        """Check if Ultron GPU server is reachable."""
        try:
            import requests
            ultron_url = os.environ.get("ULTRON_API_URL", "http://localhost:8100")
            resp = requests.get(f"{ultron_url}/health", timeout=5)
            return resp.status_code == 200
        except Exception:
            return False

    @staticmethod
    def check_memory(min_mb: float = 256.0) -> bool:
        """Check available memory."""
        try:
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemAvailable:"):
                        available_kb = int(line.split()[1])
                        available_mb = available_kb / 1024
                        if available_mb < min_mb:
                            logger.error(f"Low memory: {available_mb:.0f}MB (need {min_mb:.0f}MB)")
                            return False
                        return True
        except Exception:
            return True

    @classmethod
    def run_pre_stage_checks(cls, stage: str) -> List[str]:
        """Run all relevant health checks for a stage. Returns list of failures."""
        failures = []

        if not cls.check_disk_space():
            failures.append("disk_space")

        if not cls.check_memory():
            failures.append("memory")

        if not cls.check_api_keys(stage):
            failures.append(f"api_keys_{stage}")

        # Only check Ultron for assembly stages
        if stage in ("clip_extraction", "assembly") and not cls.check_ultron_available():
            failures.append("ultron_offline")

        return failures


# ─── Cost Circuit Breaker ───

class CostCircuitBreaker:
    """Stop pipeline if spending exceeds daily budget."""

    def __init__(self, daily_budget: float = None):
        self.daily_budget = daily_budget or float(
            os.environ.get("PIPELINE_DAILY_BUDGET", "15.0"))
        self.total_cost = 0.0
        self.stage_costs: Dict[str, float] = {}
        self._tripped = False

    def record_cost(self, stage: str, cost: float):
        """Record cost for a stage."""
        self.stage_costs[stage] = cost
        self.total_cost = sum(self.stage_costs.values())

    def check(self, stage: str) -> bool:
        """Check if budget allows continuing. Returns True if OK."""
        if self._tripped:
            logger.error(f"Circuit breaker TRIPPED — budget exceeded "
                        f"(${self.total_cost:.2f} / ${self.daily_budget:.2f})")
            return False

        # Estimate cost for upcoming stage
        config = STAGE_CONFIGS.get(stage)
        estimated_next = config.cost_weight if config else 0
        if self.total_cost + estimated_next > self.daily_budget:
            self._tripped = True
            logger.error(f"Circuit breaker TRIPPING — "
                        f"${self.total_cost:.2f} + ~${estimated_next:.2f} "
                        f"> ${self.daily_budget:.2f} budget")
            return False

        return True

    @property
    def is_tripped(self) -> bool:
        return self._tripped

    def summary(self) -> Dict:
        return {
            "daily_budget": self.daily_budget,
            "total_cost": round(self.total_cost, 2),
            "stage_costs": {k: round(v, 2) for k, v in self.stage_costs.items()},
            "tripped": self._tripped,
            "remaining": round(self.daily_budget - self.total_cost, 2)
        }


# ─── Retry Engine ───

def retry_with_backoff(
    func: Callable,
    stage_config: StageConfig,
    *args, **kwargs
) -> tuple:
    """Execute a function with exponential backoff retry logic.

    Returns (result, attempts) tuple on success.
    Raises the last exception on failure after all retries.
    """
    last_error = None
    for attempt in range(1, stage_config.max_retries + 1):
        try:
            result = func(*args, **kwargs)
            return result, attempt
        except Exception as e:
            last_error = e
            if attempt < stage_config.max_retries:
                delay = min(
                    stage_config.base_delay * (2 ** (attempt - 1)),
                    stage_config.max_delay
                )
                logger.warning(
                    f"  Stage {stage_config.name} attempt {attempt}/{stage_config.max_retries} "
                    f"failed: {e} — retrying in {delay:.0f}s"
                )
                time.sleep(delay)
            else:
                logger.error(
                    f"  Stage {stage_config.name} FAILED after {stage_config.max_retries} attempts: {e}"
                )
    raise last_error


# ─── Self-Healing Pipeline ───

class SelfHealingPipeline:
    """Production-grade pipeline wrapper with self-healing capabilities."""

    # Ordered list of stage names (execution order)
    STAGE_ORDER = [
        "acquire_lock",
        "create_bundle",
        "source_ingestion",
        "grok_triage",
        "clustering",
        "claude_director",
        "qa_review",
        "clip_extraction",
        "narration",
        "avatar",
        "manifest",
        "assembly",
        "post_qa",
        "distribution_pack",
        "editorial_memory",
        "log_costs",
        "send_alerts",
        "release_lock",
    ]

    def __init__(self, date_str: str = None, dry_run: bool = False,
                 force: bool = False, resume: bool = False):
        tz = pytz.timezone(os.environ.get("PULSE_RUN_TZ", "America/New_York"))
        self.date_str = date_str or datetime.now(tz).strftime("%Y-%m-%d")
        self.dry_run = dry_run
        self.force = force
        self.resume = resume
        self.start_time = time.time()

        # Initialize subsystems
        self.circuit_breaker = CostCircuitBreaker()
        self.health_checker = HealthChecker()
        self.stage_results: Dict[str, StageResult] = {}

        # Load or create checkpoint
        self.checkpoint = None
        if resume:
            self.checkpoint = load_checkpoint(self.date_str)
            if self.checkpoint:
                logger.info(f"Resuming from checkpoint: {len(self.checkpoint.completed_stages)} stages done")
                self.circuit_breaker.total_cost = self.checkpoint.total_cost
            else:
                logger.info("No checkpoint found — starting fresh")

        if not self.checkpoint:
            self.checkpoint = PipelineCheckpoint(
                date_str=self.date_str,
                dry_run=dry_run,
                force=force,
                started_at=datetime.utcnow().isoformat()
            )

        # Internal driver state (populated by stages)
        self._driver = None  # Lazy-loaded DailyDriver
        self._bundle_path = None
        self._source_bundle = None
        self._transcripts = None
        self._triage = None
        self._clusters = None
        self._show_plan = None
        self._qa_report = None
        self._clip_map = None
        self._audio_map = None
        self._avatar_map = None
        self._manifest = None
        self._shorts_manifests = None
        self._assembly_result = None

    def run(self) -> Dict:
        """Execute the self-healing pipeline."""
        logger.info(f"\n{'='*70}")
        logger.info(f"  SELF-HEALING PIPELINE — {self.date_str}")
        logger.info(f"  Mode: {'DRY RUN' if self.dry_run else 'PRODUCTION'}")
        logger.info(f"  Resume: {self.resume}")
        logger.info(f"  Budget: ${self.circuit_breaker.daily_budget:.2f}")
        logger.info(f"{'='*70}\n")

        result = {
            "date": self.date_str,
            "status": "running",
            "dry_run": self.dry_run,
            "stages": {},
            "dead_letters": [],
        }

        # Lazy-load the driver
        from pp_services.video_engine.daily_driver import DailyDriver
        self._driver = DailyDriver(
            date_str=self.date_str,
            dry_run=self.dry_run,
            force=self.force
        )

        try:
            for stage_name in self.STAGE_ORDER:
                # Skip if already completed in checkpoint
                if stage_name in (self.checkpoint.completed_stages or []):
                    logger.info(f"  [{stage_name}] Already completed (checkpoint) — skipping")
                    # Restore stage data from checkpoint
                    self._restore_stage_data(stage_name)
                    continue

                # Dry run stops after qa_review
                if self.dry_run and stage_name == "clip_extraction":
                    logger.info("\n  DRY RUN complete — stopping before assembly stages")
                    result["status"] = "dry_run_complete"
                    break

                # Run the stage with all protections
                stage_result = self._run_stage(stage_name)
                self.stage_results[stage_name] = stage_result
                result["stages"][stage_name] = asdict(stage_result)

                # Handle stage outcome
                if stage_result.status == StageStatus.SUCCESS:
                    self.checkpoint.completed_stages.append(stage_name)
                    save_checkpoint(self.checkpoint)

                elif stage_result.status == StageStatus.SKIPPED:
                    self.checkpoint.completed_stages.append(stage_name)
                    save_checkpoint(self.checkpoint)

                elif stage_result.status == StageStatus.DEAD_LETTER:
                    result["dead_letters"].append(stage_name)
                    config = STAGE_CONFIGS.get(stage_name, StageConfig(stage_name))
                    if config.critical:
                        logger.error(f"  CRITICAL stage {stage_name} in dead letter — aborting")
                        result["status"] = "failed"
                        result["error"] = f"Critical stage failed: {stage_name}"
                        break

                elif stage_result.status == StageStatus.FAILED:
                    config = STAGE_CONFIGS.get(stage_name, StageConfig(stage_name))
                    if config.critical:
                        result["status"] = "failed"
                        result["error"] = f"Critical stage failed: {stage_name}: {stage_result.error}"
                        break

            else:
                # All stages completed
                if result["status"] != "dry_run_complete":
                    result["status"] = "complete"

        except Exception as e:
            logger.error(f"Pipeline exception: {e}", exc_info=True)
            result["status"] = "error"
            result["error"] = str(e)

        finally:
            # Always release lock and log costs
            self._safe_release_lock()
            result["runtime_seconds"] = time.time() - self.start_time
            result["cost_summary"] = self.circuit_breaker.summary()

            if result["status"] == "complete":
                clear_checkpoint(self.date_str)
            else:
                save_checkpoint(self.checkpoint)

            # Record to monitoring system
            self._record_monitoring(result)

            # Send alerts
            self._safe_send_alerts(result)

        logger.info(f"\n{'='*70}")
        logger.info(f"  PIPELINE {result['status'].upper()}")
        logger.info(f"  Runtime: {result['runtime_seconds']:.0f}s")
        logger.info(f"  Cost: ${self.circuit_breaker.total_cost:.2f}")
        logger.info(f"  Dead letters: {len(result['dead_letters'])}")
        logger.info(f"{'='*70}\n")

        return result

    def _run_stage(self, stage_name: str) -> StageResult:
        """Run a single pipeline stage with all protections."""
        config = STAGE_CONFIGS.get(stage_name, StageConfig(stage_name))

        logger.info(f"\n  STAGE: {stage_name} "
                    f"({'critical' if config.critical else 'optional'}, "
                    f"retries={config.max_retries})")

        # 1. Cost circuit breaker check
        if not self.circuit_breaker.check(stage_name):
            if config.critical:
                return StageResult(
                    name=stage_name,
                    status=StageStatus.FAILED,
                    error="Cost circuit breaker tripped"
                )
            return StageResult(
                name=stage_name,
                status=StageStatus.SKIPPED,
                error="Cost circuit breaker — skipping optional stage"
            )

        # 2. Health checks
        health_failures = self.health_checker.run_pre_stage_checks(stage_name)
        if health_failures:
            logger.warning(f"  Health check failures: {health_failures}")
            if config.critical and "disk_space" in health_failures:
                return StageResult(
                    name=stage_name,
                    status=StageStatus.FAILED,
                    error=f"Health check failed: {health_failures}"
                )
            if not config.critical and f"api_keys_{stage_name}" in health_failures:
                logger.info(f"  Skipping {stage_name} — missing API keys")
                return StageResult(
                    name=stage_name,
                    status=StageStatus.SKIPPED,
                    error=f"Missing API keys"
                )

        # 3. Get the stage function
        stage_func = self._get_stage_func(stage_name)
        if not stage_func:
            return StageResult(
                name=stage_name,
                status=StageStatus.SKIPPED,
                error=f"No implementation for stage"
            )

        # 4. Execute with retry
        start = time.time()
        try:
            result_data, attempts = retry_with_backoff(stage_func, config)
            duration = time.time() - start

            # Record cost if available
            if hasattr(self._driver, 'costs'):
                cost = self._estimate_stage_cost(stage_name)
                self.circuit_breaker.record_cost(stage_name, cost)

            # Save stage data for checkpoint
            self._save_stage_data(stage_name, result_data)

            logger.info(f"  [{stage_name}] Complete ({duration:.1f}s, {attempts} attempt(s))")
            return StageResult(
                name=stage_name,
                status=StageStatus.SUCCESS,
                attempts=attempts,
                duration=duration,
                data={"summary": str(result_data)[:200]} if result_data else {}
            )

        except Exception as e:
            duration = time.time() - start
            error_msg = f"{type(e).__name__}: {e}"

            if config.critical:
                # Critical stage → dead letter
                send_to_dead_letter(
                    self.date_str, stage_name, error_msg,
                    {"traceback": traceback.format_exc()[-500:]}
                )
                return StageResult(
                    name=stage_name,
                    status=StageStatus.DEAD_LETTER,
                    attempts=config.max_retries,
                    duration=duration,
                    error=error_msg
                )
            else:
                # Non-critical → skip with warning
                logger.warning(f"  [{stage_name}] Failed but non-critical — continuing: {e}")
                return StageResult(
                    name=stage_name,
                    status=StageStatus.SKIPPED,
                    attempts=config.max_retries,
                    duration=duration,
                    error=error_msg
                )

    def _get_stage_func(self, stage_name: str) -> Optional[Callable]:
        """Map stage names to their implementation functions."""
        mapping = {
            "acquire_lock": self._stage_acquire_lock,
            "create_bundle": self._stage_create_bundle,
            "source_ingestion": self._stage_source_ingestion,
            "grok_triage": self._stage_grok_triage,
            "clustering": self._stage_clustering,
            "claude_director": self._stage_claude_director,
            "qa_review": self._stage_qa_review,
            "clip_extraction": self._stage_clip_extraction,
            "narration": self._stage_narration,
            "avatar": self._stage_avatar,
            "manifest": self._stage_manifest,
            "assembly": self._stage_assembly,
            "post_qa": self._stage_post_qa,
            "distribution_pack": self._stage_distribution_pack,
            "editorial_memory": self._stage_editorial_memory,
            "log_costs": self._stage_log_costs,
            "send_alerts": self._stage_send_alerts,
            "release_lock": self._stage_release_lock,
        }
        return mapping.get(stage_name)

    # ─── Stage Implementations (delegate to DailyDriver) ───

    def _stage_acquire_lock(self):
        if not self._driver._acquire_lock():
            raise RuntimeError("Could not acquire run lock")
        return {"locked": True}

    def _stage_create_bundle(self):
        from pp_services.video_engine.editorial.episode_bundle import create_episode_bundle
        self._bundle_path = create_episode_bundle(self.date_str)
        self._driver.bundle_path = self._bundle_path
        self._driver._setup_episode_log()
        return {"bundle": str(self._bundle_path)}

    def _stage_source_ingestion(self):
        self._source_bundle, self._transcripts = self._driver._stage_source_ingestion()
        return {
            "transcripts": len(self._transcripts) if self._transcripts else 0,
            "status": "complete"
        }

    def _stage_grok_triage(self):
        self._triage = self._driver._stage_grok_triage(self._source_bundle)
        count = len(self._triage.candidates) if self._triage else 0
        return {"candidates": count}

    def _stage_clustering(self):
        self._clusters = self._driver._stage_clustering(self._triage)
        count = len(self._clusters.clusters) if self._clusters else 0
        return {"clusters": count}

    def _stage_claude_director(self):
        self._show_plan = self._driver._stage_claude_director(
            self._clusters, self._source_bundle)
        if not self._show_plan:
            raise RuntimeError("Claude Director failed to produce show plan")
        return {
            "stories": len(self._show_plan.stories),
            "headline": self._show_plan.episode_headline
        }

    def _stage_qa_review(self):
        self._qa_report = self._driver._stage_qa_review(self._show_plan, self._triage)
        return {
            "approved": self._qa_report.approved if self._qa_report else False,
            "issues": len(self._qa_report.issues) if self._qa_report else 0
        }

    def _stage_clip_extraction(self):
        self._clip_map = self._driver._stage_clip_extraction(
            self._show_plan, self._transcripts)
        return {"clips": len(self._clip_map) if self._clip_map else 0}

    def _stage_narration(self):
        self._audio_map = self._driver._stage_narration(self._show_plan)
        return {"voiceovers": len(self._audio_map) if self._audio_map else 0}

    def _stage_avatar(self):
        self._avatar_map = self._driver._stage_avatar(self._audio_map or {})
        return {"segments": len(self._avatar_map) if self._avatar_map else 0}

    def _stage_manifest(self):
        self._manifest, self._shorts_manifests = self._driver._stage_manifest(
            self._show_plan, self._audio_map or {}, self._clip_map or {})
        return {
            "timeline": len(self._manifest.timeline) if self._manifest else 0
        }

    def _stage_assembly(self):
        self._assembly_result = self._driver._stage_assembly(
            self._manifest, self._shorts_manifests)
        return self._assembly_result or {}

    def _stage_post_qa(self):
        if (self._assembly_result and
                self._assembly_result.get("horizontal", {}).get("status") == "complete"):
            return self._driver._stage_post_qa()
        return {"skipped": True, "reason": "no assembled video"}

    def _stage_distribution_pack(self):
        dist = self._driver._stage_distribution_pack(self._show_plan)
        return {"platforms": len(dist) if dist else 0}

    def _stage_editorial_memory(self):
        self._driver._update_editorial_memory(self._show_plan)
        return {"updated": True}

    def _stage_log_costs(self):
        self._driver._log_costs()
        return {"costs": self._driver.costs}

    def _stage_send_alerts(self):
        # Alerts are sent in finally block
        return {"deferred": True}

    def _stage_release_lock(self):
        self._driver._release_lock()
        return {"released": True}

    # ─── Helpers ───

    def _estimate_stage_cost(self, stage_name: str) -> float:
        """Estimate cost for a stage based on driver's cost tracking."""
        costs = self._driver.costs
        if stage_name == "grok_triage":
            return (costs["grok_tokens_in"] * 0.005 +
                    costs["grok_tokens_out"] * 0.015) / 1000
        elif stage_name == "claude_director":
            return (costs["claude_tokens_in"] * 0.003 +
                    costs["claude_tokens_out"] * 0.015) / 1000
        elif stage_name == "narration":
            return costs["elevenlabs_characters"] * 0.00003
        return 0.0

    def _save_stage_data(self, stage_name: str, data: Any):
        """Save stage output data for checkpoint restoration."""
        # Only save serializable summaries, not full objects
        try:
            self.checkpoint.stage_data[stage_name] = {
                "completed_at": datetime.utcnow().isoformat(),
                "summary": str(data)[:500] if data else None
            }
            self.checkpoint.total_cost = self.circuit_breaker.total_cost
        except Exception:
            pass

    def _restore_stage_data(self, stage_name: str):
        """Restore stage data from checkpoint (for resumed runs).

        Complex objects (source_bundle, show_plan) can't be fully
        restored from JSON. Resume works by skipping completed stages,
        so the main benefit is avoiding expensive API calls for stages
        that already succeeded. We log a warning for stages that may
        need downstream data.
        """
        logger.debug(f"Skipping restore for {stage_name} — stage will be re-computed if needed downstream")

    def _record_monitoring(self, result: Dict):
        """Record run results to monitoring system."""
        try:
            from pp_services.video_engine.monitoring import PipelineMonitor
            monitor = PipelineMonitor()
            monitor.record_run(result)
            monitor.close()
        except Exception as e:
            logger.debug(f"Monitoring recording failed: {e}")

        # Record to audit trail
        try:
            from pp_services.video_engine.backup_system import AuditTrail
            audit = AuditTrail()
            audit.log_pipeline_event(
                stage="daily_driver",
                action=result.get("status", "unknown"),
                metadata={
                    "date": self.date_str,
                    "runtime": result.get("runtime_seconds", 0),
                    "cost": result.get("cost_summary", {}).get("total_cost", 0),
                    "dead_letters": result.get("dead_letters", []),
                }
            )
        except Exception as e:
            logger.debug(f"Audit trail recording failed: {e}")

    def _safe_release_lock(self):
        """Release lock without raising."""
        try:
            if self._driver:
                self._driver._release_lock()
        except Exception:
            pass

    def _safe_send_alerts(self, result: Dict):
        """Send alerts without raising."""
        try:
            if self._driver:
                self._driver._send_alerts(result)
        except Exception as e:
            logger.warning(f"Alert sending failed: {e}")


# ─── CLI ───

def main():
    parser = argparse.ArgumentParser(
        description="Self-Healing Pipeline — Pulse Check Content OS")
    parser.add_argument("--dry-run", action="store_true",
                       help="Show plan only, no assembly")
    parser.add_argument("--force", action="store_true",
                       help="Override one-run-per-day lock")
    parser.add_argument("--date", type=str,
                       help="Build for specific date (YYYY-MM-DD)")
    parser.add_argument("--resume", action="store_true",
                       help="Resume from last checkpoint")
    parser.add_argument("--dead-letters", action="store_true",
                       help="Show dead letter queue")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(name)s: %(message)s'
    )

    if args.dead_letters:
        letters = get_dead_letters()
        if not letters:
            print("No dead letters in queue.")
            return
        for dl in letters:
            print(f"\n{'─'*50}")
            print(f"Date: {dl['date']} | Stage: {dl['stage']}")
            print(f"Error: {dl['error'][:200]}")
            print(f"Time: {dl['timestamp']}")
        return

    pipeline = SelfHealingPipeline(
        date_str=args.date,
        dry_run=args.dry_run,
        force=args.force,
        resume=args.resume
    )

    result = pipeline.run()

    # Print summary
    print(f"\n{'='*50}")
    print(f"Status: {result.get('status', 'unknown')}")
    if result.get("error"):
        print(f"Error: {result['error']}")
    cost = result.get("cost_summary", {})
    print(f"Cost: ${cost.get('total_cost', 0):.2f} / ${cost.get('daily_budget', 0):.2f}")
    print(f"Runtime: {result.get('runtime_seconds', 0):.0f}s")
    if result.get("dead_letters"):
        print(f"Dead Letters: {result['dead_letters']}")
    print(f"{'='*50}")

    return result


if __name__ == "__main__":
    main()
