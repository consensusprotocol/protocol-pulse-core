import os
import base64
import time
import json
import subprocess
import sys

try:
    import requests
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
    import requests

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
REPO_OWNER = "consensusprotocol"
REPO_NAME = "protocol-pulse-core"
BRANCH = "main"
API_BASE = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}"
PROGRESS_FILE = "/home/runner/workspace/.github_push_progress.json"

headers = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

EXCLUDE_DIRS = {
    '.git', '.pythonlibs', '.cache', '.upm', '.config', '.local',
    'attached_assets', 'node_modules', '__pycache__', 'venv', '.venv',
    '.idea', '.vscode'
}

EXCLUDE_FILES = {
    'TOTAL_EXPORT.txt', 'project_backup.zip',
    'PROTOCOL_PULSE_COMPLETE_CODEBASE.md', 'github_push.py',
    'COMPLETE_PROTOCOL_PULSE_CODEBASE.md', 'COMPLETE_CODEBASE_FOR_VERIFICATION.md'
}

EXCLUDE_EXTENSIONS = {'.pyc', '.pyo', '.so', '.egg-info'}
MAX_FILE_SIZE = 50 * 1024 * 1024

def should_include(filepath):
    rel = os.path.relpath(filepath, '/home/runner/workspace')
    parts = rel.split(os.sep)
    for part in parts:
        if part in EXCLUDE_DIRS:
            return False
    filename = os.path.basename(rel)
    if filename in EXCLUDE_FILES:
        return False
    if len(filename) == 8 and '.' not in filename and filename[0] == 'z':
        return False
    _, ext = os.path.splitext(filename)
    if ext in EXCLUDE_EXTENSIONS:
        return False
    try:
        if os.path.getsize(filepath) > MAX_FILE_SIZE:
            return False
    except OSError:
        return False
    return True

def get_all_files():
    files = []
    workspace = '/home/runner/workspace'
    for root, dirs, filenames in os.walk(workspace):
        dirs[:] = sorted([d for d in dirs if d not in EXCLUDE_DIRS])
        for f in sorted(filenames):
            full_path = os.path.join(root, f)
            if should_include(full_path):
                rel_path = os.path.relpath(full_path, workspace)
                files.append((rel_path, full_path))
    return files

def load_progress():
    try:
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"uploaded_blobs": {}, "phase": "uploading"}

def save_progress(progress):
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f)

def create_blob(content_bytes):
    encoded = base64.b64encode(content_bytes).decode('utf-8')
    for attempt in range(3):
        try:
            resp = requests.post(f"{API_BASE}/git/blobs", headers=headers, json={
                "content": encoded,
                "encoding": "base64"
            }, timeout=30)
            if resp.status_code == 201:
                return resp.json()["sha"]
            if resp.status_code == 403:
                time.sleep(30)
                continue
            if resp.status_code >= 500:
                time.sleep(5)
                continue
            return None
        except requests.exceptions.Timeout:
            time.sleep(5)
            continue
    return None

def main():
    progress = load_progress()

    if progress["phase"] == "done":
        print("Push already completed! Delete /tmp/github_push_progress.json to re-run.")
        return

    files = get_all_files()
    total = len(files)
    print(f"Found {total} files")

    uploaded = progress.get("uploaded_blobs", {})
    remaining = [(r, f) for r, f in files if r not in uploaded]
    print(f"Already uploaded: {len(uploaded)}, Remaining: {len(remaining)}")

    if remaining:
        for i, (rel_path, full_path) in enumerate(remaining):
            try:
                with open(full_path, 'rb') as f:
                    content = f.read()
                blob_sha = create_blob(content)
                if blob_sha:
                    uploaded[rel_path] = blob_sha
                    progress["uploaded_blobs"] = uploaded
                    save_progress(progress)
                    if (len(uploaded)) % 10 == 0:
                        print(f"  [{len(uploaded)}/{total}] Uploaded: {rel_path}")
                else:
                    print(f"  FAILED: {rel_path}")
            except Exception as e:
                print(f"  ERROR {rel_path}: {e}")

        save_progress(progress)
        print(f"\nBlob upload complete: {len(uploaded)}/{total} files")

    if len(uploaded) < total * 0.9:
        print("Not enough files uploaded yet. Run again to continue.")
        return

    print("\nGetting branch reference...")
    ref_resp = requests.get(f"{API_BASE}/git/ref/heads/{BRANCH}", headers=headers)
    if ref_resp.status_code != 200:
        print(f"Branch not found: {ref_resp.status_code}")
        return

    current_sha = ref_resp.json()["object"]["sha"]
    print(f"HEAD: {current_sha[:8]}")

    tree_items = []
    for rel_path, blob_sha in uploaded.items():
        tree_items.append({
            "path": rel_path,
            "mode": "100644",
            "type": "blob",
            "sha": blob_sha
        })

    print(f"Creating tree with {len(tree_items)} files...")
    tree_resp = requests.post(f"{API_BASE}/git/trees", headers=headers, json={
        "tree": tree_items
    }, timeout=60)

    if tree_resp.status_code != 201:
        print(f"Tree failed: {tree_resp.status_code} {tree_resp.text[:300]}")
        return

    tree_sha = tree_resp.json()["sha"]

    print("Creating commit...")
    commit_resp = requests.post(f"{API_BASE}/git/commits", headers=headers, json={
        "message": "Export Protocol Pulse - full codebase",
        "tree": tree_sha,
        "parents": [current_sha]
    }, timeout=30)

    if commit_resp.status_code != 201:
        print(f"Commit failed: {commit_resp.status_code} {commit_resp.text[:300]}")
        return

    commit_sha = commit_resp.json()["sha"]

    print("Updating branch...")
    update_resp = requests.patch(
        f"{API_BASE}/git/refs/heads/{BRANCH}",
        headers=headers,
        json={"sha": commit_sha, "force": True},
        timeout=30
    )

    if update_resp.status_code in (200, 201):
        progress["phase"] = "done"
        save_progress(progress)
        print(f"\nSUCCESS! Pushed {len(tree_items)} files to github.com/{REPO_OWNER}/{REPO_NAME}")
        print(f"Commit: {commit_sha}")
    else:
        print(f"Ref update failed: {update_resp.status_code} {update_resp.text[:300]}")

if __name__ == "__main__":
    main()
