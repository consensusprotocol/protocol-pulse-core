# Heimdall audit

**Question:** 4b run 1 (HEAD 36e769d0, runs/fresh_20261111_190259) HELD in editorial: story_semantics.emergent_clusters crashed on sorted({None, 'name', ...}) because four whisper_words transcript records in the write-once editorial store (hand-made 2026-11-10 ~05:28 ET, outside the pipeline's writer) carry channel_id / channel_name / exact_title None while each video's meta.json (its identity record) has them; transcript_store.chunks copied the record's provenance. Fix: chunks() fills missing provenance fields from the video's meta.json and yields NO chunks when no channel identity exists anywhere (fail closed: unidentified text is no channel's evidence); _make_record (the pipeline's writer) refuses a meta without channel identity. Tests: a planted identity-less record takes its identity from meta.json; with none anywhere it yields no chunks; the writer refuses. Find real defects only: can a chunk still carry a None channel, can meta.json override a record's own non-None identity, can the fallback attribute text to the wrong channel, does the writer guard break a legitimate acquisition path (captions / whisper via acquire -> ensure_meta)? (this chunk: pipeline/transcript_store.py)

**Panel:** deepseek, qwen27b  |  **Cost:** $0.0090
## Consensus findings (majority of panel agrees)
- **[high] pipeline/transcript_store.py:423** chunks() only attempts the meta.json fallback when both channel_id and channel_name are missing. If a record has one non-None channel field but another provenance field (e.g. channel_name, channel_id, exact_title) is None, the fallback is skipped and the chunk still carries None, so the original sorted({None, ...}) crash can still occur.
  - evidence: `if not (prov.get("channel_id") or prov.get("channel_name")):`
  - fix: Always fill any missing PROVENANCE_FIELDS from meta.json (not only when both channel fields are absent), then fail closed if any required identity field remains None.
  - raised by deepseek:F1; agree: deepseek, qwen27b
- **[high] pipeline/transcript_store.py:180** _make_record's new guard only requires one of channel_id or channel_name, so it can still write a record with the other channel field (and exact_title) None. That partial identity then bypasses the chunks() fallback and can still produce None provenance.
  - evidence: `if not (meta.get("channel_id") or meta.get("channel_name")):   # every record carries its source identity`
  - fix: Require all required identity fields (at least both channel_id and channel_name, and exact_title if it is part of PROVENANCE_FIELDS) before writing a record.
  - raised by deepseek:F2; agree: deepseek, qwen27b
- **[medium] pipeline/transcript_store.py:427** A chunk can still carry a None channel_id (or None channel_name). The guard only requires that at least ONE of the two fields is truthy; the other may remain None. If the downstream clustering code (story_semantics.emergent_clusters) collects a specific field—e.g. {c['channel_id'] for c in chunks}—into a set and calls sorted(), a None value will still be in the set and the original TypeError will recur.
  - evidence: `if not (prov.get("channel_id") or prov.get("channel_name")):
        mp = os.path.join(_vdir(rec["video_id"]), "meta.json")
        if os.path.exists(mp):
            with open(mp) as f:
             `
  - fix: After the meta.json fallback, if either channel_id or channel_name is still None, fill it from the other (e.g. prov['channel_id'] = prov.get('channel_id') or prov.get('channel_name')) so that every emitted chunk has both fields non-None. Alternatively, require BOTH to be non-None before emitting chunks: change the second guard to 'if not (prov.get("channel_id") and prov.get("channel_name")): return []'.
  - raised by qwen27b:F1; agree: deepseek, qwen27b

## Raised but not agreed
- qwen27b:F2 [low] No exception handling around json.load for the meta.json fallback. A corrupt, truncated, or non-UTF-8 meta.json will raise json.JSONDecodeError / UnicodeDecodeError uncaught, crashing the pipeline with a new, harder-to-diagnose error instead of the original sorted() TypeError. The four hand-made records were written outside the pipeline, so their meta.json files are not guaranteed to be well-formed. (agree: 1)

## Added in cross-examination (not voted on)
- none
