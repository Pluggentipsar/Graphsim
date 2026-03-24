"""Common graph queries for the simulation."""

from __future__ import annotations

from graphsim.graph.models import EdgeType, NodeType
from graphsim.graph.store import GraphStore


def find_active_agents_for_case(store: GraphStore, case_id: str) -> list[str]:
    """Find all agent IDs that are connected to a specific case."""
    agents = []
    neighbors = store.get_neighbors(case_id)
    for node in neighbors:
        if node.node_type == NodeType.PERSON:
            agents.append(node.node_id)
    return agents


def find_reporting_chain(store: GraphStore, agent_id: str) -> list[str]:
    """Find the chain of agents this agent reports to (upward)."""
    chain = []
    current = agent_id
    visited = set()
    while current not in visited:
        visited.add(current)
        supervisors = store.get_outgoing_neighbors(current, EdgeType.REPORTS_TO)
        if not supervisors:
            break
        supervisor = supervisors[0]
        chain.append(supervisor.node_id)
        current = supervisor.node_id
    return chain


def find_collaborators(store: GraphStore, agent_id: str) -> list[str]:
    """Find all agents that collaborate with the given agent."""
    return [
        n.node_id
        for n in store.get_neighbors(agent_id, EdgeType.COLLABORATES_WITH)
    ]


def find_uninformed_agents(store: GraphStore, case_id: str) -> list[str]:
    """Find agents connected to a case who lack knowledge of it."""
    connected = find_active_agents_for_case(store, case_id)
    uninformed = []
    for agent_id in connected:
        lacking = store.get_neighbors(agent_id, EdgeType.LACKS_KNOWLEDGE_OF)
        if any(n.node_id == case_id for n in lacking):
            uninformed.append(agent_id)
    return uninformed
