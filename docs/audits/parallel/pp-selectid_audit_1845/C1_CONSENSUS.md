# pp-selectid audit 1845 (ruling 73: the lock pre-check's rules string and decoder sha): cycle 1 consensus

grok "SHIP: yes", qwen "SHIP: yes", glm "SHIP: yes". No P0 and no P1 from any reviewer.

All three verify that:
- RULES and DECODER take the integrator's 18:43 values exactly ("ruling 17 + ruling 72 + ruling 73";
  8a101f222598);
- an answer under the old rules string, even a newer one, is never read, and the old decoder's files are never
  opened (the file name carries the sha);
- a ruling-73 "cannot cut" hold is a hold, never a pass.

Their P2s confirm that the filtering is the existing, tested mechanism. No change.
