#!/usr/bin/env python3
"""Run a Graphsim simulation from the command line."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from graphsim.analysis.analyzer import SimulationAnalyzer
from graphsim.config import SimulationConfig
from graphsim.orchestrator import Orchestrator


async def main(scenario_path: str, analyze: bool = True) -> None:
    config = SimulationConfig()
    orchestrator = Orchestrator(config)
    orchestrator.load_scenario(scenario_path)

    state = await orchestrator.run()

    if analyze:
        print("\n=== ANALYS ===\n")
        analyzer = SimulationAnalyzer(orchestrator._get_llm())
        analysis = await analyzer.analyze(state)
        print(analysis)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Kör en Graphsim-simulering")
    parser.add_argument(
        "--scenario",
        type=str,
        default="scenarios/example_school.yaml",
        help="Sökväg till scenario-YAML",
    )
    parser.add_argument(
        "--no-analysis",
        action="store_true",
        help="Hoppa över analyssteget",
    )
    args = parser.parse_args()

    asyncio.run(main(args.scenario, analyze=not args.no_analysis))
