#!/usr/bin/env python3
"""Chapter markers — YouTube description format + FFmpeg chapter metadata.
Generates timestamped chapter list from dialogue audio timing data."""
import os, subprocess, json


def generate_chapters(script: dict, audio_data: dict,
                      output_path: str) -> str:
    """Generate YouTube-format chapter markers.

    Args:
        script: V4 script with chapters array
        audio_data: From generate_dialogue_audio() with timing info
        output_path: Path for chapters.txt

    Returns:
        Path to chapters file.
    """
    chapters = script.get("chapters", [])
    lines = audio_data.get("lines", [])
    total_dur = audio_data.get("total_duration", 0)

    if not chapters:
        # Auto-generate from dialogue structure
        chapters = _auto_chapters(script, lines)

    # Calculate timestamps based on line timing
    timed_chapters = _assign_timestamps(chapters, lines, total_dur)

    # Write YouTube description format
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w") as f:
        f.write("CHAPTERS\n")
        f.write("=" * 40 + "\n\n")
        for ch in timed_chapters:
            f.write(f"{ch['timestamp']}  {ch['title']}\n")
        f.write(f"\n{'=' * 40}\n")
        f.write("Copy the timestamps above into your YouTube description.\n")

    print(f"  [chapters] Generated {len(timed_chapters)} chapters → {output_path}")
    return output_path


def _auto_chapters(script: dict, lines: list) -> list:
    """Generate chapters automatically from dialogue structure."""
    chapters = [{"title": "Intro", "time_hint": "start"}]
    summaries = script.get("segments_summary", [])

    if summaries:
        for i, s in enumerate(summaries):
            hint = "after_intro" if i == 0 else ("mid" if i < len(summaries) - 1 else "late")
            chapters.append({"title": s, "time_hint": hint})
    else:
        # Scan for topic changes in dialogue
        seen_topics = 0
        for i, line in enumerate(lines):
            text = line.get("text", "")
            if any(w in text.lower() for w in ["meanwhile", "now", "next", "speaking of", "but here"]):
                seen_topics += 1
                chapters.append({
                    "title": f"Topic {seen_topics}",
                    "time_hint": "mid",
                })

    chapters.append({"title": "Outro", "time_hint": "end"})
    return chapters


def _assign_timestamps(chapters: list, lines: list, total_dur: float) -> list:
    """Assign actual timestamps to chapter hints."""
    n = len(chapters)
    if n == 0:
        return []

    timed = []
    for i, ch in enumerate(chapters):
        hint = ch.get("time_hint", "mid")

        if hint == "start":
            seconds = 0
        elif hint == "after_intro":
            # After first few dialogue lines
            if len(lines) > 2:
                seconds = lines[2].get("start", 0) + lines[2].get("duration", 0)
            else:
                seconds = total_dur * 0.1
        elif hint == "end":
            seconds = max(0, total_dur - 20)
        elif hint == "late":
            seconds = total_dur * 0.7
        else:  # "mid" — distribute evenly
            frac = (i / max(n - 1, 1))
            seconds = total_dur * frac

        seconds = max(0, int(seconds))
        mins = seconds // 60
        secs = seconds % 60
        timed.append({
            "title": ch["title"],
            "seconds": seconds,
            "timestamp": f"{mins}:{secs:02d}",
        })

    return timed


def embed_ffmpeg_chapters(video_path: str, chapters_path: str,
                          output_path: str) -> str:
    """Embed chapter metadata into the video file via FFmpeg."""
    # Read chapters
    chapters = []
    with open(chapters_path) as f:
        for line in f:
            line = line.strip()
            if ":" in line and line[0].isdigit():
                parts = line.split(None, 1)
                if len(parts) == 2:
                    ts, title = parts
                    mins, secs = ts.split(":")
                    total_s = int(mins) * 60 + int(secs)
                    chapters.append({"start": total_s, "title": title})

    if not chapters:
        return video_path

    # Build FFmpeg metadata file
    meta_lines = [";FFMETADATA1"]
    for i, ch in enumerate(chapters):
        start_ms = ch["start"] * 1000
        if i + 1 < len(chapters):
            end_ms = chapters[i + 1]["start"] * 1000
        else:
            end_ms = start_ms + 60000  # 1 min default for last chapter
        meta_lines.append("[CHAPTER]")
        meta_lines.append("TIMEBASE=1/1000")
        meta_lines.append(f"START={start_ms}")
        meta_lines.append(f"END={end_ms}")
        meta_lines.append(f"title={ch['title']}")

    meta_path = video_path + ".ffmeta.txt"
    with open(meta_path, "w") as f:
        f.write("\n".join(meta_lines))

    r = subprocess.run(
        ["ffmpeg", "-y", "-i", video_path, "-i", meta_path,
         "-map_metadata", "1", "-c", "copy", output_path],
        capture_output=True, text=True, timeout=120,
    )

    try:
        os.remove(meta_path)
    except Exception:
        pass

    if r.returncode == 0 and os.path.exists(output_path):
        return output_path
    return video_path


if __name__ == "__main__":
    sample = {
        "chapters": [
            {"title": "Intro", "time_hint": "start"},
            {"title": "Mining Difficulty", "time_hint": "after_intro"},
            {"title": "Sovereign Funds", "time_hint": "mid"},
            {"title": "Outro", "time_hint": "end"},
        ],
    }
    audio = {"lines": [], "total_duration": 120}
    base = os.path.dirname(os.path.abspath(__file__))
    generate_chapters(sample, audio, os.path.join(base, "output", "test_chapters.txt"))
