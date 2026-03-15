"""Tests for dataenginex.ml — training, registry, drift, serving."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from dataenginex.ml.drift import DriftDetector, DriftReport
from dataenginex.ml.registry import ModelArtifact, ModelRegistry, ModelStage
from dataenginex.ml.serving import ModelServer, PredictionRequest
from dataenginex.ml.training import SklearnTrainer, TrainingResult

# ============================================================================
# Training
# ============================================================================


class TestTrainingResult:
    def test_to_dict(self) -> None:
        r = TrainingResult(model_name="test", version="1.0.0", metrics={"acc": 0.95})
        d = r.to_dict()
        assert d["model_name"] == "test"
        assert d["metrics"]["acc"] == 0.95


class TestSklearnTrainer:
    """Exercise the trainer with a dummy estimator (no sklearn needed)."""

    class DummyEstimator:
        """Minimal sklearn-API-compatible estimator."""

        def __init__(self, value: int = 0) -> None:
            self.value = value
            self._fitted = False

        def fit(self, X: Any, y: Any) -> None:
            self._fitted = True

        def predict(self, X: Any) -> list[int]:
            return [self.value] * len(X)

        def score(self, X: Any, y: Any) -> float:
            return 0.85

        def get_params(self) -> dict[str, Any]:
            return {"value": self.value}

        def set_params(self, **params: Any) -> None:
            for k, v in params.items():
                setattr(self, k, v)

    def test_train_and_predict(self) -> None:
        trainer = SklearnTrainer("dummy", "1.0.0", self.DummyEstimator(42))
        result = trainer.train([[1], [2]], [0, 1])
        assert result.model_name == "dummy"
        assert result.metrics["train_score"] == 0.85
        preds = trainer.predict([[1], [2]])
        assert len(preds) == 2

    def test_predict_before_train_raises(self) -> None:
        trainer = SklearnTrainer("dummy", "1.0.0", self.DummyEstimator())
        with pytest.raises(RuntimeError, match="not yet trained"):
            trainer.predict([[1]])

    def test_evaluate(self) -> None:
        trainer = SklearnTrainer("dummy", "1.0.0", self.DummyEstimator())
        trainer.train([[1], [2]], [0, 1])
        metrics = trainer.evaluate([[1]], [0])
        assert "test_score" in metrics

    def test_save_and_load(self, tmp_path: Path) -> None:
        trainer = SklearnTrainer("dummy", "1.0.0", self.DummyEstimator(7))
        trainer.train([[1]], [0])
        path = str(tmp_path / "model.pkl")
        trainer.save(path)

        trainer2 = SklearnTrainer("dummy", "1.0.0")
        trainer2.load(path, extra_modules=frozenset({"tests"}))
        preds = trainer2.predict([[1]])
        assert preds == [7]

    def test_no_estimator_raises(self) -> None:
        trainer = SklearnTrainer("dummy", "1.0.0", estimator=None)
        with pytest.raises(RuntimeError, match="No estimator"):
            trainer.train([[1]], [0])


# ============================================================================
# Model Registry
# ============================================================================


class TestModelRegistry:
    def test_register_and_get(self) -> None:
        reg = ModelRegistry()
        art = ModelArtifact(name="model_a", version="1.0.0", metrics={"acc": 0.9})
        reg.register(art)
        got = reg.get("model_a", "1.0.0")
        assert got is not None
        assert got.metrics["acc"] == 0.9

    def test_duplicate_version_rejected(self) -> None:
        reg = ModelRegistry()
        reg.register(ModelArtifact(name="a", version="1.0.0"))
        with pytest.raises(ValueError, match="already registered"):
            reg.register(ModelArtifact(name="a", version="1.0.0"))

    def test_promote(self) -> None:
        reg = ModelRegistry()
        reg.register(ModelArtifact(name="a", version="1.0.0"))
        reg.promote("a", "1.0.0", ModelStage.PRODUCTION)
        prod = reg.get_production("a")
        assert prod is not None
        assert prod.stage == ModelStage.PRODUCTION

    def test_promote_archives_old(self) -> None:
        reg = ModelRegistry()
        reg.register(ModelArtifact(name="a", version="1.0.0"))
        reg.register(ModelArtifact(name="a", version="2.0.0"))
        reg.promote("a", "1.0.0", ModelStage.PRODUCTION)
        reg.promote("a", "2.0.0", ModelStage.PRODUCTION)
        v1 = reg.get("a", "1.0.0")
        assert v1 is not None
        assert v1.stage == ModelStage.ARCHIVED

    def test_get_latest(self) -> None:
        reg = ModelRegistry()
        reg.register(ModelArtifact(name="a", version="1.0.0"))
        reg.register(ModelArtifact(name="a", version="2.0.0"))
        latest = reg.get_latest("a")
        assert latest is not None
        assert latest.version == "2.0.0"

    def test_list_models(self) -> None:
        reg = ModelRegistry()
        reg.register(ModelArtifact(name="a", version="1.0.0"))
        reg.register(ModelArtifact(name="b", version="1.0.0"))
        assert sorted(reg.list_models()) == ["a", "b"]

    def test_persistence(self, tmp_path: Path) -> None:
        path = tmp_path / "models.json"
        reg = ModelRegistry(persist_path=path)
        reg.register(ModelArtifact(name="x", version="1.0.0"))
        reg2 = ModelRegistry(persist_path=path)
        assert reg2.get("x", "1.0.0") is not None

    def test_promote_not_found_raises(self) -> None:
        reg = ModelRegistry()
        with pytest.raises(ValueError, match="not found"):
            reg.promote("nope", "1.0.0", ModelStage.PRODUCTION)


# ============================================================================
# Drift Detection
# ============================================================================


class TestDriftDetector:
    def test_no_drift(self) -> None:
        ref = [float(i) for i in range(100)]
        cur = [float(i) for i in range(100)]
        detector = DriftDetector(psi_threshold=0.20)
        report = detector.check_feature("val", ref, cur)
        assert report.drift_detected is False
        assert report.severity == "none"

    def test_drift_detected(self) -> None:
        ref = [float(i) for i in range(100)]
        cur = [float(i + 50) for i in range(100)]  # shifted
        detector = DriftDetector(psi_threshold=0.10)
        report = detector.check_feature("val", ref, cur)
        assert report.psi > 0

    def test_empty_distributions(self) -> None:
        detector = DriftDetector()
        report = detector.check_feature("empty", [], [])
        assert report.drift_detected is False

    def test_check_dataset(self) -> None:
        ref = {"a": [1.0, 2.0, 3.0], "b": [4.0, 5.0, 6.0]}
        cur = {"a": [1.0, 2.0, 3.0], "b": [4.0, 5.0, 6.0]}
        detector = DriftDetector()
        reports = detector.check_dataset(ref, cur)
        assert len(reports) == 2

    def test_to_dict(self) -> None:
        report = DriftReport(feature_name="x", psi=0.05, drift_detected=False, severity="none")
        d = report.to_dict()
        assert d["feature_name"] == "x"


# ============================================================================
# Model Serving
# ============================================================================


class TestModelServer:
    class FakeModel:
        def predict(self, X: Any) -> list[int]:
            return [1] * len(X)

    def test_load_and_predict(self) -> None:
        server = ModelServer()
        server.load_model("test", "1.0.0", self.FakeModel())
        req = PredictionRequest(
            model_name="test",
            version="1.0.0",
            features=[{"a": 1}, {"a": 2}],
        )
        resp = server.predict(req)
        assert resp.predictions == [1, 1]
        assert resp.latency_ms > 0

    def test_predict_not_loaded_raises(self) -> None:
        server = ModelServer()
        req = PredictionRequest(model_name="nope", version="1.0.0", features=[{"a": 1}])
        with pytest.raises(RuntimeError, match="not loaded"):
            server.predict(req)

    def test_list_loaded(self) -> None:
        server = ModelServer()
        server.load_model("m1", "1.0.0", self.FakeModel())
        assert "m1:1.0.0" in server.list_loaded()
