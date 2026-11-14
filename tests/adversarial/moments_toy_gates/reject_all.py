"""Rejects everything: must miss the false-reject threshold."""


def context_integrity(case):
    return {"verdict": "fail", "why": "toy: reject all"}


def vo_fidelity(case):
    return {"verdict": "fail", "why": "toy: reject all"}


def exclusion(case):
    return {"verdict": "exclude", "why": "toy: reject all"}
