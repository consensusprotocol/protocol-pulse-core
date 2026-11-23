"""Ruling 133 R16: the judge service (ruling 87) with its heartbeat.

local_judge.py is not edited: judge_sha hashes it, and any change would re-ask every judge verdict. This launcher
runs local_judge.main(["serve"]) unchanged, with a heartbeat thread and a pass mark after each serve_once.
    cd /home/ultron/protocol_pulse && CUDA_VISIBLE_DEVICES=0 python3 pipeline/judge_serve.py 2>&1 | tee -a data/local_judge/serve.log
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import heartbeat  # noqa: E402
import local_judge  # noqa: E402

_serve_once = local_judge.serve_once


def serve_once(log=print):
    n = _serve_once(log=log)
    heartbeat.mark_pass("judge", served=n)
    return n


def main():
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "0":       # refused before any heartbeat, as local_judge refuses
        sys.exit("the local judge runs on GPU0: CUDA_VISIBLE_DEVICES=0 (law L-r)")
    local_judge.serve_once = serve_once                     # main() looks serve_once up at call time
    heartbeat.start("judge")
    return local_judge.main(["serve"])


if __name__ == "__main__":
    sys.exit(main())
