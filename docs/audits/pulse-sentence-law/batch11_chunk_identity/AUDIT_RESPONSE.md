# Batch 11 (chunk identity: 4b run 1 crashed on a None channel): dispositions

Why: 4b run 1 (HEAD 36e769d0, runs/fresh_20261111_190259) HELD in editorial: story_semantics.emergent_clusters
crashed on sorted({None, ...}). Four transcript.whisper_words.json records (qo8rDU3bbMo Simply Bitcoin,
jbDqdLytkNM Bitcoin Magazine, eEB0nt6jvEw Marty Bent, RXTVaDsN11M DataDash), hand-made 2026-11-10 ~05:28 ET
outside transcript_store's writer, carry channel_id / channel_name / exact_title None; each video's meta.json
has them. The write-once store keeps them; chunks() copied the record's provenance.

Fix: chunks() fills every provenance field the record lacks from the video's meta.json (never overriding a
field the record has; an absent / unreadable / corrupt / non-dict meta.json fills nothing) and yields chunks
only when BOTH channel fields are set (fail closed); the writer (_make_record) requires both. Measured: all
578 canonical records in the store have both after the fill (no evidence lost); the four records now chunk as
their channels (22 / 34 / 32 / 69 chunks). Bible E-FAIL-030.

Audited: cross-LLM GPT-4o + Gemini (Grok blocked); Heimdall deepseek + qwen27b per file and a second pass on
the revised transcript_store.py (heimdall_r2/).

## Implemented
- Heimdall consensus [high] (deepseek F1) + [medium] (qwen27b F1): the fallback ran only with BOTH channel
  fields missing, so a partial record could still put a None into a chunk: now any None field is filled, and
  a chunk needs both channel fields.
- Heimdall consensus [high] (deepseek F2): the writer accepted one channel field: now both are required.
- Cross-LLM P0 [both] + Heimdall qwen27b F2 [low]: a corrupt meta.json crashed chunks(): now (OSError,
  ValueError) and a non-dict fill nothing and the record yields no chunks. Cross-LLM P1 [Gemini]: test.
- Heimdall consensus [medium] (test): the writer test now also covers keys present but None, and one field
  only; new tests: a partial record is completed and never overridden by meta.json; a corrupt meta.json
  yields no chunks.

- Heimdall second pass, consensus [low] (qwen27b F1): rec["video_id"] was read outside the guard: a
  record without a video_id now yields no chunks.

## Rejected
- Cross-LLM P1 [both] "follow-up ticket for the core pulse-sentence-law feature": the audit feature name is
  the session's standing one for every Pulse Check batch; this is an editorial-store fix.

## Verification
test_editorial (non-live) + test_editorial_robust + test_same_event_merge + test_story_ledger: 47 passed
(4 live-GPU skips); the four real records chunk with their channels.
