"""Always 'uncertain': uncertain counts as a rejection (law L-s: any uncertain = FAIL), so this misses the
false-reject threshold like reject_all."""


def context_integrity(case):
    return {"verdict": "uncertain", "why": "toy"}


def vo_fidelity(case):
    return {"verdict": "uncertain", "why": "toy"}


def exclusion(case):
    return {"verdict": "uncertain", "why": "toy"}
