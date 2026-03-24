"""Knowledge graph extraction from simulation transcripts.

Uses LLM to extract entities (persons, decisions, events, risks) and
relationships (caused, influenced, blocked, resolved) from completed
simulations, building a structured knowledge graph.
"""

from __future__ import annotations

import json
from typing import Any

import networkx as nx
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from graphsim.engine.state import AgentMessage, SimulationState


class ExtractedEntity(BaseModel):
    """An entity extracted from simulation text."""

    entity_id: str
    entity_type: str  # person, decision, event, risk, action, outcome, information
    label: str
    properties: dict[str, Any] = Field(default_factory=dict)


class ExtractedRelationship(BaseModel):
    """A relationship extracted from simulation text."""

    source_id: str
    target_id: str
    relation_type: str  # caused, influenced, blocked, resolved, informed, escalated, missed
    properties: dict[str, Any] = Field(default_factory=dict)


class ExtractionResult(BaseModel):
    """Result of knowledge graph extraction."""

    entities: list[ExtractedEntity] = Field(default_factory=list)
    relationships: list[ExtractedRelationship] = Field(default_factory=list)


EXTRACTION_PROMPT = """Du är en kunskapsgraf-extraktor. Analysera simuleringstexten och extrahera entiteter och relationer.

## Entitetstyper
- person: En person/roll i simuleringen
- decision: Ett beslut som fattades
- event: En händelse som inträffade
- risk: En risk som identifierades eller uppstod
- action: En konkret åtgärd som genomfördes
- outcome: Ett resultat eller utfall
- information: Viktig information som delades eller saknades

## Relationstyper
- caused: A orsakade B
- influenced: A påverkade B
- blocked: A blockerade/förhindrade B
- resolved: A löste B
- informed: A informerade B
- escalated: A eskalerade till B
- missed: A missade/förbisåg B
- conflicted_with: A stod i konflikt med B
- depended_on: A var beroende av B
- led_to: A ledde till B

## Regler
- Ge varje entitet ett kort, unikt ID (snake_case)
- Extrahera MINST de viktigaste 10-20 entiteterna
- Fokusera på beslutskedjor och orsakssamband
- Identifiera information som SAKNADES eller MISSADES

Svara BARA med giltig JSON:
{
  "entities": [
    {"entity_id": "id", "entity_type": "typ", "label": "Beskrivning", "properties": {}}
  ],
  "relationships": [
    {"source_id": "id1", "target_id": "id2", "relation_type": "typ", "properties": {}}
  ]
}"""


class KnowledgeGraphExtractor:
    """Extracts knowledge graphs from simulation transcripts."""

    def __init__(self, llm: Any) -> None:
        self._llm = llm

    def _build_transcript(self, state: SimulationState) -> str:
        """Build a transcript for extraction."""
        lines = [
            f"SCENARIO: {state.metadata.get('title', state.scenario_id)}",
            f"BESKRIVNING: {state.metadata.get('description', '')}",
            f"UTLÖSANDE HÄNDELSE: {state.metadata.get('initial_event', '')}",
            "",
        ]

        current_round = -1
        for msg in state.messages:
            if msg.round_number != current_round:
                current_round = msg.round_number
                lines.append(f"\n=== RUNDA {current_round} ===")

            if msg.agent_id == "system":
                lines.append(f"[SYSTEMHÄNDELSE] {msg.content}")
            else:
                lines.append(f"[{msg.role} ({msg.agent_id})]: {msg.content}")

        if state.decisions:
            lines.append("\n=== BESLUT ===")
            for d in state.decisions:
                lines.append(f"- {d.made_by}: {d.description}")

        return "\n".join(lines)

    async def extract(self, state: SimulationState) -> ExtractionResult:
        """Extract a knowledge graph from a simulation state."""
        transcript = self._build_transcript(state)

        messages = [
            SystemMessage(content=EXTRACTION_PROMPT),
            HumanMessage(content=f"Extrahera kunskapsgraf från denna simulering:\n\n{transcript}"),
        ]

        response = await self._llm.ainvoke(messages)
        content = response.content.strip()

        # Parse JSON
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        data = json.loads(content)
        return ExtractionResult(**data)

    def extract_sync(self, state: SimulationState) -> ExtractionResult:
        """Synchronous extraction wrapper."""
        import asyncio

        return asyncio.run(self.extract(state))

    def to_networkx(self, result: ExtractionResult) -> nx.DiGraph:
        """Convert extraction result to a NetworkX graph."""
        graph = nx.DiGraph()

        for entity in result.entities:
            graph.add_node(
                entity.entity_id,
                entity_type=entity.entity_type,
                label=entity.label,
                **entity.properties,
            )

        for rel in result.relationships:
            # Only add edge if both nodes exist
            if rel.source_id in graph and rel.target_id in graph:
                graph.add_edge(
                    rel.source_id,
                    rel.target_id,
                    relation_type=rel.relation_type,
                    **rel.properties,
                )

        return graph


def build_knowledge_graph_from_state(
    state: SimulationState,
) -> nx.DiGraph:
    """Build a basic knowledge graph directly from simulation state (no LLM needed).

    This creates a graph from the structured data we already have:
    agents, messages, decisions, and their relationships.
    Useful for community detection without requiring an LLM call.
    """
    graph = nx.DiGraph()

    # Add agent nodes
    for agent_id in state.active_agent_ids:
        graph.add_node(agent_id, entity_type="person", label=agent_id)

    # Add message-based relationships
    for msg in state.messages:
        if msg.agent_id == "system":
            continue

        # Add message as node
        msg_id = f"msg_{msg.agent_id}_{msg.round_number}"
        graph.add_node(
            msg_id,
            entity_type="action",
            label=msg.content[:100],
            round=msg.round_number,
            full_content=msg.content,
        )
        graph.add_edge(msg.agent_id, msg_id, relation_type="performed")

        # Connect to visible agents (information flow)
        if msg.visible_to:
            for target_id in msg.visible_to:
                if target_id != msg.agent_id:
                    graph.add_edge(msg_id, target_id, relation_type="informed")
        else:
            # Visible to all
            for agent_id in state.active_agent_ids:
                if agent_id != msg.agent_id:
                    graph.add_edge(msg_id, agent_id, relation_type="informed")

    # Add decision nodes
    for decision in state.decisions:
        dec_id = f"dec_{decision.decision_id}"
        graph.add_node(
            dec_id,
            entity_type="decision",
            label=decision.description,
            round=decision.round_number,
        )
        graph.add_edge(decision.made_by, dec_id, relation_type="decided")
        for affected in decision.affects:
            if affected in graph:
                graph.add_edge(dec_id, affected, relation_type="affects")

    return graph
