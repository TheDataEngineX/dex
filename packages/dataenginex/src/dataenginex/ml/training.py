"""
Training framework — abstract trainer and scikit-learn implementation.

The ``BaseTrainer`` ABC defines a standard train → evaluate → save lifecycle.
``SklearnTrainer`` provides a concrete implementation using scikit-learn
(when installed; otherwise a stub that raises ``ImportError``).
"""

from __future__ import annotations

import json
import pickle
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from loguru import logger

__all__ = [
    "BaseTrainer",
    "SklearnTrainer",
    "TrainingResult",
]


@dataclass
class TrainingResult:
    """Outcome of a model training run.

    Attributes:
        model_name: Name of the trained model.
        version: Semantic version of this training run.
        metrics: Training metrics (e.g. ``{"train_score": 0.95}``).
        parameters: Hyper-parameters used for training.
        duration_seconds: Wall-clock training time.
        artifact_path: Path where the model artifact is saved.
        trained_at: Timestamp of training completion.
    """

    model_name: str
    version: str
    metrics: dict[str, float] = field(default_factory=dict)
    parameters: dict[str, Any] = field(default_factory=dict)
    duration_seconds: float = 0.0
    artifact_path: str | None = None
    trained_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))

    def to_dict(self) -> dict[str, Any]:
        """Serialize the training result to a plain dictionary."""
        return {
            "model_name": self.model_name,
            "version": self.version,
            "metrics": self.metrics,
            "parameters": self.parameters,
            "duration_seconds": round(self.duration_seconds, 2),
            "artifact_path": self.artifact_path,
            "trained_at": self.trained_at.isoformat(),
        }


class BaseTrainer(ABC):
    """Abstract base class for model trainers."""

    def __init__(self, model_name: str, version: str = "1.0.0") -> None:
        self.model_name = model_name
        self.version = version

    @abstractmethod
    def train(
        self,
        X_train: Any,
        y_train: Any,
        **params: Any,  # noqa: N803
    ) -> TrainingResult:
        """Train the model and return metrics."""
        ...

    @abstractmethod
    def evaluate(self, X_test: Any, y_test: Any) -> dict[str, float]:  # noqa: N803
        """Evaluate the model on test data."""
        ...

    @abstractmethod
    def predict(self, X: Any) -> Any:  # noqa: N803
        """Generate predictions."""
        ...

    @abstractmethod
    def save(self, path: str) -> str:
        """Persist the model to *path* and return the artifact path."""
        ...

    @abstractmethod
    def load(self, path: str) -> None:
        """Load a previously saved model from *path*."""
        ...


class SklearnTrainer(BaseTrainer):
    """scikit-learn model trainer.

    Works with any sklearn estimator (or pipeline) that implements
    ``fit``, ``predict``, and ``score``.

    Parameters
    ----------
    model_name:
        Name used in model registry.
    version:
        Semantic version string.
    estimator:
        An sklearn estimator instance (e.g. ``RandomForestClassifier()``).
    """

    def __init__(
        self,
        model_name: str,
        version: str = "1.0.0",
        estimator: Any = None,
    ) -> None:
        super().__init__(model_name, version)
        self.estimator = estimator
        self._is_fitted = False

    def train(
        self,
        X_train: Any,
        y_train: Any,
        **params: Any,  # noqa: N803
    ) -> TrainingResult:
        """Fit the estimator on *X_train*/*y_train* and return metrics."""
        if self.estimator is None:
            raise RuntimeError("No estimator provided to SklearnTrainer")

        # Apply params
        if params:
            self.estimator.set_params(**params)

        start = time.perf_counter()
        self.estimator.fit(X_train, y_train)
        duration = time.perf_counter() - start
        self._is_fitted = True

        # Compute training score
        train_score = float(self.estimator.score(X_train, y_train))
        metrics = {"train_score": round(train_score, 4)}

        logger.info(
            "Trained %s v%s in %.2fs (train_score=%.4f)",
            self.model_name,
            self.version,
            duration,
            train_score,
        )

        return TrainingResult(
            model_name=self.model_name,
            version=self.version,
            metrics=metrics,
            parameters=self.estimator.get_params(),
            duration_seconds=duration,
        )

    def evaluate(self, X_test: Any, y_test: Any) -> dict[str, float]:  # noqa: N803
        """Score the fitted model on *X_test*/*y_test* and return metrics."""
        if not self._is_fitted:
            raise RuntimeError("Model not yet trained")

        test_score = float(self.estimator.score(X_test, y_test))
        predictions = self.estimator.predict(X_test)

        metrics: dict[str, float] = {"test_score": round(test_score, 4)}

        # Attempt classification metrics
        try:
            from sklearn.metrics import (  # type: ignore[import-not-found]
                f1_score,
                precision_score,
                recall_score,
            )

            metrics["precision"] = round(
                float(
                    precision_score(
                        y_test,
                        predictions,
                        average="weighted",
                        zero_division=0,
                    ),
                ),
                4,
            )
            metrics["recall"] = round(
                float(
                    recall_score(
                        y_test,
                        predictions,
                        average="weighted",
                        zero_division=0,
                    ),
                ),
                4,
            )
            metrics["f1"] = round(
                float(
                    f1_score(
                        y_test,
                        predictions,
                        average="weighted",
                        zero_division=0,
                    ),
                ),
                4,
            )
        except Exception:
            pass

        return metrics

    def predict(self, X: Any) -> Any:  # noqa: N803
        """Generate predictions for *X* using the fitted estimator."""
        if not self._is_fitted:
            raise RuntimeError("Model not yet trained")
        return self.estimator.predict(X)

    def save(self, path: str) -> str:
        """Pickle the fitted model and its metadata to *path*."""
        if not self._is_fitted:
            raise RuntimeError("Model not yet trained")

        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(pickle.dumps(self.estimator))

        # Save metadata alongside
        meta = out.with_suffix(".json")
        meta.write_text(
            json.dumps(
                {
                    "model_name": self.model_name,
                    "version": self.version,
                    "saved_at": datetime.now(tz=UTC).isoformat(),
                }
            )
        )

        logger.info("Saved model %s to %s", self.model_name, out)
        return str(out)

    def load(self, path: str) -> None:
        """Load a pickled model from *path* and mark as fitted."""
        data = Path(path).read_bytes()
        self.estimator = pickle.loads(data)  # noqa: S301
        self._is_fitted = True
        logger.info("Loaded model %s from %s", self.model_name, path)
