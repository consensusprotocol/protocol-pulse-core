# Frontier verification round (claude-opus-5-5, effort high)

stop_reason: end_turn; model: claude-opus-5-5; usage: in 86304 / out 38737

# Verification round: moments-first exam (CORPUS_DIGEST.txt, 139 cases)

**Scope.** This round's material is the digest only. The harness, the baseline adapter and the INDEX file are not in it, so every disposition that concerns code is marked unverifiable below.

**Counts (verified from the digest):**

| Corpus | Must-fail / exclude | Must-pass / keep | False-reject budget |
|---|---|---|---|
| context_integrity | 42 | 22 | 2 false rejects = 9.1% (allowed); 3 = 13.6% (fails) |
| vo_fidelity | 27 | 13 | 1 false reject = 7.7% |
| exclusions | 23 | 12 | 1 false exclude = 8.3% |

## 1. Status of previous findings

**#1 CRITICAL, format leak: RESOLVED for the cues I cited.**
- "Also on the record" is now on 9 must-fail cases (e.g. `steelman__01`, `false_dialogue__01`, `wrong_speaker__02`) and on 2 must-pass cases (`clean_assertion__09`, `clean_conjunction_opener__02`).
- Every caption is dated.
- A both-clip bridge now appears in a must-pass case (`vo_fidelity__manifest_language__05`, "Swan Bitcoin and Coin Bureau, one after the other.").
- New, smaller cues have appeared (new defects 2 and 6).

**#2 HIGH, harness not in material: PARTLY.**
- Keep cases are now 12, verified.
- The harness and adapter are again absent from this material. Blinding, salted ids, shuffling, the ERROR-vs-ABSENT path, the spend guard, network refusal and the pp-selectid check cannot be confirmed here.
- The VO digest gives no sentence ids or source paths for its clips, so the verbatim binding of the VO corpus cannot be checked from this material at all.

**#3 HIGH, `later_retraction__04`: RESOLVED.** The bear-market clip appears in no corpus.

**#4 HIGH, guest names in must-pass titles: RESOLVED.**
- No must-pass title names a person.
- The "Swan Bitcoin's Founder" claim checks out. A window of 18 sentences ending at k20 runs k3–k20, so it includes k4 ("I'm Corey Clifston, founder of Swan Bitcoin").
- This created the opposite asymmetry: person names now appear only in must-fail titles (new defect 2).

**#5 MEDIUM, `steelman__03`: RESOLVED by replacement** (Fox Business, TAYLOR k7). The fail is defensible because the title strips "THE COUNTERARGUMENT IN BIG TECH IS". One open point is under new defect 10.

**#6 MEDIUM, confounded must-fails: PARTLY.**
- Fixed: `hypothetical__03`, `quoting_opponent__03`, `steelman__02` (title) and `later_retraction__02` (replaced).
- Still confounded:
  - `sarcasm__04`: the clip still airs "Sell your Bitcoin, all of it." This is the same span as `exclusions__imperative__03`.
  - `quoting_opponent__01`: the clip still airs "Saylor … would be insolvent, would be bankrupt". The new title adds "Strategy", which is not audible in the clip.
  - `false_dialogue__03`: now crosses channels, but has a new confound (new defect 3).
  - `conditional_split__03`: the VO name is fixed, but the class is now weak (new defect 7).

**#7 MEDIUM, `later_retraction__01`: PARTLY.**
- The title keeps "Reportedly" and "I Believe".
- The window problem was "fixed" by changing every window to 80 s after. The order says 60 s after.
- The why cites "request R-24". That request is not in the material, so I cannot verify that the owner approved the deviation.
- Either get the deviation signed off, or keep 90 / 60 s and report beyond-window retractions as a separate stratum.

**#8 MEDIUM, dropped hedge in a must-pass title: RESOLVED.** `clean_conjunction_opener__04` keeps "'I Think'" and credits "On BTC Sessions". Its clip still contains "now" (new defect 5).

**#9 MEDIUM, `guaranteed_return`: RESOLVED.** Both cases are labelled CONSTRUCTED. A filler-text leak is noted under new defect 9.

**#10 LOW, exclusion cases not matching their class: RESOLVED.**
- `neutral_company__01` is now k1, "Strategy purchased 1,036 Bitcoin…".
- `single_source_breaking__04` is gone.

**#11 LOW, absent-name VO lines adding false claims: RESOLVED.** `absent_name__01`, `__02` and `__03` now put the clip's own words in an absent person's mouth.

**Held-out set (A2): REJECTED BY AUTHOR, NOT ACCEPTABLE AS ARGUED.**
- "No file is unreadable to the builder" is true. But a held-out set does not need unreadable files. It needs cases that did not exist when the gate was frozen.
- Achievable mitigation:
  1. Record the builder's gate commit sha in the report.
  2. Then mine a fresh slice of 10–15 cases per corpus.
  3. Report it separately.
- With the answers (`expected`, `why`) readable today, the blinding only protects the gate's runtime. It does not protect the builder's development.

## 2. New defects (most severe first)

### 1. HIGH: `context_integrity__clean_conjunction_opener__03` is a time-sensitive must-pass that the store suggests is false by the package date
- **The clip** (Coin Bureau, 2026-11-05) says "And our 75K target never broke. And once the results were in, Bitcoin didn't make a new low." It is packaged on 2026-11-12.
- **The store points the other way:**
  - Natalie Brunell, 2026-11-09 (lusJ1m-J0Mc, source of `exclusions__ad_read__02`), is titled "Bitcoin Falls to Its Lowest Since August".
  - Coin Bureau, 2026-11-10, is titled "Bitcoin's Midterm CRASH".
  - "Lowest since August" after an election-day low near 75K implies a new low. I cannot confirm the level from the material.
- **Inconsistency:** the author already removed the "bottom's in" clip from must-pass for exactly this reason.
- **Impact:** a correct gate rejects this case.
- **Fix:** drop it, or replace it with an undated, non-market claim.

### 2. HIGH: the wrong_speaker class is a free win for a person-name detector, and the class has an absent-name confound
- **Every wrong_speaker title names a person who is not audible in the clip:**
  - `wrong_speaker__01`: "Morgan Stanley's Mike Wilson" (the clip is the interviewer's ">> SO YOU'RE SAYING…").
  - `wrong_speaker__02`: "Kai-Fu Lee".
  - `wrong_speaker__03`: "Ambassador Haley". "HALEY" appears only in the caption label.
- **Three more must-fail titles credit "Scott Melker:" as a person:** `conditional_split__02`, `steelman__02` and `quoting_opponent__01`. That contradicts the author's own fix, under which person-named channels are credited as "<name>'s show". The captions of those cases already say "Scott Melker's show".
- **Effect:** "title names a person → FAIL" rejects 6 must-fail cases with 0 false rejects. L-t's absent-name rule rejects every wrong_speaker case for a reason that is not the class.
- **Fix:**
  - Credit the show in these titles ("On CNBC Television: …", "On Scott Melker's Show: …").
  - Add must-pass cases whose titles name a person who is audible in the clip.
  - Extend `test_no_package_field_separates_the_verdicts` with a "title contains a person name" feature.

### 3. HIGH: the false_dialogue class is untested because every moment fails on its own
- **The moments:**
  - `false_dialogue__03`: "Yeah, I think Bitcoin would have to fail." It answers the devil's-advocate question at k348–350.
  - `false_dialogue__01`: "No, you can't. They all go down." It answers k381, and "they" is unresolved.
  - `false_dialogue__02`: "Well, if I were them, I wouldn't buy any of them…". "Them" is unresolved, and the sentence is a hypothetical.
- **Effect:** a gate that ignores sequence and bridges scores 3/3 on this class.
- **Fix:** build each case from moments that would pass as must-pass on their own, taken from two different videos. Then let the bridge or sequence ("Not everyone is convinced.", or an implied reply) be the only defect.

### 4. MEDIUM: `clean_conjunction_opener__02` is not a "single narrator" clip, and has the paraphrase risk the author removed elsewhere
- **The video plays other voices:**
  - The moment is Simply Bitcoin l987bgGZjS0, k203.
  - The same video plays Darius Dale's audio (`exclusions__third_party_media__01`, k41: "I've been doing this for almost 20 years as an institutional investor").
  - k199, four sentences before the moment, says "Groman just told you the slow road…".
- **The paraphrase risk:** k200–203 continue Gromen's "slow road" argument. This is the pattern for which k130 and k133 were removed.
- **Knock-on effect:** `vo_fidelity__absent_name__01` relies on the claim that "the words are Simply Bitcoin's narrator's".
- **Related:** the VO clip "The case for holding Bitcoin crosses party lines." (Simply Bitcoin) may be the removed k133 "Michael Saylor pointed out that…". BTC Sessions k2 has "Michael Saylor says Bitcoin Reserve Support now crosses party lines". The VO digest has no sentence ids, so I cannot verify which sentence it is.
- **Fix:**
  - Replace `clean_conjunction_opener__02`.
  - Show sentence ids in the VO digest and confirm the Simply Bitcoin clip is not k133 or k134.

### 5. MEDIUM: the stale-time boundary is not stated, and one must-pass has a time word
- **The conflict:**
  - Now that every caption carries the clip date (e.g. `stale_time_reference__02`: "Bloomberg Television (2026-11-06)"), the summarised L-v ("time words need the original publish time") is literally satisfied in all three stale cases.
  - `clean_conjunction_opener__04` (must-pass) contains "we are **now** already at the phase".
- **Trap outside the window:** for `stale_time_reference__01`, the reason it is stale is "after the post-election drop". That drop is not in its window.
- **Fix:**
  - State the rule in the corpus: a time word that the title or VO presents as current on the package date is a FAIL, even with a dated caption.
  - Either drop `clean_conjunction_opener__04` or write why "now already at the phase" is not stale.
- **Threshold impact:** defects 1, 4 and 5 are three must-pass cases a correct gate may reject. That is 13.6% of 22, which breaks the ≤10% threshold while the gate is right.

### 6. MEDIUM: structural cues in vo_fidelity
- **Intro citations:**
  - All 27 must-fail intros are "[intro cites []] Two voices."
  - 6 of 13 must-pass intros cite clips: `manifest_language__01`, `02`, `03`, `04` and `06` cite ['A','B'], and `07` cites ['A'].
- **Clip B citations:** a line citing ['B'] alone appears in 9 of 13 must-pass cases and in no must-fail case. Clip B is pure filler in every must-fail.
- **Effect:** combining the two cues is not a full pass (it false-rejects 4 of 13, about 31%). But each cue is a free win for one class.
- **Fix:**
  - Draw intro citations from the shared pool for both labels.
  - Add must-fails whose bad line cites B, and whose intro cites both clips.
  - Extend the field-separation test to the vo_fidelity corpus.

### 7. MEDIUM: conditional_split class is weak in `__03` and possibly misattributed in `__02`
- **`conditional_split__03`:** the why itself concedes the condition is expected to be met ("IT FEELS LIKE HE WILL HAVE TO DO THAT", k314). What remains is an unresolved "IT", which is the unresolved_referent class.
- **`conditional_split__02`:** the clip is "It'll literally be impossible to stop it at all".
  - k381 ("Right.") marks a turn change, and k384 names the guest, Armani. So k382 may be the guest's line.
  - The title credits "Scott Melker:" as a person. I am uncertain about the speaker.
- **Fix:**
  - Replace `__03` with a genuinely open condition.
  - Credit `__02` to "Scott Melker's show".

### 8. MEDIUM: remaining wrong-reason paths in must-fail cases
- **`sarcasm__04`:** the clip still contains a sell imperative. Drop it; three sarcasm cases remain.
- **`quoting_opponent__01`:** the clip still contains a named insolvency claim, and the title adds "Strategy".
- **`later_retraction__02`:** "I didn't cut this one big game" is a garbled, unresolved referent.
- **`hypothetical__02`:** the title contains "Confirms". That is the source's own word, so it is legal, but a banned-verb check rejects it for the wrong reason.
- **Fix:** rebuild or replace each case so the labelled class is the only defect.

### 9. LOW: constructed exclusion cases are identifiable by shared filler
- **Repeated filler lines:**
  - "You can see the wick from Tuesday." appears in `partner_attack__01`, `partner_attack__02` and `guaranteed_return__01`.
  - "Funding has reset since then." appears in `partner_attack__01` and `__02`, and in `guaranteed_return__02`, where it has no antecedent.
  - "Okay, let's get to some of your questions." appears twice.
- **Other tells:** the publish times are round (:00:00), and all four constructed cases are excludes.
- **Separate concern:** the partner-attack cases put fabricated derogatory quotes in the mouths of real partner channels.
- **Fix:** write a unique context for each constructed case. Use fictional partner names, through a test partner list, if the config allows it.

### 10. LOW: incorrect statements and an unverified clip
- **The disposition "no moment is used by two cases" is false.** Three moments are shared:
  - Swan k13: `clean_assertion__01` and `title_adds_thesis__03`.
  - Swan k9: `clean_assertion__03` and `title_adds_thesis__02`.
  - Coin Bureau k20: `clean_assertion__04` and `title_adds_thesis__01`.

  These minimal pairs are good design. Correct the claim and report the pairs in the confusion table.
- **`wrong_speaker__03`'s why is wrong.** "IT IS TOO SOON TO TELL" (k169) answers a different question. The trap is simply that JOE's voice is credited to the guest.
- **`steelman__03` may not carry the full store sentence.** CLIP M ends "…TECH GUYS WHO SAY", while the window's k7 reads "…WHO SAY I WANT". Confirm the moment equals the store sentence, or the case adds a truncation confound.
- **`single_source_breaking__02` (Paraguay bank) may not be single-source.** It may be covered again by BTC Sessions NMhilOtqU98, "Banking Collapse LOCKS OUT Half A Country". I am uncertain; the country is not named in that title.

**NOT READY.** Three label defects (new defects 1, 4 and 5) could make a correct gate miss the 10% must-pass threshold. Two whole classes (wrong_speaker, false_dialogue) can be passed without detecting the trap. The harness is not in this material to verify.
