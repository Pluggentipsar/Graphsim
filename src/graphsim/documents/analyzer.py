"""Document analyzer - uses LLM to extract structured information from documents.

Extracts stakeholders, key decisions, affected groups, risks, and
generates role-specific perspectives for simulation agents.
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from graphsim.documents.reader import DocumentContent


class StakeholderInfo(BaseModel):
    """An identified stakeholder from a document."""

    role: str
    perspective: str
    likely_stance: str  # positive, negative, neutral, mixed
    key_concerns: list[str] = Field(default_factory=list)
    information_access: str = "medium"  # high, medium, low


class DocumentAnalysis(BaseModel):
    """Structured analysis of a document."""

    title: str
    document_type: str  # reform, policy, decision, report, other
    summary: str
    key_points: list[str] = Field(default_factory=list)
    decisions_made: list[str] = Field(default_factory=list)
    affected_groups: list[str] = Field(default_factory=list)
    stakeholders: list[StakeholderInfo] = Field(default_factory=list)
    risks_identified: list[str] = Field(default_factory=list)
    timeline: str = ""
    context: str = ""
    simulation_hooks: list[str] = Field(default_factory=list)


ANALYSIS_PROMPT = """Du är en expert på att analysera offentliga dokument för simuleringsändamål.

Analysera dokumentet och extrahera strukturerad information.

Svara BARA med giltig JSON i detta format:
{
  "title": "Dokumentets titel",
  "document_type": "reform/policy/decision/report/other",
  "summary": "Kort sammanfattning (2-3 meningar)",
  "key_points": ["Nyckelpunkt 1", "Nyckelpunkt 2"],
  "decisions_made": ["Beslut 1", "Beslut 2"],
  "affected_groups": ["Grupp 1", "Grupp 2"],
  "stakeholders": [
    {
      "role": "Rollnamn",
      "perspective": "Hur denna roll ser på dokumentet",
      "likely_stance": "positive/negative/neutral/mixed",
      "key_concerns": ["Oro 1"],
      "information_access": "high/medium/low"
    }
  ],
  "risks_identified": ["Risk 1"],
  "timeline": "Eventuell tidsplan",
  "context": "Vilken kontext dokumentet verkar i",
  "simulation_hooks": [
    "Intressant konflikt att simulera 1",
    "Intressant konflikt att simulera 2"
  ]
}

Identifiera 5-10 relevanta stakeholders/roller.
Fokusera på potentiella konflikter, informationsasymmetrier och beslutskedjor.
Tänk på vad som vore intressant att SIMULERA baserat på dokumentet."""


PERSPECTIVE_PROMPT = """Du är expert på organisationsanalys.

Givet detta dokument och rollen nedan, beskriv:
1. Hur personen i denna roll troligen uppfattar dokumentet
2. Vilka delar som är mest relevanta för denna roll
3. Vad rollen troligen INTE vet eller förstår om dokumentet
4. Vilka handlingar rollen troligen vill ta

Roll: {role_title}
Ansvar: {responsibilities}
Perspektiv: {perspective}

Ge ett kort, rollspecifikt sammandrag av dokumentet (max 200 ord) som denna person
skulle kunna ha fått via sina informationskanaler. INTE hela dokumentet - bara det
denna roll rimligen har tillgång till baserat på sin position och informationsnivå.

Svara BARA med sammandraget, ingen annan text."""


class DocumentAnalyzer:
    """Analyzes documents and generates structured information for simulations."""

    def __init__(self, llm: Any) -> None:
        self._llm = llm

    async def analyze(self, document: DocumentContent) -> DocumentAnalysis:
        """Analyze a document and extract structured information."""
        # Truncate very long documents to fit context
        text = document.text
        if len(text) > 15000:
            text = text[:15000] + "\n\n[Dokumentet fortsätter...]"

        messages = [
            SystemMessage(content=ANALYSIS_PROMPT),
            HumanMessage(content=f"Analysera detta dokument:\n\n{text}"),
        ]

        response = await self._llm.ainvoke(messages)
        content = response.content.strip()

        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        data = json.loads(content)
        return DocumentAnalysis(**data)

    async def generate_role_perspective(
        self,
        document: DocumentContent,
        role_title: str,
        responsibilities: str,
        perspective: str,
        information_level: str = "medium",
    ) -> str:
        """Generate a role-specific summary/perspective of a document.

        This is what the agent actually "knows" about the document,
        filtered through their role and information level.
        """
        # Truncate based on information level
        text = document.text
        max_length = {"high": 10000, "medium": 5000, "low": 2000}.get(
            information_level, 5000
        )
        if len(text) > max_length:
            text = text[:max_length] + "\n\n[...]"

        prompt = PERSPECTIVE_PROMPT.format(
            role_title=role_title,
            responsibilities=responsibilities,
            perspective=perspective,
        )

        messages = [
            SystemMessage(content=prompt),
            HumanMessage(content=f"Dokument:\n\n{text}"),
        ]

        response = await self._llm.ainvoke(messages)
        return response.content.strip()

    async def generate_all_perspectives(
        self,
        document: DocumentContent,
        analysis: DocumentAnalysis,
    ) -> dict[str, str]:
        """Generate role-specific perspectives for all identified stakeholders."""
        perspectives = {}
        for stakeholder in analysis.stakeholders:
            perspective = await self.generate_role_perspective(
                document=document,
                role_title=stakeholder.role,
                responsibilities=", ".join(stakeholder.key_concerns),
                perspective=stakeholder.perspective,
                information_level=stakeholder.information_access,
            )
            perspectives[stakeholder.role] = perspective
        return perspectives
