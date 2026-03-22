# DEX Documentation Hub

**All documentation organized by topic and project.**

______________________________________________________________________

## Getting Started

**New to DEX? Start here:**

1. **[Main README](https://github.com/TheDataEngineX/dataenginex/blob/main/README.md)** - Project overview
1. **[Development Setup](./DEVELOPMENT.md)** - Local environment setup
1. **[CI/CD Pipeline](./CI_CD.md)** - Build, release, and publish workflow
1. **[Contributing](./CONTRIBUTING.md)** - How to contribute

### One-step Setup

```bash
uv run poe setup
uv run poe check-all
```

Use this to install dependencies, set up pre-commit hooks, and verify the workspace in one quick flow.

______________________________________________________________________

## 📂 Documentation Structure

### Framework (Common)

Core documentation for all DEX developers:

- **[Development Setup](./DEVELOPMENT.md)** - Local development, workflow, testing
- **[Contributing Guidelines](./CONTRIBUTING.md)** - Code style, commits, PR process
- **[Architecture](./ARCHITECTURE.md)** - System design and technology stack
- **[Architecture Decision Records (ADRs)](./adr/0001-medallion-architecture.md)** - Rationale for major technical decisions
  - [ADR-0001: Medallion Architecture](./adr/0001-medallion-architecture.md)
- **[CI/CD Pipeline](./CI_CD.md)** - GitHub Actions automation
- **[Observability](./OBSERVABILITY.md)** - Monitoring, logging, tracing
- **[SDLC](./SDLC.md)** - Software development lifecycle
- **[Release Notes](./RELEASE_NOTES.md)** - Version history
- **Deployment Runbook** (in `infradex` repo) - Release and K8s deploy procedures
- **Local K8s Setup** (in `infradex` repo) - Kubernetes configuration

### Examples

Runnable pipeline and ML examples:

- `examples/02_api_quickstart.py` - FastAPI server with dataenginex middleware
- `examples/07_api_ingestion.py` - Bronze→Silver→Gold medallion pipeline
- `examples/08_spark_ml.py` - Feature engineering + model training
- `examples/09_feature_engineering.py` - Time/lag/rolling features
- `examples/10_model_analysis.py` - Drift detection + prediction analysis

### Planning

- **[Project Roadmap (Canonical CSV)](./roadmap/project-roadmap.csv)** - Strategic milestones and status source of truth
- **[Project Roadmap (Derived JSON)](./roadmap/project-roadmap.json)** - Machine-readable export generated from CSV
- **[GitHub Issues](https://github.com/TheDataEngineX/dataenginex/issues)** - Task tracking

______________________________________________________________________

## 🔍 Find What You Need

| Task | Link |
|------|------|
| Set up local development | [Development Setup](./DEVELOPMENT.md) |
| Understand the architecture | [Architecture](./ARCHITECTURE.md) |
| Deploy to production | Deployment Runbook (in `infradex` repo) |
| Set up monitoring | [Observability](./OBSERVABILITY.md) |
| Contribute code | [Contributing](./CONTRIBUTING.md) |
| Understand CI/CD | [CI/CD Pipeline](./CI_CD.md) |
| Track work | [SDLC](./SDLC.md) |
| Configure org + domain | Deployment Runbook (in `infradex` repo) |
| Explore runnable examples | `examples/` directory |

______________________________________________________________________

## Documentation Structure

```
docs/
├── docs-hub.md (this file)
├── DEVELOPMENT.md
├── CONTRIBUTING.md
├── ARCHITECTURE.md
├── CI_CD.md
├── OBSERVABILITY.md
├── SDLC.md
├── RELEASE_NOTES.md
├── adr/                        # Architecture decisions
│   ├── 0000-template.md
│   ├── 0001-medallion-architecture.md
│   └── ...
├── roadmap/                    # Strategic planning
│   ├── project-roadmap.csv      # Canonical source of truth
│   └── project-roadmap.json     # Derived export
└── (other docs organized by topic)
```

______________________________________________________________________

**Version**: `uv run poe version` | see `pyproject.toml`
