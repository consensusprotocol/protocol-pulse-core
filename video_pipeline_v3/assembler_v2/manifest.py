"""Episode manifest and segment spec dataclasses. This is the source of truth."""

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional
import json, uuid, time


@dataclass
class SegmentSpec:
    segment_type: str           # cold_open|narration|partner_clip|transition|data|social|signal_active|wrap
    clip_rank: int = 0          # which partner clip this relates to (0 = none)
    tts_path: Optional[Path] = None     # ElevenLabs m4a — must be non-zero if segment has narration
    clip_path: Optional[Path] = None   # partner clip mp4
    pip_path: Optional[Path] = None    # pre-normalized pip_preview_norm_{rank}.mp4
    headline: str = ""
    body: str = ""
    chart_keyword: str = ""     # "price"|"hashrate"|"mempool"|"" for data segment
    social_posts: list = field(default_factory=list)
    signal_content: dict = field(default_factory=dict)
    is_required: bool = False   # if True, filler still marks episode DEGRADED
    duration_hint: float = 0.0  # populated from ffprobe(tts_path) during manifest build


@dataclass
class RenderedSegment:
    spec: SegmentSpec
    path: Optional[Path] = None
    duration: float = 0.0
    contract_passed: bool = False
    degraded: bool = False      # True if filler was used
    render_ms: int = 0
    ffprobe_summary: dict = field(default_factory=dict)
    error: str = ""


@dataclass
class EpisodeManifest:
    episode_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    date_str: str = ""          # YYYYMMDD
    title: str = ""
    segments: list[SegmentSpec] = field(default_factory=list)
    btc_price: str = "N/A"
    created_at: float = field(default_factory=time.time)

    def to_json(self) -> str:
        d = asdict(self)
        # Convert Path objects to strings
        def fix(obj):
            if isinstance(obj, dict): return {k: fix(v) for k, v in obj.items()}
            if isinstance(obj, list): return [fix(i) for i in obj]
            if isinstance(obj, Path): return str(obj)
            return obj
        return json.dumps(fix(d), indent=2)

    @classmethod
    def from_json(cls, path: Path) -> "EpisodeManifest":
        d = json.loads(path.read_text())
        d["segments"] = [SegmentSpec(**s) for s in d["segments"]]
        return cls(**d)

    def save(self, path: Path):
        path.write_text(self.to_json())
