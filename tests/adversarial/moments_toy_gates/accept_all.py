"""Accepts everything: must miss every must-reject case."""


def context_integrity(case):
    return {"verdict": "pass", "why": "toy: accept all"}


def vo_fidelity(case):
    return {"verdict": "pass", "why": "toy: accept all"}


def exclusion(case):
    return {"verdict": "keep", "why": "toy: accept all"}
