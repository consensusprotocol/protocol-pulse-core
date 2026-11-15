# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 27 s finish=stop usage in 14065 / out 1385 usd~0.105 (upper-bound price)

**CYCLE 2 — FINAL REVIEW (pp-selectid-20261114_1835)**

**1. WHAT DID THEY CATCH THAT YOU MISSED?**  
Honest accounting:  
- GLM's H1 (`{"directives": 5}` TypeError outside try) and one-sentence-parent silent ignore — I had only noted the duplicate-parent dict loss, not the builder-file crash or the `continue` at tail_variant.py:87 swallowing a named directive. Both now fixed (proof_ledger.py:158 `if not isinstance(rows, list)`, explicit note before `continue` at tail_variant.py:85).  
- Grok's parent-dropped-on-bad-directive-ends interaction — I missed that the pre-fix `continue` after `v is None` also skipped the parent's own hold/ceiling triggers (ruling 104 "the rules stand"). The new no-`continue` path + note-merging at tail_variant.py:117 and :128 lets both notes survive and triggers still run. Test at test_ruling_104.py:272-279 proves the hold variant is still emitted.  
- Qwen's L-k ad-hoc "..." strip in original directive_variant — I reviewed the canon call but missed the strip occurring outside it. The fix (delete strip, rely on `C.canon_tokens` at :62) is verified; both `"...I still don't use my Roth IRA."` and `"…I still..."` now canon-compare identically.  
- All three models' spot_place `pk["segments"][0]` IndexError — I scored it <medium> in Cycle 1 but did not trace that it sat inside `main`'s try yet outside the exact except tuple. The guard now at proof_ledger.py:175 (`if not segs or not isinstance(segs[0], dict)`) plus test at :335-336 kills it.

**2. WHERE DO YOU AGREE OR DISAGREE?**  
- **Grok (parent drop on miss):** Fully agree. The diff at tail_variant.py:96 (`if v is None: notes[mid]=...` with no `continue`) + later merge logic is the correct shape. The remaining `continue` at :94 (missing source) is harmless per background (no word record → no variant possible). Test :276-279 confirms combined note and hold variant both appear.  
- **Qwen L-k critical:** Agree on the original wart; disagree on <critical> severity post-fix. The comparison was always canon-vs-canon; failure was closed. The comment at tail_variant.py:62 now correctly documents canon as the single form.  
- **Qwen L-l high (field validation):** Agree with Qwen's own walk-back — this is builder input, not model reply. The added checks (20-hex parent, `moments-...-8hex` story id via fullmatch, non-blank ends/by) are sound hygiene; regexes are anchored (`re.fullmatch` for parent, `story.fullmatch` + pattern `$` semantics). Test at :291-302 covers malformed rows, trailing newline, non-story id.  
- **GLM H5 (35 s ceiling bypass):** Agree it was a real skip of the *local* ceiling check, but background + test at :337-339 (`long_` 36 s alternative refused by `pool.usable(seg_max=35)`) confirm downstream gates still apply. No change needed.  
- **GLM H4 (`alternative_to=""`):** Moot — `story.fullmatch("")` fails, so row is dropped at read time (proof_ledger.py:164). Convergence not noted by anyone in Cycle 1; worth recording.  
- **All three on IndexError:** Agree. Fixed in this diff (see below).

**3. NEW FINDINGS FROM THIS REVIEW**  
None that survive the diff.  
- `proof_ledger.py:175` guard + early return prevents IndexError; `segs = pk.get("segments") or []` then explicit `isinstance(segs[0], dict)` check is exhaustive for [], None, non-list, non-dict-first-element. Test covers all four.  
- `story.fullmatch` on alternative_to rejects trailing newline (test :296).  
- No path raises out of `main`'s try (PinRefused, ValueError, OSError) or `pool`: directive_variant only called after `k1 > k0` guard and successful `source_for`; `day_taken` uses only `.get()`.  
- Well-formed directive decisions unchanged; moments without directive unchanged (ruling 90 still blocks, hold/ceiling still fire). Mutation set (16/16 killed) and test_ruling_104.py:260-342 verify.

**4. REVISED SCORES**  
| Subsystem                  | Cycle 1     | Cycle 2     | Why changed |
|----------------------------|-------------|-------------|-------------|
| directive_variant path     | <medium>    | none        | Bad-ends `continue` removed, note merging added, canon sole path, one-sentence note |
| directives() reader        | <medium>    | none        | Strict validation, non-list handling, fullmatch story id, tests for all malformations |
| spot_place / day_taken     | <medium>    | none        | segments guard, unified ruling-90 rule, explicit alt return, 36 s ceiling test |
| ceiling / gate bypass      | <medium>    | none        | Local skip remains but downstream `usable` + test confirm refusal |
| IndexError on segments[0]  | <medium>    | none        | Guard at proof_ledger.py:175 + test :335-336 kills the crash |

**5. FINAL PRIORITY LIST**  
No P0, no P1, no P2. All Cycle-1 and Cycle-2 findings addressed in the diff under review. The single remaining stylistic note (directives() could explicitly reject unknown keys) is below hygiene threshold.

**6. THE SINGLE HIGHEST-LEVERAGE CHANGE**  
Unifying ruling 90 into `spotlight.day_taken(..., alternative_to=None)` called from both pool and pin, with the single explicit exception for a named alternative, making the orchestrator's directive path impossible to bypass without a validated builder-written row.

**7. PRODUCTION READY?**  
Yes. All attack vectors (a)–(g) are closed by the diff: no sealing without a validated directive row, variant faces every gate, full clip and alternative cannot both pin on the same day, no uncaught exceptions, no decision changes for well-formed cases or non-directive moments. 16/16 mutations killed, tests pass. Ship.