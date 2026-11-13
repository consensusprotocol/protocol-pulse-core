# glm-5.3-flash (z-ai/glm-5.3-flash) 123 s finish=stop usage in 14085 / out 3170 usd~0.090 (upper-bound price)

# pp-selectid-0640 — CYCLE 2 REVIEW (final)

## 1. What the other models caught that I missed

Honest accounting against my Cycle 1 output:

- **qwen P1-1 (exception in `f.result()` kills the build)** — I did not flag this. It was the single most important finding of Cycle 1, and the fix (the `one()` wrapper, diff lines 25–30) is the right shape: a raising chunk returns `STEP_A_UNAVAILABLE` for each of its clips, never a pass, never a crash. Tested at test_medley.py:297–312. I missed it because I focused on the verdict-selection logic and treated the parallelism as plumbing.
- **glm's PRESCREEN_N coupling (glm P1-1/K2)** — I noted the `n=len(chunk)` change but did not trace the interaction with the first screen's cap. The consensus's K2 rebuttal is correct and I can now verify it from the diff: `cleared` is built from `a_by` (build() only keeps moments the first screen answered and passed — the hunk at diff line 58 runs after the first screen, and `second_screen` itself reads `a_by.get(mid)` with a `None`-group fallback at lines 21–22, 45–47), and `n=len(chunk)` at line 27 means nothing in a chunk is truncated. So a clip beyond a cap cannot reach `second_screen` without a first verdict. I under-verified this; the consensus's reasoning is sound.
- **glm's "off_writers picks the first qualifying verdict, not the latest"** — I agree with glm's own self-correction: the `or a_by[mid]` fallback at line 87 (and 96) is transient; the `stale` computation at lines 97–98 uses the *current* `writers_v`/`writers_f` and re-screens anything still on a writer. The fallback never gates a line-up.

## 2. Agree / disagree on their key findings

| Finding | Verdict | Why |
|---|---|---|
| qwen P1-1 (exception → crash) | **Agree, now fixed** | `one()` catches `Exception` (not `BaseException` — fine; KeyboardInterrupt should propagate), returns fail-closed reasons. `ex.map` collects results; a raise inside `one` is impossible by construction. |
| qwen P1-2 (`a_by[mid]` KeyError) | **Agree with consensus: non-defect** | Line 21 uses `a_by.get(mid)`; only clips in a non-None group reach line 44, and they got there because `a_by.get(mid)` was truthy. Also `cleared` ⊆ `a_by` keys by construction in build(). |
| qwen P1-4 (verdict added to `a_two` may later be "on" a writer) | **Agree, correctly handled** | `off_writers` re-checks against the *current* `writers_v`/`writers_f` every time (lines 81–84), and the `stale` test at 97–98 uses the same current sets. A verdict that ages into "on a writer" is re-screened, not trusted. |
| glm P1-1 (PRESCREEN_N cap) | **Agree with K2: non-defect** | Verified above: `n=len(chunk)` + `cleared ⊆ a_by` closes it. |
| glm P2-3 / K3 (both vendors writing → no back-end left, swap loop) | **Agree with the consensus's two-part answer** | (a) `writer_avoid` (lines 88–89) subtracts the angle's vendor from the angle_write chain's vendors, so with the real chains the writers stay one vendor — now asserted (test line 257: `rig.write_avoid == [{"heimdall"}]`). (b) Even if both write, the loop is bounded: `dropped | doomed` grows monotonically, `swap_lineup` excludes them, and the search budget + `total < lineups` cap iterations. No infinite loop. |
| grok's blanket "no P0, no P1, SHIP: yes" | **Agree, but it's a shallow pass** | Grok's findings are accurate as far as they go (I verified each cited line), but they read as confirmation, not audit. Its claim at "pipeline/package.py:34" that fail-closed paths "never become passes" is right, but it never asked the question qwen did about `f.result()`. |

## 3. New findings from this review (Cycle 2)

**N1 (P2) — `second_screen`'s parallel groups can double-charge spend accounting, and nothing in the diff records it.** `out["prescreen"]["second_vendor"]` (diff lines 59–61) records PASS/FAIL per clip, but the *spend* of the second screen — one extra Heimdall call per (vendor, family) group, potentially several batches — is not added anywhere visible in the diff. If `out["spend"]` or the attestation's cost trail is accumulated inside `prescreen` via `store=None`... note `store=None` at line 27: the second screen's calls bypass whatever spend ledger `store` normally feeds. The first screen's call site isn't in the diff, so I cannot verify whether the first screen also passes `store=None` or whether spend is summed elsewhere. **Flag, not a defect:** if spend is tracked via `store`, the second screen's cost is invisible. Order 06:22 calls it "cheap" — but cheap must still be *counted*. Verify before ship.

**N2 (P2) — `off_writers` returns the *first* qualifying verdict, which after a re-screen may not be the freshest, and `a_two` grows without bound per clip.** Line 113 appends every successful re-screen verdict to `a_two[mid]`. `off_writers` (line 81) iterates `a_two.get(mid, ())` in insertion order: first verdict, then second, then re-screen results. If the *first* verdict's back-end is still off the writers after a write (possible when the write's vendor/family differs from both verdict vendors — only the rig's third-vendor case), `off_writers` returns the *original* first verdict, not the re-screened one. That's actually correct (any off-writer verdict satisfies L-x), but it means the re-screen's fresher verdict is appended to `a_two` yet never *selected* while an older one qualifies. Harmless for correctness; worth a comment. Also: `a_two` accumulates across the whole build; with many writes and many re-screens it grows, but bounded by (clips × writes), negligible.

**N3 (P2) — the `None`-group clips' failure is recorded AFTER the parallel phase, correctly, but their reason string hardcodes "the first verdict's back-end is unknown" — if the cause was a cap truncation (glm's scenario), the reason misleads.** With K2 verified, this can't happen via PRESCREEN_N, but it *can* happen if `router.backends` lacks the first verdict's backend key (a renamed/retired back-end in the router config while old verdicts persist in a store). The reason should ideally include the missing key. Cosmetic.

**N4 (P2) — `max_workers=max(1, len(jobs))`** (line 31): with many groups this spawns one thread per group. Groups are keyed by (vendor, family) of the first verdict; with only two real vendors there are at most 2–3 groups, so this is fine. But if the context_verdict chain ever grows, `len(jobs)` counts *batches*, not groups — wait, no: `jobs` is (key, chunk) pairs, so `max_workers` = number of batches, not groups. With 10–13 clips and PRESCREEN_BATCH=8, that's 2–4 threads. Fine. No finding; noting I checked.

**N5 (P2) — test line 325: `name = "heimdall:deepseek" if "xai" in wv else "heimdall:deepseek"`** — both branches are identical. The test's intent (z's second verdict comes from the *same vendor* heimdall, exercising STEP_A_SAME_VENDOR) works, but the ternary is dead. Cosmetic; suggests the author meant the second branch to differ and the SAME_VENDOR path is exercised only accidentally-by-construction (z's first verdict is heimdall:deepseek, its second is also heimdall:deepseek → caught at line 40). It does exercise the check, so the test is valid, just written confusingly.

**N6 — behaviour change for the Heimdall-in-time case: YES, and it's the intended one, but one subtle difference.** Before: step A ran once, on xai (off the expected Heimdall writer). After: every cuttable clip is screened twice (xai AND heimdall) before the angle. If the angle comes from Heimdall in time (the common path), the gates now use the *xai* verdict via `off_writers` (line 87) — same vendor as before, so the gates' inputs are unchanged. But `a_by[mid]` is *replaced* at line 87 with `off_writers(mid) or a_by[mid]`; if `off_writers` returns None (both verdicts on a writer — impossible here since the two verdicts are on different vendors and the writer is one of them... actually: verdicts are xai+heimdall, writer is heimdall → xai verdict qualifies, returns it. Writer is xai → heimdall verdict qualifies. So `off_writers` never returns None after a successful second screen). Verified: no behaviour change for the gates' verdict *vendor*; the only change is the extra pre-angle cost and the `second_vendor` log. **One residual:** if the second screen *fails* a clip that the first screen passed (e.g. Heimdall disagrees), that clip now drops BEFORE the angle — previously it would have reached the angle prompt and only failed later. This shrinks the angle prompt's clip pool. That's the point of item 45, but it means the angle model sees fewer clips than before in disagreement cases. Intended; noting it.

## 4. Revised scores

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| second_screen correctness (L-m fail-closed) | 9/10 | 9.5/10 | The `one()` exception wrapper (qwen's catch, now fixed+tested) closes the only crash path I could construct. |
| Threading | 8/10 | 9/10 | `ex.map` preserves (jobs, results) zip ordering; no shared mutable state inside workers; `one()` catches Exception. Only residual: spend-visibility via `store=None` (N1). |
| off_writers / L-x after writes | 8.5/10 | 9/10 |glm's transient-inconsistency worry is real but self-healing via the `stale` check; the rig's third-vendor test exercises the both-writers case. |
| Item 44 swap/re-line | 9/10 | 9.5/10 | Fail-open K2 fixed and tested both ways (swap fits / no swap fits); `dropped | doomed` monotone; no loop. |
| Tests | 8.5/10 | 9/10 | 6 new tests, all targeted at the orders; the dead ternary (N5) and the third-vendor-only coverage of item 44's mechanics are the only gaps. |
| Spend/observability | — | 7.5/10 | New subscore: `store=None` on the second screen's calls may hide its cost (N1). |

## 5. Final priority list

**P0 CRITICAL** — none.

**P1 HIGH**
- **P1-1 (N1):** `pipeline/package.py` diff line 27 — `second_screen` calls `prescreen(..., store=None)`. If spend/cost accounting flows through `store`, the second screen's calls (2+ Heimdall calls per build, ~3 min each) are invisible to the spend trail. Verify how the first screen records spend and mirror it (or confirm spend is summed elsewhere). Condition for ship.

**P2 MEDIUM**
- **P2-1 (N3):** diff lines 45–47 — the STEP_A_UNKNOWN_BACKEND reason should include the missing backend key, so a retired/renamed back-end in `router.backends` is diagnosable from the 06:22 trail.
- **P2-2 (N5):** test_medley.py:325 — dead ternary (`"heimdall:deepseek" if "xai" in wv else "heimdall:deepseek"`); simplify or make the branches actually differ.
- **P2-3 (N2):** diff lines 81–84 — add a comment that `off_writers` intentionally returns the *first* qualifying verdict (order of `a_two`), so a future reader doesn't "fix" it to the last.

## 6. The single highest-leverage change

Make the second screen's spend visible: confirm (or fix) that the `store=None` prescreen calls in `second_screen` still land in the cost/attestation trail — it's the only thing in this diff whose absence would surprise the 06:22 post-mortem.

## 7. Production ready?

**Yes with conditions.**

1. **Spend visibility (P1-1):** confirm the second screen's prescreen calls are counted in the spend/attestation trail despite `store=None` (or pass the store / add the calls' cost to `out`).
2. Everything else (P2-1..3) is polish; ship without them if needed.

Rationale: no P0. Both orders (44, 45) are implemented, fail-closed (L-m) and vendor-separated (L-x) at every path I can trace, the two Cycle 1 P1s (qwen's crash, glm's cap coupling) are fixed or disproven with tests, the both-writers case is bounded and now asserted, and the Heimdall-in-time behaviour change is exactly the intended one (a second, cheaper-to-fail verdict before the angle) with no change to which verdict the gates see.