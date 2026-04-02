# VIDEO PIPELINE — FORENSIC AUDIT V2
# Complete Code Analysis + Issues Found + Fix Plan
# For multi-LLM review (Claude, Gemini, Grok, GPT)
# Generated: 2026-03-06

---

## CODEBASE OVERVIEW

### Files (4,509 lines total):
| File | Lines | Purpose |
|------|-------|---------|
| assembler.py | 2,134 | FFmpeg + Remotion episode assembly (THE CRITICAL FILE) |
| daily_producer.py | 694 | Orchestrator — runs the full pipeline |
| clip_extractor.py | 573 | Downloads + extracts clips from YouTube |
| clip_selector.py | 392 | Intelligent clip selection (Claude LLM + scoring) |
| tts_engine.py | 384 | ElevenLabs voice generation |
| script_writer.py | 332 | Claude-generated episode scripts |

### Assembly Flow (assembler.py → assemble_episode()):
```
1. COLD OPEN HOOK — make_intro_coldopen() → first narrator line with logo + waveform
2. DIALOGUE LOOP — iterate script entries:
   a. HOST lines → make_host_visual() → waveform + bg + PiP + subtitle
   b. CLIP lines → make_clip_visual() → partner video with lower third
   c. SOCIAL lines → make_social_card_visual() → tweet cards
3. TRANSITIONS — make_transition_visual() between segments (custom whoosh)
4. OUTRO — make_branded_outro() → logo + outro music
5. CONCATENATE — normalize_part() + concatenate_parts() → final mp4
```

### Key Functions in assembler.py:
| Function | Line | What it does |
|----------|------|-------------|
| make_intro_coldopen() | 358 | Cold open with jingle + waveform bg |
| make_host_visual() | 595 | Narrator segments (waveform + bg + subtitle + PiP) |
| make_social_card_visual() | 887 | "What Bitcoin Internet Is Saying" tweet cards |
| make_pip_preview() | 514 | Extract muted 820x462 preview from upcoming clip |
| overlay_pip_on_narration() | 542 | Overlay PiP onto narrator segment |
| make_clip_visual() | 1539 | Partner clip with lower third overlay |
| make_transition_visual() | 1471 | Custom whoosh + glitch transition |
| make_branded_outro() | 448 | Logo + outro music |
| normalize_part() | 1575 | Normalize video format for concat |
| concatenate_parts() | 1600 | Concat all parts with FFmpeg demuxer |
| assemble_episode() | 1680 | THE MAIN FUNCTION — orchestrates everything |

---

## ISSUES FOUND (18 total, ranked by severity)

### CRITICAL (breaks the viewing experience):

#### ISSUE 1: NO AUDIO NORMALIZATION ACROSS CLIPS
**Severity: CRITICAL**
**Symptom:** Partner clips have wildly different volume levels. One clip is quiet, the next blasts.
**Root cause:** No `loudnorm` (EBU R128) filter applied to clips BEFORE assembly.
The only volume handling is in `make_host_visual()` where BG_MUSIC is mixed at -18dB.
Partner clips are inserted at their ORIGINAL volume with no normalization.
**Fix:** Add FFmpeg loudnorm to every clip in `make_clip_visual()`:
```
ffmpeg -i clip.mp4 -af "loudnorm=I=-16:TP=-1.5:LRA=11" -c:v copy normalized.mp4
```
Target -16 LUFS for all clips AND narration. This is broadcast standard.
Also apply to TTS narration outputs so everything matches.
**Files to modify:** assembler.py (make_clip_visual + make_host_visual)

#### ISSUE 2: CLIPS STILL END ABRUPTLY
**Severity: CRITICAL**
**Symptom:** Clips start at better timing (sentence boundary working for START) but endings cut mid-sentence.
**Root cause:** `find_sentence_boundary()` exists (line 493 clip_extractor.py) and is called for BOTH start and end (lines 419-426). BUT the end-boundary detection relies on timestamp matching in the transcript text. If the transcript doesn't have precise timestamps (Whisper word-level), the boundary search fails silently and falls back to the raw end time. Additionally, the silence detection (lines 81-114) searches for a silence gap AFTER the end time within a `pad_window`, but if the speaker keeps talking without pausing, no gap is found.
**Fix:**
1. Extend end padding from current 10s to 15s (give more room to find a natural end)
2. If no sentence boundary found, use the SILENCE detection as fallback
3. If no silence found either, EXTEND the clip until the next sentence end (up to 15s max)
4. Add a HARD rule: never cut in the middle of a word (check Whisper word timestamps)
5. As a last resort, apply a 0.5-second audio fade-out so the cut doesn't feel abrupt
**Files to modify:** clip_extractor.py (find_sentence_boundary, _trim_at_silence, extract_clip)

#### ISSUE 3: SOCIAL CARDS — ONLY FIRST AND LAST RENDER, MIDDLE CARDS GO DARK
**Severity: CRITICAL**
**Symptom:** Saylor's tweet shows correctly (first card). Then screen goes dark while narrator discusses 2-3 more tweets. Only Lyn Alden's tweet (last/top tweet of day) appears.
**Root cause:** `make_social_card_visual()` (line 887) renders ALL tweets as a SINGLE video file. The card transitions are timed by `durationInFrames` in the Remotion SocialCard. BUT the audio duration for each individual tweet narration varies, and the card timing is calculated ONCE at the beginning. If the first card's audio is shorter than the allocated card time, the remaining cards start late. If longer, cards get cut.
**The fundamental problem:** The social segment is rendered as ONE monolithic video with multiple cards timed internally, rather than rendering each tweet as its OWN segment and concatenating them. The internal timing approach is fragile.
**Fix:** Render each tweet as its OWN video segment:
```
for each tweet in social_posts:
    1. Generate narration audio for THIS tweet
    2. Render Remotion SocialCard for THIS tweet (durationInFrames matches audio)
    3. Add as a separate part to the parts[] list
    4. Add transition between cards
```
This eliminates ALL timing bugs because each card is self-contained.
**Files to modify:** assembler.py (make_social_card_visual → refactor to per-card)

#### ISSUE 4: OUTRO NARRATION PLAYS TWICE
**Severity: CRITICAL**
**Symptom:** Female narrator says closing statement, then the branded outro replays the same audio.
**Root cause:** In `assemble_episode()`, the WARM/wrap dialogue entry generates a host visual with the closing narration. Then `make_branded_outro()` or `make_tag_video()` is called with `narration_audio` parameter, which ALSO mixes the narration over the outro visual. The same audio gets added to TWO parts.
**Fix:** 
Option A (PBX's request): Don't play narration over outro at all. Just play outro visual + outro music.
```python
# In assemble_episode(), change the outro call:
outro_result = make_branded_outro(outro_out)  # NO narration_audio parameter
```
Option B: Skip the wrap dialogue entry entirely, only play it over outro.
**PBX prefers Option A.** Outro = visual + music only, no voice.
**Files to modify:** assembler.py (assemble_episode, ~line 1970-2000)

### HIGH (noticeably wrong but not unwatchable):

#### ISSUE 5: NO ANIMATED CYBERPUNK BACKGROUND
**Severity: HIGH**
**Symptom:** Narrator segments show plain dark background, not the animated cyberpunk loop.
**Root cause:** `cyberpunk_loop.mp4` exists (862KB, 10-second Remotion render) and is referenced in `make_host_visual()` at line 623-674. The code DOES check for it and DOES set up an FFmpeg filtergraph with it. However, the file is only 862KB for a 10-second 1080p video — that's suspiciously small (~700 kbps). It may be:
a) A very low quality render (nearly invisible dark particles)
b) Mostly transparent/black (the animated elements are too subtle to see)
c) Being overridden by the logo background fallback
**Investigation needed:** Play `cyberpunk_loop.mp4` standalone to verify it has visible content.
**Fix:** If the file looks too dark/empty:
1. Re-render the CyberpunkBackground Remotion component with brighter, more visible elements
2. Target: visible gradient mesh, particles, scan line, perspective grid — not pitch black
3. OR: use one of the other backgrounds: `cyberspace.mp4` (55MB), `neon_lines.mp4` (103MB), `neon_tunnel.mov` (59MB) — these are MUCH larger and likely much more visually rich
**Files to modify:** assembler.py (CYBERPUNK_BG_LOOP path, or re-render Remotion)

#### ISSUE 6: COLD OPEN STILL SHOWS LOGO INSTEAD OF PiP PREVIEW
**Severity: HIGH**
**Symptom:** First frame of video is logo + waveform, not the PiP preview of upcoming clip.
**Root cause:** `make_intro_coldopen()` (line 358) generates the cold open visual. Looking at the code, it uses `pp_intro.mp3` jingle as background, renders the waveform, and overlays the Protocol Pulse logo. It does NOT overlay the PiP preview of the first clip.
The PiP system IS built — `pip_previews` dict is populated in `assemble_episode()` (line 1803-1808). But PiP is only applied in the DIALOGUE LOOP for host entries, NOT for the cold open.
**Fix:** After creating the cold open, overlay the PiP preview of clip #1:
```python
if cold_open_audio and intro_result:
    # Overlay PiP of first clip onto cold open
    if 1 in pip_previews:
        pip_intro = os.path.join(work_dir, f"part_{part_idx-1:03d}_cold_open_pip.mp4")
        intro_result = overlay_pip_on_narration(intro_result, pip_previews[1], pip_intro)
```
Also: REMOVE the logo from cold open. The cold open should be: cyberpunk bg + waveform + PiP preview + subtitle text. No logo. Logo only appears in lower thirds and outro.
**Files to modify:** assembler.py (make_intro_coldopen + assemble_episode cold open section)

#### ISSUE 7: NO 1-SECOND INTRO MUSIC BUFFER
**Severity: HIGH**
**Symptom:** Voice starts immediately — startling for the viewer.
**Root cause:** `make_intro_coldopen()` uses `pp_intro.mp3` jingle mixed at 35% under TTS. The TTS starts at time 0. There's no breathing room.
**Fix:** Prepend 1.0 seconds of intro music at full volume before the TTS begins:
```
ffmpeg -i pp_intro.mp3 -i tts_cold_open.wav -filter_complex
  "[0:a]atrim=0:1,volume=0.8[intro_beat];
   [0:a]atrim=1,volume=0.35[bg_music];
   [1:a]adelay=1000|1000[voice];
   [intro_beat][bg_music]concat=n=2:v=0:a=1[music_full];
   [music_full][voice]amix=inputs=2:duration=longest[final]"
```
This gives 1 second of music, then voice comes in with music ducked.
**Files to modify:** assembler.py (make_intro_coldopen)

#### ISSUE 8: BACKGROUND MUSIC NOT AUDIBLE
**Severity: HIGH**
**Symptom:** No background music heard during narrator segments.
**Root cause:** `BG_MUSIC` points to `assets/music/pp_background.mp3` (4.3MB). The `make_host_visual()` function DOES reference it (line 620-632) and sets up a filtergraph input. However, the music mixing is at -18dB which is very quiet. Additionally, if the `mood_music` feature flag selects a different track via `daily_producer.py`, but that track isn't found at the expected path, it silently falls back to nothing.
**Investigation needed:** Check daily_producer.py to see what `music_bed` is being passed.
**Fix:**
1. Raise music volume from -18dB to -14dB (still subtle but audible)
2. Add explicit logging: "MUSIC BED: Playing {filename} at {volume}dB"
3. If mood-selected track fails, ALWAYS fall back to pp_background.mp3
4. Verify the 34 mood tracks are correctly categorized and selectable
**Files to modify:** assembler.py (make_host_visual music mixing), daily_producer.py

### MEDIUM (noticeable but minor):

#### ISSUE 9: ONLY 4 CLIPS INSTEAD OF 5
**Severity: MEDIUM**
**Symptom:** Latest render has 4 clips from 4 channels.
**Root cause:** clip_selector.py enforces 5-clip rule but with a fallback: if < 5 qualifying clips found, it logs a warning but proceeds with fewer. The intelligent scorer may have scored too few clips above threshold.
**Fix:** Lower the quality threshold for the 5th clip. Better to have 5 clips (one slightly weaker) than 4 clips. The 5-clip rule should be HARD — not "try for 5, accept 4."
**Files to modify:** clip_selector.py

#### ISSUE 10: PiP PREVIEW TIMING — SHOWS DURING REACT SEGMENTS
**Severity: MEDIUM** 
**Symptom:** (Improved but not perfect) PiP of next clip sometimes appears while narrator is still reacting to the previous clip.
**Root cause:** The script_writer tags segments as `[NARRATION]` but doesn't sub-tag as REACT vs SETUP. The assembler uses heuristics (position in dialogue list) but they're imperfect.
**Fix:** Force script_writer to output sub-tags. Add to prompt:
"Tag every narration line with either [NARRATION:REACT] (discussing clip just shown) or [NARRATION:SETUP] (introducing next clip). The PiP preview only shows on SETUP lines."
**Files to modify:** script_writer.py (prompt), assembler.py (tag detection)

#### ISSUE 11: TWEET SCREENSHOTS NOT APPEARING
**Severity: MEDIUM**
**Symptom:** Text-only tweet cards despite Playwright being installed.
**Root cause:** `capture_tweet()` is called (assembler.py line 1937) but requires tweet URLs. The `social_fetcher.py` may not be providing URLs, just text + handle.
**Fix:** Ensure social_fetcher returns tweet URLs. If using X API: URL = `https://x.com/{handle}/status/{tweet_id}`. If scraping: URL should be available.
**Files to modify:** utils/social_fetcher.py, assembler.py

#### ISSUE 12: NO X SPACES AUDIO IN EPISODES
**Severity: MEDIUM**
**Symptom:** Spaces Pulse is built but not wired into the assembler.
**Root cause:** `spaces_pulse.py` generates data but `daily_producer.py` doesn't read it for clip injection.
**Fix:** In daily_producer.py, after clip selection:
1. Read live_signals.json for high-impact Space moments
2. Extract best audio clip (if available)
3. Pass to script_writer as SPACES_CONTEXT
4. Assembler creates a special "SPACES" segment with the quote + audio
**Files to modify:** daily_producer.py, script_writer.py, assembler.py

### LOW (polish items):

#### ISSUE 13: TRANSITION TIMING INCONSISTENT
**Severity: LOW**
**Symptom:** Some transitions feel too fast, others too slow.
**Root cause:** `make_transition_visual()` uses fixed 0.5s duration. Custom whoosh is 2 seconds.
**Fix:** Match transition visual to whoosh audio duration. If whoosh is 2s, visual should be 1.5-2s.

#### ISSUE 14: SUBTITLE TEXT OVERLAP WITH PiP
**Severity: LOW**
**Symptom:** Occasionally subtitle text extends into PiP area.
**Root cause:** Text wrapping allows up to 55 chars which can extend past x=1056 (PiP boundary).
**Fix:** Reduce max_width in `_word_wrap()` to 45 chars, or constrain drawtext region.

#### ISSUE 15: NO CHAPTER MARKERS FOR YOUTUBE
**Severity: LOW**
**Symptom:** YouTube video has no chapters/timestamps in description.
**Root cause:** Pipeline doesn't generate chapter markers.
**Fix:** Track part durations, output chapters file for YouTube description.

#### ISSUE 16: NO THUMBNAIL GENERATION
**Severity: LOW**
**Symptom:** No auto-generated thumbnail for each episode.
**Root cause:** Not implemented.
**Fix:** Extract highest-quality face frame from clip #1, overlay title text + brand elements.

#### ISSUE 17: COLD OPEN HOOK NOT ALWAYS THE "MOST SHOCKING" MOMENT
**Severity: LOW**
**Symptom:** Cold open is just the first line, not necessarily the most compelling.
**Root cause:** script_writer picks the hook but doesn't always choose the strongest moment.
**Fix:** Explicit scoring in clip_scorer.py — highest impact clip's best moment = cold open.

#### ISSUE 18: NO FADE-TO-BLACK ON FINAL FRAME
**Severity: LOW**
**Symptom:** Video ends with hard cut after outro.
**Root cause:** `make_branded_outro()` doesn't add fade-out.
**Fix:** Add `fade=t=out:st={duration-1}:d=1` to outro.

---

## MISSING FEATURES NOT YET CONSIDERED

### A. DYNAMIC LOWER THIRDS
Currently: static text overlays on clips. Missing: animated slide-in lower thirds with
channel name, speaker name, topic tag. The Remotion LowerThird component EXISTS but may
not be wired into the clip visual pipeline.

### B. RECAP CARD AT END
After all clips but before outro: a quick visual recap card showing all 5 topics covered.
Like a "Tonight on Protocol Pulse" card in reverse. Reinforces what was learned.

### C. SUBSCRIBE CTA MID-VIDEO
At the halfway point (per PRODUCTION_DESIGN_LAWS re-engagement rule), overlay a subtle
"Subscribe" CTA. YouTube's algorithm rewards videos that drive subscriptions.

### D. INTELLIGENT MUSIC MOOD MATCHING
34 tracks exist in 7 moods (confident, contemplative, etc.) but the selection logic may
be random. Should match: bullish sentiment → confident track, bearish → contemplative.

### E. A/B THUMBNAIL TESTING
Generate 2-3 thumbnails per episode, let YouTube analytics determine winner.
Requires YouTube API integration (already have YOUTUBE_DATA_API_KEY).

### F. CLIP HIGHLIGHT REEL / SHORTS AUTO-EXTRACTION
After each episode, extract the 3 best 30-60 second moments as YouTube Shorts.
Vertical 9:16, caption-first, different thumbnail. 3-5x discovery reach.

### G. AUDIO DUCKING ON CLIP TRANSITIONS
When transitioning from narrator to clip, duck the narrator's last 0.5s of audio
while the clip fades in. Creates seamless flow instead of hard cut.

### H. BTC PRICE TICKER ACCURACY
Bottom ticker shows BTC price but may be stale (from render time, not current).
Could show "as of [timestamp]" or pull live price at render start.

---

## FIX PRIORITY ORDER (recommended execution)

| Priority | Issue | Impact | Effort |
|----------|-------|--------|--------|
| 1 | #1 Audio normalization (loudnorm) | Massive | Small (add 1 FFmpeg filter) |
| 2 | #3 Social cards per-tweet rendering | Massive | Medium (refactor function) |
| 3 | #4 Outro duplication | Major | Tiny (remove 1 parameter) |
| 4 | #2 Clip end boundary | Major | Medium (extend logic) |
| 5 | #7 Intro music buffer | Major | Small (delay TTS 1s) |
| 6 | #5 Cyberpunk background | Major | Small (swap file or re-render) |
| 7 | #6 Cold open PiP | Major | Medium (overlay + remove logo) |
| 8 | #8 Music audibility | Moderate | Small (volume + logging) |
| 9 | #9 5-clip enforcement | Moderate | Small (lower threshold) |
| 10 | #10-18 Polish items | Minor | Various |

---

## FEATURE FLAGS (config/feature_flags.json):
```json
{
  "mood_music": true,
  "ad_read_filter": true,
  "channel_dedup": true,
  "silence_detection": true,
  "social_segment": true,
  "tweet_cards": true,
  "youtube_auto_upload": false,
  "telegram_alerts": false,
  "analytics_feedback": false,
  "breaking_news_detector": false,
  "sponsor_rotation": false,
  "remotion_visuals": true
}
```

## ASSET INVENTORY:
| Asset | Size | Status |
|-------|------|--------|
| cyberpunk_loop.mp4 | 862KB | EXISTS but possibly too dark/empty |
| cyberspace.mp4 | 55MB | Alternative bg (rich visuals) |
| neon_lines.mp4 | 103MB | Alternative bg (rich visuals) |
| neon_tunnel.mov | 59MB | Alternative bg |
| pp_background.mp3 | 4.3MB | Default bg music |
| pp_intro.mp3 | 202KB | Intro jingle |
| pp_outro.mp3 | 606KB | Outro jingle |
| custom_whoosh.mp3 | 111KB | PBX's custom transition sound |
| 34 mood tracks | ~4MB each | confident(5), contemplative(5), etc. |

## VOICES:
- Eryn (Female Host 1): kdnRe2koJdOK4Ovxn2DI, speed 1.12x
- Mark (Male Host 2): 1SM7GgM6IMuvQlz2BwM3, speed 1.10x
- PBX Clone: PENDING (recording tonight)

---

*This audit covers the complete video pipeline as of 2026-03-06.*
*Pass to Claude, Gemini 2.5 Pro, GPT-4.5, Grok for multi-LLM review.*
*Each LLM should identify: issues missed, optimization opportunities,*
*and specific code fixes with FFmpeg command examples.*
