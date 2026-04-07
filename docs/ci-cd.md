# CI/CD Pipeline

**Complete guide to DataEngineX continuous integration and release automation.**

> **Quick Links:** [CI Workflow](#continuous-integration-ci) · [Release Automation](#release-automation) · [PyPI Publishing](#pypi-publishing) · [Troubleshooting](#troubleshooting) · [Quick Reference](#quick-reference)

______________________________________________________________________

## 📋 Table of Contents

- [Overview](#overview)
- [Project Structure](#project-structure)
- [Continuous Integration (CI)](#continuous-integration-ci)
- [Release Automation](#release-automation)
- [PyPI Publishing](#pypi-publishing)
- [Rollback Procedures](#rollback-procedures)
- [Pipeline Metrics](#pipeline-metrics)
- [CI/CD Evolution](#cicd-evolution)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)
- [Related Documentation](#related-documentation)
- [Quick Reference](#quick-reference)

______________________________________________________________________

## Overview

DEX is a pure Python library published to PyPI. The pipeline is:

- **CI**: Automated testing, linting, and security scanning on every PR
- **Release**: Automated tagging and GitHub release creation on version bumps
- **PyPI Publish**: Automated publishing triggered by GitHub releases

```mermaid
graph LR
    Dev[Developer] --> PR[Create PR]
    PR --> CI[CI: Lint/Test/Security]
    CI --> Review[Code Review]
    Review --> MergeMain[Merge to main]

    MergeMain --> VersionBump{Version bump?}
    VersionBump -->|Yes| Release[release-dataenginex.yml<br/>Create tag + release]
    Release --> PyPI[pypi-publish.yml<br/>Publish to PyPI]

    style CI fill:#e1f5ff
    style Release fill:#f8f5ff
    style PyPI fill:#d4edda
```

______________________________________________________________________

## Project Structure

DEX is a single-package repo:

| Component | Location | Purpose | Release |
| --- | --- | --- | --- |
| **dataenginex** | `src/dataenginex/` | Core framework (API, middleware, storage, ML) | PyPI (`v{version}`) |

### Unified Testing

The **root `pyproject.toml`** defines the package and test config:

- `name = "dataenginex"`, `version = "<current>"` (see `pyproject.toml`)
- `[tool.hatch.build.targets.wheel] packages = ["src/dataenginex"]`
- Dependency groups: `dev` (required), `data` (PySpark/Airflow), `notebook` (pandas), `ml` (sentence-transformers), `dashboard` (streamlit)

**CI workflow** (`ci.yml`) runs in a single job (`poe lint` → `poe typecheck` → `pytest`):

- Single `ci` job: `uv sync --all-extras` + `poe lint` + `poe typecheck` + `pytest --cov`
- `concurrency: cancel-in-progress: true` — stale runs cancelled on new push
- `paths-ignore` — skips CI on doc-only changes

### Release Automation

- **Release automation**: `release-please.yml` reads conventional commits → creates Release PR (bumps `pyproject.toml` + `CHANGELOG.md` + `uv.lock`) → on merge creates `v{version}` tag + GitHub Release
- **Post-release**: `release-dataenginex.yml` generates CycloneDX SBOM and attaches it to the release
- **PyPI publishing** (`pypi-publish.yml`): Triggered by GitHub release published → detects changes in `src/dataenginex/` since last `v*` tag → publishes to TestPyPI then PyPI

______________________________________________________________________

## Continuous Integration (CI)

**Workflow**: [`.github/workflows/ci.yml`](https://github.com/TheDataEngineX/dataenginex/blob/main/.github/workflows/ci.yml)

**Triggers**:

- Push to `main` or `dev` branches
- Pull requests targeting `main` or `dev`

**Jobs**:

### 1. Lint and Test

Runs code quality checks and test suite:

```bash
# Linting
uv run poe lint

# Tests with coverage
uv run poe test-cov
```

**Requirements**: All checks must pass before merge

### 2. Security Scans

Runs in parallel via [`.github/workflows/security.yml`](https://github.com/TheDataEngineX/dataenginex/blob/main/.github/workflows/security.yml):

- **CodeQL**: Static analysis for security vulnerabilities
- **Semgrep**: OWASP Top 10 and best practice checks

**Results**: Available in GitHub Security tab

### 3. Integration Test (Optional)

Optional job for full dependency coverage (PySpark, Airflow, Pandas):

**Trigger**:

- Manual: `gh workflow run ci.yml`
- Label: Add `full-test` label to pull request

**What it does**:

```bash
# Installs all dependency groups
uv sync --group dev --group data --group notebook

# Runs full test suite (may take longer)
uv run poe test-cov
```

**Use case**: Validate changes to data pipelines, ML models, or when adding new dependencies to `data` or `notebook` groups.

______________________________________________________________________

## Release Automation

### DataEngineX Releases

**Workflow**: [`.github/workflows/release-dataenginex.yml`](https://github.com/TheDataEngineX/dataenginex/blob/main/.github/workflows/release-dataenginex.yml)

**Trigger**: `release: types: [published]` — fires when release-please creates a GitHub Release

**What it does**:

1. Generates CycloneDX SBOM for the release
1. Attaches `sbom-dataenginex-{version}.json` to the GitHub Release

**How to release DataEngineX**:

Releases are fully automated via release-please. Push conventional commits to `main`; release-please creates the Release PR and tag.

```bash
# Monitor release-please PR
gh pr list --label "autorelease: pending"

# After merging the Release PR, monitor post-release workflows
gh run list --workflow=pypi-publish.yml --limit 5
gh run list --workflow=release-dataenginex.yml --limit 5
```

______________________________________________________________________

## PyPI Publishing

**Workflow**: [`.github/workflows/pypi-publish.yml`](https://github.com/TheDataEngineX/dataenginex/blob/main/.github/workflows/pypi-publish.yml)

**Trigger**: GitHub release published (from `release-dataenginex.yml`)

**What it does**:

1. Receives GitHub release event from DataEngineX release
1. Detects if files under `src/dataenginex/` actually changed since previous `v{version}` tag
1. If changes found:
   - Builds wheel distributions
   - Publishes to TestPyPI (dry-run)
   - Promotes to PyPI (stable semver tags only, not pre-release)
1. If no changes: skips publishing with informational message

**Publish gates**:

- Only publishes if code actually changed (not just version bump in other files)
- TestPyPI first for dry-run verification
- PyPI promotion requires stable semver tag: `vMAJOR.MINOR.PATCH` (not `v1.2.3-rc1`)
- Pre-release tags: publish to TestPyPI only

**Automatic flow**:

```text
conventional commits → main → release-please Release PR → merge → v{version} tag + GitHub Release → pypi-publish.yml → PyPI
```

**Manual trigger** (if needed):

```bash
gh workflow run pypi-publish.yml -f tag=v<version>
```

______________________________________________________________________

## Rollback Procedures

### Rollback a PyPI Release

PyPI does not support deleting releases, but you can:

1. Yank the release on PyPI (marks it as broken; `pip install` avoids it by default):

   ```bash
   # Via PyPI web UI: manage release → yank
   # Or via twine/API
   ```

1. Publish a patch release with the fix:

   ```bash
   # Bump version in pyproject.toml (e.g., 0.6.1)
   git commit -m "fix: revert breaking change"
   git push origin main
   ```

### Rollback a Git Tag

```bash
# Delete tag locally and remotely
git tag -d v<version>
git push origin :refs/tags/v<version>

# Delete the GitHub release via gh CLI
gh release delete v<version> --yes
```

______________________________________________________________________

## Pipeline Metrics

### Build Times

- **CI (Lint + Test)**: ~2 minutes
- **Package validation**: ~1 minute
- **PyPI publish**: ~2 minutes

### Success Rates (Target)

- **CI Pass Rate**: >95%
- **Release Success Rate**: >99%

### Monitoring

```bash
# Recent CI runs
gh run list --workflow ci.yml --limit 10

# Recent releases
gh run list --workflow release-dataenginex.yml --limit 10

# Failed builds
gh run list --workflow pypi-publish.yml --status failure
```

______________________________________________________________________

## CI/CD Evolution

### Current State ✅

- [x] Automated CI with lint, test, type checks
- [x] Security scanning (CodeQL, Semgrep)
- [x] Automated PyPI release on version bump
- [x] Package validation (wheel + twine check)
- [x] GitHub Pages documentation deployment

### Future Enhancements 🚀

- [ ] **E2E smoke tests**: Post-release validation (install from PyPI and run examples)
- [ ] **SonarCloud integration**: Code quality gates
- [ ] **Slack notifications**: Release status updates
- [ ] **Release notes**: Auto-generated from commits
- [ ] **Canary releases**: TestPyPI smoke test before PyPI promotion

______________________________________________________________________

## Troubleshooting

### CI Fails with Lint Errors

```bash
# Run lint checks locally
uv run poe lint

# Auto-fix
uv run poe lint-fix
```

### PyPI Publish Not Triggering

- Verify version bump is in root `pyproject.toml` (not elsewhere)
- Confirm push was to `main` branch (not `dev`)
- Check `release-dataenginex.yml` ran and created a GitHub release
- View workflow logs: `gh run list --workflow pypi-publish.yml`

### Package Build Fails

```bash
# Build locally to diagnose
uv build
twine check dist/*

# Verify pyproject.toml metadata
uv run python -c "import dataenginex; print(dataenginex.__version__)"
```

______________________________________________________________________

## Best Practices

### Development Workflow

1. **Create feature branch** from `dev`
1. **Develop and test locally**
1. **Run quality checks** before committing: `uv run poe lint`, `uv run poe typecheck`, `uv run poe test`
1. **Create PR** targeting `dev`
1. **Wait for CI** to pass
1. **Get code review** approval
1. **Merge to dev** → integration testing
1. **Create release PR** from `dev` → `main`
1. **Merge to main** → bump version if releasing

### Commit Messages

Use conventional commits for clarity:

```bash
feat: add new endpoint for data processing
fix: resolve memory leak in pipeline
chore: update dependencies
docs: improve deployment runbook
test: add integration tests for API
```

### PR Guidelines

- **Keep PRs small**: \<500 lines of code
- **Single purpose**: One feature/fix per PR
- **Test coverage**: Include tests for new code
- **Documentation**: Update docs for API changes

______________________________________________________________________

## Related Documentation

**Next Steps:**

- **Deployment Runbook** (in `infradex` repo) - Release procedures
- **[Observability](observability.md)** - Monitor applications built on DEX
- **[Contributing Guide](contributing.md)** - Development workflow

______________________________________________________________________

## Quick Reference

### Workflows Overview

| Workflow | Trigger | Purpose | File |
| --- | --- | --- | --- |
| **CI** | `push main/dev`, PRs to main/dev | Lint, test, type-check | [ci.yml](.github/workflows/ci.yml) |
| **Security** | `push main/dev`, PRs to main/dev | CodeQL + Semgrep scans | [security.yml](.github/workflows/security.yml) |
| **Release Please** | `push main` | Create/update Release PR with version bump + CHANGELOG | [release-please.yml](.github/workflows/release-please.yml) |
| **Release DataEngineX** | GitHub release published | Generate + attach CycloneDX SBOM | [release-dataenginex.yml](.github/workflows/release-dataenginex.yml) |
| **PyPI Publish** | GitHub release published | Detect changes + publish to TestPyPI/PyPI | [pypi-publish.yml](.github/workflows/pypi-publish.yml) |

### Local Commands

```bash
# Local development
uv lock
uv sync
uv run poe test
uv run poe lint

# Local with all dependencies (data + notebook)
uv sync --group data --group notebook
uv run poe test-cov

# Create PR
gh pr create --title "feat: add feature" --body "Description"

# Trigger optional integration tests
gh pr edit <pr-number> --add-label full-test

# Check CI status
gh pr checks <pr-number>

# Monitor CI
gh run list --workflow ci.yml
gh run view <run-id> --log

# Manual PyPI publish
gh workflow run pypi-publish.yml -f tag=v<version>

# Promote to production (dev → main PR)
./scripts/promote.sh
```

______________________________________________________________________

**[← Back to Documentation](index.md)**
