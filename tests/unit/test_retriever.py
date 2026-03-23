"""Tests for the built-in retriever (BM25, dense, hybrid)."""

from __future__ import annotations

from dataenginex.ai.retrieval.builtin import _BM25, BuiltinRetriever, _rrf

SAMPLE_DOCS = [
    {"id": "1", "text": "Python is a programming language"},
    {"id": "2", "text": "DuckDB is an in-process SQL OLAP database"},
    {"id": "3", "text": "Machine learning uses Python and data"},
    {"id": "4", "text": "SQL queries can filter and transform data"},
    {"id": "5", "text": "FastAPI is a modern Python web framework"},
]


class TestBM25:
    def test_basic_scoring(self) -> None:
        bm25 = _BM25()
        bm25.index(SAMPLE_DOCS)
        results = bm25.score("python programming")
        assert len(results) > 0
        # Doc 1 should score highest for "python programming"
        assert results[0][0] == 0

    def test_empty_query(self) -> None:
        bm25 = _BM25()
        bm25.index(SAMPLE_DOCS)
        results = bm25.score("")
        assert results == []

    def test_no_match(self) -> None:
        bm25 = _BM25()
        bm25.index(SAMPLE_DOCS)
        results = bm25.score("xyzzyplugh")
        assert results == []

    def test_top_k_limit(self) -> None:
        bm25 = _BM25()
        bm25.index(SAMPLE_DOCS)
        results = bm25.score("data", top_k=2)
        assert len(results) <= 2


class TestRRF:
    def test_basic_fusion(self) -> None:
        r1 = [(0, 1.0), (1, 0.5), (2, 0.3)]
        r2 = [(2, 1.0), (0, 0.5), (3, 0.3)]
        fused = _rrf(r1, r2)
        assert len(fused) == 4
        # Both r1 and r2 have doc 0, so it should rank high
        doc_ids = [idx for idx, _ in fused]
        assert 0 in doc_ids[:2]


class TestBuiltinRetriever:
    def test_sparse_retrieval(self) -> None:
        retriever = BuiltinRetriever(strategy="sparse", documents=SAMPLE_DOCS)
        results = retriever.retrieve("python", top_k=3)
        assert len(results) > 0
        assert all(r["method"] == "bm25" for r in results)

    def test_hybrid_without_vector_store(self) -> None:
        retriever = BuiltinRetriever(strategy="hybrid", documents=SAMPLE_DOCS)
        results = retriever.retrieve("SQL database", top_k=3)
        assert len(results) > 0
        assert all(r["method"] == "hybrid" for r in results)

    def test_dense_without_store_returns_empty(self) -> None:
        retriever = BuiltinRetriever(strategy="dense", documents=SAMPLE_DOCS)
        results = retriever.retrieve("python", top_k=3)
        assert results == []

    def test_strategy_override(self) -> None:
        retriever = BuiltinRetriever(strategy="hybrid", documents=SAMPLE_DOCS)
        results = retriever.retrieve("python", top_k=3, strategy="sparse")
        assert all(r["method"] == "bm25" for r in results)

    def test_empty_documents(self) -> None:
        retriever = BuiltinRetriever(strategy="sparse")
        results = retriever.retrieve("python", top_k=3)
        assert results == []
