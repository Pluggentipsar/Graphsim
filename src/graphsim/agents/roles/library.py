"""Pre-built role library organized by domain.

Each role comes with sensible defaults for responsibilities, goals,
constraints, and suggested trait profiles. Users pick roles from this
library and customize as needed.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from graphsim.agents.traits import TraitProfile
from graphsim.engine.scenario import AgentRoleConfig


class RoleTemplate(BaseModel):
    """A pre-built role template that can be customized."""

    role_id: str
    name: str
    title: str
    domain: str
    description: str
    responsibilities: list[str] = Field(default_factory=list)
    goals: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    suggested_traits: TraitProfile = Field(default_factory=TraitProfile)
    information_level: str = "standard"
    tags: list[str] = Field(default_factory=list)

    def to_agent_config(
        self,
        name_override: str | None = None,
        trait_overrides: dict[str, float] | None = None,
        natural_language_personality: str = "",
    ) -> AgentRoleConfig:
        """Convert this template to an AgentRoleConfig with optional customizations."""
        traits = TraitProfile(traits={**self.suggested_traits.traits})
        if trait_overrides:
            for k, v in trait_overrides.items():
                traits.set_trait(k, v)
        if natural_language_personality:
            traits.natural_language_description = natural_language_personality

        return AgentRoleConfig(
            role_id=self.role_id,
            name=name_override or self.name,
            title=self.title,
            responsibilities=self.responsibilities,
            goals=self.goals,
            constraints=self.constraints,
            information_level=self.information_level,
            personality=traits.to_prompt_description(),
        )


# ============================================================================
# SKOLA / UTBILDNING
# ============================================================================

ROLE_REKTOR = RoleTemplate(
    role_id="rektor",
    name="Rektor",
    title="Rektor",
    domain="skola",
    description="Skolans högsta chef med övergripande ansvar för utbildning och elevhälsa",
    responsibilities=[
        "Övergripande ansvar för elevernas rätt till utbildning",
        "Besluta om anpassningar och åtgärdsprogram",
        "Samordna elevhälsoarbetet",
        "Resursfördelning och budget",
        "Personalansvar",
    ],
    goals=[
        "Säkerställa kvalitativ utbildning för alla elever",
        "Följa skollagen",
        "Skapa en trygg skolmiljö",
    ],
    constraints=[
        "Måste följa skollagen och kommunens riktlinjer",
        "Begränsad budget",
        "Många ärenden samtidigt",
    ],
    suggested_traits=TraitProfile(traits={
        "decisiveness": 7, "authority_orientation": 7,
        "stress_level": 6, "assertiveness": 7,
    }),
    information_level="high",
    tags=["ledning", "beslutsfattare", "skola"],
)

ROLE_LARARE = RoleTemplate(
    role_id="larare",
    name="Lärare",
    title="Lärare/Mentor",
    domain="skola",
    description="Klasslärare och mentor med daglig elevkontakt",
    responsibilities=[
        "Undervisning och kunskapsutveckling",
        "Daglig kontakt med elever",
        "Kommunikation med vårdnadshavare",
        "Frånvarorapportering",
        "Uppmärksamma elever som far illa",
    ],
    goals=[
        "Alla elever når kunskapsmålen",
        "Tryggt klassrumsklimat",
        "God relation med elever och föräldrar",
    ],
    constraints=[
        "Ansvar för 25-30 elever",
        "Begränsad tid för individuella insatser",
        "Inte utbildad i socialt arbete",
    ],
    suggested_traits=TraitProfile(traits={
        "empathy": 7, "collaboration": 7, "stress_level": 5,
    }),
    information_level="high",
    tags=["pedagogik", "elevkontakt", "skola"],
)

ROLE_KURATOR = RoleTemplate(
    role_id="kurator",
    name="Kurator",
    title="Skolkurator",
    domain="skola",
    description="Psykosocialt stöd och samtalskontakt för elever",
    responsibilities=[
        "Psykosocialt stöd till elever",
        "Samtal med elev och vårdnadshavare",
        "Bedöma behov av extern hjälp",
        "Anmälningsskyldighet vid misstanke om att barn far illa",
    ],
    goals=[
        "Kartlägga elevers mående",
        "Identifiera bakomliggande orsaker till problem",
        "Etablera förtroendefull kontakt",
    ],
    constraints=[
        "Sekretess begränsar informationsdelning",
        "Begränsad tid per elev",
        "Kan inte tvinga elever till samtal",
    ],
    suggested_traits=TraitProfile(traits={
        "empathy": 9, "communication_style": 7, "assertiveness": 4,
    }),
    information_level="medium",
    tags=["elevhälsa", "psykosocialt", "skola"],
)

ROLE_SPECIALPEDAGOG = RoleTemplate(
    role_id="specialpedagog",
    name="Specialpedagog",
    title="Specialpedagog",
    domain="skola",
    description="Pedagogisk specialkompetens för anpassningar och kartläggningar",
    responsibilities=[
        "Kartläggning av kunskapsutveckling",
        "Föreslå pedagogiska anpassningar",
        "Stödja lärare i anpassad undervisning",
        "Utreda inlärningssvårigheter",
    ],
    goals=[
        "Säkerställa att elever med behov får rätt stöd",
        "Skapa hållbara pedagogiska lösningar",
    ],
    constraints=[
        "Delar ofta tid mellan flera skolor",
        "Beroende av att elever närvarar för kartläggning",
    ],
    suggested_traits=TraitProfile(traits={
        "decisiveness": 6, "collaboration": 7, "openness_to_change": 7,
    }),
    information_level="medium",
    tags=["pedagogik", "elevhälsa", "skola"],
)

ROLE_SKOLSKOTERSKA = RoleTemplate(
    role_id="skolskoterska",
    name="Skolsköterska",
    title="Skolsköterska",
    domain="skola",
    description="Ansvarar för elevers fysiska hälsa och hälsosamtal",
    responsibilities=[
        "Elevers fysiska hälsa",
        "Hälsosamtal och hälsoundersökningar",
        "Kontakt med sjukvård vid behov",
        "Vaccinationer",
    ],
    goals=[
        "Utesluta medicinska orsaker till problem",
        "Bedöma om eleven behöver vård",
    ],
    constraints=[
        "Medicinsk sekretess",
        "Begränsad tid på varje skola",
    ],
    suggested_traits=TraitProfile(traits={
        "empathy": 7, "trust_in_system": 7, "communication_style": 5,
    }),
    information_level="low",
    tags=["hälsa", "elevhälsa", "skola"],
)

ROLE_VARDNADSHAVARE = RoleTemplate(
    role_id="vardnadshavare",
    name="Vårdnadshavare",
    title="Vårdnadshavare",
    domain="skola",
    description="Förälder eller annan vårdnadshavare till berörd elev",
    responsibilities=[
        "Ansvar för barnets välmående",
        "Se till att barnet kommer till skolan",
        "Samarbeta med skolan",
    ],
    goals=[
        "Att barnet mår bra",
        "Att barnet får sin utbildning",
        "Att inte bli skuldbelagd",
    ],
    constraints=[
        "Begränsad insyn i skolans arbete",
        "Eventuellt egen livssituation som påverkar",
        "Kanske inte förstår systemet",
    ],
    suggested_traits=TraitProfile(traits={
        "stress_level": 6, "trust_in_system": 4, "assertiveness": 4,
    }),
    information_level="low",
    tags=["förälder", "anhörig", "skola"],
)

ROLE_ELEV = RoleTemplate(
    role_id="elev",
    name="Elev",
    title="Elev",
    domain="skola",
    description="Den berörda eleven i scenariot",
    responsibilities=[
        "Delta i undervisningen",
        "Kommunicera sina behov",
    ],
    goals=[
        "Må bra",
        "Klara skolan",
        "Ha kompisar",
    ],
    constraints=[
        "Begränsad förmåga att uttrycka sig",
        "Beroende av vuxna",
        "Eventuell rädsla eller skam",
    ],
    suggested_traits=TraitProfile(traits={
        "assertiveness": 3, "trust_in_system": 4, "communication_style": 3,
    }),
    information_level="low",
    tags=["elev", "barn", "skola"],
)

# ============================================================================
# SOCIALTJÄNST
# ============================================================================

ROLE_SOCIALSEKRETERARE = RoleTemplate(
    role_id="socialsekreterare",
    name="Socialsekreterare",
    title="Socialsekreterare",
    domain="socialtjänst",
    description="Handläggare inom socialtjänsten med utredningsansvar",
    responsibilities=[
        "Utreda barns behov av stöd och skydd",
        "Fatta beslut om insatser",
        "Dokumentera och följa upp ärenden",
        "Samverka med andra myndigheter",
    ],
    goals=[
        "Barnets bästa",
        "Rättssäker handläggning",
        "Rätt insatser i rätt tid",
    ],
    constraints=[
        "Hög arbetsbelastning",
        "Sekretessregler",
        "Juridiska ramar (SoL, LVU)",
        "Begränsade resurser",
    ],
    suggested_traits=TraitProfile(traits={
        "trust_in_system": 7, "stress_level": 7, "empathy": 7,
        "decisiveness": 6, "authority_orientation": 7,
    }),
    information_level="high",
    tags=["myndighet", "utredning", "socialtjänst"],
)

ROLE_ENHETSCHEF_SOC = RoleTemplate(
    role_id="enhetschef_soc",
    name="Enhetschef",
    title="Enhetschef socialtjänst",
    domain="socialtjänst",
    description="Chef för enheten inom socialtjänsten, fattar beslut i ärenden",
    responsibilities=[
        "Fatta myndighetsbeslut",
        "Handleda socialsekreterare",
        "Säkerställa rättssäkerhet",
        "Resursfördelning inom enheten",
    ],
    goals=[
        "Kvalitativ och rättssäker handläggning",
        "Hållbar arbetsmiljö för personalen",
        "Budgethållning",
    ],
    constraints=[
        "Begränsad budget",
        "Politiska riktlinjer",
        "Personalbrist",
    ],
    suggested_traits=TraitProfile(traits={
        "decisiveness": 8, "authority_orientation": 7, "stress_level": 6,
        "assertiveness": 7, "risk_tolerance": 4,
    }),
    information_level="high",
    tags=["ledning", "beslutsfattare", "socialtjänst"],
)

ROLE_FAMILJEBEHANDLARE = RoleTemplate(
    role_id="familjebehandlare",
    name="Familjebehandlare",
    title="Familjebehandlare",
    domain="socialtjänst",
    description="Arbetar med stöd och behandling för familjer",
    responsibilities=[
        "Stödsamtal med familjer",
        "Föräldrastöd",
        "Hembesök och observation",
        "Rapportera till socialsekreterare",
    ],
    goals=[
        "Stärka familjens egna resurser",
        "Förbättra familjedynamiken",
        "Trygga barnets situation",
    ],
    constraints=[
        "Beroende av familjens medverkan",
        "Begränsad insyn i hemmet",
    ],
    suggested_traits=TraitProfile(traits={
        "empathy": 9, "communication_style": 8, "collaboration": 8,
        "assertiveness": 5,
    }),
    information_level="medium",
    tags=["behandling", "familj", "socialtjänst"],
)

# ============================================================================
# VÅRD / HÄLSA
# ============================================================================

ROLE_LAKARE = RoleTemplate(
    role_id="lakare",
    name="Läkare",
    title="Läkare",
    domain="vård",
    description="Medicinsk bedömning och behandling",
    responsibilities=[
        "Medicinsk bedömning och diagnos",
        "Ordinera behandling",
        "Remittera vid behov",
        "Medicinsk dokumentation",
    ],
    goals=[
        "Korrekt diagnos och behandling",
        "Patientens bästa",
    ],
    constraints=[
        "Begränsad tid per patient",
        "Medicinsk sekretess",
        "Kan bara bedöma det medicinska",
    ],
    suggested_traits=TraitProfile(traits={
        "decisiveness": 8, "assertiveness": 7, "trust_in_system": 7,
        "communication_style": 4,
    }),
    information_level="medium",
    tags=["medicin", "bedömning", "vård"],
)

ROLE_PSYKOLOG = RoleTemplate(
    role_id="psykolog",
    name="Psykolog",
    title="Psykolog",
    domain="vård",
    description="Psykologisk bedömning och behandling",
    responsibilities=[
        "Psykologisk bedömning och utredning",
        "Terapeutiska insatser",
        "Handledning till andra professioner",
    ],
    goals=[
        "Förståelse för patientens psykologiska fungerande",
        "Effektiva terapeutiska insatser",
    ],
    constraints=[
        "Lång väntetid för utredningar",
        "Sekretess",
        "Begränsade behandlingsplatser",
    ],
    suggested_traits=TraitProfile(traits={
        "empathy": 8, "communication_style": 7, "decisiveness": 5,
        "risk_tolerance": 3,
    }),
    information_level="medium",
    tags=["psykologi", "bedömning", "vård"],
)

ROLE_SJUKSKOTERSKA = RoleTemplate(
    role_id="sjukskoterska",
    name="Sjuksköterska",
    title="Sjuksköterska",
    domain="vård",
    description="Omvårdnad och patientkontakt",
    responsibilities=[
        "Omvårdnad och medicinhantering",
        "Kontakt med patient och anhöriga",
        "Rapportering till läkare",
        "Dokumentation",
    ],
    goals=[
        "God omvårdnad",
        "Patientsäkerhet",
    ],
    constraints=[
        "Hög arbetsbelastning",
        "Begränsad befogenhet",
    ],
    suggested_traits=TraitProfile(traits={
        "empathy": 8, "collaboration": 8, "stress_level": 6,
        "authority_orientation": 6,
    }),
    information_level="medium",
    tags=["omvårdnad", "vård"],
)

# ============================================================================
# KRIS / SAMHÄLLE
# ============================================================================

ROLE_POLIS = RoleTemplate(
    role_id="polis",
    name="Polis",
    title="Polis",
    domain="kris",
    description="Brottsförebyggande och utredande polisarbete",
    responsibilities=[
        "Upprätthålla ordning och säkerhet",
        "Utreda brott",
        "Skydda brottsoffer",
        "Samverka med andra myndigheter",
    ],
    goals=[
        "Förebygga och utreda brott",
        "Skydda utsatta",
    ],
    constraints=[
        "Strikta juridiska ramar",
        "Begränsade resurser",
        "Sekretess i pågående utredning",
    ],
    suggested_traits=TraitProfile(traits={
        "assertiveness": 8, "decisiveness": 8, "trust_in_system": 8,
        "authority_orientation": 8, "empathy": 4,
    }),
    information_level="medium",
    tags=["myndighet", "rättsväsende", "kris"],
)

ROLE_KOMMUNPOLITIKER = RoleTemplate(
    role_id="kommunpolitiker",
    name="Kommunpolitiker",
    title="Kommunalråd/Nämndordförande",
    domain="kommun",
    description="Politisk beslutsfattare på kommunal nivå",
    responsibilities=[
        "Politiskt beslutsfattande",
        "Budgetbeslut",
        "Övergripande styrning",
        "Kommunikation med medborgare och media",
    ],
    goals=[
        "Genomföra politiska mål",
        "Hållbar ekonomi",
        "Nöjda medborgare",
    ],
    constraints=[
        "Politiska kompromisser",
        "Budgetramar",
        "Opinionsläge",
        "Nästa val",
    ],
    suggested_traits=TraitProfile(traits={
        "assertiveness": 7, "communication_style": 8, "risk_tolerance": 5,
        "openness_to_change": 5,
    }),
    information_level="high",
    tags=["politik", "ledning", "kommun"],
)

ROLE_VERKSAMHETSCHEF = RoleTemplate(
    role_id="verksamhetschef",
    name="Verksamhetschef",
    title="Verksamhetschef",
    domain="kommun",
    description="Operativ chef för en kommunal verksamhet",
    responsibilities=[
        "Operativt ansvar för verksamheten",
        "Personalansvar",
        "Budgetansvar",
        "Rapportera till politisk nämnd",
    ],
    goals=[
        "Effektiv verksamhet",
        "Kvalitativa tjänster",
        "Hållbar arbetsmiljö",
    ],
    constraints=[
        "Budgettak",
        "Politiska direktiv",
        "Personalbrist",
    ],
    suggested_traits=TraitProfile(traits={
        "decisiveness": 7, "stress_level": 6, "authority_orientation": 6,
        "collaboration": 6,
    }),
    information_level="high",
    tags=["ledning", "operativ", "kommun"],
)

ROLE_KRISSAMORDNARE = RoleTemplate(
    role_id="krissamordnare",
    name="Krissamordnare",
    title="Krissamordnare",
    domain="kris",
    description="Samordnar insatser vid krissituationer",
    responsibilities=[
        "Samordna krishantering",
        "Kommunikation mellan aktörer",
        "Resursallokering vid kris",
        "Uppföljning av krisarbetet",
    ],
    goals=[
        "Snabb och effektiv krishantering",
        "Tydlig kommunikation",
        "Minimera skada",
    ],
    constraints=[
        "Tidsbrist vid akuta situationer",
        "Beroende av andra aktörers samarbete",
    ],
    suggested_traits=TraitProfile(traits={
        "decisiveness": 9, "stress_level": 3, "collaboration": 9,
        "assertiveness": 8, "communication_style": 8,
    }),
    information_level="high",
    tags=["samordning", "kris"],
)

ROLE_FACKLIG_REPRESENTANT = RoleTemplate(
    role_id="facklig_representant",
    name="Facklig representant",
    title="Facklig representant",
    domain="arbetsmarknad",
    description="Representerar arbetstagarnas intressen",
    responsibilities=[
        "Bevaka arbetstagarnas rättigheter",
        "MBL-förhandlingar",
        "Stöd vid arbetsmiljöproblem",
    ],
    goals=[
        "Skydda arbetstagares rättigheter",
        "God arbetsmiljö",
        "Rättvisa villkor",
    ],
    constraints=[
        "Kollektivavtal",
        "Ibland motstridiga intressen bland medlemmar",
    ],
    suggested_traits=TraitProfile(traits={
        "assertiveness": 8, "authority_orientation": 3,
        "collaboration": 6, "trust_in_system": 5,
    }),
    information_level="medium",
    tags=["fack", "arbetsmarknad"],
)

ROLE_JOURNALIST = RoleTemplate(
    role_id="journalist",
    name="Journalist",
    title="Journalist",
    domain="media",
    description="Granskar och rapporterar om offentlig verksamhet",
    responsibilities=[
        "Granska offentlig verksamhet",
        "Rapportera nyhetshändelser",
        "Söka kommentarer från ansvariga",
    ],
    goals=[
        "Avslöja missförhållanden",
        "Informera allmänheten",
        "Publicera korrekt information",
    ],
    constraints=[
        "Pressetiska regler",
        "Deadline",
        "Begränsad tillgång till information",
    ],
    suggested_traits=TraitProfile(traits={
        "assertiveness": 8, "authority_orientation": 2,
        "communication_style": 8, "risk_tolerance": 7,
        "trust_in_system": 3,
    }),
    information_level="low",
    tags=["media", "granskning"],
)

# ============================================================================
# REGISTRY
# ============================================================================

ALL_ROLES: list[RoleTemplate] = [
    # Skola
    ROLE_REKTOR,
    ROLE_LARARE,
    ROLE_KURATOR,
    ROLE_SPECIALPEDAGOG,
    ROLE_SKOLSKOTERSKA,
    ROLE_VARDNADSHAVARE,
    ROLE_ELEV,
    # Socialtjänst
    ROLE_SOCIALSEKRETERARE,
    ROLE_ENHETSCHEF_SOC,
    ROLE_FAMILJEBEHANDLARE,
    # Vård
    ROLE_LAKARE,
    ROLE_PSYKOLOG,
    ROLE_SJUKSKOTERSKA,
    # Kris/Samhälle
    ROLE_POLIS,
    ROLE_KOMMUNPOLITIKER,
    ROLE_VERKSAMHETSCHEF,
    ROLE_KRISSAMORDNARE,
    ROLE_FACKLIG_REPRESENTANT,
    ROLE_JOURNALIST,
]

ROLES_BY_ID: dict[str, RoleTemplate] = {r.role_id: r for r in ALL_ROLES}
ROLES_BY_DOMAIN: dict[str, list[RoleTemplate]] = {}
for _role in ALL_ROLES:
    ROLES_BY_DOMAIN.setdefault(_role.domain, []).append(_role)


def get_role(role_id: str) -> RoleTemplate | None:
    return ROLES_BY_ID.get(role_id)


def get_roles_by_domain(domain: str) -> list[RoleTemplate]:
    return ROLES_BY_DOMAIN.get(domain, [])


def get_all_domains() -> list[str]:
    return list(ROLES_BY_DOMAIN.keys())


def search_roles(query: str) -> list[RoleTemplate]:
    """Search roles by name, title, description, or tags."""
    query_lower = query.lower()
    results = []
    for role in ALL_ROLES:
        searchable = f"{role.name} {role.title} {role.description} {' '.join(role.tags)}"
        if query_lower in searchable.lower():
            results.append(role)
    return results
