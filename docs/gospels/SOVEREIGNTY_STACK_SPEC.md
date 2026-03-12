# Foundation Spec: Sovereignty Stack — Cypherpunk Tools Section
# Protocol Pulse — Feature Spec v1.0
# Status: Foundation Layer — Ready for CC build session

---

## PLACEMENT DECISION

**Route:** `/sovereignty` — standalone page, linked from:
- Nav: "More" dropdown → "Sovereignty Stack" (between Signal Terminal and Live Pulse)
- `cypherpunks.html` existing page → feature block linking to /sovereignty
- `freedom_tech.html` — merge or cross-link
- Oracle avatar funnel → recommends tools → links to /sovereignty/[tool-slug]

**Why its own page, not embedded:** The tool count (25+), the interactivity (quiz + filtering), 
and the affiliate/onboarding potential make this a destination, not a section.

---

## PAGE ARCHITECTURE

```
/sovereignty                    → Hub page (category grid + quiz CTA)
/sovereignty/[category]         → Category filter view
/sovereignty/tool/[slug]        → Individual tool deep-dive page
/sovereignty/quiz               → Avatar-powered sovereignty assessment
```

---

## VISUAL DESIGN SYSTEM (follows VISUAL_DESIGN_SYSTEM.md gospel)

### Card Component Spec
Each tool gets a Card with:
- **Header bar** — category color accent (see color map below)
- **Icon** — custom SVG or emoji fallback, 48px
- **Tool name** — Inter 900, 22px, white
- **Sovereignty tagline** — 1 line, gold (#f8c15c), italic
- **Overview** — 2-3 sentences, gray text
- **Setup steps** — numbered list, max 4 steps, collapsible
- **Affiliate/onboard CTA** — where applicable, amber button
- **"Why Sovereign?"** badge — teal pill, 1-phrase
- **Difficulty meter** — 1-5 dots (Beginner → Advanced)
- **Privacy score** — padlock icons 1-5

### Category Color Map
```
Communication    → cyan    (#5de4ff)   🗨
Privacy/Security → red     (#ff3b5f)   🔒
AI & Tech        → lime    (#89ffb8)   🤖
Activism         → gold    (#f8c15c)   ✊
Decentralized Fi → amber   (#f97316)   ₿
```

### Page Layout
- Hero: full-width dark banner, "Your Sovereignty Stack" headline, quiz CTA button
- Category filter pills (sticky on scroll)
- Masonry card grid: 3 cols desktop, 2 tablet, 1 mobile
- Each card: hover lifts with gold border glow
- Expanded state: card flips/expands to show full setup guide

---

## COMPLETE TOOL REGISTRY (25 tools)

### CATEGORY 1: COMMUNICATION
```json
{
  "slug": "mastodon",
  "name": "Mastodon",
  "tagline": "Social media you actually own",
  "category": "communication",
  "difficulty": 2,
  "privacy_score": 4,
  "url": "https://joinmastodon.org",
  "overview": "Decentralized, federated social network. No algorithm. No ads. No deplatforming from a single point. Host your own instance or join one.",
  "setup_steps": [
    "Go to joinmastodon.org → pick a server aligned with your interests",
    "Create account — no real name required",
    "Follow people via @user@instance.social format",
    "Optional: self-host via Docker (guide at docs.joinmastodon.org)"
  ],
  "why_sovereign": "No CEO can silence you",
  "affiliate": null,
  "icon": "🦣"
}

{
  "slug": "signal",
  "name": "Signal",
  "tagline": "The gold standard of private messaging",
  "category": "communication", 
  "difficulty": 1,
  "privacy_score": 5,
  "url": "https://signal.org",
  "setup_steps": [
    "Download from signal.org (not app stores — sideload for max privacy)",
    "Verify contacts via Safety Numbers (Settings → Contact → Verify)",
    "Enable disappearing messages by default",
    "Use Note to Self as encrypted private notepad"
  ],
  "why_sovereign": "Your metadata stays yours",
  "affiliate": null
}

{
  "slug": "matrix-element",
  "name": "Matrix / Element",
  "tagline": "Encrypted, federated, self-hostable",
  "category": "communication",
  "difficulty": 3,
  "privacy_score": 5,
  "url": "https://element.io",
  "why_sovereign": "No single server owns your chats",
  "affiliate": null
}

{
  "slug": "session",
  "name": "Session",
  "tagline": "No phone number. No metadata. Just comms.",
  "category": "communication",
  "difficulty": 1,
  "privacy_score": 5,
  "url": "https://getsession.org",
  "why_sovereign": "Onion-routed — even Session can't see you",
  "affiliate": null
}
```

### CATEGORY 2: PRIVACY & SECURITY
```json
{
  "slug": "tor-browser",
  "name": "Tor Browser",
  "tagline": "Route your traffic through the world",
  "difficulty": 1,
  "privacy_score": 5,
  "url": "https://torproject.org",
  "why_sovereign": "Your IP is not your identity"
}

{
  "slug": "mullvad",
  "name": "Mullvad VPN",
  "tagline": "Pay with cash. They won't even know your name.",
  "difficulty": 1,
  "privacy_score": 5,
  "url": "https://mullvad.net",
  "affiliate_url": "https://mullvad.net",  // check affiliate program
  "why_sovereign": "Anonymous accounts, no email required"
}

{
  "slug": "protonmail",
  "name": "Proton Mail",
  "tagline": "Email that can't be read — even by Proton",
  "difficulty": 1,
  "privacy_score": 4,
  "url": "https://proton.me",
  "why_sovereign": "Swiss law + zero-access encryption"
}

{
  "slug": "tails-os",
  "name": "Tails OS",
  "tagline": "A computer with amnesia — by design",
  "difficulty": 3,
  "privacy_score": 5,
  "url": "https://tails.net",
  "why_sovereign": "Boots from USB. Leaves zero trace."
}

{
  "slug": "pi-hole",
  "name": "Pi-hole",
  "tagline": "Block every tracker on your network",
  "difficulty": 3,
  "privacy_score": 4,
  "url": "https://pi-hole.net",
  "why_sovereign": "Network-level ad/tracker blocking"
}

{
  "slug": "duckduckgo",
  "name": "DuckDuckGo",
  "tagline": "Search without being the product",
  "difficulty": 1,
  "privacy_score": 3,
  "url": "https://duckduckgo.com",
  "why_sovereign": "No search history. No profile."
}

{
  "slug": "gpg",
  "name": "GPG (GNU Privacy Guard)",
  "tagline": "Encrypt anything. Sign everything.",
  "difficulty": 4,
  "privacy_score": 5,
  "url": "https://gnupg.org",
  "why_sovereign": "Math protects your messages, not policy"
}
```

### CATEGORY 3: AI & TECH
```json
{
  "slug": "hugging-face",
  "name": "Hugging Face",
  "tagline": "Run AI locally — no corporate backdoor",
  "difficulty": 3,
  "privacy_score": 4,
  "url": "https://huggingface.co"
}

{
  "slug": "ipfs",
  "name": "IPFS",
  "tagline": "Unstoppable file storage",
  "difficulty": 3,
  "privacy_score": 3,
  "url": "https://ipfs.tech",
  "why_sovereign": "Content-addressed — can't be taken down"
}

{
  "slug": "f-droid",
  "name": "F-Droid",
  "tagline": "An app store that doesn't spy",
  "difficulty": 2,
  "privacy_score": 4,
  "url": "https://f-droid.org"
}

{
  "slug": "nextcloud",
  "name": "Nextcloud",
  "tagline": "Your cloud. Your server. Your rules.",
  "difficulty": 4,
  "privacy_score": 5,
  "url": "https://nextcloud.com"
}
```

### CATEGORY 4: ACTIVISM & TRANSPARENCY
```json
{
  "slug": "eff",
  "name": "Electronic Frontier Foundation",
  "tagline": "The legal army for your digital rights",
  "difficulty": 1,
  "privacy_score": null,
  "url": "https://eff.org"
}

{
  "slug": "opensecrets",
  "name": "OpenSecrets",
  "tagline": "Follow the money. All of it.",
  "difficulty": 1,
  "url": "https://opensecrets.org"
}

{
  "slug": "bellingcat",
  "name": "Bellingcat",
  "tagline": "Open-source intelligence for citizens",
  "difficulty": 2,
  "url": "https://bellingcat.com"
}
```

### CATEGORY 5: DECENTRALIZED FINANCE
```json
{
  "slug": "bitcoin-electrum",
  "name": "Electrum Wallet",
  "tagline": "Your keys. Your Bitcoin.",
  "difficulty": 2,
  "privacy_score": 4,
  "url": "https://electrum.org",
  "affiliate_url": "https://curatedmining.com",  // internal
  "why_sovereign": "Self-custody = no permission needed"
}

{
  "slug": "monero",
  "name": "Monero (XMR)",
  "tagline": "Untraceable by design, not by policy",
  "difficulty": 3,
  "privacy_score": 5,
  "url": "https://getmonero.org",
  "why_sovereign": "Ring signatures make surveillance impossible"
}
```

---

## FLASK ROUTES TO ADD

```python
@app.route('/sovereignty')
def sovereignty_hub():
    tools = get_all_tools()  # from tools registry JSON or DB table
    categories = get_categories()
    return render_template('sovereignty.html', tools=tools, categories=categories)

@app.route('/sovereignty/tool/<slug>')
def sovereignty_tool(slug):
    tool = get_tool_by_slug(slug)
    if not tool: abort(404)
    return render_template('sovereignty_tool.html', tool=tool)

@app.route('/sovereignty/quiz')
def sovereignty_quiz():
    return render_template('sovereignty_quiz.html')

@app.route('/api/sovereignty/tools')
def api_tools():
    category = request.args.get('category')
    tools = get_tools_filtered(category)
    return jsonify(tools)
```

---

## ACCEPTANCE CRITERIA

- [ ] `/sovereignty` loads HTTP 200 with all 25 tool cards
- [ ] Category filter pills work (JS filter, no page reload)
- [ ] Each card shows: icon, name, tagline, difficulty, privacy score, why-sovereign badge
- [ ] Card expand/collapse shows full setup steps
- [ ] Mobile: cards stack cleanly, no overflow
- [ ] `/sovereignty/tool/signal` loads individual tool page with full detail
- [ ] Nav "More" dropdown includes "Sovereignty Stack" link
- [ ] Tools registry stored in `sovereignty_tools.json` (not hardcoded in template)
- [ ] Visual matches VISUAL_DESIGN_SYSTEM.md: colors, typography, dark background
- [ ] zero JS console errors

