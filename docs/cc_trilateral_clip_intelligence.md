Read ~/protocol_pulse/PIPELINE_LAWS.md first.
Read ~/protocol_pulse/docs/gospels/TRILATERAL_CLIP_INTELLIGENCE_GOSPEL.md.

TASK: Add independent montage clip selection to the pipeline so the daily montage
uses its own best-moment clips rather than reusing Pulse Check clips.

AUDIT FIRST — read these files completely before touching anything:
  ~/protocol_pulse/video_pipeline_v3/clip_selector.py (find select_clips, line ~360)
  ~/protocol_pulse/video_pipeline_v3/clip_extractor.py (find extract_all, line 643)
  ~/protocol_pulse/video_pipeline_v3/daily_producer.py (find STEP 3 and STEP 4)
  ~/protocol_pulse/services/montage_producer.py (find load_clips, line ~84)
  ~/protocol_pulse/video_pipeline_v3/transcripts/ (transcript cache format)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 1 — ADD select_montage_clips() TO clip_selector.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
After the existing select_clips() function, add a new function:

def select_montage_clips(videos: list) -> dict:
    """
    Independent montage clip selection using local Qwen3-Coder.
    Selects the best 12-22 second standalone moment from each video.
    Completely independent from select_clips() — different timestamps, different criteria.
    Falls back to Pulse Check clip timestamps if Qwen unavailable.
    """
    import requests, json as _json, re as _re

    OLLAMA_URL = "http://localhost:11435"
    MODEL = "qwen3-coder:30b"
    montage_clips = []

    for video in videos:
        video_id = video.get("video_id", "")
        channel = video.get("channel", "")
        title = video.get("title", "")
        timestamped_text = video.get("timestamped_text", "") or video.get("transcript_text", "")

        if not timestamped_text or len(timestamped_text) < 100:
            logger.info(f"[Montage] No transcript for {channel} {video_id}, skipping")
            continue

        prompt = (
            "You are selecting the single best SHORT standalone highlight clip for a daily "
            "Bitcoin media compilation. Viewers have ZERO prior context.\n\n"
            "Select the 12-22 second window that is the most punchy, self-contained, "
            "and quotable moment in this entire video.\n"
            "CRITERIA:\n"
            "- Complete thought — starts and ends at natural sentence boundaries\n"
            "- No context needed to understand it\n"
            "- Single strong statement or striking data point\n"
            "- NOT the same as the Pulse Check clip (find a DIFFERENT moment)\n"
            "- Ideal: starts with a strong noun or number, ends with a period\n\n"
            f"VIDEO: {title}\nCHANNEL: {channel}\n\n"
            f"TIMESTAMPED TRANSCRIPT:\n{timestamped_text[:3000]}\n\n"
            "Return ONLY valid JSON, no markdown:\n"
            "{"montage_start_sec": int, "montage_end_sec": int, "
            ""quote": "exact words spoken", "reason": "why this moment"}"
        )

        try:
            resp = requests.post(
                f"{OLLAMA_URL}/api/chat",
                json={
                    "model": MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                    "options": {"temperature": 0.2},
                },
                timeout=30,
            )
            resp.raise_for_status()
            raw = resp.json().get("message", {}).get("content", "")
            match = _re.search(r"\{[^{}]+\}", raw, _re.DOTALL)
            if match:
                result = _json.loads(match.group())
                start = int(result.get("montage_start_sec", 0))
                end = int(result.get("montage_end_sec", start + 18))
                # Validate reasonable range
                if 0 <= start < end and (end - start) <= 30:
                    montage_clips.append({
                        "rank": len(montage_clips) + 1,
                        "video_id": video_id,
                        "channel": channel,
                        "video_title": title,
                        "start_seconds": start,
                        "end_seconds": end,
                        "quote": result.get("quote", ""),
                        "score": video.get("score", 50),
                        "timestamped_text": timestamped_text,
                        "montage_reason": result.get("reason", ""),
                    })
                    logger.info(f"[Montage] {channel}: {start}s-{end}s — {result.get('quote','')[:60]}")
                    continue
        except Exception as e:
            logger.warning(f"[Montage] Qwen failed for {channel}: {e}")

        # Fallback: use Pulse Check timestamps from existing select_clips output
        # (will be populated after full pipeline runs — skip for now)
        logger.info(f"[Montage] {channel}: using fallback empty (Qwen unavailable)")

    return {"clips": montage_clips}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 2 — ADD extract_montage_clips() TO clip_extractor.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
After extract_all(), add:

def extract_montage_all(montage_selections: dict, output_dir: str) -> dict:
    """Extract montage clips — same as extract_all but uses montage timestamps
    and saves to clips/montage_clip_N_CHANNEL_ID.mp4"""
    os.makedirs(output_dir, exist_ok=True)
    clips = montage_selections.get("clips", [])
    extracted = {}

    for clip in clips:
        rank = clip["rank"]
        video_id = clip["video_id"]
        start = clip["start_seconds"]
        end = clip["end_seconds"]
        channel = clip.get("channel", "unknown").replace(" ", "_")
        output_path = os.path.join(output_dir, f"montage_clip_{rank}_{channel}_{video_id}.mp4")

        try:
            ok = extract_clip(video_id, start, end, output_path, channel)
            if ok and os.path.exists(output_path):
                clip["montage_clip_path"] = output_path
                extracted[rank] = output_path
                logger.info(f"[Montage] Extracted: montage_clip_{rank}_{channel}")
            else:
                logger.warning(f"[Montage] Failed: {channel} {video_id}")
        except Exception as e:
            logger.error(f"[Montage] Error: {channel} {video_id}: {e}")

    return extracted

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 3 — WIRE INTO daily_producer.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
In daily_producer.py, find the import line:
  from clip_extractor import extract_all, check_av_sync

Change to:
  from clip_extractor import extract_all, extract_montage_all, check_av_sync

Find STEP 3 where select_clips(videos) is called (~line 287).
After that line, add:

    # ── STEP 3b: Select independent montage clips (Qwen, free) ──────────
    print("[STEP 3b] SELECTING MONTAGE CLIPS (local Qwen)...")
    try:
        from clip_selector import select_montage_clips
        montage_selections = select_montage_clips(videos)
        montage_clips = montage_selections.get("clips", [])
        montage_sel_path = os.path.join(run_dir, "montage_selections.json")
        with open(montage_sel_path, "w") as f:
            json.dump(montage_selections, f, indent=2)
        print(f"  Montage: {len(montage_clips)} independent clips selected")
    except Exception as e:
        print(f"  Montage selection failed ({e}) — montage will reuse Pulse Check clips")
        montage_selections = None

Find STEP 4 where extract_all(selections, clip_dir) is called (~line 331).
After that block completes, add:

    # ── STEP 4b: Extract montage clips ───────────────────────────────────
    if montage_selections and montage_selections.get("clips"):
        print("[STEP 4b] EXTRACTING MONTAGE CLIPS...")
        try:
            extract_montage_all(montage_selections, clip_dir)
            print(f"  Montage clips extracted to {clip_dir}")
        except Exception as e:
            print(f"  Montage extraction failed ({e}) — skipping")

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 4 — UPDATE montage_producer.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
In load_clips() (~line 84), update to prefer montage_selections.json:

    # Try montage_selections.json first (independent selection)
    montage_sel_path = output_dir / "montage_selections.json"
    sel_path = montage_sel_path if montage_sel_path.exists() else output_dir / "selections.json"
    clips_dir = output_dir / "clips"

When matching clip files, look for montage_clip_N_* files first:
    for clip_file in clips_dir.glob("montage_clip_*.mp4"):
        # parse rank from montage_clip_N_CHANNEL_ID.mp4
        ...
    # Fall back to clip_N_* if no montage clips found
    if not clip_files_by_vid:
        for clip_file in clips_dir.glob("clip_*.mp4"):
            ...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
VALIDATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
python3 -m py_compile video_pipeline_v3/clip_selector.py && echo SELECTOR_OK
python3 -m py_compile video_pipeline_v3/clip_extractor.py && echo EXTRACTOR_OK
python3 -m py_compile video_pipeline_v3/daily_producer.py && echo PRODUCER_OK
python3 -m py_compile services/montage_producer.py && echo MONTAGE_OK
bash ~/protocol_pulse/regression_test.sh

Test Qwen selection on cached transcript:
python3 -c "
import json, sys
sys.path.insert(0, 'video_pipeline_v3')
# Load a cached transcript
import os, glob
transcripts = glob.glob('video_pipeline_v3/transcripts/*.json')
if transcripts:
    with open(transcripts[0]) as f: t = json.load(f)
    from clip_selector import select_montage_clips
    result = select_montage_clips([{'video_id': t.get(chr(105)+chr(100),''), 'channel': 'Test',
        'title': 'Test', 'timestamped_text': t.get('timestamped_text','')}])
    print('Montage clips:', len(result.get('clips',[])))
    if result.get('clips'): print('First clip:', result['clips'][0].get('quote','')[:80])
"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COMMIT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
git add video_pipeline_v3/clip_selector.py video_pipeline_v3/clip_extractor.py
git add video_pipeline_v3/daily_producer.py services/montage_producer.py
git commit -m "feat(trilateral): independent montage clip selection — Qwen selects best standalone moments from same transcripts, montage_selections.json, extract_montage_all(), montage producer prefers independent clips"
git push

DO NOT touch: assembler.py, tts_engine.py, overnight_render_loop.py, gemini_grade.py
PIPELINE LAW: regression_test.sh must show zero FAILs before commit