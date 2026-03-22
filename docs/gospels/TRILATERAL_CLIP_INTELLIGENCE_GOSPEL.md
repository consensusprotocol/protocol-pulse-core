# GOSPEL: TRILATERAL CLIP INTELLIGENCE
# Version 1.0 | March 2026
# Status: SPEC WRITTEN — NOT YET BUILT

## THE INSIGHT
Every source video we download contains more signal than we currently extract.
Today we ask one question per video: "What is the best 30-45s for PBX to react to?"
We should ask three independent questions from the same transcript data.
Zero additional downloads. Zero additional API cost for transcript.
One extra Claude call per video per day.

## THREE INDEPENDENT CLIP SELECTIONS PER SOURCE VIDEO

SELECTION 1 — PULSE CHECK CLIP (existing, optimized)
  Purpose:    Episode segment for PBX to introduce and react to
  Length:     25-45 seconds
  Criteria:   Signal density, setup-ability, narrative fit, host reaction potential
  Output:     clips/clip_N_CHANNEL_ID.mp4 (current behavior, unchanged)
  Selector:   Claude Sonnet (current behavior, unchanged)

SELECTION 2 — MONTAGE CLIP (new — independent selection)
  Purpose:    Standalone highlight for Daily Montage compilation
  Length:     12-22 seconds — SHORT, punchy, self-contained
  Criteria:
    - Works with ZERO context — viewer hasn't seen the episode
    - Single complete thought or striking statement
    - Visually compelling moment (speaker animated, data on screen, etc.)
    - No mid-sentence start or end
    - No "as I was saying" or "so like I mentioned" openers
    - Optimal: starts with a strong noun or number, ends with a period
  Output:     clips/montage_clip_N_CHANNEL_ID.mp4 (NEW file, separate download)
  Selector:   Local Qwen3-Coder (zero API cost — pure timestamp selection from transcript)

SELECTION 3 — SOCIAL SHORT CLIP (new — independent selection)
  Purpose:    8-12 second vertical crop for Shorts/Reels/TikTok
  Length:     8-12 seconds
  Criteria:
    - Single sentence. One idea. Hits in under 10 seconds.
    - Works WITHOUT audio (assume silent autoplay) — strong visual
    - Quotable text overlay potential
    - Speaker is looking at camera or making strong gesture
  Output:     clips/social_clip_N_CHANNEL_ID.mp4 (NEW, vertical crop)
  Selector:   Local Qwen3-Coder

## WHERE IN THE PIPELINE THIS RUNS

CURRENT FLOW:
  channel_scanner.py → full transcript → Claude selects Pulse Check timestamps
                                       → clip_extractor downloads segment

NEW FLOW:
  channel_scanner.py → full transcript → Claude selects Pulse Check timestamps (unchanged)
                                       → Qwen selects Montage timestamps (same transcript)
                                       → Qwen selects Social timestamps (same transcript)
                     → clip_extractor downloads ALL THREE segments (3 yt-dlp calls per source)
                     → saved to separate folders

## MONTAGE CLIP SELECTION PROMPT (Qwen3-Coder)
"You are selecting the single best SHORT standalone highlight clip from this video transcript.
The clip will appear in a daily compilation reel — viewers have NO prior context.
Select the 12-22 second window that is the most self-contained, punchy, and quotable moment.
The ideal clip: starts mid-statement (not mid-breath), ends at a natural period or pause,
contains one complete strong idea, needs zero context to be understood.

TRANSCRIPT:
{full_transcript}

VIDEO TITLE: {title}
CHANNEL: {channel}

Return ONLY JSON: {montage_start_sec: int, montage_end_sec: int, quote: str, reason: str}"

## SOCIAL SHORT SELECTION PROMPT (Qwen3-Coder)
"Select the single best 8-12 second clip for a vertical social short.
One sentence. One idea. Works silent. Hits immediately.
Return ONLY JSON: {social_start_sec: int, social_end_sec: int, quote: str}"

## MONTAGE PRODUCER UPDATE
montage_producer.py currently uses Pulse Check clips (selections.json).
After this build it must use montage_clips (montage_selections.json) instead.
The montage clips are independently selected — completely different moments.

## SOCIAL CLIP PIPELINE (Phase 2)
social_clip_producer.py (to build later):
  - Vertical crop 9:16 from social_clip
  - Add caption overlay (quote text, white on black bar)
  - Add Protocol Pulse watermark
  - Output: clips/social_clip_N_vertical.mp4
  - Auto-post to X as native video reply to daily article tweet

## FILES TO MODIFY
clip_extractor.py:      Add extract_montage_clip() and extract_social_clip() functions
channel_scanner.py:     Add Qwen-based montage/social timestamp selection
daily_producer.py:      Save montage_selections.json alongside selections.json
montage_producer.py:    Read montage_selections.json instead of selections.json

## DATA SCHEMA ADDITION
montage_selections.json (new file alongside selections.json):
{
  "date": "2026-03-21",
  "clips": [
    {
      "rank": 1,
      "channel": "TheStreet",
      "video_id": "xyz",
      "montage_start_sec": 142,
      "montage_end_sec": 159,
      "quote": "The upper rail of that channel lands exactly on the 2021 bull market peak.",
      "pulse_check_start_sec": 38,  // reference to original selection
      "montage_clip_path": "clips/montage_clip_1_TheStreet_xyz.mp4"
    }
  ]
}

## WHAT NEVER CHANGES
- Pulse Check clip selection is UNCHANGED — same Claude Sonnet call, same timestamps
- Montage/Social selection never overrides or influences Pulse Check selection
- If Qwen unavailable: montage falls back to Pulse Check clips (current behavior)
- Full transcript must exist before either new selection runs
- Never re-download a video just for montage — use existing transcript data

## CC SPEC LOCATION
~/protocol_pulse/docs/cc_trilateral_clip_intelligence.md (to be written)

## BUILD ORDER
1. Modify clip_extractor.py to support 3 clip types per source video
2. Modify channel_scanner.py to run Qwen montage/social selection on existing transcripts
3. Modify daily_producer.py to write montage_selections.json
4. Modify montage_producer.py to use montage_selections.json
5. Test: verify montage clips are different moments than Pulse Check clips
6. Phase 2: social_clip_producer.py for vertical Shorts
