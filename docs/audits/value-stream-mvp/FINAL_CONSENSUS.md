# CONSENSUS REPORT — VALUE-STREAM-MVP — CYCLE 2
Generated: 2026-03-26 14:46
Models: gpt4o, grok, gemini

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Backend / Service Logic | 8/10 | 7/10 | 7/10 | **7.5/10** |
| Frontend / UI | 3/10 | 4/10 | 3/10 | **3/10** |
| Brand Alignment | 4/10 | 4/10 | 4/10 | **4/10** |
| Empty State Design | n/a | 2/10 | 3/10 | **2.5/10** |
| Hero Section / Ethos Communication | n/a | 3/10 | 3/10 | **3/10** |
| Core Feature Completeness | 4/10 | 6/10 | n/a | **5/10** |
| UX / Onboarding Flow | 2/10 | 3/10 | n/a | **2.5/10** |
| **Overall MVP Readiness** | **3/10** | **4/10** | **3/10** | **3/10** |

> **Synthesizer note:** Gemini's scores are the most granular and technically grounded; GPT-4o is slightly more optimistic across the board but converges on the same narrative. Grok's scores align closely with Gemini. The consensus rounds down where functional defects were confirmed.

---

## UNANIMOUS FINDINGS
*All 3 models agree — implement unconditionally.*

### U1 — Hero Section Fails to Communicate the Platform's Ethos
**What it is:** The current hero subtitle (`value_stream.html`, lines 246–249) uses generic, low-conviction language that fails to communicate the anti-algorithmic, proof-of-value ethos. A Bitcoin maximalist landing on this page sees nothing that distinguishes it from a generic link aggregator.

**File/Line:** `value_stream.html`, lines 246–249

**What to change:** Replace the current subtitle with ideologically sharp, defiant copy. Consensus suggested language approximating:
> *"No algorithms. No engagement farming. No dopamine loops. Economic signal surfaces the truth. Your sats are your vote."*

The goal is to make the first impression feel like a departure from Web2, not a variation of it.

---

### U2 — Empty State Is a Dead End, Not an Invitation
**What it is:** When the feed is empty (`value_stream.html`, lines 331–337), the UI renders a blank or minimal state that communicates abandonment rather than opportunity. New users have no context, no call-to-action, and no reason to engage.

**File/Line:** `value_stream.html`, lines 331–337

**What to change:** Two-part fix:
1. Replace the empty-state block with a "pioneer" framing — messaging that positions the user as the first contributor, not a latecomer to a dead platform.
2. Pre-populate the feed with 3–5 curated "genesis" posts (e.g., the Bitcoin whitepaper URL, Satoshi's whitepaper announcement, a foundational Bitcoin essay). These seed posts give immediate perceived value and demonstrate the feed mechanic in action.

---

### U3 — Brand Color and Typography Compliance Is Broken
**What it is:** The stylesheet in `value_stream.html` (lines 16, 36, 48–50, 63, 83–99, 122, 160, 164, 173 and throughout) uses `#f7931a` (Bitcoin orange) and `#8a2be2` (purple) as primary accent colors. The specified brand palette is Primary Red `#CC2222` on Background `#0A0A0F`. Typography uses inconsistent fonts where `JetBrains Mono` is specified by the design system.

**File/Line:** `value_stream.html`, pervasive — lines 16 through ~237 (entire `<style>` block)

**What to change:** Systematic find-and-replace of all non-brand color values with the official palette. Audit every `color:`, `background:`, `border:`, and `box-shadow:` declaration. Ensure all UI text elements render in `JetBrains Mono`. This is not aesthetic polish — brand trust is table stakes for a Bitcoin-native audience.

---

## MAJORITY FINDINGS
*2 of 3 models agree — implement unless there is a compelling reason not to.*

### M1 — Curator Incentive / Split Is Invisible in the UI
**Models:** Grok, Gemini (GPT-4o referenced it in Cycle 1 but not scored as a separate miss in Cycle 2)

**What it is:** The backend correctly implements a 10% curator split (`value_stream_service.py`, lines 15–16, 390–414). This is one of the most compelling differentiators of the platform — curators earn real sats. However, the UI either omits this information entirely or buries it in a tooltip. The value-for-value loop is invisible.

**File/Line:** `value_stream.html`, line 274 (hint only); `value_stream_service.py`, lines 15–16

**What to change:** On each content card, display the curator's earned sats for that post. Add a persistent UI element (badge, stat line, or sidebar) that shows the logged-in user's total claimable curator earnings. This makes the incentive model visceral and immediate.

---

### M2 — UX Relies on `alert()` and `window.location.reload()`
**Models:** Gemini, Grok

**What it is:** Zap confirmation and submission success are communicated via native browser `alert()` dialogs, and state is refreshed via full `window.location.reload()` (`value_stream.html`, lines 435–436, 438, 441, 461–462, 465, 468). This interaction pattern is jarring, feels amateurish, and breaks user flow — particularly damaging after a successful zap, which should feel like a rewarding, frictionless moment.

**File/Line:** `value_stream.html`, lines 435–436, 438, 441, 461–462, 465, 468

**What to change:** Implement a non-blocking toast notification system. On successful zap, the content card's sats counter should animate upward in place without a full reload. On submission, a toast confirms success. This is table-stakes UX for any modern web application.

---

### M3 — Signal Score Calculation Is Opaque
**Models:** Grok, Gemini

**What it is:** The `signal_score` is displayed on content cards (`value_stream.html`, line 291) but its derivation is unexplained. For a Bitcoin audience whose core tenet is "don't trust, verify," an unexplained score is a trust liability. It could appear algorithmic — the exact thing the platform is supposed to reject.

**File/Line:** `value_stream.html`, line 291; `value_stream_service.py`, line 290–302

**What to change:** Add a small info icon (ⓘ) next to the signal score display. On hover or tap, a tooltip or micro-modal explains the formula in plain language (e.g., "Signal Score = total sats weighted by recency. No hidden factors. No engagement gaming."). Consider showing raw `total_sats` alongside the derived score so users can independently verify the ordering.

---

## UNIQUE INSIGHTS
*Only 1 model caught these — evaluated individually.*

### UI-1 — Hardcoded Zap Amount of 1000 Sats (Gemini only)
**Assessment: IMPLEMENT IMMEDIATELY — This is the most important finding in the entire audit.**

Gemini identified that the zap amount is hardcoded to `1000` sats in `value_stream.html:455`. This is not a polish issue. It is a **fundamental betrayal of the platform's core thesis**. "Proof of Value" requires that the *amount* of sats be a free expression of how much value a user ascribes to the content. A fixed zap amount converts the entire mechanic into a binary like button with a fee — indistinguishable from a Reddit upvote with a $0.04 cover charge. The economic signal becomes meaningless noise. This alone would invalidate the MVP's value proposition. Replace with a custom-amount modal or input field triggered by the ZAP button.

**File/Line:** `value_stream.html`, line 455
**Verdict: P0 CRITICAL. Implement unconditionally.**

---

### UI-2 — Broken CSS for Twitter/X Platform Badge (Gemini only)
**Assessment: IMPLEMENT — Simple fix, high visibility defect.**

Gemini caught that the backend correctly identifies Twitter/X URLs and sets `platform = "x"` (`value_stream_service.py`, line 221), but the frontend CSS only defines `.platform-twitter` (`value_stream.html`, line 83). Every piece of content from X — likely the majority of curated content for this audience — will render an unstyled, broken badge. The fix is a one-line change to either the CSS or the service.

**File/Line:** `value_stream_service.py`, line 221 (change `return "x"` to `return "twitter"`) or add `.platform-x` CSS rule mirroring `.platform-twitter`
**Verdict: P1 HIGH. Implement.**

---

### UI-3 — Lack of Structured Onboarding Tutorial or Flow (Grok only)
**Assessment: INVESTIGATE — Valid strategic observation, lower implementation urgency.**

Grok identified that no model explicitly prescribed a step-by-step onboarding sequence (a "Curate → Zap → Rise → Earn" modal or tooltip flow). This is valid. However, given the MVP scope and the higher-priority functional defects, a full onboarding modal system is P2 at best. The hero section rewrite (U1) and the empty state genesis content (U2) partially address the onboarding gap. A tooltip sequence can be layered in post-launch.

**Verdict: P2 MEDIUM. Defer until P0/P1 items are resolved.**

---

### UI-4 — Sovereign Claim Portal UI Is Completely Missing (Gemini only, but elevated by Grok in Cycle 2)
**Assessment: IMPLEMENT — Strategically critical for the target audience.**

Gemini identified in Cycle 1 (and Grok endorsed in Cycle 2) that while `value_stream_service.py` contains a complete, robust implementation of `get_claimable_balance` and `process_claim` (lines 500–654), there is zero UI surface area for this functionality. For a Bitcoin maximalist, "you can earn sats but cannot withdraw them" is indistinguishable from a points scam. The platform must prove sovereignty by closing the earning loop. A minimal "Wallet" section — showing balance and a withdrawal input for a Lightning address — is non-negotiable for the MVP's credibility.

**File/Line:** New HTML template required; connects to `value_stream_service.py`, lines 500–654
**Verdict: P0 CRITICAL. This elevates from unique to consensus-tier given the strategic importance.**

---

## CONFLICTS
*Where models gave contradictory recommendations.*

### C1 — Pre-Populating Feed with "Genesis" Content: Authenticity Risk
**Grok** partially disagreed with the consensus genesis-content recommendation, flagging that pre-populating the feed risks diluting the user-driven ethos if seed content is not clearly marked as such.

**Tiebreaker verdict: Consensus wins, with Grok's caveat incorporated.**
The "empty restaurant" problem is a real and documented UX failure mode. However, Grok's concern about authenticity is also legitimate for this specific audience. Resolution: pre-populate with 3–5 genesis posts, clearly labeled with a `[Genesis Post]` or `[Seed]` badge and zero initial sats, so users understand these are curator-zero content placeholders, not organic proof-of-value signals. The first real zap on any of these posts becomes a meaningful event.

---

### C2 — Severity of Frontend Score
**GPT-4o** scored Frontend UI at 4/10 (Cycle 2). **Gemini and Grok** scored it at 3/10.

**Tiebreaker verdict: 3/10 is correct.**
The discovery of the hardcoded zap amount (a functional defect, not aesthetic) and the broken Twitter/X CSS (visible on likely the most common content type) justifies the lower score. GPT-4o's slightly higher score appears to reflect pre-hardcoded-zap-discovery optimism.

---

## VALIDATED STRENGTHS
*All models confirmed these are excellent. Do NOT change them.*

### VS1 — Backend Service Logic (`value_stream_service.py`)
All three models independently scored the backend at 7–8/10 and praised its architecture. Specifically validated:
- Intelligent, multi-fallback metadata scraping, with special handling for X/Twitter's anti-scraping measures
- Secure and logical zap processing flow
- Well-implemented curator split calculation (lines 15–16, 390–414)
- Complete claim and balance logic (lines 500–654)
- The `signal_score` algorithm itself (even if its UI transparency needs improvement)

**Do not refactor the service layer. It is the strongest part of this codebase.**

### VS2 — WebLN Integration Approach
All models confirmed that using WebLN for wallet integration is the correct, sovereignty-preserving approach for this audience. The integration pattern itself (connecting to Alby, etc. via browser extension) is right. Only the UX around it (hardcoded amount, alert/reload pattern) needs fixing.

---

## LAW COMPLIANCE CONSENSUS

| Governing Law | Status | Finding |
|---|---|---|
| Brand Visual Design System (colors) | ❌ VIOLATED | `#f7931a` and `#8a2be2` used instead of `#CC2222` and `#0A0A0F`. Pervasive violation throughout stylesheet. |
| Brand Visual Design System (typography) | ❌ VIOLATED | Inconsistent font stack; `JetBrains Mono` not uniformly applied. |
| Anti-Algorithmic Ethos Principle | ❌ VIOLATED | Hardcoded zap amount reduces economic signal to a binary like — this violates the founding premise of the platform. |
| Value-for-Value / Sovereignty Principle | ❌ VIOLATED | No UI exists to claim earned sats. Sats-in with no withdrawal path is not sovereign. |
| WebLN Integration Standard | ✅ COMPLIANT | Correct approach, correctly implemented at the API level. |
| Curator Incentive Model | ⚠️ PARTIAL | Logic exists in backend; UI does not surface it. |
| Signal-Ranked Feed | ✅ COMPLIANT | Feed is sorted by `signal_score`. Logic is correct. |

---

## SECURITY CONSENSUS

No models identified active security vulnerabilities in the backend service layer, which is consistent with the high backend scores. However, the following warrant attention before production:

1. **Input Validation on URL Submission** — Not explicitly flagged but implied by the scraping architecture. Ensure URL inputs are sanitized and validated against SSRF (Server-Side Request Forgery) before being passed to the scraper.
2. **Lightning Invoice Handling** — No model audited the Lightning invoice generation path for amount validation. With a dynamic zap amount (the fix for the hardcoded value), ensure the amount field is validated server-side and cannot be manipulated to generate zero-sat or negative invoices.
3. **Claim Authorization** — The `process_claim` function exists but its authorization guard (ensuring only the rightful curator can claim their own balance) was not audited by any model. Verify this before exposing the UI.

**Priority order:** Claim authorization → Lightning amount validation → URL/SSRF validation.

---

## WORLD-CLASS GAP CONSENSUS
*Items mentioned by 2+ models as missing from a truly world-class product.*

### WCG1 — Real-Time Feed Updates Without Page Reload (Gemini + Grok)
A world-class proof-of-value platform shows the economic signal in motion. When someone zaps a post, the sats counter on that card should increment live for all viewers — no reload required. This transforms the feed from a static leaderboard into a living, breathing signal market. Both models flagged the reload-based UX as a fundamental experience failure.

### WCG2 — Visible, Animated Value Flow (Grok + GPT-4o)
The moment a zap lands, users should feel it — an animation, a counter tick, a visual pulse that communicates "value just moved." This is not cosmetic; for this audience, it is the product. The sats flowing is the whole point. Both models mentioned the need for immediate, visceral feedback that the economic signal was received.

### WCG3 — Transparent, Auditable Ranking (Gemini + Grok)
A world-class anti-algorithmic platform does not just claim to be transparent — it proves it. Both models called for on-card explanation of ranking factors, with Gemini specifically recommending an info tooltip on the signal score. The dream-state version of this is a public, linkable methodology page: "Here is exactly how content rises on Value Stream. There are no hidden factors."

---

## FINAL ACTION PLAN
*Sorted by consensus priority.*

| Priority | Change | File:Line | Models | Why |
|---|---|---|---|---|
| **P0 CRITICAL** | Remove hardcoded `1000` sat zap amount; replace with custom-amount modal/input triggered by ZAP button | `value_stream.html:455` | Gemini (unique, elevated) | Hardcoded amount reduces the core mechanic to a binary like button, invalidating the entire "Proof of Value" thesis |
| **P0 CRITICAL** | Build Sovereign Claim Portal UI — claimable balance display + Lightning Address withdrawal form connecting to existing `get_claimable_balance` and `process_claim` | New template + `value_stream_service.py:500-654` | Gemini/Grok (consensus-tier) | Earning sats with no withdrawal path is indistinguishable from a points scam to a Bitcoin maximalist; sovereignty requires closing the loop |
| **P0 CRITICAL** | Systematic brand color replacement: all `#f7931a`, `#8a2be2` → `#CC2222`; all backgrounds → `#0A0A0F`; enforce `JetBrains Mono` typography throughout | `value_stream.html:16-237` (pervasive) | ALL 3 | Brand trust is table stakes; color non-compliance signals an unfinished or amateur product to the target audience |
| **P0 CRITICAL** | Rewrite hero section with ideologically sharp, anti-algorithmic copy communicating the proof-of-value ethos | `value_stream.html:246-249` | ALL 3 | First impression completely fails to differentiate from a generic link aggregator; must hook a skeptical Bitcoin maximalist audience on first contact |
| **P1 HIGH** | Fix broken Twitter/X platform badge CSS: standardize `return "x"` → `return "twitter"` in service OR add `.platform-x` CSS rule | `value_stream_service.py:221` + `value_stream.html:83` | Gemini (unique, high confidence) | X/Twitter is likely the dominant content source for this audience; a broken badge on every such post is a high-visibility defect |
| **P1 HIGH** | Replace all `alert()` and `window.location.reload()` calls with a non-blocking toast notification system; animate sats counter in-place on successful zap | `value_stream.html:435-436, 438, 441, 461-462, 465, 468` | Gemini + Grok | Jarring browser dialogs and full-page reloads are unprofessional and destroy the flow of the core interaction |
| **P1 HIGH** | Seed feed with 3–5 genesis posts (Bitcoin whitepaper, foundational essays), clearly labeled `[Genesis]`, with zero initial sats | `value_stream.html:331-337` + view function | ALL 3 | Empty feed communicates abandonment; genesis posts demonstrate the mechanic and create immediate perceived value while preserving authenticity |
| **P1 HIGH** | Surface curator split visually on each content card; add persistent "Your Earnings" indicator for logged-in curators | `value_stream.html:274` + card template | Grok + GPT-4o | Invisible incentive model defeats the purpose of having one; curators must see value flowing to them to be motivated to curate |
| **P1 HIGH** | Add signal score transparency tooltip/info icon explaining the ranking formula in plain language ("total sats weighted by recency — no hidden factors") | `value_stream.html:291` | Grok + Gemini | An unexplained score looks algorithmic — the exact thing the platform rejects; transparency is a core value that must be demonstrated, not claimed |
| **P2 MEDIUM** | Implement real-time feed updates via WebSocket or SSE — sats counter animates for all viewers when a zap lands without requiring reload | `value_stream.html` (new JS) | Gemini + Grok | Transforms static leaderboard into a living signal market; this is the world-class experience gap |
| **P2 MEDIUM** | Add onboarding tooltip sequence or first-visit modal explaining "Curate → Zap → Rise → Earn" flow | `value_stream.html` (new modal) | Grok (unique) | Bridges comprehension gap for users unfamiliar with value-for-value mechanics |
| **P2 MEDIUM** | Audit `process_claim` authorization guard to confirm only rightful curator can claim their own balance | `value_stream_service.py:500-654` | Synthesizer (security) | Claim portal UI exposure makes this a security-relevant pre-condition |

---

## CYCLE 2 VERDICT

**NOT PRODUCTION READY.**

After two full cycles of independent 3-model review, the consensus is unambiguous: the backend is strong (7.5/10) and should not be touched, but the frontend has both functional defects and UX failures that would cause the MVP to actively undermine the platform's credibility with its target audience.

**The two absolute final blockers before any production consideration:**

1. **The hardcoded zap amount** — This is not a UI polish issue. It is a logical contradiction of the platform's founding premise. Shipping "Proof of Value" with a fixed zap is shipping a lie to an audience that will immediately see through it.

2. **No UI for claiming earned sats** — The backend is complete. The frontend has nothing. Curators cannot withdraw. For a Bitcoin sovereignty platform, this is the equivalent of promising self-custody and delivering an IOU. It must be built before any real curator is invited to use the platform.

Everything else — the hero rewrite, brand colors, empty state, toast notifications — is important and should be fixed, but these two issues are the ones that would cause a Bitcoin maximalist to publicly dismiss the project as vaporware. Fix them first.

---

## SECOND PASS PROMPT
*Ready to fire into Claude Code.*

```
Read ~/protocol_pulse/docs/gospels/VISUAL_DESIGN_SYSTEM.md.
Read ~/protocol_pulse/docs/audits/value-stream-mvp_CONSENSUS_C2.md.

This is the FINAL PASS for value-stream-mvp.
The first build was reviewed by 3 independent AI models across 2 cycles.
Implement every P0 and P1 item from the consensus. Use judgment on P2.

PRIORITY ACTION PLAN:

P0 CRITICAL | Remove hardcoded 1000-sat zap amount; replace with a custom-amount
              modal/input triggered by the ZAP button. The amount must be
              user-specified to preserve the economic signal mechanic.
              | value_stream.html:455

P0 CRITICAL | Build the Sovereign Claim Portal UI. Create a new page or dashboard
              section where a logged-in curator can view their claimable balance
              and submit a Lightning Address for withdrawal. Connect to the
              existing get_claimable_balance and process_claim functions.
              | New HTML template + value_stream_service.py:500-654

P0 CRITICAL | Systematic brand compliance fix. Replace ALL non-brand colors
              (#f7931a, #8a2be2, and any other non-spec values) with the official
              palette: Primary Red #CC2222, Background #0A0A0F, and spec'd
              secondaries per VISUAL_DESIGN_SYSTEM.md. Enforce JetBrains Mono
              as the universal font. This is pervasive throughout the stylesheet.
              | value_stream.html:16-237 (entire <style> block)

---

# WINNER DETERMINATION

# WINNER: **Gemini**

Gemini delivered the highest-quality analysis across both cycles by correctly identifying the most consequential finding in the entire audit — the missing Sovereign Claim Portal UI — which all other models initially missed. Its technical grounding was superior (backend scored 8/10 vs. 7/10 from others, confirmed accurate by consensus), its recommendations were the most specific and implementable (e.g., explicitly linking `process_claim`/`get_claimable_balance` backend logic to the missing UI surface), and it demonstrated genuine self-correction in Cycle 2 by honestly crediting other models while still contributing net-new insight rather than merely summarizing consensus.

---

# FINAL SECOND-PASS PRIORITY LIST

Ordered by: user impact × implementation urgency × confirmed cross-model consensus.

---

## PRIORITY 1 — CRITICAL / SHIP BLOCKER
*Must be resolved before any user-facing launch.*

### P1-A — Expose the Sovereign Claim Portal in the UI
**Source:** Gemini (Cycle 1 + 2), confirmed unanimous in Cycle 2
**File/Line:** `value_stream.html` — no current implementation; backend at `value_stream_service.py` lines 500–653
**What:** The backend has fully functional `process_claim` and `get_claimable_balance` logic. The UI exposes none of it. Without a claim interface, earned sats are trapped — making the entire value-for-value promise a lie and the curator incentive system a points game rather than a sovereign economy.
**Action:** Build a persistent "Your Balance" widget visible to authenticated curators showing claimable sats, a "Claim to Lightning Wallet" button invoking the backend claim flow, and clear confirmation feedback on withdrawal success/failure.

---

### P1-B — Replace Hero Section Copy with Ideologically Sharp Messaging
**Source:** Unanimous (all 3 models, Cycle 1 + 2); Consensus Finding U1
**File/Line:** `value_stream.html`, lines 246–249
**What:** Current subtitle is generic corporate language indistinguishable from any Web2 aggregator. First impression fails the target audience completely.
**Action:** Replace with defiant, high-conviction copy:
> *"No algorithms. No engagement farming. No dopamine loops. Economic signal surfaces the truth. Your sats are your vote."*

Ensure headline and CTA button copy reinforce this framing throughout the hero section.

---

### P1-C — Redesign Empty State as a Pioneer Invitation
**Source:** Unanimous (all 3 models); Consensus Finding U2
**File/Line:** `value_stream.html`, lines 331–337
**What:** A blank feed communicates abandonment. For a new user, it destroys confidence before any interaction occurs.
**Action:** Pre-populate with 3–5 manually curated "genesis" posts representing the platform's ideal content signal. Overlay with copy framing the user as an early pioneer: *"You're one of the first. The feed is yours to shape."* This simultaneously solves the cold-start problem and reinforces the ethos.

---

## PRIORITY 2 — HIGH / PRE-LAUNCH REQUIRED
*Resolve within first sprint after core blockers are cleared.*

### P2-A — Reframe UI Language from Submission to Signaling
**Source:** Grok + Gemini, Cycle 1; confirmed Cycle 2
**File/Line:** `value_stream.html`, line 271 (submit button); related form labels
**What:** "Submit" is Web2 vocabulary. It frames the user as a content uploader, not an economic signal-sender.
**Action:** Replace "Submit" → **"Signal This"** or **"Curate"**. Replace any "Post" references with **"Signal."** Audit all button and label copy for Web2 vocabulary and reframe throughout.

---

### P2-B — Add Real-Time Zap Feedback
**Source:** GPT-4o (Cycle 2 new finding); corroborated by UX/Onboarding consensus score of 2.5/10
**File/Line:** `value_stream.html`, lines 445–470 (WebLN zap handler)
**What:** After a zap fires, there is no immediate, satisfying confirmation that value was sent and the signal score updated. This breaks the core feedback loop.
**Action:** On successful zap: animate the signal score increment in real-time, display a brief toast notification (*"⚡ 21 sats sent — signal boosted"*), and visually re-rank the post if its score crosses a threshold. On failure: surface a human-readable error with recovery options.

---

### P2-C — Enforce Brand Color and Typography Compliance
**Source:** All 3 models, Cycle 1; GPT-4o + Grok Cycle 2
**File/Line:** `value_stream.html`, global styles
**What:** Color and typography deviate from established brand identity, creating visual inconsistency across the platform.
**Action:** Audit all color values and font declarations against the brand spec. Enforce via CSS variables already defined in the design system. Do not introduce new colors or typefaces outside the spec without explicit approval.

---

## PRIORITY 3 — MEDIUM / POST-LAUNCH ITERATION
*Schedule in second sprint; does not block launch but degrades experience.*

### P3-A — Display Signal Score Prominently and Explain Its Derivation
**Source:** Grok (Cycle 1, Q1); Gemini (Cycle 1, Verifiability pillar)
**File/Line:** `value_stream.html`, line 291; `value_stream_service.py`, lines 290–302
**What:** Signal score exists in the backend and appears in the UI but is not visually prominent and its meaning is unexplained. Bitcoin maximalists need to *verify*, not trust.
**Action:** Display signal score as the dominant metric on each content card. Add a one-tap tooltip or expandable row showing: total sats zapped, number of unique zappers, and curator multiplier. This satisfies "don't trust, verify" and builds confidence in the ranking system.

---

### P3-B — Improve Onboarding Flow for Lightning Wallet Connection
**Source:** GPT-4o (Cycle 1, Q1); consensus UX score 2.5/10
**File/Line:** `value_stream.html`, WebLN initialization sequence
**What:** New users without a WebLN-compatible wallet hit a dead end with no guidance.
**Action:** Detect absence of WebLN on page load and surface a non-blocking banner with: a brief explanation of why Lightning is needed, links to 2–3 recommended wallets (Alby, Zeus, Phoenix), and a "I'll do this later — let me browse first" escape hatch so read-only browsing remains accessible.

---

## IMPLEMENTATION ORDER SUMMARY

| Priority | Item | Owner Surface | Effort Estimate |
|---|---|---|---|
| P1-A | Sovereign Claim Portal UI | Frontend + API wiring | High |
| P1-B | Hero section copy rewrite | Frontend / Copy | Low |
| P1-C | Empty state → Genesis feed | Frontend + Content | Medium |
| P2-A | UI language reframing | Frontend / Copy | Low |
| P2-B | Real-time zap feedback | Frontend (JS) | Medium |
| P2-C | Brand compliance audit | Frontend / CSS | Low |
| P3-A | Signal score transparency | Frontend | Medium |
| P3-B | Lightning onboarding flow | Frontend | Medium |

---

*P1-B and P2-A are low effort and should be completed in the same commit — they are copy changes with outsized first-impression impact. P1-A is the highest-stakes item and should be scoped as its own ticket with backend API contract review before frontend work begins.*