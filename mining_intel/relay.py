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

def run(cmd: str, timeout: int = 25) -> str:
    """Execute a command on Replit via relay and return stdout."""
    c = _load()["relay"]
    for attempt in range(2):
        try:
            r = requests.post(c["url"], json={"token": c["token"], "cmd": cmd},
                              timeout=timeout)
            if r.status_code == 200:
                data = r.json()
                return data.get("stdout", "").strip()
            return ""
        except requests.exceptions.Timeout:
            if attempt == 0:
                pass  # retry once
        except Exception as e:
            print(f"[relay] error: {e}")
            break
    return ""

def get_key(name: str) -> str:
    """Get an API key from local env first, then Replit relay."""
    local = os.environ.get(name, "")
    if local:
        return local
    return run(f"echo ${name}")

def query_db(sql: str) -> str:
    """Run a DB query on Replit and return results as JSON string."""
    escaped = sql.replace('"', '\\"').replace("'", "'\\''")
    cmd = f"python3 -c \"import json;from app import db;r=db.session.execute(db.text('{escaped}'));print(json.dumps([dict(row._mapping) for row in r], default=str))\""
    return run(cmd, timeout=30)

def insert_article(sql: str) -> str:
    """Run an INSERT on Replit and return the new article ID."""
    escaped = sql.replace('"', '\\"').replace("'", "'\\''")
    cmd = f"python3 -c \"from app import db;db.session.execute(db.text('{escaped}'));db.session.commit();print('OK')\""
    return run(cmd, timeout=30)
