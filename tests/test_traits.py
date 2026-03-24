"""Tests for the personality trait system."""

from graphsim.agents.traits import TRAIT_DEFINITIONS, TraitProfile


def test_default_trait_value():
    profile = TraitProfile()
    assert profile.get_trait("empathy") == 5.0


def test_set_and_get_trait():
    profile = TraitProfile()
    profile.set_trait("empathy", 9.0)
    assert profile.get_trait("empathy") == 9.0


def test_trait_clamping():
    profile = TraitProfile()
    profile.set_trait("empathy", 15.0)
    assert profile.get_trait("empathy") == 10.0
    profile.set_trait("empathy", -3.0)
    assert profile.get_trait("empathy") == 0.0


def test_to_prompt_description_high():
    profile = TraitProfile(traits={"empathy": 9})
    desc = profile.to_prompt_description()
    assert "Empati" in desc
    assert "empatisk" in desc.lower()


def test_to_prompt_description_low():
    profile = TraitProfile(traits={"empathy": 2})
    desc = profile.to_prompt_description()
    assert "Empati" in desc
    assert "Saklig" in desc


def test_neutral_traits_skipped():
    profile = TraitProfile(traits={"empathy": 5})
    desc = profile.to_prompt_description()
    assert "Neutral" in desc


def test_natural_language_override():
    profile = TraitProfile(
        traits={"empathy": 9},
        natural_language_description="Mycket orolig och stressad person",
    )
    desc = profile.to_prompt_description()
    assert "Mycket orolig" in desc
    assert "Empati" in desc


def test_from_preset():
    profile = TraitProfile.from_preset("change_resistant")
    assert profile.get_trait("openness_to_change") == 2
    assert profile.get_trait("trust_in_system") == 8


def test_from_preset_default():
    profile = TraitProfile.from_preset("default")
    assert len(profile.traits) == 0


def test_get_available_traits():
    profile = TraitProfile(traits={"empathy": 8})
    available = profile.get_available_traits()
    assert len(available) == len(TRAIT_DEFINITIONS)
    empathy_trait = next(t for t in available if t["id"] == "empathy")
    assert empathy_trait["value"] == 8.0
