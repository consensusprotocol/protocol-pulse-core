# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 24 s finish=stop usage in 12870 / out 1271 usd~0.096 (upper-bound price)

**CYCLE 2 AUDIT — pp-selectid-20261114_1426**

1. **WHAT DID THEY CATCH THAT YOU MISSED?**  
GLM-5.3-FLASH caught the exact mutable-reference fragility (pre-fix lock_precheck.py:82 `s["relisten"] = r["relisten"]` placed the JSON-parsed dict object directly into the segment; later in-place mutation of either would alter sealed bytes while the results/*.json file stayed unchanged). I had noted the `apply()` path but missed the concrete desync scenario (post-`apply` mutation of `pk["segments"][0]["relisten"]["second_reading"]` changes `pin_seal` without the integrator's entry file changing). GLM also flagged the test asymmetry (`test_lock_precheck.py:180` now uses `LP.DECODER` while :195 still hard-coded the old list). Qwen explicitly verified the landing-order fail-closed path (builder waiting on new decoder files while integrator still serving old ones). These were not in my Cycle 1 notes.

2. **WHERE DO YOU AGREE OR DISAGREE?**  
- **GLM (b) relisten reference (now fixed):** Fully agree. The added `json.loads(json.dumps(r["relisten"]))` at lock_precheck.py:83 plus the new assertion `self.assertIsNot(...)` at test_ruling_103.py:265 eliminates the fragility. The JSON round-trip also guarantees primitive types only.  
- **GLM (a) test literals / old-decoder list:** Agree. The updated loop now includes `"c705b20ed800"`, the f-string at :180 pins the current `LP.DECODER`, and `test_an_answer_in_the_old_decoders_file_is_never_read` still proves old files are ignored.  
- **GLM (c) canon plan branch placement:** Partially agree. The branch runs before `_NUM.match` and the `len(toks[i+1]) == 1` guard are exactly as required by the new TestRetirementPlans (test_canon.py:139-144, :146-147). The "$401k" vs "401 kilos" distinction is verified; "401b" is outside the ruling's named plans so not a break.  
- **Grok / Qwen:** Agree on all four attack vectors (a–d). The diff + facts show: old RULES/DECODER entries never read (test_ruling_103.py:240), relisten sealed only when present and as-is (SEALED_LATER + to_pin guard), canon change is byte-identical to integrator's audited batch, landing order prevents decoder mismatch. No attack sequence succeeds.  
- **Consensus copy fix:** Taken and verified.

3. **NEW FINDINGS FROM THIS REVIEW**  
<medium> **lock_precheck.py:71 (`relisten_of`) + test_ruling_103.py:267** — the edge-form dict `{token, against, verdict: "hold", why}` (explicitly listed in background facts and ruling) is a dict, therefore passes both `isinstance` checks, gets JSON-copied, and is sealed. The test only exercises non-dict odd cases ("pass", list, int). Concrete sequence: supply an entry with exactly the edge form; `pre["segments"][0]["relisten"]` becomes that dict, `apply` copies it, `to_pin` includes it because `"relisten" in s`, and `pin_seal` changes. This matches the ruling's "Record both short readings on the pin" (edge form is still a record). Not a break, but the test does not assert the edge form is carried "as it stands". Informational only; no mutation or seal mismatch possible after the JSON copy. </medium>

No other new verifiable issues. Canon spans, decoder lookup, SEALED_LATER guard, and old-pin recompute are all exercised by the supplied tests and unchanged supporting code.

4. **REVISED SCORES**  
| Subsystem          | Cycle 1     | Cycle 2     | Why changed |
|--------------------|-------------|-------------|-------------|
| lock_precheck.py   | <medium>×2 | <medium>×1 | Mutable-reference path fixed by JSON copy; test now asserts distinct object. Edge-form test gap is narrower. |
| package_pin.py     | <medium>   | none       | Guarded inclusion + test proving "pin without one seals as before" eliminates recompute regression. |
| canon.py           | <medium>   | none       | Byte-identical to integrator + new TestRetirementPlans + TestCanonOnThisSide kill all regression mutations. |
| Overall            | <medium>   | <low>      | The single taken fix (copy) plus updated tests close the only concrete fragility that was verifiable from the original diff. |

5. **FINAL PRIORITY LIST**  
**P2 MEDIUM** — lock_precheck.py:71 and test_ruling_103.py:267: add one explicit edge-form case (the dict with "why") to the "as it stands" test so that future changes cannot silently alter which fields are sealed. No P0/P1 items. All attack vectors (a–e) are closed by the diff, facts, and 8 killed mutations.

6. **THE SINGLE HIGHEST-LEVERAGE CHANGE**  
The JSON round-trip copy at lock_precheck.py:83 (plus the `assertIsNot` test) turns a mutable reference into an immutable snapshot, so the relisten record is sealed exactly "as it stands" and cannot desync from the integrator's results file.

7. **PRODUCTION READY?**  
Yes with one condition: add the edge-form dict to the test loop at test_ruling_103.py:267 (or a new assertion) so the "carried as it stands" contract is explicitly verified for every dict shape the background facts permit. After that single test expansion the change is ready to ship. All laws (L-j, L-k, L-l, M12 FAIL CLOSED) hold, every old pin recomputes, and no wrong pin can be sealed.