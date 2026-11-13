# pp-selectid audit 1300 (RULING 65: a caption never kills a package): FINAL consensus (cycle 2)

- **Cycle 2:**
  - grok: "SHIP: yes", P2s only.
  - qwen: "Yes", no P0 or P1, no conditions. It now refutes its own cycle-1 P0, matching R1 and R2.
  - glm: "SHIP: yes with conditions", one condition: show that the production Reply carries `cached`. That condition is discharged below.
- All three adopt C1's refutations R1 to R3.
- **No code change.** The diff applied is the one both cycles reviewed (dev21, base a1bc7eaf).

## The one condition (glm cycle-2 P1-1, "Reply.cached may not exist")

**Discharged: it exists, and a live run sets it.**
- `pipeline/providers.py:81` (unchanged since aef73873): `cached: bool = False  # a live run served this model's recorded reply to the same bytes`.
- `providers.py:728-729`, the served-recording return, passes it by position: `Reply(rec["text"], name, b.vendor, ..., self.replay, tried, notices, b.family, not self.replay, path)`.
- Checked on the dataclass: field 10 is `cached`. A live run (replay False) therefore serves a recorded reply with replayed False and cached True. An offline replay gets replayed True and cached False.
- The diff could not show this (the file is unchanged), which is why glm could not verify it.

## Two-model P2 (grok P2-1 = glm P2-3): merge_fid recomputes "ok" from the violations

Both made it contingent on VF's contract ("if VF never produces ok False with empty violations"). **It holds in every record shape VF produces, so no change:**
- check_deterministic: `{"ok": not v, "violations": v, ...}` (vo_fidelity.py:537). "price_now_measured" is not part of ok.
- check_verdict: `{"ok": not v, ...}` (vo_fidelity.py:721).
- The unavailable path always carries a VERDICT_UNAVAILABLE violation, with measured False (vo_fidelity.py:741).
- paid_gates calls VF.check (package.py:1848), not majority(). In majority(), ok False comes either with a VERDICT_MAJORITY violation or with measured False. An unmeasured run votes "fail" on every slot (vo_fidelity.py:770-783).
- merge_fid derives the verdict's ok as `measured and not violations`, so an unmeasured run can never come out passing (law L-m; test_merge_keeps_the_other_lines_as_gated).

## Recorded (single-model P2s, no change)

| # | finding | why no change |
|---|---|---|
| G1 | grok P2-2 / glm N2 / qwen P2-5: the title hold's thin context record and its provenance | The hold breaks the line-up before any inventory is built, and nothing from it is sealed (C1 G1). The rewrite's own record names the second write. |
| G2 | glm N3: LINE_LIMIT's text and write_line's 220 / 70 check could drift | The full write already states and checks the same 70 / 220 (package.py:702 and 1584). All three agree today. Single-model. |
| G3 | glm N1: merge_fid's class for the slot could be None | Both callers pass a class for the slot: check_verdict's classes, and the fixed line's "the fixed line: no fact". Gates read violations, not classes. |
| G4 | glm N4: a cheap violation with no slot key | lone_slot then returns None, which takes the old redo path (conservative). |
| G5 | glm N5 / qwen P2-1, P2-2: the old redo now lists cheap violations, and a lone caption or title cheap failure reaches the paid gates first | Stated reading K1 (ruling 65: "a caption never kills a package"). The instructions are a superset of before. A non-lone cheap failure still redoes at once, as before. |
| G6 | qwen P2-3 / P2-4: fixed_caption assumes a title and merge_fid assumes a deterministic layer | Both are guaranteed by control flow: the caption path runs only when the title passed, and every record has a deterministic layer. |

## Verification

- test_medley 125 OK and all 11 suites OK on dev21. They are re-run in the worktree after the apply, with regression_test.sh, before commit.
