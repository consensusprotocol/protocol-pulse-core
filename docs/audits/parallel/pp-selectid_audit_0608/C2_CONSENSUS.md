# Audit 0608 (ruling 91's MEDLEY half: the takeaway's value verdict), cycle 2: consensus

Reviewers on the fixed diff (cycle 1's consensus applied):
- grok-4.20: P0 none, P1 none, SHIP yes with conditions.
- glm-5.3-flash: P0 none, P1 none, production ready "yes with conditions". It finished this time (finish=stop).
- qwen3.8-27b: one P1, which is the orchestrator's open question (A), below.
- No reviewer found a defect that could seal a wrong pin.

Upper-bound cost of the cycle: about $0.38 ($0.156 + $0.114 + $0.113). The two cycles together: about $1.04, outside
SPEND_LY.json.

## Implemented (a reviewer's condition)

- glm condition 1: one test proving the forced ruling-91 rewrite after a ruling-66 takeaway-alone write is judged on its
  OWN new text: test_the_rewrite_after_a_takeaway_alone_is_judged_on_its_own_new_text.
  - The scenario: writes 1 and 2 fail the fidelity verdict on the takeaway. The takeaway alone then loses its value
    verdict, so the forced rewrite follows.
  - The test runs the real takeaway_alone_gates (only VF.check and the context check stubbed). The fidelity verdict
    judged exactly [[the new takeaway]], alone.
  - The sealed row's text is the new line. The attempts show the ruling-66 write, then the ruling-91 one.
  - Test only, no code change. The 11-mutation check still kills every mutation. 19 suites, 537 tests.
- glm condition 2 (replayed false enforced for this row): already met. gate_problems refuses any required row whose
  replayed is not exactly False. The existing test feeds {"text": t, "replayed": True} through to_pin and gets
  PinRefused. glm agrees it is "effectively met".

## The orchestrator's question (A), not a defect (asked on STATE line 1 at 06:14, again at 06:25)

- qwen P1 (grok and glm: "agree, by design"): a value loss on short clips never falls back to ruling 3's added clip.
  The line-up ends after the one rewrite.
- That is ruling 91's text: "falls back to L-y's no-voice shape ONLY IF its clips meet the seconds; otherwise the
  takeaway may be rewritten once".
- If the orchestrator rules that 91 leaves ruling 3's added clip in play, it is a one-line change, re-audited.
- test_a_value_loss_never_counts_toward_ruling_3s_two_failures pins the current reading.

## Refuted, with evidence from the code

- grok P2, compare the row's text after strip():
  - Both sides read ONE string. The verdict judges fields["takeaway"]["text"], and assemble_medley puts that same
    string into vo.bridges and lines.
  - So a writer's trailing space is in both, the exact comparison passes, and the render's strip() comparison passes
    too.
  - A difference can only come from a stale or foreign verdict, which is exactly what the exact check refuses. No
    change.
- grok P2, "no_voice_fits is blocked when the initial clips-alone verdict is unmeasured":
  - No write is ever paid before a MEASURED clips-alone pass. build() writes only after ok_m, which needs
    medley()'s measured verdict, so in the write loop med["measured"] is True.
  - An unmeasured verdict ends the line-up before any write.
- glm P2 (a, verify) "takeaway_alone_gates may inherit the previous write's verdict for the takeaway":
  - takeaway_alone_gates runs VF.check on the takeaway line ALONE and merges it in place of that slot's earlier
    verdict (merge_fid). Context integrity runs on the whole package as sealed.
  - The test above proves it by execution.

## Accepted as is, with reasons

- The (f) edge (grok P2 1, qwen <medium>): accepted, fail closed, and documented in C1_CONSENSUS with a proposal for
  the orchestrator (ruling 65 (b)'s fixed caption on both no-voice paths). Not built: it reaches beyond ruling 91's
  text.
- glm P2, "label both rulings when ruling 3 also fired": cosmetic.
  - The no-voice record already carries the ruling-91 verdict and why.
  - take_failed is visible in the line-up record's attempts.
  - Not changed after cycle 2.
- glm P2, also refuse a replayed verdict in takeaway_value's ok:
  - The replayed-false contract is enforced for EVERY required row in one place (package_pin.gate_problems), at the
    build and at the pin.
  - No other verdict special-cases replay. A replay (offline) run is never deliverable anyway (law L-j).
  - Not changed.
- glm <low>: takeaway_value raising (it catches broadly), and takeaway_line on mismatched list lengths (fail closed via
  the text check). Theoretical, non-blocking, agreed.

SHIP. The commit carries the three files exactly as the dev01 scratch copy holds them. FINAL.diff = C2_STEP.diff plus
glm's requested test (test only).
