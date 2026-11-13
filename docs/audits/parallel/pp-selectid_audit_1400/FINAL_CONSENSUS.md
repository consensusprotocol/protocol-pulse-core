# pp-selectid audit 1400 (RULING 67: the attested-text re-seal): FINAL consensus (cycle 2)

- **Cycle 2:**
  - grok: "Yes with conditions": two P1s, the replace-opcode repetition and the 3-decimal time match.
  - qwen: "Yes with conditions": P1, the replace-opcode repetition. It now refutes its own cycle-1 "P0"s, as R1 and
    R2 did.
  - glm: "Yes with conditions ... none of which require code changes before this pin ships ... Ship as-is for the
    held pin". It downgrades its own P1-1 and P1-3 to P2, and P1-3 is "the one I'd still take".
- No P0. R1 to R3 stand, uncontested in cycle 2.

## Applied (the two consensus items)

| # | finding | the change |
|---|---|---|
| C1 | The repetition class depends on alignment: a repetition the matcher emits as 'replace' fell to the function-word test (glm C1 P1-1, grok C2 P1, qwen C2 P1, glm C2 P2) | carry_class now classifies each side of a difference. The run's r[a:b] and the pin's p[c:d] must each be an immediate repetition on that side, or all function words; an empty side passes. That holds alike for delete, insert and replace, and critical tokens are still never carried. delete and insert keep their exact former results. Tests: "and that's why that's why we" vs "and that's why so we" aligns as a REPLACE and is "immediate repetition"; the same with "bank" on the pin side is None. |
| C2 | The second recogniser's reading is matched on 3-decimal rounding, and a miss gives a misleading refusal (glm C1 P1-3 / C2 P2, grok C2 P1, qwen C2 P2) | It now matches within 1.5 ms of the clip's start and end. A miss names every reading of that video in the build record (start, end, replayed). Tests: a reading 1 ms apart is the same clip; another span is refused, and its readings are named. |

## Recorded (single-model, no change)

| # | finding | why no change |
|---|---|---|
| G1 | glm C1 P1-4: compare the recomputed diff with the diff the render's hold records | Not adopted in cycle 2: grok calls it resolved, and glm C2 checks the inclusive i0..i1 convention against the render's hold format. On the real data the recomputed differences ARE the hold's ([["in", "you"], ["that's why", ""]], C1 A2), and the joined words 32-73 are the hold's quoted run_decode. |
| G2 | grok C2 P2: also check that this side's recogniser does NOT read the old approved text | reads() must hold for the RUN decode at every difference, with one neighbour each side, consecutive. A reading that matches the approved text there cannot also match the run's differing tokens at the same aligned position. test_it_refuses_without_both_recognisers_or_on_another_pin refuses a reading equal to the approved text. |
| G3 | glm / qwen P2s: format coupling, the copied law lists, the final write outside the try, a zero-token word | All fail closed. The lists are the render's, copied. |

## Verification

- All 12 suites OK on dev23 with C1 and C2: test_attest 7 (new), test_speakers 16 (the btc_screen fix).
- The real-data dry run on a copy of the held pin is unchanged: function word plus immediate repetition, carried; the
  attested text; re-sealed.
