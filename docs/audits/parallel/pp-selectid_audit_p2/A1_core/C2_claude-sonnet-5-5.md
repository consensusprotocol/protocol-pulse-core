# claude-sonnet-5-5 (effort high) 224 s stop_reason=end_turn usage=in 63540 / out 28412

# Cycle 2 audit: pp-selectid-p2, chunk A1_core (fixed diff)

**What I can and can't compare.** My Cycle 1 text was not included in the prompt (it says "see below", but nothing follows). I can't tell you what I got right or wrong then, so the Cycle 1 column below is "n/a". The peer median is given for reference.

**Scope.** This chunk holds `model_providers.json`, `moments_gate_adapter.py`, `package.py`, `package_pin.py` and `providers.py`. It does not hold `vo_fidelity`, `context_integrity`, `moments`, `transcript_truth`, `eligibility`, `canon`, any test, or the R7 `pinned.py` patch. Where a finding depends on those files, I say "not verifiable here" and do not call it fixed.

---

## 1. What the others caught that I would credit them for

All of the following is confirmed against the fixed code unless noted.

- **Pin literals (A fable, A opus, A sonnet, A grok, all of B).** Fixed in form. `package_pin.gate_problems` (L1192-1203) now refuses any required row that is not exactly `PASS` and live, and `package.inventory` (L1109-1142) builds the rows from the actual verdict objects. The consequences of how it was fixed are in section 3.
- **Exclusion gate not run in production (A fable P0-3, A sonnet P1-2).** Fixed. `exclusion_for` (L928-938) runs in the background for every line-up segment, and `lost` (L1067) drops any moment whose verdict is not `keep`.
- **Plain-VO path skipping L-v 2.** Fixed by removal. There is no plain fallback in `build` any more, and `plain_vo` (L535) is dead code.
- **Second pass optional and gated on numbers or negations.**
  - The trigger is fixed: `truth_for` now runs for every segment, `work_dir` is required (L987-989), and an empty `truth` gives `n=0`, which is `NOT RUN`.
  - The comparison direction, set-membership and `turn_change_inside: None` live in `transcript_truth`. **Not verifiable here.**
- **Runtime arithmetic (A sonnet P1-1).** Fixed. `FIXED_S = TAIL_S − 18/WPS` plus the real sign-off words (L570-571) counts the sign-off once.
- **Hard-coded vendors (A opus).**
  - `transcript_truth` now goes through `Router.transcribe` and the config role (L221-226).
  - `package.py` no longer names a vendor; `_writers` reads the config chain (L952-959).
- **Oversized local prompt downing Ultron (A sonnet P1-3).** Partly fixed. It is now `RequestRejected` (L1443), which is per call. The general "transient failure means down for the whole run" problem remains (see P2-6).
- **Empty `claims` passes (all Claude reviewers).** In `vo_fidelity`, **not verifiable here**. I would treat it as open until the diff for that file is shown.

## 2. Agree or disagree on key findings

| Finding | Verdict |
|---|---|
| Grok Q1 72 / Q2 88 / Q3 93 | **Disagree.** Grok missed empty or partial verdicts and, below, the step-A separation hole. It also calls the verdict chains vendor-clean because `avoid_vendor` is threaded. That holds only for verdict calls whose writer set is known at call time. |
| Grok P1, same-video "both agree" false reject | **Disagree.** Line-ups require every segment from a distinct channel (L766-773), so two cited segments are never one video. I cannot verify the RELATION rule, but the scenario cannot arise. |
| Fable P1-2, speaker is always the channel | **Mostly mitigated.** `fidelity_segments` (L888-896) names a speaker only when step A verified it. The `integrity` code the finding cites no longer exists in this chunk. |
| Opus, vendor is not family | **Agree, and implemented.** `family` plus `avoid_family` are in the config and the router. Residual issues are in section 3. |
| Sonnet, `down` is permanent | **Partially agree.** Retained; see P2-6. |
| Sonnet, adapter makes must-fail cases pass vacuously | **Agree.** Still present at L300-301; see P1-6. |

---

## 3. New findings (not raised in Cycle 1)

### P0

**P0-1. The step-A vendor and family check was lost in the refactor.**
- `build` receives `a_by, fails, a_vendors, a_families = prescreen(...)` (L977).
- `a_vendors` and `a_families` are never used again.
- `prescreen` avoids only the predicted writer from `_writers()`, which is the first chain entry that is not yet down. At the start of a run `router.down` is empty, so this is always the first back-end, `openai`.
- The angle call (L999-1000) and `write_v3` (L865) pass no `avoid_*` at all.
- Failing sequence:
  1. Step A runs on `grok`, which is down, so it runs on `anthropic:claude-opus-5-5`.
  2. OpenAI then runs dry. This is exactly the "tonight OpenAI ran dry" scenario in the providers docstring.
  3. `angle_write` falls over to `claude-fable-5-2`.
  4. The writer and the context-A judge now share a vendor and a family.
  5. `a_by` is reused unchanged by `cheap_checks`, `paid_gates` and `_lineup_block`. `writers_v` grows, but step A is never re-run or re-checked.
- This breaks L-s and L-x on the gate that clears every moment.
- The inventory row `context_a` (L1127-1129) records only the backends, never the comparison, and still reads PASS.
- Fix, either way:
  - Pass `avoid_vendor=a_vendors, avoid_family=a_families` to the angle and writer calls. Or:
  - Compare each writer reply against `a_vendors` and `a_families`, and re-run step A for the segments in the line-up when they collide.

### P1

**P1-1. The seal is computed too late and only over what `to_pin` sees.**
- `seal()` is called only inside `to_pin` (L1218). `build` never stamps a hash over the bytes the gates measured.
- Anything that edits `pk["vo"]`, `title`, `caption` or `segments` between `build` and `to_pin` is sealed as if gated, because `to_pin` reads `pk["vo"]`, not `pk["lines"]`, which is what the gates measured.
- The seal protects against tampering with the pin file after writing, not against changes to the package before it.
- Fix:
  - Compute `pk["sealed_sha"]` in `build` at the moment `inventory()` is called.
  - Have `to_pin` recompute and compare it.
  - Also compare `pk["lines"]` to the `vo`, `title` and `caption` fields.
- Related:
  - `zip(pk["vo"]["bridges"], pk["vo"]["bridges_after_clip"])` (L1217) silently truncates on a length mismatch.
  - The gate rows themselves are plain dicts with no MAC, so a hand-written `gates` of 12 rows (the full required set) passes `to_pin`.

**P1-2. `replayed` "not stated" is converted to "live".**
- `row()` (L1112-1114) does `"replayed": bool(replayed)`.
- A missing `replayed` key from `fid`, `ctx_`, step A or `truth` becomes `False`.
- `gate_problems` (L1201) then reads `replayed is not False` as live, so its "replayed or not stated" branch can never fire for a missing key.
- `ctx_.get("replayed")`, `fid.get("replayed")` and `a.get("replayed")` are not shown to exist in `context_integrity` or `vo_fidelity`.
- Fix: keep a tri-state and require an explicit `False` for every row.
- Also: `prescreen` stores step-A items (L638) from any run, including offline replay. A stored item reused in a live run carries whatever `replayed` it was stored with, or none.

**P1-3. The step-A ledger key does not bind the input.**
- The key is `moment_id:STEP_A_VERSION` (L608, L638).
- It excludes the window text, title, channel, published date and show date, all of which the step-A prompt sees (L621-625).
- A re-fetched transcript, an edited title or a changed context window under the same moment id reuses a stale clearance.
- The store is also read at the start of `prescreen` and rewritten at the end (L604, L639-643). Two runs lose each other's entries.
- Fix: key on a sha256 of the exact contexts dict, and write atomically with a lock.

**P1-4. `time_sensitive` and `price_prediction` rest on the miner's own `risk` list.**
- `usable()` (L453) and `lineup_for` (L774) read `m["risk"]`.
- `exclusion_verdict` now covers L-u hard exclusions independently. VO PRICE_NOW covers the VO's own price lines. Nothing visible re-measures:
  - an old-source "today" clip (L-v 3), or
  - the "at most one price prediction" cap (L-u).
- Failing input: the miner returns `risk: []` for a stale price call. It ships.
- Fix: run both through the independent verdict (add them to `exclusion_verdict`, or a second call). Or re-derive them deterministically from the clip text.

**P1-5. Empty replies do not fail over.**
- The `RequestRejected` docstring (L1304-1306) lists "an empty reply".
- OpenAI (L1470), Heimdall (L1498) and xAI (L1538) use `.get("content") or ""` and return `""`. Anthropic (L1570) joins text blocks and also returns `""`.
- `Router.call` (L1903-1925) returns that `Reply` at once.
- A reasoning model that burns its budget on thinking therefore ends the chain with an empty text.
- Result: the caller fails the gate (fail closed), but the next back-end is never tried. This is an availability bug that only bites more as chains reorder.
- Fix: raise `RequestRejected` on empty text in each backend, or check `text.strip()` in `Router.call` before returning.

**P1-6. Adapter: a malformed case is a free "fail".**
- `moments_gate_adapter.context_integrity` returns `{"verdict": "fail"}` when the case has no or several `role: "moment"` segments (L300-301).
- For every must-fail case with that shape, the exam counts a pass without any gate measuring it.
- This contradicts the module's own rule (L249-250: "never a free rejection either").
- Fix: raise `GateNotMeasured`.
- Also verify that the adapter's slot names (`f"{slot}_{i}"`, L330, e.g. `title_2`) match what `VF.check_deterministic` keys on. Production uses `intro`, `bridge_N`, `title`, `caption` (L551-553). The prefix logic exists in `assemble` (L554), and if `vo_fidelity` matches the exact slot name, the exam is measuring different rules. I can't see `vo_fidelity`, so this needs checking there.

**P1-7. The config puts local first on a hard-safety gate, unmeasured.**
- `exclusion_verdict` (config L203-211) is a one-model verdict where a false `keep` is final.
- The config's own header says "local first only where a measured A/B shows it meets the bar" (L9), and L10 says "an INITIAL order, not yet measured".
- The exam adapter that would measure it exists (L347-356).
- Fix: put a frontier model first for `exclusion_verdict` and `fidelity_verdict` until the exam passes on local, or require agreement from two vendors for `keep`.

### P2

1. **`exclusion_for` result is unguarded.** `got = {... f[0].result() ...}` (L1066): any exception raised inside `exclusion_for` that `M.exclusion_verdict` does not convert crashes `build`. It is a crash, not a pass, but it loses every package so far. `truth_for` already has the `try`.
2. **Sign-off budget uses a constant 18 words, but the sign-off length varies.**
   - `min_vo_words`, `r4_max_vo_words`, `budgets` and `content_range` (L475-488) assume 18 words.
   - `assemble` uses the real count (L570).
   - Long channel names mean the budget the writer is given can produce a package that fails the runtime gate (fail closed). The rejection text says "change the VO's length", which the writer cannot act on, so writes are wasted.
3. **`content_range`:** `next(...)` (L487) without a default raises `StopIteration` if the constants ever make the range empty.
4. **`usable`:** `E.age_hours(...) or 1e9` (L453) treats an age of exactly 0.0 as "unknown, too old". `lineup_for` reads `m["scores"]["hook_first_2s"]` (L764), which is a `KeyError` crash on a missing key.
5. **Budget is checked only between angles** (L1100). One angle can run several 600 s gate calls plus backoffs of 10/30/90 s per back-end, far past `BUDGET_S`.
6. **`Router.down` is run-wide for transient errors.**
   - A single 5xx or 529 after backoff downs a back-end for the whole run.
   - `_with_backoff` catches `ValueError` (L1382), so a malformed JSON body retries 10 + 30 + 90 s and is then treated as account-level unavailability.
   - The step-A / writer collision in P0-1 is made likelier by this.
7. **`transcribe` records every result, even an empty one** (L1972-1976), and has no `reject`. A garbage or silent-audio transcription is served from cache forever. `call()` has the `text.strip()` guard.
8. **Config issues.**
   - `trend_brief` has one back-end (L178-184); the law at L9 says every role names at least 2.
   - All three Heimdall back-ends point at `api-staging.heimdallm.com` (L75, L87, L99), a staging host in a production verdict chain.
   - The verdict chains end in `local:gemma3:27b`, so if frontier verdict models are unavailable the main honesty gate silently degrades to a 27B model. The inventory records `by` but nothing enforces a floor.
9. **`write_pin` is not atomic** (L1240-1246); use temp file plus `os.replace`.
10. **`exclusion_for` independence:** `avoid_model=(m.get("mined") or {}).get("by")` (L937) becomes `None` if `mined` is missing, so the miner can judge itself. The check is by backend name, not family.
11. **Untrusted transcript text goes into verdict prompts** (`quote_data` escaping, `UNTRUSTED` note). Residual prompt-injection risk is highest if `vo_fidelity` still accepts empty `claims` (not verifiable here).
12. **Vendor naming mismatch.** The class attribute `vendor` ("openai", "elevenlabs") differs from the config's vendor key ("openai_stt", "elevenlabs_stt"). `xai` and `xai_search` are two vendor strings for one account. The vendor skip logic is not affected today, but it will be if the same company's models appear under both.

---

## 4. Revised scores

Scores apply to this chunk only. Anything depending on files not shown is treated as unverified, not as passing.

| Subsystem | Cycle 1 | Cycle 2 | Peer median (C1) | Why |
|---|---|---|---|---|
| Q1 fail-open | n/a | **58** | 38 | Pin, exclusion, plain path, runtime math and the unconditional second pass are fixed. Empty verdicts, `compare` direction and unmeasured speakers are unverifiable. `replayed` is coerced to live (P1-2), and the step-A ledger is unbound to the input (P1-3). |
| Q2 vendor separation / L-x | n/a | **52** | 70 | Verdict calls avoid the writers well. Step A no longer avoids the actual writer (P0-1). Hard-coded vendors are fixed. The config puts local first on a safety gate, unmeasured (P1-7). |
| Q3 verbatim / model text | n/a | **80** | 75 | Clip text is by id and `m["text"]`. Title, caption and VO go through the gates. Residual: the angle is ungated but never reaches the audience. |
| Q4 deterministic rules | n/a | **45** | 40 | Not assessable from this chunk. Visible: `duplicates` lets paraphrased long clips pass, `usable` age-0 bug, `time_sensitive` and `price_prediction` self-reported (P1-4). |
| Q5 tests / R7 | n/a | **50** | 30 | Seal and inventory are real, and R7 can recompute. The seal is computed too late to bind the gated bytes (P1-1). The exam adapter has a free-fail path (P1-6). Tests and the R7 patch are not shown. |

---

## 5. Final priority list

**P0**
1. `package.py` L977 and L865 / L999-1000: enforce step-A independence from the actual writers. Use the unused `a_vendors` and `a_families`: pass them as `avoid_*` to the angle and writer calls, or re-run step A on collision. Add an end-of-`build` assertion over the real `Reply` objects.

**P1**
1. `package.py` L1109-1142 and `package_pin.py` L1218: stamp the seal in `build` over the gated bytes. `to_pin` recomputes and compares, and checks `lines` against `vo`, `title` and `caption`. Remove `zip` truncation (L1217).
2. `package.py` L1112-1114: tri-state `replayed`, with a required explicit `False`. Mark stored step-A items with their provenance (L638).
3. `package.py` L608 / L638: key the step-A store on a hash of the exact contexts. Write atomically.
4. `package.py` L453 / L774: independently verify `time_sensitive` and `price_prediction`.
5. `providers.py` L1470, L1498, L1538, L1570: empty reply means `RequestRejected`, so the chain continues.
6. `moments_gate_adapter.py` L300-301: raise `GateNotMeasured`. Check the slot naming at L330 against `vo_fidelity`.
7. `model_providers.json` L203-211 and the verdict chains: put a frontier model first for `exclusion_verdict` and `fidelity_verdict` until the exam measures local.
8. Show and re-audit the files not in this chunk: `vo_fidelity.check_verdict` (empty `claims`), `transcript_truth.compare` (direction, padding window, `None` speakers), and the R7 patch. The pin is only as strong as the gates feeding it.

**P2**
Items 1-12 above: guard `.result()`, make the sign-off budget real, `next` default, age-0 and `scores` KeyError, in-angle budget, `down` scope, `transcribe` rejection, config hygiene, atomic `write_pin`, `avoid_model` fallback, injection hardening, vendor naming.

---

## 6. Single highest-leverage change

End `build()` by re-deriving, from the actual `Reply` objects and the gated bytes, that no verdict or step-A back-end shares a vendor or family with any writer reply, and stamp the seal in the same step, so that neither failover nor later mutation can void the inventory.

## 7. Production ready?

**No. Yes with conditions** once these are met:
1. P0-1 is fixed and covered by a test that forces failover (writer moves to the same vendor as step A).
2. The seal is computed in `build`, and `to_pin` and R7 both verify it.
3. `replayed` is tri-state.
4. Empty replies fail over.
5. `time_sensitive` and `price_prediction` are independently measured.
6. The three unseen gate files (`vo_fidelity` empty-claims coverage, `transcript_truth` bidirectional and in-selection comparison, the R7 patch) are reviewed and show no regressions from Cycle 1.
7. Local-first on `exclusion_verdict` and `fidelity_verdict` is gated on a measured exam result.