Run cross-LLM audit on: $ARGUMENTS

Follow AUDIT-FIRST LAW:
1. Read every file mentioned — understand before changing
2. For each file, identify: bugs, fragility, quality killers, architecture smell
3. Grade each function A-F with specific reasoning
4. Provide exact code diffs for every fix (not vague suggestions)
5. Syntax check all changes: python3 -m py_compile <file>
6. Test the changes work
7. Git add + commit + push