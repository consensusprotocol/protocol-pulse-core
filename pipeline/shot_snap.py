#!/usr/bin/env python3
"""pipeline/shot_snap.py — a prepared clip never shows a frame of a neighbouring shot outside its speech.

Recut run 6 (V1 "next shot visible before the transition"): Natalie Brunell's source cuts to an
NVIDIA / AMD / MICRON graphic inside the pause before her next sentence ("Nvidia ..." at 37.94 s); the
sentence-law out-point 37.86 s keeps that pause, so the clip's last 3 frames (frame 315 of 318, scene score
0.53) showed the next shot. Orchestrator 08:30: "the visual out-point must not include a frame of the next
shot; snap the visual end to the last frame of the current shot ... audio stays on the sentence."
Rule: a hard shot change (scene score >= SCENE_CUT) AFTER the last word ends (pause_out.start) holds the
last frame before it to the end of the clip; one BEFORE the first word starts (pause_in.end) holds the
first frame after it from the start of the clip. Changes inside the speech are content and untouched.
The audio stream is copied unchanged and the frame count is unchanged, so every cut time, G16/G17/G18
measurement and the A/V lock stay as they were."""
import os
import re
import subprocess

SCENE_CUT = 0.3          # run 6 clip_02: hard cuts 0.525-0.584, on-screen graphic animation 0.055-0.058


def scene_changes(path):
    """[(frame_index, scene_score)] of every frame whose scene score is >= SCENE_CUT."""
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-an", "-vf",
                        "select='gte(scene,0)',metadata=print:key=lavfi.scene_score:file=-", "-f", "null", "-"],
                       capture_output=True, text=True, check=True, timeout=600)
    out = re.findall(r"frame:(\d+)\s+pts:\S+\s+pts_time:\S+\s+lavfi\.scene_score=([0-9.]+)", r.stdout)
    return [(int(f), float(s)) for f, s in out if float(s) >= SCENE_CUT]


def frame_count(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries",
                        "stream=nb_read_frames", "-of", "csv=p=0", path], capture_output=True, text=True,
                       check=True, timeout=300)
    return int(r.stdout.strip().split(",")[0])


def plan(changes, n_frames, fps, speech_on_s, speech_off_s):
    """(head_frames, tail_frame): frames [0, head_frames) take frame head_frames; frames [tail_frame, n)
    take frame tail_frame - 1. head_frames = 0 / tail_frame = n_frames when nothing is snapped."""
    head = max([f for f, _ in changes if speech_on_s is not None and f / fps < speech_on_s] or [0])
    tails = [f for f, _ in changes if speech_off_s is not None and f / fps > speech_off_s]
    tail = min(tails) if tails else n_frames
    if head >= tail:                              # never empty a clip: no snap is safer than a broken clip
        return 0, n_frames
    return head, tail


def apply(clip, cut, fps, qp):
    """Snap qa/final_<clip>.mp4 in place when a neighbouring shot shows outside the speech. Returns a record
    (always), {"snapped": False, ...} when nothing changed."""
    pad = float(cut.get("lead_in_pad_s") or 0.0)
    pin, pout = cut.get("pause_in") or {}, cut.get("pause_out") or {}
    on = (pin["end"] - cut["cut_in"] + pad) if "end" in pin else None
    off = (pout["start"] - cut["cut_in"] + pad) if "start" in pout else None
    changes = scene_changes(clip)
    n = frame_count(clip)
    head, tail = plan(changes, n, fps, on, off)
    rec = {"speech_on_s": None if on is None else round(on, 3), "speech_off_s": None if off is None else round(off, 3),
           "hard_cuts": [(f, round(s, 3)) for f, s in changes], "frames": n, "snapped": False}
    if head == 0 and tail == n:
        return rec
    import gpu0
    gpu0.swap_to("nvenc")                # L-r: NVENC only under the GPU0 lease, nothing else resident (an encode follows)
    vf = f"trim=start_frame={head}:end_frame={tail},setpts=PTS-STARTPTS,tpad=start_mode=clone:start={head}:" \
         f"stop_mode=clone:stop={n - tail}"
    part = clip + ".snap.mp4"
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", clip, "-map", "0:v:0", "-map", "0:a:0", "-vf", vf,
                        "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "constqp", "-qp", str(qp), "-pix_fmt", "yuv420p",
                        "-r", str(fps), "-c:a", "copy", "-movflags", "+faststart", part], capture_output=True, timeout=600)
    if r.returncode != 0:                      # L-r: stderr captured so an NVENC out-of-memory is named, not renamed
        gpu0.raise_if_oom(r, "shot_snap nvenc")
        print(r.stderr.decode(errors="replace")[-2000:], flush=True)
        raise subprocess.CalledProcessError(r.returncode, r.args, r.stdout, r.stderr)
    if frame_count(part) != n:
        os.remove(part)
        raise RuntimeError(f"shot snap changed the frame count of {clip}")
    os.replace(part, clip)
    rec.update(snapped=True, held_head_frames=head, held_tail_frames=n - tail,
               why=(f"head: frames 0-{head - 1} were the previous shot, held on frame {head}; " if head else "") +
                   (f"tail: frames {tail}-{n - 1} were the next shot, held on frame {tail - 1}" if tail < n else ""))
    return rec
