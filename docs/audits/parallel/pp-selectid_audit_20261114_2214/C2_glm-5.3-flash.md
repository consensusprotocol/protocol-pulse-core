# glm-5.3-flash (z-ai/glm-5.3-flash) 71 s finish=stop usage in 6795 / out 2388 usd_reported=0.000507 usd~0.056 (upper-bound price)

# CYCLE 2 AUDIT — pp-selectid (RULING 109, free gates first in spotlight.build)

## 1. WHAT DID THEY CATCH THAT I MISSED?

Being honest against my own Cycle 1 output:

- **Grok's P2 on output-shape consumers (release_auth / ATTESTATION / telegram).** I checked that the pin's gate rows were unchanged but did not systematically trace *every* consumer of `build()`'s output dict. Grok's framing — "any divergence from 'every REQUIRED gate ran, on exactly the bytes that are sent' is a release-authorisation hazard" — is the right discipline, and I under-argued it. The consensus later resolved it (build() output is the builder's record; release_auth reads the pin, not this dict), but the *question* was Grok's, not mine.
- **Grok's P3 on the cost-audit-pack section 10 not being in the review package.** I took "no sealed pin lost" on faith from the replay note. Grok correctly flagged that it's unverifiable from what we were given. That's a process catch, not a code catch, but it's real.
- **GLM's observation that `alone_score(m)` is called twice per moment in the dict comprehension** (once in the condition, once as the value). Trivial, but I didn't note it. It's also *load-bearing* in one subtle way: if `alone_score` were ever non-deterministic or expensive, the double call would matter — see new finding N3 below.
- **Qwen's "Potential Issue 1: stop side effects"** — whether `stop()` mutates in place or only records. I assumed the standard pattern; Qwen at least asked. The removal from `ms` makes it safe either way, but the question was sharper than anything I raised.

What nobody missed, credit where due: the consensus's refutation of the shared P1 (text-mutation-after-early-check) is thorough and correct — snapping happens in `pool()` at spotlight.py:832, *before* `with_verdict`, there is no `m["text"] =` anywhere in spotlight.py, and a trimmed opener is its own moment with its own score. I adopt that refutation.

## 2. WHERE DO I AGREE OR DISAGREE?

| Finding | Source | Verdict | Why |
|---|---|---|---|
| Early stop can drop a moment that could still seal (text changes after check) | GLM P1(a), Grok P1 | **Disagree — refuted** | Snapping is stage 1 (`pool()`, line 832), before `with_verdict` at line 8 of the diff. No later stage assigns `m["text"]`. A "~trim" is a separate moment with its own verdict. Stage 7 re-attaches verdicts for the *same* text under the *same* scorer sha, so a known-low score is exactly what stage 7 would refuse. The consensus refutation stands; the diff's "UNCHANGED GUARDS" note is accurate, not merely an assertion. |
| `alone_score` None vs. verdict-present-but-unrated; string rating → TypeError | GLM P1(b)/P2 | **Partially agree** | Under L-l, `_v_rate` guarantees a 1–5 number, so the invariant holds upstream. But "covered upstream, untested here" is a fair criticism — the diff relies on an invariant it doesn't pin. Downgrade to P2/P3: it's a test-coverage gap, not a defect. |
| New `out["ruling_109"]` key / changed reason strings vs. downstream consumers | Grok P2 | **Disagree (resolved)** | `build()`'s output is the builder's record; release_auth and the pin read the pin's gate rows, which are unchanged. The changed reason strings are exactly what the two updated tests now expect. No hazard. |
| No regression test for low-then-high score within a build | Grok P2, GLM | **Disagree (resolved)** | The case cannot arise within a build — verdicts are fixed per (text, scorer sha) and nothing mutates the text. It *could* arise across builds, and there the next build re-reads the scorer. Nothing to test. |
| Reclassified failure reason touches L-c/L-g/L-k | Grok P3 | **Disagree** | The reason string is the builder's narration, not a gate verdict. The gates themselves (ALONE ≥ 4) are unchanged; only *when* they fire moved earlier. |
| Test-name nit, comment style | Grok P3 | **Agree (trivial)** | Not worth churn. |
| Cost-audit-pack section 10 not provided | Grok P3 | **Agree** | Process gap in the review package, not the code. |

## 3. NEW FINDINGS FROM THIS REVIEW

**[P2] N1 — The early-return path skips `out["scorer"]`-adjacent bookkeeping symmetry: nothing, but the early return also skips `P._writers(router)` (line 17).** Verified: `P._writers` only opens writers for the paid stages; if `ms` is empty there is nothing to write, and the existing test (line 58–60) asserts no `prescreen` call and a `why_none`. However, if any *later* code assumes `out` always carries writer-attached records (e.g., a "writers were opened" invariant), the all-low path diverges. Nobody tested that the all-low build produces a *well-formed* `out` beyond `why_none` + `ruling_109` — specifically, that `out["moments"]` still contains the stopped moments' records. The test at line 56 checks `out["moments"]["a"]["out"]` only in the *mixed* case. Add one assertion in the all-low case: `self.assertIn("a", out["moments"])`. Cheap, pins the `stop()`-before-`return` ordering.

**[P3] N2 — `out["ruling_109"]` counts but does not list.** `{"alone_known_below_min": 1}` tells you *how many*, not *which*. For a cost-audit replay (section 10, which Grok correctly noted we can't see), the moment IDs are what an auditor reconciles against the scorer's verdicts. The per-moment reasons exist in `out["moments"][mid]["out"]`, so this is derivable — but a `sorted(low)` alongside the count would make the record self-contained. Should-fix, not must.

**[P3] N3 — The double `alone_score(m)` call in the comprehension (line 9) is correct today only because `alone_score` is a pure read of `P.verdict_of`.** If it ever gains a side effect or a cache miss cost, the condition-then-value pattern silently doubles it. One-line fix: `low = {m["moment_id"]: sc for m in ms if (sc := alone_score(m)) is not None and sc < ALONE_MIN}`. Nit today, insurance tomorrow.

**[P3] N4 — The walrus/3.8-compat note.** If this codebase targets Python < 3.8, the `:=` suggestion in N3 doesn't apply; the existing double-call form is then the *portable* one. Nobody flagged the version constraint because the diff doesn't state it. Informational only.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| Early-stop logic (spotlight.py:9–16) | Pass, minor doubt on text-mutation | **Pass, doubt resolved** | The consensus refutation (snap precedes the check; no text mutation; verdicts keyed by text+scorer sha) is code-cited and conclusive. |
| Test coverage | Adequate | **Adequate, one gap** | New: the all-low path never asserts the stopped moment's record survives in `out["moments"]` (N1). |
| Output-contract / downstream consumers | Untested assumption | **Pass** | Grok's question, consensus's answer: pin is the contract, and it's unchanged. |
| Reason-string / narration changes | — | **Pass** | Two existing tests updated; narration only, no gate semantics. |

## 5. FINAL PRIORITY LIST

- **[P0] CRITICAL** — none.
- **[P1] HIGH** — none. (The Cycle 1 shared P1 is refuted; I adopt the refutation with the code citations: snap at spotlight.py:832 precedes `with_verdict`; no `m["text"] =` in the file; "~trim" is its own moment; stage 7 re-attaches the same verdict.)
- **[P2] N1** — tests/package/test_spotlight.py, new test (diff line 58–60): in the all-low case, assert the stopped moment's record still exists, e.g. `self.assertIn("a", out["moments"])` (and optionally its "ruling 109" reason). Pins that `stop()` runs before the early `return` and that the record survives it.
- **[P2] N2** — pipeline/spotlight.py, diff line 13: consider `out["ruling_109"] = {"alone_known_below_min": len(low), "moment_ids": sorted(low)}` so the cost-audit replay can reconcile without joining against `out["moments"]`.
- **[P3] N3** — pipeline/spotlight.py, diff line 9: single-evaluation via walrus (or a plain loop) if the Python floor allows; otherwise leave as-is.
- **[P3] Grok's process note** — attach cost-audit-pack section 10 to the review package next cycle so "no sealed pin lost" is independently checkable.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

Add the one-line assertion to the all-low test — `self.assertIn("a", out["moments"])` — because it is the only untested invariant separating "we stopped it and recorded it" from "we stopped it and lost it," and it costs nothing.

## 7. PRODUCTION READY?

**Yes, with one condition.** The logic is correct: the early stop refuses only what stage 7 (ALONE ≥ 4 on the same text, same scorer sha) would refuse, unscored moments pass untouched, the all-low path makes no paid call, and the mutations (3/3: no-free-gate-first, unscored-stopped, exactly-4.0-stopped) kill the failure modes that matter. **Condition:** land the N1 assertion (all-low case retains the stopped moment's record in `out["moments"]`) — it is the only behavioral guarantee currently resting on the `stop()` implementation rather than a test. N2/N3 are should-fix, not blockers.

P1_OR_WORSE: 0