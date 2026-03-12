# CareerDEX Project Documentation

**AI-powered career intelligence platform**

## Overview

CareerDEX is an intelligent job matching platform built on the DEX framework. It combines real-time job ingestion, resume analysis, and ML-powered matching to help job seekers find their perfect role.

**Status**: Active development

## 📚 Documentation

- **[CareerDEX Source Package](https://github.com/TheDataEngineX/DEX/tree/main/src/careerdex)** - Full package architecture and implementation details
- **[CI/CD Pipeline](../CI_CD.md)** - Packaging, release, and promotion flow

## Implementation

### Current Status

Core package structure is implemented with phased modules under `src/careerdex/phases/`, with several features currently scaffolded/in progress per roadmap.

### Key Components

- **Data Ingestion**: Multi-source ingestion pipeline patterns (phased implementation)
- **Storage**: Medallion architecture (Bronze/Silver/Gold layers)
- **ML Models**: Resume scoring, matching, and salary prediction modules (in progress)
- **API**: FastAPI endpoints for search/matching/recommendations (incremental rollout)
- **UI**: Web interface planned in later roadmap phases

## Quick Links

- **GitHub Issues**: [CareerDEX Issues](https://github.com/TheDataEngineX/DEX/issues?q=label%3Acareerdex)
- **Main Issues**:
  - Issues #65-71: Development phases
  - Issue #64: Main epic tracking
- **Slack**: #careerdex-dev channel

## Getting Started

1. Read [DEVELOPMENT.md](../DEVELOPMENT.md) to set up local environment
1. Review [CareerDEX Source Package](https://github.com/TheDataEngineX/DEX/tree/main/src/careerdex) for architecture
1. Review package release setup in [packages/GUIDE.md](https://github.com/TheDataEngineX/DEX/blob/main/packages/GUIDE.md)

## Directory Structure

```
src/careerdex/
├── dags/
│   └── job_ingestion_dag.py         # Airflow DAG (10 tasks)
├── core/
│   └── notifier.py                  # Slack notifications
├── models/
│   └── [ML models]
├── phases/
│   └── phase1-6 implementations
└── README.md
```

______________________________________________________________________

**Documentation Hub**: [See docs/docs-hub.md](../docs-hub.md)
