import subprocess, os
W = "/home/runner/workspace"
G = "https://raw.githubusercontent.com/consensusprotocol/protocol-pulse-core/main"
files = [
    (G + "/oracle/Proto_P_Avatar_512.png", W + "/static/images/Proto_P_Avatar_512.png"),
    (G + "/media_reforge/templates/media_unified.html", W + "/templates/media_unified.html"),
    (G + "/media_reforge/static/css/media_unified.css", W + "/static/css/media_unified.css"),
    (G + "/media_reforge/static/js/media_unified.js", W + "/static/js/media_unified.js"),
]
for url, dest in files:
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    r = subprocess.run(["curl", "-s", "-L", "--max-time", "30", url, "-o", dest], capture_output=True)
    sz = os.path.getsize(dest) if os.path.exists(dest) else 0
    print("OK" if sz > 1000 else "FAIL", dest, sz, "B")
print("downloads complete")
