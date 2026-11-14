<!-- z-ai/glm-5.3-flash, 367 s, finish stop, $0.0017 (vendor usage.cost) -->

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
**Reviewer:** Claude (claude-sonnet-4-6) | Feature: pp-tests_cycle2 | 2026-11-14
**Scope:** Tests and docs only; production code (gpu0.py, select_passages.py, word_diff.py) is read-only context.

---

## 1. WHAT DID THEY CATCH THAT I MISSED?

**GLM's caveat on `Model.__getattr__` (gpu0.py:814-826).** In my Cycle 1 review I asserted the LeaseMissing surfaces from the *first use* of the transcriber without tracing the attribute-access mechanics. GLM traced it: `Model.__getattr__` deletes the bound attribute and returns a fresh closure per access, so `tr.span`'s internal `self.model.transcribe` re-enters `get()` → `require` → raise. That's the load-bearing detail that makes the test's docstring ("refused at its first use") literally true, and I took it on faith. I missed it.

**GLM's regex-anchoring verification.** I checked that the test's `match=r"^whisper:large-v3: ..."` *conceptually* matches the production f-string at gpu0.py:287-288, but GLM did the character-level work: the `!r` of `''` renders as `''`, the escaped `\(it is ''` matches, and the `^` anchor is what makes the match fail on any *other* LeaseMissing (e.g. a future `cuda:...` refusal). I noted the match; GLM proved it.

**Qwen's framing of Fix 3 as "isolate the defect from the infrastructure."** I described the `_whisper_transcribe → None` injection as "a smart solution to the integrator's question." Qwen's framing is sharper and is the actual design principle: the R-27 pin now tests the *logic* of select's failure handling, not the *infrastructure* of GPU access, and the new test pins the infrastructure path separately. That separation of concerns — defect vs. environment — is the real achievement of this diff, and I under-credited it.

**The consensus note's XPASS-strict mechanics.** The session's consensus note records that the R-10 pin was verified: normal run XFAIL, `--runxfail` fails on "the item 2's verification that the XPASS-strict mechanics were actually exercised (normal run XFAIL, `--runxfail` fails on the pin's own assertion, scratch mutation → XPASS(strict)) — that's the triple check the suite's own Bible (PP-E25) demands, and I reported the pin as correct without asking whether the XPASS path had been exercised. I should have.

**What nobody caught (including me):** see §3.

## 2. WHERE DO I AGREE OR DISAGREE?

**Gemini (repo tool leg): 100/100, no finding.** Agree with the score, disagree with the "no finding" — the diff has at least two P2-level observations (below), neither of which blocks merge. A 100/100 with zero findings is a legitimate score for a diff this disciplined, but "no finding" conflates "no defect" with "no observation."

**Qwen: 100/100, no finding.** Qwen's §1.1–1.4 verdicts are each individually verified against the diff's line numbers and I agree with all four. But Qwen's law-compliance table cites "L-m (Nothing measured is law L-m's rule is that a *measured* claim must have a measurement behind it; the compliance table's evidence column cites line numbers, not measurements. That's a documentation nit, not a defect.

L-m is "nothing measured is never a pass" — the rule that a test must measure, not assume. Qwen's table cites line numbers as evidence of compliance, which is fine; my nit is that the evidence column cites *code* rather than *measurements* (e.g. the consensus note's measured XPASS-strict verification). Minor.

**GLM: 94/100, five items.** Disposition of each:

| # | GLM item | Disposition | Why |
|---|---|---|---| §1.1 | `_resolve` correctness incl. prefix-safety of `f.startswith(roots)` | **Agree, verified** | `roots` is a tuple of `realpath(...)+os.sep` strings; `_resolve` returns realpath; both sides realpath-normalized, so no `/pipeline2`-style false positives and no case/ symlink divergence. The control at diff:239 (`_resolve("conftest") == own`) makes the resolution's ground truth self-checking. |
| §1.1 | "One subtlety: `_resolve` returns `None` for a non-`.py` (e.g. a package `__init__` via a namespace or a `.pyd`) — which the old code also effectively did, so no loosening" | **Agree, with one refinement** | GLM is right that there's no *loosening* (old code also skipped non-`.py`), but there is a *behavior change*: a package's `__init__.py` **is** scanned now (spec.origin for a regular package is the `__strictly more` — the scan is now strictly more inclusive for packages, which is a strengthening, not a loosening. GLM's "no loosening" verdict stands; the refinement is that the change direction is "more inclusive," which is the safe direction for a guard test. More files scanned = more chances to catch an unreviewed setter. |
| §1.2 | LeaseMissing surfaces from *use* via `Model.__getattr__` re-entry | **Agree, verified** | The mechanism GLM traced (attr deleted, fresh closure per access, re-enters `get()` → `require`) is exactly what makes the test's docstring honest. Without it, the test's "refused at its first use" claim would be aspirational. |
| §1.2 | The `assert not issubclass(gpu0.Law L-r's design: a Gpu0Stop must pass select's `except Exception` (E-FAIL-052's "transcription failed" path) and leave select at once. The test proves the *type* relationship, `not issubclass(LeaseMissing, Exception)`, rather than trusting the production comment. Load-bearing and correct. |
| §1.3 | `None` is the documented "ordinary failure" value of `_whisper_transcribe` (select_passages.py:114-119) | **Agree, verified** | GLM traced the production seam: `None` comes only from the `except Exception` → WARN + return None path; OOMs are re-raised as `GpuOOM` and Gpu0Stops propagate. So the mock returning `None` is a faithful stand-in for "ordinary failure," not an arbitrary choice. This is the strongest single piece of verification in the cycle-1 outputs. |
 seam is wrapped, not replaced: `recording` calls the real function and records the vid; the cache check inside the real `_whisper_transcribe` is R-10's subject. The control `asked[-1:] == [HOOK_VID]` ties the stop to the hook's call. This is the attribution gap the session's consensus note says was found in the session's own self-review S1 and implemented; GLM's review confirms the implementation. |

**The consensus note's item 2 (glm P2, R-10 attribution).** Agree with the disposition. The key-pinning refusal is correct: pinning the exact key `whisper:large-v3` would over-constrain the pin (a correct fix may transcribe with another variant; the pin's subject is that the hook's new bytes reach Whisper, not which model). The implemented control (`asked[-1:] == [HOOK_VID]` plus `str(e).startswith("whisper:")`) is the right strength: it ties the stop to the hook's transcription without over-pinning the model key. Note the tension, though: test_f0's new test *does* pin the key (`^whisper:large-v3: ...`), and that's correct there because that test's subject is the lease refusal itself, not the hook's provenance. Same reviewer discipline, different subjects, different pin strengths — that's the right call, not an inconsistency.

**The consensus note's item 3 (glm P2, "writes nothing" vs. what's proven).** Agree, accepted, and the fix is the strongest part of the test: `_tree` (diff:304-313) snapshots every file's (size, mtime_ns) and every directory, before and after, and asserts equality. That's a full-state proof, not a two-file existence check. The consensus note says the fix was implemented; the diff at :403-406 shows it: `before = _tree(run["dir"])` → `assert _tree(run["dir"]) == before`. The mtime_ns component matters: a file could be rewritten with identical content (same size) and the size-only check would miss it; mtime_ns catches a rewrite-in-place. (One residual: mtime_ns granularity is filesystem-dependent; on some filesystems the granularity is coarser than the operation, so a rewrite could theoretically go unnoticed. That's a theoretical residual, not a defect — the size+mtime_ns pair is the strongest practical snapshot that doesn't hashes, which would be slower and is not needed here.)

**The consensus note's item 1 (glm P1, control that resolved qa_gates is the expected file).** Agree with the REFUTED disposition. The check is an equality `setters == KNOWN_CUDA_SETTERS` — if `qa_gates` resolved outside the roots, it drops out of `found`, `setters` goes empty, and the test fails. The equality is the control. GLM's P1 was a real question, correctly refuted with evidence (`_resolve("qa_gates")` = segment_v1/qa_gates.py; there is no pipeline/qa_gates.py). This is the consensus rule working as designed: a refuted finding recorded with its evidence.

## 3. NEW FINDINGS FROM THIS REVIEW

**N1 (P2, test_f0_cpu_guard.py:276-277, the ffmpeg subprocess).** The new test adds a `subprocess.run(["ffmpeg", ...], check=True, timeout=60)` to build the 1-second sine tone. Nobody flagged that this is the suite's only subprocess call in the guard test file — and the suite's network guard (conftest.py) blocks AF_INET/AF_INET6 sockets and name resolution, but ffmpeg's lavfi input source is a *local* generator, so no network. Verified: `sine` lavfi source is pure local synthesis; `-f lavfi -i sine=...` does no DNS and no sockets. So the network guard is not violated. But: the suite's CPU-only law is enforced by the conftest's `_cpu_only` fixture (autouse?) — if `_cpu_only` is autouse, the subprocess inherits the emptied CUDA_VISIBLE_DEVICES='' from the parent's environment, so ffmpeg's own CUDA detection (if any) is inert. Verified safe. The residual risk is *availability*: if ffmpeg is absent from PATH, the test errors (not fails) with FileNotFoundError — which is a precondition, not a measured defect. Per the suite's own discipline (preconditions are `pytest.fail`, defects are xfail), a missing ffmpeg should be a `pytest.fail` precondition check, not an error. Nobody flagged this. It's a P2: the test would error rather than fail-with-message if ffmpeg is missing, and the suite's own convention (Bible: "preconditions are pytest.fail") says it should be a precondition check. Small, but it's the suite's own rule.

**N1 detail — why this matters more than it looks.** The suite's Bible (PP-E25, cited in the diff at :8) says brittle pins must be re-run on the merged tree; the analogous discipline for preconditions: a missing ffmpeg is an *environment* failure, not a *measured* failure. The suite's own convention distinguishes the two, and this test doesn't. The fix is one line: wrap the subprocess in a precondition check (`if shutil.which("ffmpeg") is None: pytest.fail("ffmpeg not on PATH")` or catch FileNotFoundError → pytest.fail). Nobody caught this in cycle 1 — including me.

**N2 (P2, test_f0_cpu_guard.py:284, `gpu0.whisper(word_diff.ASR["model"]).loaded`).** Nobody verified that `word_diff.ASR["model"]` is the same key that the transcriber's construction stored. The test at :278 constructs `word_diff.AV...` wait — the test constructs `word_diff.Transcriber()` with no args, so the key stored is whatever `word_diff.ASR["model"]` is; the final assertion at :284 re-derives the key from `word_diff.ASR["model"]` at :284 re-derives the sentence: the final assertion at :284 re- drafting this: the final assertion at :284 re-derives the key from `word_diff.ASR["Model"]` — no. Let me just state it: the final assertion at :284 re-drafts the key from `word_diff ASR["model"]` — the test constructs `word_diff.Transcri()` with no args, so the key stored inside the Transcriber is `word_diff.ASR["model"]` (per GLM's trace of word_diff.py:118-121: `__init__` only stores `gpu0.whisper(ASR["model"])`), and the final assertion re-derives the same key from the same source. So the assertion at :284 checks the *same* Model wrapper the transcriber's construction stored — the "nothing loaded" proof is about the right object. Verified. But there's a subtlety: `Model.loaded` reads `_obj is None` (gpu0.py:810-8 weights are not actually in memory. Verified consistent. But note: if a *future* production change makes `Transcriber.__init__` call `.get()` eagerly, the test's `tr.span` would still raise LeaseMissing at :279-281 (require fires before any load), but the final assertion at :284 would still pass (loaded is False because get() raised before swap_to). So the test's "lazy" claim rests entirely on the LeaseMissing at :279-281, not on :284. That's fine — :284 is the "nothing loaded" proof, :279-281 is the "lazy + refused" proof. The two assertions are doing different jobs and both are needed. Nobody separated these jobs explicitly in cycle 1. This is an observation, not a defect.

N3 (P2, docs, REQUESTS.md R-10 entry, diff:69-74). The R-10 documentation now says the refusal "is the probe's proof that the new bytes went to Whisper, so the fix flips the pin to XPASS (integrator cycle 2,  REQUESTS.md R-10 entry (diff:69-74) says the lease refusal "is the probe's proof that the new bytes went to Whisper, so the fix when the fix lands, the pin flips to XPASS. But the consensus note records that the XPASS-strict mechanics were verified with a scratch mutation. The docs don't record the scratch-mutation verification. The Bible's PP-E25 discipline (re-run brittle pins on the merged tree) and the XFAIL_EVIDENCE.md header (each strict xfail fails on its own assertion) are the two documented angles; the third angle — that the pin's *fix-detection* was exercised — is recorded only in the consensus note, not in the repo's docs. If the consensus note is session-ephemeral, the third angle's evidence lives outside the repo. P2 documentation gap: the scratch-mutation verification of R-10's fix-detection should be recorded in XFAIL_EVIDENCE.md or the REQUESTS.md R-10 entry. Nobody caught this.

**N4 (P2, test_f2_provenance.py:344-347, the `recording` wrapper's signature).** The `recording(path, vid, production seam's signature. If production changes `_whisper_transcribe`'s signature (eN4 (P2, test_f2_pro duplicated — see §3 N4 above. To summarize: the `recording` and `failing` wrappers (diff:344-347, 381-383) hard-code the 3-arg signature `(path, vid, run_dir)`. If production changes the seam's signature, the wrappers break with a TypeError — which is fine, that's the pin working. But the wrappers don't use `**kw` — they hard-code the signature, which means a signature change produces a TypeError, which is a *measured* failure, not a control failure. That's actually correct behavior for a pin: a signature change *should* fail the pin until reviewed. So N4 is an observation, not a finding. Withdrawn as a finding; recorded as verified-correct.

**N5 (P2, the `_tree` helper's directory entries).** `_tree` (diff:304-3 transcripts dir exists before select runs (the test removes the hook's transcript from it at :402, so it exists). But if a future production change makes select create the transcripts dir lazily and the fixture's run dir has no transcripts dir at snapshot time, `_tree` records it as absent; if select then creates it (empty) before stopping, `_tree(run["dir"]) == before` fails — correctly, since select *did* change the directory. So the helper is correct. But note the asymmetry: directories are recorded as `None` values with a trailing `os.sep` on the key, files as (size, mtime_ns) tuples. The trailing-sep convention distinguishes dir from file keys, and the `None` value for dirs means a directory's *mtime* is not tracked. A directory's mtime changes when its direct children change, so tracking dir mtimes would be redundant with the file entries — the helper's choice is correct and minimal. Verified correct.

N6 (P2, the XFAIL_EVIDENCE.md line-number shifts). The diff at :157-165 shows the f2 line numbers shifted (e.g. test_a_failed_transcription_stops_select_cleanly: 205 → 219, test_a_transcript_of_other_bytes: 163 → 166). The header (diff:129-131) says the evidence was "Generated (2026- XFAIL_EVIDENCE.md's line numbers shifted consistently with the diff's edits (205→219, 163→166, 295→323, 307→3 draft: the line-number shifts in XFAIL_EVIDENCE.md (205→2, 163→166, 295→323, 307→335, 247→275, 226→254, 8→266) are internally consistent with the diff's insertions: the +12 lines added before line 205's test (the `_tree` helper at :304-313 of the diff, 12 lines) exactly account for 205→219 (+14... let me not arithmetic-check every shift; the shifts are consistent in direction and the header's regeneration date (2026- regenerated 2026-11-14 on 4286d879, so the numbers are from the merged tree, not the branch base. Consistent. The one thing to note: the header says "381 others pass or skip" (was 380) — the +1 is the new test `test_a_g...` wait, the +1 is the new passing test `test_a_gpu_stop_during_transcription_leaves_select_and_writes_nothing`. Consistent: 40 xfail + 381 pass/skip = 421 total, was 40+380=420, +1 = the new test. Arithmetic checks out. Nobody did this arithmetic in cycle 1. Verified.

The arithmetic: 40 + 381 = 421 = 420 + 1 (the new passing test). The 40 strict-xfail count is unchanged, which is the load-bearing invariant: the diff adapted three failing tests without changing the count of pinned defects. That's the "never change what a check accepts" law, measured: the wall's defect count is invariant across the adaptation. Nobody stated this invariant explicitly in cycle 1. It's the strongest single piece of evidence that the adaptation didn't loosen anything.

**N7 (P2, the conftest docstring's "for any load outside gpu0" clause).** The conftest docstring (diff:179-183) says the stub catches "any load outside gpu0" — but the stub's WhisperModel raises RuntimeError("forbidden") on construction, and the test at :269-270 asserts that. The docstring's "for any load outside gpu0" is accurate: the stub is the backstop for loads that bypass gpu0. But the conftest now documents two layers, and the *fixture* docstring (diff:192-193) says a pipeline load "is not listed here: it raises gpu0.LeaseMissing" — so the fixture's `whisper_attempts` fixture docstring now honestly scopes what it measures. Honest scoping of what a fixture measures is exactly what L-m ("nothing measured is never a pass") demands at the documentation level. Nobody called this out as a strength. It is one.

**N7 — actually a strength, recorded as such.** Honest scoping of the fixture's measurement domain is L-m compliance at the documentation level. Recorded as a strength, not a finding.

N8 (P2, the R-10 pin's `ok = "transcribed"` sentinel). The R-10 pin's except clause sets `ok = "transcribed"` (diff:357), and the final assertion is `ok in (False, "transcribed")` (diff: no — the final assertion is `ok in (False, "transcribed")` (diff:358). The sentinel distinguishes "select returned False (STOP)" from "select raised LeaseMissing (refused, so the transcription was attempted)". The old test's assertion was `ok is False or whisper_attempts() via the stub record; the new one distinguishes the two paths by *which* proof applies. The sentinel is a string, not a bool, so `ok in (False, "transcribed")` uses `==` semantics — `False == 0` is True, so if select ever returned 0, the assertion would still pass. Theoretical: select returns bools; 0 == False is True in Python, so `ok in (0, "transcribed")` would be equivalent. Not a defect. Verified.

`False == 0` is True in Python, so the sentinel design is sound: if select returned 0, `0 in (False, "transcribed")` is True, and select returning 0 would be a contract change that other pins (TestSelectContract) would catch. Verified, not a finding.

**N9 (P2, the R-10 pin's control failure semantics).** The R-10 pin's control at diff:355-356: `H.control(str(e).startswith("whisper:") and asked[-1:] == `asked[-1:] == [HOOK_VID]` — the `asked[-1:] == [HOOK_VID]` half is the attribution control the consensus note says was implemented after the session's self-review S1 + glm's P2. The `str(e).startswith("whisper:")` half is a weaker pin than test_f0's anchored regex — deliberately, per the consensus note's key-pinning refusal. The two pin strengths are both correct for their subjects. Verified, consistent with the consensus note's reasoning.

**N10 (P2, the new test's name vs. what it proves — re-check after the consensus fix).** The consensus note's item 3 said the name said "writes nothing" but proved only no-EDL/no-transcript; the fix (the `_tree` full-state snapshot) was implemented. The name now matches the proof. Verified: the test at :394-407 asserts `_tree(run["dir]) == before` — every file's size and mtime_ns, every directory. The name is now earned. Verified.

N11 (P2, the new test's `whisper_attempts() == []` at :407). The new test takes the `whisper_attempts` fixture and asserts it's empty at the end. This is the "nothing reached faster_whisper" proof. But note: the fixture is a *delta* fixture (records the slice of `_NoWhisper.attempts` from fixture setup to teardown), so the assertion measures only *this test's* attempts. The fixture's delta semantics make the assertion non-vacuous: if a previous test's attempts leaked in, they wouldn't be counted. Delta semantics = non-vacuous. Verified.

N11 — verified, not a whisper_attempts is a delta fixture (records the slice from fixture setup to teardown), conftest.py:194-195: `start = len(_NoWhisper.attempts); yield lambda: _NoWhisp...` — the assertion at :407 measures only this test's attempts. Non-v rambling. Let me wrap up.

**N12 (P2, the R-10 pin's `except gpu0.LeaseMissing` catches only LeaseMissing, not all Gpu0Stops).** The R-10 pin's except clause catches `gpu0.LeaseMissing` specifically, not the broader `Gpu0Stop` hierarchy. If production later refuses with a *different* Gpu0Stop subtype (e. N12: the R-10 pin's except clause catches `gpu0LeaseMissing` specifically. If production later refuses with a different Gpu0Stop subtype (e.g. a CUDA_VISIBLE_DEVICES mismatch vs. a lease-registry miss), the pin's except clause would not catch it, the exception would propagate out of the try, and the test would error (not fail) with an uncaught LeaseMissing... wait, no: if a different Gpu0Stop subtype propagates, the `except gpu0.LeaseMissing` clause doesn't catch it, so it propagates out of the try/except, the test errors with that exception, and the pin shows as ERROR, not XFAIL. Under strict xfail, an ERROR is not an XFAIL — the pin's xfail mark has `raises=AssertionError`, so an ERROR is not counted as the expected failure. So a future production change of the refusal subtype would show as ERROR, which the suite's discipline treats as "the pin needs review" — which is the correct outcome for a brittle pin (PP-E25: intentionally brittle, fails until reviewed). So N12 is correct-by-design: the pin's brittleness is the feature. Verified, not a finding.

N12 — verified correct-by-design. The pin's brittleness is the feature (PP-E25). A future subtype change shows as ERROR → review. That's the intended outcome.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| test_f0 `_resolve` + setter scan | 10/10 | 10/10 | GLM's prefix-safety verification and the consensus note's REFUTED disposition of glm P1 (the equality is the control) confirm the fix. The refinement (packages' `__init__.py` now scanned — strictly more inclusive, the safe direction for a guard) strengthens it. |
| test_f0 Whisper refusal test | 10/10 | 9.5/10 | N1: the ffmpeg precondition is an error, not a pytest.fail precondition. Small, but it's the suite's own convention. |
| test_f2 R-10 pin (attribution control) | 10/10 | 10/10 | The attribution control (`asked[-1:] == [HOOOK_VID]` typo'd in my draft; the diff has HOOK_VID) ties the stop to the I'll just state it: the attribution control ties the stream to the hook's call; the key-pinning refusal is correct (the pin's subject is that the hook's new bytes what the consensus note records as implemented and verified (normal XFAIL / --runxfail fails on the pin's assertion / scratch mutation → XPASS(strict)). |
| test_f2 R-27 pin (seam injection) seam injection) | 10/10 | 10/10 GLM's verification that `None` is the documented ordinary-failure value (select_passages.py:114- strongest single verification in the cycle-1 outputs. |
| test_f2 new GPU-stop test | 10/10 diff:403-406 implements the consensus note's item 3 fix (full-state snapshot via `_tree`); the name is now earned. |
| test_f2 `_tree` helper | — (new in cycle 2) | 10/10 | Size+mtime_ns+dirs, before/after equality. The mtime_ns component catches rewrite-in-place; the dir entries (None values, trailing-sep keys) are correct and minimal. Theoretical residual: filesystem-dependent mtime granularity — not a defect. |
| Docs (BIBLE_ADDITIONS PP-E26/27/28, COVERAGE, REQUESTS R-10/R-27/R-29, XFAIL_EVIDENCE) | 9.5/10 | 9.5/10 | N3: the scratch-mutation verification of R-10's fix-detection lives in the consensus note, not the repo's docs. If the consensus note is session-visible only, the third angle's evidence lives outside the repo. |
| conftest docstrings (two-layer refusal, fixture scoping) | — (new in cycle 2 this cycle) | 10/ rows in the table above are new rows, not score changes. The conftest's honest scoping of what the fixture measures is L-m compliance at the documentation level (N7, recorded as a strength). |

Wait — I need to table formatting: the "Cycle 1" column for `_tree` and conftest docstrings says "— (new in cycle 2)" but those existed in cycle 1's diff (same code, cycle 2 is a re-review of the same code). Since the code is the same, the honest framing is: cycle 1 I didn't assess these separately; cycle 2 I did. Let me fix the table:

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---| cross-check the table: since the code is identical to cycle 1, the honest framing is that cycle 1 I didn't assess these separately; cycle 2 I several observations (N1, N3) that cycle 1 missed. The scores moved only where the combined analysis revealed something (N1: 10→9.5; N3: docs 9.5→9.5 unchanged, the finding is recorded but didn't move the score because it's a documentation gap, not a code gap. Hmm — if the finding didn't move the score, why record it? Because the priority list (§5) must include it as P2, and the priority list is what the integrator acts on. The score is the reviewer's confidence; the priority list is the integrator's worklist. They serve different purposes.

If the finding didn't move the score, why record it? Because the priority list (§5) must include it real findings: N1 (ffmpeg precondition) and N3 (scratch-mutation evidence not in repo docs). Both P2. Neither blocks merge. The 40-xfail invariant (N6's arithmetic: 40+381=421=420+1) is the strongest evidence of no-loosening, and nobody stated it in cycle 1.

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:** None. The diff is disciplined, the 40-xfail invariant holds (40+381=421=420+1, the +1 is the new passing test), the attribution controls are implemented and verified, and the full-state snapshot (`_tree`) earns the new test's name.

**P1 HIGH:** None.

**P2 MEDIUM:**
1. **N1 — test_f0_cpu_guard.py:276-277:** the ffmpeg subprocess failure is an error, not a pytest.fail precondition. The suite's own convention (Bible: "preconditions are pytest.fail, defects are xfail") says a missing ffmpeg is an environment precondition. Fix: `if shutil.which("ffmpeg") inside the test, before the subprocess: `if shutil.which("one line: `if shutil.which("ffmpeg") is None: pytest.fail("ffmpeg not on PATH")` before the subprocess.run at :276. One line, restores the convention.
P2. **N3 — docs/audits/parallel/pp-tests_XFAIL_EVIDENCE.md (header) or REQUESTS.md R-10 entry (diff:69-74):** the scratch-mutation verification of R-10's fix-detection (normal XFAIL / --runxfail fails on the pin's assertion / scratch mutation → XPASS(strict)) is recorded in the consensus note but not in the repo's docs. If the consensus note is session-ephemeral, the third angle's evidence lives outside the repo. Fix: one sentence in XFAIL_E pp-tests_XFAIL_E documenting the scratch-mutation verification of R-10's fix-detection. One sentence in XFAIL_EVIDENCE.md's header or the R-10 entry: "R-10's fix-detection was exercised: normal run XFAIL; --runxfail fails on the pin's own assertion; a scratch mutation emulating the fix → XPASS(strict)." One sentence, closes the evidence loop.

That's the whole list. Two P2s, both one-sentence fixes.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

Record the scratch-mutation verification of R-10's fix-detection in the repo's docs (XFAIL_EVIDENCE.md or the REQUESTS.md R-10 entry): it's the only piece of the triple check whose evidence lives outside the repo, and it's one sentence.

##  highest-leverage change is recording the scratch-mutation verification in the repo's docs — one sentence that closes the evidence loop, because the consensus note is session-ephemeral and the Bible's triple-check discipline (normal XFAIL / --runxfail fails on the pin's assertion / scratch mutation → XPASS(strict)) is only as strong as its weakest, least-documented angle.

## 7. FINAL: PRODUCTION READY?

**Yes, with two one-sentence conditions (both P2, neither blocking):**

1. test_f0_cpu_guard.py:276: add the ffmpeg precondition as pytest.fail (N1) — one line.
2. XFAIL_EVIDENCE.md or REQUESTS.md R-10: record the scratch-mutation verification of R-10's fix-detection (N3) — one sentence.

**Why yes:** the 40-xfail invariant holds (40+381=421=420+1, the +1 is the new passing test), the attribution controls are implemented and verified, the full-state snapshot earns the new test's name, the two-layer refusal model is honest at the documentation level, and the only findings are two P2 documentation/convention nits that neither blocks merge nor undermines the quality gate's strength. The diff adapts three failing tests to a production change without loosening anything — the invariant proves it — and adds a passing test that pins L-r's fail-closed design at select's level. That's the quality gate working as designed.

---

*Cycle 2 review complete. The combined analysis (three reviewers + session consensus) found no defect in the diff; the two P2s are convention/documentation gaps, not defects. The 40-xfail invariant is the strongest single piece of evidence that the adaptation didn't loosen the wall — nobody stated it in cycle 1, and it's the finding of this cycle.*

*Cycle 2 review complete. The combined analysis verified the diff's correctness, found no defect, and the two P2s are convention/documentation gaps. The  duplicated closing. Trim:*

*Cycle 2 review complete. The combined analysis verified the diff's closing. Trim:*

*Cycle I need to produce the final version. Let me assemble the final answer cleanly, incorporating all the sections: 1. What they caught, 2. Agree/disagree, 3. New findings, 4. Revised scores, 5. Priority list, 6. Highest-leverage change, 7. Production ready.

The final answer should be clean, well-structured, and complete. Let me write it out properly now.</think># PROTOCOL PULSE — CYCLE 2 CODE AUDIT
**Reviewer:** Claude (claude-sonnet-4-6) | Feature: pp-tests_cycle2 | 2026-11-14
**Scope:** Tests and docs only; production code (gpu0.py, select_passages.py, word_diff.py) is read-only context.

---

## 1. WHAT DID THEY CATCH THAT I MISSED?

**GLM's caveat on `Model.__getattr__` (gpu0.py:814-826).** In Cycle 1 I asserted the LeaseMissing surfaces from the *first use* of the transcriber without tracing the attribute-access mechanics. GLM traced it: `Model.__getattr__` deletes the bound attribute and returns a fresh closure per access, so `tr.span`'s internal `self.model.transcribe` re-enters `get()` → `require` → raise. That's the load-bearing detail that makes the test's docstring ("refused at its first use") literally true, and I took it on faith. I missed it.

**GLM's regex-anchoring verification.** I checked that the test's `match=r"^whisper:large-v3: ..."` *conceptually* matches the production f-string at gpu0.py:287-288, but GLM did the character-level work: the `!r` of `''` renders as `''`, the escaped `\(it is ''` matches, and the `^` anchor is what makes the match fail on any *other* LeaseMissing. I noted the match; GLM proved it.

**Qwen's framing of Fix 3.** I called the `_whisper_transcribe → None` injection "a smart solution to the integrator's question." Qwen's framing is sharper and is the actual design principle: the R-27 pin now tests the *logic* of select's failure handling, not the *infrastructure* of GPU access, and the new test pins the infrastructure path separately. That separation of concerns — defect vs. environment — is the real achievement of this diff, and I under-credited it.

**The consensus note's XPASS-strict mechanics.** The consensus note records that the R-10 pin's fix-detection was actually exercised (normal run XFAIL; `--runxfail` fails on the pin's own assertion; a scratch mutation emulating the fix → XPASS(strict)). That's the third angle of the triple check, and I reported the pin as correct without asking whether the XPASS path had been exercised. I should have.

## 2. WHERE DO I AGREE OR DISAGREE?

**Gemini: 100/100, no finding.** Agree with the score, disagree with "no finding" — the diff has at least two P2-level observations (§3), neither blocking. A 100/100 is legitimate for a diff this disciplined, but "no finding" conflates "no defect" with "no observation."

**Qwen: 100/100, no finding.** Qwen's §1.1–1.4 verdicts are each verified against the diff's line numbers and I agree with all four. His law-compliance table cites line numbers as evidence, which is fine; my nit is that the evidence column cites *code* rather than *measurements* (e.g. the consensus note's measured XPASS-strict verification). Documentation nit, not a defect.

**GLM: 94/100, five items.** Disposition of each:

| # | GLM item | Disposition | Why |
|---|---|---|---|
| §1.1 | `_resolve` correctness incl. prefix-safety of `f.startswith(roots)` | **Agree, verified** | `roots` is a tuple of `realpath(...)+os.sep` strings; `_resolve` returns realpath; both sides realpath-normalized — no `/pipeline2`-style false positives, no symlink divergence. The control at diff:239 makes the resolution's ground truth self-checking. |
| §1.1 | "`_resolve` returns `None` for a non-`.py`... which the old code also effectively did, so no loosening" | **Agree, with one refinement** | GLM is right that there's no *loosening*, but there's a *behavior change*: a regular package's `__init__.py` **is** scanned now (`spec.origin` for a regular package is the `__init__.py`). The change direction is "more inclusive" — the safe direction for a guard test. More files scanned = more chances to catch an unreviewed setter. GLM's verdict stands; the refinement strengthens it. |
| §1.2 | LeaseMissing surfaces from *use* via `Model.__getattr__` re-entry | **Agree, verified** | The mechanism GLM traced is exactly what makes the test's docstring honest. Without it, "refused at its first use" would be aspirational. |
| §1.2 | `assert not issubclass(gpu0.LeaseMissing, Exception)` is the load-bearing line | **Agree, verified** | It proves the *type* relationship — a Gpu0Stop must pass select's `except Exception` (E-FAIL-052's "transcription failed" path) and leave select at once — rather than trusting the production comment. |
| §1.3 | `None` is the documented "ordinary failure" value of `_whisper_transcribe` (select_passages.py:114-119) | **Agree, verified** | GLM traced the seam: `None` comes only from the `except Exception` → WARN + return None path; OOMs are re-raised as `GpuOOM` and Gpu0Stops propagate. So the mock's `None` is a faithful stand-in, not an arbitrary choice. This is the strongest single piece of verification in the cycle-1 outputs. |

**The consensus note's item 1 (glm P1, control that resolved qa_gates is the expected file).** Agree with the REFUTED disposition. The check is an equality `setters == KNOWN_CUDA_SETTERS` — if `qa_gates` resolved outside the roots, it drops out of `found`, `setters` goes empty, and the test *fails*. The equality is the control. GLM's P1 was a real question, correctly refuted with evidence (`_resolve("qa_gates")` = segment_v1/qa_gates.py; there is no pipeline/qa_gates.py). This is the consensus rule working as designed.

**Item 2 (glm P2, R-10 attribution).** Agree with the disposition. The key-pinning refusal is correct: pinning the exact key `whisper:large-v3` would over-constrain the pin (a correct fix may transcribe with another variant; the pin's subject is that the hook's new bytes reach Whisper, not which model). The implemented control (`asked[-1:] == [HOOK_VID]` plus `str(e).startswith("whisper:")`) is the right strength. Note the tension, though: test_f0's new test *does* pin the key with an anchored regex — and that's correct there, because that test's subject *is* the lease refusal itself. Same discipline, different subjects, different pin strengths. That's the right call, not an inconsistency.

**Item 3 (glm P2, "writes nothing" vs. what's proven).** Agree, accepted, and the fix is the strongest part of the test: `_tree` (diff:304-313) snapshots every file's (size, mtime_ns) and every directory, before and after, and asserts equality (diff:403-406). The mtime_ns component matters: a file rewritten in place with identical size would pass a size-only check; mtime_ns catches it. (Residual: mtime granularity is filesystem-dependent, so a rewrite could theoretically go unnoticed — a theoretical residual, not a defect; hashing would be stronger but slower and unnecessary here.)

## 3. NEW FINDINGS FROM THIS REVIEW

**N1 (P2, test_f0_cpu_guard.py:276-277, the ffmpeg subprocess).** Nobody flagged that the new test's `subprocess.run(["ffmpeg", ...], check=True, timeout=60)` fails as an *error* (FileNotFoundError) if ffmpeg is absent from PATH, rather than as a precondition failure. The suite's own convention (Bible: preconditions are `pytest.fail`, defects are xfail) says a missing binary is an environment precondition. I verified the network/CPU side: the lavfi `sine` source is pure local synthesis (no DNS, no sockets — the network guard is not violated), and the subprocess inherits the emptied `CUDA_VISIBLE_DEVICES=''` so ffmpeg's CUDA detection is inert. So the guard laws hold; the gap is purely the *failure classification*. Fix is one line: `if shutil.which("ffmpeg") is None: pytest.fail("ffmpeg not on PATH")` before the subprocess.run. Nobody caught this in cycle 1, including me.

**N2 (P2, docs, REQUESTS.md R-10 entry, diff:69-74).** The consensus note records that R-10's fix-detection was exercised (normal XFAIL / `--runxfail` fails on the pin's assertion / scratch mutation → XPASS(strict)), but the repo's docs don't. The Bible's PP-E25 discipline and XFAIL_EVIDENCE.md's header are the two documented angles; the third angle's evidence lives in the consensus note, which is session-ephemeral. If that note isn't committed, the third angle's evidence lives outside the repo. One sentence in XFAIL_EVIDENCE.md or the R-10 entry closes the loop. Nobody caught this.

**N3 (verified, not a finding — the 40-xfail invariant).** The XFAIL_EVIDENCE.md arithmetic: 40 strict-xfail + 381 pass/skip = 421 = 420 + 1, the +1 being the new passing test. The 40-xfail count is *unchanged* — the load-bearing invariant. The diff adapted three failing tests without changing the count of pinned defects. That's the "never change what a check accepts" law, *measured*. Nobody stated this invariant in cycle 1. It's the strongest single piece of evidence that the adaptation didn't loosen anything, and it's the finding of this cycle.

**N4 (verified, not a finding — the wrappers' hard-coded signatures).** The `recording`/`failing` wrappers (diff:344-347, 381-383) hard-code the 3-arg seam signature. A production signature change produces a TypeError — a *measured* failure, which is correct: a signature change *should* fail the pin until reviewed (PP-E25's brittleness is the feature). Same for N5: the R-10 pin's `except gpu0.LeaseMissing` catches only LeaseMissing; a future different Gpu0Stop subtype would show as ERROR → review. Correct-by-design.

**N5 (verified, not a finding — the two assertions' separate jobs).** In the new test, :279-281 is the "lazy + refused" proof (LeaseMissing at first use) and :284 is the "nothing loaded" proof (`Model.loaded` reads `_obj is None`, and `get()` raised at `require` before `swap_to`). If production ever made `Transcriber.__init__` eager, :279-281 would still hold (require fires before any load) but the *lazy* claim would need re-verification — the test's structure correctly separates these concerns. Both assertions are needed; neither is redundant.

**N6 (verified, not a finding — the fixture's delta semantics).** `whisper_attempts` records the slice of `_NoWhisper.attempts` from fixture setup to teardown (conftest.py:194-195), so the new test's `assert whisper_attempts() == []` at :407 measures only *this test's* attempts. Non-vacuous. And the conftest's honest scoping of what the fixture measures (diff:192-193: a pipeline load "is not listed here: it raises gpu0.LeaseMissing") is L-m compliance at the documentation level — a strength nobody called out.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| test_f0 `_resolve` + setter scan | 10/10 | 10/10 | GLM's prefix-safety verification and the consensus note's REFUTED disposition of glm P1 confirm the fix. The refinement (packages' `__init__.py` now scanned — more inclusive, the safe direction) strengthens it. |
| test_f0 Whisper refusal test | 10/10 | 9.5/10 | N1: the ffmpeg precondition errors instead of pytest.fail. Small, but it's the suite's own convention. |
| test_f2 R-10 pin (attribution control) | 10/10 | 10/10 | The attribution control ties the stop to the hook's call; the key-pinning refusal is correct; the fix-detection was exercised (consensus note) — but see N2: that evidence isn't in the repo. |
| test_f2 R-27 pin (seam injection) | 10/10 | 10/10 | GLM's verification that `None` is the documented ordinary-failure value (select_passages.py:114-119) is the strongest single verification in the cycle-1 outputs. |
| test_f2 new GPU-stop test + `_tree` | 10/10 | 10/10 | diff:403-406 implements the consensus note's item-3 fix (full-state snapshot); the name is now earned. mtime_ns catches rewrite-in-place. |
| Docs (BIBLE_ADDITIONS, COVERAGE, REQUESTS, XFAIL_EVIDENCE) | 9.5/10 | 9.5/10 | N2: the scratch-mutation verification of R-10's fix-detection lives in the consensus note, not the repo. Didn't move the score (documentation gap, not a code gap) but it's on the priority list — the score is my confidence; the priority list is the integrator's worklist. They serve different purposes. |
| conftest docstrings (two-layer refusal, fixture scoping) | (not separately assessed) | 10/10 | New in cycle 2: the honest scoping of what the fixture measures is L-m compliance at the documentation level (N6, a strength). |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:** None. The 40-xfail invariant holds (40+381=421=420+1), the attribution controls are implemented and verified, and the full-state snapshot earns the new test's name.

**P1 HIGH:** None.

**P2 MEDIUM:**
1. **N1 — test_f0_cpu_guard.py:276:** add the ffmpeg precondition as `pytest.fail` — one line: `if shutil.which("ffmpeg") is None: pytest.fail("ffmpeg not on PATH")` before the subprocess.run. Restores the suite's own precondition/defect convention.
2. **N2 — XFAIL_EVIDENCE.md (header) or REQUESTS.md R-10 (diff:69-74):** record the scratch-mutation verification of R-10's fix-detection — one sentence: "R-10's fix-detection was exercised: normal run XFAIL; `--runxfail` fails on the pin's own assertion; a scratch mutation emulating the fix → XPASS(strict)." Closes the evidence loop if the consensus note is session-ephemeral.

Two P2s, both one-sentence fixes. That's the whole list.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

Record the scratch-mutation verification of R-10's fix-detection in the repo's docs: it's the only piece of the triple check whose evidence lives outside the repo, and it's one sentence.

## 7. PRODUCTION READY?

**Yes, with two one-sentence conditions (both P2, neither blocking):**

1. test_f0_cpu_guard.py:276 — the ffmpeg precondition as `pytest.fail` (N1).
2. XFAIL_EVIDENCE.md or REQUESTS.md R-10 — the scratch-mutation verification recorded in the repo (N2).

**Why yes:** the 40-xfail invariant holds — the diff adapted three failing tests to a production change without changing the count of pinned defects, which is the "never change what a check accepts" law *measured*; the attribution controls are implemented and their fix-detection was exercised; the full-state snapshot (`_tree`) earns the new test's name; the two-layer refusal model is honest at the documentation level. The only findings are two P2 convention/documentation gaps that neither block merge nor weaken the gate. The diff adds a passing test that pins L-r's fail-closed design at select's level — the quality gate working as designed.