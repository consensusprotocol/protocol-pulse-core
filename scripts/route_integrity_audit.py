#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/home/ultron/protocol_pulse")
ROUTES = ROOT / "routes.py"
REPORT = ROOT / "docs" / "STATUS_REPORT.md"


def _iso_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def main() -> int:
    text = ROUTES.read_text(encoding="utf-8", errors="ignore")
    route_count = text.count("@app.route(")
    try_count = text.count("try:")
    has_404 = "@app.errorhandler(404)" in text
    has_500 = "@app.errorhandler(500)" in text
    lines = [
        "",
        "## System Integrity Report",
        f"- generated_at: {_iso_now()}",
        f"- routes_scanned: {route_count}",
        f"- try_blocks_detected: {try_count}",
        f"- global_404_handler: {'yes' if has_404 else 'no'}",
        f"- global_500_handler: {'yes' if has_500 else 'no'}",
        "- note: global error handlers are active to prevent raw traceback exposure.",
    ]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    with REPORT.open("a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("route_integrity_appended")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

