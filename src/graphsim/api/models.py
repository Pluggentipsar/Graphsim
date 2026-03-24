"""API request/response models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ============================================================================
# Role Library
# ============================================================================

class RoleTemplateResponse(BaseModel):
    role_id: str
    name: str
    title: str
    domain: str
    description: str
    responsibilities: list[str]
    goals: list[str]
    constraints: list[str]
    information_level: str
    tags: list[str]
    suggested_traits: list[dict[str, Any]]


class DomainResponse(BaseModel):
    domain: str
    roles: list[RoleTemplateResponse]


# ============================================================================
# Traits
# ============================================================================

class TraitDefinitionResponse(BaseModel):
    id: str
    name: str
    low_description: str
    high_description: str


class TraitPresetResponse(BaseModel):
    preset_id: str
    traits: dict[str, float]


# ============================================================================
# Scenario Builder
# ============================================================================

class BuildScenarioRequest(BaseModel):
    description: str
    num_agents: int = 8
    num_rounds: int = 5
    domain_hint: str | None = None


class AgentConfigRequest(BaseModel):
    role_id: str
    name: str | None = None
    trait_overrides: dict[str, float] = Field(default_factory=dict)
    natural_language_personality: str = ""


class SuggestRolesRequest(BaseModel):
    description: str
    max_suggestions: int = 10


# ============================================================================
# Simulation
# ============================================================================

class CreateSimulationRequest(BaseModel):
    """Create a simulation from either a scenario file, built scenario, or natural language."""

    scenario_yaml_path: str | None = None
    scenario_description: str | None = None
    scenario_config: dict[str, Any] | None = None
    num_rounds: int = 5
    num_agents: int = 8
    domain_hint: str | None = None


class SimulationStatusResponse(BaseModel):
    simulation_id: str
    status: str  # created, running, completed, error
    current_round: int
    max_rounds: int
    num_agents: int
    num_messages: int
    scenario_title: str


class MessageResponse(BaseModel):
    agent_id: str
    role: str
    content: str
    round_number: int


class SimulationResultResponse(BaseModel):
    simulation_id: str
    status: str
    scenario_title: str
    total_rounds: int
    messages: list[MessageResponse]
    analysis: dict[str, Any] | None = None


# ============================================================================
# Templates
# ============================================================================

class ScenarioTemplateResponse(BaseModel):
    template_id: str
    title: str
    domain: str
    description: str
    suggested_roles: list[str]
    decision_points: list[str]
    tags: list[str]
    difficulty: str
    estimated_rounds: int
    num_events: int


# ============================================================================
# Events
# ============================================================================

class InjectEventRequest(BaseModel):
    description: str
    affects_agents: list[str] = Field(default_factory=list)
    new_information: dict[str, str] = Field(default_factory=dict)


# ============================================================================
# Comparison
# ============================================================================

class VariantConfigRequest(BaseModel):
    variant_id: str
    label: str
    description: str = ""
    trait_overrides: dict[str, dict[str, float]] = Field(default_factory=dict)
    personality_overrides: dict[str, str] = Field(default_factory=dict)


class RunComparisonRequest(BaseModel):
    scenario_yaml_path: str | None = None
    scenario_config: dict[str, Any] | None = None
    template_id: str | None = None
    variants: list[VariantConfigRequest]


# ============================================================================
# Export
# ============================================================================

class ExportRequest(BaseModel):
    format: str = "markdown"  # markdown, json
