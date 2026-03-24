"""Tests for the agent layer."""

from graphsim.agents.base import AgentContext, BaseAgent
from graphsim.agents.registry import AgentRegistry
from graphsim.engine.scenario import AgentRoleConfig, ScenarioConfig
from graphsim.engine.state import AgentMessage


def _make_config(role_id: str = "test_role", name: str = "Test Agent") -> AgentRoleConfig:
    return AgentRoleConfig(
        role_id=role_id,
        name=name,
        title="Testroll",
        responsibilities=["Ansvar 1", "Ansvar 2"],
        goals=["Mål 1"],
        constraints=["Begränsning 1"],
        personality="Vänlig",
    )


def test_agent_creation():
    config = _make_config()
    agent = BaseAgent(config=config)
    assert agent.agent_id == "test_role"


def test_system_prompt_contains_role():
    agent = BaseAgent(config=_make_config(name="Anna"))
    prompt = agent.build_system_prompt()
    assert "Anna" in prompt
    assert "Testroll" in prompt
    assert "Ansvar 1" in prompt
    assert "Mål 1" in prompt
    assert "Begränsning 1" in prompt
    assert "Vänlig" in prompt


def test_context_prompt():
    agent = BaseAgent(config=_make_config())
    context = AgentContext(
        round_number=2,
        visible_messages=[
            AgentMessage(
                agent_id="other", role="Annan roll", content="Hej!", round_number=1
            )
        ],
        scenario_context="Ett testscenario",
        pending_decisions=["Beslut A"],
    )
    prompt = agent.build_context_prompt(context)
    assert "Runda 2" in prompt
    assert "Hej!" in prompt
    assert "Ett testscenario" in prompt
    assert "Beslut A" in prompt


def test_registry_from_scenario():
    scenario = ScenarioConfig(
        scenario_id="test",
        title="Test",
        description="Test scenario",
        agents=[
            _make_config("role_a", "Agent A"),
            _make_config("role_b", "Agent B"),
        ],
    )
    registry = AgentRegistry.from_scenario(scenario)
    assert len(registry.get_all()) == 2
    assert registry.get("role_a") is not None
    assert registry.get("role_b") is not None
    assert registry.get("nonexistent") is None


def test_registry_get_by_ids():
    scenario = ScenarioConfig(
        scenario_id="test",
        title="Test",
        description="Test",
        agents=[
            _make_config("a", "A"),
            _make_config("b", "B"),
            _make_config("c", "C"),
        ],
    )
    registry = AgentRegistry.from_scenario(scenario)
    agents = registry.get_by_ids(["a", "c"])
    assert len(agents) == 2
    ids = {a.agent_id for a in agents}
    assert ids == {"a", "c"}
