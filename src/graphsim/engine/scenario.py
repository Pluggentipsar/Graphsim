"""Scenario definitions and loading from YAML."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class AgentRoleConfig(BaseModel):
    """Configuration for a single agent role within a scenario."""

    role_id: str
    name: str
    title: str
    responsibilities: list[str] = Field(default_factory=list)
    goals: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    information_level: str = "standard"
    personality: str = ""
    initial_knowledge: list[str] = Field(default_factory=list)


class RelationshipConfig(BaseModel):
    """A relationship between two agents in the scenario."""

    source: str
    target: str
    relation_type: str
    properties: dict[str, Any] = Field(default_factory=dict)


class ScenarioConfig(BaseModel):
    """A complete scenario definition."""

    scenario_id: str
    title: str
    description: str
    context: str = ""
    agents: list[AgentRoleConfig] = Field(default_factory=list)
    relationships: list[RelationshipConfig] = Field(default_factory=list)
    initial_event: str = ""
    decision_points: list[str] = Field(default_factory=list)
    max_rounds: int = 15


def load_scenario(path: str | Path) -> ScenarioConfig:
    """Load a scenario from a YAML file."""
    path = Path(path)
    with path.open() as f:
        data = yaml.safe_load(f)
    return ScenarioConfig(**data)
