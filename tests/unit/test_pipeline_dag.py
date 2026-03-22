"""Tests for pipeline DAG resolution."""
from __future__ import annotations

import pytest

from dataenginex.data.pipeline.dag import resolve_execution_order


class TestDagResolver:
    def test_no_dependencies(self) -> None:
        pipelines = {"a": [], "b": [], "c": []}
        order = resolve_execution_order(pipelines)
        assert set(order) == {"a", "b", "c"}

    def test_linear_chain(self) -> None:
        pipelines = {"a": [], "b": ["a"], "c": ["b"]}
        order = resolve_execution_order(pipelines)
        assert order.index("a") < order.index("b") < order.index("c")

    def test_diamond_dependency(self) -> None:
        pipelines = {"a": [], "b": ["a"], "c": ["a"], "d": ["b", "c"]}
        order = resolve_execution_order(pipelines)
        assert order.index("a") < order.index("b")
        assert order.index("a") < order.index("c")
        assert order.index("b") < order.index("d")
        assert order.index("c") < order.index("d")

    def test_cycle_raises(self) -> None:
        pipelines = {"a": ["b"], "b": ["a"]}
        with pytest.raises(ValueError, match="[Cc]ycle"):
            resolve_execution_order(pipelines)

    def test_missing_dependency_raises(self) -> None:
        pipelines = {"a": ["nonexistent"]}
        with pytest.raises(KeyError, match="nonexistent"):
            resolve_execution_order(pipelines)

    def test_single_pipeline(self) -> None:
        pipelines = {"only": []}
        order = resolve_execution_order(pipelines)
        assert order == ["only"]

    def test_empty_graph(self) -> None:
        assert resolve_execution_order({}) == []
