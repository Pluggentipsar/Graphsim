"""Tests for the graph layer."""

from graphsim.graph.models import EdgeType, GraphEdge, GraphNode, NodeType
from graphsim.graph.queries import find_collaborators, find_reporting_chain
from graphsim.graph.store import GraphStore


def _make_person(node_id: str, name: str) -> GraphNode:
    return GraphNode(node_id=node_id, node_type=NodeType.PERSON, label=name)


def _make_edge(source: str, target: str, edge_type: EdgeType) -> GraphEdge:
    return GraphEdge(source_id=source, target_id=target, edge_type=edge_type)


def test_add_and_get_node():
    store = GraphStore()
    node = _make_person("rektor", "Anna Lindberg")
    store.add_node(node)

    result = store.get_node("rektor")
    assert result is not None
    assert result.label == "Anna Lindberg"
    assert result.node_type == NodeType.PERSON


def test_add_edge_and_get_neighbors():
    store = GraphStore()
    store.add_node(_make_person("mentor", "Erik"))
    store.add_node(_make_person("rektor", "Anna"))
    store.add_edge(_make_edge("mentor", "rektor", EdgeType.REPORTS_TO))

    neighbors = store.get_neighbors("mentor", EdgeType.REPORTS_TO)
    assert len(neighbors) == 1
    assert neighbors[0].node_id == "rektor"


def test_get_relationships_for_agent():
    store = GraphStore()
    store.add_node(_make_person("mentor", "Erik"))
    store.add_node(_make_person("rektor", "Anna"))
    store.add_node(_make_person("kurator", "Maria"))
    store.add_edge(_make_edge("mentor", "rektor", EdgeType.REPORTS_TO))
    store.add_edge(_make_edge("mentor", "kurator", EdgeType.COLLABORATES_WITH))

    rels = store.get_relationships_for_agent("mentor")
    assert len(rels) == 2
    types = {r["type"] for r in rels}
    assert "reports_to" in types
    assert "collaborates_with" in types


def test_find_reporting_chain():
    store = GraphStore()
    store.add_node(_make_person("teacher", "Lärare"))
    store.add_node(_make_person("head", "Avdelningschef"))
    store.add_node(_make_person("principal", "Rektor"))
    store.add_edge(_make_edge("teacher", "head", EdgeType.REPORTS_TO))
    store.add_edge(_make_edge("head", "principal", EdgeType.REPORTS_TO))

    chain = find_reporting_chain(store, "teacher")
    assert chain == ["head", "principal"]


def test_find_collaborators():
    store = GraphStore()
    store.add_node(_make_person("a", "Agent A"))
    store.add_node(_make_person("b", "Agent B"))
    store.add_node(_make_person("c", "Agent C"))
    store.add_edge(_make_edge("a", "b", EdgeType.COLLABORATES_WITH))
    store.add_edge(_make_edge("a", "c", EdgeType.COLLABORATES_WITH))

    collabs = find_collaborators(store, "a")
    assert len(collabs) == 2


def test_node_count_and_edge_count():
    store = GraphStore()
    store.add_node(_make_person("a", "A"))
    store.add_node(_make_person("b", "B"))
    store.add_edge(_make_edge("a", "b", EdgeType.REPORTS_TO))

    assert store.node_count == 2
    assert store.edge_count == 1


def test_get_nodes_by_type():
    store = GraphStore()
    store.add_node(_make_person("a", "A"))
    store.add_node(_make_person("b", "B"))
    store.add_node(GraphNode(node_id="case1", node_type=NodeType.CASE, label="Case 1"))

    persons = store.get_nodes_by_type(NodeType.PERSON)
    cases = store.get_nodes_by_type(NodeType.CASE)
    assert len(persons) == 2
    assert len(cases) == 1
