"""
Protocol Pulse V2 — manifest.py
Episode manifest and segment spec dataclasses.
The manifest is the single source of truth for every episode.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional
import json, uuid, time, os


@dataclass
class SegmentSpec:
    """Complete specification for one segment. Passed to segment.render()."""
    segment_type: str           # cold_open|narration|partner_clip|transition|data|social|signal_active|wrap
    clip_rank: int = 0          # partner clip rank (0 = no clip)
    tts_path: Optional[str] = None      # absolute path to ElevenLabs m4a
    clip_path: Optional[str] = None     # absolute path to partner clip mp4
    pip_path: Optional[str] = None      # absolute path to pip_preview_norm_{rank}.mp4
    headline: str = ""
    body: str = ""
    chart_keyword: str = ""     # "price"|"hashrate"|"mempool"|""
    social_posts: list = field(default_factory=list)
    signal_content: dict = field(default_factory=dict)
    is_required: bool = False   # filler still marks episode DEGRADED if True
    duration_hint: float = 0.0  # from ffprobe(tts_path)
    btc_price: str = "N/A"

    def tts(self) -> Optional[Path]:
        return Path(self.tts_path) if self.tts_path else None

    def clip(self) -> Optional[Path]:
        return Path(self.clip_path) if self.clip_path else None

    def pip(self) -> Optional[Path]:
        return Path(self.pip_path) if self.pip_path else None


@dataclass
class RenderedSegment:
    """Result of segment.render(). Always populated — degraded=True if filler used."""
    spec: SegmentSpec
    path: Optional[str] = None          # absolute path to rendered mp4
    duration: float = 0.0
    contract_passed: bool = False
    degraded: bool = False
    render_ms: int = 0
    ffprobe_summary: dict = field(default_factory=dict)
    error: str = ""

    def output(self) -> Optional[Path]:
        return Path(self.path) if self.path else None


@dataclass
class EpisodeManifest:
    """Complete episode plan. Written before any ffmpeg is called."""
    episode_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    date_str: str = ""
    title: str = ""
    cold_open: str = ""
    segments: list = field(default_factory=list)  # list of SegmentSpec
    btc_price: str = "N/A"
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        d = asdict(self)
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, default=str)

    def save(self, path: Path):
        tmp = path.with_suffix('.tmp')
        tmp.write_text(self.to_json())
        os.replace(str(tmp), str(path))
        return path

    @classmethod
    def from_json(cls, path: Path) -> "EpisodeManifest":
        d = json.loads(path.read_text())
        d["segments"] = [SegmentSpec(**s) for s in d.get("segments", [])]
        return cls(**d)

    def validate(self):
        if not self.segments:
            raise ValueError(f"EpisodeManifest {self.episode_id} has no segments")
        return self

    def segment_count(self) -> int:
        return len(self.segments)

    def narration_segments(self) -> list:
        return [s for s in self.segments if s.segment_type in ("narration", "cold_open")]
