# Batch 85 cycle 1: no consensus finding. qwen27b PASS 0.95 with 0 findings; glm PASS 0.82 with 3 low notes, none agreed. Panel $0.0035719. Grok not asked: no disagreement on the verdict (ruling 107 (2)).

- **glm F1, closed anyway.** build_caption's release_formats call is unguarded.
  - authorise() already refuses an unreadable or malformed 'formats', and _plan reads the formats before any caption is built.
  - Still, _plan now turns a ValueError into "STOP: the EDL's formats are unreadable".
- **glm F2, FALSE on the code.** "an absent 16x9 G18 makes 'missing' empty".
  - With reads = {'16x9': []}, any(...) over no readings is False, so every headline claim is reported missing ("no readings = all", the docstring, unchanged).
- **glm F3, closed anyway.** With the EDL's formats unreadable, PROVENANCE said release_formats both.
  - It now records None (nothing may be released). The hold "release formats unreadable" was already listed and the verdict HOLD.
- **Cross-examination, FALSE on the code.**
  - build_caption re-reads the EDL from disk: no. _plan passes snap, and build_caption uses (snap or snapshot(...))["edl"], the same verified bytes.
  - "(both: none sealed)" printed for a valid both-list: no. Only formats None prints it; ['16x9', '9x16'] is truthy and prints "(sealed)".
- **Suites after the two edits (worktree):** test_release_auth 31, test_telegram_delivery 24, test_review_drop 22, all passed.
  - test_fresh needs the main tree's untracked references (FileNotFoundError on references/v2f_2026-11-06/run/vo_audio/VO_MANIFEST.json in the worktree). It runs on main with the staged merge.
