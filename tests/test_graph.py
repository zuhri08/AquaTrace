import pytest

from app.ds.graph import Graph, MinHeap


def test_directed_graph_edge_management_and_traversals():
    graph = Graph()
    graph.add_edge("A", "B", 2)
    graph.add_edge("A", "C", 1)
    graph.add_edge("C", "D", 1)
    graph.add_edge("B", "D", 1)

    assert graph.neighbors("A") == [("B", 2), ("C", 1)]
    assert graph.bfs("A") == ["A", "B", "C", "D"]
    assert graph.dfs("A") == ["A", "B", "D", "C"]
    assert graph.bfs("unknown") == []
    assert graph.remove_edge("A", "B") is True
    assert graph.remove_edge("A", "B") is False
    assert graph.neighbors("A") == [("C", 1)]


def test_graph_rejects_duplicate_self_and_non_positive_edges():
    graph = Graph()
    graph.add_edge(1, 2, 1)
    with pytest.raises(ValueError, match="sudah ada"):
        graph.add_edge(1, 2, 3)
    with pytest.raises(ValueError, match="diri sendiri"):
        graph.add_edge(1, 1, 1)
    with pytest.raises(ValueError, match="lebih besar"):
        graph.add_edge(1, 3, 0)
    with pytest.raises(ValueError, match="lebih besar"):
        graph.add_edge(1, 3, float("nan"))
    with pytest.raises(ValueError, match="lebih besar"):
        graph.add_edge(1, 3, True)


def test_dijkstra_and_shortest_path_with_manual_heap():
    graph = Graph()
    graph.add_edge("A", "B", 4)
    graph.add_edge("A", "C", 1)
    graph.add_edge("C", "B", 2)
    graph.add_edge("B", "D", 1)
    graph.add_node("isolated")

    distances, previous = graph.dijkstra("A")
    assert distances == {"A": 0, "B": 3, "C": 1, "D": 4, "isolated": float("inf")}
    assert previous["D"] == "B"
    assert graph.shortest_path("A", "D") == (["A", "C", "B", "D"], 4)
    assert graph.shortest_path("A", "isolated") is None
    assert graph.dijkstra("missing") == ({}, {})


def test_min_heap_orders_values_without_comparing_nodes():
    heap = MinHeap()
    heap.push(3, object())
    heap.push(1, object())
    heap.push(1, object())
    assert heap.size() == 3
    assert heap.pop()[0] == 1
    assert heap.pop()[0] == 1
    assert heap.pop()[0] == 3
    assert heap.is_empty()
    with pytest.raises(IndexError):
        heap.pop()
