"""
Model registry — local model versioning and stage promotion.

Tracks model artifacts with staging lifecycle:
``development`` → ``staging`` → ``production`` → ``archived``.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from loguru import logger

__all__ = [
    "ModelArtifact",
    "ModelRegistry",
    "ModelStage",
]


class ModelStage(StrEnum):
    """Model lifecycle stages."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    ARCHIVED = "archived"


@dataclass
class ModelArtifact:
    """Registry entry for a model version.

    Attributes:
        name: Model name (e.g. ``"churn_classifier"``).
        version: Semantic version string.
        stage: Current lifecycle stage.
        artifact_path: File path to the serialised model.
        metrics: Training/evaluation metrics.
        parameters: Hyper-parameters used for training.
        description: Free-text description.
        created_at: When the artifact was registered.
        promoted_at: When the artifact was last promoted.
        tags: Arbitrary labels for filtering.
    """

    name: str
    version: str
    stage: ModelStage = ModelStage.DEVELOPMENT
    artifact_path: str = ""
    metrics: dict[str, float] = field(default_factory=dict)
    parameters: dict[str, Any] = field(default_factory=dict)
    description: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    promoted_at: datetime | None = None
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the model artifact metadata to a plain dictionary."""
        d = asdict(self)
        d["stage"] = self.stage.value
        d["created_at"] = self.created_at.isoformat()
        d["promoted_at"] = self.promoted_at.isoformat() if self.promoted_at else None
        return d


class ModelRegistry:
    """JSON-file-backed model registry.

    Parameters
    ----------
    persist_path:
        Path to a JSON file for persistence (optional).
    """

    def __init__(self, persist_path: str | Path | None = None) -> None:
        # name → version → artifact
        self._models: dict[str, dict[str, ModelArtifact]] = {}
        self._persist_path = Path(persist_path) if persist_path else None
        if self._persist_path and self._persist_path.exists():
            self._load()

    # -- registration --------------------------------------------------------

    def register(self, artifact: ModelArtifact) -> ModelArtifact:
        """Register a new model version."""
        versions = self._models.setdefault(artifact.name, {})
        if artifact.version in versions:
            raise ValueError(
                f"Model {artifact.name!r} version {artifact.version} already registered"
            )
        versions[artifact.version] = artifact
        logger.info(
            "Registered model %s v%s (stage=%s)",
            artifact.name,
            artifact.version,
            artifact.stage.value,
        )
        self._save()
        return artifact

    # -- queries -------------------------------------------------------------

    def get(self, name: str, version: str) -> ModelArtifact | None:
        """Return the artifact for *name* at *version*, or ``None``."""
        return self._models.get(name, {}).get(version)

    def get_latest(self, name: str) -> ModelArtifact | None:
        """Return the most recently registered version of *name*."""
        versions = self._models.get(name)
        if not versions:
            return None
        return list(versions.values())[-1]

    def get_production(self, name: str) -> ModelArtifact | None:
        """Return the model currently in production stage."""
        for art in self._models.get(name, {}).values():
            if art.stage == ModelStage.PRODUCTION:
                return art
        return None

    def list_models(self) -> list[str]:
        """Return all registered model names."""
        return list(self._models.keys())

    def list_versions(self, name: str) -> list[str]:
        """Return all version strings registered for *name*."""
        return list(self._models.get(name, {}).keys())

    # -- promotion -----------------------------------------------------------

    def promote(self, name: str, version: str, target_stage: ModelStage) -> ModelArtifact:
        """Promote a model version to a new stage.

        If promoting to ``production``, any existing production model is
        automatically archived.
        """
        artifact = self.get(name, version)
        if artifact is None:
            raise ValueError(f"Model {name!r} version {version} not found")

        if target_stage == ModelStage.PRODUCTION:
            # Archive the current production model
            current = self.get_production(name)
            if current and current.version != version:
                current.stage = ModelStage.ARCHIVED
                logger.info("Archived %s v%s", name, current.version)

        artifact.stage = target_stage
        artifact.promoted_at = datetime.now(tz=UTC)
        logger.info("Promoted %s v%s → %s", name, version, target_stage.value)
        self._save()
        return artifact

    # -- persistence ---------------------------------------------------------

    def _save(self) -> None:
        if not self._persist_path:
            return
        self._persist_path.parent.mkdir(parents=True, exist_ok=True)
        data: dict[str, list[dict[str, Any]]] = {}
        for name, versions in self._models.items():
            data[name] = [v.to_dict() for v in versions.values()]
        self._persist_path.write_text(json.dumps(data, indent=2, default=str))

    def _load(self) -> None:
        if not self._persist_path or not self._persist_path.exists():
            return
        raw = json.loads(self._persist_path.read_text())
        for name, versions in raw.items():
            self._models[name] = {}
            for v in versions:
                v.pop("created_at", None)
                v.pop("promoted_at", None)
                v["stage"] = ModelStage(v.get("stage", "development"))
                self._models[name][v["version"]] = ModelArtifact(**v)
        logger.info("Loaded %d models from %s", len(self._models), self._persist_path)
