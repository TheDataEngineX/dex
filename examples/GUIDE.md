# DataEngineX Examples

Runnable examples demonstrating key features of the `dataenginex` framework.

## Quick Start

```bash
# Install the package (from repo root)
uv sync

# Run an example
uv run python examples/01_hello_pipeline.py
uv run python examples/02_api_quickstart.py
uv run python examples/03_quality_gate.py
uv run python examples/04_ml_training.py
uv run python examples/05_rag_demo.py
uv run python examples/06_llm_quickstart.py

# Dashboard (requires streamlit)
uv sync --group dashboard
streamlit run examples/dashboard/run_dashboard.py
```

## Examples

| # | File | Description |
|---|------|-------------|
| 1 | `01_hello_pipeline.py` | Minimal pipeline: profiler + medallion config (e-commerce orders) |
| 2 | `02_api_quickstart.py` | Launch FastAPI app with health checks & v1 endpoints |
| 3 | `03_quality_gate.py` | Quality checks with QualityGate & QualityStore (product inventory) |
| 4 | `04_ml_training.py` | Train, register, and evaluate a model (customer churn) |
| 5 | `05_rag_demo.py` | RAG pipeline: ingest docs, query vector store, generate with LLM |
| 6 | `06_llm_quickstart.py` | LLM providers: mock, Ollama, OpenAI-compatible, factory function |
| — | `dashboard/run_dashboard.py` | Streamlit dashboard with pipeline status, quality scores, model drift panels |

## Prerequisites

- Python ≥ 3.12
- `uv` installed (`pip install uv`)
- For ML examples: `uv sync --group dev` (includes scikit-learn via test deps)
