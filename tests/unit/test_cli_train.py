"""Tests for the ``dex train`` CLI command."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from dataenginex.cli.main import dex


@pytest.fixture()
def train_config(tmp_path: Path) -> Path:
    config = tmp_path / "dex.yaml"
    config.write_text("""
project:
  name: test-train
ml:
  tracking:
    backend: builtin
  experiments:
    test_model:
      model_type: sklearn
      target: label
      features: [x1, x2]
      params:
        n_estimators: 10
""")
    return config


class TestDexTrain:
    def test_train_single_experiment(self, train_config: Path, tmp_path: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(
            dex,
            [
                "train",
                "test_model",
                "--config",
                str(train_config),
                "--model-dir",
                str(tmp_path / "models"),
            ],
        )
        assert result.exit_code == 0
        assert "test_model" in result.output

    def test_train_all(self, train_config: Path, tmp_path: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(
            dex,
            [
                "train",
                "--all",
                "--config",
                str(train_config),
                "--model-dir",
                str(tmp_path / "models"),
            ],
        )
        assert result.exit_code == 0
        assert "test_model" in result.output

    def test_train_no_experiment_shows_help(
        self,
        train_config: Path,
    ) -> None:
        runner = CliRunner()
        result = runner.invoke(
            dex,
            [
                "train",
                "--config",
                str(train_config),
            ],
        )
        assert result.exit_code == 0
        assert "Available" in result.output

    def test_train_nonexistent_experiment(
        self,
        train_config: Path,
    ) -> None:
        runner = CliRunner()
        result = runner.invoke(
            dex,
            [
                "train",
                "nonexistent",
                "--config",
                str(train_config),
            ],
        )
        assert result.exit_code != 0
