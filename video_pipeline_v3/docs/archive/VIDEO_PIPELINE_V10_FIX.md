# VIDEO PIPELINE V10 — FIX PROMPT
## Claude Code on Ultron — `~/protocol_pulse/video_pipeline_v3/`
## READ PIPELINE_LAWS.md and AGENT_HANDOFF_NOTE.md BEFORE TOUCHING ANYTHING

---

## BRAND COLORS — PROTOCOL PULSE PALETTE
Red = #CC0000 (primary accent — replaces ALL cyan/blue)
White = #FFFFFF (text)
Black/near-black = #0A0A0A (background base)
Dark red accent = #880000 (secondary)
Gold ticker = #FFD700 (keep — works on dark bg)
BANNED colors: #00D4FF (cyan), #7B2FFF (purple), #3388FF (host blue)

---

## FIX 1: BRAND COLORS THROUGHOUT (assembler.py) — TIER 1

Replace ALL occurrences of the cyan/purple/blue palette with Protocol Pulse red/black/white.

**In `make_host_visual()` and `make_intro_coldopen()`:**

```python
# OLD → NEW color mappings:
# 0x050510  → 0x0A0000  (near-black with red tint base)
# 0x0A0520  → 0x100000  (dark red-tinted top half)
# 0x00D4FF  → 0xCC0000  (cyan accent → red accent)
# 0x7B2FFF  → 0x880000  (purple → dark red)
# 0x00D4FF@0.6 leftbar → 0xCC0000@0.8 leftbar
# waveform colors: 0x00D4FF|0x7B2FFF → 0xCC0000|0xFF4444 (red gradient)
# host_colors Jessica: 0xFF3333@0.95 → 0xCC0000@0.95 (keep red, just correct shade)
# host_colors Chris:   0x3388FF@0.95 → 0x880000@0.95 (blue → dark red)
# ticker bg: 0x0A0A0A → 0x0A0000 (near-black with red undertone)
# ticker text: 0xFFCC00 → 0xFFD700 (gold — keep)
# intro title text: 0x00D4FF → 0xCC0000 (Protocol Pulse title = red)
# thumbnail border: 0x00D4FF@0.8 → 0xCC0000@0.9
# social segment box: 0x000000@0.65 → 0x0A0000@0.75
```

Do a global find-replace across assembler.py hitting every color constant.
After replacing, grep to confirm zero occurrences of 00D4FF, 7B2FFF, 3388FF remain.

---

## FIX 2: WAVEFORM — CONTAINED, SUBTLE, WORLD-CLASS UI (assembler.py) — TIER 1

Current waveform spans 1800px wide and 320px tall (wave + mirror) — too dominant.
New design: compact, centered, bar-style, elegant.

Replace the waveform section in `make_host_visual()`:

```python
# OLD: full-width showwaves spanning 1800x320
# NEW: compact centered bar visualizer, 960x80, centered horizontally

# Waveform — compact, centered, red
fg += (f"[0:a]showwaves=s=960x80:mode=cline:"
       f"colors=0xCC0000|0xFF4444:scale=sqrt:draw=full:rate=30[wave_raw];\n")

# Slim mirror reflection (subtle, 40% opacity)
fg += f"[wave_raw]split[wA][wB];\n"
fg += f"[wB]vflip,colorchannelmixer=aa=0.35[wflip];\n"
fg += f"[wA][wflip]vstack[wavepair];\n"  # 960x160 total

# Overlay centered horizontally: x=(1920-960)/2=480, vertically: y=460 (center-ish)
fg += f"[bgv0][wavepair]overlay=480:460[withwave];\n"
```

The result: a 960px wide, 160px tall compact waveform strip centered on screen,
red-on-dark, with a subtle mirror reflection. Elegant, not overwhelming.

---

## FIX 3: GLOBAL AV SYNC FIX FOR ALL CLIPS (clip_extractor.py) — TIER 1

Audio is out of sync on ALL clips, not just Saylor. The fix needs to be applied universally.

In `clip_extractor.py`, update `fix_av_sync()` to be more aggressive:

```python
def fix_av_sync(input_path: str, output_path: str) -> bool:
    """Fix audio/video sync. Apply to EVERY downloaded clip."""
    return run_ffmpeg([
        "-fflags", "+genpts",           # Regenerate PTS timestamps
        "-i", input_path,
        "-c:v", "libx264", "-crf", "20", "-preset", "fast",
        "-r", "30",
        "-vf", "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1,fps=fps=30,format=yuv420p",
        "-c:a", "aac", "-ar", "48000", "-ac", "2",
        "-af", "aresample=async=1:min_hard_comp=0.100000:first_pts=0",
        "-vsync", "cfr",               # Constant frame rate (not vfr)
        "-avoid_negative_ts", "make_zero",
        "-movflags", "+faststart",
        output_path,
    ], "av_sync_fix", 180)
```

**CRITICAL:** Make sure `fix_av_sync()` is called on EVERY clip after download,
not just some. Check the download flow — there should be a single exit point
where every clip passes through this function before being returned.

Also add a sync validation after fix:
```python
def check_av_sync(clip_path: str) -> float:
    """Return A/V offset in seconds. 0 = perfect sync. Positive = audio ahead."""
    result = subprocess.run([
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_streams", clip_path
    ], capture_output=True, text=True)
    data = json.loads(result.stdout)
    streams = data.get("streams", [])
    video_start = next((float(s.get("start_time", 0)) for s in streams if s["codec_type"] == "video"), 0)
    audio_start = next((float(s.get("start_time", 0)) for s in streams if s["codec_type"] == "audio"), 0)
    return audio_start - video_start
```

Log the sync offset for every clip. If offset > 0.1s after fix, log a WARNING.

---

## FIX 4: NEW PIPELINE LAW — NEVER CLIP AD READS (clip_selector.py + PIPELINE_LAWS) — TIER 1

The Unchained clip at 2:00 was an ad read. This must NEVER happen.

Add to `SELECTION_PROMPT` in `clip_selector.py` — insert after existing RULES:

```python
# ADD TO SELECTION_PROMPT RULES SECTION:
"""
- CRITICAL — AD READ DETECTION: NEVER select a timestamp range that contains
  an ad read, sponsorship mention, or promotional segment. Ad reads are identified by:
  * "This episode is brought to you by..."
  * "Thanks to our sponsor..."  
  * "Use code [X] at [URL]"
  * "Go to [domain].com/[show]"
  * "Check out [product]" with a URL
  * Any mention of a promo code, discount, or affiliate link
  * Host reading from a script about a product/service they're paid to mention
  If a transcript segment contains these patterns, SKIP it and find the next 
  compelling moment that is actual content, not advertising.
  
- SEGMENT CONTINUITY: Never select a clip that starts mid-ad-read or ends 
  mid-thought. The clip must begin and end at natural content boundaries.
  A clip that begins with ad-read content is invalid, full stop.
"""
```

Also add a post-selection validation function:
```python
AD_READ_PHRASES = [
    "brought to you by", "thanks to our sponsor", "use code", "promo code",
    "check out", "go to", ".com/", "discount", "affiliate", "sponsored by",
    "this episode is", "today's episode is brought", "support the show"
]

def contains_ad_read(transcript_segment: str) -> bool:
    """Return True if this transcript segment contains ad read content."""
    lower = transcript_segment.lower()
    return any(phrase in lower for phrase in AD_READ_PHRASES)
```

---

## FIX 5: SOCIAL SEGMENT — WORLD CLASS TWEET CARDS (assembler.py) — TIER 1

Replace the basic text-overlay social segment with proper tweet card design.

The social segment should display each tweet as a styled card — like a screenshot
of a real tweet but rendered natively with FFmpeg drawtext/drawbox.

```python
def make_social_card_visual(tweet_text: str, author_handle: str, 
                             likes: int, output_path: str,
                             duration: float = 5.0,
                             thumbnail_path: str = "") -> str:
    """
    Render a tweet card visual segment.
    Looks like: dark card, author handle, tweet text, like count.
    If thumbnail_path provided (for tweet with image), show it PIP.
    Brand colors: black/red/white.
    """
    total_dur = duration
    safe_text = (tweet_text.replace("'", "").replace('"', "")
                           .replace(":", " -").replace("\n", " ")
                           .replace("\\", "")[:140])
    safe_handle = author_handle.replace("'", "").replace('"', "")
    like_str = f"{likes:,}" if likes > 0 else ""
    
    fg = (
        # Deep black base
        f"color=c=0x0A0000:s=1920x1080:d={total_dur}:r=30[base];\n"
        
        # Section header — red bar top
        f"[base]drawbox=x=0:y=0:w=1920:h=8:color=0xCC0000:t=fill[hbar];\n"
        
        # Title: "WHAT THE BITCOIN INTERNET IS SAYING"
        f"[hbar]drawtext=fontfile={FONT_BOLD}:"
        f"text='WHAT THE BITCOIN INTERNET IS SAYING':"
        f"fontcolor=0xCC0000:fontsize=32:x=(w-text_w)/2:y=30[title];\n"
        
        # Tweet card background (centered, rounded-ish via padding)
        f"color=c=0x1A0000:s=1400x260:d={total_dur}:r=30[card];\n"
        f"[card]drawbox=x=0:y=0:w=1400:h=260:color=0xCC0000@0.4:t=4[cardborder];\n"
        
        # Author handle (top of card)
        f"[cardborder]drawtext=fontfile={FONT_BOLD}:"
        f"text='@{safe_handle}':"
        f"fontcolor=0xCC0000:fontsize=28:x=24:y=20[cardhandle];\n"
        
        # Tweet text (wrapped, main body)
        f"[cardhandle]drawtext=fontfile={FONT_MONO}:"
        f"text='{safe_text}':"
        f"fontcolor=white:fontsize=24:x=24:y=70:line_spacing=8:"
        f"box=0[cardtext];\n"
        
        # Like count (bottom of card)
        f"[cardtext]drawtext=fontfile={FONT_MONO}:"
        f"text='♥ {like_str}':"
        f"fontcolor=0xFF4444:fontsize=22:x=24:y=210[cardlikes];\n"
        
        # Overlay card on base, centered
        f"[title][cardborder]overlay=260:200[withcard];\n"
    )
    
    # Ticker bottom
    fg += f"color=c=0x0A0000@0.92:s=1920x44:d={total_dur}:r=30[tickbg];\n"
    fg += (f"[tickbg]drawtext=fontfile={FONT_MONO}:"
           f"text='PROTOCOL PULSE  |  PULSE CHECK  |  PROTOCOLPULSE.IO':"
           f"fontcolor=0xFFD700:fontsize=18:x=w-mod(t*80\\,w+tw):y=12[ticker];\n")
    fg += f"[withcard][ticker]overlay=0:H-44[v_final];\n"
    fg += f"[v_final]format=yuv420p[outv];\n"
    fg += f"[0:a]loudnorm=I=-16:TP=-1.5:LRA=11[outa]"
    
    # Note: audio input [0:a] will be the TTS narration for this segment
    ok = run_ffmpeg_filtergraph(
        ["dummy_audio_path"],  # caller passes actual TTS audio as [0:a]
        fg, ["[outv]", "[outa]"],
        ["-c:v", "libx264", "-crf", "20", "-preset", "fast",
         "-c:a", "aac", "-ar", "48000", "-b:a", "192k", "-t", str(total_dur)],
        output_path, "social card", 120
    )
    return output_path if ok else ""
```

Wire this into `make_host_visual()`: when `segment_type == "social_segment"`,
call `make_social_card_visual()` instead of the generic drawtext overlay.

---

## FIX 6: OUTRO TIMING FIX (assembler.py) — TIER 1

Outro is playing at 3:28 but narrator continues until 3:41 — 13 seconds of black screen.
The outro must ONLY play AFTER the last narrator line has finished completely.

In `assemble_episode()`, the wrap segment and outro must be ordered correctly:
1. All dialogue parts render including the wrap (final narrator line)
2. Wrap audio must COMPLETE before outro starts
3. Only THEN append the branded outro

```python
# In assemble_episode() — ensure wrap is part of dialogue list, not special-cased
# The outro is appended AFTER all dialogue parts are in the `parts` list:

# WRONG (current): outro renders before wrap audio completes
# CORRECT:
for entry in dialogue_entries:
    # ... render all parts including wrap ...
    parts.append(rendered_part)

# Only after ALL dialogue done:
outro_out = os.path.join(work_dir, f"part_{part_idx:03d}_outro.mp4")
outro_result = make_branded_outro(outro_out)  # no narration_audio — it already played
if outro_result:
    parts.append(outro_result)
```

Also: the outro video file (`outro_branded.mp4`) is being uploaded by PBX.
When it arrives, verify it with:
```bash
ffprobe -v quiet -print_format json -show_format assets/outro_branded.mp4
```
Ensure it's fit-to-frame (1920x1080, no letterboxing needed). If it's a different
aspect ratio, scale with `force_original_aspect_ratio=decrease` + pad to black.

---

## FIX 7: YOUNGER FEMALE VOICE (tts_engine.py) — TIER 1

Current: Bella `EXAVITQu4vr4xnSDxMaL` — American, good, but slightly mature.
Try these in order (all American English, progressively younger):

1. **Gigi** `jBpfuIE2acCO8z3wKNLl` — young, energetic, American. Try this first.
2. **Aria** `9BWtsMINqrJLrRacOk9x` — confident, American, mid-20s energy
3. **Grace** `oWAxZDx7w5VEj9dCyTzz` — upbeat, young American

Pick the one that sounds: American English, 24-28 years old energy, confident but not
childish, professional but with edge. Bloomberg anchor who moonlights as a podcast host.

Voice settings for the younger voice:
```python
"stability": 0.40,        # lower = more dynamic/expressive
"similarity_boost": 0.80,
"style": 0.25,            # slight style injection for personality
"use_speaker_boost": True
```

Update BOTH `tts_engine.py` AND `dual_host_tts.py`.

---

## FIX 8: WIRE MOOD-MATCHED MUSIC LIBRARY (daily_producer.py + assembler.py) — TIER 1

Music library is live at `assets/music/` with 30 tracks. Wire it now.

In `daily_producer.py`, after script is written, add mood classification:
```python
import glob, random, os

def classify_episode_mood(script_text: str) -> str:
    """Ask Claude to classify the episode mood from the script."""
    prompt = f"""Based on this Pulse Check script, classify the overall mood.
Choose EXACTLY ONE: tense | confident | contemplative | upbeat | edge
Consider: is this breaking news (tense)? bullish macro (confident)? philosophical (contemplative)? community/social (upbeat)? controversial hot take (edge)?
Script summary: {script_text[:500]}
Return only the single word."""
    # Use existing Claude API call pattern in this file
    response = call_claude(prompt, max_tokens=10)
    mood = response.strip().lower()
    if mood not in ["tense", "confident", "contemplative", "upbeat", "edge"]:
        mood = "confident"  # safe fallback
    return mood

def select_music_bed(mood: str, music_dir: str) -> str:
    """Pick a random track matching the mood."""
    tracks = glob.glob(os.path.join(music_dir, f"{mood}_*.mp3"))
    if not tracks:
        tracks = glob.glob(os.path.join(music_dir, "confident_*.mp3"))
    if not tracks:
        tracks = glob.glob(os.path.join(music_dir, "*.mp3"))
    return random.choice(tracks) if tracks else ""

def select_intro_music(music_dir: str) -> str:
    tracks = glob.glob(os.path.join(music_dir, "intro_*.mp3"))
    return random.choice(tracks) if tracks else ""
```

Pass `music_bed_path` and `intro_music_path` into `assemble_episode()`.
In assembler, use them instead of `BG_MUSIC` hardcoded path.

---

## EXECUTION ORDER

1. Read PIPELINE_LAWS.md — do not skip
2. Apply FIX 1 (brand colors — red/black/white throughout)
3. Apply FIX 2 (compact waveform — 960x80 centered, red)
4. Apply FIX 3 (AV sync fix — ALL clips, aggressive PTS regeneration)
5. Apply FIX 4 (ad read detection law in clip_selector.py)
6. Apply FIX 5 (tweet card visual — styled card design)
7. Apply FIX 6 (outro timing — plays AFTER narrator finishes)
8. Apply FIX 7 (younger voice — try Gigi first)
9. Apply FIX 8 (mood music wiring)
10. Test render: `python3 daily_producer.py --test --skip-scan 2>&1 | tail -60`
11. `bash regression_test.sh` — fix ALL FAILs before committing
12. Git commit with message: `feat: V10 — brand colors, compact waveform, AV sync, ad filter, tweet cards, outro timing, younger voice, mood music`
13. Report SCP path

## SUCCESS CHECKLIST
- [ ] Zero cyan/blue/purple — only red/black/white/gold
- [ ] Waveform is compact (960px wide, centered, not full-screen)
- [ ] ALL clips are AV-synced (log shows <0.1s offset for each)
- [ ] No ad read content in any clip (verified in script.json)
- [ ] Social segment shows styled tweet card (not plain text)
- [ ] Outro plays AFTER last narrator word — no black screen gap
- [ ] Female voice sounds younger (Gigi or Aria)
- [ ] Background music matches episode mood from Suno library
- [ ] Regression test: zero FAILs
- [ ] SCP path reported

## MANDATORY FINAL STEP
```bash
bash ~/protocol_pulse/video_pipeline_v3/regression_test.sh
```
Zero FAILs required before any commit. No exceptions.
