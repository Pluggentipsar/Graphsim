"""Tests for the orchestrator."""

from graphsim.config import SimulationConfig
from graphsim.engine.scenario import load_scenario
from graphsim.orchestrator import Orchestrator


def test_load_scenario():
    config = SimulationConfig()
    orchestrator = Orchestrator(config)
    scenario = load_scenario("scenarios/example_school.yaml")
    orchestrator.load_scenario(scenario)

    assert orchestrator.state is not None
    assert orchestrator.state.scenario_id == "school_absence"
    assert orchestrator.registry is not None
    assert len(orchestrator.registry.get_all()) == 6


def test_graph_built_from_scenario():
    orchestrator = Orchestrator()
    scenario = load_scenario("scenarios/example_school.yaml")
    orchestrator.load_scenario(scenario)

    # Should have 6 person nodes
    assert orchestrator.graph.node_count == 6
    # Should have relationships
    assert orchestrator.graph.edge_count > 0

    # Check specific relationship
    rektor_node = orchestrator.graph.get_node("rektor")
    assert rektor_node is not None
    assert "Anna Lindberg" in rektor_node.label


def test_scenario_state_metadata():
    orchestrator = Orchestrator()
    orchestrator.load_scenario("scenarios/example_school.yaml")

    assert orchestrator.state.metadata["title"] == "Elev med hög frånvaro"
    assert "frånvaro" in orchestrator.state.metadata["description"].lower()


def test_agent_context_building():
    orchestrator = Orchestrator()
    orchestrator.load_scenario("scenarios/example_school.yaml")

    mentor = orchestrator.registry.get("mentor")
    assert mentor is not None

    context = orchestrator._build_agent_context(mentor, round_number=0)
    assert context.round_number == 0
    assert context.scenario_context != ""
    assert len(context.relationships) > 0
