# glm-5.3-flash (z-ai/glm-5.3-flash) 283 s finish=stop usage in 8102 / out 8050 usd~0.145 (upper-bound price)

# Audit: pp-selectid-0352 — ad-read screen moved before the angle; why_none naming

## What I can verify from the diff

The diff is 161 lines: `moments.py` extracts the deterministic ad-read screen into `ad_read_marker()`; `package.py` adds `ad_read_out()` + a filter in `build()` + a `why_none` fallback; `test_medley.py` adds `TestAdReadBeforeTheAngle` (4 tests) and one assertion to an existing test. I have no access to the surrounding files, so everything below is what the diff itself shows, plus what it implies about the referenced helpers (`AD_MARKERS`, `CI.context_around`, `exclusion_for`, `src_of`, `pm`, `Rig`) — flagged as assumptions where I cannot see them.

---

## P0 findings

None. I found no defect in the diff that breaks the stated behavior on the paths the tests exercise.

---

## P1 findings

**P1-1 — `ad_read_out` can refuse a moment the package stage would NOT refuse, if `context_around` returns `""` (empty string) vs `None` differently than assumed.**
`package.py:55-58` (diff lines 55–58): `why = M.ad_read_marker(m["text"], before) if before is not None else None`. The skip condition is `before is not None`. But `ad_read_marker` treats `before_text=""` and `None` identically (`last_before = ""`), and the docstring of `ad_read_out` says a moment with "no context" is left to the package stage. If `CI.context_around` signals "no context" with `""` rather than `None` (I cannot see its contract in the diff), the moment is screened here on an empty before-text — which is exactly what `exclusion_verdict` would do anyway (`exclusion_verdict` also receives `before_text=""`-ish), so the *verdict* still matches. The residual risk is only that the "left to the package stage" claim in the docstring/test comment is inaccurate, and the moment is excluded earlier than documented while the package stage would have produced the same exclusion with its own reason string. **Scenario:** `context_around` returns `("", "after")` for a source whose head is the moment; `ad_read_out` refuses it on a marker in the moment text; the package stage would have refused it too, so behavior is equal — but if `context_around`'s "no context" sentinel is `""`, the test `test_ad_read_out_reads_the_same_context_as_the_exclusion_screen`'s `("c": (None, None))` case does not cover it. Not a behavior divergence, a documentation/coverage gap. Severity: P1 (not P0) because the verdicts coincide either way — the marker search on `""` finds nothing, so the only divergence would be a marker in the *moment text* with an empty before-context, which both stages refuse identically.

Wait — re-examine: if `before=""` and the marker is in the moment text, `ad_read_out` refuses here; the package stage's `exclusion_for` would also refuse (same marker in the moment). Equal. If `before=""` and no marker, neither refuses. Equal. So the only true divergence risk is if `context_around`'s no-context sentinel is neither `None` nor `""` — unverifiable from the diff. Downgrade: **P1-1 is really a coverage note, not a defect.** Keep as P1 only because the "same context" claim rests on an unseen contract.

**P1-2 — `why_none` fallback can overwrite nothing but can also be *set* when a later path would have set a more specific reason — ordering.**
`package.py:94-97` (diff lines 94–97): the fallback runs only `if out["package"] is None and not out.get("why_none")`. That correctly defers to any earlier-set reason (e.g. the `<3 channels` early return at diff line 87–89, which returns before this code — actually that path `return out` at line 89, so the fallback never runs on it; good). But I cannot see, from the diff, whether any *other* code path between line 93 and 98 (the angle loop, `over_budget`, `budget_stop`) sets `why_none` — the diff shows only the added lines. If some path inside the angle loop sets `why_none` and then a package IS found... no, the fallback is guarded by `out["package"] is None`. If a path sets `why_none` AND leaves package None, the fallback respects it (`not out.get("why_none")`). So the guard is correct as far as the diff shows. The remaining question: does the angle loop's failure path set `tried[i]["why"]` for *every* failure mode, including "line-ups formed but every write/gate failed"? If a tried angle's `why` key is absent (`t.get('why')` → None), the message reads `angle 1: None`. **Scenario:** an angle whose line-up failed at the write/gate stage records `{"angle": 1}` with no `why` key → `why_none` = "no angle gave a package: angle 1: None". Cosmetic, not a hidden reason. P1→P2. I'll list it as P2-1.

**P1-3 — the 900-char truncation can cut mid-escape.** `[:900]` truncates the joined string; if it cuts inside an angle's why, the last angle's reason is silently clipped. That's the documented intent ("names every tried angle's own why" — it may not, if >900 chars). With up to 3 angles this is unlikely to exceed 900 chars, but the truncation is applied to the *whole* message including the "no angle gave a package: " prefix. Minor. P2.

**P1-4 — `ad_read_out`'s KeyError catch is broader than "no Source".**
`package.py:54-57`: `try: before, _ = CI.context_around(src_of(m, sources), m["sentences"][0], m["sentences"][1], *m["words"]) except KeyError: continue`. The `try` wraps the *entire* expression, including `m["sentences"]`, `m["words"]`, and anything `context_around` itself raises KeyError from *inside* (e.g. a missing word key in the source's word list). So a moment with a Source but a malformed `sentences`/`words` field, or a word missing inside `context_around`, is silently skipped here — which is fail-closed (the package stage still screens it), so no wrong pass. But the docstring says only "no Source" is skipped; the code skips on any KeyError. Fail-closed, so P2, but the docstring/test comment ("d has no Source: left to the package") documents a narrower cause than the code implements. Also note: `src_of(m, sources)` — I cannot see `src_of`; if it raises something other than KeyError for a missing source (e.g. returns None and `context_around(None, ...)` raises AttributeError), the moment would crash `build()` rather than be skipped. Unverifiable from the diff; the test's `d` case (no Source) exercises the KeyError path, so presumably `src_of` raises KeyError — but the test's `sources` dict is `{"va": "a", ...}` and moments reference sources by... I can't see `src_of`'s lookup. If `src_of` does `sources[m["source_key"]]`-style, moment "d" (built by `pm("d", ...)` with no source key) raising KeyError is consistent. Flag as assumption.

**P1-5 — the `out["ad_read"]` moments are removed from `ms` BEFORE `prescreen` (step A), which changes what step A measures — is `out["usable"]` really unchanged?**
Diff line 68: `n_usable = len(ms)` is captured *before* the no_role filter (existing behavior — the comment says "out['usable'] keeps its meaning (audit 0310 C1, glm P2-2)"), and the new ad_read filter at diff lines 71–72 removes more moments from `ms` afterward. `n_usable` is still the pre-filter count, so `out["usable"]` is unchanged. ✔. But the *log line* now reports `len(ad_read)` moments "on an ad-read marker" — and the no_role filter already removed some; a moment could be in neither. Fine. However: the ad_read filter runs on `ms` AFTER no_role removal, so a moment removed by no_role never gets an ad_read record — its ad-read-ness is never recorded in `out["ad_read"]`. Is that a defect? The package stage previously would have... no: no_role-removed moments never reach the package stage either (they're removed before). So the exclusion screen at the package stage never saw them either. Consistent. ✔. But note the *order*: previously, the exclusion screen (inside the per-clip gates, after the angle) ran on moments that had already passed no_role; now the deterministic part runs on the same surviving set. Same set, same verdicts. ✔.

**P1-6 — the model verdict at the package stage: unchanged?**
`exclusion_verdict` now calls `ad_read_marker` and, if it returns a reason, returns the same record as before (diff lines 31–34 vs the removed 26–30). Comparing the removed lines 26–30 with the new 31–34: the removed code returned `{"verdict": "exclude", "why": f"ad-read marker '{...}' in {where}", "risks": ["ad_read"], "backend": "deterministic", "me equivalence...` — the new code returns the identical dict literal. ✔ Byte-identical record. The model call after it (`router.call("exclusion_verdict", ...)`) is untouched (diff lines 35–37 show it unchanged in context). ✔.

**P1-7 — `ad_read_marker`'s double `AD_MARKERS.search` call.** Diff lines 14–15: `if AD_MARKERS.search(txt): return f"ad-read marker '{AD_MARKERS.search(txt).group(0)}'` — the regex runs twice per text. Purely a performance nit (a compiled-regex search on a sentence), not a defect. P2.

**P1-8 — `ad_read_marker`'s sentence-splitting of `before_text` matches `exclusion_verdict`'s old behavior exactly?** The removed lines 26–27 and the new line 12 are the same expression, moved verbatim. ✔. And `ad_read_out` passes `before` — the *full* context-before string from `context_around` — as `before_text`, while `exclusion_for` at the package stage passes... I cannot see `exclusion_for` in the diff. The claim "the SAME context exclusion_for reads (CI.context_around on the moment's Source, by source_key else video_id)" is asserted in the change description but the diff does not show `exclusion_for`'s call. If `exclusion_for` passes a *truncated* before-text (e.g. `quote_data(before, 3000)` — note `EXCLUSION_PROMPT.format(before=quote_data(before_text, 3000), ...)` at diff line 37 truncates for the *prompt*, but the deterministic screen in `exclusion_verdict` runs on the *untruncated* `before_text` parameter), then `ad_read_out`'s use of the raw `before` matches the deterministic screen's input. ✔ as far as visible: `exclusion_verdict`'s deterministic part runs on the raw `before_text` (diff line 31: `why = ad_read_marker(moment_text, before_text)` — wait, the signature is `exclusion_verdict(router, moment_text, before_text="", after_text="", ...)` and the deterministic screen uses `moment_text` and `before_text` raw, before any `quote_data` truncation). So the question reduces to: does `exclusion_for` pass the same raw `before` string that `ad_read_out` computes via `CI.context_around(...)`? The change description says yes; the diff cannot prove it. **This is the single most important unverifiable assumption in the diff** — the "refuses exactly what the package stage refuses, nothing more" guarantee rests entirely on `ad_read_out`'s context computation being byte-identical to `exclusion_for`'s. The test `test_ad_read_out_reads_the_same_context_as_the_exclusion_screen` (diff lines 131–142) monkeypatches `CI.context_around` and checks `ad_read_out` uses it — it does NOT compare against `exclusion_for`'s actual computation. So the "same context" property is tested only by construction, not by a differential test. **P1.**

**P1-9 — `m["sentences"][0], m["sentences"][1]` — what if a moment has fewer than 2 sentences?** Diff line 55: indexes 0 and 1. If `m["sentences"]` has 1 element, IndexError — NOT caught (only KeyError is). **Scenario:** a moment whose sentences list has one entry reaches `ad_read_out` → IndexError → `build()` crashes. Does the package stage's `exclusion_for`/`context_around` call handle 1-sentence moments? Unverifiable. If every moment in practice has ≥2 sentences (the `pm()` fixture uses `sentences=[0, 0]` — two entries, both 0, interesting: both indexes 0, so `context_around` receives the same sentence index twice — that's the fixture's convention, presumably "start/end word indexes into the source" or similar), this never fires. But the diff's own test fixture uses `sentences=[0, 0]`, which suggests these are indexes, not a list of sentence texts, and a 1-sentence moment (a moment that IS one sentence) would have... I genuinely cannot tell. If IndexError is possible, it's a crash in `build()` — fail closed? No: a crash is not a clean fail-closed rejection, it's a broken build. **P1, conditional on unseen data.** Actually — the existing `no_role_on_screen(m)` at diff line 64–66 presumably reads the same fields, and it's called unguarded at diff line 69 (`no_role = {... for m in ms ...}`), so if `m["sentences"]` were malformed, the existing code would already crash before the new code runs. So the new code's exposure is no worse than the existing code's. Downgrade to P2: the new code adds no new crash exposure beyond what `no_role_on_screen` already assumes, EXCEPT the `*m["words"]` unpacking — if `m["words"]` is missing, KeyError, caught. If `m["words"]` is None, TypeError, not caught — but again, existing code paths presumably read it too. P2.

**P1-10 — the `why_none` message when `out["tried"]` is empty.** Diff lines 94–97: if `out["tried"]` is empty and package is None and why_none unset → "no angle gave a line-up to try". When can this happen? The angle step (step 6) proposes angles; if the writer call fails, does `tried` stay empty? If the writer fails, does some other path set why_none? Unverifiable. If the writer fails and `tried` is empty and nothing else sets why_none, the new fallback gives "no angle gave a line-up to try" — better than None. ✔. But: is there a path where `packages` is empty, `tried` is empty, AND `why_none` was already set by the angle step (e.g. "writer call failed")? Then the fallback respects it. ✔.

**P1-11 — test at diff lines 109–110: `out["why_none"].startswith(...)` — the existing test's rig produces exactly one tried angle with why "the clips alone have no through-line". The new assertion expects the joined message to start with "no angle strengthens the...".** — reads "no angle gave a package: angle 1: the clips alone have no through-line". For this to hold, the rig's tried entry must have `{"angle": 1, "why": "the clips alone have no through-line"}`. The test asserts `out["tried"][0]["why"]` contains "no through-line" (existing, line 108) — consistent. ✔. But note: the existing test at diff line 106–107 asserts `out["package"] is None` and `write_calls == []` — so the fallback fires. ✔. However, the assertion uses `assertTrue(startswith(...))` rather than `assertEqual` — weaker than it could be, but the message's tail depends on the rig, so startswith is a reasonable choice. Fine.

**P1-12 — `ad_read_out`'s moments-removal happens before `prescreen(router, ms, ...)` — the prescreen's `screened` count.** Diff line 80: `"prescreen": {"screened": len(fails), ...}` — `fails` comes from `prescreen(router, ms, ...)` where `ms` is now the post-ad_read list. So `screened` counts fewer moments than before. Is that a "changed what a check accepts"? No — it's a changed *input* to step A, documented. The standing law says the change "must refuse exactly what the package stage already refuses, only EARLIER, and must not pass anything new" — the prescreen now never sees ad-read moments, so its `failed` dict can't contain them; previously the prescreen DID see them (they were screened, cleared, angled, then refused at the exclusion gate). So downstream records (prescreen.cleared, angles' membership) change. That's the intended "only earlier" — but note: **the exclusion screen at the package stage still runs on the surviving moments and can still refuse them for OTHER reasons (model verdict, or a marker `ad_read_out` missed).** Does anything guarantee the package-stage exclusion screen still runs? The diff doesn't touch the per-clip gates, so yes, it still runs. ✔ — the deterministic part will now find the same markers it would have (the moments it would have caught are gone, and the survivors' contexts are the same), so the package-stage exclusion verdicts on survivors are unchanged. ✔.

**P1-13 — `out["ad_read"]` key placement in the `out` dict literal (diff line 79) vs the mutation at diff line 71–72.** The dict literal at line 77–82 includes `"ad_read": ad_read` — and `ad_read` was computed at line 71. ✔. No ordering issue.

**P1-1 (revisited) — the `before is not None` guard vs `ad_read_marker`'s None/"" equivalence.** Covered above; the verdicts coincide; the only gap is documentation.

---

## P2 findings

**P2-1 — `t.get('why')` may render "None" into why_none.** `package.py` diff lines 95–96: if a tried entry lacks a `why` key, the message contains "angle 1: None". Cosmetic; the reason is not hidden, just ugly. (Whether a tried entry can lack `why` is unverifiable from the diff.)

**P2-2 — double regex search in `ad_read_marker`** (diff lines 14–15). Compute `mt = AD_MARKERS.search(txt)` once. Performance nit only.

**P2-3 — the 900-char truncation** (diff line 96) can clip the last angle's reason; with ≤3 angles unlikely, but the truncation counts the prefix. Consider truncating per-angle. Cosmetic.

**P2-4 — test coverage: no differential test that `ad_read_out` and `exclusion_for` compute the same context.** The "refuses exactly what the package stage refuses" guarantee is by construction (shared `ad_read_marker`, shared `CI.context_around`), not by a test that runs both on the same fixture and compares. If `exclusion_for` ever passes a different before-text (e.g. truncated, or a different context function), the two screens diverge silently. A test asserting `exclusion_for`'s deterministic part's verdict == `ad_read_out`'s verdict on the same moments would pin it. (The change description asserts the same context; the diff shows `ad_read_out`'s side only.)

**P2-5 — `test_build_leaves_an_ad_read_moment_out_before_the_angle` monkeypatches `PK.ad_read_out`** (diff lines 147–152) with a lambda ignoring its `sources` argument — fine, but the monkeypatch-restore via try/finally is the module's existing convention (the previous test does the same for `CI.context_around`), so consistent. No finding, noted for completeness. Actually, one subtlety: the lambda is `lambda ms_, sources: {...}` — if `build()` ever calls `ad_read_out` with keyword args (`ad_read_out(ms=..., sources=...)`), the lambda's positional-only params would raise. The call site (diff line 71) is positional. ✔.

P2-6 — the log line (diff lines 85–86) says "on an ad-read marker (the exclusion screen's deterministic part)" — accurate.

P2-2 (recheck) — the `ad_read` filter's placement AFTER no_role: a moment removed by no_role never appears in `out["ad_read"]` even if it has a marker. That's consistent with "the package stage never saw it either" (no_role-removed moments are dropped before any exclusion screen, both before and after this change). ✔ — no finding, but worth stating: the record `out["ad_read"]` is therefore NOT "every moment with a marker", it's "every no_role-surviving moment with a marker". If anyone downstream reads `out["ad_read"]` as the full marker census, it undercounts. Documentation nit.

P2-7 — `ad_read_out`'s docstring says "A moment with no Source or no context is left to the package stage, which refuses it (fail closed)" — for the no-Source case, the package stage's `exclusion_for` presumably also fails to find a Source/context and excludes; the diff's own description says exclusion_for refuses a moment without context ("no context" -> exclude). For no-Source: does `exclusion_for` refuse a moment whose Source is missing? The change description says the package stage "refuses a moment without context (exclusion_for: 'no context' -> exclude)" — a moment with no Source presumably has no context, so it's refused. But if `src_of` raises KeyError in `ad_read_out` yet `exclusion_for`'s own source lookup *succeeds* (different lookup — e.g. `ad_read_out`'s `src_of` uses `source_key else video_id` while `exclusion_for` uses something more forgiving), the two stages could disagree. Unverifiable from the diff; the change description asserts they're the same lookup ("by source_key else video_id"). Flag as assumption, P2.

P2-8 — `why_none` fallback placement: it runs AFTER the angle loop, BEFORE `out["seconds"]`/`out["usd"]` are set (diff lines 98–99) — no interaction. ✔.

---

## Laws compliance (what the diff shows)

- **L-m / fail-closed (L-j):** the skipped cases (no Source → KeyError → skip; no context → `before is None` → skip) are left to the package stage which excludes them — fail closed. ✔ (conditional on `exclusion_for`'s behavior, which the diff doesn't show — assumption, see P2-7).
- **"Refuse exactly what the package stage refuses, only earlier, nothing new":** the deterministic screen is the same function (`ad_read_marker`) on (per the change description) the same context; the record returned by `exclusion_verdict` is byte-identical to the removed code; the model verdict path is untouched. ✔ as far as visible; the differential-coverage gap is P2-4.
- **Law 20/M2 (thresholds are constants; never change what a check accepts):** no threshold touched; `AD_MARKERS` untouched; the filter only removes moments, never adds. ✔.
- **M12:** exceptions in `ad_read_out` — only KeyError is caught; other exceptions propagate (fail closed by crash, consistent with the existing code's behavior for the same fields). ✔.
- **Smallest diff / M1:** no new renderer/selector; a helper extraction + a filter + a diagnostic. ✔.

---

## SHIP: yes with conditions

Conditions (all cheap, none blocking the logic):
1. **Add the differential test (P2-4):** one test that runs `exclusion_for`'s deterministic part (or `exclusion_verdict` with a stubbed router/model) and `ad_read_out` on the same fixture and asserts identical verdicts/reasons — this is the only thing that *proves* "refuses exactly what the package stage refuses" rather than asserting it by construction.
2. **Confirm `src_of` raises KeyError (not returns None) for a missing source** and that `exclusion_for`'s source lookup is the same one — the no-Source skip's fail-closedness rests on it (P2-7/P1-4).
3. **Confirm `m["sentences"]` always has ≥2 entries** (or that `no_role_on_screen` already guarantees it) — the new `*m["words"]`/indexing adds no new crash exposure only if the existing code reads the same fields (P1-9→P2).
4. Optionally: compute the regex match once in `ad_read_marker` (P2-2) and don't let the 900-char truncation clip a reason (P2-3); ensure tried entries always carry `why` so the message never reads "angle N: None" (P2-1).

No P0. The core guarantees — identical deterministic verdict, unchanged model verdict, fail-closed skips, why_none never overwriting an existing reason — hold on every path the diff exposes.</think># Audit: pp-selectid-0352 — ad-read screen moved before the angle; why_none naming

Scope note: I can only see the 161-line diff. Everything about `AD_MARKERS`, `CI.context_around`, `src_of`, `exclusion_for`, `exclusion_verdict`'s model branch, and the `Rig`/`pm` test helpers is inferred from the diff's context lines and the change description, and is flagged as assumption where it matters.

---

## P0 findings

None. On every path the diff exposes, the stated guarantees hold: the deterministic verdict is computed by the same extracted function on the same inputs, the model verdict is untouched, the skips are fail-closed, and the `why_none` fallback defers to any reason already set.

---

## P1 findings

**P1-1 — The "refuses exactly what the package stage refuses" guarantee rests on an unseen contract, and no differential test pins it.**
`package.py` (diff lines 46–61): `ad_read_out` computes the before-context as `CI.context_around(src_of(m, sources), m["sentences"][0], m["sentences"][1], *m["words"])`. The claim that this is "the SAME context exclusion_for reads" is asserted in the change description but `exclusion_for` is not in the diff. Two specific assumptions:
- that `exclusion_for` passes the *raw, untruncated* before-string to `exclusion_verdict` (the diff shows `quote_data(before_text, 3000)` truncation happens only for the *prompt* at diff line 37, after the deterministic screen — so if `exclusion_for` passes raw, the two screens agree; if it pre-truncates, they can diverge: a marker sitting past the truncation point would be caught here and missed at the package stage, or vice versa);
- that `src_of`'s lookup (source_key else video_id) is the same lookup `exclusion_for` uses.

The new test `test_ad_read_out_reads_the_same_context_as_the_exclusion_screen` (diff lines 131–142) monkeypatches `CI.context_around` and only proves `ad_read_out` *calls* it — it never compares against `exclusion_for`'s actual computation. **Scenario:** someone later changes `exclusion_for` to pass a shortened before-text; the two screens diverge silently; the early filter then refuses (or spares) a moment the package stage would not — violating "refuse exactly what the package stage refuses, nothing more" with no failing test. This is the single most important unverifiable assumption in the diff.

**P1-2 — The KeyError catch in `ad_read_out` is broader than "no Source", and only KeyError is caught.**
Diff lines 54–57: the `try` wraps the whole expression, so a KeyError raised *inside* `CI.context_around` (e.g. a word missing from the source's word list) is also swallowed and the moment silently skipped — documented as "no Source" only. Conversely, anything not-KeyError (a `TypeError` from `m["words"]` being None, an `AttributeError` if `src_of` returns None instead of raising) propagates and crashes `build()`. Mitigation: the existing `no_role_on_screen(m)` at diff line 69 runs unguarded over the same moments and presumably reads the same fields, so the new code adds little new crash exposure — but that equivalence is itself inferred, not shown. Fail-closed either way (a crash is not a wrong pass; a skipped moment still faces the package stage), so P1 not P0, conditional on unseen data.

**P1-3 — `m["sentences"][0]` / `m["sentences"][1]` assumes ≥2 entries; IndexError is not caught.**
Diff line 55. If a one-sentence moment can exist, `ad_read_out` raises IndexError and the build dies rather than failing closed. The fixture's `sentences=[0, 0]` (diff line 138) suggests these are indexes into the source, not a list of sentence texts, so a 1-entry list may be impossible — I cannot verify from the diff. Same mitigation as P1-2: if `no_role_on_screen` indexes the same fields, the exposure pre-exists. Conditional.

**P1-4 — `out["ad_read"]` is a post-no_role census, not a marker census.**
Diff lines 70–72: the ad_read filter runs on `ms` *after* the no_role removal, so a moment dropped by no_role never gets an `ad_read` record even if it carries a marker. This is behaviorally consistent (no_role-removed moments never reached the package-stage exclusion screen before either), but anyone reading `out["ad_read"]` as "every moment with an ad-read marker" will undercount. Documentation/semantics nit, listed P1 only because `out` is a sealed record someone will trust.

---

## P2 findings

**P2-1 — `t.get('why')` can render "angle N: None"** (diff lines 95–96). If any tried entry lacks a `why` key, the message reads `angle 1: None`. Whether that's reachable depends on the angle loop's failure paths, which the diff doesn't show. Cosmetic; the reason isn't hidden, just unnamed.

**P2-2 — Double regex search** (diff lines 14–15): `AD_MARKERS.search(txt)` evaluated twice per text. Compute the match once. Performance nit.

**P2-3 — The 900-char truncation** (diff line 96) applies to the whole message including the prefix, so with long per-angle reasons the last angle's why can be clipped. With ≤3 angles unlikely to bind. Cosmetic.

**P2-4 — `before is not None` vs `ad_read_marker`'s None/""-equivalence** (diff line 58): if `CI.context_around` signals "no context" as `""` rather than `None`, the moment is screened here on an empty before-text instead of being skipped. Verdicts still coincide (a marker in the moment text is refused by both stages; no marker, neither refuses), so this is a documentation-accuracy gap, not a divergence — but the "left to the package stage" claim in the docstring (diff lines 49–50) and the test's `(None, None)` case (diff line 133) only cover the `None` sentinel.

**P2-5 — Weak assertion** (diff lines 109–110): `assertTrue(out["why_none"].startswith(...))` where `assertEqual` on the full expected message would also pin the angle numbering and the exact join format. Deliberate looseness, probably, given the rig; noting it.

**P2-6 — Monkeypatched lambda's signature** (diff line 149): `lambda ms_, sources: {...}` — matches the positional call at diff line 71; would break if the call ever went keyword. Consistent with the file's existing convention (the preceding test monkeypatches `CI.context_around` the same way). No action.

---

## Law compliance (what the diff shows)

- **"Refuse exactly what the package stage refuses, only earlier, nothing new":** the filter only *removes* moments; nothing new passes. The extracted `ad_read_marker` is the identical expression, moved verbatim (diff line 12 vs removed lines 26–27), and `exclusion_verdict`'s early-return record is byte-identical to the removed one (diff lines 31–34 vs 29–30) — same `verdict/why/risks/backend/measured/replayed`. The model branch (diff lines 35–37) is untouched context. ✔, modulo P1-1's unseen `exclusion_for` contract.
- **L-m / fail-closed:** skipped moments (no Source → KeyError; no context → `before is None`) fall through to the package stage, which the change description says excludes them ("no context" → exclude). ✔, conditional on `exclusion_for` (P2-4, P2-7 assumption).
- **Law 20/M2:** no threshold touched; `AD_MARKERS` untouched; no check's acceptance changed. ✔.
- **`out["usable"]` meaning:** `n_usable` is captured at diff line 68, *before* both filters — unchanged. ✔.
- **why_none never hides a reason:** the fallback is guarded by `not out.get("why_none")` (diff line 94), and the `<3 channels` early return (diff lines 87–89) exits before the fallback runs, so it can't be overwritten there. ✔.
- **M1 / smallest diff:** helper extraction + one filter + one diagnostic; no new selector or renderer. ✔.

---

## SHIP: yes with conditions

1. **Add a differential test** (closes P1-1): run `exclusion_for`'s deterministic part (or `exclusion_verdict` with a stubbed router) and `ad_read_out` on the same fixture, assert identical verdicts and reason strings. This is the only way to *prove* rather than assert "the same context, nothing more" — the current test proves only that `ad_read_out` calls `CI.context_around`.
2. **Confirm from the surrounding code** (outside this diff): (a) `exclusion_for` passes the raw, untruncated before-string to `exclusion_verdict`; (b) `src_of` raises KeyError (not returns None) for a missing source and uses the same source_key-else-video_id lookup `exclusion_for` uses; (c) `m["sentences"]` always has ≥2 entries, or that `no_role_on_screen` already indexes the same fields so the new code adds no crash exposure (P1-2, P1-3).
3. Cheap, non-blocking: single regex match in `ad_read_marker` (P2-2); ensure tried entries always carry `why` so the message never reads "angle N: None" (P2-1); consider truncating per-angle rather than the whole message (P2-3); document that `out["ad_read"]` is a post-no_role census (P1-4).

No P0. The logic is right, the extraction is verbatim, the skips fail closed, and the `why_none` guard is correctly ordered — the residual risk is concentrated in contracts the diff doesn't show, which is exactly what conditions 1–2 retire.