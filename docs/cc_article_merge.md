Read PIPELINE_LAWS.md first. Then merge the p4-article-page worktree.

## TASK: Merge p4-article-page branch into main

### CONTEXT:
There is a completed feature branch in the worktree at ~/worktrees/p4-article-page (branch: p4-article-page, last commit a74e80c, marked BUILD_COMPLETE).

### STEPS:
1. First read what was built:
   cd ~/worktrees/p4-article-page && git log --oneline -5
   cat ~/protocol_pulse/docs/gospels/ARTICLE_PAGE_LAWS.md 2>/dev/null | head -50

2. Run the audit merge script:
   bash ~/cc_audit_merge.sh p4-article-page 2>&1 | tee /tmp/article_merge_audit.log

3. If audit passes (0 critical failures):
   cd ~/protocol_pulse
   git merge p4-article-page --no-ff -m "feat(articles): merge p4-article-page - improved article detail page"
   git push origin main

4. If audit finds issues, fix them in the worktree first, then merge.

5. After merge:
   kill -HUP $(cat ~/protocol_pulse/gunicorn.pid) 2>/dev/null
   sleep 3
   curl -s -o /dev/null -w "%{http_code}" https://protocolpulse.io/articles/1

6. Log result to ~/protocol_pulse/docs/overnight_report.md

IMPORTANT: Work in ~/worktrees/p4-article-page for any fixes, NOT in ~/protocol_pulse directly.