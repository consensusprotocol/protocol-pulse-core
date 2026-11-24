# Batch 115 (ruling 148 (1), render side), cycle 2 consensus (the callers and the release decision)

- qwen27b (effort medium, 248.5 s, 34,163 chars of reasoning): PASS, no findings. It traced (a)-(e):
  - (a) edl_path None: open(None) raises TypeError, which g5_window's existing except catches: ruling 12's window.
  - (b) A replay copies PINNED_DECISION.json, so the same sealed pin behaves the same.
  - (c) 57.0 s is accepted and recorded as a deviation from the target; 44.0 s is refused.
  - (d) R4 is SOFT, and the HARD rules hold before flag_soft_rules runs.
  - (e) The old inline loop was no function, so nothing imported it.
- gpt-oss-20b, effort medium: NO VERDICT. It stopped at its 24,576-token limit (finish "length", 87,621 chars of
  reasoning, empty content). Kept in gptoss_medium_length/ and recorded, not counted.
- gpt-oss-20b, re-asked at effort low (6.0 s, 620 chars of reasoning): FAIL with 4 findings, all DISPROVED from the
  files (it saw only the diff hunks):
  - F1, "os/json not imported in edl_rules": edl_rules.py:38-39 import both.
  - F2, "FINAL_TAIL_S undefined": edl_rules.py:229 defines it (14.30).
  - F3/F4, "EDL_SOFT not imported in run_fresh": it is defined in run_fresh.py itself (:177).
  - Every one of these paths runs in test_ruling148_runtime.py, which passes.

Mutations 9 of 9 killed (b148/MUTATIONS.log); must-fail on the live code: 19 failures, 4 controls pass.

Decision: no code change. Batch 115 is ready. It merges AFTER the Nov 18 exception video's render: main stays as it
is until delivery (ruling 149: the render first; the launcher's preflight wants a clean pipeline tree). It needs no
lockstep (no decoder file).
