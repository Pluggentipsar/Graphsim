"""Pre-built scenario templates organized by domain.

Users pick a template, customize agents/traits, and run.
Each template includes suggested roles, relationships, events, and decision points.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class EventTrigger(BaseModel):
    """An event that can be injected at a specific round."""

    round_number: int
    description: str
    affects_agents: list[str] = Field(default_factory=list)
    new_information: dict[str, str] = Field(default_factory=dict)


class ScenarioTemplate(BaseModel):
    """A pre-built scenario template ready to customize and run."""

    template_id: str
    title: str
    domain: str
    description: str
    context: str
    initial_event: str
    suggested_roles: list[str] = Field(default_factory=list)
    suggested_relationships: list[dict[str, str]] = Field(default_factory=list)
    decision_points: list[str] = Field(default_factory=list)
    events: list[EventTrigger] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    difficulty: str = "medium"  # easy, medium, hard
    estimated_rounds: int = 5


# ============================================================================
# SKOLA
# ============================================================================

TEMPLATE_SCHOOL_ABSENCE = ScenarioTemplate(
    template_id="school_absence",
    title="Elev med hög frånvaro",
    domain="skola",
    description=(
        "En elev har haft ökande frånvaro de senaste månaderna. "
        "Frånvaron har gått från sporadisk till nästan daglig. "
        "Tvärprofessionellt möte har kallats."
    ),
    context="Kommunal grundskola, medelstor stad med elevhälsoteam.",
    initial_event=(
        "Rektor kallar till tvärprofessionellt möte angående elev med 60% "
        "frånvaro senaste månaden. Mentor rapporterar att eleven verkar "
        "nedstämd och att vårdnadshavare säger att eleven vägrar gå till skolan."
    ),
    suggested_roles=["rektor", "larare", "kurator", "specialpedagog", "skolskoterska", "vardnadshavare"],
    suggested_relationships=[
        {"source": "larare", "target": "rektor", "type": "reports_to"},
        {"source": "kurator", "target": "rektor", "type": "reports_to"},
        {"source": "specialpedagog", "target": "rektor", "type": "reports_to"},
        {"source": "skolskoterska", "target": "rektor", "type": "reports_to"},
        {"source": "larare", "target": "kurator", "type": "collaborates_with"},
        {"source": "larare", "target": "specialpedagog", "type": "collaborates_with"},
        {"source": "kurator", "target": "skolskoterska", "type": "collaborates_with"},
        {"source": "larare", "target": "vardnadshavare", "type": "collaborates_with"},
        {"source": "vardnadshavare", "target": "kurator", "type": "lacks_knowledge_of"},
    ],
    decision_points=[
        "Ska skolan göra en orosanmälan till socialtjänsten?",
        "Vilka anpassningar ska göras för eleven?",
        "Ska extern hjälp (BUP, socialtjänst) kopplas in?",
    ],
    events=[
        EventTrigger(
            round_number=2,
            description="Eleven berättar för kuratorn att hen blir mobbad online av klasskamrater.",
            affects_agents=["kurator"],
            new_information={"kurator": "Eleven utsätts för nätmobbning av klasskamrater."},
        ),
        EventTrigger(
            round_number=3,
            description="Vårdnadshavare ringer skolan i panik - eleven har låst in sig på rummet och vägrar äta.",
            affects_agents=["larare", "rektor"],
            new_information={"larare": "Vårdnadshavare larmar om att eleven vägrar äta och låser in sig."},
        ),
    ],
    tags=["frånvaro", "elevhälsa", "samverkan"],
    difficulty="medium",
    estimated_rounds=5,
)

TEMPLATE_HONOR_VIOLENCE = ScenarioTemplate(
    template_id="honor_violence",
    title="Misstanke om hedersrelaterat våld",
    domain="skola",
    description=(
        "Personal på skolan misstänker att en elev utsätts för hedersrelaterat "
        "förtryck och eventuellt våld i hemmet. Eleven har blivit alltmer "
        "tillbakadragen och har blåmärken."
    ),
    context="Kommunal högstadieskola i förort. Eleven går i årskurs 9.",
    initial_event=(
        "Idrottsläraren upptäcker blåmärken på elevens armar i omklädningsrummet. "
        "Eleven säger att hen ramlade men verkar rädd. Läraren rapporterar till mentor."
    ),
    suggested_roles=["rektor", "larare", "kurator", "skolskoterska", "vardnadshavare", "polis", "socialsekreterare"],
    suggested_relationships=[
        {"source": "larare", "target": "rektor", "type": "reports_to"},
        {"source": "kurator", "target": "rektor", "type": "reports_to"},
        {"source": "skolskoterska", "target": "rektor", "type": "reports_to"},
        {"source": "larare", "target": "kurator", "type": "collaborates_with"},
        {"source": "kurator", "target": "socialsekreterare", "type": "collaborates_with"},
        {"source": "socialsekreterare", "target": "polis", "type": "collaborates_with"},
        {"source": "vardnadshavare", "target": "kurator", "type": "lacks_knowledge_of"},
        {"source": "vardnadshavare", "target": "socialsekreterare", "type": "lacks_knowledge_of"},
    ],
    decision_points=[
        "Ska orosanmälan göras omedelbart?",
        "Hur hanteras kontakten med hemmet utan att utsätta eleven?",
        "Behöver eleven skyddas akut?",
        "Hur samordnas insatser mellan skola, socialtjänst och polis?",
    ],
    events=[
        EventTrigger(
            round_number=1,
            description="Eleven söker upp kuratorn och berättar att familjen planerar att skicka hen utomlands.",
            affects_agents=["kurator"],
            new_information={"kurator": "Eleven riskerar att föras utomlands mot sin vilja."},
        ),
        EventTrigger(
            round_number=3,
            description="En äldre släkting till eleven dyker upp på skolan och kräver att få träffa eleven.",
            affects_agents=["rektor", "larare"],
            new_information={"rektor": "Okänd släkting till eleven har kommit till skolan och är aggressiv."},
        ),
    ],
    tags=["heder", "våld", "sekretess", "samverkan", "akut"],
    difficulty="hard",
    estimated_rounds=5,
)

TEMPLATE_SCHOOL_CRISIS = ScenarioTemplate(
    template_id="school_crisis",
    title="Allvarlig händelse på skola",
    domain="skola",
    description=(
        "En allvarlig händelse har inträffat på skolan som kräver "
        "krishantering, kommunikation med föräldrar och media, "
        "samt stöd till elever och personal."
    ),
    context="Kommunal gymnasieskola med 800 elever.",
    initial_event=(
        "En elev har kollapsat i matsalen och förts till sjukhus med ambulans. "
        "Rykten sprids snabbt bland elever och i sociala medier. "
        "Föräldrar börjar ringa skolan."
    ),
    suggested_roles=["rektor", "larare", "kurator", "skolskoterska", "krissamordnare", "vardnadshavare", "journalist"],
    suggested_relationships=[
        {"source": "larare", "target": "rektor", "type": "reports_to"},
        {"source": "kurator", "target": "rektor", "type": "reports_to"},
        {"source": "rektor", "target": "krissamordnare", "type": "collaborates_with"},
        {"source": "kurator", "target": "skolskoterska", "type": "collaborates_with"},
        {"source": "journalist", "target": "rektor", "type": "has_info_about"},
        {"source": "vardnadshavare", "target": "rektor", "type": "lacks_knowledge_of"},
        {"source": "journalist", "target": "kurator", "type": "lacks_knowledge_of"},
    ],
    decision_points=[
        "Hur kommuniceras händelsen till föräldrar?",
        "Ska skolan stängas resten av dagen?",
        "Hur hanteras media?",
        "Vilka krisstödinsatser behövs?",
    ],
    events=[
        EventTrigger(
            round_number=1,
            description="Sjukhuset meddelar att elevens tillstånd är kritiskt.",
            affects_agents=["rektor", "skolskoterska"],
            new_information={"rektor": "Elevens tillstånd på sjukhuset är kritiskt."},
        ),
        EventTrigger(
            round_number=2,
            description="En journalist publicerar ett inlägg på sociala medier med felaktig information om händelsen.",
            affects_agents=["rektor", "krissamordnare"],
            new_information={"rektor": "Felaktig information sprids i media om händelsen."},
        ),
        EventTrigger(
            round_number=3,
            description="Flera elever mår dåligt och gråter. Två lärare vill gå hem.",
            affects_agents=["rektor", "kurator", "larare"],
            new_information={"kurator": "Flera elever i chocktillstånd. Personal vill lämna."},
        ),
    ],
    tags=["kris", "kommunikation", "media", "stöd"],
    difficulty="hard",
    estimated_rounds=5,
)

# ============================================================================
# SOCIALTJÄNST
# ============================================================================

TEMPLATE_CHILD_WELFARE = ScenarioTemplate(
    template_id="child_welfare",
    title="Orosanmälan om barn som far illa",
    domain="socialtjänst",
    description=(
        "Socialtjänsten har fått in en orosanmälan om ett barn. "
        "Flera aktörer är involverade och informationsbilden är otydlig."
    ),
    context="Socialtjänsten i en medelstor kommun. Hög arbetsbelastning.",
    initial_event=(
        "En orosanmälan har kommit in från barnets skola. Mentor rapporterar "
        "att barnet ofta kommer till skolan utan frukost, har smutsiga kläder "
        "och verkar oroligt. Föräldrarna har inte svarat på skolans kontaktförsök."
    ),
    suggested_roles=["socialsekreterare", "enhetschef_soc", "familjebehandlare", "larare", "vardnadshavare", "skolskoterska"],
    suggested_relationships=[
        {"source": "socialsekreterare", "target": "enhetschef_soc", "type": "reports_to"},
        {"source": "familjebehandlare", "target": "socialsekreterare", "type": "reports_to"},
        {"source": "socialsekreterare", "target": "larare", "type": "collaborates_with"},
        {"source": "socialsekreterare", "target": "skolskoterska", "type": "collaborates_with"},
        {"source": "familjebehandlare", "target": "vardnadshavare", "type": "collaborates_with"},
        {"source": "vardnadshavare", "target": "socialsekreterare", "type": "lacks_knowledge_of"},
    ],
    decision_points=[
        "Ska förhandsbedömning leda till utredning?",
        "Behövs akut skyddsplacering?",
        "Vilka insatser ska erbjudas familjen?",
        "Hur hanteras föräldrarnas motstånd?",
    ],
    events=[
        EventTrigger(
            round_number=2,
            description="Grannarna ringer in en ny orosanmälan - de har hört skrik från lägenheten på natten.",
            affects_agents=["socialsekreterare", "enhetschef_soc"],
            new_information={"socialsekreterare": "Ny anmälan: grannar rapporterar skrik nattetid."},
        ),
        EventTrigger(
            round_number=3,
            description="Vid hembesök upptäcker familjebehandlaren att det finns en okänd vuxen man i hemmet.",
            affects_agents=["familjebehandlare", "socialsekreterare"],
            new_information={"familjebehandlare": "Okänd vuxen man bor i hemmet, inte registrerad."},
        ),
    ],
    tags=["barn", "orosanmälan", "utredning", "sekretess"],
    difficulty="medium",
    estimated_rounds=5,
)

# ============================================================================
# KOMMUN / ORGANISATION
# ============================================================================

TEMPLATE_BUDGET_CUT = ScenarioTemplate(
    template_id="budget_cut",
    title="Budgetneddragning i kommunal verksamhet",
    domain="kommun",
    description=(
        "Kommunen måste spara 15% på en förvaltnings budget. "
        "Olika aktörer har olika intressen och prioriteringar."
    ),
    context="Medelstor svensk kommun. Socialförvaltningen ska spara 20 MSEK.",
    initial_event=(
        "Kommunstyrelsen har beslutat om sparkrav på 15% för socialförvaltningen. "
        "Verksamhetschefen har kallat till möte med berörda chefer och fackliga "
        "representanter för att diskutera hur besparingarna ska genomföras."
    ),
    suggested_roles=[
        "kommunpolitiker", "verksamhetschef", "enhetschef_soc",
        "socialsekreterare", "facklig_representant", "journalist",
    ],
    suggested_relationships=[
        {"source": "verksamhetschef", "target": "kommunpolitiker", "type": "reports_to"},
        {"source": "enhetschef_soc", "target": "verksamhetschef", "type": "reports_to"},
        {"source": "socialsekreterare", "target": "enhetschef_soc", "type": "reports_to"},
        {"source": "facklig_representant", "target": "verksamhetschef", "type": "collaborates_with"},
        {"source": "journalist", "target": "kommunpolitiker", "type": "has_info_about"},
        {"source": "socialsekreterare", "target": "kommunpolitiker", "type": "lacks_knowledge_of"},
        {"source": "journalist", "target": "enhetschef_soc", "type": "lacks_knowledge_of"},
    ],
    decision_points=[
        "Var ska besparingarna göras?",
        "Ska personal sägas upp eller ska tjänster omfördelas?",
        "Hur kommuniceras besluten till personalen?",
        "Vilka verksamheter prioriteras?",
    ],
    events=[
        EventTrigger(
            round_number=2,
            description="Lokaltidningen publicerar en artikel om att kommunen planerar stänga ett gruppboende.",
            affects_agents=["kommunpolitiker", "verksamhetschef", "journalist"],
            new_information={
                "kommunpolitiker": "Media har fått tag på information om möjlig stängning av gruppboende.",
            },
        ),
        EventTrigger(
            round_number=3,
            description="Fackförbundet hotar med strejkvarsel om uppsägningar genomförs utan förhandling.",
            affects_agents=["facklig_representant", "verksamhetschef"],
            new_information={
                "verksamhetschef": "Facket överväger strejkvarsel.",
            },
        ),
        EventTrigger(
            round_number=4,
            description="En allvarlig incident inträffar i en underbemannad enhet, vilket väcker frågor om patientsäkerhet.",
            affects_agents=["enhetschef_soc", "verksamhetschef", "journalist"],
            new_information={
                "enhetschef_soc": "Incident i underbemannad enhet - risk för IVO-anmälan.",
            },
        ),
    ],
    tags=["budget", "organisation", "förändring", "politik"],
    difficulty="hard",
    estimated_rounds=6,
)

TEMPLATE_AI_IMPLEMENTATION = ScenarioTemplate(
    template_id="ai_implementation",
    title="Införande av AI-stöd i offentlig verksamhet",
    domain="kommun",
    description=(
        "En kommun vill införa AI-baserat beslutsstöd i socialtjänstens "
        "handläggning. Olika aktörer har olika syn på tekniken."
    ),
    context="Stor kommun som vill effektivisera med AI. Pilotprojekt i socialförvaltningen.",
    initial_event=(
        "Kommunstyrelsen har beslutat att starta ett pilotprojekt med AI-baserat "
        "beslutsstöd för socialsekreterare vid riskbedömningar av barn. "
        "Kickoff-möte hålls med alla berörda."
    ),
    suggested_roles=[
        "kommunpolitiker", "verksamhetschef", "socialsekreterare",
        "enhetschef_soc", "facklig_representant", "journalist",
    ],
    suggested_relationships=[
        {"source": "verksamhetschef", "target": "kommunpolitiker", "type": "reports_to"},
        {"source": "enhetschef_soc", "target": "verksamhetschef", "type": "reports_to"},
        {"source": "socialsekreterare", "target": "enhetschef_soc", "type": "reports_to"},
        {"source": "facklig_representant", "target": "verksamhetschef", "type": "collaborates_with"},
        {"source": "journalist", "target": "kommunpolitiker", "type": "has_info_about"},
    ],
    decision_points=[
        "Ska AI-verktyget användas som beslutsstöd eller beslutsfattare?",
        "Hur hanteras etiska frågor kring algoritmbias?",
        "Vilken transparens ska ges till klienter?",
        "Hur hanteras personalens oro?",
    ],
    events=[
        EventTrigger(
            round_number=2,
            description="AI-systemet flaggar ett ärende som högrisk, men socialsekreteraren bedömer det som lågrisk. Vems bedömning gäller?",
            affects_agents=["socialsekreterare", "enhetschef_soc"],
            new_information={
                "socialsekreterare": "AI-systemet och min professionella bedömning motsäger varandra.",
            },
        ),
        EventTrigger(
            round_number=3,
            description="En journalist kontaktar kommunen om att AI-systemet kan vara diskriminerande mot vissa socioekonomiska grupper.",
            affects_agents=["journalist", "kommunpolitiker", "verksamhetschef"],
            new_information={
                "kommunpolitiker": "Media ifrågasätter om AI-systemet diskriminerar.",
            },
        ),
    ],
    tags=["ai", "teknologi", "etik", "organisation"],
    difficulty="medium",
    estimated_rounds=5,
)

# ============================================================================
# VÅRD
# ============================================================================

TEMPLATE_PATIENT_HANDOFF = ScenarioTemplate(
    template_id="patient_handoff",
    title="Patientöverlämning mellan vårdnivåer",
    domain="vård",
    description=(
        "En patient med komplexa behov ska överlämnas mellan slutenvård "
        "och primärvård/kommun. Risker för informationstapp."
    ),
    context="Regionsjukhus och kommunal hemsjukvård. Patienten är äldre med multisjuklighet.",
    initial_event=(
        "En 78-årig patient med diabetes, hjärtsvikt och begynnande demens "
        "ska skrivas ut från sjukhuset efter en höftoperation. "
        "Utskrivningsplanering påbörjas."
    ),
    suggested_roles=["lakare", "sjukskoterska", "psykolog", "socialsekreterare", "vardnadshavare"],
    suggested_relationships=[
        {"source": "sjukskoterska", "target": "lakare", "type": "reports_to"},
        {"source": "sjukskoterska", "target": "socialsekreterare", "type": "collaborates_with"},
        {"source": "lakare", "target": "psykolog", "type": "collaborates_with"},
        {"source": "vardnadshavare", "target": "lakare", "type": "lacks_knowledge_of"},
        {"source": "vardnadshavare", "target": "socialsekreterare", "type": "lacks_knowledge_of"},
    ],
    decision_points=[
        "Är patienten redo för utskrivning?",
        "Vilka kommunala insatser behövs?",
        "Hur säkerställs medicinsk säkerhet efter utskrivning?",
        "Vem tar ansvar för uppföljning?",
    ],
    events=[
        EventTrigger(
            round_number=2,
            description="Patienten ramlar på avdelningen natten innan planerad utskrivning.",
            affects_agents=["lakare", "sjukskoterska"],
            new_information={"lakare": "Patienten har ramlat igen - ny skada måste bedömas."},
        ),
        EventTrigger(
            round_number=3,
            description="Anhöriga kräver att patienten ska få bo kvar på sjukhuset och hotar med att kontakta media.",
            affects_agents=["lakare", "vardnadshavare"],
            new_information={"lakare": "Anhöriga motsätter sig utskrivning och hotar med media."},
        ),
    ],
    tags=["vård", "överlämning", "samverkan", "patientsäkerhet"],
    difficulty="medium",
    estimated_rounds=5,
)

# ============================================================================
# KRIS
# ============================================================================

TEMPLATE_NATURAL_DISASTER = ScenarioTemplate(
    template_id="natural_disaster",
    title="Naturkatastrof - översvämning",
    domain="kris",
    description=(
        "Kraftigt skyfall har orsakat översvämningar i en kommun. "
        "Flera samhällsfunktioner påverkas och krisorganisationen aktiveras."
    ),
    context="Liten kommun vid vattendrag. 15 000 invånare. Begränsade resurser.",
    initial_event=(
        "Kraftigt skyfall under natten har lett till att ån svämmat över. "
        "Tre bostadsområden är drabbade, vägar är avstängda och ett äldreboende "
        "riskerar att översvämmas. Krisorganisationen aktiveras klockan 05:00."
    ),
    suggested_roles=["krissamordnare", "kommunpolitiker", "verksamhetschef", "polis", "sjukskoterska", "journalist"],
    suggested_relationships=[
        {"source": "krissamordnare", "target": "kommunpolitiker", "type": "reports_to"},
        {"source": "verksamhetschef", "target": "krissamordnare", "type": "collaborates_with"},
        {"source": "polis", "target": "krissamordnare", "type": "collaborates_with"},
        {"source": "sjukskoterska", "target": "krissamordnare", "type": "collaborates_with"},
        {"source": "journalist", "target": "kommunpolitiker", "type": "has_info_about"},
        {"source": "journalist", "target": "krissamordnare", "type": "lacks_knowledge_of"},
    ],
    decision_points=[
        "Ska äldreboendet evakueras?",
        "Hur fördelas räddningsresurserna?",
        "Hur kommuniceras läget till invånarna?",
        "Behövs förstärkning från andra kommuner?",
    ],
    events=[
        EventTrigger(
            round_number=1,
            description="Vattennivån stiger snabbare än prognostiserat. Ytterligare ett bostadsområde hotas.",
            affects_agents=["krissamordnare", "polis"],
            new_information={"krissamordnare": "Vattennivån stiger dubbelt så snabbt som väntat."},
        ),
        EventTrigger(
            round_number=2,
            description="Mobilnätet går ner i delar av kommunen. Kommunikation försvåras.",
            affects_agents=["krissamordnare", "polis", "verksamhetschef"],
            new_information={"krissamordnare": "Mobilnätet har fallit i drabbade områden."},
        ),
        EventTrigger(
            round_number=3,
            description="En person rapporteras saknad. Anhöriga kontaktar polisen.",
            affects_agents=["polis", "krissamordnare"],
            new_information={"polis": "En person saknas - senast sedd nära ån igår kväll."},
        ),
    ],
    tags=["kris", "naturkatastrof", "evakuering", "samordning"],
    difficulty="hard",
    estimated_rounds=5,
)

# ============================================================================
# REGISTRY
# ============================================================================

ALL_TEMPLATES: list[ScenarioTemplate] = [
    TEMPLATE_SCHOOL_ABSENCE,
    TEMPLATE_HONOR_VIOLENCE,
    TEMPLATE_SCHOOL_CRISIS,
    TEMPLATE_CHILD_WELFARE,
    TEMPLATE_BUDGET_CUT,
    TEMPLATE_AI_IMPLEMENTATION,
    TEMPLATE_PATIENT_HANDOFF,
    TEMPLATE_NATURAL_DISASTER,
]

TEMPLATES_BY_ID: dict[str, ScenarioTemplate] = {t.template_id: t for t in ALL_TEMPLATES}
TEMPLATES_BY_DOMAIN: dict[str, list[ScenarioTemplate]] = {}
for _t in ALL_TEMPLATES:
    TEMPLATES_BY_DOMAIN.setdefault(_t.domain, []).append(_t)


def get_template(template_id: str) -> ScenarioTemplate | None:
    return TEMPLATES_BY_ID.get(template_id)


def get_templates_by_domain(domain: str) -> list[ScenarioTemplate]:
    return TEMPLATES_BY_DOMAIN.get(domain, [])


def get_all_template_domains() -> list[str]:
    return list(TEMPLATES_BY_DOMAIN.keys())


def search_templates(query: str) -> list[ScenarioTemplate]:
    """Search templates by title, description, or tags."""
    query_lower = query.lower()
    return [
        t for t in ALL_TEMPLATES
        if query_lower in f"{t.title} {t.description} {' '.join(t.tags)}".lower()
    ]
