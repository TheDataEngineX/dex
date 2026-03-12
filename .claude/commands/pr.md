Generate a PR description for the current branch's changes.

Steps:
1. Run `git log --oneline main..HEAD` to see commits
2. Run `git diff main --stat` to see changed files
3. Run `git diff main` for the actual changes
4. Categorize changes:
   - **What** — What changed and why
   - **How** — Implementation approach
   - **Testing** — How it was validated (include test results)
   - **Breaking Changes** — Any API contract changes
   - **Checklist** — Based on `.github/CHECKLISTS.md`

Format as a proper GitHub PR description with:
- Title following conventional commit format
- Summary paragraph
- Bullet-point change list
- Test evidence
- Reviewer notes

Reference related issues where applicable.
