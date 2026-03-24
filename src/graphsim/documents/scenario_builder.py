"""Build simulation scenarios from documents.

Takes a document analysis and generates a complete ScenarioConfig
that can be loaded directly into the orchestrator.
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from graphsim.agents.roles.library import ALL_ROLES, ROLES_BY_DOMAIN
from graphsim.documents.analyzer import DocumentAnalysis
from graphsim.documents.reader import DocumentContent
from graphsim.engine.scenario import ScenarioConfig
from graphsim.engine.templates import EventTrigger


SCENARIO_FROM_DOC_PROMPT = """Du skapar simuleringsscenarier baserade på verkliga dokument.

## Dokumentanalys
Titel: {title}
Typ: {document_type}
Sammanfattning: {summary}
Nyckelpunkter: {key_points}
Beslut: {decisions}
Berörda grupper: {affected_groups}
Risker: {risks}
Simuleringskrokar: {hooks}

## Identifierade stakeholders
{stakeholders}

## Tillgängliga roller i systemet
{role_catalog}

## Uppgift
Skapa ett komplett simuleringscenario baserat på detta dokument.

Svara BARA med giltig JSON:
{{
  "scenario_id": "kort_id",
  "title": "Scenariots titel (baserat på dokumentet)",
  "description": "Detaljerad beskrivning av simuleringen",
  "context": "Organisatorisk kontext",
  "initial_event": "Den utlösande händelsen (t.ex. dokumentet presenteras/beslutet meddelas)",
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
      "initial_knowledge": ["Vad personen vet om dokumentet"]
    }}
  ],
  "relationships": [
    {{
      "source": "role_id_1",
      "target": "role_id_2",
      "relation_type": "reports_to/collaborates_with/has_info_about/lacks_knowledge_of"
    }}
  ],
  "events": [
    {{
      "round_number": 2,
      "description": "Händelse som inträffar",
      "affects_agents": ["role_id"]
    }}
  ]
}}

Gör scenariot RELEVANT för dokumentet. Agenter ska reagera på dokumentets innehåll.
Skapa 6-10 agenter med realistiska roller baserade på stakeholderanalysen.
Inkludera 2-3 händelser som gör simuleringen dynamisk.
Tänk på informationsasymmetri - alla ska INTE veta allt om dokumentet."""


class DocumentScenarioBuilder:
    """Builds simulation scenarios from document analysis."""

    def __init__(self, llm: Any) -> None:
        self._llm = llm

    async def build_scenario(
        self,
        document: DocumentContent,
        analysis: DocumentAnalysis,
        num_rounds: int = 5,
        custom_instructions: str = "",
    ) -> ScenarioConfig:
        """Generate a complete scenario from a document and its analysis."""
        # Build role catalog
        role_catalog_lines = []
        for domain, roles in ROLES_BY_DOMAIN.items():
            role_catalog_lines.append(f"\n### {domain.upper()}")
            for role in roles:
                role_catalog_lines.append(f"- {role.role_id}: {role.title} - {role.description}")
        role_catalog = "\n".join(role_catalog_lines)

        # Build stakeholder text
        stakeholder_lines = []
        for s in analysis.stakeholders:
            stakeholder_lines.append(
                f"- {s.role}: {s.perspective} (inställning: {s.likely_stance}, "
                f"info: {s.information_access})"
            )
        stakeholders_text = "\n".join(stakeholder_lines)

        prompt = SCENARIO_FROM_DOC_PROMPT.format(
            title=analysis.title,
            document_type=analysis.document_type,
            summary=analysis.summary,
            key_points=", ".join(analysis.key_points),
            decisions=", ".join(analysis.decisions_made),
            affected_groups=", ".join(analysis.affected_groups),
            risks=", ".join(analysis.risks_identified),
            hooks=", ".join(analysis.simulation_hooks),
            stakeholders=stakeholders_text,
            role_catalog=role_catalog,
        )

        if custom_instructions:
            prompt += f"\n\nExtra instruktioner: {custom_instructions}"

        messages = [
            SystemMessage(content=prompt),
            HumanMessage(
                content=f"Skapa scenario baserat på dokumentet '{analysis.title}'."
            ),
        ]

        response = await self._llm.ainvoke(messages)
        content = response.content.strip()

        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        data = json.loads(content)

        # Extract events separately (not part of ScenarioConfig)
        events_data = data.pop("events", [])
        data["max_rounds"] = num_rounds

        scenario = ScenarioConfig(**data)

        # Store events for later scheduling
        scenario_events = [
            EventTrigger(
                round_number=e.get("round_number", 1),
                description=e.get("description", ""),
                affects_agents=e.get("affects_agents", []),
                new_information=e.get("new_information", {}),
            )
            for e in events_data
        ]

        # Attach events as metadata for the caller to schedule
        scenario.context = (
            f"{scenario.context}\n\n"
            f"Baserat på dokumentet: {analysis.title}\n"
            f"Dokumenttyp: {analysis.document_type}"
        )

        return scenario, scenario_events
