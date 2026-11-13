# pp-selectid audit 1810 (ruling 76: the 12 h window on the render clock): FINAL consensus (three cycles)

(Started 18:10 ET; label read from the clock.)

| cycle | grok | qwen | glm |
|---|---|---|---|
| 1 | "no" (P0 refuted) | "No" (two P0s refuted) | "yes with conditions" |
| 2 | "yes with conditions" | "yes with conditions" | "Ship" (with conditions) |
| 3 | "SHIP: yes" | "yes with conditions" | "yes with conditions" |

No P0 in cycles 2 or 3.

## What changed after each cycle (all tested; all reporting or stricter, never more permissive)

- **After cycle 1 (C1_CONSENSUS.md):**
  - expiry durability pinned by a test;
  - REPOST_ALIGN_MIN = 0.80 named;
  - the --hours 12 bound tested;
  - a zoneless publish time is no measurement in window_problems too.
- **After cycle 2 (consensus of all three, plus glm and qwen):**
  - usable() checks ruling 76 (a) FIRST, so every expired moment's why agrees with (d)'s count;
  - each expiry's why names the record whose inputs.json was read, or that it could not be read (still expired:
    an unknown age is never fresh).
- **After cycle 3 (qwen P1-1, glm P1-2):**
  - same_speech now applies to delivered spans in EVERY video. The same speech said again at another time of the
    same video is out too ("never reuse any of it"); stricter.
  - glm's conditions are met:
    - a test proves a delivered span's text is the clip's own approved_text, never a title, caption or VO line,
      on real fixture pins;
    - window_problems refuses a zoneless render clock (ValueError);
    - a comment shows ruling_76's inside_12h counts the adapter's pool BEFORE usable() (moments = LB.build_inputs(...)).
  - FINAL_STEP.diff is the diff as committed.

## Refuted (evidence in C1_CONSENSUS.md)

- grok C1 P0 (REPOST_ALIGN_MIN undefined): defined at package.py:877.
- qwen C1 P0-1 (fuzzy matching against L-k): same_speech only EXCLUDES. A wrong match loses one moment; strict
  equality would reuse re-posts cut differently.
- qwen C1 P0-2 / C3 P1-3 (the pin check's clock): the real clock at the pin stage is "the moment they would render".
  Later clocks only tighten; qwen C3 agrees.
- glm C3 P1-1 (whose inputs.json): seed() never changes an existing entry's source. The record that first passed
  the line-up holds every moment of it.

## Recorded (no change)

- Imports inside same_speech / expired / window_problems: the file's own style (reposted_once does the same).
  Build-time CPU only.
- same_speech runs twice for a matched moment (any, then next). Build-time CPU only.
- L-v 3's 24 h rule can no longer fire (12 h < 24 h). It is kept: harmless, and it returns if the window ever moves.

## Cost of this audit

Upper-bound price estimates, not on the ruling-48 ledger:

| cycle | grok | qwen | glm |
|---|---|---|---|
| 1 | $0.084 | – | – |
| 2 | $0.115 | $0.099 | $0.076 |
| 3 | $0.082 | $0.115 | $0.120 |

Cycle 1's qwen and glm figures are in their files. The total is about $1.0.
