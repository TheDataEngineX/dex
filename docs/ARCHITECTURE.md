# DEX Project Architecture & Roadmap

## Executive Summary

**DEX (DataEngineX)** is evolving from a foundational API service into a complete data engineering and ML platform. We are following a phased approach: **Foundation → Core Features → Advanced Platform → Future Innovation**.

## DEX Philosophy

DEX is a unified framework that bridges **Data Engineering, Data Warehousing, Machine Learning, AI Agents, MLOps, and DevOps**. It focuses on building **AI‑ready infrastructure** that moves models from notebooks to production.

**Portfolio Modules (Roadmap):**

- dex-data (Spark/Flink/Kafka pipelines)
- dex-warehouse (dbt + lakehouse/warehouse patterns)
- dex-lakehouse (Iceberg/Delta datasets)
- dex-ml (MLflow/Kubeflow + model serving)
- dex-api (FastAPI feature/prediction APIs)
- dex-ops (Terraform + Kubernetes + GitOps)

See [README.md](https://github.com/TheDataEngineX/DEX/blob/main/README.md) for the full philosophy and roadmap context.

## Current State (v0.5.0 - Foundation + Data + ML Platform)

### Infrastructure Baseline (implemented)

- ✅ **CI/CD**: GitHub Actions — lint (ruff), type-check (mypy), test (pytest), build, push
- ✅ **GitOps**: ArgoCD with branch-based deployment (dev/prod)
- ✅ **Code Quality**: Ruff (0 errors), mypy strict (0 errors), 94% test coverage
- ✅ **Pre-commit**: ruff + mypy + standard hooks
- ✅ **Containerization**: Multi-stage Docker with non-root user, healthcheck
- ✅ **Infrastructure-as-Code**: Kustomize overlays for all environments
- ✅ **Observability**: Structured logging (structlog), Prometheus metrics, OpenTelemetry tracing
- ✅ **Data Framework**: Medallion architecture (Bronze/Silver/Gold), data quality validators
- ✅ **Security**: CodeQL, Trivy scanning, pip-audit, branch protection

### Current Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     DEX Platform (v0.5.0)                   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐     ┌──────────────┐    ┌──────────────┐│
│  │  DataEngineX │     │  CareerDEX   │    │  WeatherDEX  ││
│  │   (API +     │     │  (Job Data   │    │  (Weather    ││
│  │  Framework)  │     │   Platform)  │    │   Pipeline)  ││
│  └──────────────┘     └──────────────┘    └──────────────┘│
│  Observability: Prometheus + OpenTelemetry + structlog      │
│  Quality: Ruff + mypy + pytest (94% cov) + pre-commit      │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│              Kubernetes + ArgoCD (GitOps)                   │
│   Environments: dev (2 pods, dex-dev), prod (3 pods, dex)    │
└─────────────────────────────────────────────────────────────┘
```

## Target Architecture (v1.0.0 - Production Ready)

```
┌─────────────────────────────────────────────────────────────────────┐
│                     DEX Platform (v1.0.0)                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌────────────────┐  ┌──────────────┐  ┌─────────────────┐        │
│  │  FastAPI       │  │  Data        │  │  ML Model       │        │
│  │  Service       │  │  Pipelines   │  │  Serving        │        │
│  │                │  │              │  │                 │        │
│  │ • Auth (JWT)   │  │ • Ingestion  │  │ • Training      │        │
│  │ • Validation   │  │ • Transform  │  │ • Inference     │        │
│  │ • Logging      │  │ • Quality    │  │ • Monitoring    │        │
│  │ • Metrics      │  │ • Scheduling │  │ • Registry      │        │
│  └────────────────┘  └──────────────┘  └─────────────────┘        │
│         │                   │                    │                  │
│         └───────────────────┴────────────────────┘                  │
│                             │                                       │
├─────────────────────────────┼───────────────────────────────────────┤
│  ┌───────────┐  ┌──────────┐│  ┌────────┐  ┌──────────────┐       │
│  │PostgreSQL │  │  Redis   ││  │ MinIO  │  │   MLflow     │       │
│  │  (OLTP)   │  │ (Cache)  ││  │(Object)│  │ (Experiments)│       │
│  └───────────┘  └──────────┘│  └────────┘  └──────────────┘       │
└─────────────────────────────┼───────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│        Observability Layer (Prometheus, Grafana, Loki)              │
│        GitOps (ArgoCD) + Secret Management (Sealed Secrets)         │
│        Kubernetes Cluster (HPA, Resource Limits, Health Checks)     │
└─────────────────────────────────────────────────────────────────────┘
```

## Roadmap Overview

The detailed roadmap is tracked in GitHub Issues/Milestones with CSV export in `docs/roadmap/project-roadmap.csv` as canonical documentation source.

Organization project hub: `https://github.com/orgs/TheDataEngineX/projects`

### Phases (High Level)

- **Phase 1: Foundation (v0.1.0)** ✅ — CI/CD, GitOps, multi‑env deployments
- **Phase 2: Production Hardening (v0.2.0)** ✅ — observability, health probes, API quality
- **Phase 3: Data Platform (v0.3.0)** ✅ — medallion architecture foundation, incremental data quality/schema implementation
- **Phase 4: ML Platform (v0.4.0)** ✅ — training, registry, serving, monitoring
- **Phase 5: Advanced Features (v0.5.0)** — auth, caching, analytics
- **Phase 6: Production Ready (v1.0.0)** — DR, security, performance

For execution details, see GitHub Issues and [SDLC](SDLC.md).

## Modular Monolith Strategy

### Current Module Structure

```
src/
├── dataenginex/          # Core framework (API, middleware, validators, schemas)
│   ├── api/              # FastAPI app, health, errors
│   ├── core/             # Medallion architecture, validators, schemas
│   ├── dashboard/        # Streamlit dashboard (panels, config)
│   ├── ml/               # Training, registry, vectorstore, LLM adapters
│   ├── plugins/          # Plugin system (ABC, registry, discovery)
│   └── middleware/       # Logging, metrics, tracing, request handling
├── careerdex/            # Job data ingestion platform (phases 1-6)
│   ├── api/              # FastAPI app entry point + routers
│   ├── core/             # Domain schemas, validators, settings
│   ├── phases/           # Implementation phases
│   ├── dags/             # Airflow DAGs
│   └── models/           # Data models
└── weatherdex/           # Weather ML pipeline (reference implementation)
    ├── core/             # Pipeline core
    ├── ml/               # ML models
    └── notebooks/        # Notebook-based experimentation assets
```

### Service Extraction Criteria

**When to Extract a Service:**

1. **Independent Scaling**: Different resource requirements (e.g., GPU for ML)
1. **Team Ownership**: Separate team needs autonomy
1. **Technology Diversity**: Different tech stack required
1. **Deployment Frequency**: Needs to deploy independently
1. **Fault Isolation**: Failures shouldn't cascade

**First Extraction Candidate: ML Model Serving**

- GPU scaling independent from API
- Polyglot support (TensorFlow Serving, TorchServe)
- High-frequency model updates
- Separate SLA requirements

**Not Extracting Yet:**

- Data pipelines (shared storage, orchestration overhead)
- API endpoints (low latency requirements)
- Analytics (tightly coupled to data layer)

## Technology Decisions

### Core Stack (Confirmed)

- **API**: FastAPI + Uvicorn
- **Language**: Python 3.12+
- **Package Management**: uv (dependencies/env) + Hatchling (build backend)
- **Container**: Docker
- **Orchestration**: Kubernetes + ArgoCD
- **CI/CD**: GitHub Actions

### Infrastructure Additions (v0.2.0+)

- **Observability**: Prometheus, Grafana, Loki, OpenTelemetry
- **Database**: PostgreSQL (OLTP)
- **Cache**: Redis
- **Object Storage**: MinIO (default) / S3-compatible adapters
- **Secrets**: Sealed Secrets

### Data & ML Stack (v0.5.0+)

- **Orchestration**: Apache Airflow
- **ML Tracking**: MLflow (preferred) or Weights & Biases
- **BI Tool**: Metabase (preferred) or Superset
- **Data Quality**: Great Expectations
- **Feature Store**: Feast (future)

## Development Workflow

### 1. Planning Phase

```
TODO.md → GitHub Issue (using template) → Add to Project Board → Assign Milestone
```

### 2. Development Phase

```
Create branch → Develop → Test locally → Commit with #issue → Push
```

### 3. Review Phase

```
Create PR → CI checks → Code review → Merge to main
```

### 4. Deployment Phase

```
CI builds image → CD updates manifests → ArgoCD syncs → Monitor
```

### 5. Promotion Flow

```
dev (auto) → prod (PR promotion via main branch)
```

## Risk Management

### High Priority Risks

1. **Complexity Creep**: Too many features, slow delivery

   - **Mitigation**: Strict prioritization, MVP mindset

1. **Technical Debt**: Fast iteration sacrifices quality

   - **Mitigation**: 20% time for refactoring, code reviews

1. **Infrastructure Costs**: Cloud bills spiral

   - **Mitigation**: Resource limits, cost monitoring, right-sizing

1. **Security Gaps**: Auth/secrets not implemented early

   - **Mitigation**: Phase 5 prioritizes security hardening

### Medium Priority Risks

1. **Data Quality Issues**: Bad data in production

   - **Mitigation**: Data quality framework in Phase 3

1. **Model Drift**: Models degrade over time

   - **Mitigation**: Monitoring and automated retraining in Phase 4

1. **Scaling Bottlenecks**: Performance issues at scale

   - **Mitigation**: Load testing, HPA, caching

## Success Metrics

### v0.2.0 (Production Hardening)

- API uptime: >99%
- P99 latency: \<200ms
- Test coverage: >80%
- Zero critical security vulnerabilities

### v0.3.0 (Data Platform) ✅

- Pipeline success rate: >95%
- Data freshness: \<1 hour delay
- Data quality checks: 100% passing
- Pipeline runtime: \<30 minutes

### v0.4.0 (ML Platform) ✅

- Model deployment time: \<5 minutes
- Model accuracy: >baseline
- Inference latency: \<100ms
- Drift detection: active

### v1.0.0 (Production)

- SLA: 99.9% uptime
- RTO: \<1 hour
- Cost per request: \<$0.001
- Customer satisfaction: >4/5

## Next Actions

1. **Immediate** (This Sprint):

   - Database integration (PostgreSQL)
   - Authentication (JWT + API keys)
   - Cache layer (Redis)

1. **Short Term** (Next 2 Sprints):

   - ML experiment tracking (MLflow)
   - Model serving endpoints
   - Feature store integration

1. **Medium Term** (Next Quarter):

   - Complete v1.0.0 production readiness
   - Performance tuning and load testing

______________________________________________________________________

**Last Updated**: 2026-03-12
**Document Owner**: Project Lead
**Review Cadence**: Bi-weekly
