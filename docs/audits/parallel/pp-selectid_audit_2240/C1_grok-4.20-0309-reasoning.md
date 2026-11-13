# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 76 s finish=stop usage in 33291 / out 527 usd~0.180 (upper-bound price)

**P2: pipeline/house_style.py:154**  
Title possessive detection (after _norm and strip) correctly rejects "Bitcoin’s" / "Holders'" and accepts listed CONTRACTIONS, but the regex [\w-]+'s|[\w-]+s' on the lowercased first token can be bypassed by a title starting with a non-word token + possessive (e.g. "'Bitcoin's value'"). TestTheInterface and TestEveryRuleFails never exercise this; the gate would accept a malformed opener that LAW 20/M2 and R6 require to be refused. (Verified from lint(), _norm(), RULE_IDS, and test fixtures only.)

**P2: pipeline/package.py:456**  
no_voice() calls paid_gates(..., nv_pool) while still inside the ThreadPoolExecutor 'with' block (the subsequent if-not-fid block is at with-body indent). If paid_gates submits additional work to the same pool, the with __exit__ shutdown occurs before all futures are guaranteed collected, violating the "every REQUIRED gate ran, on samples, unwaived, on exactly the bytes" requirement of L-j. The Rig.test_no_voice_* cases never surface the race because they stub paid_gates. (Verified from the exact with/indentation and paid_gates call site only.)

**P2: pipeline/providers.py:708**  
_within() marks the thread daemon=True and abandons it on timeout, then _settle books the *upper* USD. A late-finishing thread that still mutates the shared ledger or cache after the next backend has been chosen (and Reply.tried recorded) can produce a non-deterministic "executed code at the launch revision" attestation, violating L-j's "exact gate inventory v1" and "replays are never deliverable". TestDeadline only checks the immediate reply and ledger entry, not the abandoned thread's final side-effects. (Verified from daemon=True, done.wait, _settle call, and DeadlineExceeded handling only.)

No P0 or P1 findings; all R1/R3/R5/R6 behaviors (recency seal+refusal, no-voice fallback with added-clip path, writer deadline+avoid, house_style lint+inventory+prompt, budget on reported+estimate) match the diff text and tests. The new gate is deterministic, fail-closed, and does not alter existing sentence/edge/fidelity rules.

**SHIP: yes with conditions** (the three P2 edge cases must be exercised or hardened before merge; v2f byte-identity and L-j pin seal remain intact).