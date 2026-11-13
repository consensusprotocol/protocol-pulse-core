# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 36 s finish=stop usage in 16432 / out 1366 usd~0.116 (upper-bound price)

**CYCLE 2 AUDIT — pp-selectid-1400 (RULING 67 attested-text re-seal)**

1. WHAT DID THEY CATCH THAT YOU MISSED?
GLM caught the replace-opcode fragility in carry_class (P1-1: a repeated phrase emitted as replace instead of delete/insert can fall through to None even when the ruling intends carry) and the reads() end-anchor using `len(s)-1` plus the exact `hi < len(x)` logic (P1-2), which can refuse on trailing tokens the render might accept. GLM also highlighted the 3-decimal rounding in reseal_attested.py:249-250 (P1-3) as the single most likely operational failure. I had rated these only P2 because the fixture and tests use delete/insert and exact times; GLM's concrete alignment and float-boundary scenarios were overlooked. Qwen's claimed P0s on critical() and sentence-opening names were already refuted by the render's _lv2_critical verbatim match (lines 52-58), which I had correctly identified in Cycle 1.

2. WHERE DO YOU AGREE OR DISAGREE?
- GLM P1-1 (repetition on replace): partially agree — the one-sided tag test is alignment-dependent and the ruling's "immediate repetition" example can be emitted as replace by SequenceMatcher; the shipped fixture happens to align safely, but future pins could regress. The suggested "treat replace where one side repeats its own neighbour" mitigation is sound.
- GLM P1-2 (reads() window/anchor): agree — the docstring claims behavioural identity with pinned.adjudicate_lock; the diff and consensus verification confirm the map, consecutive check, and start/end anchors are identical (only s is now a parameter). The stricter "nothing follows at all" rule is intentional and fail-closed.
- GLM P1-3 (rounding): fully agree — this remains the highest operational risk; build records and pins can differ by 1 ms across stages.
- Grok P2 on word_at split guard and replayed-reading refusal: agree — both are exercised by the new test suite and match the "fail closed" requirement.
- Qwen P0s on critical()/names/ordinals: disagree — the code copies the render's exact lists and sentence-opening exclusion; refusal for sentence-start names is the safe path and matches K2/K3. The self-contradiction in Qwen's own text was correctly flagged in the consensus refutations (R1-R3).
- All models agree on seal compatibility (SEALED_LATER addition leaves prior pins untouched), test coverage (12 suites, real held-clip fixture), and that nothing is written on refusal.

3. NEW FINDINGS FROM THIS REVIEW
**P2-new — reseal_attested.py:254** `all(AT.reads(r, s, a, b) for ...)` only checks the run side; the ruling requires the second recogniser to agree with the render's decode, but the code never asserts that the same recogniser does *not* read the old approved_text (only the test does). Verifiable from diff; harmless because the attested_text test already confirms no ruling-17 diff remains, but the orchestrator could be tighter.
**P2-new — attest.py:151** `quotes()` uses `p[max(c-1,0):d+1]` and `r[max(a-1,0):b+1]`; when a difference is at token 0 the neighbour window includes a fictional token that canon_tokens("") would never produce, yet the test passes. Edge-case only.
No P0 or P1 introduced by the "fixed" diff; the Cycle-1 issues around word ranges (P1-4) and speaker test are resolved.

4. REVISED SCORES
| Subsystem                  | Cycle 1 | Cycle 2 | Why changed |
|----------------------------|---------|---------|-------------|
| attest.py (critical/carry/reads/quotes) | P2     | P1     | GLM's replace-alignment and end-anchor analysis raised the operational fragility; still no correctness break on the held pin. |
| reseal_attested.py orchestration & time matching | P2     | P1     | Rounding brittleness confirmed as most likely future refusal; unchanged code but higher visibility after cross-model review. |
| attested_text minimal edit & word-boundary guards | P2     | P2     | Tests now explicitly cover split-word, replace, and the real fixture; no change. |
| SEALED_LATER, seal compatibility, test_speakers fix | P2     | P2     | Unchanged assessment; the speakers test fix is purely mechanical. |

5. FINAL PRIORITY LIST
**P0 CRITICAL**: None verifiable from the diff.
**P1 HIGH**:
- attest.py:79 (`carry_class`): one-sided tag test for repetition (GLM P1-1); add replace handling or document that SequenceMatcher on these texts always emits delete/insert for the held case.
- reseal_attested.py:249 (`round(..., 3)` equality): replace with tolerance `abs(float(t.get("start", -1)) - float(seg["start"])) < 0.0015` (and same for end) plus debug output of nearest candidates on failure (GLM P1-3).
**P2 MEDIUM**:
- reseal_attested.py:254: add explicit check that second recogniser does *not* read the old approved_text (new finding).
- attest.py:95 (`reads` end anchor): confirm byte-identical to current render's adjudicate_lock (already done in consensus A1, but worth a comment).
- reseal_attested.py:270: consider storing full run commit hash in attested["render"] for provenance.

6. THE SINGLE HIGHEST-LEVERAGE CHANGE
Replace the exact `round(..., 3)` time match in reseal_attested.py:249-250 with a small epsilon tolerance plus diagnostic output; it eliminates the most probable operational refusal on otherwise valid pins.

7. PRODUCTION READY?
Yes with conditions: (1) implement the P1 time-tolerance change (or prove every build record and pin uses identical 3-decimal rounding), (2) add the replace-opcode test case to carry_class so the repetition path is exercised beyond the fixture, (3) confirm via diff that reads() is still byte-identical to the render's adjudicate_lock after any future render changes. With those three addressed the attested-text re-seal satisfies K1-K5, seal compatibility, fail-closed refusals, and the ruling verbatim.