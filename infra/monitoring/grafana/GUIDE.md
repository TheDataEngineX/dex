# Grafana Dashboards

This folder contains ready-to-import Grafana dashboards for DataEngineX observability.

## Dashboards

- **DEX Metrics**: Prometheus-based service metrics (latency, error rate, RPS, in-flight).
- **DEX Logs**: Loki-based log exploration and error spikes.
- **DEX Traces**: Tempo-based tracing overview and trace search.

## Import

### Automatic (docker compose)

Dashboards and the Prometheus datasource are auto-provisioned when using `docker compose up -d`. No manual import needed.

### Manual

1. Open Grafana → **Dashboards** → **New** → **Import**.
2. Upload the JSON from `infra/monitoring/grafana/dashboards/`.
3. Select the correct data sources when prompted.

## Data Sources

- **Prometheus**: required for metrics dashboard.
- **Loki**: required for logs dashboard.
- **Tempo** (or OTLP/Jaeger-backed Tempo): required for traces dashboard.

## Notes

Dashboards are designed to work with default labels from DataEngineX metrics and structured logs. If your labels differ, update the dashboard variables or panel queries.
