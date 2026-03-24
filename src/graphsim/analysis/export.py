"""Export simulation results as structured reports.

Supports Markdown and JSON export formats.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from graphsim.analysis.analyzer import AnalysisResult
from graphsim.engine.comparison import ComparisonResult
from graphsim.engine.state import SimulationState


class ReportExporter:
    """Exports simulation results in various formats."""

    def to_markdown(
        self,
        state: SimulationState,
        analysis: AnalysisResult | None = None,
    ) -> str:
        """Export a simulation as a Markdown report."""
        lines = [
            f"# Simuleringsrapport: {state.metadata.get('title', state.scenario_id)}",
            "",
            f"**Datum:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"**Scenario:** {state.scenario_id}",
            f"**Antal rundor:** {state.current_round + 1}",
            f"**Antal meddelanden:** {len(state.messages)}",
            f"**Antal agenter:** {len(state.active_agent_ids)}",
            "",
        ]

        # Description
        if state.metadata.get("description"):
            lines.extend([
                "## Scenariobeskrivning",
                "",
                state.metadata["description"],
                "",
            ])

        # Initial event
        if state.metadata.get("initial_event"):
            lines.extend([
                "## Utlösande händelse",
                "",
                state.metadata["initial_event"],
                "",
            ])

        # Transcript
        lines.extend(["## Simuleringsförlopp", ""])
        current_round = -1
        for msg in state.messages:
            if msg.round_number != current_round:
                current_round = msg.round_number
                lines.extend([f"### Runda {current_round}", ""])

            if msg.agent_id == "system":
                lines.append(f"> **{msg.content}**")
            else:
                lines.append(f"**{msg.role}** ({msg.agent_id}):")
                lines.extend([
                    "",
                    msg.content,
                    "",
                    "---",
                    "",
                ])

        # Decisions
        if state.decisions:
            lines.extend(["## Beslut", ""])
            for d in state.decisions:
                lines.append(f"- **{d.made_by}**: {d.description}")
                if d.rationale:
                    lines.append(f"  - Motivering: {d.rationale}")
                if d.affects:
                    lines.append(f"  - Påverkar: {', '.join(d.affects)}")
            lines.append("")

        # Analysis
        if analysis:
            lines.extend(self._format_analysis_markdown(analysis))

        return "\n".join(lines)

    def _format_analysis_markdown(self, analysis: AnalysisResult) -> list[str]:
        """Format analysis result as Markdown sections."""
        lines = [
            "## Analys",
            "",
            f"**Sammanfattning:** {analysis.summary}",
            "",
            f"**Övergripande risknivå:** {analysis.overall_risk_level.upper()}",
            "",
        ]

        if analysis.conflicts:
            lines.extend(["### Konflikter", ""])
            for c in analysis.conflicts:
                severity_icon = {"low": "🟡", "medium": "🟠", "high": "🔴"}.get(
                    c.severity, "⚪"
                )
                lines.append(
                    f"- {severity_icon} **{c.severity.upper()}**: {c.description} "
                    f"(Involverade: {', '.join(c.agents_involved)})"
                )
            lines.append("")

        if analysis.information_gaps:
            lines.extend(["### Informationsluckor", ""])
            for g in analysis.information_gaps:
                lines.append(f"- **{g.who_lacked}** saknade: {g.what_was_missing}")
                lines.append(f"  - Påverkan: {g.impact}")
                if g.could_have_been_shared_by:
                    lines.append(f"  - Kunde delats av: {g.could_have_been_shared_by}")
            lines.append("")

        if analysis.decision_assessments:
            lines.extend(["### Beslutsbedömningar", ""])
            for d in analysis.decision_assessments:
                badge = {
                    "reasonable": "✅", "risky": "⚠️", "problematic": "❌"
                }.get(d.assessment, "❓")
                lines.append(f"- {badge} **{d.decision}** (av {d.made_by})")
                lines.append(f"  - {d.reasoning}")
                if d.alternatives:
                    lines.append(f"  - Alternativ: {', '.join(d.alternatives)}")
            lines.append("")

        if analysis.systemic_patterns:
            lines.extend(["### Systemiska mönster", ""])
            for p in analysis.systemic_patterns:
                lines.append(f"- **{p.pattern}**")
                lines.append(f"  - Belägg: {p.evidence}")
                lines.append(f"  - Rekommendation: {p.recommendation}")
            lines.append("")

        if analysis.key_insights:
            lines.extend(["### Nyckelinsikter", ""])
            for i, insight in enumerate(analysis.key_insights, 1):
                lines.append(f"{i}. {insight}")
            lines.append("")

        if analysis.recommendations:
            lines.extend(["### Rekommendationer", ""])
            for i, rec in enumerate(analysis.recommendations, 1):
                lines.append(f"{i}. {rec}")
            lines.append("")

        return lines

    def to_json(
        self,
        state: SimulationState,
        analysis: AnalysisResult | None = None,
    ) -> str:
        """Export a simulation as a JSON report."""
        report: dict[str, Any] = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "scenario_id": state.scenario_id,
                "title": state.metadata.get("title", ""),
                "description": state.metadata.get("description", ""),
                "total_rounds": state.current_round + 1,
                "total_messages": len(state.messages),
                "total_agents": len(state.active_agent_ids),
            },
            "rounds": {},
            "decisions": [d.model_dump() for d in state.decisions],
        }

        # Group messages by round
        for msg in state.messages:
            round_key = str(msg.round_number)
            if round_key not in report["rounds"]:
                report["rounds"][round_key] = []
            report["rounds"][round_key].append(msg.model_dump())

        if analysis:
            report["analysis"] = analysis.model_dump()

        return json.dumps(report, ensure_ascii=False, indent=2)

    def comparison_to_markdown(self, comparison: ComparisonResult) -> str:
        """Export a comparison result as Markdown."""
        lines = [
            f"# Jämförelserapport: {comparison.scenario_title}",
            "",
            f"**Datum:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"**Antal varianter:** {len(comparison.variants)}",
            "",
        ]

        # Summary table
        lines.extend([
            "## Översikt",
            "",
            "| Variant | Rundor | Meddelanden | Risknivå | Konflikter |",
            "|---------|--------|-------------|----------|------------|",
        ])

        for v in comparison.variants:
            risk = v.analysis.overall_risk_level if v.analysis else "N/A"
            conflicts = len(v.analysis.conflicts) if v.analysis else "N/A"
            lines.append(
                f"| {v.label} | {v.state.current_round + 1} | "
                f"{len(v.state.messages)} | {risk} | {conflicts} |"
            )
        lines.append("")

        # Detailed results per variant
        for v in comparison.variants:
            lines.extend([
                f"## Variant: {v.label}",
                "",
            ])
            if v.analysis:
                lines.append(f"**Sammanfattning:** {v.analysis.summary}")
                lines.append("")

                if v.analysis.key_insights:
                    lines.append("**Nyckelinsikter:**")
                    for insight in v.analysis.key_insights:
                        lines.append(f"- {insight}")
                    lines.append("")

                if v.analysis.recommendations:
                    lines.append("**Rekommendationer:**")
                    for rec in v.analysis.recommendations:
                        lines.append(f"- {rec}")
                    lines.append("")

        if comparison.comparison_summary:
            lines.extend([
                "## Jämförelsesammanfattning",
                "",
                comparison.comparison_summary,
            ])

        return "\n".join(lines)
