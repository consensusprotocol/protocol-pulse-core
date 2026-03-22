Load ~/protocol_pulse/PIPELINE_LAWS.md first.
Read ~/protocol_pulse/video_pipeline_v3/assembler.py lines 1-200 for context.
Read ~/protocol_pulse/video_pipeline_v3/script_writer.py lines 90-220 for tag context.
Read ~/protocol_pulse/services/nitter_scraper.py lines 140-220 for likes parsing.

TEN surgical fixes. assembler.py is primary target. Read each section fully before editing.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BUG 1 — Narrator reading [DATA], [WARM], [SETUP] etc tags aloud
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
In script_writer.py line 213 there is already a comment "strip the tag" but it may not be
working for all lines. The TTS engine receives text like "[DATA] Bitcoin is sitting at..."
and reads the bracket tag aloud.

Fix in script_writer.py: Find where dialogue lines are sent to TTS. Ensure this regex
strip is applied to EVERY line before TTS synthesis:
  import re
  text = re.sub(r'^\s*\[[A-Z_]+\]\s*', '', text).strip()
Also strip: [NARRATION], [WARM], [DATA], [SETUP], [REACT], [BRIDGE], [CTA], [COLD]
Find where tts_line or synthesize is called and ensure text is pre-stripped.

Also fix in assembler.py: anywhere dialogue text is passed to TTS (search for
synthesize_host1, synthesize_host2, tts_kokoro, generate_dialogue_audio) — add
the same strip BEFORE the call so even if script_writer misses it, assembler catches it.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BUG 2 — Intro background video should be FULL COLOR
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
In assembler.py _get_bg_layer() around line 129-130:
  f"hue=s=0.15,"  # Near-monochrome grayscale
This desaturates the bg_loop for ALL segments. But the INTRO background should be
FULL COLOR (hue=s=1.0). Only the PiP preview clip should have desaturation.

Fix: In _get_bg_layer(), check if we are in intro context and skip the hue filter.
Actually simpler: Remove hue=s=0.15 from _get_bg_layer() entirely. The bg_loop
itself has its own color — let it show. The 45% dark overlay already provides
cinematic effect. Change:
  f"hue=s=0.15,"
to nothing (remove the line).

The PiP PREVIEW clip at line 1122-1123 (make_pip_preview):
  "hue=s=0,eq=brightness=-0.1:contrast=1.1,"
Keep this — the PREVIEW clip stays grayscale. Only bg_loop changes.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BUG 3 — PiP video disappears at 3:19, right panel goes black
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
In make_narrator_pip_scene() around line 1730:
  has_pip = bool(pip_video_path and os.path.exists(pip_video_path)
                 and os.path.getsize(pip_video_path) > 10000)
The pip_video_path is a short clip (8-15s). When stream_loop=-1 with trim is applied
to a short clip, it may fail silently after the clip duration expires.

Fix: In the has_pip block (line 1733), change the trim to use the clip duration
with a large loop buffer instead of total_dur:
OLD:
  f"trim=0:{total_dur + 0.5},setpts=PTS-STARTPTS[pip_raw];\n")
NEW: Remove trim entirely — stream_loop=-1 handles looping:
  f"setpts=PTS-STARTPTS[pip_raw];\n")

Also check overlay_pip_on_narration() around line 1217 — same issue may exist.
Remove any trim that limits the looped pip to a fixed duration.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BUG 4 — Tweet likes show 0 (Nitter not parsing counts)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
In nitter_scraper.py lines 189-190:
  "likes": 0,
  "retweets": 0,
Nitter DOES show engagement stats in HTML. The parser is not extracting them.

Fix: In the tweet parsing section, add BeautifulSoup parsing for the stat elements.
Nitter renders stats as: <span class="tweet-stat"><span class="icon-heart"/><span>12.4K</span>
or similar. Find the tweet card HTML and extract:
  # Find stat spans
  stats = tweet_elem.find_all("span", class_="tweet-stat")
  for stat in stats:
    icon = stat.find("span", class_=lambda c: c and "icon" in c)
    count_span = stat.find_all("span")[-1] if stat.find_all("span") else None
    count_text = count_span.get_text(strip=True).replace(",","").replace(".","") if count_span else "0"
    # Parse K/M suffixes
    if "K" in count_text: count = int(float(count_text.replace("K","")) * 1000)
    elif "M" in count_text: count = int(float(count_text.replace("M","")) * 1000000)
    else:
        try: count = int(count_text) if count_text.isdigit() else 0
        except: count = 0
    if icon and "heart" in (icon.get("class") or [""])[0]: likes = count
    if icon and "retweet" in (icon.get("class") or [""])[0]: retweets = count

Then set engagement_rate = (likes + retweets * 2) / max(followers, 1000)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BUG 5 — Tweet card background — spice it up
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
In make_social_card_visual() around line 3167 (or make_remotion_social_card).
The tweet card currently has a solid black background box.

Fix: In the social segment scene, add a subtle red vignette glow behind the tweet card:
After the black card background drawbox, add:
  f"drawbox=x=220:y=60:w=1000:h=280:color=0x880000@0.25:t=fill,"
  f"vignette=PI/5:mode=backward,"
Also consider adding a faint animated scanline or grid pattern if SCANLINE_OVERLAY exists.
Keep the existing card border and text — just add depth to the background.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BUG 6 — Signal active scene shows duplicate body text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
In make_signal_active_scene() line 2626. The body text (which is the raw transcript)
is being rendered TWICE — once in the main text area, once elsewhere.

Read make_signal_active_scene() in full. Find where body/safe_body is rendered.
Remove the SECOND occurrence of safe_body drawtext.
The transcript text should only appear once — in the tweet-card-style box on the right.
The left panel (SIGNAL ACTIVE headline + metrics) should have NO body text.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BUG 7 — Intro narrator volume too low (drowned by music)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
In assembler.py around line 805 (intro mix):
  f"[intro_mus][tts_delayed]amix=inputs=2:duration=longest:weights=0.5 3.0,"
The intro music is at volume=0.05 before the mix, and weights are 0.5 (music) vs 3.0 (TTS).
But the intro music itself (volume=0.05 at input) combined with weight=0.5 means effective
music volume = 0.05 * 0.5 = 0.025. TTS = weight 3.0.
The narrator IS louder than music, yet user reports narrator is too low.

The issue: the TTS is delayed by 300ms (adelay=300|300) and the music is VERY short
(atrim 0:8, fade out from 6s). During the first 8 seconds the music dominates.

Fix: Reduce intro music volume further:
  volume=0.05 → volume=0.03
AND increase TTS delay reduction:
  adelay=300|300 → adelay=100|100 (narrator starts sooner)
AND boost TTS weight:
  weights=0.5 3.0 → weights=0.3 4.0

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BUG 8 — Random clip appears after "stay sovereign" outro
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Read the main assembly function (search for "build_episode" or "assemble_episode" or
the function that builds the final parts list). Find where outro/wrap segments are added.

The outro_branded_new.mp4 is added as the final segment. But somewhere a clip segment
is being appended AFTER the outro. 

Find the loop that processes segments/dialogue and ensure:
1. No clip segment is generated after the wrap/outro segment
2. If a clip is the LAST item in the dialogue list, it should be skipped (no clip after outro)

Look for the segment ordering logic. The fix: after the wrap segment is identified,
break out of any further segment processing. Set a flag `past_wrap = True` and skip
any clip segments when `past_wrap` is True.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BUG 9 — Background music interrupted at second 12 by scene transition
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
The global music bed (BG_MUSIC, applied in build_final_episode around line 4477) is
a single continuous track mixed over the whole episode. But scene transitions add a
swoosh sound effect that seems to cut/interrupt the music.

Find where transition swoosh is mixed. It likely uses amix with duration=first which
cuts the background audio. Change transition swoosh mixing to:
  Use duration=longest instead of duration=first
  OR apply the swoosh as a secondary overlay that does NOT interrupt the primary audio

Also: the music fade-in at the start (around second 12, after intro) is likely an
aevalsrc silence pad or deliberate fade. Find where the music starts in the first
non-intro segment and ensure it uses afade=t=in:st=0:d=2.0 (2s fade in) rather than
a hard cut in at second 12.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
VALIDATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
python3 -m py_compile video_pipeline_v3/assembler.py && echo ASSEMBLER_OK
python3 -m py_compile video_pipeline_v3/script_writer.py && echo WRITER_OK
python3 -m py_compile services/nitter_scraper.py && echo NITTER_OK
bash ~/protocol_pulse/regression_test.sh  # ZERO FAILs

THREE commits:
git add video_pipeline_v3/assembler.py && git commit -m "fix(assembler): bg_loop full color, PiP loop no trim, social bg depth, signal active dedup, intro volume, outro clip guard, music continuity"
git add video_pipeline_v3/script_writer.py && git commit -m "fix(script): strip [DATA]/[WARM]/[SETUP] tags before TTS"  
git add services/nitter_scraper.py && git commit -m "fix(nitter): parse actual likes/retweet counts from HTML"
git push

DO NOT touch: tts_engine.py, overnight_render_loop.py, daily_producer.py, gemini_grade.py