"""Graph node and edge models."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class NodeType(str, Enum):
    PERSON = "person"
    ROLE = "role"
    CASE = "case"
    MEETING = "meeting"
    DECISION = "decision"
    DOCUMENT = "document"
    RISK_FACTOR = "risk_factor"
    RESOURCE_CONSTRAINT = "resource_constraint"


class EdgeType(str, Enum):
    REPORTS_TO = "reports_to"
    COLLABORATES_WITH = "collaborates_with"
    HAS_INFO_ABOUT = "has_info_about"
    AFFECTS = "affects"
    PARTICIPATED_IN = "participated_in"
    RESPONSIBLE_FOR = "responsible_for"
    LACKS_KNOWLEDGE_OF = "lacks_knowledge_of"


class GraphNode(BaseModel):
    """A node in the simulation graph."""

    node_id: str
    node_type: NodeType
    label: str
    properties: dict[str, Any] = Field(default_factory=dict)

    def __hash__(self) -> int:
        return hash(self.node_id)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, GraphNode):
            return self.node_id == other.node_id
        return NotImplemented


class GraphEdge(BaseModel):
    """An edge (relationship) in the simulation graph."""

    source_id: str
    target_id: str
    edge_type: EdgeType
    properties: dict[str, Any] = Field(default_factory=dict)

    @property
    def key(self) -> tuple[str, str, str]:
        return (self.source_id, self.target_id, self.edge_type.value)
