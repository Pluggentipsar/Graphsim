"""Graphsim Streamlit Dashboard.

Run with: streamlit run src/graphsim/ui/app.py
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import plotly.graph_objects as go
import streamlit as st

from graphsim.agents.roles.library import (
    ALL_ROLES,
    ROLES_BY_DOMAIN,
    get_role,
    get_all_domains,
)
from graphsim.agents.traits import TRAIT_DEFINITIONS, TraitProfile
from graphsim.analysis.analyzer import SimulationAnalyzer
from graphsim.analysis.export import ReportExporter
from graphsim.config import SimulationConfig
from graphsim.engine.builder import ScenarioBuilder
from graphsim.engine.scenario import AgentRoleConfig, RelationshipConfig, ScenarioConfig
from graphsim.engine.templates import (
    ALL_TEMPLATES,
    TEMPLATES_BY_DOMAIN,
    get_template,
)
from graphsim.orchestrator import Orchestrator
from graphsim.rag.communities import CommunityDetector
from graphsim.rag.engine import GraphRAGEngine
from graphsim.rag.extractor import build_knowledge_graph_from_state

# Page config
st.set_page_config(
    page_title="Graphsim - Multi-Agent Simulator",
    page_icon="🔗",
    layout="wide",
    initial_sidebar_state="expanded",
)


def _run_async(coro: Any) -> Any:
    """Run an async coroutine from sync context."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ============================================================================
# Session state initialization
# ============================================================================

def init_session_state() -> None:
    if "orchestrator" not in st.session_state:
        st.session_state.orchestrator = None
    if "scenario_config" not in st.session_state:
        st.session_state.scenario_config = None
    if "simulation_running" not in st.session_state:
        st.session_state.simulation_running = False
    if "current_step" not in st.session_state:
        st.session_state.current_step = "setup"  # setup, configure, simulate, analyze
    if "analysis_result" not in st.session_state:
        st.session_state.analysis_result = None
    if "trait_overrides" not in st.session_state:
        st.session_state.trait_overrides = {}


init_session_state()


# ============================================================================
# Sidebar navigation
# ============================================================================

def render_sidebar() -> str:
    with st.sidebar:
        st.title("Graphsim")
        st.caption("Multi-Agent Simulator")

        st.divider()

        # Navigation
        step = st.radio(
            "Steg",
            options=["setup", "configure", "simulate", "analyze"],
            format_func=lambda x: {
                "setup": "1. Välj scenario",
                "configure": "2. Konfigurera roller",
                "simulate": "3. Kör simulering",
                "analyze": "4. Analys & insikter",
            }[x],
            index=["setup", "configure", "simulate", "analyze"].index(
                st.session_state.current_step
            ),
            key="nav_radio",
        )

        st.divider()

        # Status
        if st.session_state.orchestrator:
            state = st.session_state.orchestrator.state
            st.metric("Scenario", state.metadata.get("title", "")[:25])
            st.metric("Agenter", len(state.active_agent_ids))
            st.metric("Meddelanden", len(state.messages))
            st.metric("Runda", f"{state.current_round}/{state.max_rounds}")

        st.divider()
        st.caption("Graphsim v0.1.0")

    return step


# ============================================================================
# Step 1: Scenario Selection
# ============================================================================

def render_setup() -> None:
    st.header("Välj scenario")

    tab_template, tab_describe, tab_yaml = st.tabs([
        "Välj mall", "Beskriv med text", "Ladda YAML"
    ])

    # --- Tab 1: Templates ---
    with tab_template:
        st.subheader("Scenariomallar")

        # Domain filter
        domains = list(TEMPLATES_BY_DOMAIN.keys())
        selected_domain = st.selectbox(
            "Filtrera på domän",
            options=["Alla"] + domains,
            key="template_domain",
        )

        if selected_domain == "Alla":
            templates = ALL_TEMPLATES
        else:
            templates = TEMPLATES_BY_DOMAIN.get(selected_domain, [])

        # Display templates as cards
        for template in templates:
            with st.container(border=True):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.subheader(template.title)
                    st.caption(f"{template.domain.upper()} | {template.difficulty} | ~{template.estimated_rounds} rundor")
                    st.write(template.description)

                    # Tags
                    st.caption("Taggar: " + ", ".join(template.tags))

                    # Roles
                    with st.expander("Roller"):
                        for role_id in template.suggested_roles:
                            role = get_role(role_id)
                            if role:
                                st.write(f"**{role.name}** - {role.title}")

                    # Events
                    if template.events:
                        with st.expander(f"Händelser ({len(template.events)} st)"):
                            for event in template.events:
                                st.info(f"Runda {event.round_number}: {event.description}")

                with col2:
                    if st.button("Välj", key=f"select_{template.template_id}", use_container_width=True):
                        _load_template(template.template_id)

    # --- Tab 2: Natural language ---
    with tab_describe:
        st.subheader("Beskriv ditt scenario")
        st.write("Skriv en beskrivning av situationen du vill simulera. "
                 "AI:n skapar ett komplett scenario med roller och relationer.")

        description = st.text_area(
            "Scenariobeskrivning",
            height=150,
            placeholder="T.ex: En kommun ska spara 20% på socialförvaltningen. "
                        "Flera chefer, fackliga och politiker har olika intressen...",
        )

        col1, col2, col3 = st.columns(3)
        with col1:
            num_agents = st.slider("Antal agenter", 4, 15, 8)
        with col2:
            num_rounds = st.slider("Antal rundor", 3, 10, 5)
        with col3:
            domain_hint = st.selectbox(
                "Domänledtråd (valfritt)",
                options=["Ingen"] + get_all_domains(),
            )

        if st.button("Generera scenario", type="primary", disabled=not description):
            with st.spinner("Genererar scenario med AI..."):
                try:
                    config = SimulationConfig()
                    orch = Orchestrator(config)
                    llm = orch._get_llm()
                    builder = ScenarioBuilder(llm)
                    scenario = _run_async(builder.build_from_description(
                        description=description,
                        num_agents=num_agents,
                        num_rounds=num_rounds,
                        domain_hint=domain_hint if domain_hint != "Ingen" else None,
                    ))
                    st.session_state.scenario_config = scenario
                    st.session_state.current_step = "configure"
                    st.success(f"Scenario genererat: {scenario.title}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Kunde inte generera scenario: {e}")

    # --- Tab 3: YAML ---
    with tab_yaml:
        st.subheader("Ladda YAML-fil")
        yaml_path = st.text_input(
            "Sökväg till YAML-fil",
            value="scenarios/example_school.yaml",
        )
        if st.button("Ladda", key="load_yaml"):
            try:
                from graphsim.engine.scenario import load_scenario
                scenario = load_scenario(yaml_path)
                st.session_state.scenario_config = scenario
                st.session_state.current_step = "configure"
                st.success(f"Laddat: {scenario.title}")
                st.rerun()
            except Exception as e:
                st.error(f"Kunde inte ladda: {e}")


def _load_template(template_id: str) -> None:
    """Load a scenario from a template."""
    template = get_template(template_id)
    if not template:
        return

    agents = []
    for role_id in template.suggested_roles:
        role = get_role(role_id)
        if role:
            agents.append(role.to_agent_config())

    relationships = [
        RelationshipConfig(
            source=r["source"], target=r["target"], relation_type=r["type"]
        )
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

    st.session_state.scenario_config = scenario
    st.session_state.current_step = "configure"

    # Schedule template events
    st.session_state.template_events = template.events
    st.rerun()


# ============================================================================
# Step 2: Role Configuration
# ============================================================================

def render_configure() -> None:
    scenario = st.session_state.scenario_config
    if not scenario:
        st.warning("Välj ett scenario först.")
        return

    st.header(f"Konfigurera: {scenario.title}")
    st.write(scenario.description)

    # Settings
    col1, col2 = st.columns(2)
    with col1:
        max_rounds = st.slider(
            "Antal rundor",
            min_value=2, max_value=15,
            value=scenario.max_rounds,
            key="config_rounds",
        )
    with col2:
        st.write("")  # Spacing

    st.divider()
    st.subheader("Roller och personligheter")

    # Preset buttons
    st.write("**Snabbinställning:**")
    preset_cols = st.columns(6)
    preset_names = {
        "default": "Standard",
        "change_resistant": "Förändringsmotstånd",
        "stressed_leader": "Stressad ledare",
        "empathic_listener": "Empatisk",
        "bureaucrat": "Byråkrat",
        "maverick": "Rebell",
    }

    for i, (preset_id, preset_label) in enumerate(preset_names.items()):
        with preset_cols[i]:
            if st.button(preset_label, key=f"preset_{preset_id}", use_container_width=True):
                # Apply preset to all agents
                profile = TraitProfile.from_preset(preset_id)
                for agent in scenario.agents:
                    st.session_state.trait_overrides[agent.role_id] = dict(profile.traits)
                st.rerun()

    st.divider()

    # Per-agent configuration
    for agent in scenario.agents:
        with st.expander(f"**{agent.name}** - {agent.title}", expanded=False):
            col_info, col_traits = st.columns([1, 2])

            with col_info:
                st.write("**Ansvar:**")
                for r in agent.responsibilities:
                    st.write(f"- {r}")
                st.write("**Mål:**")
                for g in agent.goals:
                    st.write(f"- {g}")
                if agent.constraints:
                    st.write("**Begränsningar:**")
                    for c in agent.constraints:
                        st.write(f"- {c}")

                # Natural language personality override
                nl_personality = st.text_area(
                    "Fri personlighetsbeskrivning (valfritt)",
                    key=f"nl_{agent.role_id}",
                    height=80,
                    placeholder="T.ex: Extremt stressad, misstror alla...",
                )

            with col_traits:
                st.write("**Personlighetsdrag** (dra i slidern)")
                agent_traits = st.session_state.trait_overrides.get(agent.role_id, {})

                for trait_id, trait_def in TRAIT_DEFINITIONS.items():
                    current_val = agent_traits.get(trait_id, 5.0)
                    new_val = st.slider(
                        trait_def["name_sv"],
                        min_value=0.0, max_value=10.0,
                        value=current_val, step=0.5,
                        help=f"Lågt: {trait_def['low']}\nHögt: {trait_def['high']}",
                        key=f"trait_{agent.role_id}_{trait_id}",
                    )

                    if agent.role_id not in st.session_state.trait_overrides:
                        st.session_state.trait_overrides[agent.role_id] = {}
                    st.session_state.trait_overrides[agent.role_id][trait_id] = new_val

    st.divider()

    # Start simulation button
    if st.button("Starta simulering", type="primary", use_container_width=True):
        _start_simulation(scenario, max_rounds)


def _start_simulation(scenario: ScenarioConfig, max_rounds: int) -> None:
    """Apply trait overrides and start the simulation."""
    # Apply trait overrides to agents
    for agent in scenario.agents:
        traits = st.session_state.trait_overrides.get(agent.role_id, {})
        nl_key = f"nl_{agent.role_id}"
        nl_personality = st.session_state.get(nl_key, "")

        if traits or nl_personality:
            profile = TraitProfile(traits=traits)
            if nl_personality:
                profile.natural_language_description = nl_personality
            agent.personality = profile.to_prompt_description()

    scenario.max_rounds = max_rounds

    # Create orchestrator
    config = SimulationConfig()
    orchestrator = Orchestrator(config)
    orchestrator.load_scenario(scenario)

    # Schedule template events if any
    if hasattr(st.session_state, "template_events") and st.session_state.template_events:
        orchestrator.schedule_events(st.session_state.template_events)

    st.session_state.orchestrator = orchestrator
    st.session_state.current_step = "simulate"
    st.rerun()


# ============================================================================
# Step 3: Simulation Runner
# ============================================================================

def render_simulate() -> None:
    orchestrator = st.session_state.orchestrator
    if not orchestrator or not orchestrator.state:
        st.warning("Ingen simulering laddad.")
        return

    state = orchestrator.state
    st.header(f"Simulering: {state.metadata.get('title', '')}")

    # Controls
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        step_btn = st.button("Kör en runda", type="primary", use_container_width=True)
    with col2:
        run_all = st.button("Kör alla rundor", use_container_width=True)
    with col3:
        analyze_btn = st.button("Analysera nu", use_container_width=True)
    with col4:
        st.metric("Runda", f"{state.current_round}/{state.max_rounds}")

    # Run one step
    if step_btn:
        next_round = state.current_round + 1 if state.messages else 0
        if next_round < state.max_rounds:
            with st.spinner(f"Kör runda {next_round}..."):
                _run_async(orchestrator.run_round(next_round))
            st.rerun()
        else:
            st.info("Simuleringen är klar!")

    # Run all
    if run_all:
        start_round = state.current_round + 1 if state.messages else 0
        progress = st.progress(0, text="Startar simulering...")
        for round_num in range(start_round, state.max_rounds):
            progress.progress(
                (round_num - start_round + 1) / (state.max_rounds - start_round),
                text=f"Runda {round_num + 1}/{state.max_rounds}...",
            )
            _run_async(orchestrator.run_round(round_num))
        progress.progress(1.0, text="Klar!")
        st.rerun()

    # Analyze
    if analyze_btn:
        with st.spinner("Analyserar simuleringen..."):
            analyzer = SimulationAnalyzer(orchestrator._get_llm())
            result = _run_async(analyzer.analyze(state))
            st.session_state.analysis_result = result
        st.session_state.current_step = "analyze"
        st.rerun()

    st.divider()

    # Event injection
    with st.expander("Injicera händelse"):
        event_desc = st.text_area(
            "Beskriv händelsen",
            placeholder="T.ex: En journalist ringer och ställer frågor om ärendet",
            key="event_desc",
        )
        affected = st.multiselect(
            "Berörda agenter",
            options=state.active_agent_ids,
            key="event_agents",
        )
        if st.button("Injicera", disabled=not event_desc):
            from graphsim.engine.templates import EventTrigger
            event = EventTrigger(
                round_number=state.current_round,
                description=event_desc,
                affects_agents=affected,
            )
            orchestrator.inject_event(event)
            st.success("Händelse injicerad!")
            st.rerun()

    st.divider()

    # Message display
    if state.messages:
        _render_messages(state)
    else:
        st.info("Inga meddelanden ännu. Kör första rundan!")


def _render_messages(state: Any) -> None:
    """Render simulation messages grouped by round."""
    # Round selector
    rounds = sorted(set(m.round_number for m in state.messages))
    view_mode = st.radio(
        "Visa",
        ["Alla rundor", "Per runda"],
        horizontal=True,
        key="msg_view",
    )

    if view_mode == "Per runda":
        selected_round = st.select_slider(
            "Runda", options=rounds, value=rounds[-1], key="round_slider"
        )
        messages = [m for m in state.messages if m.round_number == selected_round]
    else:
        messages = state.messages

    # Color map for agents
    colors = [
        "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4",
        "#FFEAA7", "#DDA0DD", "#98D8C8", "#F7DC6F",
        "#BB8FCE", "#85C1E9", "#F0B27A", "#82E0AA",
    ]
    agent_colors = {}
    for i, agent_id in enumerate(state.active_agent_ids):
        agent_colors[agent_id] = colors[i % len(colors)]

    current_round = -1
    for msg in messages:
        if msg.round_number != current_round:
            current_round = msg.round_number
            st.subheader(f"Runda {current_round}")

        if msg.agent_id == "system":
            st.warning(msg.content)
        else:
            color = agent_colors.get(msg.agent_id, "#CCCCCC")
            with st.container(border=True):
                st.markdown(
                    f"<div style='border-left: 4px solid {color}; padding-left: 12px;'>"
                    f"<strong>{msg.role}</strong> <em>({msg.agent_id})</em>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
                st.write(msg.content)


# ============================================================================
# Step 4: Analysis & Insights
# ============================================================================

def render_analyze() -> None:
    orchestrator = st.session_state.orchestrator
    if not orchestrator or not orchestrator.state:
        st.warning("Ingen simulering att analysera.")
        return

    state = orchestrator.state
    st.header("Analys & insikter")

    # Run analysis if not done yet
    if not st.session_state.analysis_result:
        if st.button("Kör analys", type="primary"):
            with st.spinner("Analyserar..."):
                analyzer = SimulationAnalyzer(orchestrator._get_llm())
                result = _run_async(analyzer.analyze(state))
                st.session_state.analysis_result = result
            st.rerun()
        st.info("Klicka ovan för att köra analysen.")
        # Still show GraphRAG even without LLM analysis
        _render_graphrag_analysis(state)
        return

    analysis = st.session_state.analysis_result

    # Tabs
    tab_overview, tab_graph, tab_details, tab_export = st.tabs([
        "Översikt", "Grafanalys", "Detaljer", "Exportera"
    ])

    with tab_overview:
        _render_analysis_overview(analysis)

    with tab_graph:
        _render_graphrag_analysis(state)

    with tab_details:
        _render_analysis_details(analysis)

    with tab_export:
        _render_export(state, analysis)


def _render_analysis_overview(analysis: Any) -> None:
    """Render analysis overview with key metrics."""
    # Risk level banner
    risk_colors = {
        "low": "green", "medium": "orange",
        "high": "red", "critical": "red",
    }
    risk_color = risk_colors.get(analysis.overall_risk_level, "gray")
    st.markdown(
        f"### Risknivå: :{risk_color}[{analysis.overall_risk_level.upper()}]"
    )

    st.write(f"**Sammanfattning:** {analysis.summary}")

    st.divider()

    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Konflikter", len(analysis.conflicts))
    with col2:
        st.metric("Informationsluckor", len(analysis.information_gaps))
    with col3:
        st.metric("Beslut bedömda", len(analysis.decision_assessments))
    with col4:
        st.metric("Systemiska mönster", len(analysis.systemic_patterns))

    st.divider()

    # Key insights
    if analysis.key_insights:
        st.subheader("Nyckelinsikter")
        for i, insight in enumerate(analysis.key_insights, 1):
            st.info(f"**{i}.** {insight}")

    # Recommendations
    if analysis.recommendations:
        st.subheader("Rekommendationer")
        for i, rec in enumerate(analysis.recommendations, 1):
            st.success(f"**{i}.** {rec}")


def _render_graphrag_analysis(state: Any) -> None:
    """Render GraphRAG visualizations."""
    st.subheader("Kunskapsgraf & communityanalys")

    kg = build_knowledge_graph_from_state(state)
    engine = GraphRAGEngine()
    stats = engine.analyze_graph_structure(kg)

    # Graph stats
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Noder", stats["nodes"])
    with col2:
        st.metric("Kanter", stats["edges"])
    with col3:
        st.metric("Densitet", f"{stats.get('density', 0):.3f}")
    with col4:
        st.metric("Komponenter", stats.get("connected_components", 0))

    # Entity type distribution
    if stats.get("entity_types"):
        st.subheader("Entitetstyper")
        fig = go.Figure(data=[go.Pie(
            labels=list(stats["entity_types"].keys()),
            values=list(stats["entity_types"].values()),
            hole=0.4,
        )])
        fig.update_layout(height=300, margin=dict(t=20, b=20, l=20, r=20))
        st.plotly_chart(fig, use_container_width=True)

    # Relationship types
    if stats.get("relationship_types"):
        st.subheader("Relationstyper")
        rel_types = stats["relationship_types"]
        fig = go.Figure(data=[go.Bar(
            x=list(rel_types.values()),
            y=list(rel_types.keys()),
            orientation='h',
            marker_color='#4ECDC4',
        )])
        fig.update_layout(height=300, margin=dict(t=20, b=20, l=20, r=20))
        st.plotly_chart(fig, use_container_width=True)

    # Community detection
    st.subheader("Community-analys (klusterdetektion)")
    communities = engine.detect_communities(kg)
    detector = CommunityDetector()
    communities = detector.generate_local_summaries(kg, communities)

    st.write(f"**{communities.total_communities} kluster** hittade "
             f"(modularitet: {communities.modularity:.3f})")

    for community in communities.communities:
        with st.container(border=True):
            st.write(f"**{community.community_id}** ({community.size} noder)")
            st.write(community.summary)
            if community.key_entities:
                st.caption("Nyckelentiteter: " + ", ".join(community.key_entities[:5]))

    # Silo detection
    silos = engine.find_silos(kg, communities.communities)
    if silos:
        st.subheader("Informationssilos")
        st.warning(f"{len(silos)} potentiella silos identifierade")
        for silo in silos:
            st.error(silo.get("description", ""))

    # Graph visualization
    st.subheader("Grafvisualisering")
    _render_graph_plotly(kg, state)


def _render_graph_plotly(kg: Any, state: Any) -> None:
    """Render knowledge graph using Plotly."""
    import networkx as nx

    if kg.number_of_nodes() == 0:
        st.info("Ingen graf att visa ännu.")
        return

    # Layout
    pos = nx.spring_layout(kg, seed=42, k=2)

    # Build edges
    edge_x, edge_y = [], []
    for src, tgt in kg.edges():
        if src in pos and tgt in pos:
            x0, y0 = pos[src]
            x1, y1 = pos[tgt]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])

    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=0.5, color='#888'),
        hoverinfo='none',
        mode='lines',
    )

    # Build nodes
    node_x, node_y, node_text, node_color, node_size = [], [], [], [], []
    color_map = {
        "person": "#FF6B6B",
        "action": "#4ECDC4",
        "decision": "#FFEAA7",
        "event": "#DDA0DD",
        "information": "#85C1E9",
    }

    for node_id in kg.nodes():
        if node_id not in pos:
            continue
        x, y = pos[node_id]
        node_x.append(x)
        node_y.append(y)
        data = kg.nodes[node_id]
        entity_type = data.get("entity_type", "unknown")
        label = data.get("label", node_id)
        if len(label) > 50:
            label = label[:50] + "..."
        node_text.append(f"{label}<br>({entity_type})")
        node_color.append(color_map.get(entity_type, "#CCCCCC"))
        node_size.append(20 if entity_type == "person" else 10)

    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode='markers+text',
        hoverinfo='text',
        text=[t.split("<br>")[0][:20] for t in node_text],
        textposition="top center",
        textfont=dict(size=8),
        hovertext=node_text,
        marker=dict(
            color=node_color,
            size=node_size,
            line_width=1,
            line_color='white',
        ),
    )

    fig = go.Figure(
        data=[edge_trace, node_trace],
        layout=go.Layout(
            showlegend=False,
            hovermode='closest',
            margin=dict(b=20, l=5, r=5, t=40),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            height=500,
        ),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Legend
    st.caption(
        "🔴 Person | 🟢 Åtgärd | 🟡 Beslut | 🟣 Händelse | 🔵 Information"
    )


def _render_analysis_details(analysis: Any) -> None:
    """Render detailed analysis sections."""
    # Conflicts
    if analysis.conflicts:
        st.subheader("Konflikter")
        for conflict in analysis.conflicts:
            severity_icon = {"low": "🟡", "medium": "🟠", "high": "🔴"}.get(
                conflict.severity, "⚪"
            )
            with st.container(border=True):
                st.write(f"{severity_icon} **{conflict.severity.upper()}**: {conflict.description}")
                st.caption(f"Involverade: {', '.join(conflict.agents_involved)}")

    # Information gaps
    if analysis.information_gaps:
        st.subheader("Informationsluckor")
        for gap in analysis.information_gaps:
            with st.container(border=True):
                st.write(f"**{gap.who_lacked}** saknade: {gap.what_was_missing}")
                st.write(f"Påverkan: {gap.impact}")
                if gap.could_have_been_shared_by:
                    st.caption(f"Kunde delats av: {gap.could_have_been_shared_by}")

    # Decision assessments
    if analysis.decision_assessments:
        st.subheader("Beslutsbedömningar")
        for dec in analysis.decision_assessments:
            badge = {"reasonable": "✅", "risky": "⚠️", "problematic": "❌"}.get(
                dec.assessment, "❓"
            )
            with st.container(border=True):
                st.write(f"{badge} **{dec.decision}** (av {dec.made_by})")
                st.write(dec.reasoning)
                if dec.alternatives:
                    st.caption(f"Alternativ: {', '.join(dec.alternatives)}")

    # Systemic patterns
    if analysis.systemic_patterns:
        st.subheader("Systemiska mönster")
        for pattern in analysis.systemic_patterns:
            with st.container(border=True):
                st.write(f"**{pattern.pattern}**")
                st.write(f"Belägg: {pattern.evidence}")
                st.success(f"Rekommendation: {pattern.recommendation}")


def _render_export(state: Any, analysis: Any) -> None:
    """Render export options."""
    st.subheader("Exportera rapport")

    exporter = ReportExporter()

    col1, col2 = st.columns(2)

    with col1:
        st.write("**Markdown-rapport**")
        md_content = exporter.to_markdown(state, analysis)
        st.download_button(
            label="Ladda ner Markdown",
            data=md_content,
            file_name=f"rapport_{state.scenario_id}.md",
            mime="text/markdown",
            use_container_width=True,
        )

    with col2:
        st.write("**JSON-rapport**")
        json_content = exporter.to_json(state, analysis)
        st.download_button(
            label="Ladda ner JSON",
            data=json_content,
            file_name=f"rapport_{state.scenario_id}.json",
            mime="application/json",
            use_container_width=True,
        )

    st.divider()

    # Preview
    with st.expander("Förhandsgranska Markdown-rapport"):
        st.markdown(md_content)


# ============================================================================
# Main
# ============================================================================

def main() -> None:
    step = render_sidebar()
    st.session_state.current_step = step

    if step == "setup":
        render_setup()
    elif step == "configure":
        render_configure()
    elif step == "simulate":
        render_simulate()
    elif step == "analyze":
        render_analyze()


if __name__ == "__main__":
    main()
