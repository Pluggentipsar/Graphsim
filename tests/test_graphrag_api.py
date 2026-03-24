"""Tests for GraphRAG API endpoints."""

from fastapi.testclient import TestClient

from graphsim.api.app import app

client = TestClient(app)


def _create_simulation() -> str:
    """Helper to create a simulation and return its ID."""
    response = client.post("/api/simulations", json={
        "scenario_yaml_path": "scenarios/example_school.yaml",
    })
    return response.json()["simulation_id"]


def test_extract_knowledge_graph():
    sim_id = _create_simulation()
    response = client.post(f"/api/simulations/{sim_id}/graphrag/extract")
    assert response.status_code == 200
    data = response.json()
    assert data["nodes"] > 0
    assert "graph_stats" in data


def test_detect_communities():
    sim_id = _create_simulation()
    response = client.post(f"/api/simulations/{sim_id}/graphrag/communities")
    assert response.status_code == 200
    data = response.json()
    assert "total_communities" in data
    assert "communities" in data


def test_detect_silos():
    sim_id = _create_simulation()
    response = client.post(f"/api/simulations/{sim_id}/graphrag/silos")
    assert response.status_code == 200
    data = response.json()
    assert "total_silos" in data
    assert "silos" in data


def test_archive_simulation():
    sim_id = _create_simulation()
    response = client.post(f"/api/simulations/{sim_id}/graphrag/archive")
    assert response.status_code == 200
    data = response.json()
    assert data["archived"] is True
    assert data["simulation_id"] == sim_id


def test_list_archives():
    response = client.get("/api/graphrag/archives")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_precedents():
    response = client.get("/api/graphrag/precedents?scenario_title=frånvaro")
    assert response.status_code == 200
    data = response.json()
    assert "precedents" in data
    assert "total_archives" in data


def test_get_patterns():
    response = client.get("/api/graphrag/patterns")
    assert response.status_code == 200
    data = response.json()
    assert "total_patterns" in data
    assert "patterns" in data


def test_extract_not_found():
    response = client.post("/api/simulations/nonexistent/graphrag/extract")
    assert response.status_code == 404
