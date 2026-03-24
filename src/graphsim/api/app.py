"""FastAPI application for Graphsim."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from graphsim.agents.roles.library import (
    ALL_ROLES,
    ROLES_BY_DOMAIN,
    get_role,
    get_roles_by_domain,
    search_roles,
)
from graphsim.agents.traits import TRAIT_DEFINITIONS, TraitProfile
from graphsim.analysis.analyzer import SimulationAnalyzer
from graphsim.analysis.export import ReportExporter
from graphsim.api.models import (
    BuildScenarioRequest,
    CreateSimulationRequest,
    DomainResponse,
    ExportRequest,
    InjectEventRequest,
    MessageResponse,
    RoleTemplateResponse,
    RunComparisonRequest,
    ScenarioTemplateResponse,
    SimulationResultResponse,
    SimulationStatusResponse,
    SuggestRolesRequest,
    TraitDefinitionResponse,
    TraitPresetResponse,
    VariantConfigRequest,
)
from graphsim.config import SimulationConfig
from graphsim.engine.builder import ScenarioBuilder
from graphsim.engine.comparison import ComparisonRunner, VariantConfig
from graphsim.engine.scenario import ScenarioConfig, load_scenario
from graphsim.engine.templates import (
    ALL_TEMPLATES,
    EventTrigger,
    TEMPLATES_BY_DOMAIN,
    get_template,
    search_templates,
)
from graphsim.orchestrator import Orchestrator
from graphsim.rag.engine import GraphRAGEngine
from graphsim.rag.extractor import build_knowledge_graph_from_state
from graphsim.documents.analyzer import DocumentAnalyzer
from graphsim.documents.reader import read_document
from graphsim.documents.scenario_builder import DocumentScenarioBuilder
from graphsim.rag.store import KnowledgeStore

# Shared GraphRAG engine and knowledge store
_knowledge_store = KnowledgeStore()
_graphrag_engine = GraphRAGEngine(knowledge_store=_knowledge_store)

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


# ============================================================================
# Scenario Template Endpoints
# ============================================================================

@app.get("/api/templates", response_model=list[ScenarioTemplateResponse])
async def list_templates(domain: str | None = None, query: str | None = None):
    """List available scenario templates."""
    if query:
        templates = search_templates(query)
    elif domain:
        templates = TEMPLATES_BY_DOMAIN.get(domain, [])
    else:
        templates = ALL_TEMPLATES
    return [
        ScenarioTemplateResponse(
            template_id=t.template_id,
            title=t.title,
            domain=t.domain,
            description=t.description,
            suggested_roles=t.suggested_roles,
            decision_points=t.decision_points,
            tags=t.tags,
            difficulty=t.difficulty,
            estimated_rounds=t.estimated_rounds,
            num_events=len(t.events),
        )
        for t in templates
    ]


@app.get("/api/templates/{template_id}")
async def get_template_detail(template_id: str):
    """Get full details for a scenario template including events."""
    template = get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")
    return template.model_dump()


@app.post("/api/simulations/from-template", response_model=SimulationStatusResponse)
async def create_simulation_from_template(
    template_id: str,
    num_rounds: int | None = None,
):
    """Create a simulation from a pre-built template, including its events."""
    template = get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")

    # Build a ScenarioConfig from the template using the role library
    from graphsim.agents.roles.library import get_role as get_library_role

    agents = []
    for role_id in template.suggested_roles:
        role = get_library_role(role_id)
        if role:
            agents.append(role.to_agent_config())

    relationships = []
    from graphsim.engine.scenario import RelationshipConfig
    for rel in template.suggested_relationships:
        relationships.append(RelationshipConfig(
            source=rel["source"],
            target=rel["target"],
            relation_type=rel["type"],
        ))

    scenario = ScenarioConfig(
        scenario_id=template.template_id,
        title=template.title,
        description=template.description,
        context=template.context,
        initial_event=template.initial_event,
        agents=agents,
        relationships=relationships,
        decision_points=template.decision_points,
        max_rounds=num_rounds or template.estimated_rounds,
    )

    sim_id = str(uuid.uuid4())[:8]
    config = SimulationConfig()
    orchestrator = Orchestrator(config)
    orchestrator.load_scenario(scenario)

    # Schedule template events
    if template.events:
        orchestrator.schedule_events(template.events)

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


# ============================================================================
# Event Injection Endpoints
# ============================================================================

@app.post("/api/simulations/{sim_id}/events")
async def inject_event(sim_id: str, request: InjectEventRequest):
    """Inject an event into the current round of a simulation."""
    if sim_id not in _simulations:
        raise HTTPException(status_code=404, detail="Simulation not found")

    orchestrator: Orchestrator = _simulations[sim_id]["orchestrator"]
    state = orchestrator.state

    event = EventTrigger(
        round_number=state.current_round,
        description=request.description,
        affects_agents=request.affects_agents,
        new_information=request.new_information,
    )

    orchestrator.inject_event(event)
    return {"status": "injected", "round": state.current_round}


@app.get("/api/simulations/{sim_id}/events")
async def list_simulation_events(sim_id: str):
    """List all pending and processed events for a simulation."""
    if sim_id not in _simulations:
        raise HTTPException(status_code=404, detail="Simulation not found")

    orchestrator: Orchestrator = _simulations[sim_id]["orchestrator"]
    return {
        "pending": [e.model_dump() for e in orchestrator.event_manager.pending_events],
        "processed": [
            {
                "event": o.event.model_dump(),
                "messages_injected": o.messages_injected,
                "agents_notified": o.agents_notified,
            }
            for o in orchestrator.event_manager.processed_events
        ],
    }


# ============================================================================
# Comparison Endpoints
# ============================================================================

@app.post("/api/comparisons/run")
async def run_comparison(request: RunComparisonRequest):
    """Run the same scenario with different configurations and compare."""
    # Load base scenario
    if request.scenario_yaml_path:
        scenario = load_scenario(request.scenario_yaml_path)
    elif request.scenario_config:
        scenario = ScenarioConfig(**request.scenario_config)
    elif request.template_id:
        template = get_template(request.template_id)
        if not template:
            raise HTTPException(status_code=404, detail=f"Template '{request.template_id}' not found")
        from graphsim.agents.roles.library import get_role as get_library_role
        from graphsim.engine.scenario import RelationshipConfig

        agents = []
        for role_id in template.suggested_roles:
            role = get_library_role(role_id)
            if role:
                agents.append(role.to_agent_config())
        relationships = [
            RelationshipConfig(source=r["source"], target=r["target"], relation_type=r["type"])
            for r in template.suggested_relationships
        ]
        scenario = ScenarioConfig(
            scenario_id=template.template_id,
            title=template.title,
            description=template.description,
            context=template.context,
            initial_event=template.initial_event,
            agents=agents,
            relationships=relationships,
            decision_points=template.decision_points,
            max_rounds=template.estimated_rounds,
        )
    else:
        raise HTTPException(
            status_code=400,
            detail="Provide scenario_yaml_path, scenario_config, or template_id",
        )

    variants = [
        VariantConfig(
            variant_id=v.variant_id,
            label=v.label,
            description=v.description,
            trait_overrides=v.trait_overrides,
            personality_overrides=v.personality_overrides,
        )
        for v in request.variants
    ]

    try:
        runner = ComparisonRunner()
        result = await runner.run_comparison(scenario, variants)

        return {
            "scenario_title": result.scenario_title,
            "num_variants": len(result.variants),
            "variants": [
                {
                    "variant_id": v.variant_id,
                    "label": v.label,
                    "total_rounds": v.state.current_round + 1,
                    "total_messages": len(v.state.messages),
                    "analysis": v.analysis.model_dump() if v.analysis else None,
                }
                for v in result.variants
            ],
            "comparison_summary": result.comparison_summary,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Comparison failed: {str(e)}")


# ============================================================================
# Export Endpoints
# ============================================================================

@app.post("/api/simulations/{sim_id}/export")
async def export_simulation(sim_id: str, request: ExportRequest):
    """Export simulation results as Markdown or JSON report."""
    if sim_id not in _simulations:
        raise HTTPException(status_code=404, detail="Simulation not found")

    sim = _simulations[sim_id]
    orchestrator: Orchestrator = sim["orchestrator"]
    state = orchestrator.state
    exporter = ReportExporter()

    # Try to get existing analysis
    analysis = None
    if sim.get("analysis"):
        analysis = sim["analysis"]

    if request.format == "markdown":
        content = exporter.to_markdown(state, analysis)
        return PlainTextResponse(content=content, media_type="text/markdown")
    elif request.format == "json":
        content = exporter.to_json(state, analysis)
        return PlainTextResponse(content=content, media_type="application/json")
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {request.format}")


# ============================================================================
# GraphRAG Endpoints
# ============================================================================

@app.post("/api/simulations/{sim_id}/graphrag/extract")
async def extract_knowledge_graph(sim_id: str):
    """Extract a knowledge graph from a simulation's messages."""
    if sim_id not in _simulations:
        raise HTTPException(status_code=404, detail="Simulation not found")

    state = _simulations[sim_id]["orchestrator"].state
    kg = build_knowledge_graph_from_state(state)

    return {
        "simulation_id": sim_id,
        "nodes": kg.number_of_nodes(),
        "edges": kg.number_of_edges(),
        "graph_stats": _graphrag_engine.analyze_graph_structure(kg),
    }


@app.post("/api/simulations/{sim_id}/graphrag/communities")
async def detect_communities(sim_id: str, resolution: float = 1.0):
    """Detect communities in a simulation's knowledge graph."""
    if sim_id not in _simulations:
        raise HTTPException(status_code=404, detail="Simulation not found")

    state = _simulations[sim_id]["orchestrator"].state
    kg = build_knowledge_graph_from_state(state)
    result = _graphrag_engine.detect_communities(kg, resolution=resolution)

    # Generate local summaries (no LLM needed)
    from graphsim.rag.communities import CommunityDetector
    detector = CommunityDetector()
    result = detector.generate_local_summaries(kg, result)

    return {
        "simulation_id": sim_id,
        "total_communities": result.total_communities,
        "modularity": result.modularity,
        "communities": [
            {
                "community_id": c.community_id,
                "size": c.size,
                "summary": c.summary,
                "key_entities": c.key_entities,
                "key_relationships": c.key_relationships[:5],
            }
            for c in result.communities
        ],
    }


@app.post("/api/simulations/{sim_id}/graphrag/silos")
async def detect_silos(sim_id: str):
    """Detect information silos in a simulation."""
    if sim_id not in _simulations:
        raise HTTPException(status_code=404, detail="Simulation not found")

    state = _simulations[sim_id]["orchestrator"].state
    kg = build_knowledge_graph_from_state(state)
    communities = _graphrag_engine.detect_communities(kg)
    silos = _graphrag_engine.find_silos(kg, communities.communities)

    return {
        "simulation_id": sim_id,
        "total_silos": len(silos),
        "silos": silos,
    }


@app.post("/api/simulations/{sim_id}/graphrag/archive")
async def archive_simulation_graphrag(sim_id: str):
    """Archive a simulation with its knowledge graph for cross-simulation learning."""
    if sim_id not in _simulations:
        raise HTTPException(status_code=404, detail="Simulation not found")

    state = _simulations[sim_id]["orchestrator"].state

    try:
        archive = await _graphrag_engine.archive_simulation(
            simulation_id=sim_id,
            state=state,
            use_llm_extraction=False,
            use_llm_summaries=False,
        )
        return {
            "simulation_id": sim_id,
            "scenario_title": archive.scenario_title,
            "communities": len(archive.communities),
            "silos": len(archive.silos),
            "patterns": archive.key_patterns,
            "archived": True,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Archival failed: {str(e)}")


@app.get("/api/graphrag/archives")
async def list_archives():
    """List all archived simulations in the knowledge store."""
    archives = _knowledge_store.list_archives()
    return [
        {
            "simulation_id": a.simulation_id,
            "scenario_id": a.scenario_id,
            "scenario_title": a.scenario_title,
            "total_rounds": a.total_rounds,
            "total_messages": a.total_messages,
            "communities": len(a.communities),
            "silos": len(a.silos),
            "patterns": len(a.key_patterns),
        }
        for a in archives
    ]


@app.get("/api/graphrag/precedents")
async def get_precedents(scenario_title: str, max_results: int = 3):
    """Get precedent context from archived simulations for a new scenario."""
    precedents = _knowledge_store.get_precedent_context(
        scenario_title, max_precedents=max_results
    )
    return {
        "scenario_title": scenario_title,
        "precedents": precedents,
        "total_archives": _knowledge_store.archive_count,
    }


@app.get("/api/graphrag/patterns")
async def get_all_patterns():
    """Get all patterns learned from archived simulations."""
    patterns = _knowledge_store.get_all_patterns()
    return {
        "total_patterns": len(patterns),
        "patterns": patterns,
    }


# ============================================================================
# Document Endpoints
# ============================================================================

@app.post("/api/documents/analyze")
async def analyze_document(
    file: Any = None,
    file_path: str | None = None,
):
    """Analyze an uploaded document and extract structured information."""
    from fastapi import File, UploadFile

    # This endpoint works with file_path for simplicity
    if not file_path:
        raise HTTPException(
            status_code=400,
            detail="Provide file_path to the document",
        )

    try:
        doc = read_document(file_path=file_path)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read document: {str(e)}")

    config = SimulationConfig()
    orchestrator = Orchestrator(config)
    llm = orchestrator._get_llm()
    analyzer = DocumentAnalyzer(llm)

    try:
        analysis = await analyzer.analyze(doc)
        return {
            "document": {
                "filename": doc.filename,
                "file_type": doc.file_type,
                "word_count": doc.word_count,
                "num_pages": doc.num_pages,
            },
            "analysis": analysis.model_dump(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.post("/api/documents/build-scenario")
async def build_scenario_from_document(
    file_path: str,
    num_rounds: int = 5,
    custom_instructions: str = "",
):
    """Analyze a document and generate a complete simulation scenario from it."""
    try:
        doc = read_document(file_path=file_path)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read document: {str(e)}")

    config = SimulationConfig()
    orchestrator = Orchestrator(config)
    llm = orchestrator._get_llm()

    analyzer = DocumentAnalyzer(llm)
    builder = DocumentScenarioBuilder(llm)

    try:
        analysis = await analyzer.analyze(doc)
        scenario, events = await builder.build_scenario(
            document=doc,
            analysis=analysis,
            num_rounds=num_rounds,
            custom_instructions=custom_instructions,
        )

        return {
            "document": {
                "filename": doc.filename,
                "word_count": doc.word_count,
            },
            "analysis": analysis.model_dump(),
            "scenario": scenario.model_dump(),
            "events": [e.model_dump() for e in events],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scenario generation failed: {str(e)}")
