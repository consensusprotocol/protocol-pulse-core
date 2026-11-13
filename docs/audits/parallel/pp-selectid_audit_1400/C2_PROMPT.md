# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-1400
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 181 s finish=stop usage in 15825 / out 4783 usd~0.119 (upper-bound price)

# Audit: pp-selectid-1400 — ATTESTED-TEXT RE-SEAL (RULING 67)

Scope: I verified what the diff shows. I did not run the code; where behavior depends on unseen modules (`canon.canon_tokens`, `package_pin.seal`, the render's `pinned.adjudicate_lock`), I state assumptions.

## P0

None found.

## P1

**P1-1 — `attest.py:79` carry_class: "immediate repetition" is checked before the function-word class, and a delete/insert of repeated function words is classified as repetition — fine — but the repetition test is one-sided and can misclassify a *replace* whose both sides repeat.**
`carry_class` only tests `tag == "delete"` / `tag == "insert"` for the repetition branch. For a `replace` opcode (e.g. run "we buy it we buy it" vs pin "we buy it now" — actually that's a delete; consider run "that's why that's why" vs pin "that's why, so" → SequenceMatcher may emit `replace`), the repetition branch is skipped and the tokens fall to the FUNCTION_WORDS check. That is *correct* per the ruling's wording ("a function word, or an immediate repetition") only if a repeated-phrase replace is meant to be carried as a function-word diff when all tokens are function words, or refused otherwise. Scenario: run "and that's why that's why we" vs pin "and that's why we" — SequenceMatcher can emit this as `replace("that's why", "that's why that's why")`-adjacent opcodes rather than a pure insert depending on alignment; if it emits `replace` with repeated tokens on the run side, the diff is refused (class None) even though the ruling's example ("a repeated 'that's why'") is exactly this shape. The shipped fixture happens to align as insert/delete, but the ruling's carry-over class is alignment-dependent. Concrete risk: a future held pin with the same editorial phenomenon refuses where the ruling says it should carry. Not a correctness bug on this pin; flagging as P1 because the ruling's example is the very case that is alignment-fragile. Mitigation if accepted: also treat `replace` where one side's tokens are a repetition of its own neighbours.

**P1-2 — `attest.py:86-95` reads(): the "one neighbour on each side" window can pass when the recogniser's alignment is coincidental, and the end-anchoring uses `len(s) - 1` which is wrong when the difference is at the very end and the recogniser's text has trailing tokens.**
Line 95: `(lo > 0 or xmap[idx[0]] == 0) and (hi < len(x) or xmap[idx[-1]] == len(s) - 1)`. When `hi == len(x)` (difference at the end of the run decode), it requires the last matched token to be the *last token of the recogniser's text* — i.e. the recogniser may not hear anything after the clip's last word. That is the intended "at x's end nothing may follow" rule, but note the neighbour window `idx` extends to `min(hi + 1, len(x))`, so when `hi == len(x)` the window is `lo-1..len(x)-1` and the anchor demands `xmap` of the *last* token = `len(s)-1`. If the recogniser's transcript of the clip ends with, say, a trailing "Mm-hmm" or a punctuation-only token that canon keeps, the reads() check fails and the reseal refuses — fail closed, so not a correctness bug, but the docstring's "one neighbour on each side" is not what the end anchor enforces (it enforces *nothing follows in s at all*). Same, symmetric, at the start. This is stricter than the render's rule only if the render's `reads` is identical; the comment claims "pinned.adjudicate_lock's reads" — I cannot verify byte-equality from this diff. If the render's version differs (e.g. it does not require the end anchor), this side's check is stricter and a pin the render would pass gets refused here: fail closed, P1 not P0. **Verify against the render's source that the two `reads` implementations are behaviourally identical; the docstring asserts it, the diff cannot.**

**P1-3 — `reseal_attested.py:249-250` the second-recogniser match on start/end uses rounding to 3 decimals, but the build record's clip times and the pin's `seg["start"]/["end"]` come from different stages; a 1 ms disagreement silently yields `sp == []` → refusal.**
`round(float(t.get("start", -1)), 3) == round(float(seg["start"]), 3)`. If the build record stored the clip times before any later rounding (e.g. 6-decimal floats) and the pin sealed rounded values, equality at 3 decimals can still fail when the true difference straddles a 0.0005 boundary. Fail closed (refusal, nothing written), so P1 not P0 — but the error message ("no live reading of the clip in the build record") would mislead. Concrete: this is the single most likely operational failure of this tool on the *next* pin. Suggest: if `sp` is empty, include the candidate start/ends found near `seg["start"]` in the error.

**P1-4 — `reseal_attested.py:236` the run's words are taken as `transcripts/<vid>.json["words"][i0:i1+1]` — inclusive of i1 — while the hold string's range and the pin's word span convention must agree; if the render's hol

## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 65 s finish=stop usage in 15596 / out 577 usd~0.092 (upper-bound price)

**P0: none verifiable from diff**  
**P1: none verifiable from diff**  
**P2: pipeline/attest.py:122 (attested_text word_at + words)**  
Concrete scenario: an insert opcode with lo == hi on the pin token side that falls inside a multi-token approved word (e.g. "that'swhy" tokenized as one canon token but split by run decode) would hit the "if lo < n and not wmap[lo][1]" guard and raise ValueError("a difference splits a word..."). The test suite never exercises a split inside a single approved surface word; the real held-pin case uses whole-word boundaries only. Behavior matches the documented "Raises ValueError when a difference does not fall on whole words (fail closed)", but the guard's exact token-length assumption is not exercised on a replace-inside-punctuated-word case also present in the fixture texts.  

**P2: tests/package/reseal_attested.py:253**  
Concrete scenario: build_rec["tried"][0]["attempts"][0]["second_pass"] contains a replayed=True reading that exactly matches start/end/VID. The code explicitly rejects it ("a replayed reading is never evidence"), matching the ruling's "live, not replayed" requirement and the test "test_it_refuses_without_both_recognisers_or_on_another_pin". The refusal path writes nothing (exit 2), satisfying fail-closed. However, the lookup uses round(..., 3) on floats; the diff supplies no proof that every prior build record uses identical 3-decimal rounding, so a future float drift would silently skip the live reading and refuse a valid reseal.  

**P2: tests/package/test_speakers.py:472**  
Concrete scenario: any pin carrying "btc_screen" (the 13:38 pin committed 13:45) previously failed the "every earlier pin still recomputes" loop because seal() was called without the final argument. The added mp.get("btc_screen") makes the test match the integrator's check_pin_only call site and restores the "earlier pins unchanged" guarantee after SEALED_LATER grew. Pure test-only change; no runtime effect on pins.  

All other paths (carry_class never returns carry for critical tokens, attested_text produces canon-equivalent output, reads() requires both recognisers to agree on run decode at every diff + neighbors, quotes() blocks any line containing a changed span, seal compatibility for pre-attested pins, nothing written on any refusal, attested record sealed inside package_sha256) match the ruling text, the held-clip fixture, L-j byte-exact authorisation, L-k canonical-form requirement, selection-lock preservation, and the 12 passing suites. K1–K5 readings above are identical to the ruling.  

**SHIP: yes**

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 95 s finish=stop usage in 17297 / out 7070 usd~0.158 (upper-bound price)

I’ll audit the diff strictly against the stated laws and the specific change. I will focus on the new `attest.py` logic, the `reseal_attested.py` orchestration, the seal compatibility, and the test coverage.

### P0 Findings (Blockers)

**1. `attest.py`: `critical()` logic is flawed for names and ordinals (Law L-v / Ruling 67 violation)**
*   **File:** `pipeline/attest.py`, lines 47-59.
*   **Issue:** The `critical()` function determines if a token is a "name" by checking if it is capitalized mid-sentence in *either* text. However, it returns `True` (critical) if *any* match in the text is capitalized mid-sentence.
    *   Scenario: If the run decode has "bitcoin" (lowercase) and the pin has "Bitcoin" (capitalized, mid-sentence), `critical("bitcoin", ...)` will find the match in the pin text, see it is capitalized and not at the start, and return `True`. This correctly flags it as critical.
    *   **The Bug:** Consider a token like "I". The code explicitly excludes "I" from the name check (`w != "I"`). However, consider a proper noun that *is* at the start of a sentence in one text but mid-sentence in the other, or simply a common word that happens to be capitalized in a title-case context.
    *   **More Critical Bug:** The `LV2_ORDINALS` list includes "half", "quarter", "double", "triple", "dozen". These are not strictly ordinals in the linguistic sense of "first/second", but more importantly, the `critical` check `tok in LV2_ORDINALS` will flag "half" as critical. If the speaker says "half" and the ASR writes "half", it's fine. But if the diff is between "half" and "1/2" (which canon might normalize differently), or if "half" is considered a content word in this context, it might be over-restrictive.
    *   **The Real P0:** Look at `carry_class` (line 68). It calls `critical(t, texts)` for *every* token in the difference. If *any* token is critical, it returns `None` (refuse).
    *   **Scenario:** The ruling says "If any differing token is a number, a name, a negation or a content word... re-judged".
    *   **Code Behavior:** `critical` returns `True` for numbers, negations, ordinals, and names. It returns `False` for function words.
    *   **Missing:** What about **content words** that are *not* names, numbers, negations, or ordinals? E.g., "code" vs "card".
        *   `critical("code", ...)` -> No digit, not in negations, not in ordinals. Is it a name? "code" is lowercase. Returns `False`.
        *   `carry_class` then checks if it's an "immediate repetition" (no) or a "function word" (is "code" in `FUNCTION_WORDS`? No).
        *   So `carry_class` returns `None`.
        *   **Result:** It refuses. This is **correct** behavior (fail closed).
    *   **Wait, let's look closer at `critical`'s name detection.**
        *   `re.finditer(r"[A-Za-z][A-Za-z'’-]*", t or "")`
        *   If the token is "Saylor", and the text is "I told Saylor today".
        *   `w` = "Saylor". `w.lower()` == "saylor". `w[0].isupper()` is True. `w != "I"` is True.
        *   `before` = "I told ". `before[-1]` is space. Not in `.!?`.
        *   Returns `True`. Correct.
    *   **Is there a case where `critical` returns `False` for a name?**
        *   If the name is at the start of a sentence in *both* texts?
        *   Text: "Saylor is here." Token: "saylor".
        *   `w` = "Saylor". `before` = "" (empty). `if before and ...` fails. Returns `False`.
        *   **P0:** A name at the start of a sentence is **not** flagged as critical by `critical()`.
        *   **Consequence:** If the diff is `["Saylor"]` vs `["Saylor"]` (no diff) it's fine. But if the diff is `["Saylor"]` (run) vs `["saylor"]` (pin) or vice versa, and it's the first word of the clip/sentence, `critical` returns `False`.
        *   Then `carry_class` checks: Is it a repetition? No. Is it a function word? No. Returns `None`.
        *   **Result:** It refuses.
        *   **So, is it a P0?** The refusal is safe (fail closed). The law says "If any differing token is a... name... re-judged". The code refuses, which triggers the re-judge path (or blocks it). It does *not* incorrectly carry it over.
        *   **However**, the docstring for `critical` says: "a name (in either text, a capitalised word that does not open a sentence...". It explicitly *excludes* words that open a sentence.
        *   **Ruling 67 says:** "If any differing token is a number, a name, a negation or a content word...". It does *not* exclude names that open a sentence.
        *   **Risk:** If a name opens a sentence, `critical` returns `False`. `carry_class` returns `None` (because it's not a function word). The reseal is **refused**.
        *   **Is this a violation?** The refusal is the safe path. The code does not *incorrectly* re-seal. It just fails to *identify* it as a name for the purpose of the error message, but the outcome (refusal) is the same as if it h

## CLAUDE'S CYCLE 1 CONSENSUS
# pp-selectid audit 1400 (RULING 67: the attested-text re-seal): cycle 1 consensus

- **Run:**
  - grok: "SHIP: yes", P2s only.
  - glm: "SHIP: yes, with conditions", single-model P1s.
  - qwen: "SHIP: Yes with conditions", after two "P0"s its own text contradicts.
- No P0 holds against the code.
- Nothing changes in the code; cycle 2 reviews the same diff.

## REFUTED (with evidence)

| # | claim | the code / the evidence |
|---|---|---|
| R1 | qwen "P0": the repetition test checks the wrong side (delete/insert swapped), so "immediate repetition" never fires | difflib's get_opcodes describes turning the FIRST sequence into the SECOND. diff() is `SequenceMatcher(None, r, p)` with r = the run's tokens, p = the pin's. 'delete' means r[i1:i2] is in the run and not the pin (j1 == j2); 'insert' means p[j1:j2] is in the pin and not the run (i1 == i2). carry_class tests `delete -> repeats(r, a, b)` and `insert -> repeats(p, c, d)`: the side that HOLDS the tokens. Evidence: (1) the real held clip's op is ('delete', 38, 40, 38, 38), whose run tokens "that's why" are classed "immediate repetition" (the dry run); (2) test_a_number_a_name_a_negation_or_a_content_word_is_never_carried asserts "we buy it we buy it now" vs "we buy it now" -> ["immediate repetition"]. "buy" is not a function word, so only the repetition branch can return that, and the suite passes (qwen notes the contradiction itself). |
| R2 | qwen "P0": a name opening a sentence is not critical | critical() is the render's _lv2_critical rule exactly (pipeline/pinned.py:335-347 in the main tree, read only): "a capitalised word that does not open a sentence; 'I' excepted". The point is to classify exactly as the render's lock does. A sentence-opening name that is not repeated is a content word, so its class is None (refused, "re-judged first"). |
| R3 | qwen P1: the integrator's package_pin may lack "attested" in SEALED_LATER, so the seal mismatches | The integrator's check_pin_only loads THIS worktree's pipeline/package_pin.py (spec_from_file_location on /home/ultron/worktrees/pp-selectid/pipeline/package_pin.py). The integrator confirmed it in writing at 14:0x: '"attested" in SEALED_LATER is picked up with no change on my side ... make sure the commit adding it lands in your worktree before you send READY'. The commit lands before READY, and check_pin_only is run on the re-sealed pin before it is sent. |

## Answered

| # | finding | the answer |
|---|---|---|
| A1 | glm P1-2: is attest.reads() behaviourally identical to the render's reads()? | Yes, verified against pipeline/pinned.py (adjudicate_lock: amap + reads). The same equal-opcode alignment map, the window `range(max(lo - 1, 0), min(hi + 1, len(x)))`, the consecutive check, and the start / end anchors `(lo > 0 or xmap[idx[0]] == 0) and (hi < len(x) or xmap[idx[-1]] == len(s) - 1)`. The only change: s is a parameter instead of a closure variable. |
| A2 | glm P1-4: the recomputed diff is never compared with the diff the render's hold re

---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_1400/C2_STEP.diff (477 lines)
```
   1 | diff --git a/pipeline/attest.py b/pipeline/attest.py
   2 | new file mode 100644
   3 | index 0000000..61fd446
   4 | --- /dev/null
   5 | +++ b/pipeline/attest.py
   6 | @@ -0,0 +1,148 @@
   7 | +"""RULING 67 (orchestrator 14:02 Nov 13): ATTESTED-TEXT RE-SEAL.
   8 | +
   9 | +When the render's decode and the second recogniser AGREE on a span and the pin's text differs, the pin is re-sealed
  10 | +with the attested text (law L-v: the words as spoken). The verdicts already paid for carry over, recorded as carried
  11 | +with the exact diff, ONLY when every differing token is a function word or an immediate repetition of the speaker's
  12 | +own words. If any differing token is a number, a name, a negation or a content word, the clip's step A (both vendors)
  13 | +and the stand-alone verdict are re-judged on the attested text before the seal (not done here: such a diff is
  14 | +refused). The takeaway, title and caption are re-gated only if they quote the changed words (refused here too).
  15 | +
  16 | +The diff is the render's own (pipeline/pinned.adjudicate_lock): canon.canon_tokens of the run's decode against the
  17 | +approved text, difflib.SequenceMatcher(autojunk=False) opcodes. canon.py here is byte-identical to the render's, and
  18 | +critical() is the render's _lv2_critical with its lists. CPU only, no model call. Imports nothing from package.py
  19 | +(package_pin, which the integrator's check imports, must never pull it in)."""
  20 | +import re
  21 | +from difflib import SequenceMatcher
  22 | +
  23 | +import canon
  24 | +
  25 | +# pipeline/pinned.py (the render), LV2_NEGATIONS / LV2_ORDINALS / _lv2_critical, copied verbatim in behaviour
  26 | +LV2_NEGATIONS = frozenset({"not", "no", "never", "none", "nobody", "nothing", "neither", "nor", "cannot", "can't",
  27 | +                           "won't", "don't", "doesn't", "didn't", "isn't", "aren't", "wasn't", "weren't", "shouldn't",
  28 | +                           "wouldn't", "couldn't", "hasn't", "haven't", "hadn't"})
  29 | +LV2_ORDINALS = frozenset({"first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth", "tenth",
  30 | +                          "eleventh", "twelfth", "twentieth", "hundredth", "thousandth", "millionth", "billionth",
  31 | +                          "half", "quarter", "double", "triple", "dozen"})
  32 | +# English closed-class words: articles, demonstratives, pronouns, prepositions, conjunctions, auxiliaries and their
  33 | +# contractions, wh-words. NO negation, number or ordinal is in it (those are law L-v 2's critical tokens).
  34 | +FUNCTION_WORDS = frozenset("""
  35 | +a an the this that these those that's this's there there's here here's
  36 | +i you he she it we they me him her us them my your his its our their mine yours hers ours theirs
  37 | +myself yourself himself herself itself ourselves themselves one's
  38 | +i'm you're he's she's it's we're they're i've you've we've they've i'll you'll he'll she'll it'll we'll they'll
  39 | +i'd you'd he'd she'd we'd they'd
  40 | +in on at to of for from with by about into onto upon over under up down out off through as like than via per
  41 | +and or but so because if then when while though although whether
  42 | +is are was were be been being am do does did have has had will would can could shall should may might must
  43 | +what which who whom whose why how where
  44 | +""".split())
  45 | +
  46 | +
  47 | +def critical(tok, texts):
  48 | +    """Law L-v 2 as the render tests it (pinned._lv2_critical): a number, a negation, or a name (in either text, a
  49 | +    capitalised word that does not open a sentence; 'I' excepted). A doubtful token is critical."""
  50 | +    if re.search(r"\d", tok) or tok in LV2_NEGATIONS or tok.endswith("n't") or tok in LV2_ORDINALS:
  51 | +        return True
  52 | +    for t in texts:
  53 | +        for m in re.finditer(r"[A-Za-z][A-Za-z'’-]*", t or ""):
  54 | +            w = m.group(0)
  55 | +            if w.lower() == tok and w[0].isupper() and w != "I":
  56 | +                before = t[:m.start()].rstrip()
  57 | +                if before and before[-1] not in ".!?":
  58 | +                    return True
  59 | +    return False
  60 | +
  61 | +
  62 | +def diff(run_text, pin_text):
  63 | +    """The render's ruling-17 diff -> (run tokens, pin tokens, the non-equal opcodes (tag, a, b, c, d))."""
  64 | +    r, p = canon.canon_tokens(run_text), canon.canon_tokens(pin_text)
  65 | +    return r, p, [o for o in SequenceMatcher(None, r, p, autojunk=False).get_opcodes() if o[0] != "equal"]
  66 | +
  67 | +
  68 | +def carry_class(r, p, op, texts):
  69 | +    """RULING 67: the class of one difference -> "immediate repetition", "function word", or None (re-judge).
  70 | +    An immediate repetition: one side holds tokens the other lacks, and they repeat the tokens right before or right
  71 | +    after them on that side (the speaker's own words said twice). No critical token (L-v 2) is ever carried over."""
  72 | +    tag, a, b, c, d = op
  73 | +    if any(critical(t, texts) for t in r[a:b] + p[c:d]):
  74 | +        return None
  75 | +
  76 | +    def repeats(x, lo, hi):
  77 | +        n = hi - lo
  78 | +        return n > 0 and (x[max(lo - n, 0):lo] == x[lo:hi] or x[hi:hi + n] == x[lo:hi])
  79 | +    if (tag == "delete" and repeats(r, a, b)) or (tag == "insert" and repeats(p, c, d)):
  80 | +        return "immediate repetition"
  81 | +    if r[a:b] + p[c:d] and all(t in FUNCTION_WORDS for t in r[a:b] + p[c:d]):
  82 | +        return "function word"
  83 | +    return None
  84 | +
  85 | +
  86 | +def reads(x, s, lo, hi):
  87 | +    """The second recogniser's tokens s read x's tokens lo..hi-1 AT this position (pinned.adjudicate_lock's reads):
  88 | +    they and one neighbour on each side are aligned and consecutive in s; at x's start / end nothing may precede /
  89 | +    follow them in s."""
  90 | +    xmap = {a + k: b + k for op, a, a2, b, _ in SequenceMatcher(None, x, s, autojunk=False).get_opcodes()
  91 | +            if op == "equal" for k in range(a2 - a)}
  92 | +    idx = list(range(max(lo - 1, 0), min(hi + 1, len(x))))
  93 | +    if not idx or not all(i in xmap for i in idx) or not all(xmap[j] == xmap[i] + 1 for i, j in zip(idx, idx[1:])):
  94 | +        return False
  95 | +    return (lo > 0 or xmap[idx[0]] == 0) and (hi < len(x) or xmap[idx[-1]] == len(s) - 1)
  96 | +
  97 | +
  98 | +def attested_text(pin_text, run_words):
  99 | +    """The minimal edit of the approved text to the run's decode: the approved surface words wherever the tokens are
 100 | +    equal, the run's own decoded words at each difference. run_words: the run's decoded words of the locked span, in
 101 | +    order. Raises ValueError when a difference does not fall on whole words (fail closed). The result's canonical
 102 | +    tokens equal the run decode's exactly (checked)."""
 103 | +    pw = pin_text.split()
 104 | +    rw = [str(w).strip() for w in run_words if str(w).strip()]
 105 | +    pt = [canon.canon_tokens(w) for w in pw]
 106 | +    rt = [canon.canon_tokens(w) for w in rw]
 107 | +    p, r = [t for x in pt for t in x], [t for x in rt for t in x]
 108 | +    if p != canon.canon_tokens(pin_text) or r != canon.canon_tokens(" ".join(rw)):
 109 | +        raise ValueError("the per-word canonical tokens do not add up to the text's (fail closed)")
 110 | +
 111 | +    def word_at(tok_lens):                              # token index -> (word index, first token of that word)
 112 | +        out, k = {}, 0
 113 | +        for i, n in enumerate(tok_lens):
 114 | +            for j in range(n):
 115 | +                out[k + j] = (i, j == 0)
 116 | +            k += n
 117 | +        return out, k
 118 | +    pmap, pn = word_at([len(x) for x in pt])
 119 | +    rmap, rn = word_at([len(x) for x in rt])
 120 | +
 121 | +    def words(wmap, n, lo, hi, side):                  # the whole words covering tokens lo..hi-1
 122 | +        if lo == hi:                                    # an insertion point must fall between two words
 123 | +            if lo < n and not wmap[lo][1]:
 124 | +                raise ValueError(f"a difference splits a word on the {side} side (fail closed)")
 125 | +            return []
 126 | +        if not wmap[lo][1] or (hi < n and not wmap[hi][1]):
 127 | +            raise ValueError(f"a difference splits a word on the {side} side (fail closed)")
 128 | +        return sorted({wmap[t][0] for t in range(lo, hi)})
 129 | +    out = []
 130 | +    for tag, c, d, a, b in SequenceMatcher(None, p, r, autojunk=False).get_opcodes():   # pin -> run
 131 | +        if tag == "equal":
 132 | +            out += [pw[i] for i in words(pmap, pn, c, d, "approved")]
 133 | +        else:
 134 | +            words(pmap, pn, c, d, "approved")
 135 | +            out += [rw[i] for i in words(rmap, rn, a, b, "run")]
 136 | +    text = " ".join(out)
 137 | +    if canon.canon_tokens(text) != r:
 138 | +        raise ValueError("the attested text's tokens are not the run decode's (fail closed)")
 139 | +    return text
 140 | +
 141 | +
 142 | +def quotes(lines, r, p, ops):
 143 | +    """The lines (takeaway, title, caption, ...) that quote the changed words: a line holding, consecutively, the
 144 | +    approved tokens of a difference with one neighbour on each side, or the run's. -> [line text]."""
 145 | +    def has(text, w):
 146 | +        t, n = canon.canon_tokens(text), len(w)
 147 | +        return n > 0 and any(t[i:i + n] == w for i in range(len(t) - n + 1))
 148 | +    hit = []
 149 | +    for line in lines:
 150 | +        for _, a, b, c, d in ops:
 151 | +            if has(line, p[max(c - 1, 0):d + 1]) or has(line, r[max(a - 1, 0):b + 1]):
 152 | +                hit.append(line)
 153 | +                break
 154 | +    return hit
 155 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
 156 | index 0573b1d..90c18f3 100644
 157 | --- a/pipeline/package_pin.py
 158 | +++ b/pipeline/package_pin.py
 159 | @@ -70,7 +70,8 @@ SEALED_LATER = ("time_sensitive", "source_published_at",   # ruling 1 (22:40): t
 160 |                  "trimmed_leading", "untrimmed_start",      # ruling 33 part 2 (render merged 11e361cc): only when a word
 161 |                  "scorer_pending",                          # is trimmed, so every other pin seals as before (ruling 49 a;
 162 |                                                             # retired by ruling 56: kept so its pins still recompute)
 163 | -                "scorer_verdict")                          # ruling 56: the clip scorer's affirmation, only when sealed
 164 | +                "scorer_verdict",                          # ruling 56: the clip scorer's affirmation, only when sealed
 165 | +                "attested")                                # ruling 67: the attested-text re-seal's record (re-sealed)
 166 |  TRIMMED_PER_PIN_MAX = 1                                    # ruling 49 (b): package.TRIMMED_PER_LINEUP_MAX. Kept a
 167 |                                                             # separate constant (a test holds them equal): the
 168 |                                                             # integrator's check_pin_only imports this module, which
 169 | diff --git a/tests/package/reseal_attested.py b/tests/package/reseal_attested.py
 170 | new file mode 100644
 171 | index 0000000..f1d8979
 172 | --- /dev/null
 173 | +++ b/tests/package/reseal_attested.py
 174 | @@ -0,0 +1,135 @@
 175 | +#!/usr/bin/env python3
 176 | +"""RULING 67 (orchestrator 14:02 Nov 13): re-seal a pin the render HELD at ruling 17 with the ATTESTED text of the
 177 | +clip it held (pipeline/attest.py). CPU only, no model call; every input is read only.
 178 | +
 179 | +usage: reseal_attested.py PIN RUN_DIR BUILD_DIR
 180 | +  PIN        the sealed pin the render held
 181 | +  RUN_DIR    the render's run that held it: PROVENANCE.json names the pin file it rendered (its seal must be PIN's);
 182 | +             status.json's one hold reads "<video> words <i0>-<i1>: lock text not adjudicated (ruling 17): ... the
 183 | +             second recogniser reads the run decode"; transcripts/<video>.json holds the run's decoded words
 184 | +  BUILD_DIR  the build that sealed PIN: its package.json holds this side's own second recogniser (scribe_v1) reading
 185 | +             of that clip, recorded live by law L-v 2
 186 | +
 187 | +Writes MOMENTS_PIN_ATTESTED.json beside PIN (never over an existing file). Refuses (exit 2, nothing written) unless:
 188 | +the render's hold says its second recogniser reads the run decode; this side's second recogniser reads the run decode
 189 | +at every difference too; every difference is in ruling 67's carry-over class (a function word, or an immediate
 190 | +repetition of the speaker's own words; never a number, a name or a negation); no line quotes the changed words; and
 191 | +the attested text's canonical tokens are the run decode's, so no ruling-17 difference is left. The re-sealed segment
 192 | +carries "attested" (package_pin.SEALED_LATER: sealed): the text it replaced, the exact diff with each difference's
 193 | +class, and that the pin's verdicts and gates carry over."""
 194 | +import copy
 195 | +import json
 196 | +import os
 197 | +import re
 198 | +import sys
 199 | +from datetime import datetime, timezone
 200 | +
 201 | +HERE = os.path.dirname(os.path.abspath(__file__))
 202 | +REPO = os.path.dirname(os.path.dirname(HERE))
 203 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
 204 | +import attest as AT  # noqa: E402
 205 | +import package_pin  # noqa: E402
 206 | +
 207 | +HOLD = re.compile(r"(?P<vid>[A-Za-z0-9_-]{11}) words (?P<i0>\d+)-(?P<i1>\d+): lock text not adjudicated \(ruling 17\): "
 208 | +                  r"at .*? the second recogniser reads the run decode \|")
 209 | +
 210 | +
 211 | +def reseal(pin, run_dir, build_rec, build_dir="", now=None):
 212 | +    """-> (the re-sealed pin, a summary). Raises ValueError with the reason (fail closed)."""
 213 | +    mp = pin["moments_package"]
 214 | +    args = lambda segs: (segs, mp["edl_vo"], mp.get("signoff_expected"), mp["title"], mp["caption"], mp["gates"],
 215 | +                         mp.get("btc_screen"))
 216 | +    if package_pin.seal(*args(pin["segments"])) != mp["package_sha256"]:
 217 | +        raise ValueError("the pin does not recompute to its own seal with this package_pin")
 218 | +    prov = open(os.path.join(run_dir, "PROVENANCE.json")).read()
 219 | +    m = re.search(r"--pinned (\S+?\.json)", prov)
 220 | +    if not m:
 221 | +        raise ValueError("the run's PROVENANCE names no pinned file")
 222 | +    with open(m.group(1)) as f:
 223 | +        if json.load(f)["moments_package"]["package_sha256"] != mp["package_sha256"]:
 224 | +            raise ValueError(f"the run rendered another pin ({m.group(1)})")
 225 | +    with open(os.path.join(run_dir, "status.json")) as f:
 226 | +        holds = [h for h in json.load(f).get("holds") or [] if HOLD.search(str(h))]
 227 | +    if len(holds) != 1:
 228 | +        raise ValueError(f"{len(holds)} ruling-17 holds where the second recogniser reads the run decode (need 1)")
 229 | +    h = HOLD.search(str(holds[0]))
 230 | +    vid, i0, i1 = h["vid"], int(h["i0"]), int(h["i1"])
 231 | +    idx = [i for i, s in enumerate(pin["segments"]) if s["video_id"] == vid]
 232 | +    if len(idx) != 1:
 233 | +        raise ValueError(f"{len(idx)} segments on {vid} (need 1)")
 234 | +    seg = pin["segments"][idx[0]]
 235 | +    with open(os.path.join(run_dir, "transcripts", f"{vid}.json")) as f:
 236 | +        words = [str(w["word"]) for w in json.load(f)["words"][i0:i1 + 1]]
 237 | +    run_t, pin_t = " ".join(w.strip() for w in words), seg["approved_text"]
 238 | +    r, p, ops = AT.diff(run_t, pin_t)
 239 | +    if not ops:
 240 | +        raise ValueError("the approved text already reads the run decode")
 241 | +    classes = [AT.carry_class(r, p, o, (run_t, pin_t)) for o in ops]
 242 | +    if None in classes:
 243 | +        raise ValueError("ruling 67: a differing token is a number, a name, a negation or a content word: step A "
 244 | +                         "(both vendors) and the stand-alone verdict are re-judged first: " +
 245 | +                         str([[" ".join(r[a:b]), " ".join(p[c:d])] for (_, a, b, c, d), k in zip(ops, classes)
 246 | +                              if k is None]))
 247 | +    sp = [t for tr in build_rec.get("tried") or [] for at in tr.get("attempts") or []
 248 | +          for t in (at.get("second_pass") or {}).values()
 249 | +          if t.get("video_id") == vid and round(float(t.get("start", -1)), 3) == round(float(seg["start"]), 3)
 250 | +          and round(float(t.get("end", -1)), 3) == round(float(seg["end"]), 3)]
 251 | +    if not sp or sp[0].get("replayed") is not False or not sp[0].get("second_pass_text"):
 252 | +        raise ValueError("this side's second recogniser has no live reading of the clip in the build record")
 253 | +    s = AT.canon.canon_tokens(sp[0]["second_pass_text"])
 254 | +    if not all(AT.reads(r, s, a, b) for _, a, b, _c, _d in ops):
 255 | +        raise ValueError("this side's second recogniser does not read the run decode at every difference")
 256 | +    text = AT.attested_text(pin_t, words)
 257 | +    lines = [x["text"] for x in mp["edl_vo"].get("bridges") or []] + \
 258 | +        ([mp["edl_vo"]["intro"]] if mp["edl_vo"].get("intro") else []) + [mp["title"], mp["caption"]]
 259 | +    q = AT.quotes(lines, r, p, ops)
 260 | +    if q:
 261 | +        raise ValueError(f"ruling 67: these lines quote the changed words and are re-gated first: {q}")
 262 | +    out = copy.deepcopy(pin)
 263 | +    diffs = [{"run": " ".join(r[a:b]), "approved": " ".join(p[c:d]), "class": k}
 264 | +             for (_, a, b, c, d), k in zip(ops, classes)]
 265 | +    out["segments"][idx[0]].update(approved_text=text, attested={
 266 | +        "rule": "ruling 67 (orchestrator 14:02 Nov 13): the attested-text re-seal",
 267 | +        "was": pin_t, "differences": diffs,
 268 | +        "carried": "every verdict and gate this pin was sealed with, judged on the text it replaces: each difference "
 269 | +                   "is in ruling 67's carry-over class, and no line quotes the changed words",
 270 | +        "render": {"run": os.path.basename(os.path.normpath(run_dir)), "words": [i0, i1], "decode": run_t},
 271 | +        "second_recogniser": {"model": sp[0].get("model"), "text": sp[0]["second_pass_text"], "record": build_dir}})
 272 | +    sha = package_pin.seal(*args(out["segments"]))
 273 | +    old = mp["package_sha256"]
 274 | +    at = (now or datetime.now(timezone.utc)).isoformat(timespec="seconds")
 275 | +    out["story_id"] = re.sub(r"-[0-9a-f]{8}$", "-" + sha[:8], pin["story_id"])
 276 | +    out["approved_at"] = at
 277 | +    out["approval_ref"] = f"{pin.get('approval_ref')}; re-sealed under ruling 67 (the attested text of {vid})"
 278 | +    out["moments_package"].update(package_sha256=sha, resealed={"of": pin["story_id"], "package_sha256": old,
 279 | +                                                                 "rule": "ruling 67", "at": at})
 280 | +    return out, {"segment": idx[0], "video_id": vid, "differences": diffs, "text": text, "was": pin_t,
 281 | +                 "story_id": out["story_id"], "package_sha256": sha}
 282 | +
 283 | +
 284 | +def main(argv=None):
 285 | +    a = argv if argv is not None else sys.argv[1:]
 286 | +    if len(a) != 3:
 287 | +        print(__doc__, file=sys.stderr)
 288 | +        return 2
 289 | +    pin_path, run_dir, build_dir = a
 290 | +    dest = os.path.join(os.path.dirname(os.path.abspath(pin_path)), "MOMENTS_PIN_ATTESTED.json")
 291 | +    try:
 292 | +        if os.path.exists(dest):
 293 | +            raise ValueError(f"{dest} exists (never written over)")
 294 | +        with open(pin_path) as f:
 295 | +            pin = json.load(f)
 296 | +        with open(os.path.join(build_dir, "package.json")) as f:
 297 | +            rec = json.load(f)
 298 | +        out, summary = reseal(pin, run_dir, rec, os.path.relpath(os.path.abspath(build_dir), REPO))
 299 | +    except (OSError, ValueError, KeyError, TypeError) as e:
 300 | +        print(f"REFUSED (ruling 67): {type(e).__name__}: {e}", file=sys.stderr)
 301 | +        return 2
 302 | +    with open(dest, "x") as f:
 303 | +        json.dump(out, f, indent=1)
 304 | +    print(json.dumps(dict(summary, path=os.path.relpath(dest, REPO)), indent=1))
 305 | +    return 0
 306 | +
 307 | +
 308 | +if __name__ == "__main__":
 309 | +    sys.exit(main())
 310 | diff --git a/tests/package/test_attest.py b/tests/package/test_attest.py
 311 | new file mode 100644
 312 | index 0000000..66b5f3c
 313 | --- /dev/null
 314 | +++ b/tests/package/test_attest.py
 315 | @@ -0,0 +1,147 @@
 316 | +#!/usr/bin/env python3
 317 | +"""RULING 67 (orchestrator 14:02 Nov 13): the attested-text re-seal (pipeline/attest.py, tests/package/reseal_attested.py).
 318 | +The fixture is the pin the render held at 13:48 ET (ledger_20261113_183302, clip 3 mKNAcOFMYD4 words 32-73)."""
 319 | +import copy
 320 | +import json
 321 | +import os
 322 | +import sys
 323 | +import tempfile
 324 | +import unittest
 325 | +
 326 | +HERE = os.path.dirname(os.path.abspath(__file__))
 327 | +REPO = os.path.dirname(os.path.dirname(HERE))
 328 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
 329 | +sys.path.insert(0, HERE)
 330 | +import attest as AT  # noqa: E402
 331 | +import package_pin  # noqa: E402
 332 | +import reseal_attested as RA  # noqa: E402
 333 | +
 334 | +PIN = os.path.join(HERE, "proof", "ledger_20261113_183302", "MOMENTS_PIN_LEDGER.json")
 335 | +APPROVED = ("My biggest fear is that I go to the bank and I punch you my code and the money's not there because the bank "
 336 | +            "owns the money and they could just take it from me. And that's why we Bitcoin.")
 337 | +RUN = ("my biggest fear is that i go to the bank and i punch in my code and the money's not there because the bank owns "
 338 | +       "the money and they could just take it from me. and that's why that's why we bitcoin.")
 339 | +SCRIBE = ("My biggest fear is that I go to the bank and I punch in my code and the money's not there, 'cause the bank "
 340 | +          "owns the money and they could just take it from me. And that's why, that's why we Bitcoin.")
 341 | +ATTESTED = ("My biggest fear is that I go to the bank and I punch in my code and the money's not there because the bank "
 342 | +            "owns the money and they could just take it from me. And that's why that's why we Bitcoin.")
 343 | +
 344 | +
 345 | +class TestAttest(unittest.TestCase):
 346 | +    def test_the_held_clip_is_the_carry_over_class(self):
 347 | +        r, p, ops = AT.diff(RUN, APPROVED)
 348 | +        self.assertEqual([[" ".join(r[a:b]), " ".join(p[c:d])] for _, a, b, c, d in ops],
 349 | +                         [["in", "you"], ["that's why", ""]])            # the render's own diffs, verbatim
 350 | +        self.assertEqual([AT.carry_class(r, p, o, (RUN, APPROVED)) for o in ops],
 351 | +                         ["function word", "immediate repetition"])
 352 | +        s = AT.canon.canon_tokens(SCRIBE)
 353 | +        self.assertEqual([AT.reads(r, s, a, b) for _, a, b, c, d in ops], [True, True])    # reads the run decode
 354 | +        self.assertEqual([AT.reads(p, s, c, d) for _, a, b, c, d in ops], [False, False])  # not the approved text
 355 | +        self.assertEqual(AT.attested_text(APPROVED, RUN.split()), ATTESTED)
 356 | +        self.assertEqual(AT.diff(RUN, ATTESTED)[2], [])                   # no ruling-17 difference is left
 357 | +
 358 | +    def test_a_number_a_name_a_negation_or_a_content_word_is_never_carried(self):
 359 | +        for run, pin in (("the money is there", "the money is not there"),          # a negation
 360 | +                         ("i paid 3 coins", "i paid 2 coins"),                     # a number
 361 | +                         ("the first block", "the second block"),                  # an ordinal
 362 | +                         ("i punch in my card", "i punch in my code"),             # a content word
 363 | +                         ("as I told Saylor today", "as I told him today"),        # a name (capitalised mid-sentence)
 364 | +                         ("no no it is fine", "no it is fine")):                   # a repeated negation stays critical
 365 | +            r, p, ops = AT.diff(run, pin)
 366 | +            self.assertTrue(ops, (run, pin))
 367 | +            self.assertIn(None, [AT.carry_class(r, p, o, (run, pin)) for o in ops], (run, pin))
 368 | +        r, p, ops = AT.diff("we buy it we buy it now", "we buy it now")            # a repeated phrase: carried
 369 | +        self.assertEqual([AT.carry_class(r, p, o, ("", "")) for o in ops], ["immediate repetition"])
 370 | +
 371 | +    def test_the_attested_text_is_a_minimal_edit_with_the_run_tokens(self):
 372 | +        self.assertEqual(AT.attested_text("So it is, Mr. Big.", "so it was mr big".split()),
 373 | +                         "So it was Mr. Big.")                           # the run's whole word replaces "is,"
 374 | +        with self.assertRaises(ValueError):                                       # a difference inside a word
 375 | +            AT.attested_text("a well-known fact", "a well made fact".split())
 376 | +        self.assertEqual(AT.canon.canon_tokens(AT.attested_text(APPROVED, RUN.split())), AT.canon.canon_tokens(RUN))
 377 | +
 378 | +    def test_a_line_quoting_the_changed_words_is_found(self):
 379 | +        r, p, ops = AT.diff(RUN, APPROVED)
 380 | +        self.assertEqual(AT.quotes(["i punch you my code, he says", "no single owner"], r, p, ops),
 381 | +                         ["i punch you my code, he says"])
 382 | +        self.assertEqual(AT.quotes(["No single owner controls the bitcoin network"], r, p, ops), [])
 383 | +
 384 | +
 385 | +class TestReseal(unittest.TestCase):
 386 | +    """reseal() on the pin the render held, with its run's records rebuilt in a temporary directory."""
 387 | +
 388 | +    def setUp(self):
 389 | +        with open(PIN) as f:
 390 | +            self.pin = json.load(f)
 391 | +        self.tmp = tempfile.TemporaryDirectory()
 392 | +        d = self.tmp.name
 393 | +        self.frozen = os.path.join(d, "MOMENTS_PIN_LEDGER_183302.json")
 394 | +        with open(self.frozen, "w") as f:
 395 | +            json.dump(self.pin, f)
 396 | +        os.makedirs(os.path.join(d, "transcripts"))
 397 | +        with open(os.path.join(d, "PROVENANCE.json"), "w") as f:
 398 | +            json.dump({"x": {"owner": f"pulse_check_run 1 (--pinned {self.frozen})"}}, f)
 399 | +        with open(os.path.join(d, "transcripts", "mKNAcOFMYD4.json"), "w") as f:
 400 | +            json.dump({"words": [{"word": "x"}] * 32 + [{"word": " " + w} for w in RUN.split()]}, f)
 401 | +        self.hold("the run decode")
 402 | +        seg = self.pin["segments"][2]
 403 | +        self.rec = {"tried": [{"attempts": [{"second_pass": {"c3": {
 404 | +            "video_id": "mKNAcOFMYD4", "start": seg["start"], "end": seg["end"], "model": "elevenlabs_stt:scribe_v1",
 405 | +            "replayed": False, "second_pass_text": SCRIBE}}}]}]}
 406 | +
 407 | +    def tearDown(self):
 408 | +        self.tmp.cleanup()
 409 | +
 410 | +    def hold(self, side):
 411 | +        with open(os.path.join(self.tmp.name, "status.json"), "w") as f:
 412 | +            json.dump({"holds": [f"pinned: pinned decision rejected: mKNAcOFMYD4 words 32-{32 + len(RUN.split()) - 1}"
 413 | +                                 f": lock text not adjudicated (ruling 17): at [['in', 'you']] the second recogniser "
 414 | +                                 f"reads {side} | run_decode: '...'"]}, f)
 415 | +
 416 | +    def test_the_held_pin_is_re_sealed_with_the_attested_text(self):
 417 | +        out, summary = RA.reseal(self.pin, self.tmp.name, self.rec, "tests/package/proof/ledger_x")
 418 | +        seg, mp = out["segments"][2], out["moments_package"]
 419 | +        self.assertEqual(seg["approved_text"], ATTESTED)
 420 | +        self.assertEqual(seg["attested"]["was"], APPROVED)
 421 | +        self.assertEqual([(x["run"], x["approved"], x["class"]) for x in seg["attested"]["differences"]],
 422 | +                         [("in", "you", "function word"), ("that's why", "", "immediate repetition")])
 423 | +        sha = package_pin.seal(out["segments"], mp["edl_vo"], mp.get("signoff_expected"), mp["title"], mp["caption"],
 424 | +                               mp["gates"], mp.get("btc_screen"))
 425 | +        self.assertEqual((mp["package_sha256"], out["story_id"]), (sha, "moments-ledger_20261113_183302-" + sha[:8]))
 426 | +        self.assertNotEqual(sha, self.pin["moments_package"]["package_sha256"])
 427 | +        self.assertEqual(mp["resealed"]["package_sha256"], self.pin["moments_package"]["package_sha256"])
 428 | +        segs = [{k: v for k, v in s.items() if k != "attested"} for s in out["segments"]]
 429 | +        self.assertNotEqual(package_pin.seal(segs, mp["edl_vo"], mp.get("signoff_expected"), mp["title"],
 430 | +                                             mp["caption"], mp["gates"], mp.get("btc_screen")), sha)   # sealed
 431 | +        self.assertEqual([s["approved_text"] for i, s in enumerate(out["segments"]) if i != 2],
 432 | +                         [s["approved_text"] for i, s in enumerate(self.pin["segments"]) if i != 2])   # one clip
 433 | +
 434 | +    def test_it_refuses_without_both_recognisers_or_on_another_pin(self):
 435 | +        self.hold("neither")                                               # the render's recogniser did not attest
 436 | +        with self.assertRaises(ValueError):
 437 | +            RA.reseal(self.pin, self.tmp.name, self.rec)
 438 | +        self.hold("the run decode")
 439 | +        rec = copy.deepcopy(self.rec)                                      # this side's recogniser reads the pin
 440 | +        rec["tried"][0]["attempts"][0]["second_pass"]["c3"]["second_pass_text"] = APPROVED
 441 | +        with self.assertRaises(ValueError):
 442 | +            RA.reseal(self.pin, self.tmp.name, rec)
 443 | +        rec["tried"][0]["attempts"][0]["second_pass"]["c3"].update(second_pass_text=SCRIBE, replayed=True)
 444 | +        with self.assertRaises(ValueError):                                # a replayed reading is never evidence
 445 | +            RA.reseal(self.pin, self.tmp.name, rec)
 446 | +        other = copy.deepcopy(self.pin)
 447 | +        other["moments_package"]["package_sha256"] = "0" * 64
 448 | +        with open(self.frozen, "w") as f:
 449 | +            json.dump(other, f)
 450 | +        with self.assertRaises(ValueError):                                # the run rendered another pin
 451 | +            RA.reseal(self.pin, self.tmp.name, self.rec)
 452 | +
 453 | +    def test_it_refuses_a_difference_outside_the_carry_over_class(self):
 454 | +        with open(os.path.join(self.tmp.name, "transcripts", "mKNAcOFMYD4.json"), "w") as f:
 455 | +            json.dump({"words": [{"word": "x"}] * 32 + [{"word": w} for w in RUN.replace("code", "card").split()]}, f)
 456 | +        with self.assertRaises(ValueError) as e:
 457 | +            RA.reseal(self.pin, self.tmp.name, self.rec)
 458 | +        self.assertIn("re-judged first", str(e.exception))
 459 | +
 460 | +
 461 | +if __name__ == "__main__":
 462 | +    unittest.main()
 463 | diff --git a/tests/package/test_speakers.py b/tests/package/test_speakers.py
 464 | index 876be01..f3230cd 100644
 465 | --- a/tests/package/test_speakers.py
 466 | +++ b/tests/package/test_speakers.py
 467 | @@ -219,7 +219,8 @@ class TestPinCarriesTheSpeaker(unittest.TestCase):
 468 |                  continue
 469 |              n += 1
 470 |              self.assertEqual(package_pin.seal(pin["segments"], mp["edl_vo"], mp.get("signoff_expected"), mp["title"],
 471 | -                                              mp["caption"], mp["gates"]), mp["package_sha256"], p)
 472 | +                                              mp["caption"], mp["gates"], mp.get("btc_screen")),   # as check_pin_only
 473 | +                             mp["package_sha256"], p)
 474 |          self.assertGreaterEqual(n, 6)                                    # 37c5b5f5, 41f29b1f and the four L-y pins
 475 |          unknown = {"name": "unknown", "role": None, "line": None, "basis": None, "why": "", "people": [],
 476 |                     "measured": True}
 477 | 
```

---

You are auditing a SMALL change on branch pp-selectid (Protocol Pulse: the builder that seals the pins the integrator
renders). Your role: a strict reviewer of a path that changes a SEALED pin's text. Only state what you can verify from
the diff; if uncertain, say so; do not guess.

Background (static):
- A pin seals each clip's approved_text, the exact words the render must find. package_pin.seal is sha256 over a
  canonical body: the segments (video, start, end, text, transcript sha, and each SEALED_LATER key a segment carries),
  the VO, the sign-off, title, caption, the gate inventory, and btc_screen.
  - The integrator's check_pin_only imports THIS package_pin.py from the worktree and recomputes every pin's seal.
  - A SEALED_LATER key enters the body only when a segment carries it, so every earlier pin keeps its digest.
- The render's ruling 17 (pipeline/pinned.adjudicate_lock, main tree, read only here):
  - It decodes the clip itself and compares canon.canon_tokens(run decode) with canon_tokens(approved_text) using
    difflib.SequenceMatcher(autojunk=False). No difference: the lock stands.
  - A difference on a number, name or negation always holds.
  - Otherwise its second recogniser (ElevenLabs scribe_v1) decides. If it reads the approved text at every
    difference, the lock takes the approved text; if it reads the run decode, or neither, the render HOLDS.
- 13:48 ET: the render held pin 61fd55d0 at ruling 17 on clip 3 (mKNAcOFMYD4, run words 32-73), with diffs
  [['in','you'], ["that's why",'']] (run decode first). Its second recogniser read the run decode at both places.
  - The approved text came from the word pass's decode: "...I punch you my code ... And that's why we Bitcoin."
  - The speaker says "punch in my code" and "and that's why, that's why we Bitcoin".

The ruling this diff implements (ORCHESTRATOR 14:02 Nov 13, verbatim):
"67. ATTESTED-TEXT RE-SEAL. When the render's decode and the second recogniser AGREE on a span and the pin's text
differs, the pin is re-sealed with the attested text (L-v: the words as spoken). The verdicts already paid for carry
over, recorded as carried with the exact diff, ONLY when every differing token is a function word or an immediate
repetition of the speaker's own words (here: you -> in; a repeated "that's why"). If any differing token is a number, a
name, a negation or a content word, the clip's step A (both vendors) and the stand-alone verdict are re-judged on the
attested text before the seal. The takeaway, title and caption are re-gated only if they quote the changed words.
Here: both differences are in the carry-over class. Re-seal, verify, send to the integrator at once."

The change:
1. pipeline/attest.py (new; imports canon only, never package.py):
   - diff(): the render's own diff (canon.py here is byte-identical to the render's).
   - critical(): the render's _lv2_critical with its negation and ordinal lists: a number, a negation, or a name
     (capitalised mid-sentence in either text).
   - carry_class(): "immediate repetition" (a delete/insert whose tokens repeat the tokens right before or after them
     on that side), or "function word" (every token in a closed FUNCTION_WORDS list with no negation, number or
     ordinal), else None. A critical token is never carried.
   - reads(): the render's reads() rule, i.e. the second recogniser reads x's tokens at that position (with one
     neighbour each side, consecutive).
   - attested_text(): the minimal edit. It keeps the approved surface words where tokens are equal and uses the run's
     own decoded words at each difference. A difference that splits a word raises; the result's canonical tokens must
     equal the run decode's.
   - quotes(): the lines quoting the changed words (the approved or run tokens of a difference, with one neighbour
     each side).
2. tests/package/reseal_attested.py PIN RUN_DIR BUILD_DIR (new). reseal() refuses (ValueError; exit 2, nothing written)
   unless all of these hold:
   - the pin recomputes to its own seal;
   - the run's PROVENANCE names a pinned file whose seal is the pin's;
   - status.json has exactly one ruling-17 hold whose second recogniser "reads the run decode";
   - exactly one segment is on that video;
   - this side's own second recogniser reading of that clip (live, not replayed, from the build record that sealed
     the pin) reads the run decode at every difference;
   - every difference is in the carry-over class (otherwise: "re-judged first");
   - no line (takeaway/bridges/intro, title, caption) quotes the changed words.
   It then sets that segment's approved_text to the attested text and its "attested" record: the text replaced, the
   exact diffs with their classes, what is carried, the render's run and words and decode, and the second
   recogniser's reading. It re-seals, sets story_id with the new sha8, approved_at, and moments_package.resealed {of,
   old sha, rule, at} (outside the seal), and writes MOMENTS_PIN_ATTESTED.json beside the pin (never over a file).
3. package_pin.SEALED_LATER gains "attested". Earlier pins carry no such key, so they recompute unchanged.
4. tests/package/test_speakers.py: its "every earlier pin still recomputes" test called seal() without btc_screen, so
   the first pin carrying btc_screen (the 13:38 pin, committed at 13:45) failed it. It now passes mp.get("btc_screen"),
   as the integrator's check_pin_only does. Test-only.
5. Tests: test_attest.py (7) runs the held clip's real texts:
   - the render's exact diffs and the classes;
   - the second recogniser reads the run decode, not the approved text;
   - the attested text, with no ruling-17 difference left;
   - negation, number, ordinal, content word, name, and a repeated negation are never carried;
   - a word-splitting difference raises; the quoting check;
   - reseal() end to end on the real held pin with its run records rebuilt in a temp dir (the seal recomputes, the
     "attested" record is sealed, only clip 3 changes);
   - the refusals: neither recogniser, this side reads the pin, a replayed reading, another pin, a content word.
   All 12 suites OK.

Real-data dry run, on a copy of the held pin with the real run dir and build record:
- differences [{run "in", approved "you", "function word"}, {run "that's why", approved "", "immediate repetition"}];
- attested text "My biggest fear is that I go to the bank and I punch in my code and the money's not there because
  the bank owns the money and they could just take it from me. And that's why that's why we Bitcoin.";
- re-sealed; no line quotes the changed words.

Stated readings (say so if you read the ruling differently):
- K1: "the render's decode and the second recogniser AGREE": the render's own hold says so ("the second recogniser
  reads the run decode"), AND this side's own live scribe_v1 reading must read the run decode at every difference.
  Both are required (fail closed).
- K2: "immediate repetition of the speaker's own words": the tokens one side lacks repeat the tokens right before or
  right after them. A critical token (L-v 2) is never carried, even when repeated.
- K3: a difference outside the carry-over class, or a line quoting the changed words, REFUSES here. The re-judge path
  the ruling describes for those is not built (not needed for this pin; fail closed).
- K4: the "attested" record is SEALED (a SEALED_LATER key), so the text's provenance cannot be altered without
  breaking the seal. resealed {of, old sha, at} is outside the seal (bookkeeping).
- K5: the minimal edit uses the run's own words at the differences, so the display text keeps the approved casing
  elsewhere; equal canonical tokens make the render's lock stand with no difference.

Check in particular:
- that no path re-seals a text the render's lock would still hold, or carries over a critical or content-word diff;
- the seal compatibility for every earlier pin and for check_pin_only;
- the refusal paths, and that nothing is written on a refusal;
- the minimal edit's correctness (word boundaries, insert/delete/replace);
- the test_speakers fix.

Answer with P0/P1/P2 findings (file:line, concrete scenario), then "SHIP: yes / no / yes with conditions".


---

## CYCLE 2 INSTRUCTIONS

You've now seen what the other models said. This is your final review.

1. WHAT DID THEY CATCH THAT YOU MISSED?
   Review their findings. Be honest about what you overlooked.

2. WHERE DO YOU AGREE OR DISAGREE?
   For each of their key findings: agree / disagree / partially agree + why.

3. NEW FINDINGS FROM THIS REVIEW
   Anything the combined analysis revealed that nobody caught in Cycle 1?

4. REVISED SCORES
   Update your scores from Cycle 1. Did anything change your assessment?
   | Subsystem | Cycle 1 | Cycle 2 | Why changed |

5. FINAL PRIORITY LIST
   Your definitive list of what must change before this ships.
   P0 CRITICAL | P1 HIGH | P2 MEDIUM — cite file and line numbers.

6. THE SINGLE HIGHEST-LEVERAGE CHANGE
   After seeing everything — one sentence. What matters most?

7. PRODUCTION READY?
   Yes / No / Yes with conditions. State your conditions precisely.
