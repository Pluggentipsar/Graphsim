"""Configuration and settings for Graphsim."""

from __future__ import annotations

import os
from enum import Enum

from pydantic import BaseModel, Field


class LLMProvider(str, Enum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"


class LLMConfig(BaseModel):
    provider: LLMProvider = LLMProvider.ANTHROPIC
    model: str = "claude-sonnet-4-20250514"
    temperature: float = 0.7
    max_tokens: int = 2048


class GraphBackend(str, Enum):
    NETWORKX = "networkx"
    NEO4J = "neo4j"


class GraphConfig(BaseModel):
    backend: GraphBackend = GraphBackend.NETWORKX
    neo4j_uri: str = Field(default_factory=lambda: os.getenv("NEO4J_URI", "bolt://localhost:7687"))
    neo4j_user: str = Field(default_factory=lambda: os.getenv("NEO4J_USER", "neo4j"))
    neo4j_password: str = Field(default_factory=lambda: os.getenv("NEO4J_PASSWORD", ""))


class SimulationConfig(BaseModel):
    """Top-level configuration for a simulation run."""

    llm: LLMConfig = Field(default_factory=LLMConfig)
    graph: GraphConfig = Field(default_factory=GraphConfig)
    max_rounds: int = 20
    max_concurrent_agents: int = 5
    verbose: bool = True
