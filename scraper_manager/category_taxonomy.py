"""Scraper-side job category taxonomy helpers."""

CANONICAL_JOB_CATEGORIES = {
    "operations_control": "Operations Control",
    "crew_control": "Crew Control",
    "ground_operations": "Ground Operations",
    "management": "Management",
    "corporate": "Corporate",
    "maintenance": "Maintenance & Engineering",
    "other": "Other",
}

LEGACY_CATEGORY_ALIASES = {
    "operations_control": {
        "operations_control",
        "operations_control_center",
        "flight_operations",
        "OCC",
        "IOCC",
        "dispatcher",
        "dispatch",
        "flight dispatch",
        "ops control",
        "network control",
        "load control",
        "flight preparation",
        "régulation des vols",
        "préparation des vols",
        "répartiteur",
        "despacho de vuelos",
        "centro de controle",
    },
    "crew_control": {
        "crew_control",
        "crew control",
        "crew scheduling",
        "crew rostering",
        "crew planning",
        "aircrew",
    },
    "ground_operations": {
        "ground_operations",
        "ground_staff",
        "airport_operations",
        "passenger_station_services",
        "passenger_services",
        "Ramp Agent",
        "baggage handler",
        "turnaround coordinator",
        "TRC",
        "marshalling",
        "agent de piste",
        "agente de rampa",
        "gepäckabfertiger",
    },
    "management": {
        "management",
        "corporate_business",
    },
    "corporate": {
        "corporate",
        "corporate_support",
        "safety_security_quality",
        "Finance",
        "HR",
        "Human Resources",
        "Legal",
        "Marketing",
        "Sales",
        "IT",
        "administration",
        "gestion",
    },
    "maintenance": {
        "maintenance",
        "maintenance_engineering",
        "Maintenance & Engineering",
        "Maintenance Control",
        "MCC",
        "Avionics",
        "Technician",
        "Mechanic",
        "Engineer",
        "entretien d'avions",
        "mantenimiento",
    },
    "other": {"other", "Other"},
}

FILTER_CATEGORY_MAP = {
    "Core_Function_Terms_Only": "operations_control",
    "Operative_Functional_Control_Keywords": "operations_control",
    "Crew_Control_Keywords": "crew_control",
    "Supervisory_Level_Control_Keywords": "operations_control",
    "Management_Executive_Control_Keywords": "management",
    "Maintenance_Engineering_Control": "maintenance",
    "Operations_Performance_Analytics": "operations_control",
    "Ground_Airport_Operations": "ground_operations",
    "Entry_Level_Operations_Roles": "operations_control",
    "Corporate_Aviation_Support_Roles": "corporate",
}

_ALIASES_CASEFOLDED = {
    key: {alias.casefold() for alias in aliases}
    for key, aliases in LEGACY_CATEGORY_ALIASES.items()
}


def normalize_job_category(value):
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    if raw in CANONICAL_JOB_CATEGORIES:
        return raw
    lowered = raw.casefold()
    for canonical, aliases in _ALIASES_CASEFOLDED.items():
        if lowered in aliases:
            return canonical
    return FILTER_CATEGORY_MAP.get(raw)


def normalize_job_categories(values):
    if values is None:
        return []
    if isinstance(values, str):
        values = [item.strip() for item in values.split(",") if item.strip()]

    normalized = []
    for value in values:
        canonical = normalize_job_category(value)
        if canonical and canonical not in normalized:
            normalized.append(canonical)
    return normalized


def infer_job_category(
    title="",
    description="",
    primary_category=None,
    matched_categories=None,
    matched_filter_types=None,
    existing_category=None,
):
    """
    Intelligent category inference based on title and description.
    Prioritizes explicit matches but falls back to regex-based keyword analysis.
    """
    import re

    # 1. Check explicit matches from previous stages
    for value in [
        existing_category,
        primary_category,
        *(matched_categories or []),
        *(matched_filter_types or []),
    ]:
        canonical = normalize_job_category(value)
        if canonical:
            return canonical

    text = f"{title} {description}".lower()

    # 2. Define weighted regex patterns for fallback inference
    # Using word boundaries \b for accuracy
    inference_patterns = {
        "operations_control": [
            r"\bocc\b",
            r"\biocc\b",
            r"\bnoc\b",
            r"\bsoc\b",
            r"\bdispatcher?\b",
            r"\bdispatch\b",
            r"\bflight dispatch",
            r"\bnetwork operat",
            r"\brégul",
            r"\brépartiteur\b",
            r"\bpréparation des vols\b",
            r"\bscheduler\b",
            r"\bflight planning\b",
            r"\bdespacho\b",
            r"\bcontrol de vuelo\b",
            r"\boperator\b",
            r"\boperations operator\b",
            r"\bflight operation",
            r"\bperformance engineer",
            r"\bpilot\b",
            r"\bcaptain\b",
            r"\bfirst officer\b",
        ],
        "crew_control": [
            r"\bcrew control\b",
            r"\bcrew schedul",
            r"\bcrew roster",
            r"\bcrew planning\b",
            r"\bcrew planner\b",
            r"\bcrew allocat",
            r"\bcrew coordinator\b",
            r"\baircrew\b",
            r"\binflight planning\b",
        ],
        "ground_operations": [
            r"\bramp\b",
            r"\bbaggage\b",
            r"\bturnaround\b",
            r"\btrc\b",
            r"\bground handler?\b",
            r"\bground ops\b",
            r"\bground operations\b",
            r"\bairport operations\b",
            r"\bmarshalling\b",
            r"\bpushback\b",
            r"\bload control\b",
            r"\bweight and balance\b",
            r"\bgate agent\b",
            r"\bcheck-?in\b",
            r"\bstation agent\b",
        ],
        "management": [
            r"\bdirector\b",
            r"\bhead of\b",
            r"\bvice president\b",
            r"\b vp \b",
            r"\bgeneral manager\b",
        ],
        "corporate": [
            r"\bsafety\b",
            r"\bsecurity\b",
            r"\bquality assurance\b",
            r"\bcompliance\b",
            r"\bsms\b",
            r"\baudit",
            r"\bregulatory\b",
            r"\bfinance\b",
            r"\bhuman resources\b",
            r"\bhr\b",
            r"\bit support\b",
            r"\blegal\b",
            r"\baccounting\b",
            r"\badministration\b",
        ],
        "maintenance": [
            r"\btechnician\b",
            r"\bmechanic\b",
            r"\bmro\b",
            r"\bavionics\b",
            r"\bmaintenance control",
            r"\bmcc\b",
            r"\bb[12]\b.*engineer",  # Matches B1 Engineer, B2 Aircraft Engineer, etc.
        ],
    }

    for category, patterns in inference_patterns.items():
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return category

    return "other"


# Word-boundary patterns. Order doesn't matter within a list — every pattern
# is tried, first hit wins the True for that flag. Patterns are kept broad on
# purpose (catch every phrasing a real job board uses) but anchored with \b so
# e.g. "senior" doesn't fire on "seniority" and "vp" doesn't fire on "service".
SENIOR_PATTERNS = [
    r"\bsenior\b",
    r"\bsnr\b",
    r"\bsr\.?\b",
    r"\blead\b",
    r"\bprincipal\b",
    r"\bexpert\b",
    r"\bchief\b",
    r"\b(?:level|lvl)\s*(?:ii|iii|2|3)\b",
    r"\b(?:ii|iii)\b\s*$",
]

MANAGER_PATTERNS = [
    r"\bmanager\b",
    r"\bmgr\b",
    r"\bdirector\b",
    r"\bhead of\b",
    r"\bvice president\b",
    r"\bvp\b",
    r"\bgeneral manager\b",
    r"\bgm\b",
    r"\bsupervisor\b",
    r"\bsupervising\b",
    r"\bdeputy director\b",
    r"\bdepartment head\b",
    r"\bteam lead(?:er)?\b",
    r"\bchief\b",
    r"\bpresident\b",
    r"\bexecutive\b",
    r"\bc[a-z]o\b",  # CEO, COO, CFO, CTO, CXO style abbreviations
    # Common non-English equivalents seen across European/LatAm career sites
    # in this dataset (French, German, Spanish/Portuguese, Italian, Polish).
    r"\bdirecteur(?:rice)?\b",
    r"\bdiretor(?:a)?\b",
    r"\bdirettore\b",
    r"\bdirectora\b",
    r"\bgerente\b",
    r"\bsuperviseur(?:e)?\b",
    r"\bsupervisore\b",
    r"\bjefe(?: de)?\b",
    r"\bkierownik\b",
    r"leiter(?:in)?\b",  # suffix match: catches Schichtleiter, Stationsleiter, Abfertigungsleiter
]


def classify_seniority(title="", description=""):
    """
    Dynamic, regex-based seniority/management classifier.
    Title-only by design — job descriptions routinely mention "senior",
    "manager", "lead" etc. in unrelated context (reporting lines, team intros,
    boilerplate), so using description text produces false positives on
    junior roles. The title is the actual signal for job *level*.
    Returns (is_senior, is_manager). Not mutually exclusive — a
    "Senior Manager" title is both.
    """
    import re

    title_text = (title or "").lower()

    is_senior = any(re.search(p, title_text, re.IGNORECASE) for p in SENIOR_PATTERNS)
    is_manager = any(re.search(p, title_text, re.IGNORECASE) for p in MANAGER_PATTERNS)

    return is_senior, is_manager


def matches_selected_categories(
    selected_categories,
    primary_category=None,
    matched_categories=None,
    matched_filter_types=None,
):
    normalized_selected = normalize_job_categories(selected_categories)
    if not normalized_selected:
        return True

    matched = set()
    for value in [
        primary_category,
        *(matched_categories or []),
        *(matched_filter_types or []),
    ]:
        canonical = normalize_job_category(value)
        if canonical:
            matched.add(canonical)

    return bool(matched.intersection(normalized_selected))
