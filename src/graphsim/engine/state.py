"""Simulation state management - the central state that flows through LangGraph."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AgentMessage(BaseModel):
    """A message from an agent during simulation."""

    agent_id: str
    role: str
    content: str
    round_number: int
    visible_to: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DecisionRecord(BaseModel):
    """A decision made during simulation."""

    decision_id: str
    made_by: str
    description: str
    round_number: int
    affects: list[str] = Field(default_factory=list)
    rationale: str = ""


class SimulationState(BaseModel):
    """The complete state of a running simulation.

    This is the state object that flows through the LangGraph graph.
    """

    scenario_id: str
    current_round: int = 0
    max_rounds: int = 20
    active_agent_ids: list[str] = Field(default_factory=list)
    messages: list[AgentMessage] = Field(default_factory=list)
    decisions: list[DecisionRecord] = Field(default_factory=list)
    pending_actions: list[dict[str, Any]] = Field(default_factory=list)
    finished: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    def messages_visible_to(self, agent_id: str) -> list[AgentMessage]:
        """Return messages that a specific agent is allowed to see."""
        return [
            m
            for m in self.messages
            if not m.visible_to or agent_id in m.visible_to or m.agent_id == agent_id
        ]

    def add_message(self, message: AgentMessage) -> None:
        self.messages.append(message)

    def add_decision(self, decision: DecisionRecord) -> None:
        self.decisions.append(decision)
