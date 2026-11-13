# glm-5.3-flash (z-ai/glm-5.3-flash) 114 s finish=stop usage in 15612 / out 3089 usd~0.093 (upper-bound price)

# pp-selectid-1300 — CYCLE 2 REVIEW (RULING 65: a caption never kills a package)

## 1. WHAT DID THEY CATCH THAT I MISSED?

Honest accounting against my Cycle 1 output:

- **GLM's P1-1 (merge_fid's `ok` recomputation ignores a non-`violations` failure marker).** I did not flag this. The concrete scenario — `d0 = {"ok": False, "violations": [], "price_now_measured": False}` merging to `det["ok"] = True` — is real *as a code-reading matter*: line 93 (`det["ok"] = not det["violations"]`) and line 99 (`ver["ok"] = measured and not ver["violations"]`) both recompute `ok` from `violations` alone and discard the stored flag. Whether it bites depends on whether `VF.check`/`VF.check_deterministic` ever return `ok: False` with empty `violations` — which I cannot verify from the diff. GLM itself hedged ("if it never does, downgrade to P2"). I agree with the hedge: it's a P2, contingent on VF's contract, not a P1.
- **GLM's P1-2 (title-hold returns a literal `{"ok": True, "violations": []}` context record).** I missed the shape-thinness. But the consensus refutation (G1) is correct and I adopt it: the hold breaks the line-up before any inventory is built, the hold rests on `fid["ok"]=False` at line 213, and the ruling's (c) says "then hold" — nothing seals. Downgrade to recorded, no change.
- **GLM's P1-3 (success-path break with `why=None`).** I missed the `rw.get("why")`-is-None wrinkle. The consensus refutation (R3) holds: `rewrite_alone` raises on any cheap2 failure *before* the verdict (line 133-134), so a returned "passed" rewrite always has empty cheap results; the `if not (fid["ok"] and cx["ok"]) or cheap:` at 213 can't see a non-empty `cheap` on the success path. Disagree with GLM's severity; the state is unreachable.
- **QWEN's P0/P1 (fixed-caption path doesn't check cheap3; att["violations"] stale).** Both correctly refuted in the consensus (R1, R2): the caller unpacks `cheap, det, dup, rt_ok, r4_res = cheap_t` (line 209) and gates at 213 before anything seals; `att` is a record, not a decision input. QWEN's own text conceded the P0 mid-argument. I agree with the refutations.
- **GROK's P2s.** All confirmations, no disagreements. Its note that `writers_v.add(r.vendor)`/`writers_f.add(r.family)` occur *before* VF.check (L-x) is the cleanest statement of the L-x compliance and matches line 129-130 preceding line 136.

What I caught that nobody else weighted: the **K1 reading** (cheap failures on a lone caption/title now enter the paid-gates path) and the **`att["violations"] = cheap + fid["violations"] + cx["violations"]` change at line 194** — the old redo's `_redo` instructions now include cheap violations (line 227), which is a behavior change to the old path nobody else examined.

## 2. WHERE DO I AGREE / DISAGREE?

| # | Finding | Verdict | Why |
|---|---|---|---|
| R1 | qwen P0: fixed-caption cheap3 unchecked | **Agree with refutation** | Caller gates at 213 on `cheap` (=cheap3) before any seal; fid3["ok"] also fails if deterministic layer failed (merge_fid line 100-101: `ok=det["ok"] and ver["ok"]`). |
| R2 | qwen: att["violations"] stale | **Agree with refutation** | att is record-keeping; sealing decisions read fid/cx/cheap/dup/rt_ok/r4_res. |
| R3 | glm P1-3: why=None on success break | **Agree with refutation** | cheap2 failure raises (line 133-134) before "passed" can be set; unreachable. |
| G1 | glm P1-2: literal cx on title hold | **Agree: recorded, no change** | Hold precedes inventory; ruling (c) intends the hold. |
| G2 | glm P1-1: merge_fid ok-recompute | **Partially agree** | Real code-reading, but contingent on VF's contract (does VF.check ever return ok:False, violations:[]?). Unverifiable from the diff → P2, not P1. |
| G4 | replayed vs cached both free | **Agree** | Line 176: `0 if med.get("replayed") or med.get("cached") else 1` — matches the 12:00 note's "cached verdicts for an identical line-up are free". |
| — | grok's L-x ordering | **Agree** | writers_v/writers_f updated (129-130) before VF.check (136) — the line's verdict never comes from its writer. |

## 3. NEW FINDINGS FROM THIS REVIEW

**N1 (P2) — `merge_fid`'s `classes` for the replaced slot can be `None` when the fallback's `one` lacks that slot's class.** Line 97: `classes=dict(v0.get("classes") or {}, **{slot: (v1.get("classes") or {}).get(slot)})`. In the fallback path (line 159) the hardcoded verdict *does* carry `classes: {"caption": ["the fixed line: no fact"]}`, so the shipped path is fine. But `merge_fid` is a general helper: any caller passing `one` without `classes[slot]` seals a verdict whose class for the replaced line is `None` rather than absent. Cosmetic/record-keeping only; the gate reads `violations`, not `classes`. Nobody flagged the general-case None.

**N2 (P2) — the title-hold path's `cheap` recheck is redundant but harmless, and the hold's `fid` loses `measured` provenance.** Line 152: `dict(fid, ok=False)` — the held record keeps `measured: True` from the first run while the second (held) write's fidelity was never measured. Correct per the ruling (the hold is the *line-up's* outcome, not a fidelity claim about the second write), but the record's `backend` still names only the first run's back-end while `rec` (the rewrite record) names the second. A reader of the pin's provenance could think the second write was fidelity-checked. Record-keeping only; the gates are right.

**N3 (P2) — `write_line`'s length check duplicates LINE_LIMIT semantics but the prompt's `{limit}` and the enforcement can drift.** Line 37 vs line 62: the enforcement hardcodes `220 if slot == "caption" else 70` while the prompt interpolates `LINE_LIMIT[slot]`. If LINE_LIMIT ever changes, the prompt says the new limit but the code enforces the old. One-line fix: `len(ln["text"]) > int(LINE_LIMIT[slot].split()[2])` or a parallel dict. Nobody caught this.

**N4 (P2, contingent) — `lone_slot` treats a violation with `slot: None`/missing as a distinct slot.** Line 74-75: `slots = {v.get("slot") for v in violations}`; a cheap violation lacking a `slot` key yields `None` in the set, so `len(slots) == 1` with a single keyless violation returns `None` (not "caption"/"title") — correct — but a *mixed* set of `{"caption", None}` also returns None, which is the conservative, correct behavior. However the test at 378-380 covers `{"slot": "-"}` but not a *missing* key. Whether cheap_checks' violations always carry `slot` is unverifiable from the diff. Conservative failure = the old redo path, so no ruling violation; noting only.

**N5 — the old redo path's change (nobody examined this).** Two behavior changes: (i) line 185: `if cheap and lone_slot(cheap) is None:` — a lone caption/title cheap failure now proceeds to paid gates instead of redoing immediately (this is the K1 reading, intended); (ii) lines 227-228: `_redo` instructions now include cheap violations, so a redo after a *mixed* failure tells the writer about the cheap rules too. Both are improvements and consistent with the ruling's principle; (ii) is an untested behavior (no test covers a redo whose instructions include cheap violations). P2, test-coverage gap.

**N6 — the budget fix is correct and minimal.** Line 176: `0 if med.get("replayed") or med.get("cached") else 1`. The Rig's `cached` flag (line 276, 400-403) exercises it. Matches the 12:00 note. One subtlety: `medley()` (line 10) reads `getattr(r, "cached", False)` — if the production Reply class lacks `.cached`, this silently reads False and a cached line-up counts against the budget (the pre-fix behavior). The diff doesn't show Reply gaining a `cached` attribute. **If Reply.cached doesn't exist, the budget fix is a no-op in production.** This is my strongest new finding: the diff adds the *read* but I cannot verify the *write* of that attribute anywhere. Flagging as P1-contingent: "verify Reply.cached exists; if it's set elsewhere in an unchanged file, downgrade to P2-verified."

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| lone_slot gating / ruling-65 path selection | 9/10 | 9/10 | Tests 375-384 cover the boundary; N4's missing-key case is conservative. |
| rewrite_alone (write, gates, fallback, hold) | 9/10 | 9/10 | Consensus refutations (R1-R3) held; the unreachable-state concern is closed. |
| merge_fid record integrity | 8/10 | 8/10 | G2/N1: ok-recompute and None-class are contingent, record-keeping only. |
| Fixed-caption format vs ruling (b) | 10/10 | 10/10 | Line 82 matches the ruling verbatim (title.lower() + "\n" + names " / ", cites all). |
| L-x (line writer's independence) | 9/10 | 10/10 | Grok's ordering note + lines 129-130 → 136: verified. |
| Budget (12:00) | 8/10 | 8/10 | N6: the read-side fix is right, but Reply.cached's existence is unverified in the diff. |
| Tests | 9/10 | 8/10 | N5: the modified old-redo instructions (line 227) have no coverage; otherwise 6 targeted tests are precise. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL** — none.

**P1 HIGH**
- **P1-1 (N6):** `pipeline/package.py:10` — `getattr(r, "cached", False)` silently defaults; if the production `Reply` never gains `cached`, the 12:00 budget fix never fires. **Condition to ship: confirm Reply.cached is set (or show the unchanged line where it is); otherwise the diff's budget clause is dead code.**

**P2 MEDIUM**
- **P2-1 (N3):** `package.py:37` vs `:62` — LINE_LIMIT prompt text and the hardcoded 220/70 enforcement can drift. Single-source it.
- **P2-2 (N1):** `package.py:97` — `merge_fid` seals `classes[slot] = None` when `one` lacks that slot's class; only the shipped fallback path is safe today.
- **P2-3 (G2/GLM):** `package.py:93,99` — `ok` recomputed from `violations` discards a stored `ok: False` with empty violations; contingent on VF's contract, unverifiable from the diff.
- **P2-4 (N2):** `package.py:152` — the title-hold's fid keeps the first run's `measured`/`backend` while the second write's provenance lives only in `rec`; provenance-reading hazard, gates correct.
- **P2-5 (N5):** `package.py:227-228` — the old redo's instructions now include cheap violations; behavior change with no test.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

Verify that `Reply.cached` actually exists and is populated — it is the only finding that could make a shipped clause (the 12:00 budget) silently do nothing in production.

## 7. PRODUCTION READY?

**Yes with conditions.**

1. **Reply.cached (P1-1):** show, in the diff or an unchanged file, that the production Reply carries `cached` (set on a live run served from its recorded reply). If it's already set elsewhere, this condition is discharged and I'd ship unconditionally.
2. Everything else (P2-1…P2-5) is record-keeping, drift-hazard, or test-coverage; none blocks the ruling's behavior. All six TestRuling65Caption cases, the ruling's (a)/(b)/(c) shapes, the fixed line's format, L-x, the lone-slot restriction, the title hold, and the budget's read-side logic check out from the diff.

**SHIP: yes with conditions** (the single condition above).