# gpt-6.1-sol (86 s) usage={'prompt_tokens': 2102, 'completion_tokens': 3060, 'total_tokens': 5162, 'prompt_tokens_details': {'cached_tokens': 0, 'cache_write_tokens': 2099, 'audio_tokens': 0}, 'completion_tokens_details': {'reasoning_tokens': 2048, 'audio_tokens': 0, 'accepted_prediction_tokens': 0, 'rejected_prediction_tokens': 0}}

## 1. BLOCKING — The changed checks no longer reject nonpositive durations

**`pipeline/edl_rules.py:233–246,248–252`**

The patch changes both the per-clip lower bound and per-channel lower bound from failures into deviations.

If `dur` reaches these checks as `0` or a negative number, and the clip/channel-count checks otherwise succeed:

- `0` produces an “8.0s under” deviation.
- `-1` produces a “9.0s under” deviation.
- Neither adds a failure; the deviation branch returns `True`.

These checks previously rejected those values. The change does not distinguish a legitimate short passage from an empty or backwards duration. A final-runtime gate does not, by itself, establish that each constituent clip has a valid duration.

**Uncertain:** duration extraction and any preceding validation are omitted from the supplied hunks. I cannot verify that an EDL containing `"duration": 0` or `-1` actually reaches these checks unchanged, or that another rule permits release. The verified regression is the removal of rejection **in these checks**.

## 2. BLOCKING — PROVENANCE and caption delivery are not established

**`pipeline/edl_rules.py:234,236,246,249–251`**

The visible implementation constructs deviation strings and returns them in `reason`. That is the only demonstrated output.

The supplied diff contains no demonstrated connection from that reason to:

- PROVENANCE;
- the Telegram caption.

**Uncertain:** an existing validate-stage consumer might already deliver the complete reason to both destinations. That consumer is not shown. Recording a validation reason is not evidence that both required release artifacts contain every deviation and its size.

The modified test checks only substrings in the returned reason: **`pipeline/test_edl_rules.py:202–209`**. It does not establish either delivery requirement.

## 3. Not BLOCKING as a verified new regression — Other malformed durations remain unresolved

**`pipeline/edl_rules.py:233–239,244–252`**

For values reaching the shown arithmetic unchanged:

| Value | Verified behavior of the shown checks | Regression established? |
|---|---|---|
| `NaN` | Both window comparisons are false. Adding it contaminates the channel total with NaN; that total also fails to trigger `< 8`. These checks record no deviation for it. | **No.** The old comparisons also missed NaN. |
| `None` | `dur < 8` raises `TypeError`; it does not return PASS. | **No PASS regression demonstrated.** |
| String | Comparing it with integer `8` raises `TypeError`; it does not return PASS. | **No PASS regression demonstrated.** |
| Missing duration key | **Uncertain.** Extraction/default behavior is outside the shown hunks. | **Uncertain.** |

Whether exceptions reliably stop release is also **uncertain**: the caller’s exception handling is not supplied.

## 4. Not BLOCKING as a verified regression — The clip-count check does not exclude hooks

**`pipeline/edl_rules.py:221,224–225`**

The check uses the length of the raw `clips` list. A hook entry placed in that list counts toward this particular minimum; the shown check does not classify entries by role.

This counting behavior is unchanged.

**Uncertain:** whether hooks are allowed in that list, whether they can satisfy the distinct-channel check, and whether another rule rejects them. The diff does not establish a newly accepted hook-based lineup.

## 5. Not independently BLOCKING — The changed tests leave the critical boundaries unproved

**`pipeline/test_edl_rules.py:193–218`**

The added/modified tests cover a positive short duration, an over-window duration, and three insufficient-count cases. They do not exercise the fail-closed boundaries raised by this change: zero, negative, missing, `None`, NaN, or string durations.

Specific weaknesses:

- **No release-artifact assertion:** only `reason` is inspected, not PROVENANCE or caption contents — **lines 202–209**.
- **No whole-sentence proof:** the “whole sentence” test supplies only index, duration and channel. It cannot establish verbatim sentences or intact edges — **lines 194–201**.
- **No isolation of the two minimum-count checks:** the one-clip case also has one channel; the empty case violates both. Those cases cannot independently detect removal of the clip-count requirement — **lines 213–218**.

The first two blocking findings remain open on this diff alone. Preservation of sentence integrity, credits equality, byte-bound release, and downstream fail-closed behavior is **uncertain**, not demonstrated by this patch.