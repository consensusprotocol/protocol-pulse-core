# Heimdall audit

**Question:** Batch 56 cycle 2 (verification). Cycle 1 implemented: valley_in reset for a moved cut; every measurement applies the clip's own fade-in (prepare's order); a padded-None test. Re-measured: pin #1 refused (best 60 ms), the medley hook unchanged, check_medley_reference REPRODUCED.

Batch 56 = RULING 28 (orchestrator 2026-11-13 '01:55'), verbatim: "G17 hook lead 30 ms against 80 ms: the cut is wrong, not the rule. The pin stage measured the transcript gap, the gate measures sound. ... For this pin: move cut_in earlier inside the 230 ms pause if the measured quiet allows 80 ms, else a declared pad as D1 permits."
Measured on pin #1's hook (Sjb6lUiL0m4):
- the 230 ms gap holds a breath, then the digital zeros of a hard edit until about 40 ms before the first word;
- every legal cut keeps 0-20 ms of genuine quiet (G17a counts nothing below the -100 dBFS digital floor);
- the D1 pad loops the source's own quietest room tone (a 40 ms run at -65..-69 dB). Each loop join dips to -107 dB, below the floor, so even padded the head measures 20 ms.
The change, in sentence_law.write_lock_cut_table, for the HOOK only, when it is not at a file head (the file-head D1 rule is unchanged), via the new hook_lead(src, plan, pick):
1. G17a's own measure (head_tail) on the audio as cut at the planned cut (hook_lead_at): >= 80 ms -> the cut stands.
2. Else the legal candidates inside the pause (cut_candidates: cut_accept-clean, nearest the target first), each with its edge fade and neighbour_clear: the first keeping >= 80 ms is taken.
3. Else the D1 pad (LEAD_PAD_S 0.25 s) before a candidate whose quiet is genuine from the cut to the word (onset > one hop, and lead >= onset - one hop), and ONLY when padded_lead_ms (room_tone + the audio as cut, head_tail) measures >= 80 ms.
4. Else the entry is refused: verified false with the measured reason, so stage_cut HOLDS before any render. That is fail-closed, earlier than G17a.
Measured outcome: pin #1's hook is refused with "... G17a measures 20 ms at 14.810, 20 ms at 14.820 ...", and its clips keep their cuts. The medley reference's hook keeps its planned cut (260 ms), and check_medley_reference REPRODUCES. The protected references' hooks measure 120-310 ms, so step 1 applies to them.
Tests: test_hook_lead 6 (two on the real fixtures; four on the decision logic with stubbed measurements).
FIND: anything still open; a hook G17a will fail that passes the cut stage, or the reverse; a reference cut changed; a non-hook clip affected; a test that does not test what it claims. Reply with the JSON verdict; keep the reasoning short; at most 3 findings.

**Panel:** qwen27b, glm  |  **Cost:** $0.0028
## Consensus findings (majority of panel agrees)
- **[critical] pipeline/sentence_law.py:810** The code sets `verified: True` for refused hooks, contradicting the audit description ('verified false') and the test expectation (`assertFalse(h['verified'])`). This causes the test to fail and misrepresents the state of the cut table.
  - evidence: `cuts.append({**entry, "error": f"hook lead (ruling 28): {hook['refused']}", "hook_lead": hook})
                continue`
  - fix: Add `"verified": False` to the entry dict when appending a refused hook: `cuts.append({**entry, "verified": False, "error": ..., "hook_lead": hook})`.
  - raised by qwen27b:F1; agree: qwen27b, glm
- **[medium] pipeline/test_hook_lead.py:46** The test `test_pin1s_hook_is_refused_before_any_render_and_its_clips_keep_their_cuts` expects `h['verified']` to be `False`, but the code sets it to `True` (or leaves it as default `True` from `entry` if `entry` has it, but `entry` is built from `pick` which likely doesn't have `verified`). Actually, `entry` is built earlier in `write_lock_cut_table`. Let's check. `entry` is `{**pick, ...}`. `pick` comes from `plan['in']` or similar. It likely doesn't have `verified`. So `cuts.append({**entry, ...})` will not have `verified` unless added. The code for the refused case does NOT add `verified`. So `h` will not have a `verified` key. `h['verified']` will raise `KeyError`. The test will crash, not just fail.
  - evidence: `self.assertFalse(h["verified"])`
  - fix: Ensure the refused entry explicitly sets `"verified": False` in `sentence_law.py` so the test can access it.
  - raised by qwen27b:F3; agree: qwen27b, glm

## Raised but not agreed
- qwen27b:F2 [high] The `genuine_from_cut` logic uses `onset` (time from cut to first sound) to verify quietness, but `onset` is not guaranteed to be the time to the *first word* if there are non-word sounds (like breaths) before the word. The audit states 'the word record puts the word's start before the zeros end', implying the cut is on the zeros. If `onset` measures the start of the zeros (digital silence), `lead` might be small, but `onset` could be large if the zeros are considered 'sound' by `head_tail` or if `head_tail` returns 0 for digital zeros. More critically, the condition `lead >= onset * 1000 - HOP_S * 1000` is a heuristic that may not correctly identify 'genuine quiet from the cut to the word' as required by Ruling 28 Step 3. If `head_tail` treats digital zeros as silence, `onset` will be the time to the first *non-zero* sample. If the first non-zero sample is the word, this is correct. However, the audit notes 'digital zeros... until about 40 ms before the first word'. If `head_tail` detects the word at 40ms, `onset` is 0.04. `lead` is 20ms. `20 >= 40 - 10` is false. So `genuine_from_cut` is false. This seems correct for pin #1. But the logic is fragile. A more direct check against the word timestamp from the transcript would be safer. (agree: 1)
- glm:F1 [medium] hook_lead_at's fade-in is applied to the raw head, but G17a's head_tail measures the rendered clip whose fade-in starts at the cut, so a fade longer than the measured window shifts the onset later than the gate will see it; a hook whose lead0 < 80 ms only because the fade eats the head would be moved/padded though the rendered clip passes, and conversely a hook whose fade pushes the onset past the window would pass the cut stage and fail G17a. (agree: 0)

## Added in cross-examination (not voted on)
- glm: [medium] In the pad loop, t['padded_lead_ms'] is only set for candidates that pass the neighbour_clear and genuine_from_cut filter, but the refusal message's list comprehension (padded = [(t['cut_in'], t['padded_lead_ms']) for t in tried if 'padded_lead_ms' in t]) silently drops candidates that were tried but not padded, so the refusal reason can under-report (e.g. a candidate that is neighbour-clear but not genuine_from_cut gets no padded measurement and no mention), weakening the 'measured reason' requirement of ruling 28.
- glm: [low] The logic tests stub hook_lead_at, cut_candidates, edge_fades, neighbour_clear, and padded_lead_ms, so they never exercise _cut_head/_head_tail_of/room_tone; the only integration coverage is the two real-fixture tests, which are skipUnless-guarded and silently skip when the pin/medley media are absent, leaving the fade/measure path (the actual ruling-28 measurement) untested on a machine without the fixtures.
- glm: [low] The hook branch reads plan['in']['lead_in_pad_s'] into pad_s before the hook decision but then overwrites it with hook['pad_s']; for a hook whose planned cut stands (step 1), hook['pad_s'] is 0.0, discarding any planner-set lead_in_pad_s for that hook, so a planned pad on a hook that passes step 1 is silently dropped from the cut table.
