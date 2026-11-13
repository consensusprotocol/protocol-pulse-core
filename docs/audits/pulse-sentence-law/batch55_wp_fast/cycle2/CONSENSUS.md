# Batch 55 cycle 2: two consensus findings, both [low] with "no fix needed"

- The loop waits (wait(..., timeout=5)) whenever fetches are pending and no batch is ready. A ready-but-short buffer waits for more fetches, or for the last fetch to finish.
- The decode-order assertion is sound. bad.wav raises "no words" before needs_restoration is called.
