# C1 CONSENSUS (written by the pp-selectid session, ruling 118: Heimdall seats only)
Seats answered: 2 of 3 (qwen3.8-27b, gpt-oss-20b; gemma-4-31b-it HTTP 429, no answer). P0/P1: 0 and 0.
- qwen P2 (the value flag counts toward REVIEW_FLAGS_MAX = 3): BY DESIGN. The orchestrator's rule caps a flagged
  package at 3 flags; its 18:18 ET Nov 23 order lets the builder raise one of ITS counts or caps when that alone blocks
  a through-lined, hard-gated package, written on the state line. No code change.
- qwen P3 ("value.ok" attribute access in inventory): DISPROVED. The diff reads `value.get("soft") and
  value.get("ok") is not True` (package.py:4742's row); there is no attribute access.
- qwen P3 (val["ok"] direct access) and P3 (answers record None for an absent sub-field): pre-existing contract of
  takeaway_value (ok and measured are always set; L-l: a reply counts only whole); no change.
- gpt-oss P2 (measured stored as "True" / 1 never softens): fail-closed by intent (L-l: exact types; a non-True
  measured is not a measured verdict). P3 (ok None not flagged): DISPROVED: `is not True` flags it. P2 (an ok=True line
  with no measured verdict): pre-existing takeaway_value contract (ok only on a measured clear yes); outside this change.
All four questions answered "no / yes / yes / no" by both seats. Nothing to fix; cycle 2 cross-examines the same diff.
