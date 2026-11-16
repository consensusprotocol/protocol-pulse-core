# mimo-v2.6-flash-rl (xiaomi/mimo-v2.6-flash-rl) 265 s finish=stop usage in 5868 / out 20411 usd_reported=0.002026 usd~0.324 (upper-bound price)

# Audit: pp-selectid — RULING 122 (3) The No-Hook Line

## Check (1): Is the line true in every case?

**The logic is sound.** When `passing` is empty and `on_bar` is non-empty, every `on_bar` moment must be visually blocked — because any `on_bar` moment that were *not* visually blocked would flow through `can_open()` → `hook_pool` → `passing`, contradicting the branch guard. The message's claim ("the visual check refuses each") is therefore correct by construction.

When `on_bar` is empty, the fallback "none of the N…" is also correct: no rated opener passes the bar.

**[P3]** Grammar: when `len(on_bar) == 1`, the f-string produces *"1 of the 4 moments that can open **pass** the calibrated hook bar"* — the subject is "1" (singular), so it should read *"passes"*. The test asserts the same incorrect string, so both code and test would need updating together. Semantically the line is true; this is purely a wording nit.

**[P3]** `m.get('channel_name')` can return `None` if the key is absent from a moment dict, yielding *"None h: …"* in the message. The parallel `m['moment_id']` uses `[]` (will `KeyError` if missing) while `channel_name` uses `.get()` (silently `None`) — inconsistent access on the same dict. In practice both keys are present in the test rig, so this is defensive-coding hygiene rather than a live defect.

## Check (2): Did any gate change?

**No.** The diff touches only the `why_none` string construction. `hook_pool`, `can_open()`, `visual_hook_block`, `HB`, `hook_bar.passes`, and every threshold are untouched. The `on_bar` list-comprehension is computed solely for the message. No gate, no threshold, no classification changed.

## Check (3): The tests

Both scenarios are covered correctly:

| Scenario | Assertion | Verdict |
|---|---|---|
| Visual check alone refuses a bar-passing hook | `"1 of the 4 moments … pass the calibrated hook bar"` present; `"the visual check (rulings 70 / 93) refuses each … A h: ruling 93 … a ticker"` present; `"none of the"` absent | ✅ |
| Bar itself refuses | `"none of the 4 moments … passes the calibrated hook bar"` present; `"the visual check"` absent | ✅ |

The two assertions are mutually exclusive and correctly exercise both branches of the ternary. The `assertNotIn` guards prevent regression to the old misleading wording.

**Not covered (acceptable):** the mixed case where some openers fail the bar *and* some are visually blocked — `on_bar` would contain only the visually-blocked passers, and the message would correctly say "K of the N pass … visual check refuses each" while silently omitting the N−K that fail the bar. This is arguably fine (the message focuses on what *did* pass), but a test would strengthen confidence.

---

**Summary:** The change correctly diagnoses and fixes the RULING 122(3) misdiagnosis. No gate altered. Two cosmetic nits.

P1_OR_WORSE: 0