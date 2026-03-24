"""Base agent class for all simulation agents."""

from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from graphsim.engine.scenario import AgentRoleConfig
from graphsim.engine.state import AgentMessage, SimulationState


class AgentContext(BaseModel):
    """The information package an agent receives each round."""

    round_number: int
    visible_messages: list[AgentMessage] = Field(default_factory=list)
    relationships: list[dict[str, Any]] = Field(default_factory=list)
    pending_decisions: list[str] = Field(default_factory=list)
    scenario_context: str = ""


class BaseAgent(BaseModel):
    """A simulation agent that acts based on its role configuration."""

    config: AgentRoleConfig
    agent_id: str = ""

    def model_post_init(self, _context: Any) -> None:
        if not self.agent_id:
            self.agent_id = self.config.role_id

    def build_system_prompt(self) -> str:
        """Build the system prompt for this agent based on its role."""
        parts = [
            f"Du är {self.config.name}, {self.config.title}.",
            "",
            "Ditt ansvar:",
        ]
        for r in self.config.responsibilities:
            parts.append(f"- {r}")

        parts.append("")
        parts.append("Dina mål:")
        for g in self.config.goals:
            parts.append(f"- {g}")

        if self.config.constraints:
            parts.append("")
            parts.append("Begränsningar:")
            for c in self.config.constraints:
                parts.append(f"- {c}")

        if self.config.personality:
            parts.append("")
            parts.append(f"Personlighet/arbetssätt: {self.config.personality}")

        parts.append("")
        parts.append(
            "Svara alltid i roll. Basera dina beslut på den information du har tillgång till. "
            "Om du saknar information, säg det. Föreslå konkreta åtgärder."
        )
        return "\n".join(parts)

    def build_context_prompt(self, context: AgentContext) -> str:
        """Build the context message for a specific round."""
        parts = [f"=== Runda {context.round_number} ==="]

        if context.scenario_context:
            parts.append(f"\nScenario: {context.scenario_context}")

        if context.visible_messages:
            parts.append("\nTidigare kommunikation:")
            for msg in context.visible_messages[-10:]:  # Last 10 visible messages
                parts.append(f"[{msg.role}]: {msg.content}")

        if context.pending_decisions:
            parts.append("\nBeslut som behöver fattas:")
            for d in context.pending_decisions:
                parts.append(f"- {d}")

        if context.relationships:
            parts.append("\nDina relationer:")
            for rel in context.relationships:
                parts.append(f"- {rel.get('type', '?')}: {rel.get('target_name', '?')}")

        parts.append(
            "\nVad gör du i denna runda? Beskriv dina åtgärder, "
            "kommunikation och eventuella beslut."
        )
        return "\n".join(parts)

    def build_messages(self, context: AgentContext) -> list[SystemMessage | HumanMessage]:
        """Build the full message list for an LLM call."""
        return [
            SystemMessage(content=self.build_system_prompt()),
            HumanMessage(content=self.build_context_prompt(context)),
        ]

    async def act(
        self, state: SimulationState, context: AgentContext, llm: Any
    ) -> AgentMessage:
        """Execute this agent's turn and return a message."""
        messages = self.build_messages(context)
        response = await llm.ainvoke(messages)

        return AgentMessage(
            agent_id=self.agent_id,
            role=self.config.title,
            content=response.content,
            round_number=context.round_number,
            visible_to=[],  # Empty = visible to all by default
        )
