"""Event injection system for dynamic simulations.

Events can be pre-scheduled (from templates) or injected live via the API.
They change the simulation mid-flow: new information, changed circumstances,
external pressure, etc.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from graphsim.engine.state import AgentMessage, SimulationState
from graphsim.engine.templates import EventTrigger


class EventOutcome(BaseModel):
    """What happened when an event was processed."""

    event: EventTrigger
    messages_injected: int = 0
    agents_notified: list[str] = Field(default_factory=list)


class EventManager:
    """Manages scheduled and ad-hoc events during a simulation."""

    def __init__(self) -> None:
        self._scheduled: list[EventTrigger] = []
        self._processed: list[EventOutcome] = []

    def schedule(self, event: EventTrigger) -> None:
        """Schedule an event for a specific round."""
        self._scheduled.append(event)
        self._scheduled.sort(key=lambda e: e.round_number)

    def schedule_many(self, events: list[EventTrigger]) -> None:
        """Schedule multiple events."""
        for event in events:
            self.schedule(event)

    def inject_now(self, state: SimulationState, event: EventTrigger) -> EventOutcome:
        """Immediately inject an event into the current simulation state."""
        event = event.model_copy(update={"round_number": state.current_round})
        return self._process_event(state, event)

    def process_round(self, state: SimulationState, round_number: int) -> list[EventOutcome]:
        """Process all events scheduled for a given round."""
        outcomes = []
        remaining = []

        for event in self._scheduled:
            if event.round_number == round_number:
                outcome = self._process_event(state, event)
                outcomes.append(outcome)
            elif event.round_number > round_number:
                remaining.append(event)
            # Events from past rounds that weren't processed are dropped

        self._scheduled = remaining
        return outcomes

    def _process_event(self, state: SimulationState, event: EventTrigger) -> EventOutcome:
        """Process a single event: inject information into the simulation state."""
        agents_notified = []

        # Inject the event as a system message visible to affected agents
        event_message = AgentMessage(
            agent_id="system",
            role="Händelse",
            content=f"[HÄNDELSE] {event.description}",
            round_number=event.round_number,
            visible_to=event.affects_agents if event.affects_agents else [],
            metadata={"event": True},
        )
        state.add_message(event_message)

        # Inject agent-specific information
        for agent_id, info in event.new_information.items():
            info_message = AgentMessage(
                agent_id="system",
                role="Information",
                content=f"[NY INFORMATION] {info}",
                round_number=event.round_number,
                visible_to=[agent_id],
                metadata={"event_info": True, "for_agent": agent_id},
            )
            state.add_message(info_message)
            agents_notified.append(agent_id)

        # Make sure affected agents are active
        for agent_id in event.affects_agents:
            if agent_id not in state.active_agent_ids:
                state.active_agent_ids.append(agent_id)
            if agent_id not in agents_notified:
                agents_notified.append(agent_id)

        outcome = EventOutcome(
            event=event,
            messages_injected=1 + len(event.new_information),
            agents_notified=agents_notified,
        )
        self._processed.append(outcome)
        return outcome

    @property
    def pending_events(self) -> list[EventTrigger]:
        """Events still waiting to be processed."""
        return list(self._scheduled)

    @property
    def processed_events(self) -> list[EventOutcome]:
        """Events that have already been processed."""
        return list(self._processed)

    def get_events_for_round(self, round_number: int) -> list[EventTrigger]:
        """Preview events scheduled for a specific round."""
        return [e for e in self._scheduled if e.round_number == round_number]
