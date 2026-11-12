"""pipeline.ingest: continuous ingest + first-pass moment mining (branch pp-ingest).

docs/audits/INGEST_DESIGN.md is the design. Modules:
  config     paths, the store guard, transcript_store bound to the store
  contract   sentence ids and the pp.moment/1 contract (pp-selectid's definitions, imported, fingerprinted)
  providers  ONE provider interface for every model role (law L-x); vendors and models only in providers.json
  queue      the durable SQLite queue: channels (last-seen ledger), videos (state machine), calls, events
  watch      channel listing (RSS first, uploads playlist fallback)
  fetch      per-video probe and caption fetch into the staging store
  mine       windows, the prompt, strict reply validation, moments
  ledger     the append-only moment ledger and the packager adapter (best unused moments since T)
  coverage   the daily coverage check
  stats      the live numbers
  service    the long-running loops
  ab         the blind A/B harness per back-end
"""
