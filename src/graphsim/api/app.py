"""FastAPI application for Graphsim."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from graphsim.agents.roles.library import (
    ALL_ROLES,
    ROLES_BY_DOMAIN,
    get_role,
    get_roles_by_domain,
    search_roles,
)
from graphsim.agents.traits import TRAIT_DEFINITIONS, TraitProfile
from graphsim.analysis.analyzer import SimulationAnalyzer
from graphsim.api.models import (
    BuildScenarioRequest,
    CreateSimulationRequest,
    DomainResponse,
    MessageResponse,
    RoleTemplateResponse,
    SimulationResultResponse,
    SimulationStatusResponse,
    SuggestRolesRequest,
    TraitDefinitionResponse,
    TraitPresetResponse,
)
from graphsim.config import SimulationConfig
from graphsim.engine.builder import ScenarioBuilder
from graphsim.engine.scenario import ScenarioConfig
from graphsim.orchestrator import Orchestrator

app = FastAPI(
    title="Graphsim",
    description="Multi-agent simulation tool for organizational scenarios",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for simulations (replace with DB later)
_simulations: dict[str, dict[str, Any]] = {}


def _role_to_response(role: Any) -> RoleTemplateResponse:
    return RoleTemplateResponse(
        role_id=role.role_id,
        name=role.name,
        title=role.title,
        domain=role.domain,
        description=role.description,
        responsibilities=role.responsibilities,
        goals=role.goals,
        constraints=role.constraints,
        information_level=role.information_level,
        tags=role.tags,
        suggested_traits=role.suggested_traits.get_available_traits(),
    )


# ============================================================================
# Role Library Endpoints
# ============================================================================

@app.get("/api/roles", response_model=list[RoleTemplateResponse])
async def list_roles(domain: str | None = None, query: str | None = None):
    """List all available role templates, optionally filtered by domain or search query."""
    if query:
        roles = search_roles(query)
    elif domain:
        roles = get_roles_by_domain(domain)
    else:
        roles = ALL_ROLES
    return [_role_to_response(r) for r in roles]


@app.get("/api/roles/{role_id}", response_model=RoleTemplateResponse)
async def get_role_detail(role_id: str):
    """Get details for a specific role template."""
    role = get_role(role_id)
    if not role:
        raise HTTPException(status_code=404, detail=f"Role '{role_id}' not found")
    return _role_to_response(role)


@app.get("/api/domains", response_model=list[DomainResponse])
async def list_domains():
    """List all domains with their roles."""
    result = []
    for domain, roles in ROLES_BY_DOMAIN.items():
        result.append(DomainResponse(
            domain=domain,
            roles=[_role_to_response(r) for r in roles],
        ))
    return result


# ============================================================================
# Trait Endpoints
# ============================================================================

@app.get("/api/traits", response_model=list[TraitDefinitionResponse])
async def list_traits():
    """List all available personality trait dimensions."""
    return [
        TraitDefinitionResponse(
            id=trait_id,
            name=defn["name_sv"],
            low_description=defn["low"],
            high_description=defn["high"],
        )
        for trait_id, defn in TRAIT_DEFINITIONS.items()
    ]


@app.get("/api/traits/presets/{preset_id}", response_model=TraitPresetResponse)
async def get_trait_preset(preset_id: str):
    """Get a trait preset by name."""
    try:
        profile = TraitProfile.from_preset(preset_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Preset '{preset_id}' not found")
    return TraitPresetResponse(preset_id=preset_id, traits=profile.traits)


@app.get("/api/traits/presets", response_model=list[str])
async def list_trait_presets():
    """List available trait preset names."""
    return ["default", "change_resistant", "stressed_leader", "empathic_listener",
            "bureaucrat", "maverick", "anxious"]


# ============================================================================
# Scenario Builder Endpoints
# ============================================================================

@app.post("/api/scenarios/build")
async def build_scenario(request: BuildScenarioRequest):
    """Build a scenario from a natural language description."""
    config = SimulationConfig()
    orchestrator = Orchestrator(config)
    llm = orchestrator._get_llm()
    builder = ScenarioBuilder(llm)

    try:
        scenario = await builder.build_from_description(
            description=request.description,
            num_agents=request.num_agents,
            num_rounds=request.num_rounds,
            domain_hint=request.domain_hint,
        )
        return scenario.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to build scenario: {str(e)}")


@app.post("/api/scenarios/suggest-roles")
async def suggest_roles(request: SuggestRolesRequest):
    """Suggest relevant roles from the library for a scenario description."""
    config = SimulationConfig()
    orchestrator = Orchestrator(config)
    llm = orchestrator._get_llm()
    builder = ScenarioBuilder(llm)

    try:
        suggestions = await builder.suggest_roles(
            description=request.description,
            max_suggestions=request.max_suggestions,
        )
        return suggestions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to suggest roles: {str(e)}")


# ============================================================================
# Simulation Endpoints
# ============================================================================

@app.post("/api/simulations", response_model=SimulationStatusResponse)
async def create_simulation(request: CreateSimulationRequest):
    """Create a new simulation."""
    sim_id = str(uuid.uuid4())[:8]
    config = SimulationConfig()
    orchestrator = Orchestrator(config)

    try:
        if request.scenario_yaml_path:
            orchestrator.load_scenario(request.scenario_yaml_path)
        elif request.scenario_config:
            scenario = ScenarioConfig(**request.scenario_config)
            orchestrator.load_scenario(scenario)
        elif request.scenario_description:
            llm = orchestrator._get_llm()
            builder = ScenarioBuilder(llm)
            scenario = await builder.build_from_description(
                description=request.scenario_description,
                num_agents=request.num_agents,
                num_rounds=request.num_rounds,
                domain_hint=request.domain_hint,
            )
            orchestrator.load_scenario(scenario)
        else:
            raise HTTPException(
                status_code=400,
                detail="Provide scenario_yaml_path, scenario_config, or scenario_description",
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create simulation: {str(e)}")

    _simulations[sim_id] = {
        "orchestrator": orchestrator,
        "status": "created",
    }

    state = orchestrator.state
    return SimulationStatusResponse(
        simulation_id=sim_id,
        status="created",
        current_round=state.current_round,
        max_rounds=state.max_rounds,
        num_agents=len(state.active_agent_ids),
        num_messages=len(state.messages),
        scenario_title=state.metadata.get("title", ""),
    )


@app.post("/api/simulations/{sim_id}/run", response_model=SimulationResultResponse)
async def run_simulation(sim_id: str):
    """Run a simulation to completion."""
    if sim_id not in _simulations:
        raise HTTPException(status_code=404, detail="Simulation not found")

    sim = _simulations[sim_id]
    orchestrator: Orchestrator = sim["orchestrator"]
    sim["status"] = "running"

    try:
        state = await orchestrator.run()
        sim["status"] = "completed"

        # Run analysis
        analyzer = SimulationAnalyzer(orchestrator._get_llm())
        analysis_result = await analyzer.analyze(state)

        messages = [
            MessageResponse(
                agent_id=m.agent_id,
                role=m.role,
                content=m.content,
                round_number=m.round_number,
            )
            for m in state.messages
        ]

        return SimulationResultResponse(
            simulation_id=sim_id,
            status="completed",
            scenario_title=state.metadata.get("title", ""),
            total_rounds=state.current_round + 1,
            messages=messages,
            analysis=analysis_result.model_dump(),
        )
    except Exception as e:
        sim["status"] = "error"
        raise HTTPException(status_code=500, detail=f"Simulation failed: {str(e)}")


@app.post("/api/simulations/{sim_id}/step", response_model=SimulationStatusResponse)
async def step_simulation(sim_id: str):
    """Run a single round of the simulation."""
    if sim_id not in _simulations:
        raise HTTPException(status_code=404, detail="Simulation not found")

    sim = _simulations[sim_id]
    orchestrator: Orchestrator = sim["orchestrator"]
    state = orchestrator.state

    if state.finished or state.current_round >= state.max_rounds - 1:
        raise HTTPException(status_code=400, detail="Simulation already finished")

    sim["status"] = "running"
    next_round = state.current_round + 1 if state.messages else 0

    try:
        await orchestrator.run_round(next_round)
        sim["status"] = "running"

        return SimulationStatusResponse(
            simulation_id=sim_id,
            status="running",
            current_round=state.current_round,
            max_rounds=state.max_rounds,
            num_agents=len(state.active_agent_ids),
            num_messages=len(state.messages),
            scenario_title=state.metadata.get("title", ""),
        )
    except Exception as e:
        sim["status"] = "error"
        raise HTTPException(status_code=500, detail=f"Step failed: {str(e)}")


@app.get("/api/simulations/{sim_id}", response_model=SimulationStatusResponse)
async def get_simulation_status(sim_id: str):
    """Get current status of a simulation."""
    if sim_id not in _simulations:
        raise HTTPException(status_code=404, detail="Simulation not found")

    sim = _simulations[sim_id]
    state = sim["orchestrator"].state

    return SimulationStatusResponse(
        simulation_id=sim_id,
        status=sim["status"],
        current_round=state.current_round,
        max_rounds=state.max_rounds,
        num_agents=len(state.active_agent_ids),
        num_messages=len(state.messages),
        scenario_title=state.metadata.get("title", ""),
    )


@app.get("/api/simulations/{sim_id}/messages", response_model=list[MessageResponse])
async def get_simulation_messages(sim_id: str, round_number: int | None = None):
    """Get messages from a simulation, optionally filtered by round."""
    if sim_id not in _simulations:
        raise HTTPException(status_code=404, detail="Simulation not found")

    state = _simulations[sim_id]["orchestrator"].state
    messages = state.messages

    if round_number is not None:
        messages = [m for m in messages if m.round_number == round_number]

    return [
        MessageResponse(
            agent_id=m.agent_id,
            role=m.role,
            content=m.content,
            round_number=m.round_number,
        )
        for m in messages
    ]


@app.post("/api/simulations/{sim_id}/analyze")
async def analyze_simulation(sim_id: str):
    """Run analysis on a simulation (can be called during or after)."""
    if sim_id not in _simulations:
        raise HTTPException(status_code=404, detail="Simulation not found")

    sim = _simulations[sim_id]
    orchestrator: Orchestrator = sim["orchestrator"]

    try:
        analyzer = SimulationAnalyzer(orchestrator._get_llm())
        result = await analyzer.analyze(orchestrator.state)
        return result.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
