"""Integration tests: config loading + CLI validate end-to-end."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from click.testing import CliRunner

from dataenginex.cli.main import dex
from dataenginex.config.loader import load_config, validate_config

EXAMPLES_DIR = Path(__file__).resolve().parents[2] / "examples"


class TestExampleDexYaml:
    """The shipped examples/dex.yaml must load and validate cleanly."""

    def test_load_example_config(self) -> None:
        cfg = load_config(EXAMPLES_DIR / "dex.yaml")
        assert cfg.project.name == "demo-project"

    def test_cross_reference_validation_passes(self) -> None:
        cfg = load_config(EXAMPLES_DIR / "dex.yaml")
        errors = validate_config(cfg)
        assert errors == []

    def test_sources_populated(self) -> None:
        cfg = load_config(EXAMPLES_DIR / "dex.yaml")
        assert "raw_users" in cfg.data.sources
        assert "raw_events" in cfg.data.sources

    def test_pipelines_populated(self) -> None:
        cfg = load_config(EXAMPLES_DIR / "dex.yaml")
        assert "clean_users" in cfg.data.pipelines
        assert "user_events" in cfg.data.pipelines

    def test_ml_experiment_populated(self) -> None:
        cfg = load_config(EXAMPLES_DIR / "dex.yaml")
        assert "churn_model" in cfg.ml.experiments

    def test_ai_agent_populated(self) -> None:
        cfg = load_config(EXAMPLES_DIR / "dex.yaml")
        assert "assistant" in cfg.ai.agents


class TestCliValidate:
    """CLI ``dex validate`` command integration tests."""

    def test_validate_example_config(self) -> None:
        runner = CliRunner()
        result = runner.invoke(dex, ["validate", str(EXAMPLES_DIR / "dex.yaml")])
        assert result.exit_code == 0
        assert "Config is valid" in result.output

    def test_validate_missing_file(self) -> None:
        runner = CliRunner()
        result = runner.invoke(dex, ["validate", "/nonexistent/dex.yaml"])
        assert result.exit_code != 0

    def test_validate_invalid_yaml(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.yaml"
        bad.write_text(": : : invalid {{{")
        runner = CliRunner()
        result = runner.invoke(dex, ["validate", str(bad)])
        assert result.exit_code != 0

    def test_validate_with_overlay(self, tmp_path: Path) -> None:
        base = dedent("""\
            project:
              name: overlay-test
            server:
              port: 17000
        """)
        overlay = dedent("""\
            server:
              port: 9999
        """)
        (tmp_path / "dex.yaml").write_text(base)
        (tmp_path / "dex.prod.yaml").write_text(overlay)

        runner = CliRunner()
        result = runner.invoke(
            dex,
            [
                "validate",
                str(tmp_path / "dex.yaml"),
                "--overlay",
                str(tmp_path / "dex.prod.yaml"),
            ],
        )
        assert result.exit_code == 0
        assert "overlay-test" in result.output


class TestCliVersion:
    def test_version_output(self) -> None:
        runner = CliRunner()
        result = runner.invoke(dex, ["version"])
        assert result.exit_code == 0
        assert "DataEngineX" in result.output

    def test_version_flag(self) -> None:
        runner = CliRunner()
        result = runner.invoke(dex, ["--version"])
        assert result.exit_code == 0
