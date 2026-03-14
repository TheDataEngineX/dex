# Scripts

Utility scripts for DEX development and deployment.

## Scripts

### `setup-system.sh`

Installs all Linux/macOS system-level packages required to develop, test, and run the DEX project locally.

**Usage:**

```bash
bash scripts/setup-system.sh     # direct
uv run poe setup-system          # via poe task
```

**Installs:**

- Core: git, curl, build-essential, Python 3.12+, Java 17 JRE, uv
- Recommended: Docker + Docker Compose
- Optional: Trivy (security scanning), actionlint (workflow linting)

**Supports:** Ubuntu/Debian, Fedora/RHEL, Arch Linux, macOS (Homebrew)

______________________________________________________________________

### `promote.sh`

Promotes from dev to prod by creating a PR from `dev` → `main`.

**Usage:**

```bash
# Branch promotion: dev → main (creates PR)
./scripts/promote.sh

# Branch promotion with auto-merge
./scripts/promote.sh --auto-merge
```

**Features:**

- Creates PR from `dev` → `main` for branch promotion
- Creates GitHub PR with deployment checklist (requires `gh` CLI)
- Supports auto-merge with `--auto-merge` flag

**Prerequisites:**

- bash
- GitHub CLI (`gh`) installed and authenticated
- Git configured with push access to repository

Make the scripts executable once:

```bash
chmod +x ./scripts/*.sh
```

______________________________________________________________________

## Promotion Workflow

### Standard Flow: Dev → Prod (PyPI Release)

```bash
# 1. Ensure dev is stable
uv run poe test

# 2. Bump version in pyproject.toml (e.g., version = "0.7.0")
# 3. Update CHANGELOG.md

# 4. Commit and push to dev
git add pyproject.toml CHANGELOG.md
git commit -m "chore: bump dataenginex to 0.7.0"
git push origin dev

# 5. Create PR: dev → main
./scripts/promote.sh

# 6. Merge PR after CI passes
# → release-dataenginex.yml auto-creates tag + GitHub release
# → pypi-publish.yml auto-publishes to PyPI
```

### Verify Release

```bash
# Check PyPI
pip install dataenginex==0.7.0 --dry-run

# Confirm import
python -c "import dataenginex; print(dataenginex.__version__)"
```

______________________________________________________________________

## Troubleshooting

### "You have uncommitted changes"

```bash
# Stash changes
git stash

# Run promotion
./scripts/promote.sh

# Restore changes
git stash pop
```

### "gh: command not found"

```bash
# Install GitHub CLI (Ubuntu)
sudo apt-get update
sudo apt-get install -y gh

# Authenticate
gh auth login
```

### PR creation fails

```bash
# Check gh auth status
gh auth status

# Check repository permissions
gh repo view TheDataEngineX/DEX

# Manual PR creation
git push origin dev
# Then create PR via GitHub UI: dev → main
```

______________________________________________________________________

## Best Practices

1. **Always promote via PR**: dev → main for traceability
1. **Use PR reviews**: Require approvals before merging
1. **Keep CHANGELOG up to date**: Update before releasing
1. **Use conventional commits**: `feat:`, `fix:`, `chore:` for clear history

## References

- [Release Runbook](../docs/DEPLOY_RUNBOOK.md)
- [CI/CD Pipeline](../docs/CI_CD.md)
