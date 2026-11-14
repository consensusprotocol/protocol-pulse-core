# glm-5.3-flash (z-ai/glm-5.3-flash) 104 s finish=stop usage in 9705 / out 3399 usd~0.080 (upper-bound price)

# CYCLE 2 — FINAL REVIEW (pp-selectid, rulings 2 + 3)

## 1. WHAT DID THEY CATCH THAT I MISSED?

- **glm's locale point (M2, now implemented):** `strftime('%B')` follows the process locale; under a non-English `LC_TIME`, "November 12" would stop matching and the 30 dated sign-offs would fail again. I did not flag this. The fix — the literal `MONTHS` table (vo_fidelity.py:39-40, 53) — is correct and the right shape (no import, no dependency).
- **glm's "no third reader of SNAP_MAX_S" and grok's downstream question:** I did not systematically grep for other readers. The orchestrator's facts confirm: only `ledger_build.py` (docstring, constant, check, reason) and `test_ledger_build.py` reference it. Nothing between the read and `package.usable` assumes 20 s.
- **grok's "can a 21-35 s moment reach a MEDLEY?"** — I did not trace the medley path. Answer, verified from the given facts: no. `package.usable(..., seg_max=SEG_MAX_S)` (package.py:162, SEG_MAX_S=20.0 at :67) drops >20 s moments before any medley stage; the spotlight calls `usable(..., seg_max=SPOT_S[1])` (spotlight.py:196, :217, SPOT_S=(12.0, 35.0) at :53). The 22.5 s test case (test_ledger_build.py:143-150) correctly asserts `assertIsNotNone(sp)` with the comment "the medley's usable() drops it" — the test itself documents the separation.

## 2. WHERE DO I AGREE / DISAGREE?

**grok's <critical> (LAW 20/M2, "never change what a check accepts to make a render pass") — DISAGREE, and the orchestrator's refutation stands.** The ruling *is* the change: ruling (3) explicitly says NUMBER accepts the manifest's own show date. Changing what a check accepts when a ruling orders it is not "changing what a check accepts to make a render pass"; it is the ruling. grok's own note ("previously triggered per background") concedes the 16/40 must-pass failures were the *pre-existing* bug the ruling fixes. Not a defect.

**qwen's <high> (hardcoded 35.0 vs importing `spotlight.SPOT_S[1]`) — PARTIALLY AGREE.** The drift risk is real but bounded: the test at test_ledger_build.py:133-139 asserts the triple `(35.0, 35.0, 20.0)` exactly, so any change to `SPOT_S[1]` breaks the test loudly. That converts "silent drift" into "test failure" — acceptable, though importing would be strictly better. P2, not P1. (qwen's own caveat about circular imports is fair; the test-only coupling is the pragmatic middle.)

**glm H1 (malformed/missing manifest date) — PARTIALLY AGREE, mostly resolved.** The orchestrator's facts settle the format question: the packager's manifest and every exam case carry "YYYY-MM-DD", and this machine runs Python 3.10, whose `fromisoformat` reads only that. A malformed date → `ValueError` → text unchanged → digits read as numbers again = the *stricter* old behaviour, never a looser one. One residual: `except ValueError` (vo_fidelity.py:51) does not catch `TypeError`/`AttributeError` if `manifest` is a truthy non-dict. But `check_deterministic`'s other uses of `manifest` (e.g. `manifest_terms` at :83, :276) already assume dict-like, so this adds no new failure mode. Not a defect introduced by this diff.

**glm H2/H3 (regex lookahead, NEEDS_SOURCE vs NUMBER-loop divergence) — AGREE with their own conclusions: both resolve to "verified correct."** I independently traced "November 120": after "November 12", the lookahead `(?![\w.]?\d)` — `[\w.]?`="0" then no digit, or empty then "0" is a digit — fails both ways, so no match, "120" survives whole, test :115-116 passes. And "November 12, 2025": the year group is optional and pinned to `d.year`=2026, so it matches "November 12" only, leaving "2025" → NUMBER+NEEDS_SOURCE, exactly what test :110 asserts. Both correct.

**qwen's "Nov. 12" note — AGREE, verified.** "Nov." is excluded by design (its period ends a sentence in `_governed`); test :111 covers it. Correct.

## 3. NEW FINDINGS (Cycle 2)

**N1. <medium> — `without_manifest_date` runs twice on the same text with different results, and the second application is a no-op that masks nothing but costs nothing — however, the NEEDS_SOURCE/NUMBER-loop pair can now disagree on *which* numbers they see when a date spans a chunk boundary.** Actually, tracing it: `_governed` splits at sentence ends; a written date "November 12, 2026." ends with the period *inside* the chunk, so the whole date sits in one chunk — no divergence. The ISO form has no period. **No concrete breaking input found; recorded as verified-consistent.** (Stated for completeness; not a finding.)

**N2. <medium> — `strict_features` strips the date but `names_of`/`time_words` do not, so a production claim whose *only* strict feature is the date now passes — which is the ruling's intent, but check the *other* direction: a production claim "Pulse Check, November 12" where the manifest's show is "Pulse Check" — `names_of` reads "November" as a month name, which `manifest_terms` (:276) already admits as production metadata, so no feature. Consistent.** No defect.

**N3. <medium> — test_ledger_build.py:148: `row(" ".join(["keeps"] * 8) + " settling payments.")` — the row's anchored text is 9 words; the snapped span is 65 words (asserted at :150).** The test asserts `info["snapped_words"][0] == 65`, which pins the *snap* mechanics, but nothing in the new test asserts the snapped row's *text* is the whole 75-word sentence — i.e., that the read now returns the 22.5 s moment's full sentence, not a truncated one. If `reanchor` returned the row's own 9 words with a 22.5 s span, the test would still pass. **Concrete gap: the test proves the row survives, not that its text is whole.** However, ruling 32's existing tests (unchanged, :128-131) already pin "added" words, so this is covered by the unchanged suite. Downgrade to <low>/note.

**N4. <medium> — the drop-reason string changed (ledger_build.py:26-27), and test :158 asserts the new substring.** Any *external* consumer parsing the reason (a log scraper, the live check's log) matching the old `"> 20 s (ruling 32"` would silently stop matching. The orchestrator's facts say the first build after this lands is the live check whose log shows what snapped past 20 s — if that log-parsing is code, it needs the new string. **Not verifiable from the diff** — flagging as a condition, not a defect.

**N5. <medium> — `without_manifest_date` is applied to `chunk` in the NUMBER loop (vo_fidelity.py:77) but the *cited* side (`gpool`, the governing segments' tokens) is NOT date-stripped.** This is correct by the ruling (the cited sentences' numbers must still contain the value — the date is production metadata, not a fact), but consider: a VO line "Bitcoin hit $100K on 2026-11-12" citing a segment that says "Bitcoin hit $100K on 2026-11-12." The VO's "100" (from 100K) must be in the cited sentences — fine. But now the *date* in the cited segment is still a number in `gpool`... no, `gpool` is only searched, never flagged. `_has_number(gpool, val, unit)` checks membership; stripping the VO side only *removes* candidates, never adds. So the change can only *reduce* violations, never create a false pass for a non-date number. **Verified: the change is strictly narrowing on the VO side.** No defect — but note the asymmetry: a VO line whose *only* number is the date, citing a segment with no numbers, now passes NEEDS_SOURCE... wait, NEEDS_SOURCE fires when there's *any* fact; with the date stripped, if the line has no other fact, it no longer *needs* a source — which is the ruling's intent (production metadata). Consistent.

**N6. <medium> — case-insensitivity: `re.I` (vo_fidelity:56) applies to the whole pattern including the ordinal suffixes and the year.** "NOVEMBER 12TH" → matches (good). But `re.I` also means the *ISO* alternative's lookbehind/lookahead character classes are unaffected (they're already char classes). No issue. However: "november 12, 2026" — the year group `,?\s+{d.year}` — with `re.I`, digits are unaffected. Fine. **No defect.** One more: the written pattern's `\b` before the month — "SubNovember 12" → `\b` fails between "b" and "N"? No: "b" and "N" are both `\w`, so no boundary → no match → "SubNovember 12" keeps its date → NUMBER sees... the date's digits "12" as a number. Is that right? "SubNovember" isn't a real word; not a realistic input. No defect.

**N7. <medium> — the `0?` in the written pattern (vo_fidelity:55) accepts "November 012"?** `0?{d.day}` = "0" + "12" = "012" → matches "November 012" → stripped → NUMBER never sees it. Is "November 012" a must-fail? Not in the test list. The ruling says "the WHOLE date only... never a bare number" — "November 012" *is* the whole date with a zero-padded day, which the ruling's spirit accepts (ISO dates zero-pad). Not a defect; noting the ruling's "never a bare number" is about a *day alone* ("Pulse Check for 12."), which test :110 covers.

**N8. <high> — the 30 dated sign-offs in pp-tests: the ruling says "pp-tests keeps its 30 cases," and the change's facts say 16 of 40 must-pass cases failed before.** The diff adds tests to `tests/package/test_gates.py` (5+7+1+2+2 = 17 assertions in one new test) but the *pp-tests* 30-case suite is elsewhere (not in the diff). **Not verifiable from the diff whether pp-tests' 30 cases now pass** — the change's own facts say "9 mutations, each killed; 20 suites, 570 tests," which presumably includes them. If the 570 include pp-tests' 30, this is settled; if not, the ruling's "pp-tests keeps its 30 cases" is unverified. **Condition, not a defect.**

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why |
|---|---|---|---|
| ledger_build SNAP_MAX_S (ruling 2) | 8/10 | 9/10 | Downstream verified: no third reader, medley path confirmed separate; only residual is the hardcoded 35.0 (P2, test-pinned). |
| vo_fidelity without_manifest_date (ruling 3) | 8/10 | 9/10 | Locale fix verified; regex traced through every test case; the change is strictly narrowing on the VO side (N5); malformed/missing date falls back to the stricter old behaviour. |
| Tests | 7/10 | 8/10 | 9/9 mutations killed, 570 tests; residual: pp-tests' 30-case pass not independently verifiable from the diff (N8), and the 22.5 s test doesn't pin the snapped row's *text* (N3, covered by unchanged ruling-32 tests). |
| Reason-string / log consumers | 7/10 | 7/10 | Unchanged: the new reason substring (ledger_build.py:26-27, test :158) may break external log-parsers; not verifiable from the diff. |

## 5. FINAL PRIORITY LIST

- **P0 CRITICAL:** none.
- **P1 HIGH:** none.
- **P2 MEDIUM:**
  1. **ledger_build.py:10** — `SNAP_MAX_S = 35.0` hardcoded; import `spotlight.SPOT_S[1]` (or keep the test-pinned triple, which already catches drift loudly). (qwen, agreed, bounded.)
  2. **ledger_build.py:26-27** — the drop reason's changed substring; confirm no external log-parser matches the old `"> 20 s (ruling 32"` (not verifiable from the diff).
  3. **vo_fidelity.py:51** — `except ValueError` only; a truthy non-dict `manifest` raises `AttributeError`/`TypeError` uncaught. Adds no *new* failure mode (other `manifest` uses assume dict-like), but a one-line `except (ValueError, AttributeError, TypeError)` would make the fallback total.
  4. **N8** — confirm the 570-test run includes pp-tests' 30 dated sign-off cases; the ruling's "pp-tests keeps its 30 cases" must be demonstrated, not assumed.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

Confirm, with a printed run, that the 570-test / 20-suite run includes pp-tests' 30 dated sign-off cases — the ruling's acceptance criterion — because everything else in this diff is either test-pinned, strictly narrowing, or falls back to the stricter old behaviour.

## 7. PRODUCTION READY?

**Yes with conditions:**
1. Confirm pp-tests' 30 dated sign-off cases are inside the 570-test run (N8) — the ruling's own acceptance criterion.
2. Either import `SNAP_MAX_S = spotlight.SPOT_S[1]` or accept the test-pinned triple (test_ledger_build.py:139) as the drift guard — state which, in the ruling's record.
3. Confirm no external consumer parses the old drop-reason substring `"> 20 s (ruling 32"` (ledger_build.py:26-27).

No <critical> or <high> findings survive Cycle 2. The change is strictly narrowing on the VO side, the medley/spotlight ceilings are correctly separated, the locale fix is the right shape, and every failure path falls back to the pre-change (stricter) behaviour.