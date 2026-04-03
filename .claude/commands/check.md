Audit and verify a specific file or module.

Target: $ARGUMENTS
- Read the file thoroughly
- Check for: syntax errors, logic bugs, missing imports, dead code
- Verify all functions are called (not orphaned)
- Check integration with other modules (imports work both ways)
- Run: `python3 -m py_compile $ARGUMENTS`
- Report: issues found, grade A-F, fixes needed