# Batch 78 cycle 3 (verification of a55e4dcf): the behavioural key test is sound; ONE NARROW CONSENSUS FINDING sent to pp-tests (panel qwen27b FAIL, glm PASS; Grok PASS 0.8 with 0 findings; panel $0.0017)
- CONSENSUS (glm F1, agreed by qwen27b): the "nothing opened" guarantee covers open / io.open / os.open only.
  - A _key that ALSO side-reads the key file through a subprocess or exec, discards it and returns the loader's value would pass. The sentinel check catches only a _key that RETURNS such a read.
  - Fix asked: deny subprocess.Popen, os.system, os.posix_spawn(p) and os.exec* during the calls (a BaseException, attempts recorded), plus one scratch mutation that side-reads via subprocess and must fail.
- REFUTED: qwen27b F1 "the bytecode-flag assert breaks under -B". The test forces sys.dont_write_bytecode = False before the calls and checks _key restores that value; pp-tests' mutations also ran under -B.
- glm F2 (low): no key value can leak; failures print types and names. No change.
- Integrator's wall run on the merge (04a0b95c, 09:25-09:28): 382 passed, 40 xfailed, 3 skipped, 0 failed.
