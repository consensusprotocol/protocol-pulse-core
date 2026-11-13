# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-2240
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 435 s finish=stop usage in 34022 / out 11384 usd~0.273 (upper-bound price)

# Audit: pp-selectid-2240 (C1_STEP.diff, 1313 lines)

Scope note: I verified what the diff shows. Where a finding depends on code outside the diff (e.g. `Router._settle`, `time_sensitive()`, `medley()`), I say so.

---

## P0 findings

**P0-1. No-voice package can ship with a flagged join — the guard checks the *original* medley, not the *final* one when no clip was added.**
`pipeline/package.py` (build loop, diff lines 544–548; `no_voice()` at 400–481).

Scenario: clips total ≥ 45.7 s (so the `content < nv_lo` add-a-clip branch never runs, and `nv_med` stays the *original* `med`), the takeaway fails twice, and `med` has a flagged join. The dispatch condition at diff line 544 (`not med["flagged"]`) does guard this — but only at the moment of dispatch. Inside `no_voice()`, when a clip *is* added, the re-check is `if not ok2 or nv_med["flagged"]` (line 433) — correct. When no clip is added, `nv_med` is the passed-in `med` and the check is skipped entirely; that's fine because dispatch already required `not med["flagged"]`. However, the dispatch condition also requires `not relined` — and `relined` is set when the *last* write's failure triggered a re-line. Trace: `take_failed` increments only in the `if cheap:` branch (line 513) and the fidelity/context branch (line 521). If write 1 fails cheap-gates and write 2 fails fidelity, `take_failed` = 2, but the loop `break`s on package success only; if write 2's failure path sets `relined` (code outside the diff), the no-voice fallback is skipped silently and the angle is dropped despite ruling 3 saying "it is not dropped." I cannot verify `relined`'s assignment sites from this diff — flagging as **needs-confirmation, potentially P0** (ruling 3's "not dropped" guarantee).

**P0-2. `no_voice()` re-runs `exclusion_for`/`truth_for` on the *hook* too, but the added-clip candidate list can include the hook's channel — no, verified: it can't. Withdrawn.** (See P1-3 for the real added-clip issue.)

**P0-3. `_within` leaks the reservation's *reported* cost and can double-settle.**
`pipeline/providers.py` (diff lines 689–712, 740–747).

Scenario: `deadline_s` set, back-end A times out. The handler calls `self._settle(key, b, {"in": 0, "out": 0}, upper, role)` and `continue`s. But A's thread is still running; when it finishes, nothing records its usage — correct per the docstring. However: if the *next* back-end B also times out, B's `_settle` books B's upper bound too, and so on. With a 3-deep chain and 300 s deadlines, worst case books 3× upper bounds as "estimate" spend while reported stays 0 — the budget stop (`est > BUDGET_USD_ESTIMATE`) then fires on phantom spend. Whether `_settle(key, b, usage, upper, role)` actually adds `upper` to the estimate (vs. the reservation already having added it, causing *double-count*) depends on `_reserve`/`_settle`, which are not in the diff. The test at diff lines 1292–1295 asserts `usd_estimate == slow.upper_usd(...)` after one timeout, which proves single-settle works for one abandonment — but proves nothing about the reservation already being counted. **Uncertain; if `_reserve` adds to the ledger optimistically, the test's own assertion would fail, so likely correct — but the abandoned thread's late answer being *dropped* while the ledger says "calls: 1" is a real accounting asymmetry** (a call that actually completed and will be billed by the vendor is booked at upper, never reconciled). P1 in practice.

---

## P1 findings

**P1-1. `utc_z` returns `None` for a naive ISO string, and `recency_problems` correctly rejects it — but `_package` silently seals `None`→refuse, making every moment with a timezone-less `published_at` unpackageable with no earlier diagnostic.**
`pipeline/package.py` (diff lines 258–266), `pipeline/package_pin.py` (diff lines 623–643, 663–669).

Scenario: a moment's `published_at` = `"2026-11-11T18:03:23"` (no offset — the test at line 830 confirms this returns `None`). `_package` seals `source_published_at: None`; `to_pin` then raises `PinRefused` at pin time, *after* all gates and spend. Fail-closed, so law-compliant — but the failure surfaces at the very last step. The test `test_the_package_states_each_clips_recency_from_its_moment` (line 1117) only uses offsets. Whether upstream guarantees an offset is unverifiable from this diff. P1 (late failure, not wrong result).

**P1-2. `house_style.sentence_count` counts a sentence-final token *inside* an abbreviation-lookalike incorrectly, and the last-token rule double-counts.**
`pipeline/house_style.py` (diff lines 91–98).

Scenario: `"u.s. markets fell."` → tokens `["u.s.", "markets", "fell."]`. `_END_RE` matches `"u.s."` (ends with `.`) but `_ABBREV_RE.fullmatch("u.s.")` — pattern `(\w\.)+['\")\]]*` — matches, so it's excluded. Good. But `"e.g. bitcoin. it fell."`: `"e.g."` excluded, `"bitcoin."` counted, `"it fell."` counted → 2. Correct. Now `"v2f. 

## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 76 s finish=stop usage in 33291 / out 527 usd~0.180 (upper-bound price)

**P2: pipeline/house_style.py:154**  
Title possessive detection (after _norm and strip) correctly rejects "Bitcoin’s" / "Holders'" and accepts listed CONTRACTIONS, but the regex [\w-]+'s|[\w-]+s' on the lowercased first token can be bypassed by a title starting with a non-word token + possessive (e.g. "'Bitcoin's value'"). TestTheInterface and TestEveryRuleFails never exercise this; the gate would accept a malformed opener that LAW 20/M2 and R6 require to be refused. (Verified from lint(), _norm(), RULE_IDS, and test fixtures only.)

**P2: pipeline/package.py:456**  
no_voice() calls paid_gates(..., nv_pool) while still inside the ThreadPoolExecutor 'with' block (the subsequent if-not-fid block is at with-body indent). If paid_gates submits additional work to the same pool, the with __exit__ shutdown occurs before all futures are guaranteed collected, violating the "every REQUIRED gate ran, on samples, unwaived, on exactly the bytes" requirement of L-j. The Rig.test_no_voice_* cases never surface the race because they stub paid_gates. (Verified from the exact with/indentation and paid_gates call site only.)

**P2: pipeline/providers.py:708**  
_within() marks the thread daemon=True and abandons it on timeout, then _settle books the *upper* USD. A late-finishing thread that still mutates the shared ledger or cache after the next backend has been chosen (and Reply.tried recorded) can produce a non-deterministic "executed code at the launch revision" attestation, violating L-j's "exact gate inventory v1" and "replays are never deliverable". TestDeadline only checks the immediate reply and ledger entry, not the abandoned thread's final side-effects. (Verified from daemon=True, done.wait, _settle call, and DeadlineExceeded handling only.)

No P0 or P1 findings; all R1/R3/R5/R6 behaviors (recency seal+refusal, no-voice fallback with added-clip path, writer deadline+avoid, house_style lint+inventory+prompt, budget on reported+estimate) match the diff text and tests. The new gate is deterministic, fail-closed, and does not alter existing sentence/edge/fidelity rules.

**SHIP: yes with conditions** (the three P2 edge cases must be exercised or hardened before merge; v2f byte-identity and L-j pin seal remain intact).

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 94 s finish=stop usage in 37826 / out 5149 usd~0.191 (upper-bound price)

# Code Audit: pp-selectid-2240 (C1_STEP.diff)

## P0 Findings

### P0-1: `no_voice` fallback can ship a package with a flagged join (violates R3 / L-y)
**File:** `pipeline/package.py`, `no_voice()` function (approx. lines 400–481 in diff)

**Scenario:**
1. A medley line-up has a join that the blind clips-alone verdict flags (e.g., `med["flagged"] = ["clip_01 -> clip_02"]`).
2. The takeaway fails its gates twice (`take_failed >= NO_VOICE_AFTER`).
3. `no_voice()` is called. It checks `if not ok2 or nv_med["flagged"]:` **only when it adds a clip** (line 433). If the original line-up’s content is already within `nv_lo..nv_hi` (45.7–55.7 s), it skips the clip-addition block entirely.
4. The original `med` (with `flagged` non-empty) is used as `nv_med` (line 409: `nv_med = med`).
5. The code proceeds to `assemble_medley` and `cheap_checks` without ever verifying that the *original* line-up has no flagged joins.
6. `ly_shape()` (line 353–357) checks `if bridges or after or vo.get("intro"):` for no-voice, but does **not** re-check `med["flagged"]` for the no-voice case. The `flagged` check in `ly_shape` is only in the normal VO path.
7. Result: A no-voice package ships with a join a viewer cannot follow, violating R3 (“provided the clips-alone verdict passed” implies no flagged joins) and L-y.

**Fix:** In `no_voice()`, before proceeding, assert `not med["flagged"]` for the original line-up (not just the re-judged one after adding a clip).

---

### P0-2: `house_style` gate is not required for non-medley packages, but `lint_lines` is only called for medleys
**File:** `pipeline/package.py`, `cheap_checks()` (line 366) and `package_pin.py` (line 614)

**Scenario:**
1. `cheap_checks()` only calls `HS.lint_lines(pk["lines"])` when `pk.get("shape") == "medley"` (line 364–366).
2. `package_pin.MEDLEY_GATES` includes `"house_style"` (line 614), so it is required for medley pins.
3. However, if a non-medley package (e.g., a single-clip or R4 package) has lines that violate house style, they are **not** linted and **not** gated.
4. R6 states “HOUSE STYLE on the three text surfaces” without limiting it to medleys. The title and caption are present in all packages.
5. Result: Non-medley packages can ship with titles/captions that violate PBX’s copy rules (e.g., hashtags, em-dashes, hedges), because the gate is never run.

**Fix:** Either run `HS.lint_lines` for all packages in `cheap_checks()`, or clarify that R6 applies only to medleys. If the latter, document it; if the former, add the gate to `REQUIRED_GATES` for all shapes.

---

### P0-3: `utc_z()` returns `None` for naive datetimes, but `recency_problems()` rejects `None`
**File:** `pipeline/package.py`, `utc_z()` (lines 258–266) and `package_pin.py`, `recency_problems()` (lines 626–643)

**Scenario:**
1. A moment’s `published_at` is a naive ISO string (e.g., `"2026-11-12T01:00:00"` with no offset).
2. `utc_z()` returns `None` (line 266: `return None if t.tzinfo is None else ...`).
3. `_package()` sets `source_published_at: None` (line 277).
4. `recency_problems()` checks `isinstance(at, str) and bool(RECENCY_AT.match(at))` (line 635). `None` is not a `str`, so `ok = False`.
5. The pin is refused with `source_published_at must be YYYY-MM-DDTHH:MM:SSZ (got None)`.
6. This is correct fail-closed behavior, **but** the error message is misleading: it says “must be YYYY-MM-DDTHH:MM:SSZ” when the real issue is “missing offset.” More critically, if a moment’s `published_at` is `None` (not a string), `utc_z(None)` returns `None` (line 264: `except (TypeError, ValueError): return None`), and the same rejection occurs.
7. **However**, the test `test_the_package_states_each_clips_recency_from_its_moment` (line 830) asserts `PK.utc_z("2026-11-11T18:03:23")` is `None`, which is correct. The issue is that **all** moments with naive or missing `published_at` will fail to pin, which may be too strict if the source data is known to be naive. But per R1, the pin must carry a UTC time, so this is likely intentional. **No bug here, but worth noting the strictness.**

**Revised:** This is **not** a P0. It is fail-closed as required. Downgrade to P2 (documentation).

---

### P0-4: `no_voice()` does not re-run `ly_shape()` on the final package
**File:** `pipeline/package.py`, `no_voice()` (lines 400–481)

**Scenario:**
1. `no_voice()` calls `assemble_medley()` (line 442) and `cheap_checks()` (line 444).
2. `cheap_checks()` calls `ly_shape(pk)` (line 365) and adds its failures to `v`.
3. If `ly_shape()` fails (e.g., because the no-voice record is missing or malformed), `cheap` is non-empty, and `no_voice()` returns `None` (line 446–448).
4. This is correct. **However**, `ly_shape()` for no-voice checks `if bridges or after or vo.get("intro"):` (line 356). If `vo` is `{"intro": None, "bridges": [], "bridges_after_clip": []}`, this passes. But if `assemble_medley` accidentally sets `vo["in

## CLAUDE'S CYCLE 1 CONSENSUS
# pp-selectid audit of the 22:40 rulings diff (R1 recency in the seal, R3 no-voice, R5 budget / deadline, R6 house style): cycle 1 consensus (synthesis by the pp-selectid session, 23:20 ET Nov 12)

**Run.** C1_STEP.diff is 83,798 bytes; the prompt is 113,741 bytes. Reviewers:
- grok-4.20-0309-reasoning (xAI): SHIP yes with conditions; three P2s, no P0 / P1.
- qwen/qwen3.8-27b (Heimdall, effort none): SHIP no; four P0s, two of them withdrawn by qwen itself.
- z-ai/glm-5.3-flash (Heimdall, effort none): SHIP yes with conditions.

## Consensus

| # | finding (reviewers) | disposition |
|---|---|---|
| K1 | "a no-voice package can ship with a join the clips-alone verdict flagged" (qwen P0-1, glm P0-1) | REFUTED on the code, and hardened anyway. build() calls no_voice() only when `ok_m and not med["flagged"]`. ly_shape compares the bridged joins (none in a no-voice package) with the flagged ones and fails any mismatch. Tests: test_no_voice_never_ships_a_join_the_blind_check_flagged; the flagged must-fail in test_a_no_voice_medley_needs_its_record_and_no_vo_line. Hardened: no_voice() now refuses by itself, at its first line, a clips-alone verdict that is not a measured pass with flagged == [] |

## Unique findings, evaluated

| finding | disposition |
|---|---|
| glm P1-5: take_failed counts one write twice (a cheap failure, then a fidelity failure) | REFUTED: the cheap-failure branch ends in `continue`, so the paid verdict never runs on that write. Each write adds at most once |
| glm condition (b): the budget is only checked when an angle ends, so a package can run past 15 min inside one angle | IMPLEMENTED: over_budget() runs before every line-up and every write, and the end-of-angle check stays. Test: test_the_budget_stops_on_the_reported_cost_or_the_estimate_ceiling (one stop after line-up 1, one before any call or write) |
| glm P0-3: _within double-settles, or leaks the reported cost | REFUTED: _settle pops the reservation and books the upper bound once. TestDeadline asserts one call, the upper bound, and no reservation left. A late answer is dropped unrecorded, never settled again; this asymmetry is on purpose (documented) |
| grok P2: paid_gates runs inside the no-voice pool's `with` and can race its shutdown | REFUTED: paid_gates submits both verdicts and waits for both (`.result()`) before it returns, all inside the `with` |
| grok P2: an abandoned thread mutates the ledger or the cache later | REFUTED: the thread runs only `b.complete()`; settling, recording and serving happen in Router.call, on the caller's side |
| grok P2: a quoted possessive slips past title-possessive | REFUTED by running it: "'Bitcoin's value is real'", the curly-quoted form and "(Bitcoin's) value" all fail title-possessive |
| qwen P0-2: house style is linted only for medleys | KEPT: build() makes only medleys (L-y). The v3 shape remains only for the orchestrator's given packages of Nov 11-12 |
| qwen P0-3 / glm P1-1: utc_z refuses a published time with no offset, bu

---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_2240/C2_STEP.diff (1344 lines)
```
   1 | diff --git a/pipeline/house_style.py b/pipeline/house_style.py
   2 | new file mode 100644
   3 | index 00000000..195a6912
   4 | --- /dev/null
   5 | +++ b/pipeline/house_style.py
   6 | @@ -0,0 +1,183 @@
   7 | +#!/usr/bin/env python3
   8 | +"""pipeline/house_style.py — ORCHESTRATOR RULING 6 (22:40 ET Nov 12): the HOUSE STYLE of the text a viewer reads or
   9 | +hears. That is the TITLE, the CAPTION and the TAKEAWAY (the one VO line); a BRIDGE / INTRO gets the rules shared by every
  10 | +surface.
  11 | +
  12 | +PBX's standing copy rules: lowercase, no hashtags, no em-dashes, no emoji clutter, no AI-sounding phrasing, no hedging.
  13 | +
  14 | +A deterministic lint, no model:
  15 | +- lint(slot, text) -> [violation];
  16 | +- lint_lines(lines) lints a package's lines;
  17 | +- PROMPT_RULES tells the writer the same rules, built from the same constants so the two never drift.
  18 | +
  19 | +Each violation is {"slot", "rule": "STYLE", "detail": "<rule id>: <the offending words>"}, one per rule id.
  20 | +
  21 | +It is a gate on the writer's text BESIDE the VO-fidelity and context gates (L-q / L-t), never instead of them.
  22 | +
  23 | +Decisions the ruling leaves open:
  24 | +- the caption's "short" is CAPTION_MAX_WORDS (24);
  25 | +- a period after a one-letter abbreviation ("u.s.") ends no sentence;
  26 | +- money words match as STEMS on purpose ("investigation" trips invest\\w*);
  27 | +- "May" the month trips the hedge "may";
  28 | +- a title's first-word contraction ("It's", "That's") is not a possessive.
  29 | +"""
  30 | +import re
  31 | +
  32 | +STYLE_SLOTS = ("title", "caption", "takeaway", "bridge", "intro")   # "bridge_1" etc. and "intro" use the bridge rules
  33 | +
  34 | +# every surface
  35 | +HEDGES = ("may", "might", "could be", "perhaps", "possibly", "arguably")
  36 | +AI_PHRASES = ("it's worth noting", "it is worth noting", "delve", "delves", "delving", "tapestry", "testament to",
  37 | +              "in today's world", "ever-evolving", "game-changer", "navigate the")
  38 | +EM_DASHES = ("—", "–", " -- ")                         # em-dash, en-dash, the typed double hyphen
  39 | +EMOJI_RE = re.compile("[\U0001F300-\U0001FAFF\U0001F1E6-\U0001F1FF☀-➿⭐⭕️]")
  40 | +HASHTAG_RE = re.compile(r"#\w")
  41 | +
  42 | +# caption
  43 | +CAPTION_MAX_SENTENCES = 2
  44 | +CAPTION_MAX_WORDS = 24             # the builder's reading of "one or two SHORT sentences"
  45 | +SELF_REFERENCE = ("this medley", "this video", "this clip", "these clips", "builds toward", "this montage")
  46 | +MONEY_PATTERNS = (r"opportunit\w*", r"invest\w*", r"profit\w*", r"get\s+rich", r"to\s+the\s+moon", r"buy\s+the\s+dip",
  47 | +                  r"financial\s+advice")   # stems on purpose: "opportunity"/"invest"-style words in any form
  48 | +
  49 | +# title
  50 | +TITLE_MAX_WORDS = 8
  51 | +CONTRACTIONS = ("it's", "that's", "what's", "here's", "there's", "who's", "let's", "he's", "she's", "where's", "how's",
  52 | +                "why's")          # a first word that ends in 's but is not a possessive
  53 | +
  54 | +# takeaway
  55 | +TAKEAWAY_MAX_WORDS = 20
  56 | +TAKEAWAY_OPENERS = ("what stands out", "it's worth noting", "ultimately", "in the end")
  57 | +WHICH_MAKES_RE = re.compile(r"\bwhich\s+makes\b", re.I)
  58 | +STYLE_REFERENCE = ("No ruler. Just rules nobody gets to bend. That's the idea, and it's the part most people still miss "
  59 | +                   "when they look at Bitcoin.")   # the line PBX appreciated (24 words; the 20-word cap is for new lines)
  60 | +
  61 | +RULE_IDS = ("hashtag", "em-dash", "emoji", "hedge", "ai-phrasing",
  62 | +            "caption-lowercase", "caption-sentences", "caption-words", "self-reference", "money-word",
  63 | +            "title-words", "title-possessive",
  64 | +            "takeaway-words", "takeaway-opener", "which-makes")
  65 | +
  66 | +
  67 | +def _norm(text):
  68 | +    """Curly apostrophes read as straight ones, so "it’s worth noting" is caught as "it's worth noting"."""
  69 | +    return (text or "").replace("’", "'").replace("‘", "'")
  70 | +
  71 | +
  72 | +def _phrase_re(phrase):
  73 | +    """A word-bounded, case-insensitive pattern for a phrase; any run of spaces between its words."""
  74 | +    return re.compile(r"\b" + r"\s+".join(re.escape(w) for w in phrase.split()) + r"\b", re.I)
  75 | +
  76 | +
  77 | +_HEDGE_RES = [(h, _phrase_re(h)) for h in HEDGES]
  78 | +_AI_RES = [(p, _phrase_re(p)) for p in AI_PHRASES]
  79 | +_SELF_RES = [(p, _phrase_re(p)) for p in SELF_REFERENCE]
  80 | +_MONEY_RES = [(p, re.compile(r"\b" + p + r"\b", re.I)) for p in MONEY_PATTERNS]
  81 | +_OPENER_RES = [(o, re.compile(r"^\W*" + r"\s+".join(re.escape(w) for w in o.split()) + r"\b", re.I))
  82 | +               for o in TAKEAWAY_OPENERS]
  83 | +_END_RE = re.compile(r"[.!?]['\")\]]*$")
  84 | +_ABBREV_RE = re.compile(r"(\w\.)+['\")\]]*")
  85 | +
  86 | +
  87 | +def words(text):
  88 | +    return len((text or "").split())
  89 | +
  90 | +
  91 | +def sentence_count(text):
  92 | +    """Sentences = tokens that end a sentence ('.', '!', '?', then closing quotes or brackets), not counting a
  93 | +    one-letter abbreviation ("u.s.", "e.g."); a last sentence without final punctuation still counts."""
  94 | +    toks = (text or "").split()
  95 | +    n = sum(1 for t in toks if _END_RE.search(t) and not _ABBREV_RE.fullmatch(t))
  96 | +    if toks and not _END_RE.search(toks[-1]):
  97 | +        n += 1
  98 | +    return max(n, 1) if toks else 0
  99 | +
 100 | +
 101 | +def _found(res, text):
 102 | +    return [name for name, rx in res if rx.search(text)]
 103 | +
 104 | +
 105 | +def lint(slot, text):
 106 | +    """The house style of one line -> [{"slot", "rule": "STYLE", "detail": "<rule id>: <the offending words>"}], one
 107 | +    violation per broken rule. slot: "title", "caption", "takeaway", "intro" or "bridge*" (the bridge rules)."""
 108 | +    kind = "bridge" if slot == "intro" or slot.startswith("bridge") else slot
 109 | +    if kind not in ("title", "caption", "takeaway", "bridge"):
 110 | +        raise ValueError(f"house_style.lint: unknown slot {slot!r}")
 111 | +    t = _norm(text)
 112 | +    out = []
 113 | +
 114 | +    def v(rule, why):
 115 | +        out.append({"slot": slot, "rule": "STYLE", "detail": f"{rule}: {why}"})
 116 | +
 117 | +    # every surface
 118 | +    tags = re.findall(r"#\w+", t)
 119 | +    if tags:
 120 | +        v("hashtag", ", ".join(repr(x) for x in tags))
 121 | +    dashes = [d for d in EM_DASHES if d in t]
 122 | +    if dashes:
 123 | +        v("em-dash", ", ".join(repr(d.strip() or d) for d in dashes) + " (use a period or a comma)")
 124 | +    emo = EMOJI_RE.findall(t)
 125 | +    if emo:
 126 | +        v("emoji", ", ".join(repr(e) for e in emo))
 127 | +    hedges = _found(_HEDGE_RES, t)
 128 | +    if hedges:
 129 | +        v("hedge", ", ".join(repr(h) for h in hedges) + " (say it plainly or not at all)")
 130 | +    ai = _found(_AI_RES, t)
 131 | +    if ai:
 132 | +        v("ai-phrasing", ", ".join(repr(p) for p in ai))
 133 | +
 134 | +    if kind == "caption":
 135 | +        if t != t.lower():
 136 | +            upper = [w for w in t.split() if w != w.lower()]
 137 | +            v("caption-lowercase", "capitals in " + ", ".join(repr(w) for w in upper[:5]) + " (all lowercase, names too)")
 138 | +        n = sentence_count(t)
 139 | +        if n > CAPTION_MAX_SENTENCES:
 140 | +            v("caption-sentences", f"{n} sentences (at most {CAPTION_MAX_SENTENCES})")
 141 | +        if words(t) > CAPTION_MAX_WORDS:
 142 | +            v("caption-words", f"{words(t)} words (at most {CAPTION_MAX_WORDS})")
 143 | +        selfref = _found(_SELF_RES, t)
 144 | +        if selfref:
 145 | +            v("self-reference", ", ".join(repr(p) for p in selfref) + " (never talk about the video itself)")
 146 | +        money = [m.group(0) for _, rx in _MONEY_RES for m in [rx.search(t)] if m]
 147 | +        if money:
 148 | +            v("money-word", ", ".join(repr(m) for m in money))
 149 | +    elif kind == "title":
 150 | +        if words(t) > TITLE_MAX_WORDS:
 151 | +            v("title-words", f"{words(t)} words (at most {TITLE_MAX_WORDS})")
 152 | +        first = t.split()[0] if t.split() else ""
 153 | +        tok = re.sub(r"^\W+|[^\w']+$", "", first).lower()
 154 | +        if re.fullmatch(r"[\w-]+'s|[\w-]+s'", tok) and tok not in CONTRACTIONS:
 155 | +            v("title-possessive", f"opens with the possessive {first!r} (say the thing: 'The market no government owns')")
 156 | +    elif kind == "takeaway":
 157 | +        if words(t) > TAKEAWAY_MAX_WORDS:
 158 | +            v("takeaway-words", f"{words(t)} words (at most {TAKEAWAY_MAX_WORDS})")
 159 | +        opener = _found(_OPENER_RES, t)
 160 | +        if opener:
 161 | +            v("takeaway-opener", f"opens with {opener[0]!r} (make the point; no throat-clearing)")
 162 | +        if WHICH_MAKES_RE.search(t):
 163 | +            v("which-makes", "a 'which makes ...' clause (end the sentence; say the point in the next one)")
 164 | +    return out
 165 | +
 166 | +
 167 | +def lint_lines(lines):
 168 | +    """The house style of a package's lines ([{"slot", "text", ...}]): every title, caption, takeaway, intro and
 169 | +    bridge* line, each violation under the line's own slot; other slots are not text a viewer gets."""
 170 | +    out = []
 171 | +    for ln in lines or []:
 172 | +        slot = ln.get("slot") or ""
 173 | +        if slot in STYLE_SLOTS or slot.startswith("bridge"):
 174 | +            out += lint(slot, ln.get("text") or "")
 175 | +    return out
 176 | +
 177 | +
 178 | +PROMPT_RULES = (
 179 | +    "HOUSE STYLE (PBX's standing copy rules; a line that breaks one is rejected):\n"
 180 | +    f"- Everywhere: no hashtags; no em-dash or en-dash (use a period or a comma); no emoji; no hedging words "
 181 | +    f"({', '.join(HEDGES)}); no AI-sounding phrasing ({', '.join(AI_PHRASES)}).\n"
 182 | +    f"- CAPTION: all lowercase, names too; one or two short sentences, at most {CAPTION_MAX_WORDS} words in all; never "
 183 | +    f"talk about the video itself ({', '.join(SELF_REFERENCE)}); no money words (opportunity, invest, profit, get "
 184 | +    f"rich, to the moon, buy the dip, financial advice).\n"
 185 | +    f"- TITLE: at most {TITLE_MAX_WORDS} words, plain; never open with a possessive (not \"Bitcoin's overlooked value "
 186 | +    f"comes from ...\" but \"The market no government owns\").\n"
 187 | +    f"- TAKEAWAY: at most {TAKEAWAY_MAX_WORDS} words in short declarative sentences: a point, not a summary; never "
 188 | +    f"open with " + ", ".join(f'"{o}"' for o in TAKEAWAY_OPENERS) + "; no \"which makes ...\" clause.\n"
 189 | +    f"- PBX MAX's voice, for its rhythm, never its words: \"{STYLE_REFERENCE}\"")
 190 | diff --git a/pipeline/package.py b/pipeline/package.py
 191 | index 2ca61824..cf9d0ce3 100644
 192 | --- a/pipeline/package.py
 193 | +++ b/pipeline/package.py
 194 | @@ -54,6 +54,7 @@ from concurrent.futures import ThreadPoolExecutor
 195 |  
 196 |  import context_integrity as CI
 197 |  import eligibility as E
 198 | +import house_style as HS
 199 |  import vo_fidelity as VF
 200 |  
 201 |  SEG_MAX_S = 20.0                   # L-u: at most 20 s per source video
 202 | @@ -68,7 +69,12 @@ SHORT_CLIP_S = 8.0                 # a clip under ~8 s is a penalty unless it is
 203 |  MAX_ANGLES = 3                     # orchestrator 05:30: at most 3 angles x 2 writes
 204 |  WRITES = 2
 205 |  COHERENCE_MIN = 4                  # the blind coherence verdict: every rating >= 4 and a through-line, else next angle
 206 | -BUDGET_S, BUDGET_USD = 360.0, 1.50  # orchestrator 05:25 item 5: per package
 207 | +BUDGET_WALL_S = 900.0              # orchestrator 22:40 ruling 5 (Heimdall as the writer; was 05:25 item 5's 360 s x2):
 208 | +BUDGET_USD_REPORTED = 1.50         # per package 15 min wall and $1.50 by the vendors' OWN reported cost,
 209 | +BUDGET_USD_ESTIMATE = 5.00         # with the price-table estimate (it over-states ~7x) only as a hard ceiling
 210 | +NO_VOICE_AFTER = 2                 # ruling 3 (22:40): the takeaway failing its gates this many times ships no VO line
 211 | +WRITER_DEADLINE_S = 300.0          # ruling 5: one writer call never waits more than 5 min; it fails over (deepseek ->
 212 | +                                   # qwen -> xAI in the writer chain) and the failover is recorded
 213 |  VO_DEPENDENT = ("NOT_ENTAILED", "POLARITY", "STRONGER", "FALSE_RELATION")   # context failures the VO's framing causes
 214 |  VO_FIX = {"NOT_ENTAILED": "the viewer would take this clip to assert more than its speaker said in context: do not "
 215 |                            "frame or restate it",
 216 | @@ -139,7 +145,9 @@ R4_MOMENTS_SHARE = 0.45            # orchestrator 08:29 ruling 9: moments-first
 217 |  
 218 |  
 219 |  LY_CLIPS = (2, 4)                  # L-y 4: 3 to 5 clips = the hook + 2-4 clips, back to back (the medley)
 220 | -LY_TAKEAWAY_MIN_WORDS = 8          # L-y 5: one or two sentences; the cap is ruling 10's MOMENTS_TAKEAWAY_WORD_CAP
 221 | +LY_TAKEAWAY_MIN_WORDS = 8          # L-y 5: one or two sentences
 222 | +LY_TAKEAWAY_MAX_WORDS = HS.TAKEAWAY_MAX_WORDS   # ruling 6 (22:40): at most 20 words for a new takeaway; ruling 10's
 223 | +                                   # MOMENTS_TAKEAWAY_WORD_CAP (30) stays the factory's upper bound in R4
 224 |  LY_BRIDGE_WORDS = 12               # L-y 2: the one exceptional bridge, "as short as it can be" (asked of the writer;
 225 |                                     # config.BRIDGE_WORD_CAP 20 stays the hard bound, ly_shape)
 226 |  LY_BRIDGE_MIN_WORDS = 3            # the shortest bridge a first write budgets for ("Next, on keys.")
 227 | @@ -150,10 +158,10 @@ LY_LINEUPS = 2                     # line-ups tried per angle (a clips-alone fai
 228 |  
 229 |  
 230 |  def medley_content_range(n_bridges=0, bridge_words=LY_BRIDGE_WORDS):
 231 | -    """Seconds the clips may fill so that ONE takeaway of LY_TAKEAWAY_MIN_WORDS..MOMENTS_TAKEAWAY_WORD_CAP words (and
 232 | +    """Seconds the clips may fill so that ONE takeaway of LY_TAKEAWAY_MIN_WORDS..LY_TAKEAWAY_MAX_WORDS words (and
 233 |      n_bridges bridges of bridge_words) lands the factory's estimate (runtime()) inside 60-70 s (L-y 4)."""
 234 |      extra = n_bridges * (bridge_words / R4_WPS + R4_PREROLL_S)
 235 | -    lo = RUNTIME_S[0] - FINAL_TAIL_S - extra - (MOMENTS_TAKEAWAY_WORD_CAP / R4_WPS + R4_PREROLL_S)
 236 | +    lo = RUNTIME_S[0] - FINAL_TAIL_S - extra - (LY_TAKEAWAY_MAX_WORDS / R4_WPS + R4_PREROLL_S)
 237 |      hi = RUNTIME_S[1] - FINAL_TAIL_S - extra - (LY_TAKEAWAY_MIN_WORDS / R4_WPS + R4_PREROLL_S)
 238 |      return round(lo, 2), round(hi, 2)
 239 |  
 240 | @@ -177,11 +185,11 @@ def bridge_budget(content_s):
 241 |  def takeaway_budget(content_s, other=()):
 242 |      """(lo, hi) words for the takeaway, given the clips' seconds and the other VO lines' texts (a bridge): the factory's
 243 |      estimate (runtime()) inside LY_AIM_S when the clips allow it, else inside 60-70 s; never under
 244 | -    LY_TAKEAWAY_MIN_WORDS, above the cap of 30 or past R4's share. None when no length lands 60-70 s."""
 245 | +    LY_TAKEAWAY_MIN_WORDS, above house style's cap (20, ruling 6) or past R4's share. None when no length lands 60-70 s."""
 246 |      other = [t for t in other if t and t.strip()]
 247 |      fixed = content_s + FINAL_TAIL_S + sum(len(t.split()) / R4_WPS + R4_PREROLL_S for t in other)
 248 |      words_at = lambda s: R4_WPS * (s - fixed - R4_PREROLL_S)     # the takeaway's words that land the estimate at s
 249 | -    cap = min(MOMENTS_TAKEAWAY_WORD_CAP,
 250 | +    cap = min(LY_TAKEAWAY_MAX_WORDS,
 251 |                r4_max_vo_words(content_s, 1 + len(other)) - sum(len(t.split()) for t in other))
 252 |      for a, b in (LY_AIM_S, RUNTIME_S):
 253 |          lo, hi = max(LY_TAKEAWAY_MIN_WORDS, math.ceil(words_at(a) - 1e-9)), min(cap, math.floor(words_at(b) + 1e-9))
 254 | @@ -254,6 +262,17 @@ def signoff(segs, ctx):
 255 |      return f"Clips today from {who}. Go follow them for more. Links are below."
 256 |  
 257 |  
 258 | +def utc_z(when):
 259 | +    """An ISO 8601 time with its offset -> "YYYY-MM-DDTHH:MM:SSZ" (UTC), or None when it cannot be read (the pin then
 260 | +    refuses it: ruling 1, 22:40, recency on the render clock needs the source's publish time)."""
 261 | +    from datetime import datetime, timezone
 262 | +    try:
 263 | +        t = datetime.fromisoformat(str(when).replace("Z", "+00:00"))
 264 | +    except (TypeError, ValueError):
 265 | +        return None
 266 | +    return None if t.tzinfo is None else t.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
 267 | +
 268 | +
 269 |  def labels(n):
 270 |      """The segments' labels in play order: the hook, then clip_01 ... (the renderer's clip index = the position)."""
 271 |      return ["hook" if i == 0 else f"clip_{i:02d}" for i in range(n)]
 272 | @@ -268,6 +287,8 @@ def _package(segs, ctx, fields, vo_kind, vo, lines):
 273 |                          "k0": m["sentences"][0], "k1": m["sentences"][1], "words": m["words"],
 274 |                          "start": m["start"], "end": m["end"], "duration_s": m["duration_s"], "text": m["text"],
 275 |                          "published_at": m["published_at"], "transcript_sha256": m["transcript_sha256"],
 276 | +                        "time_sensitive": bool(time_sensitive(m)),          # ruling 1 (22:40): L-v 3 on the render
 277 | +                        "source_published_at": utc_z(m.get("published_at")),  # clock, both sealed in the pin
 278 |                          "url_30s_before": f"https://www.youtube.com/watch?v={m['video_id']}&t={max(0, int(m['start']) - 30)}s"}
 279 |                         for lb, m in zip(labels(len(segs)), segs)],
 280 |            "vo": dict(vo, signoff=signoff(segs, ctx)),
 281 | @@ -301,17 +322,19 @@ def assemble_medley(order, by_id, fields, ctx, vo_kind):
 282 |      (None, 0 = after the hook, or k), title, caption."""
 283 |      segs = [by_id[i] for i in order]
 284 |      n_clips = len(segs) - 1
 285 | -    b, k = fields.get("bridge"), fields.get("bridge_after")
 286 | +    b, k, t = fields.get("bridge"), fields.get("bridge_after"), fields.get("takeaway")
 287 |      if b is not None and (type(k) is not int or not 0 <= k < n_clips):
 288 |          raise ValueError(f"a bridge sits at a join between two clips: after 0..{n_clips - 1}, not {k!r}")
 289 | +    if t is None and b is not None:
 290 | +        raise ValueError("a no-voice medley carries no bridge either (ruling 3, 22:40: clips back to back)")
 291 |      mid = b is not None and k > 0
 292 |      lines = ([dict(b, slot="intro")] if b is not None and k == 0 else []) + \
 293 |          ([dict(b, slot="bridge_1")] if mid else []) + \
 294 | -        [dict(fields["takeaway"], slot="takeaway"), dict(fields["title"], slot="title"),
 295 | -         dict(fields["caption"], slot="caption")]
 296 | +        ([dict(t, slot="takeaway")] if t is not None else []) + \
 297 | +        [dict(fields["title"], slot="title"), dict(fields["caption"], slot="caption")]
 298 |      vo = {"intro": b["text"] if b is not None and k == 0 else None,
 299 | -          "bridges": ([b["text"]] if mid else []) + [fields["takeaway"]["text"]],
 300 | -          "bridges_after_clip": ([k] if mid else []) + [n_clips]}
 301 | +          "bridges": ([b["text"]] if mid else []) + ([t["text"]] if t is not None else []),
 302 | +          "bridges_after_clip": ([k] if mid else []) + ([n_clips] if t is not None else [])}
 303 |      pk = _package(segs, ctx, fields, vo_kind, vo, lines)
 304 |      pk["shape"] = "medley"
 305 |      pk["bridge"] = None if b is None else {"after": pk["segments"][k]["label"], "after_clip": k,
 306 | @@ -319,6 +342,7 @@ def assemble_medley(order, by_id, fields, ctx, vo_kind):
 307 |                                             "text": b["text"], "why": b.get("why"),
 308 |                                             "confirmed_by": fields.get("bridge_confirmed_by")}
 309 |      pk["supply_exception"] = fields.get("supply_exception")
 310 | +    pk["no_voice"] = fields.get("no_voice")
 311 |      return pk
 312 |  
 313 |  
 314 | @@ -437,8 +461,8 @@ in one conversation and never answer each other):
 315 |  
 316 |  After the last clip you speak ONE closing line, the TAKEAWAY; then a sign-off credits every channel (written by code).
 317 |  {bridge}Write:
 318 | -- "takeaway": one or two sentences, {lo}-{hi} words: the point the medley adds up to, as YOUR OWN commentary (your
 319 | -  opinion or conclusion), never a restatement of any clip.
 320 | +- "takeaway": {lo}-{hi} words in short declarative sentences: the point the medley adds up to, as YOUR OWN
 321 | +  commentary (your opinion or conclusion), a point and not a summary, never a restatement of any clip.
 322 |  - "title": ONE title, at most 70 characters; "caption": ONE caption, at most 220 characters. Both carry the angle.
 323 |  Every line gives "cites": the ids of the clips it relies on (none for your own commentary).
 324 |  RULES (a line that breaks one is rejected):
 325 | @@ -452,8 +476,8 @@ RULES (a line that breaks one is rejected):
 326 |  - Never say or imply that channels agree, answer, rebut or react to each other.
 327 |  - No price level; no advice to buy, sell or use leverage; no quotes except a clip's exact words; no "destroys",
 328 |    "slams", "exposes", "admits", "confirms", "caught".
 329 | -- Write the title and caption in sentence case: capitalise only the first word and real names. A line that names a
 330 | -  show, a person or Bitcoin's price cites the clips it comes from.
 331 | +- A line that names a show, a person or Bitcoin's price cites the clips it comes from.
 332 | +{style}
 333 |  {extra}Return ONLY this JSON object: {{"takeaway": {{"text": "...", "cites": []}}, "bridge": {bridge_shape},
 334 |  "title": {{"text": "...", "cites": []}}, "caption": {{"text": "...", "cites": []}}}}"""
 335 |  
 336 | @@ -697,8 +721,8 @@ def write_takeaway(router, angle, segs, ctx, a_by, join=None, extra="", seed=7,
 337 |      angle_text = " ".join(quote_data(angle["angle"], 300).replace('"', "'").split())     # M9: escaped, one line
 338 |      prompt = WRITE_LY.format(angle=angle_text, note=UNTRUSTED.replace("<sentences>", "the quotes"),
 339 |                               lineup=_lineup_block(segs, ctx, a_by), bridge=ask, lo=budget[0], hi=budget[1],
 340 | -                             extra=(extra + "\n") if extra else "", bridge_shape=shape)
 341 | -    r = router.call("angle_write", prompt, 3000, seed, avoid_vendor=avoid_vendor)
 342 | +                             extra=(extra + "\n") if extra else "", bridge_shape=shape, style=HS.PROMPT_RULES)
 343 | +    r = router.call("angle_write", prompt, 3000, seed, avoid_vendor=avoid_vendor, deadline_s=WRITER_DEADLINE_S)
 344 |      try:
 345 |          obj = json.loads(r.text.strip())
 346 |          ids = [m["moment_id"] for m in segs]
 347 | @@ -739,7 +763,13 @@ def ly_shape(pk):
 348 |      if not LY_CLIPS[0] <= n_clips <= LY_CLIPS[1]:
 349 |          fails.append(f"{len(segs)} segments: a medley plays 3-5 (the hook + {LY_CLIPS[0]}-{LY_CLIPS[1]} clips)")
 350 |      bridges, after = list(vo.get("bridges") or []), list(vo.get("bridges_after_clip") or [])
 351 | -    if not bridges or len(after) != len(bridges) or after[-1] != n_clips or not (bridges[-1] or "").strip():
 352 | +    nv = pk.get("no_voice")
 353 | +    if nv is not None:                        # ruling 3 (22:40): clips back to back and the sign-off, NO VO line at all,
 354 | +        if not isinstance(nv, dict) or not str(nv.get("why") or "").strip():   # only after the takeaway failed twice
 355 | +            fails.append("a no-voice medley must record why (ruling 3: the takeaway failed its gates twice)")
 356 | +        if bridges or after or vo.get("intro"):
 357 | +            fails.append("a no-voice medley carries no VO line (ruling 3)")
 358 | +    elif not bridges or len(after) != len(bridges) or after[-1] != n_clips or not (bridges[-1] or "").strip():
 359 |          fails.append("no takeaway after the last clip (L-y 1)")
 360 |      js = joins([sg["label"] for sg in segs])
 361 |      bad = [a for a in after[:-1] if type(a) is not int or not 0 < a < n_clips]
 362 | @@ -805,6 +835,7 @@ def cheap_checks(pk, a_by, levels, now):
 363 |          ([] if r4_res[0] else [{"slot": "-", "rule": "R4", "detail": r4_res[1]}])
 364 |      if pk.get("shape") == "medley":
 365 |          v += [{"slot": "-", "rule": "LY_SHAPE", "detail": why} for why in ly_shape(pk)[1]]
 366 | +        v += HS.lint_lines(pk["lines"])                    # ruling 6 (22:40): PBX's copy rules, deterministic
 367 |      return v, det, dup, rt_ok, r4_res
 368 |  
 369 |  
 370 | @@ -927,7 +958,7 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 371 |      spend: a callable returning the ledger's USD (dollars per package).
 372 |      -> {"package", "packages", "tried", "angles", "takeaways" (every written takeaway with its gates), ...}."""
 373 |      t0 = time.time()
 374 | -    usd0 = spend() if spend else None
 375 | +    usd0 = _spent(spend)
 376 |      ms, why = usable(moments, ctx, delivered, optout)
 377 |      wv, wf = _writers(router)
 378 |      a_by, fails, a_vendors, a_families = prescreen(router, ms, sources, ctx, wv, wf, store=store, log=log)
 379 | @@ -970,7 +1001,8 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 380 |          r = None
 381 |          try:
 382 |              r = router.call("angle_write", ANGLE_PROMPT.format(note=UNTRUSTED.replace("<sentences>", "the quotes"),
 383 | -                                                               clips=clips, k=max_angles, lo=lo, hi=hi), 3000, seed)
 384 | +                                                               clips=clips, k=max_angles, lo=lo, hi=hi), 3000, seed,
 385 | +                            deadline_s=WRITER_DEADLINE_S)
 386 |              angles, angle_reply = check_angles(json.loads(r.text.strip()), cleared, max_angles), r
 387 |              break
 388 |          except Exception as e:
 389 | @@ -981,13 +1013,119 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 390 |          return out
 391 |      out.pop("why_none", None)
 392 |      out["angles"] = [{"angle": a["angle"], "moments": a["moments"], "hook": a["hook"]} for a in angles]
 393 | +    out["angle_backend"], out["angle_tried"] = angle_reply.backend, [list(x) for x in angle_reply.tried]   # ruling 5
 394 |      writers_v, writers_f = {angle_reply.vendor}, {angle_reply.family}
 395 | +    writer_avoid = {router.backends[n].vendor for n in router.chain("angle_write") if n in router.backends} - \
 396 | +        {angle_reply.vendor}                   # every write stays on the angle's vendor, so a judge is always left
 397 |      log(f"  {len(angles)} angles from {angle_reply.backend} ({time.time() - t0:.0f} s)")
 398 |      doomed = set()                                         # moments a per-moment gate dropped: out of every angle
 399 | +
 400 | +    def over_budget(ai):
 401 | +        """Ruling 5 (22:40): per package 15 min wall / $1.50 reported / the $5 estimate ceiling. Checked before every
 402 | +        line-up and every write (audit 2240 C1, glm), not only when an angle ends. -> the stop record, or None."""
 403 | +        used_s = time.time() - t0
 404 | +        est, rep = (a - b for a, b in zip(_spent(spend), usd0))
 405 | +        if used_s <= BUDGET_WALL_S and rep <= BUDGET_USD_REPORTED and est <= BUDGET_USD_ESTIMATE:
 406 | +            return None
 407 | +        out["why_none"] = (f"stopped in angle {ai + 1} of {len(angles)}: {used_s:.0f} s of {BUDGET_WALL_S:.0f} s wall / "
 408 | +                           f"${rep:.2f} of ${BUDGET_USD_REPORTED:.2f} reported / ${est:.2f} of the "
 409 | +                           f"${BUDGET_USD_ESTIMATE:.2f} estimate ceiling (ruling 5, 22:40)")
 410 | +        out["budget_stop"] = {"seconds": round(used_s, 1), "usd_reported": round(rep, 4), "usd_estimate": round(est, 4),
 411 | +                              "angles_tried": ai + 1, "angles": len(angles)}
 412 | +        return out["budget_stop"]
 413 | +
 414 | +    def no_voice(angle, segs, med, last, exception, dropped, rec, ai, n_lineup):
 415 | +        """Ruling 3 (22:40): the takeaway failed its gates twice on a line-up whose clips ALONE passed with no join a
 416 | +        viewer cannot follow, so the package ships with NO VO line: clips back to back and the sign-off. It is not
 417 | +        dropped. The title and caption are the latest write's and go through every gate again. The factory's estimate
 418 | +        must still land 60-70 s, so when the clips are too short one more clip of the angle is added in the proposer's
 419 | +        order, and the new line-up is judged on the clips alone again. -> a package, or None (rec["no_voice"] why)."""
 420 | +        nv_lo, nv_hi = RUNTIME_S[0] - FINAL_TAIL_S, RUNTIME_S[1] - FINAL_TAIL_S
 421 | +        pos = {m_: i for i, m_ in enumerate(angle["moments"])}
 422 | +        rec["no_voice"] = note = {"tried": True}
 423 | +        if med.get("measured") is not True or med.get("flagged") != []:     # audit 2240 C1 (qwen, glm): its own guard
 424 | +            note["why_not"] = "the clips-alone verdict is not a measured pass with every join followable"
 425 | +            return None
 426 | +        order, added, nv_med = list(segs), None, med
 427 | +        content = sum(m["duration_s"] for m in order)
 428 | +        if content > nv_hi:
 429 | +            note["why_not"] = f"{content:.1f} s of clips: over {nv_hi:.1f} s with no VO line"
 430 | +            return None
 431 | +        if content < nv_lo:                                  # "the packager may add a clip"
 432 | +            chans = {m["channel_id"] for m in segs}
 433 | +            for mid in angle["moments"]:
 434 | +                m = cleared.get(mid)
 435 | +                if m is None or m in segs or mid in dropped or mid in doomed or m["channel_id"] in chans or \
 436 | +                        not (m.get("eligibility") or {}).get("clip", {}).get("ok"):
 437 | +                    continue
 438 | +                cand = [segs[0]] + sorted(segs[1:] + [m], key=lambda x: pos.get(x["moment_id"], 99))
 439 | +                if len(cand) - 1 > LY_CLIPS[1] or [x for x in cand[1:-1] if x["duration_s"] < SHORT_CLIP_S] or \
 440 | +                        sum("price_prediction" in x.get("risk", []) for x in cand) > PRICE_PREDICTIONS_MAX or \
 441 | +                        not nv_lo <= sum(x["duration_s"] for x in cand) <= nv_hi:
 442 | +                    continue
 443 | +                order, added = cand, mid
 444 | +                break
 445 | +            if added is None:
 446 | +                note["why_not"] = f"{content:.1f} s of clips and no one clip of the angle lands {nv_lo:.1f}-{nv_hi:.1f} s"
 447 | +                return None
 448 | +            ok2, nv_med = medley(router, order, ctx, writers_v, seed=50 + n_lineup + 10 * ai, writer_family=writers_f)
 449 | +            note["medley"] = nv_med
 450 | +            if not ok2 or nv_med["flagged"]:
 451 | +                note["why_not"] = "the line-up with the added clip fails on the clips alone (or has a join to bridge)"
 452 | +                return None
 453 | +        fields = {"takeaway": None, "bridge": None, "bridge_after": None, "title": last["title"],
 454 | +                  "caption": last["caption"], "type": "moments", "angle": angle["angle"], "style": "medley, no voice",
 455 | +                  "supply_exception": exception,
 456 | +                  "no_voice": {"why": "the takeaway failed its gates in both writes; ruling 3 (22:40) ships the clips "
 457 | +                                      "back to back with the sign-off only", "added_clip": added,
 458 | +                               "lineup_before": [m["moment_id"] for m in segs]}}
 459 | +        pk = assemble_medley([m["moment_id"] for m in order], cleared, fields, ctx, "medley (L-y), no voice")
 460 | +        pk["medley"] = nv_med
 461 | +        cheap, det, dup, rt_ok, r4_res = cheap_checks(pk, a_by, levels, ctx.now)
 462 | +        if cheap:
 463 | +            note["why_not"] = f"cheap gates: {sorted({v['rule'] for v in cheap})}"
 464 | +            note["violations"] = cheap
 465 | +            return None
 466 | +        with ThreadPoolExecutor(max_workers=8) as nv_pool:
 467 | +            bg2 = {m["moment_id"]: (nv_pool.submit(exclusion_for, router, m, sources, exc),
 468 | +                                    nv_pool.submit(truth_for, router, m, work_dir, tru)) for m in order}
 469 | +            got = {mid: (f[0].result(), f[1].result()) for mid, f in bg2.items()}
 470 | +            if any(e.get("verdict") != "keep" or not t.get("ok") or (t.get("edges") or {}).get("cuttable") is not True
 471 | +                   for e, t in got.values()):
 472 | +                note["why_not"] = "a clip fails exclusion, the second pass or CUTTABLE"
 473 | +                return None
 474 | +            fid, cx = paid_gates(router, pk, sources, a_by, levels, ctx.now, writers_v, writers_f, nv_pool)
 475 | +        if not fid["ok"] or not cx["ok"]:
 476 | +            note["why_not"] = "the title / caption fail VO fidelity or context integrity"
 477 | +            note["violations"] = fid["violations"] + cx["violations"]
 478 | +            return None
 479 | +        coh = dict(nv_med, vo_point=None, note="no VO line: the clips-alone verdict is the coherence verdict (ruling 3)")
 480 | +        a_lab = {sg["label"]: a_by[sg["moment_id"]] for sg in pk["segments"]}
 481 | +        pk["gates"] = inventory(fid, dup, rt_ok, r4_res, cx, a_lab, {k: v for k, (v, _) in got.items()},
 482 | +                                {k: v for k, (_, v) in got.items()}, True, coh, medley=(True, nv_med),
 483 | +                                shape=ly_shape(pk), style=HS.lint_lines(pk["lines"]))
 484 | +        import package_pin
 485 | +        problems = package_pin.gate_problems(pk["gates"], package_pin.required_gates(pk))
 486 | +        if problems:
 487 | +            note["why_not"] = f"a required gate is not exactly PASS: {problems}"
 488 | +            return None
 489 | +        pk["models"] = {"angle": angle_reply.backend, "writer": "the latest write's title and caption",
 490 | +                        "medley": nv_med.get("backend"), "fidelity_verdict": fid.get("backend"),
 491 | +                        "context": cx.get("backends"), "coherence": nv_med.get("backend")}
 492 | +        pk["checks"] = {"fidelity": fid, "context": cx, "coherence": coh, "medley": nv_med}
 493 | +        pk["seconds"] = round(time.time() - t0, 1)
 494 | +        pk["usd"] = round(_spent(spend)[0] - usd0[0], 4) if spend else None
 495 | +        note["result"] = "PACKAGE"
 496 | +        log(f"  angle {ai + 1} line-up {n_lineup}: NO-VOICE package ({len(order)} clips, "
 497 | +            f"{sum(m['duration_s'] for m in order):.1f} s, added {added}) ({time.time() - t0:.0f} s)")
 498 | +        return pk
 499 | +
 500 |      with ThreadPoolExecutor(max_workers=8) as pool:
 501 |          for ai, angle in enumerate(angles):
 502 |              dropped, n_lineup = set(), 0
 503 | -            while n_lineup < lineups and not out["packages"]:
 504 | +            while n_lineup < lineups and not out["packages"] and not out.get("budget_stop"):
 505 | +                if over_budget(ai):
 506 | +                    break
 507 |                  segs, exception = lineup_for(angle, cleared, frozenset(dropped | doomed)), None
 508 |                  if segs is None:                          # L-y 4: one clip per channel unless the supply forces otherwise
 509 |                      segs = lineup_for(angle, cleared, frozenset(dropped | doomed), repeat_ok=True)
 510 | @@ -1029,11 +1167,15 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 511 |                  bg = {m["moment_id"]: (pool.submit(exclusion_for, router, m, sources, exc),
 512 |                                         pool.submit(truth_for, router, m, work_dir, tru)) for m in segs}
 513 |                  extra, relined, w_used, written = "", False, 0, ()
 514 | +                take_failed, last_fields = 0, None         # ruling 3 (22:40): the no-voice fallback reads these
 515 |                  while w_used < writes:
 516 | +                    if over_budget(ai):
 517 | +                        break
 518 |                      w_used += 1
 519 |                      try:
 520 |                          wr, fields = write_takeaway(router, angle, segs, ctx, a_by, join, extra,
 521 | -                                                    seed=7 + w_used + 10 * ai + 100 * n_lineup, other=written)
 522 | +                                                    seed=7 + w_used + 10 * ai + 100 * n_lineup,
 523 | +                                                    avoid_vendor=writer_avoid or None, other=written)
 524 |                      except NoBridgeFits as e:                  # the seconds rule it out: re-line, no write is paid
 525 |                          if join is not None:
 526 |                              dropped.add(segs[join[0] + 1]["moment_id"])
 527 | @@ -1077,6 +1219,7 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 528 |                      rec["attempts"].append(att)
 529 |                      take = _takeaway_record(ai, n_lineup, w_used, pk, cheap)
 530 |                      out["takeaways"].append(take)
 531 | +                    last_fields = fields
 532 |                      log(f"  angle {ai + 1} line-up {n_lineup} write {w_used} ({wr.backend}, takeaway {take['words']} "
 533 |                          f"words, {pk['runtime_s_estimate']} s): " +
 534 |                          ("cheap gates fail " + ", ".join(sorted({v["rule"] for v in cheap})) if cheap else "cheap PASS")
 535 | @@ -1097,6 +1240,7 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 536 |                          break
 537 |                      if cheap:
 538 |                          att["violations"] = cheap
 539 | +                        take_failed += take["passed"] is False
 540 |                          b = takeaway_budget(sum(m["duration_s"] for m in segs), written)
 541 |                          extra = _redo([dict(v, detail=v["detail"] + (f" (a takeaway of {b[0]}-{b[1]} words lands it)"
 542 |                                                                       if b else " (no takeaway length lands it with this "
 543 | @@ -1112,6 +1256,7 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 544 |                      log(f"    fidelity {'PASS' if fid['ok'] else 'FAIL'} (takeaway "
 545 |                          f"{'PASS' if take['passed'] else take['verdict_fail']}), context "
 546 |                          f"{'PASS' if cx['ok'] else 'FAIL'} ({time.time() - t0:.0f} s)")
 547 | +                    take_failed += take["passed"] is False
 548 |                      if not fid["ok"] or not cx["ok"]:
 549 |                          if fid["ok"] and not framing:
 550 |                              rec["why"] = "context integrity failed on something the VO cannot fix"
 551 | @@ -1130,12 +1275,14 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 552 |                      a_lab = {sg["label"]: a_by[sg["moment_id"]] for sg in pk["segments"]}
 553 |                      pk["gates"] = inventory(fid, dup, rt_ok, r4_res, cx, a_lab,
 554 |                                              {k: v for k, (v, _) in got.items()}, {k: v for k, (_, v) in got.items()},
 555 | -                                            ok_c, coh, medley=(ok_m, med), shape=ly_shape(pk))
 556 | +                                            ok_c, coh, medley=(ok_m, med), shape=ly_shape(pk),
 557 | +                                            style=HS.lint_lines(pk["lines"]))
 558 |                      if not ok_c:
 559 |                          tl = coh.get("through_line") if isinstance(coh.get("through_line"), str) else ""
 560 |                          if coh.get("measured") and type(coh.get("vo_point")) is int and \
 561 |                                  coh["vo_point"] < COHERENCE_MIN and min(coh["clips"].values()) >= COHERENCE_MIN and \
 562 |                                  len(tl.split()) >= 4 and not NO_LINE.search(tl):
 563 | +                            take_failed += 1                  # the takeaway's point failed its coherence gate
 564 |                              extra = _redo([{"slot": "takeaway", "rule": "COHERENCE", "detail":
 565 |                                              f"a blind viewer rated the takeaway's point {coh['vo_point']} of 5 for "
 566 |                                              f"being supported by the clips: land the point the clips make together"}])
 567 | @@ -1158,29 +1305,36 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 568 |                                      "coherence": coh.get("backend")}
 569 |                      pk["checks"] = {"fidelity": fid, "context": cx, "coherence": coh, "medley": med}
 570 |                      pk["seconds"] = round(time.time() - t0, 1)
 571 | -                    pk["usd"] = round(spend() - usd0, 4) if spend else None
 572 | +                    pk["usd"] = round(_spent(spend)[0] - usd0[0], 4) if spend else None
 573 |                      out["packages"].append(pk)
 574 |                      rec["result"] = "PACKAGE"
 575 |                      break
 576 | +                if not out["packages"] and not relined and ok_m and not med["flagged"] and \
 577 | +                        take_failed >= NO_VOICE_AFTER and last_fields is not None and not out.get("budget_stop"):
 578 | +                    nv = no_voice(angle, segs, med, last_fields, exception, dropped, rec, ai, n_lineup)
 579 | +                    if nv is not None:
 580 | +                        out["packages"].append(nv)
 581 | +                        rec["result"] = "PACKAGE (no voice, ruling 3)"
 582 |                  if out["packages"] or not relined:
 583 |                      break
 584 | -            if out["packages"]:
 585 | -                break
 586 | -            used_s, used_usd = time.time() - t0, (spend() - usd0) if spend else 0.0
 587 | -            if used_s > BUDGET_S * 2 or used_usd > BUDGET_USD * 2:
 588 | -                out["why_none"] = (f"stopped after angle {ai + 1} of {len(angles)}: {used_s:.0f} s of the "
 589 | -                                   f"{BUDGET_S * 2:.0f} s / ${used_usd:.2f} of the ${BUDGET_USD * 2:.2f} (estimate) "
 590 | -                                   f"per-package budget (05:25 item 5, twice)")
 591 | -                out["budget_stop"] = {"seconds": round(used_s, 1), "usd_estimate": round(used_usd, 4),
 592 | -                                      "angles_tried": ai + 1, "angles": len(angles)}
 593 | +            if out["packages"] or out.get("budget_stop") or over_budget(ai):
 594 |                  break
 595 |      out["package"] = out["packages"][0] if out["packages"] else None
 596 |      out["seconds"] = round(time.time() - t0, 1)
 597 | -    out["usd"] = round(spend() - usd0, 4) if spend else None
 598 | +    out["usd"] = round(_spent(spend)[0] - usd0[0], 4) if spend else None
 599 |      return out
 600 |  
 601 |  
 602 | -def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medley=None, shape=None):
 603 | +def _spent(spend):
 604 | +    """(estimate, vendor-reported) from the caller's meter. A bare number is the estimate alone; its reported figure
 605 | +    is then taken to be the same (the conservative reading). No meter: (0, 0)."""
 606 | +    if not spend:
 607 | +        return 0.0, 0.0
 608 | +    v = spend()
 609 | +    return (float(v[0]), float(v[1])) if isinstance(v, (tuple, list)) else (float(v), float(v))
 610 | +
 611 | +
 612 | +def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medley=None, shape=None, style=None):
 613 |      """The sealed GATE INVENTORY (audit p2 C1; package_pin.required_gates): one row per hard gate, each
 614 |      {"status": "PASS" | "FAIL" | "NOT RUN", "by", "replayed", "n"}. Nothing measured is never a PASS (law L-m).
 615 |      A medley (L-y) adds two rows: "medley" (the blind clips-alone verdict, medley=(ok, verdict)) and "ly_shape"
 616 | @@ -1237,4 +1391,7 @@ def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medl
 617 |             if medley is not None else {}),
 618 |          **({"ly_shape": dict(row(bool(shape[0]), "code (package.ly_shape, L-y)"), why=list(shape[1]))}
 619 |             if shape is not None else {}),
 620 | +        **({"house_style": dict(row(not style, "code (house_style.lint_lines, ruling 6)"),
 621 | +                                why=[f"{v['slot']}: {v['detail']}" for v in style])}
 622 | +           if style is not None else {}),
 623 |      }
 624 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
 625 | index b1da529b..c079de8f 100644
 626 | --- a/pipeline/package_pin.py
 627 | +++ b/pipeline/package_pin.py
 628 | @@ -20,12 +20,14 @@ gates -> release authorisation) renders a moments-first package.
 629 |  import hashlib
 630 |  import json
 631 |  import os
 632 | +import re
 633 |  from datetime import datetime, timezone
 634 |  
 635 |  SCHEMA = "protocol_pulse.pinned_story.v1"
 636 |  REQUIRED_GATES = ("vo_fidelity_deterministic", "vo_fidelity_verdict", "duplicate", "price_now", "runtime", "r4",
 637 |                    "context_a", "context_b", "context_c", "exclusion", "second_pass", "cuttable", "coherence")
 638 | -MEDLEY_GATES = ("medley", "ly_shape")      # L-y (orchestrator 20:30): the clips-alone verdict and the medley's shape
 639 | +MEDLEY_GATES = ("medley", "ly_shape", "house_style")   # L-y (20:30): the clips-alone verdict, the medley's shape;
 640 | +                                                         # ruling 6 (22:40): PBX's copy rules on every line
 641 |  
 642 |  
 643 |  def required_gates(pk):
 644 | @@ -38,13 +40,40 @@ class PinRefused(Exception):
 645 |      """The package may not become a pinned decision."""
 646 |  
 647 |  
 648 | +RECENCY_AT = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
 649 | +
 650 | +
 651 | +def recency_problems(segments):
 652 | +    """[why] for segments that do not state the recency facts the render clock checks (ruling 1, 22:40): every segment
 653 | +    a bool "time_sensitive" and "source_published_at" as "YYYY-MM-DDTHH:MM:SSZ" (UTC) that parses."""
 654 | +    from datetime import datetime
 655 | +    out = []
 656 | +    for i, s in enumerate(segments):
 657 | +        if type(s.get("time_sensitive")) is not bool:
 658 | +            out.append(f"segment {i}: time_sensitive must be true or false (got {s.get('time_sensitive')!r})")
 659 | +        at = s.get("source_published_at")
 660 | +        ok = isinstance(at, str) and bool(RECENCY_AT.match(at))
 661 | +        if ok:
 662 | +            try:
 663 | +                datetime.strptime(at, "%Y-%m-%dT%H:%M:%SZ")
 664 | +            except ValueError:
 665 | +                ok = False
 666 | +        if not ok:
 667 | +            out.append(f"segment {i}: source_published_at must be YYYY-MM-DDTHH:MM:SSZ (got {at!r})")
 668 | +    return out
 669 | +
 670 | +
 671 |  def seal(segments, edl_vo, signoff, title, caption, gates):
 672 |      """sha256 over the gated bytes, in a canonical form both sides compute: the segments (video, start, end, the exact
 673 | -    words, the transcript sha), the VO the renderer will speak (intro, bridges with after_clip), the sign-off, the ONE
 674 | -    title and caption (law L-t), and the gate inventory."""
 675 | +    words, the transcript sha, and since ruling 1 (22:40) time_sensitive and source_published_at), the VO the renderer
 676 | +    will speak (intro, bridges with after_clip), the sign-off, the ONE title and caption (law L-t), and the gate
 677 | +    inventory."""
 678 |      body = {"segments": [{"video_id": s["video_id"], "start": round(float(s["start"]), 3),
 679 |                            "end": round(float(s["end"]), 3), "text": s["approved_text"],
 680 | -                          "transcript_sha256": s.get("transcript_sha256")} for s in segments],
 681 | +                          "transcript_sha256": s.get("transcript_sha256"),
 682 | +                          "time_sensitive": s.get("time_sensitive"),             # ruling 1 (22:40): the render clock
 683 | +                          "source_published_at": s.get("source_published_at")}   # checks L-v 3 on these
 684 | +                         for s in segments],
 685 |              "vo": {"intro": edl_vo.get("intro"), "bridges": [{"text": b["text"], "after_clip": b["after_clip"]}
 686 |                                                               for b in edl_vo.get("bridges") or []]},
 687 |              "signoff": signoff, "title": title, "caption": caption, "gates": gates}
 688 | @@ -96,7 +125,8 @@ def line_problems(pk):
 689 |  
 690 |  def to_pin(pk, run_name):
 691 |      problems = gate_problems(pk.get("gates"), required_gates(pk)) + [f"{x}: the gated line differs from the one shipped"
 692 | -                                                                     for x in line_problems(pk)]
 693 | +                                                                     for x in line_problems(pk)] + \
 694 | +        recency_problems(pk.get("segments") or [])
 695 |      if problems:
 696 |          raise PinRefused("the package's gates do not authorise a pin: " + "; ".join(problems))
 697 |      segs = []
 698 | @@ -104,6 +134,7 @@ def to_pin(pk, run_name):
 699 |          segs.append({"role": "hook" if i == 0 else "clip", "video_id": s["video_id"], "channel": s["channel"],
 700 |                       "start": round(float(s["start"]), 3), "end": round(float(s["end"]), 3),
 701 |                       "approved_text": s["text"], "transcript_sha256": s.get("transcript_sha256"),
 702 | +                     "time_sensitive": s.get("time_sensitive"), "source_published_at": s.get("source_published_at"),
 703 |                       "time_coords": "youtube", "source": {"kind": "youtube"}})
 704 |      edl_vo = {"intro": pk["vo"]["intro"],
 705 |                "bridges": [{"text": t, "after_clip": a} for t, a in zip(pk["vo"]["bridges"], pk["vo"]["bridges_after_clip"])]}
 706 | diff --git a/pipeline/providers.py b/pipeline/providers.py
 707 | index 6e8220ca..e65bca1c 100644
 708 | --- a/pipeline/providers.py
 709 | +++ b/pipeline/providers.py
 710 | @@ -221,6 +221,32 @@ class OpenAIBackend(Backend):
 711 |          return text, {"in": int(u.get("prompt_tokens") or 0), "out": int(u.get("completion_tokens") or 0)}, time.time() - t0
 712 |  
 713 |  
 714 | +class DeadlineExceeded(Exception):
 715 | +    """A back-end gave no answer within the caller's deadline (orchestrator 22:40 ruling 5: one writer call never waits
 716 | +    more than 5 min). The call is abandoned, not killed: Python cannot stop the thread."""
 717 | +
 718 | +
 719 | +def _within(seconds, fn):
 720 | +    """fn() in a daemon thread, waited for at most `seconds`. -> its value, or its own exception re-raised, or
 721 | +    DeadlineExceeded. An abandoned thread finishes (or times out) on its own; its result is dropped unrecorded."""
 722 | +    import threading
 723 | +    box, done = {}, threading.Event()
 724 | +
 725 | +    def run():
 726 | +        try:
 727 | +            box["value"] = fn()
 728 | +        except BaseException as e:            # handed back to the caller below
 729 | +            box["error"] = e
 730 | +        finally:
 731 | +            done.set()
 732 | +    threading.Thread(target=run, daemon=True, name="pp-deadline").start()
 733 | +    if not done.wait(seconds):
 734 | +        raise DeadlineExceeded(f"no answer within {seconds:.0f} s")
 735 | +    if "error" in box:
 736 | +        raise box["error"]
 737 | +    return box["value"]
 738 | +
 739 | +
 740 |  def _num(x):
 741 |      import math
 742 |      return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) and x >= 0
 743 | @@ -642,7 +668,7 @@ class Router:
 744 |          os.replace(tmp, path)
 745 |  
 746 |      def call(self, role, prompt, max_tokens=2000, seed=7, system=None, avoid_vendor=None, avoid_model=None,
 747 | -             avoid_family=None):
 748 | +             avoid_family=None, deadline_s=None):
 749 |          av, am, af = _as_set(avoid_vendor), _as_set(avoid_model), _as_set(avoid_family)
 750 |          tried, notices = [], []
 751 |          for name in self.chain(role):
 752 | @@ -662,13 +688,21 @@ class Router:
 753 |              if self.replay:
 754 |                  tried.append((name, "replay: not recorded"))
 755 |                  continue
 756 | -            key = self._reserve(b, b.upper_usd(prompt, max_tokens, system))
 757 | +            upper = b.upper_usd(prompt, max_tokens, system)
 758 | +            key = self._reserve(b, upper)
 759 |              if b.vendor == "heimdall":
 760 |                  n = self.heimdall_tripwire()
 761 |                  if n:
 762 |                      notices.append(n)
 763 |              try:
 764 | -                text, usage, secs = b.complete(prompt, max_tokens, seed, system)
 765 | +                if deadline_s:                         # ruling 5 (22:40): fail over instead of waiting
 766 | +                    text, usage, secs = _within(deadline_s, lambda: b.complete(prompt, max_tokens, seed, system))
 767 | +                else:
 768 | +                    text, usage, secs = b.complete(prompt, max_tokens, seed, system)
 769 | +            except DeadlineExceeded as e:              # abandoned; the vendor may still bill it, so its UPPER bound is
 770 | +                self._settle(key, b, {"in": 0, "out": 0}, upper, role)     # booked as spent (estimate, unreported)
 771 | +                tried.append((name, f"{e} (abandoned at the deadline; its upper bound ${upper:.2f} booked as spent)"))
 772 | +                continue
 773 |              except RequestRejected as e:
 774 |                  self._settle(key)
 775 |                  tried.append((name, f"refused this request: {e}"))
 776 | diff --git a/tests/package/proof_ly.py b/tests/package/proof_ly.py
 777 | index 23286dd1..40779901 100644
 778 | --- a/tests/package/proof_ly.py
 779 | +++ b/tests/package/proof_ly.py
 780 | @@ -55,7 +55,9 @@ RUNS = ("fresh_20261112_050611", "fresh_20261112_013452", "fresh_20261112_001448
 781 |          "fresh_20261107_065702", "fresh_20261106_213852")           # newest first: the first is tonight's
 782 |  NEWEST = RUNS[0]
 783 |  FROZEN = ("local:", "anthropic:", "openai:", "openai_stt:")         # GPU0 (never this builder's); out of credit 20:32
 784 | -WRITERS = ["heimdall:deepseek/deepseek-v4.1-flash", "heimdall:qwen/qwen3.8-27b"]
 785 | +WRITERS = ["heimdall:deepseek/deepseek-v4.1-flash", "heimdall:qwen/qwen3.8-27b",      # ruling 5 (22:40): a writer
 786 | +           "xai:grok-4.20-0309-reasoning"]       # call over 5 min fails over deepseek -> qwen -> xAI; the writes then
 787 | +                                                 # stay on the angle's vendor and every verdict avoids it (L-x)
 788 |  SCRATCH = "/tmp/claude-1000/-home-ultron-worktrees-pp-selectid/9e163ea0-e85c-404b-9baf-67af8f2ebf8b/scratchpad"
 789 |  
 790 |  
 791 | @@ -145,7 +147,8 @@ def run_one(run, router, work_dir, log, own, used=None, as_of_now=False):
 792 |      u0 = dict(used) if used is not None else None
 793 |      t0 = time.time()
 794 |      res = PK.build(router, rec_m["moments"], sources, ctx, delivered=(), optout=M.optout_ids(), log=log,
 795 | -                   work_dir=work_dir, store=os.path.join(OUT, run, f"step_a{suffix}.json"), spend=lambda: own["est"])
 796 | +                   work_dir=work_dir, store=os.path.join(OUT, run, f"step_a{suffix}.json"),
 797 | +                   spend=lambda: (own["est"], own["best"]))       # ruling 5: the budget reads the reported cost
 798 |      e1, b1 = own["est"], own["best"]
 799 |      res.update(run=run, seconds=round(time.time() - t0, 1), usd_estimate=round(e1 - e0, 4),
 800 |                 usd_best_known=round(b1 - b0, 4), code=code_sha(), chains=router.chains,
 801 | diff --git a/tests/package/test_angles.py b/tests/package/test_angles.py
 802 | index 61cb0ed8..34762dcd 100644
 803 | --- a/tests/package/test_angles.py
 804 | +++ b/tests/package/test_angles.py
 805 | @@ -55,7 +55,7 @@ class TestAngles(unittest.TestCase):
 806 |          seg = PK.lineup_for(angle(["a", "d", "b", "c"], "a"), by)
 807 |          self.assertIsNotNone(seg)
 808 |          self.assertNotIn("d", [m["moment_id"] for m in seg[1:-1]])                # 6 s: never in the middle
 809 | -        by2 = {m["moment_id"]: m for m in (pm("a", "A", 12.0), pm("b", "B", 16.0), pm("d", "D", 6.0))}
 810 | +        by2 = {m["moment_id"]: m for m in (pm("a", "A", 12.0), pm("b", "B", 19.0), pm("d", "D", 6.0))}
 811 |          seg2 = PK.lineup_for(angle(["a", "b", "d"], "a"), by2)
 812 |          self.assertEqual([m["moment_id"] for m in seg2], ["a", "b", "d"])         # allowed as the last (the punchline)
 813 |  
 814 | @@ -128,7 +128,8 @@ class TestPinAndTruth(unittest.TestCase):
 815 |                  "lines": [{"slot": "intro", "text": "I"}, {"slot": "bridge_1", "text": "B"},
 816 |                            {"slot": "title", "text": "T"}, {"slot": "caption", "text": "C"}],
 817 |                  "segments": [{"video_id": v, "channel": "ch", "start": 1.0, "end": 9.0, "text": f"Bitcoin is {v}.",
 818 | -                              "transcript_sha256": "t", "url_30s_before": "u"} for v in ("aaaaaaaaaaa", "bbbbbbbbbbb")]}
 819 | +                              "transcript_sha256": "t", "url_30s_before": "u", "time_sensitive": False,
 820 | +                              "source_published_at": "2026-11-12T01:00:00Z"} for v in ("aaaaaaaaaaa", "bbbbbbbbbbb")]}
 821 |  
 822 |      def test_the_pin_refuses_anything_not_exactly_pass_and_is_sealed(self):
 823 |          pin = package_pin.to_pin(self.pk(), "r")
 824 | @@ -156,6 +157,36 @@ class TestPinAndTruth(unittest.TestCase):
 825 |          with self.assertRaises(package_pin.PinRefused):
 826 |              package_pin.to_pin(p, "r")
 827 |  
 828 | +    def test_every_pin_segment_states_its_recency_facts_inside_the_seal(self):
 829 | +        """Ruling 1 (22:40): the render clock checks L-v 3 on pin.segments[i].time_sensitive / source_published_at;
 830 | +        both are sealed, and a pin without them is never written (the render side holds such a run too)."""
 831 | +        pin = package_pin.to_pin(self.pk(), "r")
 832 | +        self.assertEqual([(s["time_sensitive"], s["source_published_at"]) for s in pin["segments"]],
 833 | +                         [(False, "2026-11-12T01:00:00Z")] * 2)
 834 | +        mp = pin["moments_package"]
 835 | +        for key, val in (("time_sensitive", True), ("source_published_at", "2026-11-12T01:00:01Z")):
 836 | +            segs = [dict(pin["segments"][0], **{key: val})] + pin["segments"][1:]
 837 | +            self.assertNotEqual(mp["package_sha256"], package_pin.seal(segs, mp["edl_vo"], mp["signoff_expected"],
 838 | +                                                                        mp["title"], mp["caption"], mp["gates"]), key)
 839 | +        for key, bad in (("time_sensitive", None), ("time_sensitive", "true"), ("time_sensitive", 1),
 840 | +                         ("source_published_at", None), ("source_published_at", "2026-11-12T01:00:00+00:00"),
 841 | +                         ("source_published_at", "2026-11-12 01:00:00Z"), ("source_published_at", "2026-13-40T01:00:00Z")):
 842 | +            p = self.pk()
 843 | +            p["segments"] = [dict(p["segments"][0], **{key: bad})] + p["segments"][1:]
 844 | +            with self.assertRaises(package_pin.PinRefused) as cm:
 845 | +                package_pin.to_pin(p, "r")
 846 | +            self.assertIn(f"segment 0: {key}", str(cm.exception))
 847 | +        p = self.pk()
 848 | +        p["segments"] = [{k: v for k, v in p["segments"][0].items() if k != "source_published_at"}] + p["segments"][1:]
 849 | +        with self.assertRaises(package_pin.PinRefused):
 850 | +            package_pin.to_pin(p, "r")
 851 | +
 852 | +    def test_the_package_states_each_clips_recency_from_its_moment(self):
 853 | +        self.assertEqual(PK.utc_z("2026-11-11T13:03:23-05:00"), "2026-11-11T18:03:23Z")
 854 | +        self.assertEqual(PK.utc_z("2026-11-11T18:03:23Z"), "2026-11-11T18:03:23Z")
 855 | +        self.assertIsNone(PK.utc_z("2026-11-11T18:03:23"))                       # no offset: not a time we can place
 856 | +        self.assertIsNone(PK.utc_z(None))
 857 | +
 858 |      def test_the_second_pass_compares_both_ways_inside_the_clip_only(self):
 859 |          self.assertFalse(TT.compare("Bitcoin is going to zero.", "Bitcoin is not going to zero.")["ok"])   # a dropped not
 860 |          self.assertFalse(TT.compare("Bitcoin is not going to zero.", "Bitcoin is going to zero.")["ok"])
 861 | diff --git a/tests/package/test_gates.py b/tests/package/test_gates.py
 862 | index 3f5e7b23..71cc0330 100644
 863 | --- a/tests/package/test_gates.py
 864 | +++ b/tests/package/test_gates.py
 865 | @@ -22,7 +22,7 @@ class Canned:
 866 |          self.answers, self.calls, self.rejected = {k: list(v) for k, v in answers.items()}, [], []
 867 |  
 868 |      def call(self, role, prompt, max_tokens=2000, seed=7, system=None, avoid_vendor=None, avoid_model=None,
 869 | -             avoid_family=None):
 870 | +             avoid_family=None, deadline_s=None):
 871 |          self.calls.append((role, avoid_vendor, avoid_family))
 872 |          q = self.answers.get(role)
 873 |          if not q:
 874 | diff --git a/tests/package/test_house_style.py b/tests/package/test_house_style.py
 875 | new file mode 100644
 876 | index 00000000..3d75022d
 877 | --- /dev/null
 878 | +++ b/tests/package/test_house_style.py
 879 | @@ -0,0 +1,166 @@
 880 | +#!/usr/bin/env python3
 881 | +"""pipeline/house_style.py, ORCHESTRATOR RULING 6 (22:40 ET Nov 12): the house style of the title, the caption and the
 882 | +takeaway (bridges get the rules shared by every surface). Must-fail and must-pass cases; the 41f29b1f pin's own lines
 883 | +are the fixtures the ruling names. Offline, no model."""
 884 | +import os
 885 | +import sys
 886 | +import unittest
 887 | +
 888 | +HERE = os.path.dirname(os.path.abspath(__file__))
 889 | +REPO = os.path.dirname(os.path.dirname(HERE))
 890 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
 891 | +import house_style as HS  # noqa: E402
 892 | +
 893 | +PIN_41F29B1F = {   # the delivered medley's lines (tests/package/proof/fresh_20261112_050611/MOMENTS_PIN_LY.json)
 894 | +    "caption": "A market that no single authority can switch off may be the most mispriced opportunity in finance, and "
 895 | +               "that is the point this medley builds toward.",
 896 | +    "title": "Bitcoin's overlooked value comes from a market no government owns",
 897 | +    "takeaway": "What stands out is how rare it is for any asset to be priced by everyone and controlled by no one, which "
 898 | +                "makes the usual political drama feel irrelevant.",
 899 | +}
 900 | +
 901 | +
 902 | +def ids(slot, text):
 903 | +    return {v["detail"].split(":")[0] for v in HS.lint(slot, text)}
 904 | +
 905 | +
 906 | +class TestTheDeliveredLines(unittest.TestCase):
 907 | +    def test_the_41f29b1f_caption_fails_four_rules(self):
 908 | +        got = ids("caption", PIN_41F29B1F["caption"])
 909 | +        self.assertTrue({"caption-lowercase", "hedge", "self-reference", "money-word"} <= got, got)
 910 | +        self.assertIn("caption-words", got)                     # 26 words, over 24
 911 | +        self.assertGreaterEqual(len(got), 4)
 912 | +
 913 | +    def test_the_41f29b1f_title_fails_possessive_and_length(self):
 914 | +        self.assertEqual(ids("title", PIN_41F29B1F["title"]), {"title-possessive", "title-words"})
 915 | +
 916 | +    def test_the_41f29b1f_takeaway_fails_opener_which_makes_and_length(self):
 917 | +        self.assertEqual(ids("takeaway", PIN_41F29B1F["takeaway"]),
 918 | +                         {"takeaway-opener", "which-makes", "takeaway-words"})
 919 | +
 920 | +    def test_the_style_reference_fails_only_its_length(self):
 921 | +        self.assertEqual(len(HS.STYLE_REFERENCE.split()), 24)
 922 | +        self.assertEqual(ids("takeaway", HS.STYLE_REFERENCE), {"takeaway-words"})
 923 | +
 924 | +
 925 | +class TestMustPass(unittest.TestCase):
 926 | +    def test_plain_lines_pass(self):
 927 | +        self.assertEqual(HS.lint("title", "The market no government owns"), [])
 928 | +        self.assertEqual(HS.lint("caption", "no authority. that's the design."), [])
 929 | +        self.assertEqual(HS.lint("bridge", "Next, on keys."), [])
 930 | +        self.assertEqual(HS.lint("bridge_1", "Next, on keys."), [])
 931 | +        self.assertEqual(HS.lint("intro", "Next, on keys."), [])
 932 | +        self.assertEqual(HS.lint("takeaway", "No ruler. Just rules nobody gets to bend."), [])
 933 | +
 934 | +    def test_pbx_s_own_caption_fails_only_the_sentence_count(self):
 935 | +        self.assertEqual(ids("caption", "no authority. that's the design. three clips, links below."),
 936 | +                         {"caption-sentences"})
 937 | +
 938 | +    def test_no_false_hedges_and_no_false_possessives(self):
 939 | +        for ok in ("the mayor spoke", "maybe not", "mighty rules", "the perhapsless case"):
 940 | +            self.assertNotIn("hedge", ids("caption", ok), ok)
 941 | +        self.assertNotIn("title-possessive", ids("title", "It's the market no government owns"))
 942 | +        self.assertNotIn("title-possessive", ids("title", "That's the design"))
 943 | +        self.assertIn("title-possessive", ids("title", "Bitcoin’s quiet edge"))      # a curly apostrophe too
 944 | +        self.assertIn("title-possessive", ids("title", "Holders' real problem"))      # a plural possessive
 945 | +
 946 | +    def test_a_one_letter_abbreviation_ends_no_sentence(self):
 947 | +        self.assertEqual(HS.sentence_count("u.s. markets fell. bitcoin did not."), 2)
 948 | +        self.assertEqual(HS.sentence_count("no authority"), 1)
 949 | +        self.assertEqual(HS.sentence_count(""), 0)
 950 | +
 951 | +    def test_money_words_are_stems_on_purpose(self):
 952 | +        self.assertIn("money-word", ids("caption", "an investigation of the network"))    # deliberate: invest\w*
 953 | +        self.assertNotIn("money-word", ids("caption", "a nonprofit keeps the code"))     # not a word start
 954 | +
 955 | +
 956 | +class TestEveryRuleFails(unittest.TestCase):
 957 | +    def test_hashtag_on_every_surface(self):
 958 | +        for slot in ("title", "caption", "takeaway", "bridge"):
 959 | +            self.assertIn("hashtag", ids(slot, "rules #bitcoin"), slot)
 960 | +        self.assertNotIn("hashtag", ids("caption", "rule # one"))                        # a bare '#' is no tag
 961 | +
 962 | +    def test_each_dash_form(self):
 963 | +        for d in ("—", "–", " -- "):
 964 | +            self.assertIn("em-dash", ids("caption", f"no ruler{d}just rules"), repr(d))
 965 | +        self.assertNotIn("em-dash", ids("caption", "self-custody, no ruler"))             # a hyphen is fine
 966 | +
 967 | +    def test_emoji(self):
 968 | +        for e in ("\U0001F680", "⭐", "✅", "\U0001F1FA\U0001F1F8"):
 969 | +            self.assertIn("emoji", ids("title", f"No ruler {e}"), repr(e))
 970 | +
 971 | +    def test_every_hedge(self):
 972 | +        for h in HS.HEDGES:
 973 | +            self.assertIn("hedge", ids("takeaway", f"It {h} hold."), h)
 974 | +            self.assertIn("hedge", ids("caption", f"it {h.upper()} hold."), h)          # case-insensitive
 975 | +
 976 | +    def test_every_ai_phrase(self):
 977 | +        for p in HS.AI_PHRASES:
 978 | +            self.assertIn("ai-phrasing", ids("bridge", f"Here, {p} things."), p)
 979 | +        self.assertIn("ai-phrasing", ids("bridge", "It’s worth noting the rules."))     # the curly apostrophe
 980 | +
 981 | +    def test_every_self_reference(self):
 982 | +        for p in HS.SELF_REFERENCE:
 983 | +            self.assertIn("self-reference", ids("caption", f"look at {p} now."), p)
 984 | +
 985 | +    def test_every_money_pattern(self):
 986 | +        for word in ("opportunity", "opportunities", "invest", "investors", "profit", "profitable", "get rich",
 987 | +                     "to the moon", "buy the dip", "financial advice"):
 988 | +            self.assertIn("money-word", ids("caption", f"some {word} here."), word)
 989 | +
 990 | +    def test_the_length_rules(self):
 991 | +        self.assertIn("title-words", ids("title", " ".join(["word"] * (HS.TITLE_MAX_WORDS + 1))))
 992 | +        self.assertNotIn("title-words", ids("title", " ".join(["word"] * HS.TITLE_MAX_WORDS)))
 993 | +        self.assertIn("takeaway-words", ids("takeaway", " ".join(["word"] * (HS.TAKEAWAY_MAX_WORDS + 1))))
 994 | +        self.assertNotIn("takeaway-words", ids("takeaway", " ".join(["word"] * HS.TAKEAWAY_MAX_WORDS)))
 995 | +        self.assertIn("caption-words", ids("caption", " ".join(["word"] * (HS.CAPTION_MAX_WORDS + 1))))
 996 | +        self.assertNotIn("caption-words", ids("caption", " ".join(["word"] * HS.CAPTION_MAX_WORDS)))
 997 | +        self.assertIn("caption-lowercase", ids("caption", "no Ruler."))
 998 | +
 999 | +    def test_every_opener_and_which_makes(self):
1000 | +        for o in HS.TAKEAWAY_OPENERS:
1001 | +            self.assertIn("takeaway-opener", ids("takeaway", f"\"{o.capitalize()}, the rules hold."), o)
1002 | +            self.assertNotIn("takeaway-opener", ids("takeaway", f"The rules hold, {o}."), o)    # only as the opener
1003 | +        self.assertIn("which-makes", ids("takeaway", "The rules hold, which makes it rare."))
1004 | +
1005 | +    def test_every_rule_id_has_a_must_fail_case(self):
1006 | +        fired = set()
1007 | +        for slot, text in [("caption", PIN_41F29B1F["caption"]), ("title", PIN_41F29B1F["title"]),
1008 | +                           ("takeaway", PIN_41F29B1F["takeaway"]), ("caption", "one. two. three."),
1009 | +                           ("bridge", "#tag — \U0001F680 delve")]:
1010 | +            fired |= ids(slot, text)
1011 | +        self.assertEqual(fired, set(HS.RULE_IDS))
1012 | +
1013 | +
1014 | +class TestTheInterface(unittest.TestCase):
1015 | +    def test_violations_carry_the_slot_rule_and_a_rule_id_detail(self):
1016 | +        for v in HS.lint("caption", PIN_41F29B1F["caption"]):
1017 | +            self.assertEqual((v["slot"], v["rule"]), ("caption", "STYLE"))
1018 | +            self.assertIn(v["detail"].split(":")[0], HS.RULE_IDS)
1019 | +        self.assertEqual(len({v["detail"].split(":")[0] for v in HS.lint("caption", PIN_41F29B1F["caption"])}),
1020 | +                         len(HS.lint("caption", PIN_41F29B1F["caption"])))             # one violation per rule id
1021 | +
1022 | +    def test_lint_lines_keeps_each_line_s_own_slot_and_skips_the_rest(self):
1023 | +        lines = [{"slot": "intro", "text": "Next — keys."}, {"slot": "bridge_1", "text": "maybe #keys"},
1024 | +                 {"slot": "takeaway", "text": PIN_41F29B1F["takeaway"]}, {"slot": "title", "text": "Fine title"},
1025 | +                 {"slot": "caption", "text": "fine caption."}, {"slot": "-", "text": "#ignored"}]
1026 | +        got = [(v["slot"], v["detail"].split(":")[0]) for v in HS.lint_lines(lines)]
1027 | +        self.assertIn(("intro", "em-dash"), got)
1028 | +        self.assertIn(("bridge_1", "hashtag"), got)
1029 | +        self.assertNotIn(("bridge_1", "hedge"), got)                                      # "maybe" is no hedge
1030 | +        self.assertIn(("takeaway", "which-makes"), got)
1031 | +        self.assertFalse([s for s, _ in got if s in ("title", "caption", "-")])
1032 | +
1033 | +    def test_an_unknown_slot_is_refused(self):
1034 | +        with self.assertRaises(ValueError):
1035 | +            HS.lint("signoff", "Clips today from A.")
1036 | +
1037 | +    def test_the_prompt_states_the_same_rules(self):
1038 | +        p = HS.PROMPT_RULES
1039 | +        for x in (str(HS.CAPTION_MAX_WORDS), str(HS.TITLE_MAX_WORDS), str(HS.TAKEAWAY_MAX_WORDS), HS.STYLE_REFERENCE,
1040 | +                  "lowercase", "possessive", "which makes") + HS.HEDGES + HS.SELF_REFERENCE + HS.TAKEAWAY_OPENERS:
1041 | +            self.assertIn(x, p, x)
1042 | +
1043 | +
1044 | +if __name__ == "__main__":
1045 | +    unittest.main()
1046 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
1047 | index f0a35edc..9c6fe5af 100644
1048 | --- a/tests/package/test_medley.py
1049 | +++ b/tests/package/test_medley.py
1050 | @@ -60,9 +60,9 @@ def medley_pk(n=3, bridge=None, after=None, flagged=(), measured=True, chans=Non
1051 |  class TestMedleyArithmetic(unittest.TestCase):
1052 |      def test_the_medley_seconds_let_one_takeaway_land_60_to_70(self):
1053 |          lo, hi = PK.medley_content_range()
1054 | -        self.assertEqual((lo, hi), (32.7, 51.5))          # 60 - 14.30 - (30 / 2.5 + 1); 70 - 14.30 - (8 / 2.5 + 1)
1055 | -        seg = lambda c: [{"duration_s": c}]
1056 | -        self.assertAlmostEqual(PK.runtime(seg(lo), [W(PK.MOMENTS_TAKEAWAY_WORD_CAP)]), 60.0, places=2)
1057 | +        self.assertEqual((lo, hi), (36.7, 51.5))          # 60 - 14.30 - (20 / 2.5 + 1); 70 - 14.30 - (8 / 2.5 + 1)
1058 | +        seg = lambda c: [{"duration_s": c}]               # (ruling 6, 22:40: a new takeaway is at most 20 words)
1059 | +        self.assertAlmostEqual(PK.runtime(seg(lo), [W(PK.LY_TAKEAWAY_MAX_WORDS)]), 60.0, places=2)
1060 |          self.assertAlmostEqual(PK.runtime(seg(hi), [W(PK.LY_TAKEAWAY_MIN_WORDS)]), 70.0, places=2)
1061 |          lo1, hi1 = PK.medley_content_range(n_bridges=1)
1062 |          self.assertAlmostEqual(lo - lo1, PK.LY_BRIDGE_WORDS / 2.5 + 1.0, places=2)
1063 | @@ -77,7 +77,7 @@ class TestMedleyArithmetic(unittest.TestCase):
1064 |                  self.assertTrue(c > PK.medley_content_range()[1] or c < PK.medley_content_range()[0], c)
1065 |                  continue
1066 |              lo, hi = b
1067 | -            self.assertTrue(PK.LY_TAKEAWAY_MIN_WORDS <= lo <= hi <= PK.MOMENTS_TAKEAWAY_WORD_CAP, (c, b))
1068 | +            self.assertTrue(PK.LY_TAKEAWAY_MIN_WORDS <= lo <= hi <= PK.LY_TAKEAWAY_MAX_WORDS, (c, b))
1069 |              for w in (lo, hi):
1070 |                  est = PK.runtime([{"duration_s": c}], [W(w)])
1071 |                  self.assertTrue(PK.RUNTIME_S[0] <= est <= PK.RUNTIME_S[1], (c, w, est))
1072 | @@ -87,7 +87,7 @@ class TestMedleyArithmetic(unittest.TestCase):
1073 |              aimed += all(PK.LY_AIM_S[0] <= PK.runtime([{"duration_s": c}], [W(w)]) <= PK.LY_AIM_S[1] for w in (lo, hi))
1074 |          self.assertGreater(aimed, 100)                    # most clip lengths land the aim (61.5-68.5 s)
1075 |          self.assertIsNone(PK.takeaway_budget(60.0))       # too many seconds of clips: no takeaway lands 70 s
1076 | -        b0, b1 = PK.takeaway_budget(40.0), PK.takeaway_budget(40.0, other=[W(10)])
1077 | +        b0, b1 = PK.takeaway_budget(45.0), PK.takeaway_budget(45.0, other=[W(10)])
1078 |          self.assertLess(b1[1], b0[1])                     # a bridge's seconds come off the takeaway
1079 |  
1080 |  
1081 | @@ -100,9 +100,9 @@ class TestMedleyLineup(unittest.TestCase):
1082 |          self.assertTrue(PK.medley_content_range()[0] <= sum(m["duration_s"] for m in seg) <= PK.medley_content_range()[1])
1083 |  
1084 |      def test_more_clips_when_two_do_not_fill_the_medley(self):
1085 | -        by = {m["moment_id"]: m for m in (pm("h", "A", 9.0), pm("x", "B", 9.0), pm("y", "C", 9.0), pm("z", "D", 9.0))}
1086 | +        by = {m["moment_id"]: m for m in (pm("h", "A", 9.5), pm("x", "B", 9.5), pm("y", "C", 9.5), pm("z", "D", 9.5))}
1087 |          seg = PK.lineup_for(angle(["h", "x", "y", "z"], "h"), by)
1088 | -        self.assertEqual([m["moment_id"] for m in seg], ["h", "x", "y", "z"])   # 36 s: the hook + 3 clips
1089 | +        self.assertEqual([m["moment_id"] for m in seg], ["h", "x", "y", "z"])   # 38 s: the hook + 3 clips
1090 |          short = {k: dict(v, duration_s=6.0) for k, v in by.items()}
1091 |          self.assertIsNone(PK.lineup_for(angle(["h", "x", "y", "z"], "h"), short))   # 24 s: no medley fits
1092 |  
1093 | @@ -212,7 +212,7 @@ class TestWriteTakeaway(unittest.TestCase):
1094 |                  continue
1095 |              fits += 1
1096 |              PK.write_takeaway(r, angle(["h", "x", "y"], "h"), segs, E.Context(NOW, REG), {}, join=(1, "w"))
1097 | -            lo, hi = map(int, re.search(r"one or two sentences, (\d+)-(\d+) words", prompts[0]).groups())
1098 | +            lo, hi = map(int, re.search(r'"takeaway": (\d+)-(\d+) words', prompts[0]).groups())
1099 |              n = int(re.search(r"as short as it can be \(at most (\d+) words\)", prompts[0]).group(1))
1100 |              self.assertEqual((n, (lo, hi)), bb)
1101 |              self.assertTrue(PK.LY_BRIDGE_MIN_WORDS <= n <= PK.LY_BRIDGE_WORDS)
1102 | @@ -220,7 +220,7 @@ class TestWriteTakeaway(unittest.TestCase):
1103 |                  for bw in range(PK.LY_BRIDGE_MIN_WORDS, n + 1):
1104 |                      est = PK.runtime([{"duration_s": c}], [W(t), W(bw)])
1105 |                      self.assertTrue(PK.RUNTIME_S[0] <= est <= PK.RUNTIME_S[1], (c, t, bw, est))
1106 | -        self.assertGreater(fits, 50)
1107 | +        self.assertGreater(fits, 40)                       # coverage: both branches exercised (50 fit, ruling 6 caps)
1108 |          self.assertGreater(none, 0)                         # at the top of the medley's seconds no bridge fits
1109 |  
1110 |      def test_the_prompt_asks_for_one_takeaway_inside_the_budget(self):
1111 | @@ -230,7 +230,8 @@ class TestWriteTakeaway(unittest.TestCase):
1112 |          r.call = lambda role, prompt, *a, **k: (prompts.append(prompt), call(role, prompt, *a, **k))[1]
1113 |          PK.write_takeaway(r, angle(["h", "x", "y"], "h"), self.SEGS, E.Context(NOW, REG), {})
1114 |          lo, hi = PK.takeaway_budget(39.0)
1115 | -        self.assertIn(f"one or two sentences, {lo}-{hi} words", prompts[0])
1116 | +        self.assertIn(f'"takeaway": {lo}-{hi} words in short declarative sentences', prompts[0])
1117 | +        self.assertIn("HOUSE STYLE", prompts[0])                  # ruling 6 (22:40): the copy rules ride every write
1118 |          self.assertNotIn("ONE JOIN NEEDS HELP", prompts[0])
1119 |          self.assertNotIn('"intro"', prompts[0])
1120 |  
1121 | @@ -284,6 +285,16 @@ class TestLyShape(unittest.TestCase):
1122 |          pk["vo"] = dict(pk["vo"], bridges=[], bridges_after_clip=[])
1123 |          self.assertFalse(PK.ly_shape(pk)[0])
1124 |  
1125 | +    def test_a_no_voice_medley_needs_its_record_and_no_vo_line(self):
1126 | +        pk = medley_pk()
1127 | +        pk["vo"] = dict(pk["vo"], bridges=[], bridges_after_clip=[])
1128 | +        self.assertFalse(PK.ly_shape(pk)[0])                          # no takeaway and no record: L-y 1 fails
1129 | +        self.assertTrue(PK.ly_shape(dict(pk, no_voice={"why": "the takeaway failed twice"}, bridge=None))[0])
1130 | +        self.assertFalse(PK.ly_shape(dict(pk, no_voice={"why": " "}, bridge=None))[0])      # a record without a why
1131 | +        self.assertFalse(PK.ly_shape(dict(medley_pk(), no_voice={"why": "x"}))[0])        # a VO line with the record
1132 | +        flagged = dict(pk, no_voice={"why": "x"}, bridge=None, medley={"measured": True, "flagged": ["hook -> clip_01"]})
1133 | +        self.assertFalse(PK.ly_shape(flagged)[0])                     # a join a viewer cannot follow, left unbridged
1134 | +
1135 |      def test_three_to_five_segments_and_one_clip_per_channel(self):
1136 |          self.assertFalse(PK.ly_shape(medley_pk(n=2))[0])
1137 |          self.assertFalse(PK.ly_shape(medley_pk(n=6))[0])
1138 | @@ -323,6 +334,16 @@ class TestMedleyPackageAndPin(unittest.TestCase):
1139 |          self.assertAlmostEqual(pk["runtime_s_estimate"], 39.0 + 8 / 2.5 + 1.0 + PK.FINAL_TAIL_S, places=2)
1140 |          self.assertEqual(PK.r4(pk)[0], True)
1141 |  
1142 | +    def test_each_segment_states_whether_its_clip_is_time_sensitive_and_when_it_was_published(self):
1143 | +        by = {m["moment_id"]: m for m in (pm("h", "A", 12.0), pm("x", "B", 14.0, risk=("time_sensitive",)),
1144 | +                                          pm("y", "C", 13.0))}
1145 | +        fields = {"takeaway": {"text": "No ruler, just rules.", "cites": []}, "bridge": None, "bridge_after": None,
1146 | +                  "title": {"text": "No ruler", "cites": []}, "caption": {"text": "three clips", "cites": []}}
1147 | +        pk = PK.assemble_medley(["h", "x", "y"], by, fields, ctx(), "medley (L-y)")
1148 | +        self.assertEqual([s["time_sensitive"] for s in pk["segments"]], [False, True, False])
1149 | +        self.assertEqual({s["source_published_at"] for s in pk["segments"]}, {PK.utc_z(by["h"]["published_at"])})
1150 | +        self.assertRegex(pk["segments"][0]["source_published_at"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
1151 | +
1152 |      def test_the_one_bridge_after_a_clip_or_after_the_hook(self):
1153 |          b = {"text": "Next, on keys.", "cites": ["y"], "why": "no referent"}
1154 |          pk = self.build(bridge=b, k=1, n=4)
1155 | @@ -337,14 +358,14 @@ class TestMedleyPackageAndPin(unittest.TestCase):
1156 |  
1157 |      def test_the_pin_requires_the_medley_rows_and_carries_intro_null(self):
1158 |          pk = self.build()
1159 | -        self.assertEqual(package_pin.required_gates(pk)[-2:], ("medley", "ly_shape"))
1160 | +        self.assertEqual(package_pin.required_gates(pk)[-3:], ("medley", "ly_shape", "house_style"))
1161 |          pk["gates"] = self.gates(pk)
1162 |          pin = package_pin.to_pin(pk, "test")
1163 |          mp = pin["moments_package"]
1164 |          self.assertEqual(mp["edl_vo"], {"intro": None, "bridges": [{"text": pk["vo"]["bridges"][0], "after_clip": 2}]})
1165 |          self.assertEqual(mp["vo_jobs"], {"takeaway": "takeaway"})
1166 |          self.assertEqual(mp["shape"], "medley")
1167 | -        for missing in ("medley", "ly_shape"):
1168 | +        for missing in ("medley", "ly_shape", "house_style"):
1169 |              g = self.gates(pk)
1170 |              g.pop(missing)
1171 |              with self.assertRaises(package_pin.PinRefused):
1172 | @@ -389,9 +410,11 @@ class Rig:
1173 |      A_OK = {"backend": "xai:grok", "replayed": False, "speaker_changes_inside": "no", "view": "own_sincere",
1174 |              "referents": [], "conditions": [], "retraction": "none", "time_ok": "yes", "certainty": "certain"}
1175 |  
1176 | -    def __init__(self, moments, angle_moments, medleys, writes, uncuttable=(), excluded=()):
1177 | +    def __init__(self, moments, angle_moments, medleys, writes, uncuttable=(), excluded=(), takeaways=None,
1178 | +                 spend=None):
1179 |          import providers as P
1180 |          self.P, self.moments, self.medleys, self.writes = P, moments, list(medleys), list(writes)
1181 | +        self.takeaways, self.spend = list(takeaways or []), spend
1182 |          self.uncuttable, self.excluded = set(uncuttable), set(excluded)
1183 |          self.medley_calls, self.write_calls, self.prompts = [], [], []
1184 |          many = angle_moments if isinstance(angle_moments[0], list) else [angle_moments]
1185 | @@ -399,7 +422,11 @@ class Rig:
1186 |          call = self.router.call
1187 |          self.router.call = lambda role, prompt, *a, **k: (self.prompts.append((role, prompt)),
1188 |                                                            call(role, prompt, *a, **k))[1]
1189 | -        self.router.backends = {"xai:grok": type("B", (), {"vendor": "xai", "family": "grok"})()}
1190 | +        B = lambda v, f: type("B", (), {"vendor": v, "family": f})()
1191 | +        self.router.backends = {"xai:grok": B("xai", "grok"), "heimdall:deepseek": B("heimdall", "deepseek"),
1192 | +                                "heimdall:qwen": B("heimdall", "qwen")}
1193 | +        self.router.chain = lambda role: ["heimdall:deepseek", "heimdall:qwen", "xai:grok"]
1194 | +        self.write_avoid = []
1195 |  
1196 |      def medley(self, router, segs, ctx_, wv, seed=7, writer_family=None):
1197 |          self.medley_calls.append([m["moment_id"] for m in segs])
1198 | @@ -412,11 +439,12 @@ class Rig:
1199 |          if join is not None and not other and PK.bridge_budget(sum(m["duration_s"] for m in segs)) is None:
1200 |              raise PK.NoBridgeFits("no bridge of 3-12 words fits (the real write_takeaway's precondition)")
1201 |          self.write_calls.append(([m["moment_id"] for m in segs], join))
1202 | +        self.write_avoid.append(avoid_vendor)
1203 |          b = self.writes.pop(0)
1204 | -        fields = {"takeaway": {"text": self.LINE, "cites": []}, "bridge": b,
1205 | +        fields = {"takeaway": {"text": self.takeaways.pop(0) if self.takeaways else self.LINE, "cites": []}, "bridge": b,
1206 |                    "bridge_after": join[0] if join is not None and b is not None else None,
1207 |                    "title": {"text": "Nobody bends the rules", "cites": []},
1208 | -                  "caption": {"text": "three voices, one point", "cites": []},
1209 | +                  "caption": {"text": "nobody bends these rules", "cites": []},
1210 |                    "type": "moments", "angle": angle_["angle"], "style": "medley", "takeaway_budget": [10, 30]}
1211 |          return self.P.Reply("{}", "heimdall:deepseek", "heimdall", family="deepseek"), fields
1212 |  
1213 | @@ -446,7 +474,8 @@ class Rig:
1214 |          try:
1215 |              for k, v in stubs.items():
1216 |                  setattr(PK, k, v)
1217 | -            return PK.build(self.router, self.moments, {}, ctx(), log=lambda s: None, work_dir="/nonexistent")
1218 | +            return PK.build(self.router, self.moments, {}, ctx(), log=lambda s: None, work_dir="/nonexistent",
1219 | +                            spend=self.spend)
1220 |          finally:
1221 |              for k, v in saved.items():
1222 |                  setattr(PK, k, v)
1223 | @@ -525,6 +554,59 @@ class TestBuildLoop(unittest.TestCase):
1224 |          self.assertEqual(len(rig.write_calls), 2)          # the paid verdicts never ran on the doomed line-up
1225 |          self.assertEqual([s["moment_id"] for s in out["package"]["segments"]], ["h", "z", "w"])
1226 |  
1227 | +    def test_no_voice_when_the_takeaway_fails_twice_on_clips_that_hold_alone(self):
1228 | +        """Ruling 3 (22:40): clips back to back and the sign-off, NOT dropped; one clip added to land 60-70 s."""
1229 | +        bad = ["Ultimately the network decides what it is worth.", "In the end the rules decide everything here."]
1230 | +        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE), (True, [], None, Rig.LINE)],
1231 | +                  [None, None], takeaways=bad)
1232 | +        out = rig.run()
1233 | +        pk = out["package"]
1234 | +        self.assertIsNotNone(pk)
1235 | +        self.assertEqual(len(rig.write_calls), 2)                  # both takeaways failed (takeaway-opener)
1236 | +        self.assertEqual([s["moment_id"] for s in pk["segments"]], ["h", "x", "y", "z"])   # 39 s + z: 52 s
1237 | +        self.assertEqual(rig.medley_calls[-1], ["h", "x", "y", "z"])   # the new line-up judged on the clips alone
1238 | +        self.assertEqual((pk["vo"]["intro"], pk["vo"]["bridges"], pk["vo"]["bridges_after_clip"]), (None, [], []))
1239 | +        self.assertEqual(pk["no_voice"]["added_clip"], "z")
1240 | +        self.assertEqual([x["slot"] for x in pk["lines"]], ["title", "caption"])
1241 | +        self.assertAlmostEqual(pk["runtime_s_estimate"], 52.0 + PK.FINAL_TAIL_S, places=2)
1242 | +        self.assertTrue(all(g["status"] == "PASS" for g in pk["gates"].values()), pk["gates"])
1243 | +        self.assertIn("no VO line", pk["checks"]["coherence"]["note"])
1244 | +        mp = package_pin.to_pin(pk, "test")["moments_package"]
1245 | +        self.assertEqual(mp["edl_vo"], {"intro": None, "bridges": []})
1246 | +
1247 | +    def test_no_voice_never_ships_a_join_the_blind_check_flagged(self):
1248 | +        b = {"text": "Next, on keys.", "cites": ["y"], "why": "no referent"}
1249 | +        bad = ["Ultimately the network decides what it is worth.", "In the end the rules decide everything here."]
1250 | +        rig = Rig(self.MS, ["h", "x", "y"], [(True, ["clip_01 -> clip_02"], None, Rig.LINE)], [b, b], takeaways=bad)
1251 | +        out = rig.run()
1252 | +        self.assertIsNone(out["package"])
1253 | +        self.assertNotIn("no_voice", out["tried"][0])           # not tried: the clips need a bridge to be followed
1254 | +
1255 | +    def test_every_write_stays_on_the_angles_vendor(self):
1256 | +        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None])
1257 | +        out = rig.run()
1258 | +        self.assertEqual(rig.write_avoid, [{"heimdall", "xai"}])  # the angle came from vendor "fake": all others out
1259 | +        self.assertEqual(out["angle_backend"], "fake:angle_write")
1260 | +        self.assertEqual(out["angle_tried"], [])
1261 | +
1262 | +    def test_the_budget_stops_on_the_reported_cost_or_the_estimate_ceiling(self):
1263 | +        """Ruling 5 (22:40): per package 15 min wall / $1.50 by the vendors' reported cost; the estimate only as a $5
1264 | +        ceiling. Checked before every line-up and every write (audit 2240 C1, glm), not only when an angle ends."""
1265 | +        for spent, why in (((0.10, 1.51), "reported"), ((5.01, 0.20), "estimate ceiling")):
1266 | +            reads = [(0.0, 0.0), (0.0, 0.0)]                  # the baseline, then the check before line-up 1
1267 | +            calls = iter(reads + [spent] * 50)                # ... then over budget from the next check on
1268 | +            rig = Rig(self.MS, [["h", "x", "y"], ["h", "x", "z"]], [(False, [], None, "none")] * 2, [],
1269 | +                      spend=lambda: next(calls))
1270 | +            out = rig.run()
1271 | +            self.assertIn("ruling 5", out["why_none"], why)
1272 | +            self.assertEqual(len(rig.medley_calls), 1, why)          # line-up 1 ran; nothing after the stop
1273 | +            self.assertEqual(out["budget_stop"]["angles_tried"], 1, why)
1274 | +        over = iter([(0.0, 0.0)] + [(9.0, 9.0)] * 50)               # over budget from the very first check
1275 | +        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None], spend=lambda: next(over))
1276 | +        out = rig.run()
1277 | +        self.assertEqual((rig.medley_calls, rig.write_calls), ([], []))   # no clips-alone call, no write paid
1278 | +        self.assertIsNone(out["package"])
1279 | +
1280 |      def test_the_supply_exception_is_recorded(self):
1281 |          ms = [pm("h", "A", 14.0), pm("x", "B", 13.0), pm("y", "C", 3.0), pm("e", "A", 13.0)]
1282 |          rig = Rig(ms, ["h", "x", "y", "e"], [(True, [], None, Rig.LINE)], [None])
1283 | diff --git a/tests/providers/test_providers.py b/tests/providers/test_providers.py
1284 | index 23c2775b..fca94141 100644
1285 | --- a/tests/providers/test_providers.py
1286 | +++ b/tests/providers/test_providers.py
1287 | @@ -65,6 +65,56 @@ def wav(tmp, seconds=2.0):
1288 |      return p
1289 |  
1290 |  
1291 | +class Slow(Fake):
1292 | +    """A back-end that answers only after `delay` seconds (a Heimdall angle call that hangs)."""
1293 | +
1294 | +    def __init__(self, name, vendor, answer, delay, **kw):
1295 | +        super().__init__(name, vendor, answer=answer, **kw)
1296 | +        self.delay = delay
1297 | +
1298 | +    def complete(self, prompt, max_tokens, seed, system=None):
1299 | +        import time as _t
1300 | +        _t.sleep(self.delay)
1301 | +        return super().complete(prompt, max_tokens, seed, system)
1302 | +
1303 | +
1304 | +class TestDeadline(unittest.TestCase):
1305 | +    """Orchestrator 22:40 ruling 5: one writer call never waits more than its deadline; it fails over to the next
1306 | +    back-end, the failover is recorded, and the abandoned call's upper bound is booked as spent."""
1307 | +
1308 | +    def test_a_call_that_passes_its_deadline_fails_over_and_is_recorded(self):
1309 | +        import tempfile
1310 | +        import time as _t
1311 | +        with tempfile.TemporaryDirectory() as d:
1312 | +            slow = Slow("heimdall:deepseek", "heimdall", '{"ok": 1}', delay=2.0, family="deepseek")
1313 | +            next_ = Fake("heimdall:qwen", "heimdall", answer='{"ok": 2}', family="qwen")
1314 | +            r = router(d, [slow, next_], {"angle_write": ["heimdall:deepseek", "heimdall:qwen"]},
1315 | +                       spend_path=os.path.join(d, "SPEND.json"), limit_usd=50.0)
1316 | +            t0 = _t.time()
1317 | +            rep = r.call("angle_write", "p", 100, 7, deadline_s=0.3)
1318 | +            self.assertLess(_t.time() - t0, 1.5)                       # never waited for the slow one
1319 | +            self.assertEqual((rep.backend, rep.text), ("heimdall:qwen", '{"ok": 2}'))
1320 | +            self.assertIn("no answer within 0 s", rep.tried[0][1])   # the failover is recorded on the reply
1321 | +            self.assertIn("abandoned at the deadline", rep.tried[0][1])
1322 | +            led = json.load(open(os.path.join(d, "SPEND.json")))
1323 | +            self.assertEqual(led["by_backend"]["heimdall:deepseek"]["calls"], 1)       # booked, at its upper bound
1324 | +            self.assertAlmostEqual(led["by_backend"]["heimdall:deepseek"]["usd_estimate"],
1325 | +                                   slow.upper_usd("p", 100), places=6)
1326 | +            self.assertEqual(led["reserved"], {})                      # no reservation left behind
1327 | +
1328 | +    def test_an_answer_inside_the_deadline_and_an_error_keep_their_meaning(self):
1329 | +        import tempfile
1330 | +        with tempfile.TemporaryDirectory() as d:
1331 | +            ok = Slow("heimdall:deepseek", "heimdall", '{"ok": 1}', delay=0.05)
1332 | +            r = router(d, [ok], {"angle_write": ["heimdall:deepseek"]})
1333 | +            self.assertEqual(r.call("angle_write", "p", 100, 7, deadline_s=5).text, '{"ok": 1}')
1334 | +            bad = Fake("heimdall:deepseek", "heimdall", fail="HTTP 503")
1335 | +            r2 = router(d, [bad], {"angle_write": ["heimdall:deepseek"]})
1336 | +            with self.assertRaises(P.ProviderError) as cm:            # the back-end's own error, not a deadline
1337 | +                r2.call("angle_write", "p", 100, 7, deadline_s=5)
1338 | +            self.assertIn("HTTP 503", str(cm.exception))
1339 | +
1340 | +
1341 |  class TestRouter(unittest.TestCase):
1342 |      def test_the_chain_fails_over_and_names_the_model_that_answered(self):
1343 |          with tempfile.TemporaryDirectory() as d:
1344 | 
```

---

You are auditing a diff on branch pp-selectid (Protocol Pulse, moments-first packaging under law L-y, the MEDLEY: clips
back to back, ONE takeaway VO line at the end). It implements the orchestrator's rulings of 22:40 ET Nov 12. Standing
laws: nothing measured is never a pass (L-m); fail closed (L-j); never change what a check accepts in order to make
something pass; every verdict avoids the vendor and model family of any reply whose text it judges (L-x).

THE RULINGS (paraphrased exactly):
R1 Recency is checked against the RENDER clock, not the universe's. Pins carry, per segment, "time_sensitive" (bool)
   and "source_published_at" (ISO 8601 UTC), INSIDE the seal. The render side holds a run when a time-sensitive clip is
   older than 24 h at render time, and holds any pin missing or malforming either field.
R3 NO-VOICE FALLBACK (replaces the old plain-VO fallback, which had no L-y form): if the takeaway fails its gates twice,
   the package ships with NO takeaway (clips back to back and the sign-off only), provided the clips-alone verdict
   passed. It is not dropped. The runtime rule still applies, so the packager may add a clip.
R5 BUDGET with Heimdall as the writer: per package 15 min wall and $1.50 by the vendors' reported cost; the price-table
   estimate (it over-states about 7x) only as a hard ceiling at $5. One writer (angle) call may not wait more than
   5 min: on timeout it fails over to the next back-end (qwen, then xAI), and the failover is recorded.
R6 HOUSE STYLE on the three text surfaces, as a deterministic lint, writer-prompt rules and must-fail tests. PBX's copy
   rules: lowercase captions, no hashtags, no em-dashes, no emoji, no AI-sounding phrasing, no hedging.
   - CAPTION: lowercase, one or two short sentences; no hedges (may, might, could be, perhaps); no self-reference (this
     medley, this video, builds toward); no "opportunity"/"invest"-style words.
   - TITLE: at most 8 words, plain, no possessive throat-clearing.
   - TAKEAWAY: at most 20 words, short declarative sentences; never opens with "What stands out", "It's worth noting",
     "Ultimately", "In the end"; no "which makes ..." clause.
   The delivered 41f29b1f caption is a must-fail fixture. Still gated by VO fidelity / context integrity as before.

What changed, and what to check:
1. pipeline/package_pin.py: seal() hashes time_sensitive and source_published_at per segment; to_pin() refuses a
   package whose segment lacks either, or has a non-bool time_sensitive or a published time that is not exactly
   YYYY-MM-DDTHH:MM:SSZ and parseable (recency_problems). The pin's segments carry both fields.
   pipeline/package.py: _package computes them per segment (time_sensitive() of the moment; utc_z of its published_at).
   Can a pin be written whose recency facts are missing, wrong or outside the seal? Is utc_z right on offsets?
2. pipeline/house_style.py (new): lint(slot, text) and lint_lines(lines); the rules and constants; PROMPT_RULES.
   package.cheap_checks runs it on every line of a medley; a sealed "house_style" inventory row is required for a medley
   pin (package_pin.MEDLEY_GATES); the writer prompt carries PROMPT_RULES; the takeaway's word budget is capped at 20
   (LY_TAKEAWAY_MAX_WORDS), so medley_content_range is now 36.7-51.5 s. Check false positives and negatives, the
   sentence counting, the possessive / contraction handling and the emoji ranges.
3. The no-voice fallback in package.build(): a line-up whose clips-alone verdict passed with NO flagged join, whose
   takeaway failed its own gates in both writes (take_failed >= NO_VOICE_AFTER), gets no_voice():
   - the latest write's title and caption;
   - when the clips are under 45.7 s, ONE more clip of the angle in the proposer's order, and that line-up judged on
     the clips alone again with no flagged join;
   - assemble_medley with no takeaway and no bridge, recording pk["no_voice"] = {why, added_clip, lineup_before};
   - every gate again: cheap, exclusion / L-v 2 / CUTTABLE, fidelity and context;
   - coherence = the clips-alone verdict;
   - the inventory, then package_pin.gate_problems.
   ly_shape accepts no VO line only with that record. Can a no-voice package ship without its clips-alone verdict, with
   a join a viewer cannot follow, with a VO line, outside 60-70 s, or with title / caption that skipped a gate?
4. pipeline/providers.py: Router.call(..., deadline_s): the back-end runs in a daemon thread (_within). Past the
   deadline the call is abandoned (DeadlineExceeded), its reservation is settled at its UPPER bound as spent, the
   failover is recorded in Reply.tried, and the next back-end in the chain is tried. Can a reservation leak? Can an
   abandoned call's late answer be recorded or served? Is a back-end's own error still reported as before?
5. package.build(): every writer call carries WRITER_DEADLINE_S (300 s); every takeaway write avoids every writer
   vendor except the angle's (writer_avoid), so the judges keep a vendor; out["angle_tried"] records the failover.
   The budget stop (checked when an angle ends) is: wall > 900 s, or vendor-reported > $1.50, or estimate > $5;
   spend() returns (estimate, reported).
6. tests: test_medley.py (no-voice, vendor pinning, budget, recency), test_house_style.py, test_angles.py (recency
   must-fails), test_providers.py (TestDeadline), test_gates.py (the Canned router takes deadline_s).

Output: findings ranked P0 / P1 / P2, each with file:line and a concrete failure scenario (inputs -> wrong result).
Only state what you can verify from the diff provided. If uncertain, say so; do not guess. End with a verdict line:
"SHIP: yes | yes with conditions | no".


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
