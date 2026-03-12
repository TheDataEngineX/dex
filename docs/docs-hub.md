# DEX Documentation Hub

**All documentation organized by topic and project.**

______________________________________________________________________

## Getting Started

**New to DEX? Start here:**

1. **[Main README](https://github.com/TheDataEngineX/DEX/blob/main/README.md)** - Project overview
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
- **[Deployment Runbook](./DEPLOY_RUNBOOK.md)** - Release procedures
- **[Observability](./OBSERVABILITY.md)** - Monitoring, logging, tracing
- **[SDLC](./SDLC.md)** - Software development lifecycle
- **[Release Notes](./RELEASE_NOTES.md)** - Version history
- **[Org + Domain Rollout](./DEPLOY_RUNBOOK.md)** - GitHub Organization and Cloudflare setup checklist
- **[Kubernetes Setup](./LOCAL_K8S_SETUP.md)** - Local K8s configuration

### Projects

Project-specific documentation:

**CareerDEX**

- **[CareerDEX Docs](./careerdex/index.md)** - Project overview and implementation status
- **[Source Package](https://github.com/TheDataEngineX/DEX/tree/main/src/careerdex)** - Package-level structure and architecture

**Weather** (Reference Implementation)

- **[Weather Docs](./weather/index.md)** - Reference implementation guide
- **[Source Package](./weather/index.md)** - Source package summary

### Planning

- **[Project Roadmap (Canonical CSV)](./roadmap/project-roadmap.csv)** - Strategic milestones and status source of truth
- **[Project Roadmap (Derived JSON)](./roadmap/project-roadmap.json)** - Machine-readable export generated from CSV
- **[GitHub Issues](https://github.com/TheDataEngineX/DEX/issues)** - Task tracking

______________________________________________________________________

## 🔍 Find What You Need

| Task | Link |
|------|------|
| Set up local development | [Development Setup](./DEVELOPMENT.md) |
| Understand the architecture | [Architecture](./ARCHITECTURE.md) |
| Deploy to production | [Deployment Runbook](./DEPLOY_RUNBOOK.md) |
| Set up monitoring | [Observability](./OBSERVABILITY.md) |
| Contribute code | [Contributing](./CONTRIBUTING.md) |
| Understand CI/CD | [CI/CD Pipeline](./CI_CD.md) |
| Track work | [SDLC](./SDLC.md) |
| Configure org + domain | [Org + Domain Rollout](./DEPLOY_RUNBOOK.md) |
| Work on CareerDEX | [CareerDEX Docs](./careerdex/index.md) |
| Learn from reference | [Weather Docs](./weather/index.md) |

______________________________________________________________________

## Documentation Structure

```
docs/
├── docs-hub.md (this file)
├── DEVELOPMENT.md
├── CONTRIBUTING.md
├── ARCHITECTURE.md
├── CI_CD.md
├── DEPLOY_RUNBOOK.md
├── OBSERVABILITY.md
├── SDLC.md
├── RELEASE_NOTES.md
├── LOCAL_K8S_SETUP.md
├── adr/                        # Architecture decisions
│   ├── 0000-template.md
│   ├── 0001-medallion-architecture.md
│   └── ...
├── careerdex/                  # CareerDEX project
│   └── index.md
├── weather/                    # Weather reference
│   └── index.md
├── roadmap/                    # Strategic planning
│   ├── project-roadmap.csv      # Canonical source of truth
│   └── project-roadmap.json     # Derived export
└── (other docs organized by topic)
```

______________________________________________________________________

**Version**: v0.5.0 | **Updated**: March 12, 2026
