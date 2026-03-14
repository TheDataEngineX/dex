#!/usr/bin/env bash
set -euo pipefail

# ---------------------------------------------------------------
# promote.sh — Branch-based promotion: dev → prod (main)
#
# Creates a PR to merge the dev branch into main. If the PR
# includes a version bump in pyproject.toml, the CI/release
# pipeline will automatically tag and publish to PyPI.
# ---------------------------------------------------------------

usage() {
  cat <<'USAGE'
Usage:
  ./scripts/promote.sh [--auto-merge]

Promotes dev → prod by creating a merge PR from dev into main.

Examples:
  ./scripts/promote.sh               # PR: dev → main
  ./scripts/promote.sh --auto-merge  # PR: dev → main (auto-merge)
USAGE
}

auto_merge="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --auto-merge)
      auto_merge="true"
      shift 1
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1"
      usage
      exit 1
      ;;
  esac
done

if [[ -n "$(git status --porcelain)" ]]; then
  echo "Warning: you have uncommitted changes"
  git status --porcelain
  read -r -p "Continue anyway? (y/N) " continue_choice
  if [[ "$continue_choice" != "y" ]]; then
    exit 1
  fi
fi

# ---------------------------------------------------------------
# Branch promotion (dev → main)
# ---------------------------------------------------------------
echo "Promoting dev → main (prod)"
echo "This creates a PR to merge the dev branch into main."

git fetch origin dev main

# Check dev is ahead of main
dev_ahead=$(git rev-list --count origin/main..origin/dev 2>/dev/null || echo "0")
if [[ "$dev_ahead" == "0" ]]; then
  echo "dev is not ahead of main — nothing to promote."
  exit 0
fi
echo "dev is ${dev_ahead} commit(s) ahead of main"

if command -v gh >/dev/null 2>&1; then
  # Check if a promotion PR already exists
  existing_pr=$(gh pr list --base main --head dev --json number --jq '.[0].number' 2>/dev/null || echo "")
  if [[ -n "$existing_pr" ]]; then
    echo "Promotion PR #${existing_pr} already exists: dev → main"
    gh pr view "$existing_pr" --web
    exit 0
  fi

  dev_sha=$(git rev-parse --short=8 origin/dev)
  pr_title="chore: promote dev to prod (${dev_sha})"
  pr_body=$(cat <<EOF
## Branch Promotion: dev → prod

**Source**: \`dev\` (${dev_sha})
**Target**: \`main\` (prod)
**Commits**: ${dev_ahead} commit(s) ahead

### Checklist
- [ ] Dev branch is stable (all CI checks pass)
- [ ] \`CHANGELOG.md\` is updated
- [ ] Version is bumped in \`pyproject.toml\` (if releasing to PyPI)
- [ ] Notify team of release

### Post-Merge
- If \`pyproject.toml\` version was bumped: \`release-dataenginex.yml\` creates tag + GitHub release
- \`pypi-publish.yml\` publishes to TestPyPI → PyPI automatically

### Rollback
If the release has issues, yank the PyPI version and publish a patch:
\`\`\`bash
# Yank via PyPI web UI, then:
# Bump to patch version on dev → promote again
\`\`\`

---
Automated promotion via promote.sh
EOF
)

  gh pr create --title "$pr_title" --body "$pr_body" --base main --head dev --label "promotion" --label "prod"

  if [[ "$auto_merge" == "true" ]]; then
    gh pr merge dev --auto --squash
    echo "PR will auto-merge after checks pass"
  else
    gh pr view --web
  fi
else
  echo "GitHub CLI (gh) not found. Create a PR manually:"
  echo "  Base: main"
  echo "  Head: dev"
  echo "  Title: Promote dev to prod"
fi

echo "Promotion complete"
