"""GraphRAG engine - ties together extraction, community detection, and retrieval.

This is the main interface for GraphRAG functionality in Graphsim.
"""

from __future__ import annotations

from typing import Any

import networkx as nx

from graphsim.engine.state import SimulationState
from graphsim.rag.communities import (
    Community,
    CommunityDetectionResult,
    CommunityDetector,
    detect_information_silos,
    find_agent_communities,
)
from graphsim.rag.extractor import (
    KnowledgeGraphExtractor,
    build_knowledge_graph_from_state,
)
from graphsim.rag.store import KnowledgeStore, SimulationArchive


class GraphRAGEngine:
    """Main GraphRAG engine for Graphsim.

    Provides:
    - Knowledge graph extraction from simulations
    - Community detection and summarization
    - Cross-simulation learning via knowledge store
    - Agent context enrichment with precedents and patterns
    """

    def __init__(
        self,
        llm: Any | None = None,
        knowledge_store: KnowledgeStore | None = None,
    ) -> None:
        self._llm = llm
        self._detector = CommunityDetector(llm)
        self._store = knowledge_store or KnowledgeStore()
        self._extractor = KnowledgeGraphExtractor(llm) if llm else None

    @property
    def knowledge_store(self) -> KnowledgeStore:
        return self._store

    def build_knowledge_graph(
        self,
        state: SimulationState,
        use_llm: bool = False,
    ) -> nx.DiGraph:
        """Build a knowledge graph from a simulation state.

        Args:
            state: The simulation state to extract from
            use_llm: If True, use LLM for richer extraction (slower, costs tokens).
                     If False, build from structured data only (fast, free).
        """
        if use_llm and self._extractor:
            import asyncio

            result = asyncio.run(self._extractor.extract(state))
            return self._extractor.to_networkx(result)
        else:
            return build_knowledge_graph_from_state(state)

    def detect_communities(
        self,
        graph: nx.DiGraph,
        resolution: float = 1.0,
        min_size: int = 2,
    ) -> CommunityDetectionResult:
        """Detect communities in a knowledge graph."""
        return self._detector.detect_communities(graph, resolution, min_size)

    async def detect_and_summarize(
        self,
        graph: nx.DiGraph,
        resolution: float = 1.0,
        use_llm: bool = False,
    ) -> CommunityDetectionResult:
        """Detect communities and generate summaries."""
        result = self._detector.detect_communities(graph, resolution)

        if use_llm and self._llm:
            result = await self._detector.summarize_communities(graph, result)
        else:
            result = self._detector.generate_local_summaries(graph, result)

        return result

    def find_silos(
        self,
        graph: nx.DiGraph,
        communities: list[Community],
    ) -> list[dict[str, Any]]:
        """Find information silos between communities."""
        return detect_information_silos(graph, communities)

    def get_agent_context(
        self,
        agent_id: str,
        graph: nx.DiGraph,
        communities: list[Community],
        scenario_title: str = "",
    ) -> str:
        """Build GraphRAG-enhanced context for an agent.

        Returns relevant community summaries and historical precedents.
        """
        parts = []

        # Find relevant communities for this agent
        relevant = find_agent_communities(agent_id, graph, communities)
        if relevant:
            parts.append("Relevanta mönster i detta ärende:")
            for community in relevant[:3]:
                if community.summary:
                    parts.append(f"  - {community.summary}")

        # Find historical precedents
        if scenario_title:
            precedents = self._store.get_precedent_context(scenario_title)
            if precedents:
                parts.append("\nErfarenheter från liknande fall:")
                for precedent in precedents[:2]:
                    parts.append(precedent)

        return "\n".join(parts) if parts else ""

    async def archive_simulation(
        self,
        simulation_id: str,
        state: SimulationState,
        use_llm_extraction: bool = False,
        use_llm_summaries: bool = False,
    ) -> SimulationArchive:
        """Full pipeline: extract KG, detect communities, archive."""
        # Build knowledge graph
        kg = self.build_knowledge_graph(state, use_llm=use_llm_extraction)

        # Detect and summarize communities
        communities = await self.detect_and_summarize(
            kg, use_llm=use_llm_summaries
        )

        # Find silos
        silos = self.find_silos(kg, communities.communities)

        # Archive
        archive = self._store.archive_simulation(
            simulation_id=simulation_id,
            scenario_id=state.scenario_id,
            scenario_title=state.metadata.get("title", state.scenario_id),
            total_rounds=state.current_round + 1,
            total_messages=len(state.messages),
            knowledge_graph=kg,
            communities=communities,
            silos=silos,
        )

        return archive

    def analyze_graph_structure(self, graph: nx.DiGraph) -> dict[str, Any]:
        """Analyze the structure of a knowledge graph."""
        if graph.number_of_nodes() == 0:
            return {"nodes": 0, "edges": 0}

        # Basic stats
        stats: dict[str, Any] = {
            "nodes": graph.number_of_nodes(),
            "edges": graph.number_of_edges(),
            "density": nx.density(graph),
        }

        # Entity type distribution
        type_counts: dict[str, int] = {}
        for _, data in graph.nodes(data=True):
            etype = data.get("entity_type", "unknown")
            type_counts[etype] = type_counts.get(etype, 0) + 1
        stats["entity_types"] = type_counts

        # Relationship type distribution
        rel_counts: dict[str, int] = {}
        for _, _, data in graph.edges(data=True):
            rtype = data.get("relation_type", "unknown")
            rel_counts[rtype] = rel_counts.get(rtype, 0) + 1
        stats["relationship_types"] = rel_counts

        # Most connected nodes
        degree_sorted = sorted(
            graph.nodes(),
            key=lambda n: graph.degree(n),
            reverse=True,
        )
        stats["most_connected"] = [
            {
                "id": n,
                "label": graph.nodes[n].get("label", n),
                "degree": graph.degree(n),
            }
            for n in degree_sorted[:5]
        ]

        # Connected components (treating as undirected)
        undirected = graph.to_undirected()
        components = list(nx.connected_components(undirected))
        stats["connected_components"] = len(components)

        return stats
