# Audit 0614 (the orchestrator's 06:12 routing rulings (1) and (2)), cycle 1: consensus

Reviewers: grok-4.20 SHIP yes (no defect); qwen3.8-27b SHIP yes (two conditions); glm-5.3-flash SHIP yes with
conditions (documentation only). No critical, no high defect from any reviewer. Upper-bound cost of the cycle: about
$0.24 ($0.050 + $0.075 + $0.119), outside SPEND_LY.json.

## Implemented

- glm (a) + condition 1 (i): the "94 %" read as Grok's figure. The ruling_0612 note now says whose it is: "glm agreed
  with Grok on 94 % of the replay's coherence decisions". It also says outright that deepseek "stays second". The note
  already had glm "after Grok and ruling 96's deepseek"; it is now explicit.
- glm (c) + condition 1 (ii), and qwen's <high>: the coherence role's DEFAULT list (Grok -> deepseek) is unchanged, and
  the note did not say so. It now records that the default list is not changed, that the spotlight's closing-line and
  the medley's takeaway value verdicts use it, that the replay has no data for them, and that the orchestrator is
  asked (STATE line 1, 06:14, question B).
  - This is not a defect of this change. The ruling names coherence and clips-alone. Moving a verdict type off
    unmeasured data would break ruling 96's own rule.
- glm condition 3 (Plan B's clips-alone): VERIFIED from the code, and the note now records it.
  - providers.Router.chain reads Plan B's lists first while Heimdall is down. The keys tried are
    ["coherence_verdict:clips_alone", "coherence_verdict"].
  - routing.plan_b has no clips-alone key of its own, so clips-alone in Plan B mode is Plan B's coherence list:
    Grok -> Gemini -> OpenAI -> Anthropic (local and openai_stt are dropped by proof_ly.plan_b_chains).
  - So no Heimdall model judges clips-alone in either mode.

## Verified, no change

- qwen condition 2 / glm "unverified": Gemini resolves.
  - backends["google:gemini-2.5-pro"] exists (key name GEMINI_API_KEY_MEDLEY, min_out 8000), and it is Plan B's
    coherence list's second entry.
  - The edit script asserted both before it wrote.
  - proof_ly.FROZEN = ("local:", "anthropic:", "openai:", "openai_stt:") is a deny-list, so a google: leg survives
    chains().
  - The test asserts chains("heimdall_first")["coherence_verdict:clips_alone"] == [Grok, Gemini], and that the xAI-down
    pick returns Gemini. It passes.
- glm condition 2: no other test pins the old lists. Verified by execution: all 19 suites pass in the scratch copy
  dev02 (518 tests). Any test pinning the old lists would fail.
- qwen <medium> ("today" routing unchanged): every build runs with --routing heimdall_first (handoff 3.1; the driver
  passes it).
  - The 06:12 rulings amend ruling 96's heimdall_first table. "today" is the legacy mode, and the test still pins its
    two lists as before (a regression check, not the live routing).
  - No change.
- glm (d): no verdict becomes looser.
  - Every changed model is appended after the old deciders (coherence), removed where the ruling strikes it (qwen in
    step A), or swapped for the ruling's own replacement (clips-alone).
  - Agreed with grok and qwen.
- glm's test notes (the sequential r.down state; vendor-only vs per-family skip coverage) are coverage observations,
  not defects. The sequence is commented step by step in the test. No change.

## Not a change in this commit

- None. The rulings are implemented as written: (1) glm last on coherence, after Grok and deepseek; clips-alone Grok
  -> Gemini, with no Heimdall model; (2) qwen out of every step-A list.
