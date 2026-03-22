"""DAG resolver for pipeline execution order.

Resolves cross-pipeline dependencies defined by `depends_on` in config.
Uses Kahn's algorithm (topological sort) to produce execution order.
"""

from __future__ import annotations

from collections import deque


def _validate_deps(pipelines: dict[str, list[str]]) -> None:
    """Raise KeyError if any dependency references a non-existent pipeline."""
    for name, deps in pipelines.items():
        for dep in deps:
            if dep not in pipelines:
                msg = f"Pipeline '{name}' depends on '{dep}' which does not exist"
                raise KeyError(msg)


def _build_graph(
    pipelines: dict[str, list[str]],
) -> tuple[dict[str, int], dict[str, list[str]]]:
    """Build in-degree map and adjacency list from dependency graph."""
    in_degree: dict[str, int] = {name: 0 for name in pipelines}
    adjacency: dict[str, list[str]] = {name: [] for name in pipelines}
    for name, deps in pipelines.items():
        for dep in deps:
            adjacency[dep].append(name)
            in_degree[name] += 1
    return in_degree, adjacency


def resolve_execution_order(
    pipelines: dict[str, list[str]],
) -> list[str]:
    """Resolve execution order from dependency graph.

    Args:
        pipelines: Mapping of pipeline_name -> list of dependency names.

    Returns:
        List of pipeline names in valid execution order.

    Raises:
        KeyError: If a dependency references a non-existent pipeline.
        ValueError: If there is a cycle in the dependency graph.
    """
    _validate_deps(pipelines)
    in_degree, adjacency = _build_graph(pipelines)

    queue: deque[str] = deque(name for name, degree in in_degree.items() if degree == 0)
    order: list[str] = []

    while queue:
        node = queue.popleft()
        order.append(node)
        for neighbor in adjacency[node]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    if len(order) != len(pipelines):
        msg = "Cycle detected in pipeline dependencies"
        raise ValueError(msg)

    return order
