# Cycle 2 consensus (pp-selectid_audit_20261117_1556, the post_live fetch fallback)

SEATS ANSWERED: 3 of 3. qwen3.8-27b and gemma-4-31b-it: P0/P1 none (qwen: two P2s). gpt-oss-20b: two P1 claimed:
1. "whole_stream may return a partially-downloaded file": REFUTED. yt-dlp writes <stem>.<ext>.part (fragments
   <stem>.<ext>.part-FragN) and renames to <stem>.<ext> only on success; whole_stream matches os.path.splitext(f)[0] ==
   <stem> exactly, so a partial file is never found. A failed download raises (check=True): the window is not measured
   (fail closed). An unusable whole stream fails the cut's own duration check, and the cut is atomic (cycle 1's fix).
2. "no concurrency guard": a NARROW RACE, P2, NOT a wrong pass. Builds are serialized (build_and_record.sh refuses while
   another build runs), but a build's vision pool (4 workers) could fetch frames for two clips of the same uncached
   post_live video at once and start two downloads of one whole stream. The worst case is a failed yt-dlp, so that clip
   is not measured and fails closed. Today's stream (MeC8YEmUx_w) is served from the integrator's read-only cache, with
   no download at all. Follow-up recorded: a per-video lock in whole_stream.
qwen's P2s are the same two points. The first item of gpt-oss's table is cycle 1's finding, fixed then.
CLEARED to land (no change from cycle 2). Mutations 9 of 9.
