# pp-selectid audit 1545 (RULING 69: the speaker attribution reads the caption turn): FINAL consensus (cycle 2)

- **Cycle 2:** all three say "yes with conditions", with no P0 or P1.
  - grok: "No path verified in the diff names a speaker on less than turn structure + validated address/self-intro".
  - qwen: "the conditions are met by the current diff".
  - glm: "Ship it".
- The cycle-1 fixes (C1 the backchannel tokens, C2 the guarded parsing, C3 the word-boundary cut) and the
  refutations (R1, R2) are endorsed by all three.

## Applied (the one cycle-2 consensus item)

| # | finding | the change |
|---|---|---|
| C4 | The two name-word filters differed (> 1 for the turn quotes, > 2 for the lower third) (grok (b), glm N3, glm's "single highest-leverage change") | ONE constant, NAME_WORD_MIN = 2 characters, for both. An initial such as "W." (normalised "w") never counts as a name word. test_speakers 23 OK. |

## Recorded (single-model, no change)

| # | finding | why no change |
|---|---|---|
| G1 | glm N1: turn["end"] is the START time of the turn's last caption line (945.28), not the speech's end | That is what the caption record carries: line display times, not word ends. The recorded value is the last line's time. The 945.28 address is that line, so the evidence and the record agree. |
| G2 | grok (a): first store with any marker wins | Fails closed (C1 G1). A live episode's main-tree copy has no auto captions, which is why the ingest store is read second. |
| G3 | glm N4: no test of a repeated line next to a bare '>>' | The repeat check compares whole lines before the split; a bare '>>' line is its own line. Single-model. |
| G4 | glm N5: a lower third naming someone who is not among the people neither confirms nor vetoes | Stated reading: a lower third is evidence about the people the source's lines name (ruling 70: "never alone"). A strap naming nobody listed is no evidence either way. |
