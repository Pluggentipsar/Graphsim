"""Tests for scenario templates."""

from graphsim.engine.templates import (
    ALL_TEMPLATES,
    get_all_template_domains,
    get_template,
    get_templates_by_domain,
    search_templates,
)


def test_all_templates_exist():
    assert len(ALL_TEMPLATES) >= 8


def test_get_template():
    t = get_template("school_absence")
    assert t is not None
    assert t.title == "Elev med hög frånvaro"
    assert t.domain == "skola"


def test_get_template_not_found():
    assert get_template("nonexistent") is None


def test_templates_have_events():
    t = get_template("school_absence")
    assert len(t.events) >= 2
    assert t.events[0].round_number == 2


def test_templates_have_roles():
    t = get_template("budget_cut")
    assert len(t.suggested_roles) >= 5
    assert "kommunpolitiker" in t.suggested_roles


def test_templates_have_decision_points():
    t = get_template("honor_violence")
    assert len(t.decision_points) >= 3


def test_get_templates_by_domain():
    school = get_templates_by_domain("skola")
    assert len(school) >= 3


def test_get_all_template_domains():
    domains = get_all_template_domains()
    assert "skola" in domains
    assert "kommun" in domains
    assert "kris" in domains


def test_search_templates():
    results = search_templates("budget")
    assert len(results) >= 1
    assert results[0].template_id == "budget_cut"


def test_search_templates_by_tag():
    results = search_templates("samverkan")
    assert len(results) >= 1
