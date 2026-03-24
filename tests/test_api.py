"""Tests for the API endpoints (non-LLM endpoints only)."""

import pytest
from fastapi.testclient import TestClient

from graphsim.api.app import app

client = TestClient(app)


def test_list_roles():
    response = client.get("/api/roles")
    assert response.status_code == 200
    roles = response.json()
    assert len(roles) >= 15
    assert all("role_id" in r for r in roles)


def test_list_roles_by_domain():
    response = client.get("/api/roles?domain=skola")
    assert response.status_code == 200
    roles = response.json()
    assert len(roles) >= 5
    assert all(r["domain"] == "skola" for r in roles)


def test_list_roles_search():
    response = client.get("/api/roles?query=kurator")
    assert response.status_code == 200
    roles = response.json()
    assert any(r["role_id"] == "kurator" for r in roles)


def test_get_role_detail():
    response = client.get("/api/roles/rektor")
    assert response.status_code == 200
    role = response.json()
    assert role["role_id"] == "rektor"
    assert "suggested_traits" in role
    assert len(role["suggested_traits"]) > 0


def test_get_role_not_found():
    response = client.get("/api/roles/nonexistent")
    assert response.status_code == 404


def test_list_domains():
    response = client.get("/api/domains")
    assert response.status_code == 200
    domains = response.json()
    domain_names = [d["domain"] for d in domains]
    assert "skola" in domain_names
    assert "socialtjänst" in domain_names


def test_list_traits():
    response = client.get("/api/traits")
    assert response.status_code == 200
    traits = response.json()
    assert len(traits) >= 10
    assert all("id" in t and "name" in t for t in traits)


def test_list_trait_presets():
    response = client.get("/api/traits/presets")
    assert response.status_code == 200
    presets = response.json()
    assert "change_resistant" in presets
    assert "maverick" in presets


def test_get_trait_preset():
    response = client.get("/api/traits/presets/change_resistant")
    assert response.status_code == 200
    data = response.json()
    assert data["preset_id"] == "change_resistant"
    assert data["traits"]["openness_to_change"] == 2


def test_create_simulation_with_yaml():
    response = client.post("/api/simulations", json={
        "scenario_yaml_path": "scenarios/example_school.yaml",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "created"
    assert data["num_agents"] == 6
    assert "simulation_id" in data


def test_create_simulation_no_input():
    response = client.post("/api/simulations", json={})
    assert response.status_code == 400


# ============================================================================
# Template endpoints
# ============================================================================

def test_list_templates():
    response = client.get("/api/templates")
    assert response.status_code == 200
    templates = response.json()
    assert len(templates) >= 8
    assert all("template_id" in t for t in templates)


def test_list_templates_by_domain():
    response = client.get("/api/templates?domain=skola")
    assert response.status_code == 200
    templates = response.json()
    assert len(templates) >= 3
    assert all(t["domain"] == "skola" for t in templates)


def test_get_template_detail():
    response = client.get("/api/templates/school_absence")
    assert response.status_code == 200
    data = response.json()
    assert data["template_id"] == "school_absence"
    assert "events" in data
    assert len(data["events"]) >= 2


def test_get_template_not_found():
    response = client.get("/api/templates/nonexistent")
    assert response.status_code == 404


def test_create_simulation_from_template():
    response = client.post("/api/simulations/from-template?template_id=school_absence")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "created"
    assert data["num_agents"] >= 5
    assert "Elev med hög frånvaro" in data["scenario_title"]


def test_create_simulation_from_template_not_found():
    response = client.post("/api/simulations/from-template?template_id=nonexistent")
    assert response.status_code == 404


# ============================================================================
# Event endpoints
# ============================================================================

def test_inject_event():
    # First create a simulation
    create_resp = client.post("/api/simulations", json={
        "scenario_yaml_path": "scenarios/example_school.yaml",
    })
    sim_id = create_resp.json()["simulation_id"]

    # Inject event
    response = client.post(f"/api/simulations/{sim_id}/events", json={
        "description": "Eleven ringer hem",
        "affects_agents": ["vardnadshavare"],
        "new_information": {"vardnadshavare": "Eleven har ringt hem och gråter"},
    })
    assert response.status_code == 200
    assert response.json()["status"] == "injected"


def test_list_events():
    create_resp = client.post("/api/simulations", json={
        "scenario_yaml_path": "scenarios/example_school.yaml",
    })
    sim_id = create_resp.json()["simulation_id"]

    response = client.get(f"/api/simulations/{sim_id}/events")
    assert response.status_code == 200
    data = response.json()
    assert "pending" in data
    assert "processed" in data


# ============================================================================
# Export endpoints
# ============================================================================

def test_export_markdown():
    create_resp = client.post("/api/simulations", json={
        "scenario_yaml_path": "scenarios/example_school.yaml",
    })
    sim_id = create_resp.json()["simulation_id"]

    response = client.post(f"/api/simulations/{sim_id}/export", json={"format": "markdown"})
    assert response.status_code == 200
    assert "Simuleringsrapport" in response.text


def test_export_json():
    create_resp = client.post("/api/simulations", json={
        "scenario_yaml_path": "scenarios/example_school.yaml",
    })
    sim_id = create_resp.json()["simulation_id"]

    response = client.post(f"/api/simulations/{sim_id}/export", json={"format": "json"})
    assert response.status_code == 200
    import json
    data = json.loads(response.text)
    assert "metadata" in data
