#!/usr/bin/env python3
"""boomers_clip.py — Bitcoin Boomers short-clip generator (Fable5 2026-07-02).

Uses the FIXED word-level boundary detection (find_optimal_start /
find_optimal_end_words) that resolved the months-long mid-sentence-cut problem
on Cypherpunk'd, applied to Bitcoin Boomers episodes with Boomers branding.

Flow per video:
  1. word-transcribe (faster-whisper large-v3, word timestamps) -> words.json
  2. Qwen picks best moments from the SRT (30-90s each)
  3. snap each moment to clean sentence start + resolved sentence end
  4. render 9x16 with Boomers branding + outro via full_pipeline_render (nvenc)

Resumable: existing clips are skipped. Progress + manifest written per run.
Run:  python3 boomers_clip.py            # all episodes in videos/
      python3 boomers_clip.py EP6_JOE_KELLY   # single episode
"""
import os, sys, json, time, re, subprocess

sys.path.insert(0, os.path.expanduser("~/boomers_pipeline"))
os.chdir(os.path.expanduser("~/boomers_pipeline"))

from core.word_transcribe import transcribe
from core.punchline_detector import load_words, find_optimal_start, find_optimal_end_words
from core.post_production import full_pipeline_render

CHANNEL = "bitcoin_boomers"
BASE = os.path.expanduser("~/boomers_pipeline")
CH = os.path.join(BASE, "channels", CHANNEL)
VIDEO_DIR = os.path.join(CH, "videos")
PROC_DIR = os.path.join(CH, "processing")
OUT_DIR = os.path.expanduser("~/protocol_pulse/static/boomers_clips_v2")
OUTRO = os.path.join(BASE, "assets/branding/bitcoin_boomers/outro_tag.mp4")
WATERMARK = os.path.join(BASE, "assets/branding/bitcoin_boomers/watermark.png")
CONFIG = json.load(open(os.path.join(CH, "config.json")))
SKIP_INTRO = int(CONFIG.get("skip_intro_seconds", 120))
MIN_DUR = int(CONFIG.get("min_clip_duration", 15))
MAX_DUR = int(CONFIG.get("max_clip_duration", 150))
LOG_PATH = os.path.join(CH, "boomers_clip.log")
PROGRESS = os.path.join(CH, "boomers_clip_progress.json")
MANIFEST = os.path.join(CH, "boomers_clip_manifest.json")

os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(PROC_DIR, exist_ok=True)
ONLY = sys.argv[1] if len(sys.argv) > 1 else None


def log(m):
    line = time.strftime("[%Y-%m-%d %H:%M:%S] ") + m
    print(line, flush=True)
    with open(LOG_PATH, "a") as f:
        f.write(line + "\n")


def save_progress(d):
    d["updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(PROGRESS, "w") as f:
        json.dump(d, f, indent=1)


def query_qwen(prompt, timeout=300):
    data = json.dumps({
        "model": "qwen3-coder:30b", "prompt": prompt, "stream": False,
        "options": {"num_predict": 2000, "temperature": 0.3},
    }).encode()
    req = __import__("urllib.request", fromlist=["request"]).Request(
        "http://localhost:11434/api/generate", data=data,
        headers={"Content-Type": "application/json"})
    import urllib.request as _ur
    with _ur.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode()).get("response", "")


PROMPT = """You are a viral clip editor for a Bitcoin roundtable podcast called
Bitcoin Boomers (hosts Gary Leland, Lawrence Lepard, Bob Burnett). Analyze this
transcript and identify the 5 best moments for short vertical clips (30-90s each).

RULES:
- Each moment must be a self-contained story, revelation, or strong statement
- Prefer strong emotional impact: controversy, surprise, conviction, humor, wisdom
- Skip intros, sponsor reads, and small talk
- For each: start_seconds, end_seconds, hook_text (compelling 8-12 word title)
- hook_text formula: [Authority/Action] + [Shocking/Compelling claim]

RESPOND ONLY IN THIS JSON FORMAT, no other text:
[
  {"start": 120, "end": 190, "hook": "Why the Fed Cannot Stop What Is Coming"},
  {"start": 450, "end": 530, "hook": "This Veteran Investor Just Called the Top"}
]

VIDEO TITLE: %s
VIDEO DURATION: %d seconds

TRANSCRIPT:
%s"""


def find_videos():
    vids = []
    for f in sorted(os.listdir(VIDEO_DIR)):
        if not f.endswith(".mp4"):
            continue
        vid = f[:-4]
        if ONLY and vid != ONLY:
            continue
        vids.append({"id": vid, "path": os.path.join(VIDEO_DIR, f)})
    return vids


def get_duration(path):
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                            "format=duration", "-of", "csv=p=0", path],
                           capture_output=True, text=True, timeout=30)
        return int(float(r.stdout.strip()))
    except Exception:
        return 0


def main():
    log("=" * 64)
    log("BITCOIN BOOMERS CLIPPER | fixed word-boundaries + nvenc")
    log("=" * 64)

    # free GPU for whisper large-v3
    try:
        subprocess.run(["ollama", "stop", "qwen3-coder:30b"], capture_output=True, timeout=30)
    except Exception:
        pass

    videos = find_videos()
    log("Videos to process: %d" % len(videos))

    # PHASE 1+2: word-transcribe
    for v in videos:
        out_dir = os.path.join(PROC_DIR, v["id"])
        os.makedirs(out_dir, exist_ok=True)
        v["dur"] = get_duration(v["path"])
        log("Transcribing %s (%ds)..." % (v["id"], v["dur"]))
        t0 = time.time()
        try:
            res = transcribe(v["path"], out_dir)
            v["words"] = res["words"]
            v["srt"] = res["srt"]
            log("  words.json ready (%s) in %ds"
                % ("cached" if res.get("skipped") else "fresh", time.time() - t0))
        except Exception as e:
            log("  TRANSCRIBE ERROR: %s" % e)
            v["words"] = None

    # PHASE 3: moments via Qwen
    all_clips = []
    for v in videos:
        if not v.get("words") or not v.get("srt"):
            continue
        srt_text = open(v["srt"]).read()
        sample = (srt_text[:8000] + "\n...[MIDDLE OMITTED]...\n" + srt_text[-4000:]
                  if len(srt_text) > 15000 else srt_text)
        log("Finding moments in %s..." % v["id"])
        try:
            resp = query_qwen(PROMPT % (v["id"], v["dur"], sample))
            mm = re.search(r"\[.*\]", resp, re.DOTALL)
            if not mm:
                log("  no JSON in Qwen response")
                continue
            moments = json.loads(mm.group())
            for m in moments:
                m["video_id"] = v["id"]
                m["video_path"] = v["path"]
                m["words_path"] = v["words"]
                m["srt_path"] = v["srt"]
            all_clips.extend(moments)
            log("  %d moments" % len(moments))
        except Exception as e:
            log("  MOMENTS ERROR: %s" % e)

    with open(os.path.join(PROC_DIR, "all_moments.json"), "w") as f:
        json.dump(all_clips, f, indent=2)
    log("Total moments: %d" % len(all_clips))

    # PHASE 4: render with fixed boundaries + nvenc
    rendered = failed = skipped = 0
    manifest = []
    for idx, clip in enumerate(all_clips, 1):
        try:
            raw_s, raw_e = float(clip["start"]), float(clip["end"])
        except Exception:
            skipped += 1
            continue
        if raw_s < SKIP_INTRO:
            log("  clip%03d SKIP intro reel (%.0fs)" % (idx, raw_s))
            skipped += 1
            continue
        words = load_words(clip["words_path"])
        try:
            opt_s = find_optimal_start(words, raw_s)
            opt_e = find_optimal_end_words(words, raw_e)
        except Exception as e:
            log("  clip%03d boundary error %s -- raw" % (idx, e))
            opt_s, opt_e = raw_s, raw_e + 1.0
        dur = opt_e - opt_s
        if dur < MIN_DUR:
            log("  clip%03d too short %.0fs -- skip" % (idx, dur))
            skipped += 1
            continue
        if dur > MAX_DUR:
            opt_e = opt_s + MAX_DUR
            dur = MAX_DUR

        hook = re.sub(r"[^a-zA-Z0-9 ]", "", clip.get("hook", "clip"))[:40].strip().replace(" ", "_").lower()
        vid_out = os.path.join(OUT_DIR, clip["video_id"])
        os.makedirs(vid_out, exist_ok=True)
        out = os.path.join(vid_out, "clip%03d_%s_9x16.mp4" % (idx, hook))
        if os.path.exists(out) and os.path.getsize(out) > 100000:
            log("  clip%03d exists -- skip" % idx)
            rendered += 1
            manifest.append({"clip": idx, "video_id": clip["video_id"], "file": out,
                             "start": opt_s, "end": opt_e, "hook": clip.get("hook", "")})
            continue

        log("  clip%03d %s (%.0fs)" % (idx, clip.get("hook", "?")[:48], dur))
        t0 = time.time()
        try:
            ok = full_pipeline_render(
                clip["video_path"], clip["srt_path"], opt_s, dur, out,
                outro_path=OUTRO, hook_text=clip.get("hook", ""),
                channel=CHANNEL, video_codec="nvenc", ffmpeg_timeout=1800)
            if ok and os.path.exists(out):
                sz = os.path.getsize(out) / 1e6
                log("    OK %.1fMB in %ds" % (sz, time.time() - t0))
                rendered += 1
                manifest.append({"clip": idx, "video_id": clip["video_id"], "file": out,
                                 "start": round(opt_s, 1), "end": round(opt_e, 1),
                                 "duration": round(dur, 1), "hook": clip.get("hook", ""),
                                 "size_mb": round(sz, 1)})
            else:
                log("    RENDER FAILED")
                failed += 1
        except Exception as e:
            log("    ERROR: %s" % e)
            failed += 1
        save_progress({"rendered": rendered, "failed": failed, "skipped": skipped,
                       "total_moments": len(all_clips), "processed": idx})

    with open(MANIFEST, "w") as f:
        json.dump(manifest, f, indent=1)
    log("DONE. rendered=%d failed=%d skipped=%d of %d" % (rendered, failed, skipped, len(all_clips)))


if __name__ == "__main__":
    main()
