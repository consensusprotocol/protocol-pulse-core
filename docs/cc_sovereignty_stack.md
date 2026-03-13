Read these files first — mandatory before writing a single line of code:
1. cat ~/protocol_pulse/PIPELINE_LAWS.md
2. cat ~/protocol_pulse/docs/gospels/SOVEREIGNTY_STACK_SPEC.md
3. cat ~/protocol_pulse/templates/base.html | head -120  (for nav structure)
4. ls ~/protocol_pulse/templates/ | grep -i "cypher\|freedom\|sovereign"
5. grep -n "More.*dropdown\|moreDropdown\|sovereignty\|freedom_tech" ~/protocol_pulse/templates/base.html | head -20
6. cat ~/protocol_pulse/app.py | grep -n "def \|@app.route" | head -60

## TASK: BUILD SOVEREIGNTY STACK — /sovereignty page + nav integration

### WHAT TO BUILD (in order):

**Step 1 — sovereignty_tools.json registry**
Create ~/protocol_pulse/static/data/sovereignty_tools.json with all 25 tools from the spec.
Each tool: slug, name, tagline, category, difficulty (1-5), privacy_score (1-5 or null), 
url, overview (2-3 sentences), setup_steps (array, max 4), why_sovereign (1 phrase), 
affiliate_url (null unless specified), icon (emoji).

Categories: communication | privacy_security | ai_tech | activism | decentralized_finance

**Step 2 — Flask routes in app.py**
Add these routes (find the right place in app.py, after existing routes):

@app.route('/sovereignty')
def sovereignty():
    import json as _json
    tools = _json.load(open(f'{app.root_path}/static/data/sovereignty_tools.json'))
    categories = [
        {'id': 'all', 'label': 'All Tools', 'color': '#ffffff'},
        {'id': 'communication', 'label': 'Communication', 'color': '#5de4ff'},
        {'id': 'privacy_security', 'label': 'Privacy & Security', 'color': '#ff3b5f'},
        {'id': 'ai_tech', 'label': 'AI & Tech', 'color': '#89ffb8'},
        {'id': 'activism', 'label': 'Activism', 'color': '#f8c15c'},
        {'id': 'decentralized_finance', 'label': 'Decentralized Finance', 'color': '#f97316'},
    ]
    return render_template('sovereignty.html', tools=tools, categories=categories)

@app.route('/sovereignty/tool/<slug>')
def sovereignty_tool(slug):
    import json as _json
    tools = _json.load(open(f'{app.root_path}/static/data/sovereignty_tools.json'))
    tool = next((t for t in tools if t['slug'] == slug), None)
    if not tool:
        abort(404)
    return render_template('sovereignty_tool.html', tool=tool)

@app.route('/api/sovereignty/tools')
def api_sovereignty_tools():
    import json as _json
    tools = _json.load(open(f'{app.root_path}/static/data/sovereignty_tools.json'))
    category = request.args.get('category', 'all')
    if category != 'all':
        tools = [t for t in tools if t['category'] == category]
    return jsonify(tools)

**Step 3 — sovereignty.html template**
Create ~/protocol_pulse/templates/sovereignty.html

DESIGN RULES (follow VISUAL_DESIGN_SYSTEM.md gospel exactly):
- Background: #06070b
- Accent colors: cyan #5de4ff, red #ff3b5f, lime #89ffb8, gold #f8c15c, orange #f97316
- NO pure white (#ffffff) or pure black (#000000) — use #f0f0f0 and #06070b
- Typography: Inter for headlines (weight 900, tracking tight), JetBrains Mono for scores/data
- Gold info bar: the signature element at top of each card

LAYOUT:
- Extend base.html ({% extends 'base.html' %})
- Hero section: full-width, dark, with headline "Your Sovereignty Stack" + subheadline + 
  amber CTA button linking to /sovereignty/quiz ("Take the Assessment →")
- Category filter pills: sticky below hero, horizontal scroll on mobile
  Each pill color matches category (cyan/red/lime/gold/orange)
  "All" pill selected by default, highlighted white
- Tool cards: CSS grid, 3 cols desktop, 2 tablet, 1 mobile
  Each card:
  - Top color bar: 4px solid, category color
  - Icon: 36px emoji in dark circle
  - Category pill: small, category color
  - Tool name: Inter 800, 20px, #f0f0f0
  - Tagline: italic, gold #f8c15c, 14px
  - Overview: #888, 13px, 3 lines max
  - "Why Sovereign?" badge: teal pill, small
  - Difficulty dots: 5 dots, filled = category color
  - Privacy score: padlock icons (🔒 = filled, gray = empty)
  - "Setup Guide" accordion: click to expand steps as numbered list
  - CTA button (if affiliate_url): amber "Get Started →" linking to affiliate_url
  - Otherwise: gray "Visit Site →" linking to url
- Card hover: translateY(-4px), gold border glow (box-shadow: 0 0 20px rgba(248,193,92,0.3))
- Filter JS: vanilla JS, filter cards by data-category, smooth opacity transition

ACCESSIBILITY: aria-labels on all interactive elements, keyboard navigable

**Step 4 — sovereignty_tool.html**
Individual tool deep-dive. Same dark design.
- Full tool name + icon as hero
- Large overview paragraph
- Full setup steps (numbered, detailed)
- "Why Sovereign?" callout box in gold
- Privacy score + difficulty displayed prominently
- "Visit Site" primary CTA
- Affiliate CTA if applicable
- "← Back to Sovereignty Stack" breadcrumb

**Step 5 — Nav update in base.html**
Find the "More" dropdown in the desktop nav.
Add "Sovereignty Stack" as first item (most important):
<a class="dropdown-item" href="/sovereignty" style="color:#5de4ff;">
  🛡️ Sovereignty Stack
</a>

Also add to mobile nav in the same file.

Also add a PROMINENT HERO BUTTON on the homepage (find index.html or home template):
Look for the main hero/CTA section and add a teal "🛡️ Sovereignty Stack" card or button 
that links to /sovereignty. Make it visually distinct.

**Step 6 — Cross-links**
In cypherpunks.html: add a section at top linking to /sovereignty
In freedom_tech.html: add a section at top linking to /sovereignty

**Step 7 — Verify everything**
curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/sovereignty
curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/sovereignty/tool/signal
curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/api/sovereignty/tools

All must return 200.

**Step 8 — Regression test + commit**
cd ~/protocol_pulse && bash regression_test.sh
Must show zero FAILs.
git add static/data/sovereignty_tools.json templates/sovereignty.html templates/sovereignty_tool.html templates/base.html app.py
git commit -m "feat(sovereignty): /sovereignty hub + 25 tool cards + category filter + nav integration"
git push

## ACCEPTANCE CRITERIA (verify each before committing):
- [ ] /sovereignty returns 200
- [ ] /sovereignty/tool/signal returns 200  
- [ ] /api/sovereignty/tools returns JSON with 25 tools
- [ ] Category filter works (JS, no page reload)
- [ ] "Sovereignty Stack" visible in nav More dropdown
- [ ] Sovereignty Stack visible on homepage
- [ ] sovereignty_tools.json has all 25 tools with correct slugs
- [ ] Mobile: no horizontal overflow on card grid
- [ ] regression_test.sh: zero FAILs
