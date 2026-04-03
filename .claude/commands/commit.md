Commit changes with Protocol Pulse standards.

Commit message: $ARGUMENTS

Steps:
1. Show all changed files: `git diff --name-only`
2. Syntax check every modified .py file: `python3 -m py_compile <file>`
3. If any syntax errors, FIX THEM before committing
4. `git add -A`
5. Check if pipeline files changed — if yes, prefix with [HOTFIX-EXEMPT] unless audit exists
6. `git commit -m "$ARGUMENTS"`
7. `git push`
8. Verify push succeeded
9. Report: files committed, push status