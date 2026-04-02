# PIPELINE FIX — RENDER QUALITY ISSUES (PBX NOTES)

Load PIPELINE_LAWS.md first. This session fixes 14 specific issues found in the first successful PBX solo render. The audio TTS pipeline is NOW FIXED. These are all visual/audio mixing/content/UX issues. DO NOT break anything that works.

## CRITICAL RULES
- Triple-verify every change with a unit test before moving on
- Run `python3 -m py_compile` after every file edit
- Never touch tts_engine.py VOICES dict or PBX voice ID
- Preserve all narration quality instructions in script_writer.py SCRIPT_PROMPT
- Do NOT run a full render — only fast-test after all fixes

---

## ISSUE 1: INTRO MUSIC DROWNS PBX NARRATION
**File:** `assembler.py` function `make_intro_with_pbx_voiceover()` around line 713-800
**Root cause:** Intro music volume at 0.40 while PBX TTS is at 1.0, but intro.mp4 has its own embedded audio ALSO at 0.7 — three audio layers competing. PBX voice is buried.
**Fix:** In the `amix` filter for intro cold open (around line 761-764):
- Intro.mp4 embedded audio: drop from 0.7 → 0.15 (near-silent, just ambience)
- Intro jingle (intro_mus): drop from 0.40 → 0.20
- PBX TTS narration: keep at 1.0
- Also in `make_intro_video()` (around line 465): drop `[0:a]volume=0.7` → 0.15 and `[1:a]volume=0.9` → 0.25

## ISSUE 2: PIP SHOWS WRONG CLIP FOR EACH SEGMENT
**File:** `assembler.py` PIP preview build section around line 4530-4560
**Root cause:** `pip_previews` dict uses `rank` key (1,2,3,4,5) correctly, BUT the pip_source lookup searches `clips_dir` for `clip_{rank}_*.mp4`. The clips directory has files from the PREVIOUS render iteration mixed in. The glob is returning the wrong file.
**Fix:** When building pip_previews, verify the clip filename CONTAINS the channel name from `cinfo.get("channel","")` before accepting it. Log every match. Add a hard check: if the returned clip filename doesn't match any substring of the expected channel name, reject it and use the clip_path directly from `cinfo["path"]`.

## ISSUE 3: PIP SHOWS STATIC IMAGE NOT LOOPED B-ROLL VIDEO
**File:** `assembler.py` function `make_pip_preview()` around line 1010-1067
**Root cause:** `make_pip_preview` detects "still image" at line 1061 but after logging the error, it does NOT return None or a fallback — it returns the still-image file anyway. Caller then uses it.
**Fix:** After line 1061 `logger.error(f"PiP STILL IMAGE detected...")`:
- Delete the output file
- Return `""` (empty string, signals no valid PIP)
- Also add: after `run_ffmpeg` extract, check `frame_count` by running `ffprobe -count_frames`. If frames < 15, reject.
- Add grayscale + slow zoom effect to the PIP: modify the ffmpeg command to add `hue=s=0,eq=brightness=-0.1:contrast=1.1,zoompan=z='min(zoom+0.0005,1.15)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'` before scale. This gives the requested grayscale + slow Ken Burns zoom.

## ISSUE 4: PIP LAYOUT ASSETS STACKED/OVERLAPPING
**File:** `assembler.py` function `overlay_pip_on_narration()` around line 1093
**Current position:** PIP at x=1056, y=200 (820x462)
**Fix:** Reorganize the full layout so nothing overlaps:
- PIP: x=1056, y=140, size=820x462 (right panel, starts below ticker bar)
- BTC price ticker: stays at bottom (y=1032 area) — do not move
- "COMING UP..." label: inside PIP at bottom-left (keep)
- Channel name/handle: draw ABOVE the PIP box at x=1056, y=120 in gold, fontsize=22
- Ensure ticker bar (y=1032) does not overlap PIP (PIP ends at y=602) — safe
- Add 2px red border outline around PIP box: `drawbox=x=1054:y=138:w=824:h=466:color=0xff3b5f@0.8:t=2`

## ISSUE 5: SAYLOR MISPRONUNCIATION (STRETCHED VOWEL)
**File:** `tts_engine.py` PRONUNCIATION_MAP around line 321-323
**Current:** `"Michael Saylor": "MY-kul SAY-lor"` — ElevenLabs is stretching the "AY" 
**Fix:** Change pronunciation entries:
- `"Michael Saylor": "Michael Sayler"` (drop the phonetic entirely — ElevenLabs handles "Saylor" correctly when spelled naturally as "Sayler")
- `"Saylor": "Sayler"` 
- Test with the actual string to ensure no stretching

## ISSUE 6: DEAD SILENCE GAPS READING NUMBERS
**File:** `tts_engine.py` function `expand_numbers_for_tts()` 
**Root cause:** num2words produces verbose output like "seventy-four thousand, four hundred and twenty-one" with implied pauses at commas. ElevenLabs inserts micro-pauses at commas causing stuttering.
**Fix:** After num2words conversion, strip all commas from the spoken number: `spoken = spoken.replace(",", "")`. Also add `"and"` removal: `spoken = re.sub(r'\band\b', '', spoken)` for numbers (e.g. "one hundred and fifty" → "one hundred fifty" — flows faster).

## ISSUE 7: PBX SPEED TOO SLOW — INCREASE BY 0.25x
**File:** `tts_engine.py` line 27
**Current:** `"speed": 1.2`
**Note:** ElevenLabs max speed is 1.2. Already at max. 
**Alternative fix:** In the TTS post-processing, after generating the .mp3, apply ffmpeg `atempo=1.08` to speed up by 8% without pitch shift. Add this to the `_mp3_to_m4a()` function: append `-af atempo=1.08` to the ffmpeg conversion command. This gives effective 1.3x speed.

## ISSUE 8: SOLO NARRATOR PROMPT — REMOVE DUAL-HOST CONVERSATIONAL STYLE
**File:** `script_writer.py` SCRIPT_PROMPT
**Current issue:** Script still uses "REACT" lines that read like responses to a second host ("Exactly.", "100%.", "I mean—") — sounds like PBX is talking to someone who isn't there.
**Fix:** Update SCRIPT_PROMPT:
1. Replace "REACT" framing: instead of reacting TO someone, PBX is reacting TO THE CLIP. Reframe: "REACT lines = PBX's direct hot take on what was just shown. He's speaking to the AUDIENCE, not to a co-host. No conversational openers that imply a partner ('Exactly.', 'I mean—', 'Right, and—'). Instead: direct audience address ('Here's what this means.', 'What nobody's saying is—', 'The tell here is—')."
2. Add: "Each new segment opens with a LIFT — a single high-energy sentence that raises the stakes for what's coming. Think: news anchor tossing to the next story. Creates energy flow without a co-host."
3. Remove: "React lines start with a reaction word: 'Yeah.', 'Exactly.', '100%.', 'I mean—'" — these imply co-host
4. Add instead: "React lines start with the IMPLICATION: 'What this means is—', 'The signal here is—', 'Nobody's talking about—', 'That's the tell.'"
5. Preserve ALL other quality instructions unchanged (tone, gossip energy, Austrian economics, no banned phrases)

## ISSUE 9: CLIP CUTOFF TOO EARLY — REMOVE HARD TIME LIMITS ON CLIPS
**File:** `assembler.py` — find where partner clips are trimmed
**Search for:** Any `atrim`, `trim`, `ss`, `-t` flags applied TO the clip content (not to the PIP)
**Also check:** `script_writer.py` for any duration cap in the segment structure
**Fix:** 
- Episodes can be 10-15 minutes. Remove any hard cap below 15 minutes (900 seconds)
- For clip playback: do NOT trim clips to a hard duration. Let the clip play to its natural endpoint OR to a soft sentence-boundary detected by silence. 
- If a clip must be limited: cap at 180 seconds max (3 minutes), not the current shorter limit
- Add: when a clip ends, detect the last sentence boundary in the last 10 seconds. If the clip ends mid-sentence (no silence gap in final 3s), extend by up to 5 seconds or fade out gracefully rather than hard cut.
- In `gemini_qc.py` and `gemini_grade.py`: update min duration from 180s to 300s, max from 600s to 900s

## ISSUE 10: BTC → BITCOIN EVERYWHERE
**Files:** `tts_engine.py` PRONUNCIATION_MAP, `script_writer.py` SCRIPT_PROMPT, `assembler.py` ticker text
**Fix:**
- In PRONUNCIATION_MAP add: `"BTC": "Bitcoin"` (already has this? verify and add if missing)
- In SCRIPT_PROMPT add: "CRITICAL: NEVER write 'BTC' in any line. Always write 'Bitcoin' in full."
- In assembler.py line 323 and 889 where ticker says "BTC {safe_btc}": change to "₿ {safe_btc}" or "BITCOIN {safe_btc}"

## ISSUE 11: SOCIAL MEDIA HANDLE MISPRONUNCIATION
**File:** `tts_engine.py` PRONUNCIATION_MAP and `script_writer.py`
**Root cause:** Handles like `@SomeHandle123` are passed raw to ElevenLabs which reads them as word salad.
**Fix in tts_engine.py:**
- In `apply_pronunciation_map()`, add a pre-processing step BEFORE the map: detect @handles with regex `@[A-Za-z0-9_]+`
- For each handle found: split camelCase and underscores into separate words with spaces. E.g. `@MaxKeiser` → "at Max Kaiser", `@some_handle` → "at some handle", `@TFTC` → "at T-F-T-C"
- Convert ALL CAPS handles to spelled-out letters: `@TFTC` → "T-F-T-C", `@WBD` → "W-B-D"
- Add to PRONUNCIATION_MAP: `"@MaxKeiser": "at Max Kaiser"`, `"@prestopysh": "at Preston Pish"` etc. for known handles
**Fix in script_writer.py:** Add to SCRIPT_PROMPT: "When referencing a social media handle, write it in natural spoken form. NEVER write '@MaxKeiser'. Write 'Max Kaiser on X' or 'Preston Pysh posted'. Do not read handles aloud at all — reference the person by name."

## ISSUE 12: YEAR READING — "1602" SAID AS "one six oh two" NOT AS A YEAR
**File:** `tts_engine.py` function `expand_numbers_for_tts()`
**Fix:** Add year detection BEFORE general number expansion:
- Regex: detect 4-digit numbers that look like years (1600-2099) in context
- If a number matches `\b(1[6-9]\d{2}|20[0-2]\d)\b` and is NOT preceded by `$`, currency, or metric unit, treat as year
- Convert to spoken year: 1602 → "sixteen oh two", 1776 → "seventeen seventy-six", 2024 → "twenty twenty-four"
- Use a year_to_words() helper function

## ISSUE 13: DEBUG TEXT VISIBLE IN SIGNAL ACTIVE SEGMENT
**File:** `assembler.py` function `make_signal_active_scene()` and `make_broadcast_segment()`
**Root cause:** When signal_content is None or sparse, fallback text from segment_data["text"] leaks into the drawtext — shows internal script field values like "COLD OPEN" or segment type labels.
**Fix:** 
- In `make_signal_active_scene()`: NEVER display raw segment_data text on screen. Only display: BTC price, UTC timestamp, spaces quotes, nostr posts. Remove any drawtext that pulls from `text` or `headline` fields directly.
- Add guard: if spaces and nostr are both empty, show a clean "SIGNAL COLLECTING..." placeholder rather than any internal text.
- Remove duplicate text: if the same content appears in two drawtext calls, eliminate one and use the space for something else (e.g. "Powered by Protocol Pulse" or leave clean)

## ISSUE 14: NATALIE BRUNELL PRONOUNCED SLOWLY
**File:** `tts_engine.py` PRONUNCIATION_MAP  
**Current:** `"Natalie Brunell": "NAT-uh-lee broo-NELL"` — the phonetic form causes ElevenLabs to slow down
**Fix:** Change to: `"Natalie Brunell": "Natalie Brunelle"` — drop the phonetic, let ElevenLabs handle it naturally with a slight French spelling cue on Brunell→Brunelle. Add `"Brunell": "Brunelle"`.

---

## VERIFICATION SEQUENCE (run after ALL fixes)
1. `python3 -m py_compile assembler.py tts_engine.py script_writer.py gemini_qc.py gemini_grade.py` — all must pass
2. Test pronunciation: `python3 -c "from tts_engine import apply_pronunciation_map, expand_numbers_for_tts; print(apply_pronunciation_map('Michael Saylor said BTC hit 1602 in the @MaxKeiser tweet')); print(expand_numbers_for_tts('Bitcoin at 1602 was mentioned'))"` 
3. `python3 preflight.py` — 0 errors
4. `python3 daily_producer.py --fast-test` — clean render, no errors
5. Inspect fast-test audio/: all files are `_pbx.m4a`, all > 10KB
6. Inspect fast-test work/: verify PIP previews are actual video (not still images)
7. `git add -A && git commit -m "fix: 14 render quality issues — PIP content/layout/broll, intro music balance, pronunciations, solo narrator prompt, clip cutoffs, BTC→Bitcoin, handle reading, debug text" && git push origin main`

DO NOT run a full render. Fast-test only. Report results.
