# Frontier review (claude-opus-5-5, effort high) - pp-tests_moments_B

stop_reason: max_tokens; model: claude-opus-5-5; usage: in 80152 / out 32000

# Audit: pp-tests phase 2 moments-first exam (CORPUS_DIGEST.txt)

**Scope.** The diff contains only `CORPUS_DIGEST.txt`. It covers 137 cases:

- context_integrity: 66 cases (44 must-fail, 22 must-pass).
- vo_fidelity: 39 cases (27 must-fail, 12 must-pass).
- exclusions: 32 cases (23 exclude, 9 keep).

These counts meet the order's minimums. Everything below is checked against the digest only.

---

### 1. CRITICAL: the package format gives away the answer
**Where:** context_integrity, all must-pass versus all must-fail.

**Evidence:**
- **Bridge line.** Every one of the 22 must-pass cases (`clean_assertion__01..12`, `clean_conjunction_opener__01..10`) has the bridge `['Also on the record:']`. None of the 44 must-fail cases uses it. A gate that returns PASS exactly when bridge == "Also on the record:" scores 100% / 0%.
- **Undated captions.** The 3 `stale_time_reference` cases are the only ones whose caption has no dates (`CAPTION: Clips: Bitcoin Magazine; Swan Bitcoin.`). That makes the class separable by format alone.
- **Both-clip citations.** In vo_fidelity, a bridge line that cites `['A', 'B']` appears only in the 3 `invented_agreement` must-fails.

**Why it matters:**
- A builder's gate, or an LLM baseline, can learn the surface cue instead of the law.
- The confusion table would certify that gate.

**Fix:**
- Draw bridges, VO intros and caption formats from one shared pool, randomised across both labels. Put "Also on the record:" on must-fails too.
- Add must-pass cases with undated captions where the clip has no time word.
- Add stale must-fails that do have dated captions but whose VO says "today".
- Add must-pass VO lines that cite both clips.
- Add a harness check: a format-only classifier must score at chance.

### 2. HIGH: the harness and baseline adapter are not in the material
**Where:** `tests/adversarial/test_moments_gates.py`, the baseline adapter, `tests/adversarial/corpora/*`.

**Evidence:**
- The diff contains only `CORPUS_DIGEST.txt`.
- Case ids encode both class and verdict (`context_integrity__clean_assertion__01`). Records carry `origin=`, `EXPECTED=` and `why:`.

**Why it matters:**
- None of priorities 3–5 can be verified:
  - leakage of id, origin or why to the gate;
  - skip-with-reason when the gate is absent, never a pass;
  - absent versus error handling, and "uncertain" counted as a rejection;
  - exit-code precedence;
  - verbatim binding of each case to the store bytes;
  - cross-process reserve-then-settle spend guard;
  - keys read by name and never printed;
  - no network in the default run, no GPU, no writes outside the worktree.
- With only 9 exclusion keep cases, one false exclude is 11.1%. The "≤10%" threshold is therefore effectively 0 on that corpus. State this, or add keep cases.

**Fix:**
- Submit the harness and adapter for review.
- Pass the gate an opaque record: hashed id; `origin`, `why`, `EXPECTED` and class stripped; shuffled order.

### 3. HIGH: `context_integrity__later_retraction__04` has a must-fail label that is not defensible
**Evidence:**
- The clip is "every Bitcoin bear market has been shallower than the last … minus 53%" (k1227–1229).
- The host next says "We've spent ample time covering this **fact** on the show" (k1230).
- The host then adds only "But **maybe** there's a more nuanced view owed" (k1232). That nuance is about a different measure (drawdown relative to volatility, k1233).
- Nothing is retracted. The percentage claim in the title still holds.
- The corpus itself uses this same clip as a faithful source in `vo_fidelity__faithful_paraphrase__05` (PASS).

**Fix:** Drop this case or relabel it as pass. Replace it with a real reversal.

### 4. HIGH: must-pass titles name guests whose names are not in the clip, and the corpus contradicts itself on this
**Where:** `clean_assertion__02` ("Jeff Booth"), `clean_assertion__05` ("Mark Moss"), `clean_conjunction_opener__07` ("Kai-Fu Lee"), `clean_conjunction_opener__09` and `__10` ("Joe Burnett").

**Evidence:**
- L-t says "no absent names".
- `vo_fidelity__faithful_paraphrase__04` avoids naming Moss: "a guest says…", with why "no unverified name". So the corpus treats a VO naming Moss as unverified, while a must-pass title naming Moss is labelled clean.

**Why it matters:**
- A gate that applies L-t strictly would reject 5 of 22 must-pass cases (23%). That breaks the 10% threshold while being right.

**Second problem in `__09`:**
- k281–284 reads like the host setting up a question ("the Bitcoin community has been interested in various models, right? We had the stock to flow model…").
- The record has no speaker labels, so attributing k285 to Burnett is not verifiable.

**Fix:**
- Decide whether video-title metadata counts as manifest. Apply that decision in both corpora.
- Until then, attribute these titles to the channel or "a guest".
- Replace `__09`.

### 5. MEDIUM: `context_integrity__steelman__03` has a wrong class and a rationale that misses k175
**Evidence:**
- The why says the criticism is "withdrawn in k174".
- k175 then reaffirms it: "That's probably the thing they're doing wrong."
- The real trap is that the title drops the hedge ("if I was being critical", "probably"). It is not a steelman.

**Fix:**
- Reclassify as hedge dropped / stronger certainty, or replace with a real steelman.
- Correct the why to account for k175.

### 6. MEDIUM: must-fail cases that a gate can reject for the wrong reason
These cases inflate the per-class table: a gate gets credit for the class without detecting it.

| Case | Labelled class | Confound |
|---|---|---|
| `quoting_opponent__01` | quoting an opponent | Title "Saylor 'Would Be Insolvent, Would Be Bankrupt'" is a named insolvency accusation (L-u). |
| `sarcasm__04` | sarcasm | Title is a sell imperative; the same span is `exclusions__imperative__03`. |
| `false_dialogue__03` | false dialogue | Both clips are CoinTelegraph, which breaks one-clip-per-channel. The why concedes it. |
| `hypothetical__03` | hypothetical | Title attributes the MMT debater's words to Saifedean (wrong speaker). |
| `quoting_opponent__03` | quoting an opponent | Debate audio played inside Simply Bitcoin (third-party media) and credited to "Simply Bitcoin". |
| `conditional_split__03` | conditional split | VO names "Nvidia's chief", which is not in the clip. |
| `steelman__02` | steelman | Title quotes 'a Psyop'; the store reads "sci -op". |
| `later_retraction__02` | later retraction | The clip is part of interviewer GUY's question ("DO YOU THINK…? [k971]…"). |

**Fix:** Rebuild each package so that the labelled class is the only defect.

### 7. MEDIUM: `context_integrity__later_retraction__01` uses a non-spec window and has its own confound
**Evidence:**
- The case states "window: 60 sentences, 90s before / 80s after". The order fixes 60 s after.
- The title "Trump-Xi Summit in Shenzhen 'Next Month'" drops the clip's "reportedly" and "I believe it is". A gate can fail it for the dropped hedge without finding the k155–156 correction.

**Fix:**
- Remove the hedge drop from the title.
- Report beyond-window retractions as a separate stratum, and state the window that the harness actually feeds to the gate.

### 8. MEDIUM: `context_integrity__clean_conjunction_opener__02` drops a hedge in a must-pass title
**Evidence:**
- The clip says "And **I think** we are now already at the phase…".
- The title "BTC Sessions: Bitcoin Trading 'More and More' as a Macro Sound-Money Asset" drops "I think" and credits the channel, not the guest.
- Compare `clean_assertion__06` and `clean_conjunction_opener__07`, which keep "Think".

**Fix:** Retitle to "BTC Sessions Guest Thinks Bitcoin Is Trading 'More and More'…".

### 9. MEDIUM: `exclusions__guaranteed_return__01` is a shaky label and the class has only one case
**Evidence:**
- The text is "That **seems** like a fairly but risk free trade **to me**" (garbled).
- It is a hedged personal view about a block-sale deal offered to others (k27–30), not a guaranteed-return claim to viewers. It reads closer to the "framed personal view" near miss.

**Fix:** Mine at least 3 real "guaranteed / can't lose" claims, and drop or relabel this case.

### 10. LOW: two exclusion keep/exclude cases do not match their class
- **`exclusions__neutral_company__01`:** the moment says "The company will list… ticker ANT". The name "Anthropic" is in k976, outside the moment, so the moment does not name a company.
- **`exclusions__single_source_breaking__04`:** the OpenAI ~$11 billion raise is also reported in Yahoo Finance k44 (`sarcasm__03`). The "single-source" premise is contestable in the store itself.

**Fix:** Include k976 in `neutral_company__01`, or pick another case. Replace `single_source_breaking__04`.

### 11. LOW: confounds in VO must-fails
- **`absent_name__01`:** "Jerome Powell's Fed" is also false in the store's own world. TFTC k973 says "working with Warsh", and k435 says Powell is "staying on… shadow Fed chair".
- **`absent_name__03`:** "Larry Fink's ETFs" adds a false claim as well as an absent name.
