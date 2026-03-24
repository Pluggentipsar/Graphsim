"""Graph storage abstraction - NetworkX backend for MVP."""

from __future__ import annotations

from typing import Any

import networkx as nx

from graphsim.graph.models import EdgeType, GraphEdge, GraphNode, NodeType


class GraphStore:
    """Graph store using NetworkX as the backend.

    Provides a clean abstraction that can later be swapped for Neo4j.
    """

    def __init__(self) -> None:
        self._graph = nx.DiGraph()

    def add_node(self, node: GraphNode) -> None:
        self._graph.add_node(
            node.node_id,
            node_type=node.node_type.value,
            label=node.label,
            **node.properties,
        )

    def add_edge(self, edge: GraphEdge) -> None:
        self._graph.add_edge(
            edge.source_id,
            edge.target_id,
            edge_type=edge.edge_type.value,
            **edge.properties,
        )

    def get_node(self, node_id: str) -> GraphNode | None:
        if node_id not in self._graph:
            return None
        data = dict(self._graph.nodes[node_id])
        node_type = NodeType(data.pop("node_type"))
        label = data.pop("label")
        return GraphNode(node_id=node_id, node_type=node_type, label=label, properties=data)

    def get_neighbors(
        self, node_id: str, edge_type: EdgeType | None = None
    ) -> list[GraphNode]:
        """Get all nodes connected to the given node, optionally filtered by edge type."""
        neighbors = []
        for _, target, data in self._graph.out_edges(node_id, data=True):
            if edge_type and data.get("edge_type") != edge_type.value:
                continue
            node = self.get_node(target)
            if node:
                neighbors.append(node)
        for source, _, data in self._graph.in_edges(node_id, data=True):
            if edge_type and data.get("edge_type") != edge_type.value:
                continue
            node = self.get_node(source)
            if node:
                neighbors.append(node)
        return neighbors

    def get_outgoing_neighbors(
        self, node_id: str, edge_type: EdgeType | None = None
    ) -> list[GraphNode]:
        """Get nodes reachable via outgoing edges only."""
        neighbors = []
        for _, target, data in self._graph.out_edges(node_id, data=True):
            if edge_type and data.get("edge_type") != edge_type.value:
                continue
            node = self.get_node(target)
            if node:
                neighbors.append(node)
        return neighbors

    def get_edges_for_node(self, node_id: str) -> list[GraphEdge]:
        """Get all edges connected to a node."""
        edges = []
        for src, tgt, data in self._graph.out_edges(node_id, data=True):
            edge_data = dict(data)
            edge_type = EdgeType(edge_data.pop("edge_type"))
            edges.append(GraphEdge(
                source_id=src, target_id=tgt, edge_type=edge_type, properties=edge_data
            ))
        for src, tgt, data in self._graph.in_edges(node_id, data=True):
            edge_data = dict(data)
            edge_type = EdgeType(edge_data.pop("edge_type"))
            edges.append(GraphEdge(
                source_id=src, target_id=tgt, edge_type=edge_type, properties=edge_data
            ))
        return edges

    def get_nodes_by_type(self, node_type: NodeType) -> list[GraphNode]:
        """Get all nodes of a specific type."""
        return [
            self.get_node(nid)
            for nid, data in self._graph.nodes(data=True)
            if data.get("node_type") == node_type.value and self.get_node(nid)
        ]

    def get_relationships_for_agent(self, agent_id: str) -> list[dict[str, Any]]:
        """Get human-readable relationship descriptions for an agent."""
        relationships = []
        for edge in self.get_edges_for_node(agent_id):
            other_id = edge.target_id if edge.source_id == agent_id else edge.source_id
            other_node = self.get_node(other_id)
            if other_node:
                relationships.append({
                    "type": edge.edge_type.value,
                    "target_id": other_id,
                    "target_name": other_node.label,
                    "direction": "outgoing" if edge.source_id == agent_id else "incoming",
                })
        return relationships

    def get_info_accessible_agents(self, node_id: str) -> list[str]:
        """Get IDs of agents that a given node has information about."""
        return [
            n.node_id
            for n in self.get_neighbors(node_id, EdgeType.HAS_INFO_ABOUT)
        ]

    @property
    def node_count(self) -> int:
        return self._graph.number_of_nodes()

    @property
    def edge_count(self) -> int:
        return self._graph.number_of_edges()
