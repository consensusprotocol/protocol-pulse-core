# X SPACES LAWS — Protocol Pulse Permanent Reference
# Status: GOSPEL. Load into every session touching X Spaces code.
# Created: 2026-03-08 | Updated: 2026-03-08 (V2 Senior Build)

---

## TRANSCRIPT TRUTH LAW

"context_only" transcripts (tweets, titles, metadata) are NEVER directly
quoted in episode narration as if they were speech. They may only appear
labeled as "X Spaces Context" and require impact_score >= 75 to inject.
Only "audio_replay" and "live_capture" sources produce narration-grade text.

Source constants (in transcript_fetcher.py):
- `AUDIO_REPLAY = "audio_replay"` — yt-dlp download + Whisper transcription
- `LIVE_CAPTURE = "live_capture"` — twspace-dl + rolling Whisper
- `CONTEXT_ONLY = "context_only"` — tweets/title only, NOT a real transcript

---

## WHISPER WORKER LAW

WhisperWorker is a singleton. Never instantiate WhisperModel inside fetch
functions. Call `WhisperWorker.get()` always. The model loads once and stays
in GPU memory across calls.

Model fallback order: distil-large-v3 -> small.en -> base.en -> base

---

## STATE LEDGER LAW

Every Space is tracked in `data/spaces_state.db` (SQLite with WAL mode).
No space is processed twice for the same state (idempotent).
Cron cycles are safe to race — the DB enforces single-write semantics.

States: discovered -> downloaded -> transcribed -> summarized -> injected -> published

---

## QUALITY GATE LAW

Minimum transcript quality to inject into narration:
- `word_count >= 150` (real speech floor)
- `language_probability >= 0.70` (Whisper confidence)
- `bigram_unique_rate >= 0.60` (repetition check — >40% repeated bigrams = ambient/looped)
- `source` must be `audio_replay` or `live_capture` for narration

Transcripts failing quality gate are stored but marked `usable: false`.

---

## MAP-REDUCE LAW

Transcripts > 2000 words use map-reduce summarization:
- Chunks: ~600 words each
- Map: Claude Haiku (claude-haiku-4-5-20251001) summarizes each chunk
- Reduce: Claude Sonnet (claude-sonnet-4-6) synthesizes final briefing
- This preserves editorial quality while respecting token budgets.
- Full transcript preserved in `full_transcript` field; summary in `transcript`.

---

## DIARIZATION LAW

All audio-derived transcripts attempt speaker diarization.
Fallback order: pyannote-audio -> energy-based heuristic -> all-HOST.
Speaker labels: HOST, GUEST_1, GUEST_2, GUEST_3.

Energy-based heuristic: silence gaps > 1.5s = speaker change.
Most-speaking speaker = HOST.

---

## PARALLEL SAFETY LAW

`spaces_pipeline.py`, `x_spaces_scraper/`, and `spaces_state.db` are fully
independent of the video render path. Safe to run during active renders.

`assembler.py` and `daily_run.py` integration patches are staged only —
applied via `staged_patches/` after render session exits.

---

## CRON SCHEDULE

```
*/5  spaces_monitor.py   — detect live + ended Spaces, update live_signals.json
*/10 run_scraper.py      — discover, fetch transcripts, generate articles
*/15 channel_daemon.py   — scan partner channels for new uploads
```

---

## INJECTION RULES

- `audio_replay` / `live_capture` with impact_score >= 40: inject with full narration
- `context_only` with impact_score >= 75: inject with "CONTEXT ONLY" label
- `context_only` with impact_score < 75: DO NOT inject
- Segments with `usable: false`: DO NOT inject into narration
- Speaker attribution: if diarized segments exist, use HOST's longest quote

---

## DATA FLOW (V2)

```
Twitter API v2 / Guest Token GraphQL / yt-dlp
        |
        v
  x_spaces_scraper/scraper.py -> find_spaces()
        |
        v
  spaces_state.db (state ledger — idempotent tracking)
        |
        v
  transcript_fetcher.py -> TranscriptFetcher.fetch()
    Source truth model:
      1. yt-dlp audio + WhisperWorker.get().transcribe() -> AUDIO_REPLAY
      2. Twitter API v2 tweets -> CONTEXT_ONLY (never narration)
      3. Metadata fallback -> CONTEXT_ONLY
    Quality gate: word_count, language_prob, repetition
    Diarization: pyannote -> energy-based -> all-HOST
    Map-reduce: Haiku chunks -> Sonnet synthesis (>2000 words)
        |
        v
  article_generator.py -> generate_article()
  pp_publisher.py -> publish to Protocol Pulse
        |
        v
  Cache: x_spaces_scraper/cache/
    - processed_ids.json (dedup)
    - transcript_{id}.json (cached transcripts)
    - last_run.json (pipeline stats)
```

## VIDEO PIPELINE INTEGRATION

### Bridge: `utils/spaces_pipeline.py`
- `get_latest_spaces_segment(max_age_hours=4)` -> segment dict or None
- Scans: `x_spaces_scraper/cache/` + `data/spaces/`
- Enforces transcript source truth and quality gates
- Returns highest-impact chunk as video segment with speaker attribution

### Injection Point: `daily_run.py` (via staged patch)
- Called between Step 5 (B-roll) and Step 6 (Assembly)
- Inserts segment before last segment (wrap/outro)
- Graceful: if no fresh spaces, skips silently

### Visual: `assembler.py` (via staged patch)
- Segment type `x_spaces` -> routes to `data_segment` scene
- Eyebrow override: `LIVE X SPACES SIGNAL` or `LIVE INTEL — CONTEXT ONLY`
- Uses standard narrator visual (waveform + branded overlay)

## IMPACT THRESHOLD

- Minimum score to inject into video: **40** (audio-derived), **75** (context-only)
- Score from `spaces_pulse.py:score_chunk()`:
  - Controversy words: +25
  - Data/metrics: +20
  - Named entity + prediction: +20
  - Breaking reference: +10
  - Length bonus: +5/+10/+15
- Max score: 100

## STATUS

Current status: **LIVE (V2)**

---

*This document governs all X Spaces pipeline code. Read before modifying any spaces-related files.*
