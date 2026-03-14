#!/usr/bin/env python
"""04_ml_training.py — Train and register a scikit-learn model.

Demonstrates:
- ``SklearnTrainer`` for model training
- ``ModelRegistry`` for versioned model storage
- ``DriftDetector`` for distribution drift detection
- Model stage promotion (development → staging → production)

Run:
    uv run python examples/04_ml_training.py
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from dataenginex.ml.registry import ModelArtifact
from dataenginex.ml.training import TrainingResult

from dataenginex.ml import (
    DriftDetector,
    ModelRegistry,
    ModelStage,
    SklearnTrainer,
)


def main() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        artifact_dir = Path(tmpdir) / "models"
        artifact_dir.mkdir()
        registry_dir = Path(tmpdir) / "registry"
        registry_dir.mkdir()

        # ----- 1. Generate toy tabular data (e.g. customer churn) ---------
        import random

        random.seed(42)
        n = 200
        # Features: tenure, monthly_spend, support_tickets, login_frequency
        X_train = [[random.gauss(0, 1) for _ in range(4)] for _ in range(n)]
        y_train = [1 if sum(row) > 0 else 0 for row in X_train]  # churn label
        X_test = [[random.gauss(0, 1) for _ in range(4)] for _ in range(50)]
        y_test = [1 if sum(row) > 0 else 0 for row in X_test]

        print(f"Training set: {len(X_train)} samples (4 features)")
        print(f"Test set:     {len(X_test)} samples\n")

        # ----- 2. Train with SklearnTrainer --------------------------------
        from sklearn.ensemble import RandomForestClassifier  # type: ignore[import-untyped]

        trainer = SklearnTrainer(
            model_name="demo_classifier",
            version="1.0.0",
            estimator=RandomForestClassifier(n_estimators=50, max_depth=3, random_state=42),
        )
        result = trainer.train(X_train=X_train, y_train=y_train)
        eval_metrics = trainer.evaluate(X_test, y_test)
        result.metrics.update(eval_metrics)

        # Save model artifact
        artifact_path = str(artifact_dir / "demo_classifier")
        saved_path = trainer.save(artifact_path)
        result = TrainingResult(
            model_name=result.model_name,
            version=result.version,
            metrics=result.metrics,
            parameters=result.parameters,
            duration_seconds=result.duration_seconds,
            artifact_path=saved_path,
        )

        print("Training result:")
        print(f"  Model: {result.model_name} v{result.version}")
        print(f"  Duration: {result.duration_seconds:.2f}s")
        print(f"  Metrics: {result.metrics}")
        print(f"  Artifact: {result.artifact_path}\n")

        # ----- 3. Register in ModelRegistry --------------------------------
        registry = ModelRegistry(persist_path=str(registry_dir / "registry.json"))
        artifact = registry.register(
            ModelArtifact(
                name=result.model_name,
                version=result.version,
                artifact_path=result.artifact_path or "",
                metrics=result.metrics,
                parameters=result.parameters,
                description="Demo binary classifier",
            )
        )
        print(f"Registered: {artifact.name} v{artifact.version} [{artifact.stage.value}]")

        # ----- 4. Promote through stages -----------------------------------
        registry.promote(result.model_name, result.version, ModelStage.STAGING)
        print("Promoted to: staging")

        registry.promote(result.model_name, result.version, ModelStage.PRODUCTION)
        print("Promoted to: production")

        prod = registry.get_production(result.model_name)
        if prod:
            print(f"Production model: {prod.name} v{prod.version}\n")

        # ----- 5. Drift detection ------------------------------------------
        detector = DriftDetector()
        feature_names = ["tenure", "monthly_spend", "support_tickets", "login_freq"]
        ref_rows = [[random.gauss(0, 1) for _ in range(4)] for _ in range(100)]
        cur_rows = [[random.gauss(0.5, 1.2) for _ in range(4)] for _ in range(100)]

        # Transpose rows to feature-keyed dicts
        ref_data = {f: [row[i] for row in ref_rows] for i, f in enumerate(feature_names)}
        cur_data = {f: [row[i] for row in cur_rows] for i, f in enumerate(feature_names)}

        reports = detector.check_dataset(reference=ref_data, current=cur_data)
        print("Drift detection:")
        any_drift = any(r.drift_detected for r in reports)
        print(f"  Drift detected: {any_drift}")
        for r in reports:
            print(f"    {r.feature_name}: psi={r.psi:.4f} drifted={r.drift_detected}")

    print("\nDone! ✓")


if __name__ == "__main__":
    main()
