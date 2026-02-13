#!/usr/bin/env python3
"""
Self-check for AI Arbitrage Pipeline and QC.
Exits 0 if ContentGenerator and ContentEngine have arbitrage + multi-review logic.
Runs without importing app (no flask/dotenv required).
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def main():
    errors = []
    cg_path = os.path.join(ROOT, "services", "content_generator.py")
    ce_path = os.path.join(ROOT, "services", "content_engine.py")
    with open(cg_path, "r") as f:
        cg_src = f.read()
    with open(ce_path, "r") as f:
        ce_src = f.read()
    if "def generate_article_variants" not in cg_src:
        errors.append("ContentGenerator missing generate_article_variants")
    if "def select_best_variant" not in cg_src:
        errors.append("ContentGenerator missing select_best_variant")
    if "def fact_check_with_live_data" not in cg_src:
        errors.append("ContentGenerator missing fact_check_with_live_data")
    if "_get_live_bitcoin_facts" not in cg_src or "3.125" not in cg_src:
        errors.append("ContentGenerator missing live Bitcoin facts (3.125 block reward)")
    if "def multi_ai_review" not in ce_src:
        errors.append("ContentEngine missing multi_ai_review")
    if "REVIEW_PROMPT_LIVE_FACT" not in ce_src or "3.125" not in ce_src:
        errors.append("ContentEngine missing REVIEW_PROMPT_LIVE_FACT with 3.125")
    if errors:
        for e in errors:
            print("FAIL:", e)
        return 1
    print("OK: Arbitrage pipeline and multi-AI review in place.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
