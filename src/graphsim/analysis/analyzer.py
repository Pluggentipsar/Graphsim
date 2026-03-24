"""Post-simulation analysis with structured output."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from graphsim.engine.state import SimulationState


class ConflictPoint(BaseModel):
    """An identified conflict between agents or goals."""

    agents_involved: list[str]
    description: str
    severity: str = "medium"  # low, medium, high
    round_number: int | None = None


class InformationGap(BaseModel):
    """Missing or unshared information that affected the outcome."""

    who_lacked: str
    what_was_missing: str
    impact: str
    could_have_been_shared_by: str = ""


class DecisionAssessment(BaseModel):
    """Assessment of a decision made during the simulation."""

    decision: str
    made_by: str
    assessment: str  # reasonable, risky, problematic
    reasoning: str
    alternatives: list[str] = Field(default_factory=list)


class SystemicPattern(BaseModel):
    """A systemic pattern identified in the simulation."""

    pattern: str
    evidence: str
    recommendation: str


class AnalysisResult(BaseModel):
    """Structured analysis result from a completed simulation."""

    summary: str
    conflicts: list[ConflictPoint] = Field(default_factory=list)
    information_gaps: list[InformationGap] = Field(default_factory=list)
    decision_assessments: list[DecisionAssessment] = Field(default_factory=list)
    systemic_patterns: list[SystemicPattern] = Field(default_factory=list)
    key_insights: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    overall_risk_level: str = "medium"  # low, medium, high, critical


ANALYSIS_SYSTEM_PROMPT = """Du är en analysagent som utvärderar simuleringar av organisatoriska scenarier.

Analysera simuleringen och producera en STRUKTURERAD analys.

Du MÅSTE svara med ENBART giltig JSON i följande format:
{
  "summary": "Kort sammanfattning av simuleringen (2-3 meningar)",
  "conflicts": [
    {
      "agents_involved": ["roll_id_1", "roll_id_2"],
      "description": "Beskrivning av konflikten",
      "severity": "low/medium/high",
      "round_number": 1
    }
  ],
  "information_gaps": [
    {
      "who_lacked": "roll_id",
      "what_was_missing": "Vilken information saknades",
      "impact": "Hur påverkade det utfallet",
      "could_have_been_shared_by": "roll_id"
    }
  ],
  "decision_assessments": [
    {
      "decision": "Vad beslutades",
      "made_by": "roll_id",
      "assessment": "reasonable/risky/problematic",
      "reasoning": "Varför bedömningen",
      "alternatives": ["Alternativ 1"]
    }
  ],
  "systemic_patterns": [
    {
      "pattern": "Mönsterbeskrivning",
      "evidence": "Belägg från simuleringen",
      "recommendation": "Förbättringsförslag"
    }
  ],
  "key_insights": ["Insikt 1", "Insikt 2"],
  "recommendations": ["Rekommendation 1"],
  "overall_risk_level": "low/medium/high/critical"
}

Var konkret. Referera till specifika händelser och roller.
Svara BARA med JSON, ingen annan text."""


class SimulationAnalyzer:
    """Analyzes a completed simulation and produces structured insights."""

    def __init__(self, llm: Any) -> None:
        self._llm = llm

    def _build_transcript(self, state: SimulationState) -> str:
        """Build a readable transcript of the simulation."""
        lines = [
            f"Scenario: {state.metadata.get('title', state.scenario_id)}",
            f"Beskrivning: {state.metadata.get('description', '')}",
            f"Antal rundor: {state.current_round + 1}",
            f"Antal meddelanden: {len(state.messages)}",
            "",
            "=== TRANSKRIPTION ===",
        ]

        current_round = -1
        for msg in state.messages:
            if msg.round_number != current_round:
                current_round = msg.round_number
                lines.append(f"\n--- Runda {current_round} ---")
            lines.append(f"[{msg.role} ({msg.agent_id})]: {msg.content}")

        if state.decisions:
            lines.append("\n=== BESLUT ===")
            for decision in state.decisions:
                lines.append(
                    f"- {decision.made_by}: {decision.description} "
                    f"(Påverkar: {', '.join(decision.affects)})"
                )

        return "\n".join(lines)

    async def analyze(self, state: SimulationState) -> AnalysisResult:
        """Run structured analysis on a completed simulation state."""
        transcript = self._build_transcript(state)

        messages = [
            SystemMessage(content=ANALYSIS_SYSTEM_PROMPT),
            HumanMessage(content=f"Analysera följande simulering:\n\n{transcript}"),
        ]

        response = await self._llm.ainvoke(messages)
        content = response.content.strip()

        # Extrahera JSON
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        data = json.loads(content)
        return AnalysisResult(**data)

    async def analyze_plain_text(self, state: SimulationState) -> str:
        """Run analysis and return as formatted text (for CLI/simple output)."""
        result = await self.analyze(state)
        return self._format_result(result)

    def _format_result(self, result: AnalysisResult) -> str:
        """Format an AnalysisResult as readable text."""
        lines = [
            "=" * 60,
            "SIMULERINGSANALYS",
            "=" * 60,
            "",
            f"Sammanfattning: {result.summary}",
            f"Övergripande risknivå: {result.overall_risk_level.upper()}",
            "",
        ]

        if result.conflicts:
            lines.append("--- KONFLIKTER ---")
            for c in result.conflicts:
                lines.append(
                    f"  [{c.severity.upper()}] {c.description} "
                    f"(Involverade: {', '.join(c.agents_involved)})"
                )
            lines.append("")

        if result.information_gaps:
            lines.append("--- INFORMATIONSLUCKOR ---")
            for g in result.information_gaps:
                lines.append(f"  {g.who_lacked} saknade: {g.what_was_missing}")
                lines.append(f"    Påverkan: {g.impact}")
                if g.could_have_been_shared_by:
                    lines.append(f"    Kunde delats av: {g.could_have_been_shared_by}")
            lines.append("")

        if result.decision_assessments:
            lines.append("--- BESLUTSBEDÖMNINGAR ---")
            for d in result.decision_assessments:
                lines.append(f"  [{d.assessment.upper()}] {d.decision} (av {d.made_by})")
                lines.append(f"    {d.reasoning}")
                if d.alternatives:
                    lines.append(f"    Alternativ: {', '.join(d.alternatives)}")
            lines.append("")

        if result.systemic_patterns:
            lines.append("--- SYSTEMISKA MÖNSTER ---")
            for p in result.systemic_patterns:
                lines.append(f"  Mönster: {p.pattern}")
                lines.append(f"    Belägg: {p.evidence}")
                lines.append(f"    Rekommendation: {p.recommendation}")
            lines.append("")

        if result.key_insights:
            lines.append("--- NYCKELINSIKTER ---")
            for i, insight in enumerate(result.key_insights, 1):
                lines.append(f"  {i}. {insight}")
            lines.append("")

        if result.recommendations:
            lines.append("--- REKOMMENDATIONER ---")
            for i, rec in enumerate(result.recommendations, 1):
                lines.append(f"  {i}. {rec}")

        return "\n".join(lines)
