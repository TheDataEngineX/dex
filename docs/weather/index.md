# Weather Pipeline - Reference Implementation

**Reference pipeline implementation for multi-layer architecture**

## Overview

The Weather Pipeline is a working reference implementation of the DEX framework's medallion architecture. It serves as a template for future projects (like CareerDEX).

**Status**: Reference implementation (actively refined)
**Purpose**: Learn DEX patterns, validate architecture, reuse for other projects

## 📚 Documentation

- **[Weather Source Package](https://github.com/TheDataEngineX/DEX/tree/main/src/weatherdex)** - Core weather modules and notebooks
- **[CI/CD Pipeline](../CI_CD.md)** - Packaging, release, and promotion flow

## What You'll Learn

This reference implementation demonstrates:

- **Data Ingestion**: Fetching external data (weather API)
- **Bronze Layer**: Raw data storage and schema validation
- **Silver Layer**: Data cleaning, validation, transformations
- **Gold Layer**: Feature engineering and aggregations
- **ML Integration**: Training models on processed data
- **Airflow Orchestration**: DAG configuration and 3-hour cycles
- **Monitoring**: Data quality checks and metrics
- **Testing**: Unit and integration test patterns

## Quick Start

```bash
cd src/weatherdex

# Explore package modules
python -c "import weatherdex; print(weatherdex.__all__)"
```

## Key Files

- `core/` - Data fetching and transformation logic
- `ml/` - ML model training and prediction
- `config/` - Configuration and schema definitions
- `notebooks/` - Analysis and exploration notebooks

## How to Adapt for Your Project

1. Copy the structure: `src/{project_name}/`
1. Update configs in `config/schema_definitions.py`
1. Replace fetchers in `core/fetch_*.py`
1. Implement business logic transformations
1. Add ML models in `ml/`
1. Create Airflow DAG similar to weather pipeline

## Reference Links

- **DEX Framework**: [docs/ARCHITECTURE.md](../ARCHITECTURE.md)
- **Medallion Architecture**: [docs/adr/0001-medallion-architecture.md](../adr/0001-medallion-architecture.md)
- **Development Guide**: [docs/DEVELOPMENT.md](../DEVELOPMENT.md)

______________________________________________________________________

**Documentation Hub**: [See docs/docs-hub.md](../docs-hub.md)
