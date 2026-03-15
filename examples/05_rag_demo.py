"""Example 05 — RAG (Retrieval-Augmented Generation) Pipeline Demo.

Demonstrates:
    1. Creating an in-memory vector store backend
    2. Embedding documents with SentenceTransformerEmbedder (or hash fallback)
    3. Ingesting documents into the RAG pipeline
    4. Using RAGPipeline.answer() for the full retrieve → augment → generate loop
    5. Swapping providers: MockProvider for tests, OllamaProvider for production

Run with hash-based embeddings (no extra deps)::

    uv run python examples/05_rag_demo.py

Run with real sentence-transformer embeddings::

    uv sync --extra ml
    uv run python examples/05_rag_demo.py --embed sentence-transformers

Run against a live Ollama instance::

    uv run python examples/05_rag_demo.py --llm ollama --model qwen3-coder:30b-a3b-q4_K_M
"""

from __future__ import annotations

import argparse

from dataenginex.ml.llm import MockProvider, OllamaProvider
from dataenginex.ml.vectorstore import InMemoryBackend, RAGPipeline, SentenceTransformerEmbedder

DOCS = [
    (
        "DataEngineX is a data engineering and ML platform. "
        "It provides quality gates, medallion architecture, "
        "and model lifecycle management."
    ),
    (
        "The medallion architecture organises data into three layers: "
        "Bronze (raw ingestion), Silver (cleaned and validated), "
        "and Gold (business-ready aggregations)."
    ),
    (
        "DataEngineX examples demonstrate end-to-end pipelines. "
        "Examples 07-10 cover API ingestion, PySpark ML, "
        "feature engineering, and model analysis."
    ),
    (
        "The DataEngineX ML module provides ModelRegistry, DriftDetector, "
        "RAGPipeline, and LLM provider adapters for production ML workflows."
    ),
    (
        "Quality gates in DataEngineX enforce data completeness, "
        "consistency, and freshness checks before data moves "
        "between medallion layers."
    ),
]

QUERIES = [
    "What is the medallion architecture?",
    "How does the model registry work?",
    "What are quality gates?",
]


def build_pipeline(use_sentence_transformers: bool) -> RAGPipeline:
    if use_sentence_transformers:
        embedder = SentenceTransformerEmbedder()
        return RAGPipeline(store=InMemoryBackend(dimension=384), embed_fn=embedder, dimension=384)
    print("Using hash-based embeddings (install dataenginex[ml] for real embeddings)\n")
    return RAGPipeline(store=InMemoryBackend(dimension=64), dimension=64)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--embed", choices=["hash", "sentence-transformers"], default="hash")
    parser.add_argument("--llm", choices=["mock", "ollama"], default="mock")
    parser.add_argument("--model", default="qwen3-coder:30b-a3b-q4_K_M")
    args = parser.parse_args()

    # 1. Build pipeline
    pipeline = build_pipeline(use_sentence_transformers=args.embed == "sentence-transformers")

    # 2. Ingest
    print("=== Ingesting documents ===")
    count = pipeline.ingest(DOCS)
    print(f"Stored {count} documents\n")

    # 3. Choose LLM provider
    if args.llm == "ollama":
        llm = OllamaProvider(model=args.model)
        if not llm.is_available():
            print(
                f"Ollama not reachable or model '{args.model}' not loaded — falling back to mock\n"
            )
            llm = MockProvider()  # type: ignore[assignment]
    else:
        llm = MockProvider()  # type: ignore[assignment]

    print(f"LLM provider: {llm.__class__.__name__}\n")

    # 4. Full RAG loop via RAGPipeline.answer()
    for query in QUERIES:
        print(f"Q: {query}")
        response = pipeline.answer(query, llm, top_k=2)
        print(f"A: {response.text[:300]}")
        print(f"   tokens={response.total_tokens} finish={response.finish_reason}\n")

    print("Done.")


if __name__ == "__main__":
    main()
