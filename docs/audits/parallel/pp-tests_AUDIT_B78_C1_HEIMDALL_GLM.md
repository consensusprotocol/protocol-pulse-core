<!-- z-ai/glm-5.3-flash, 181 s, finish stop, $0.0010 (vendor usage.cost) -->

# FORENSIC CODE REVIEW — pp-tests_batch78
**Reviewer: Gemini 2.5 Pro** | 2026-11-14 | Diff: 383 lines, 8 files

---

## SECTION 1: CORRECTNESS

**Main flow: the runner's network guard (moments_exam.py)**

The diff's headline fix. Old code (l.247): `socket.getaddrinfo = socket.gethostbyname = socket.gethostbyname_ex = no_resolve` — one shared closure, so the message couldn't name the function. New code (ll.239–251): a factory `no_resolve(name)` returns a closure per name, sets `f.__name__` for debuggability, and `setattr(socket, name, no_resolve(name))` for all five names. This is correct and strictly stronger. The message format `moments_exam: network is disabled ({name} of {a[:1]!r})` matches the test's assertion `f"({n} of " in r["why"]` (l.378) — the `(` before the name and ` of ` after are both present. ✓

**network_reverse toy gate (ll.260–291)**

- `_calls[0] % 2` alternates: case 1 → gethostbyaddr, case 2 → getnameinfo, case 3 → gethostbyaddr... ✓
- The gate swallows `Exception` (l.277) but `NetworkRefused` is a `BaseException` subclass (l.221), so it propagates — this is the documented mechanism (l.264: "the refusal is an ERROR, because a BaseException passes the `except Exception` below"). Correct and clever. ✓
- `context_integrity` returns `{"verdict": "pass", "why": ...}` — but when the lookup raises, the runner catches `NetworkRefused` and records an ERROR row with the exception's `str()` as `why`. The test asserts `r["why"].startswith("NetworkRefused: moments_exam: network is disabled")` (l.375). For this to hold, the runner must prefix the exception class name. **Not verifiable from the diff** — the runner's ERROR-row formatting is outside the diff. If the runner stores `repr(e)` or `f"{type(e).__name__}: {e}"`, it works; if it stores `str(e)` only, the assertion fails. The measured results (379 passed, 0 failed) imply it works, but the reviewer must note: **the proof lives outside the diff.** (Minor: the docstring at l.263 says "Refused unless PP_MOMENTS_ALLOW_NETWORK=1; the refusal is an ERROR" — consistent.)
- `vo_fidelity = context_integrity` (l.287) and `exclusion = _call`-wrapping (ll.290–291): the test only runs corpus "exclusions" (l.372), so only `exclusion` is exercised. `context_integrity`/`vo_fidelity` are dead weight for this test but harmless — they exist so the gate satisfies the runner's gate-attribute contract. Acceptable.

**Alternation assumption (l.377–379)**

The test asserts BOTH lookups appear among the rows: `{n for n in ("gethostbyaddr", "getnameinfo") if any(f"({n} of " in r["why"] for r in rows)} == {"gethostbyaddr", "getnameinfo"}`. This requires ≥2 rows. The exclusions corpus must have ≥2 cases — the old test ran the same corpus with the `network` gate and asserted `all(...)` over rows, so ≥1 row existed; but if the exclusions corpus has exactly 1 case, the alternation yields only gethostbyaddr and the new assertion fails. The measured pass implies ≥2 cases. **Fragile coupling: the test's correctness depends on the corpus size, which the diff doesn't show.** If someone later trims the exclusions corpus to 1 case, this test breaks — but that's a *visible* failure, not a silent pass, so it's acceptable (fail-closed, L-j).

**frontier_blind._key (ll.112–137)**

- Lazy load under `_TLOCK` (docstring l.124–125 says "Called under _TLOCK (from _client)"). The `_GET_KEY` list-as-cache: check-then-act, but the docstring pins the lock. If any other call site exists outside `_TLOCK`, there's a benign race (double-load, both discard one). Not visible in diff; the docstring's claim is the only evidence. **PARTIAL: thread-safety is by convention, not enforced.**
- `sys.dont_write_bytecode` toggle (ll.131–135): set before `exec_module`, restored in `finally`. Correct. But note: this is process-global. If another thread concurrently imports something during that window, it also skips writing bytecode — harmless (only a perf nit, no correctness issue).
- `spec.loader.exec_module(mod)` — if `KEY_LOADER` doesn't exist, `spec_from_file_location` returns a spec with `None` loader → `AttributeError` on `spec.loader.exec_module`. Not a KeyError, not a NetworkRefused — a raw AttributeError. Fail-closed, but the error message would be cryptic. Minor.
- **`_GET_KEY` is a list, not a module-level function reference — why?** Because the module must not import at module-import time (the exam process imports gate modules by name; importing relay eagerly could... actually no, relay.py has no import side effects beyond `os`/`pathlib`). The lazy pattern is defensible (defer cost until a baseline actually runs) but the list-wrapper is slightly awkward vs. a `global`. Cosmetic.

**test_f0 unscanned-names (ll.309–316)**

```python
names, found = _imported_names(), {}
for name in names:
    f = _resolve(name)
    if f and f.startswith(roots):
        found[name] = f
...
unscanned = {n for n in names - set(found) if any(os.path.exists(os.path.join(r, n + ".py")) for r in roots)}
assert unscanned <= {"conftest"}, ...
```

- `names - set(found)`: `found`'s keys are exactly the names that resolved inside roots. So `names - found.keys()` = names that resolved elsewhere, resolved to nothing, or weren't pipeline/segment_v1 at all. The `any(os.path.exists(...))` filter keeps only those with a `.py` in pipeline/ or segment_v1/. Logic is right.
- **Edge: `n + ".py"` misses packages.** A pipeline module that's a *package* (`pipeline/foo/__init__.py`) imported as `foo` would have `pipeline/foo.py` not exist → counted as unscanned → assertion fails → listed → developer reviews. Fail-closed, but a false positive on packages. Does pipeline/ have packages? Not visible. If it does, this test would already be failing (it passes: 379/0), so currently no package is imported by the suite, OR the exception list covers it. Note it.
- **Edge: `_resolve` returning a namespace/`__init__`** — same reasoning; currently passes, so benign today.
- The `{"conftest"}` exception: conftest resolves to the suite's own conftest (asserted at l.306 via `H.control`), which is not under roots, so it lands in `unscanned` if `pipeline/conftest.py` or `segment_v1/conftest.py` exists. The exception is precisely scoped. ✓

**conftest._REAL / _LOOKUPS (ll.189–203)**

`getnameinfo` added to both `_REAL` (l.193) and `_LOOKUPS` (ll.202–203). Symmetric with the other four. The guard function `_guard_lookup(n)` is presumably shared — the diff shows the dict comprehension extended, so the same mechanism applies. ✓

**child_guard/sitecustomize.py (ll.165–171)**

`getnameinfo` appended to the setattr loop (l.170). The probe test (ll.340–345, 352) asserts the child's `__name__`s are `_child_no_gethostbyaddr` / `_child_no_getnameinfo` — meaning the child guard's `_lookup` factory must name functions `_child_no_{n}`. The old guard's naming convention (l.343: `_child_no_getaddrinfo`) implies the factory; the new names follow. ✓ But: **the diff doesn't show the child guard's `_lookup` factory** — we trust the naming convention from the probe's expected output. The measured pass (0 failed) confirms.

**Docstring vs. behavior: conftest l.180** — "no name can be looked up, forward or reverse (getaddrinfo, gethostbyname[_ex], gethostbyaddr, getnameinfo)" — matches the code. ✓

**XFAIL_EVIDENCE count (ll.49–50)**: "40 strict-xfail instances; with --runxfail exactly those fail (382 others pass or skip)". 40 + 382 = 422 = the total. Arithmetic ✓. But the header (l.44) still says "each strict xfail fails on its own assertion" — consistent. The only row changed is the `quote_in` function's memory address (l.58–59: `0x778410d5b2e0` → `0x781bbed13400`) — a regeneration artifact, expected. ✓

---

## SECTION 2: LAW COMPLIANCE

| Law | Status | Evidence |
|---|---|---|
| Tests/docs only; never edit pipeline/, scripts/, segment_v1/ | **COMPLIANT** | Diff touches only `docs/audits/parallel/` (ll.1–62) and `tests/adversarial/` (ll.63–383). No pipeline/ or scripts/ hunks. |
| Never change what a check accepts to make something pass | **COMPLIANT** | The network test got *stronger* (l.375: prefix+type match replaces substring; l.377–379: both lookups required). test_f0's setter scan got *stronger* (l.316: unscanned-names assertion). No check weakened. |
| Nothing measured is never a pass (L-m) | **COMPLIANT** | Every behavioral claim in the docs is backed by a measured number: 422 = 379+40+3, 0 failed; the must-fail line measured against the pre-fix runner (PP-E30, l.28). |
| Fail closed (L-j) | **COMPLIANT** | NetworkRefused is a BaseException (l.221) so `except Exception` can't absorb it (l.277, documented at l.264). Missing key → KeyError (l.124). Unscanned names → assertion lists them (l.316). |
| Every pinned defect: xfail(strict=True, raises=AssertionError); preconditions: pytest.fail (H.control) | **COMPLIANT** | No new xfail marks in this diff (the 40 are pre-existing; the evidence file regenerated, count unchanged at 40). Preconditions in test_f0 use `H.control` (l.306). |
| CPU only, no network, no GPU | **COMPLIANT** | CUDA_VISIBLE_DEVICES= in the measured run; the toy gates use TEST-NET-1 (192.0.2.1, l.274, 276) — never answered, and the guard raises before any packet. |
| Keys by NAME, never printed/logged/written | **COMPLIANT** | `_key(name)` → `relay.get_key(name)` (l.137); relay's get_key returns the value, never prints (relay.py ll.56–85). frontier_blind's docstring: "never printed" (l.76). SPEND.jsonl records costs, not keys (l.93). |
| Only report what you can verify; if uncertain, say so | **COMPLIANT** (this review) | See the "not verifiable from the diff" notes in §1. |

**One nuance (not a violation):** PP-E31 (l.37) says "Grep the test tree for a key-file path before committing. **Detection: none automatic.**" — the law itself admits there's no automated check. That's honest, but it means the *next* regression to a hard-coded key path will not be caught by any test. A one-line test (import frontier_blind, assert it has no ENV_FILE/parse loop, or assert `_key`'s module is the relay) would close it. This is the diff's biggest *missed opportunity*, not a defect.

---

## SECTION 3: SECURITY

- **Secrets**: No key value appears in the diff. `KEY_LOADER = "/home/ultron/protocol_pulse/video_pipeline_v3/relay.py"` (l.92) is a *path*, not a secret — and PP-E31 explicitly blesses the main-tree relay path. relay.get_key checks os.environ first (relay.py l.69) — if the exam process's environment has a *stale* key, it wins over the .env; that's the documented precedence, not a flaw. **COMPLIANT.**
- **Injection**: No SQL, no shell. The only subprocesses are the probe commands in test_f0 (ll.342, 346, 349, 353–355) with literal argv, no shell=True. ✓
- **Input validation**: The toy gate's addresses are literals (TEST-NET-1). `no_resolve`'s message interpolates the caller's args via `!r` (l.241) — repr, safe. ✓
- **Rate limiting / paid-API exhaustion**: frontier_blind's budget guard: preflight (estimate, +25% margin, ll.98–107) + per-call reservation in `_call` (worst case: 2.5 chars/token, full output cap — documented at ll.101–104). The glm note (preflight admits → mid-run BudgetExhausted) is now *documented* (ll.101–104) but not *fixed* — the integrator marked it a note, not consensus, so this is compliant with the merge gate. The ERROR rows are reported, not silent. ✓
- **Filesystem writes**: SPEND.jsonl (l.93, pinned, fcntl-locked — `import fcntl` l.82, so concurrent runs serialize). The only other write risk — `__pycache__` in the main tree — is explicitly handled (ll.131–135) and *measured* (same .pyc mtime/count). Excellent. ✓

**Security: 95/100.** The only residual: relay.get_key's os.environ-first precedence means a stale exported var silently shadows the .env — documented house behavior, not this diff's problem.

---

## SECTION 4: FRONTEND QUALITY

N/A — this diff is tests + docs. No UI. (The stack section's UI/DB laws are not exercised here; noting that so the score isn't padded.)

---

## SECTION 5: BACKEND QUALITY

- **Concurrency**: `_TLOCK`-guarded lazy init (l.125); SPEND.jsonl under fcntl (l.82, 93); the exam's THREAD_SAFE contract documented (l.212). The `sys.dont_write_bytecode` toggle is process-global — a concurrent import in another thread during the exec_module window skips its .pyc write. Harmless (perf-only), but worth one docstring word. 
- **Error paths**: `spec_from_file_location` with a missing file → `spec.loader` is None → AttributeError, not a friendly KeyError. One `if spec.loader is None: raise KeyError(...)`-style guard would make the failure legible. (P2.)
- **Resource cleanup**: `sys.dont_write_bytecode` restored in `finally` (ll.134–135) ✓; the toy gate's socket... wait, the toy gate never *creates* a socket — it calls module-level lookups only, so no leak. test_f0's UDP probe closes in `finally` (l.323) ✓.
- **Idempotency**: `_GET_KEY` caches the function, not the key value — repeated calls re-resolve via relay (which caches .env in `_env_cache`, relay.py ll.19–20, 40–52). Note: relay's `_load_env` is itself check-then-act without a lock (relay.py ll.41–43) — but relay is read-only context, and the exam's `_TLOCK` serializes the first call, so the race window is: two threads both past `_GET_KEY`-empty check... no, they're serialized by _TLOCK. Fine.
- **Logging**: ERROR rows keep the exception + traceback tail (l.213). The refusal messages name the function (l.241) — exactly what PP-E30 demands. ✓

---

## SECTION 6: WORLD-CLASS GAP ANALYSIS

**Already excellent (say so, don't pad):**
- The layered-guard discipline (PP-E30: assert the guard under test by type + message prefix, and prove the must-fail against the *pre-fix* code) is genuinely rare. Most suites never notice that a substring assertion is satisfied by the wrong layer. This is the strongest thing in the diff.
- Fail-closed via BaseException (NetworkRefused/NetworkBlocked) so `except Exception` in code-under-test can't absorb the guard — documented *why* (conftest l.184–185). Textbook.
- Measured .pyc mtime/count before/after the relay load — nobody does this.

**Material gaps:**

1. **PP-E31's "Detection: none automatic" is a self-inflicted wound.** The whole diff exists because a hard-coded key path survived; the fix's own law says the next one won't be caught. A 5-line test — import the baseline module, assert its key resolution goes through a module whose `__file__` is the main tree's relay.py, and assert no `open(ENV_FILE)`-style parse remains — would make the law enforceable. (P1, not P0: nothing breaks today.)

2. **The runner's ERROR-row `why` format is load-bearing but unverified in the diff.** The new assertion (l.375) depends on the runner prefixing `NetworkRefused: ` to the stored message. If the runner's formatting ever changes, this test fails — good (fail-closed) — but the coupling is implicit. One line in the runner-facing test docstring noting the dependency, or a tiny unit test of the row formatter, would pin it. (P3.)

3. **`spec.loader is None` → AttributeError** (l.130): if the main tree moves, the failure is cryptic. One guard line. (P2.)

4. **Package-style modules** in pipeline/segment_v1 would false-positive in the unscanned-names check (l.315, `n + ".py"`). Currently passes, so no live impact; a `__init__.py`-aware existence check (or noting the assumption) would future-proof. (P3.)

---

## SECTION 7: SCORES

- Backend logic: **92** (logic correct; thread-safety by convention; spec.loader-None edge)
- Frontend/UI: **N/A** — tests+docs only; scored on what's present: n/a (would be unfair to penalize; excluded from OVERALL weighting)
- Error handling: **90** (fail-closed everywhere; the one cryptic AttributeError)
- Security: **95** (secrets by name, no prints, .pyc measured; residual = house precedence, not this diff)
- Performance: **93** (lazy key-loader; fcntl-locked ledger; the bytecode-toggle nit is perf-only)
- Law compliance: **97** (every law checked, no violation; the only deduction is PP-E31's "no automatic detection" — the law admits it)
- World-class gap: **88** (the layered-guard discipline is exemplary; the missing automated PP-E31 detection is the one material gap)
- **OVERALL: 92** (tests+docs diff; weighted on logic/error/security/compliance)

---

## SECTION 8: PRIORITY ACTION PLAN

P0 CRITICAL | — | — | — (none: 0 failed, 0 errors, all consensus findings addressed; nothing will break production)

P1 HIGH | Add the automated PP-E31 detection: a test asserting frontier_blind's key path goes through the main-tree relay (module's `__file__` endswith `video_pipeline_v3/relay.py`) and that no key-file parsing remains | tests/adversarial/test_f0_cpu_guard.py (new test) or a baselines test | PP-E31 (diff l.37) admits "Detection: none automatic" — the next hard-coded key path regression ships silently, exactly as this one did

P2 MEDIUM | Guard the relay load: `if spec is None or spec.loader is None: raise KeyError(f"key loader not found: {KEY_LOADER}")` | tests/adversarial/baselines/frontier_blind.py:129–130 | a moved/renamed main tree yields a cryptic `AttributeError: 'NoneType' object has no attribute 'exec_module'` instead of a legible failure (L-j wants fail-closed *and legible*)

P2 MEDIUM | Note the process-global bytecode-toggle window in the `_key` docstring | tests/adversarial/baselines/frontier_blind.py:131 | a concurrent import during exec_module silently skips its .pyc; harmless but undocumented (the glm-note discipline this diff otherwise exemplifies)

P3 LOW | Pin the ERROR-row format dependency: one docstring line in the network test noting that the assertion (l.375) depends on the runner prefixing `NetworkRefused: ` to `why` | tests/adversarial/test_moments_gates.py:368–371 | the coupling is implicit; a runner formatting change would fail the test correctly but puzzlingly

P3 LOW | Package-awareness in the unscanned-names check (`n + ".py"` misses `__init__.py` packages) | tests/adversarial/test_f0_cpu_guard.py:315 | a future pipeline package import false-positives the assertion; fail-closed, but a confusing DX

P3 LOW | `context_integrity`/`vo_fidelity` are unexercised by the test (only corpus "exclusions" runs) | tests/adversarial/moments_toy_gates/network_reverse.py:282–287 | dead-ish code; either exercise them or note they exist to satisfy the gate-attribute contract

---

## SECTION 9: THE ONE THING

The diff's own new law (PP-E31) ends with "Detection: none automatic" — close that loop before merging: one small test that fails when anyone reintroduces a hard-coded key path, because this entire batch exists to fix a defect that no test would have caught.

---

## SECTION 10: FINAL VERDICT

**Ready to merge.** Both consensus findings are fixed correctly and *stronger* than required (the guard now covers five lookups, not just the four the finding demanded; the test asserts the refusing guard by type+prefix, not substring), the notes are addressed with measured evidence, and the measured 422 = 379+40+3/0-failed run is consistent. The one thing I'd ask for before or immediately after merge: the automated PP-E31 detection test — the batch's own law admits the next regression of this class would ship silently, and that's the only material gap in an otherwise exemplary, fail-closed, measurement-first diff.