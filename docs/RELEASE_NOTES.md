# Release Notes

## v0.5.0 — 2026-03-01

### Highlights

- **Storage abstraction layer** — `list_objects(prefix)` and `exists(path)` on `StorageBackend` ABC with implementations across all 6 backends (Local, BigQuery, JSON, Parquet, S3, GCS). New `get_storage(uri)` factory resolves `s3://`, `gs://`, and local paths automatically (#89)
- **ML serving endpoints** — `POST /api/v1/predict`, `GET /api/v1/models`, `GET /api/v1/models/{name}` with Pydantic request/response models and ML-specific Prometheus metrics for latency, throughput, and in-flight predictions (#92)
- **Drift monitoring scheduler** — `DriftScheduler` runs background drift checks on registered models, publishes PSI scores to Prometheus gauges, and fires alert counters when drift exceeds thresholds. Includes Prometheus alert rules for moderate, severe, spike, and stale drift conditions (#93)
- **Comprehensive docstrings** — Google-style docstrings added across 55+ methods and 9 Pydantic models covering all public APIs (#88)
- **Cloud emulator testing** — Docker Compose stack with LocalStack (S3) and fake-gcs-server (GCS) plus 25 integration tests with auto-detection
- **Infrastructure fixes** — Dockerfile runtime stage now copies the core package; docs workflow uses `--frozen` sync

### Breaking changes

None. All new features are additive.

### Verification checklist

1. `uv run poe lint` — Ruff checks clean
2. `uv run poe typecheck` — mypy strict (40 files, 0 errors)
3. `uv run poe test` — 299 passed, 28 skipped
4. `docker compose build` — multi-stage Dockerfile builds successfully
5. `docker compose -f docker-compose.test.yml up -d` — emulators start healthy

---

## v0.4.11 — 2026-02-27

### Highlights

- **Environment-labeled metrics** — Added `environment` label support across HTTP metrics counters/histograms/gauges and middleware emission
- **Aligned alert rules** — Histogram quantile expressions use explicit bucket aggregation by `le` and `environment`
- **CSV-canonical roadmap** — Standardized docs and release prep metadata

---

## v1.0.0 — 2026-02-11

### Highlights
- **SLO-aware monitoring**: Alerting rules now track latency, error rates, and saturation per environment, routed through Alertmanager runbooks aligned with the SLO definitions documented in `infra/prometheus/alerts/dataenginex-alerts.yml` and `infra/alertmanager`.
- **Environment-labeled metrics**: The Prometheus client now exports all HTTP counters, histograms, and gauges with an `environment` label so dashboards & alerts can differentiate `dev`/`stage`/`prod` workloads without duplicating services.
- **Pyconcepts-facing API**: Added `/api/external-data` (wraps `pyconcepts.external_data.fetch_external_data`) and `/api/insights` (text/event-stream) so downstream runners can consume the helper data + streaming insights from `pyconcepts`.
- **Docs/tests**: `tests/test_main.py` and `tests/test_metrics.py` cover the new endpoints and metrics labels, and the documentation now explains how to validate the new alerts and APIs.

### Verification checklist
1. `uv run poe lint` — Ruff/mypy checks green
2. `uv run pytest -v` — 31 tests including the new endpoints pass
3. `docker compose build` — multi-stage Dockerfile builds
