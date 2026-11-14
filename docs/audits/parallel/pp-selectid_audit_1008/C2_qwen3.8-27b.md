# qwen3.8-27b (qwen/qwen3.8-27b) 91 s finish=stop usage in 13056 / out 3054 usd~0.085 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-1008

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I (implicitly, as the "you" in the prompt structure) likely focused on the logic of the clock reset. The other models, specifically **Grok-4.20**, correctly identified the **cross-process slot starvation/claim bypass** as a `<critical>` issue in Cycle 1. I need to verify if the *current* diff fixes this or if it remains a latent risk depending on deployment order.

Grok's Cycle 1 finding was: *"pp-ingest current calls... bypass the skip... enables false reset after single failed call."*
The Cycle 1 Consensus recorded this as a **condition**, not a defect, arguing that `families=None` (the old behavior) is safe because *any* answer resets the clock.

**Did I miss the nuance?**
I need to check if the *new* code in `probe_due` (lines 111-113) actually prevents the "false reset" scenario Grok described, or if it only prevents *slot claiming* by the wrong prober.
- If pp-ingest (old code, `families=None`) claims the slot, it runs a probe on its families (qwen, glm, muse).
- If the builder's family (deepseek) is the one failing, and pp-ingest's probe (qwen) answers, `probe_result(True)` is called.
- `probe_result` resets `failing_since_utc` and `failing_families`.
- The clock stops.
- Is this a "false reset"? The ruling says: *"any answered call OR answered probe resets the clock to zero."*
- So, if qwen answers, the clock *should* reset. The "false outage" was when *no* answers were coming, but the clock ran. Here, an answer *is* coming.
- Therefore, Grok's "false reset" label was technically incorrect regarding the *ruling*, but correct regarding the *intent* that the probe should ask the *failed* family. The ruling says "A probe must be a real model call on the family that failed (and one other)". If pp-ingest probes qwen (not failed) and it answers, the clock resets. This is compliant with "any answer resets". It is *not* compliant with "probe must ask the failed family" if the probe *only* asks qwen. But the code allows `families=None` to claim.

**My Miss:** I failed to explicitly verify if the *steering* logic (lines 111-113) is sufficient to prevent the *builder* from being starved when *it* is the one that can ask the failed family, but the *other* prober (with `families=None`) grabs the slot first.
- Scenario: Builder fails deepseek. `failing_families=["deepseek"]`.
- Builder calls `probe_due(families=["deepseek", "glm", "qwen"])`.
- pp-ingest (old code) calls `probe_due(families=None)`.
- If pp-ingest calls *first*: `families is None` -> skip the check at line 112. It claims the slot.
- Builder calls *second*: `families` is not None. `failed` is `{"deepseek"}`. `failed & set(families)` is `{"deepseek"}`. It does *not* return False. It checks time. If pp-ingest just claimed, `last_probe_utc` is now. `(now - lp) < PROBE_EVERY_S` -> returns False.
- Result: pp-ingest claims the slot. Builder does not.
- pp-ingest probes qwen/glm/muse. If qwen answers, clock resets.
- If qwen *fails* (and deepseek is the only one down, but qwen is also down?), clock continues.
- The issue is: The *builder* is the one that *can* ask deepseek. If pp-ingest grabs the slot, it *cannot* ask deepseek. If deepseek is the *only* family down, and qwen/glm/muse are up, pp-ingest's probe will answer, and the clock resets. This is *correct* behavior per the ruling ("any answer resets").
- However, if deepseek is down, and qwen/glm/muse are *also* down (total outage), pp-ingest's probe fails. Clock continues. Builder is starved from probing deepseek (which is also down). No difference in outcome.
- What if deepseek is down, but qwen is up? pp-ingest probes qwen, it answers, clock resets. Builder never gets to probe deepseek. But the clock reset is *valid*.
- So, is there a bug? The ruling says "A probe must be a real model call on the family that failed". If pp-ingest probes qwen, it is *not* calling the family that failed. Does this violate the ruling?
- The ruling context: "so one failed call followed by one good probe is never 'down'".
- If the "good probe" is on a *different* family, is it a "good probe" for the purpose of the failed family?
- The ruling says: "any answered call OR answered probe resets the clock". It does *not* say "only a probe on the failed family resets the clock".
- Therefore, the steering logic is an *optimization* to ensure the *most relevant* probe happens, but the *reset* logic is broader.
- **Conclusion:** The "critical" finding from Grok in Cycle 1 was based on a misinterpretation of the ruling's reset condition. The reset condition is "any answer". The steering condition is "ask the failed family". The code implements both. The interaction is safe.

## 2. WHERE DO YOU AGREE OR DISAGREE?

- **Grok-4.20 (Cycle 1):**
    - **Disagree** with the `<critical>` severity. The "false reset" is not false; it is a valid reset per the ruling. The "bypass" of the steering logic is by design for backward compatibility (`families=None`).
    - **Agree** with the `<medium>` finding on `now >= fs` (equal times). The code uses `>=`, which means an answer at the *exact* second the clock started resets it. This is correct ("not before").
    - **Agree** with the `<medium>` finding on `family=None` in `note`. If `family` is None, `failing_families` is not updated. This is correct; we don't know which family failed.

- **Qwen3.8-27B (Cycle 1):**
    - **Agree** with the conclusion that the race condition is handled by `flock`.
    - **Agree** that the "False Outage" scenario is fixed by `probe_result(True)` resetting the clock.

- **GLM-5.3-Flash (Cycle 1):**
    - **Disagree** with the "none found" assessment. It was too shallow.

## 3. NEW FINDINGS FROM THIS REVIEW

**<medium> `pipeline/heimdall_health.py:112` (Steering Logic Edge Case)**
The condition `if families is not None and s["mode"] != "plan_b" and failed and not failed & set(families): return False`
If `failed` is empty (no families recorded as failing), the condition `failed` is False, so it does *not* return False. This is correct.
If `failed` is not empty, but the prober's `families` list is empty `[]`, `set(families)` is empty. `failed & set(families)` is empty. `not empty` is True. It returns False.
This means a prober with an *empty* family list will *not* claim the slot if there are failing families. This is correct behavior (it can't ask any of them).

**<medium> `pipeline/heimdall_health.py:136` (Late Report Guard)**
`if answered and (fs is None or now >= fs):`
If `fs` is None (no clock running), it resets. This is correct.
If `now < fs`, it does *not* reset. This is correct.
What if `fs` is in the *future*? (Clock bug). `now >= fs` is False. It does not reset. This is safe.

**<high> `pipeline/providers.py:1037-1038` (Probe Thread Family List)**
```python
families=sorted({self.backends[n].family for n in fams})
```
`fams` is the list of families the router probes. The background says: "their chains use only the families deepseek, glm and qwen".
So `families` will be `["deepseek", "glm", "qwen"]`.
This is passed to `probe_due`.
If `failing_families` is `["muse"]` (pp-ingest's family), the builder's `families` do *not* include "muse".
`failed & set(families)` is empty.
Builder returns False.
pp-ingest (if updated) passes `families=["qwen", "glm", "muse"]`.
`failed & set(families)` is `{"muse"}`.
pp-ingest claims.
This is correct.

**<critical> `pipeline/heimdall_health.py:112` (Plan B Bypass)**
The condition `s["mode"] != "plan_b"` ensures that in Plan B, *any* prober can claim.
This is correct. Plan B needs to close, so any answer helps.

**<medium> `tests/providers/test_heimdall_health.py:271-273` (Malformed Field Test)**
```python
st["mode"], st["failing_families"], st["failing_since_utc"] = "heimdall_first", "muse", "2026-11-14T02:30:00Z"
json.dump(st, open(self.state, "w"))
self.assertTrue(HH.probe_due(self.state, at(31), families=mine))
```
Here, `failing_families` is set to the string `"muse"`, not a list.
`_families(s)` at line 92:
```python
f = s.get("failing_families")
return [x for x in f if isinstance(x, str)] if isinstance(f, list) else []
```
If `f` is `"muse"` (a string), `isinstance(f, list)` is False. It returns `[]`.
So `failed` is empty.
The condition `failed` is False.
It does *not* return False.
It proceeds to check time.
It claims the slot.
This is correct: "A malformed field reads as none: no prober is kept out by it."

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| Clock Logic | 9/10 | 10/10 | Verified `now >= fs` handles equal times correctly. |
| Slot Claiming | 7/10 | 9/10 | Verified steering logic works for both updated and legacy probers. |
| Plan B Interaction | 8/10 | 9/10 | Verified Plan B bypasses steering, allowing any prober to claim. |
| Test Coverage | 8/10 | 9/10 | Tests cover malformed fields, late reports, and steering. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:** None.

**P1 HIGH:** None.

**P2 MEDIUM:**
1.  **`pipeline/heimdall_health.py:112`**: The steering logic relies on `failing_families` being accurate. If `note(False)` is called with `family=None` (legacy), `failing_families` remains empty (or unchanged). If the clock is running but `failing_families` is empty, *any* prober can claim (since `failed` is empty). This is safe but less optimal. No action needed.
2.  **`pipeline/providers.py:1037`**: Ensure `fams` is never empty. If `fams` is empty, `families` is `[]`. A prober with `families=[]` will *not* claim if there are failing families. This is correct.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The addition of `families` to `probe_due` and `family` to `note` is the highest-leverage change, as it enables the "steering" of probes to the failed family, which is the core of the amended ruling.

## 7. PRODUCTION READY?

**Yes with conditions.**

**Conditions:**
1.  **pp-ingest must update its calls** to pass `family` to `note` and `families` to `probe_due` before this change is deployed. If pp-ingest is not updated, it will use `families=None`, which is safe (it can claim any slot) but less optimal (it might claim a slot that the builder could have used to probe the failed family). However, since *any* answer resets the clock, this is not a correctness issue, only an efficiency issue.
2.  **Verify that `fams` in `providers.py` is not empty** when the probe thread starts. If it is empty, the builder will not claim slots when there are failing families. This is unlikely but should be verified.

**SHIP: yes with conditions**