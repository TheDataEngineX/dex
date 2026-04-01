# Changelog

All notable changes to `dataenginex` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.10.0](https://github.com/TheDataEngineX/dex/compare/v0.9.9...v0.10.0) (2026-04-01)


### Features

* docs cleanup ([f4eff14](https://github.com/TheDataEngineX/dex/commit/f4eff14a1aeed657b715b182ac495c920f7b701f))
* docs notify ([#210](https://github.com/TheDataEngineX/dex/issues/210)) ([c36616d](https://github.com/TheDataEngineX/dex/commit/c36616d9d0ae7a97274bd40ea41f39bc26f68fe0))
* quality schema spark audit ([#212](https://github.com/TheDataEngineX/dex/issues/212)) ([2965801](https://github.com/TheDataEngineX/dex/commit/2965801257f6949a48f1c59be2f88e92294b4691))


### Bug Fixes

* add last-release-sha to anchor release-please at v0.9.9 ([7e78ca2](https://github.com/TheDataEngineX/dex/commit/7e78ca203347ff4c4000ca6ec42c335650da1b86))
* restructure release-please-config to packages format with last-release-sha ([46f0b69](https://github.com/TheDataEngineX/dex/commit/46f0b69b8372d54d26ba60eedd9095d7fb0f6cd3))
* sync dev to main ([40d5dff](https://github.com/TheDataEngineX/dex/commit/40d5dff99ae4295599badc848cd530df6eff9ffb))


### Documentation

* docs cleanup ([#211](https://github.com/TheDataEngineX/dex/issues/211)) ([0a6b7f7](https://github.com/TheDataEngineX/dex/commit/0a6b7f70287eb7399eb17acea2fb0ad09efd0597))

## [Unreleased]

## [0.7.1] - 2026-03-17

### Fixed

- **MLflow 3.x alias API** — `MLflowModelRegistry` now uses the alias-based API (`get_model_version_by_alias`, `set_registered_model_alias`, `delete_registered_model_alias`). MLflow 3.x removed all stage-based model management (`get_latest_versions`, `transition_model_version_stage`, `current_stage`).
- **Release workflow reliability** — removed `paths: - 'pyproject.toml'` filter from `release-dataenginex.yml`. GitHub suppresses all push-event workflow triggers when a commit modifies `.github/workflows/`; the tag-exists check inside the workflow handles no-ops.
- **Duplicate mypy override** — removed duplicate `[[tool.mypy.overrides]] module = ["mlflow.*"]` in `pyproject.toml` left by merge conflict.

### Changed

- **Cloud SDKs now optional** — `boto3`, `google-cloud-storage`, `google-cloud-bigquery` moved from core dependencies to `[project.optional-dependencies] cloud = [...]`. Install via `pip install dataenginex[cloud]`. Core install no longer requires any cloud SDK.
- **GCS emulator updated for 3.x** — `GCSStorage` now uses `ClientOptions(api_endpoint=...)` instead of the removed private `client._connection.API_BASE_URL`.
- **Dependency floors bumped** — pydantic 2.10, fastapi 0.135.1, pyarrow 23.0.1, sentence-transformers 5.3, mlflow 3.0, hatchling 1.29, mkdocstrings 1.0.

## [0.6.1] - 2026-03-15

### Added

- **`SentenceTransformerEmbedder`** — thin wrapper over `sentence-transformers` (`all-MiniLM-L6-v2` default). Install via `uv add 'dataenginex[ml]'`. Implements the `embed_fn` protocol for `RAGPipeline`.
- **`RAGPipeline.answer(question, llm, ...)`** — full retrieve → augment → generate loop in one call. Combines `build_context` with any `LLMProvider.generate_with_context`.
- **GitHub Actions upgraded to Node.js 24** — `ci.yml`, `pypi-publish.yml`, `release-dataenginex.yml`, `security.yml` now use `actions/checkout@v6`, `actions/setup-python@v6`, `astral-sh/setup-uv@v7`.
- **`examples/05_rag_demo.py`** — end-to-end RAG demo with `--embed`, `--llm`, `--model` CLI flags; Ollama fallback to MockProvider; uses `RAGPipeline.answer()`.

## [0.6.0] - 2026-03-03

### Changed — BREAKING

- **Routers removed** — `api/routers/v1.py` and `api/routers/ml.py` moved to application packages (e.g. `careerdex.api.routers`). `dataenginex` no longer ships any route definitions — it provides only reusable API utilities (auth, health, errors, pagination, rate limiting).
- **FastAPI is now optional** — Core install (`pip install dataenginex`) includes only lightweight deps: `pydantic`, `pyyaml`, `loguru`, `httpx`, `python-dotenv`, `prometheus-client`. API/middleware consumers must install `pip install dataenginex[api]` to get FastAPI, uvicorn, structlog, OpenTelemetry.
- **Root `__init__.py` slimmed** — `from dataenginex import ...` no longer re-exports `HealthChecker`, `HealthStatus`, `configure_logging`, `configure_tracing`, `get_logger`. Use `from dataenginex.api import ...` or `from dataenginex.middleware import ...` directly (requires `[api]` extra).
- **Domain extraction** — Removed all CareerDEX-specific code from the framework:
  - Removed domain schemas from `core/schemas.py`: `JobSourceEnum`, `JobLocation`, `JobBenefits`, `JobPosting`, `UserProfile`, `PipelineExecutionMetadata`, `DataQualityReport`
  - Removed domain validators from `core/validators.py`: `SchemaValidator`, `DataHash`, `QualityScorer`, domain-specific `DataQualityChecks` methods
  - Deleted `core/pipeline_config.py` (100% domain-specific)
  - Cleaned up all domain-specific docstring examples (`job_posting`, `job_classifier`, `salary_min`) → replaced with generic examples
- **Injectable `QualityGate`** — `QualityGate.__init__` now accepts `scorer`, `required_fields`, and `uniqueness_key` keyword arguments
- **Real `LocalParquetStorage`** — Reads/writes actual Parquet files via `pyarrow` (optional dep with `_HAS_PYARROW` guard)
- **`BigQueryStorage` stubbed** — All methods raise `NotImplementedError`

### Fixed

- **Pickle safety** — `ml/training.py` now uses `SafeUnpickler` restricting deserialization to sklearn/numpy namespaces only; HMAC signature verification on model load (`DATAENGINEX_MODEL_HMAC_KEY` env var)
- **Error swallowing** — `ml/training.py` `evaluate()` silence `except Exception: pass` → `except ImportError: logger.debug(...)` for optional metrics
- **LLM error handling** — `OllamaProvider.generate()`/`chat()` raise `ConnectionError` on HTTP failures instead of returning empty `LLMResponse`
- **Pagination cursor** — `decode_cursor()` raises `ValueError` on invalid input instead of silently returning 0
- **Storage backends** — `S3Storage.exists()` catches `NoSuchKey` specifically; `GCSStorage.exists()` returns `blob.exists()` directly with specific exception handling

### Added

- **RAG Vector DB adapter** — `VectorStoreBackend` ABC with `InMemoryBackend` and `ChromaDBBackend` implementations; `RAGPipeline` orchestrator for document ingestion and semantic retrieval; `Document` and `SearchResult` dataclasses (#94)
- **LLM integration** — `LLMProvider` ABC with `OllamaProvider` (local Ollama REST API) and `MockProvider` for testing; `generate_with_context()` for RAG-style augmented generation; `ChatMessage`, `LLMConfig`, `LLMResponse` dataclasses (#95)
- **CareerDEX Phase 1: Foundation** — config loading from `job_config.json`, schema validation (JobPosting, UserProfile, PipelineExecutionMetadata), medallion architecture bootstrap, sample data generation (#65)
- **CareerDEX Phase 2: Job Ingestion** — `JobSourceConnector` ABC with LinkedIn, Indeed, Glassdoor, CompanyCareerPages connectors; `DeduplicationEngine` for content-hash dedup; `JobIngestionPipeline` orchestrator (#66)
- **CareerDEX Phase 3: Feature Engineering** — `JobDescriptionParser` (skill/salary/seniority extraction), `ResumeParser`, `SkillNormalizer` with 30+ alias mappings and category taxonomy, `EmbeddingGenerator` with sentence-transformers + hash fallback, `InMemoryVectorStore` (#67)
- **CareerDEX Phase 4: ML Models** — `ResumeJobMatcher` (weighted cosine + skill/location/salary scoring), `SalaryPredictor` (XGBoost-style with location/seniority/skills adjustments), `SkillGapAnalyzer` (collaborative filtering), `CareerPathRecommender` (transition graph), `ChurnPredictor` (logistic regression) (#68)
- **CareerDEX Phase 5: API Services** — FastAPI router at `/api/v1/careerdex/` with endpoints: salary prediction, skill gap analysis, career paths, career health/churn risk, market trends, job recommendations; full Pydantic request/response models (#69)
- **CareerDEX Phase 6: Testing & Deployment** — `DeploymentConfig` with K8s manifest helpers, `MonitoringConfig` with 5 default Prometheus alert rules, `SecurityAudit` for secret scanning and SQL injection detection (#70)
- Re-exports in root `__init__.py` and `ml/__init__.py` for all new vector store and LLM symbols
- 82 new unit tests: `test_careerdex_phases.py` (55 tests), `test_vectorstore.py` (16 tests), `test_llm.py` (11 tests)

## [0.5.0] - 2026-03-01

### Added

- **Storage abstraction** — `list_objects(prefix)` and `exists(path)` on `StorageBackend` ABC; concrete implementations in `LocalParquetStorage`, `BigQueryStorage`, `JsonStorage`, `ParquetStorage`, `S3Storage`, `GCSStorage`; `get_storage(uri)` factory function (#89)
- **ML serving endpoints** — `POST /api/v1/predict`, `GET /api/v1/models`, `GET /api/v1/models/{name}` with `PredictRequestBody`/`PredictResponseBody` Pydantic models; ML-specific Prometheus metrics (`model_prediction_latency_seconds`, `model_prediction_total`, `model_predictions_in_flight`) (#92)
- **Drift monitoring scheduler** — `DriftScheduler` with background thread for periodic drift checks; `DriftMonitorConfig`, `DriftCheckResult` dataclasses; publishes PSI scores to `model_drift_psi` gauge; increments `model_drift_alerts_total` counter on drift detection (#93)
- Prometheus alert rules for drift monitoring — `ModelDriftModerate`, `ModelDriftSevere`, `DriftAlertSpike`, `DriftCheckStale` in `monitoring/alerts/drift_alerts.yml`
- `endpoint_url` parameter on `S3Storage` for LocalStack/emulator support
- `api_endpoint` parameter on `GCSStorage` for fake-gcs-server/emulator support
- Docker emulator stack (`docker-compose.test.yml`) — LocalStack 4.0 (S3) + fake-gcs-server 1.49 (GCS)
- 25 integration tests with emulator auto-detection in `tests/integration/test_storage_real.py`
- Terraform module for cloud test buckets (moved to infrastructure repo)
- Google-style docstrings across 55+ methods and 9 Pydantic models (#88)
- `py.typed` marker for PEP 561 compliance — downstream consumers get type checking support
- Module-level `__all__` in all 30 `.py` source files — every public symbol is explicitly gated
- Convenience re-exports in root `__init__.py` — `from dataenginex import MedallionArchitecture` etc.
- `core/__init__.py` now exports: `BigQueryStorage`, `DataLineage`, `DualStorage`, `LocalParquetStorage`, `StorageBackend`, `ComponentStatus`, `EchoRequest`, `EchoResponse`, `ReadinessResponse`, `StartupResponse`
- PyPI badge in README (#87)

### Fixed

- `docs-pages.yml` workflow: replaced `uv lock && uv sync` with `uv sync --frozen` to prevent lock drift in CI
- `Dockerfile` runtime stage: added missing `COPY --from=builder /build/packages /app/packages` for `PYTHONPATH` resolution
- mypy overrides for optional cloud SDKs (`boto3`, `google.auth`, `google.cloud`) — prevents `unused-ignore` vs `import-not-found` flip-flop depending on installed packages

## [0.4.11] - 2026-02-27

### Changed

- Added `environment` label support across HTTP metrics counters/histograms/gauges and middleware emission.
- Aligned alert rule histogram quantile expressions with explicit bucket aggregation by `le` and `environment`.
- Standardized docs and release prep metadata for CSV-canonical roadmap and setup workflow updates.

## [0.4.10] - 2026-02-21

### Added

- `examples/` directory with 4 runnable quickstart scripts
- `01_hello_pipeline.py` — profiler, schema validation, medallion config
- `02_api_quickstart.py` — FastAPI app with health, v1 router, metrics
- `03_quality_gate.py` — QualityGate evaluations against layer thresholds
- `04_ml_training.py` — SklearnTrainer, ModelRegistry, DriftDetector demo
- `examples/GUIDE.md` with table of examples and run instructions

## [0.4.8] - 2026-02-21

### Added

- PySpark local-mode test fixtures in `tests/conftest.py` (session-scoped `spark` session)
- Sample DataFrame fixtures: `spark_df_jobs`, `spark_df_weather`, `spark_df_empty`
- `requires_pyspark` skip marker — tests auto-skip when PySpark is not installed
- `tests/fixtures/sample_data.py` — factory helpers for job, user, and weather records
- `tests/unit/test_spark_fixtures.py` — validates PySpark fixture behaviour

## [0.4.6] - 2026-02-21

### Added

- `QualityGate` — orchestrates quality checks at medallion layer transitions
- `QualityStore` — in-memory store accumulating per-layer quality metrics
- `QualityResult` — immutable dataclass capturing evaluation outcomes
- `QualityDimension` — StrEnum for named quality dimensions
- `/api/v1/data/quality/{layer}` endpoint for per-layer quality history
- `set_quality_store()` / `get_quality_store()` for wiring quality at app startup
- New exports in `dataenginex.core` and `dataenginex.api`

### Changed

- `/api/v1/data/quality` now returns live metrics from `QualityStore` (was placeholder zeros)
- Wired `DataProfiler`, `DataQualityChecks`, and `QualityScorer` into `QualityGate` pipeline

## [0.4.5] - 2026-02-21

### Added

- `StorageBackend` ABC with proper `@abstractmethod` contracts
- `S3Storage` backend for AWS S3 (requires `boto3`)
- `GCSStorage` backend for Google Cloud Storage (requires `google-cloud-storage`)
- Re-exported `StorageBackend` from `dataenginex.lakehouse`

### Changed

- Refactored `StorageBackend` from plain class to proper `ABC` subclass
- Updated `lakehouse.__init__` to export all 4 storage backends + ABC

## [0.4.3] - 2026-02-21

### Added

- Comprehensive attribute-level docstrings on all public dataclasses
- `from __future__ import annotations` in all source modules
- Module-level class/function inventory docstrings
- mkdocs API reference configuration with `mkdocstrings` plugin
- API reference pages for all 7 subpackages under `docs/api-reference/`

### Changed

- Upgraded mkdocs theme from `mkdocs` to `material`
- Enhanced module docstrings in middleware, core, and validators

## [0.4.1] - 2026-02-21

### Added

- CHANGELOG.md with Keep a Changelog format
- Release workflow extracts changelog notes for GitHub Releases automatically

### Changed

- `release.yml` now reads `packages/dataenginex/CHANGELOG.md` for release notes

## [0.4.0] - 2026-02-21

### Added

- Stable `__all__` exports in every subpackage `__init__.py`
- `from __future__ import annotations` in all public modules
- Comprehensive module-level docstrings with usage examples
- New public API exports: `ComponentHealth`, `AuthMiddleware`, `AuthUser`,
  `create_token`, `decode_token`, `BadRequestError`, `NotFoundError`,
  `PaginationMeta`, `RateLimiter`, `RateLimitMiddleware`,
  `ConnectorStatus`, `FetchResult`, `ColumnProfile`, `get_logger`, `get_tracer`

### Changed

- Reorganized `__all__` in all subpackages for logical grouping
- Updated package version to 0.4.0

## [0.3.5] - 2026-02-13

### Added

- Production hardening: structured logging, Prometheus/OTel, health probes
- Data connectors: `RestConnector`, `FileConnector` with async interface
- Schema registry with versioned schema management
- Data profiler with automated dataset statistics
- Lakehouse catalog, partitioning, and storage backends
- ML framework: trainer, model registry, drift detection, serving
- Warehouse transforms and persistent lineage tracking
- JWT authentication middleware
- Rate limiting middleware
- Cursor-based pagination utilities
- Versioned API router (`/api/v1/`)

[0.3.5]: https://github.com/TheDataEngineX/DEX/releases/tag/v0.3.5
[0.4.0]: https://github.com/TheDataEngineX/DEX/compare/v0.3.5...v0.4.0
[0.4.1]: https://github.com/TheDataEngineX/DEX/compare/v0.4.0...v0.4.1
[0.4.10]: https://github.com/TheDataEngineX/DEX/compare/v0.4.8...v0.4.10
[0.4.11]: https://github.com/TheDataEngineX/DEX/compare/v0.4.10...v0.4.11
[0.4.3]: https://github.com/TheDataEngineX/DEX/compare/v0.4.1...v0.4.3
[0.4.5]: https://github.com/TheDataEngineX/DEX/compare/v0.4.3...v0.4.5
[0.4.6]: https://github.com/TheDataEngineX/DEX/compare/v0.4.5...v0.4.6
[0.4.8]: https://github.com/TheDataEngineX/DEX/compare/v0.4.6...v0.4.8
[0.5.0]: https://github.com/TheDataEngineX/DEX/compare/v0.4.11...v0.5.0
[unreleased]: https://github.com/TheDataEngineX/DEX/compare/v0.5.0...HEAD
