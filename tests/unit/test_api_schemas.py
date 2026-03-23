from __future__ import annotations

from dataenginex.api.schemas import (
    AgentChatRequest,
    AgentChatResponse,
    PipelineResultResponse,
    PredictionRequest,
    PromoteRequest,
    ServiceUnavailableResponse,
)


class TestSchemaValidation:
    def test_pipeline_result_response(self) -> None:
        resp = PipelineResultResponse(
            pipeline="ingest",
            success=True,
            rows_input=100,
            rows_output=95,
            steps_completed=3,
            duration_ms=1200.5,
        )
        assert resp.pipeline == "ingest"
        assert resp.success is True

    def test_service_unavailable_response(self) -> None:
        resp = ServiceUnavailableResponse(
            error="service_unavailable",
            component="llm",
            message="LLM provider not running",
        )
        assert resp.component == "llm"

    def test_agent_chat_request(self) -> None:
        req = AgentChatRequest(message="Hello")
        assert req.message == "Hello"

    def test_agent_chat_response(self) -> None:
        resp = AgentChatResponse(
            agent="data-analyst",
            response="The answer is 42",
            iterations=2,
            tool_calls=1,
        )
        assert resp.iterations == 2

    def test_prediction_request(self) -> None:
        req = PredictionRequest(model_name="my-model", features={"x": 1.0})
        assert req.model_name == "my-model"

    def test_promote_request(self) -> None:
        req = PromoteRequest(stage="production")
        assert req.stage == "production"
