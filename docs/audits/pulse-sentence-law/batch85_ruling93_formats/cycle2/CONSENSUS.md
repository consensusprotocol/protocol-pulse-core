# Batch 85 cycle 2: NO DEFECT; batch 85 closes. qwen27b PASS 0.95, glm PASS 0.90, no consensus finding; panel $0.0024209. Grok not asked: no disagreement (ruling 107 (2)). Batch 85 total $0.0059928.

- **glm F1 [low]:** build_caption's release_formats is unguarded. glm itself concludes "fail-closed, not a release defect".
  - authorise refuses an unreadable 'formats' first, and _plan raises "STOP: the EDL's formats are unreadable" before any caption is built (the cycle-1 edit).
- **glm F2 [low]:** PROVENANCE keeps the 9:16's verdict for a 16:9-only run. This is intended: every format's verdict is reported, and only the released formats decide (release_verdict).
- **glm F3 [low]:** review_nonpass(run_dir, formats=()) would fall back to review_formats(run_dir). That is the EDL's formats, the correct value, not "both".
  - review_drop always passes the parsed formats, which are never empty (release_formats returns ('16x9',) or both).
