# Batch 52 cycle 1: consensus and what was done

C1 [low], times without an offset: is_fresh now reads published_at exactly as the ledger's own _aware does. A trailing Z means UTC: Python 3.10's fromisoformat rejects Z, so this was a real gap. A time without an offset is not measured and so never fresh; the adapter drops those rows before the worker sees them. All 2069 ledger lines carry an offset. TypeError is caught as well (glm, cross-examination). Test: the Z case and a None time.
