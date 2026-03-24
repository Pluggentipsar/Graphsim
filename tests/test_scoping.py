"""Tests for the information scoping system."""

from graphsim.engine.scoping import (
    InformationScope,
    SecrecyDomain,
    SecrecyRule,
)
from graphsim.engine.state import AgentMessage, SimulationState
from graphsim.graph.models import EdgeType, GraphEdge, GraphNode, NodeType
from graphsim.graph.store import GraphStore


def _build_test_graph() -> GraphStore:
    store = GraphStore()
    store.add_node(GraphNode(
        node_id="kurator", node_type=NodeType.PERSON, label="Kurator",
        properties={"information_level": "medium"},
    ))
    store.add_node(GraphNode(
        node_id="rektor", node_type=NodeType.PERSON, label="Rektor",
        properties={"information_level": "high"},
    ))
    store.add_node(GraphNode(
        node_id="larare", node_type=NodeType.PERSON, label="Lärare",
        properties={"information_level": "high"},
    ))
    store.add_node(GraphNode(
        node_id="vardnadshavare", node_type=NodeType.PERSON, label="VH",
        properties={"information_level": "low"},
    ))
    store.add_edge(GraphEdge(
        source_id="kurator", target_id="rektor", edge_type=EdgeType.REPORTS_TO,
    ))
    store.add_edge(GraphEdge(
        source_id="larare", target_id="kurator", edge_type=EdgeType.COLLABORATES_WITH,
    ))
    return store


def _make_state_with_messages() -> SimulationState:
    state = SimulationState(scenario_id="test", current_round=1, max_rounds=5)
    # Public message
    state.add_message(AgentMessage(
        agent_id="rektor", role="Rektor", content="Välkomna alla",
        round_number=0,
    ))
    # Message with visibility restriction
    state.add_message(AgentMessage(
        agent_id="kurator", role="Kurator",
        content="Eleven mår dåligt (sekretess)",
        round_number=0, visible_to=["kurator", "rektor"],
    ))
    # Open message from teacher
    state.add_message(AgentMessage(
        agent_id="larare", role="Lärare", content="Eleven har hög frånvaro",
        round_number=1,
    ))
    return state


def test_own_messages_always_visible():
    graph = _build_test_graph()
    scope = InformationScope(graph)
    state = _make_state_with_messages()

    visible = scope.get_visible_messages("kurator", state, "medium")
    own = [m for m in visible if m.agent_id == "kurator"]
    assert len(own) == 1


def test_visibility_restrictions_respected():
    graph = _build_test_graph()
    scope = InformationScope(graph)
    state = _make_state_with_messages()

    # VH should NOT see kurator's restricted message
    vh_visible = scope.get_visible_messages("vardnadshavare", state, "low")
    kurator_msgs = [m for m in vh_visible if m.agent_id == "kurator"]
    assert len(kurator_msgs) == 0

    # Rektor SHOULD see kurator's restricted message
    rektor_visible = scope.get_visible_messages("rektor", state, "high")
    kurator_msgs = [m for m in rektor_visible if m.agent_id == "kurator"]
    assert len(kurator_msgs) == 1


def test_secrecy_prompt_for_medical_role():
    graph = _build_test_graph()
    # Add a medical role
    graph.add_node(GraphNode(
        node_id="skolskoterska", node_type=NodeType.PERSON, label="Skolsköterska",
    ))
    scope = InformationScope(graph)

    prompt = scope.get_secrecy_prompt("skolskoterska")
    assert "sekretess" in prompt.lower() or "Medicinsk" in prompt


def test_secrecy_prompt_empty_for_non_secrecy_role():
    graph = _build_test_graph()
    scope = InformationScope(graph)

    prompt = scope.get_secrecy_prompt("larare")
    assert prompt == ""


def test_information_level_window():
    graph = _build_test_graph()
    scope = InformationScope(graph)
    state = SimulationState(scenario_id="test", current_round=5, max_rounds=10)

    # Add many messages
    for i in range(30):
        state.add_message(AgentMessage(
            agent_id="rektor", role="Rektor", content=f"Msg {i}",
            round_number=i % 5,
        ))

    # Low info level gets fewer messages
    low_msgs = scope.get_visible_messages("vardnadshavare", state, "low")
    high_msgs = scope.get_visible_messages("rektor", state, "high")
    assert len(low_msgs) <= len(high_msgs)
