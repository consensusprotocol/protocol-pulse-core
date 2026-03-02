"""Replit relay helper — runs commands on the Replit deployment."""
import json, requests, yaml, os

_cfg = None
def _load():
    global _cfg
    if _cfg is None:
        p = os.path.join(os.path.dirname(__file__), "config.yaml")
        with open(p) as f:
            _cfg = yaml.safe_load(f)
    return _cfg

def run(cmd: str, timeout: int = 15) -> str:
    """Execute a command on Replit via relay and return stdout."""
    c = _load()["relay"]
    try:
        r = requests.post(c["url"], json={"token": c["token"], "cmd": cmd}, timeout=timeout)
        if r.status_code == 200:
            data = r.json()
            return data.get("stdout", "").strip()
        return ""
    except Exception as e:
        print(f"[relay] error: {e}")
        return ""

def get_key(name: str) -> str:
    """Get an API key from Replit env, falling back to local env."""
    local = os.environ.get(name, "")
    if local:
        return local
    return run(f"echo ${name}")

def query_db(sql: str) -> str:
    """Run a DB query on Replit and return results as JSON string."""
    escaped = sql.replace('"', '\\"').replace("'", "'\\''")
    cmd = f"python3 -c \"import json;from app import db;r=db.session.execute(db.text('{escaped}'));print(json.dumps([dict(row._mapping) for row in r]))\""
    return run(cmd, timeout=30)
