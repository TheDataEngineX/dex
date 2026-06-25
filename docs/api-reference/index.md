# API Reference

Complete Python API reference for `dataenginex`. All modules are pure Python — no HTTP server required.

| Module | Description |
|--------|-------------|
| [engine](engine.md) | `DexEngine` — main entry point, store, worker |
| [config](config.md) | Schema, loader, settings, defaults |
| [core](core.md) | Medallion architecture, quality gates, interfaces, registry, exceptions |
| [data](data.md) | Connectors, pipeline runner, transforms, profiler, quality |
| [ml](ml.md) | Training, registry, drift detection, serving, feature store, tracking |
| [ai](ai.md) | LLM routing, agents, vector store, memory, retrieval, workflows |
| [lakehouse](lakehouse.md) | Storage backends, catalog, partitioning |
| [warehouse](warehouse.md) | SQL transforms, lineage tracking |
| [secops](secops.md) | PII detection, masking, audit logging, access gates, privacy guard |
| [orchestration](orchestration.md) | Cron scheduler, built-in jobs |
| [middleware](middleware.md) | Structured logging, Prometheus metrics, domain metrics |
| [plugins](plugins.md) | Plugin registry, extension points |
| [api](api.md) | FastAPI helpers — errors, pagination, schemas (for custom HTTP layers) |
