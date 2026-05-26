"""
Story Clustering + Novelty Gate — Stage 1.5
=============================================
Groups triage candidates into story clusters.
Enforces diversity rules. Checks against editorial memory.

1. Cluster by topic similarity (fuzzy matching)
2. Pick 1-2 hero candidates per cluster
3. Score novelty vs editorial memory (14-day rolling)
4. Enforce source diversity (no source > 40%, max 2 stories)
5. Detect contradictions for debate mode

Output: clusters/cluster_output.json
"""
import json
import logging
from pathlib import Path
from difflib import SequenceMatcher
from typing import Dict, List, Optional
from collections import defaultdict

from pp_services.video_engine.editorial.schemas import (
    ClusterOutput, StoryCluster, TriageOutput, EditorialMemory
)

logger = logging.getLogger("StoryClustering")

# Thresholds
SIMILARITY_THRESHOLD = 0.45  # Topic match threshold for same cluster
NOVELTY_STALE_COUNT = 3      # Covered this many times in 14 days = stale
SOURCE_MAX_PCT = 0.40         # No source > 40% of clips
SOURCE_MAX_STORIES = 2        # No source in > 2 stories


class StoryClustering:
    """Cluster candidates into stories with diversity and novelty enforcement."""

    def __init__(self, editorial_memory: Dict = None):
        self.memory = editorial_memory or {}
        self.running_stories = self.memory.get("running_stories", [])

    def cluster(self, triage: TriageOutput,
                bundle_path: Path = None) -> ClusterOutput:
        """
        Group candidates into story clusters.
        Returns ClusterOutput with diversity warnings.
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"STORY CLUSTERING — Stage 1.5")
        logger.info(f"{'='*60}\n")

        candidates = [c.dict() for c in triage.candidates]
        if not candidates:
            logger.warning("  No candidates to cluster")
            return ClusterOutput(clusters=[])

        # Step 1: Build clusters by topic similarity
        clusters = self._build_clusters(candidates)
        logger.info(f"  Built {len(clusters)} raw clusters from {len(candidates)} candidates")

        # Step 2: Pick hero candidates per cluster
        for cluster in clusters:
            cluster["hero_candidates"] = self._pick_heroes(
                cluster["all_candidates"], candidates)

        # Step 3: Score novelty against editorial memory
        dropped_stale = []
        for cluster in clusters:
            novelty = self._score_novelty(cluster["topic"])
            cluster["novelty_score"] = novelty
            if novelty < 0.3:
                dropped_stale.append(cluster["topic"])

        # Step 4: Source diversity enforcement
        diversity_warnings = self._check_diversity(clusters, candidates)

        # Step 5: Detect contradictions for debate mode
        self._detect_debates(clusters, candidates)

        # Sort clusters: fresh + high relevance first
        clusters.sort(key=lambda c: (
            c.get("novelty_score", 0.5) * 0.4 +
            self._cluster_avg_relevance(c, candidates) * 0.6
        ), reverse=True)

        # Build schema output
        schema_clusters = []
        for i, c in enumerate(clusters):
            schema_clusters.append(StoryCluster(
                cluster_id=f"cluster_{i}",
                topic=c["topic"],
                hero_candidates=c.get("hero_candidates", []),
                all_candidates=c.get("all_candidates", []),
                novelty_score=c.get("novelty_score", 0.5),
                sources_represented=c.get("sources", [])
            ))

        output = ClusterOutput(
            clusters=schema_clusters,
            dropped_as_stale=dropped_stale,
            diversity_warnings=diversity_warnings
        )

        logger.info(f"\n  Clustering results:")
        logger.info(f"    Clusters: {len(schema_clusters)}")
        logger.info(f"    Stale dropped: {len(dropped_stale)}")
        logger.info(f"    Diversity warnings: {len(diversity_warnings)}")

        for c in schema_clusters[:5]:
            logger.info(f"    [{c.cluster_id}] {c.topic} "
                        f"(novelty={c.novelty_score:.2f}, "
                        f"heroes={len(c.hero_candidates)}, "
                        f"sources={c.sources_represented})")

        # Save output
        if bundle_path:
            out_path = bundle_path / "clusters" / "cluster_output.json"
            out_path.write_text(json.dumps(output.dict(), indent=2, default=str))
            logger.info(f"  Saved: {out_path}")

        return output

    def _build_clusters(self, candidates: List[dict]) -> List[dict]:
        """Group candidates by topic similarity using fuzzy matching."""
        clusters = []
        assigned = set()

        for i, cand in enumerate(candidates):
            if i in assigned:
                continue

            topic = cand.get("topic", "")
            why = cand.get("why_interesting", "")
            match_text = f"{topic} {why}".lower()

            cluster = {
                "topic": topic,
                "all_candidates": [str(i)],
                "sources": [cand.get("source_name", "")],
                "sentiments": [cand.get("sentiment", "neutral")],
            }
            assigned.add(i)

            # Find similar candidates
            for j, other in enumerate(candidates):
                if j in assigned:
                    continue

                other_text = f"{other.get('topic', '')} {other.get('why_interesting', '')}".lower()
                similarity = SequenceMatcher(None, match_text, other_text).ratio()

                if similarity >= SIMILARITY_THRESHOLD:
                    cluster["all_candidates"].append(str(j))
                    source = other.get("source_name", "")
                    if source not in cluster["sources"]:
                        cluster["sources"].append(source)
                    cluster["sentiments"].append(other.get("sentiment", "neutral"))
                    assigned.add(j)

            clusters.append(cluster)

        return clusters

    def _pick_heroes(self, candidate_indices: List[str],
                     all_candidates: List[dict]) -> List[str]:
        """Pick 1-2 best candidates per cluster (highest relevance, best diversity)."""
        if not candidate_indices:
            return []

        scored = []
        for idx_str in candidate_indices:
            idx = int(idx_str)
            if idx < len(all_candidates):
                cand = all_candidates[idx]
                scored.append((idx_str, cand.get("relevance_score", 0)))

        scored.sort(key=lambda x: x[1], reverse=True)

        heroes = [scored[0][0]] if scored else []

        # Pick second hero from different source if possible
        if len(scored) > 1:
            first_source = all_candidates[int(scored[0][0])].get("source_name", "")
            for idx_str, score in scored[1:]:
                if all_candidates[int(idx_str)].get("source_name", "") != first_source:
                    heroes.append(idx_str)
                    break
            if len(heroes) == 1 and len(scored) > 1:
                heroes.append(scored[1][0])

        return heroes[:2]

    def _score_novelty(self, topic: str) -> float:
        """Score topic novelty against 14-day editorial memory."""
        if not self.running_stories:
            return 1.0  # No memory = everything is fresh

        topic_lower = topic.lower()
        best_match = 0.0
        times_covered = 0

        for story in self.running_stories:
            similarity = SequenceMatcher(
                None, topic_lower, story.get("topic", "").lower()
            ).ratio()
            if similarity > best_match:
                best_match = similarity
                times_covered = story.get("times_covered", 0)

        if best_match < 0.4:
            return 1.0  # New topic

        if times_covered >= NOVELTY_STALE_COUNT:
            return 0.2  # Stale

        if times_covered >= 2:
            return 0.5  # Monitor for new angle

        return 0.8  # Covered once — still fresh enough

    def _check_diversity(self, clusters: List[dict],
                          candidates: List[dict]) -> List[str]:
        """Enforce source diversity rules."""
        warnings = []
        source_story_count = defaultdict(int)
        source_candidate_count = defaultdict(int)
        total_candidates = 0

        for cluster in clusters:
            sources_in_cluster = set()
            for idx_str in cluster.get("hero_candidates", []):
                idx = int(idx_str)
                if idx < len(candidates):
                    source = candidates[idx].get("source_name", "")
                    sources_in_cluster.add(source)
                    source_candidate_count[source] += 1
                    total_candidates += 1

            for source in sources_in_cluster:
                source_story_count[source] += 1

        # Check: no source in > 2 stories
        for source, count in source_story_count.items():
            if count > SOURCE_MAX_STORIES:
                warnings.append(
                    f"Source '{source}' appears in {count} stories "
                    f"(max {SOURCE_MAX_STORIES})"
                )

        # Check: no source > 40% of candidates
        if total_candidates > 0:
            for source, count in source_candidate_count.items():
                pct = count / total_candidates
                if pct > SOURCE_MAX_PCT:
                    warnings.append(
                        f"Source '{source}' is {pct:.0%} of hero candidates "
                        f"(max {SOURCE_MAX_PCT:.0%})"
                    )

        return warnings

    def _detect_debates(self, clusters: List[dict], candidates: List[dict]):
        """Flag clusters with opposing sentiments for debate mode."""
        for cluster in clusters:
            sentiments = cluster.get("sentiments", [])
            has_bullish = "bullish" in sentiments
            has_bearish = "bearish" in sentiments

            if has_bullish and has_bearish:
                cluster["debate_detected"] = True
                logger.info(f"  Debate detected in '{cluster['topic']}' "
                            f"(bullish + bearish)")

    def _cluster_avg_relevance(self, cluster: dict,
                                candidates: List[dict]) -> float:
        """Calculate average relevance score for a cluster's heroes."""
        heroes = cluster.get("hero_candidates", [])
        if not heroes:
            return 0.0
        scores = []
        for idx_str in heroes:
            idx = int(idx_str)
            if idx < len(candidates):
                scores.append(candidates[idx].get("relevance_score", 0))
        return sum(scores) / len(scores) / 10.0 if scores else 0.0
