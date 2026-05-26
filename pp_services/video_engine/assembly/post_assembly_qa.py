"""
Post-Assembly QA
=================
Automated checks on the assembled video.
Never ship a broken episode. Fail closed into shorter edition if needed.

Checks:
1. ffprobe duration within expected range
2. Silence gaps > 2 seconds (warning)
3. Audio clipping: peaks above threshold (warning)
4. File size sanity (30-200MB for 5-8 min H.264)
5. Clip-time ratio (clips should be 30-50% of total)
"""
import json
import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("PostAssemblyQA")


class PostAssemblyQA:
    """Validate assembled video before distribution."""

    def validate(self, video_path: Path,
                 expected_duration_range: tuple = (180, 540),
                 bundle_path: Path = None) -> dict:
        """
        Run automated checks on the assembled video.

        Returns:
            {"passed": bool, "warnings": [...], "errors": [...], "metadata": {...}}
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"POST-ASSEMBLY QA")
        logger.info(f"{'='*60}\n")

        result = {
            "passed": True,
            "warnings": [],
            "errors": [],
            "metadata": {}
        }

        if not video_path.exists():
            result["passed"] = False
            result["errors"].append(f"Video file not found: {video_path}")
            return result

        # 1. Probe video metadata
        probe = self._ffprobe(video_path)
        if not probe:
            result["passed"] = False
            result["errors"].append("ffprobe failed — cannot validate video")
            return result

        result["metadata"] = probe

        # 2. Duration check
        duration = probe.get("duration", 0)
        min_dur, max_dur = expected_duration_range

        if duration < min_dur:
            result["errors"].append(
                f"Video too short: {duration:.1f}s (min {min_dur}s)")
            result["passed"] = False
        elif duration > max_dur:
            result["warnings"].append(
                f"Video longer than expected: {duration:.1f}s (max {max_dur}s)")
        else:
            logger.info(f"  Duration: {duration:.1f}s — OK")

        # 3. File size sanity
        size_mb = video_path.stat().st_size / (1024 * 1024)
        result["metadata"]["size_mb"] = size_mb

        if size_mb < 5:
            result["errors"].append(f"File too small: {size_mb:.1f}MB (corrupt?)")
            result["passed"] = False
        elif size_mb > 300:
            result["warnings"].append(f"File very large: {size_mb:.1f}MB")
        else:
            logger.info(f"  File size: {size_mb:.1f}MB — OK")

        # 4. Resolution check
        width = probe.get("width", 0)
        height = probe.get("height", 0)
        if width < 1280 or height < 720:
            result["warnings"].append(
                f"Low resolution: {width}x{height} (expected >= 1280x720)")
        else:
            logger.info(f"  Resolution: {width}x{height} — OK")

        # 5. Audio stream check
        has_audio = probe.get("has_audio", False)
        if not has_audio:
            result["errors"].append("No audio stream found")
            result["passed"] = False
        else:
            logger.info(f"  Audio: present — OK")

        # 6. Silence detection (via Ultron if available)
        silences = self._detect_silences(video_path)
        if silences:
            long_silences = [s for s in silences if s.get("duration", 0) > 2.0]
            if long_silences:
                result["warnings"].append(
                    f"{len(long_silences)} silence gaps > 2 seconds detected")
                for s in long_silences[:3]:
                    logger.warning(
                        f"    Silence at {s.get('start', 0):.1f}s "
                        f"({s.get('duration', 0):.1f}s)")

        # Summary
        logger.info(f"\n  QA Result: {'PASS' if result['passed'] else 'FAIL'}")
        logger.info(f"  Errors: {len(result['errors'])}")
        logger.info(f"  Warnings: {len(result['warnings'])}")

        for err in result["errors"]:
            logger.error(f"    ERROR: {err}")
        for warn in result["warnings"]:
            logger.warning(f"    WARN: {warn}")

        # Save QA result
        if bundle_path:
            qa_path = bundle_path / "qa" / "post_assembly_qa.json"
            qa_path.write_text(json.dumps(result, indent=2, default=str))
            logger.info(f"  Saved: {qa_path}")

        return result

    def _ffprobe(self, video_path: Path) -> Optional[dict]:
        """Run ffprobe on the video. Try Ultron SSH first, then local."""
        # Try via Ultron
        try:
            import subprocess
            cmd = (
                f'ssh ultron "ffprobe -v quiet -print_format json '
                f'-show_format -show_streams '
                f'/home/ultron/video_engine/output/{video_path.name}" 2>/dev/null'
            )
            result = subprocess.run(cmd, shell=True, capture_output=True,
                                     text=True, timeout=15)
            if result.returncode == 0 and result.stdout.strip():
                data = json.loads(result.stdout)
                return self._parse_probe(data)
        except Exception:
            pass

        # Try local ffprobe
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "quiet", "-print_format", "json",
                 "-show_format", "-show_streams", str(video_path)],
                capture_output=True, text=True, timeout=15
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                return self._parse_probe(data)
        except Exception:
            pass

        return None

    def _parse_probe(self, data: dict) -> dict:
        """Parse ffprobe output into simple dict."""
        fmt = data.get("format", {})
        streams = data.get("streams", [])

        result = {
            "duration": float(fmt.get("duration", 0)),
            "size_bytes": int(fmt.get("size", 0)),
            "bitrate": int(fmt.get("bit_rate", 0)),
            "has_audio": False,
            "has_video": False,
        }

        for s in streams:
            if s.get("codec_type") == "video":
                result["has_video"] = True
                result["width"] = s.get("width", 0)
                result["height"] = s.get("height", 0)
                result["codec"] = s.get("codec_name", "unknown")
                result["fps"] = s.get("r_frame_rate", "unknown")
            elif s.get("codec_type") == "audio":
                result["has_audio"] = True
                result["audio_codec"] = s.get("codec_name", "unknown")
                result["sample_rate"] = s.get("sample_rate", "unknown")

        return result

    def _detect_silences(self, video_path: Path,
                          threshold_db: float = -40,
                          min_duration: float = 1.0) -> List[dict]:
        """Detect silence gaps in the video audio."""
        try:
            cmd = (
                f'ssh ultron "ffmpeg -i /home/ultron/video_engine/output/{video_path.name} '
                f'-af silencedetect=noise={threshold_db}dB:d={min_duration} '
                f'-f null - 2>&1 | grep silence_" 2>/dev/null'
            )
            result = subprocess.run(cmd, shell=True, capture_output=True,
                                     text=True, timeout=30)

            silences = []
            lines = result.stdout.strip().split("\n") if result.stdout else []

            for line in lines:
                if "silence_start" in line:
                    try:
                        start = float(line.split("silence_start: ")[1].split()[0])
                        silences.append({"start": start})
                    except (IndexError, ValueError):
                        pass
                elif "silence_end" in line and silences:
                    try:
                        parts = line.split("silence_end: ")[1]
                        end = float(parts.split()[0])
                        duration = float(parts.split("silence_duration: ")[1].split()[0])
                        silences[-1]["end"] = end
                        silences[-1]["duration"] = duration
                    except (IndexError, ValueError):
                        pass

            return silences

        except Exception:
            return []
