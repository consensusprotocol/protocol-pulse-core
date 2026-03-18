"""
Protocol Pulse V2 — state.py
Episode-scoped state object. NO module-level globals anywhere.
EpisodeContext is passed as a parameter to every function that needs state.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import uuid, time, logging

logger = logging.getLogger(__name__)


@dataclass
class EpisodeContext:
    """
    All mutable state for one episode render.
    Created once in episode.py, passed everywhere as ctx.
    Never stored as a module-level global.
    """
    episode_id: str
    date_str: str
    workdir: Path

    # SFX dedup — episode-scoped, not global
    whoosh_applied: set = field(default_factory=set)

    # Segment tracking
    segments_rendered: list = field(default_factory=list)
    degraded_count: int = 0
    total_filler_seconds: float = 0.0

    # Sponsor tracking
    sponsor_reads_done: list = field(default_factory=list)

    # Runtime
    started_at: float = field(default_factory=time.time)

    @classmethod
    def create(cls, date_str: str, base_output_dir: Path) -> "EpisodeContext":
        """Factory method. Creates workdir structure."""
        episode_id = str(uuid.uuid4())[:8]
        workdir = base_output_dir / f"{date_str}_{episode_id}"
        workdir.mkdir(parents=True, exist_ok=True)
        (workdir / "segments").mkdir(exist_ok=True)
        (workdir / "logs").mkdir(exist_ok=True)
        (workdir / "reports").mkdir(exist_ok=True)
        logger.info(f"[ctx] Episode {episode_id} | workdir: {workdir}")
        return cls(episode_id=episode_id, date_str=date_str, workdir=workdir)

    # ── Whoosh dedup ────────────────────────────────────────────────
    def mark_whoosh(self, path: Path):
        self.whoosh_applied.add(str(path.resolve()))

    def has_whoosh(self, path: Path) -> bool:
        return str(path.resolve()) in self.whoosh_applied

    # ── Degraded tracking ────────────────────────────────────────────
    def mark_degraded(self, segment_type: str, reason: str, filler_sec: float = 0.0):
        self.degraded_count += 1
        self.total_filler_seconds += filler_sec
        logger.warning(
            f"[ctx] DEGRADED #{self.degraded_count} | {segment_type} | {reason} | "
            f"+{filler_sec:.1f}s filler | total_filler={self.total_filler_seconds:.1f}s"
        )

    # ── Verdict ─────────────────────────────────────────────────────
    def verdict(self) -> str:
        """PASS | DEGRADED | HOLD
        Intentional ordering: HOLD is checked before DEGRADED so that
        episodes with excessive filler are held regardless of degraded count.
        HOLD is the strictest gate — it supersedes DEGRADED.
        """
        from .constants import QC_MAX_FILLER_SECONDS, QC_MAX_DEGRADED_SEGMENTS
        if self.total_filler_seconds >= QC_MAX_FILLER_SECONDS:
            return "HOLD"
        if self.degraded_count > QC_MAX_DEGRADED_SEGMENTS:
            return "DEGRADED"
        return "PASS"

    def elapsed(self) -> float:
        return time.time() - self.started_at

    def segment_dir(self) -> Path:
        return self.workdir / "segments"

    def log_dir(self) -> Path:
        return self.workdir / "logs"

    def report_dir(self) -> Path:
        return self.workdir / "reports"

    def summary(self) -> dict:
        return {
            "episode_id": self.episode_id,
            "date_str": self.date_str,
            "segments_rendered": len(self.segments_rendered),
            "degraded_count": self.degraded_count,
            "total_filler_seconds": self.total_filler_seconds,
            "verdict": self.verdict(),
            "elapsed_seconds": round(self.elapsed(), 1),
        }
