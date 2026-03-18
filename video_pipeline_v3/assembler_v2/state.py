"""Episode-scoped state. No module globals anywhere."""

from dataclasses import dataclass, field
from pathlib import Path
import uuid, os, time, logging

logger = logging.getLogger(__name__)


@dataclass
class EpisodeContext:
    episode_id: str
    date_str: str
    workdir: Path

    # Per-episode SFX dedup — never a global
    whoosh_applied: set = field(default_factory=set)

    # Segment tracking
    segments_rendered: list = field(default_factory=list)
    degraded_count: int = 0
    total_filler_seconds: float = 0.0

    # Sponsor tracking
    sponsor_reads_done: list = field(default_factory=list)

    # Runtime metrics
    started_at: float = field(default_factory=time.time)

    @classmethod
    def create(cls, date_str: str, base_output_dir: Path) -> "EpisodeContext":
        episode_id = str(uuid.uuid4())[:8]
        workdir = base_output_dir / date_str
        workdir.mkdir(parents=True, exist_ok=True)
        (workdir / "segments").mkdir(exist_ok=True)
        (workdir / "logs").mkdir(exist_ok=True)
        logger.info(f"[state] Episode {episode_id} workdir: {workdir}")
        return cls(episode_id=episode_id, date_str=date_str, workdir=workdir)

    def mark_whoosh_applied(self, path: Path):
        self.whoosh_applied.add(str(path.resolve()))

    def whoosh_was_applied(self, path: Path) -> bool:
        return str(path.resolve()) in self.whoosh_applied

    def mark_degraded(self, reason: str, filler_seconds: float = 0.0):
        self.degraded_count += 1
        self.total_filler_seconds += filler_seconds
        logger.warning(f"[state] DEGRADED segment #{self.degraded_count}: {reason} ({filler_seconds:.1f}s filler)")

    def elapsed_seconds(self) -> float:
        return time.time() - self.started_at

    def verdict(self) -> str:
        from .constants import QC_MAX_FILLER_SECONDS, QC_MAX_DEGRADED_SEGMENTS
        if self.total_filler_seconds >= QC_MAX_FILLER_SECONDS:
            return "HOLD"
        if self.degraded_count > QC_MAX_DEGRADED_SEGMENTS:
            return "DEGRADED"
        return "PASS"
