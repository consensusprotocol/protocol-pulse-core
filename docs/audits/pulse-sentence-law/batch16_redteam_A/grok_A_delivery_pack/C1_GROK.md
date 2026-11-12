**Q1: CORRECTNESS**  
The diff shows `deliver_run` now calls `release_auth.authorise` first (lines 297-299) and refuses before any send. `_plan` (lines 235-281) builds every payload and checks dimensions, size, headline numbers (via `canon`), and attestation before the first send. `_send_bot_api` distinguishes `SendRejected` (Telegram answered "no") from unknown outcomes (lines 412-416). Legacy `send_telegram_preview` is replaced by a stub that always raises (lines 129-132). No off-by-one, unit, or silent-exception paths are visible in the changed functions; all error paths raise before side effects.

**Q2: LAW COMPLIANCE**  
- L-j (RELEASE IS AUTHORISED ON THESE BYTES): COMPLIANT — `authorise` + per-file digest re-checks (lines 322, 302) and `ATTESTATION.json` last-write rule are enforced in `deliver_run`.  
- L-d (PROTECTED PREVIEW): no change visible.  
- M12 (FAIL CLOSED): COMPLIANT — missing attestation, changed files, or failing rows produce immediate `RuntimeError` before any network call.  
- No evidence of loosened thresholds, recomputed selection locks, or cuts moving outside gaps (those changes are outside this diff).  
- v2f reference path: untouched.

**Q3: TESTS**  
`test_failure_blocks.py` and `test_telegram_delivery.py` now use `make_run` + `release_auth` fixtures (lines 620-648, 741-828). They verify:  
- no send occurs on missing/failing attestation or post-attestation mutation;  
- checkpointing resumes correctly after `SendRejected`/`unknown`;  
- legacy markers no longer authorise anything.  
Assertions are non-vacuous (they check `sent == []`, exact exception text, and `status == "complete"`). `TestVisionMustPass` and `panel_ok` tests are present but concern V1, not sentence law.

**Q4: VERDICT**  
No defects found in the diff.  
**READY**