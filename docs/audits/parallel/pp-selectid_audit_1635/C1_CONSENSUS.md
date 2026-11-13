# pp-selectid audit 1635 (ruling 70's cost report: the vendor's figure, an estimate labelled): cycle 1 consensus

- **Run:**
  - grok: "SHIP: yes", no findings.
  - qwen: "SHIP: yes", P2 observations, each "verified correct".
  - glm: "SHIP: yes with conditions": two confirmations and one optional test.
- No P0 or P1 holds. Nothing changes in the code; cycle 2 reviews the same diff.

## Answered (glm's conditions)

| # | condition | the answer |
|---|---|---|
| A1 | No other reader of the renamed out["visual"]["usd"]? | grep over pipeline/ and tests/ for visual"]["usd"], .get("usd") on the visual summary and out_visual["usd"] finds none. The only reader is the driver's log line, which this diff updates. |
| A2 | Does VP.sealed() keep usd_basis out of the seal? | sealed() is an INCLUSION list: it copies only version, measured, flags, third_person, on_screen_text, lower_third, backend, replayed and why, plus the sheet's name, sha256 and times (visual_pin.sealed). usd, usd_basis, usage and cached can never reach the seal, whatever the record carries. |
| A3 | glm P1-4: a record without usd_basis (one written before this change) would add to neither sum | Every record build() can see carries a basis now. visual_for's fresh path sets it through cost(); both cache-hit paths set "cached", and they serve records cached before this change too. Since the cost of a cache hit is 0, nothing is lost. |

## Recorded (single-model, no change)

| # | finding | why no change |
|---|---|---|
| G1 | glm P1-2: the estimate branch has no bool guard | Reply.usd is the back-end's price-table float (Backend.usd), never a bool. glm: "latent, not active". |
| G2 | glm (optional): a build-level test of the estimate branch | cost()'s three bases are unit-tested; the build's split is tested with reported records. |

## Verification

- test_visual_pin 11 and test_medley 138 OK on dev27 (base 57e7239f).
