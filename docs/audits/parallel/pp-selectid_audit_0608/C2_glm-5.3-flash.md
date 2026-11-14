# glm-5.3-flash (z-ai/glm-5.3-flash) 100 s finish=stop usage in 24466 / out 2617 usd~0.113 (upper-bound price)

# CYCLE 2 — FINAL REVIEW (pp-selectid-0608, ruling 91's medley half)

## 1. WHAT THE OTHERS CAUGHT THAT I MISSED

- **grok's `take_failed`-never-incremented observation** (package.py:261/284): I had noted the value loss bypasses ruling 3's counter but hadn't pinned down that this is *by design* per ruling 91's text ("a value loss never counts toward ruling 3's two failures") and that the consensus output explicitly pins it with test M9. I flagged it as a question; it's actually the agreed reading. Grok's framing ("matches L-c dissent rule but interacts with ruling-66/3 counter as side-effect") was the sharper statement.
- **glm's replay-flag uncertainty**: glm correctly noticed that `ok` in `takeaway_value` (package.py:274) does not require `replayed is False`, and that whether the pin side catches it depends on `gate_problems`' body, which the diff doesn't show. I didn't chase this. The test at 766–767 (`{"text": t, "replayed": True}` → PinRefused) shows the *pin* enforces it, so the row contract is enforced at the gate, not at the verdict — but glm's "verify" caveat was legitimate: the enforcement lives in code outside the diff, so it's only test-attested, not diff-attested.
- **qwen's `no_voice_fits` fail-closed note**: I hadn't explicitly traced that `med.get("measured") is True` failing (model failure on the clips-alone verdict) silently routes a value loss to the rewrite path rather than no-voice — correct, fail-closed, but worth stating.

## 2. AGREE / DISAGREE

| Finding | Verdict | Why |
|---|---|---|
| grok <high> value loss never increments `take_failed` | **Agree, by design** | Ruling 91's text says the no-voice fallback for a value loss requires "its clips meet the seconds" — ruling 3's clip-adding path is a *different* trigger. Test at 639–650 pins it. Not a defect. |
| grok <medium> (f) edge: lone caption failure + value loss → no-voice fails closed, no ruling-65 rescue | **Agree it's real; judge acceptable** | package.py:277–279: `break` happens before paid gates, so `lone_slot`/ruling-65 never runs. But ruling 91's text mandates the no-voice fallback *only* conditioned on clips meeting the seconds — it doesn't reserve a ruling-65 rescue. Fail-closed, costs one package, not a wrong pin. |
| glm <medium> `replayed` not enforced in `ok` | **Agree, but enforced downstream** | `ok` (package.py:274) ignores `replayed`; the row contract is enforced at `to_pin` via `gate_problems` (test 766–767). Defense-in-depth would put it in `ok` too, but the agreed row's enforcement point is the pin. Non-blocking. |
| glm <medium> ruling-91 path skips paid gates → caption never re-judged | **Agree** | Same (f) edge, correctly traced: `no_voice()` re-gates title/caption (package.py:190–193 region) and fails closed. Consistent with L-m. |
| qwen <high> stale verdict after ruling-65 rewrite | **Agree with qwen's own resolution — not a bug** | `lone_slot` returns only "caption"/"title"; `rewrite_alone` uses `dict(fields, **{slot: line})`, so the takeaway text is untouched and `val` stays valid. The consensus output's refutation is correct, and the row's `text` binding (package_pin.py:429) would catch it fail-closed anyway. |
| qwen <medium> prompt injection | **Agree, adequately mitigated** | `quote_data(...).replace('"', "'")` (package.py:59) plus the UNTRUSTED block; `parse_value`'s strict contract + reject-on-out-of-contract (package.py:69–72) makes injection at worst a lost verdict, not a wrong pin. Fail-closed. |

## 3. NEW FINDINGS (this cycle)

**<medium> package.py:286 (`last_fid, last_rw65 = (last_fid if lone else None), False`) — the value-rewrite path can discard a full write's paid-gate verdicts that ruling 66's amended path would have kept, and the ruling-66 "kept lines keep their verdicts" shortcut then judges the *rewrite* against the *previous* write's fid/cx.** Trace: on a value loss from a *full* write (`lone` False), `last_fid` is set to None. The forced rewrite runs with `lone=True` (via `v_redo`), so at package.py:288–290, `if lone and last_fid is not None` is False → it calls `paid_gates(...)` fresh. That's correct. But if the value loss happens on a *ruling-66 alone* write (`lone` already True), `last_fid` is kept — and `takeaway_alone_gates(router, pk, last_fid, ...)` reuses the previous alone-write's fid/cx as the base. That's the amended ruling-66 behavior, unchanged. So the interaction is: a value-rewrite that *follows* a ruling-66 alone-write inherits `last_fid` from a write whose *takeaway text differed* — `takeaway_alone_gates` presumably re-judges only the takeaway slot against the new text, which is the amended ruling's intent. I cannot verify `takeaway_alone_gates`'s body from the diff; if it re-uses the old fid's violations list wholesale without re-checking the new takeaway text, the rewrite's fidelity verdict would be stale. **Flagging as verify, not a defect** — the test at 587–604 exercises this path (value loss on a full write → forced alone rewrite) but only asserts the value row and prompt, not the fid/cx provenance.

**<medium> package.py:327 (`v_novoice is not None or take_failed >= NO_VOICE_AFTER`) — a value loss on FITS clips short-circuits ruling 3 even when `take_failed` has also reached 2, and the `no_voice` note's `ruling` field then mislabels the reason.** Concrete: write 1 fails a *paid* gate (take_failed=1), write 2's takeaway passes gates but loses value on FITS clips → `v_novoice` set, `break`. At 327, `v_novoice is not None` → `no_voice(value=v_novoice)` → note says `ruling: 91`. But the takeaway *also* failed its gates twice — ruling 3 independently fired. The label is cosmetic (both paths ship the same no-voice shape, no clip added either way since FITS), but the record attributes the fallback to 91 when 3 also applies. Only matters for audit trails. Non-blocking.

**<low> package.py:261 — `val` is assigned unconditionally after cheap gates pass, but `att["value"] = val` (262) and the `_takeaway_record` overwrite (263–264) happen before the `if not val["ok"]` branch; if `takeaway_value` raises (it catches broadly, so it shouldn't), the record would keep the previous write's shape.** `takeaway_value` catches `Exception` broadly (package.py:68), so this is theoretical. Non-blocking.

**<low> package_pin.py:397 — `takeaway_line`'s package-branch uses `zip(vo.get("bridges") or [], vo.get("bridges_after_clip") or [])` and takes `hit[-1]`; if `bridges` and `bridges_after_clip` differ in length (a malformed package), the zip silently truncates and could miss the takeaway.** Both lists are built together in `to_pin`/build, so they're always equal-length in practice; the moments_package branch (400–402) reads `ev["bridges"][-1]` directly. Fail-closed via `takeaway_problems` (row text won't match → PinRefused). Non-blocking.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| takeaway_value verdict | 8.5/10 | 8.5/10 | glm's replay-flag note is real but enforced at the pin; no change. |
| no_voice_fits / ruling-91 no-voice path | 8/10 | 8/10 | (f) edge confirmed real, judged acceptable; ruling-3-vs-91 label cosmetic. |
| build loop (v_redo/alone interaction) | 7.5/10 | 7.5/10 | My `last_fid` provenance question remains verify-only; tests exercise the path. |
| package_pin row binding | 9/10 | 9/10 | Fail-closed, test-attested; unchanged. |
| Tests | 8.5/10 | 8.5/10 | 18 new tests, real-path test, 11-mutation check; the (f) edge and last_fid provenance are the gaps. |

## 5. FINAL PRIORITY LIST

- **P0 CRITICAL**: none.
- **P1 HIGH**: none.
- **P2 MEDIUM**:
  1. package.py:286/288–290 — verify `takeaway_alone_gates` re-judges the *new* takeaway text against `last_fid`'s verdict rather than inheriting it wholesale; if it doesn't, the forced ruling-91 rewrite after a ruling-66 alone-write ships a stale fidelity/context verdict. (Verify; the diff doesn't show its body.)
  2. package.py:327/334 — when both `v_novoice` and `take_failed >= NO_VOICE_AFTER` apply, the no-voice note's `ruling` field attributes the fallback to 91 alone; record both (cosmetic, audit-trail only).
  3. package.py:274 — consider adding `and not value.get("replayed")` to `ok` (or to `takeaway_problems`) so the replayed-false contract is enforced at the verdict, not only at the pin via `gate_problems` (defense-in-depth; currently test-attested only, since `gate_problems`' body is outside this diff).

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

Verify (one test) that `takeaway_alone_gates` re-judges the rewritten takeaway's text against the inherited `last_fid` verdict — it's the only remaining path where a stale verdict could reach the pin, and everything else is already fail-closed.

## 7. PRODUCTION READY?

**Yes with conditions** — precisely:
1. Add one test (or diff-attestation) that `takeaway_alone_gates` re-judges the forced ruling-91 rewrite's takeaway text, not the previous write's (package.py:288–290, `last_fid` provenance).
2. Confirm `gate_problems` enforces `replayed is False` for the `takeaway_value` row (glm's verify item; the test at 766–767 suggests yes, but the body is outside this diff — a one-line confirmation or a test asserting it via `to_pin` suffices; the existing test at 766–767 already does this, so this condition is effectively met).

Everything else — the (f) fail-closed edge, the ruling-3/91 label, the replayed-in-`ok` defense-in-depth — is acceptable as-is.