# Batch 115 (ruling 148 (1), render side), cycle 1 consensus

Reviewers: qwen27b (medium, 302.2 s, 41,175 chars of reasoning): PASS with one low finding. gpt-oss-20b (medium,
36.8 s, 22,161 chars): FAIL with two findings.

- gpt-oss F1 (high), "r4_sentences returns the runtime sentence for a voiceover-only failure": DISPROVED. It confuses
  the names: EDL_SOFT["rule_r4"] IS the voiceover sentence ("The voiceover runs over its length limit."); R4_RUNTIME
  is the length sentence. The tests "share alone" -> [voiceover] and "a story pin's R4" -> [voiceover] pass.
- gpt-oss F2 (medium), "sealed_ok(None) may raise TypeError": DISPROVED. sealed_ok's first line (edl_rules.py:89) is
  `if not isinstance(row, dict) or row.get("replayed") is not False: return False`.
- qwen F1 (low), "a runtime row that is a non-dict scalar reaches sealed_ok unguarded": traced. sealed_ok returns False
  for any non-dict, and `and` short-circuits before row.get. No crash. Now tested: a string row and a None row read
  None (commit 37b1ff7d on the branch).

Decision: no code change. Cycle 2 audits the callers and G5's window from another angle.
