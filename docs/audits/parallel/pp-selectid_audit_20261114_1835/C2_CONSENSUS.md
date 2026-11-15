# Audit 20261114_1835 (ruling 104's directive path), cycle 2: consensus

- grok-4.20: yes with conditions. No P0 or P1.
- qwen3.8-27b: yes with conditions. No P0. One <high>: the IndexError on an empty package.
- glm-5.3-flash: yes with conditions. No P0 or P1. It notes that the cycle-1 <critical> and <high> were, on inspection,
  a wart and a hygiene item, both fixed.

## Taken (cycle 3 reviews these)

- **All three: spot_place read pk["segments"][0] unguarded.** An empty or odd package would raise an IndexError
  outside the pin's except, and stop the build instead of refusing the pin. The inline check this replaced had the same
  exposure. spot_place now refuses ("a spotlight without its segment has no channel to place") for an empty, missing or
  non-object segment list. Tests cover [], None and ["x"]; mutation D14 is killed.
- **qwen P2 / glm (2), the story id.** `$` lets a trailing newline through. The match is now re.fullmatch on the pins'
  own form (moments-<run>-<8 hex>), tested against to_pin's real id "moments-ledger_20261114_230148-3f481f5a" and
  against a trailing "\n". Mutation D15 is killed.
- **grok (2), the ceiling.** A test now gives a 36 s alternative to spotlight.pool: refused by usable's 35 s ceiling,
  directive or not.

## Documented, no change

- **qwen P2, directive_variant on a source with no sentences.** The parent's own sentences [k0, k1] index the same
  source; for_pool reaches directive_variant only for a parent with k1 > k0, whose source has those sentences.
- **glm (2), the count of dropped directive rows.** The builder writes the file. The build's RULING 104 line names
  each named parent's outcome, and a parent whose row was dropped has no directive note, which is visible there.
- **glm (3), the colliding id in "already in the pool".** The note names the variant's id, and it is in the pool beside
  it.

Verification: 16 of 16 mutations killed. test_ruling_104, test_spotlight and test_ledger_build, 98 passed.
