# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-0007
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 208 s finish=stop usage in 19849 / out 5933 usd~0.149 (upper-bound price)

# Audit — pp-selectid (speakers + batch), 2026-11-13

Scope note: I can only see the diff. I have not seen `providers.py`, `package.py`, `eligibility.py`, `proof_ly.py`'s `meter`/`reply_meter`, or the store's `meta.json` schema, so anything that depends on their internals is marked uncertain.

## P0

None found. (I looked for: a wrong name reaching a pin, a silent failure counted as a pass, a seal leak, a delivered-span leak. Each is addressed below; none is a blocker.)

## P1

**P1-1 — `speakers.attribute` (pipeline/speakers.py:241-249, diff lines 241-249): a JSON reply that is valid JSON but not a dict, or a `check()`-shaped failure, is handled inconsistently; and `router.reject` is only called for ValueError/TypeError, not for a `check`-contract failure raised as something else.**
Concrete: `check()` raises `ValueError("speaker verdict out of contract")` when `v` is not a dict / `people` not a list / `speaker` not a dict. That is caught, `r` is not None and it's a ValueError → `router.reject(r)` is called, and the record is `unknown, measured=False`. Good. But if `json.loads` succeeds and returns e.g. a *list* (a JSON array reply), `check` raises ValueError → reject → unknown. Also fine. What I cannot verify: whether `router.call` itself can raise other exception types (e.g. `KeyError`, `json.JSONDecodeError` — note `json.JSONDecodeError` *is* a subclass of `ValueError`, so that's covered; but a `ProviderError` subclass like a timeout) that would propagate out of `attribute` and out of `attribute_package`, aborting the whole package seal rather than degrading that one segment to "unknown". The `except` clause lists `(P.ProviderError, P.SpendLimit, ValueError, TypeError)`; if `providers.Router.call` raises anything else (e.g. `KeyError` for a missing chain, `AttributeError`), `attribute_package` (line 254-260) has no try/except, so the whole seal fails. Whether that's a defect depends on `providers.py`'s contract, which I don't have. Flagging as "verify": **if `Router.call` can raise anything outside that tuple, one bad segment kills the batch's seal** — arguably fail-closed-correct, but it contradicts the docstring "A call that fails, or a reply out of contract, is 'unknown' with measured false" (line 231).

**P1-2 — `speakers.attribute` (line 244): `check(json.loads(r.text.strip()), ...)` — `r.text` may carry markdown fences.** If the model returns ` ```json ... ``` `, `json.loads` raises `JSONDecodeError` (a ValueError) → caught → `unknown, measured=False`, and `router.reject(r)` is called. So it fails closed, but a *good* reply wrapped in fences is silently discarded and the segment ships "unknown" even though the model answered. Whether the router already strips fences is not visible in the diff. If it doesn't, this is a systematic "unknown" bias, not a correctness bug. Verify against `providers.py`.

**P1-3 — `package_pin.speaker_problems` (diff lines 49-62): a named speaker's `people` list is required, but a named speaker's own membership in `people` is not.** `speaker_problems` requires: `name` non-empty str, `people` is a list, `measured` is exactly bool, and for a named (≠"unknown") speaker, `line` and `basis` non-empty strings. It does **not** require that the named speaker appear in `people`, nor that `line` be one of the source's lines. So a hand-built or partially-attacked package could pin `{"name": "Jeff Booth", "line": "anything", "basis": "anything", "people": []}` and pass `to_pin`. In the real flow `check()` guarantees consistency, but `to_pin` is the enforcement point (L-j: the pin's authorisation is what the seal covers), and it accepts records `check()` would never produce. Is that a defect? It's weaker than the law's "code keeps only what the text shows" — the *pin* does not re-verify the evidence against the source. Concrete failure: a stale/hand-edited `package_batch_T.json` (the seal step re-reads it from disk, proof_batch.py:371-374) with a fabricated `speaker.line` seals and pins. Since the package JSON is rewritten after attribution (line 379-380) and the pin is sealed from the in-memory `pk` — wait, no: `seal()` re-reads the file, attributes, writes back, then calls `write_pin(pk, ...)` with the in-memory `pk` — the file and the pin agree. So the exposure is only for the `proof_ledger`/`proof_ly` paths where `res["package"]` came from a fresh build. Downgrade: this is a **P2** in practice; the enforcement gap is real but the flows shown always populate via `check()`. I'll list it as P2.

**P1-4 — `proof_batch.build` (diff lines 338-367): `delivered` spans from `--exclude` packages are merged, but the *kept* package's own spans are not re-checked against the just-built package.** Flow: `build()` passes `delivered = delivered_pins(...) + package_spans(a.exclude)` into `PK.build(..., delivered=delivered)`. Whether overlap is actually dropped depends on `package.usable

## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 54 s finish=stop usage in 19400 / out 414 usd~0.107 (upper-bound price)

**Findings**

No P0 or P1 findings verifiable from the diff.

P2: pipeline/speakers.py:217 (in check())
Concrete failure scenario: model returns `{"people": [{"name":"Jeff Booth","role":"guest","line":"title: Jeff Booth Warning"}], "speaker":{"name":"Jeff Booth","basis":"When I wrote The Price of Tomorrow","why":"x"}}` with a basis that is only in source_lines() and not in clip/around -> check() correctly sets name=unknown (per test at test_speakers.py:690) but the "people" list still carries the title-derived person; a downstream tagger using only "people" could credit a title-only name that the speaker logic itself rejected.

P2: pipeline/package_pin.py:72 (speaker_problems call) + speakers.py:232 (base dict)
Concrete failure scenario: attribute() hits ProviderError before any router.call (e.g. missing env var for a chain member) -> returns dict with measured=False, name=unknown, why=...; speaker_problems accepts it (no "named without line/basis" path taken) and to_pin succeeds, so a completely unmeasured segment reaches the sealed pin (violates "nothing measured is never a pass" but is allowed by the explicit speaker_problems logic shown).

P2: tests/package/proof_batch.py:378 (and equivalent calls at proof_ly.py:484, proof_ledger.py:464)
Concrete failure scenario: package_batch_{tag}.json is written (line 380) *before* SP.attribute_package, then overwritten; a concurrent process or failed run reading the intermediate JSON sees segments without speaker records, yet the test fixtures in test_medley.py:514 and test_angles.py:496 assume the final form is always present.

**Verdict**
SHIP: yes with conditions (must add speaker record before any intermediate JSON write; tighten measured=False handling in speaker_problems to match L-m/L-j; confirm production package flow calls attribute_package before any seal)

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 67 s finish=stop usage in 21977 / out 2042 usd~0.097 (upper-bound price)

# Code Audit: pp-selectid-0007 (Speaker Attribution & Batch Build)

## Findings

### P1: `speaker_problems` validation is incomplete; a named speaker can reach a pin with a fabricated `line`
**File:** `pipeline/package_pin.py` (lines 49–62 in diff)

The `speaker_problems` function validates that a named speaker has a non-empty `line` and `basis` string, but it does **not** verify that the `line` actually exists in the source metadata or that the `basis` is a substring of the transcript. The `check()` function in `speakers.py` performs these verifications, but `to_pin` calls `speaker_problems` directly on the segment data without re-running `check()`.

**Failure Scenario:**
1. A model reply is out of contract or the `check()` function is bypassed (e.g., via a direct JSON injection into the package before `to_pin`).
2. The segment contains: `{"speaker": {"name": "Jeff Booth", "line": "FAKE LINE", "basis": "FAKE BASIS", "people": [], "measured": true}}`.
3. `speaker_problems` sees `name` is not "unknown", `line` is a non-empty string, `basis` is a non-empty string, `people` is a list, `measured` is a bool. It returns `[]` (no problems).
4. `to_pin` proceeds to seal the pin with a speaker name that has no textual evidence in the source or transcript.

**Mitigation in current flow:** In the normal flow, `attribute_package` calls `attribute` which calls `check()`, so the `line` and `basis` are verified before being stored in the segment. However, `to_pin` is a public API that can be called with arbitrary package data. The seal is only as strong as the data passed to it. If any code path constructs a package without going through `attribute_package`, a fake speaker can be sealed.

**Recommendation:** `speaker_problems` should either re-verify the `line` against the source metadata (if available) or the pin should be sealed with a hash of the source metadata so that a mismatch can be detected later. Alternatively, `to_pin` should require that the speaker record was produced by `speakers.attribute` (e.g., by checking a signature or a specific structure that only `check()` produces).

---

### P1: `check()` basis verification uses `_norm` which may allow false positives
**File:** `pipeline/speakers.py` (lines 159–161, 222)

The `_norm` function strips all non-alphanumeric characters (except apostrophes) and lowercases. The basis is checked with `nb in _norm(clip) or nb in _norm(around)`. This is a substring match on normalized text.

**Failure Scenario:**
1. The clip text is: "I wrote a book about deflation."
2. The model proposes a basis: "I wrote a book about deflation" (correct).
3. But also consider: clip text is "I wrote a book. About deflation, I said."
4. The model proposes a basis: "I wrote a book about deflation" (not a contiguous substring in the original, but after normalization, "i wrote a book about deflation" is a substring of "i wrote a book about deflation i said").
5. This is a false positive: the basis is not a verbatim quote from the transcript, but a re-ordered or re-combined phrase.

**Impact:** A speaker can be named based on a basis that is not actually a contiguous quote from the transcript. This violates the law that "the basis is verbatim in the clip or the transcript around it."

**Recommendation:** The basis should be checked as a contiguous substring of the *original* (unnormalized) text, or the normalization should be more conservative (e.g., only case-folding, not stripping punctuation).

---

### P2: `source_lines` may include description lines that are not actually naming people
**File:** `pipeline/speakers.py` (lines 174–185)

The `source_lines` function includes all non-link description lines. The `check()` function then checks if a person's `line` is a substring of one of these lines. However, a description line might mention a person's name in a context that does not name them as a participant (e.g., "This video is dedicated to the memory of John Doe").

**Failure Scenario:**
1. Description line: "In memory of John Doe, who passed away last year."
2. The model proposes a person: `{"name": "John Doe", "line": "In memory of John Doe, who passed away last year."}`.
3. `check()` sees that the line is in the source lines and the name is in the line. It accepts John Doe as a person.
4. John Doe is not a speaker or participant in the video, but is listed in `people` for tagging.

**Impact:** Incorrect people are tagged. This is a lower-severity issue because it does not affect the speaker name, but it affects the `people` list used for tagging.

**Recommendation:** The `check()` function should require that the person's name appears in a context that suggests they are a participant (e.g., "host", "guest", "with", "featuring"). This is difficult to do reliably with text matching, so it may be acceptable to leave as is, but the risk should be documented.

---

### P2: `proof_batch.py`

## CLAUDE'S CYCLE 1 CONSENSUS
# pp-selectid audit of the batch + speakers diff (00:05 ET Nov 13 order): cycle 1 consensus (synthesis by the pp-selectid session, 00:14 ET Nov 13)

**Run.** C1_STEP.diff is 44,699 bytes; the prompt is 68,620 bytes. No reviewer raised a P0.
- grok-4.20-0309-reasoning (xAI): no P0/P1; three P2s. SHIP yes with conditions.
- qwen/qwen3.8-27b (Heimdall, effort none): two P1s and three P2s. SHIP yes with conditions.
- z-ai/glm-5.3-flash (Heimdall, effort none): five P1s (it downgrades one itself) and twelve P2s. SHIP yes with
  conditions.

**One change outside the reviewed diff, made while cycle 1 ran.** The integrator's check_pin_only recomputes seal()
from this worktree's package_pin.py. Since ruling 1 (88397a53) put time_sensitive and source_published_at in the seal
body ALWAYS (None when absent), all 6 earlier pins in tests/package/proof recomputed to a different digest, including
the delivered 37c5b5f5 and 41f29b1f. The speaker edit would have added a third such field.
- Fix: SEALED_LATER = (time_sensitive, source_published_at, speaker). Each enters the body only when the segment
  carries its key, so all 6 earlier pins recompute again (0 of 6 under HEAD 0453f171).
- A new pin always carries all three, because to_pin refuses one without; dropping any of them changes the digest.
- Test: test_every_earlier_pin_still_recomputes_and_a_dropped_later_field_is_caught. Cycle 2 reviews this change.

## Consensus

| # | finding (reviewers) | disposition |
|---|---|---|
| K1 | to_pin checks the speaker record's shape only, so a record check() would never produce can be sealed: a named speaker absent from people, or a line that is not that person's (qwen P1, glm P1-3) | IMPLEMENTED: speaker_problems now requires what check() produces. Every person has a name, a source line and a role in host / guest / other. A named speaker is one of the people, with that person's line and role, plus a non-empty basis. to_pin cannot re-read the source or the transcript; that verification is check()'s, at attribution, and the evidence is sealed for the reader. Test: 4 new must-fail shapes in test_the_pin_refuses_... |
| K2 | an unmeasured speaker record reaches the pin (grok P2, which wants it tightened; glm P2-3, which says it is not a defect: "unknown" claims nothing) | IMPLEMENTED in part. A failed attribution is tried once more with a new seed (seed 8). A second failure stays "unknown" with measured false and its why, and it still pins: it claims no name. The order's rule is "Unknown speaker = say unknown, never guess", and L-m governs gates; this record is not one. STATE marks every unmeasured speaker. Test: test_an_unmeasured_attribution_is_tried_once_more_with_a_new_seed |
| K3 | people and roles are verified only as far as the name in the line (qwen P2: a memorial mention; glm P2-1: the role is never checked) | DOCUMENTED, kept. "people" means named in the source's own lines. Code checks the name is in the line it cites; the role is the verdict's reading of that line

---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_0007/C2_STEP.diff (864 lines)
```
   1 | diff --git a/pipeline/model_providers.json b/pipeline/model_providers.json
   2 | index 1709764a..8c184de0 100644
   3 | --- a/pipeline/model_providers.json
   4 | +++ b/pipeline/model_providers.json
   5 | @@ -212,6 +212,15 @@
   6 |     ],
   7 |     "what": "package.coherence: the blind QUALITY verdict (through-line, ratings); never the writer's vendor"
   8 |    },
   9 | +  "speaker_verdict": {
  10 | +   "chain": [
  11 | +    "xai:grok-4.20-0309-reasoning",
  12 | +    "anthropic:claude-opus-5-5",
  13 | +    "heimdall:deepseek/deepseek-v4.1-flash",
  14 | +    "local:gemma3:27b"
  15 | +   ],
  16 | +   "what": "speakers.attribute: who speaks one pin segment, from the source's own title / channel / description and the transcript around the clip (orchestrator 00:05 ET Nov 13 item 3); code keeps only what the text shows"
  17 | +  },
  18 |    "transcribe": {
  19 |     "chain": [
  20 |      "openai_stt:gpt-4o-transcribe-diarize",
  21 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
  22 | index 598db658..6620b9ab 100644
  23 | --- a/pipeline/package_pin.py
  24 | +++ b/pipeline/package_pin.py
  25 | @@ -63,23 +63,54 @@ def recency_problems(segments):
  26 |      return out
  27 |  
  28 |  
  29 | +SEALED_LATER = ("time_sensitive", "source_published_at",   # ruling 1 (22:40): the render clock checks L-v 3 on these
  30 | +                "speaker")                                 # the 00:05 ET Nov 13 order, item 3
  31 | +
  32 | +
  33 |  def seal(segments, edl_vo, signoff, title, caption, gates):
  34 |      """sha256 over the gated bytes, in a canonical form both sides compute: the segments (video, start, end, the exact
  35 | -    words, the transcript sha, and since ruling 1 (22:40) time_sensitive and source_published_at), the VO the renderer
  36 | -    will speak (intro, bridges with after_clip), the sign-off, the ONE title and caption (law L-t), and the gate
  37 | -    inventory."""
  38 | -    body = {"segments": [{"video_id": s["video_id"], "start": round(float(s["start"]), 3),
  39 | -                          "end": round(float(s["end"]), 3), "text": s["approved_text"],
  40 | -                          "transcript_sha256": s.get("transcript_sha256"),
  41 | -                          "time_sensitive": s.get("time_sensitive"),             # ruling 1 (22:40): the render clock
  42 | -                          "source_published_at": s.get("source_published_at")}   # checks L-v 3 on these
  43 | -                         for s in segments],
  44 | +    words, the transcript sha, and each SEALED_LATER field the segment carries), the VO the renderer will speak (intro,
  45 | +    bridges with after_clip), the sign-off, the ONE title and caption (law L-t), and the gate inventory.
  46 | +    A SEALED_LATER field enters the body only when the segment carries its key. Every pin sealed before that field
  47 | +    existed then recomputes to its own package_sha256: the integrator's check recomputes seals with this module, and
  48 | +    all 6 earlier pins in tests/package/proof failed under an always-present field. A new pin always carries them,
  49 | +    because to_pin refuses one without (recency_problems, speaker_problems), and removing one changes the digest."""
  50 | +    def body_of(s):
  51 | +        b = {"video_id": s["video_id"], "start": round(float(s["start"]), 3), "end": round(float(s["end"]), 3),
  52 | +             "text": s["approved_text"], "transcript_sha256": s.get("transcript_sha256")}
  53 | +        b.update({k: s[k] for k in SEALED_LATER if k in s})
  54 | +        return b
  55 | +    body = {"segments": [body_of(s) for s in segments],
  56 |              "vo": {"intro": edl_vo.get("intro"), "bridges": [{"text": b["text"], "after_clip": b["after_clip"]}
  57 |                                                               for b in edl_vo.get("bridges") or []]},
  58 |              "signoff": signoff, "title": title, "caption": caption, "gates": gates}
  59 |      return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
  60 |  
  61 |  
  62 | +def speaker_problems(segments):
  63 | +    """[why] for segments whose speaker record (speakers.attribute) is missing or malformed: the orchestrator's 00:05 ET
  64 | +    Nov 13 order (item 3) has every pin carry, per segment, the speaker's name (or "unknown", never a guess) with its
  65 | +    evidence. A named speaker needs the source line that names them and the basis that shows they speak the clip."""
  66 | +    out = []
  67 | +    for i, s in enumerate(segments):
  68 | +        sp = s.get("speaker")
  69 | +        if not isinstance(sp, dict) or not isinstance(sp.get("name"), str) or not sp["name"].strip():
  70 | +            out.append(f'segment {i}: no speaker record (a name, or "unknown")')
  71 | +        elif not isinstance(sp.get("people"), list) or type(sp.get("measured")) is not bool:
  72 | +            out.append(f"segment {i}: the speaker record states no people list or no measured flag")
  73 | +        elif not all(isinstance(p, dict) and isinstance(p.get("name"), str) and p["name"].strip() and
  74 | +                     isinstance(p.get("line"), str) and p["line"].strip() and p.get("role") in ("host", "guest", "other")
  75 | +                     for p in sp["people"]):
  76 | +            out.append(f"segment {i}: a person without a name, a source line or a role")
  77 | +        elif sp["name"] != "unknown" and not all(isinstance(sp.get(k), str) and sp[k].strip() for k in ("line", "basis")):
  78 | +            out.append(f"segment {i}: speaker {sp['name']!r} is named without the source line and the basis")
  79 | +        elif sp["name"] != "unknown" and not any(p["name"] == sp["name"] and p["line"] == sp["line"] and
  80 | +                                                 p["role"] == sp.get("role") for p in sp["people"]):
  81 | +            out.append(f"segment {i}: speaker {sp['name']!r} is not one of the people the source names, with that "
  82 | +                       f"person's line and role")             # what speakers.check produces (audit 0007 C1 K1)
  83 | +    return out
  84 | +
  85 | +
  86 |  def gate_problems(gates, required=REQUIRED_GATES):
  87 |      """[why] for an inventory that does not authorise a pin (empty = every required gate exactly PASS, measured live)."""
  88 |      if not isinstance(gates, dict):
  89 | @@ -126,7 +157,7 @@ def line_problems(pk):
  90 |  def to_pin(pk, run_name):
  91 |      problems = gate_problems(pk.get("gates"), required_gates(pk)) + [f"{x}: the gated line differs from the one shipped"
  92 |                                                                       for x in line_problems(pk)] + \
  93 | -        recency_problems(pk.get("segments") or [])
  94 | +        recency_problems(pk.get("segments") or []) + speaker_problems(pk.get("segments") or [])
  95 |      if problems:
  96 |          raise PinRefused("the package's gates do not authorise a pin: " + "; ".join(problems))
  97 |      segs = []
  98 | @@ -135,6 +166,7 @@ def to_pin(pk, run_name):
  99 |                       "start": round(float(s["start"]), 3), "end": round(float(s["end"]), 3),
 100 |                       "approved_text": s["text"], "transcript_sha256": s.get("transcript_sha256"),
 101 |                       "time_sensitive": s.get("time_sensitive"), "source_published_at": s.get("source_published_at"),
 102 | +                     "speaker": s.get("speaker"),                     # 00:05 ET Nov 13 item 3 (sealed)
 103 |                       "time_coords": "youtube", "source": {"kind": "youtube"}})
 104 |      edl_vo = {"intro": pk["vo"]["intro"],
 105 |                "bridges": [{"text": t, "after_clip": a} for t, a in zip(pk["vo"]["bridges"], pk["vo"]["bridges_after_clip"])]}
 106 | diff --git a/pipeline/speakers.py b/pipeline/speakers.py
 107 | new file mode 100644
 108 | index 00000000..940930cd
 109 | --- /dev/null
 110 | +++ b/pipeline/speakers.py
 111 | @@ -0,0 +1,186 @@
 112 | +#!/usr/bin/env python3
 113 | +"""pipeline/speakers.py: ORCHESTRATOR 00:05 ET Nov 13, item 3. Every pin segment names its SPEAKER where the source
 114 | +names the person, with the evidence: PBX tags the right people, and law L-v 1 needs it. An unknown speaker is
 115 | +"unknown", never a guess.
 116 | +
 117 | +Evidence is text, and code checks it:
 118 | +- source_lines(meta): the source's own lines, from the store's meta.json (yt-dlp, at acquisition): "title: ...",
 119 | +  "channel: ...", then each description line that is not a bare link.
 120 | +- context(src, k0, k1): the clip's own words in the word record, with CONTEXT_BEFORE sentences before it and
 121 | +  CONTEXT_AFTER after it.
 122 | +- One verdict (role speaker_verdict) proposes, as JSON, two things: the people the source's lines name, each with the
 123 | +  line that names them; and who speaks THIS clip, with a basis quoted from the transcript.
 124 | +- check() keeps only what the text shows:
 125 | +  - a person stands only if their line is part of one of the source's lines and holds their name; the person
 126 | +    carries that WHOLE source line as evidence;
 127 | +  - the speaker is named only if they are one of those people AND the basis (>= BASIS_MIN_WORDS words) is verbatim in
 128 | +    the clip or the transcript around it.
 129 | +  A source line alone never names a clip's speaker: a title that names a guest does not show who speaks a given
 130 | +  clip. Otherwise the speaker is "unknown", with why, and every person the source names is still listed (people) for
 131 | +  tagging.
 132 | +-> the segment's "speaker": {"name", "role", "line", "basis", "why", "people", "measured", "backend", "replayed"}.
 133 | +"people" means named in the source's own lines. Code verifies that the name is in the line it cites; the role
 134 | +(host / guest / other) is the verdict's reading of that line, shown beside it for the reader (audit 0007 C1 K3: qwen,
 135 | +glm). A call that fails is retried once with a new seed; a second failure stays "unknown" with measured false, which
 136 | +claims no name (audit 0007 C1 K2).
 137 | +"""
 138 | +import json
 139 | +import os
 140 | +import re
 141 | +
 142 | +import eligibility as E
 143 | +
 144 | +CONTEXT_BEFORE, CONTEXT_AFTER = 8, 2      # sentences of the word record around the clip, for who speaks it
 145 | +BASIS_MIN_WORDS = 3                       # a basis is a phrase, never one word
 146 | +MAX_DESCRIPTION_LINES = 60
 147 | +ROLES = ("host", "guest", "other")
 148 | +UNKNOWN = "unknown"
 149 | +STORE = os.path.join(os.environ.get("PP_MAIN_TREE", "/home/ultron/protocol_pulse"), "data", "editorial")
 150 | +
 151 | +PROMPT = """You identify who is SPEAKING in one clip of a Bitcoin video, so the people in it can be credited and tagged.
 152 | +
 153 | +Tone: factual. Name a person only when the text below shows it. "unknown" is a correct, expected answer, and a wrong
 154 | +name is worse than "unknown". Never infer from the topic, the style or the title alone.
 155 | +
 156 | +THE SOURCE'S OWN LINES (its title, its channel and its description, one per line):
 157 | +{lines}
 158 | +
 159 | +THE TRANSCRIPT AROUND THE CLIP (the clip is between <clip> and </clip>; speaker turns are not marked):
 160 | +{context}
 161 | +
 162 | +Do this:
 163 | +1. List every person these source lines name who appears in the video (host, guest or other), each with the ONE
 164 | +   source line that names them, copied character for character.
 165 | +2. Decide who speaks the words inside <clip>. Name a person only if the TRANSCRIPT shows it, for example:
 166 | +   - the transcript just before the clip addresses them by name, and the clip answers;
 167 | +   - the clip speaks of their own work, role or company in the first person, and a source line ties that to them.
 168 | +   Copy the exact words from the clip or the transcript around it that show it (the basis, at least three words).
 169 | +   A title or description that names a guest does NOT show who speaks a given clip. If nothing in the transcript
 170 | +   shows it, the speaker is "unknown", and "why" says what is missing.
 171 | +
 172 | +Example: an interview whose title names a guest, where the clip and the transcript around it hold no name, no
 173 | +first-person tie and no address -> "speaker": {{"name": "unknown", "basis": "", "why": "both the host and the guest
 174 | +speak in this episode, and nothing in or around the clip shows which one this is"}}
 175 | +
 176 | +Return ONLY this JSON object:
 177 | +{{"people": [{{"name": "...", "role": "host|guest|other", "line": "..."}}],
 178 | + "speaker": {{"name": "<one of the people, or unknown>", "basis": "<exact words from the transcript, or empty>",
 179 | + "why": "..."}}}}
 180 | +
 181 | +Remember: copy every line and the basis exactly; "unknown" whenever the transcript does not show who speaks."""
 182 | +
 183 | +
 184 | +def _norm(s):
 185 | +    """Case, punctuation and spacing aside: the text a quote must match."""
 186 | +    return " ".join(re.sub(r"[^\w']+", " ", str(s or "").casefold()).split())
 187 | +
 188 | +
 189 | +def store_meta(video_id, store=STORE):
 190 | +    """The store's meta.json for a video (title, channel, description), or {} when it is not there."""
 191 | +    try:
 192 | +        with open(os.path.join(store, "transcripts", video_id, "meta.json")) as f:
 193 | +            meta = json.load(f)
 194 | +        return meta if isinstance(meta, dict) else {}
 195 | +    except (OSError, ValueError):
 196 | +        return {}
 197 | +
 198 | +
 199 | +def source_lines(meta):
 200 | +    out = []
 201 | +    if isinstance(meta.get("exact_title"), str) and meta["exact_title"].strip():
 202 | +        out.append(f"title: {meta['exact_title'].strip()}")
 203 | +    if isinstance(meta.get("channel_name"), str) and meta["channel_name"].strip():
 204 | +        out.append(f"channel: {meta['channel_name'].strip()}")
 205 | +    desc = meta.get("description") if isinstance(meta.get("description"), str) else ""
 206 | +    for line in desc.split("\n"):
 207 | +        line = line.strip()
 208 | +        if line and not re.fullmatch(r"\S*https?://\S*", line) and len(out) < MAX_DESCRIPTION_LINES + 2:
 209 | +            out.append(line)
 210 | +    return out
 211 | +
 212 | +
 213 | +def context(src, k0, k1, before=CONTEXT_BEFORE, after=CONTEXT_AFTER):
 214 | +    """(the sentences before, the clip, the sentences after) in the word record's own words."""
 215 | +    sents = src.sentences
 216 | +    a, b = max(0, k0 - before), min(len(sents) - 1, k1 + after)
 217 | +
 218 | +    def say(i, j):
 219 | +        return E.spoken(src.tokens[sents[i][0]:sents[j][1] + 1]) if i <= j else ""
 220 | +    return say(a, k0 - 1), say(k0, k1), say(k1 + 1, b)
 221 | +
 222 | +
 223 | +def _json(text):
 224 | +    """The reply's JSON object, a ```json fence aside (audit 0007 C1, glm P1-2)."""
 225 | +    t = str(text or "").strip()
 226 | +    if t.startswith("```"):
 227 | +        t = t.split("\n", 1)[1] if "\n" in t else ""
 228 | +        t = t[:t.rfind("```")] if "```" in t else t
 229 | +    return json.loads(t.strip())
 230 | +
 231 | +
 232 | +def check(v, lines, clip, around):
 233 | +    """The verdict, kept only where the text shows it (never the model's word) -> the speaker record (no backend)."""
 234 | +    if not isinstance(v, dict) or not isinstance(v.get("people"), list) or not isinstance(v.get("speaker"), dict):
 235 | +        raise ValueError("speaker verdict out of contract")
 236 | +    nlines = [_norm(x) for x in lines]
 237 | +    people = []
 238 | +    for p in v["people"]:
 239 | +        if not isinstance(p, dict) or not isinstance(p.get("name"), str) or not isinstance(p.get("line"), str):
 240 | +            continue
 241 | +        nn, nl = _norm(p["name"]), _norm(p["line"])
 242 | +        whole = next((lines[i] for i, x in enumerate(nlines) if nl and nl in x), None)
 243 | +        if not nn or whole is None or nn not in _norm(whole) or any(_norm(q["name"]) == nn for q in people):
 244 | +            continue                             # not a source line, or the line does not name them
 245 | +        people.append({"name": p["name"].strip(), "role": p.get("role") if p.get("role") in ROLES else "other",
 246 | +                       "line": whole})
 247 | +    sp = v["speaker"]
 248 | +    name, basis = sp.get("name"), sp.get("basis")
 249 | +    rec = {"name": UNKNOWN, "role": None, "line": None, "basis": None,
 250 | +           "why": str(sp.get("why") or "")[:300], "people": people}
 251 | +    if isinstance(name, str) and _norm(name) not in ("", UNKNOWN):
 252 | +        match = next((p for p in people if _norm(p["name"]) == _norm(name)), None)
 253 | +        nb = _norm(basis)
 254 | +        if match is None:
 255 | +            rec["why"] = f"{name.strip()!r} is not a person the source's lines name"
 256 | +        elif len(nb.split()) < BASIS_MIN_WORDS or not (nb in _norm(clip) or nb in _norm(around)):
 257 | +            rec["why"] = (f"the basis for {name.strip()!r} is not {BASIS_MIN_WORDS}+ words found in the clip or the "
 258 | +                          f"transcript around it")
 259 | +        else:
 260 | +            rec.update(name=match["name"], role=match["role"], line=match["line"], basis=str(basis).strip())
 261 | +    return rec
 262 | +
 263 | +
 264 | +def attribute(router, seg, src, meta, seed=7):
 265 | +    """One segment's speaker record. A call that fails, or a reply out of contract, is "unknown" with measured false."""
 266 | +    import providers as P
 267 | +    base = {"name": UNKNOWN, "role": None, "line": None, "basis": None, "people": [], "measured": False}
 268 | +    if src is None or "k0" not in seg or "k1" not in seg:
 269 | +        return dict(base, why="no word record for the clip's context")
 270 | +    lines = source_lines(meta or {})
 271 | +    if not lines:
 272 | +        return dict(base, why="the source's title, channel and description are not in the store", measured=True)
 273 | +    before, clip, after = context(src, int(seg["k0"]), int(seg["k1"]))
 274 | +    prompt = PROMPT.format(lines="\n".join(lines), context=f"{before}\n<clip>{clip}</clip>\n{after}".strip())
 275 | +    r = None
 276 | +    try:
 277 | +        r = router.call("speaker_verdict", prompt, 900, seed)
 278 | +        rec = check(_json(r.text), lines, clip, f"{before} {after}")
 279 | +    except Exception as e:                      # any failure claims no name (audit 0007 C1, glm P1-1): Router.call
 280 | +        if r is not None and not isinstance(e, (P.ProviderError, P.SpendLimit)):    # re-raises a back-end's own
 281 | +            router.reject(r)                                                         # error
 282 | +        return dict(base, why=f"not measured: {type(e).__name__}: {str(e)[:160]}")
 283 | +    return dict(rec, measured=True, backend=r.backend, replayed=bool(getattr(r, "replayed", False)))
 284 | +
 285 | +
 286 | +def attribute_package(router, pk, sources, meta_for=store_meta, log=print):
 287 | +    """Every segment of a package gets its speaker record, in place (before the pin is sealed)."""
 288 | +    for i, s in enumerate(pk["segments"]):
 289 | +        src, meta = sources.get(s["video_id"]), meta_for(s["video_id"])
 290 | +        sp = attribute(router, s, src, meta)
 291 | +        if not sp["measured"] and sp["why"].startswith("not measured"):      # once more, a new sample (C1 K2)
 292 | +            sp = attribute(router, s, src, meta, seed=8)
 293 | +        s["speaker"] = sp
 294 | +        log(f"    speaker {i}: {s['video_id']} -> {sp['name']}"
 295 | +            + (f" ({sp['role']}; basis {sp['basis']!r})" if sp["name"] != UNKNOWN else f" ({sp.get('why')})")
 296 | +            + f"; the source names {[p['name'] for p in sp['people']]}")
 297 | +    return pk
 298 | diff --git a/tests/package/proof_batch.py b/tests/package/proof_batch.py
 299 | new file mode 100644
 300 | index 00000000..5c2ca35c
 301 | --- /dev/null
 302 | +++ b/tests/package/proof_batch.py
 303 | @@ -0,0 +1,181 @@
 304 | +#!/usr/bin/env python3
 305 | +"""ORCHESTRATOR 00:05 ET Nov 13 (PBX on the L-y medley: "new batch!"): up to THREE novel L-y medleys, ranked, sealed.
 306 | +
 307 | +Why rebuilds: the four L-y packages of the 20:30 re-run (fresh_20261112_001448, fresh_20261111_213954,
 308 | +fresh_20261111_192645, fresh_20261111_190259) were built with delivered=() and every one reuses delivered moments.
 309 | +Each opens on the hook wdk5JZ9hPzs 3218.1-3221.6 (in 37c5b5f5 and 41f29b1f) and carries c1JGheQBPH4 2403.2-2422.1 (in
 310 | +41f29b1f); 001448 is 41f29b1f clip for clip. The order's item 2 ("no moment reused") therefore rebuilds every one from
 311 | +the remaining moments.
 312 | +
 313 | +build RUN: one universe's medley, built by the packager as it stands (house style in the writer's prompt and in the
 314 | +STYLE lint, recency facts per segment, ruling 5's budget and deadlines):
 315 | +- "now" is the RENDER clock (ruling 1): step A, L-v 3 and currency are judged against tonight.
 316 | +- Novelty: every clip span of --delivered (the delivered pins) and of --exclude (the batch's kept packages) goes to
 317 | +  package.usable as delivered, which drops any moment that overlaps one in the same video (L-p).
 318 | +- --avoid-videos drops every moment of those source videos first ("no source video used twice across the batch if
 319 | +  avoidable"). When such a build finds no package, a second build without the avoidance is the order's "if
 320 | +  avoidable"; it is a separate run with its own tag.
 321 | +- The legs and meters are proof_ly's. Spend goes to the batch's own ledger, SPEND_BATCH.json (estimate ceiling
 322 | +  BATCH_LIMIT_USD). The order's budget is $6 vendor-reported for the batch.
 323 | +Writes tests/package/proof/<RUN>/package_batch_<tag>.json (the package, or why none) and package_batch_<tag>.log.
 324 | +
 325 | +seal RUN --tag T: the kept package's speakers (speakers.attribute_package: the source's own lines and the transcript
 326 | +around each clip; "unknown" unless the text shows it), then the pin through package_pin.to_pin (every gate, recency
 327 | +and speaker check) -> tests/package/proof/<RUN>/MOMENTS_PIN_BATCH_<T>.json; the speakers are written back into
 328 | +package_batch_<T>.json.
 329 | +
 330 | +Usage: python3 tests/package/proof_batch.py build RUN --tag T --delivered PIN ... [--exclude PKG_JSON ...]
 331 | +                                                   [--avoid-videos VID ...]
 332 | +       python3 tests/package/proof_batch.py seal RUN --tag T
 333 | +"""
 334 | +import argparse
 335 | +import json
 336 | +import os
 337 | +import sys
 338 | +import time
 339 | +from datetime import datetime, timezone
 340 | +
 341 | +HERE = os.path.dirname(os.path.abspath(__file__))
 342 | +REPO = os.path.dirname(os.path.dirname(HERE))
 343 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
 344 | +sys.path.insert(0, HERE)
 345 | +import eligibility as E  # noqa: E402
 346 | +import moments as M  # noqa: E402
 347 | +import package as PK  # noqa: E402
 348 | +import package_pin  # noqa: E402
 349 | +import proof_ledger as PLG  # noqa: E402
 350 | +import proof_ly as PL  # noqa: E402
 351 | +import providers as P  # noqa: E402
 352 | +import speakers as SP  # noqa: E402
 353 | +
 354 | +OUT = PL.OUT
 355 | +SPEND = os.path.join(OUT, "SPEND_BATCH.json")
 356 | +BATCH_LIMIT_USD = 30.0     # the price-table estimate ceiling for the batch's own ledger (an upper bound; the
 357 | +                           # reported cost ran about 1/8 of it tonight); ruling 5's per-package $1.50 reported and
 358 | +                           # $5 estimate still stop each build; the order's batch budget is $6 vendor-reported
 359 | +
 360 | +
 361 | +def package_spans(paths):
 362 | +    """Every clip span of the batch's kept packages (package_batch_*.json) -> [{video_id, start, end, pin}]."""
 363 | +    out = []
 364 | +    for p in paths:
 365 | +        with open(p) as f:
 366 | +            res = json.load(f)
 367 | +        pk = res.get("package")
 368 | +        if not pk:
 369 | +            raise ValueError(f"{p}: holds no package")
 370 | +        out += [{"video_id": s["video_id"], "start": float(s["start"]), "end": float(s["end"]),
 371 | +                 "pin": f"batch:{os.path.basename(os.path.dirname(p))}"} for s in pk["segments"]]
 372 | +    return out
 373 | +
 374 | +
 375 | +def build(run, tag, delivered, avoid, router, own, used, say, work_dir):
 376 | +    rec_m = json.load(open(os.path.join(PL.PM.OUT, run, "moments.json")))
 377 | +    words, captions, ctx_u, saved = PL.PM.universe_sources(run)
 378 | +    sources = {s.video_id: s for s in words}
 379 | +    now = datetime.now(timezone.utc)
 380 | +    ctx = E.Context(now, PL.PM.PS.REG, ledger=PL.PM.PS.ledger_entries())
 381 | +    moments = [m for m in rec_m["moments"] if m["video_id"] not in avoid]
 382 | +    say(f"  {len(rec_m['moments'])} moments, {len(rec_m['moments']) - len(moments)} on avoided videos out; "
 383 | +        f"{len(delivered)} delivered or kept spans out; now (render clock) {now.isoformat(timespec='seconds')}")
 384 | +    e0, b0 = own["est"], own["best"]
 385 | +    u0 = dict(used)
 386 | +    t0 = time.time()
 387 | +    res = PK.build(router, moments, sources, ctx, delivered=delivered, optout=M.optout_ids(), log=say,
 388 | +                   work_dir=work_dir, store=os.path.join(OUT, run, "step_a_now.json"),
 389 | +                   spend=lambda: (own["est"], own["best"]))
 390 | +    res.update(run=run, tag=tag, seconds=round(time.time() - t0, 1), usd_estimate=round(own["est"] - e0, 4),
 391 | +               usd_best_known=round(own["best"] - b0, 4), code=PL.code_sha(), chains=router.chains,
 392 | +               at=time.strftime("%Y-%m-%d %H:%M:%S %Z"), as_of=now.isoformat(), avoid_videos=sorted(avoid),
 393 | +               delivered_spans=delivered,
 394 | +               full={k: round(used[k] - u0[k], 4) for k in ("est", "best", "model_s", "calls")})
 395 | +    if res["package"]:
 396 | +        res["package"]["usd_best_known"] = res["usd_best_known"]
 397 | +        say(f"PACKAGE ({res['seconds']} s, ${res['usd_estimate']} estimate, ${res['usd_best_known']} best known): "
 398 | +            + "; ".join(f"{s['video_id']} {float(s['start']):.1f}-{float(s['end']):.1f}"
 399 | +                        for s in res["package"]["segments"]))
 400 | +    else:
 401 | +        say(f"no package ({res.get('why_none')}); usable {res['usable']}, cleared {res['prescreen'].get('cleared')}")
 402 | +    with open(os.path.join(OUT, run, f"package_batch_{tag}.json"), "w") as f:
 403 | +        json.dump(res, f, indent=1, default=str)
 404 | +    return res
 405 | +
 406 | +
 407 | +def seal(run, tag, router, say):
 408 | +    path = os.path.join(OUT, run, f"package_batch_{tag}.json")
 409 | +    with open(path) as f:
 410 | +        res = json.load(f)
 411 | +    pk = res.get("package")
 412 | +    if not pk:
 413 | +        raise ValueError(f"{path}: holds no package")
 414 | +    words, captions, ctx_u, saved = PL.PM.universe_sources(run)
 415 | +    SP.attribute_package(router, pk, {s.video_id: s for s in words}, log=say)
 416 | +    with open(path, "w") as f:
 417 | +        json.dump(res, f, indent=1, default=str)
 418 | +    out, pin = package_pin.write_pin(pk, f"batch_{tag}_{run}", os.path.join(OUT, run),
 419 | +                                     name=f"MOMENTS_PIN_BATCH_{tag.upper()}.json")
 420 | +    say(f"PIN {os.path.relpath(out, REPO)} {pin['moments_package']['package_sha256']}")
 421 | +    return out, pin
 422 | +
 423 | +
 424 | +def main(argv=None):
 425 | +    ap = argparse.ArgumentParser()
 426 | +    sub = ap.add_subparsers(dest="cmd", required=True)
 427 | +    b = sub.add_parser("build")
 428 | +    b.add_argument("run")
 429 | +    b.add_argument("--tag", required=True)
 430 | +    b.add_argument("--delivered", nargs="+", required=True, metavar="PIN")
 431 | +    b.add_argument("--exclude", nargs="*", default=[], metavar="PKG_JSON", help="the batch's kept packages")
 432 | +    b.add_argument("--avoid-videos", nargs="*", default=[], metavar="VID")
 433 | +    b.add_argument("--work-dir", default=os.path.join(PL.SCRATCH, "lv2"))
 434 | +    sl = sub.add_parser("seal")
 435 | +    sl.add_argument("run")
 436 | +    sl.add_argument("--tag", required=True)
 437 | +    a = ap.parse_args(argv)
 438 | +    if a.cmd == "seal":
 439 | +        router = P.Router(env_path=PL.PM.PS.ENV, record_dir=PL.REPLIES, spend_path=SPEND,
 440 | +                          limit_usd=BATCH_LIMIT_USD, chains=PL.chains())
 441 | +        own = PL.meter(router)
 442 | +        with open(os.path.join(OUT, a.run, f"package_batch_{a.tag}.log"), "a") as logf:
 443 | +            def say(s):
 444 | +                print(f"[{a.run}:{a.tag}] {s}", flush=True)
 445 | +                logf.write(s + "\n")
 446 | +                logf.flush()
 447 | +            say(f"=== {time.strftime('%H:%M:%S %Z')} SEAL {a.tag}: speakers, then the pin")
 448 | +            try:
 449 | +                seal(a.run, a.tag, router, say)
 450 | +            except (package_pin.PinRefused, ValueError, OSError, KeyError, TypeError) as e:   # glm C1 P1-5
 451 | +                say(f"PIN REFUSED: {type(e).__name__}: {e}")
 452 | +                return 4
 453 | +            finally:
 454 | +                say(f"  speakers: ${own['est']:.4f} estimate, ${own['best']:.4f} best known")
 455 | +        return 0
 456 | +    try:                                                # read before anything is written (fail closed)
 457 | +        delivered, _, pins = PLG.delivered_pins(a.delivered)
 458 | +        delivered = delivered + package_spans(a.exclude)
 459 | +        if not os.path.exists(os.path.join(PL.PM.OUT, a.run, "moments.json")):
 460 | +            raise ValueError(f"{a.run}: no saved universe")
 461 | +    except (OSError, ValueError, KeyError, TypeError) as e:
 462 | +        print(f"REFUSED: {type(e).__name__}: {e}", file=sys.stderr)
 463 | +        return 2
 464 | +    os.makedirs(a.work_dir, exist_ok=True)
 465 | +    router = P.Router(env_path=PL.PM.PS.ENV, record_dir=PL.REPLIES, spend_path=SPEND, limit_usd=BATCH_LIMIT_USD,
 466 | +                      chains=PL.chains())
 467 | +    own, used = PL.meter(router), PL.reply_meter(router)
 468 | +    with open(os.path.join(OUT, a.run, f"package_batch_{a.tag}.log"), "a") as logf:
 469 | +        def say(s):
 470 | +            print(f"[{a.run}:{a.tag}] {s}", flush=True)
 471 | +            logf.write(s + "\n")
 472 | +            logf.flush()
 473 | +        say(f"=== {time.strftime('%H:%M:%S %Z')} BATCH medley build {a.tag}, code {PL.code_sha()}, delivered "
 474 | +            f"{[p['story_id'] for p in pins]}, kept {a.exclude}, avoid {sorted(a.avoid_videos)}")
 475 | +        try:
 476 | +            build(a.run, a.tag, delivered, set(a.avoid_videos), router, own, used, say, a.work_dir)
 477 | +        except P.SpendLimit as e:
 478 | +            say(f"STOPPED: {e}")
 479 | +            return 3
 480 | +    return 0
 481 | +
 482 | +
 483 | +if __name__ == "__main__":
 484 | +    sys.exit(main())
 485 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
 486 | index e574a0ad..5d344003 100644
 487 | --- a/tests/package/proof_ledger.py
 488 | +++ b/tests/package/proof_ledger.py
 489 | @@ -43,6 +43,7 @@ import package_pin  # noqa: E402
 490 |  import proof_ly as PL  # noqa: E402
 491 |  import proof_saved_runs as PS  # noqa: E402
 492 |  import providers as P  # noqa: E402
 493 | +import speakers as SP  # noqa: E402
 494 |  
 495 |  def delivered_pins(paths):
 496 |      """The pins already delivered -> (every clip span {video_id, start, end, pin} for package.usable's overlap check,
 497 | @@ -123,6 +124,7 @@ def main(argv=None):
 498 |                 full={k: round(v, 4) for k, v in used.items()}, code=PL.code_sha(), now=now.isoformat(),
 499 |                 since=since.isoformat(), delivered_pins=pins, chains=router.chains, inputs=inputs)
 500 |      if res["package"]:
 501 | +        SP.attribute_package(router, res["package"], sources, log=say)     # 00:05 ET Nov 13 item 3: sealed in the pin
 502 |          try:
 503 |              path, pin = package_pin.write_pin(res["package"], f"ledger_{now.strftime('%Y%m%d_%H%M%S')}", out_dir,
 504 |                                                name="MOMENTS_PIN_LEDGER.json")
 505 | diff --git a/tests/package/proof_ly.py b/tests/package/proof_ly.py
 506 | index 40779901..75193f64 100644
 507 | --- a/tests/package/proof_ly.py
 508 | +++ b/tests/package/proof_ly.py
 509 | @@ -41,6 +41,7 @@ import package as PK  # noqa: E402
 510 |  import package_pin  # noqa: E402
 511 |  import proof_moments as PM  # noqa: E402
 512 |  import providers as P  # noqa: E402
 513 | +import speakers as SP  # noqa: E402
 514 |  
 515 |  REPLIES = os.path.join(HERE, "fixtures", "replies")
 516 |  OUT = os.path.join(HERE, "proof")
 517 | @@ -159,6 +160,7 @@ def run_one(run, router, work_dir, log, own, used=None, as_of_now=False):
 518 |      if res["package"]:
 519 |          pk = res["package"]
 520 |          pk["usd_best_known"] = res["usd_best_known"]
 521 | +        SP.attribute_package(router, pk, sources, log=log)                # 00:05 ET Nov 13 item 3: sealed in the pin
 522 |          try:
 523 |              path, pin = package_pin.write_pin(pk, run, os.path.join(OUT, run), name=f"MOMENTS_PIN_LY{suffix.upper()}.json")
 524 |              res["pin"] = {"path": os.path.relpath(path, REPO), "story_id": pin["story_id"],
 525 | diff --git a/tests/package/test_angles.py b/tests/package/test_angles.py
 526 | index 34762dcd..60a9f85a 100644
 527 | --- a/tests/package/test_angles.py
 528 | +++ b/tests/package/test_angles.py
 529 | @@ -129,6 +129,8 @@ class TestPinAndTruth(unittest.TestCase):
 530 |                            {"slot": "title", "text": "T"}, {"slot": "caption", "text": "C"}],
 531 |                  "segments": [{"video_id": v, "channel": "ch", "start": 1.0, "end": 9.0, "text": f"Bitcoin is {v}.",
 532 |                                "transcript_sha256": "t", "url_30s_before": "u", "time_sensitive": False,
 533 | +                              "speaker": {"name": "unknown", "role": None, "line": None, "basis": None, "why": "t",
 534 | +                                          "people": [], "measured": True},
 535 |                                "source_published_at": "2026-11-12T01:00:00Z"} for v in ("aaaaaaaaaaa", "bbbbbbbbbbb")]}
 536 |  
 537 |      def test_the_pin_refuses_anything_not_exactly_pass_and_is_sealed(self):
 538 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 539 | index 68b37217..6b68f88e 100644
 540 | --- a/tests/package/test_medley.py
 541 | +++ b/tests/package/test_medley.py
 542 | @@ -58,6 +58,15 @@ def medley_pk(n=3, bridge=None, after=None, flagged=(), measured=True, chans=Non
 543 |              "supply_exception": supply}
 544 |  
 545 |  
 546 | +
 547 | +def spk(pk):
 548 | +    """speakers.attribute's record on every segment, as the real flow attaches it before the pin is sealed (the
 549 | +    00:05 ET Nov 13 order, item 3): an unknown speaker, measured, no person named."""
 550 | +    for s in pk.get("segments") or []:
 551 | +        s.setdefault("speaker", {"name": "unknown", "role": None, "line": None, "basis": None, "why": "test",
 552 | +                                 "people": [], "measured": True})
 553 | +    return pk
 554 | +
 555 |  class TestMedleyArithmetic(unittest.TestCase):
 556 |      def test_the_medley_seconds_let_one_takeaway_land_60_to_70(self):
 557 |          lo, hi = PK.medley_content_range()
 558 | @@ -361,7 +370,7 @@ class TestMedleyPackageAndPin(unittest.TestCase):
 559 |          pk = self.build()
 560 |          self.assertEqual(package_pin.required_gates(pk)[-3:], ("medley", "ly_shape", "house_style"))
 561 |          pk["gates"] = self.gates(pk)
 562 | -        pin = package_pin.to_pin(pk, "test")
 563 | +        pin = package_pin.to_pin(spk(pk), "test")
 564 |          mp = pin["moments_package"]
 565 |          self.assertEqual(mp["edl_vo"], {"intro": None, "bridges": [{"text": pk["vo"]["bridges"][0], "after_clip": 2}]})
 566 |          self.assertEqual(mp["vo_jobs"], {"takeaway": "takeaway"})
 567 | @@ -370,16 +379,16 @@ class TestMedleyPackageAndPin(unittest.TestCase):
 568 |              g = self.gates(pk)
 569 |              g.pop(missing)
 570 |              with self.assertRaises(package_pin.PinRefused):
 571 | -                package_pin.to_pin(dict(pk, gates=g), "test")
 572 | +                package_pin.to_pin(spk(dict(pk, gates=g)), "test")
 573 |          with self.assertRaises(package_pin.PinRefused):
 574 | -            package_pin.to_pin(dict(pk, gates=self.gates(pk, ly_shape={"status": "FAIL", "replayed": False})), "test")
 575 | +            package_pin.to_pin(spk(dict(pk, gates=self.gates(pk, ly_shape={"status": "FAIL", "replayed": False}))), "test")
 576 |  
 577 |      def test_the_gated_takeaway_must_be_the_spoken_one(self):
 578 |          pk = self.build()
 579 |          pk["gates"] = self.gates(pk)
 580 |          pk["vo"] = dict(pk["vo"], bridges=["A different closing line."])
 581 |          with self.assertRaises(package_pin.PinRefused) as cm:
 582 | -            package_pin.to_pin(pk, "test")
 583 | +            package_pin.to_pin(spk(pk), "test")
 584 |          self.assertIn("bridges", str(cm.exception))
 585 |  
 586 |      def test_the_old_shape_keeps_its_slots(self):
 587 | @@ -396,7 +405,7 @@ class TestMedleyPackageAndPin(unittest.TestCase):
 588 |          b = {"text": "Next, on keys.", "cites": ["x"], "why": "no referent"}
 589 |          pk0 = self.build(bridge=b, k=0)                   # audit 2030 C1 (grok P2-2): the intro slot pins as intro
 590 |          pk0["gates"] = self.gates(pk0)
 591 | -        mp = package_pin.to_pin(pk0, "test")["moments_package"]
 592 | +        mp = package_pin.to_pin(spk(pk0), "test")["moments_package"]
 593 |          self.assertEqual(mp["edl_vo"], {"intro": "Next, on keys.",
 594 |                                          "bridges": [{"text": pk0["vo"]["bridges"][0], "after_clip": 2}]})
 595 |          self.assertEqual(mp["vo_jobs"], {"intro": "connection", "takeaway": "takeaway"})
 596 | @@ -530,7 +539,7 @@ class TestBuildLoop(unittest.TestCase):
 597 |          self.assertEqual(pk["bridge"]["confirmed_by"]["join"], "clip_01 -> clip_02")
 598 |          self.assertEqual(pk["vo"]["bridges_after_clip"], [1, 2])
 599 |          self.assertTrue(all(g["status"] == "PASS" for g in pk["gates"].values()), pk["gates"])
 600 | -        package_pin.to_pin(pk, "test")                    # every required row exactly PASS: the pin is allowed
 601 | +        package_pin.to_pin(spk(pk), "test")                    # every required row exactly PASS: the pin is allowed
 602 |  
 603 |      def test_a_clip_the_second_recogniser_cannot_cut_is_never_offered_to_the_angles(self):
 604 |          rig = Rig(self.MS, ["h", "x", "z"], [(True, [], None, Rig.LINE)], [None], uncuttable={"y"})
 605 | @@ -543,7 +552,7 @@ class TestBuildLoop(unittest.TestCase):
 606 |          self.assertEqual(rig.medley_calls, [["h", "x", "z"]])
 607 |          pk = out["package"]
 608 |          self.assertEqual(pk["gates"]["cuttable"]["status"], "PASS")
 609 | -        package_pin.to_pin(pk, "test")                    # build() returns only a package its pin accepts
 610 | +        package_pin.to_pin(spk(pk), "test")                    # build() returns only a package its pin accepts
 611 |  
 612 |      def test_an_excluded_moment_stays_out_of_every_later_angle(self):
 613 |          ms = self.MS + [pm("w", "E", 14.0)]
 614 | @@ -572,7 +581,7 @@ class TestBuildLoop(unittest.TestCase):
 615 |          self.assertAlmostEqual(pk["runtime_s_estimate"], 52.0 + PK.FINAL_TAIL_S, places=2)
 616 |          self.assertTrue(all(g["status"] == "PASS" for g in pk["gates"].values()), pk["gates"])
 617 |          self.assertIn("no VO line", pk["checks"]["coherence"]["note"])
 618 | -        mp = package_pin.to_pin(pk, "test")["moments_package"]
 619 | +        mp = package_pin.to_pin(spk(pk), "test")["moments_package"]
 620 |          self.assertEqual(mp["edl_vo"], {"intro": None, "bridges": []})
 621 |  
 622 |      def test_no_voice_never_ships_a_join_the_blind_check_flagged(self):
 623 | @@ -667,7 +676,7 @@ class TestNoVoiceRealGates(unittest.TestCase):
 624 |          pk["gates"] = PK.inventory(fid, dup, rt_ok, r4_res, cx, a_lab, exc, tru, True, coh, medley=(True, med),
 625 |                                     shape=PK.ly_shape(pk), style=HS.lint_lines(pk["lines"]))
 626 |          self.assertEqual(package_pin.gate_problems(pk["gates"], package_pin.required_gates(pk)), [])
 627 | -        mp = package_pin.to_pin(pk, "test")["moments_package"]
 628 | +        mp = package_pin.to_pin(spk(pk), "test")["moments_package"]
 629 |          self.assertEqual((mp["edl_vo"], mp["no_voice"]["added_clip"]), ({"intro": None, "bridges": []}, None))
 630 |  
 631 |      def test_a_published_time_without_an_offset_fails_before_any_paid_verdict(self):
 632 | diff --git a/tests/package/test_speakers.py b/tests/package/test_speakers.py
 633 | new file mode 100644
 634 | index 00000000..9c50f6b6
 635 | --- /dev/null
 636 | +++ b/tests/package/test_speakers.py
 637 | @@ -0,0 +1,226 @@
 638 | +#!/usr/bin/env python3
 639 | +"""pipeline/speakers.py (ORCHESTRATOR 00:05 ET Nov 13, item 3): every pin segment names its speaker where the source
 640 | +names the person, with the evidence; an unknown speaker is "unknown", never a guess. Offline: the verdict is canned,
 641 | +and code checks every claim against the text."""
 642 | +import json
 643 | +import os
 644 | +import sys
 645 | +import unittest
 646 | +
 647 | +HERE = os.path.dirname(os.path.abspath(__file__))
 648 | +REPO = os.path.dirname(os.path.dirname(HERE))
 649 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
 650 | +sys.path.insert(0, os.path.join(REPO, "tests", "eligibility"))
 651 | +import package_pin  # noqa: E402
 652 | +import speakers as SP  # noqa: E402
 653 | +from test_eligibility import source  # noqa: E402
 654 | +
 655 | +META = {"exact_title": "Jeff Booth Warning: The Scenario Nobody in Bitcoin Wants to Talk About",
 656 | +        "channel_name": "Natalie Brunell",
 657 | +        "description": "Are we headed toward a future of abundance?\n"
 658 | +                       "Jeff Booth joins me to revisit The Price of Tomorrow and explore how AI is shaping our future.\n"
 659 | +                       "https://example.com/link\n"}
 660 | +LINES = SP.source_lines(META)
 661 | +SENTS = ["Jeff, you wrote about deflation years ago.", "What do you see now?",
 662 | +         "When I wrote The Price of Tomorrow, I said technology is deflationary.",
 663 | +         "Bitcoin lets that deflation reach everyone.", "That is the point."]
 664 | +
 665 | +
 666 | +def verdict(name, basis, people=None):
 667 | +    return {"people": people if people is not None else [
 668 | +        {"name": "Jeff Booth", "role": "guest", "line": "Jeff Booth joins me to revisit The Price of Tomorrow"},
 669 | +        {"name": "Natalie Brunell", "role": "host", "line": "channel: Natalie Brunell"}],
 670 | +        "speaker": {"name": name, "basis": basis, "why": "w"}}
 671 | +
 672 | +
 673 | +class Reply:
 674 | +    def __init__(self, text):
 675 | +        self.text, self.backend, self.replayed, self.usage, self.usd, self.seconds = text, "xai:grok", False, {}, 0, 0
 676 | +
 677 | +
 678 | +class Canned:
 679 | +    def __init__(self, text):
 680 | +        self.text, self.calls, self.rejected = text, [], []
 681 | +
 682 | +    def call(self, role, prompt, max_tokens=2000, seed=7, **k):
 683 | +        self.calls.append((role, prompt))
 684 | +        return Reply(self.text)
 685 | +
 686 | +    def reject(self, r):
 687 | +        self.rejected.append(r)
 688 | +
 689 | +
 690 | +class TestSourceLinesAndContext(unittest.TestCase):
 691 | +    def test_the_sources_own_lines_and_never_a_bare_link(self):
 692 | +        self.assertEqual(LINES[:2], ["title: Jeff Booth Warning: The Scenario Nobody in Bitcoin Wants to Talk About",
 693 | +                                     "channel: Natalie Brunell"])
 694 | +        self.assertIn("Jeff Booth joins me to revisit The Price of Tomorrow and explore how AI is shaping our future.",
 695 | +                      LINES)
 696 | +        self.assertNotIn("https://example.com/link", LINES)
 697 | +        self.assertEqual(SP.source_lines({}), [])
 698 | +
 699 | +    def test_the_context_is_the_word_records_own_sentences_around_the_clip(self):
 700 | +        before, clip, after = SP.context(source(SENTS), 2, 2, before=2, after=1)
 701 | +        self.assertEqual((before, clip, after), (SENTS[0] + " " + SENTS[1], SENTS[2], SENTS[3]))
 702 | +
 703 | +
 704 | +class TestCheck(unittest.TestCase):
 705 | +    clip, around = SENTS[2], SENTS[0] + " " + SENTS[1]
 706 | +
 707 | +    def test_a_person_stands_only_on_a_source_line_that_names_them_and_carries_the_whole_line(self):
 708 | +        people = [{"name": "Jeff Booth", "role": "guest", "line": "Jeff Booth joins me to revisit"},     # part of a line
 709 | +                  {"name": "Saifedean Ammous", "role": "guest", "line": "Saifedean Ammous joins me"},      # not a line
 710 | +                  {"name": "Natalie Brunell", "role": "host", "line": "Jeff Booth joins me to revisit"},  # not her line
 711 | +                  {"name": "jeff booth", "role": "guest", "line": "title: Jeff Booth Warning"}]           # twice
 712 | +        rec = SP.check(verdict("unknown", "", people), LINES, self.clip, self.around)
 713 | +        self.assertEqual([(p["name"], p["line"]) for p in rec["people"]], [
 714 | +            ("Jeff Booth", "Jeff Booth joins me to revisit The Price of Tomorrow and explore how AI is shaping our "
 715 | +                           "future.")])
 716 | +
 717 | +    def test_a_speaker_is_named_only_on_a_basis_in_the_clip_or_the_transcript_around_it(self):
 718 | +        rec = SP.check(verdict("Jeff Booth", "When I wrote The Price of Tomorrow"), LINES, self.clip, self.around)
 719 | +        self.assertEqual((rec["name"], rec["role"], rec["basis"]), ("Jeff Booth", "guest",
 720 | +                                                                    "When I wrote The Price of Tomorrow"))
 721 | +        self.assertTrue(rec["line"].startswith("Jeff Booth joins me"))
 722 | +        rec = SP.check(verdict("Jeff Booth", "jeff you wrote about deflation"), LINES, self.clip, self.around)
 723 | +        self.assertEqual(rec["name"], "Jeff Booth")                  # case and punctuation aside, in the context
 724 | +
 725 | +    def test_a_title_that_names_a_guest_never_names_the_clips_speaker(self):
 726 | +        """A basis found only in the source's lines (the title, the description) does not show who speaks a clip."""
 727 | +        for basis in ("Jeff Booth joins me to revisit", "title: Jeff Booth Warning"):
 728 | +            rec = SP.check(verdict("Jeff Booth", basis), LINES, self.clip, self.around)
 729 | +            self.assertEqual(rec["name"], "unknown", basis)
 730 | +            self.assertIn("not 3+ words found in the clip", rec["why"])
 731 | +            self.assertEqual([p["name"] for p in rec["people"]], ["Jeff Booth", "Natalie Brunell"])   # still tagged
 732 | +
 733 | +    def test_a_short_basis_an_unnamed_person_or_an_invented_quote_is_unknown(self):
 734 | +        for name, basis in (("Jeff Booth", "I wrote"), ("Saifedean Ammous", "When I wrote The Price of Tomorrow"),
 735 | +                            ("Jeff Booth", "As I said on my own podcast yesterday")):
 736 | +            rec = SP.check(verdict(name, basis), LINES, self.clip, self.around)
 737 | +            self.assertEqual((rec["name"], rec["basis"], rec["line"]), ("unknown", None, None), (name, basis))
 738 | +
 739 | +    def test_a_verdict_out_of_contract_raises(self):
 740 | +        for bad in ([], {"people": {}, "speaker": {}}, {"people": [], "speaker": "Jeff"}):
 741 | +            with self.assertRaises(ValueError):
 742 | +                SP.check(bad, LINES, self.clip, self.around)
 743 | +
 744 | +
 745 | +class TestAttribute(unittest.TestCase):
 746 | +    seg = {"video_id": "vidA", "k0": 2, "k1": 2}
 747 | +
 748 | +    def test_a_named_speaker_with_its_evidence_and_the_backend(self):
 749 | +        r = Canned(json.dumps(verdict("Jeff Booth", "When I wrote The Price of Tomorrow")))
 750 | +        rec = SP.attribute(r, self.seg, source(SENTS), META)
 751 | +        self.assertEqual((rec["name"], rec["measured"], rec["backend"]), ("Jeff Booth", True, "xai:grok"))
 752 | +        self.assertEqual(r.calls[0][0], "speaker_verdict")
 753 | +        self.assertIn("<clip>" + SENTS[2] + "</clip>", r.calls[0][1])
 754 | +
 755 | +    def test_a_reply_out_of_contract_is_unknown_not_measured_and_rejected(self):
 756 | +        r = Canned("Jeff Booth, probably")
 757 | +        rec = SP.attribute(r, self.seg, source(SENTS), META)
 758 | +        self.assertEqual((rec["name"], rec["measured"]), ("unknown", False))
 759 | +        self.assertTrue(rec["why"].startswith("not measured"))
 760 | +        self.assertEqual(len(r.rejected), 1)
 761 | +
 762 | +    def test_a_fenced_reply_is_read_and_any_failure_claims_no_name(self):
 763 | +        """glm C1 P1-2: a ```json fence is read; glm C1 P1-1: Router.call re-raises a back-end's own error, and any
 764 | +        failure is "unknown" with measured false, never a crash of the whole seal."""
 765 | +        r = Canned("```json\n" + json.dumps(verdict("Jeff Booth", "When I wrote The Price of Tomorrow")) + "\n```")
 766 | +        self.assertEqual(SP.attribute(r, self.seg, source(SENTS), META)["name"], "Jeff Booth")
 767 | +
 768 | +        class Boom(Canned):
 769 | +            def call(self, *a, **k):
 770 | +                raise RuntimeError("a back-end's own error")
 771 | +        rec = SP.attribute(Boom("{}"), self.seg, source(SENTS), META)
 772 | +        self.assertEqual((rec["name"], rec["measured"]), ("unknown", False))
 773 | +        self.assertIn("RuntimeError", rec["why"])
 774 | +
 775 | +    def test_an_unmeasured_attribution_is_tried_once_more_with_a_new_seed(self):
 776 | +        """Audit 0007 C1 K2: a failed call is retried once (seed 8); a second failure stays unknown, measured false."""
 777 | +        class Flaky(Canned):
 778 | +            def call(self, role, prompt, max_tokens=2000, seed=7, **k):
 779 | +                self.calls.append((role, seed))
 780 | +                if seed == 7:
 781 | +                    raise RuntimeError("down")
 782 | +                return Reply(self.text)
 783 | +        r = Flaky(json.dumps(verdict("Jeff Booth", "When I wrote The Price of Tomorrow")))
 784 | +        pk = {"segments": [dict(self.seg)]}
 785 | +        SP.attribute_package(r, pk, {"vidA": source(SENTS)}, meta_for=lambda v: META, log=lambda s: None)
 786 | +        self.assertEqual([c[1] for c in r.calls], [7, 8])
 787 | +        self.assertEqual((pk["segments"][0]["speaker"]["name"], pk["segments"][0]["speaker"]["measured"]),
 788 | +                         ("Jeff Booth", True))
 789 | +
 790 | +    def test_no_source_lines_or_no_word_record_is_unknown_with_why(self):
 791 | +        r = Canned("{}")
 792 | +        self.assertEqual(SP.attribute(r, self.seg, source(SENTS), {})["why"],
 793 | +                         "the source's title, channel and description are not in the store")
 794 | +        self.assertEqual(SP.attribute(r, self.seg, None, META)["why"], "no word record for the clip's context")
 795 | +        self.assertEqual(r.calls, [])                                # nothing to ask: no call is paid
 796 | +
 797 | +
 798 | +class TestPinCarriesTheSpeaker(unittest.TestCase):
 799 | +    def pk(self, sp):
 800 | +        g = {k: {"status": "PASS", "replayed": False} for k in package_pin.REQUIRED_GATES}
 801 | +        return {"schema": "pp.package/1", "type": "moments", "title": "T", "caption": "C", "hook_first_words": "Bitcoin is",
 802 | +                "runtime_s_estimate": 62.0, "vo_kind": "written", "gates": g,
 803 | +                "vo": {"intro": "I", "bridges": ["B"], "bridges_after_clip": [1], "signoff": "S"},
 804 | +                "lines": [{"slot": "intro", "text": "I"}, {"slot": "bridge_1", "text": "B"},
 805 | +                          {"slot": "title", "text": "T"}, {"slot": "caption", "text": "C"}],
 806 | +                "segments": [{"video_id": v, "channel": "ch", "start": 1.0, "end": 9.0, "text": f"Bitcoin is {v}.",
 807 | +                              "transcript_sha256": "t", "url_30s_before": "u", "time_sensitive": False,
 808 | +                              "source_published_at": "2026-11-12T01:00:00Z", **({"speaker": sp} if sp else {})}
 809 | +                             for v in ("aaaaaaaaaaa", "bbbbbbbbbbb")]}
 810 | +
 811 | +    def test_the_pin_refuses_a_segment_without_a_speaker_record_or_a_named_one_without_evidence(self):
 812 | +        jeff = {"name": "Jeff Booth", "role": "guest", "line": "Jeff Booth joins me"}
 813 | +        named = {"name": "Jeff Booth", "role": "guest", "line": "Jeff Booth joins me", "basis": "When I wrote it",
 814 | +                 "why": "", "people": [jeff], "measured": True}
 815 | +        for sp in (None, {"name": ""}, {"name": "unknown", "people": []}, dict(named, basis=""), dict(named, line=None),
 816 | +                   dict(named, people=[]),                                   # C1 K1: a name nobody in people holds
 817 | +                   dict(named, line="Jeff Booth wrote a book"),               # not that person's line
 818 | +                   dict(named, role="host"),                                  # not that person's role
 819 | +                   dict(named, people=[dict(jeff, role="speaker")])):         # a role outside host / guest / other
 820 | +            with self.assertRaises(package_pin.PinRefused, msg=sp):
 821 | +                package_pin.to_pin(self.pk(sp), "r")
 822 | +        pin = package_pin.to_pin(self.pk(named), "r")
 823 | +        self.assertEqual([s["speaker"]["name"] for s in pin["segments"]], ["Jeff Booth", "Jeff Booth"])
 824 | +
 825 | +    def test_the_speaker_is_inside_the_seal(self):
 826 | +        unknown = {"name": "unknown", "role": None, "line": None, "basis": None, "why": "", "people": [],
 827 | +                   "measured": True}
 828 | +        pin = package_pin.to_pin(self.pk(unknown), "r")
 829 | +        mp = pin["moments_package"]
 830 | +        self.assertEqual(mp["package_sha256"], package_pin.seal(pin["segments"], mp["edl_vo"], mp["signoff_expected"],
 831 | +                                                                 mp["title"], mp["caption"], mp["gates"]))
 832 | +        segs = [dict(s, speaker=dict(s["speaker"], name="Jeff Booth")) for s in pin["segments"]]
 833 | +        self.assertNotEqual(mp["package_sha256"], package_pin.seal(segs, mp["edl_vo"], mp["signoff_expected"],
 834 | +                                                                    mp["title"], mp["caption"], mp["gates"]))
 835 | +
 836 | +    def test_every_earlier_pin_still_recomputes_and_a_dropped_later_field_is_caught(self):
 837 | +        """The integrator's pin check recomputes seals with THIS module (imported from the worktree). A field added
 838 | +        to the seal later enters the body only when a segment carries its key: every earlier pin keeps its digest,
 839 | +        and removing a sealed field from a new pin changes it."""
 840 | +        import glob
 841 | +        n = 0
 842 | +        for p in glob.glob(os.path.join(HERE, "proof", "**", "MOMENTS_PIN*.json"), recursive=True):
 843 | +            with open(p) as f:
 844 | +                pin = json.load(f)
 845 | +            mp = pin.get("moments_package") or {}
 846 | +            if "package_sha256" not in mp:
 847 | +                continue
 848 | +            n += 1
 849 | +            self.assertEqual(package_pin.seal(pin["segments"], mp["edl_vo"], mp.get("signoff_expected"), mp["title"],
 850 | +                                              mp["caption"], mp["gates"]), mp["package_sha256"], p)
 851 | +        self.assertGreaterEqual(n, 6)                                    # 37c5b5f5, 41f29b1f and the four L-y pins
 852 | +        unknown = {"name": "unknown", "role": None, "line": None, "basis": None, "why": "", "people": [],
 853 | +                   "measured": True}
 854 | +        pin = package_pin.to_pin(self.pk(unknown), "r")
 855 | +        mp = pin["moments_package"]
 856 | +        for k in package_pin.SEALED_LATER:
 857 | +            segs = [{x: v for x, v in sg.items() if x != k} for sg in pin["segments"]]
 858 | +            self.assertNotEqual(package_pin.seal(segs, mp["edl_vo"], mp["signoff_expected"], mp["title"],
 859 | +                                                 mp["caption"], mp["gates"]), mp["package_sha256"], k)
 860 | +
 861 | +
 862 | +if __name__ == "__main__":
 863 | +    unittest.main()
 864 | 
```

---

You are auditing a diff on branch pp-selectid (Protocol Pulse: moments-first packaging under law L-y, the MEDLEY of
real clips). It implements the builder's part of the orchestrator's order of 00:05 ET Nov 13: a BATCH of up to three
novel medleys, and item 3, "every pin carries, per segment, the SPEAKER'S NAME where the source's title/description
names the guest, with its evidence (the description line) ... Unknown speaker = say unknown, never guess."

Only state what you can verify from the diff provided. If uncertain, say so; do not guess.

Standing laws:
- nothing measured is never a pass (L-m); fail closed (L-j);
- never change what a check accepts in order to make something pass;
- no clip span already delivered is used again (L-p);
- time-sensitive words only from a source <= 24 h old, judged on the RENDER clock (L-v 3);
- every pin is sealed: package_sha256 over its segments, VO, title, caption and gate inventory.

The files:
1. pipeline/speakers.py (new): who speaks each pin segment.
   - source_lines(meta): the source's own title / channel / description lines (the store's meta.json).
   - context(src, k0, k1): the word record's sentences around the clip.
   - One verdict call (new role speaker_verdict in model_providers.json) proposes the people the source names and the
     clip's speaker, with quotes.
   - check() keeps only what the text shows:
     - a person needs a source line that names them;
     - a named speaker needs a basis of 3+ words found in the clip or the transcript around it (never a source line
       alone: a title naming a guest does not show who speaks a given clip).
   - Otherwise the speaker is "unknown", with why, and the people the source names stay listed for tagging.
2. pipeline/package_pin.py:
   - speaker_problems(): to_pin refuses a segment without a speaker record, or a named speaker without its line and
     basis;
   - the speaker record is carried on each pin segment and is inside the seal.
3. tests/package/proof_batch.py (new): the batch driver.
   - build: one saved universe's medley, built by the packager on the render clock, with every clip span of the
     delivered pins and of the batch's kept packages passed as delivered, and the kept source videos avoided where
     possible.
   - seal: speakers, then the pin.
4. tests/package/proof_ledger.py and proof_ly.py: speakers are attributed before a pin is written.
5. Tests: tests/package/test_speakers.py (new); fixture updates in test_medley.py / test_angles.py (each pin fixture
   now carries a speaker record, as the real flow attaches it before sealing).

Check, concretely:
(a) Can a WRONG speaker name reach a pin? For example: a title naming a guest while the host speaks the clip; a quote
    that is not in the text; a person the source does not name; a reply out of contract.
(b) Is any failure silent or counted as a pass? A failed call must be "unknown" with measured false, never a name.
(c) Is the speaker record really inside the seal, and does to_pin refuse every malformed record?
(d) Does the batch build keep delivered spans and the batch's kept spans out, on the render clock?
(e) Do the tests fail on the defect each one names?

Output:
- Findings ranked P0 / P1 / P2, each with file:line and a concrete failure scenario (inputs -> wrong result).
- Only state what you can verify from the diff provided. If uncertain, say so; do not guess.
- End with a verdict line: "SHIP: yes | yes with conditions | no".


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
