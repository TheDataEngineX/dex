---
applyTo: "infra/**/*,Dockerfile,docker-compose.yml"
---

# Infrastructure — Project Specifics

## Docker
- Multi-stage build: `python:3.12-slim` base, non-root `dex` user
- No dev deps in production image — maintain `.dockerignore`
- Docker Compose includes Jaeger + OTLP for local observability

## Kubernetes
- Kustomize base: `infra/argocd/base/` (deployment, HPA, ingress, NetworkPolicy, PDB)
- Overlays: `infra/argocd/overlays/` (dev, prod)
- ArgoCD GitOps — deploys on merge | Envs: dev (2 pods, dex-dev), prod (3 pods, dex)
- Set resource limits/requests, liveness/readiness/startup probes

## Monitoring
- Prometheus: `infra/monitoring/prometheus.yml` | Alerts: `infra/monitoring/alerts/`
- Grafana: `infra/monitoring/grafana/` | AlertManager: `infra/monitoring/alertmanager.yml`

## Conventions
- YAML: 2-space indent | Names: lowercase hyphens (`dex-dev`) | Pin image tags, never `latest`
