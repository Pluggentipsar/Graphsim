"""Central simulation orchestrator - controls agent activation and turn flow."""

from __future__ import annotations

import asyncio
from typing import Any

from langchain_anthropic import ChatAnthropic
from rich.console import Console
from rich.panel import Panel

from graphsim.agents.base import AgentContext, BaseAgent
from graphsim.agents.registry import AgentRegistry
from graphsim.config import LLMProvider, SimulationConfig
from graphsim.engine.events import EventManager
from graphsim.engine.scenario import ScenarioConfig, load_scenario
from graphsim.engine.scoping import InformationScope
from graphsim.engine.state import AgentMessage, SimulationState
from graphsim.engine.templates import EventTrigger
from graphsim.graph.models import EdgeType, GraphEdge, GraphNode, NodeType
from graphsim.graph.queries import find_collaborators
from graphsim.graph.store import GraphStore

console = Console()


class Orchestrator:
    """Orchestrates a multi-agent simulation.

    Manages the simulation loop: selecting active agents each round,
    providing them with scoped information, collecting their responses,
    and updating the graph state.
    """

    def __init__(
        self,
        config: SimulationConfig | None = None,
        graphrag_engine: Any | None = None,
    ) -> None:
        self.config = config or SimulationConfig()
        self.registry: AgentRegistry | None = None
        self.graph: GraphStore = GraphStore()
        self.state: SimulationState | None = None
        self.event_manager: EventManager = EventManager()
        self._scope: InformationScope | None = None
        self._graphrag = graphrag_engine  # Optional GraphRAGEngine
        self._llm: Any = None

    def _get_llm(self) -> Any:
        if self._llm is None:
            if self.config.llm.provider == LLMProvider.ANTHROPIC:
                self._llm = ChatAnthropic(
                    model=self.config.llm.model,
                    temperature=self.config.llm.temperature,
                    max_tokens=self.config.llm.max_tokens,
                )
            else:
                raise ValueError(f"Unsupported LLM provider: {self.config.llm.provider}")
        return self._llm

    def load_scenario(self, scenario: ScenarioConfig | str) -> None:
        """Load a scenario and set up the simulation."""
        if isinstance(scenario, str):
            scenario = load_scenario(scenario)

        # Create agent registry
        self.registry = AgentRegistry.from_scenario(scenario)

        # Build graph from scenario
        self._build_graph(scenario)

        # Initialize information scoping
        self._scope = InformationScope(self.graph)

        # Initialize state
        self.state = SimulationState(
            scenario_id=scenario.scenario_id,
            max_rounds=scenario.max_rounds,
            active_agent_ids=[a.config.role_id for a in self.registry.get_all()],
            metadata={
                "title": scenario.title,
                "description": scenario.description,
                "initial_event": scenario.initial_event,
                "decision_points": scenario.decision_points,
            },
        )

    def schedule_events(self, events: list[EventTrigger]) -> None:
        """Schedule events for the simulation."""
        self.event_manager.schedule_many(events)

    def inject_event(self, event: EventTrigger) -> None:
        """Inject an event into the current round immediately."""
        if not self.state:
            raise RuntimeError("No simulation state loaded")
        self.event_manager.inject_now(self.state, event)

    def _build_graph(self, scenario: ScenarioConfig) -> None:
        """Build the graph from a scenario configuration."""
        for agent_config in scenario.agents:
            self.graph.add_node(GraphNode(
                node_id=agent_config.role_id,
                node_type=NodeType.PERSON,
                label=f"{agent_config.name} ({agent_config.title})",
                properties={
                    "information_level": agent_config.information_level,
                },
            ))

        for rel in scenario.relationships:
            self.graph.add_edge(GraphEdge(
                source_id=rel.source,
                target_id=rel.target,
                edge_type=EdgeType(rel.relation_type),
                properties=rel.properties,
            ))

    def _select_active_agents(self, round_number: int) -> list[str]:
        """Select which agents should be active this round."""
        if not self.state:
            return []

        # Round 0: all agents
        if round_number == 0:
            return self.state.active_agent_ids

        # Find agents affected by recent messages and events
        recent_messages = [
            m for m in self.state.messages if m.round_number == round_number - 1
        ]
        active = set()
        for msg in recent_messages:
            if msg.agent_id == "system":
                # Event messages: activate affected agents
                if msg.visible_to:
                    active.update(msg.visible_to)
                continue
            active.add(msg.agent_id)
            for collab_id in find_collaborators(self.graph, msg.agent_id):
                active.add(collab_id)

        # Check for events in this round that should wake agents
        upcoming = self.event_manager.get_events_for_round(round_number)
        for event in upcoming:
            active.update(event.affects_agents)

        # Always include agents with pending decisions
        if self.state.pending_actions:
            for action in self.state.pending_actions:
                if "agent_id" in action:
                    active.add(action["agent_id"])

        return list(active) if active else self.state.active_agent_ids

    def _build_agent_context(self, agent: BaseAgent, round_number: int) -> AgentContext:
        """Build the information context for an agent's turn."""
        if not self.state:
            raise RuntimeError("No simulation state loaded")

        # Use information scoping if available
        if self._scope:
            agent_node = self.graph.get_node(agent.agent_id)
            info_level = (
                agent_node.properties.get("information_level", "medium")
                if agent_node
                else "medium"
            )
            visible_messages = self._scope.get_visible_messages(
                agent.agent_id, self.state, info_level
            )
        else:
            visible_messages = self.state.messages_visible_to(agent.agent_id)

        relationships = self.graph.get_relationships_for_agent(agent.agent_id)

        pending = []
        if self.state.metadata.get("decision_points"):
            pending = self.state.metadata["decision_points"]

        scenario_context = ""
        if round_number == 0:
            scenario_context = (
                f"{self.state.metadata.get('description', '')}\n\n"
                f"Händelse: {self.state.metadata.get('initial_event', '')}"
            )

        # Add secrecy rules to context
        if self._scope:
            secrecy_prompt = self._scope.get_secrecy_prompt(agent.agent_id)
            if secrecy_prompt:
                scenario_context += f"\n\n{secrecy_prompt}"

        # Add GraphRAG context (precedents, community patterns)
        if self._graphrag and round_number == 0:
            from graphsim.rag.extractor import build_knowledge_graph_from_state

            # Only build KG context if we have messages or historical data
            kg = build_knowledge_graph_from_state(self.state)
            communities = self._graphrag.detect_communities(kg)
            rag_context = self._graphrag.get_agent_context(
                agent.agent_id,
                kg,
                communities.communities,
                scenario_title=self.state.metadata.get("title", ""),
            )
            if rag_context:
                scenario_context += f"\n\n{rag_context}"

        # Add document context (role-specific perspective of uploaded documents)
        if self.state.document_context and agent.agent_id in self.state.document_context:
            doc_perspective = self.state.document_context[agent.agent_id]
            scenario_context += (
                f"\n\nDokumentunderlag (din bild av dokumentet):\n{doc_perspective}"
            )

        return AgentContext(
            round_number=round_number,
            visible_messages=visible_messages,
            relationships=relationships,
            pending_decisions=pending,
            scenario_context=scenario_context,
        )

    async def _run_agent_turn(self, agent: BaseAgent, round_number: int) -> AgentMessage:
        """Run a single agent's turn."""
        context = self._build_agent_context(agent, round_number)
        llm = self._get_llm()
        message = await agent.act(self.state, context, llm)
        return message

    async def run_round(self, round_number: int) -> list[AgentMessage]:
        """Execute a single simulation round."""
        if not self.state or not self.registry:
            raise RuntimeError("Simulation not loaded")

        # Process scheduled events for this round
        event_outcomes = self.event_manager.process_round(self.state, round_number)
        if event_outcomes and self.config.verbose:
            for outcome in event_outcomes:
                console.print(
                    f"  [bold yellow]HÄNDELSE:[/bold yellow] {outcome.event.description}"
                )

        active_ids = self._select_active_agents(round_number)
        agents = self.registry.get_by_ids(active_ids)

        if self.config.verbose:
            console.print(
                Panel(
                    f"Runda {round_number} | Aktiva agenter: {len(agents)}",
                    title="[bold blue]Simulation[/bold blue]",
                )
            )

        # Run agents concurrently (up to max_concurrent)
        semaphore = asyncio.Semaphore(self.config.max_concurrent_agents)

        async def run_with_semaphore(agent: BaseAgent) -> AgentMessage:
            async with semaphore:
                return await self._run_agent_turn(agent, round_number)

        tasks = [run_with_semaphore(agent) for agent in agents]
        messages = await asyncio.gather(*tasks)

        # Add messages to state
        for msg in messages:
            self.state.add_message(msg)
            if self.config.verbose:
                console.print(f"  [{msg.role}] {msg.content[:200]}...")

        self.state.current_round = round_number
        return list(messages)

    async def run(self) -> SimulationState:
        """Run the full simulation."""
        if not self.state:
            raise RuntimeError("No scenario loaded. Call load_scenario() first.")

        console.print(
            Panel(
                f"[bold]{self.state.metadata.get('title', 'Simulation')}[/bold]\n"
                f"{self.state.metadata.get('description', '')}",
                title="[bold green]Graphsim Starter[/bold green]",
            )
        )

        for round_num in range(self.state.max_rounds):
            await self.run_round(round_num)

            if self.state.finished:
                break

        console.print("[bold green]Simulation klar![/bold green]")
        return self.state
