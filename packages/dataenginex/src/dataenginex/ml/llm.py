"""LLM Integration — Ollama, OpenAI-Compatible & Provider Abstraction (Issue #95).

Provides a pluggable LLM abstraction with concrete adapters:

- **OllamaProvider** — local Ollama server (Llama 3, Mistral, etc.)
- **OpenAICompatibleProvider** — any OpenAI-compatible API (OpenAI, Groq, Together, etc.)
- **MockProvider** — deterministic stub for testing
- **get_llm_provider()** — factory function to instantiate providers by name

All providers implement :class:`LLMProvider` so they can be swapped
transparently in RAG pipelines and agents.

Example::

    from dataenginex.ml.llm import get_llm_provider

    llm = get_llm_provider("ollama", model="llama3.1:8b")
    response = llm.generate("Explain data lineage in 3 sentences.")
    print(response.text)
"""

from __future__ import annotations

import abc
import time
from dataclasses import dataclass, field
from typing import Any

from loguru import logger
from prometheus_client import Counter, Histogram

__all__ = [
    "ChatMessage",
    "LLMConfig",
    "LLMProvider",
    "LLMResponse",
    "MockProvider",
    "OllamaProvider",
    "OpenAICompatibleProvider",
    "get_llm_provider",
]

# ======================================================================
# Prometheus metrics
# ======================================================================

llm_request_latency_seconds = Histogram(
    "llm_request_latency_seconds",
    "Latency of LLM generate/chat calls in seconds",
    labelnames=["provider", "model", "method"],
)

llm_tokens_total = Counter(
    "llm_tokens_total",
    "Total tokens processed by LLM providers",
    labelnames=["provider", "model", "direction"],
)


# ======================================================================
# Data models
# ======================================================================


@dataclass
class ChatMessage:
    """Single chat message."""

    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class LLMConfig:
    """Configuration for an LLM provider."""

    model: str = "llama3.1:8b"
    temperature: float = 0.7
    max_tokens: int = 2048
    top_p: float = 0.9
    system_prompt: str = "You are a helpful data engineering assistant."
    timeout_seconds: int = 120


@dataclass
class LLMResponse:
    """Response from an LLM generation call."""

    text: str
    model: str = ""
    finish_reason: str = "stop"
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


# ======================================================================
# Abstract provider
# ======================================================================


class LLMProvider(abc.ABC):
    """Abstract LLM provider interface."""

    def __init__(self, config: LLMConfig | None = None) -> None:
        self.config = config or LLMConfig()

    @abc.abstractmethod
    def generate(self, prompt: str) -> LLMResponse:
        """Generate text from a single prompt string."""

    @abc.abstractmethod
    def chat(self, messages: list[ChatMessage]) -> LLMResponse:
        """Generate a response from a chat conversation."""

    @abc.abstractmethod
    def is_available(self) -> bool:
        """Check whether the provider is reachable."""

    def generate_with_context(
        self,
        question: str,
        context: str,
        system_prompt: str | None = None,
    ) -> LLMResponse:
        """RAG-style generation: inject *context* before the *question*.

        Args:
            question: User question.
            context: Retrieved context documents.
            system_prompt: Optional override for the system prompt.

        Returns:
            LLM response with augmented generation.
        """
        sys_msg = system_prompt or self.config.system_prompt
        augmented_prompt = (
            f"Use the following context to answer the question.\n\n"
            f"Context:\n{context}\n\n"
            f"Question: {question}\n\n"
            f"Answer:"
        )
        messages = [
            ChatMessage(role="system", content=sys_msg),
            ChatMessage(role="user", content=augmented_prompt),
        ]
        return self.chat(messages)


# ======================================================================
# Ollama provider
# ======================================================================


class OllamaProvider(LLMProvider):
    """Ollama local LLM provider.

    Talks to a local Ollama server via its REST API.

    Args:
        model: Ollama model name (e.g. ``llama3.1:8b``).
        base_url: Ollama server URL.
        config: LLM configuration overrides.
    """

    def __init__(
        self,
        model: str = "llama3.1:8b",
        base_url: str = "http://localhost:11434",
        config: LLMConfig | None = None,
    ) -> None:
        cfg = config or LLMConfig(model=model)
        super().__init__(cfg)
        self.base_url = base_url.rstrip("/")
        self._api_generate = f"{self.base_url}/api/generate"
        self._api_chat = f"{self.base_url}/api/chat"
        self._api_tags = f"{self.base_url}/api/tags"
        logger.info("OllamaProvider model={} url={}", cfg.model, self.base_url)

    def generate(self, prompt: str) -> LLMResponse:
        """Generate text via Ollama ``/api/generate``."""
        try:
            import httpx
        except ImportError as exc:
            msg = "httpx is required for OllamaProvider — install with: uv add httpx"
            raise ImportError(msg) from exc

        payload = {
            "model": self.config.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens,
                "top_p": self.config.top_p,
            },
        }

        start = time.monotonic()
        try:
            resp = httpx.post(
                self._api_generate,
                json=payload,
                timeout=self.config.timeout_seconds,
            )
            resp.raise_for_status()
            data = resp.json()

            result = LLMResponse(
                text=data.get("response", ""),
                model=data.get("model", self.config.model),
                finish_reason="stop" if data.get("done") else "length",
                prompt_tokens=data.get("prompt_eval_count", 0),
                completion_tokens=data.get("eval_count", 0),
                total_tokens=(data.get("prompt_eval_count", 0) + data.get("eval_count", 0)),
                metadata={
                    "total_duration_ns": data.get("total_duration", 0),
                    "load_duration_ns": data.get("load_duration", 0),
                },
            )

            elapsed = time.monotonic() - start
            labels = {"provider": "ollama", "model": self.config.model}
            llm_request_latency_seconds.labels(method="generate", **labels).observe(elapsed)
            llm_tokens_total.labels(direction="input", **labels).inc(result.prompt_tokens)
            llm_tokens_total.labels(direction="output", **labels).inc(result.completion_tokens)

            return result
        except httpx.ConnectError as exc:
            logger.error("Ollama server not reachable at {}", self.base_url)
            msg = f"Ollama server not reachable at {self.base_url}"
            raise ConnectionError(msg) from exc
        except httpx.HTTPStatusError as exc:
            logger.error("Ollama HTTP error status={}", exc.response.status_code)
            msg = f"Ollama returned HTTP {exc.response.status_code}"
            raise ConnectionError(msg) from exc

    def chat(self, messages: list[ChatMessage]) -> LLMResponse:
        """Generate via Ollama ``/api/chat``."""
        try:
            import httpx
        except ImportError as exc:
            msg = "httpx is required for OllamaProvider — install with: uv add httpx"
            raise ImportError(msg) from exc

        payload = {
            "model": self.config.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
            "options": {
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens,
                "top_p": self.config.top_p,
            },
        }

        start = time.monotonic()
        try:
            resp = httpx.post(
                self._api_chat,
                json=payload,
                timeout=self.config.timeout_seconds,
            )
            resp.raise_for_status()
            data = resp.json()

            msg = data.get("message", {})
            result = LLMResponse(
                text=msg.get("content", ""),
                model=data.get("model", self.config.model),
                finish_reason="stop" if data.get("done") else "length",
                prompt_tokens=data.get("prompt_eval_count", 0),
                completion_tokens=data.get("eval_count", 0),
                total_tokens=(data.get("prompt_eval_count", 0) + data.get("eval_count", 0)),
            )

            elapsed = time.monotonic() - start
            labels = {"provider": "ollama", "model": self.config.model}
            llm_request_latency_seconds.labels(method="chat", **labels).observe(elapsed)
            llm_tokens_total.labels(direction="input", **labels).inc(result.prompt_tokens)
            llm_tokens_total.labels(direction="output", **labels).inc(result.completion_tokens)

            return result
        except httpx.ConnectError as exc:
            logger.error("Ollama server not reachable at {}", self.base_url)
            msg = f"Ollama server not reachable at {self.base_url}"
            raise ConnectionError(msg) from exc
        except httpx.HTTPStatusError as exc:
            logger.error("Ollama HTTP error status={}", exc.response.status_code)
            msg = f"Ollama returned HTTP {exc.response.status_code}"
            raise ConnectionError(msg) from exc

    def is_available(self) -> bool:
        """Check if Ollama server is running and the model is loaded."""
        try:
            import httpx

            resp = httpx.get(self._api_tags, timeout=5)
            if resp.status_code != 200:
                return False
            models = resp.json().get("models", [])
            available = [m.get("name", "") for m in models]
            return any(self.config.model in name for name in available)
        except (ImportError, httpx.ConnectError, httpx.TimeoutException):
            return False

    def list_models(self) -> list[str]:
        """List models available on the Ollama server."""
        try:
            import httpx

            resp = httpx.get(self._api_tags, timeout=5)
            resp.raise_for_status()
            models = resp.json().get("models", [])
            return [m.get("name", "") for m in models]
        except (ImportError, httpx.ConnectError, httpx.TimeoutException):
            logger.warning("Could not list Ollama models")
            return []
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "Ollama returned HTTP %d while listing models",
                exc.response.status_code,
            )
            return []


# ======================================================================
# Mock provider (for tests)
# ======================================================================


class MockProvider(LLMProvider):
    """Deterministic mock LLM provider for testing.

    Returns canned responses that include the prompt in the output
    for assertion convenience.
    """

    def __init__(
        self,
        config: LLMConfig | None = None,
        default_response: str = "This is a mock LLM response.",
    ) -> None:
        super().__init__(config or LLMConfig(model="mock-model"))
        self.default_response = default_response
        self.call_history: list[dict[str, Any]] = []

    def generate(self, prompt: str) -> LLMResponse:
        self.call_history.append({"type": "generate", "prompt": prompt})
        return LLMResponse(
            text=f"{self.default_response} (prompt_length={len(prompt)})",
            model=self.config.model,
            prompt_tokens=len(prompt.split()),
            completion_tokens=10,
            total_tokens=len(prompt.split()) + 10,
        )

    def chat(self, messages: list[ChatMessage]) -> LLMResponse:
        self.call_history.append({"type": "chat", "messages": len(messages)})
        return LLMResponse(
            text=f"{self.default_response} (messages={len(messages)})",
            model=self.config.model,
            prompt_tokens=sum(len(m.content.split()) for m in messages),
            completion_tokens=10,
            total_tokens=sum(len(m.content.split()) for m in messages) + 10,
        )

    def is_available(self) -> bool:
        return True


# ======================================================================
# OpenAI-compatible provider
# ======================================================================


class OpenAICompatibleProvider(LLMProvider):
    """OpenAI-compatible API provider (supports OpenAI, Groq, Together, etc.).

    Uses the ``/v1/chat/completions`` endpoint with httpx.

    Args:
        api_key: API key for authentication. Never logged.
        base_url: API base URL (default: OpenAI).
        model: Model name.
        config: LLM configuration overrides.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com",
        model: str = "gpt-4o-mini",
        config: LLMConfig | None = None,
    ) -> None:
        cfg = config or LLMConfig(model=model)
        super().__init__(cfg)
        self._api_key = api_key
        self.base_url = base_url.rstrip("/")
        self._chat_url = f"{self.base_url}/v1/chat/completions"
        # Never log the API key
        logger.info(
            "OpenAICompatibleProvider model={} url={}",
            cfg.model,
            self.base_url,
        )

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def generate(self, prompt: str) -> LLMResponse:
        """Generate text via a single-turn chat completion."""
        messages = [
            ChatMessage(role="system", content=self.config.system_prompt),
            ChatMessage(role="user", content=prompt),
        ]
        return self.chat(messages)

    def chat(self, messages: list[ChatMessage]) -> LLMResponse:
        """Generate a response via ``/v1/chat/completions``."""
        try:
            import httpx
        except ImportError as exc:
            msg = "httpx is required for OpenAICompatibleProvider — install with: uv add httpx"
            raise ImportError(msg) from exc

        payload = {
            "model": self.config.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "top_p": self.config.top_p,
        }

        start = time.monotonic()
        try:
            resp = httpx.post(
                self._chat_url,
                json=payload,
                headers=self._headers(),
                timeout=self.config.timeout_seconds,
            )
            resp.raise_for_status()
            data = resp.json()

            choice = data.get("choices", [{}])[0]
            usage = data.get("usage", {})

            result = LLMResponse(
                text=choice.get("message", {}).get("content", ""),
                model=data.get("model", self.config.model),
                finish_reason=choice.get("finish_reason", "stop"),
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                total_tokens=usage.get("total_tokens", 0),
            )

            elapsed = time.monotonic() - start
            labels = {"provider": "openai_compatible", "model": self.config.model}
            llm_request_latency_seconds.labels(method="chat", **labels).observe(elapsed)
            llm_tokens_total.labels(direction="input", **labels).inc(result.prompt_tokens)
            llm_tokens_total.labels(direction="output", **labels).inc(result.completion_tokens)

            return result
        except httpx.ConnectError as exc:
            logger.error("OpenAI-compatible server not reachable at {}", self.base_url)
            msg = f"OpenAI-compatible server not reachable at {self.base_url}"
            raise ConnectionError(msg) from exc
        except httpx.HTTPStatusError as exc:
            logger.error(
                "OpenAI-compatible HTTP error status={}",
                exc.response.status_code,
            )
            msg = f"OpenAI-compatible API returned HTTP {exc.response.status_code}"
            raise ConnectionError(msg) from exc

    def is_available(self) -> bool:
        """Check if the API is reachable (HEAD request to base URL)."""
        try:
            import httpx

            resp = httpx.get(
                f"{self.base_url}/v1/models",
                headers=self._headers(),
                timeout=5,
            )
            return resp.status_code == 200
        except (ImportError, httpx.ConnectError, httpx.TimeoutException):
            return False


# ======================================================================
# Factory function
# ======================================================================


def get_llm_provider(provider: str, **kwargs: Any) -> LLMProvider:
    """Create an LLM provider by name.

    Args:
        provider: One of ``"ollama"``, ``"openai"``, ``"mock"``.
        **kwargs: Passed directly to the provider constructor.

    Returns:
        LLMProvider instance.

    Raises:
        ValueError: If the provider name is unknown.

    Example::

        llm = get_llm_provider("ollama", model="llama3.1:8b")
        llm = get_llm_provider("openai", api_key="sk-...", model="gpt-4o")
        llm = get_llm_provider("mock")
    """
    providers: dict[str, type[LLMProvider]] = {
        "ollama": OllamaProvider,
        "openai": OpenAICompatibleProvider,
        "mock": MockProvider,
    }
    cls = providers.get(provider.lower())
    if cls is None:
        valid = ", ".join(sorted(providers.keys()))
        msg = f"Unknown LLM provider '{provider}'. Valid: {valid}"
        raise ValueError(msg)
    return cls(**kwargs)
