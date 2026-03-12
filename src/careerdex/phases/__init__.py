"""CareerDEX Pipeline Phases.

Individual implementations for each phase of the CareerDEX pipeline:

- phase1_foundation: Config loading, schema validation, medallion init
- phase2_job_ingestion: Multi-source connectors, dedup, ingestion pipeline
- phase3_embeddings: Text parsing, skill normalisation, embedding generation
- phase4_ml_models: Resume matcher, salary predictor, skill gap, career path, churn
- phase5_api_services: FastAPI routers for recommendations, salary, market intel
- phase6_testing_deployment: Deployment config, monitoring, security audit
"""

from __future__ import annotations

__all__: list[str] = []
