"""Community detection and hierarchical summarization.

Identifies clusters of related entities in the knowledge graph,
generates summaries for each community, and enables community-based
retrieval for agent context building.
"""

from __future__ import annotations

from typing import Any

import networkx as nx
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field


class Community(BaseModel):
    """A detected community/cluster in the knowledge graph."""

    community_id: str
    node_ids: list[str] = Field(default_factory=list)
    size: int = 0
    summary: str = ""
    key_entities: list[str] = Field(default_factory=list)
    key_relationships: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CommunityDetectionResult(BaseModel):
    """Result of community detection on a knowledge graph."""

    communities: list[Community] = Field(default_factory=list)
    total_nodes: int = 0
    total_communities: int = 0
    modularity: float = 0.0


SUMMARIZE_COMMUNITY_PROMPT = """Sammanfatta denna grupp av relaterade entiteter och händelser från en organisatorisk simulering.

Entiteter i gruppen:
{entities}

Relationer inom gruppen:
{relationships}

Ge en kort sammanfattning (2-4 meningar) som beskriver:
1. Vad denna grupp handlar om
2. Vilka nyckelaktörer som ingår
3. Vilka viktigaste beslut eller mönster som syns

Svara BARA med sammanfattningen, ingen annan text."""


class CommunityDetector:
    """Detects and analyzes communities in knowledge graphs."""

    def __init__(self, llm: Any | None = None) -> None:
        self._llm = llm

    def detect_communities(
        self,
        graph: nx.DiGraph,
        resolution: float = 1.0,
        min_community_size: int = 2,
    ) -> CommunityDetectionResult:
        """Run Louvain community detection on the graph.

        Args:
            graph: The knowledge graph (directed, converted to undirected for detection)
            resolution: Higher = more communities, lower = fewer/larger
            min_community_size: Minimum nodes per community
        """
        if graph.number_of_nodes() == 0:
            return CommunityDetectionResult()

        # Convert to undirected for community detection
        undirected = graph.to_undirected()

        # Remove isolated nodes for cleaner communities
        connected_nodes = [n for n in undirected.nodes() if undirected.degree(n) > 0]
        if not connected_nodes:
            return CommunityDetectionResult(total_nodes=graph.number_of_nodes())

        subgraph = undirected.subgraph(connected_nodes)

        # Run Louvain community detection
        communities_sets = nx.community.louvain_communities(
            subgraph, resolution=resolution, seed=42
        )

        # Build community objects
        communities = []
        for i, node_set in enumerate(communities_sets):
            if len(node_set) < min_community_size:
                continue

            node_ids = list(node_set)
            community_subgraph = graph.subgraph(node_ids)

            # Identify key entities (highest degree nodes)
            degree_sorted = sorted(
                node_ids,
                key=lambda n: community_subgraph.degree(n),
                reverse=True,
            )
            key_entities = []
            for node_id in degree_sorted[:5]:
                label = graph.nodes[node_id].get("label", node_id)
                entity_type = graph.nodes[node_id].get("entity_type", "unknown")
                key_entities.append(f"{label} ({entity_type})")

            # Identify key relationships
            key_rels = []
            for src, tgt, data in community_subgraph.edges(data=True):
                src_label = graph.nodes[src].get("label", src)
                tgt_label = graph.nodes[tgt].get("label", tgt)
                rel_type = data.get("relation_type", "related")
                key_rels.append(f"{src_label} --[{rel_type}]--> {tgt_label}")

            # Entity type distribution
            type_counts: dict[str, int] = {}
            for nid in node_ids:
                etype = graph.nodes[nid].get("entity_type", "unknown")
                type_counts[etype] = type_counts.get(etype, 0) + 1

            communities.append(Community(
                community_id=f"community_{i}",
                node_ids=node_ids,
                size=len(node_ids),
                key_entities=key_entities,
                key_relationships=key_rels[:10],  # Limit for readability
                metadata={"entity_type_distribution": type_counts},
            ))

        # Calculate modularity
        modularity = 0.0
        if communities:
            partition = [set(c.node_ids) for c in communities]
            try:
                modularity = nx.community.modularity(subgraph, partition)
            except (nx.NetworkXError, ZeroDivisionError):
                modularity = 0.0

        return CommunityDetectionResult(
            communities=communities,
            total_nodes=graph.number_of_nodes(),
            total_communities=len(communities),
            modularity=modularity,
        )

    async def summarize_communities(
        self,
        graph: nx.DiGraph,
        result: CommunityDetectionResult,
    ) -> CommunityDetectionResult:
        """Generate LLM summaries for each detected community."""
        if not self._llm:
            raise RuntimeError("LLM required for summarization")

        for community in result.communities:
            entities_text = "\n".join(
                f"- {graph.nodes[nid].get('label', nid)} "
                f"(typ: {graph.nodes[nid].get('entity_type', '?')})"
                for nid in community.node_ids[:20]  # Limit to avoid context overflow
            )

            rels_text = "\n".join(community.key_relationships[:15])

            prompt = SUMMARIZE_COMMUNITY_PROMPT.format(
                entities=entities_text,
                relationships=rels_text,
            )

            response = await self._llm.ainvoke([HumanMessage(content=prompt)])
            community.summary = response.content.strip()

        return result

    def generate_local_summaries(
        self,
        graph: nx.DiGraph,
        result: CommunityDetectionResult,
    ) -> CommunityDetectionResult:
        """Generate simple summaries without LLM (fast, no API calls)."""
        for community in result.communities:
            # Count entity types
            type_counts = community.metadata.get("entity_type_distribution", {})

            # Build summary from structured data
            parts = [f"Kluster med {community.size} noder."]

            if type_counts:
                type_desc = ", ".join(
                    f"{count} {etype}" for etype, count in type_counts.items()
                )
                parts.append(f"Innehåller: {type_desc}.")

            if community.key_entities:
                parts.append(f"Nyckelaktörer: {', '.join(community.key_entities[:3])}.")

            # Identify dominant relationship types
            rel_types: dict[str, int] = {}
            for rel_str in community.key_relationships:
                for rel_type in ["caused", "influenced", "informed", "decided",
                                 "blocked", "escalated", "conflicted_with"]:
                    if rel_type in rel_str:
                        rel_types[rel_type] = rel_types.get(rel_type, 0) + 1

            if rel_types:
                dominant = max(rel_types, key=rel_types.get)
                parts.append(f"Dominerande mönster: {dominant}.")

            community.summary = " ".join(parts)

        return result


def find_agent_communities(
    agent_id: str,
    graph: nx.DiGraph,
    communities: list[Community],
) -> list[Community]:
    """Find communities relevant to a specific agent."""
    relevant = []
    for community in communities:
        # Check if agent is directly in the community
        if agent_id in community.node_ids:
            relevant.append(community)
            continue

        # Check if any node in the community references the agent
        for node_id in community.node_ids:
            if graph.has_edge(agent_id, node_id) or graph.has_edge(node_id, agent_id):
                relevant.append(community)
                break

    return relevant


def detect_information_silos(
    graph: nx.DiGraph,
    communities: list[Community],
) -> list[dict[str, Any]]:
    """Detect information silos - communities with weak cross-connections."""
    silos = []

    for i, c1 in enumerate(communities):
        for j, c2 in enumerate(communities):
            if i >= j:
                continue

            # Count edges between communities
            cross_edges = 0
            for n1 in c1.node_ids:
                for n2 in c2.node_ids:
                    if graph.has_edge(n1, n2) or graph.has_edge(n2, n1):
                        cross_edges += 1

            # Expected edges based on community sizes
            possible_edges = c1.size * c2.size
            if possible_edges == 0:
                continue

            density = cross_edges / possible_edges

            if density < 0.05:  # Less than 5% connectivity = silo
                silos.append({
                    "community_a": c1.community_id,
                    "community_b": c2.community_id,
                    "cross_edges": cross_edges,
                    "density": density,
                    "key_entities_a": c1.key_entities[:3],
                    "key_entities_b": c2.key_entities[:3],
                    "description": (
                        f"Svag koppling mellan kluster "
                        f"({', '.join(c1.key_entities[:2])}) och "
                        f"({', '.join(c2.key_entities[:2])}). "
                        f"Bara {cross_edges} kopplingar."
                    ),
                })

    return silos
