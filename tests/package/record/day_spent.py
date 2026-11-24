"""The build's own spend figure for the day it would charge NOW (proof_ledger.build_router's router.spent(): ruling 48,
vendor-reported, the estimate where a vendor reports none) and that day's ledger file name. Read only: the router is
built and asked spent(), no call is made. Prints: '<usd, 6 decimals> <ledger file name>'."""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))   # tests/package/record/ -> the repo
W = REPO
sys.path[:0] = [os.path.join(W, "tests/package"), os.path.join(W, "pipeline")]
os.chdir(W)
import proof_ledger as PLG  # noqa: E402

r = PLG.build_router("heimdall_first", {}, os.devnull)
print(f"{r.spent():.6f} {os.path.basename(PLG.PL.SPEND)}")
