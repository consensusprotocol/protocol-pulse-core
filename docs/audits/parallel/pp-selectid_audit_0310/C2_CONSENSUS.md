# pp-selectid audit 0310 (the render's STAND_ALONE at the pin stage): cycle 2 consensus, FINAL

Synthesis by the pp-selectid session, 03:16 ET Nov 13.

**Run.** Cycle 2 cross-reviewed the FIXED diff against the cycle-1 reviews and C1_CONSENSUS.md. No P0. Verdicts:
- grok (xAI): no P0 and no P1, "Yes. No conditions";
- glm (Heimdall): no P0 and no P1, P2 items only;
- qwen (Heimdall): "Yes with conditions". Its one "P1" asks to verify an invariant, which is answered below (Q1).

## Consensus (implemented or verified)

| # | finding (reviewers) | disposition |
|---|---|---|
| Q1 | The fixed subject {bitcoin, btc} holds only while every moments pin is labelled 'bitcoin' (qwen P1, glm P2-3) | VERIFIED and TESTED. package_pin.to_pin writes "label": "bitcoin" as a constant (package_pin.py:179). A test now asserts it on a medley pin. |
| Q2 | required_gates for a non-medley shape is unverified (glm P2-1, still open after cycle 1) | TESTED: required_gates({"shape": "story"}) does not hold "stand_alone". |
| Q3 | no_role_on_screen read m.get("text") while stand_alone_check reads m["text"] (qwen P2) | IMPLEMENTED: m["text"], so a moment without text fails fast. |

## Kept (with reasons)

- **glm N1:** `cleared[sg["moment_id"]]` is a direct subscript in both inventory calls. KEPT, because it fails closed: every sealed segment comes from cleared, and a KeyError aborts the build rather than sealing.
- **glm N2:** the order of no_role. Informational; nothing reads it.
- **glm N3:** check_edl runs twice, in the line-up filter and in the inventory. Pure-re CPU in microseconds, and both runs read the same segments.
- **glm N4:** verified both directions.
  - pin-FAIL means render-FAIL, or a scorer rescue the pin never relies on.
  - pin-PASS means render-PASS: a passing line-up has no conjunction or reply opener, so the render's scorer is never asked, and the opener and topic rules are byte-identical.

## Verification

- test_medley 51 OK; test_gates, test_angles, test_speakers, test_hook_onset, test_house_style and test_providers OK.
- Reproduction on the held pin d2657bbe: hook PASS, clip_01 FAIL, clip_02 FAIL. These are the render's own verdicts (runs/pinned_20261113_075638/run_log.txt lines 47-49).
