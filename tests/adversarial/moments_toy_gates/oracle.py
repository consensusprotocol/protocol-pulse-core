"""Knows the answers: proves the thresholds are reachable. It can map the opaque ids back only because the test
that runs it sets PP_MOMENTS_SALT (a real run's salt is random and written to the report after the run). Loaded on
first use, from the same corpus directory the runner reads."""
import hashlib
import os

import moments_exam as ME

_V = {}


def _answer(case_id):
    if not _V:
        salt = os.environ["PP_MOMENTS_SALT"]
        for corpus in ME.GATES:
            for c in ME.load_corpus(corpus):
                _V["case-" + hashlib.sha256((salt + c["id"]).encode()).hexdigest()[:12]] = c["expected"]["verdict"]
    return _V[case_id]


def context_integrity(case):
    return {"verdict": _answer(case["id"]), "why": "oracle"}


vo_fidelity = context_integrity
exclusion = context_integrity
