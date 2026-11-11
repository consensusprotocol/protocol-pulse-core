# Heimdall audit

**Question:** Second pass after the batch-11 consensus: transcript_store.chunks now fills EVERY provenance field the record lacks (None) from the video's meta.json, never overriding a field the record has; an absent / unreadable / corrupt / non-dict meta.json fills nothing; a record yields chunks only when BOTH channel_id and channel_name are set afterwards (fail closed); _make_record (the pipeline's writer) requires both. Measured: all 578 canonical records in the store have both after the fill. Report only real defects you can quote.

**Panel:** deepseek, qwen27b  |  **Cost:** $0.0092
## Consensus findings (majority of panel agrees)
- **[low] pipeline/transcript_store.py:427** rec["video_id"] is accessed outside the try/except that guards the meta.json read. If a record lacks the key (KeyError) or has video_id set to None (TypeError from _vdir(None)), the exception is not caught by `except (OSError, ValueError)` and propagates as an unhandled crash, violating the documented fail-closed contract ('the record yields no chunks').
  - evidence: `with open(os.path.join(_vdir(rec["video_id"]), "meta.json")) as f:
                m = json.load(f)
        except (OSError, ValueError):               # absent / unreadable / corrupt: nothing to fill`
  - fix: Either use rec.get("video_id") and guard against None before calling _vdir, or broaden the except clause to also catch (KeyError, TypeError) so the function falls through to the fail-closed `return []` path.
  - raised by qwen27b:F1; agree: deepseek, qwen27b

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
