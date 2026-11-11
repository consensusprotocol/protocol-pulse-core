# Heimdall audit

**Question:** 4b run 1 (HEAD 36e769d0, runs/fresh_20261111_190259) HELD in editorial: story_semantics.emergent_clusters crashed on sorted({None, 'name', ...}) because four whisper_words transcript records in the write-once editorial store (hand-made 2026-11-10 ~05:28 ET, outside the pipeline's writer) carry channel_id / channel_name / exact_title None while each video's meta.json (its identity record) has them; transcript_store.chunks copied the record's provenance. Fix: chunks() fills missing provenance fields from the video's meta.json and yields NO chunks when no channel identity exists anywhere (fail closed: unidentified text is no channel's evidence); _make_record (the pipeline's writer) refuses a meta without channel identity. Tests: a planted identity-less record takes its identity from meta.json; with none anywhere it yields no chunks; the writer refuses. Find real defects only: can a chunk still carry a None channel, can meta.json override a record's own non-None identity, can the fallback attribute text to the wrong channel, does the writer guard break a legitimate acquisition path (captions / whisper via acquire -> ensure_meta)? (this chunk: pipeline/test_editorial.py)

**Panel:** deepseek, qwen27b  |  **Cost:** $0.0090
## Consensus findings (majority of panel agrees)
- **[medium] pipeline/test_editorial.py:119** The writer-guard test exercises a dict with channel keys entirely ABSENT, but the 4b crash scenario (and the _plant_bare helper that models it) has channel keys PRESENT with value None. If _make_record's guard checks key presence (e.g. 'channel_id' not in record) rather than value (e.g. record.get('channel_id') is None), the test passes while the real-world None-valued records still slip through the writer.
  - evidence: `bare = {"schema": 1, "video_id": "GGGGGGGGGGG", "canonical_url": ts.canonical_url("GGGGGGGGGGG")}
        with self.assertRaisesRegex(ts.AcquisitionError, "no channel identity"):
            ts._make_`
  - fix: Add a second assertion (or a second test) that calls _make_record with a dict where channel_id/channel_name/exact_title are explicitly None (matching the _plant_bare shape) and also expects AcquisitionError. E.g.: bare_none = {"schema":1, "video_id":"HHHHHHHHHHH", "canonical_url":ts.canonical_url("HHHHHHHHHHH"), "channel_id":None, "channel_name":None, "exact_title":None}; with self.assertRaisesRegex(ts.AcquisitionError, "no channel identity"): ts._make_record(bare_none, "whisper_words", "fw", self.SEGS)
  - raised by qwen27b:F1; agree: deepseek, qwen27b

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- deepseek: [medium] No test that a record's own non-None channel identity takes precedence over meta.json. The fallback test only uses _plant_bare with all identity fields None, so it cannot detect if meta.json overrides a record's own identity.
- deepseek: [medium] Fail-closed test only covers the case where no meta.json exists. It does not cover meta.json present but lacking channel identity, which the fix says should also yield no chunks.
- deepseek: [medium] Writer guard test only checks refusal. It does not verify that _make_record still accepts a legitimate meta with channel identity, so a too-strict guard could break acquisition paths (captions/whisper via acquire -> ensure_meta).
- deepseek: [low] Fallback test uses a single video, so it cannot detect if the fallback accidentally attributes text to the wrong channel (e.g., via a global or wrong meta lookup).
