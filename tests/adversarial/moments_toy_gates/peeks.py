"""Tries to read the answer: the case it receives is blind, so this is an ERROR on every case."""


def context_integrity(case):
    return {"verdict": case["expected"]["verdict"], "why": "toy: peeked"}


def vo_fidelity(case):
    return {"verdict": case["expected"]["verdict"], "why": "toy: peeked"}


def exclusion(case):
    return {"verdict": case["expected"]["verdict"], "why": "toy: peeked"}
