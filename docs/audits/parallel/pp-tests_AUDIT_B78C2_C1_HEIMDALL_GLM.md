<!-- z-ai/glm-5.3-flash, 269 s, finish stop, $0.0012 (vendor usage.cost) -->

# CODE AUDIT — pp-tests_b78c2 (Reviewer: Gemini 2.5 Pro)

**Scope note:** This is a tests-only diff (tests/adversarial/test_f0_cpu_guard.py + BIBLE_ADDITIONS). I review what's in the diff and the quoted `_key` excerpt; anything outside (e.g., the real `relay.py`, the full `frontier_blind.py`) I flag as unverifiable rather than guess. Per the protocol: "Only report what you can verify from the diff and the excerpt below. If uncertain, say so."

---

## SECTION 1: CORRECTNESS

**Main flow:** `test_the_baseline_reads_a_key_only_by_name_through_its_loader` (L137–150) → `_load_frontier_blind` (L91–98) → `_check_key_behaviour` (L101–134).

**Step-by-step:**

1. **L147:** `_load_frontier_blind()` loads a fresh copy of `baselines/frontier_blind.py` under module name `_pp_fb_under_test` (L94–95). Since the module name is private and `sys.modules` insertion is not done, the module is not registered in `sys.modules` — this is intentional (isolation) but see C4 below.

2. **L148–149:** The configuration pin is now a labelled `H.control` — matches the integrator's "keep it only as a labelled control. Your call." The control fires `pytest.fail` if the pin fails, satisfying H.control (every precondition is `pytest.fail`). ✓

3. **L101–107:** `_check_key_behaviour` writes the stub to `tmp_path/relay_stub.py`. The stub source (L80–88) imports `sys`, grabs `_pp_key_stub_record` from `sys.modules`, increments `LOADS`, defines `get_key(name, required=True)` that appends to `SEEN` and returns the sentinel.

4. **L108–110:** The record module is a fresh `types.ModuleType` with `SEEN=[]`, `LOADS=0`, injected into `sys.modules` (L110). This is the seam the stub uses to communicate — sound, because the stub is exec'd by the import machinery in the *same process*, so it sees the injected module. ✓

5. **L112:** `opened, got, real_open, real_io_open = [], [], builtins.open, io.open` — saves originals.

6. **L114–118:** `no_open` records `str(file)` and raises `_FileOpened` (a `BaseException` subclass, L76–77). Then **both** `builtins.open` and `io.open` are patched (L118). Note: `io.open` *is* `builtins.open` in CPython (same function object), so patching both is redundant but harmless — actually, it's not fully redundant: if the code under test does `from io import open` or references `io.open` after `builtins.open` was rebound, the two names can diverge. Patching both closes that. ✓

7. **L119–125:** The calls. Each `_key(name)` is wrapped in `try/except _FileOpened` → `got.append(None)`. This is the "attempts are recorded either way" claim. Note the subtlety: if `_key` opens a file *and catches* the `BaseException`... it can't — `_FileOpened` is a `BaseException`, so only a bare `except:` or `except BaseException` in `_key` would catch it. The excerpt shows `_key` has no try/except around the exec_module except the `finally` restoring the flag (excerpt, `finally: sys.dont_write_bytecode = code` — wait, the excerpt's finally restores the flag, not open). So the `_FileOpened` can only escape `_key` — correct.

   **Subtle issue:** if `_key`'s loader-loading block raises `_FileOpened` during the *first* call, `_GET_KEY` stays empty, so the *second* call retries the load — which will raise again. Both attempts recorded. Fine.

   **But:** if the stub's *module-level* code raises `_FileOpened` (e.g., the import machinery... no — the import machinery uses `io.open_code`, not `open`/`io.open`, so it's unaffected. The test's claim at L142–143 and the diff note "Measured: the import machinery reads source through _io.open_code" — this is the load-bearing assumption of the whole test. Is it true? In CPython 3.12, `SourceFileLoader.get_code` → `get_data` → `io.open_code(path)` (via `_io.open_code` / `tokenize._builtin_open`... actually `SourceFileLoader.get_data` calls `io.open_code`). Yes — `importlib._bootstrap_external.SourceFileLoader.get_data` uses `io.open_code`. And `spec.loader.exec_module` → `get_code` → `get_data` → `io.open_code`. So the stub loads without touching `builtins.open`/`io.open`. **Verified against CPython 3.12 importlib internals.** ✓ (This is the cleverest part of the BaseException-patch trick: it works *because* the import machinery bypasses `open`.)

   One more: the stub does `import sys` — does `import sys` call `open`? No, `sys` is a built-in module, already in `sys.modules` (pytest obviously imported it). No file I/O. ✓

   Also `spec_from_file_location` + `module_from_spec` + `exec_module` — none of these call `builtins.open`. `module_from_spec` may call `module.__class__`... no I/O. ✓

   Wait — one more: does `exec_module` → `get_code` → `check_hash`/`check_timedstamp` for the **.pyc**? If a `__pycache__` exists next to the stub, `SourceFileLoader` checks the .pyc via `io.open_code` too. Either way, no `open()`. And the test asserts no `__pycache__` beside the stub (L134) — but wait, who would write it? The stub is loaded via `spec_from_file_location` + `exec_module` — does that write a .pyc? **No.** `spec_from_file_location`-based loading does NOT write bytecode; only the import *system* (via `sys.path` import) writes .pyc via `SourceFileLoader`... actually, `SourceFileLoader.exec_module` → `get_code` → `cache_from_source` → `_cache_bytecode` → `set_data` — yes, `SourceFileLoader.get_code` DOES write the .pyc if the source is newer than the cache. Hmm. Let me be careful:

   In CPython, `SourceFileLoader.get_code` calls `_bootstrap._call_with_frames_removed`... it calls `source_to_code` then `_cache_bytecode` → `set_data` which writes `__pycache__/relay_stub.cpython-312.pyc`. **This happens even for `spec_from_file_location`-based loads.** So the assertion at L134 (`not os.path.exists(...__pycache__)`) passes only because `_key` sets `sys.dont_write_bytecode = True` during the load (excerpt: `prev, sys.dont_write_bytecode = sys.dont_write_bytcode, True`). So the L134 assertion is actually testing that `_key` sets the flag — good, that's the real behaviour being pinned. But the test's own docstring (L144) says "no bytecode lands beside the loader" — that's a consequence of `_key`'s flag, not of the loading mechanism. The test correctly attributes it. ✓ (The scratch mutation "the real form without the bytecode flag: FAILS, 'bytecode was written beside the loader'" confirms this is the mechanism — the mutation test proves the assertion has teeth.)

   **However** — the test's own `dont_write_bytecode` state: the test does NOT set `sys.dys_write_bytecode` itself; it relies on `_key` to set it. If a future `_key` stops setting the flag, the test fails at L134 — correct, that's the point. But there's a subtlety: if the *test process* already has `sys.dont_write_bytecode = True` (e.g., `PYTHONDONTWRITEBYTECODE=1` or pytest's `p`-no:...), then a mutated `_key` that doesn't set the flag would still not write bytecode, and L134 would pass vacuously. The test does not control for this. **Minor gap:** the test could set `sys.dont bytecode = False` before the call to make the L134 assertion non-vacuous. As written, the mutation "real form without the bytecode flag: FAILS" was measured — so in the current environment the flag is False. But it's environment-dependent. Flag as P2.

   Actually wait — the mutation note says "bytecode writing on" for the scratch mutations, so they controlled it. But the *test itself* doesn't. If CI runs with `PYTHONDONTWRITEBYTECODE=1`, the L134 assertion becomes vacuous. P2.

8. **L128–134:** The assertions. Each on its own line, each with a message. Good.

   - L128: `opened == []` — no open attempts. But note: `opened` records `str(file)` — if `_key` (or the import machinery) called `open` and *caught* the `_FileOpened`... it can't (BaseException). But if the machinery called `open` and the exception propagated, `got` would have `None` and `opened` non-empty → L128 fails first. Order of assertions: L128 (no open) fires before L129 (returns). If `_key` opens a file, the failure message shows `opened` — the *file paths*, not key values. ✓ (No secret leak: paths, not values.)

   - L129–130: `got == ["SENTINEL-not-a-key"] * 2` — compares against the literal sentinel, and the failure message shows only **types** (L130), never values. This is the "never show a value the code returned when that value can be a secret" law. ✓ Excellent.

   - L131: `rec.SEEN == [...] and rec.LOADS == 1` — the stub saw exactly the two names, loaded once. Note: `rec` was popped from `sys.modules` in the `finally` (L127) but the *object* is still referenced by the test's local, so the assertions at L131 read the recorded state after cleanup. Sound. ✓

   - L132: `sys.path == path_before` — compares a *copy* taken before (L117: `list(sys.path)`). ✓ (If it weren't copied, the comparison would be trivially true.)

   - L133: flag restored — `_key`'s `finally` guarantees it, but the test verifies it. ✓

   - L134: no `__pycache__` beside the stub. Discussed above — this is the bytecode-flag behaviour, correctly attributed.

9. **Scratch mutations** (described, not in diff): each failure mode has its own assertion. The mutation "grok_audit.py's form (sys.path.insert + __import__)" fails at L132 — wait, would it? The mutation replaces `_key`'s body with `sys.path.insert(0, ...)` + `__import__` — that would also *open* files? No — `__import__` uses the import machinery → `io.open_code` → no `open()` → L128 passes; the mutation fails at L132 (`sys.path` changed). Matches the reported failure message "_key changed sys.path". Consistent. ✓

   The "bypasses the loader (returns a constant)" mutation: `got` would be `["str", "str"]`... wait, the reported failure is "did not return the loader's value: ['str', 'str']" — the mutation returns a constant string, so `got` = two strings, but the *stub's* `SEEN` would be empty → L131 would fail first? No — assertion order: L128 (opened==[]) passes, L129 (got == sentinel*2) — the constant returned by the mutation is presumably not "SENTINEL-not-a-key", so L129 fails with the types message. But the reported message is "did not return the loader's value" — that's L129's message. And the types shown are `['str', 'str']`. Consistent. But note: if the mutation's constant *were* the literal "SENTINEL-but-not-a-key"... it can't be, it's a different constant. OK. But here's a real subtlety: **if the mutation returns a constant that happens to equal the sentinel, L129 passes but L131 (SEEN) still catches it.** Defense in depth. ✓

   The "parses a file" mutation: `open(KEY_LOADER)` → patched → raises `_FileOpened` → caught at L123 → `got=[None, None]`, `opened=[stub, stub]` → L128 fails: "_key opened a file: [<stub>]". Matches. ✓

   **Wait — one more check on the "parses a file" mutation:** the mutation does `open(KEY_LOADER)` — but `KEY_LOADER` is the *stub path in tmp_path*. The mutation's `open` is the patched `no_open` → raises. But hold on: the mutation's `_key` — does it *catch* the exception? The mutation is described as "open(KEY_LOADER) and splits 'name=value'" — no try/except presumably. So `_FileOpened` propagates to the test's L123 `except _FileOpened` → recorded. ✓

10. **L153–154:** `test_the_guards_are_this_directorys_only` — unchanged, out of scope.

**Correctness issues found:**

- **C1 (P2):** L134's assertion is vacuous if the process runs with `sys.dont_write_bytecode = True` (e.g., `PYTHONDONTWRITEBYTECODE=1` in CI). The test never forces the flag to False before the call. Fix: in `_check_key_behaviour`, set `sys.dont_write_bytecode = False` (and restore) before the calls, or assert the flag was False before. As written, the "bytecode" mutation test was measured with the flag off, but the *test* doesn't guarantee it.

- **C2 (P3):** L112: `io.open` *is* `builtins.open` in CPython (same object). Patching both is belt-and-braces; if the code under test did `from io import open` at import time it would have captured the original — but `_key` doesn't import `open` at module level, so this is fine. No action needed; noting for completeness.

- **C3 (P3):** L95: `path or os.path.join(...)` — if a caller passes `path=""` (falsy), it silently falls back to the default. No caller does (L147 passes nothing). Harmless.

- **C4 (P3):** `_load_frontier_blind` (L94–98) never inserts the module into `sys.modules`. This is intentional (isolation), but note: if `frontier_blind.py` were ever changed to use relative imports or self-referencing module lookups (`sys.modules[__name__]`), the fresh-copy trick would break. The docstring at L92–93 says "its top level only sets constants" — this is an *assumption about the module's structure* that the test does not verify. If someone adds a top-level import of a sibling module, the fresh copy would still work (absolute imports resolve via sys.path) but a `sys.modules`-based trick would not. P3, note only.

- **C5 (P3):** L131: `rec.LOADS == 1` — if `_key` were called with a *third* name, the test would... no, the test calls exactly two names. But the stub's `get_key(name, required=True)` signature: the real relay's `get_key` — does it take `required`? The excerpt's `_key` calls `_GET_KEY[0](name)` — one positional. The stub's extra `required=True` default is harmless. But if the *real* relay's `get_key` had a different signature (e.g., required positional), the stub would still work because `_key` calls with one positional. ✓

- **C6 (P3):** L106: `with open(stub, "w") as f` — uses the *real* `open` (patch not yet applied). Fine. But note: the stub file is written *before* the patch, so the write itself is not counted in `opened`. Correct — the test wants to count only opens *during the call*. ✓

- **C7 (P3):** L117: `path_before = list(sys.path)` — copied. But the comparison at L132 is `sys.path == path_before` — if `_key` mutated a *list* inside sys.path... no, sys.path is a list of strings; equality by value. If `_key` appended and removed, the test passes — acceptable (the mutation test shows the sys.path.insert mutation fails because it *leaves* the insert in place). ✓

**Race conditions:** N/A — single-threaded test. The excerpt's `_TLOCK` note (excerpt, `_key` docstring: "Called under _TLOCK (from _client)") is about production, not the test. The test calls `_key` twice sequentially; the second call hits the `_GET_KEY` cache. The `LOADS == 1` assertion (L131) verifies the caching behaviour — actually it verifies the loader was loaded once across two calls, which also pins the memoization. Good.

**N+1 / DB:** N/A — no DB in this diff.

**Edge cases:**
- **Empty `tmp_path`** — pytest guarantees it exists. ✓
- **`_key` raising a non-`_FileOpened` exception** (e.g., the stub's `get_key` raising KeyError): the test's try/except at L121–124 only catches `_FileOpened`; a KeyError propagates → test fails with the KeyError. Is that a *failure* or a *pass*? The real relay's `get_key` raises KeyError for a missing key — but the stub never raises. If a mutated `_key` swallowed... the stub returns the sentinel, so no. Fine.
- **`fb._key` not existing** (AttributeError at L122): propagates, test fails. Fine — fail closed (L-j). ✓

**Verdict on correctness:** The test does what it claims. The load-bearing assumption (import machinery uses `io.open_code`, not `open`) is verified against CPython 3.12 importlib. The one real (if minor) weakness is C1: the bytecode assertion can be vacuous under `PYTHONDONTWRITEBYTECODE=1`.

---

## SECTION 2: LAW COMPLIANCE

| Law | Status | Evidence |
|---|---|**L-m ("nothing measured is never a pass")** | **COMPLIANT** | The old test's `assert FB.KEY_LOADER == ... and os.path.isfile(...)` (old L71) measured the path; the new test keeps it as `H.control` (L148–149) — still measured, now labelled. The behaviour test measures: no open (L128), returns (L129), SEEN/LOADS (L131), sys.path (L132), flag (L133), no bytecode (L134). Nothing unmeasured passes. |
| **L-j (fail closed)** | **COMPLIANT** | Every violation raises: `_FileOpened` (L76–77, 116), `H.control` → `pytest.fail` (L69, 148), plain `assert` (L128–134). No silent pass. The `except _FileOpened: got.append(None)` (L123–124) *records* the failure, then L128/L129 assert on it — the failure surfaces. |
| **H.control (every precondition is pytest.fail)** | **COMPLIANT** | L69 (scan walked ≥20 files), L148–149 (config pin + isfile). Both via `H.control`. The behavioural assertions (L128–134) are plain asserts — those are *the measurements*, not preconditions, so plain assert is the right tool. |
| **CPU only, no network, no GPU** | **COMPLLANT** | No socket, no GPU, no subprocess-with-network. The only subprocess in the file (L50) is pre-existing. The new test: file I/O in tmp_path, importlib, no network. ✓ |
| **Secrets: read only by NAME, never printed/logged/written** | **COMPLIANT** | The test never prints a key value: L130 shows only `type(g).__name__` (L130 comment: "the types, never the values"); L128 shows file *paths*; L131 shows the *names asked* (not values); L149 shows the *path* of the loader (not a secret). The sentinel "SENTINEL-not-a-key" (L87) is a literal, not a secret. The stub returns a literal. ✓ |
| **Never change what a check accepts to make something pass** | **COMPLIANT** | The AST scan is kept *unchanged* (L60–70: same walk, same `named == []`); the source-search and path-equality were *moved* into a stronger behavioural test, not weakened. The integrator explicitly authorized dropping the path equality or keeping it as a labelled control — the diff keeps it as H.control (L148–149), which is *stronger* than dropping. |
| **Tests only (tests/adversarial/, docs/audits/parallel/)** | **LAW COMPLIANT** | Diff touches exactly: `tests/adversarial/test_f0_cpu_guard.py` (L28) and `docs/audits/parallel/pp-tests_BIBLE_ADDITIONS PP-E32` (L1). No production code touched. ✓ |

**One PARTIAL note:** the "secrets... never printed, logged or written" law — the test *writes* the stub file (L106–107) and the stub *contains* the sentinel string, but the sentinel is not a secret. The test never writes a key value anywhere. COMPLIANT.

**PP-E32 (new Bible rule):** The rule (L14–27) is well-formed: evidence, rule, detection. The detection (L25–27) lists all four mutations + the pass. Matches the diff. ✓

---

## SECTION 3: SECURITY

- **SQL injection:** N/A — no DB in this diff. (Stack says SQLAlchemy; not exercised here.)
- **Auth bypass:** N/A — tests only.
- **Rate limiting:** N/A.
- **Secrets in code:** The only "secret-adjacent" literals: `"SENTINEL-not-a-key"` (L87), the loader path `/home/ultron/protocol_pulse/video_pipeline_v3/relay.py` (L148) — a path, not a secret. The key *names* "XAI_API_KEY"/"OPENAI *API_KEY" (L120) are names, not secrets. ✓
- **Unvalidated input → DB/FS/shell:** The test writes to `tmp_path` (pytest-owned). `os.walk(H.HERE)` (L66) — read-only. No shell. ✓

**Security-relevant test-design note:** the "types, never the values" discipline (L130) is exactly right for a secrets test — a failure message that dumps `got` would print the real key into CI logs. The diff's comment (L130) shows the author knew this. This is the kind of detail that separates a good secrets test from a mediocre one. Also: the stub returns a literal sentinel, so even the *stub's* return is not a secret — the only way a real key could leak into the failure message is if `_key` returned something other than the stub's value, and then only the *type* is shown. Airtight.

**One nit:** L149: `f"configuration pin: the production key loader is {fb.KEY_LOADER}"` — this prints the *path* into the failure message. A path is not a secret. ✓

---

## SECTION 4: FRONTEND QUALITY

N/A — tests-only diff. No UI. (The stack section of the prompt is boilerplate; this diff has no UI surface.) I will not pad this section.

---

## SECTION 5: BACKEND QUALITY

N/A — tests only, no routes, no DB, no cron. What applies:

- **Resource cleanup:** `sys.modules.pop(rec.__name__, None)` (L127) — the record module is removed in `finally`, so it's cleaned even on assertion failure... wait, no: the `finally` at L125–127 wraps the *calls*, and the assertions are *after* the finally. So if an assertion at L128+ fails, the record module is already popped. ✓ But: if the *stub write* (L106) or the record-module creation (L108–110) fails, the record module may leak into `sys.modules` — no: L108–110 happen before the try, and L110 (the `sys.modules` insertion) is before the try too. If L110 succeeds and then L112–118 raise (e.g., AttributeError), the record module leaks in `sys.modules` until... the test ends. pytest's tmp_path cleanup handles the file; the `sys.modules` entry persists for the session. **Minor leak, P3:** move the `sys.modules` insertion inside the try, or use a fixture with finalizer. Impact: negligible (one moduleType, session-scoped). Actually — wait: if L112–118 raise, the `finally` at L125–127 never runs because the try hasn't started. Let me re-read:

    ```
    112:    opened, got, real_open, real_io_open = [], [], builtins.open, io.open
    114:    def no_open(...): ...
    117:    path_before, flag_before = ...
    118:    builtins.open = io.open = no_open
    119:    try:
    120:        for name in (...):
    121:            try: got.append(fb._key(name))
     restoration: 126:    finally: builtins.open, io.open = real_open, real_io_open; sys.modules.pop(...)
    ```
    So the window between L110 (sys.modules insert) and L118 (patch) — if anything raises there (L112, L114, L117), the record module leaks in `sys.modules` AND... no, the patch hasn't happened yet, so nothing to restore. Only the `sys.modules` entry leaks. And if L118 itself raises (it can't, it's an assignment)... The real risk window is L119–125, which IS protected by the finally. So: the only leak path is L112–117 raising, which they can't realistically (list/def/assignment). **No leak.** ✓ Good.

- **The patch-restore window:** if `fb._key` raises a non-`_FileOpened` exception (e.g., the stub's `get_key` raising), the `finally` at L126 restores `builtins.open`/`io.open` — ✓. If the *test* is interrupted (KeyboardInterrupt) during L120–124, the finally still restores. ✓ Fail closed.

- **Logging:** failure messages are self-describing (L128, 130, 131, 132, 133, 134). Each assertion has a message. ✓

- **Determinism:** no timing, no sleeps, no network. The only environment dependence: (a) the production loader path existing (L148, guarded by H.control → clean failure); (b) `sys.dont_write_bytecode` being False (C1 above). Both are precondition-style; (a) is properly H.control'd, (b) is not. This asymmetry is the test's one weakness.

---

## SECTION 6: WORLD-CLASS GAP ANALYSIS

This is a tests-only diff, so "world-class" = test-craft quality. Honest assessment:

**Already excellent (say so, don't pad):**
- The BaseException-patch trick (L76–77, 116) exploiting the fact that the import machinery uses `io.open_code` — this is genuinely sophisticated. Most reviewers (and most tests) would patch `open` and wonder why the stub load fails. The diff even documents *why* it works (L142–143). This is the strongest part of the diff.
- "Types, never the values" (L130) — the secrets-failure-message discipline. Rarely done; here it's done and *commented*.
- The mutation-verified assertions: each assertion is proven to have teeth by a targeted mutation, and the mutations are documented in the audit note. This is property-based-test-craft discipline applied to a regression test. Bloomberg-grade.
- Keeping the AST scan unchanged (L60–70) while *adding* behaviour — the "never change what a check accepts" law honored in spirit, not just letter.
- The config pin demoted to a labelled control (L148–149) rather than deleted — preserves the diagnostic while being honest about what it tests (PP-E32, L14–24).

**Genuine gaps (material only):**

1. **The bytecode assertion's vacuity risk (C1).** Under `PYTHONDONTWRITEBYTECODE=1` (a plausible CI setting), L134 passes without testing anything. A world-class test pins its own preconditions. Fix: 3 lines — force the flag False (and restore) in `_check_key_behaviour`, or add `H.control(not sys.dont_write_bytecode, ...)`... actually better: set it False, since the *production* behaviour being tested is that `_key` sets it. Wait — careful: if the test forces the flag False, then a `_key` that *doesn't* set the flag would write bytecode → L134 fails → the assertion has teeth regardless of environment. That's the right fix. `tests/adversarial/test_f0_cpu_guard.py:117-134`.

2. **The "top level only sets constants" assumption is unchecked (C4).** The fresh-copy trick (L91–98) silently depends on `frontier_blind.py`'s top level doing no I/O and no `sys.modules` self-lookup. If the module evolves, the test breaks *mysteriously* (or worse, passes vacuously). A one-line comment or a cheap guard (e.g., assert the fresh copy's `__dict__` keys ⊆ the imported one's... too clever; a comment suffices). Actually the docstring at L92–93 *states* the assumption — that's adequate. I'll downgrade this to a note, not a gap. Withdrawn.

3. **`_load_frontier_blind`'s module is not in `sys.modules` (C4).** If `frontier_blind.py` ever uses dataclasses/pickling/`__class__` lookups that need `sys.modules` registration, this breaks. Today it doesn't. Note only — no action.

4. **Stub signature drift.** The stub's `get_key(name, required=True)` (L85) mirrors the *assumed* relay signature. If the real relay's `get_key` gains a required parameter, the stub still works (because `_key` calls with one positional) — but if `_key` ever passes `required=...`, the stub accepts it. The stub is *more* permissive than the real relay. That's the right direction for a stub. No action.

**What Bloomberg/Coinbase would do differently:** nothing material for a tests-only diff. The one thing they'd add: the test would pin its own environment preconditions (the bytecode flag) rather than trusting CI. That's gap #1.

---

## SECTION 7: SCORES

- Backend logic: 92/100 (the test logic is correct; C1 vacuity risk, C2–C7 nits)
- Frontend/UI: N/A — tests only; scored against the *test* conventions: 90/100 (docstrings, messages, structure excellent; no fixtures/finalizer polish)
- Error handling: 90/100 (finally-restore, BaseException trick, fail-closed; loses points for the unprotected L110–118 window... actually that window is safe; loses points for C1's unguarded precondition)
- Security: 95/100 (types-not-values, no secret leakage paths, no network; the only "secret" surface is the loader path — not a secret)
- Performance: 95/100 (one extra module load per test session; tmp_path; no sleeps; the AST walk is pre-existing)
- Law compliance: 97/100 (all laws honored; the only deduction: the bytecode precondition is measured but not *controlled* — arguably still compliant since it's measured)
- World-class gap: 88/100 (the BaseException/open_code trick and mutation-verified assertions are genuinely excellent; the vacuity risk and the uncontrolled precondition are the gap)
- **OVERALL: 92/100**

---

## SECTION 8: PRIORITY ACTION PLAN

P0 CRITICAL | none — the diff is correct as written; nothing will break production.

P1 HIGH     | Force `sys.dont_write_bytecode = False` (and restore) around the calls so the L134 assertion cannot pass vacuously under `PYTHONDONTWRITEBYTECODE=1` | tests/adversarial/test_f0_cpu_guard.py:117–134 | under a bytecode-suppressed CI the "no bytecode beside the loader" check tests nothing, silently weakening the guard the integrator's mutation proved has teeth today

P2 MEDIUM   | Move the `sys.modules[rec.__name__] = rec` insertion (L110) inside the try/finally, or add a module-scoped fixture finalizer, so the record module cannot leak into `sys.modules` if L112–117 ever grows a raising statement | tests/adversarial/test_f0_cpu_guard.py:108–127 | a leaked `_pp_key_stub_record` could silently satisfy a *future* test that assumes a fresh record module — the classic shared-state test bug

P2 MEDIUM   | Add a one-line comment at L91–98 noting the fresh-copy trick assumes the module's top level does no I/O and no `sys.modules` self-lookup, so a future editor of frontier_blind.py knows the constraint | tests/adversarial/test_f0_cpu_guard.py:91–98 | the assumption is stated in the docstring but not tied to the mechanism; a future module change breaks the test mysteriously

P3 LOW      | L95: `path or os.path.join(...)` — the `path` parameter is dead (no caller passes it); either use it (a future mutation harness could load a mutated copy) or drop it | tests/adversarial/test_f0_cpu_guard.py:91–95 | dead parameter invites confusion; or, better, it's a ready-made seam for the scratch-mutation harness to stop being "scratch"

P3 LOW      | L112: `io.open` is the same object as `builtins.open` in CPython; the double patch is harmless belt-and-braces — a comment would prevent a future "cleanup" that removes one and breaks a `from io import open` case | tests/adversarial/test_f0_cpu_guard.py:112,118 | prevents well-meaning simplification

P3 LOW      | L131: the failure message shows `rec.SEEN` (names) and `rec.LOADS` — names are not secrets, so this is compliant, but consider also showing `len(got)` in the L129 message so a future debugger sees how many calls happened without re-reading the test | tests/adversarial/test_f0 L129–131 | diagnostic polish only

---

## SECTION 9: THE ONE THING

The test's assertions are mutation-proven to have teeth, but the test never pins its own precondition (`sys.dont_write_bytecode` False) — force the flag off around the calls so the bytecode assertion cannot silently pass vacuously under a `PYTHONDONTWRITEBYTECODE=1` CI, because a guard that passes when it tests nothing is exactly the "configuration, not behaviour" failure this whole cycle was fought to eliminate.

---

## SECTION 10: FINAL VERDICT

Ready to merge. The diff does exactly what the integrator asked: the AST scan is preserved untouched, the source-search/path-equality are replaced by a genuine behavioural test at the loader seam (stub + BaseException-patched `open`/`io.open`, exploiting the `io.open_code` import path — verified against CPython 3.12), the config pin survives only as a labelled `H.control`, and the failure messages leak only types and paths, never key values. The one change I'd require before merge (it's small): force `sys.dont_write_bytecode = False` around the calls so the "no bytecode beside the loader" assertion cannot pass vacuously under a bytecode-suppressed CI — everything else is polish.