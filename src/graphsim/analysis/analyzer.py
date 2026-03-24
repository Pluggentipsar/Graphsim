"""Post-simulation analysis agent."""

from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from graphsim.engine.state import SimulationState


ANALYSIS_SYSTEM_PROMPT = """Du är en analysagent som utvärderar simuleringar av organisatoriska scenarier.

Din uppgift är att analysera en avslutad simulering och sammanfatta:
1. Var konflikter uppstod mellan roller
2. Vilken information som saknades eller inte delades
3. Vilka mål som kolliderade
4. Vilka beslut som blev rimliga eller riskabla
5. Systemiska mönster och förbättringsförslag

Var konkret och referera till specifika händelser i simuleringen."""


class SimulationAnalyzer:
    """Analyzes a completed simulation and produces insights."""

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

    async def analyze(self, state: SimulationState) -> str:
        """Run analysis on a completed simulation state."""
        transcript = self._build_transcript(state)

        messages = [
            SystemMessage(content=ANALYSIS_SYSTEM_PROMPT),
            HumanMessage(content=f"Analysera följande simulering:\n\n{transcript}"),
        ]

        response = await self._llm.ainvoke(messages)
        return response.content

    def analyze_sync(self, state: SimulationState) -> str:
        """Synchronous wrapper for analysis."""
        import asyncio

        return asyncio.run(self.analyze(state))
