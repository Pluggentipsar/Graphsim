"""Agent registry - creates and manages agent instances from scenario configs."""

from __future__ import annotations

from graphsim.agents.base import BaseAgent
from graphsim.engine.scenario import AgentRoleConfig, ScenarioConfig


class AgentRegistry:
    """Registry that holds all agents for a simulation run."""

    def __init__(self) -> None:
        self._agents: dict[str, BaseAgent] = {}

    def register(self, config: AgentRoleConfig) -> BaseAgent:
        """Create and register an agent from a role config."""
        agent = BaseAgent(config=config)
        self._agents[agent.agent_id] = agent
        return agent

    def get(self, agent_id: str) -> BaseAgent | None:
        return self._agents.get(agent_id)

    def get_all(self) -> list[BaseAgent]:
        return list(self._agents.values())

    def get_by_ids(self, agent_ids: list[str]) -> list[BaseAgent]:
        return [a for aid in agent_ids if (a := self._agents.get(aid))]

    @classmethod
    def from_scenario(cls, scenario: ScenarioConfig) -> AgentRegistry:
        """Build a full registry from a scenario configuration."""
        registry = cls()
        for agent_config in scenario.agents:
            registry.register(agent_config)
        return registry
