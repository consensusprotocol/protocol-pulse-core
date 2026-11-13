# glm-5.3-flash (z-ai/glm-5.3-flash) 157 s finish=stop usage in 8625 / out 4758 usd~0.097 (upper-bound price)

# Spend-Guard Audit — Ruling 48 (limit_basis="reported")

Scope: only the 170-line diff provided. Everything below is verified against the diff text; where the diff doesn't show the underlying code (e.g. `_settle`, `_ledger`, the `router()` test helper), I say so.

---

## What the diff establishes (verified)

- `providers.py:15-17` — `limit_basis` validated at construction: only `"estimate"` / `"reported"`; anything else raises `ValueError`. Default `"estimate"` preserves old behaviour for every caller that doesn't pass it. ✔
- `providers.py:25-32` — `_basis_total`: reported basis = `usd_reported + usd_unreported_estimate`; estimate basis = `usd_estimate`. ✔
- `providers.py:34-39` — `spent()` reads the basis under `self._lock()`, returns `0.0` when `spend_path` is unset. ✔
- `providers.py:41-56` — `_reserve` now compares `spent (on the basis) + held + upper > limit_usd`. The reservation itself is still the price-table `upper` (docstring, line 44-45: "The reservations stay price-table upper bounds whatever the basis: the guard can only stop early, never late"). The lock, the `reserved` dict, the key format, and the `round(upper, 6)` booking are untouched by the diff. ✔
- `proof_ly.py:115-118` — `LY_LIMIT_USD = 12.0`, `LY_LIMIT_BASIS = "reported"`, `LY_STOP_USD = 10.0`; the driver's Router passes the basis (lines 127-128). ✔
- `proof_ledger.py:66-76` — Router constructed with the basis; pre-build stop check `spent0 >= PL.LY_STOP_USD` → REFUSED, exit 3, before any paid call; otherwise the running total is logged. Post-build, `spend_ruling_48 {before, after, cap, stop, basis}` is written into `package.json` (lines 84-87). ✔

---

## Findings

### P1-1 — `proof_ledger.py:84` — `res["spend_ruling_48"] = ...` can raise `KeyError`/`TypeError` when the build produced no package, killing the post-build accounting

`proof_ledger.py:80-83`:

```python
    else:
        say(f"no package ({res.get('why_none')}); usable {res['usable']}, cleared {res['prescreen'].get('cleared')}")
+   res["spend_ruling_48"] = {"before": round(spent0, 4), "after": round(router.spent(), 4), "cap": PL.LY_LIMIT_USD,
+                             "stop": PL.LY_STOP_USD, "basis": PL.LY_LIMIT_BASIS}
```

The assignment is outside the `if/else`, so it runs in both branches — good, that's the intent. But it assumes `res` is a dict. From the diff alone I cannot verify that `PK.build` always returns a dict (it might return `None` on some failure path, in which case `res.get('why_none')` at line 83 would already have failed, which weakly suggests `res` is always a dict — but that's inference, not verification). If `PK.build` can return `None`, the diff turns a graceful "no package" outcome into a crash after the paid calls, losing the spend record the ruling demands ("Keep the running total on STATE line 1 with every build").

Additionally, even if `res` is a dict, note the ruling says the running total goes on **STATE line 1**; the diff logs it via `say(...)` (lines 75-76, 86-87) and into `package.json`. Whether `say()` writes to STATE line 1 depends on code not in the diff — I cannot verify that the ruling's STATE requirement is literally satisfied. Flagging as unverifiable-from-diff, not as a defect.

**Scenario:** `PK.build` returns `None` → line 84 raises `AttributeError`/`TypeError` → `package.json` never written, `logf.close()` (line 90) never reached, post-build spend never recorded — exactly the accounting the ruling asks to keep.

**Fix (1 line):** `res = res or {}` before line 84, or guard the assignment.

### P1-2 — `providers.py:31` — reported-basis total silently treats missing ledger keys as 0.0, diverging from the estimate basis's strictness

```python
+        if self.limit_basis == "reported":
+            return float(d.get("usd_reported", 0.0)) + float(d.get("usd_unreported_estimate", 0.0))
+        return float(d["usd_estimate"])
```

The estimate basis uses `d["usd_estimate"]` (KeyError → fail-closed, consistent with M12). The reported basis uses `.get(..., 0.0)`: an old ledger written before this diff that lacks `usd_reported`/`usd_unreported_estimate` reads as **$0.00 spent**, so `_reserve` will happily admit calls until reservations alone pass the cap, and `spent()` reports $0.00.

Is that a real scenario? The background says `_settle` maintains all three totals, and the measured ledger (usd_estimate $39.49, usd_reported $3.46, usd_unreported_estimate $1.81) evidently has them. But the diff's own test writes all keys explicitly (line 145-146), so the test never exercises a legacy ledger. Whether any ledger in this order predates the `usd_reported` fields is not verifiable from the diff. If one does, the guard under-counts — the opposite failure direction of the docstring's "can only stop early, never late" claim, which that claim (line 44-45) only makes about *reservations*, so the docstring is technically consistent; the risk is purely the legacy-ledger case.

**Severity: P1** (not P0) because the measured ledger has the keys and the drivers here (proof_ly, proof_ledger) point at `SPEND_LY.json` which demonstrably has them. But it's a silent-0.0 failure mode in a guard whose governing law is M12 FAIL CLOSED.

**Fix:** either require the keys (`d["usd_reported"]`) when basis is "reported", or have `_settle`-era ledgers versioned; at minimum, note it.

### P2-1 — `providers.py:53-54` — the reservation guard mixes bases in one comparison; correct, but only because reservations are upper bounds — worth stating the invariant's proof obligation

```python
+            spent = self._basis_total(d)
+            if spent + held + upper > self.limit_usd:
```

`held` sums price-table upper bounds; `upper` is a price-table upper bound; `spent` is on the ruling's basis. The comparison is therefore `reported_total + estimate_upper_bounds > reported_cap`. Since reported ≤ estimate per call (the vendor's figure, else the estimate — by the background's definition of `usd_unreported_estimate`), the reported-basis total of the in-flight + new calls is ≤ `held + upper`, so the guard can only refuse *earlier* than a perfect reported-basis accounting would, never later. That matches the docstring. ✔

One subtlety I can verify: a call whose vendor reports a figure *higher* than the price-table estimate would break the "reported ≤ estimate" premise. The background says the estimate is "an upper bound", so this is excluded by construction — but nothing in the diff (nor in the test) asserts it. If a vendor ever reports above the price table, the reservation (estimate) under-counts and the guard could stop late. Not a defect under the stated invariants; noting the dependency.

### P2-2 — `test_providers.py:150-151` — the "old basis refuses" assertion depends on the `Fake` upper bound, which the diff doesn't show

```python
+            with self.assertRaises(P.SpendLimit):                   # the old basis: 39.5 + the upper bound > 40
+                router(d, [a], {"write": ["openai:x"]}, spend_path=led, limit_usd=40).call("write", p)
```

For this to fail with `SpendLimit`, the call's price-table upper bound must exceed $0.50. The `Fake`'s usage is `{"in": 1000, "out": 100}`; the price table that maps that to an upper bound is not in the diff. If the upper bound were, say, $0.02, the old-basis call would *pass* (39.5 + 0.02 + 0 < 40) and the test would fail — which would be caught, not silently. So this is a test-robustness note, not a correctness risk: the test self-announces if the price table changes. Similarly, line 155's comment "5.27 + its upper bound < 12" presumes upper < 6.73 — surely true, but again derived from the unseen price table.

Also note: the same 50 000-char prompt `p` is used for both calls, and the second call's reported figure is `0.001` (line 148) — the test then asserts `5.29 + 0.001` (line 158). Arithmetic checks: 5.27 + 0.02 = 5.29; 5.29 + 0.001 = 5.291. ✔. And `r.spent()` after the first call: 3.46 + 1.81 = 5.27. ✔. The test's arithmetic is internally consistent.

### P2-3 — `proof_ledger.py:70-74` — the stop check uses `>=` and reads spend *before* the build; correct, but the "no paid call" claim holds only because the Router is constructed before the check

Verified: the Router is constructed at line 66-68 (no calls happen in `__init__` — it only loads config and builds backends, per the diff's context lines 11-20), `spent0` is read at line 69, the REFUSED branch returns 3 at line 74 before `PK.build` (line 79). So "no build starts at or over $10" holds: the only paid-call paths are inside `PK.build` / `PL.meter` / `PL.reply_meter`, all after the check. ✔

Edge: exactly $10.00 → `>=` → refused. The ruling says "At $10 reported stop" — refusing *at* $10 (inclusive) is a defensible reading; a build starting at exactly $10.00 would have $2.00 of headroom under the $12 cap, and the ruling's "stop and tell me" arguably means "stop *starting new work*". Both readings are consistent with the diff; the diff chose the stricter one. I read the ruling the same way, with one caveat: the ruling's "At $10 reported stop and tell me" most naturally reads as a *running* stop (tell me when the total crosses $10), whereas the diff implements it as a *pre-build* gate. A build starting at $9.99 that spends $2.50 crosses $10 mid-build and finishes at $12.49 — wait, it can't: the $12 hard cap binds via `_reserve`. So the maximum final total is $12.00 + (one in-flight call's overshoot? No —) let me be precise: `_reserve` refuses when `spent + held + upper > 12`, so the final *basis* total can exceed $12 only by the amount a settled call comes in *under* its reserved upper bound... actually no: settled calls replace their reservation with their actual (reported-or-estimate) cost, which is ≤ their upper bound, so the final total is ≤ $12.00 + 0 — the cap is genuinely hard on the basis. ✔ (Caveat: the final reported total can exceed $12 only if a call's reported figure exceeds its reserved upper bound — see P2-1's caveat; excluded by the "estimate is an upper bound" invariant.)

So: "at $10 stop" = "no new build starts at/over $10; a started build is bounded by the $12 hard cap" — this satisfies the ruling's intent (the orchestrator is told via the REFUSED log and the `spend_ruling_48` record), and the mid-build crossing of $10 is bounded by $12. I read the ruling the same way. If the orchestrator meant "pause the *running* build at $10", the diff does not do that — but ruling 41's $3.00 per-build search budget (cited in the change note 3) keeps a single build's spend bounded, and the diff's interpretation is the only one implementable at the Router layer without a mid-build checkpoint, which the diff doesn't add. Say: defensible; flag for the orchestrator to confirm.

### P2-4 — `proof_ly.py:115-117` — the $12 cap's provenance comment is good, but `LY_STOP_USD` is defined in proof_ly and consumed in proof_ledger via `PL.LY_STOP_USD`

`proof_ledger.py:70, 84` reference `PL.LY_STOP_USD` and `PL.LY_LIMIT_USD` (PL = proof_ly, per line 66's `PL.chains()` usage pattern). The diff shows `LY_STOP_USD` being *added* in proof_ly (line 117) — since proof_ledger already imported PL before this diff (line 66-67's context uses `PL.ENV`, `PL.LY_LIMIT_USD`), the new constant is reachable. ✔ But: proof_ly's *own* `main` (line 126-128) uses `LY_LIMIT_USD` and `LY_LIMIT_BASIS` but — verified from the diff — **never checks `LY_STOP_USD`**. The $10 stop exists only in proof_ledger (the one-build driver). Is that per the ruling? The ruling says "At $10 reported stop and tell me" without distinguishing drivers; the change note 3 says the stop is implemented in proof_ledger ("one build"). If proof_ly (the saved-runs replay driver) is meant to also honour the $10 stop, it doesn't. From the diff, proof_ly's Router still admits calls until the $12 cap. Whether proof_ly counts as "a build" under the ruling is not verifiable from the diff — proof_ly replays recorded exchanges (`replay`-style, per the Router docstring line 6: "replay=True serves recorded exchanges only"), and the diff does not show proof_ly passing `replay=True`, so I cannot even confirm proof_ly's calls are free. If proof_ly makes *paid* calls (no `replay=True` visible in its Router construction, line 126-128), then the $10 stop's absence there is a gap worth one line. **Uncertain; flagging.**

Hmm — actually, looking again at line 126-128: `P.Router(env_path=PM.PS.ENV, record_dir=REPLIES, spend_path=SPEND, ...)` — `record_dir=REPLIES` with a `spend_path` suggests it records/replays against the same ledger. Without the surrounding code I can't determine whether its calls cost money. Stated as uncertain.

### P2-5 — `providers.py:34-39` — `spent()` returns 0.0 with no `spend_path`; the pre-build stop in proof_ledger then always passes

Consistent with the old behaviour of `spent_estimate` (line 575-577 context: same `if not self.spend_path` pattern — actually the context shows `spent_estimate` returning under lock; the 0.0-with-no-ledger behaviour is stated in the new `spent()` docstring, line 35). For proof_ledger, `spend_path=PL.SPEND` is always passed (line 67), so this path doesn't arise there. ✔ No finding, noted for completeness.

### P2-6 — Double-counting check (asked explicitly): does the reported basis count every call exactly once?

By the background: `_settle` books each call's cost into `usd_reported` (when the vendor reports) **or** `usd_unreported_estimate` (when it doesn't, including deadline-abandoned calls at their upper bound). `_basis_total` sums exactly those two. So each call contributes to exactly one of the two summands — assuming `_settle` maintains the partition correctly, which the diff does not show and I cannot verify. What I *can* verify: `_basis_total` itself adds no call twice and skips none *provided the two ledger fields partition the calls*. The test (lines 152-158) exercises both branches (a no-figure call adds its estimate: 5.27 → 5.29; a figured call adds only its figure: 5.29 → 5.291) — consistent with the partition, but the test drives settlement through `Fake`/`router()` helpers not shown, so it proves the *counting* given `_settle`'s behaviour, not `_settle` itself. Within the diff's scope: ✔, with the noted dependency.

### P2-7 — Lock usage: `spent()` takes the lock; `_reserve` holds the lock across its read-and-check

`_reserve` (lines 48-58) reads the ledger, computes `spent = self._basis_total(d)`, checks, and writes the reservation — all inside `with self._lock():`. `spent()` (lines 38-39) also takes the lock. If `_lock()` is a plain (non-reentrant) lock, no deadlock arises since neither calls the other while holding it (`_basis_total` is lock-free, pure). ✔ If `_lock` were reentrant it'd also be fine. No TOCTOU between `spent0` (proof_ledger line 69) and the build's first `_reserve` — but that's inherent and harmless: the $12 cap is enforced at `_reserve` time, not at the pre-build check. ✔

---

## Ruling-compliance summary

| Ruling 48 clause | Diff | Verified? |
|---|---|---|
| Cap on vendor-reported, not estimate | `limit_basis="reported"`, `_basis_total` | ✔ (counting partition depends on unseen `_settle`) |
| $12.00 total, from $3.46 used | `LY_LIMIT_USD = 12.0`; measured total $5.27 (3.46+1.81) — note ruling's own math says $5.26, test/ledger says $5.27; the 1¢ gap is rounding in the measured figures, not a diff defect | ✔ (arithmetic: 3.46+1.81=5.27; the ruling's "$5.26" vs the diff's implied $5.27 — trivial, but the ruling's "So the running total by the ruling's own rule is $5.26, not $3.46" vs the test's 5.27: the diff is consistent with its own ledger, the ruling's prose rounded) |
| Estimate counts only where vendor reports none | second `usd_unreported_estimate` summand; test lines 155-158 | ✔ |
| Running total on STATE line 1 with every build | logged via `say()` + `package.json` | Partially — whether `say()` reaches "STATE line 1" is not verifiable from the diff |
| At $10 reported, stop and tell me | pre-build `>= $10` → REFUSED, exit 3, told via log | ✔ as a *start* gate; mid-build crossing bounded by the $12 hard cap (see P2-3) — my reading agrees, flag for confirmation |
| Other callers unchanged | default `limit_basis="estimate"`; `_reserve`'s estimate-basis path is byte-identical arithmetic to the old `d["usd_estimate"] + held + upper > limit` | ✔ |

---

## SHIP: yes with conditions

1. **(P1-1)** Guard `res` being non-dict (or `None`) before `proof_ledger.py:84`, so a failed build still records `spend_ruling_48` — the ruling's accounting must survive a "no package" outcome.
2. **(P1-2)** Decide the legacy-ledger story: either require `usd_reported`/`usd_unreported_estimate` (KeyError, fail-closed, M12) when basis is "reported", or confirm every ledger this order touches predates nothing. Silent 0.0 in a spend guard is the one failure direction the ruling's cap can't tolerate.
3. **(P2-4)** Confirm whether proof_ly's saved-runs driver is meant to honour the $10 stop; if its calls are paid, add the same pre-build check (one `if`), else note that the stop is proof_ledger-only.
4. **(P2-3, informational)** Have the orchestrator confirm that "at $10 stop" = "no new build *starts* at/over $10, running builds bounded by the $12 cap" — the diff's reading is defensible and mine, but it's the ruling's call.

No P0. The core guard change is correct, minimal, and the reservation/lock logic is untouched; the reported-basis arithmetic in the test is internally consistent (5.27 → 5.29 → 5.291) and the hard cap genuinely binds on the ruling's basis given the stated "estimate = upper bound" invariant.