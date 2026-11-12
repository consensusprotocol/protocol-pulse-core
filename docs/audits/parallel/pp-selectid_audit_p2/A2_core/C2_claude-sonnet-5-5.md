# claude-sonnet-5-5 (effort high) 200 s stop_reason=end_turn usage=in 67380 / out 24566

# Cycle 2 audit: pp-selectid-p2, chunk A2_core (fixed diff)

**Scope and limits**
- This chunk holds `context_integrity.py`, `moments.py`, `transcript_truth.py`, `trend_brief.py` and `vo_fidelity.py`.
- `package.py`, `package_pin.py`, `providers.py`, the tests and the R7 patch are not in it. Cycle 1 findings that live there (pin literals, optional `truth_dir`, runtime arithmetic, router `down`, hard-coded vendors) cannot be re-verified from this diff.
- My Cycle 1 text was not supplied (the placeholder reads "[See below]"), so I cannot compare myself against it. The Cycle 1 column below shows the range of the other reviewers.
- I am Claude, not one of the three models named in the header.
- Line numbers are STEP.diff lines.

## 1. What the others caught that holds up

Checked against the fixed code in this chunk:

| Cycle 1 finding | Status in this chunk |
|---|---|
| Blind verdict passes on `{"claims": []}` | Partly fixed. Sentence coverage is now required, but it is checked by overlap, not coverage (new P0-1). |
| Step B may omit relation pairs | Fixed. Every pair must be rated exactly once (L408-418). |
| Truth `compare` is one-directional and set-based | Fixed. It now uses counts in both directions (L993-1000). |
| "Not measured" speaker passes | Fixed. `ok` needs `turn_change_inside is False` (L1046). |
| Title Case lines disable the NAME rule | Fixed. `names_of` no longer special-cases Title Case. |
| Colon attribution format unbound | Fixed. The `colon` form exists (L1561). |
| Exclusion verdict not wired | Not verifiable here. `record()` still sets `excluded` from the miner's own `risk` (L791). |
| Pin asserts literals, `truth_dir` optional, plain-VO skips the truth pass | Not in this chunk. |

## 2. Agree / disagree

- **Fable, Opus, Sonnet on the fidelity verdict (P0).** Agree. The fix is incomplete (new P0-1).
- **Sonnet: "any claim can cite the manifest."** Agree, and it is still open. See P0-2 below.
- **Grok P1, pin literals.** Agree in principle, but it is outside this chunk.
- **Grok Q4, RELATION false-rejects same-video "both agree."** Disagree. L1749-1751 only fires when `len(parties | named) > 1`, i.e. more than one video id.
- **Grok Q3 93 and Q2 88.** Too high. They ignore that the verdict's yes/no is the only semantic judge and that its supports are never tied to the claim.
- **Opus: transcript_truth hard-codes a vendor.** Not visible here. The router path `router.transcribe("transcribe", wav)` at L965 is clean.

## 3. New findings

### P0

**P0-1. Verdict coverage is overlap, not coverage** (`vo_fidelity.check_verdict`, L1923-1933).
- The test is `any(x < b and y > a for x, y in cover[slot])`. One claim whose `words` is a single token marks the whole sentence covered.
- Failing input: line "The government is banning self-custody." The reply gives one claim: words "The government", class commentary, all five tests "no".
  - `strict_features("The government")` is empty.
  - No VERDICT_INCOMPLETE fires.
  - The deterministic layer has no trigger, because there is no number, name, quote or attribution.
  - The line passes.
- Claims are also placed at the first occurrence of their words (`_run_find`, L1882), so repeated phrases miscount.
- This is the hole the consensus C2 fix says it closed.
- Fix:
  - Require the union of claim spans to cover every content token of each sentence. Allow at most a small, fixed stop-word residue.
  - Reject overlapping or duplicate placements.

**P0-2. Class laundering through "production", and supports are never tied to the claim** (L1904-1922).
- `allowed = {"manifest"}` for class production. There is no `strict_features`-style screen on production words; only commentary gets one (L1893).
- The support test is only "a verbatim ≥3-token run of an allowed text" (L1915).
- Failing input: a claim "The government is banning self-custody", class production, supported yes, support `{"segment": "manifest", "words": "The video is about Bitcoin"}`.
  - Every check passes.
  - A single mislabel by the model launders any trigger-free fact.
  - The same applies to attribution and fact claims: any 3 words of a cited segment "support" any claim.
- Fix:
  - Production claim words must be a near-verbatim sentence or template from `manifest_text`, with no number, name or verb outside it.
  - For all classes, require lexical overlap of content tokens between claim and support, or a fixed-template check.

### P1

**P1-1. Names that are dictionary words bypass NAME and the transcript-truth name check** (`names_of` L1534, `critical_tokens` L979-981).
- `lexicon()` holds every lowercase dictionary word. So "Bill Gates", "Larry Fink", "Mark Carney", "Swan", "Strike", "Strategy", "Fidelity", "Block", "Ledger" and "Marathon" are never candidates.
- Failing input: title "Strategy Buys Another 5000 BTC" with no clip naming Strategy. NAME stays silent.
- The rule also depends on a host file, `/usr/share/dict/words` (L1349). CI and production can disagree; the OSError fallback only fails closed.
- Fix:
  - Treat any mid-sentence capitalised token as a name candidate, whatever the dictionary says.
  - Check the sentence-initial token against the lexicon only.
  - Ship a pinned word list.

**P1-2. The second pass never checks that the audio matches the selection** (`verify_segment` L1033-1046, `span_text` fallback L1040).
- A selection with no number, negation or name passes the compare against any second text, including an empty one, a wrong window, or the whole padded `sec["text"]` fallback.
- Diarisation then rests on possibly mis-aligned audio.
- With segment-level timing (no word times), a neighbour's "not" or number can offset a missing one in the selection, because comparison is by counts.
- Fix:
  - Require a token-overlap floor (for example ≥0.7) between the selection and the second-pass span.
  - Fail when the span is empty.
  - Fail, rather than fall back to the full text, when word timing is absent.

**P1-3. Step C downgrades unverifiable model answers to NOTES.**
- `entails: "no"` with no verbatim outside limit is only a note (L466-469).
- `stronger_certainty: "yes"` with non-verbatim raising words is a note (L490-497).
- `added_by` that does not name the show or speaker is a note (L475-478).
- Step B0, which can excuse STRONGER (L485), has no `avoid_vendor` or `avoid_family` (L392). It is cheap, but it loosens a gate.
- Notes gate nothing and nobody is shown to read them.
- Fix:
  - Re-ask once when "no" arrives without a limit, and fail if it still has none.
  - Count notes in the pin inventory.
  - Run B0 under the same vendor avoidance.

**P1-4. `check()` drops the show date, and an unclocked window collapses to the selection.**
- `check()` calls `contexts_from_sources(package, sources)` with `now=None` (L229). So `show_date` is "unknown" and STALE_TIME rests on the model alone.
- `window()` with `t0` or `t1` None returns just the selection (L56, L71). Step A then sees no context and "no retraction" is vacuous.
- Fix: make `now` a required argument, and raise when the selection's own times are missing.

**P1-5. Host verification is easy to satisfy** (`speaker_verified` L261-270).
- Evidence only needs to be any ≥3-token run anywhere in the ±90 s excerpt, including inside the selection or in another speaker's turn ("thank you so much").
- The model's "host" plus that phrase lets `_segment_names` credit a named person ("Natalie Brunell says…").
- Fix:
  - Require self-identification patterns, or evidence located before the selection with no diarised turn change between the two.
  - Without a name evidenced in the transcript, never name a person.

**P1-6. PRICE_NOW misses plain "is/was/of" prices** (`PRICE_PREPS` L1325, `_price_values` L1417).
- "Bitcoin is 74,000 right now": the preceding token "is" is not in `PRICE_PREPS` and there is no "dollars", so no price is detected.
- NUMBER still passes if the source said it on another day.
- Fix: add "is", "was", "are", "of", "valued", "priced" and "worth", and treat a 5-digit number near "Bitcoin" as a price.

### P2

- **Truncation.** `quote_data(text, n)` limits the clip views (900 chars), the exclusion `moment` (1500) and `before`/`after` (3000, L886-888, L1825-1829). The gate judges full text while the model sees cut text. Reject over-limit text instead of cutting, and verify which end `quote_data` cuts.
- **Partial `contexts` accepted.** `check_contexts` judges only labels that have a context (L372); `out["judged"]` records this. Confirm the caller asserts `judged == all labels`.
- **Name fold bug.** `rstrip("'’s")` strips every trailing "s" (L996, L998): "Hayes" becomes "haye", compared against unfolded tokens. It false-rejects when the second pass writes the name in lowercase.
- **Negation list.** It is closed and omits "without", "unlikely", "unable" and "fail(s) to". "can not" vs "cannot" is a false reject.
- **Audio cache.** `audio_window` reuses an existing `.wav` (L950). A crash mid-ffmpeg leaves a truncated file. Write to a temp name, then rename.
- **Trend cache.** `trend_brief.grok_brief` reads the cache outside its `try` (L1193-1195), so a corrupt cache file crashes instead of re-asking.
- **Dedup.** `mine()` dedups "last wins" (L818-821). If duplicates ever arrive, take the union of risks, not the last record's.
- **Exclusion avoidance.** `exclusion_verdict` avoids only the miner's model (`avoid_model`), not its vendor or family.
- **Attribution verbs.** The list is closed: "is bullish", "doubts", "fears", "wants" and "sounds" are unbound. The blind layer is the only catch.

## 4. Revised scores (this chunk only)

| Subsystem | Cycle 1 (peers' range) | Cycle 2 | Why changed |
|---|---|---|---|
| Q1 Fail-open | 35-72 | 50 | Explicit failures, empty second-pass speaker and missing pairs now fail closed. Overlap coverage, production laundering and NOTE downgrades remain. |
| Q2 Vendor separation / L-x | 66-88 | 70 | Avoidance is threaded through A, B, C, fidelity and coherence. B0 and the exclusion verdict avoid less. The router is not visible. |
| Q3 Verbatim / model text | 58-93 | 78 | Clip text stays by id. Fix: the cited-support check is only verbatimness, not relevance (P0-2). |
| Q4 Deterministic rules | 40-55 | 45 | Title Case and attribution fixed. Dictionary-word names, PRICE_NOW gaps and the closed verb list remain. |
| Q5 Tests / R7 | 15-45 | 30 | Not in this chunk. The pin and R7 are unverified. |

## 5. Final priority list

**P0**
1. `vo_fidelity.py` L1923-1933: full token coverage, no overlap shortcut.
2. `vo_fidelity.py` L1904-1922: bind production claims to manifest templates, and require claim↔support relevance in every class.

**P1**
3. `vo_fidelity.py` L1534 and `transcript_truth.py` L979-981: names must not depend on dictionary membership or a host file.
4. `transcript_truth.py` L1033-1046: alignment floor, empty-span failure, no whole-text fallback.
5. `context_integrity.py` L464-497 and L392: re-ask or fail instead of NOTE, and apply vendor avoidance to B0.
6. `context_integrity.py` L229 and L56-76: required `now`, and fail on unclocked windows.
7. `context_integrity.py` L261-270: stronger host evidence.
8. `vo_fidelity.py` L1325 and L1417: widen price detection.
9. Outside this chunk: confirm the pin inventory and seal, the exclusion verdict wired into `usable()`, `truth_dir` mandatory for the plain-VO path, and the runtime arithmetic (the sign-off subtracted twice).

**P2**: the items listed above.

## 6. Single highest-leverage change

Make the blind verdict's acceptance code-verifiable: full token coverage, claim↔support relevance and a closed production template, so one mislabelled or omitted model answer can no longer pass a line.

## 7. Production ready?

**No.** Conditions to ship:
- P0-1 and P0-2 fixed, with regression tests: partial-coverage reply, production-laundered fact, manifest-cited fact.
- P1-1 to P1-6 fixed, or each recorded with an owner and the law that permits it.
- Outside this chunk, show the pin inventory with seal recompute, the exclusion verdict on the production path, and the second-pass check mandatory with a recorded "ran / not run" marker.
- Tests in chunk B must assert the must-fail cases against production code paths, not the exam adapter.