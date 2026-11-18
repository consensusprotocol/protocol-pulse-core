# Cycle 1 consensus (pp-selectid_audit_20261118_0711, ruling 144's one exception)

SEATS ANSWERED: 2 of 3. qwen3.8-27b: P0/P1 none. gemma-4-31b-it: one P1 claimed, REFUTED below. gpt-oss-20b: no answer.

gemma [P1] "the driver adds the exception row to the package's gates but not to a review_flags field, and
LP.pin_problems -> review_problems then refuses the pin": REFUTED. lock_precheck.pin_problems(pk) checks ONLY the lock
pre-check's coverage of the package's segments (ruling 68: ok, the same spans, pass / adopt, the same texts); it never
reads review flags. The PACKAGE carries no "review_flags" field at all: package_pin.to_pin derives them from the sealed
gates (rf = review_flags_of(pk["gates"])) and writes them into the pin's moments_package, so the exception row added
before write_pin is in them by construction, first. review_problems(mp) is the integrator's check of a written PIN,
where got == want by that construction.
gemma [P3] the double isinstance in content_flags: cosmetic, declined.

## No change from cycle 1 to cycle 2.
