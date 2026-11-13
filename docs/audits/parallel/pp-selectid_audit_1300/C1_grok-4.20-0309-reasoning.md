# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 101 s finish=stop usage in 14556 / out 629 usd~0.089 (upper-bound price)

**P2: pipeline/package.py:74**  
lone_slot() correctly returns only when *every* violation shares a single slot ∈ {"caption","title"} (test at 376–380 confirms takeaway or mixed-slot cases stay on the old redo path).

**P2: pipeline/package.py:202**  
The guard `if cx["ok"] and fid.get("measured")` before calling lone_slot(...) plus the later `if not (fid["ok"] and cx["ok"]) or cheap:` after rewrite_alone() ensures a takeaway failure or unmeasured fidelity never takes the lone-write path (matches ruling 65 and test at 381–384).

**P2: pipeline/package.py:126**  
write_line() builds a *new* WRITE_LINE prompt that quotes the refused sentence + LINE_WHY reason and the gated takeaway/title; router.call("angle_write", …) therefore cannot hit an identical-prompt replay (explicitly satisfies the 12:52 ruling paragraph on replay trapping). writers_v.add(r.vendor) / writers_f.add(r.family) occurs before the subsequent VF.check, satisfying L-x for the line writer.

**P2: pipeline/package.py:158**  
fixed_caption() produces exactly the format required by ruling 65(b) and K2: gated title.lower() + "\n" + lowercase channel names joined by " / ", citing every clip. The fallback record supplies deterministic + "the fixed line: no fact" verdict class with no model verdict (K3). cheap3, house-style lint, and CI.check_contexts still run on the final pk3 bytes (L-j, L-t).

**P2: pipeline/package.py:90**  
merge_fid() retains the original fid's deterministic/verdict results for the other two lines, merges only the lone slot's violations/classes, requires measured on *both* runs, and annotates the backend with "(ruling 65)". The test at 387–397 verifies that an unmeasured second run forces ok=False (M12/L-j).

**P2: pipeline/package.py:175**  
medley() now surfaces cached=…; build() treats replayed *or* cached line-ups as free against the 8-line-up budget (12:00 note). Test at 400–403 confirms a cached clips-alone verdict costs 0 search lineups.

**P2: pipeline/package_pin.py:241 / tests/package/test_medley.py:354**  
caption_fallback flag is recorded outside the seal (like no_voice) and the test suite asserts the exact gate rows, house-style PASS on the fixed line, and that a title failing its second write is held with no package emitted. All six TestRuling65Caption cases pass; no path seals an ungated caption/title.

No P0/P1 findings. The diff introduces no new renderer/compositor/selector, changes no gate thresholds, keeps every required gate on the final bytes, and complies with every concrete clause of ruling 65 and the listed K1–K5 that can be verified from the patch alone.

**SHIP: yes**