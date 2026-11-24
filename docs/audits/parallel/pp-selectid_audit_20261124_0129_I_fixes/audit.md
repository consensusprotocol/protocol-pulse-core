# Heimdall audit

**Question:** pp-selectid (Protocol Pulse clip-video builder), cycle 2 for the fixes of audits 20261124_0101_F_rows and 0109_H_undone, plus one fix found by hand (uncommitted; the hunks shown hold surrounding code that earlier audits passed):
(1) providers.Router.call, RULING 154 (1)'s stand-in judges (never-empty pass only): for role "context_verdict" with a step-A kind ("step_a_first" / "step_a_second") only step 1 stands in (a Heimdall family that did not write or judge first): step A's second verdict must come from another family (package.second_screen refuses a same-vendor or same-family answer as STEP_A_SAME_VENDOR, while NO verdict is HELD and retried next build, ruling 102), so steps 2-3 could only turn a hold into a refusal.
(2) package.fallback_fields: the join must be a non-empty list or tuple whose first item is an int (not a bool) between two of the line-up's clips, else no fallback (None).
(3) RULING 143 at selection: lv2_settled settles a words-only L-v 2 failure only on the lock's "pass" or "adopt"; the prescreen's pending reading (kept in the pool only when the build has the lock) is its own function lv2_pending; lock_verdicts returns {} unless the record's "segments" is a list of the line-up's length.
(4) RULING 155 (2) in the line-up search: seg_marks(segs, a_by) reads the same step-A record (a_by) as the pin's context_a row: a clip whose only step-A code is REFERENT_OUTSIDE adds no kind unless a referent of that record says changes_assertion "yes" (the pin's flag condition, whose other half, step C, the search cannot know yet); no record: counted.
(5) tests/package/proof_ledger.open_work (RULING 107 (1)'s count of work left undone): every level of the build record read through one helper, so a malformed record is read as empty, never a crash.
CHECK, quoting the code: can (1) block a valid independent stand-in for step A or let a same-family one answer; can (2)-(5) raise, settle a span the lock held, count a kind the pin will not flag, or skip one it will. Report only what the code shows.

**Panel:** qwen27b, gptoss, gemma  |  **Cost:** $0.0149
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
