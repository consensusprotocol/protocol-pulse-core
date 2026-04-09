#!/usr/bin/env python3
"""
Hook Forensic Analysis — Cypherpunk'd Editing DNA Extraction
Analyzes cut timing, audio energy, pacing patterns from first 2 minutes
of Cypherpunk'd episodes + cinematic intros.
"""

import json
import os
import re
import subprocess
import sys
import statistics
from pathlib import Path
from datetime import datetime

# --- Config ---
RAW_DIR = Path("/home/ultron/protocol_pulse/data/hook_analysis/raw")
RESULTS_DIR = Path("/home/ultron/protocol_pulse/data/hook_analysis/results")
FRAMES_DIR = RESULTS_DIR / "frames"
RESULTS_JSON = RESULTS_DIR / "forensic_results.json"
DNA_MD = Path("/home/ultron/protocol_pulse/docs/HOOK_EDITING_DNA.md")

FRAMES_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
DNA_MD.parent.mkdir(parents=True, exist_ok=True)


def get_duration(filepath: str) -> float:
    """Get video duration in seconds via ffprobe."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "csv=p=0", filepath
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def get_video_info(filepath: str) -> dict:
    """Get resolution, fps, bitrate."""
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,r_frame_rate,bit_rate",
        "-of", "json", filepath
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    try:
        streams = json.loads(r.stdout).get("streams", [{}])
        s = streams[0] if streams else {}
        fps_str = s.get("r_frame_rate", "30/1")
        parts = fps_str.split("/")
        fps = float(parts[0]) / float(parts[1]) if len(parts) == 2 and float(parts[1]) > 0 else 30.0
        return {
            "width": s.get("width", 0),
            "height": s.get("height", 0),
            "fps": round(fps, 2),
            "bitrate_kbps": int(s.get("bit_rate", 0)) // 1000 if s.get("bit_rate") else None
        }
    except (json.JSONDecodeError, IndexError, KeyError):
        return {"width": 0, "height": 0, "fps": 30.0, "bitrate_kbps": None}


def detect_scenes(filepath: str, threshold: float = 27.0) -> list:
    """Use PySceneDetect ContentDetector to find cut points."""
    try:
        from scenedetect import open_video, SceneManager
        from scenedetect.detectors import ContentDetector

        video = open_video(filepath)
        sm = SceneManager()
        sm.add_detector(ContentDetector(threshold=threshold))
        sm.detect_scenes(video, show_progress=False)
        scene_list = sm.get_scene_list()

        scenes = []
        for start, end in scene_list:
            scenes.append({
                "start": start.get_seconds(),
                "end": end.get_seconds(),
                "duration": end.get_seconds() - start.get_seconds()
            })
        return scenes
    except Exception as e:
        print(f"  Scene detection error: {e}", file=sys.stderr)
        return []


def analyze_audio_energy(filepath: str) -> list:
    """Extract per-second RMS audio levels via ffprobe astats."""
    cmd = [
        "ffprobe", "-f", "lavfi",
        "-i", f"amovie={filepath},astats=metadata=1:reset=1",
        "-show_entries", "frame_tags=lavfi.astats.Overall.RMS_level",
        "-of", "csv=p=0",
        "-v", "error"
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

    levels = []
    for line in r.stdout.strip().split("\n"):
        line = line.strip()
        if not line or line == "-inf":
            levels.append(-100.0)
        else:
            try:
                levels.append(float(line))
            except ValueError:
                levels.append(-100.0)
    return levels


def extract_first_10s_frames(filepath: str, video_id: str) -> int:
    """Extract 1 frame per second for first 10s (at 30fps, every 30th frame)."""
    out_dir = FRAMES_DIR / video_id
    out_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg", "-i", filepath,
        "-t", "10",
        "-vf", "fps=1",
        "-vsync", "vfr",
        "-frames:v", "10",
        f"{out_dir}/frame_%03d.png",
        "-y"
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    return len(list(out_dir.glob("*.png")))


def compute_pacing_metrics(scenes: list, duration: float) -> dict:
    """Compute pacing statistics from scene list."""
    if not scenes:
        return {
            "time_to_first_cut": duration,
            "avg_segment_duration": duration,
            "median_segment_duration": duration,
            "cuts_per_minute": 0.0,
            "shortest_segment": duration,
            "longest_segment": duration,
            "total_segments": 1,
            "total_cuts": 0,
            "segment_durations": [duration]
        }

    durations = [s["duration"] for s in scenes]
    first_cut = scenes[0]["end"] if scenes else duration
    cuts = len(scenes) - 1 if len(scenes) > 1 else len(scenes)
    minutes = duration / 60.0 if duration > 0 else 1.0

    return {
        "time_to_first_cut": round(scenes[0]["duration"], 3) if scenes else duration,
        "avg_segment_duration": round(statistics.mean(durations), 3),
        "median_segment_duration": round(statistics.median(durations), 3),
        "cuts_per_minute": round(len(durations) / minutes, 2),
        "shortest_segment": round(min(durations), 3),
        "longest_segment": round(max(durations), 3),
        "total_segments": len(scenes),
        "total_cuts": max(0, len(scenes) - 1),
        "segment_durations": [round(d, 3) for d in durations]
    }


def compute_audio_cut_correlation(scenes: list, audio_levels: list) -> dict:
    """Check if audio peaks align with cuts (bass-hit-on-cut pattern)."""
    if not scenes or len(scenes) < 2 or len(audio_levels) < 2:
        return {"correlation": 0.0, "aligned_cuts": 0, "total_cuts": 0, "alignment_pct": 0.0}

    # Get cut timestamps (transition points between scenes)
    cut_times = [s["start"] for s in scenes[1:]]  # skip first scene start

    # For each cut, check if there's an audio peak within 0.5s
    aligned = 0
    peak_threshold = -20.0  # dB — anything above this is a "peak"

    # Find all audio peak moments (local maxima above threshold)
    peak_seconds = set()
    for i, level in enumerate(audio_levels):
        if level > peak_threshold:
            peak_seconds.add(i)

    for cut_time in cut_times:
        cut_sec = int(cut_time)
        # Check if audio peak within 1 second window of cut
        if cut_sec in peak_seconds or (cut_sec - 1) in peak_seconds or (cut_sec + 1) in peak_seconds:
            aligned += 1

    total = len(cut_times)
    return {
        "correlation": round(aligned / total, 3) if total > 0 else 0.0,
        "aligned_cuts": aligned,
        "total_cuts": total,
        "alignment_pct": round(100 * aligned / total, 1) if total > 0 else 0.0
    }


def analyze_audio_dynamics(audio_levels: list) -> dict:
    """Compute audio dynamics summary."""
    valid = [l for l in audio_levels if l > -100.0]
    if not valid:
        return {"mean_rms": -100.0, "max_rms": -100.0, "min_rms": -100.0, "dynamic_range": 0.0}
    return {
        "mean_rms": round(statistics.mean(valid), 2),
        "max_rms": round(max(valid), 2),
        "min_rms": round(min(valid), 2),
        "dynamic_range": round(max(valid) - min(valid), 2),
        "samples": len(valid)
    }


def analyze_one_video(filepath: str, video_id: str) -> dict:
    """Full forensic analysis of a single video."""
    print(f"\n  Analyzing: {video_id}")

    duration = get_duration(filepath)
    info = get_video_info(filepath)
    print(f"    Duration: {duration:.1f}s | {info['width']}x{info['height']} @ {info['fps']}fps")

    print(f"    Scene detection...")
    scenes = detect_scenes(filepath, threshold=27.0)
    print(f"    Found {len(scenes)} scenes")

    print(f"    Audio energy analysis...")
    audio_levels = analyze_audio_energy(filepath)
    print(f"    Got {len(audio_levels)} audio samples")

    pacing = compute_pacing_metrics(scenes, duration)
    audio_cut_corr = compute_audio_cut_correlation(scenes, audio_levels)
    audio_dynamics = analyze_audio_dynamics(audio_levels)

    print(f"    Frame extraction (first 10s)...")
    frame_count = extract_first_10s_frames(filepath, video_id)
    print(f"    Extracted {frame_count} frames")

    return {
        "video_id": video_id,
        "filepath": filepath,
        "duration": round(duration, 3),
        "video_info": info,
        "scenes": scenes,
        "pacing": pacing,
        "audio_levels_summary": audio_dynamics,
        "audio_cut_correlation": audio_cut_corr,
        "frames_extracted": frame_count
    }


def compute_aggregate(results: list) -> dict:
    """Cross-video aggregate statistics."""
    # Separate episodes from intros
    episodes = [r for r in results if not r["video_id"].startswith("cypherpunkd_intro")]
    intros = [r for r in results if r["video_id"].startswith("cypherpunkd_intro")]

    def agg_pacing(subset):
        if not subset:
            return {}
        first_cuts = [r["pacing"]["time_to_first_cut"] for r in subset]
        avg_segs = [r["pacing"]["avg_segment_duration"] for r in subset]
        med_segs = [r["pacing"]["median_segment_duration"] for r in subset]
        cpm = [r["pacing"]["cuts_per_minute"] for r in subset]
        shortest = [r["pacing"]["shortest_segment"] for r in subset]
        longest = [r["pacing"]["longest_segment"] for r in subset]

        # Flatten all segment durations for histogram
        all_durations = []
        for r in subset:
            all_durations.extend(r["pacing"]["segment_durations"])

        # Duration histogram buckets
        buckets = {"<0.5s": 0, "0.5-1s": 0, "1-2s": 0, "2-3s": 0, "3-5s": 0, "5-10s": 0, "10-20s": 0, "20s+": 0}
        for d in all_durations:
            if d < 0.5:
                buckets["<0.5s"] += 1
            elif d < 1.0:
                buckets["0.5-1s"] += 1
            elif d < 2.0:
                buckets["1-2s"] += 1
            elif d < 3.0:
                buckets["2-3s"] += 1
            elif d < 5.0:
                buckets["3-5s"] += 1
            elif d < 10.0:
                buckets["5-10s"] += 1
            elif d < 20.0:
                buckets["10-20s"] += 1
            else:
                buckets["20s+"] += 1

        return {
            "first_cut_timing": {
                "mean": round(statistics.mean(first_cuts), 3),
                "median": round(statistics.median(first_cuts), 3),
                "min": round(min(first_cuts), 3),
                "max": round(max(first_cuts), 3),
                "stdev": round(statistics.stdev(first_cuts), 3) if len(first_cuts) > 1 else 0.0
            },
            "segment_duration": {
                "mean_of_means": round(statistics.mean(avg_segs), 3),
                "mean_of_medians": round(statistics.mean(med_segs), 3),
                "global_mean": round(statistics.mean(all_durations), 3) if all_durations else 0,
                "global_median": round(statistics.median(all_durations), 3) if all_durations else 0,
                "global_stdev": round(statistics.stdev(all_durations), 3) if len(all_durations) > 1 else 0
            },
            "cuts_per_minute": {
                "mean": round(statistics.mean(cpm), 2),
                "median": round(statistics.median(cpm), 2),
                "min": round(min(cpm), 2),
                "max": round(max(cpm), 2)
            },
            "segment_extremes": {
                "shortest_across_all": round(min(shortest), 3),
                "longest_across_all": round(max(longest), 3)
            },
            "duration_histogram": buckets,
            "total_segments_analyzed": len(all_durations)
        }

    # Audio-cut correlation aggregate
    episode_corrs = [r["audio_cut_correlation"]["alignment_pct"] for r in episodes if r["audio_cut_correlation"]["total_cuts"] > 0]

    return {
        "episodes": agg_pacing(episodes),
        "intros": agg_pacing(intros),
        "audio_cut_alignment": {
            "mean_pct": round(statistics.mean(episode_corrs), 1) if episode_corrs else 0,
            "median_pct": round(statistics.median(episode_corrs), 1) if episode_corrs else 0,
            "per_video": {r["video_id"]: r["audio_cut_correlation"]["alignment_pct"] for r in episodes}
        },
        "sample_size": {
            "episodes": len(episodes),
            "intros": len(intros),
            "total": len(results)
        }
    }


def main():
    print("=" * 60)
    print("HOOK FORENSIC ANALYSIS — Cypherpunk'd Editing DNA")
    print("=" * 60)

    videos = sorted(RAW_DIR.glob("*.mp4"))
    if not videos:
        print("ERROR: No videos found in", RAW_DIR)
        sys.exit(1)

    print(f"\nFound {len(videos)} videos to analyze")

    results = []
    for vpath in videos:
        video_id = vpath.stem
        try:
            result = analyze_one_video(str(vpath), video_id)
            results.append(result)
        except Exception as e:
            print(f"  ERROR analyzing {video_id}: {e}", file=sys.stderr)

    print(f"\n{'=' * 60}")
    print(f"CROSS-VIDEO ANALYSIS ({len(results)} videos)")
    print(f"{'=' * 60}")

    aggregate = compute_aggregate(results)

    # Save raw JSON
    output = {
        "analyzed_at": datetime.now().isoformat(),
        "source_dir": str(RAW_DIR),
        "video_count": len(results),
        "per_video": results,
        "aggregate": aggregate
    }

    # Remove raw audio_levels from JSON (too large), keep summaries
    for r in output["per_video"]:
        # Keep scenes but limit detail
        if len(r.get("scenes", [])) > 100:
            r["scenes_truncated"] = True
            r["scenes"] = r["scenes"][:100]

    with open(RESULTS_JSON, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to {RESULTS_JSON}")

    # Print summary
    ep = aggregate.get("episodes", {})
    if ep:
        print(f"\n--- EPISODE PACING (n={aggregate['sample_size']['episodes']}) ---")
        fc = ep.get("first_cut_timing", {})
        print(f"  First cut: mean={fc.get('mean', 'N/A')}s, median={fc.get('median', 'N/A')}s")
        sd = ep.get("segment_duration", {})
        print(f"  Segment duration: global_mean={sd.get('global_mean', 'N/A')}s, global_median={sd.get('global_median', 'N/A')}s")
        cpm = ep.get("cuts_per_minute", {})
        print(f"  Cuts/min: mean={cpm.get('mean', 'N/A')}, range=[{cpm.get('min', 'N/A')}, {cpm.get('max', 'N/A')}]")
        print(f"  Duration histogram: {ep.get('duration_histogram', {})}")

    ac = aggregate.get("audio_cut_alignment", {})
    if ac:
        print(f"\n--- AUDIO-CUT ALIGNMENT ---")
        print(f"  Mean alignment: {ac.get('mean_pct', 0)}%")

    return output


if __name__ == "__main__":
    main()
