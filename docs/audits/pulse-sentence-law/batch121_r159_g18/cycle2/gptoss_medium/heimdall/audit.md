# Heimdall audit

**Question:** TASK: cycle 2 of the audit of batch 121 (Protocol Pulse, Python): G18 follows ruling 143 for every lock (the same diff as cycle 1). Cycle 1: qwen27b (high effort, traced) PASS, gemma PASS, gpt-oss PASS: no findings. This cycle asks for the strongest case AGAINST the change. Only state what you can verify from the diff and the cited lines. If uncertain, say so. Do not guess.

TRACE AND ANSWER:
T1. Construct the most dangerous input you can for the changed line: a final whose words differ from the source span's decode where the difference is classed NON-material but changes what the speaker asserts (a tense, a modal like "will"/"would", "can"/"can't" split by the decoder, a plural/singular). Which of these does pinned.material_pair (via _material) class as material, and which pass now on the audio check?
T2. The audio check (span_fidelity between the prepared clip and the source span) passes when the clip plays the speaker's own audio. In that case, is a decoder's word-form difference ever a claim we make that the speaker did not make?
T3. Any other defect.

OUTPUT: for each finding, severity, file:line, the concrete failure, the fix. If none, say NONE.
REMINDER: only what the diff and the cited lines show; say when uncertain.

**Panel:** gptoss  |  **Cost:** $0.0008
## Consensus findings (majority of panel agrees)
- **[high] pipeline/test_word_diff.py:0** NameError: 'mock' is used but not imported
  - evidence: `mock.patch.object(SLW, "span_fidelity", return_value=(same, {"stub": True})), \
                    mock.patch.object(SLW, "span_matches", return_value=(False, {"stub": True}))`
  - fix: Add `import unittest.mock as mock` at the top of the file or import `mock` from the standard library.
  - raised by gptoss:F1; agree: gptoss
- **[high] pipeline/test_word_diff.py:0** NameError: 'W' is used but not defined
  - evidence: `ok, rows = W.gate_g18("final.mp4", segs, clips, transcriber=Tr())`
  - fix: Replace `W.gate_g18` with `self.g18` or import the module/class that defines `gate_g18` and refer to it correctly.
  - raised by gptoss:F2; agree: gptoss

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
