from __future__ import annotations
from abc import ABC, abstractmethod
from pathlib import Path
import logging
from ..manifest import SegmentSpec, RenderedSegment
from ..state import EpisodeContext
from ..helpers import ffprobe_duration, make_filler
logger = logging.getLogger(__name__)

class Segment(ABC):
    criticality: str = 'optional'

    @abstractmethod
    def render(self, spec: SegmentSpec, ctx: EpisodeContext, output_path: Path, idx: int) -> RenderedSegment:
        ...

    def validate(self, spec: SegmentSpec) -> tuple:
        if spec.tts_path and not Path(spec.tts_path).exists():
            return False, f'TTS missing: {spec.tts_path}'
        return True, ''

    def get_duration(self, spec: SegmentSpec) -> float:
        if spec.duration_hint and spec.duration_hint > 0:
            return spec.duration_hint
        if spec.tts_path:
            p = Path(spec.tts_path)
            if p.exists():
                d = ffprobe_duration(p)
                if d > 0: return d
        return 15.0

    def filler_result(self, spec: SegmentSpec, ctx: EpisodeContext,
                      output_path: Path, reason: str) -> RenderedSegment:
        dur = self.get_duration(spec)
        tts = Path(spec.tts_path) if spec.tts_path else None
        ok = make_filler(output_path, dur, tts)
        if not ok or not output_path.exists() or output_path.stat().st_size < 1000:
            # Emergency: write static black+silent as last resort
            logger.error(f"[base] make_filler failed for {reason} — emergency black")
            try:
                from ..helpers import run_ffmpeg
                run_ffmpeg([
                    "-f", "lavfi", "-i",
                    f"color=c=black:s=1920x1080:r=30,format=yuv420p",
                    "-f", "lavfi", "-i",
                    "anullsrc=r=48000:cl=stereo",
                    "-c:v", "libx264", "-crf", "17", "-preset", "ultrafast",
                    "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
                    "-t", str(max(dur, 1.0)),
                    "-movflags", "+faststart", str(output_path)
                ], f"emergency filler {reason}", 30)
                ok = output_path.exists() and output_path.stat().st_size > 1000
            except Exception as ex:
                logger.error(f"[base] emergency filler also failed: {ex}")
                ok = False
        ctx.mark_degraded(spec.segment_type, reason, dur)
        actual = ffprobe_duration(output_path) if ok and output_path.exists() else dur
        return RenderedSegment(spec=spec, path=str(output_path) if ok else None,
                               duration=actual, contract_passed=ok,
                               degraded=True, error=reason)
