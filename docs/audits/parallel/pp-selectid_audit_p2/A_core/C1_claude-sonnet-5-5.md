# claude-sonnet-5-5 (effort high) 290 s stop_reason=end_turn usage=in 87345 / out 37492

# Audit: pp-selectid-p2 (moments, package, providers)

Scope: only the diff shown. The tests, `pinned.py`, `eligibility.py`, `canon.py`, `story_semantics.quote_data` and `select_by_id` are not in it, so anything depending on them is marked uncertain.

## Scores

| Question | Score | Why |
|---|---|---|
| Q1 fail-open | 38 | The main control flow is sound, but the blind verdict accepts zero claims and the second recognition pass is optional and one-directional. |
| Q2 vendor separation / L-x | 66 | The writer-vendor handling is sound. The router's permanent "down" marking and some hard-coded vendors are real defects. |
| Q3 verbatim / model text | 58 | Clip text is verbatim, but hard exclusions rest on the miner's own self-report and the angle text is injected raw. |
| Q4 deterministic rules | 40 | Several concrete false passes and false rejects (below). |
| Q5 tests / wiring | 30 | Mostly unverifiable from the diff. `package_pin` hard-codes its gate results, and the adapter makes must-fail cases pass vacuously. |

## FINDINGS

### P0

**P0-1. The blind fidelity verdict passes with zero or partial claims** (`vo_fidelity.check_verdict`).
```python
obj["claims"] ... v = [] ... return {"ok": not v, "claims": obj["claims"], "violations": v}
```
- Failing input: the model replies `{"claims": []}`. `v` stays empty, so `ok` is True.
- The same happens if it lists one benign claim for the intro and omits the title and caption.
- Code never requires that each non-connective slot has at least one claim.
- Impact: layer (b) can be bypassed entirely by an omission. Layer (a) is then the only defence, and it has the holes in Q4 (including Title Case lines skipping NAME).
- Also, a "yes" is only checked for verbatim-ness of the cited words, not for support. `texts` includes `manifest`, so any claim can "cite" the manifest text `"contains clips from"`.

**P0-2. The L-v 2 second recognition pass is optional, one-directional and skipped on the plain path** (`package.build`).
- **Optional by default:** the pass only runs under `if truth_dir:`, and the default is `truth_dir=None`. With the default, a package ships with no second pass.
- **Trigger reads the first transcript only:**
  ```python
  if any(TT.critical_tokens(sg["text"])[k] for k in ("numbers", "negations")):
  ```
  If the first ASR dropped the only "not" or number, the segment is never sent to the second pass.
  - Names are not in the trigger.
  - Speaker-change detection therefore only runs for segments that already contain a number or negation.
- **Comparison is one-directional and set-based** (`transcript_truth.compare`):
  ```python
  bset = set(b); ... [n for n in a["negations"] if n not in bset]
  ```
  - It only checks that the first transcript's critical tokens appear somewhere in the second.
  - Failing input: the first text says "will rise". The second says "will not rise". `not` is absent from `a`, so nothing is checked.
  - Presence anywhere in the window also satisfies a token. First "will not rise" against second "will rise… not sure" passes.
- **"Not measured" counts as pass:**
  ```python
  or (t.get("speakers") or {}).get("turn_change_inside")
  ```
  `None` is falsy and is not treated as bad.
- **Plain-VO path skips it:** the plain package goes into `out["plain"]` and returns as `out["package"]` without coherence or truth. It never reaches the `truth_dir` block.

### P1

**P1-1. The runtime gate underestimates, by my arithmetic** (`package.py`).
```python
FIXED_S = round(E.TAIL_S - SIGNOFF_WORDS / WPS, 2)
vo_s = vo_words / WPS + len(pk["vo"]["signoff"].split()) / WPS - SIGNOFF_WORDS / WPS
```
- The sign-off VO duration is subtracted twice, once in `FIXED_S` and once in `vo_s`. The estimate therefore omits the sign-off VO (about 18/2.6 ≈ 6.9 s).
- Whatever `E.TAIL_S` contains, the estimate is low.
- Packages of about 70–77 s real length can pass `rt_ok`.
- `content_range` inherits the same offset.
- WPS is also an assumed constant. The estimate is not the rendered runtime.

**P1-2. The independent exclusion verdict is not wired in this diff.**
- `moments.exclusion_verdict` is called only from `moments_gate_adapter.exclusion`.
- `package.usable` relies on `m.get("excluded")`, which `record()` sets from the miner's own `risk` list: `sorted(set(m["risk"]) & set(HARD_RISKS))`.
- Failing input: the mining model omits `"accusation"` or `"imperative"` and the moment ships.
- The `package.py` docstring ("an exclusion failure drops the moment") has no code behind it here. If it is wired elsewhere, I can't see it.

**P1-3. `Router.down` is permanent and content-triggered** (`providers.Router.call`).
```python
except Unavailable as e:
    self.down[name] = str(e)
```
- `LocalBackend.complete` raises `Unavailable("prompt over the local context …")` for one oversized prompt. That marks local down for the whole run, contradicting "Ultron first".
- Any HTTP 4xx on one bad request (`_with_backoff` raises Unavailable for any other 4xx) or an empty-choices reply does the same to a cloud back-end.
- Use a per-prompt skip, not a run-wide kill.

**P1-4. `package_pin.to_pin` hard-codes the gate results.**
```python
"checks": {"vo_fidelity_ok": True, "context_integrity_ok": True, ...}
```
- It never reads `pk["checks"]` and never refuses a package without them.
- A plain-VO package, or any dict, is pinned as gated.
- `vo_kind` is not carried.
- R7's refusal logic isn't in this diff, so I can't say the patch refuses an ungated package. This function would not.

**P1-5. The exam adapter makes must-fail cases pass vacuously** (`moments_gate_adapter`).
- Every `ReplayMiss` returns `"fail"` or `"exclude"`.
- With an empty `gate_replies` directory, every must-fail case is green. Only must-pass cases reveal the gap.
- A must-fail case also passes on any provider outage.
- The adapter never passes `current_levels`, so PRICE_NOW is unexercised by the exam.

### P1 — deterministic rules (Q4)

**Numbers**
- Exemptions in `check_deterministic`:
  ```python
  not (unit is None and val in meta_nums)
  and not (unit is None and float(val) <= 10 and not re.search(rf"\b{val}\b", text))
  ```
  - "four rate cuts" with 4 segments is exempt (the count of segments, videos or channels).
  - Spelled-out numbers ≤10 are never checked ("three banks failed").
  - A bare day-of-month or year is exempt ("12 ETFs" on the 12th).
- `att_pool` is overwritten per attribution. With two attributions in one line, every number is checked against the last speaker's pool only. The first speaker's numbers are falsely rejected, and the second's can validate a misattributed one.

**Attribution**
- `ATTRIB_VERBS` has third-person singular forms only. These evade it: "Coin Bureau and Altcoin Daily warn…", "Coin Bureau: $200,000 by year end", "Natalie's $200K call", "per Coin Bureau".
- With no attribution found, the number is checked against the pool of all cited clips, so a clip A number credited to channel B passes.
- `_attributions` appends the "according to" pattern inside the `for v in ATTRIB_VERBS` loop. A failing line produces about 35 duplicate violations, which pollute the rewrite prompt.

**Names**
- `names_of` returns `[]` for any Title Case text, so "Vitalik Buterin Loves Bitcoin Rally" gets no NAME check.
- It skips single capitalised sentence-initial words, so "Blackrock sold." has no NAME check.
- It allows a name if any allowed term is a run inside it:
  ```python
  _run_in(nt, a) or _run_in(a, nt)
  ```
  "Bitcoin Magazine", "Bitcoin Jesus" and "Coin Bureau CEO" pass as the allowed "Bitcoin" or the channel name.

**Imperatives and framing**
- `IMPERATIVE`:
  - It requires `you␠(should|…)␠buy` with no adverb or contraction. "you've got to buy", "You should probably buy" and "don't sell" all pass.
  - It false-rejects honest lines starting with "Sell-off fears…" or "Short sellers are trapped" (the sentence-start alternative `(^|[.!?:]\s*)(short|sell…)\b`).
- `FRAMING` has 6 stems. "torches", "blasts", "crushes", "reveals" and "bombshell" pass.
- `RELATION` false-rejects "the answer is simple", "counter-intuitive" and "most agree". It misses "while X says… Y", "backs up Saifedean" and "similarly".
- `TIME_WORDS` covers a fixed phrase list. "just reached", "overnight", "last night" and "recently" pass. A bare "breaking" false-rejects "breaking down the case".

**PRICE_NOW / `current_levels`**
- `HISTORY` contains `all[- ]time`, `once`, `since` and any 4-digit year. "Bitcoin just hit a new all-time high at $130,000" is therefore exempt.
- `price_levels` flags any value ≥1000. If canon turns "21 million" into a value, honest lines like "21 million coin cap" or "640,000 bitcoin" in the intro, title or caption are falsely rejected.
- `current_levels` whitelists any number 10k–500k from sentences matching `PRESENT`. That regex includes "is", "are", "just" and "now". A prediction ("is going to hit 150,000") or "72,000 BTC" legitimises a stale price within ±5 %.
- PRICE_NOW is skipped when `current_levels is None` (the default in `VF.check`, `gates()` and the adapter).

**Duplicates**
- `duplicates` checks only the line right before a clip and the title. It misses the caption and a VO line that repeats a different clip.

### P1 — context integrity

- **Relations:** only relations the model chooses to list are judged. `B["relations"] == []` passes even if the VO says "both agree". Code does not require every pair to be rated.
- **Window:** the stated window is "≥ 90 s before / ≥ 60 s after". The code includes only sentences that start at or after `t0 - before` and end at or before `t1 + after`. The window is therefore at most those spans, never at least. Context can be materially shorter than the law demands.
- **Truncation:** `_q(contexts[lb]["text"], 6000)` could truncate a trailing retraction. I can't see `quote_data`'s behaviour, so this is uncertain.

### P2

- **Hard-coded vendor (L-x):**
  - `def _writer_vendor … return "openai"` and `def prescreen(…, writer_vendor="openai")`.
  - `transcript_truth.second_pass` hard-codes the model `gpt-4o-transcribe-diarize` and the OpenAI URL, and calls it outside the Router.
  - It bypasses the spend ledger and vendor config (and leaves the audio file handle open).
  - `HeimdallBackend.BASE` is a staging URL in production code.
- **Angle injection:** `WRITE_V2.format(angle=angle["angle"].replace('"', "'"), …)`.
  - Model text derived from untrusted transcripts enters the writer prompt unquoted, with newlines intact.
  - The angle is never gated, though the legacy `WRITE_PROMPT` still claims it is "checked like the VO".
  - The VO lines remain gated, so this is injection-to-gate pressure, not a bypass.
- **Coherence through-line:** `str(v["through_line"]).strip().lower() not in ("", "none")` passes "None." and "none – unrelated clips".
- **Unhashable values escape as `TypeError`:**
  - `check_verdict` (`c["line"] not in slots`, `x.get("segment") in texts`) raises `TypeError`.
  - `VF.check` catches only `(ProviderError, SpendLimit, ValueError)`.
  - `context_integrity` relations: `any(x not in vid for x in labs)` is outside the `try`.
  - Either crashes `build`. Fail-closed, but not a clean failure.
- **Outage costs moments:** `CONTEXT_UNAVAILABLE` has `segment "-"`, so `bad` is empty and `dropped |= {order[-1]}` drops a good clip on a provider outage. Three rebuilds waste spend.
- **Unvalidated precomputed `a_by`:** `check_contexts(a_by=…)` takes the dict without key validation, and `a.get("time_ok", "yes")` defaults a missing field to pass. This is reachable only via the public `a_by` argument. Law L-l says a missing field means a failed call.
- **Dead legacy code** with weaker gates: `candidate_sets`, `write`, `check_written` and `gates()` (no PRICE_NOW or DUPLICATE, no `now`). Remove it.
- **Failed trend brief cached:** `grok_brief` caches a failed brief for the whole 4 h cycle. Shadow only.
- **Speaker offset:** `speaker_turns(sec, PAD_S, …)` assumes a 1.5 s pad. `audio_window` uses `max(0, start - pad)`, so for `start < 1.5` the offset is wrong.

## Q2 answers in brief

- **Writer after a failover:** per attempt, `integrity(..., wr.vendor, None if wr.vendor in a_vendors else a_by, …)` re-runs step A when the precomputed vendor equals the writer. Coherence uses `wr.vendor`. I found no same-vendor path other than the `writer_vendor=None` exam adapter, which is intentional.
- **Vendor means host, not model lab.** A heimdall-hosted Gemma writer and a local Gemma verdict count as different vendors.
- **Router and contract violations:** the router does not convert contract violations into silent failover. Only `Unavailable` moves the chain. An empty or garbage reply returns as a `Reply`, and the caller fails closed.

## Q1 answer in brief

Control flow in `build` is otherwise sound. A package is appended only after `g["ok"]`, coherence and (when enabled) truth. A model reply that is not exactly "yes" or "no" fails the A, B and C decisions. The leaks are P0-1, P0-2, the relation omission and the runtime error.

## Highest-leverage change

Make `vo_fidelity.check_verdict` coverage-complete, and make the second pass mandatory.
1. Require at least one claim for every non-connective slot (intro, title, caption, any line with a fact), and reject `{"claims": []}`.
2. In `build`, remove the `if truth_dir:` default. Run the second pass on every segment, treating "no result" and `turn_change_inside is None` as failure. Compare in both directions, with counts and positions, and apply it to the plain-VO path too.

Failing both ways closed removes the two P0s and most of what the rule gaps in Q4 would otherwise let through.