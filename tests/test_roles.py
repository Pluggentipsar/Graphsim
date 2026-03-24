"""Tests for the role library."""

from graphsim.agents.roles.library import (
    ALL_ROLES,
    get_all_domains,
    get_role,
    get_roles_by_domain,
    search_roles,
)


def test_all_roles_exist():
    assert len(ALL_ROLES) >= 15  # We defined 19 roles


def test_get_role():
    role = get_role("rektor")
    assert role is not None
    assert role.title == "Rektor"
    assert role.domain == "skola"


def test_get_role_not_found():
    assert get_role("nonexistent") is None


def test_get_roles_by_domain():
    school_roles = get_roles_by_domain("skola")
    assert len(school_roles) >= 5
    assert all(r.domain == "skola" for r in school_roles)


def test_get_all_domains():
    domains = get_all_domains()
    assert "skola" in domains
    assert "socialtjänst" in domains
    assert "vård" in domains


def test_search_roles():
    results = search_roles("kurator")
    assert len(results) >= 1
    assert any(r.role_id == "kurator" for r in results)


def test_search_roles_by_tag():
    results = search_roles("elevhälsa")
    assert len(results) >= 2  # kurator, specialpedagog, skolsköterska


def test_role_template_to_agent_config():
    role = get_role("rektor")
    config = role.to_agent_config(name_override="Test Rektor")
    assert config.name == "Test Rektor"
    assert config.role_id == "rektor"
    assert len(config.responsibilities) > 0


def test_role_template_with_trait_overrides():
    role = get_role("rektor")
    config = role.to_agent_config(trait_overrides={"stress_level": 9})
    assert "Stressnivå" in config.personality


def test_role_template_with_natural_language():
    role = get_role("rektor")
    config = role.to_agent_config(
        natural_language_personality="Extremt stressad och aggressiv"
    )
    assert "Extremt stressad" in config.personality
