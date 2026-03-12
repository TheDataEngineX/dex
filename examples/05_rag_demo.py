"""Example 05 — RAG (Retrieval-Augmented Generation) Pipeline Demo.

Demonstrates:
    1. Creating an in-memory vector store backend
    2. Ingesting sample documents into a RAG pipeline
    3. Querying the pipeline to retrieve relevant context
    4. Using the MockProvider to generate an LLM response with context

Run::

    uv run python examples/05_rag_demo.py
"""

from __future__ import annotations

from dataenginex.ml.llm import MockProvider
from dataenginex.ml.vectorstore import InMemoryBackend, RAGPipeline


def main() -> None:
    """Run the RAG demo pipeline."""
    # 1. Set up components
    backend = InMemoryBackend(dimension=64)
    pipeline = RAGPipeline(store=backend, dimension=64)
    llm = MockProvider(default_response="Based on the provided context, here is my answer.")

    # 2. Prepare sample documents
    texts = [
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
            "CareerDEX is the job matching application built on DataEngineX. "
            "It provides salary prediction, skill gap analysis, "
            "career path recommendations, and job matching."
        ),
        (
            "WeatherDEX is the weather pipeline module. It uses PySpark "
            "for feature engineering and ML model training on weather data."
        ),
        (
            "Quality gates in DataEngineX enforce data completeness, "
            "consistency, and freshness checks before data moves "
            "between medallion layers."
        ),
    ]
    doc_ids = ["doc-1", "doc-2", "doc-3", "doc-4", "doc-5"]

    # 3. Ingest documents into the RAG pipeline
    print("=== Ingesting documents ===")
    count = pipeline.ingest(texts, ids=doc_ids)
    print(f"Ingested {count} documents into the vector store.\n")

    # 4. Query the pipeline
    queries = [
        "What is the medallion architecture?",
        "How does CareerDEX work?",
        "What are quality gates?",
    ]

    for query in queries:
        print(f"--- Query: {query} ---")

        # Retrieve relevant context
        context = pipeline.build_context(query, top_k=2)
        print(f"Retrieved context ({len(context)} chars):\n{context[:200]}...\n")

        # Generate response using the LLM with retrieved context
        response = llm.generate_with_context(question=query, context=context)
        print(f"LLM Response: {response.text}\n")

    # 5. Show call history
    print(f"=== LLM was called {len(llm.call_history)} times ===")
    print("Done!")


if __name__ == "__main__":
    main()
