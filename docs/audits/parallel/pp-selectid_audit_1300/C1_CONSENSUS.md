# pp-selectid audit 1300 (RULING 65: a caption never kills a package): cycle 1 consensus

- **Run:**
  - grok: "SHIP: yes", no P0 or P1.
  - glm: "SHIP: yes with conditions", record-keeping P1s.
  - qwen: "SHIP: No", on a "P0" its own text re-grades.
- No P0 or P1 holds against the code. Nothing changes; cycle 2 reviews the same diff.

## REFUTED (with evidence)

| # | claim | the code |
|---|---|---|
| R1 | qwen P0: the fixed-caption path does not check its cheap gates before sealing, so a failing fixed line could be sealed | The caller checks them before anything is sealed. Right after rewrite_alone it sets `cheap, det, dup, rt_ok, r4_res = cheap_t` (the cheap checks on the package as it now stands), then `if not (fid["ok"] and cx["ok"]) or cheap:` records the why and breaks the line-up. The inventory is never built and nothing is sealed. The fixed line's own deterministic layer is merged into fid3 (merge_fid), so a deterministic failure there also makes fid3["ok"] False. qwen's own text: "This is not a P0 for sealing a bad package, because fid3["ok"] becomes False, triggering the break." |
| R2 | qwen P1: att["violations"] is stale after a successful rewrite, so the sealing logic will reject a valid package | att is the attempt's RECORD; nothing decides sealing from it. The inventory is built from the merged fid, dup / rt_ok / r4_res from the final cheap checks, the final cx, coherence, and style=HS.lint_lines(pk["lines"]) on the final package. to_pin reads only pk["gates"] and the package. The rewrite's own record (att["rewrite"]: refused, written, verdict, passed / fallback) is beside it. |
| R3 | glm P1-3: a rewrite that passes fidelity and context but fails the cheap checks breaks with why None | That state cannot occur. rewrite_alone runs the cheap checks on the new package BEFORE any verdict, and raises on a failure (`if cheap2[0]: raise ValueError("cheap gates: ...")`). A raise takes the caption to the fixed line, or holds the title with its why. A "passed" rewrite therefore always returns empty cheap results. |

## Recorded (no change)

| # | finding | why no change |
|---|---|---|
| G1 | glm P1-2: the title-hold path returns a literal context record ({"ok": True, ...}) | The hold breaks the line-up before any inventory is built, so that record is never sealed or gated. The hold rests on fid["ok"] False. That is the ruling's intent ("then hold"). |
| G2 | glm P1-1: merge_fid when the first record has no "verdict" key | Every record VF.check returns carries "verdict" (a dict, also on the unavailable path). The fallback's `one` carries one too. |
| G3 | glm P1-4: the line contract refuses extra keys | Intended: "Return ONLY this JSON object". A reply out of contract is rejected; for the caption it leads to the fixed line, for the title to a hold. |
| G4 | glm P1-5: replayed vs cached | Both are free (the 12:00 note): `total += 0 if med.get("replayed") or med.get("cached") else 1`. |
| G5 | glm P2s (the test rig's shapes; the fallback's measured flag) | Records. The fallback's verdict entry names itself "code, no model (ruling 65 b)", and the row's "by" carries it. |

## Verification

- test_medley 125 OK; all 11 suites OK on the scratch copy (dev21, base a1bc7eaf).
