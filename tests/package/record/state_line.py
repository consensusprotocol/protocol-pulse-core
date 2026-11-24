"""Insert ONE new physical line at the top of pp-selectid_STATE.md, under the file's own flock (the lock
heimdall_health._prepend uses), via an atomic replace.

Usage: python3 -B state_line.py <HH:MM from date> <text file>
The text file holds the line with the placeholder {T} where the time goes. It must not contain a newline
(a trailing one is stripped)."""
import fcntl
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
STATE = os.path.join(REPO, "docs", "audits", "parallel", "pp-selectid_STATE.md")


def main():
    t, src = sys.argv[1], sys.argv[2]
    if len(t) != 5 or t[2] != ":" or not (t[:2] + t[3:]).isdigit():
        sys.exit(f"refused: {t!r} is not HH:MM from date")
    with open(src) as f:
        text = f.read().rstrip("\n")
    if "\n" in text or "{T}" not in text:
        sys.exit("refused: the line must be one physical line holding {T}")
    line = text.replace("{T}", t)
    with open(STATE + ".lock", "w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        try:
            with open(STATE) as f:
                body = f.read()
            tmp = f"{STATE}.{os.getpid()}.tmp"
            with open(tmp, "w") as f:
                f.write(line + "\n" + body)
            os.replace(tmp, STATE)
        finally:
            fcntl.flock(lk, fcntl.LOCK_UN)
    print(f"STATE line 1 written ({len(line)} chars) at {t}")


if __name__ == "__main__":
    main()
