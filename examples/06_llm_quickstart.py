"""Example 06 — LLM Provider Quickstart.

Demonstrates:
    1. Creating LLM providers (Mock, Ollama, OpenAI-compatible)
    2. Generating text with ``generate()`` and ``chat()``
    3. RAG-style generation with ``generate_with_context()``
    4. Using the ``get_llm_provider()`` factory function

Run::

    uv run python examples/06_llm_quickstart.py
"""

from __future__ import annotations

from dataenginex.ml.llm import ChatMessage, MockProvider, get_llm_provider


def main() -> None:
    """Demonstrate LLM provider capabilities."""
    # 1. Create a mock provider (no API key or server needed)
    llm = MockProvider(default_response="Here is a helpful answer.")
    print("=== MockProvider ===")
    print(f"Available: {llm.is_available()}")

    # 2. Simple text generation
    response = llm.generate("Explain the medallion architecture in data engineering.")
    print(f"\nGenerate: {response.text}")
    print(f"  Model: {response.model}")
    print(f"  Tokens: {response.total_tokens}")

    # 3. Chat-style conversation
    messages = [
        ChatMessage(role="system", content="You are a data engineering expert."),
        ChatMessage(role="user", content="What is a quality gate?"),
    ]
    response = llm.chat(messages)
    print(f"\nChat: {response.text}")

    # 4. RAG-style: generate with retrieved context
    context = (
        "DataEngineX uses a medallion architecture with Bronze (raw), "
        "Silver (validated), and Gold (aggregated) layers."
    )
    response = llm.generate_with_context(
        question="How does DataEngineX organise data?",
        context=context,
    )
    print(f"\nRAG: {response.text}")

    # 5. Factory function
    print("\n=== Factory ===")
    for provider_name in ("mock", "ollama"):
        provider = get_llm_provider(provider_name)
        print(f"  {provider_name}: {type(provider).__name__} (available={provider.is_available()})")

    # 6. Call history (mock only)
    print(f"\n=== MockProvider called {len(llm.call_history)} times ===")
    for entry in llm.call_history:
        print(f"  {entry['type']}")

    print("\nDone!")


if __name__ == "__main__":
    main()
