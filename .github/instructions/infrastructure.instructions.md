---
applyTo: "monitoring/**/*,Dockerfile,docker-compose.yml,docker-compose.test.yml"
---

# Infrastructure — Project Specifics

## Docker
- Multi-stage build: `python:3.12-slim` base, non-root `dex` user
- No dev deps in production image — maintain `.dockerignore`
- Docker Compose includes Jaeger + OTLP for local observability

## Monitoring (Local Dev)
- Prometheus: `monitoring/prometheus.yml` | Alerts: `monitoring/alerts/`
- Grafana: `monitoring/grafana/` | AlertManager: `monitoring/alertmanager.yml`
- Run with: `docker compose up -d`

## Conventions
- YAML: 2-space indent | Names: lowercase hyphens (`dex-dev`) | Pin image tags, never `latest`
