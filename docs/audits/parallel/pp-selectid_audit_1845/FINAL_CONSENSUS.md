# pp-selectid audit 1845 (ruling 73: the lock pre-check's rules string and decoder sha): FINAL consensus (cycle 2)

| cycle | grok | qwen | glm |
|---|---|---|---|
| 1 | SHIP yes | SHIP yes | SHIP yes |
| 2 | yes with conditions | SHIP yes | yes with conditions |

No P0 and no P1 in either cycle.

## The conditions

1. **grok (b), glm (1): no other place carries the old values.** A repo grep of pipeline/ and tests/ (*.py) for
   "25cd6f15e6c9" and the old rules string finds them only in test_lock_precheck.py, which names them on purpose.
2. **glm (2): a file named for the old decoder is never opened.** Added
   test_an_answer_in_the_old_decoders_file_is_never_read. A matching, newer entry under the current rules, placed
   in the 25cd6f15e6c9 file, is not read. FINAL_STEP.diff is the diff as committed.
3. **grok (a): the service runs the merged decoder.** The integrator's notice: merged 585b6da5, pre-check restarted
   18:43:08.

## Cost

Upper-bound price estimates, not on the ledger:
- cycle 1: grok $0.037, qwen $0.035, glm $0.043;
- cycle 2: grok $0.054, qwen $0.034, glm $0.055.

About $0.26 in all.
