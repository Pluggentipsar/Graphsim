"""Natural language scenario builder.

Users describe a scenario in plain Swedish/English and an LLM
generates a complete ScenarioConfig with roles, relationships,
events, and decision points.
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from graphsim.agents.roles.library import ALL_ROLES, ROLES_BY_DOMAIN
from graphsim.engine.scenario import AgentRoleConfig, RelationshipConfig, ScenarioConfig

BUILDER_SYSTEM_PROMPT = """Du är en scenariobyggare för Graphsim, ett simuleringsverktyg för organisatoriska scenarier.

Din uppgift är att ta en fri textbeskrivning av en situation och skapa ett komplett simuleringscenario.

## Tillgängliga roller per domän:
{role_catalog}

## Tillgängliga relationstyper:
- reports_to: rapporterar till (hierarki)
- collaborates_with: samarbetar med
- has_info_about: har information om
- affects: påverkar
- participated_in: deltog i
- responsible_for: ansvarar för
- lacks_knowledge_of: saknar kännedom om

## Du MÅSTE svara med ENBART giltig JSON i följande format:
{{
  "scenario_id": "kort_id",
  "title": "Scenariots titel",
  "description": "Detaljerad beskrivning",
  "context": "Kontextbeskrivning (typ av organisation, storlek, etc)",
  "initial_event": "Den utlösande händelsen",
  "max_rounds": 5,
  "decision_points": ["Beslutspunkt 1", "Beslutspunkt 2"],
  "agents": [
    {{
      "role_id": "unikt_id",
      "name": "Namn Efternamn",
      "title": "Titel",
      "responsibilities": ["Ansvar 1"],
      "goals": ["Mål 1"],
      "constraints": ["Begränsning 1"],
      "information_level": "high/medium/low",
      "personality": "Personlighetsbeskrivning",
      "initial_knowledge": ["Vad personen vet från start"]
    }}
  ],
  "relationships": [
    {{
      "source": "role_id_1",
      "target": "role_id_2",
      "relation_type": "reports_to"
    }}
  ]
}}

Välj 6-12 relevanta roller. Ge dem svenska namn. Skapa realistiska relationer.
Tänk på informationsasymmetri - alla ska INTE veta allt.
Svara BARA med JSON, ingen annan text."""


def _build_role_catalog() -> str:
    """Build a text catalog of available roles for the prompt."""
    lines = []
    for domain, roles in ROLES_BY_DOMAIN.items():
        lines.append(f"\n### {domain.upper()}")
        for role in roles:
            lines.append(f"- {role.role_id}: {role.title} - {role.description}")
    return "\n".join(lines)


class ScenarioBuilder:
    """Builds simulation scenarios from natural language descriptions."""

    def __init__(self, llm: Any) -> None:
        self._llm = llm

    async def build_from_description(
        self,
        description: str,
        num_agents: int = 8,
        num_rounds: int = 5,
        domain_hint: str | None = None,
    ) -> ScenarioConfig:
        """Generate a complete scenario from a natural language description."""
        role_catalog = _build_role_catalog()
        system_prompt = BUILDER_SYSTEM_PROMPT.format(role_catalog=role_catalog)

        user_prompt_parts = [
            f"Skapa ett simuleringscenario baserat på denna beskrivning:\n\n{description}",
            f"\nAntal agenter: ungefär {num_agents}",
            f"Antal rundor: {num_rounds}",
        ]
        if domain_hint:
            user_prompt_parts.append(f"Domän: {domain_hint}")

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content="\n".join(user_prompt_parts)),
        ]

        response = await self._llm.ainvoke(messages)
        content = response.content.strip()

        # Extrahera JSON från svaret (hantera eventuell markdown-wrapping)
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        data = json.loads(content)

        # Överskriv med användarens val om angivet
        data["max_rounds"] = num_rounds

        return ScenarioConfig(**data)

    async def suggest_roles(
        self, description: str, max_suggestions: int = 10
    ) -> list[dict[str, Any]]:
        """Suggest relevant roles from the library for a given scenario description."""
        messages = [
            SystemMessage(
                content=(
                    "Du är en expert på organisatoriska scenarier. "
                    "Givet en situationsbeskrivning, välj de mest relevanta rollerna "
                    "från listan nedan. Svara med en JSON-lista av role_id:n.\n\n"
                    f"Tillgängliga roller:\n{_build_role_catalog()}\n\n"
                    "Svara BARA med JSON: [\"role_id_1\", \"role_id_2\", ...]"
                )
            ),
            HumanMessage(content=description),
        ]

        response = await self._llm.ainvoke(messages)
        content = response.content.strip()
        if "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
            if content.startswith("json"):
                content = content[4:].strip()

        role_ids = json.loads(content)

        suggestions = []
        for role_id in role_ids[:max_suggestions]:
            for role in ALL_ROLES:
                if role.role_id == role_id:
                    suggestions.append({
                        "role_id": role.role_id,
                        "name": role.name,
                        "title": role.title,
                        "domain": role.domain,
                        "description": role.description,
                    })
                    break

        return suggestions
