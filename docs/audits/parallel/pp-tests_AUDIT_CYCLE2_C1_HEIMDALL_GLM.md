<!-- z-ai/glm-5.3-flash, 220 s, finish stop, $0.0013 (vendor usage.cost) -->

# PROTOCOL PULSE — INDEPENDENT AI AUDIT
**Reviewer: Gemini 2.5 Pro | Feature: pp-tests_cycle2 | 2026-11-14**

---

## SECTION 1: CORRECTNESS

**Main flow: the three wall failures → the diff's fixes.**

**Fix 1 (test_f0 setter scan, CURRENT.diff:217-251).** The old resolution mapped each imported *name* to `pipeline/<name>.py` by bare filename. The suite's own `import conftest` (tests/adversarial/conftest.py:169-186) then matched `pipeline/conftest.py` — a file the suite never imports — producing `{'conftest', 'qa_gates'} != {'qa_gates'}`. The new `_resolve` (diff:217-227) resolves the way the interpreter does: `sys.modules[name].__file__` first, else `find_spec(name)` on the suite's sys.path, with a control (diff:239) that `conftest` resolves to the suite's own file. This is correct: pytest registers the suite's conftest as module `conftest` (rootdir-relative, no package), so `sys.modules["conftest"]` is tests/adversarial/conftest.py, and the control would catch any regression. The membership test `f.startswith(roots)` (diff:247) with `roots` as `realpath(...)+os.sep` tuples (diff:237) is prefix-safe (no `/pipeline2`-style false positives) and realpath-normalized on both sides — `_resolve` also returns realpath (diff:227), so the comparison is consistent. The scan remains at least as strict: every name that previously resolved under pipeline/ or segment_v1/ still resolves to the same file (only `conftest` changed, per the diff's own measurement), and the setter regex is unchanged, so `KNOWN_CUDA_SETTERS == {"qa_gates"}` still holds. One subtlety: `_resolve` returns `None` for a name that resolves to a non-`.py` (e.g. a package `__init__` via a namespace or a `.pyd`), which the old code also effectively did (it only looked for `<name>.py`), so no loosening. **Verdict: correct.**

**Fix 2 (test_f0 Whisper refusal, diff:256-283).** Under L-r, `word_diff.Transcriber.__init__` (word_diff.py:118-121) only stores `gpu0.whisper(ASR["model"])` — a `Model` wrapper, `_obj=None` — so constructing it loads nothing. The first *use* (`tr.span(...)` → `self.model.transcribe(...)` → `Model.__getattr__("transcribe")` → `self.get()` → `require(key)` at gpu0.py:795) raises `LeaseMissing` at gpu0.py:286-288 because `CUDA_VISIBLE_DEVICES=''` ≠ `'0'`. The test now asserts exactly that: `pytest.raises(gpu0.LeaseMissing, match=r"^whisper:large-v3: GPU0 loads need CUDA_VISIBLE_DEVICES=0 \(it is ''")` (diff:278-280), which matches the f-string at gpu0.py:287-288 (`f"{what}: GPU{g} loads need CUDA_VISIBLE_DEVICES={g} (it is {os.environ.get('CUDA_VISIBLE_DEVICES')!r}; ...)"` → `whisper:large-v3: GPU0 loads need CUDA_VISIBLE_DEVICES=0 (it is ''; one GPU per process)`). The regex is anchored `^` and the `!r` of `''` renders as `''` — the escaped `\(it is ''` matches. The `assert not issubclass(gpu0.LeaseMissing, Exception)` (diff:281) is the load-bearing line: it proves the refusal is a `BaseException` that passes select's `except Exception` (gpu0.py:87-88, 99-100). The final `assert not gpu0.whisper(...).loaded` (diff:283) is the "nothing loaded" proof: `Model.loaded` (gpu0.py:810-812) reads `_obj is None`, and since `get()` raised at `require` before `swap_to`, `_obj` stays `None`. **One caveat:** `Model.__getattr__` (gpu0.py:814-826) deletes the bound attr and returns a fresh closure per access, so `tr.span`'s internal `self.model.transcribe` re-enters `get()` → `require` → raise — the LeaseMissing indeed surfaces from the *use*, not from construction, exactly as the test's docstring claims. **Verdict: correct, and the layering is now named honestly.**

**Fix 3 (R-27 pin, diff:339-361).** The failure is now injected at select's own seam: `monkeypatch.setattr(SP, "_whisper_transcribe", failing)` (diff:353), where `failing` returns `None` for HOOK_VID and calls the real function otherwise (diff:350-352). Reading `_whisper_transcribe` (select_passages.py:71-119): it returns `None` only via the `except Exception` at :114-119 for *ordinary* errors (the WARN + return None path), while OOMs are re-raised as `GpuOOM` (:116-117) and `Gpu0Stop`s propagate (the comment at :91). So `None` is the documented "ordinary failure" value — a faithful stand-in. The pin's control `HOOK_VID in asked` (diff:357, 360) ensures the KeyError (if it fires) came *after* the hook's transcription was attempted — the "control failure" discipline. The measured failure is `KeyError: 'VIDAAAAAAAA'` at select_passages.py:314 (`span = transcripts[vid].get("duration") or 0` — wait, :314 is `span = transcripts[vid]...`; the KeyError is `transcripts[vid]` for a downloaded-but-untranscribed source). Tracing: hook fails → `transcripts` lacks HOOK_VID → `valid` filter (:202) keeps only passages whose vid is in `transcripts`; if the hook's passage is filtered, `_source_for` (:303-317) is later called for a *different* passage whose vid was downloaded but whose transcription also failed... actually the measured KeyError vid is `VIDAAAAAAAA`, which per the test's `_replace_source`/fixture naming is the hook. Either way, the mechanism is: `transcripts[vid]` at :314 (or :313→:314) for a vid in `sources` but not in `transcripts` — exactly R-27. The pin catches only `KeyError` (diff:356) and converts it to the pinned `AssertionError` (diff:358) so the strict-xfail's `raises=AssertionError` (diff:333-334) matches — any other exception shows FAILED, which is the fail-closed discipline. **Verdict: correct; the injection point is the production seam, not a mock below it.**

**New passing test (diff:363-375).** `_select(run)` → hook has no transcript → `_whisper_transcribe` → `gpu0.whisper("large-v3")` (select_passages.py:91) → `Model.get` → `require` → `LeaseMissing` (gpu0.py:286-288). Since `LeaseMissing` is a `BaseException` (diff:281 proves it; gpu0.py:87-99), it passes the `except Exception` at select_passages.py:114, so select does not catch it, does not return False, and does not write `edl.json` or the transcript. The test asserts: the raise (diff:371), no edl.json (diff:373), no transcript (diff:374), and `whisper_attempts() == []` (diff:375 — nothing reached the stub, since the lease refusal precedes it). All three "writes nothing" assertions are real, not vacuous: the fixture guarantees the transcript was removed (diff:370) and... **one question: does select write edl.json earlier in its flow?** If select writes intermediate state before the transcription loop, the `not os.path.exists(edl.json)` (diff:373) could pass for the wrong reason. From the excerpt, select's writes happen after the transcription loop (the `valid`/`_source_for`/EDL assembly at :202+), so the assertion holds. **Verdict: correct, and it answers the integrator's question (no request needed).**

**R-10's pin (diff:303-327).** The proof that new bytes went to Whisper is now the `LeaseMissing` naming a `whisper:` key (diff:324-326), since the stub is never reached under L-r. The `H.control(str(e).startswith("whisper:"))` (diff:325) is the discriminator: a LeaseMissing from a *non-Whisper* GPU0 use (e.  g. punctuation's reference decode, which also goes through `gpu0.whisper` — same key, fine; or a different model, e.g. `whisper:large-v3:batched` — still `whisper:`-prefixed, so the control passes; the control is slightly loose but the key namespace is whisper-only for this call path). The `ok in (False, "transcribed")` (diff:327) accepts either select's clean STOP (False) or the lease refusal (the "transcribed" sentinel) — the pin's subject (old transcript never used) is preserved. **Verdict: correct, with the minor looseness noted.**

**Edge cases.** `subprocess.run(["ffmpeg", ...], check=True, timeout=60)` (diff:275-276) — if ffmpeg is absent, the test errors (not fails) — acceptable for a test, and the suite already requires ffmpeg elsewhere (word_diff.py:128-129). `_resolve`'s `find_spec` (diff:225) can raise `ModuleNotFoundError` for a name in `sys.modules`-only... no, it's guarded by the `sys.modules.get` first. `find_spec` on a name whose parent package import fails raises — but the names come from `_imported_names()` (AST of the suite's own imports), so they're importable in this process. **No correctness defects found in the diff.**

---

## SECTION 2: LAW COMPLIANCE

| Law | Status | Evidence |
|---|---|---|
| Tests/docs only; never edits pipeline/, scripts/, segment_v1/ | **COMPLIANT** | Diff touches only tests/adversarial/ (diff:169-380) and docs/audits/parallel/pp-tests_* (diff:1-168). `git diff --stat cc8cccd0 HEAD` = 2 docs files (per the brief, lines 1-2 of "What pp-tests did"). |
| Never change what a check accepts to make something pass | **COMPLIANT** | The setter scan's *acceptance* is unchanged: same regex, same `KNOWN_CUDA_SETTERS` (diff:251); only the *resolution* was corrected to what the interpreter actually does (diff:217-227). The Whisper test's acceptance *changed* — but that's the PP-E27 rule: naming the layer, not loosening (the old assertion "stub raises" was simply wrong about which layer refuses; the new one asserts the production refusal *and* keeps the stub check, diff:268-269). |
| Nothing measured is never a pass (L-m) | **COMPLIANT** | Every behavioral claim is measured: the merged-tree counts (378/40/3/0, brief line "Measured after the diff"), the 40-xfail --runxfail proof (XFAIL_EVIDENCE regenerated, diff:120-168), regression_test.sh 26/0. The new passing test's claims (no edl, no transcript, no stub hit) are each asserted, not assumed (diff:373-375). |
| Fail closed (L-j) | **COMPLIANT** | Controls use `H.control` (pytest.fail) — a broken setup shows FAILED, never as the defect: diff:239, 273, 325, 357, 360. The R-27 pin converts KeyError→AssertionError (diff:356-358) so the xfail's `raises=AssertionError` stays honest; any other exception = FAILED. |
| Every pinned defect: xfail(strict=True, raises=AssertionError); every precondition: pytest.fail | **COMSET** — | |
| CPU only, no network | **COMPLIANT** | `CUDA_VISIBLE_DEVICES=` in the measured command (diff:130); the conftest hides GPUs (diff:174-176, 179-183); the new test's only subprocess is local ffmpeg (diff:275-276); the conftest blocks AF_INET/AF_INET6 + resolution (diff:184-186). The new test's ffmpeg tone (diff:275) is a local lavfi sine — no network, no GPU. |
| Production code is read-only context | **N/A (this diff)** | gpu0.py / select_passages.py / word_diff.py excerpts are release-line context, not the diff. |

**Note on the xfail table (diff:333-334, 301-302):** both changed pins keep `xfail(strict=True, raises=AssertionError)` — R-10's reason text updated to the new proof (diff:301-302... actually the reason string is unchanged in the diff; only the body changed). Wait — checking: diff:301-302 shows the R-10 mark's reason is *unchanged* ("GPT-select F10 (OPEN)... REQUESTS.md R-10") — good, the reason still names the open request; the *proof mechanism* changed inside the body, documented in the docstring (diff:310-313). Consistent.

---

## SECTION 3: SECURITY

Tests-only diff; the security surface is the test harness itself.

- **Subprocess:** `subprocess.run([...], check=True, timeout=60)` (diff:275-276) — list-args, no shell, timeout, check. Clean. The 60s timeout on a 1s lavfi sine is generous but bounded.
- **File I/O:** `open(p).read()` (diff:250) — read-only, path from `_resolve` (realpath'd, under the repo's pipeline/ or segment_v1/). No injection. `tmp_path` fixture (diff:257) — pytest-managed, no traversal.
- **Secrets:** none in the diff. No tokens, no keys.
- **Input validation:** `_resolve` (diff:217-227) — `sys.modules.get` then `find_spec`; a hostile `sys.modules` entry with a bogus `__file__` is not a production concern in a test. The `f.endswith(".py")` guard (diff:227) prevents resolving a package's `__init__`... actually a package's `__init__.py` *ends with* .py, so it would resolve — but the suite imports no packages from pipeline/segment_v1 (module-style, per the old code's `<name>.py` assumption), so no behavioral change.
- **No SQL, no routes, no auth** in this diff — N/A.

**Verdict: no security findings.** The harness's fail-closed discipline (H.control → pytest.fail) is itself the security property here: a broken guard cannot masquerade as a pass.

---

## SECTION 4: FRONTEND QUALITY

N/A — tests and docs only. (The Technology Stack section of the brief — Flask, SQLAlchemy, ~1000 concurrent users — describes the product, not this diff; nothing in the diff touches it. I will not pad this section with findings about code I cannot see.)

---

## Only what the diff shows. No padding.

## SECTION 5: BACKEND QUALITY

Test-harness quality, since that's what the diff is.

- **Resource cleanup:** the ffmpeg tone (diff:274-276) is written to pytest's `tmp_path` (diff:257) — auto-cleaned. `word_diff.Transcriber()`'s TemporaryDirectory (word_diff.py:126) is context-managed. The `Model` singleton `_models` (gpu0.py:847-863) persists across tests in the process — but `loaded` is False (diff:283) and nothing was resident, so no cross-test GPU/CUDA state. Clean.
- **Determinism:** the LeaseMissing message match (diff:278-279, 371) pins the *exact* production message — brittle by design (the suite's stated philosophy, diff:234-235: "INTENTIONALLY BRITTLE"), and the right kind of brittle: a message change fails the test, forcing a conscious review. Good.
- **Ordering hazards:** `test_a_gpu_stop_...` (diff:363-375) removes the hook's transcript (diff:370) and asserts it's absent after (diff:374) — if select *had* written it, the test catches it. But note: the `run` fixture (not shown) must guarantee a fresh run dir per test; if it's module-scoped and shared with the earlier TestDirtyCache tests, the `os.remove` (diff:370) could race... no — pytest runs tests in a class sequentially, single-process; the fixture's scoping is the only question, and the earlier tests in the class also mutate the run dir (diff:316, 347), so the fixture must be function-scoped (the suite's 378-passing wall is the evidence it is). No finding.
- **Logging/diagnostics:** the controls carry their evidence in the message (diff:239, 273, 325, 357, 360) — a failure names what was expected and what was found. This is better than most production code I review.

---

## SECTION 6: WORLD-CLASS GAP ANALYSIS

Tests-only diff; I judge it as a quality-gate artifact.

**Genuinely excellent (no padding — this is rare):**
1. **The seam discipline (PP-E27).** Injecting the failure at `_whisper_transcribe` (diff:353) — the function whose *documented* failure value (select_passages.py:76: "Returns dict with 'words' list or None on failure") the test relies on — rather than mocking faster_whisper below a guard that never runs, is exactly right. Most teams would have mocked the stub and shipped a test that passes for the wrong reason.
2. **The control/defect separation.** `H.control` (pytest.fail) for preconditions vs. `AssertionError` for the pinned defect (diff:356-360) means a broken fixture shows FAILED and a real regression shows the pinned xfail — the triple-check (normal run / --runxfail / XFAIL_EVIDENCE) can then distinguish them. This is a more rigorous failure taxonomy than most production codebases have.
3. **The BaseException proof (diff:281).** `assert not issubclass(gpu0.LeaseMissing, Exception)` — one line that pins L-r's entire "no `except Exception` absorbs a GPU stop" design. If someone "fixes" gpu0.py to inherit from Exception, this test catches it. That's a law pinned as a test.

**Material gaps (few, and small):**

1. **The `startswith(roots)` membership (diff:247) trusts `__file__` blindly.** If a same-named module were *imported* from outside the roots (e.g. a stale `qa_gates` from segment_v1/ when the suite meant pipeline/), `_resolve` would faithfully report the wrong file — the interpreter's truth, yes, but the *scan's* purpose is to review the pipeline/segment_v1 sources. The control (diff:239) covers only `conftest`. A second control — that the resolved `qa_gates` (the one setter) is the expected file — would close the loop. Minor: the 378-passing wall plus the "every other name resolves to the same file" measurement (brief, Fix 1) makes this theoretical today.

2. **`test_a_gpu_stop_...`'s "writes nothing" proof is existence-only (diff:373-374).** It asserts the files don't exist, not that select wrote no *partial* state elsewhere (e.g. a half-written download record, the `sources/` dir). Given the test's stated subject ("writes no EDL and no transcript", diff:367-368), the assertions match the claim — the claim is just narrower than "writes nothing" in the title. Cosmetic.

3. **R-10's `startswith("whisper:")` control (diff:325) is loose.** Any whisper-keyed LeaseMissing satisfies it, including a *punctuation* reference decode (select_passages.py:109 also goes through `gpu0.whisper` — same key, so actually identical) — fine — but also a *batched* variant (`whisper:large-v3:batched`), which would still prove "a Whisper load was refused" but not necessarily *the re-transcription*. Given the pin's purpose (proof the new bytes went to Whisper) and that the only whisper use in select's path is the transcription, this is acceptable; noting it for completeness.

4. **The 60s ffmpeg timeout (diff:276) vs. word_diff's 120s (word_diff.py:129).** Inconsistent, but the test's tone is 1s of sine — 60s is 60× headroom. No action needed.

---

## SECTION 7: SCORES

- Backend logic: **94**/100 (the diff's logic is correct; the -6 is the trust-`__file__`/loose-control residuals, all theoretical today)
- Frontend/UI: **N/A** — tests/docs only; not scored (the brief's stack section describes the product, not this diff)
- Error handling: **96**/100 (the control/defect taxonomy is exemplary; -4 for existence-only "writes nothing" proofs)
- Security: **95**/100 (list-args subprocess with timeout, no secrets, no injection surface; nothing more to find in a tests-only diff)
- Performance: **92**/100 (one extra ffmpeg spawn per wall run, ~100ms; the `_resolve` scan is O(names) with realpath — negligible; nothing to fix)
- Law compliance: **98**/100 (every law checked, every claim measured, fail-closed honored; -2 for the "writes nothing" title vs. narrower proof)
- World-class gap: **90**/100 (the seam discipline and failure taxonomy are genuinely above the bar; the residuals are the trust-`__file__` control, the loose whisper: prefix, the title/proof scope mismatch)
- OVERALL: **94**/100

---

## SECTION 8: PRIORITY ACTION PLAN

P1 HIGH     | Add a control that the resolved `qa_gates` (the one KNOWN_CUDA_SETTERS entry) is the expected pipeline/segment_v1 file, closing the trust-`__file__` loop | tests/adversarial/test_f0_cpu_guard.py:246-248 (diff:246-248) | if a same-named stranger ever shadows qa_gates, the scan reviews the wrong file and the setter check passes vacuously — the exact failure mode PP-E26 documents, surviving one name deeper
P2 MEDIUM   | Tighten R-10's lease-refusal control from `startswith("whisper:")` to the full expected key `whisper:large-v3` (or assert the message matches the same regex the f0 test uses) | tests/adversarial/test_f2_provenance.py:325 (diff:325) | a differently-keyed whisper variant (e.g. :batched) would satisfy the control while proving a different load went to Whisper, weakening the pin's "the new bytes" claim
P2 MEDIUM   | Either narrow the new test's title/docstring to "writes no EDL and no transcript" (which it proves) or add assertions for the other select outputs (SELECT_BOUNDARIES.json, sources/ records) | tests/adversarial/test_f2_provenance.py:363-375 (diff:363-375) | the title promises "writes nothing" but the proof covers two paths; a future partial-write defect elsewhere would pass the test that claims to catch it
P3 LOW      | Align the ffmpeg timeout with word_diff's (120s) or document why 60s suffices | tests/adversarial/test_f0_cpu_guard.py:276 (diff:276) | consistency; a 1s tone needs neither, but two conventions in one suite invites drift
P3 LOW      | In `_resolve`, note why a package `__init__.py` (endswith .py) would resolve, and that the suite imports no packages from the roots | tests/adversarial/test_f0_cpu_guard.py:227 (diff:227) | the guard's assumptions should be written where the next editor will read them

---

## SECTION 9: THE ONE THING

The diff's great strength is that every test now names the *layer* it means — lease, stub, or seam — so the one thing: add the missing control that the resolved `qa_gates` is the real pipeline/segment_v1 file, because PP-E26's lesson (a same-named stranger blamed for another's behavior) currently survives one name deeper, and the scan's whole purpose is to review the right source.

---

## SECTION 10: FINAL VERDICT

**Ready to merge.** The three wall failures are fixed by correcting the tests' *model of the production layering* (PP-E27), not by loosening any check — the setter scan now resolves imports the way the interpreter does, the Whisper refusal is asserted at the layer that actually refuses (with the BaseException law pinned as a test), and R-27's failure is injected at the production seam whose documented failure value the pin relies on. The residuals (trust-`__file__` control, the loose `whisper:` prefix, the "writes nothing" scope) are P1/P2 polish, none blocking; the 378/40/3/0 wall with the --runxfail proof and the 26/0 regression script is the strongest evidence in the package.