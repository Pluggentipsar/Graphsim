# Graphsim - Multi-Agent Simulator

## Project Overview

Graphsim is a simulation tool where multiple AI agent instances communicate with each other based on defined roles, relationships, and scenarios. The system uses a graph-based architecture to model relationships between agents, information flow, and decision chains.

**Primary use case:** Simulating complex organizational scenarios (education, social services, crisis management) where multiple professionals with different roles, responsibilities, and information levels must collaborate.

## Architecture

Six-layer architecture:

1. **Scenario Engine** (`src/engine/`) - Defines and manages simulation cases, templates, events
2. **Agent Layer** (`src/agents/`) - Role-based AI agents with trait system and role library
3. **Graph Layer** (`src/graph/`) - Relationships, information flow, reporting chains (Neo4j/NetworkX)
4. **Analysis Layer** (`src/analysis/`) - Post-simulation analysis, export, and reporting
5. **GraphRAG Layer** (`src/rag/`) - Knowledge extraction, community detection, cross-simulation learning
6. **UI Layer** (`src/ui/`) - Streamlit dashboard for interactive simulation

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
│       │   ├── traits.py      # Personality trait system (0-10 sliders)
│       │   └── roles/
│       │       ├── __init__.py
│       │       └── library.py # 19 pre-built roles across 6 domains
│       ├── graph/
│       │   ├── __init__.py
│       │   ├── models.py      # Graph node/edge models
│       │   ├── store.py       # Graph storage abstraction
│       │   └── queries.py     # Common graph queries
│       ├── analysis/
│       │   ├── __init__.py
│       │   ├── analyzer.py    # Structured post-simulation analysis
│       │   └── export.py      # Markdown/JSON report export
│       ├── rag/               # GraphRAG system
│       │   ├── __init__.py
│       │   ├── extractor.py   # Knowledge graph extraction
│       │   ├── communities.py # Community detection (Louvain)
│       │   ├── store.py       # Cross-simulation knowledge store
│       │   └── engine.py      # GraphRAG unified interface
│       ├── api/               # FastAPI REST API
│       │   ├── __init__.py
│       │   ├── app.py         # All API endpoints
│       │   └── models.py      # Request/response models
│       └── ui/                # Streamlit dashboard
│           ├── __init__.py
│           └── app.py         # Interactive simulation UI
├── scenarios/                 # YAML scenario definitions
│   └── example_school.yaml
├── tests/                     # 105 tests
│   ├── __init__.py
│   ├── test_orchestrator.py
│   ├── test_agents.py
│   ├── test_graph.py
│   ├── test_traits.py
│   ├── test_roles.py
│   ├── test_templates.py
│   ├── test_events.py
│   ├── test_scoping.py
│   ├── test_export.py
│   ├── test_api.py
│   ├── test_graphrag.py
│   └── test_graphrag_api.py
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
- **Start UI**: `streamlit run src/graphsim/ui/app.py`
- **Start API**: `uvicorn graphsim.api.app:app --reload`

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
