# Cycle 1 consensus: pp-selectid audit for ruling 109 (free gates first in the spotlight build)

qwen3.8-27b reports P1_OR_WORSE 0 and glm-5.3-flash 1. They disagreed, so Grok was asked as the third: 1. Cost: $0.0269
vendor-reported.

THE SHARED P1 (glm, Grok): "the text may change after the early check (a snap, a trim, a rewrite), so a score known
low at the start may not be its final score". REFUTED from the code:
- Snapping happens in spotlight.pool (stage 1, spotlight.py:832, `ms, why = pool(...)`), BEFORE the early check. The
  moments reaching it are already the snapped spans, and with_verdict attaches the score of that exact text.
- No later stage assigns a moment's text: spotlight.py has no `m["text"] =`. A trimmed opener is its own moment
  ("~trim", with its own text and its own score), never a rewrite of another.
- Stage 7 re-attaches the scorer's verdicts (P.with_verdict) for the SAME text under the same scorer sha. A verdict
  is fixed per text and scorer version, so a score known below 4 at the start is the score stage 7 would stop it on.
- Nothing is dropped for good. Every build re-reads the scorer's verdicts, so a new scorer version is read by the
  next build.
- SELECTION LOCK, L-c and L-f: no selected word, cut or cluster changes. The early stop refuses only what stage 7
  refuses anyway, earlier and without a paid call.
Grok P2 (the new out["ruling_109"] key and the reasons): build() output is the builder's record. release_auth and
the pin never read it, and the pin's gate rows are unchanged.
Grok P2 / glm (a test of a low-then-high score): the case cannot arise within a build, for the reasons above.

No change. Mutations: 3 of 3 killed (no free gate first; an unscored moment stopped; exactly 4.0 stopped).
