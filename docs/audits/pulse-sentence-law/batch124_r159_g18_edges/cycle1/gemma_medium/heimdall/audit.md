# Heimdall audit

**Question:** TASK: audit batch 124 of the Protocol Pulse video pipeline (Python): G18's EDGE check (the first and last EDGE_WORDS canonical words of the final's decode must equal the lock's; word_diff.edges, unchanged) now follows ruling 143. Only state what you can verify from the diff and the cited lines. If uncertain, say so. Do not guess.

RULINGS. 143: a non-material differing pair never holds; a material pair (a number, a negation, a name, a ticker or an amount: pinned.material_pair via word_diff._material) holds unless the audio readings agree. 159 (b): "the lock and the release gate must not disagree". A cut mid-word, or a clipped or shifted cut, stays HARD. FOUND: on the real Nov 12 clip_01, the lock (ruling 143) took 'I think' (run decode and second recogniser agree); a final decoded 'I mean' failed G18's edge check, because ruling 18's alternatives, which used to excuse it, are gone under 143.

THE DIFF: _edges_substituted_only(expected, heard) aligns the canonical words (difflib) and returns True only when every difference touching the first or last n words is a 'replace' of equal length whose words are non-material. Then, when the identity check is clear, the edge differences go to the same audio adjudication as the identity's small words (sentence_law.span_fidelity: the prepared clip's interior between the fades must BE the source span) and are cleared (row["edges_small_words"]) only if the audio is the same. Any insert or delete at an edge, or a material word, returns False: the edge stays a FAIL.

CHECK, AND ANSWER EACH:
Q1. Can a CLIPPED cut (the first word missing, or part of it), a SHIFTED cut (an extra word at an edge) or a cut mid-word now pass G18's edge check? Construct the closest case.
Q2. difflib aligns words, not audio. Name an input where the alignment calls a shift a one-for-one replace (e.g. a repeated word next to the edge), and say whether the audio check still catches it.
Q3. The audio check covers the interior between the fades; the edge words' own audio is measured by G17c (REQUIRED, separate). Is there an edge failure that NEITHER catches now?
Q4. Any other defect.

OUTPUT: for each finding, severity (critical|high|medium|low), file:line, the concrete failure (inputs -> wrong result), and the fix. If none, say NONE for that question.
REMINDER: only what the diff and the cited lines show; say when uncertain.

**Panel:** gemma  |  **Cost:** $0.0021
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
