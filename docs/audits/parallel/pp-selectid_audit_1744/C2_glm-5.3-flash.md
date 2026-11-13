# glm-5.3-flash (z-ai/glm-5.3-flash) 126 s finish=stop usage in 22830 / out 2931 usd~0.112 (upper-bound price)

# pp-selectid-1744 — CYCLE 2 AUDIT (final)

## 1. WHAT DID THEY CATCH THAT I MISSED?

Honest accounting against my Cycle 1 output:

- **glm P1-2 (bare `lock_check` calls)** — I flagged the *shape* of the problem (an exception in `decide`/`send` escaping `check`) but did not trace it to the call sites in `package.build` and did not note that a crash loses the build record and the registry update. The consensus's fix (wrap → `LP.failed(e)` → same no-verdict shape → `lock_stop`) is the right one, and the mutation test (`test_a_pre_check_that_raises_is_no_verdict_never_a_crash`, both voiced and no-voice) is properly wired. I missed the call-site severity.
- **glm P1-3 / consensus C1-b (pin stage never compared the TEXT)** — I noted the asymmetry between `apply` (compares `approved_text`) and `pin_problems` (didn't) but undersold it: the concrete divergence vector is `SP.attribute_package` running *between* `build` and `pin_problems` (proof_ledger.py:404→406 region, now :422→:424). The fix — `apply` records the passed text in `pk["precheck"]["segments"][i]["text"]` (lock_precheck.py:220-223) and `pin_problems` compares `r.get("text") != s.get("text")` (:244) — closes it, and the test at test_medley.py:798-804 mutates the text after the lock passed and asserts the refusal. Verified real, verified fixed.
- **The no-voice `lock_stop` gap** — the consensus's C1-a note that the no-voice path previously did not set `lock_stop` (so later line-ups would each wait up to 1200 s) is a subtlety I did not raise. Now fixed at package.py:293-294 (`if nv_pre.get("error") or not nv_pre.get("segments"): out["lock_stop"] = ...`).

What nobody caught that I also didn't: see §3.

## 2. AGREE / DISAGREE

- **glm P1-1 (mixed-request answers in the reuse path)** — **partially agree, downgrade to P2.** The reuse path `got = [answer(s, results_dir) for s in req]` (lock_precheck.py:162) indeed ignores `request_id`, so segments can come from different requests. But: (a) the contract's results are keyed per segment-window file, and the match requires window+role+approved_text+trim to equal the *current* request's — so a reused answer judged the same words on the same window; (b) the consensus's refutation (one clip per channel per L-y medley; a wider window never matches → error → fail closed) is sound. Residual risk is only if the integrator's answers are line-up-scoped despite the per-segment result files. The docstring at :158-160 now says "An answer already on file is used (never an error)" and the test at :573-579 pins it — the behavior is documented and intentional. Agree it's worth the integrator's confirmation; not a ship blocker.
- **glm's refuted items** — agree with the refutations. The request-id collision argument (build dir created with `os.makedirs` without `exist_ok`, driver refuses an existing one; `n` increments in-process) holds; the ID_RE check at :115-116 plus the driver's `ledger_YYYYMMDD_HHMMSS` basename keeps ids within `[A-Za-z0-9_.:~-]`.
- **grok's all-clear** — agree; its four verified checks (build+apply+pin_problems gating; adopt only via this side's carry_class; error→ok=False→lock_stop; matching fields) are exactly the ones I'd want verified, and I re-verified them independently below.
- **qwen's P2s** — agree they're verifications, not findings. Its note on `_matches` rounding (both sides rounded to 3dp, :88, :91) and `os.rename` atomicity (:124) are correct.

## 3. NEW FINDINGS (this cycle)

**N1 (P2) — `check()`'s reuse-vs-ask condition can send a request whose answers are already all on file as *holds*.** lock_precheck.py:164: `if any(e is None or e.get("outcome") not in PASS | {"adopt_spoken", "hold"} for e in got)`. If every segment's newest ruling-72 entry is a `hold`, no request is sent (`sent = None`, returned at :182) — correct and cheap. But if the newest entry is an *error* outcome, the condition triggers, a request is sent, and the wait loop (:170) filters by `request_id` — while the *reused* segments' answers (the ones not re-answered) keep their old, non-`request_id` entries. That's the documented design (the erroring segment is re-asked; the passing ones are not), and the test at :581-593 pins exactly this. Not a defect — but note the returned `request_id` (:182, `sent`) is then the id of a request that only *part* of the line-up answered, while `rows`' `entry.request_id` fields (via :178) will show the old ids for the reused segments. Anyone debugging the ledger sees a mixed-provenance line-up under one request id. Cosmetic/traceability only.

**N2 (P2) — `apply()`'s `hook_first_words` is recomputed, not verified.** lock_precheck.py:219: `pk["hook_first_words"] = " ".join(segs[0]["text"].split()[:8])` — comment "as package._package derives it". If `package._package`'s derivation ever differs (e.g. punctuation stripping, a different normalization), `apply` silently *overwrites* the package's value rather than confirming it. For an adopted hook, the overwrite is required (the words follow the spoken text); for a non-adopted hook it masks any divergence between the two derivations. The test at :629 pins the adopted case only. Low risk, but the invariant "hook_first_words follows the sealed hook text" is now enforced in two places that could drift.

**N3 (P2) — `pin_problems` trusts `precheck` written by `apply`, which trusts `pre` — but the no-voice path's `nv_pre` and the voiced path's `pre` are the only producers, and both are wrapped.** Verified: every producer of `pk["precheck"]` is `LP.apply` (package.py:303-308, :356-362), both inside `try/except Exception` → no pin on failure; `pin_problems` itself re-checks `ok is not True` and per-segment verdict+text+coords (:238-245). The chain is closed. No finding — stated because it's the question the prompt asks and nobody wrote the closure down.

**N4 (P2) — `attested()`'s "carried" claim is a constant string, not a verified fact.** lock_precheck.py:189-191: `"carried": "every verdict and gate of this line-up, judged on the text it replaces: ..."` — the *record* asserts the verdicts carried; the code's actual guarantee is that `apply` re-derives nothing (it seals `spoken_text` because `decide` said the differences are in-class). That matches ruling 67's "verdicts carry over" semantics (the gates were judged on the approved text and the differences are only function words/repetitions), so the wording is defensible — but it is a sealed field whose content is a prose promise. If a future ruling changes what "carried" means, this string goes stale inside a sealed pin. Documentation-adjacent; no action required for this ship.

**N5 (P2, uncertain) — `decide()`'s `AT.diff`/`AT.carry_class` calls are inside `check`, which the build now wraps** (package.py:328-331, :357-361) — so glm's original P1-2 residual (an unexpected spoken_text shape raising inside attest) is now *contained* at the build level: it becomes `LP.failed(e)` → no verdict → `lock_stop`. But in the **no-voice** path, `LP.apply`'s `quoting_lines` (lock_precheck.py:196-197, called at :215) also calls `AT.diff` — wrapped at package.py:306-308, fine. And the driver's `pin_problems` call (proof_ledger.py:424) does *not* call attest. So: every attest call site is either wrapped or absent. Closed. (I'm noting it because glm's P1-2 named `AT.diff` specifically, and the fix's coverage of *that* specific vector — vs. only the `send` OSError — deserves an explicit yes: yes, both, via the same wrap.)

**N6 (P2) — the two stop guards.** package.py:317-318 (inner `while` condition) and :379 (angle-loop `break`) — the change notes say they fail only together, by design. Verified both present; either alone suffices as claimed (the inner condition prevents the next line-up; the break prevents the next angle). Redundancy, not a defect.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| Matching/contract (answer, _matches, result_file) | pass | pass | unchanged; rounding + trim + rules filtering verified again (:85-92, :47) |
| Request writing (send, ids) | pass | pass | unchanged; atomic, never overwritten, ID_RE enforced (:112-125) |
| decide / ruling-67 veto | pass | pass | unchanged; this-side carry_class veto, hold on disagreement (:143-153); attest call sites now all wrapped (N5) |
| Build wiring (gates, hold→reline, error→stop) | pass | pass | C1-a fix verified; both stop guards present; no-voice path now stops on no-verdict |
| apply / attested record / pin stage | pass | pass | C1-b fix verified; text compared at pin stage (:244); test mutates text post-lock and fails without it |
| Tests | pass | pass | 12 + 4, mutation-backed; the two-guard design documented |
| Traceability of mixed-provenance reuse | — | pass w/ note | N1: cosmetic, documented behavior, pinned by test |

Nothing changed my overall assessment: no P0, no P1.

## 5. FINAL PRIORITY LIST

**P0 CRITICAL** — none.

**P1 HIGH** — none.

**P2 MEDIUM**
1. **N1** — lock_precheck.py:162-166, :182: reused answers keep their original `request_id` while the returned `request_id` is the new one; the ledger's `entry.request_id` fields will show mixed provenance under one id. Add a one-line note to the docstring, or include the reused entries' ids in the returned rows' `entry` (they already are, via :178) — just document it.
2. **N2** — lock_precheck.py:219: `hook_first_words` overwritten, not cross-checked against `package._package`'s derivation for the non-adopted case. Add an assertion-style comparison or a comment naming the second derivation site.
3. **glm P1-1 (downgraded)** — lock_precheck.py:162: reuse path ignores `request_id`; confirm with the integrator that answers are per-segment, not line-up-scoped. The per-segment result files strongly suggest they are.
4. **N4** — lock_precheck.py:189-191: the "carried" prose in a sealed field; keep it in sync with any future ruling-67 change.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

Confirm with the integrator, in writing, that ruling-72 answers are keyed per segment (window+role+text+trim) and not per line-up request — it is the only assumption in the reuse path (lock_precheck.py:162) that the diff cannot verify and that would silently change a sealed text if wrong.

## 7. PRODUCTION READY?

**Yes.**

Conditions (none blocking; all P2):
1. Integrator confirms per-segment answer semantics (N1 / glm P1-1 residual).
2. The `hook_first_words` dual-derivation sites are cross-referenced in comments so they drift together (N2).
3. The "carried" prose in `attested()` is reviewed whenever ruling 67 changes (N4).

Both Cycle 1 fixes (C1-a: wrapped `lock_check`/`LP.apply` → no-verdict, never a crash; C1-b: the pin stage compares the text the lock passed) are verified in the diff, mutation-tested, and correctly fail closed. `seal()` and every other gate are untouched; `to_pin` only adds the already-sealed `attested` field. Ship it.