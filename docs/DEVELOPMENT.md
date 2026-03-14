# Development Setup Guide

**Version**: v0.6.0 | **Updated**: March 14, 2026

## Prerequisites

### System Dependencies

| Package | Required | Purpose |
|---------|----------|---------|
| Git | Yes | Version control |
| curl | Yes | Downloading tools |
| Python 3.12+ | Yes | Runtime (managed by uv) |
| build-essential / gcc | Yes | Native extension compilation |
| Java 17+ JRE | Yes\* | PySpark tests (`openjdk-17-jre-headless`) |
| uv | Yes | Python package & env manager |
| Docker + Compose | Recommended | Full stack, integration tests, emulators |
| Trivy | Optional | Local security scanning (`uv run poe security`) |
| actionlint | Optional | GitHub Actions workflow linting |

\* PySpark tests are auto-skipped when Java is unavailable.

**One-command install** (Ubuntu/Debian, Fedora, Arch, macOS):

```bash
bash scripts/setup-system.sh        # or: uv run poe setup-system
```

This installs all system packages, uv, Docker, and optional tools, then verifies the setup.

### Cloud Credentials (Optional)

- AWS / GCP credentials only needed for cloud storage adapters (staging/prod)
- Local development runs entirely on path-based storage

## Quick Start

```bash
# 1. Install system dependencies (first time only)
bash scripts/setup-system.sh

# 2. Clone repo and create feature branch
git clone https://github.com/TheDataEngineX/DEX.git
cd DEX
git checkout -b feat/issue-XXX-description dev

# 3. Install Python deps & pre-commit hooks
uv run poe setup

# 4. Verify setup
uv run poe check-all
```

All tests and linting should pass. You're ready to develop!

## Project Structure

```
DEX/
├── src/dataenginex/        # Core framework package
├── examples/               # Runnable example scripts (01–10)
├── tests/                  # Test suite
├── docs/                   # Documentation
├── .github/workflows/      # CI/CD pipelines
├── infra/                  # Infrastructure as Code
├── pyproject.toml          # Project config (dataenginex 0.6.0)
└── poe_tasks.toml          # Task definitions
```

## Development Workflow

### Branch & Commit

```bash
# 1. Create feature branch from dev
git checkout -b feat/issue-XXX-description dev

# 2. Make changes to src/
# Add tests in tests/

# 3. Format & validate
uv run poe lint
uv run poe typecheck
uv run poe test

# 4. Commit (pre-commit hooks run automatically)
git commit -m "feat(#XXX): description"

# 5. Push & create PR
git push origin feat/issue-XXX-description
```

**PR Requirements:**

- Link to issue: `Closes #XXX`
- All checks pass (CI/CD ~3-5 min)
- 1 approval required
- Merge to `dev` when ready

### Version Management

DEX has a single version source:

- **dataenginex version**: root `pyproject.toml` → release tag `dataenginex-vX.Y.Z` and PyPI publish flow

```bash
# DataEngineX release (package + PyPI flow)
# 1) Bump version in root pyproject.toml
# 2) Merge to main and push
git add pyproject.toml
git commit -m "chore: bump dataenginex to X.Y.Z"
git push origin main
```

On `main`, the release workflow creates Git tags/releases automatically:

- `dataenginex-vX.Y.Z` from `release-dataenginex.yml` (then triggers `pypi-publish.yml`)

## Local Data Setup

### Path-Based (Local Dev)

```bash
mkdir -p ~/data/dex/{bronze,silver,gold}
```

### Optional Cloud Warehouse Adapter (Example: BigQuery)

Use this only when validating the cloud warehouse path; local development can run entirely on path-based storage.

```bash
export GCP_PROJECT=your-dex-project
bq mk --dataset dex_bronze
bq mk --dataset dex_silver
bq mk --dataset dex_gold
```

## Running Pipelines & Tests

### Example Scripts

```bash
# Medallion pipeline demo
uv run python examples/07_api_ingestion.py

# PySpark ML (requires Java 17+)
uv run python examples/08_spark_ml.py

# Feature engineering
uv run python examples/09_feature_engineering.py

# Model analysis + drift detection
uv run python examples/10_model_analysis.py
```

### Testing

```bash
# Run all tests with coverage
uv run poe test-cov

# Run unit tests only
uv run poe test-unit

# Check code quality
uv run poe check-all
```

### Monitoring & Debugging

```bash
# View application logs
tail -f logs/app.log

# Enable debug logging
export LOG_LEVEL=DEBUG
uv run poe dev

# Use Python debugger
python -m pdb examples/02_api_quickstart.py

# Prometheus metrics (if running)
open http://localhost:9090
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Pre-commit hooks fail | `uv run poe lint-fix` then retry |
| Tests fail locally but pass in CI | Check Python version (3.12+), run `uv sync --reinstall` |
| Import errors | Run `uv sync --reinstall` and restart the shell |
| PySpark examples fail | Check Java 17+ is installed (`java -version`) |

## Common Commands

```bash
uv run poe setup              # One-step setup (all deps + pre-commit hooks)
uv run poe check-all          # Run lint + typecheck + tests in sequence
uv run poe lint               # Ruff lint check
uv run poe lint-fix           # Auto-fix lint + format
uv run poe typecheck          # mypy strict type checking
uv run poe test               # Run all tests
uv run poe test-cov           # Tests with coverage report
uv run poe security           # pip-audit vulnerability scan
uv run poe pre-commit         # Run all pre-commit hooks
uv run poe dev                # Run dev server (localhost:8000)
uv run poe clean              # Remove caches and build artifacts
```

## Resources & Support

- **Code Style**: See [CONTRIBUTING.md](./CONTRIBUTING.md)
- **Architecture**: See [ARCHITECTURE.md](./ARCHITECTURE.md)
- **ADRs**: See [ADR-0001](./adr/0001-medallion-architecture.md) for architectural decisions
- **Deployment**: See [DEPLOY_RUNBOOK.md](./DEPLOY_RUNBOOK.md)
- **Issues**: [GitHub Issues](https://github.com/TheDataEngineX/DEX/issues)
- **Chat**: #dex-dev Slack channel
