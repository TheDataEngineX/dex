"""CareerDEX — Job Ingestion, Matching & Recommendation Platform.

**Phases:**

1. Foundation — config, schemas, medallion architecture
2. Job Ingestion — multi-source connectors, deduplication
3. Feature Engineering — text parsing, embeddings, vector store
4. ML Models — matcher, salary, skill gap, career path, churn
5. API Services — FastAPI routers for recommendations & market intel
6. Testing & Deployment — monitoring, security, deploy config

**Architecture:**

- Medallion Architecture: Bronze → Silver → Gold layers
- Dual Storage: Local Parquet + BigQuery cloud
- Real-time Processing: Async/await patterns
- ML Pipeline: scikit-learn + XGBoost + embeddings
- RAG: Vector DB + LLM integration

**Configuration:** ``config/job_config.json``

**Phases:** ``phases/`` directory
"""

from __future__ import annotations

__all__: list[str] = []
