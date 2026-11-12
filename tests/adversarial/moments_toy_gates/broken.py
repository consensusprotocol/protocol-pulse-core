"""Raises on context cases, returns an invalid verdict on VO cases, returns a non-dict on exclusion cases."""


def context_integrity(case):
    raise RuntimeError("toy: gate crashed")


def vo_fidelity(case):
    return {"verdict": "maybe", "why": "toy"}


def exclusion(case):
    return "exclude"
