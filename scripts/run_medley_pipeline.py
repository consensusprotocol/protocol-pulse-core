#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path("/home/ultron/protocol_pulse")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.sovereign_medley_pipeline import sovereign_medley_pipeline


def main() -> int:
    out = sovereign_medley_pipeline.run_once()
    print(json.dumps(out, ensure_ascii=True, indent=2))
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())

