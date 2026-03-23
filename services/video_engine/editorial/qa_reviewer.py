"""
QA Standards Editor — Stage 3
===============================
Automated showrunner that enforces quality before assembly.
Checks duration, clip boundaries, diversity, claims, ethics.

Flow:
  1. Run QA check on ShowPlanV2
  2. If approved → proceed to clip extraction
  3. If not → apply suggested edits, retry ONCE
  4. If still failing → trigger fallback (Quick Hits Edition)

Output: qa/qa_report.json
"""
import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

from services.video_engine.editorial.schemas import (
    ShowPlanV2, QAReport, QAIssue, TriageOutput
)

logger = logging.getLogger("QAReviewer")

QA_SYSTEM_PROMPT = """You review Pulse Check show plans for quality before production.
Check ALL of the following. Report every issue found.

1. DURATION: Estimated total 300-480 seconds (or smaller for slow-news editions).
2. CLIP RULES: Every clip_transcript must:
   - Start with capital letter or follow sentence-ending punctuation
   - End with period, question mark, or exclamation point
   - Be self-contained (no "as I was saying", "that thing", orphan references)
   - Be 15-30 seconds estimated (roughly 35-75 words)
3. DIVERSITY: No source in >2 stories. No source >40% of total clips.
4. CLAIMS: Every high-risk claim has evidence, or is softened with "reports suggest".
5. STALE: No story covered in last 2 days without genuinely new angle.
6. SPEAKER INTRO: Every clip has intro_line naming the speaker.
7. SIGNAL vs NOISE: Segment present and substantive.
8. ETHICS: Feuds = idea disagreements. No personal attacks or unverified accusations.
9. COMPLETENESS: cold_open, stories, signal_vs_noise, outro all present.
10. NO REJECTED OVERLAPS: No clip timestamps overlap with rejected segments.

Return JSON:
{
  "approved": true|false,
  "issues": [{"issue_type": "...", "detail": "...", "fix_suggestion": "..."}],
  "suggested_edits": {}
}

issue_type must be one of: clip_boundary, duration, diversity, claim_risk,
stale_topic, missing_intro, ethics, schema"""


class QAReviewer:
    """Stage 3: Quality gate before production."""

    def __init__(self):
        self.api_key = os.environ.get("ANTHROPIC_API_KEY", "")

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def review(self, show_plan: ShowPlanV2,
               triage: Optional[TriageOutput] = None,
               bundle_path: Path = None) -> QAReport:
        """
        Review show plan for quality issues.
        Runs both automated checks and AI review.
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"QA REVIEW — Stage 3")
        logger.info(f"{'='*60}\n")

        all_issues = []

        # Automated checks (always run, no API needed)
        auto_issues = self._automated_checks(show_plan, triage)
        all_issues.extend(auto_issues)
        logger.info(f"  Automated checks: {len(auto_issues)} issues")

        # AI review (if Claude available)
        if self.configured:
            ai_issues = self._ai_review(show_plan)
            all_issues.extend(ai_issues)
            logger.info(f"  AI review: {len(ai_issues)} issues")
        else:
            logger.info("  AI review: skipped (ANTHROPIC_API_KEY not set)")

        # Build report
        approved = all(
            issue.issue_type not in ("clip_boundary", "ethics", "schema")
            for issue in all_issues
        )

        # If only warnings (duration, diversity), still approve
        if not approved and all_issues:
            critical = [i for i in all_issues
                        if i.issue_type in ("clip_boundary", "ethics", "schema")]
            if not critical:
                approved = True

        report = QAReport(
            approved=approved,
            issues=all_issues
        )

        logger.info(f"\n  QA Result: {'APPROVED' if approved else 'NEEDS REVISION'}")
        for issue in all_issues:
            logger.info(f"    [{issue.issue_type}] {issue.detail}")

        # Save report
        if bundle_path:
            out_path = bundle_path / "qa" / "qa_report.json"
            out_path.write_text(json.dumps(report.dict(), indent=2, default=str))
            logger.info(f"  Saved: {out_path}")

        return report

    def _automated_checks(self, plan: ShowPlanV2,
                           triage: Optional[TriageOutput]) -> List[QAIssue]:
        """Run deterministic quality checks."""
        issues = []

        # 1. Duration check
        dur = plan.estimated_duration_seconds
        if plan.slow_news_mode:
            if dur > 300:
                issues.append(QAIssue(
                    issue_type="duration",
                    detail=f"Slow news edition at {dur}s exceeds 300s target",
                    fix_suggestion="Tighten scripts or remove a quick hit"
                ))
        else:
            if dur < 180:
                issues.append(QAIssue(
                    issue_type="duration",
                    detail=f"Episode too short: {dur}s (min 180s)",
                    fix_suggestion="Add more stories or expand narrator scripts"
                ))
            if dur > 540:
                issues.append(QAIssue(
                    issue_type="duration",
                    detail=f"Episode too long: {dur}s (max 540s)",
                    fix_suggestion="Cut a story or shorten clips"
                ))

        # 2. Clip boundary checks
        for story in plan.stories + plan.quick_hits:
            for i, clip in enumerate(story.clips):
                # Check transcript boundaries
                text = clip.clip_transcript.strip()
                if text and not text[0].isupper() and not text[0] == '"':
                    issues.append(QAIssue(
                        issue_type="clip_boundary",
                        detail=f"Story {story.story_number} clip {i}: "
                               f"doesn't start with capital letter",
                        fix_suggestion="Extend clip start to sentence beginning"
                    ))

                if text and text[-1] not in '.?!"\u2019':
                    issues.append(QAIssue(
                        issue_type="clip_boundary",
                        detail=f"Story {story.story_number} clip {i}: "
                               f"doesn't end with sentence-ending punctuation",
                        fix_suggestion="Extend clip end to sentence completion"
                    ))

                # Check word count (rough duration estimate: 2.5 words/sec)
                word_count = len(text.split())
                if word_count < 25:
                    issues.append(QAIssue(
                        issue_type="clip_boundary",
                        detail=f"Story {story.story_number} clip {i}: "
                               f"too short ({word_count} words, ~{word_count/2.5:.0f}s)",
                        fix_suggestion="Expand clip to 35-75 words for impact"
                    ))
                elif word_count > 90:
                    issues.append(QAIssue(
                        issue_type="clip_boundary",
                        detail=f"Story {story.story_number} clip {i}: "
                               f"too long ({word_count} words, ~{word_count/2.5:.0f}s)",
                        fix_suggestion="Split into two clips with narrator bridge"
                    ))

                # Check speaker intro
                if not clip.intro_line or len(clip.intro_line) < 10:
                    issues.append(QAIssue(
                        issue_type="missing_intro",
                        detail=f"Story {story.story_number} clip {i}: "
                               f"missing or too short intro_line",
                        fix_suggestion="Add narrator intro naming the speaker"
                    ))

        # 3. Source diversity
        from collections import Counter
        source_counts = Counter()
        total_clips = 0
        for story in plan.stories + plan.quick_hits:
            for clip in story.clips:
                source_counts[clip.source_name] += 1
                total_clips += 1

        if total_clips > 0:
            for source, count in source_counts.items():
                pct = count / total_clips
                if pct > 0.40:
                    issues.append(QAIssue(
                        issue_type="diversity",
                        detail=f"Source '{source}' is {pct:.0%} of clips (max 40%)",
                        fix_suggestion=f"Replace some {source} clips with other sources"
                    ))

        # 4. Signal vs Noise completeness
        svn = plan.signal_vs_noise
        if not svn.signal or len(svn.signal) < 10:
            issues.append(QAIssue(
                issue_type="schema",
                detail="Signal vs Noise: 'signal' is empty or too short",
                fix_suggestion="Add substantive signal content"
            ))
        if not svn.noise or len(svn.noise) < 10:
            issues.append(QAIssue(
                issue_type="schema",
                detail="Signal vs Noise: 'noise' is empty or too short",
                fix_suggestion="Add substantive noise content"
            ))

        # 5. Check for rejected segment overlaps
        if triage and triage.rejected:
            for story in plan.stories + plan.quick_hits:
                for clip in story.clips:
                    for rej in triage.rejected:
                        if (clip.source_id == rej.source_id and
                                self._timestamps_overlap(
                                    clip.approx_start, clip.approx_end,
                                    rej.approx_start, rej.approx_end)):
                            issues.append(QAIssue(
                                issue_type="clip_boundary",
                                detail=f"Clip from {clip.source_name} overlaps "
                                       f"rejected segment ({rej.reason})",
                                fix_suggestion="Select a different clip range"
                            ))

        # 6. Claims with high risk
        for story in plan.stories:
            for claim in story.claims:
                if claim.risk == "high" and not claim.evidence:
                    issues.append(QAIssue(
                        issue_type="claim_risk",
                        detail=f"High-risk claim without evidence: {claim.claim[:80]}",
                        fix_suggestion="Add evidence source or soften with 'reports suggest'"
                    ))

        return issues

    def _ai_review(self, plan: ShowPlanV2) -> List[QAIssue]:
        """Run AI-powered review for subjective quality checks."""
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=self.api_key)

            plan_json = json.dumps(plan.dict(), indent=2, default=str)

            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=2000,
                system=QA_SYSTEM_PROMPT,
                messages=[{
                    "role": "user",
                    "content": f"Review this show plan:\n\n{plan_json}"
                }]
            )

            content = response.content[0].text.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[-1]
            if content.endswith("```"):
                content = content.rsplit("```", 1)[0]

            data = json.loads(content.strip())

            ai_issues = []
            for issue in data.get("issues", []):
                try:
                    ai_issues.append(QAIssue(**issue))
                except Exception:
                    pass

            return ai_issues

        except Exception as e:
            logger.warning(f"  AI review failed: {e}")
            return []

    def _timestamps_overlap(self, s1: str, e1: str, s2: str, e2: str) -> bool:
        """Check if two timestamp ranges (MM:SS format) overlap."""
        try:
            def to_sec(ts: str) -> int:
                parts = ts.split(":")
                return int(parts[0]) * 60 + int(parts[1])

            start1, end1 = to_sec(s1), to_sec(e1)
            start2, end2 = to_sec(s2), to_sec(e2)
            return start1 < end2 and start2 < end1
        except (ValueError, IndexError):
            return False
