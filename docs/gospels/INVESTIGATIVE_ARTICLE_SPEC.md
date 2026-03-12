# Foundation Spec: Investigative Journalist Article Engine
# Protocol Pulse — Feature Spec v1.0
# Status: Foundation Layer — Ready for CC build session

---

## OVERVIEW

A daily deep-dive article series called **"The Dispatch"** — long-form investigative journalism (1,200–2,500 words) with a pro-Bitcoin, pro-sovereignty undertone. Written in the style of a foreign correspondent who has seen how centralized systems fail and understands why sound money matters. Not propaganda — rigorous, sourced, intellectually honest. The Bitcoin angle emerges naturally from the evidence.

**Tagline:** *"What the mainstream won't investigate. What history already proved."*

---

## ARTICLE DNA

### Tone & Voice
- Foreign correspondent meets financial historian
- Cites primary sources: IMF reports, central bank filings, court records, academic papers
- Never says "Bitcoin fixes this" — shows the failure, lets the reader conclude
- Pro-individual, anti-capture — not anti-government per se, anti-corruption
- Reads like Matt Taibbi meets Lyn Alden meets Michael Lewis

### Structure (every article)
1. **The Hook** (150 words) — Present-tense scene setting. One vivid moment that captures the crisis
2. **The Setup** (200 words) — What was the official story? What did institutions claim?
3. **The Investigation** (600–900 words) — What actually happened. Primary sources. Named actors. Data.
4. **The Pattern** (200 words) — How this connects to a larger systemic theme (monetary sovereignty, currency debasement, institutional capture, censorship, surveillance capitalism)
5. **The Parallel** (150 words) — A present-day echo. Where is this happening now?
6. **The Sovereign Takeaway** (100–200 words) — What tools, knowledge, or mental models protect individuals from this pattern. Bitcoin, hard money, self-custody, privacy tools — named where genuinely relevant

---

## STORY CATEGORY TAXONOMY

### Category A: Monetary Sovereignty Failures
Iceland 2008–2012 (prosecuted bankers, rewrote constitution, rejected IMF)
Cyprus 2013 (overnight bank bail-in, savings confiscated)
Argentina 2001 (corralito — savings accounts frozen, peso devalued 75%)
Zimbabwe 2007–2009 (100 trillion dollar notes, agricultural collapse)
Weimar Germany 1921–1923 (wheelbarrows of cash, middle class wiped)
Lebanon 2019–present (banks locked citizens out of dollar accounts)
Venezuela 2013–present (bolivar hyperinflation, food rationing)
Turkey 2021–present (lira lost 80%, Erdogan fired central bank governors)

### Category B: Institutional Capture
The 2008 Bailout (TARP — who got paid, who got fired — nobody)
IMF Structural Adjustment Programs (austerity sold as medicine, populations bear cost)
BIS and the Tower of Basel (the bank for central banks, unaccountable by design)
Operation Choke Point (US DOJ using banks to kill legal industries)
Debanking (Nigel Farage, crypto companies, political dissidents, legal gun shops)

### Category C: Surveillance & Control
China's Social Credit System (implementation details, western adoption signals)
CBDCs (programmable money — what "expiry dates" and "approved merchants" actually mean)
Canada Trucker Convoy 2022 (Emergencies Act, accounts frozen without court order)
EU's MiCA regulation (crypto KYC overreach, self-custody restrictions)
PayPal's misinformation fine clause (October 2022 — $2,500 fine for "misinformation")

### Category D: The Builders (positive stories)
El Salvador's Bitcoin experiment (actual ground-level data, not pundit takes)
Prospera, Honduras (charter city, opt-in governance)
Colorado's 2022 Bitcoin tax payment (state-level adoption)
Baltic states and digital governance (Estonia's e-residency, minimal bureaucracy)
Lightning Network merchants in developing economies

---

## GENERATION PIPELINE

### Trigger
- Daily cron: 06:00 UTC
- 1 article per day from rotating category (A→B→C→D→A...)
- Story selected by: recency + uniqueness score (avoid repeating same country within 30 days)

### Research Phase (Claude Opus)
```python
RESEARCH_PROMPT = """
You are an investigative journalist for Protocol Pulse's 'The Dispatch' series.
Today's story topic: {topic}
Category: {category}

Research task:
1. Identify 5-8 specific, verifiable facts with source citations (IMF reports, court filings, 
   academic papers, official government documents, established news archives)
2. Name specific individuals where public record allows
3. Find the specific numbers: amounts stolen/lost/inflated, dates, percentages
4. Identify the systemic mechanism (how did institutional capture/debasement/surveillance enable this?)
5. Find a present-day parallel — where is this pattern repeating right now?

Output as JSON: {facts[], sources[], key_actors[], mechanism, present_parallel, bitcoin_relevance_score 1-10}
"""
```

### Writing Phase (Claude Opus with research JSON)
```python
WRITING_PROMPT = """
Write a 'Dispatch' article for Protocol Pulse using the research below.

Tone: Foreign correspondent. Rigorous. Evidence-first. Pro-individual.
Structure: Hook → Setup → Investigation → Pattern → Parallel → Sovereign Takeaway
Length: 1,400–2,000 words
Style rules:
- No "Bitcoin fixes this" — show the failure, let reader conclude
- Cite sources inline (e.g., "according to IMF Article IV consultation, 2009")
- Vivid opening scene — present tense, specific location, real person if possible
- The Bitcoin/sovereignty takeaway must be earned by the evidence, not bolted on
- End with a question, not a declaration

Research: {research_json}
"""
```

### Fact-Check Phase (Grok)
- Verify named individuals and dates
- Flag any claims that can't be sourced
- Return confidence score per claim

### Quality Gate
- Word count: 1,200–2,500
- Source count: minimum 4 citations
- Fact-check confidence: all claims > 70%
- Duplicate check: semantic similarity < 0.85 vs last 30 articles
- Bitcoin relevance score: 4–8 (not too low, not preachy)

---

## DATABASE SCHEMA ADDITIONS

```sql
-- Add to existing articles table
ALTER TABLE articles ADD COLUMN article_type VARCHAR(50) DEFAULT 'standard';
ALTER TABLE articles ADD COLUMN series VARCHAR(100);  -- 'The Dispatch'
ALTER TABLE articles ADD COLUMN word_count INTEGER;
ALTER TABLE articles ADD COLUMN source_citations JSONB;
ALTER TABLE articles ADD COLUMN fact_check_score FLOAT;
ALTER TABLE articles ADD COLUMN story_category VARCHAR(50);
ALTER TABLE articles ADD COLUMN read_time_minutes INTEGER;

-- New series table
CREATE TABLE article_series (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE,
    tagline TEXT,
    description TEXT,
    cover_image_url TEXT,
    article_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## FRONTEND DISPLAY

### Article Page Differentiation
- `article_type = 'dispatch'` → dark theme card with red "DISPATCH" badge
- Reading time shown prominently
- Source citations expandable at bottom
- "Part of The Dispatch series" breadcrumb
- Related dispatches sidebar (same category)

### Homepage Integration
- One featured Dispatch article always in hero slot
- "The Dispatch" section below main feed with distinct visual treatment

---

## ACCEPTANCE CRITERIA (for CC build session)

- [ ] `article_generator.py` has `generate_dispatch_article(topic, category)` function
- [ ] Research → write → fact-check → quality-gate pipeline runs end-to-end
- [ ] Daily cron at 06:00 UTC triggers one article
- [ ] Article stored with `series='The Dispatch'`, `article_type='dispatch'`
- [ ] Frontend renders dispatch articles with distinct visual treatment
- [ ] Source citations stored in JSONB and displayed on article page
- [ ] Category rotation enforced (no same category 2 days in a row)
- [ ] Live test: one manually-triggered dispatch article end-to-end

---

## SAMPLE TOPIC QUEUE (first 14 days)
1. Iceland 2008 — Citizens Who Jailed Their Bankers
2. Cyprus 2013 — The Day Europe Stole Savings Overnight
3. El Salvador Year 3 — What the Data Actually Shows
4. Operation Choke Point — How the DOJ Weaponized Banks
5. Lebanon's Dollar Trap — When Your Savings Aren't Yours
6. Canada 2022 — The Truckers and the Emergency Act
7. Weimar's Middle Class — Inflation as Class Warfare
8. Estonia's Digital Republic — What Minimal Government Looks Like
9. CBDCs — What "Programmable Money" Actually Means
10. Argentina's Corralito — The Night They Froze Everything
11. The BIS — The Unaccountable Bank That Runs Central Banks
12. Prospera, Honduras — Opt-In Governance in Practice
13. Turkey's Lira — What Happens When a President Fires the Fed
14. PayPal's $2,500 Misinformation Clause — The Day It Went Public
