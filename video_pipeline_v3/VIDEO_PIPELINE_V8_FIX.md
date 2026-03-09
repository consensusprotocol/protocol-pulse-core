# VIDEO PIPELINE V8 — FIX PROMPT
## Claude Code on Ultron — `~/protocol_pulse/video_pipeline_v3/`

PBX reviewed V7. Good progress — structure works, thumbnails work, tag.mp4 works.
Now fix the remaining issues. Tier 1 mandatory. 15-minute rule on complex fixes.

---

## FIX 1: INTRO + DOUBLE OUTRO — USE tag_vertical.mp4 FOR BOTH (assembler.py)

**Problem:** Intro logo still not showing. There are now TWO outros — the generic one AND tag_vertical.mp4.

**Fix:**
- Remove `make_outro_video()` entirely from `assemble_episode()` parts list
- Use `make_tag_video()` as BOTH the intro AND the final outro
- The episode now starts with tag_vertical.mp4 (fades in from black) and ends with tag_vertical.mp4 (fades to black)
- In `assemble_episode()`:
  - Part 0: `make_tag_video(intro_out)` — tag as intro
  - Final part: `make_tag_video(outro_out)` — tag as outro
- `make_tag_video()` already exists — just call it for both slots
- Add 0.5s fade-in at start, 0.5s fade-to-black at end inside `make_tag_video()`
- Remove all calls to `make_intro_video()` and `make_outro_video()` — they are replaced

**Narrator outro line:** The WRAP dialogue segment (last host line) should play OVER the outro tag video simultaneously. Implement by making the outro tag video use the wrap TTS audio mixed in:
- In `assemble_episode()`, when building the outro tag part, check if the last dialogue entry is `type: "wrap"` and if so, pass its audio path to `make_tag_video()` to mix in
- Signature: `make_tag_video(output_path: str, narration_audio: str = "") -> str`
- If `narration_audio` provided, mix it at full volume over the tag video's natural audio using amix

---

## FIX 2: AUDIO SYNC FIX FOR YOUTUBE CLIPS (clip_extractor.py)

**Problem:** Saylor/Brunell clip has video ahead of audio — mouths move before words come out.

**Fix:** In `clip_extractor.py`, when re-encoding the clip with ffmpeg, add audio delay correction:
- Add `-af "aresample=async=1:min_hard_comp=0.100000:first_pts=0"` to normalize audio timing
- Also add `-vsync 1` to fix video frame timing
- AND ensure the clip is extracted with `-avoid_negative_ts make_zero` flag
- If the clip has a known A/V offset (detectable via ffprobe), apply `-itsoffset` correction

Specifically, after downloading with yt-dlp, run a sync-fix pass:
```python
def fix_av_sync(input_path: str, output_path: str) -> bool:
    """Fix audio/video sync issues common in downloaded YouTube clips."""
    return run_ffmpeg([
        "-i", input_path,
        "-c:v", "libx264", "-crf", "20", "-preset", "fast",
        "-r", "30", "-vf", "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1,fps=30,format=yuv420p",
        "-c:a", "aac", "-ar", "44100", "-ac", "2",
        "-af", "aresample=async=1:min_hard_comp=0.100000:first_pts=0",
        "-vsync", "1",
        "-avoid_negative_ts", "make_zero",
        output_path,
    ], "av_sync_fix", 120)
```
Call this after downloading each clip before returning the path.

---

## FIX 3: REPLACE BACKGROUND LOOP VIDEOS WITH DESIGNED VISUALIZER BACKGROUND (assembler.py)

**Problem:** PBX doesn't like the rotating background video loops.

**New design:** Replace ALL background video loops with a single designed dark background + real-time audio waveform visualizer. This should look 2026 cutting-edge.

**Implementation using ffmpeg filters only (no extra assets needed):**

Replace `make_host_visual()` background generation with this ffmpeg filter approach:

```
Background: Deep space dark gradient — color=c=0x050510:s=1920x1080 (near-black deep navy)
+ Subtle grid overlay using geq filter for a tech grid pattern
+ Audio waveform: showwaves=s=1920x200:mode=cline:colors=0x00D4FF|0x7B2FFF:scale=lin
  positioned at y=440 (vertical center), full width
+ Below waveform: mirror the waveform inverted for symmetry (vflip on the waveform)
+ Thin horizontal accent line at y=540 (center), color 0x00D4FF@0.4, 1px
+ Speaker name bar bottom-left: red for Jessica (#FF3333), blue for Chris (#3388FF)
+ BTC price ticker bottom strip
+ Watermark top-right
+ Thumbnail PIP right side (when present)
```

The waveform is driven by the actual TTS audio input — it's REAL, not faked.

Full ffmpeg filter_complex approach:
```python
# Generate the visual background with waveform from TTS audio
bg_filter = (
    # Deep space background
    f"color=c=0x050510:s=1920x1080:d={total_dur}[base];"
    # Tech grid (subtle lines every 120px)
    f"[base]geq=lum='if(eq(mod(X,120),0),30,if(eq(mod(Y,120),0),30,lum(X,Y)))'"
    f":cb='cb(X,Y)':cr='cr(X,Y)'[grid];"
    # Waveform from audio input [1:a] — full width, 200px tall, centered
    f"[1:a]showwaves=s=1920x200:mode=cline:colors=0x00D4FF|0x7B2FFF"
    f":scale=lin:draw=full[wave];"
    # Mirror waveform for symmetry
    f"[wave]split[w1][w2];"
    f"[w2]vflip[wflip];"
    # Stack wave + mirror
    f"[w1][wflip]vstack[wavepair];"
    # Overlay waveform pair centered vertically on grid bg
    f"[grid][wavepair]overlay=0:340[withwave];"  # y=340 centers 400px wave block
)
```

**If the showwaves filter approach causes errors, fall back to a static designed background:**
```python
# Fallback: static dark navy bg with a pulsing circle (audio-driven opacity via volume detection)
# Use: color=c=0x050510:s=1920x1080 + drawtext for speaker + a static accent bar
```

Key point: **No more video file backgrounds.** The `BACKGROUNDS` list and `_episode_bg` global can be removed entirely. The background is now generated procedurally from the TTS audio signal.

---

## FIX 4: SMARTER CLIP END TIMING — NO MID-SENTENCE CUT-INS (clip_extractor.py + clip_selector.py)

**Problem:** Narrator jumps in while River podcast host is still mid-sentence.

**Fix in `clip_extractor.py`:** After extracting a clip, use ffmpeg silence detection to find the nearest natural pause AFTER the specified end time, then trim there:

```python
def find_nearest_pause(clip_path: str, target_end: float, search_window: float = 4.0) -> float:
    """
    Find nearest silence/pause after target_end within search_window seconds.
    Returns adjusted end time at a natural pause point.
    """
    result = subprocess.run([
        "ffmpeg", "-i", clip_path,
        "-af", f"silencedetect=noise=-35dB:d=0.3",
        "-f", "null", "-"
    ], capture_output=True, text=True, timeout=30)
    
    # Parse silence_end timestamps from stderr
    import re
    pauses = [float(m.group(1)) for m in 
              re.finditer(r"silence_end: ([\d.]+)", result.stderr)]
    
    # Find first pause AFTER target_end within search_window
    candidates = [p for p in pauses if target_end <= p <= target_end + search_window]
    return candidates[0] if candidates else target_end + 1.5  # fallback: +1.5s
```

Call `find_nearest_pause()` on each downloaded clip and trim to that point before returning.

Also add a rule to `clip_selector.py` Claude prompt: "When specifying clip end times, always allow 3-4 seconds of buffer AFTER the key statement ends so the narrator never interrupts a sentence in progress."

---

## FIX 5: NARRATOR TONE — CONVERSATIONAL INVESTIGATIVE JOURNALIST (script_writer.py)

**Update SCRIPT_PROMPT tone rules to add:**

```
DELIVERY RULES:
- ALWAYS open setup lines with a natural verbal bridge: "Ok so—", "Right, and—", "Here's the thing—", "Check this out—", "So—". Never start cold.
- The setup is a LAY-UP for the clip. Tease the knockout moment. Don't explain the whole clip.
- React lines start with a reaction word: "Yeah.", "Exactly.", "Wild.", "That's the tell.", "100%.", "I mean—"
- Tone = investigative gossip journalist who happens to understand Austrian economics. 
- Think Page Six but for Bitcoin. Sharp. Knowing. Never neutral.
- Max 2 sentences per setup or react. Ruthlessly cut anything that sounds like a press release.
```

---

## FIX 6: JESSICA VOICE — YOUNGER, EDGIER, BLOOMBERG-SEXY (tts_engine.py or dual_host_tts.py)

**Change Jessica's voice from Deborah (`VeCVR24o7g2y1IxLJzZs`) to one of these — try in order:**

1. **Charlotte** — `XB0fDUnXU5powFXDhCwa` — Young, confident, British-American crossover. Smart energy.
2. **Lily** — `pFZP5JQG7iQjIQuC4Bku` — Edgy, younger, punchy

Try Charlotte first. Keep voice_settings: `stability: 0.45, similarity_boost: 0.80, style: 0.15, use_speaker_boost: true`

The `style: 0.15` adds a slight emotional edge without going over the top.

---

## EXECUTION ORDER

1. Read: `assembler.py`, `clip_extractor.py`, `script_writer.py`, `tts_engine.py` or `dual_host_tts.py`
2. Apply FIX 1 (intro/outro — tag_vertical for both, remove double outro) — TIER 1
3. Apply FIX 2 (AV sync) — TIER 1
4. Apply FIX 5 (narrator tone) — TIER 1
5. Apply FIX 6 (Charlotte voice) — TIER 1
6. Apply FIX 3 (waveform visualizer bg) — TIER 2, 15-min rule
7. Apply FIX 4 (smart clip timing) — TIER 2, 15-min rule
8. Test render: `python3 daily_producer.py --test --skip-scan 2>&1 | tail -60`
9. Verify parts list and check that part_000 is NOT black
10. Git commit + push

## SUCCESS CHECKLIST
- [ ] tag_vertical.mp4 plays as BOTH intro AND outro
- [ ] NO generic outro card — only tag_vertical.mp4
- [ ] Narrator wrap line plays OVER outro tag video
- [ ] Saylor clip audio in sync with video
- [ ] Visualizer waveform OR clean static bg (no rotating video loops)
- [ ] Narrator setup lines start with "Ok so—" / "Right—" / "Here's the thing—" style openers
- [ ] Jessica voice is Charlotte or Lily (not Deborah)
- [ ] SCP download path reported at end
