# C2 CONSENSUS (written by the pp-selectid session, ruling 118: Heimdall seats only)
Seats answered: 2 of 2 (gpt-oss-20b at effort low, glm-5.3-flash at effort none); both close on P1_OR_WORSE: 0.
gpt-oss's table still lists three 'P1' rows; each is DISPROVED in the code:
- "a doubled 'Bitcoin' (subject 'Bitcoin and Bitcoin')": 'bitcoin' is in fallback_subject's skip set; no run holding
  it is ever a name, so the subject is 'Bitcoin' or '<Name> and Bitcoin'.
- "may not return the shortest template": FALLBACK_CLOSING's variants are nested (each adds words to the one before)
  and are tried in that order, so the first inside the budget is the shortest that fits (test at 31.5-45 s).
- "IndexError still present for an empty channel list": the hardened line returns 'the channels' (C1 fix F1).
glm: 0, no new finding. FINAL: no open P0/P1 in either cycle.
