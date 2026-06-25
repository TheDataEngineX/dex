# dataenginex.ai

LLM routing, agent runtimes, vector stores, memory, retrieval, observability, and workflow orchestration.

## Quick import

```python
from dataenginex.ai import (
    ModelRouter, BaseProvider,
    LLMProvider, LLMResponse,
    BuiltinAgentRuntime,
    BuiltinRetriever,
    VectorStore,
    SandboxConfig,
)
```

______________________________________________________________________

## LLM Interface

`dataenginex.ai.llm`

Unified LLM request/response interface across providers. Handles streaming, tool calls, retries, and token counting.

::: dataenginex.ai.llm

**Key classes:** `LLMProvider`, `LLMResponse`, `LLMMessage`, `ToolCall`

```python
from dataenginex.ai.llm import LLMMessage

response = provider.complete([
    LLMMessage(role="user", content="Summarize this dataset."),
])
print(response.content)
```

______________________________________________________________________

## Model Router

`dataenginex.ai.routing.router`

Routes LLM requests to the appropriate provider based on cost, latency, capability, and fallback rules.

::: dataenginex.ai.routing.router

**Key class:** `ModelRouter`

```python
from dataenginex.ai.routing.router import ModelRouter

router = ModelRouter.from_config(engine.config)
response = router.complete("Explain this error.", model_hint="fast")
```

### Providers

`dataenginex.ai.routing.anthropic` · `dataenginex.ai.routing.openai` · `dataenginex.ai.routing.ollama` · `dataenginex.ai.routing.guarded`

::: dataenginex.ai.routing.anthropic
::: dataenginex.ai.routing.openai
::: dataenginex.ai.routing.ollama
::: dataenginex.ai.routing.guarded

______________________________________________________________________

## Agents

`dataenginex.ai.agents.builtin`

Built-in agent runtime — tool-use loop, memory injection, step tracing, and structured output parsing.

::: dataenginex.ai.agents.builtin

**Key class:** `BuiltinAgentRuntime`

```python
from dataenginex.ai.agents.builtin import BuiltinAgentRuntime

agent = BuiltinAgentRuntime(router=router, tools=[search_tool, sql_tool])
result = agent.run("Find the top 10 customers by revenue last quarter.")
print(result.output)
```

______________________________________________________________________

## Vector Store

`dataenginex.ai.vectorstore`

Embedding storage and similarity search. Defaults to in-process DuckDB VSS; swap for Qdrant via `dataenginex[qdrant]`.

::: dataenginex.ai.vectorstore

**Key class:** `VectorStore`

```python
from dataenginex.ai.vectorstore import VectorStore

store = VectorStore(db_path=".dex/store.duckdb")
store.upsert("doc-1", embedding=[0.1, 0.2, ...], metadata={"source": "wiki"})
results = store.search(query_embedding, top_k=5)
```

______________________________________________________________________

## Memory

`dataenginex.ai.memory.base` — abstract memory interface

::: dataenginex.ai.memory.base

`dataenginex.ai.memory.episodic` — short-term conversation memory scoped to a single agent session

::: dataenginex.ai.memory.episodic

`dataenginex.ai.memory.long_term` — persistent memory backed by the vector store, survives across sessions

::: dataenginex.ai.memory.long_term

______________________________________________________________________

## Retrieval

`dataenginex.ai.retrieval.builtin` — RAG retriever: embeds query, searches vector store, returns ranked chunks

::: dataenginex.ai.retrieval.builtin

`dataenginex.ai.retrieval.graph` — graph-based retrieval for structured knowledge graphs

::: dataenginex.ai.retrieval.graph

______________________________________________________________________

## Runtime

`dataenginex.ai.runtime.executor` — async execution engine with concurrency, timeout, and step-level error handling

::: dataenginex.ai.runtime.executor

`dataenginex.ai.runtime.checkpoint` — saves and restores agent run state for long-running or resumable workflows

::: dataenginex.ai.runtime.checkpoint

`dataenginex.ai.runtime.sandbox` — isolated code execution sandbox for agent-generated Python with configurable resource limits

::: dataenginex.ai.runtime.sandbox

______________________________________________________________________

## Tools

`dataenginex.ai.tools.builtin`

Built-in agent tools: `sql_query`, `web_search`, `file_read`, `python_exec`, `vector_search`.

::: dataenginex.ai.tools.builtin

______________________________________________________________________

## Workflows

`dataenginex.ai.workflows.dag` — multi-step agent workflows as DAGs; steps branch, merge, and pass structured outputs

::: dataenginex.ai.workflows.dag

`dataenginex.ai.workflows.conditions` — conditional branching logic for DAG workflows

::: dataenginex.ai.workflows.conditions

`dataenginex.ai.workflows.human_loop` — pause a workflow at a step requiring human review or approval

::: dataenginex.ai.workflows.human_loop

______________________________________________________________________

## Observability

`dataenginex.ai.observability.audit` — logs every LLM request/response, tool call, and agent step for compliance

::: dataenginex.ai.observability.audit

`dataenginex.ai.observability.cost` — tracks token usage and estimated cost per provider, model, and agent run

::: dataenginex.ai.observability.cost

`dataenginex.ai.observability.metrics` — Prometheus metrics for LLM latency, token throughput, error rate

::: dataenginex.ai.observability.metrics
