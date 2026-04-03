Fix this issue: $ARGUMENTS

Follow the Protocol Pulse fix protocol:
1. AUDIT-FIRST: Read all relevant files before touching anything
2. Identify root cause (not symptoms)
3. Implement the minimal fix that solves the problem
4. Syntax check: `python3 -m py_compile <file>` for every changed file
5. Test the fix works (don't just claim it works)
6. Git add + commit + push with descriptive message
7. Verify deployment: check waitress still healthy after changes
8. Report what was changed, why, and proof it works