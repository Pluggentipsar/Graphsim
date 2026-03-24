"""Tests for the export/report functionality."""

import json

from graphsim.analysis.analyzer import AnalysisResult, ConflictPoint, InformationGap
from graphsim.analysis.export import ReportExporter
from graphsim.engine.state import AgentMessage, SimulationState


def _make_state() -> SimulationState:
    state = SimulationState(
        scenario_id="test_scenario",
        current_round=2,
        max_rounds=5,
        active_agent_ids=["rektor", "kurator"],
        metadata={
            "title": "Testscenario",
            "description": "Ett test",
            "initial_event": "Något hände",
        },
    )
    state.add_message(AgentMessage(
        agent_id="rektor", role="Rektor", content="Hej alla",
        round_number=0,
    ))
    state.add_message(AgentMessage(
        agent_id="kurator", role="Kurator", content="Jag instämmer",
        round_number=0,
    ))
    state.add_message(AgentMessage(
        agent_id="rektor", role="Rektor", content="Vi beslutar X",
        round_number=1,
    ))
    return state


def _make_analysis() -> AnalysisResult:
    return AnalysisResult(
        summary="En sammanfattning av simuleringen",
        conflicts=[
            ConflictPoint(
                agents_involved=["rektor", "kurator"],
                description="Oenighet om åtgärder",
                severity="medium",
            )
        ],
        information_gaps=[
            InformationGap(
                who_lacked="kurator",
                what_was_missing="Elevens hemförhållanden",
                impact="Kunde inte göra fullständig bedömning",
                could_have_been_shared_by="larare",
            )
        ],
        key_insights=["Bättre kommunikation behövs"],
        recommendations=["Inför rutin för informationsdelning"],
        overall_risk_level="medium",
    )


def test_export_markdown():
    exporter = ReportExporter()
    state = _make_state()
    md = exporter.to_markdown(state)

    assert "# Simuleringsrapport: Testscenario" in md
    assert "Hej alla" in md
    assert "Runda 0" in md
    assert "Runda 1" in md


def test_export_markdown_with_analysis():
    exporter = ReportExporter()
    state = _make_state()
    analysis = _make_analysis()
    md = exporter.to_markdown(state, analysis)

    assert "## Analys" in md
    assert "Oenighet om åtgärder" in md
    assert "Elevens hemförhållanden" in md
    assert "Bättre kommunikation behövs" in md


def test_export_json():
    exporter = ReportExporter()
    state = _make_state()
    json_str = exporter.to_json(state)

    data = json.loads(json_str)
    assert data["metadata"]["scenario_id"] == "test_scenario"
    assert data["metadata"]["total_rounds"] == 3
    assert data["metadata"]["total_messages"] == 3
    assert "0" in data["rounds"]
    assert len(data["rounds"]["0"]) == 2


def test_export_json_with_analysis():
    exporter = ReportExporter()
    state = _make_state()
    analysis = _make_analysis()
    json_str = exporter.to_json(state, analysis)

    data = json.loads(json_str)
    assert "analysis" in data
    assert data["analysis"]["overall_risk_level"] == "medium"
    assert len(data["analysis"]["conflicts"]) == 1
