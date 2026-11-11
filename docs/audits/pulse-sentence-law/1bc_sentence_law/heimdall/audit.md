# Heimdall audit

**Question:** Commit 1b+1c implements the sentence-boundary law (pipeline/sentence_law.py): selection locks (anchor selected text in the file transcript, sha-sealed), boundary rule (punctuation or cached model adjudication + >=80 ms acoustic pause), cut placement only inside the locked pauses intersected with the unchanged cut_accept checks (replacing the +-2 s snap and the edge-word recompute tautology), G16 pre-render + final gate, G17 onset/tail integrity (prepared clips: >=80 ms genuine lead-in/tail; outputs: edge words keep >=85%), D1 room-tone lead-in pad. Find correctness bugs: wrong time/units, any path where missing data or a model failure yields a PASS/cut/lock, any way a cut can include a word outside the lock, any loosened acceptance, and any change to the frozen v2f path.

**Panel:** deepseek, qwen27b, glm  |  **Cost:** $0.0235
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
