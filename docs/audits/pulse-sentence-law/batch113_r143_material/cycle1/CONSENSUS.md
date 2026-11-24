# Batch 113 (ruling 143, the lock's material / non-material principle), cycle 1 consensus

Run 16:12 ET Nov 17 (qwen27b effort medium, 55,436 chars of reasoning; gpt-oss-20b effort medium, 9,005 chars). Both
said FAIL. Each finding was read on the morning of Nov 18 against the code itself; the reviewers saw only diff hunks:
- qwen F1 (critical), "relisten() calls canon.same_words but never imports canon": DISPROVED. lock_precheck.relisten
  imports it locally, on the line after `from difflib import SequenceMatcher` (outside the hunk). Module-level code
  imports it the same way in each function (e.g. :239).
- qwen F2 (high), "the ticker rule is dead code: the regex \b[A-Z][a-z]+\b never matches an all-caps word":
  DISPROVED. That regex is in neither the code nor the audited diff, where only the changed `if` line was shown.
  pinned._lv2_critical matches `[A-Za-z][A-Za-z'’-]*`, so 'IBIT' matches and `len(w) >= 2 and w.isupper()`
  decides it. TestRuling143.test_a_ticker_holds_unless_both_audio_readings_agree passes, including the
  sentence-opening ticker.
- gpt-oss F1/F2 (high), "material_pair / audio_share / wrong_audio get strings, not token lists": DISPROVED. In
  adjudicate_lock, r, p = canon.canon_tokens(run_t), canon.canon_tokens(pin_t), and s is canon_tokens(sec_t) minus
  fillers, all token lists; r[a:b] and p[c:d] are lists.

Decision: no code change from cycle 1.
