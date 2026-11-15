# Audit 20261114_1835 (ruling 104's directive path: the orchestrator-ordered alternative variant), cycle 1: consensus

Reviewers:
- grok-4.20: yes with conditions. Two <medium>.
- qwen3.8-27b: yes with conditions. One <critical> (L-k), one <high> (field validation), one <medium>.
- glm-5.3-flash (778 s, finish=length): no <critical> or <high>; yes with four conditions.

## Taken (the diff as it stands now)

- **grok, a directive whose ending matches no boundary.** The parent did stay in the pool (with_variants keeps every
  moment that is not replaced). But the branch's `continue` also skipped that parent's OWN triggers (a current hold,
  the ceiling), which is not "the rules stand".
  - Now a miss is noted and the normal triggers run.
  - Test: a non-matching directive leaves the parent in the pool, and with a current hold the hold's variant is made,
    both notes kept. Mutation D11 is killed.
- **qwen <critical> (L-k, a normaliser outside canon).** directive_variant stripped a leading "..." itself before
  canon. canon.canon_tokens already drops it (checked: "...I still don't use my Roth IRA." and "…I still ..."
  both give ['i', 'still', "don't", 'use', 'my', 'roth', 'ira']). The strip is removed; the comparison is canon's alone.
  The span's text is E.spoken, the canonical read of the record's words (law L-h).
- **qwen <high>, the directive's fields checked by type only.** This is a builder-written file, not a model reply, so
  L-l does not govern it, but fail-closed does. directives() now also requires:
  - parent: a moment id (20 hex);
  - alternative_to: a pin's story id (moments-<run>-<8 hex>);
  - ends and by: non-blank.
  Mutations D5 and D5b are killed.
- **glm (1), a crash.** {"directives": 5} raised a TypeError outside the try and would have stopped a build. A
  non-list value now gives no directive (mutation D12; tests for 5, null, a list file and a null file).
- **glm (3), a silent ignore.** A directive on a one-sentence parent is now noted ("no earlier boundary"), mutation
  D13.

## Documented, no change

- **glm (2)/(4), the directive variant and the 35 s ceiling.** The directive branch makes the variant the orchestrator
  named. Every pool moment, the variant included, still faces spotlight.pool's usable(seg_max=35 s) and every later
  gate. The variant here is 15.28 s.
- **qwen <medium>, two records for the channel that day.** By design, the alternative takes the named story's place
  and records it ("alternative_to"). day_taken admits ONE alternative: a third moment naming the same story is
  refused, because the alternative's own record now takes the day (test).

Verification: 14 of 14 mutations killed. test_ruling_104, test_spotlight and test_ledger_build, 98 passed.
