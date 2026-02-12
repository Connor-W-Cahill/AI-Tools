# Changelog Generator

Transform git commits into polished, user-friendly changelogs.

## When to Use
- Preparing release notes for a new version
- Creating weekly/monthly product update summaries
- Writing changelog entries for app store submissions
- Maintaining a public changelog page

## Process
1. Scan git history (date range or between tags/versions)
2. Categorize changes: features, improvements, bug fixes, breaking changes, security
3. Translate technical commits into customer-friendly language
4. Filter noise (exclude refactoring, tests, CI changes)
5. Format with categories and consistent style

## Output Format
```markdown
# Updates - [Date/Version]

## New Features
- **Feature Name**: Clear description of what users can now do

## Improvements
- **Area**: What improved and why it matters

## Fixes
- Fixed [user-facing description of what was broken]
```

## Tips
- Run from git repository root
- Specify date ranges for focused changelogs
- Review generated changelog before publishing
