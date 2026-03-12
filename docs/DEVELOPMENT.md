# Development Setup Guide

**Version**: v0.5.0 | **Updated**: March 12, 2026

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
├── packages/dataenginex/src/dataenginex/  # Main framework package
├── src/careerdex/          # CareerDEX project
├── src/weatherdex/         # Weather reference implementation
├── tests/                  # Test suite
├── docs/                  # Documentation
├── .github/workflows/     # CI/CD pipelines
├── infra/                 # Infrastructure as Code
├── pyproject.toml         # Project config
└── poe_tasks.toml        # Task definitions
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

DEX uses **two independent version sources** and release tags:

- **CareerDEX app version**: root `pyproject.toml` → release tag `careerdex-vX.Y.Z`
- **DataEngineX package version**: `packages/dataenginex/pyproject.toml` → release tag `dataenginex-vX.Y.Z` and PyPI publish flow

```bash
# CareerDEX release (app)
# 1) Bump root version
# 2) Merge to main and push
git add pyproject.toml
git commit -m "chore: bump careerdex to X.Y.Z"
git push origin main

# DataEngineX release (package + PyPI flow)
# 1) Bump package version
# 2) Merge to main and push
git add packages/dataenginex/pyproject.toml
git commit -m "chore: bump dataenginex to X.Y.Z"
git push origin main
```

On `main`, release workflows create Git tags/releases automatically:

- `careerdex-vX.Y.Z` from `release-careerdex.yml`
- `dataenginex-vX.Y.Z` from `release-dataenginex.yml` (then triggers `pypi-publish.yml`)

## Local Data Setup

### Path-Based (Local Dev)

```bash
mkdir -p ~/data/careerdex/{bronze,silver,gold}
mkdir -p ~/data/weather/{bronze,silver,gold}
```

### Optional Cloud Warehouse Adapter (Example: BigQuery)

Use this only when validating the cloud warehouse path; local development can run entirely on path-based storage.

```bash
export GCP_PROJECT=your-dex-project
bq mk --dataset careerdex_bronze
bq mk --dataset careerdex_silver
bq mk --dataset careerdex_gold
```

## Running Pipelines & Tests

### Airflow DAGs

```bash
# Initialize database
airflow db init

# Start webserver (http://localhost:8080)
airflow webserver --port 8080

# In another terminal, start scheduler
airflow scheduler

# Trigger DAG
airflow dags trigger careerdex_job_ingestion

# View logs
airflow tasks logs careerdex_job_ingestion fetch_linkedin 2024-01-01
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
python -m pdb src/careerdex/api/main.py

# Prometheus metrics (if running)
open http://localhost:9090
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Pre-commit hooks fail | `uv run poe lint-fix` then retry |
| Tests fail locally but pass in CI | Check Python version (3.12+), run `uv sync --reinstall` |
| Import errors | Run `uv sync --reinstall` and restart the shell |
| Airflow DAG not found | Check `src/careerdex/dags/` folder, restart scheduler |

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
