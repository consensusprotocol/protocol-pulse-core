# AUDIT BRIEF — pp-tests phase 2: the moments-first EXAM (tests and fixtures only)

## Task context
You are reviewing a TESTS-ONLY change on branch pp-tests of a Bitcoin video pipeline ("Pulse Check": short videos
assembled from verbatim clips of partner / news channels plus a voice-over (VO), one title, one caption). Another
session (the builder) is writing three new gates; this change is the EXAM those gates will be proven on, written by a
different session so the builder does not write its own exam. Nothing under pipeline/ is edited.

## The order (03:00 ET 2026-11-12), verbatim essentials
- "Its gates are only as good as the corpora they are proven on, and it should not write its own exam. You write the
  exam, from REAL material."
- context_integrity corpus: >= 40 MUST-FAIL and >= 20 MUST-PASS cases mined from the real transcript store; each with
  the source video id, the selected sentence ids, the context window (90 s before / 60 s after, verbatim), a package
  around it (adjacent clip, VO line, title), the expected verdict and a reason class. Classes: steelman / quoting an
  opponent / sarcasm / hypothetical / conditional split across sentences / unresolved pronoun or 'this/that/today' /
  'some people say' / answer without its question / later retraction / reading a tweet or ad aloud / wrong speaker
  (host paraphrasing a guest) / stale time reference / false dialogue created by sequence or bridge between two
  different videos / title adds a thesis. "Find real instances first ...; construct a case only when a class has no
  real instance, and label it CONSTRUCTED." Must-pass: "real, clean, sincere stand-alone assertions packaged
  honestly, including ones that open on 'And'/'So' and still stand alone."
- vo_fidelity corpus: >= 25 must-fail VO lines and >= 10 must-pass against real selected sentences. Must-fail: stance
  flips, 'could' -> 'will', swapped or rounded numbers, invented agreement, a true fact not in any clip, a name of
  someone who does not appear, a banned framing verb, a second-person financial imperative. Must-pass includes
  legitimate manifest-derived language (channel names, 'two voices', dates), "so a checker that rejects everything
  fails".
- exclusions corpus (law L-u): exclude named accusation of fraud/crime/insolvency, partner attacking partner,
  buy/sell/leverage imperative, guaranteed-return claim, single-source 'breaking' claim, ad read, third-party media
  played in a partner video, altcoin content; keep near misses (criticising a policy, a clearly framed personal
  prediction, naming a company neutrally).
- Harness tests/adversarial/test_moments_gates.py: runs whatever gate implementation exists at a configurable import
  path; "skip-with-reason, never pass, when absent"; a confusion table per gate and per reason class; thresholds
  "100% of must-fail rejected, false-reject on must-pass <= 10% (state the number; it is PBX's supply)".
- Then a blind baseline through two frontier models from different vendors (~$15 guard).

## Laws the exam encodes (summarised from PIPELINE_LAWS.md)
- L-s CONTEXT INTEGRITY: PASS only if the speaker's own sincere assertion; every referent inside the clip; no unmet
  condition and no reversal; the in-context proposition entails the viewer takeaway with the same polarity and no
  stronger certainty; no implied relation between speakers who were not in the same source video (sequence, bridge,
  title); any 'uncertain' is a FAIL.
- L-t: title / caption / VO: every number, name and claim audible in a clip; no stronger certainty; framing verbs
  destroys / slams / exposes / admits / confirms / caught banned unless the source's own word; no absent names; no
  second-person financial imperative.
- L-u: never auto-selected: accusations against a named person or company; partner attacking partner; buy / sell /
  leverage imperatives and guaranteed-return claims; single-source 'breaking' claims; ad reads; third-party media in a
  partner's video. At most one clip per channel per video.
- L-v: a moment may not span a speaker change; time words need the original publish time.
- L-m: nothing measured is never a pass. L-j: fail closed.

## Hard rules for this session
Tests and fixtures only; no edit under pipeline/; never write to the main tree /home/ultron/protocol_pulse (the store
is read-only input); CPU and API only (no GPU); keys read by name inside code, never printed.

## What to review (be concrete; quote the file / case id)
1. LABEL CORRECTNESS (most important): for every case in the digest, is the expected verdict defensible from the
   material shown? A must-fail case whose trap is not really there, or a must-pass case that is not clean (hidden
   referent, hedge dropped by the title, a qualification nearby, a speaker change, a time word), poisons the exam.
   Also: is the class right; is any case's trap only visible outside the window it gives (say so).
2. Is any package (title / VO / caption) of a MUST-PASS case unfaithful (stronger certainty, number change, absent
   name, implied relation, same channel twice)? Is any MUST-FAIL case failing for a reason other than its class
   (a confound that lets a gate reject it for the wrong reason)?
3. Harness: can a gate pass without being right (leaks of the answer: id, origin, provenance, file order)? Can the
   harness fail to report a real miss (exit-code precedence, absent vs error, uncertain counted as rejection)? Is
   skip-with-reason honoured and never a pass? Does the verbatim check really bind every case to the store bytes?
4. Baseline adapter: spend guard (cross-process, reserve then settle), key handling, blindness, prompt fairness.
5. Anything that writes outside the worktree, reaches the network in the default test run, or uses a GPU.

## Output format
Findings ranked most severe first, each: SEVERITY (CRITICAL / HIGH / MEDIUM / LOW), the file or case id, the quoted
evidence, the concrete fix. Only state what you can verify from the material; if uncertain, say so. End with READY or
NOT READY.
