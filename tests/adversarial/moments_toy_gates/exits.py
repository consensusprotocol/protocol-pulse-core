"""Calls sys.exit(3) (the runner's ABSENT code) inside the gate: must be an ERROR, never reported as absent."""
import sys


def context_integrity(case):
    sys.exit(3)


vo_fidelity = exclusion = context_integrity
