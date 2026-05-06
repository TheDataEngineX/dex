"""Extended tests for the pipeline router — /api/v1/pipelines.

Covers run success/failure, 404 on run, pipeline with transforms
and quality gate, empty pipeline list, and response schema.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from dataenginex.api.routers.pipelines import router
from dataenginex.api.schemas import PipelineResultResponse
from dataenginex.config.schema import (
    DataConfig,
    DexConfig,
    PipelineConfig,
    ProjectConfig,
    QualityCheckConfig,
    SourceConfig,
    TransformStepConfig,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_app(
    pipelines: dict[str, PipelineConfig] | None = None,
    runner_result: MagicMock | None = None,
) -> FastAPI:
    if pipelines is None:
        pipelines = {}

    config = DexConfig(
        project=ProjectConfig(name="test-pipelines"),
        data=DataConfig(
            sources={"src": SourceConfig(type="csv", path="data.csv")},
            pipelines=pipelines,
        ),
    )
    app = FastAPI()
    app.state.config = config

    mock_runner = MagicMock()
    if runner_result is not None:
        mock_runner.run.return_value = runner_result
    else:
        default = MagicMock()
        default.success = True
        default.rows_input = 100
        default.rows_output = 95
        default.steps_completed = 3
        default.error = None
        mock_runner.run.return_value = default

    app.state.pipeline_runner = mock_runner
    app.include_router(router, prefix="/api/v1")
    return app


@pytest.fixture()
def empty_app() -> FastAPI:
    return _make_app()


@pytest.fixture()
def app_with_pipelines() -> FastAPI:
    return _make_app(
        pipelines={
            "ingest": PipelineConfig(source="src"),
            "transform": PipelineConfig(
                source="src",
                transforms=[
                    TransformStepConfig(type="filter", condition="age > 18"),
                    TransformStepConfig(type="deduplicate", key="id"),
                ],
            ),
            "quality-checked": PipelineConfig(
                source="src",
                quality=QualityCheckConfig(completeness=0.95),
            ),
        }
    )


# ---------------------------------------------------------------------------
# List pipelines
# ---------------------------------------------------------------------------


class TestListPipelines:
    def test_empty_pipeline_list(self, empty_app: FastAPI) -> None:
        client = TestClient(empty_app)
        resp = client.get("/api/v1/pipelines/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["pipelines"] == []
        assert data["count"] == 0

    def test_returns_all_pipeline_names(self, app_with_pipelines: FastAPI) -> None:
        client = TestClient(app_with_pipelines)
        resp = client.get("/api/v1/pipelines/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 3
        assert "ingest" in data["pipelines"]
        assert "transform" in data["pipelines"]
        assert "quality-checked" in data["pipelines"]

    def test_response_has_count_field(self, app_with_pipelines: FastAPI) -> None:
        client = TestClient(app_with_pipelines)
        resp = client.get("/api/v1/pipelines/")
        assert "count" in resp.json()


# ---------------------------------------------------------------------------
# Get pipeline
# ---------------------------------------------------------------------------


class TestGetPipeline:
    def test_get_returns_source(self, app_with_pipelines: FastAPI) -> None:
        client = TestClient(app_with_pipelines)
        resp = client.get("/api/v1/pipelines/ingest")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "ingest"
        assert data["source"] == "src"

    def test_get_returns_transform_count(self, app_with_pipelines: FastAPI) -> None:
        client = TestClient(app_with_pipelines)
        resp = client.get("/api/v1/pipelines/transform")
        data = resp.json()
        assert data["transforms"] == 2

    def test_get_has_quality_gate_true(self, app_with_pipelines: FastAPI) -> None:
        client = TestClient(app_with_pipelines)
        resp = client.get("/api/v1/pipelines/quality-checked")
        data = resp.json()
        assert data["has_quality_gate"] is True

    def test_get_has_quality_gate_false(self, app_with_pipelines: FastAPI) -> None:
        client = TestClient(app_with_pipelines)
        resp = client.get("/api/v1/pipelines/ingest")
        data = resp.json()
        assert data["has_quality_gate"] is False

    def test_get_nonexistent_returns_404(self, app_with_pipelines: FastAPI) -> None:
        client = TestClient(app_with_pipelines)
        resp = client.get("/api/v1/pipelines/does-not-exist")
        assert resp.status_code == 404
        assert "does-not-exist" in resp.json()["detail"]

    def test_get_empty_app_returns_404(self, empty_app: FastAPI) -> None:
        client = TestClient(empty_app)
        resp = client.get("/api/v1/pipelines/any")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Run pipeline
# ---------------------------------------------------------------------------


class TestRunPipeline:
    def test_run_success_returns_200(self, app_with_pipelines: FastAPI) -> None:
        client = TestClient(app_with_pipelines)
        resp = client.post("/api/v1/pipelines/ingest/run")
        assert resp.status_code == 200

    def test_run_success_response_shape(self, app_with_pipelines: FastAPI) -> None:
        client = TestClient(app_with_pipelines)
        resp = client.post("/api/v1/pipelines/ingest/run")
        data = resp.json()
        assert data["pipeline"] == "ingest"
        result = data.get("result") or data  # async: result nested; sync: top-level
        assert result["success"] is True
        assert result["rows_input"] == 100
        assert result["rows_output"] == 95
        assert result["steps_completed"] == 3
        assert result["error"] is None
        assert "duration_ms" in result

    def test_run_failure_returns_200_with_error(self) -> None:
        failed = MagicMock()
        failed.success = False
        failed.rows_input = 50
        failed.rows_output = 0
        failed.steps_completed = 1
        failed.error = "Source file not found"
        app = _make_app(
            pipelines={"broken": PipelineConfig(source="src")},
            runner_result=failed,
        )
        client = TestClient(app)
        resp = client.post("/api/v1/pipelines/broken/run")
        assert resp.status_code == 200
        data = resp.json()
        result = data.get("result") or data
        assert result["success"] is False
        assert result["error"] == "Source file not found"

    def test_run_nonexistent_returns_404(self, app_with_pipelines: FastAPI) -> None:
        client = TestClient(app_with_pipelines)
        resp = client.post("/api/v1/pipelines/missing-pipeline/run")
        assert resp.status_code == 404
        assert "missing-pipeline" in resp.json()["detail"]

    def test_run_records_duration(self, app_with_pipelines: FastAPI) -> None:
        client = TestClient(app_with_pipelines)
        resp = client.post("/api/v1/pipelines/ingest/run")
        data = resp.json()
        result = data.get("result") or data
        assert isinstance(result["duration_ms"], float)
        assert result["duration_ms"] >= 0.0

    def test_run_with_zero_rows(self) -> None:
        empty_result = MagicMock()
        empty_result.success = True
        empty_result.rows_input = 0
        empty_result.rows_output = 0
        empty_result.steps_completed = 0
        empty_result.error = None
        app = _make_app(
            pipelines={"empty-src": PipelineConfig(source="src")},
            runner_result=empty_result,
        )
        client = TestClient(app)
        resp = client.post("/api/v1/pipelines/empty-src/run")
        assert resp.status_code == 200
        data = resp.json()
        result = data.get("result") or data
        assert result["rows_input"] == 0

    def test_run_response_matches_schema(self, app_with_pipelines: FastAPI) -> None:
        """Validate sync fallback response result against PipelineResultResponse schema."""
        client = TestClient(app_with_pipelines)
        resp = client.post("/api/v1/pipelines/ingest/run")
        data = resp.json()
        result = data.get("result") or data
        PipelineResultResponse(**result)

    def test_run_calls_runner_with_pipeline_name(self, app_with_pipelines: FastAPI) -> None:
        client = TestClient(app_with_pipelines)
        client.post("/api/v1/pipelines/transform/run")
        runner = app_with_pipelines.state.pipeline_runner
        runner.run.assert_called_once_with("transform")
