# claude-fable-5-2 (645 s) usage={'input_tokens': 115544, 'cache_creation_input_tokens': 0, 'cache_read_input_tokens': 0, 'cache_creation': {'ephemeral_5m_input_tokens': 0, 'ephemeral_1h_input_tokens': 0}, 'output_tokens': 61315, 'output_tokens_details': {'thinking_tokens': 57650}, 'service_tier': 'standard', 'inference_geo': 'global', 'speed': 'standard'}

**Verdict: not fail-closed as shipped.** Eight findings, most severe first. Nothing was executed; all of this is read from the diff. Line numbers for new files are counted from the diff (±3); for modified files they come from the hunk headers.

### 1. HIGH — a run with failing gates is sent as "all release gates passed, no waivers"

- `pipeline/release_auth.py` ~L38-44 makes 9 rows MONITORING in both formats, plus four more for 9:16: `"9x16": frozenset(_MONITORING + ("G11_parity", "G14_audio_offset", "G14c_duration_parity", "vertical_silent_fallback"))`.
- ~L78-79 only requires an exact verdict for them: `if rows.get(k) not in VERDICTS:`. So `FAIL`, `HOLD` and `SKIPPED` all authorise.
- 9:16 now has no deciding A/V-sync gate: `INVENTORY["9x16"] = frozenset(_REQUIRED)`, and `G14_av_alignment` is 16:9 only.
- `verification_ok` (~L100-112) checks only `vision` and `complete`. `pack["passed"]` and `visual[fmt]["ok"]` are never read, although the `verify_pack.py` docstring says "release_auth reads this".
- The caption is unconditional: `HOLD_OK = "HOLD FOR APPROVAL - all release gates passed, no waivers"` (`telegram.py`). `test_monitoring_rows_are_reported_in_the_caption_not_deciding` asserts exactly this for `G1_voice = FAIL`.
- This is a regression: the old `verdict_for` held on `"FAIL (fallback occurred)"`, and the old `gate_status` required every row to read PASS.
- `test_visual_check.py` states that V1 now has a passing fixture, failing fixtures and a missing-evidence answer. By the rule in the `release_auth.py` comment it qualifies as REQUIRED, yet it sits in `_MONITORING`.

**Fix:** move `V1_visual_checklist`, `G11_parity`, `G14_audio_offset`, `G14c_duration_parity` and `vertical_silent_fallback` to REQUIRED, or require `pack["passed"] is True`. Whichever rows stay MONITORING, `HOLD_OK` must not be used when `monitoring_report` is non-empty.

### 2. HIGH — evidence is fail-open when absent and derived from the verdict when present

- `release_auth.py` ~L60/84: `def blockers(fmt, rows, evidence=None)` then `if evidence is not None:`. A missing or `null` evidence block skips the whole check.
- `attest` passes `rep.get("evidence")`; `authorise` passes `att.get("evidence")`; `transition_options.py` ~L50 passes `rep.get("evidence")`. With no evidence in either file, `None == None` also satisfies "rows / evidence differ".
- Only `run_tail` closes it, with `rep.get("evidence") or {}`. `TestEvidence` removes one row's evidence, never the whole block.
- The evidence itself is not a measurement. `run_fresh.py` ~L833: `evidence[fmt][row] = {"executed": verdict != "SKIPPED", "samples": _samples(data)}`, and `_samples` returns `len(x)` for any dict.
- Example: `outro_locked` is given `g9_report[fmt]`, a six-key literal, so it always has 6 "samples".
- Uncertain: if `G5_tech`, `G12_credits` or `G8_sharpness` results have no `"table"`/`"data"`, they get `samples: 0` and every run holds. I cannot see `qa_gates`' result shapes.

**Fix:** treat `evidence is None` as a blocker (no default). Have each gate return an explicit executed flag and a real sample count.

### 3. HIGH — lock anchoring lost its edge-word check and ends a lock on the wrong word

- `sentence_law.py` ~L353 removed `tokens(words[i0]["word"])[0] != qt[0] or tokens(words[i1]["word"])[-1] != qt[-1]`.
- Its replacement is `if (s and toks[s - 1][1] == i0) or (e + 1 < len(toks) and toks[e + 1][1] == i1): return None`. That checks word boundaries only. The docstring still says "The span's first and last tokens must equal the selection's". The window search is not in the diff, so I cannot confirm it enforces equality itself.
- `canon._canon_seq` assigns a whole number phrase to its first word: `out.append((_value(num), own))`.
- So a selection ending "…above 40 trillion." (or "1.3 billion.", "five and a half.") has its last token owned by "40". `i1 = toks[e][1]` is the word "40", and the guard passes because the next token belongs to a later word.
- The lock ends before "trillion". `test_an_amount_is_owned_by_its_words` only covers the `$` case, where the appended "dollars" token happens to land on the last word.
- `editorial_select.align_quote` uses the same `(t, idx[o])` pairs.

**Fix:** have `canon_aligned` return first and last owner per token and use the last owner for `i1`. Restore `seq[s] == qt[0] and seq[e] == qt[-1]`.

### 4. MEDIUM — "an unknown outcome is never resent" is false for a killed process, and sent bytes are not the checked bytes

- `telegram.py` `deliver_run` records an unknown outcome only in `except Exception: record["unknown"].append(item["key"])`.
- SIGKILL, SIGTERM, Ctrl-C or a tmux kill during a 600 s upload leaves no checkpoint. The record file does not even exist until the first `save()`. A rerun sends the video again.
- A failure after a successful `send` but before `save()` duplicates it too; the `open(item["path"], "rb")` re-hash sits in that window.
- `release_auth.check_file(...)` hashes the path, then `_send_bot_api` reopens it with `open(path, "rb")`. The recorded `sha256` is a third read, taken after the send.

**Fix:** save a write-ahead `pending: key` before `send`, and treat a pending key as unknown on resume. Open the file once, hash that handle, upload the same handle, and record that digest.

### 5. MEDIUM — canon makes different words equal and the same words unequal

- `canon.py` `_words_number` ~L97: `elif w == "and" and seen and … : pass`. The "and" is consumed even when the next number word then breaks the phrase.
  - `"three and four"` → `["3","4"]`, equal to `"three four"`.
  - `"twenty and five"` → `["25"]`.
  - The old rule only joined after `("hundred", "scale")`.
- `_SPACED_THOUSANDS` is single-pass. `"1 000 000"` → `"1000 000"` → `["1000","0"]`, which no longer equals `"1,000,000"`. The old `(\d)\s+(?=\d{3}\b)` chained.
- `_ORD` maps `"second"` → `"2"` and `"third"` → `"3"` unconditionally, so `"one second"` equals `"one two"`.
- `TestDifferences` drops only the first word of each sentence, so none of this is exercised.

**Fix:** consume "and" only after hundred/scale and roll `j` back otherwise. Loop the spaced-thousands substitution to a fixpoint. Add interior-word drops and number-adjacent cases to the test.

### 6. MEDIUM — tests that do not test what they claim

- `test_canon.py` `test_the_comparison_sites_import_canon`: `"canon" not in open(...).read()`. This matches "canonical". `editorial_select.py` contains `ts.canonical_transcript`, so it passes with no canon import.
- `FORBIDDEN` has no pattern for `re.sub(r"[^a-z0-9]…`. Two normalisers this diff removed, `editorial_gate._norm` and `gates._g20_norm`, would pass the grep test if put back.
- `test_preflight.py` `test_secrets_never_reach_the_output` mocks `_get_json` to succeed. The only route for a secret into output is `detail = f"{type(e).__name__}: {str(e)[:160]}"` in `run_checks`, which is never exercised.
- I believe `http.client` puts the header value or URL path in its error text when a key contains a newline or control character. That is from memory, not from the diff.

**Fix:** assert `import canon` by regex. Add `re\.(sub|split|findall)\(\s*r?["']\[\^?a-z0-9`. Report preflight exceptions by type only, and test with a raising `_get_json`.

### 7. MEDIUM — the headline number check ignores units and context

- `telegram.py` `headline_numbers_said`: `said |= set(canon.canon_tokens(...))`, then a set difference of bare numeric tokens.
- Fail-open: a headline "Bitcoin falls 5%" passes if any clip says "five years". Unit, sign and position are not checked.
- Over-blocking: "second straight weekly loss" produces `"2"` (via `_ORD`) and stops an authorised run at delivery, exit 70, unless someone says "two" or "second".

**Fix:** require the headline's canonical number with its unit and sign tokens as a contiguous run inside a single lock. Exclude ordinals.

### 8. LOW — crashes instead of holds (all fail closed)

- `release_auth.blockers`: `if rows.get(k) not in ok:` with `ok` a frozenset. A list or dict row value raises `TypeError` inside `authorise`.
- `sentence_law.edge_word_fidelity`: `worst = float(np.max(diff))` lost its `if len(diff) else` guard. If `keep` is all False this is a `ValueError`. Uncertain: a guard may exist in lines the diff does not show.
- `edges_on_final` catches `(LawError, OSError, ValueError, KeyError, SubprocessError)`. A `TypeError` or `IndexError` from a malformed lock aborts `stage_gates` before `GATE_REPORT.json` is written.
- `verify_pack._sheets_and_checklist`: `if not r.get("ok")` sits outside the try, although `panel_ok` tolerates non-dict rows.
- `run_fresh.run_tail`: `d["rows"]` raises `KeyError` for a panel entry with no rows.

**Fix:** type-check before membership; restore the empty-diff guard as `ok False`; catch `Exception` per segment; use `.get` consistently.