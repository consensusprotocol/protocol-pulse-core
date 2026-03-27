Read PIPELINE_LAWS.md briefly.

TASK: Fix all admin dashboard metrics widgets

The /admin dashboard loads but all metric widgets show spinners forever.
Route is core/routes.py line ~2495 def admin_dashboard()

1. Check what data the admin dashboard template expects:
   cat ~/protocol_pulse/templates/admin/dashboard.html | grep -E "{{|total_|recent_|grade|pipeline|render"

2. The dashboard currently only receives: total_articles, published_articles, total_podcasts, recent_articles
   Add these to the route:
   - latest_render_grade (from overnight_loop.log - grep GRADE | tail -1)
   - pipeline_status (DEGRADED/OK from heartbeat)
   - oracle_status (curl localhost:8200/health)
   - article_count_24h (articles created in last 24h)
   - render_iteration (from log)

3. Find what widgets exist in dashboard.html that have no data:
   grep -n "data-metric\|widget\|spinner\|loading\|LAST_VIDEO\|NEXT_BRIEF" ~/protocol_pulse/templates/admin/dashboard.html | head -20

4. For each broken widget, add the corresponding data to the Flask route and pass it to render_template
5. Reload gunicorn: kill -1 $(pgrep -f "gunicorn.*5000" | grep -v golds | grep -v relay | head -1)
6. Test: curl -s -b /tmp/tc6.txt http://localhost:5000/admin | grep -c "loading\|spinner"
7. git add -A && git commit -m "fix(admin): populate all dashboard metrics widgets" && git push
