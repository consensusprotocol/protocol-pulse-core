# VIDEO PIPELINE V9 — FIX PROMPT
## Claude Code on Ultron — `~/protocol_pulse/video_pipeline_v3/`

Targeted fixes only. No new features. Fix what's broken, lock what's working.
15-minute rule on any single fix. Tier 1 mandatory. Tier 2 best-effort.

---

## CRITICAL CONTEXT — WHY WAVEFORM + THUMBNAILS DISAPPEARED

The `make_host_visual()` waveform filtergraph is failing silently because the `geq` tech
grid filter is crashing ffmpeg. When it fails, it falls back to `_make_host_visual_fallback()`
which is a bare static bg with NO thumbnails and NO waveform.

**Root fix: Simplify the filtergraph to eliminate the `geq` failure point.**
Remove the `geq` tech grid — replace with a static design that CANNOT fail.
The waveform and thumbnail MUST work on every segment. No fallbacks that lose features.

---

## FIX 1: ROCK-SOLID WAVEFORM + THUMBNAIL (assembler.py) — TIER 1

Replace the `geq` tech grid block entirely. New simplified filtergraph for `make_host_visual()`:

```python
# 1. Deep space base (cannot fail — it's just a color)
fg = f"color=c=0x050510:s=1920x1080:d={total_dur}:r=30[base];\n"

# 2. Subtle gradient overlay — two color blocks, no geq
fg += f"color=c=0x0A0520:s=1920x540:d={total_dur}:r=30[tophalf];\n"
fg += f"[base][tophalf]overlay=0:0[bgbase];\n"

# 3. Thin horizontal accent lines — SIMPLE drawbox, not geq
fg += (f"[bgbase]drawbox=x=0:y=538:w=1920:h=2:color=0x00D4FF@0.35:t=fill"
       f",drawbox=x=0:y=542:w=1920:h=1:color=0x7B2FFF@0.2:t=fill[bglines];\n")

# 4. LEFT SIDE vertical accent bar
fg += f"color=c=0x00D4FF@0.6:s=4x1080:d={total_dur}:r=30[leftbar];\n"
fg += f"[bglines][leftbar]overlay=0:0[bgv0];\n"

# 5. Audio waveform — showwaves driven by TTS audio [0:a]
fg += (f"[0:a]showwaves=s=1800x160:mode=cline:"
       f"colors=0x00D4FF|0x7B2FFF:scale=lin:draw=full:rate=30[wave];\n")

# 6. Mirror waveform for symmetry (top + bottom reflection)
fg += f"[wave]split[w1][w2];\n"
fg += f"[w2]vflip[wflip];\n"
fg += f"[w1][wflip]vstack[wavepair];\n"   # 1800x320 total

# 7. Overlay waveform centered horizontally, vertically centered
fg += f"[bgv0][wavepair]overlay=60:380[withwave];\n"  # y=380 centers the 320px block

# 8. Speaker label bar (bottom left)
fg += f"color=c={color}:s=280x52:d={total_dur}:r=30[spkbg];\n"
fg += (f"[spkbg]drawtext=fontfile={FONT_BOLD}:text='{speaker}':"
       f"fontcolor=white:fontsize=26:x=16:y=12[spklabel];\n")

# 9. Ticker bar (bottom)
fg += f"color=c=0x0A0A0A@0.92:s=1920x44:d={total_dur}:r=30[tickbg];\n"
fg += (f"[tickbg]drawtext=fontfile={FONT_MONO}:text='{ticker_text}':"
       f"fontcolor=0xFFCC00:fontsize=18:x=w-mod(t*80\\,w+tw):y=12[ticker];\n")

# 10. Compose base layers
fg += f"[withwave][spklabel]overlay=40:H-90[v1];\n"
fg += f"[v1][ticker]overlay=0:H-44[v2];\n"
last_v = "v2"

# 11. Watermark top-right
if has_wm:
    fg += f"[{wm_idx}:v]scale=150:-1[wm];\n"
    fg += f"[v2][wm]overlay=W-170:16[v3];\n"
    last_v = "v3"

# 12. Thumbnail PIP — MANDATORY for setup/react — right side
if has_thumb:
    fg += f"[{thumb_idx}:v]scale=720:405,pad=722:407:1:1:color=0x00D4FF@0.8[thumb];\n"
    fg += f"[{last_v}][thumb]overlay=1160:120[vthumb];\n"
    last_v = "vthumb"

# 13. Social segment title card (only for social_segment type)
if is_social:
    safe_text = (text.replace("'", "").replace('"', "")
                     .replace(":", " -").replace(";", ",")
                     .replace("[", "(").replace("]", ")")
                     .replace("\u2014", "-").replace("\u2019", ""))[:100]
    fg += (f"[{last_v}]drawtext=fontfile={FONT_BOLD}:"
           f"text='WHAT THE BITCOIN INTERNET IS SAYING':"
           f"fontcolor=white:fontsize=36:x=(w-text_w)/2:y=80:"
           f"box=1:boxcolor=0x000000@0.65:boxborderw=14[vsoc1];\n")
    fg += (f"[vsoc1]drawtext=fontfile={FONT_MONO}:"
           f"text='{safe_text}':"
           f"fontcolor=0xE0E0E0:fontsize=22:x=(w-text_w)/2:y=h/2:"
           f"box=1:boxcolor=0x111111@0.75:boxborderw=10[vsoc2];\n")
    last_v = "vsoc2"

fg += f"[{last_v}]format=yuv420p[outv];\n"

# Audio
if has_bgm:
    fg += f"[0:a]loudnorm=I=-16:TP=-1.5:LRA=11[tts];\n"
    fg += f"[{bgm_idx}:a]volume=-18dB[bgm];\n"
    fg += f"[tts][bgm]amix=inputs=2:duration=first:weights=1 0.12[outa]"
else:
    fg += f"[0:a]loudnorm=I=-16:TP=-1.5:LRA=11[outa]"
```

**CRITICAL: Remove the `_make_host_visual_fallback()` call from the error path.**
If the main filtergraph fails, log the error AND the full ffmpeg stderr for debugging,
then raise an exception. Do NOT silently fall back to a version that loses thumbnails.
We need to know when it fails so we can fix it, not hide it.

**Test after implementing:** Run a quick ffmpeg test of just the filtergraph:
```bash
ffmpeg -f lavfi -i "sine=frequency=440:duration=3" \
  -filter_complex "color=c=0x050510:s=1920x1080:d=3:r=30[base];[base]drawbox=x=0:y=538:w=1920:h=2:color=0x00D4FF@0.35:t=fill[bglines];[0:a]showwaves=s=1800x160:mode=cline:colors=0x00D4FF|0x7B2FFF:scale=lin:draw=full:rate=30[wave];[wave]split[w1][w2];[w2]vflip[wflip];[w1][wflip]vstack[wavepair];[bglines][wavepair]overlay=60:380[out]" \
  -map "[out]" -f null - 2>&1 | tail -5
```
If this passes, the filtergraph is solid. Then implement in assembler.py.

---

## FIX 2: INTRO — NO TAG VIDEO, COLD OPEN + MUSIC JINGLE (assembler.py) — TIER 1

**PBX wants: No intro clip. Strong opening statement (cold_open TTS) + pp_intro.mp3 playing underneath.**

In `assemble_episode()`, replace the current `make_tag_video(intro_out)` call with:

```python
# INTRO: cold open TTS audio + pp_intro.mp3 jingle underneath
# Find the cold_open audio line (first dialogue entry with type "cold_open")
cold_open_audio = None
for al in audio_lines:
    if al.get("type") == "cold_open" or (audio_idx == 0 and al.get("host") in (1, "1")):
        cold_open_audio = al
        break

if cold_open_audio and os.path.exists(cold_open_audio.get("path", "")):
    intro_out = os.path.join(work_dir, f"part_{part_idx:03d}_intro_coldopen.mp4")
    result = make_intro_coldopen(cold_open_audio["path"], intro_out, btc_price=btc_price)
    if result:
        parts.append(result)
        part_idx += 1
        # Skip this cold_open entry when we process the dialogue loop
        # (mark it consumed so it doesn't double-render)
        cold_open_consumed = True
```

Add function `make_intro_coldopen(tts_path, output_path, btc_price)`:
```python
def make_intro_coldopen(tts_path: str, output_path: str, btc_price: str = "N/A") -> str:
    """
    Intro segment: cold open TTS narration with pp_intro.mp3 jingle underneath.
    Deep space background + waveform + Protocol Pulse branding.
    The jingle plays at full volume, TTS plays over it at slightly lower volume.
    """
    jingle = os.path.join(ASSETS, "music", "pp_intro.mp3")
    tts_dur = ffprobe_duration(tts_path)
    # Pad to at least 4 seconds for the jingle to breathe
    total_dur = max(tts_dur + 1.0, 4.0)
    
    has_jingle = os.path.exists(jingle)
    
    # Background: same deep space design as host visual but BRIGHTER/more dramatic for intro
    fg = f"color=c=0x020208:s=1920x1080:d={total_dur}:r=30[base];\n"
    fg += (f"[base]drawbox=x=0:y=536:w=1920:h=3:color=0x00D4FF@0.5:t=fill"
           f",drawbox=x=0:y=541:w=1920:h=1:color=0x7B2FFF@0.3:t=fill[bglines];\n")
    fg += f"color=c=0x00D4FF@0.8:s=4x1080:d={total_dur}:r=30[leftbar];\n"
    fg += f"[bglines][leftbar]overlay=0:0[bgv0];\n"
    
    # Waveform from TTS
    fg += (f"[0:a]showwaves=s=1800x160:mode=cline:"
           f"colors=0x00D4FF|0x7B2FFF:scale=lin:draw=full:rate=30[wave];\n")
    fg += f"[wave]split[w1][w2];\n[w2]vflip[wflip];\n[w1][wflip]vstack[wavepair];\n"
    fg += f"[bgv0][wavepair]overlay=60:380[withwave];\n"
    
    # Protocol Pulse title (centered, top area)
    fg += (f"[withwave]drawtext=fontfile={FONT_BOLD}:"
           f"text='PROTOCOL PULSE':fontcolor=0x00D4FF:fontsize=72:"
           f"x=(w-text_w)/2:y=80[title];\n")
    fg += (f"[title]drawtext=fontfile={FONT_MONO}:"
           f"text='PULSE CHECK':fontcolor=0xFFFFFF@0.7:fontsize=32:"
           f"x=(w-text_w)/2:y=175[subtitle];\n")
    
    # Watermark
    if os.path.exists(WATERMARK):
        fg += f"[1:v]scale=150:-1[wm];\n"
        fg += f"[subtitle][wm]overlay=W-170:16[outv_pre];\n"
        last_v = "outv_pre"
    else:
        last_v = "subtitle"
    fg += f"[{last_v}]format=yuv420p[outv];\n"
    
    # Audio: TTS + jingle underneath
    if has_jingle:
        fg += f"[0:a]volume=1.0[tts];\n"
        fg += f"[2:a]volume=0.35[jingle];\n"  # jingle at 35% under TTS
        fg += f"[tts][jingle]amix=inputs=2:duration=first:weights=1 0.35[outa]"
        inputs = [tts_path, WATERMARK if os.path.exists(WATERMARK) else tts_path, jingle]
    else:
        fg += f"[0:a]loudnorm=I=-16:TP=-1.5:LRA=11[outa]"
        inputs = [tts_path, WATERMARK if os.path.exists(WATERMARK) else tts_path]
    
    ok = run_ffmpeg_filtergraph(
        inputs, fg, ["[outv]", "[outa]"],
        ["-c:v", "libx264", "-crf", "18", "-preset", "fast",
         "-c:a", "aac", "-ar", "44100", "-b:a", "192k", "-t", str(total_dur)],
        output_path, "intro cold open", 120,
    )
    return output_path if ok else ""
```

In the dialogue loop, skip the cold_open entry if `cold_open_consumed = True`.

---

## FIX 3: OUTRO — NEW BRANDED VIDEO FILE (assembler.py) — TIER 1

PBX is uploading a new outro file to: `~/protocol_pulse/video_pipeline_v3/assets/outro_branded.mp4`

Update:
```python
OUTRO_BRANDED = os.path.join(ASSETS, "outro_branded.mp4")
```

In `assemble_episode()`, replace `make_tag_video(outro_out, narration_audio=wrap_audio)` with:
```python
def make_branded_outro(output_path: str, narration_audio: str = "") -> str:
    """Use PBX's branded outro video. Mix wrap narration audio over it."""
    src = OUTRO_BRANDED if os.path.exists(OUTRO_BRANDED) else TAG_VIDEO
    if not os.path.exists(src):
        return ""
    
    outro_dur = ffprobe_duration(src)
    vf = f"scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1,fps=30,format=yuv420p,fade=t=out:st={max(outro_dur-0.8, outro_dur*0.8):.2f}:d=0.8"
    
    if narration_audio and os.path.exists(narration_audio):
        ok = run_ffmpeg([
            "-i", src, "-i", narration_audio,
            "-filter_complex",
            f"[0:a]volume=0.3[va];[1:a]volume=1.0[vb];[va][vb]amix=inputs=2:duration=longest[outa]",
            "-map", "0:v", "-map", "[outa]",
            "-vf", vf,
            "-c:v", "libx264", "-crf", "20", "-preset", "fast",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-ar", "44100", "-b:a", "192k",
            output_path,
        ], "branded outro", 60)
    else:
        ok = run_ffmpeg([
            "-i", src,
            "-vf", vf,
            "-c:v", "libx264", "-crf", "20", "-preset", "fast",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-ar", "44100", "-b:a", "192k",
            output_path,
        ], "branded outro (no narration)", 60)
    
    return output_path if ok else ""
```

---

## FIX 4: AMERICAN ENGLISH VOICE FOR JESSICA (tts_engine.py) — TIER 1

Charlotte (`XB0fDUnXU5powFXDhCwa`) has a British accent. Replace with American options.

Try in this order — update `tts_engine.py` JESSICA voice_id:
1. `EXAVITQu4vr4xnSDxMaL` — Bella/Sarah: American, clear, professional, young-ish
2. `21m00Tcm4TlvDq8ikWAM` — Rachel: American, calm, Bloomberg-professional

Use Bella first. Keep voice_settings:
```python
"voice_settings": {
    "stability": 0.45,
    "similarity_boost": 0.80,
    "style": 0.20,
    "use_speaker_boost": True
}
```
The `style: 0.20` adds edge and warmth without going theatrical.

Also check `dual_host_tts.py` — it still has the OLD Jessica voice `cgSgspJ2msm6clMCkdW9`.
Update that file too. The active TTS is `tts_engine.py` (imported by daily_producer),
but dual_host_tts.py must also be updated for consistency.

---

## FIX 5: CLIP TIMING — HARDER SILENCE PADDING (clip_extractor.py) — TIER 1

The narrator is still cutting in mid-sentence. The current `find_nearest_pause()` isn't aggressive enough.

Two changes:
1. Increase `search_window` from 4.0 to 6.0 seconds
2. Change silence threshold from `-35dB:d=0.3` to `-30dB:d=0.5` (longer pauses only)
3. Add minimum padding: even if no pause found, always add 2.5s after clip end (not 1.5s)

```python
def find_nearest_pause(clip_path: str, target_end: float, search_window: float = 6.0) -> float:
    result = subprocess.run([
        "ffmpeg", "-i", clip_path,
        "-af", "silencedetect=noise=-30dB:d=0.5",
        "-f", "null", "-"
    ], capture_output=True, text=True, timeout=30)
    
    import re
    pauses = [float(m.group(1)) for m in 
              re.finditer(r"silence_end: ([\d.]+)", result.stderr)]
    
    candidates = [p for p in pauses if target_end <= p <= target_end + search_window]
    return candidates[0] if candidates else target_end + 2.5  # 2.5s minimum buffer
```

---

## EXECUTION ORDER

1. Run ffmpeg waveform test first (see FIX 1) — confirm showwaves works on this machine
2. Apply FIX 1 (waveform + thumbnail — simplified filtergraph, no geq)
3. Apply FIX 4 (American voice — Bella)
4. Apply FIX 5 (clip timing — harder silence padding)
5. Apply FIX 2 (intro — cold open + jingle, no tag video)
6. Apply FIX 3 (outro — branded video, if file exists at assets/outro_branded.mp4)
7. Test render: `python3 daily_producer.py --test --skip-scan 2>&1 | tail -50`
8. Verify: `ls -lh output/$(ls -t output/ | head -1)/work/`
9. Confirm part_001 (cold open intro) renders with waveform visible
10. Git commit + push

## SUCCESS CHECKLIST
- [ ] Waveform VISIBLE on ALL narrator segments (not falling back)
- [ ] Thumbnail PIP showing on setup/react segments
- [ ] Intro = cold open TTS + jingle music underneath, NO tag clip
- [ ] Outro = PBX branded video (or tag fallback) with narrator wrap over it
- [ ] Jessica voice = American (Bella or Rachel, not British Charlotte)
- [ ] Clip audio finishes before narrator cuts in (2.5s buffer minimum)
- [ ] SCP path reported at end
