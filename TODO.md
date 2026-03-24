# TODO — TheDataEngineX ORG

> **Goal:** Build a full-stack Data/AI/ML platform portfolio that demonstrates
> Data Engineer + AI Engineer + ML Engineer + Data Scientist skills, get reach,
> and land a job.
>
> **Repos:** `dex` · `datadex` · `agentdex` · `careerdex` · `dex-studio` · `infradex`

______________________________________________________________________

## Phase 1 — Core Platform Completion

> Finish what's stubbed. These are the highest-impact gaps for a credible portfolio.

### MLFlow Integration (`dex`)

> Replace the custom JSON-based ModelRegistry with MLFlow — the industry standard.

- [ ] Add `mlflow>=2.0` to `dex` `[dependency-groups] ml`
- [ ] Implement `MLFlowModelRegistry` wrapping MLFlow's tracking + model registry APIs
- [ ] Map existing `ModelStatus` (development → staging → production → archived) to MLFlow lifecycle stages
- [ ] Add `mlflow_tracking_uri` to settings (default: `http://localhost:5000`)
- [ ] Update `examples/07_model_registry.py` to demo MLFlow
- [ ] Add MLFlow service to `infradex/docker-compose.monitoring.yml`
- [ ] Keep `JsonModelRegistry` as fallback when MLFlow unreachable

### PySpark Pipeline (`datadex`)

> PySpark is declared but not wired into the pipeline engine.

- [ ] Add `SparkConnector` to `datadex/connectors/` (reads/writes Spark DataFrames)
- [ ] Implement `SparkTransform` in `datadex/transforms/` (map PySpark operations to pipeline YAML config)
- [ ] Add Databricks connector (`datadex/connectors/databricks.py`) using `databricks-sdk`
- [ ] Wire Spark session lifecycle into `datadex/engine/runner.py`
- [ ] Add example: `datadex/examples/spark_lakehouse_pipeline.yaml`

### DataSecops (`dex`)

> Security operations on data — PII detection, masking, audit logging. Not implemented anywhere.

- [ ] Add `dex/src/dataenginex/secops/` module
- [ ] `pii.py` — PII field detection (regex + ML-based, patterns: email, SSN, phone, credit card)
- [ ] `masking.py` — Masking/redaction strategies (hash, truncate, tokenize, nullify)
- [ ] `audit.py` — Structured audit log for data access events (who, what, when, where)
- [ ] Integrate PII check into `DataQualityGate` in `dex/core/`
- [ ] Add `secops` example: `examples/11_secops.py`

### Complete DB Connectors (`datadex`)

> Kafka, Postgres, MySQL are stubs that raise `NotImplementedError`.

- [ ] `postgres.py` — implement using `psycopg[binary]`; add to optional `[db]` dep group
- [ ] `mysql.py` — implement using `mysql-connector-python`; add to optional `[db]` dep group
- [ ] `kafka.py` — implement producer/consumer using `confluent-kafka`; add to optional `[streaming]` dep group

### Complete Cloud Storage Backends (`dex`)

> S3Storage and GCSStorage are stubs — they log but don't actually upload/download.

- [ ] `lakehouse/storage.py` — implement `S3Storage` (list, read, write, delete via boto3)
- [ ] `lakehouse/storage.py` — implement `GCSStorage` (via `google-cloud-storage`)
- [ ] `lakehouse/storage.py` — implement `BigQueryStorage` (load/export via `google-cloud-bigquery`)
- [ ] Add integration tests under `tests/integration/test_storage.py` (mock S3 via moto)

### AgentDEX Sandbox Runtime (`agentdex`)

> `runtime/sandbox.py` raises `NotImplementedError` — blocks autonomous code execution.

- [ ] Implement subprocess-based sandbox (restricted env, timeout, memory cap)
- [ ] Optionally: Docker-based sandbox (`docker run --rm --memory 128m`) for stronger isolation
- [ ] Add `RestrictedPython` as optional dep for in-process sandboxing
- [ ] Wire into code execution tool in `agentdex/tools/`

______________________________________________________________________

## Phase 2 — Load Testing + Observability

> Prove the system handles real traffic. Locust is already in careerdex — expand everywhere.

### Locust Load Tests

- [ ] `dex/tests/load/locustfile.py` — test FastAPI endpoints (`/health`, `/api/v1/`, `/metrics`)
- [ ] `datadex/tests/load/locustfile.py` — test pipeline trigger and run status endpoints
- [ ] `agentdex/tests/load/locustfile.py` — test agent creation and tool execution
- [ ] Add `uv run poe load-test` task to each repo's `poe_tasks.toml`
- [ ] Add load test results badge / summary to each repo README

### Observability Completion (`infradex`)

- [ ] Complete Prometheus alert rules for each service in `infradex/monitoring/`
- [ ] Add Grafana dashboard per repo (import via `infradex/monitoring/grafana/`)
- [ ] Wire OpenTelemetry traces from `dex` → Jaeger (already in docker-compose)
- [ ] Add `infradex/ansible/playbooks/deploy-mlflow.yml`

______________________________________________________________________

## Phase 3 — Demo Projects

> These are the portfolio proof points. Each one showcases a different skill combination.

### Language-Learning Agent (`agentdex`)

> Conversational agent that teaches vocabulary/grammar using OpenAI + LangGraph + Ollama + MCP.

- [ ] Create `agentdex/examples/language_learning_agent/`
- [ ] Memory: store user's vocabulary progress (long-term memory module)
- [ ] Tools: dictionary lookup (MCP), pronunciation audio (HTTP tool), quiz generator
- [ ] Planning: lesson plan decomposition (goal decomposition + planning modules)
- [ ] LLM routing: OpenAI for production, Ollama (Qwen3-Coder) for local dev
- [ ] CLI demo + FastAPI endpoint
- [ ] Blog post + YouTube demo (see Phase 5)

### Book Recommender (`careerdex` + `datadex` + `dex`)

> End-to-end: ingest Open Library data → embed → RAG → recommend.

- [ ] `datadex` pipeline YAML: ingest Open Library dataset (REST API connector)
- [ ] `dex` ML: embed book descriptions with `SentenceTransformerEmbedder`
- [ ] `dex` ML: store vectors in Qdrant (add `QdrantVectorStore` to `dex/ml/vectorstore.py`)
- [ ] `careerdex` models: `BookRecommender` using cosine similarity + user history
- [ ] `dex-studio` page: Book Recommender UI with search + recommendations
- [ ] Deploy Qdrant via `infradex/helm/charts/qdrant/` (already scaffolded)

### Movie Recommender (`careerdex` + `datadex` + `dex`)

> Similar stack to book recommender but with TMDB / MovieLens data.

- [ ] `datadex` pipeline YAML: ingest MovieLens 25M dataset
- [ ] `dex` ML: collaborative filtering model (`MovieRecommender` in careerdex)
- [ ] `dex` ML: content-based fallback using movie descriptions + embeddings
- [ ] `dex-studio` page: Movie Recommender UI
- [ ] MLFlow experiment tracking for model comparison

______________________________________________________________________

## Phase 4 — Infrastructure & DevOps

### Free Artifact Registry (replace JFrog)

> **GitHub Container Registry (GHCR)** — already available under TheDataEngineX org, completely free.

- [ ] Push Docker images to `ghcr.io/thedataenginex/<repo>` in each CI workflow
- [ ] Add `docker-build-push.yml` workflow to `dex`, `datadex`, `agentdex`, `careerdex`
- [ ] Update `infradex` Helm `values.yaml` to pull from GHCR instead of Docker Hub
- [ ] Add package visibility settings in GitHub org settings

### Domain + Org Setup

- [ ] Point `thedataenginex.org` DNS to Cloudflare Pages (docs/landing page)
- [ ] Set up `admin@thedataenginex.org` email via Cloudflare Email Routing (free)
- [ ] Configure GitHub org profile (`TheDataEngineX/.github/profile/README.md`)
- [ ] Set up Slack workspace for community (free tier)

### Cloudflare Pages — Docs & Landing Page

- [ ] `dex` already has `mkdocs-material` — run `mkdocs build` and deploy to Cloudflare Pages
- [ ] Configure Cloudflare Pages build settings (build: `uv run mkdocs build`, publish: `site/`)
- [ ] Create `TheDataEngineX/.github/profile/README.md` org landing page on GitHub
- [ ] Link all repos and published content from the org README

### Infradex Completion

- [ ] Complete Terraform modules: Hetzner VPS provisioning (K3s single-node for dev)
- [ ] Complete Ansible playbooks: bootstrap + K3s install + monitoring stack
- [ ] Test full stack deploy: `terraform apply` → `ansible-playbook` → ArgoCD sync
- [ ] Add `infradex/README.md` with architecture diagram

______________________________________________________________________

## Phase 5 — Content & Reach

> Content strategy to build visibility for a job. Post about what you build as you build it.

### Content Pipeline (run in parallel with Phase 1–4)

Each feature you complete = one content piece. Template:

> *"I built X using Y — here's how it works and why I made these decisions"*

| Feature | LinkedIn | Dev.to | YouTube | GitHub |
| -------------------------- | ---------------------------------- | ----------------------- | --------------- | ----------------- |
| MLFlow integration | Short post + diagram | Technical article | 5-min demo | Release notes |
| DataSecops / PII masking | "Why data security matters" | Deep-dive article | — | Example notebook |
| Language-Learning Agent | Agent AI post | Architecture breakdown | Full demo video | README + examples |
| Book/Movie Recommender | "Built a recommender from scratch" | Step-by-step article | Demo video | Colab notebook |
| Full platform demo | "6 repos, 1 platform" | Series finale | Long-form video | Org README |

### Platform Profiles to Set Up

- [ ] **LinkedIn** — headline: "Data/AI/ML Engineer | Building TheDataEngineX | Open Source"
- [ ] **Dev.to** — account as `thedataenginex`, tag all posts: `python`, `mlops`, `dataengineering`, `ai`
- [ ] **YouTube** — channel name: "TheDataEngineX", shorts for quick demos, long-form for deep dives
- [ ] **Instagram** — visual architecture diagrams, tech stack infographics
- [ ] **PyPI** — `dataenginex` already published (0.6.1) — document install + usage in all posts
- [ ] **GitHub** — pin the 6 repos on the org profile, add topics/tags to each repo

### Patreon

> For after you have an audience (~500+ followers). Set up but don't promote until ready.

- [ ] Create Patreon: tiers — free (GitHub), $5 (early access + Discord), $15 (1:1 office hours)

______________________________________________________________________

## Projects — Backlog

- [ ] Book Recommender → see Phase 3
- [ ] Movie Recommender → see Phase 3
- [ ] Streaming Pipeline Demo (`datadex` Kafka connector → real-time dashboard in `dex-studio`)
- [ ] CareerDEX public demo — "find your next data job" powered by careerdex ML models

______________________________________________________________________

## AI / ML Knowledge Map

> Reference — topics to demonstrate through the codebase and content.

### AI Agent Types

- GPT · MoE · VLM · LRM · SLM · LAM

### Generative AI

- LLMs · Transformers · Variational Autoencoders · Diffusion Models · Multimodal Models

### Deep Learning

- Transformers · LSTM · GAN · GNN · Autoencoders

### Neural Networks

- Perceptrons · MLP · Backpropagation · CNNs · RNNs

### Machine Learning

- Regression · Classification · Anomaly Detection · Dimensionality Reduction · Clustering

### Artificial Intelligence

- Reasoning · NLP · Knowledge Representation · Planning · Expert Systems

### Vector Database Decision Guide

| DB | Use when |
| -------- | ------------------------------------------- |
| Pinecone | Zero infra headaches |
| Chroma | Fast local prototyping |
| Weaviate | Text + image data |
| Qdrant | Speed and filtering both matter (our pick) |
| FAISS | Offline or cost-constrained |
| Redis | Latency measured in milliseconds |

______________________________________________________________________

## Architecture Reference

### Repo Map

| Repo | Package | Role |
| ----------- | ------------ | --------------------------------------------------------------- |
| `dex` | `dataenginex`| Core framework — FastAPI, ML, observability, plugins |
| `datadex` | `datadex` | Config-driven pipeline engine — connectors, transforms, lineage |
| `agentdex` | `agentdex` | AI agent orchestration — memory, tools, LLM routing, workflows |
| `careerdex` | `careerdex` | Career intelligence — job ingestion, matching, salary prediction|
| `dex-studio`| `dex-studio` | Desktop UI — NiceGUI, dashboards, ML management |
| `infradex` | `infradex` | IaC — Terraform, Helm, Ansible, ArgoCD, monitoring |

### Data Flow

```text
Data Sources (REST, Kafka, S3, Postgres, Databricks)
      ↓
Ingestion Pipelines  [datadex connectors]
      ↓
Lakehouse (Bronze / Silver / Gold)  [dex lakehouse]
      ↓
Feature Engineering + DataSecops (PII mask)  [dex secops]
      ↓
ML Training + MLflow experiment tracking  [dex ml]
      ↓
Vector Search Index (Qdrant)  [dex vectorstore]
      ↓
RAG Retrieval Layer  [dex ml / agentdex]
      ↓
Inference API  [dex api / agentdex api]
      ↓
UI  [dex-studio]
```

______________________________________________________________________

## MLOps Implementation Workflow

### Experimentation Setup

1. **Define Problem Scope** — Business objective, ML use case, constraints, success metrics.
1. **Prepare Training Data** — Collect, clean, label, validate datasets.
1. **Setup Experiment Tracking** — MLflow: log params, metrics, artifacts.

### Version Control & Reproducibility

1. **Version Code & Data** — Git + DVC or MLflow artifact tracking.
1. **Build Reproducible Pipelines** — `datadex` YAML-driven pipelines.
1. **Package Model Artifacts** — MLflow model registry with stage transitions.

### CI/CD Integration

1. **Setup CI Pipelines** — GitHub Actions: lint → typecheck → test → build.
1. **Automate Model Testing** — Data validation + performance benchmarks.
1. **Register Models Centrally** — MLflow model registry (Phase 1).

### Deployment & Serving

1. **Select Deployment Strategy** — Batch (datadex), real-time (dex API), streaming (Kafka).
1. **Deploy Model Services** — Helm charts via infradex → Kubernetes.
1. **Integrate Production Systems** — Plugin system in `dex/plugins/`.

### Monitoring & Optimization

1. **Monitor Model Performance** — Prometheus metrics + Grafana dashboards (infradex).
1. **Detect Drift & Failures** — PSI-based drift detection already in `dex/ml/`.
1. **Retrain & Improve Models** — MLflow experiment comparison → promote to production.

______________________________________________________________________

## Career

### Target Roles

| Role | Stack to Demonstrate |
| ------------------ | --------------------------------------------------------------------------- |
| **Data Engineer** | PySpark, datadex pipelines, lakehouse, Kafka, Airflow DAGs, Terraform |
| **AI Engineer** | agentdex, LLM routing, RAG, MCP, tool use, LangGraph-style workflows |
| **ML Engineer** | MLflow, model registry, drift detection, training pipelines, Kubernetes |
| **Data Scientist** | careerdex ML models, embeddings, recommenders, salary prediction, analysis |

### Portfolio Narrative

> "I built a production-grade data/AI platform from scratch across 6 repos —
> from raw ingestion through lakehouse, ML training, vector search, agent
> orchestration, and a full desktop UI — and shipped it as open-source on PyPI."
