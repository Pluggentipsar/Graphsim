# Graphsim - Multi-Agent Simulator

## Project Overview

Graphsim is a simulation tool where multiple AI agent instances communicate with each other based on defined roles, relationships, and scenarios. The system uses a graph-based architecture to model relationships between agents, information flow, and decision chains.

**Primary use case:** Simulating complex organizational scenarios (education, social services, crisis management) where multiple professionals with different roles, responsibilities, and information levels must collaborate.

## Architecture

Four-layer architecture:

1. **Scenario Engine** (`src/engine/`) - Defines and manages simulation cases
2. **Agent Layer** (`src/agents/`) - Role-based AI agents with defined responsibilities
3. **Graph Layer** (`src/graph/`) - Relationships, information flow, reporting chains (Neo4j/NetworkX)
4. **Analysis Layer** (`src/analysis/`) - Post-simulation analysis and insights

### Key Design Principles

- **Orchestrator-driven**: A central orchestrator controls which agents are active per step
- **Graph-activated**: Only relevant agents are woken per step based on graph relationships
- **Information-scoped**: Each agent only sees information they should have access to
- **State-managed**: All simulation state flows through LangGraph's state management

## Tech Stack

- **Language**: Python 3.11+
- **Orchestration**: LangGraph
- **Graph database**: Neo4j (production) / NetworkX (local dev)
- **State/persistence**: PostgreSQL via SQLAlchemy
- **LLM provider**: Anthropic Claude API (primary), OpenAI (optional)
- **Frontend**: Next.js (separate repo, future)
- **Testing**: pytest
- **Linting**: ruff

## Project Structure

```
graphsim/
├── CLAUDE.md
├── pyproject.toml
├── src/
│   └── graphsim/
│       ├── __init__.py
│       ├── config.py          # Settings, env vars, model config
│       ├── orchestrator.py    # Central simulation orchestrator
│       ├── engine/
│       │   ├── __init__.py
│       │   ├── scenario.py    # Scenario definitions and loading
│       │   └── state.py       # Simulation state management
│       ├── agents/
│       │   ├── __init__.py
│       │   ├── base.py        # Base agent class
│       │   ├── registry.py    # Agent role registry
│       │   └── roles/         # Role-specific agent configs
│       │       └── __init__.py
│       ├── graph/
│       │   ├── __init__.py
│       │   ├── models.py      # Graph node/edge models
│       │   ├── store.py       # Graph storage abstraction
│       │   └── queries.py     # Common graph queries
│       └── analysis/
│           ├── __init__.py
│           └── analyzer.py    # Post-simulation analysis
├── scenarios/                 # YAML scenario definitions
│   └── example_school.yaml
├── tests/
│   ├── __init__.py
│   ├── test_orchestrator.py
│   ├── test_agents.py
│   └── test_graph.py
└── scripts/
    └── run_simulation.py
```

## Development Guidelines

### Commands
- **Install**: `pip install -e ".[dev]"`
- **Run tests**: `pytest`
- **Run single test**: `pytest tests/test_file.py::test_name`
- **Lint**: `ruff check src/`
- **Format**: `ruff format src/`
- **Run simulation**: `python scripts/run_simulation.py --scenario scenarios/example_school.yaml`

### Code Style
- Use type hints everywhere
- Pydantic models for all data structures
- Async where appropriate (agent LLM calls)
- Keep agents stateless - all state lives in the graph/state store
- Swedish comments are OK, but code (variable names, functions) in English

### Agent Design
- Each agent has: role, responsibilities, goals, constraints, information_level, personality
- Agents communicate through the orchestrator, never directly
- The orchestrator decides turn order based on graph activation rules
- Information scoping: agents only receive context they have access to per the graph

### Graph Conventions
- Node types: Person, Role, Case, Meeting, Decision, Document, RiskFactor, ResourceConstraint
- Edge types: reports_to, collaborates_with, has_info_about, affects, participated_in, responsible_for, lacks_knowledge_of
- All graph mutations go through the store abstraction

### Environment Variables
- `ANTHROPIC_API_KEY` - Claude API key
- `OPENAI_API_KEY` - OpenAI API key (optional)
- `NEO4J_URI` - Neo4j connection URI (optional, falls back to NetworkX)
- `NEO4J_USER` - Neo4j username
- `NEO4J_PASSWORD` - Neo4j password
- `DATABASE_URL` - PostgreSQL connection string (optional for MVP)
