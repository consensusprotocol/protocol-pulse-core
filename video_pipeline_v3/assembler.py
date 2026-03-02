#!/usr/bin/env python3
"""Step 7: Assembler — FFmpeg video assembly.
Builds the final video from assets, audio, and clips.
Uses filter_complex_script files to avoid shell escaping issues."""
import os, subprocess, json, sys, tempfile
from pathlib import Path

BASE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(BASE, "assets")
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"


def ffprobe_duration(path: str) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
        capture_output=True, text=True
    )
    try:
        return float(r.stdout.strip())
    except:
        return 0.0


def run_ffmpeg(args: list, label: str = "", timeout: int = 300) -> bool:
    """Run ffmpeg with list args (no shell escaping issues)."""
    cmd = ["ffmpeg", "-y"] + args
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        print(f"  [FAIL] {label}: {r.stderr[-400:]}")
        return False
    return True


def run_ffmpeg_filtergraph(inputs: list, filtergraph: str, maps: list,
                           output_args: list, output_path: str,
                           label: str = "", timeout: int = 300) -> bool:
    """Run ffmpeg with a filter_complex written to a temp file to avoid shell issues."""
    # Write filtergraph to temp file
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
    """Ensure a video file has an audio stream (add silence if needed)."""
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a",
         "-show_entries", "stream=codec_type", "-of", "csv=p=0", video_path],
        capture_output=True, text=True
    )
    if "audio" in r.stdout:
        return video_path
    out = video_path.replace(".mp4", "_waud.mp4")
    dur = ffprobe_duration(video_path)
    run_ffmpeg(
        ["-i", video_path, "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo",
         "-t", str(dur), "-c:v", "copy", "-c:a", "aac", "-shortest", out],
        "add silence", 60
    )
    return out if os.path.exists(out) else video_path


def generate_visual(output_path: str, duration: float, text_main: str,
                    text_sub: str = "", font_size: int = 72) -> bool:
    """Generate a simple branded visual clip (no complex expressions)."""
    safe_main = text_main.replace("'", "").replace(":", " -").replace('"', '')
    safe_sub = text_sub.replace("'", "").replace(":", " -").replace('"', '') if text_sub else ""

    fg = (
        f"[0:v]drawgrid=w=60:h=60:t=1:c=0x1A1A1A@0.5,"
        f"drawgrid=w=300:h=300:t=2:c=0x2A0000@0.3,"
        f"colorbalance=rs=0.1:gs=0:bs=0,"
        f"drawtext=fontfile={FONT_BOLD}:text='{safe_main}':"
        f"fontcolor=white:fontsize={font_size}:x=(w-text_w)/2:y=(h-text_h)/2-30,"
    )
    if safe_sub:
        fg += (
            f"drawtext=fontfile={FONT_MONO}:text='{safe_sub}':"
            f"fontcolor=0xCC0000:fontsize=28:x=(w-text_w)/2:y=(h/2+30),"
        )
    fg += f"noise=alls=5:allf=t,format=yuv420p[out]"

    return run_ffmpeg_filtergraph(
        [["-f", "lavfi", "-i", f"color=c=0x080808:s=1920x1080:d={duration}:r=30"]],
        fg, ["[out]"],
        ["-c:v", "libx264", "-crf", "20", "-preset", "fast"],
        output_path, f"visual: {safe_main[:30]}"
    )


def make_segment_video(clip_path: str, audio_path: str, headline: str,
                       source: str, output_path: str, seg_index: int) -> str:
    """Compose a single segment: B-roll/card + narration + lower third."""
    audio_dur = ffprobe_duration(audio_path)
    if audio_dur <= 0:
        audio_dur = 15
    total_dur = audio_dur + 1.0

    safe_headline = headline.replace("'", "").replace(":", " -").replace('"', '').replace('%', ' pct')
    safe_source = source.replace("'", "").replace(":", "").replace('"', '')

    loop_frames = int(total_dur * 30) + 60

    fg = (
        f"[0:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,"
        f"setsar=1,fps=30,loop=-1:size={loop_frames}:start=0,"
        f"trim=0:{total_dur},setpts=PTS-STARTPTS[bg];\n"
        f"color=c=0x0A0A0A@0.85:s=800x100:d={total_dur}[ltbg];\n"
        f"color=c=0xCC0000:s=8x100:d={total_dur}[ltbar];\n"
        f"[ltbg][ltbar]overlay=0:0[ltbase];\n"
        f"[ltbase]drawtext=fontfile={FONT_BOLD}:text='{safe_headline}':"
        f"fontcolor=white:fontsize=30:x=20:y=20,"
        f"drawtext=fontfile={FONT_MONO}:text='{safe_source}':"
        f"fontcolor=0xCC0000:fontsize=18:x=20:y=62,"
        f"format=yuva420p[lt];\n"
        f"[bg][lt]overlay=x=60:y=H-140:shortest=1,"
        f"drawtext=fontfile={FONT_MONO}:text='PROTOCOL PULSE':"
        f"fontcolor=white@0.3:fontsize=18:x=W-250:y=25,"
        f"format=yuv420p[outv];\n"
        f"[1:a]loudnorm=I=-16:TP=-1.5:LRA=11[outa]"
    )

    ok = run_ffmpeg_filtergraph(
        [clip_path, audio_path], fg, ["[outv]", "[outa]"],
        ["-c:v", "libx264", "-crf", "20", "-preset", "fast",
         "-c:a", "aac", "-ar", "44100", "-b:a", "192k", "-t", str(total_dur)],
        output_path, f"segment {seg_index}"
    )
    if ok:
        print(f"  [assemble] segment {seg_index} OK: {ffprobe_duration(output_path):.1f}s")
        return output_path
    return ""


def make_bridge_video(audio_path: str, output_path: str, index: int) -> str:
    """Create a bridge segment — transitional visual + narration."""
    audio_dur = ffprobe_duration(audio_path)
    if audio_dur <= 0:
        audio_dur = 4
    total_dur = audio_dur + 0.5

    fg = (
        f"[0:v]drawgrid=w=80:h=80:t=1:c=0x1A1A1A@0.4,"
        f"colorbalance=rs=0.12:gs=0:bs=0,"
        f"drawbox=x=0:y=538:w=1920:h=4:c=0xCC0000@0.6:t=fill,"
        f"drawtext=fontfile={FONT_MONO}:text='PROTOCOL PULSE':"
        f"fontcolor=white@0.3:fontsize=18:x=W-250:y=25,"
        f"noise=alls=4:allf=t,format=yuv420p[v];\n"
        f"[1:a]loudnorm=I=-16:TP=-1.5:LRA=11[a]"
    )

    ok = run_ffmpeg_filtergraph(
        [["-f", "lavfi", "-i", f"color=c=0x0A0A0A:s=1920x1080:d={total_dur}:r=30"],
         audio_path],
        fg, ["[v]", "[a]"],
        ["-c:v", "libx264", "-crf", "20", "-c:a", "aac",
         "-ar", "44100", "-b:a", "192k", "-t", str(total_dur)],
        output_path, f"bridge {index}"
    )
    if ok:
        print(f"  [assemble] bridge {index} OK: {ffprobe_duration(output_path):.1f}s")
        return output_path
    return ""


def make_editorial_video(audio_path: str, text: str, output_path: str, index: int) -> str:
    """Create an editorial drop segment — data card + narration."""
    audio_dur = ffprobe_duration(audio_path)
    if audio_dur <= 0:
        audio_dur = 10
    total_dur = audio_dur + 0.5
    safe_text = text[:90].replace("'", "").replace(":", " -").replace('"', '').replace('%', ' pct')

    fg = (
        f"[0:v]drawgrid=w=60:h=60:t=1:c=0x1A1A1A@0.3,"
        f"colorbalance=rs=0.1:gs=0:bs=0,"
        f"drawbox=x=200:y=300:w=1520:h=400:c=0x111111@0.9:t=fill,"
        f"drawbox=x=200:y=300:w=6:h=400:c=0xCC0000:t=fill,"
        f"drawtext=fontfile={FONT_BOLD}:text='EDITORIAL':"
        f"fontcolor=0xCC0000:fontsize=22:x=230:y=320,"
        f"drawtext=fontfile={FONT_BOLD}:text='{safe_text}':"
        f"fontcolor=white:fontsize=28:x=230:y=380,"
        f"drawtext=fontfile={FONT_MONO}:text='PROTOCOL PULSE':"
        f"fontcolor=white@0.3:fontsize=18:x=W-250:y=25,"
        f"noise=alls=3:allf=t,format=yuv420p[v];\n"
        f"[1:a]loudnorm=I=-16:TP=-1.5:LRA=11[a]"
    )

    ok = run_ffmpeg_filtergraph(
        [["-f", "lavfi", "-i", f"color=c=0x080808:s=1920x1080:d={total_dur}:r=30"],
         audio_path],
        fg, ["[v]", "[a]"],
        ["-c:v", "libx264", "-crf", "20", "-c:a", "aac",
         "-ar", "44100", "-b:a", "192k", "-t", str(total_dur)],
        output_path, f"editorial {index}"
    )
    if ok:
        print(f"  [assemble] editorial {index} OK: {ffprobe_duration(output_path):.1f}s")
        return output_path
    return ""


def concatenate_final(parts: list, output_path: str) -> str:
    """Concatenate all video parts into final output using concat demuxer."""
    normalized = []
    for i, p in enumerate(parts):
        if not p or not os.path.exists(p):
            continue
        norm = ensure_audio(p)
        tmp = p.replace(".mp4", "_norm.mp4")
        ok = run_ffmpeg(
            ["-i", norm, "-c:v", "libx264", "-crf", "20", "-preset", "fast",
             "-r", "30", "-vf", "scale=1920:1080,setsar=1,format=yuv420p",
             "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "192k", tmp],
            f"normalize part {i}", 120
        )
        if ok and os.path.exists(tmp):
            normalized.append(tmp)
        else:
            normalized.append(norm)

    concat_file = output_path + ".concat.txt"
    with open(concat_file, "w") as f:
        for p in normalized:
            f.write(f"file '{os.path.abspath(p)}'\n")

    ok = run_ffmpeg(
        ["-f", "concat", "-safe", "0", "-i", concat_file,
         "-c:v", "libx264", "-crf", "20", "-preset", "fast",
         "-c:a", "aac", "-ar", "44100", "-b:a", "192k", output_path],
        "concat final", 600
    )
    if not ok:
        return ""

    # Cleanup
    for p in normalized:
        if p.endswith("_norm.mp4") and os.path.exists(p):
            os.remove(p)
    for p in parts:
        if p and os.path.exists(p) and p.endswith("_waud.mp4"):
            os.remove(p)
    if os.path.exists(concat_file):
        os.remove(concat_file)

    return output_path


def assemble_episode(script: dict, audio_paths: dict, clip_data: dict,
                     output_path: str) -> str:
    """Assemble a complete episode from all components."""
    print("\n" + "=" * 60)
    print("ASSEMBLING FINAL VIDEO")
    print("=" * 60)

    work_dir = os.path.join(os.path.dirname(os.path.abspath(output_path)), "work")
    os.makedirs(work_dir, exist_ok=True)

    parts = []

    # 1. Intro
    intro_path = os.path.join(ASSETS, "intro.mp4")
    if os.path.exists(intro_path):
        parts.append(intro_path)
        print(f"  [assemble] intro: {ffprobe_duration(intro_path):.1f}s")

    # 2. Transition
    trans_path = os.path.join(ASSETS, "transitions", "glitch_transition.mp4")

    # 3. Cold open
    if audio_paths.get("cold_open"):
        cold_clip = os.path.join(work_dir, "cold_visual.mp4")
        dur = ffprobe_duration(audio_paths["cold_open"])
        generate_visual(cold_clip, dur + 1, "PULSE CHECK", "Bitcoin Intelligence Daily")

        if os.path.exists(cold_clip):
            cold_seg = os.path.join(work_dir, "cold_open.mp4")
            result = make_segment_video(cold_clip, audio_paths["cold_open"],
                                        "PULSE CHECK", "Bitcoin Intelligence Daily",
                                        cold_seg, -1)
            if result:
                parts.append(result)

    # 4. Transition before segments
    if os.path.exists(trans_path):
        parts.append(trans_path)

    # 5. Segments with bridges and editorial drops
    segments = script.get("segments", [])
    seg_audios = audio_paths.get("segments", [])
    bridges = audio_paths.get("bridges", [])
    editorials = audio_paths.get("editorials", [])
    seg_clips = clip_data.get("segments", [])

    for i, seg in enumerate(segments):
        clip = ""
        if i < len(seg_clips):
            clip_list = seg_clips[i].get("clips", [])
            clip = clip_list[0] if clip_list else ""

        audio = seg_audios[i] if i < len(seg_audios) else None
        if not audio or not os.path.exists(audio):
            print(f"  [assemble] skipping segment {i}: no audio")
            continue

        if not clip or not os.path.exists(clip):
            clip = os.path.join(work_dir, f"seg_{i}_visual.mp4")
            dur = ffprobe_duration(audio)
            kw = seg.get("keywords_for_visuals", ["bitcoin"])[0].upper()
            kw = kw.replace("'", "").replace('"', '')
            generate_visual(clip, dur + 1, kw, seg["headline"][:40])

        if os.path.exists(clip):
            seg_out = os.path.join(work_dir, f"seg_{i:02d}.mp4")
            result = make_segment_video(clip, audio, seg["headline"],
                                        "Protocol Pulse Intelligence", seg_out, i)
            if result:
                parts.append(result)

        # Editorial drop
        if i < len(editorials) and editorials[i] and os.path.exists(editorials[i]):
            ed_out = os.path.join(work_dir, f"editorial_{i:02d}.mp4")
            ed_text = seg.get("editorial_drop", "")
            result = make_editorial_video(editorials[i], ed_text, ed_out, i)
            if result:
                parts.append(result)

        # Bridge
        if i < len(bridges) and bridges[i] and os.path.exists(bridges[i]):
            br_out = os.path.join(work_dir, f"bridge_{i:02d}.mp4")
            result = make_bridge_video(bridges[i], br_out, i)
            if result:
                parts.append(result)
        elif i < len(segments) - 1:
            if os.path.exists(trans_path):
                parts.append(trans_path)

    # 6. Transition before outro
    if os.path.exists(trans_path):
        parts.append(trans_path)

    # 7. Outro narration
    if audio_paths.get("outro"):
        outro_visual = os.path.join(work_dir, "outro_visual.mp4")
        dur = ffprobe_duration(audio_paths["outro"])
        generate_visual(outro_visual, dur + 1, "PULSE CHECK", "Stay Sovereign.", 64)

        if os.path.exists(outro_visual):
            outro_seg = os.path.join(work_dir, "outro_seg.mp4")
            result = make_segment_video(outro_visual, audio_paths["outro"],
                                        "PULSE CHECK", "Stay Sovereign.",
                                        outro_seg, 99)
            if result:
                parts.append(result)

    # 8. Outro asset
    outro_asset = os.path.join(ASSETS, "outro.mp4")
    if os.path.exists(outro_asset):
        parts.append(outro_asset)

    # 9. Final concatenation
    print(f"\n  [assemble] Concatenating {len(parts)} parts...")
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    result = concatenate_final(parts, output_path)

    if result and os.path.exists(result):
        dur = ffprobe_duration(result)
        sz = os.path.getsize(result)
        print(f"\n  [DONE] Final video: {result}")
        print(f"         Duration: {dur:.1f}s")
        print(f"         Size: {sz / 1024 / 1024:.1f}MB")
        return result

    return ""


def verify_video(path: str) -> bool:
    """Full verification of output video."""
    print(f"\n{'='*60}")
    print(f"VERIFICATION: {os.path.basename(path)}")
    print(f"{'='*60}")

    if not os.path.exists(path):
        print("  [FAIL] File does not exist")
        return False

    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", path],
        capture_output=True, text=True
    )
    try:
        info = json.loads(r.stdout)
    except:
        print(f"  [FAIL] Cannot parse ffprobe output")
        return False

    streams = info.get("streams", [])
    fmt = info.get("format", {})

    vid = next((s for s in streams if s.get("codec_type") == "video"), None)
    aud = next((s for s in streams if s.get("codec_type") == "audio"), None)

    checks = []

    if vid:
        w = int(vid.get("width", 0))
        h = int(vid.get("height", 0))
        codec = vid.get("codec_name", "")
        checks.append(("Video codec", codec == "h264", f"h264 ({codec})"))
        checks.append(("Resolution", w == 1920 and h == 1080, f"{w}x{h}"))
    else:
        checks.append(("Video stream", False, "MISSING"))

    if aud:
        acodec = aud.get("codec_name", "")
        arate = aud.get("sample_rate", "")
        checks.append(("Audio codec", acodec == "aac", f"aac ({acodec})"))
        checks.append(("Sample rate", arate == "44100", f"44100 ({arate})"))
    else:
        checks.append(("Audio stream", False, "MISSING"))

    duration = float(fmt.get("duration", 0))
    size_mb = int(fmt.get("size", 0)) / 1024 / 1024
    checks.append(("Duration", 30 <= duration <= 300, f"{duration:.1f}s"))
    checks.append(("File size", 1 <= size_mb <= 200, f"{size_mb:.1f}MB"))

    if vid and aud:
        vdur = float(vid.get("duration", duration))
        adur = float(aud.get("duration", duration))
        sync_diff = abs(vdur - adur)
        checks.append(("A/V sync", sync_diff < 2.0, f"diff={sync_diff:.2f}s"))

    all_pass = True
    for name, passed, detail in checks:
        status = "PASS" if passed else "FAIL"
        if not passed:
            all_pass = False
        print(f"  [{status}] {name}: {detail}")

    return all_pass


if __name__ == "__main__":
    print("Assembler module — use daily_run.py to run the full pipeline")
