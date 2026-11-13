# pp-selectid audit 0855 (ruling 54's placement limits corrected): cycle 1 consensus

- grok: no P0 / P1, "SHIP: yes"; glm: "SHIP: yes"; qwen: "yes with conditions" (one P1).
- IMPLEMENTED (qwen P1): the prompt-level test now shows a short clip that CAN open: its line in the angle prompt reads
  "under 8 s: only the hook or the LAST clip". The test already showed the short clip that cannot open, the long clip
  that cannot open, and the unlimited clip.
- Verification: test_medley 90 OK; every other suite OK.
