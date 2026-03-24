"""Comparison mode - run the same scenario with different configurations.

Allows users to compare outcomes when agent traits differ,
e.g., "What happens if the principal is change-resistant vs. a maverick?"
"""

from __future__ import annotations

import copy
from typing import Any

from pydantic import BaseModel, Field

from graphsim.analysis.analyzer import AnalysisResult, SimulationAnalyzer
from graphsim.config import SimulationConfig
from graphsim.engine.scenario import ScenarioConfig
from graphsim.engine.state import SimulationState
from graphsim.orchestrator import Orchestrator


class VariantConfig(BaseModel):
    """Configuration for one variant of a comparison run."""

    variant_id: str
    label: str
    description: str = ""
    trait_overrides: dict[str, dict[str, float]] = Field(default_factory=dict)
    personality_overrides: dict[str, str] = Field(default_factory=dict)


class VariantResult(BaseModel):
    """Result from running a single variant."""

    variant_id: str
    label: str
    state: SimulationState
    analysis: AnalysisResult | None = None


class ComparisonResult(BaseModel):
    """Complete comparison between multiple simulation variants."""

    scenario_title: str
    variants: list[VariantResult] = Field(default_factory=list)
    comparison_summary: str = ""


class ComparisonRunner:
    """Runs the same scenario with different configurations and compares results."""

    def __init__(self, config: SimulationConfig | None = None) -> None:
        self.config = config or SimulationConfig()

    async def run_comparison(
        self,
        scenario: ScenarioConfig,
        variants: list[VariantConfig],
        analyze: bool = True,
    ) -> ComparisonResult:
        """Run multiple variants of the same scenario and compare results."""
        results = []

        for variant in variants:
            modified_scenario = self._apply_variant(scenario, variant)
            orchestrator = Orchestrator(self.config)
            orchestrator.load_scenario(modified_scenario)

            state = await orchestrator.run()

            analysis = None
            if analyze:
                analyzer = SimulationAnalyzer(orchestrator._get_llm())
                analysis = await analyzer.analyze(state)

            results.append(VariantResult(
                variant_id=variant.variant_id,
                label=variant.label,
                state=state,
                analysis=analysis,
            ))

        comparison = ComparisonResult(
            scenario_title=scenario.title,
            variants=results,
        )

        if analyze and len(results) >= 2:
            comparison.comparison_summary = self._generate_comparison_summary(results)

        return comparison

    def _apply_variant(
        self, scenario: ScenarioConfig, variant: VariantConfig
    ) -> ScenarioConfig:
        """Apply variant overrides to a scenario config."""
        modified = scenario.model_copy(deep=True)

        for agent in modified.agents:
            # Apply trait overrides
            if agent.role_id in variant.trait_overrides:
                trait_values = variant.trait_overrides[agent.role_id]
                from graphsim.agents.traits import TraitProfile

                profile = TraitProfile(traits=trait_values)
                trait_desc = profile.to_prompt_description()
                if agent.personality:
                    agent.personality = f"{agent.personality}\n{trait_desc}"
                else:
                    agent.personality = trait_desc

            # Apply personality overrides
            if agent.role_id in variant.personality_overrides:
                agent.personality = variant.personality_overrides[agent.role_id]

        return modified

    def _generate_comparison_summary(self, results: list[VariantResult]) -> str:
        """Generate a text summary comparing variant results."""
        lines = ["=== JÄMFÖRELSEANALYS ===\n"]

        for result in results:
            lines.append(f"Variant: {result.label}")
            lines.append(f"  Meddelanden: {len(result.state.messages)}")
            lines.append(f"  Rundor: {result.state.current_round + 1}")
            if result.analysis:
                lines.append(f"  Risknivå: {result.analysis.overall_risk_level}")
                lines.append(f"  Konflikter: {len(result.analysis.conflicts)}")
                lines.append(f"  Informationsluckor: {len(result.analysis.information_gaps)}")
            lines.append("")

        # Simple comparison metrics
        if all(r.analysis for r in results):
            lines.append("--- Jämförelse ---")
            risk_levels = {
                r.label: r.analysis.overall_risk_level
                for r in results if r.analysis
            }
            conflict_counts = {
                r.label: len(r.analysis.conflicts)
                for r in results if r.analysis
            }
            lines.append(f"Risknivåer: {risk_levels}")
            lines.append(f"Antal konflikter: {conflict_counts}")

            # Highlight key differences in insights
            all_insights = {}
            for r in results:
                if r.analysis:
                    all_insights[r.label] = set(r.analysis.key_insights)

            if len(all_insights) >= 2:
                labels = list(all_insights.keys())
                unique_to_first = all_insights[labels[0]] - all_insights[labels[1]]
                unique_to_second = all_insights[labels[1]] - all_insights[labels[0]]

                if unique_to_first:
                    lines.append(f"\nUnikt för '{labels[0]}':")
                    for insight in unique_to_first:
                        lines.append(f"  - {insight}")
                if unique_to_second:
                    lines.append(f"\nUnikt för '{labels[1]}':")
                    for insight in unique_to_second:
                        lines.append(f"  - {insight}")

        return "\n".join(lines)
