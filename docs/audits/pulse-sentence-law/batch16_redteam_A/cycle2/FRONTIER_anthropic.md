# claude-fable-5-2 (649 s) usage={'input_tokens': 128706, 'cache_creation_input_tokens': 0, 'cache_read_input_tokens': 0, 'cache_creation': {'ephemeral_5m_input_tokens': 0, 'ephemeral_1h_input_tokens': 0}, 'output_tokens': 64000, 'output_tokens_details': {'thinking_tokens': 59226}, 'service_tier': 'standard', 'inference_geo': 'global', 'speed': 'standard'}

# Batch 16, cycle 2 audit: fix verification and new findings

Nothing was executed; every claim below is traced by hand from the diff. Line numbers marked `~` are derived from hunk headers or counted in the new files.

## Cycle 1 fixes checked against the diff

| Fix | Status |
|---|---|
| GPT #1 evidence absent or malformed | Holds (`release_auth.blockers`: `ev = evidence.get(fmt) if isinstance(evidence, dict) else None`). |
| GPT #2 TOCTOU | Holds for file payloads (read once, hashed, same bytes uploaded). Residuals in F7. |
| GPT #3 in-flight record | Holds (durable `in_flight` before the request; rerun refuses). Residual in F7. |
| GPT #4 number spans | Holds for the named case. `canon_spans` does not produce the same form as `canon_tokens` (F3). |
| GPT #5 'and' | Holds for the four tested strings only. Adjacent scaled numbers are still summed (F2). |
| GPT #6 signs | Holds in `canon_tokens`. Not applied in `canon_spans` (F3). |
| GPT #7 headline claims | Logic matches the description. Its negative tests assert only "some RuntimeError" (F8). |
| GPT #8 foreign checkout | Incomplete: still exempted by path spelling (F6). |
| Claude #1 MONITORING / REQUIRED | Inventory and caption as described. The G14 vertical fail and HOLD fixtures are not in the diff (F8). |
| Claude #2 evidence | Incomplete (F1). |
| Claude #3 anchor edge equality | Not verifiable: the cited `if seq[s] != qt[0]: continue` lines are outside the diff. The explicit check was removed from `anchor`. |
| Claude #5 | 'and': see F2. Spaced thousands: fixed in `fold` only (F3). Ordinals: simple ones only (F4). |
| Claude #6 tests | Import regex and fuzz additions are present. The site test is per file, not per site (F8). |
| Claude #7 | Same as GPT #7. |
| Claude #8 crash paths | Holds where visible. `edges_on_final` still opens `edl.json` and `cuts_final.json` outside its per-segment `try`. |

## Findings

### F1. HIGH — Execution evidence is still derived from the verdict or from constants (Claude #2 not fixed)

- `pipeline/run_fresh.py` ~L838, in `put`: `evidence[fmt][row] = {"executed": verdict != "SKIPPED", "samples": _samples(data)}`. `executed` restates the verdict for every row.
- `pipeline/verify_pack.py` ~L202 does the same for V1: `{"executed": verdict != "SKIPPED", "samples": n}`.
- `run_fresh.py` ~L949: `put(fmt, row, verdict, d if row == "G9_tail" else [msha, csha])`. `_samples` (~L784) has `if isinstance(x, list): return len(x)`, so `outro_locked` always has 2 samples, even if both hashes are `None`. The docstring says "never its labels, hashes or flags".
- `run_fresh.py` L738: `"checked": [c["clip_id"] for c in cuts]` is built before the per-clip loop. ~L1046 then uses `fb.get("checked") or []` as the sample count for `vertical_silent_fallback`, so it counts clip labels, not clips measured.
- No test in the diff exercises `_samples` or `put`. `make_run` hardcodes `{"executed": True, "samples": 3}`.

Consequence: for these REQUIRED rows, `release_auth`'s "executed True, samples >= 1" check cannot fail independently of the verdict.

Fix:
- Have each gate return its own `executed` flag and its measured entries.
- Count only entries that carry a measurement; count hashes only when both are non-null strings.
- Append to `checked` inside the loop, after the file was probed.
- Unit-test `_samples` with `[None, None]`, a label list, and bool or numpy values.

### F2. HIGH — The number parser sums two adjacent numbers (GPT #5 fix is incomplete)

`pipeline/canon.py` ~L101-109, in `_words_number`:

```python
elif w in _SCALES and (seen or w == "hundred"):
    cur = (cur or 1) * _SCALES[w]
    if w != "hundred":
        total, cur = total + cur, Decimal(0)
...
elif w == "and" and last == "scale" and ... : pass
```

There is no check that scales descend. Traced by hand:
- "five thousand and six thousand" gives `11000`, equal to "eleven thousand" and unequal to "5,000 and 6,000".
- "one hundred and two hundred" gives `10200`.
- "seventy thousand eighty thousand" gives `150000`.

A spoken range is the obvious trigger, and this form now feeds every comparison site, not only G18. `TestAuditBatch16` tests only "one and two", "twenty and five", "one hundred and two" and "two thousand and five".

Fix:
- Accept a scale at total level only if it is strictly smaller than the last one applied.
- Accept "hundred" only when `cur < 100`.
- On violation, rewind to before the consumed "and" and end the number there.
- Add both directions as tests.

### F3. MEDIUM — `canon_spans` is not the same canonical form as `canon_tokens`

`pipeline/canon.py`, `canon_spans`: `trips += [(p, i, j - 1) for p in _prepare(w)]` prepares one word at a time. The sign and thousands rules need cross-word context, so they do not fire.

| Input | `canon_tokens` | `canon_spans` |
|---|---|---|
| `- 5% today` | `minus 5 percent today` | `5 percent today` |
| `+ 5%` | `plus 5 percent` | `5 percent` |
| `1 000 000` | `1000000` | `1000`, `0` |

The third row is because the merge guard `re.fullmatch(r"\$?\d{1,3}", w.strip())` stops after one merge.

Consequences:
- `sentence_law.anchor` and `editorial_select.align_quote` compare `qt` (from `canon_tokens`) against `seq` (from `canon_spans`), so such a quote cannot anchor.
- `_SIGN_SPACED` (`(^|[(:,;])\s*-\s+(?=\$?\d)`) turns a dash that opens a transcript line before a number (`- 21 million …`) into `minus`.
- `test_aligned_tokens_equal_text_tokens…` claims equality but mutates only `$81 ,000`, `74 000` and `$40 trillion`.

Fix: build `canon_spans` by running `_prepare` once on the joined text while tracking character-to-word offsets. Add sign layouts and `1 000 000` to `TestAligned`.

### F4. MEDIUM — Compound ordinals are unequal to their digit form (Claude #5 fix is incomplete)

`pipeline/canon.py`, `_canon_seq`: `elif _ORDNUM.match(t) or t in _ORD:` handles single ordinal words only, and `_words_number` stops at an ordinal.
- "twenty first" or "twenty-first" gives `20`, `ord1`; "21st" gives `ord21`.
- "one hundredth" gives `1`, `ord100`; "100th" gives `ord100`.

`test_ordinals` draws `randrange(1, 21)` from a list that ends at "twentieth", so it never reaches a compound.

Effect: a date such as "November 21st" rendered two ways by Whisper fails G18. `headline_numbers_said` would also refuse a headline "21st" that the video says as "twenty-first".

Fix: fold a cardinal followed by an ordinal tail into one `ord{n}`. Test 21-99 and 100th.

### F5. MEDIUM — A REQUIRED G3c FAIL is rewritten to PASS from a partial list of failures

`pipeline/run_fresh.py` ~L996-1008:

```python
failed = [... if e.get(key) is False]
if rows[fmt].get("G3c_acoustic_tail") == "FAIL" and failed and all(_edge_proved(sg, sd) for sg, sd in failed):
    put(fmt, "G3c_acoustic_tail", "PASS", g3c, ...)
```

The whole row flips when every edge that reads exactly `False` is proved. Nothing checks that those edges are the only reason the row failed. An entry with `tail_ok: None`, an error entry or a non-dict entry is not in `failed`.

Uncertain: `gate_g3c` is not in the diff, so I cannot show that it can FAIL for another reason. The structure predates this batch; the batch only rewrote it to use `put`.

Also not verifiable: the hidden branch in `edge_word_fidelity` (`if (a if side == "in" else b) is None: … continue`) may set `ok` True for an edge with no bound.

Fix: flip only when the set of non-passing G3c entries equals `failed`; otherwise leave FAIL. Test with one proved edge plus one unmeasurable entry.

### F6. MEDIUM — The foreign-module rule still depends on path spelling (GPT #8)

`pipeline/run_fresh.py` ~L1089-1091, in `executed_code`:

```python
elif (name.split(".")[-1] in first_party or re.search(r"/(protocol_pulse|worktrees)/", f)) and \
        not any(x in f for x in ("site-packages", "dist-packages", "/venv/")):
```

- **Fail-open:** a first-party name (`canon`, `telegram`, `relay`, `release_auth`) loaded from any path containing `site-packages`, `dist-packages` or `/venv/` is not flagged. The response says "whatever the path".
- **False HOLD:** matching on the last dotted component flags the standard library's `logging.config`, because `pipeline/config.py` exists. I cannot tell from the diff whether `logging.config` is loaded in a run. The test covers only `{"json": json}`.
- **Launch fallback:** ~L1159 has `launch = (...).get("git_head") or "HEAD"`. With no recorded launch revision, the comparison is against current HEAD and the "HEAD moved" check is skipped.
- **Preflight gap:** `preflight.check_git` checks only `pipeline` and `segment_v1` with `--untracked-files=no`. A change in `video_pipeline_v3`, or an untracked module, is caught only after the run.

Fix:
- Match the full top-level module name.
- Drop the path exemption for first-party names.
- Hold when `git_head` is missing.
- Align the preflight scope with `first_party`.

### F7. MEDIUM — Delivery residuals after GPT #2 / #3

All in `pipeline/telegram.py`.

- **Partial drop.** Digests are checked per item at send time (`deliver_run` ~L196-201). A 9:16 final that changed after authorisation is refused only after the 16:9 has gone out captioned `HOLD_OK`. The test codifies this: `self.assertEqual(sent, ["segment.mp4"])`. Fix: read and hash every payload before the first send.
- **Unbound text.** `_plan` runs after `authorise` and re-reads `edl.json` and `GATE_REPORT.json` (`headline_numbers_said`, `build_caption`, `publish_kit`) with no digest check. Caption and kit text can come from bytes other than the attested ones. Fix: load those files once, hash them against `att["files"]`, and pass the parsed objects on.
- **Misclassified refusal.** In `_send_bot_api`, `raise SendRejected("STOP: no payload bytes for a file send")` sits inside `try: … except Exception as e: raise RuntimeError("… outcome unknown …")`. A definite non-send is recorded as `unknown` and blocks the rerun. Fix: move the check above the `try`, or add `except SendRejected: raise`.
- **Repeat guard is per option.** The record and lock are keyed by option (`TELEGRAM_DELIVERY{'_' + option}.json`). The "never repeated" and "one delivery per run" guarantees do not hold across option labels on the same run directory.

### F8. MEDIUM — Tests that do not test what they claim

- **Any-RuntimeError refusals.** `test_telegram_delivery.py`, `TestNothingIsSentUnlessAuthorised.refused`, uses `with self.assertRaises(RuntimeError, msg=label)`. The reason is never asserted. The wrong-dimensions, oversize and three headline cases would pass on any refusal, including "not authorised". Fix: assert the needle, as `test_failure_blocks.refused` does.
- **G14 vertical fixtures.** `TestG14AudioOffsetVertical` adds one must-pass test. Its docstring and the audit response claim a must-fail and a HOLD fixture. Those would have to be inherited tests that call the overridden `_gate` and `man`, which the diff does not show. The class is also `skipUnless` a machine-local run exists, while `INVENTORY["9x16"]` makes the gate REQUIRED unconditionally.
- **`span_matches` decides G18 on a synthetic fixture.** In `word_diff.gate_g18`, `if same: row["identity_repeats_only"], row["identity"] = row["identity"], []` clears a REQUIRED difference. The only fixture is sine bursts with silent gaps (`TestSpanMatches`). The criterion is a 6 dB level envelope over 150 ms runs on the louder half. No real-speech repeat fixture exists, which is the batch's own rule for a release-deciding check. I cannot show a false pass from the diff