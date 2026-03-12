# Foundation Spec: Oracle Sovereignty Assessment — Avatar-Powered Tool Recommender  
# Protocol Pulse — Feature Spec v1.0
# Status: Foundation Layer — Ready for CC build session

---

## CONCEPT

The Oracle avatar doesn't just answer questions — it **assesses your sovereignty posture** and 
recommends your next move. A 5-question conversational quiz that feels like talking to a 
well-traveled cypherpunk advisor, not filling out a form.

This is the bridge between Oracle (trust/engagement) and Sovereignty Stack (conversion/onboarding).
It also feeds the Curated Mining affiliate funnel naturally.

**Entry points:**
- `/sovereignty/quiz` — standalone quiz page
- Oracle chat: user can type "assess me" or "what should I use?" → triggers quiz flow
- Homepage CTA: "Find Your Sovereignty Score"
- `/oracle` page: secondary CTA button below main Oracle interface

---

## QUIZ ARCHITECTURE

### The 5 Questions (conversational, not checkbox)

The avatar speaks each question. User selects from 2-4 options OR types freely (typed responses 
parsed by Claude Sonnet for intent classification).

```
Q1: CURRENT STACK — "Let's start with where you are. Which of these describes you?"
  A) "I use Gmail, iMessage, and keep my money in a bank" → SCORE: Sovereign=0
  B) "I use Signal sometimes but still on big tech mostly" → SCORE: Sovereign=1
  C) "I've got a hardware wallet, use ProtonMail, on Signal" → SCORE: Sovereign=3
  D) "Running my own node, self-custody, Mullvad, Tor regularly" → SCORE: Sovereign=5

Q2: BIGGEST CONCERN — "What keeps you up at night? What are you most trying to protect against?"
  A) "Government surveillance and financial censorship"
  B) "Corporate data harvesting and manipulation"
  C) "My savings being inflated or confiscated"
  D) "All of it — I want full spectrum sovereignty"

Q3: BITCOIN POSTURE — "Where are you with Bitcoin?"
  A) "I've heard of it but haven't bought any"
  B) "I own some but it's on an exchange"
  C) "I self-custody on a hardware wallet"
  D) "Running a node, lightning wallet, mining"

Q4: THREAT MODEL — "Who are you protecting yourself from primarily?"
  A) "Advertisers and big tech"
  B) "Employers and social pressure (cancel culture)"
  C) "Financial institutions and government overreach"
  D) "I want privacy as a baseline — everyone's a potential adversary"

Q5: COMMITMENT LEVEL — "How deep are you willing to go?"
  A) "Easy wins only — I want better privacy without much friction"
  B) "I'll put in a weekend — teach me the important stuff"
  C) "I'm ready to overhaul my setup — all in"
  D) "I'm already technical — point me to advanced tools"
```

---

## SCORING & RECOMMENDATION ENGINE

### Sovereignty Tiers (computed from Q1-Q5 scores)

```python
TIERS = {
  "newbie": {
    "score_range": (0, 4),
    "title": "Sovereignty Initiate",
    "avatar_response": "You're just getting started, and that's actually the most 
      exciting place to be. The biggest gains in privacy and financial sovereignty 
      come from your first three moves. Here's exactly where I'd start...",
    "priority_tools": ["signal", "protonmail", "duckduckgo", "bitcoin-electrum"],
    "first_move": "Get off SMS. Signal takes 3 minutes.",
    "bitcoin_cta": "Your first step to financial sovereignty",
    "affiliate_push": "curated_mining_intro"
  },
  "emerging": {
    "score_range": (5, 9),
    "title": "Sovereignty Practitioner", 
    "avatar_response": "You've made real moves. You're past the starting line — 
      most people never get here. Now it's about closing the gaps. 
      Here's what your threat model suggests you're still exposed on...",
    "priority_tools": ["mullvad", "tor-browser", "tails-os", "matrix-element"],
    "first_move": "Your exchange is a single point of failure. Let's fix that.",
    "bitcoin_cta": "Move to self-custody — hardware wallet guide",
    "affiliate_push": "hardware_wallet_comparison"
  },
  "advanced": {
    "score_range": (10, 14),
    "title": "Sovereignty Architect",
    "avatar_response": "You've built something real. The question now is redundancy, 
      and then helping others. Here are the gaps I see in most advanced setups...",
    "priority_tools": ["pi-hole", "nextcloud", "gpg", "ipfs"],
    "first_move": "Your home network is probably still leaking metadata.",
    "bitcoin_cta": "Have you considered running a node? Here's why it matters.",
    "affiliate_push": "curated_mining_advanced"
  },
  "sovereign": {
    "score_range": (15, 20),
    "title": "Full Sovereign",
    "avatar_response": "You're in rare company. Most people will never get here. 
      The work now is to make this accessible for people who want to follow. 
      Here's what the cutting edge looks like...",
    "priority_tools": ["session", "ipfs", "hugging-face", "tails-os"],
    "first_move": "Consider running infrastructure others can rely on.",
    "bitcoin_cta": "Have you considered mining? The full stack awaits.",
    "affiliate_push": "curated_mining_full"
  }
}
```

---

## AVATAR INTEGRATION

### How the Avatar Delivers Results

After Q5, avatar generates a **personalized 60-90 second spoken response** using:

```python
RESULT_PROMPT = """
You are the Oracle — a cypherpunk advisor who has seen how centralized systems fail.
You've just assessed {user_name or "this user"} and they scored {score}/20.
Their tier is: {tier_title}
Their biggest concern: {q2_answer}
Their Bitcoin posture: {q3_answer}

Deliver their sovereignty assessment in 80-100 words. Tone: direct, earned, no fluff.
You're a trusted advisor, not a salesperson. Acknowledge what they've built.
Name their 2-3 highest-priority next moves specifically.
End with one sentence that connects their threat model to why this matters.
Do NOT say "sovereignty" more than once. Vary your language.
"""
```

This response is:
1. Fed to Oracle TTS (Jessica voice via ElevenLabs) → spoken aloud
2. Displayed as text below the avatar
3. Followed by 3-4 tool cards (priority recommendations)
4. CTA button: "Start with [first_move tool]" → links to `/sovereignty/tool/[slug]`

---

## AFFILIATE FUNNEL INTEGRATION

### Curated Mining Natural Entry Points

**Tier: Newbie**
→ "Before anything else: do you own any Bitcoin?"
→ If no: "Here's the 5-minute guide to your first purchase"
→ CTA: "When you're ready to go deeper — Curated Mining helps serious investors get exposure the right way" (link to curatedmining.com)

**Tier: Emerging**
→ "Your next big move: get off exchanges"
→ Hardware wallet comparison card (Coldcard vs Ledger vs Trezor)
→ "For investors who want full exposure without the technical setup — Curated Mining handles everything"

**Tier: Advanced/Sovereign**
→ "Have you considered mining? It's the most sovereign form of Bitcoin acquisition"
→ "Curated Mining is built for exactly your profile — white-glove, serious investors"
→ Direct to john@curatedmining.com or contact form

### RNS.ID / Palau Digital Residency
- Appears for Tier: Advanced + Sovereign
- "Your sovereignty stack is solid. Have you considered your digital residency?"
- $300/referral — referralCode=KKM73K

---

## FRONTEND SPEC

### Quiz Page (`/sovereignty/quiz`)

```
Layout:
- Full dark background (#06070b)
- Centered card, max-width 680px
- Progress bar: 5 steps, gold fill
- Avatar video loop: Oracle idle animation (3s loop, top of card)
- Question text: Inter 700, 28px, white
- Answer options: cards with hover glow (gold border on hover)
- "Oracle is thinking..." state between Q and next Q (1.2s delay, avatar "thinking" expression)
- Results: avatar speaks + tool cards appear one by one (staggered 0.3s CSS animation)
```

### State Machine
```
IDLE → Q1 → Q2 → Q3 → Q4 → Q5 → PROCESSING (1.5s) → RESULTS → TOOL_CARDS → CTA
                                                          ↓
                                              Oracle speaks result (avatar video)
```

### Session Storage
```javascript
// Store quiz results for personalization
sessionStorage.setItem('sovereignty_score', score)
sessionStorage.setItem('sovereignty_tier', tier)
sessionStorage.setItem('priority_tools', JSON.stringify(tools))
// Oracle chat reads these → personalizes all future responses in session
```

---

## ORACLE CHAT INTEGRATION

Once quiz is complete, the Oracle avatar's system prompt in the main chat gets augmented:

```python
ORACLE_SYSTEM_AUGMENTATION = """
This user has completed the Sovereignty Assessment.
Score: {score}/20 | Tier: {tier}
Biggest concern: {q2}
Bitcoin posture: {q3}

When they ask about tools, privacy, Bitcoin, or security:
- Prioritize recommendations matching their tier
- Reference their specific gaps (from quiz answers)
- For finance questions, always acknowledge their Bitcoin posture level
- Affiliate mentions: {affiliate_push} is appropriate for their tier
"""
```

---

## ACCEPTANCE CRITERIA

- [ ] `/sovereignty/quiz` loads with Oracle avatar idle loop playing
- [ ] 5 questions delivered in sequence, answer selection advances automatically
- [ ] Scoring engine calculates tier correctly for all 4 tiers
- [ ] Oracle speaks personalized result (TTS via avatar generate endpoint)
- [ ] 3-4 tool recommendation cards appear after avatar speaks
- [ ] Each tool card links to `/sovereignty/tool/[slug]`
- [ ] Affiliate CTA appears appropriate to tier (not hardcoded — tier-driven)
- [ ] Quiz results stored in sessionStorage
- [ ] Oracle main chat reads sessionStorage quiz data and personalizes responses
- [ ] Mobile: full quiz flow works on iPhone Safari
- [ ] "Retake quiz" button on results page
- [ ] Quiz completion tracked in analytics (Discord webhook: "Quiz completed: {tier}")

---

## BUILD ORDER (for CC session)

1. `sovereignty_tools.json` registry (25 tools, full data)
2. Flask routes: `/sovereignty`, `/sovereignty/tool/<slug>`, `/sovereignty/quiz`, `/api/sovereignty/tools`
3. `sovereignty.html` template (hub + cards + filter)
4. `sovereignty_tool.html` (individual tool deep-dive)
5. `sovereignty_quiz.html` (avatar + 5-question flow + results)
6. Quiz scoring engine (`sovereignty_scorer.py`)
7. Oracle chat integration (system prompt augmentation from sessionStorage)
8. Nav update: "Sovereignty Stack" in More dropdown
9. Cross-link from `cypherpunks.html` and `freedom_tech.html`
10. Regression test + commit

