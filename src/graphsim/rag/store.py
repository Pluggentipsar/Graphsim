"""Cross-simulation knowledge store.

Persists knowledge graphs and community analyses from completed
simulations. Enables cross-simulation learning by querying patterns
and precedents from past runs.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import networkx as nx
from networkx.readwrite import json_graph
from pydantic import BaseModel, Field

from graphsim.rag.communities import Community, CommunityDetectionResult


class SimulationArchive(BaseModel):
    """Archived data from a completed simulation."""

    simulation_id: str
    scenario_id: str
    scenario_title: str
    total_rounds: int
    total_messages: int
    communities: list[Community] = Field(default_factory=list)
    silos: list[dict[str, Any]] = Field(default_factory=list)
    key_patterns: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class KnowledgeStore:
    """Persistent store for cross-simulation knowledge.

    Stores archived simulations with their knowledge graphs and
    community analyses. Supports querying for patterns and precedents.
    """

    def __init__(self, storage_dir: str | Path | None = None) -> None:
        self._archives: dict[str, SimulationArchive] = {}
        self._graphs: dict[str, nx.DiGraph] = {}
        self._storage_dir = Path(storage_dir) if storage_dir else None
        if self._storage_dir:
            self._storage_dir.mkdir(parents=True, exist_ok=True)
            self._load_from_disk()

    def archive_simulation(
        self,
        simulation_id: str,
        scenario_id: str,
        scenario_title: str,
        total_rounds: int,
        total_messages: int,
        knowledge_graph: nx.DiGraph,
        communities: CommunityDetectionResult,
        silos: list[dict[str, Any]] | None = None,
    ) -> SimulationArchive:
        """Archive a completed simulation with its knowledge graph."""
        # Extract key patterns from communities
        key_patterns = []
        for community in communities.communities:
            if community.summary:
                key_patterns.append(community.summary)

        archive = SimulationArchive(
            simulation_id=simulation_id,
            scenario_id=scenario_id,
            scenario_title=scenario_title,
            total_rounds=total_rounds,
            total_messages=total_messages,
            communities=communities.communities,
            silos=silos or [],
            key_patterns=key_patterns,
            metadata={
                "total_communities": communities.total_communities,
                "modularity": communities.modularity,
                "kg_nodes": knowledge_graph.number_of_nodes(),
                "kg_edges": knowledge_graph.number_of_edges(),
            },
        )

        self._archives[simulation_id] = archive
        self._graphs[simulation_id] = knowledge_graph

        if self._storage_dir:
            self._save_to_disk(simulation_id)

        return archive

    def get_archive(self, simulation_id: str) -> SimulationArchive | None:
        return self._archives.get(simulation_id)

    def get_knowledge_graph(self, simulation_id: str) -> nx.DiGraph | None:
        return self._graphs.get(simulation_id)

    def list_archives(self) -> list[SimulationArchive]:
        return list(self._archives.values())

    def find_similar_scenarios(
        self, scenario_title: str, tags: list[str] | None = None
    ) -> list[SimulationArchive]:
        """Find archived simulations with similar scenarios."""
        title_lower = scenario_title.lower()
        results = []

        for archive in self._archives.values():
            score = 0

            # Title similarity (simple word overlap)
            archive_words = set(archive.scenario_title.lower().split())
            query_words = set(title_lower.split())
            common = archive_words & query_words
            if common:
                score += len(common) / max(len(archive_words), len(query_words))

            # Scenario ID match
            if archive.scenario_id in title_lower or title_lower in archive.scenario_id:
                score += 0.5

            if score > 0.1:
                results.append((score, archive))

        results.sort(key=lambda x: x[0], reverse=True)
        return [archive for _, archive in results]

    def get_precedent_context(
        self, scenario_title: str, max_precedents: int = 3
    ) -> list[str]:
        """Get relevant precedent summaries for a new simulation."""
        similar = self.find_similar_scenarios(scenario_title)[:max_precedents]

        precedents = []
        for archive in similar:
            parts = [f"Liknande fall: {archive.scenario_title}"]
            parts.append(f"({archive.total_rounds} rundor, {archive.total_messages} meddelanden)")

            if archive.key_patterns:
                parts.append("Mönster:")
                for pattern in archive.key_patterns[:3]:
                    parts.append(f"  - {pattern}")

            if archive.silos:
                parts.append("Identifierade silos:")
                for silo in archive.silos[:2]:
                    parts.append(f"  - {silo.get('description', '')}")

            precedents.append("\n".join(parts))

        return precedents

    def get_all_patterns(self) -> list[str]:
        """Get all key patterns from all archived simulations."""
        patterns = []
        for archive in self._archives.values():
            for pattern in archive.key_patterns:
                patterns.append(f"[{archive.scenario_title}] {pattern}")
        return patterns

    def _save_to_disk(self, simulation_id: str) -> None:
        """Save an archive and its graph to disk."""
        if not self._storage_dir:
            return

        archive = self._archives[simulation_id]
        graph = self._graphs[simulation_id]

        # Save archive metadata
        archive_path = self._storage_dir / f"{simulation_id}_archive.json"
        with archive_path.open("w", encoding="utf-8") as f:
            json.dump(archive.model_dump(), f, ensure_ascii=False, indent=2)

        # Save graph
        graph_path = self._storage_dir / f"{simulation_id}_graph.json"
        graph_data = json_graph.node_link_data(graph)
        with graph_path.open("w", encoding="utf-8") as f:
            json.dump(graph_data, f, ensure_ascii=False, indent=2)

    def _load_from_disk(self) -> None:
        """Load all archives from disk."""
        if not self._storage_dir or not self._storage_dir.exists():
            return

        for archive_path in self._storage_dir.glob("*_archive.json"):
            sim_id = archive_path.stem.replace("_archive", "")
            try:
                with archive_path.open(encoding="utf-8") as f:
                    data = json.load(f)
                self._archives[sim_id] = SimulationArchive(**data)

                graph_path = self._storage_dir / f"{sim_id}_graph.json"
                if graph_path.exists():
                    with graph_path.open(encoding="utf-8") as f:
                        graph_data = json.load(f)
                    self._graphs[sim_id] = json_graph.node_link_graph(graph_data)
            except (json.JSONDecodeError, ValueError):
                continue

    @property
    def archive_count(self) -> int:
        return len(self._archives)
