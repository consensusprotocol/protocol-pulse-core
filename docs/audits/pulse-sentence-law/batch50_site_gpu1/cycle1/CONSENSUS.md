# Batch 50 cycle 1: the one consensus finding [low] is documentation only

Implemented:
- the worst-case stall is stated in the docstring: about 300 s waiting for the lease plus 180 s for the answer, in one waitress worker thread;
- glm, cross-examination: a missing client file now raises a clear RuntimeError("GPU1 lease client not found at ...") instead of an AttributeError.

Kept: the cached module lives as long as the process does, so a restart loads new code. Restarting is how the site is deployed (restart Waitress only).
