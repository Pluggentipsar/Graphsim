"""Tests for the event injection system."""

from graphsim.engine.events import EventManager
from graphsim.engine.state import SimulationState
from graphsim.engine.templates import EventTrigger


def _make_state() -> SimulationState:
    return SimulationState(scenario_id="test", current_round=0, max_rounds=5)


def test_schedule_event():
    mgr = EventManager()
    event = EventTrigger(
        round_number=2,
        description="Något händer",
        affects_agents=["rektor"],
    )
    mgr.schedule(event)
    assert len(mgr.pending_events) == 1


def test_schedule_multiple_sorted():
    mgr = EventManager()
    mgr.schedule(EventTrigger(round_number=3, description="Sen"))
    mgr.schedule(EventTrigger(round_number=1, description="Tidig"))
    mgr.schedule(EventTrigger(round_number=2, description="Mellan"))

    assert mgr.pending_events[0].round_number == 1
    assert mgr.pending_events[1].round_number == 2
    assert mgr.pending_events[2].round_number == 3


def test_process_round():
    mgr = EventManager()
    mgr.schedule(EventTrigger(
        round_number=1,
        description="Händelse i runda 1",
        affects_agents=["kurator"],
        new_information={"kurator": "Hemlig info"},
    ))
    mgr.schedule(EventTrigger(round_number=2, description="Händelse i runda 2"))

    state = _make_state()
    outcomes = mgr.process_round(state, 1)

    assert len(outcomes) == 1
    assert outcomes[0].event.description == "Händelse i runda 1"
    assert outcomes[0].agents_notified == ["kurator"]
    # System message + info message
    assert outcomes[0].messages_injected == 2

    # State should have messages
    assert len(state.messages) == 2
    assert state.messages[0].content == "[HÄNDELSE] Händelse i runda 1"
    assert state.messages[1].visible_to == ["kurator"]

    # Round 2 event should still be pending
    assert len(mgr.pending_events) == 1


def test_inject_now():
    mgr = EventManager()
    state = _make_state()
    state.current_round = 3

    event = EventTrigger(
        round_number=0,  # Will be overridden
        description="Akut händelse",
        affects_agents=["rektor", "larare"],
    )
    outcome = mgr.inject_now(state, event)

    assert outcome.event.round_number == 3
    assert len(state.messages) == 1
    assert "rektor" in state.active_agent_ids
    assert "larare" in state.active_agent_ids


def test_get_events_for_round():
    mgr = EventManager()
    mgr.schedule(EventTrigger(round_number=2, description="A"))
    mgr.schedule(EventTrigger(round_number=2, description="B"))
    mgr.schedule(EventTrigger(round_number=3, description="C"))

    events = mgr.get_events_for_round(2)
    assert len(events) == 2

    events = mgr.get_events_for_round(3)
    assert len(events) == 1
