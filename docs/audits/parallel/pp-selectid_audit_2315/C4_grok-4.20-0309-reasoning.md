# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 26 s finish=stop usage in 21881 / out 1409 usd~0.145 (upper-bound price)

**Findings (verifiable from diff only)**

**P0** — None.  
(a) Non-whole-sentence clip refused by reanchor (lines 191-193: left/right > SNAP_WORDS or risky added word via SNAP_GUARD); non-word-timed / unverified record refused by E.sentence_ready + transcript_sha256 check + words_off_segments (lines 164, 153-158, 102-130); delivered span refused by PK.usable overlap (proof_ledger:397, test lines 772-776). All paths exercised in test_ledger_build.py.

**P2** — pipeline/ledger_build.py:386 (call site) and proof_ledger.py:386  
`LB.rows(since, now, horizon_h=a.hours)` supplies no `delivered_ids` (remains `()`). Driver reads full delivered spans (lines 363, 325-349) solely for `PK.build(..., delivered=delivered)`. Concrete scenario: ledger row mined before last pin but overlapping an old delivered span whose ledger moment_id is unknown → adapter returns it (no id filter), `build_inputs` accepts (only intra-run `(vid, k0, k1)` dedup at 248), `reanchor` succeeds, `M.record` succeeds; only later `usable` overlap drops it. Matches current docstring intent (K7) but if adapter contract evolves to treat delivered_ids as video-level, older overlaps could reach package stage before usable. (Uncertain whether ingest adapter ever widens delivered_ids semantics.)

**P2** — tests/package/test_ledger_build.py:600-601 (and ledger_build:55,140)  
Test asserts `WORD_RECORDS` tuple order but does not exercise a store containing both a punctuated_v2 variant *and* the canonical punctuated file; filesystem glob order is no longer used, yet comment at 57 still references the old glm P1-2 risk. Minor documentation-test gap only; no runtime defect verifiable.

No other P0/P1. (b) Every drop path counted (no_word_record_why, fallbacks, not_anchored, malformed, duplicates, channel_conflict). (c) `since` defaults to newest pin `approved_at` (proof_ledger:364); adapter receives it; docstring + test_driver_refuses (719-753) match ruling-2 wording sufficiently; no verifiable case of reading too few lines. (d) All listed Cycle-2 fixes present and complete: passed_over collection/reporting (word_source:144-167, test:616-639), channel_conflict whole-video drop (build_inputs:229-232, test:640-649), --delivered required + pre-mkdir refusal + exit 2 (proof_ledger:354,362-377, test:719-753), SNAP_GUARD expanded + APOSTROPHES map (ledger_build:40-46,194), no-sha test, words_off_segments, SEARCH_PAD_S offset recording. (e) Each named defect test would fail its asserts if the defect were reintroduced (e.g. test_a_snap_never_adds_a_near_negation, test_a_record_whose_words_do_not_spell_its_segments_is_never_read, test_the_driver_reads_the_delivered_pins_before_writing_and_refuses_a_bad_one).

**1. WHAT DID THEY CATCH THAT YOU MISSED?**  
GLM caught the non-total sort in word_source glob (now eliminated by fixed WORD_RECORDS tuple) and the sha-vs-words gap (now closed by words_off_segments + test). Qwen caught SNAP_GUARD missing “hardly/scarcely/barely/rarely/seldom” (now added with dedicated test). I missed both the near-negation family and the exact sha/words spelling contract in Cycle 1.

**2. WHERE DO YOU AGREE OR DISAGREE?**  
- GLM P1-1 / Grok P2 on delivered_ids: fully agree it was a real gap in Cycle 1; now explicitly intentional (overlap stricter than id check, pins carry no ledger ids) and tested via usable — resolved.  
- GLM P1-2 on word_source sort: agree; fixed cleanly by explicit tuple + test.  
- Qwen/GLM on SNAP_GUARD: agree; expansion and apostrophe normalization + test make it complete.  
- Qwen P2 on `since` ambiguity: partially agree the choice was underspecified in Cycle 1; current diff documents approved_at rationale and adds refusal tests — sufficient.  
- All on malformed rows / channel_conflict / fallback reporting: agree; implementations match consensus K7/K8 exactly.

**3. NEW FINDINGS FROM THIS REVIEW**  
Only the two P2 items above. No new P0/P1; the combined Cycle-1 feedback plus current tests close every concrete scenario previously raised. The words_off_segments + passed_over reporting is stronger than any reviewer required.

**4. REVISED SCORES**  
| Subsystem                  | Cycle 1 | Cycle 2 | Why changed |
|----------------------------|---------|---------|-------------|
| Ledger Adapter Integration | P2      | P2      | delivered_ids still omitted but now documented, tested via usable, and consensus-accepted |
| Word Record Selection      | P1      | None    | Fixed ordering, sha+words check, full passed_over reporting, dedicated tests |
| Snap Guard & Reanchor      | P1      | None    | Expanded guard, apostrophe map, offset recording, negation tests |
| Driver Safety & Refusals   | P2      | None    | Required --delivered, pre-write pin validation, exit-2 paths, mkdir guard all present |
| Test Coverage              | P2      | None    | Every named defect now has a failing-assert test |

**5. FINAL PRIORITY LIST**  
No P0 CRITICAL.  
P2 MEDIUM: pipeline/ledger_build.py:386 (and proof_ledger.py:386) — delivered_ids remains default `()`; monitor if ingest adapter contract changes.  
P2 MEDIUM: tests/package/test_ledger_build.py:600 — minor test/docs gap on punctuated_v2 variant (non-functional).

**6. THE SINGLE HIGHEST-LEVERAGE CHANGE**  
words_off_segments + full passed_over reporting in word_source (lines 102-167) ties the sha-checked segments to the exact words used for anchoring and makes every fallback visible, closing the largest unverifiable gap from Cycle 1.

**7. PRODUCTION READY?**  
Yes with conditions: (1) integrator must confirm that empty delivered_ids to best_unused_moments remains correct long-term (per K7); (2) any future window-record path must preserve the “no word record” counting contract. All verifiable defects from both cycles are fixed and tested.

**SHIP: yes with conditions**