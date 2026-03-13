Read PIPELINE_LAWS.md first. Then fix the site navigation.

## TASK: Add missing pages to site navigation in base.html

File: ~/protocol_pulse/templates/base.html

### WHAT'S CURRENTLY IN DESKTOP NAV (lines ~147-162):
Intel, Media, Podcasts, Markets, Charts, Live Pulse, Stage, Oracle, Maps, Merch

### WHAT'S LIVE BUT MISSING FROM NAV:
- /briefings — Oracle Briefings (video episodes) — HIGH PRIORITY, this is a flagship feature
- /clips — Signal Clips
- /signal-terminal — Signal Terminal
- /media-terminal — Media Terminal
- /chat — Ask Alex (AI chat)
- /dashboard — User Dashboard
- /pulse-forecast — Pulse Forecast (already in mobile nav but not desktop)

### WHAT TO DO:
1. Restructure the desktop nav links into a cleaner dropdown-style nav with logical groupings. The current flat list is getting too long. Use this structure:

KEEP AS TOP-LEVEL LINKS (most important, always visible):
- Intel (/articles)
- Briefings (/briefings) — add with gold color like Oracle: style="color:var(--pp-amber);"
- Media (/media)
- Markets (/market)
- Oracle (/oracle) — keep amber
- Stage (/stage) — keep teal

ADD A "More" DROPDOWN containing:
- Podcasts (/podcasts)
- Charts (/charts)
- Signal Terminal (/signal-terminal)
- Live Pulse (/bitfeed-live)
- Clips (/clips)
- Media Terminal (/media-terminal)
- Forecast (/pulse-forecast)
- Maps (/map)
- Merch (/merch)

The dropdown should use vanilla CSS/JS that already exists in pp-core.css or pp-style.css — check if there's already a dropdown pattern (class pp-dropdown or similar) before writing new CSS. If no dropdown exists, use a simple hover/click pattern with inline style.

2. Add ALL missing pages to the mobile nav as well (the pp-nav__mobile div). Mobile nav should include every page.

3. Do NOT change anything else in base.html — header, footer, CSS links, scripts stay identical.

4. After editing, verify the file has no Jinja2 syntax errors:
   python3 -c "from jinja2 import Environment, FileSystemLoader; env = Environment(loader=FileSystemLoader('templates')); env.get_template('base.html'); print('Jinja2 OK')"

5. Reload Flask (gunicorn) to test:
   kill -HUP $(cat ~/protocol_pulse/gunicorn.pid) 2>/dev/null || pkill -HUP gunicorn
   sleep 3
   curl -s -o /dev/null -w "%{http_code}" https://protocolpulse.io/ 

6. Commit: git add templates/base.html && git commit -m "feat(nav): add Briefings, Clips, Signal Terminal, Media Terminal, Chat to nav; restructure desktop nav with More dropdown" && git push

IMPORTANT: This is a templates-only change. Do NOT touch any .py files, CSS files, or anything else.