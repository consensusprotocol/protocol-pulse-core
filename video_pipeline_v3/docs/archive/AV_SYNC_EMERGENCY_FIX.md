# EMERGENCY FIX — AV SYNC ROOT CAUSE
## Read this entire file before touching anything

---

## WHAT IS ACTUALLY WRONG

The `fix_av_sync()` function EXISTS and IS being called. But it is NOT fixing the problem.
Here is why:

### ROOT CAUSE: `bestvideo+bestaudio` separate stream merge

The yt-dlp command uses:
```
-f "bestvideo[height<=1080]+bestaudio/best[height<=1080]"
```

This downloads VIDEO and AUDIO as **separate streams** and merges them with ffmpeg muxer.
When yt-dlp does this merge, the video stream often has a non-zero start_pts and the
audio stream starts at 0 — they are ALREADY out of sync before our fix runs.

`+genpts` regenerates PTS but does NOT fix the underlying start time mismatch.
`aresample=async=1` shifts audio slightly but NOT enough for a 1-second drift.

The check_av_sync() function measures `start_time` from ffprobe streams.
But `start_time=0` for both does NOT mean they are in sync — it means the container
says they both start at 0. The ACTUAL drift is in the encoded frame timestamps (DTS),
not the container start_time. That's why the diagnosis said "neither root cause active"
— it was measuring the wrong thing.

### THE REAL FIX: Force single-format download OR use ffmpeg to re-mux with explicit sync

**Option A (preferred): Force yt-dlp to download a pre-muxed format**
```python
"-f", "best[height<=1080][ext=mp4]/bestvideo[height<=1080]+bestaudio/best",
```
This prefers a pre-merged mp4 (no separate stream merging) which has correct sync.
Only falls back to separate streams if no pre-merged format exists.

**Option B: Fix the merge with explicit ffmpeg re-encode using -itsoffset**
After yt-dlp downloads, probe the actual video start DTS and compensate:
```bash
ffprobe -v quiet -print_format json -show_packets -read_intervals "%+#5" input.mp4
```
Look at the first video packet's pts_time vs first audio packet's pts_time.
The difference is the actual drift. Apply it as `-itsoffset`.

**Option C (nuclear, guaranteed): Re-encode both streams from scratch**
```python
ffmpeg -fflags +genpts+igndts -i input.mp4 \
  -map 0:v:0 -map 0:a:0 \
  -c:v libx264 -crf 20 -preset fast -r 30 -vsync cfr \
  -vf "setpts=PTS-STARTPTS" \    # <-- THIS IS THE KEY LINE MISSING FROM CURRENT FIX
  -c:a aac -ar 48000 -ac 2 \
  -af "asetpts=PTS-STARTPTS" \   # <-- AND THIS
  -avoid_negative_ts make_zero \
  output.mp4
```

`setpts=PTS-STARTPTS` and `asetpts=PTS-STARTPTS` RESET both video and audio PTS
to start from zero independently. This is the correct fix for drift caused by
non-zero start PTS in either stream. The current fix is missing both of these.

---

## THE FIX — DO THIS NOW

### Step 1: Update `fix_av_sync()` in clip_extractor.py

Replace the entire `fix_av_sync` function with this:

```python
def fix_av_sync(input_path: str, output_path: str) -> bool:
    """
    Fix audio/video sync by resetting both stream PTS to zero independently.
    The key fix is setpts=PTS-STARTPTS and asetpts=PTS-STARTPTS which forces
    both streams to start from absolute zero, eliminating any drift from
    separate-stream yt-dlp merges.
    """
    return _run_ffmpeg([
        "-fflags", "+genpts+igndts",
        "-i", input_path,
        "-map", "0:v:0",
        "-map", "0:a:0",
        "-c:v", "libx264", "-crf", "20", "-preset", "fast",
        "-r", "30", "-vsync", "cfr",
        "-vf", "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1,fps=fps=30,format=yuv420p,setpts=PTS-STARTPTS",
        "-c:a", "aac", "-ar", "48000", "-ac", "2",
        "-af", "asetpts=PTS-STARTPTS,aresample=async=1:min_hard_comp=0.100000:first_pts=0",
        "-avoid_negative_ts", "make_zero",
        "-movflags", "+faststart",
        output_path,
    ], "av_sync_fix", 180)
```

### Step 2: Update yt-dlp format selection in clip_extractor.py

Change the format string from:
```python
"-f", "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
```
To:
```python
"-f", "best[height<=1080][ext=mp4]/bestvideo[height<=1080]+bestaudio/best[height<=1080]",
```

Do this for BOTH Method 1 and Method 2 (the fallback download).

### Step 3: Update check_av_sync() to measure DTS not start_time

Replace the current check with packet-level measurement:
```python
def check_av_sync(clip_path: str) -> float:
    """Measure actual AV sync using first packet DTS timestamps."""
    result = subprocess.run([
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_packets", "-read_intervals", "%+#10",
        clip_path
    ], capture_output=True, text=True)
    try:
        import json as _json
        data = _json.loads(result.stdout)
        packets = data.get("packets", [])
        v_dts = next((float(p.get("dts_time", 0)) for p in packets if p.get("codec_type") == "video"), 0)
        a_dts = next((float(p.get("dts_time", 0)) for p in packets if p.get("codec_type") == "audio"), 0)
        offset = a_dts - v_dts
        logger.info(f"AV packet-level offset for {os.path.basename(clip_path)}: {offset:+.3f}s")
        if abs(offset) > 0.05:
            logger.warning(f"WARNING: AV offset {offset:+.3f}s exceeds 0.05s threshold after fix")
        return offset
    except Exception as e:
        logger.warning(f"Could not measure AV sync: {e}")
        return 0.0
```

### Step 4: Add sync validation GATE — reject clips that are still out of sync

After calling fix_av_sync and check_av_sync, add a hard gate:
```python
offset = check_av_sync(output_path)
if abs(offset) > 0.15:  # 150ms is visible to human eye
    logger.error(f"CLIP REJECTED: AV offset {offset:+.3f}s after fix. Clip unusable.")
    # Try one more time with nuclear option
    nuclear_tmp = output_path + ".nuclear.mp4"
    if _run_ffmpeg([
        "-fflags", "+genpts+igndts+discardcorrupt",
        "-i", output_path,
        "-map", "0:v:0", "-map", "0:a:0",
        "-c:v", "libx264", "-crf", "22", "-preset", "fast",
        "-r", "30", "-vsync", "cfr",
        "-vf", "setpts=PTS-STARTPTS,scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1,format=yuv420p",
        "-c:a", "aac", "-ar", "48000", "-ac", "2",
        "-af", "asetpts=PTS-STARTPTS",
        "-avoid_negative_ts", "make_zero",
        nuclear_tmp,
    ], "av_sync_nuclear", 180) and os.path.exists(nuclear_tmp):
        os.replace(nuclear_tmp, output_path)
        final_offset = check_av_sync(output_path)
        logger.info(f"Nuclear re-encode: final offset {final_offset:+.3f}s")
```

---

## ALSO FIX: make_clip_visual() in assembler.py

The clip visual also re-encodes the clip. It must preserve the sync fix.
Currently it uses a filtergraph that processes video only and passes audio through
`loudnorm`. The loudnorm filter can introduce latency. Replace with:

```python
# In make_clip_visual(), change the audio filter from:
f"[0:a]loudnorm=I=-16:TP=-1.5:LRA=11[outa]"
# To:
f"[0:a]asetpts=PTS-STARTPTS,volume=1.0[outa]"
```

The loudnorm filter adds up to 200ms of lookahead delay which can re-introduce
drift on clips that were perfectly synced before make_clip_visual ran.

---

## EXECUTION ORDER

1. Update fix_av_sync() — add setpts=PTS-STARTPTS and asetpts=PTS-STARTPTS
2. Update yt-dlp format string — prefer pre-muxed format
3. Update check_av_sync() — packet-level DTS measurement
4. Add sync validation gate with nuclear fallback
5. Update make_clip_visual() — remove loudnorm, use asetpts+volume
6. Clear the clip cache so fresh downloads go through the new fix:
   `rm -rf ~/protocol_pulse/video_pipeline_v3/downloads/clip_cache/*`
7. Run test render: `python3 daily_producer.py --test --skip-scan 2>&1 | tail -60`
8. Check the log output for AV offset lines — they must all show < 0.05s
9. bash regression_test.sh — zero FAILs before commit
10. Git commit + report SCP path

## THE LOG LINE TO LOOK FOR
After the fix, every clip should log something like:
```
AV packet-level offset for clip_001.mp4: +0.000s
AV packet-level offset for clip_002.mp4: +0.000s
```
If you see anything > 0.05s, the clip is still drifted and the nuclear fallback fired.
If nuclear also fails, log it as UNRECOVERABLE and skip that clip.

## MANDATORY FINAL STEP
```bash
bash ~/protocol_pulse/video_pipeline_v3/regression_test.sh
```
Zero FAILs required. No exceptions.
Report SCP path of new render.
