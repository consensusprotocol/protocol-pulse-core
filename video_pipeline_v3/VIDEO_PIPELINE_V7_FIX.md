# VIDEO PIPELINE V7 — DEFINITIVE FIX PROMPT
## For Claude Code on Ultron — `~/protocol_pulse/video_pipeline_v3/`

You are fixing the Protocol Pulse "Pulse Check" video pipeline. PBX just watched the latest test output and has specific feedback. Fix ALL of the following issues in one session. Do NOT stop until you've run a test render and verified all fixes are visible.

---

## ISSUES TO FIX (all of them, no exceptions)

### FIX 1: INTRO VIDEO NOT PLAYING (assembler.py)
The intro logo video renders as part_000_intro.mp4 (53MB) but appears as a black screen in the final concat. Root cause: `normalize_part()` re-encodes with `-crf 20` but the intro's original codec may have pixel format incompatibility. Fix: in `make_intro_video()`, force re-encode to `yuv420p` with explicit pixel format AND add `-pix_fmt yuv420p` to the scale filter. Also add a test: after writing part_000_intro.mp4, run `ffprobe` on it and log the first video frame to confirm it has real content. The normalize_part function should also explicitly add `-pix_fmt yuv420p` to the output vf filter.

Additionally: add fade-IN at the start of the intro (0.5s) so the logo fades in from black rather than hard-cutting in.

### FIX 2: INTRO FADES INTO COLD OPEN (assembler.py)
Currently the intro hard-cuts into the cold open. Instead:
- Add a 1.5s audio crossfade + video fade-out at the END of the intro video
- The intro music should fade to silence (not hard cut) as it transitions into the cold open narration
- Use ffmpeg afade filter: `afade=t=out:st=(intro_dur-1.5):d=1.5` on the intro audio
- Use ffmpeg vf fade: `fade=t=out:st=(intro_dur-0.5):d=0.5` on the intro video  
Do this inside `make_intro_video()` before returning.

### FIX 3: OUTRO — PLAY FULL WITH FADE + TAG_VERTICAL.MP4 (assembler.py)
Currently outro.mp4 (5s) hard-cuts at the end. Fix:
- Let outro.mp4 play in full
- Add 1s audio fade-out and 0.5s video fade-to-black at the end of outro
- AFTER the outro, append `assets/tag_vertical.mp4` (3.5s) as the final element
- tag_vertical.mp4 plays in full, then fades to black (0.5s)
- The pp_outro.mp3 should be mixed into the outro video and fade out with it
- Add `TAG_VIDEO = os.path.join(ASSETS, "tag_vertical.mp4")` constant
- Create `make_tag_video(output_path: str) -> str` function that normalizes tag_vertical.mp4 to 1920x1080, adds silent audio if none, adds 0.5s fade-to-black at end

In `assemble_episode()`, after the outro part, append the tag video as the final part.

### FIX 4: SINGLE BACKGROUND PER EPISODE (assembler.py)
Currently `_bg_index` cycles through all 4 backgrounds, creating a jarring visual experience.

New rule: **Pick ONE background at EPISODE START (random), use it for ALL host segments in that episode.**

Change:
```python
# At top of assembler.py, change _bg_index global to _episode_bg
_episode_bg = None  # Set once per episode run

# In assemble_episode(), add near the top (after work_dir creation):
import random
_episode_bg = random.choice([b for b in BACKGROUNDS if os.path.exists(b)])
logger.info(f"Episode background: {os.path.basename(_episode_bg)}")

# In make_host_visual(), replace the rotating background logic with:
bg_path = _episode_bg if (_episode_bg and os.path.exists(_episode_bg)) else BACKGROUNDS[0]
```

Remove the `_bg_index` global and `next_background()` function entirely.

### FIX 5: THUMBNAIL OVERLAY DURING SETUP/REACT SEGMENTS (assembler.py + script_writer.py)
When a host is doing SETUP or REACT for a clip, show that clip's YouTube thumbnail as an overlay on the background video.

Implementation:
1. In `assemble_episode()`, build a dict: `clip_thumbnails = {}` that maps `rank → thumbnail_path`
2. For each extracted clip, call `fetch_youtube_thumbnail(clip_info)` to get the thumbnail
3. Pass `thumbnail_path` to `make_host_visual()` as an optional parameter

Add function:
```python
def fetch_youtube_thumbnail(clip_info: dict) -> str:
    """Download YouTube thumbnail for a clip. Returns local path or ''."""
    video_id = clip_info.get("video_id", "")
    if not video_id:
        return ""
    url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
    thumb_path = f"/tmp/thumb_{video_id}.jpg"
    if os.path.exists(thumb_path):
        return thumb_path
    try:
        import urllib.request
        urllib.request.urlretrieve(url, thumb_path)
        return thumb_path if os.path.exists(thumb_path) else ""
    except Exception:
        # fallback to hqdefault
        try:
            url2 = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
            urllib.request.urlretrieve(url2, thumb_path)
            return thumb_path if os.path.exists(thumb_path) else ""
        except Exception:
            return ""
```

In `make_host_visual()`, add `thumbnail_path: str = ""` parameter. When provided, overlay the thumbnail as a picture-in-picture in the right side of the frame:
- Position: right side, vertically centered — x=1100, y=190
- Size: 760x430 (16:9 scaled)
- Semi-transparent border: use `pad=762:432:1:1:color=0xFFFFFF@0.6` on the thumbnail
- Brightness on the background: reduce to 0.25 (dimmer when thumbnail is present)
- The thumbnail is a JPEG — use `-i thumbnail_path` as input [2] (or [3] if watermark present)

In `assemble_episode()`, pass the appropriate thumbnail when calling `make_host_visual()` for setup/react segments (look up the current clip_rank from the dialogue entry).

### FIX 6: GLITCH TRANSITION AUDIO VOLUME BOOST (assembler.py)
The glitch_transition_waud.mp4 has AAC audio but it's inaudible. In `make_transition_visual()`, add audio normalization and volume boost:
```
"-af", "volume=3.0,loudnorm=I=-6:TP=-0.5:LRA=5"
```
Add this to the ffmpeg args in the glitch transition encoding.

### FIX 7: SCRIPT TONE — PUNCHY MMA-STYLE, NOT GENERIC (script_writer.py)
Replace the SCRIPT_PROMPT with this improved version that enforces the right tone:

The key changes to the prompt:
```
OLD: "Keep host dialogue SHORT. The show is the clips, not the commentary."
NEW: See full prompt below
```

Replace the system description and tone instructions in `SCRIPT_PROMPT` with:

```python
SCRIPT_PROMPT = """You are writing host dialogue for "Pulse Check" — a daily Bitcoin highlight show.
Think: ESPN SportsCenter meets Cypherpunk Gossip. MMA Central energy. The clips are the star.

HOST 1 (Jessica) — Sharp, fast, no-fluff. Sets up each clip like a boxing ring announcer.
HOST 2 (Chris) — Hot takes, contrarian, dry wit. Reacts like he just saw a knockout.

TONE RULES (NON-NEGOTIABLE):
- NEVER generic. Never say "interesting" or "really impactful" or "that's great stuff."
- SETUP lines = 1-2 sentences MAX. A teaser, not a summary. Leave them wanting the clip.
- REACT lines = 1-2 sentences MAX. A hot take or one sharp observation. Not a recap.
- Cold open = 1 explosive sentence. Most outrageous or interesting story. Hook them in 3 seconds.
- Wit over wisdom. Brief over brilliant. Gossip energy, Bitcoin knowledge.
- Think: "Yo, you gotta hear what Saylor just said about this" NOT "Michael Saylor made some interesting comments about..."
- Reactions should feel genuine — surprised, amused, sharp, or skeptical. Never neutral.

SOCIAL SEGMENT (MANDATORY — include this in EVERY episode):
After the last clip, add a "WHAT THE BITCOIN INTERNET IS SAYING" segment:
- Jessica reads 2-3 of the top tweets or Nostr posts provided (sharp, brief, 1 line each)
- Chris drops a one-liner reaction to the best one
- This is a separate section in the dialogue with type: "social_segment"

{clips_info}

BTC Price Today: {btc_price}
Top Tweets/Nostr Posts Today: {social_posts}

OUTPUT FORMAT (strict JSON):
{{
  "cold_open": "explosive 1-sentence cold open",
  "dialogue": [
    {{"host": 1, "text": "...", "type": "cold_open"}},
    {{"host": 1, "text": "...", "type": "setup", "clip_rank": 1}},
    {{"host": "CLIP", "rank": 1}},
    {{"host": 2, "text": "...", "type": "react", "clip_rank": 1}},
    {{"host": 1, "text": "...", "type": "setup", "clip_rank": 2}},
    {{"host": "CLIP", "rank": 2}},
    {{"host": 2, "text": "...", "type": "react", "clip_rank": 2}},
    ...
    {{"host": 1, "text": "...", "type": "social_segment"}},
    {{"host": 2, "text": "...", "type": "social_segment"}},
    {{"host": 1, "text": "...", "type": "wrap"}}
  ],
  "shorts_quotes": ["best one-liner 1", "best one-liner 2", "best one-liner 3"]
}}"""
```

In `write_script()`, add `social_posts` parameter. Fetch top tweets/Nostr posts from the database or use a placeholder if not available:
```python
social_posts = kwargs.get("social_posts", "No social posts available today.")
prompt = SCRIPT_PROMPT.format(clips_info=clips_info, btc_price=btc_price, social_posts=social_posts)
```

### FIX 8: SOCIAL SEGMENT VISUAL (assembler.py)
When the dialogue entry type is `social_segment`, create a special visual:
- Background: episode background (same loop), dimmed to 0.2
- Overlay a static title card: "WHAT THE BITCOIN INTERNET IS SAYING" — white text, centered, top third
- Add the tweet text as a subtitle in the lower two-thirds (use drawtext with a semi-transparent dark box behind the text)
- Keep the host speaker bar (red for Jessica, blue for Chris)
- Handle this in `make_host_visual()` by checking if `label` contains "social" or by passing a `segment_type` param

### FIX 9: SARAH VOICE — REPLACE WITH MATILDA/DEBORAH (tts_engine.py or wherever Jessica's voice ID is set)
Sarah/Jessica's current voice (`cgSgspJ2msm6clMCkdW9`) has a moaning sentence ending problem. Switch to one of the auditioned alternatives. Best option based on prior auditions: try `VeCVR24o7g2y1IxLJzZs` (Deborah - Female Newscaster) or `FyrYFW3P9GUxA348YGWu` (Madison Rae - News Anchor).

Check where Jessica's voice ID is defined — likely in `tts_engine.py` or `dual_host_tts.py`. Swap to Deborah first (ID: `VeCVR24o7g2y1IxLJzZs`). Also add `stability: 0.55, similarity_boost: 0.75, style: 0.0, use_speaker_boost: true` to the ElevenLabs API call to reduce the moaning artifact.

Find the voice settings dict in tts_engine.py or dual_host_tts.py and add:
```python
"voice_settings": {
    "stability": 0.55,
    "similarity_boost": 0.75,
    "style": 0.0,
    "use_speaker_boost": True
}
```

---

## EXECUTION ORDER

1. Read ALL files first: `assembler.py`, `script_writer.py`, `tts_engine.py`, `dual_host_tts.py`, `daily_producer.py`
2. Apply fixes in PRIORITY ORDER (see below)
3. Verify `tag_vertical.mp4` exists: `ls -lh ~/protocol_pulse/video_pipeline_v3/assets/tag_vertical.mp4`
4. Test render: `cd ~/protocol_pulse/video_pipeline_v3 && python3 daily_producer.py --test --skip-scan 2>&1 | tail -50`
5. Download and verify: `ls -lh output/$(ls -t output/ | head -1)/`
6. Check parts list: `ls output/$(ls -t output/ | head -1)/work/`
7. Verify intro is NOT black: `ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1 output/$(ls -t output/ | head -1)/work/part_000_intro.mp4`
8. Git commit: `git add -A && git commit -m "feat: V7 — intro fix, single BG loop, thumbnail overlays, fade transitions, tag video, punchy script tone, social segment, Deborah voice" && git push origin main`

## PRIORITY ORDER + 15-MINUTE RULE

**TIER 1 — Ship these no matter what (simple, high-impact):**
- FIX 1: Intro black screen (pixel format)
- FIX 2: Intro fade in/out
- FIX 3: Outro full play + fade + tag_vertical.mp4
- FIX 4: Single background per episode
- FIX 6: Glitch transition audio boost
- FIX 7: Script tone rewrite (MMA-gossip style)
- FIX 9: Jessica voice → Deborah + stability settings

**TIER 2 — Attempt, skip if >15 min of debugging:**
- FIX 5: Thumbnail PIP overlay (complex ffmpeg filtergraph — if it's fighting you, add a `# TODO: thumbnail PIP` comment and move on)
- FIX 8: Social segment visual (depends on FIX 7 structure being clean)

**15-MINUTE RULE:** If any single fix requires more than 15 minutes of active debugging (errors, filtergraph issues, import problems), mark it with `# TODO: [fix name] — skipped, needs iteration` and proceed to the next fix. **Do not let one hard fix block the other 7 easy wins.** The Tier 1 fixes alone will make the video dramatically better.

## SOCIAL POSTS NOTE

`tweet_screenshot.py` and `nostr_capture.py` exist in `services/video_engine/sources/` but are NOT yet wired to `video_pipeline_v3/`. For now, in `write_script()`, default `social_posts` to a best-effort placeholder:

```python
social_posts = "Bitcoin Twitter is reacting to today's price action. Nostr devs are building. The community is sovereign and online."
```

Wire the actual live feed in a future session. The goal today is to get the segment STRUCTURE into the script and assembler so it renders correctly. Placeholder copy is fine.

---

## WHAT SUCCESS LOOKS LIKE
After the test render, provide `scp` commands and confirm:
- [ ] Intro logo video VISIBLE (not black screen)
- [ ] Intro fades in, then fades out into cold open
- [ ] Single background used throughout all host segments
- [ ] Thumbnail visible as overlay when hosts intro/react to a clip
- [ ] Glitch transition AUDIBLE (woosh sound)
- [ ] Outro plays full, fades to black, then tag_vertical.mp4 plays as final element
- [ ] Host commentary is short and punchy (read the script.json to verify)
- [ ] Social segment present in script
- [ ] Jessica's voice changed to Deborah

---

## RELAY / INFRA
- Ultron: `~/protocol_pulse/video_pipeline_v3/`
- Git push from Ultron (SSH configured)
- Token: `581b1076ca6d8a8809997d24f0869431ffd75c64de9ea703b6ab0f3e39fbd552`
- Test cmd: `python3 daily_producer.py --test --skip-scan`
