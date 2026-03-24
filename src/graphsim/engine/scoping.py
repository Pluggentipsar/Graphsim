"""Information scoping rules for agent communication.

Controls what each agent can see based on:
- Graph relationships (who has info about whom)
- Secrecy rules (medical, social services, legal)
- Information level (high/medium/low)
- Explicit visibility tags on messages
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from graphsim.engine.state import AgentMessage, SimulationState
from graphsim.graph.models import EdgeType
from graphsim.graph.store import GraphStore


class SecrecyDomain(str, Enum):
    """Types of professional secrecy that restrict information sharing."""

    MEDICAL = "medical"  # Medicinsk sekretess (HSL)
    SOCIAL = "social"  # Socialtjänstsekretess (SoL, OSL)
    SCHOOL = "school"  # Skolsekretess
    LEGAL = "legal"  # Rättslig sekretess
    NONE = "none"  # Ingen sekretess


class SecrecyRule(BaseModel):
    """A secrecy rule that restricts information flow."""

    domain: SecrecyDomain
    holder_roles: list[str] = Field(default_factory=list)
    description: str = ""
    can_share_with: list[str] = Field(default_factory=list)
    requires_consent: bool = False
    override_conditions: list[str] = Field(default_factory=list)


# Standard Swedish professional secrecy rules
DEFAULT_SECRECY_RULES = [
    SecrecyRule(
        domain=SecrecyDomain.MEDICAL,
        holder_roles=["lakare", "sjukskoterska", "skolskoterska", "psykolog"],
        description="Medicinsk sekretess - patientuppgifter får inte delas utan samtycke",
        can_share_with=[],
        requires_consent=True,
        override_conditions=["Fara för liv", "Anmälningsskyldighet barn"],
    ),
    SecrecyRule(
        domain=SecrecyDomain.SOCIAL,
        holder_roles=["socialsekreterare", "enhetschef_soc", "familjebehandlare"],
        description="Socialtjänstsekretess - uppgifter om enskildas personliga förhållanden",
        can_share_with=[],
        requires_consent=True,
        override_conditions=["Barnets bästa", "Samtycke från klient"],
    ),
    SecrecyRule(
        domain=SecrecyDomain.SCHOOL,
        holder_roles=["kurator"],
        description="Stark skolsekretess - elevsamtal och känslig information",
        can_share_with=["rektor"],
        requires_consent=False,
        override_conditions=["Orosanmälan", "Fara för eleven"],
    ),
    SecrecyRule(
        domain=SecrecyDomain.LEGAL,
        holder_roles=["polis"],
        description="Förundersökningssekretess - uppgifter i pågående utredning",
        can_share_with=[],
        requires_consent=False,
        override_conditions=["Pågående fara"],
    ),
]


class InformationLevel(str, Enum):
    """How much general information an agent has access to."""

    HIGH = "high"  # Ser det mesta
    MEDIUM = "medium"  # Ser relevant information
    LOW = "low"  # Ser bara det som direkt berör dem


# Information level controls how many messages are visible
INFO_LEVEL_MESSAGE_WINDOW = {
    InformationLevel.HIGH: 50,
    InformationLevel.MEDIUM: 20,
    InformationLevel.LOW: 10,
}


class InformationScope:
    """Determines what information each agent can access."""

    def __init__(
        self,
        graph: GraphStore,
        secrecy_rules: list[SecrecyRule] | None = None,
    ) -> None:
        self._graph = graph
        self._rules = secrecy_rules or DEFAULT_SECRECY_RULES
        self._secrecy_map: dict[str, list[SecrecyDomain]] = {}
        self._build_secrecy_map()

    def _build_secrecy_map(self) -> None:
        """Map each role to its secrecy domains."""
        for rule in self._rules:
            for role in rule.holder_roles:
                self._secrecy_map.setdefault(role, []).append(rule.domain)

    def get_visible_messages(
        self,
        agent_id: str,
        state: SimulationState,
        information_level: str = "standard",
    ) -> list[AgentMessage]:
        """Get all messages visible to a specific agent, respecting scoping rules."""
        info_level = InformationLevel(information_level) if information_level in [
            e.value for e in InformationLevel
        ] else InformationLevel.MEDIUM
        window = INFO_LEVEL_MESSAGE_WINDOW[info_level]

        visible = []
        for msg in state.messages:
            if self._can_see_message(agent_id, msg):
                visible.append(msg)

        # Apply window limit
        return visible[-window:]

    def _can_see_message(self, agent_id: str, message: AgentMessage) -> bool:
        """Check if an agent can see a specific message."""
        # Own messages are always visible
        if message.agent_id == agent_id:
            return True

        # Explicit visibility list
        if message.visible_to:
            return agent_id in message.visible_to

        # System/event messages without visibility restrictions
        if message.agent_id == "system" and not message.visible_to:
            return True

        # Check secrecy rules
        sender_secrecy = self._get_secrecy_domains(message.agent_id)
        if sender_secrecy:
            # Sender has secrecy - check if receiver is allowed
            for domain in sender_secrecy:
                rule = self._get_rule(domain)
                if rule and agent_id not in rule.can_share_with:
                    # Check if there's a graph relationship that allows sharing
                    if not self._has_info_relationship(message.agent_id, agent_id):
                        return False

        # Check graph-based information access
        if self._has_info_relationship(message.agent_id, agent_id):
            return True

        # Check if they collaborate
        neighbors = self._graph.get_neighbors(agent_id)
        for neighbor in neighbors:
            if neighbor.node_id == message.agent_id:
                return True

        # Default: visible (for agents without secrecy)
        return True

    def _get_secrecy_domains(self, agent_id: str) -> list[SecrecyDomain]:
        """Get secrecy domains for an agent."""
        return self._secrecy_map.get(agent_id, [])

    def _get_rule(self, domain: SecrecyDomain) -> SecrecyRule | None:
        """Get the rule for a specific secrecy domain."""
        for rule in self._rules:
            if rule.domain == domain:
                return rule
        return None

    def _has_info_relationship(self, source_id: str, target_id: str) -> bool:
        """Check if source has an information-sharing relationship with target."""
        neighbors = self._graph.get_neighbors(source_id, EdgeType.HAS_INFO_ABOUT)
        return any(n.node_id == target_id for n in neighbors)

    def get_secrecy_prompt(self, agent_id: str) -> str:
        """Get a prompt section describing the agent's secrecy obligations."""
        domains = self._get_secrecy_domains(agent_id)
        if not domains:
            return ""

        parts = ["\nSekretessregler du måste följa:"]
        for domain in domains:
            rule = self._get_rule(domain)
            if rule:
                parts.append(f"- {rule.description}")
                if rule.override_conditions:
                    parts.append(
                        f"  Undantag: {', '.join(rule.override_conditions)}"
                    )

        return "\n".join(parts)
