# Heimdall audit

**Question:** pp-selectid (Protocol Pulse clip-video builder). RULING 160 (2b): every build ends in EXACTLY ONE recorded outcome, one JSON line in data/builds/outcomes.jsonl: SEALED, HARD_REJECTED, NO_ELIGIBLE_STORY, INDETERMINATE (a hard check that could not be answered, or ANY check left unanswered or unmeasured: ruling 163 (4)), BUDGET_STOPPED. NEW FILE tests/package/outcomes.py (diff below): outcome_of(build_dir) reads one build record and returns its line; precedence: a pin file -> SEALED; NOTHING_NEW.json -> NO_ELIGIBLE_STORY; the start refusal (rc 3) -> BUDGET_STOPPED; no package.json -> INDETERMINATE; pin_refused -> HARD_REJECTED; FINGERPRINT.json spend_refused non-empty -> BUDGET_STOPPED; undone() items (non-money) -> INDETERMINATE; else classify(why_none of the deciding pass: the never-empty pass when package.json has "never_empty", else the clean pass). undone() lists what a build left unanswered (it replaces proof_ledger.open_work's count, which the NOTHING NEW guard compares with 0: a build with open work is never skipped as NOTHING NEW). write_once() appends one line per (side, run) under a flock. backfill_160.py wrote builds 152-168 (build 156's reason given by hand, quoted from its STATE line).
CHECK, quoting the code: (1) can classify() or outcome_of() return anything outside KINDS, raise on a malformed record (non-dict fields, missing files), or call an answered refusal INDETERMINATE / an unanswered check HARD_REJECTED; (2) can undone() count 0 for a record where a vision check, a hook rating or a verdict was never answered (the never-empty pass's soft_record.hook_pool.visual_blocked / error, tried[].attempts verdicts with "measured": false), or count something answered; (3) can write_once() write two lines for one run, or lose a line, when two processes append at once; (4) does yield_of() mis-count a stage. Report only what the code shows; if unsure, say so.

**Panel:** qwen27b, gptoss, gemma  |  **Cost:** $0.0054
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
