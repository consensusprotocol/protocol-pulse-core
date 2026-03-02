#!/usr/bin/env python3
"""
Phase 1 Mega-Deploy — single request to Replit
Executes: avatar push, oracle template updates, media_unified deploy, route addition
"""
import base64, json, subprocess, time, sys

REPLIT_RELAY = "https://protocolpulse.replit.app/api/admin/exec"
REPLIT_TOKEN = "581b1076ca6d8a8809997d24f0869431ffd75c64de9ea703b6ab0f3e39fbd552"
WORKSPACE = "/home/runner/workspace"

def replit_exec(cmd, label="", max_retries=3):
    payload = json.dumps({"token": REPLIT_TOKEN, "cmd": cmd})
    for attempt in range(max_retries):
        result = subprocess.run(
            ["curl", "-s", "-X", "POST", REPLIT_RELAY,
             "-H", "Content-Type: application/json",
             "-d", payload],
            capture_output=True, text=True, timeout=60
        )
        resp = result.stdout.strip()
        if "429" in resp or "Too Many Requests" in resp:
            print(f"[{label}] RATE LIMITED — still hitting 429. Abort.")
            sys.exit(1)
        if resp:
            try:
                d = json.loads(resp)
                print(f"[{label}] rc={d.get('returncode')} stdout={d.get('stdout','')[:200]} stderr={d.get('stderr','')[:100]}")
                return d
            except:
                print(f"[{label}] raw: {resp[:200]}")
                return {}
        print(f"  [{label}] empty response, retry {attempt+1}...")
        time.sleep(2)
    return {}

# ──────────────────────────────────────────────────────────
# READ LOCAL FILES
# ──────────────────────────────────────────────────────────
print("Reading local files...")
avatar_b64 = base64.b64encode(open("/home/ultron/protocol_pulse/oracle/Proto_P_Avatar_512.png", "rb").read()).decode()
html_b64   = base64.b64encode(open("/home/ultron/protocol_pulse/media_reforge/templates/media_unified.html", "rb").read()).decode()
css_b64    = base64.b64encode(open("/home/ultron/protocol_pulse/media_reforge/static/css/media_unified.css", "rb").read()).decode()
js_b64     = base64.b64encode(open("/home/ultron/protocol_pulse/media_reforge/static/js/media_unified.js", "rb").read()).decode()
print(f"Avatar: {len(avatar_b64)}  HTML: {len(html_b64)}  CSS: {len(css_b64)}  JS: {len(js_b64)} chars")

# ──────────────────────────────────────────────────────────
# BUILD THE MEGA PYTHON SCRIPT  
# ──────────────────────────────────────────────────────────
NEW_ROUTE = '''
@app.route('/media-unified')
def media_unified():
    """Media Unified v2.0 — Bloomberg terminal layout"""
    try:
        from models import Podcast
        series_list = [
            {'key': 'everything_21m', 'title': 'Everything Divided by 21 Million', 'description': 'Bitcoin, time, money, freedom.', 'first_id': 'FA8tvWEydcA', 'ep_count': 11},
            {'key': 'big_print', 'title': 'The Big Print', 'description': 'The Fed wealth extraction scheme.', 'first_id': 'W09CNU_q6Yo', 'ep_count': 12},
            {'key': 'daylight_robbery', 'title': 'Daylight Robbery', 'description': 'How taxation shaped civilization.', 'first_id': 'ZCc78wvwd6U', 'ep_count': 13},
            {'key': 'genesis_book', 'title': 'The Genesis Book', 'description': 'Origins of Bitcoin.', 'first_id': 'y7KBeC4jfbo', 'ep_count': 5},
        ]
        tag = os.environ.get('AMAZON_AFFILIATE_TAG', 'protocolpulse-20')
        all_books = [
            {'title': 'The Bitcoin Standard', 'author': 'Saifedean Ammous', 'amazon_url': f'https://www.amazon.com/dp/1119473861?tag={tag}', 'color': '#f7931a'},
            {'title': 'Broken Money', 'author': 'Lyn Alden', 'amazon_url': f'https://www.amazon.com/dp/B0CG8985FR?tag={tag}', 'color': '#3b82f6'},
            {'title': 'The Sovereign Individual', 'author': 'Davidson & Rees-Mogg', 'amazon_url': f'https://www.amazon.com/dp/0684832720?tag={tag}', 'color': '#8b5cf6'},
            {'title': 'Mastering Bitcoin', 'author': 'Andreas Antonopoulos', 'amazon_url': f'https://www.amazon.com/dp/1098150090?tag={tag}', 'color': '#f59e0b'},
            {'title': 'The Fiat Standard', 'author': 'Saifedean Ammous', 'amazon_url': f'https://www.amazon.com/dp/1544526474?tag={tag}', 'color': '#6366f1'},
            {'title': 'The Price of Tomorrow', 'author': 'Jeff Booth', 'amazon_url': f'https://www.amazon.com/dp/1999257405?tag={tag}', 'color': '#10b981'},
        ]
        latest_episodes = Podcast.query.order_by(Podcast.published_date.desc()).limit(12).all()
        podcast_count = Podcast.query.count()
        return render_template('media_unified.html',
            series_list=series_list, series_count=len(series_list),
            latest_episodes=latest_episodes, podcast_count=podcast_count,
            all_books=all_books)
    except Exception as e:
        logging.error(f"media_unified error: {e}")
        return render_template('media_unified.html',
            series_list=[], series_count=0,
            latest_episodes=[], podcast_count=0, all_books=[])

'''

python_script = f'''import base64, os, re, logging, sys

WORKSPACE = "{WORKSPACE}"

# 1 — Write Proto_P_Avatar_512.png
img_b64 = """{avatar_b64}"""
with open(WORKSPACE + "/static/images/Proto_P_Avatar_512.png", "wb") as f:
    f.write(base64.b64decode(img_b64))
print("Avatar:", os.path.getsize(WORKSPACE + "/static/images/Proto_P_Avatar_512.png"), "bytes")

# 2 — Update oracle.html avatar reference
with open(WORKSPACE + "/templates/oracle.html", "r") as f:
    oc = f.read()
oc = re.sub(r"oracle_analyst_dark\\.png", "Proto_P_Avatar_512.png", oc)
oc = re.sub(r"oracle_avatar_anime\\.png", "Proto_P_Avatar_512.png", oc)
with open(WORKSPACE + "/templates/oracle.html", "w") as f:
    f.write(oc)
print("oracle.html updated")

# 3 — Update oracle_v2.html avatar reference
with open(WORKSPACE + "/templates/oracle_v2.html", "r") as f:
    v2c = f.read()
v2c = re.sub(r"oracle_analyst_dark\\.png", "Proto_P_Avatar_512.png", v2c)
v2c = re.sub(r"oracle_avatar_anime\\.png", "Proto_P_Avatar_512.png", v2c)
with open(WORKSPACE + "/templates/oracle_v2.html", "w") as f:
    f.write(v2c)
print("oracle_v2.html updated")

# 4 — Write media_unified.html
html_b64 = """{html_b64}"""
with open(WORKSPACE + "/templates/media_unified.html", "w") as f:
    f.write(base64.b64decode(html_b64).decode("utf-8"))
print("media_unified.html:", os.path.getsize(WORKSPACE + "/templates/media_unified.html"), "bytes")

# 5 — Ensure static/css/ and static/js/ exist
os.makedirs(WORKSPACE + "/static/css", exist_ok=True)
os.makedirs(WORKSPACE + "/static/js", exist_ok=True)

# 6 — Write media_unified.css
css_b64 = """{css_b64}"""
with open(WORKSPACE + "/static/css/media_unified.css", "w") as f:
    f.write(base64.b64decode(css_b64).decode("utf-8"))
print("media_unified.css:", os.path.getsize(WORKSPACE + "/static/css/media_unified.css"), "bytes")

# 7 — Write media_unified.js
js_b64 = """{js_b64}"""
with open(WORKSPACE + "/static/js/media_unified.js", "w") as f:
    f.write(base64.b64decode(js_b64).decode("utf-8"))
print("media_unified.js:", os.path.getsize(WORKSPACE + "/static/js/media_unified.js"), "bytes")

# 8 — Add /media-unified route to routes.py (if not already present)
with open(WORKSPACE + "/routes.py", "r") as f:
    routes = f.read()
if "def media_unified()" not in routes:
    # Insert before def media_terminal()
    insertion = """{NEW_ROUTE}"""
    routes = routes.replace("\\ndef media_terminal():", insertion + "\\ndef media_terminal():", 1)
    with open(WORKSPACE + "/routes.py", "w") as f:
        f.write(routes)
    print("Route /media-unified added to routes.py")
else:
    print("Route /media-unified already present, skipping")

# 9 — Graceful gunicorn reload
import subprocess
result = subprocess.run(["pkill", "-HUP", "-f", "gunicorn"], capture_output=True)
print("Gunicorn reload signal sent, rc:", result.returncode)
print("DEPLOY COMPLETE")
'''

total_size = len(python_script)
print(f"Python script size: {total_size} chars ({total_size/1024:.1f} KB)")

# ──────────────────────────────────────────────────────────
# BUILD SHELL COMMAND (use python3 with heredoc-style stdin)  
# ──────────────────────────────────────────────────────────
# Write Python script to /tmp then execute it using printf + base64 approach
py_b64 = base64.b64encode(python_script.encode()).decode()
print(f"Python script b64: {len(py_b64)} chars ({len(py_b64)/1024:.1f} KB)")

# The shell command: decode the b64 python script and run it
cmd = f"echo '{py_b64}' | base64 -d | python3"
print(f"Shell command size: {len(cmd)} chars ({len(cmd)/1024:.1f} KB)")

# Save the command for later execution
with open("/tmp/phase1_cmd.txt", "w") as f:
    f.write(cmd)
print("\nScript prepared. Run deploy_phase1.py when rate limit resets.")
print("Total Replit calls needed: 3 (deploy + verify oracle + verify media-unified)")

