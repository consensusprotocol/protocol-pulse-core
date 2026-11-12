# claude-opus-5-5 (effort high) 232 s stop_reason=end_turn usage=in 63540 / out 22870

# Protocol Pulse Cycle 2 audit: pp-selectid-p2, chunk A1_core (fixed diff)

**Reviewer:** Claude (Anthropic).

**My Cycle 1 text is not in this prompt.** The section "YOUR CYCLE 1 OUTPUT" contains only a placeholder. I cannot honestly say what I personally caught or missed, so I won't. Instead:
- I treat the four Cycle 1 outputs and the Cycle 1 consensus as the baseline.
- I re-audit the fixed A1_core diff line by line.
- In §4 the "Cycle 1" column is the median of the four reviewers' chunk-A scores, labelled as such.

**Scope:** model_providers.json, moments_gate_adapter.py, package.py, package_pin.py and providers.py. The files `vo_fidelity.py`, `context_integrity.py`, `moments.py`, `transcript_truth.py`, `select_by_id.py`, `pinned.py` (the R7 patch) and the tests are **not in this chunk**. Findings that depend on them are marked "unverifiable here".

---

## 1. What the other reviewers caught, and whether the fix landed

| Cycle 1 finding (who) | Status in the fixed A1 diff |
|---|---|
| **Pin stamps gates passed with literals** (all four) | **Partly fixed.** `to_pin` now refuses unless every row in `REQUIRED_GATES` is exactly `PASS` and not replayed (L1206-1209). Three gaps remain: the literals still exist (L1233); the seal is computed **at pin time, not gate time** (§3 N1); and the "not stated" replay check is vacuous (§3 N2). |
| **Exclusion verdict never runs in production** (fable P0-3, sonnet P1-2) | **Fixed.** `exclusion_for` runs `M.exclusion_verdict` on every line-up moment (L928-938, L1025, L1067). A non-`keep` result drops the moment. |
| **Second recognition pass optional; plain path skips it** (fable, opus, sonnet) | **Fixed in this file.** A missing `work_dir` returns no package (L987-989). The truth pass runs on every line-up moment (L1026, L1067). The plain path is no longer called; `plain_vo` is dead code (L535). An unmeasured pass is a drop (L948, L1067). |
| **One-directional, set-based truth compare** (fable, sonnet) | **Unverifiable here.** `transcript_truth.py` is not in A1. This must be confirmed in the other chunk. |
| **Blind verdict passes on `{"claims": []}`** (fable, opus, sonnet) | **Unverifiable here.** `vo_fidelity.py` is not in A1. This must be confirmed. |
| **Runtime arithmetic subtracts the sign-off twice** (sonnet, opus) | **Fixed.** `assemble` adds `so_words` (L570-571). `FIXED_S` removes the standard sign-off from `TAIL_S` once. The two now cancel correctly. |
| **`transcript_truth` hard-codes OpenAI; `"openai"` fallback** (opus) | **Fixed.** The `transcribe` role now goes through `Router.transcribe` (L1930). The `_writer_vendor` fallback is gone, and `_writers` returns empty sets (L952-959). |
| **`Router.down` marked permanent by one bad request** (sonnet) | **Mostly fixed.** `RequestRejected` covers 400/413/422, oversized local prompts and empty choices. Two residues remain (§3 N8). |
| **Speaker is always the channel** (fable P1-2) | **Partly fixed.** A speaker is named only when step A sets `speaker_verified` (L846, L893-895). Even then the "speaker" is the channel's *display name* (see §3 N12). |
| **Vendor ≠ family** (opus) | **Fixed.** `avoid_family` exists, every back-end has a `family`, and `_skip` checks it (L1862). |

---

## 2. Agree / disagree with key Cycle 1 findings

- **Fable / opus / sonnet: the blind fidelity verdict accepts zero claims.** Agree that it was real. It remains the single most important item I cannot verify in this chunk.
- **Grok, Q1 = 72, "only theoretical hole".** Disagree. It missed the empty-claims pass, the optional truth pass and the plain path, all of which the other three verified.
- **Grok: "both agree" from the same video is falsely rejected.** Disagree that it is reachable. `lineup_for` enforces one segment per channel (L766-772), and a video belongs to one channel. Two segments from one video cannot coexist in a package.
- **Grok: PRICE_NOW tolerance false-passes 74000 against 74210.** Mostly disagree. A 0.3 % rounding of a fresh level is not misleading. The real risk is level *freshness*, and `current_levels` handles that with the 24 h window (L716-729).
- **Grok: Title Case lines disable the NAME rule.** Agree in principle (fable and opus also raised it). `vo_fidelity` is not in this chunk, so I cannot confirm the fix.
- **Sonnet: hard exclusions rest on the miner's self-report.** Agree that it was true. It is now fixed for `excluded`. **It is still true for `time_sensitive`** (§3 N4).
- **Sonnet: `Router.down` is permanent and content-triggered.** Agree. Largely fixed, with residues in N8.
- **Opus: the exam adapter does not exercise production paths.** Agree. The adapter also still has one free-rejection path (§3 N9).

---

## 3. New findings in the fixed code

### N1 (P1). The seal binds pin-time bytes, not the bytes the gates measured
- The C1 fix was specified as `package.seal()` written by `build` over the gated bytes. The code computes `seal(...)` **only inside `to_pin`** (L1218), over whatever `pk["title"]`, `pk["caption"]`, `pk["vo"]` and segments hold at that moment.
- The gates measured `pk["lines"]` (L903, L919). Nothing checks at pin time that `pk["title"]` / `pk["vo"]` still equal `pk["lines"]`, or that the inventory belongs to these bytes.
- **Failing input:**
  1. Take a package that passed `build`.
  2. Set `pk["title"] = "Saylor: Bitcoin to $1M"`. The module docstring advertises a "STEP 3 OPTIMISE", so such edits are plausible.
  3. `to_pin` still pins it, with all rows PASS and a valid-looking `package_sha256`.
- **Fix:**
  - At the end of gating in `build`, compute `pk["gated_sha256"] = seal(...)` over the measured lines and segments, and store it inside the inventory.
  - In `to_pin`, recompute it and refuse on any mismatch.
  - Optionally HMAC the result with an env key, so that a hand-built dict cannot self-assert PASS.

### N2 (P1). `inventory.row` coerces `replayed` with `bool()`, so the pin's "not stated" check is dead
- `row()` stores `"replayed": bool(replayed)` (L1112-1114). `gate_problems` refuses `replayed is not False` (L1201), so only `True` is ever caught.
- Any gate result dict that **omits** `replayed` is therefore pinned as live. The affected sources are `fid`, `ctx_`, exclusion, truth and the step-A items, which come from VF / CI / M / TT and are not in this chunk.
- **Fix:** pass the raw value through and require `is False` per row. In `row`, map a missing key to `None`, not to `False`.

### N3 (P1). The step-A store can launder replayed verdicts into live runs
- `prescreen` writes every new step-A item to `store` (L635-643), even when `router.replay` is True.
- Later live runs reuse a stored item if its back-end is off the writers' vendor and family (L608-614). They never check whether the item was produced offline.
- `context_a`'s replayed flag is `any(a.get("replayed"))` (L1128). If `CI.step_a` does not stamp `replayed` on each item, a replayed step A becomes a deliverable PASS.
- **Fix:**
  - Never write the store when `router.replay`.
  - Stamp `replayed` and `backend` on each item in `prescreen` itself, not via CI.

### N4 (P1). L-v 3 time-sensitivity still rests on the miner's self-report
- `usable()` enforces freshness only when `"time_sensitive" in m["risk"]` (L453). That list is the mining model's own flag.
- PRICE_NOW checks VO lines only, not clip text, and `exclusion_verdict` covers L-u, not L-v 3.
- **Failing input:** a 3-week-old clip saying "Bitcoin just broke 100k today", with the miner returning `risk: []`. It ships.
- **Side bug:** `E.age_hours(...) or 1e9` treats an age of `0.0` as unknown, which rejects a source published this instant.
- **Fix:**
  - Run a deterministic time-word and price-level scan of `m["text"]` (the `current_level_values` and time-word lists already exist in VF) and OR it with the flag.
  - Write the age test as `is None`.

### N5 (P1). Step-A vendor separation was dropped: `a_vendors` / `a_families` are computed and never used
- `prescreen` avoids `_writers(router)`, which is the angle chain's **first live** back-end only (L976-977).
- If the angle or write call then fails over, the writer may share a vendor or family with step A. Example: openai is down, the writer becomes `anthropic:claude-fable-5-2`, and step A ran on `claude-opus-5-5`.
- Cycle 1 code re-ran step A in that case. The fixed code returns `a_vendors, a_families` (L644) but never reads them. `a_use` is reused unconditionally (L921).
- This breaks the config's own rule for `context_verdict` (L167: "never the writer's vendor") and the prescreen docstring (L595).
- **Fix:** before `paid_gates`, if `writers_v & a_vendors` or `writers_f & a_families` is non-empty, re-run step A for the line-up's moments while avoiding the writers.

### N6 (P1, verify against select_by_id). `RoleModel` gives no per-call model or family avoidance
- `RoleModel.complete` passes only a constructor-fixed `avoid_vendor` (L1988-1995).
- Both the `story` and `check` chains start with `local:gemma3:27b` (L186-199). So the check runs on the same model that wrote the story whenever local is up.
- This contradicts L-x ("generator and judge are different models") and the config's own `"called with avoid_model = the story's model"` (L201).
- **Fix:** add `avoid_model` / `avoid_family` to `complete()`, filled from the story reply's `meta["backend"]`.

### N7 (P2). The exclusion verdict avoids the miner's *model* only
- `avoid_model=(m.get("mined") or {}).get("by")` is used (L937), with no family avoidance.
- It works only if `mined.by` equals the config key string (for example `local:gemma3:27b`), not the bare model name `gemma3:27b`. This is unverifiable here.
- **Fix:** add `avoid_family`, and normalise to the config name.

### N8 (P2). Router residues
- **A malformed 200 body downs the vendor.** `_with_backoff` catches `ValueError` (a JSON decode of a 200 body) as transport (L1382). It retries 10 + 30 + 90 s, re-sends a **paid** request each time, then raises `Unavailable` and downs the vendor for the run.
  - Only one upper bound is reserved, so un-reserved retries can overspend the guard.
  - Timeouts (an `OSError`) behave the same way: up to 4 × 600 s on one call.
- **Anthropic 429/529 downs the vendor at once** (L1567), unlike every other back-end.
- **`SpendLimit` from `_reserve` aborts the whole chain** (L1897). The free `local` back-end later in the chain is never tried, which contradicts "a free back-end is never stopped" (L1278-1279).

### N9 (P2). The adapter has a free rejection
- `context_integrity` returns `"fail"` for a case with ≠ 1 moment segment (L300-301). This contradicts its docstring ("never a free rejection", L249-250).
- On a must-fail corpus, a malformed case scores as correct.
- **Fix:** raise `GateNotMeasured`.

### N10 (P2). Recordings are trusted as live verdicts
- In a live run, any file at the recording path is served with `replayed=False, cached=True` (L1889-1893). Nothing checks that its `prompt` or `backend` match, and `cached` is not carried into the inventory.
- The gate verdicts are only as trustworthy as the record directory's write permissions.
- **Fix:**
  - Verify `rec["prompt"] == prompt` and `rec["backend"] == name`.
  - Record `cached` in each inventory row.

### N11 (P2). Concurrency and cost in `build`
- **Duplicate paid calls.** The `exc` / `tru` caches use check-then-set from worker threads (L929, L942). Re-lined line-ups resubmit moments whose earlier futures are still running, so paid exclusion and STT calls can run twice.
- **Crash on exception.** An exception inside `exclusion_for` (`ReplayMiss`, `SpendLimit`) surfaces at `.result()` (L1066) and kills the whole build. That is fail-closed but loses all work.
- **Fix:** cache the future, not the result.

### N12 (P2). Deterministic false rejects and inconsistencies in this chunk
- **NO_LINE rejects valid through-lines.** The regex `^\W*(none|no\b|…)` (L815) rejects "No one can stop self-custody's growth" as having no through-line.
- **Quote style conflicts with DUPLICATE.** The quote style invites "at most four exact words" (L671-673). On a short clip (≤ 15 content words), four content words can reach the 60 % share and trigger DUPLICATE (L810). The writer is told to do what the gate rejects.
- **"Speaker VERIFIED" uses the channel's display name** (L847, L894). For a show-named channel, "Coin Bureau thinks so" passes as a person's attribution.
- **R4 ruling vs the writer's slots.** The R4 comment says "a VO line … after the last clip" (L467-468). `write_v3` writes `len(segs)-2` bridges, none after the last clip (L857, L686).
- **Dead plain fallback.** `plain_vo` is unused (L535-546). Either delete it or route it through the full gate set, so a future re-wire cannot reintroduce the unverified path.
- **Price_now gate may never measure (verify in VF).** The `price_now` row is `NOT RUN` whenever `det["price_now_measured"]` is false (L1124). If VF reports "not measured" when there are no current levels or no price in the VO, every such package becomes unpinnable.

### N13 (P2). L-x compliance is declared, not met
`angle_write` puts a frontier model first with "INITIAL order, not yet measured" (L10, L142-149). The law text (L9) requires a measured A/B before a frontier model may be first.

---

## 4. Revised scores

The "Cycle 1" column is the median of fable, opus, sonnet and grok on chunk A. My own Cycle 1 numbers are not in the prompt.

| Q | Cycle 1 (median) | Cycle 2 | Why changed |
|---|---|---|---|
| Q1 fail-open | 39 | **66** | Up: exclusion wired, truth pass required, plain path gone, pin refuses non-PASS. Down: the seal does not bind gated bytes (N1), the replayed check is vacuous (N2), the store launders replays (N3), and the VF empty-claims issue is unverified. |
| Q2 vendor / L-x | 71 | **68** | Up: family avoidance and STT through the router. Down: a regression, since step-A separation was dropped (N5); `RoleModel` lets the same model judge itself (N6); exclusion avoids model only (N7); frontier-first is unmeasured (N13). |
| Q3 verbatim / model text | 78 | **76** | Clip text is verbatim and the angle text is escaped. L-v 3 still trusts the miner's flag (N4), and "verified speaker" means the channel name (N12). |
| Q4 deterministic rules | 40 | **55** (scoped to A1) | The runtime arithmetic is fixed. NO_LINE and the quote-vs-DUPLICATE conflict are new false rejects. Most rules live in VF, which is not visible here. |
| Q5 tests / R7 | 22 | **30** | Unmeasured cases now raise `GateNotMeasured` (adapter L314-317, L336-341, L352-355). One free-fail path remains (N9). Tests and R7 are not in this chunk. |

---

## 5. Final priority list

### P0: carried over, must be confirmed fixed in the other chunk before merge
1. **`vo_fidelity.check_verdict`:** an empty or partial `claims` list must fail. Every non-connective slot needs ≥ 1 claim, and every claim needs cited support.
2. **`transcript_truth.compare`:** it must be bidirectional and position-aware for negations and numbers. An unmeasured speaker change must be a failure.

### P1: this chunk
3. **Bind the seal to the measured bytes** (N1; package.py L1080-1082, package_pin.py L1206-1218). Compute it in `build`, recompute in `to_pin`, and refuse on mismatch or on `pk["title"]` ≠ the title line.
4. **Stop coercing `replayed`** (N2; L1112-1114, L1201). A missing value must refuse.
5. **No store writes under replay; stamp `replayed` and `backend` per step-A item** (N3; L635-643, L608-614).
6. **Use `a_vendors` / `a_families`** (N5; L977, L921). Re-run step A when the writers overlap them.
7. **Make L-v 3 deterministic** (N4; L453). Scan clip text for time words and price levels, and fix the `or 1e9` age test.
8. **Give `RoleModel` per-call `avoid_model` / `avoid_family`** (N6; L1988-1995).

### P2
9. **Router:** stop retrying paid calls on a 200-body `ValueError`, back off Anthropic 429/529, and fall through to free back-ends on `SpendLimit` (N8; L1382, L1567, L1897).
10. **Adapter:** raise `GateNotMeasured` for malformed cases (N9; L300-301).
11. **Recordings:** verify prompt and back-end on load, and record `cached` in the inventory (N10; L1889-1893).
12. **Concurrency:** cache futures, not results (N11; L929, L942, L1025-1026).
13. **Small fixes:** NO_LINE, quote style vs DUPLICATE, delete or gate `plain_vo`, the R4 wording, confirm `price_now_measured` semantics, and exclusion `avoid_family` (N7, N12).
14. **Run the A/B** that the L-x law requires before frontier-first `angle_write` (N13).

---

## 6. Single highest-leverage change

Make the gate inventory cryptographically bound to the exact bytes it measured. `build` should seal the measured lines, segments and live-only (`replayed is False`) rows, and `to_pin` / R7 should refuse any mismatch. Without that binding, every other gate's PASS is a self-assertion.

## 7. Production ready?

**No.** I would accept it with these conditions:
1. P0 items 1-2 are verified fixed in `vo_fidelity.py` and `transcript_truth.py`, each with an adversarial test that fails on the old code.
2. P1 items 3-8 are implemented. Each has a unit test:
   - a mutated title after `build` is refused by `to_pin`;
   - a row with `replayed` missing is refused;
   - a replay-mode prescreen writes no store;
   - a writer failover onto the step-A vendor re-runs step A;
   - a stale clip saying "today" with an empty `risk` list is unusable;
   - the check role never runs on the story's model.
3. The R7 `pinned.py` patch recomputes the same seal and refuses on mismatch. This is verified against a real pin.
4. The pin stays `REVIEW ONLY` (no human approval implied) until the `angle_write` A/B required by L-x is run and recorded.