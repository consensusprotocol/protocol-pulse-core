#!/usr/bin/env python3
"""
Phase 1 Deploy v2 - GitHub-pull approach.
Downloads files from GitHub raw URLs, adds route, restarts server.
Uses only ~9 Replit relay calls total.
"""
import base64, json, subprocess, time, sys

REPLIT_RELAY = "https://protocolpulse.replit.app/api/admin/exec"
REPLIT_TOKEN = "581b1076ca6d8a8809997d24f0869431ffd75c64de9ea703b6ab0f3e39fbd552"

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
            print(f"[{label}] RATE LIMITED. Abort.")
            sys.exit(1)
        if resp:
            try:
                d = json.loads(resp)
                stdout = d.get("stdout", "").strip()
                stderr = d.get("stderr", "").strip()
                rc = d.get("returncode", -1)
                msg = stdout[:200] + (" | ERR:" + stderr[:100] if stderr else "")
                print(f"  [{label}] rc={rc} | {msg}")
                return d
            except:
                print(f"  [{label}] raw: {resp[:200]}")
                return {}
        print(f"  [{label}] empty, retry {attempt+1}...")
        time.sleep(2)
    return {}

def encode_script(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

# ──────────────────────────────────────────────────────────
# STEP 1: Write and execute download script
# ──────────────────────────────────────────────────────────
print("\n=== STEP 1: Deploy files from GitHub ===")
ds_b64 = encode_script("/home/ultron/protocol_pulse/pp_download.py")
print(f"Download script b64: {len(ds_b64)} chars")
replit_exec(f"echo '{ds_b64}' | base64 -d > /tmp/pp_download.py", "write-download")
replit_exec("python3 /tmp/pp_download.py", "download-files")

# ──────────────────────────────────────────────────────────
# STEP 2: Update oracle templates avatar references
# ──────────────────────────────────────────────────────────
print("\n=== STEP 2: Update oracle templates ===")
W = "/home/runner/workspace"
oracle_cmd = (
    f"sed -i 's/oracle_analyst_dark\\.png/Proto_P_Avatar_512.png/g' {W}/templates/oracle.html {W}/templates/oracle_v2.html 2>/dev/null; "
    f"sed -i 's/oracle_avatar_anime\\.png/Proto_P_Avatar_512.png/g' {W}/templates/oracle.html {W}/templates/oracle_v2.html 2>/dev/null; "
    f"grep -rn 'Proto_P_Avatar' {W}/templates/oracle*.html 2>/dev/null || echo 'Pattern not found'"
)
replit_exec(oracle_cmd, "update-oracle")

# ──────────────────────────────────────────────────────────
# STEP 3: Add /media-unified route to routes.py
# ──────────────────────────────────────────────────────────
print("\n=== STEP 3: Add media-unified route ===")
rs_b64 = encode_script("/home/ultron/protocol_pulse/pp_add_route.py")
print(f"Route script b64: {len(rs_b64)} chars")
replit_exec(f"echo '{rs_b64}' | base64 -d > /tmp/pp_route.py", "write-route")
replit_exec("python3 /tmp/pp_route.py", "add-route")

# ──────────────────────────────────────────────────────────
# STEP 4: Graceful gunicorn restart
# ──────────────────────────────────────────────────────────
print("\n=== STEP 4: Restart gunicorn ===")
replit_exec(
    "kill -HUP $(pgrep -f gunicorn | head -1) 2>/dev/null; echo 'HUP sent'; sleep 3; echo 'workers:' $(pgrep -f gunicorn | wc -l)",
    "restart"
)

# ──────────────────────────────────────────────────────────
# STEP 5: Verify
# ──────────────────────────────────────────────────────────
print("\n=== STEP 5: Verify ===")
time.sleep(5)

# Verify avatar in oracle page
replit_exec(
    f"curl -s https://protocolpulse.replit.app/oracle 2>/dev/null | grep -o 'Proto_P_Avatar[^\"]*' | head -2; echo ---; "
    f"ls -la {W}/static/images/Proto_P_Avatar_512.png 2>/dev/null",
    "verify-oracle"
)

# Verify media-unified route
replit_exec(
    f"curl -s https://protocolpulse.replit.app/media-unified 2>/dev/null | head -20",
    "verify-media-unified"
)

print("\n=== PHASE 1 DEPLOY COMPLETE ===")
print("Tasks 1 and 3 deployed.")
print("Verify in browser:")
print("  https://protocolpulse.replit.app/oracle  (check Proto_P avatar)")
print("  https://protocolpulse.replit.app/media-unified  (check telemetry ribbon)")
