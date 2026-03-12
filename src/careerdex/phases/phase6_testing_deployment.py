"""CareerDEX Phase 6: Testing, Documentation & Deployment (Issue #70).

Provides utilities for:
- Deployment configuration (Docker, K8s, GCP Cloud Run)
- Monitoring dashboards and alerting rules
- Load-test configuration (Locust)
- Health-check integration
- Security audit helpers

This module does NOT perform actual deployment — it generates the
configuration that deployment tools (ArgoCD, GitHub Actions) consume.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from loguru import logger

__all__ = [
    "AlertRule",
    "DeploymentConfig",
    "MonitoringConfig",
    "SecurityAudit",
    "generate_deployment_config",
]


# ======================================================================
# Deployment configuration
# ======================================================================


@dataclass
class DeploymentConfig:
    """Deployment parameters for CareerDEX."""

    image: str = "ghcr.io/thedataenginex/dex:latest"
    replicas: int = 2
    cpu_request: str = "250m"
    cpu_limit: str = "1000m"
    memory_request: str = "512Mi"
    memory_limit: str = "2Gi"
    port: int = 8000
    health_path: str = "/health"
    readiness_path: str = "/ready"
    startup_path: str = "/startup"
    env_vars: dict[str, str] = field(default_factory=dict)

    def to_k8s_env(self) -> list[dict[str, str]]:
        """Convert env vars to K8s manifest format."""
        return [{"name": k, "value": v} for k, v in sorted(self.env_vars.items())]

    def summary(self) -> dict[str, Any]:
        """Return a deployment summary dict."""
        return {
            "image": self.image,
            "replicas": self.replicas,
            "resources": {
                "cpu": f"{self.cpu_request}/{self.cpu_limit}",
                "memory": f"{self.memory_request}/{self.memory_limit}",
            },
            "probes": {
                "health": self.health_path,
                "readiness": self.readiness_path,
                "startup": self.startup_path,
            },
            "env_var_count": len(self.env_vars),
        }


# ======================================================================
# Monitoring & alerting
# ======================================================================


@dataclass
class AlertRule:
    """Prometheus alerting rule."""

    name: str
    expr: str
    duration: str = "5m"
    severity: str = "warning"
    summary: str = ""

    def to_prom_rule(self) -> dict[str, Any]:
        """Serialise to Prometheus rule YAML structure."""
        return {
            "alert": self.name,
            "expr": self.expr,
            "for": self.duration,
            "labels": {"severity": self.severity},
            "annotations": {"summary": self.summary or self.name},
        }


@dataclass
class MonitoringConfig:
    """Monitoring and alerting setup."""

    alert_rules: list[AlertRule] = field(default_factory=list)

    @classmethod
    def default(cls) -> MonitoringConfig:
        """Return default alerting rules for CareerDEX."""
        return cls(
            alert_rules=[
                AlertRule(
                    name="HighErrorRate",
                    expr='rate(http_requests_total{status=~"5.."}[5m]) > 0.05',
                    severity="critical",
                    summary="CareerDEX API error rate > 5 %",
                ),
                AlertRule(
                    name="HighLatency",
                    expr=(
                        "histogram_quantile(0.95,"
                        " rate(http_request_duration_seconds_bucket[5m])) > 2"
                    ),
                    severity="warning",
                    summary="P95 latency exceeds 2 s",
                ),
                AlertRule(
                    name="IngestionPipelineStale",
                    expr="time() - careerdex_last_ingestion_timestamp > 14400",
                    severity="warning",
                    summary="No ingestion in 4 hours (expected every 3 h)",
                ),
                AlertRule(
                    name="ModelDriftDetected",
                    expr="model_drift_psi > 0.25",
                    severity="critical",
                    summary="Model drift PSI exceeds severe threshold",
                ),
                AlertRule(
                    name="LowQualityScore",
                    expr="careerdex_quality_score_avg < 0.6",
                    duration="15m",
                    severity="warning",
                    summary="Average data quality score below 0.6",
                ),
            ]
        )

    def all_rules_yaml(self) -> list[dict[str, Any]]:
        """Return all rules in Prometheus YAML format."""
        return [r.to_prom_rule() for r in self.alert_rules]


# ======================================================================
# Security audit
# ======================================================================


class SecurityAudit:
    """Security checklist helpers.

    Each method returns ``(passed, findings)`` so they can be aggregated
    into a report.
    """

    @staticmethod
    def check_no_hardcoded_secrets(
        file_contents: dict[str, str],
    ) -> tuple[bool, list[str]]:
        """Scan file contents for common secret patterns.

        Args:
            file_contents: Mapping of file path → file text.

        Returns:
            ``(passed, list_of_findings)``
        """
        import re

        patterns = [
            (r"(?i)(api[_-]?key|secret|password|token)\s*=\s*['\"][^'\"]{8,}", "hardcoded secret"),
            (r"(?i)AKIA[0-9A-Z]{16}", "AWS access key"),
            (r"-----BEGIN (RSA |EC )?PRIVATE KEY-----", "private key"),
        ]
        findings: list[str] = []
        for path, text in file_contents.items():
            for pattern, label in patterns:
                if re.search(pattern, text):
                    findings.append(f"{path}: potential {label}")

        passed = len(findings) == 0
        logger.info("security audit secrets passed={} findings={}", passed, len(findings))
        return passed, findings

    @staticmethod
    def check_sql_injection(
        file_contents: dict[str, str],
    ) -> tuple[bool, list[str]]:
        """Flag string-concatenated SQL queries."""
        import re

        pattern = r'(?i)(execute|cursor\.execute)\s*\(\s*f["\']'
        findings: list[str] = []
        for path, text in file_contents.items():
            if re.search(pattern, text):
                findings.append(f"{path}: possible SQL injection via f-string")

        passed = len(findings) == 0
        logger.info("security audit sql_injection passed={} findings={}", passed, len(findings))
        return passed, findings


# ======================================================================
# Convenience
# ======================================================================


def generate_deployment_config(
    env: str = "dev",
    image_tag: str = "latest",
) -> DeploymentConfig:
    """Generate deployment configuration for *env*.

    Args:
        env: Target environment (``dev`` or ``prod``).
        image_tag: Docker image tag.

    Returns:
        Populated ``DeploymentConfig``.
    """
    replicas = 1 if env == "dev" else 3
    cfg = DeploymentConfig(
        image=f"ghcr.io/thedataenginex/dex:{image_tag}",
        replicas=replicas,
        env_vars={
            "ENVIRONMENT": env,
            "LOG_LEVEL": "DEBUG" if env == "dev" else "INFO",
            "LOG_FORMAT": "json",
        },
    )
    logger.info("deployment config env={} replicas={} image={}", env, replicas, cfg.image)
    return cfg
