"""Tests for the GraphRAG system."""

import networkx as nx

from graphsim.engine.state import AgentMessage, DecisionRecord, SimulationState
from graphsim.rag.communities import (
    CommunityDetector,
    detect_information_silos,
    find_agent_communities,
)
from graphsim.rag.engine import GraphRAGEngine
from graphsim.rag.extractor import (
    ExtractionResult,
    ExtractedEntity,
    ExtractedRelationship,
    KnowledgeGraphExtractor,
    build_knowledge_graph_from_state,
)
from graphsim.rag.store import KnowledgeStore


def _make_simulation_state() -> SimulationState:
    """Create a realistic simulation state for testing."""
    state = SimulationState(
        scenario_id="test_school",
        current_round=3,
        max_rounds=5,
        active_agent_ids=["rektor", "kurator", "larare", "vardnadshavare"],
        metadata={
            "title": "Elev med hög frånvaro",
            "description": "En elev har haft ökande frånvaro",
            "initial_event": "Rektor kallar till möte",
        },
    )

    # Round 0 messages
    state.add_message(AgentMessage(
        agent_id="rektor", role="Rektor",
        content="Välkomna till mötet. Vi behöver diskutera elevens frånvaro.",
        round_number=0,
    ))
    state.add_message(AgentMessage(
        agent_id="larare", role="Lärare",
        content="Eleven har missat 60% av lektionerna senaste månaden.",
        round_number=0,
    ))
    state.add_message(AgentMessage(
        agent_id="kurator", role="Kurator",
        content="Jag har inte haft kontakt med eleven ännu men vill boka samtal.",
        round_number=0,
    ))

    # Round 1
    state.add_message(AgentMessage(
        agent_id="kurator", role="Kurator",
        content="Jag har pratat med eleven. Hen berättar om mobbning.",
        round_number=1, visible_to=["kurator", "rektor"],
    ))
    state.add_message(AgentMessage(
        agent_id="vardnadshavare", role="Vårdnadshavare",
        content="Mitt barn vill inte gå till skolan men säger inte varför.",
        round_number=1,
    ))

    # Round 2
    state.add_message(AgentMessage(
        agent_id="rektor", role="Rektor",
        content="Vi behöver göra en anmälan och sätta in åtgärder mot mobbningen.",
        round_number=2,
    ))
    state.add_message(AgentMessage(
        agent_id="larare", role="Lärare",
        content="Jag kan anpassa undervisningen så eleven kan vara med på distans.",
        round_number=2,
    ))

    # Decisions
    state.add_decision(DecisionRecord(
        decision_id="dec_1",
        made_by="rektor",
        description="Beslut att utreda mobbning",
        round_number=2,
        affects=["larare", "kurator"],
    ))

    return state


# ============================================================================
# Knowledge Graph Extraction
# ============================================================================

def test_build_kg_from_state():
    state = _make_simulation_state()
    kg = build_knowledge_graph_from_state(state)

    # Should have agent nodes
    assert "rektor" in kg.nodes
    assert "kurator" in kg.nodes
    assert "larare" in kg.nodes

    # Should have message nodes
    assert kg.number_of_nodes() > 4  # agents + messages + decisions

    # Should have edges
    assert kg.number_of_edges() > 0


def test_build_kg_has_decisions():
    state = _make_simulation_state()
    kg = build_knowledge_graph_from_state(state)

    # Should have decision nodes
    decision_nodes = [
        n for n, d in kg.nodes(data=True)
        if d.get("entity_type") == "decision"
    ]
    assert len(decision_nodes) == 1


def test_build_kg_information_flow():
    state = _make_simulation_state()
    kg = build_knowledge_graph_from_state(state)

    # Check that "informed" edges exist
    informed_edges = [
        (u, v) for u, v, d in kg.edges(data=True)
        if d.get("relation_type") == "informed"
    ]
    assert len(informed_edges) > 0


def test_extraction_result_to_networkx():
    extractor = KnowledgeGraphExtractor.__new__(KnowledgeGraphExtractor)
    result = ExtractionResult(
        entities=[
            ExtractedEntity(entity_id="e1", entity_type="person", label="Anna"),
            ExtractedEntity(entity_id="e2", entity_type="decision", label="Beslut X"),
        ],
        relationships=[
            ExtractedRelationship(
                source_id="e1", target_id="e2", relation_type="decided"
            ),
        ],
    )
    graph = extractor.to_networkx(result)
    assert graph.number_of_nodes() == 2
    assert graph.number_of_edges() == 1


# ============================================================================
# Community Detection
# ============================================================================

def test_community_detection_basic():
    # Build a graph with two clear clusters
    graph = nx.DiGraph()
    # Cluster 1: agents
    for i in range(5):
        graph.add_node(f"a{i}", entity_type="person", label=f"Agent {i}")
    for i in range(4):
        graph.add_edge(f"a{i}", f"a{i+1}", relation_type="collaborates")
        graph.add_edge(f"a{i+1}", f"a{i}", relation_type="collaborates")

    # Cluster 2: decisions
    for i in range(4):
        graph.add_node(f"d{i}", entity_type="decision", label=f"Decision {i}")
    for i in range(3):
        graph.add_edge(f"d{i}", f"d{i+1}", relation_type="led_to")
        graph.add_edge(f"d{i+1}", f"d{i}", relation_type="influenced")

    # Weak connection between clusters
    graph.add_edge("a0", "d0", relation_type="decided")

    detector = CommunityDetector()
    result = detector.detect_communities(graph)

    assert result.total_communities >= 1
    assert result.total_nodes == 9


def test_community_detection_empty_graph():
    detector = CommunityDetector()
    result = detector.detect_communities(nx.DiGraph())
    assert result.total_communities == 0


def test_generate_local_summaries():
    state = _make_simulation_state()
    kg = build_knowledge_graph_from_state(state)

    detector = CommunityDetector()
    result = detector.detect_communities(kg, min_community_size=2)

    # Generate summaries without LLM
    result = detector.generate_local_summaries(kg, result)

    for community in result.communities:
        assert community.summary != ""


def test_find_agent_communities():
    graph = nx.DiGraph()
    graph.add_node("agent1", entity_type="person", label="Agent 1")
    graph.add_node("msg1", entity_type="action", label="Message")
    graph.add_node("other", entity_type="person", label="Other")
    graph.add_edge("agent1", "msg1", relation_type="performed")

    from graphsim.rag.communities import Community
    communities = [
        Community(
            community_id="c0",
            node_ids=["agent1", "msg1"],
            size=2,
        ),
        Community(
            community_id="c1",
            node_ids=["other"],
            size=1,
        ),
    ]

    relevant = find_agent_communities("agent1", graph, communities)
    assert len(relevant) == 1
    assert relevant[0].community_id == "c0"


def test_detect_information_silos():
    graph = nx.DiGraph()
    # Two disconnected clusters
    for i in range(3):
        graph.add_node(f"a{i}", entity_type="person", label=f"A{i}")
    for i in range(3):
        graph.add_node(f"b{i}", entity_type="person", label=f"B{i}")

    # Intra-cluster connections
    graph.add_edge("a0", "a1", relation_type="collaborates")
    graph.add_edge("a1", "a2", relation_type="collaborates")
    graph.add_edge("b0", "b1", relation_type="collaborates")
    graph.add_edge("b1", "b2", relation_type="collaborates")

    # No cross-cluster connections
    from graphsim.rag.communities import Community
    communities = [
        Community(community_id="c0", node_ids=["a0", "a1", "a2"], size=3),
        Community(community_id="c1", node_ids=["b0", "b1", "b2"], size=3),
    ]

    silos = detect_information_silos(graph, communities)
    assert len(silos) == 1
    assert silos[0]["cross_edges"] == 0


# ============================================================================
# Knowledge Store
# ============================================================================

def test_knowledge_store_archive():
    store = KnowledgeStore()
    kg = nx.DiGraph()
    kg.add_node("n1", entity_type="person", label="Test")

    from graphsim.rag.communities import CommunityDetectionResult
    communities = CommunityDetectionResult()

    archive = store.archive_simulation(
        simulation_id="test_sim",
        scenario_id="test_scenario",
        scenario_title="Test Scenario",
        total_rounds=3,
        total_messages=10,
        knowledge_graph=kg,
        communities=communities,
    )

    assert archive.simulation_id == "test_sim"
    assert store.archive_count == 1


def test_knowledge_store_find_similar():
    store = KnowledgeStore()
    kg = nx.DiGraph()
    kg.add_node("n1")

    from graphsim.rag.communities import CommunityDetectionResult
    communities = CommunityDetectionResult()

    store.archive_simulation(
        simulation_id="s1",
        scenario_id="school_absence",
        scenario_title="Elev med hög frånvaro",
        total_rounds=5, total_messages=20,
        knowledge_graph=kg, communities=communities,
    )
    store.archive_simulation(
        simulation_id="s2",
        scenario_id="budget_cut",
        scenario_title="Budgetneddragning i kommun",
        total_rounds=6, total_messages=30,
        knowledge_graph=kg, communities=communities,
    )

    similar = store.find_similar_scenarios("Elev frånvaro skola")
    assert len(similar) >= 1
    assert similar[0].scenario_id == "school_absence"


def test_knowledge_store_precedent_context():
    store = KnowledgeStore()
    kg = nx.DiGraph()
    kg.add_node("n1")

    from graphsim.rag.communities import Community, CommunityDetectionResult
    communities = CommunityDetectionResult(
        communities=[
            Community(
                community_id="c0", node_ids=["n1"], size=1,
                summary="Tidig samverkan ledde till bättre utfall",
            ),
        ],
        total_communities=1,
    )

    store.archive_simulation(
        simulation_id="s1",
        scenario_id="school_absence",
        scenario_title="Elev med hög frånvaro",
        total_rounds=5, total_messages=20,
        knowledge_graph=kg, communities=communities,
    )

    precedents = store.get_precedent_context("Elev frånvaro")
    assert len(precedents) >= 1
    assert "Tidig samverkan" in precedents[0]


# ============================================================================
# GraphRAG Engine
# ============================================================================

def test_engine_build_kg():
    engine = GraphRAGEngine()
    state = _make_simulation_state()
    kg = engine.build_knowledge_graph(state, use_llm=False)

    assert kg.number_of_nodes() > 0
    assert kg.number_of_edges() > 0


def test_engine_detect_communities():
    engine = GraphRAGEngine()
    state = _make_simulation_state()
    kg = engine.build_knowledge_graph(state, use_llm=False)
    result = engine.detect_communities(kg)

    assert result.total_nodes > 0


def test_engine_analyze_graph_structure():
    engine = GraphRAGEngine()
    state = _make_simulation_state()
    kg = engine.build_knowledge_graph(state, use_llm=False)
    stats = engine.analyze_graph_structure(kg)

    assert stats["nodes"] > 0
    assert stats["edges"] > 0
    assert "entity_types" in stats
    assert "relationship_types" in stats
    assert "most_connected" in stats


def test_engine_empty_graph_stats():
    engine = GraphRAGEngine()
    stats = engine.analyze_graph_structure(nx.DiGraph())
    assert stats["nodes"] == 0
