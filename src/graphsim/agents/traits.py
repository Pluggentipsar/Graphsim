"""Personality trait system for configurable agent behavior.

Traits can be set via numeric sliders (0-10) or natural language descriptions.
They influence how agents behave, communicate, and make decisions.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# Alla tillgängliga personlighetsdimensioner
TRAIT_DEFINITIONS: dict[str, dict[str, str]] = {
    "openness_to_change": {
        "name_sv": "Förändringsbenägenhet",
        "low": "Motståndskraftig mot förändring, föredrar beprövade metoder",
        "high": "Öppen för nya idéer, driver förändring aktivt",
    },
    "decisiveness": {
        "name_sv": "Beslutsamhet",
        "low": "Tveksam, vill ha mer information innan beslut",
        "high": "Fattar snabba beslut, handlingskraftig",
    },
    "empathy": {
        "name_sv": "Empati",
        "low": "Saklig och distanserad, fokus på fakta",
        "high": "Starkt empatisk, prioriterar känslor och relationer",
    },
    "assertiveness": {
        "name_sv": "Genomslagskraft",
        "low": "Tillbakadragen, undviker konflikter",
        "high": "Tydlig och bestämd, driver sin linje",
    },
    "stress_level": {
        "name_sv": "Stressnivå",
        "low": "Lugn och balanserad, hanterar press väl",
        "high": "Pressad och stressad, kort stubin",
    },
    "trust_in_system": {
        "name_sv": "Systemtillit",
        "low": "Misstror byråkrati och processer",
        "high": "Litar på systemet och följer regler",
    },
    "collaboration": {
        "name_sv": "Samarbetsvilja",
        "low": "Jobbar helst ensam, svår att nå",
        "high": "Söker aktivt samarbete, delar information",
    },
    "risk_tolerance": {
        "name_sv": "Risktolerans",
        "low": "Försiktig, vill minimera risker",
        "high": "Vågar ta risker, accepterar osäkerhet",
    },
    "communication_style": {
        "name_sv": "Kommunikationsstil",
        "low": "Kort och formell, delar lite",
        "high": "Öppen och pratig, delar mycket",
    },
    "authority_orientation": {
        "name_sv": "Auktoritetsorientering",
        "low": "Ifrågasätter hierarkier, agerar självständigt",
        "high": "Respekterar hierarkier, följer instruktioner",
    },
}

TRAIT_NAMES = list(TRAIT_DEFINITIONS.keys())


class TraitProfile(BaseModel):
    """A set of personality traits with values 0-10."""

    traits: dict[str, float] = Field(default_factory=dict)
    natural_language_description: str = ""

    def get_trait(self, trait_name: str) -> float:
        """Get a trait value, defaulting to 5 (neutral)."""
        return self.traits.get(trait_name, 5.0)

    def set_trait(self, trait_name: str, value: float) -> None:
        """Set a trait value (clamped to 0-10)."""
        self.traits[trait_name] = max(0.0, min(10.0, value))

    def to_prompt_description(self) -> str:
        """Convert trait profile to a natural language description for the LLM prompt."""
        if self.natural_language_description:
            parts = [self.natural_language_description]
        else:
            parts = []

        for trait_name, value in self.traits.items():
            if trait_name not in TRAIT_DEFINITIONS:
                continue
            defn = TRAIT_DEFINITIONS[trait_name]
            if value <= 3:
                parts.append(f"{defn['name_sv']}: {defn['low']} (nivå {value:.0f}/10)")
            elif value >= 7:
                parts.append(f"{defn['name_sv']}: {defn['high']} (nivå {value:.0f}/10)")
            # Values 4-6 are neutral, skip them to keep prompts concise

        return "\n".join(parts) if parts else "Neutral personlighet utan starka drag."

    @classmethod
    def from_preset(cls, preset: str) -> TraitProfile:
        """Create a trait profile from a named preset."""
        presets: dict[str, dict[str, float]] = {
            "default": {},
            "change_resistant": {
                "openness_to_change": 2,
                "trust_in_system": 8,
                "authority_orientation": 8,
                "risk_tolerance": 2,
            },
            "stressed_leader": {
                "stress_level": 8,
                "decisiveness": 7,
                "assertiveness": 7,
                "empathy": 4,
                "collaboration": 4,
            },
            "empathic_listener": {
                "empathy": 9,
                "collaboration": 8,
                "assertiveness": 3,
                "communication_style": 8,
            },
            "bureaucrat": {
                "trust_in_system": 9,
                "authority_orientation": 9,
                "risk_tolerance": 2,
                "openness_to_change": 2,
                "communication_style": 3,
            },
            "maverick": {
                "openness_to_change": 9,
                "authority_orientation": 2,
                "risk_tolerance": 8,
                "assertiveness": 8,
                "decisiveness": 8,
            },
            "anxious": {
                "stress_level": 8,
                "decisiveness": 3,
                "risk_tolerance": 2,
                "assertiveness": 2,
                "trust_in_system": 4,
            },
        }
        trait_values = presets.get(preset, {})
        return cls(traits=trait_values)

    def get_available_traits(self) -> list[dict[str, Any]]:
        """Return all available trait definitions with current values."""
        result = []
        for trait_name, defn in TRAIT_DEFINITIONS.items():
            result.append({
                "id": trait_name,
                "name": defn["name_sv"],
                "value": self.get_trait(trait_name),
                "low_description": defn["low"],
                "high_description": defn["high"],
            })
        return result
