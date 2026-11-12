# claude-fable-5-2 (effort high) 469 s stop_reason=end_turn usage=in 87345 / out 44522

**Reviewer note:** I am Claude (Anthropic), not one of the three models named in the header. Scope limits: the diff contains no test files and no `pinned.py` / R7 patch, so Q5 is only answerable for `moments_gate_adapter.py` and `package_pin.py`. Laws L-m through L-x are cited by the code but are not in the law list I was given, and `canon.py`, `eligibility.py`, `select_by_id.py` and `story_semantics.quote_data` are not shown. Findings that depend on them say so.

## Scores

| Q | Score | Summary |
|---|---|---|
| Q1 fail-open | 35 | Explicit failures fail closed, but several gates pass when the model answers with nothing, and one gate is optional. |
| Q2 vendor separation / L-x | 70 | `avoid_vendor` holds through failover, rewrites and precomputed step A; L-x is broken by hard-coded vendors, and per-request errors trigger silent failover. |
| Q3 verbatim / model text | 75 | Clip text is by id only (assuming `Span.text` is verbatim); title, caption and VO are always gated; the angle is ungated and attribution is by channel, not speaker. |
| Q4 deterministic rules | 40 | Many concrete false passes and false rejects (table below). |
| Q5 tests / R7 | 15, on the two visible files only | Tests and R7 are not in the diff; the pin stamps gates as passed with literals. |

## P0

**P0-1. The pin asserts gates passed with constants** (`package_pin.py`)
`"checks": {"vo_fidelity_ok": True, "context_integrity_ok": True, "models": pk.get("models")}`
- `to_pin` never reads `pk["checks"]`.
- Failing input: any dict with the right keys (a plain-VO package, a hand-edited package, one that never went through `build`) is pinned with both flags `True`.
- Any R7 refusal keyed on these flags would be vacuous.

**P0-2. The blind fidelity verdict passes on an empty answer** (`vo_fidelity.check_verdict`)
`for c in obj["claims"]: ...` then `return {"ok": not v, ...}`
- Failing input: the reply `{"claims": []}` gives `ok: True`. A reply covering only the intro and skipping the title also passes.
- `write_v2` accepts `"cites": []` on every line, since `any(c not in ids for c in ln["cites"])` is false for an empty list.
- NEEDS_SOURCE only fires on a detected number, name, quote, attribution or time word.
- Combined: intro "The government is banning self-custody." with no cites and an empty verdict passes both layers.

**P0-3. The exclusion gate the exam certifies is not run in production** (`moments.py`, `package.py`, `moments_gate_adapter.py`)
- The adapter says "These are the SAME gates the packager runs (… `moments.exclusion_verdict`)".
- In the diff, `exclusion_verdict` is called only from the adapter.
- Production uses `"excluded": sorted(set(m["risk"]) & set(HARD_RISKS))`, which is the miner's own flags on the moment it just picked.
- `time_sensitive` in `usable()` rests on the same self-report.
- Failing input: the miner returns `"risk": []` for an accusation against a named person; nothing else in `build` screens it.

**P0-4. The second recognition pass (L-v 2) is optional, partial and one-directional** (`package.build`, `transcript_truth.py`)
- **Optional:** `if truth_dir:` with default `None`. The package is returned with no marker that the pass did not run.
- **Skipped for plain VO:** `out["plain"].append(pk3)` happens before the truth block, and `out["package"] = (out["packages"] or out["plain"] or [None])[0]`. So the plain fallback can ship unverified.
- **Partial:** `if any(TT.critical_tokens(sg["text"])[k] for k in ("numbers", "negations"))`. A segment with only names gets neither the name check nor diarisation.
- **One-directional:** `[n for n in a["negations"] if n not in bset]`. Whisper "Bitcoin is going to zero" against a second pass "is not going to zero" is never even sent for checking.
- **Set membership over the padded window:** a "not" in the ±1.5 s neighbour satisfies a missing one inside the selection.
- **Unmeasured passes:** `speaker_turns` returns `turn_change_inside: None` for "not measured", and `build` treats `None` as clean.

## P1

**P1-1. Step B relations pass when unanswered** (`context_integrity.check_contexts`)
`for rel in B["relations"]:`
- Nothing requires every pair to be answered.
- Failing input: `"relations": []` means FALSE_RELATION can never fire.

**P1-2. The speaker is always the channel** (`package.integrity`)
`"speaker": s["channel"], "names": [s["channel"]]`
- Step A's JSON has no "who is speaking" field, although the docstring promises one.
- Failing input: a guest's whole moment on the Natalie Brunell channel. No speaker change inside, own sincere view, so the VO "Natalie Brunell says …" passes ATTRIBUTION, and the blind verdict is told she is the speaker.

**P1-3. The attribution format the prompt recommends is unbound** (`vo_fidelity._attributions`, `WRITE_V2`)
- `WRITE_V2` recommends `"Saifedean Ammous: no authority…"`. `_attributions` knows only the verb list and "according to".
- Failing input: "Coin Bureau: Bitcoin could hit 200,000." citing both clips, where Natalie said 200,000. NUMBER checks the pooled cites and passes.
- Pronoun and lower-case subjects ("she says", "the host warns") are also undetected.

**P1-4. L-x violations**
- `transcript_truth.second_pass(wav, model="gpt-4o-transcribe-diarize", …)` with `api.openai.com` hard-coded. It bypasses the Router: one back-end, no failover, no spend ledger, no record/replay.
- `package.prescreen(..., writer_vendor="openai")` and `_writer_vendor` → `return "openai"`.
- `trend_brief` has a one-entry chain.
- `HeimdallBackend.BASE = "https://api-staging.heimdallm.com/api/v1"` is a staging host.
- `"/home/ultron/protocol_pulse/" + "." + "env"` (twice, plus the Router): why is the literal split? It reads like dodging a grep.

**P1-5. The Router turns per-request errors into silent, run-wide failover** (`providers.py`)
- Any non-429 4xx (for example a 400 for an over-long prompt or a policy refusal) raises `Unavailable(last)`, then `self.down[name] = str(e)`.
- `LocalBackend` raises `Unavailable("prompt over the local context …")` for one long prompt, which takes local down for every later role. That defeats "Ultron first".
- Reply-contract violations themselves are not failed over; parsing stays with the caller, which is correct.

**P1-6. The spend guard fails open, and blocks the free model**
- `_spent()` has `except (OSError, ValueError, TypeError): return 0.0`. A corrupt ledger means no limit, and `_account` then overwrites it from zero.
- `if self.spend_path and self._spent() >= self.limit_usd: raise SpendLimit` runs before `local:gemma3:27b` (price 0) is tried, so hitting the cap also stops the free back-end.

**P1-7. The exam adapter diverges from production and its must-fail cases can pass vacuously** (`moments_gate_adapter.py`)
- A `ReplayMiss`, a provider outage, or `len(moment) != 1` all return "fail" / "exclude", the same verdict as a real catch. An expected-fail case passes with no gate run unless the harness asserts the rule, which I cannot see.
- The adapter injects `"[another speaker] "` and `f"{s['speaker']}: "` markers; production `_window_text` never has them.
- It passes `manifest` and speaker names; production passes neither.
- It omits `current_levels`, so PRICE_NOW is off, and it omits `duplicates`.
- It never returns the "uncertain" its interface declares.

## P2

- **Default on a missing field:** `a.get("time_ok", "yes")` breaks L-l's "never a default" when `a_by` is supplied externally.
- **Wrong moment dropped:** `dropped |= bad or {order[-1]}`. A CONTEXT_UNAVAILABLE or RELATION_UNREADABLE (segment "-") from an outage drops an innocent last clip for the whole build.
- **Uncaught TypeError crashes the build:** `c["line"] not in slots`, `x not in vid` and `x not in HARD_RISKS` with a list value. Fail-closed, but one malformed reply kills the cycle.
- **Budget arithmetic:** `budgets` gives intro 40 % plus 30 % per bridge. With one bridge the estimate is `65 − 0.3·vo_s`, so a hook + 2 clips under about 41 s of content cannot reach 60 s within budget (taking `FIXED_S ≈ 7.4` from the comment).
- **Plain fallback is often impossible:** the plain VO is about 10–15 words, so it fails runtime unless content is roughly 47 s or more. Verdict calls are also spent when `runtime_ok` is already false.
- **Context window is "at most", not "at least":** `window()` includes sentences within 90 s / 60 s; the docstring says ">=". A retraction 61 s later is unseen.
- **`quote_data` on marked text:** `_q(contexts[lb]["text"], 6000)` passes `<selected>` tags through `quote_data`. If that escapes markup, the markers are destroyed. I cannot verify this.
- **Coherence through-line:** `str(v["through_line"]).strip().lower() not in ("", "none")`. "None." or "no through-line" counts as a through-line.
- **Invalid replies are cached:** the Router records any non-empty text and serves it again for the same seed. The angle call uses a fixed seed of 7, so an invalid reply is permanent and never re-asked.
- **Ungated angle:** `WRITE_PROMPT` says the angle "is checked like the VO"; it is not in `lines`. It is not audience-facing through the pin.
- **Dead weaker gate:** v1 `candidate_sets` / `write` / `gates()` are unused by `build`, and `gates()` lacks DUPLICATE and PRICE_NOW. `CI.repairable` is never called; the "extend backwards" repair in the docstring is not implemented.
- **AD_MARKERS:** `sponsor(ed)?` excludes "Senator Lummis sponsored the Bitcoin reserve bill". The marker is tested per sentence, so the sentence after "brought to you by River." is still offered.
- **Novelty by exact id:** `moment_id` includes `transcript_sha256`, so a re-punctuated record or an overlapping range defeats "delivered in the previous 24 h".
- **Duplicate violations:** the "according to" search sits inside `for v in ATTRIB_VERBS`, giving 29 identical violations.
- **Laws as given:** M1 says "no new selector" and this diff adds one. I assume a later order supersedes it, but that order is not shown. FRAMING compares line and source by raw regex outside `canon.py` (L-k).

## Q4: rule by rule

Number handling below assumes `canon` lower-cases tokens and turns number words into digits.

| Rule | False PASS | False REJECT |
|---|---|---|
| NEEDS_SOURCE | "Self-custody is being banned." with no cites | — |
| NUMBER | "Seven countries hold Bitcoin" (spelled numbers ≤ 10 are exempt); a unitless number equal to the segment count; "up 16 percent" when the clip says "down 16 percent" | "$74,000" when the speaker said "seventy-four thousand" without "dollars" (the unit must be adjacent) |
| NAME | "Saylor sold everything." (a sentence-initial single word is skipped); any Title Case line (`_title_case` returns `[]`); "the Trump Bitcoin Reserve" (`_run_in(a, nt)` exempts any run containing "Bitcoin") | "ETF" when the clip says "ETFs"; "Fed" when the clip says "Federal Reserve"; "Bitcoiners" |
| QUOTE | Single-quoted text; a one-word quote such as "fraud" (`len(ctoks(q)) >= 2`); a quote from any cited segment, not the attributed one | — |
| ATTRIBUTION | "X: …", "she says", or X's clip merely being cited | "The Fed says…" or "Saylor said…" when the clip itself reports it |
| ATTRIBUTION pool | — | "Natalie Brunell says 81,000 …; Coin Bureau warns of 74,000": `att_pool` is overwritten, and the last owner wins |
| RELATION | "goes further", "isn't buying it", "has a different view", "concurs" | "how miners respond to the halving", "fell in response to the Fed"; always rejected with one clip per video |
| FRAMING | "torches", "debunks", "concedes"; "destroys Natalie" when a clip says "inflation destroys savings" | "Bitcoin exposure" (`expos\w*`), "six confirmations", "caught a bid" |
| IMPERATIVE | "It's time to buy.", "So buy the dip.", "Never sell.", "You should be buying." | "Short-term holders are capitulating.", "Sell-off fears…", "Sell pressure is fading." |
| TIME | "The Senate just passed…", "this month", "currently", "overnight" | "record-breaking inflows", "is breaking resistance"; "right now" when the clip says "now" |
| PRICE_NOW | "trading at 126,000, a new all-time high" (the HISTORY regex exempts the whole line, as do "since", "once" and any year, so "200,000 by 2027" passes); percent moves are never checked; bridges are exempt | "Strategy holds 640,000 Bitcoin" (any value ≥ 1000 is treated as a price); an honestly attributed target in the intro |
| current_levels | "I think Bitcoin is going to 250,000" adds 250,000 as current (PRESENT matches "is"), so a headline within ±5 % passes | An empty set rejects every headline level |
| DUPLICATE | Paraphrase; a 4-token run; the caption | Clip "Bitcoin is the best money." against title "Why the Dollar Is Losing to Bitcoin": the stop-word share is 3/5 = 60 % |

## Q5

- **Tests and R7:** not in the diff, so I cannot say whether they fail for the right reason or whether R7 leaves a plain pin unchanged.
- **Visible wiring:** `to_pin` refuses nothing (P0-1).
- **Rendering today:** the `package_pin` docstring says `pinned.py` "ignores the block, so its VO falls back to none". Until R7 lands, a pin renders without the gated VO.
- **Exam:** vacuous on must-fail cases unless the harness checks the rule (P1-7).

## Single highest-leverage change

Apply the L-j pattern to the package.

- `package.build` emits a fixed gate inventory. Each row must be exactly PASS, with evidence that it executed and a sample count of at least 1. Rows:
  - fidelity deterministic;
  - fidelity verdict;
  - DUPLICATE;
  - PRICE_NOW;
  - context A, B and C;
  - runtime;
  - exclusion verdict;
  - second pass.
- Coverage is part of each row's contract:
  - every line is answered by the verdict;
  - every segment pair has a relation;
  - every segment has a second-pass result with a measured speaker.
- `package_pin.to_pin` and R7 refuse anything else, replacing the two literal `True`s.

This closes P0-1 through P0-4 and P1-1.