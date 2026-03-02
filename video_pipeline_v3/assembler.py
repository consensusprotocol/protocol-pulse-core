#!/usr/bin/env python3
"""Assembler V4 — dual-host dialogue visuals + YouTube clip-react layout.
During dialogue: dark studio overlay with speaker labels.
During clips: full-screen YouTube clip with source attribution.
Lower-third ticker: PROTOCOL PULSE | PULSE CHECK | BTC $XX,XXX"""
import os, subprocess, json, sys, tempfile, shutil
from pathlib import Path

BASE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(BASE, "assets")
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"


def ffprobe_duration(path: str) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", path],
        capture_output=True, text=True,
    )
    try:
        return float(r.stdout.strip())
    except Exception:
        return 0.0


def run_ffmpeg(args: list, label: str = "", timeout: int = 300) -> bool:
    cmd = ["ffmpeg", "-y"] + args
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        print(f"  [FAIL] {label}: {r.stderr[-400:]}")
        return False
    return True


def run_ffmpeg_filtergraph(inputs: list, filtergraph: str, maps: list,
                           output_args: list, output_path: str,
                           label: str = "", timeout: int = 300) -> bool:
    fd, fpath = tempfile.mkstemp(suffix=".txt", prefix="ff_filter_")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(filtergraph)
        cmd = ["ffmpeg", "-y"]
        for inp in inputs:
            if isinstance(inp, list):
                cmd.extend(inp)
            else:
                cmd.extend(["-i", inp])
        cmd.extend(["-filter_complex_script", fpath])
        for m in maps:
            cmd.extend(["-map", m])
        cmd.extend(output_args)
        cmd.append(output_path)
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if r.returncode != 0:
            print(f"  [FAIL] {label}: {r.stderr[-400:]}")
            return False
        return True
    finally:
        os.unlink(fpath)


def ensure_audio(video_path: str) -> str:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a",
         "-show_entries", "stream=codec_type", "-of", "csv=p=0", video_path],
        capture_output=True, text=True,
    )
    if "audio" in r.stdout:
        return video_path
    out = video_path.replace(".mp4", "_waud.mp4")
    dur = ffprobe_duration(video_path)
    run_ffmpeg(
        ["-i", video_path, "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo",
         "-t", str(dur), "-c:v", "copy", "-c:a", "aac", "-shortest", out],
        "add silence", 60,
    )
    return out if os.path.exists(out) else video_path


# ── Dialogue line visual ─────────────────────────────────────────────────────

def make_dialogue_visual(audio_path: str, host: int, text: str,
                         broll_path: str, output_path: str,
                         btc_price: str = "N/A",
                         line_index: int = 0) -> str:
    """Create a dialogue line video: B-roll background + speaker label + ticker."""
    audio_dur = ffprobe_duration(audio_path)
    if audio_dur <= 0:
        audio_dur = 5
    total_dur = audio_dur + 0.2

    host_names = {1: "JESSICA", 2: "CHRIS"}
    host_colors = {1: "0xCC0000", 2: "0x0066CC"}
    speaker = host_names.get(host, "HOST")
    color = host_colors.get(host, "0xCC0000")

    # Truncate display text for subtitle
    display_text = text[:100].replace("'", "").replace('"', '').replace(":", " -").replace("%", " pct")

    loop_frames = int(total_dur * 30) + 60

    fg_parts = []

    if broll_path and os.path.exists(broll_path):
        # B-roll background
        fg_parts.append(
            f"[0:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,"
            f"setsar=1,fps=30,loop=-1:size={loop_frames}:start=0,"
            f"trim=0:{total_dur},setpts=PTS-STARTPTS,"
            f"eq=brightness=-0.15:saturation=0.7[bg]"
        )
        audio_input = "1:a"
    else:
        # Dark background
        fg_parts.append(
            f"color=c=0x080808:s=1920x1080:d={total_dur}:r=30[bg]"
        )
        audio_input = "1:a"

    # Speaker label bar (left side)
    fg_parts.append(f"color=c={color}:s=6x60:d={total_dur}[spkbar]")
    fg_parts.append(f"color=c=0x0A0A0A@0.85:s=220x60:d={total_dur}[spkbg]")
    fg_parts.append(
        f"[spkbg][spkbar]overlay=0:0[spkbase];\n"
        f"[spkbase]drawtext=fontfile={FONT_BOLD}:text='{speaker}':"
        f"fontcolor=white:fontsize=24:x=20:y=18[spklabel]"
    )

    # Lower-third ticker
    ticker_text = f"PROTOCOL PULSE  |  PULSE CHECK  |  BTC {btc_price}"
    ticker_text = ticker_text.replace("'", "").replace('"', '')
    fg_parts.append(
        f"color=c=0x0A0A0A@0.9:s=1920x50:d={total_dur}[tickbg];\n"
        f"[tickbg]drawtext=fontfile={FONT_MONO}:text='{ticker_text}':"
        f"fontcolor=0xAAAAAA:fontsize=20:x=(w-text_w)/2:y=15[ticker]"
    )

    # Compose
    fg_parts.append(
        f"[bg][spklabel]overlay=60:H-180[v1];\n"
        f"[v1][ticker]overlay=0:H-50[v2];\n"
        f"[v2]drawtext=fontfile={FONT_MONO}:text='PROTOCOL PULSE':"
        f"fontcolor=white@0.25:fontsize=16:x=W-220:y=20,"
        f"format=yuv420p[outv];\n"
        f"[{audio_input}]loudnorm=I=-16:TP=-1.5:LRA=11[outa]"
    )

    filtergraph = ";\n".join(fg_parts)

    inputs = []
    if broll_path and os.path.exists(broll_path):
        inputs.append(broll_path)
    else:
        inputs.append(["-f", "lavfi", "-i", f"color=c=0x080808:s=1920x1080:d={total_dur}:r=30"])
    inputs.append(audio_path)

    ok = run_ffmpeg_filtergraph(
        inputs, filtergraph, ["[outv]", "[outa]"],
        ["-c:v", "libx264", "-crf", "20", "-preset", "fast",
         "-c:a", "aac", "-ar", "44100", "-b:a", "192k", "-t", str(total_dur)],
        output_path, f"dialogue line {line_index}",
    )
    return output_path if ok else ""


# ── YouTube clip visual ──────────────────────────────────────────────────────

def make_clip_visual(clip_path: str, source: str, output_path: str,
                     duration: float = 15, btc_price: str = "N/A") -> str:
    """Create a full-screen clip segment with source attribution."""
    clip_dur = ffprobe_duration(clip_path)
    use_dur = min(clip_dur, duration) if clip_dur > 0 else duration

    safe_source = source.replace("'", "").replace('"', '').replace(":", "")
    ticker_text = f"PROTOCOL PULSE  |  PULSE CHECK  |  BTC {btc_price}"
    ticker_text = ticker_text.replace("'", "").replace('"', '')

    fg = (
        f"[0:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,"
        f"setsar=1,fps=30,trim=0:{use_dur},setpts=PTS-STARTPTS[clip];\n"
        # Source attribution overlay
        f"color=c=0x0A0A0A@0.8:s=350x45:d={use_dur}[srcbg];\n"
        f"[srcbg]drawtext=fontfile={FONT_MONO}:text='Source  {safe_source}':"
        f"fontcolor=white:fontsize=18:x=15:y=12[srclabel];\n"
        # Ticker
        f"color=c=0x0A0A0A@0.9:s=1920x50:d={use_dur}[tickbg];\n"
        f"[tickbg]drawtext=fontfile={FONT_MONO}:text='{ticker_text}':"
        f"fontcolor=0xAAAAAA:fontsize=20:x=(w-text_w)/2:y=15[ticker];\n"
        # Compose
        f"[clip][srclabel]overlay=W-370:20[v1];\n"
        f"[v1][ticker]overlay=0:H-50,"
        f"format=yuv420p[outv]"
    )

    # Generate silent audio as second input
    ok = run_ffmpeg_filtergraph(
        [clip_path,
         ["-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo"]],
        fg, ["[outv]", "1:a"],
        ["-c:v", "libx264", "-crf", "20", "-preset", "fast",
         "-c:a", "aac", "-ar", "44100", "-b:a", "192k",
         "-t", str(use_dur), "-shortest"],
        output_path, f"clip visual ({safe_source})",
    )
    return output_path if ok else ""


# ── Concatenation ────────────────────────────────────────────────────────────

def concatenate_parts(parts: list, output_path: str) -> str:
    """Concat video parts with crossfade transitions."""
    valid = [p for p in parts if p and os.path.exists(p)]
    if not valid:
        return ""
    if len(valid) == 1:
        shutil.copy2(valid[0], output_path)
        return output_path

    # Normalize all parts
    normalized = []
    for i, p in enumerate(valid):
        p = ensure_audio(p)
        tmp = output_path + f".norm{i}.mp4"
        ok = run_ffmpeg(
            ["-i", p, "-c:v", "libx264", "-crf", "20", "-preset", "fast",
             "-r", "30", "-vf", "scale=1920:1080,setsar=1,format=yuv420p",
             "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "192k", tmp],
            f"normalize {i}", 120,
        )
        normalized.append(tmp if (ok and os.path.exists(tmp)) else p)

    # Use concat demuxer (fast, reliable)
    concat_file = output_path + ".concat.txt"
    with open(concat_file, "w") as f:
        for p in normalized:
            f.write(f"file '{os.path.abspath(p)}'\n")

    ok = run_ffmpeg(
        ["-f", "concat", "-safe", "0", "-i", concat_file,
         "-c:v", "libx264", "-crf", "20", "-preset", "fast",
         "-c:a", "aac", "-ar", "44100", "-b:a", "192k", output_path],
        "concat final", 600,
    )

    # Cleanup
    for p in normalized:
        if ".norm" in p and os.path.exists(p):
            try:
                os.remove(p)
            except Exception:
                pass
    for p in valid:
        if p.endswith("_waud.mp4") and os.path.exists(p):
            try:
                os.remove(p)
            except Exception:
                pass
    if os.path.exists(concat_file):
        os.remove(concat_file)

    return output_path if ok else ""


# ── Main assembly ────────────────────────────────────────────────────────────

def assemble_episode(script: dict, audio_data: dict, clip_data: dict,
                     output_path: str, btc_price: str = "N/A") -> str:
    """Assemble a V4 dual-host episode from dialogue audio + clips.

    Args:
        script: V4 script with dialogue array
        audio_data: From generate_dialogue_audio() — {lines, full, total_duration}
        clip_data: From fetch_all_clips() — {yt_clips, broll, count}
        output_path: Final video path
        btc_price: BTC price string for ticker
    """
    print("\n" + "=" * 60)
    print("ASSEMBLING V4 DUAL-HOST VIDEO")
    print("=" * 60)

    work_dir = os.path.join(os.path.dirname(os.path.abspath(output_path)), "work")
    os.makedirs(work_dir, exist_ok=True)

    dialogue = script.get("dialogue", [])
    lines = audio_data.get("lines", [])
    yt_clips = clip_data.get("yt_clips", {})
    broll = clip_data.get("broll", [])

    parts = []
    broll_idx = 0

    # 1. Intro asset
    intro_path = os.path.join(ASSETS, "intro.mp4")
    if os.path.exists(intro_path):
        parts.append(intro_path)
        print(f"  [assemble] intro: {ffprobe_duration(intro_path):.1f}s")

    # 2. Transition
    trans_path = os.path.join(ASSETS, "transitions", "glitch_transition.mp4")
    if os.path.exists(trans_path):
        parts.append(trans_path)

    # 3. Dialogue lines + clip inserts
    for i, entry in enumerate(dialogue):
        host = entry.get("host")

        if host == "CLIP":
            # YouTube clip insert
            clip_idx = i
            yt_path = yt_clips.get(clip_idx) or yt_clips.get(str(clip_idx))
            if yt_path and os.path.exists(yt_path):
                clip_out = os.path.join(work_dir, f"clip_{i:03d}.mp4")
                source = entry.get("source", "")
                result = make_clip_visual(yt_path, source, clip_out,
                                          duration=15, btc_price=btc_price)
                if result:
                    parts.append(result)
                    print(f"  [assemble] clip {i}: YouTube ({source})")
            else:
                print(f"  [assemble] clip {i}: no YouTube clip, skipping")
            continue

        # Regular dialogue line
        if i >= len(lines):
            continue
        line = lines[i]
        if not line.get("path") or not os.path.exists(line["path"]):
            continue

        host_num = line.get("host", 1)
        text = line.get("text", "")

        # Pick B-roll for background
        bg_clip = None
        if broll and broll_idx < len(broll):
            bg_clip = broll[broll_idx % len(broll)]
        broll_idx += 1

        line_out = os.path.join(work_dir, f"line_{i:03d}.mp4")
        result = make_dialogue_visual(
            line["path"], host_num, text, bg_clip, line_out,
            btc_price=btc_price, line_index=i,
        )
        if result:
            parts.append(result)

    # 4. Transition before outro
    if os.path.exists(trans_path):
        parts.append(trans_path)

    # 5. Outro asset
    outro_asset = os.path.join(ASSETS, "outro.mp4")
    if os.path.exists(outro_asset):
        parts.append(outro_asset)

    # 6. Concatenate
    print(f"\n  [assemble] Concatenating {len(parts)} parts...")
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    result = concatenate_parts(parts, output_path)

    if result and os.path.exists(result):
        dur = ffprobe_duration(result)
        sz = os.path.getsize(result)
        print(f"\n  [DONE] Final video: {result}")
        print(f"         Duration: {dur:.1f}s | Size: {sz / 1024 / 1024:.1f}MB")
        return result

    return ""


def verify_video(path: str) -> bool:
    """Verify output video meets spec."""
    print(f"\n{'='*60}")
    print(f"VERIFICATION: {os.path.basename(path)}")
    print(f"{'='*60}")

    if not os.path.exists(path):
        print("  [FAIL] File does not exist")
        return False

    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", path],
        capture_output=True, text=True,
    )
    try:
        info = json.loads(r.stdout)
    except Exception:
        print("  [FAIL] Cannot parse ffprobe output")
        return False

    streams = info.get("streams", [])
    fmt = info.get("format", {})
    vid = next((s for s in streams if s.get("codec_type") == "video"), None)
    aud = next((s for s in streams if s.get("codec_type") == "audio"), None)

    checks = []
    if vid:
        w, h = int(vid.get("width", 0)), int(vid.get("height", 0))
        checks.append(("Video codec", vid.get("codec_name") == "h264", vid.get("codec_name")))
        checks.append(("Resolution", w == 1920 and h == 1080, f"{w}x{h}"))
    else:
        checks.append(("Video stream", False, "MISSING"))

    if aud:
        checks.append(("Audio codec", aud.get("codec_name") == "aac", aud.get("codec_name")))
        checks.append(("Sample rate", aud.get("sample_rate") == "44100", aud.get("sample_rate")))
    else:
        checks.append(("Audio stream", False, "MISSING"))

    duration = float(fmt.get("duration", 0))
    size_mb = int(fmt.get("size", 0)) / 1024 / 1024
    checks.append(("Duration", 10 <= duration <= 600, f"{duration:.1f}s"))
    checks.append(("File size", 0.5 <= size_mb <= 500, f"{size_mb:.1f}MB"))

    all_pass = True
    for name, passed, detail in checks:
        status = "PASS" if passed else "FAIL"
        if not passed:
            all_pass = False
        print(f"  [{status}] {name}: {detail}")

    return all_pass


if __name__ == "__main__":
    print("Assembler V4 — use daily_producer.py to run the full pipeline")
