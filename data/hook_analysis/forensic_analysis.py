#!/usr/bin/env python3
"""Forensic analysis of PBX intro hook editing patterns."""

import subprocess
import json
import os
import sys
import statistics

RAW_DIR = "/home/ultron/protocol_pulse/data/hook_analysis/raw"
RESULTS_DIR = "/home/ultron/protocol_pulse/data/hook_analysis/results"
os.makedirs(RESULTS_DIR, exist_ok=True)

def get_video_info(path):
    """Get duration, fps, resolution via ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    info = json.loads(result.stdout)
    duration = float(info["format"]["duration"])
    for s in info["streams"]:
        if s["codec_type"] == "video":
            fps_parts = s.get("r_frame_rate", "24/1").split("/")
            fps = float(fps_parts[0]) / float(fps_parts[1]) if len(fps_parts) == 2 else 24.0
            width = int(s.get("width", 1920))
            height = int(s.get("height", 1080))
            return {"duration": duration, "fps": fps, "width": width, "height": height}
    return {"duration": duration, "fps": 24.0, "width": 1920, "height": 1080}


def detect_scenes(path, threshold=27):
    """Scene detection using PySceneDetect."""
    try:
        from scenedetect import detect, ContentDetector
        scenes = detect(path, ContentDetector(threshold=threshold))
        cuts = []
        for i, (start, end) in enumerate(scenes):
            cuts.append({
                "cut_index": i,
                "start_sec": round(start.get_seconds(), 3),
                "end_sec": round(end.get_seconds(), 3),
                "duration_sec": round((end - start).get_seconds(), 3)
            })
        return cuts
    except Exception as e:
        print(f"  Scene detection error: {e}")
        return []


def get_audio_energy(path, sample_count=200):
    """Extract audio RMS energy curve using ffprobe astats."""
    cmd = [
        "ffprobe", "-f", "lavfi",
        "-i", f"amovie={path},astats=metadata=1:reset=1",
        "-show_entries", "frame_tags=lavfi.astats.Overall.RMS_level",
        "-of", "csv=p=0", "-v", "quiet"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    values = []
    for line in result.stdout.strip().split("\n"):
        line = line.strip()
        if line and line != "-inf":
            try:
                values.append(float(line))
            except ValueError:
                continue
    return values[:sample_count]


def get_audio_peaks(path):
    """Get loudness stats using ffmpeg loudnorm."""
    cmd = [
        "ffmpeg", "-i", path, "-af",
        "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json",
        "-f", "null", "-", "-v", "quiet"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    # Extract JSON from stderr (loudnorm outputs there)
    stderr = result.stderr
    try:
        json_start = stderr.rfind("{")
        json_end = stderr.rfind("}") + 1
        if json_start >= 0:
            return json.loads(stderr[json_start:json_end])
    except:
        pass
    return {}


def analyze_pacing(cuts, video_duration):
    """Compute pacing metrics from cut list."""
    if not cuts:
        return {"cuts_per_minute": 0, "avg_segment_dur": video_duration,
                "shortest_segment": video_duration, "longest_segment": video_duration,
                "first_cut_time": video_duration, "segment_durations": []}

    segment_durations = [c["duration_sec"] for c in cuts]
    first_cut = cuts[0]["end_sec"] if cuts else video_duration
    total_cuts = len(cuts)
    cuts_per_min = (total_cuts / video_duration) * 60 if video_duration > 0 else 0

    return {
        "cuts_per_minute": round(cuts_per_min, 2),
        "avg_segment_dur": round(statistics.mean(segment_durations), 3) if segment_durations else 0,
        "median_segment_dur": round(statistics.median(segment_durations), 3) if segment_durations else 0,
        "shortest_segment": round(min(segment_durations), 3) if segment_durations else 0,
        "longest_segment": round(max(segment_durations), 3) if segment_durations else 0,
        "first_cut_time": round(first_cut, 3),
        "std_dev": round(statistics.stdev(segment_durations), 3) if len(segment_durations) > 1 else 0,
        "segment_durations": segment_durations,
        "total_cuts": total_cuts
    }


def analyze_audio_cut_correlation(audio_energy, cuts, fps):
    """Check if audio energy spikes align with cut points."""
    if not audio_energy or not cuts:
        return {"correlation": 0, "aligned_cuts_pct": 0}

    # Audio energy is per-frame (roughly), map cut times to frame indices
    samples_per_sec = len(audio_energy) / 120  # ~2 min clips
    if samples_per_sec <= 0:
        return {"correlation": 0, "aligned_cuts_pct": 0}

    aligned = 0
    total_checked = 0
    window = max(2, int(samples_per_sec * 0.5))  # 0.5s window around cut

    for cut in cuts:
        cut_frame = int(cut["end_sec"] * samples_per_sec)
        if cut_frame < window or cut_frame + window >= len(audio_energy):
            continue
        total_checked += 1

        # Get energy around cut point
        cut_region = audio_energy[max(0, cut_frame - window):min(len(audio_energy), cut_frame + window)]
        # Get baseline energy (middle of segment)
        seg_mid = int((cut["start_sec"] + cut["end_sec"]) / 2 * samples_per_sec)
        baseline_region = audio_energy[max(0, seg_mid - window):min(len(audio_energy), seg_mid + window)]

        if cut_region and baseline_region:
            cut_energy = max(cut_region)
            baseline_energy = statistics.mean(baseline_region)
            # Higher energy at cut point = aligned
            if cut_energy > baseline_energy + 3:  # 3dB above baseline
                aligned += 1

    pct = (aligned / total_checked * 100) if total_checked > 0 else 0
    return {
        "aligned_cuts_pct": round(pct, 1),
        "aligned_cuts": aligned,
        "total_checked": total_checked
    }


def extract_first_frames(path, video_name, count=10):
    """Extract first N frames (1 per second) for text detection."""
    frame_dir = os.path.join(RESULTS_DIR, "frames", video_name.replace(" ", "_")[:30])
    os.makedirs(frame_dir, exist_ok=True)
    cmd = [
        "ffmpeg", "-i", path, "-vf", "select=not(mod(n\\,30))",
        "-vsync", "vfr", "-frames:v", str(count),
        os.path.join(frame_dir, "frame_%03d.png"),
        "-y", "-v", "quiet"
    ]
    subprocess.run(cmd, timeout=30)
    frames = sorted([f for f in os.listdir(frame_dir) if f.endswith(".png")])
    return frame_dir, frames


def analyze_video(path):
    """Run full forensic analysis on one video."""
    name = os.path.basename(path).replace(".mp4", "")
    print(f"\n{'='*60}")
    print(f"ANALYZING: {name}")
    print(f"{'='*60}")

    # Video info
    info = get_video_info(path)
    print(f"  Duration: {info['duration']:.1f}s | FPS: {info['fps']:.1f} | {info['width']}x{info['height']}")

    # Scene detection
    print("  Running scene detection...")
    cuts = detect_scenes(path, threshold=27)
    print(f"  Found {len(cuts)} scene cuts")

    # Pacing analysis
    pacing = analyze_pacing(cuts, info["duration"])
    print(f"  Cuts/min: {pacing['cuts_per_minute']} | Avg segment: {pacing['avg_segment_dur']}s")
    print(f"  First cut at: {pacing['first_cut_time']}s")
    print(f"  Shortest: {pacing['shortest_segment']}s | Longest: {pacing['longest_segment']}s")

    # Audio energy
    print("  Extracting audio energy curve...")
    audio_energy = get_audio_energy(path)
    print(f"  Got {len(audio_energy)} audio samples")

    # Audio-cut correlation
    correlation = analyze_audio_cut_correlation(audio_energy, cuts, info["fps"])
    print(f"  Audio-cut alignment: {correlation['aligned_cuts_pct']}% ({correlation.get('aligned_cuts',0)}/{correlation.get('total_checked',0)})")

    # First frames
    print("  Extracting first frames...")
    frame_dir, frames = extract_first_frames(path, name)
    print(f"  Extracted {len(frames)} frames to {frame_dir}")

    # Segment duration distribution (first 30s vs rest)
    early_segments = [c["duration_sec"] for c in cuts if c["start_sec"] < 30]
    late_segments = [c["duration_sec"] for c in cuts if c["start_sec"] >= 30]

    result = {
        "name": name,
        "video_info": info,
        "scene_cuts": cuts,
        "pacing": pacing,
        "audio_energy_samples": len(audio_energy),
        "audio_energy_mean": round(statistics.mean(audio_energy), 2) if audio_energy else 0,
        "audio_energy_peak": round(max(audio_energy), 2) if audio_energy else 0,
        "audio_cut_correlation": correlation,
        "early_avg_segment": round(statistics.mean(early_segments), 3) if early_segments else 0,
        "late_avg_segment": round(statistics.mean(late_segments), 3) if late_segments else 0,
        "frame_dir": frame_dir,
        "frame_count": len(frames)
    }

    return result


def cross_video_analysis(all_results):
    """Aggregate metrics across all videos."""
    print("\n" + "="*60)
    print("CROSS-VIDEO PATTERN ANALYSIS")
    print("="*60)

    first_cuts = [r["pacing"]["first_cut_time"] for r in all_results if r["pacing"]["first_cut_time"] < 120]
    avg_segments = [r["pacing"]["avg_segment_dur"] for r in all_results if r["pacing"]["avg_segment_dur"] > 0]
    cpm = [r["pacing"]["cuts_per_minute"] for r in all_results if r["pacing"]["cuts_per_minute"] > 0]
    shortest = [r["pacing"]["shortest_segment"] for r in all_results if r["pacing"]["shortest_segment"] > 0]
    longest = [r["pacing"]["longest_segment"] for r in all_results if r["pacing"]["longest_segment"] > 0]
    correlations = [r["audio_cut_correlation"]["aligned_cuts_pct"] for r in all_results]
    early_avgs = [r["early_avg_segment"] for r in all_results if r["early_avg_segment"] > 0]
    late_avgs = [r["late_avg_segment"] for r in all_results if r["late_avg_segment"] > 0]

    cross = {
        "sample_size": len(all_results),
        "first_cut_timing": {
            "mean": round(statistics.mean(first_cuts), 2) if first_cuts else 0,
            "median": round(statistics.median(first_cuts), 2) if first_cuts else 0,
            "min": round(min(first_cuts), 2) if first_cuts else 0,
            "max": round(max(first_cuts), 2) if first_cuts else 0,
            "stdev": round(statistics.stdev(first_cuts), 2) if len(first_cuts) > 1 else 0
        },
        "segment_duration": {
            "mean": round(statistics.mean(avg_segments), 2) if avg_segments else 0,
            "median": round(statistics.median(avg_segments), 2) if avg_segments else 0,
            "stdev": round(statistics.stdev(avg_segments), 2) if len(avg_segments) > 1 else 0
        },
        "cuts_per_minute": {
            "mean": round(statistics.mean(cpm), 2) if cpm else 0,
            "median": round(statistics.median(cpm), 2) if cpm else 0,
            "min": round(min(cpm), 2) if cpm else 0,
            "max": round(max(cpm), 2) if cpm else 0
        },
        "shortest_segments": {
            "mean": round(statistics.mean(shortest), 3) if shortest else 0,
            "min": round(min(shortest), 3) if shortest else 0
        },
        "longest_holds": {
            "mean": round(statistics.mean(longest), 2) if longest else 0,
            "max": round(max(longest), 2) if longest else 0
        },
        "audio_cut_correlation": {
            "mean_pct": round(statistics.mean(correlations), 1) if correlations else 0
        },
        "pacing_acceleration": {
            "early_30s_avg_segment": round(statistics.mean(early_avgs), 3) if early_avgs else 0,
            "late_30s_avg_segment": round(statistics.mean(late_avgs), 3) if late_avgs else 0,
            "acceleration_factor": round(
                statistics.mean(early_avgs) / statistics.mean(late_avgs), 2
            ) if early_avgs and late_avgs and statistics.mean(late_avgs) > 0 else 0
        }
    }

    # Print summary
    print(f"\n  Sample size: {cross['sample_size']} videos")
    print(f"\n  FIRST CUT TIMING:")
    print(f"    Mean: {cross['first_cut_timing']['mean']}s | Median: {cross['first_cut_timing']['median']}s")
    print(f"    Range: {cross['first_cut_timing']['min']}s — {cross['first_cut_timing']['max']}s")
    print(f"\n  SEGMENT DURATION:")
    print(f"    Mean: {cross['segment_duration']['mean']}s | Median: {cross['segment_duration']['median']}s")
    print(f"\n  CUTS PER MINUTE:")
    print(f"    Mean: {cross['cuts_per_minute']['mean']} | Range: {cross['cuts_per_minute']['min']}—{cross['cuts_per_minute']['max']}")
    print(f"\n  EXTREME SEGMENTS:")
    print(f"    Shortest avg: {cross['shortest_segments']['mean']}s (absolute min: {cross['shortest_segments']['min']}s)")
    print(f"    Longest avg: {cross['longest_holds']['mean']}s (absolute max: {cross['longest_holds']['max']}s)")
    print(f"\n  AUDIO-CUT ALIGNMENT: {cross['audio_cut_correlation']['mean_pct']}%")
    print(f"\n  PACING ACCELERATION:")
    print(f"    First 30s avg segment: {cross['pacing_acceleration']['early_30s_avg_segment']}s")
    print(f"    After 30s avg segment: {cross['pacing_acceleration']['late_30s_avg_segment']}s")
    print(f"    Factor: {cross['pacing_acceleration']['acceleration_factor']}x")

    return cross


if __name__ == "__main__":
    clips = sorted([
        os.path.join(RAW_DIR, f) for f in os.listdir(RAW_DIR)
        if f.endswith(".mp4")
    ])

    print(f"Found {len(clips)} clips to analyze")

    all_results = []
    for clip in clips:
        result = analyze_video(clip)
        all_results.append(result)

    cross = cross_video_analysis(all_results)

    # Save raw results
    output = {
        "per_video": [{k: v for k, v in r.items() if k != "frame_dir"} for r in all_results],
        "cross_video": cross
    }
    output_path = os.path.join(RESULTS_DIR, "forensic_results.json")
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to {output_path}")
