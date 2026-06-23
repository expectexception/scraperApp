"""Scraper-side job category taxonomy helpers."""

CANONICAL_JOB_CATEGORIES = {
    "operations_control": "Operations Control",
    "crew_control": "Crew Control",
    "ground_operations": "Ground Operations",
    "management": "Management",
    "corporate": "Corporate",
    "maintenance": "Maintenance & Engineering",
    "airports_only": "Airports Only",
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
    },
    "corporate": {
        "corporate",
        "corporate_business",
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
    "Airports_Only": "airports_only",
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
    source="",
    company="",
):
    """
    Intelligent category inference based on title and description.
    Prioritizes explicit matches but falls back to regex-based keyword analysis.
    """
    import re

    source_lower = (source or "").lower()
    company_lower = (company or "").lower()
    
    # Airports Only override: Only Adani and Malta airport jobs should be classified under airports_only
    is_adani_or_malta_airport = (
        "adani_airports" in source_lower 
        or "maltairport" in source_lower 
        or "adani airports" in company_lower 
        or "malta airport" in company_lower
    )
    
    if is_adani_or_malta_airport:
        return "airports_only"

    # Swissport override: all Swissport jobs map to ground_operations
    if "swissport" in source_lower or "swissport" in company_lower:
        return "ground_operations"

    title_lower = (title or "").lower()

    # High-priority keyword overrides based on title
    # Crew Control
    if "crew" in title_lower and any(kw in title_lower for kw in ["control", "schedul", "plan", "roster", "allocat", "coord", "dispatch"]):
        return "crew_control"

    # Maintenance & Engineering
    if any(re.search(p, title_lower) for p in [
        r"\bmaintenance\b",
        r"\btechnician\b",
        r"\bmechanic\b",
        r"\bpart[- ]145\b",
        r"\bstores operative\b",
        r"\bstorekeeper\b",
        r"\bstoreperson\b",
        r"\btooling\b",
        r"\bworkshop\b",
        r"\bhangar\b",
        r"\bavionics\b",
        r"\bpowerplant\b",
        r"\bsheet[- ]metal\b",
        r"\bstructures\b",
        r"\bpropulsion\b",
        r"\b(b1|b2|lame)(\b|\.\d)",
        r"\b(camo|mcc|moc|amos|aog)\b",
        r"\btechnical records\b",
        r"\btech records\b",
        r"\b(aircraft|licensed|avionics|propulsion|powerplant|camo|mcc|moc|hangar|line|base|maintenance|b1|b2|lame|structures|structural|propulsion)\s+engineer\b"
    ]):
        return "maintenance"

    # Ground Operations
    if any(re.search(p, title_lower) for p in [
        r"\bramp\b",
        r"\bground\s+(ops|operations|operator|handler|handling|staff|agent|service|support)\b",
        r"\bairport\s+(agent|ops|operations|officer|helper|representative)\b",
        r"\bpassenger\s+(service|handling|agent|representative)\b",
        r"\bgate\s+agent\b",
        r"\bstation\s+agent\b",
        r"\bbaggage\b",
        r"\bluggage\b",
        r"\bcleaner\b",
        r"\bcabin\s+cleaner\b",
        r"\bload\s+(control|planner|planning|coordinator|master)\b",
        r"\bweight\s+and\s+balance\b",
        r"\barff\s+duty\s+manager\b",
        r"\bline\s+service\b",
        r"\bams\b",
        r"\bls\b",
        r"\bcargo\b",
    ]):
        return "ground_operations"

    # Operations Control
    if any(re.search(p, title_lower) for p in [
        r"\boperations\s+control(ler)?(s)?\b",
        r"\bocc\b",
        r"\biocc\b",
        r"\bnoc\b",
        r"\bsoc\b",
        r"\bdispatcher(s)?\b",
        r"\bdispatch(es)?\b",
        r"\bflight\s+dispatch(er)?\b",
        r"\bflight\s+planning\b",
        r"\bflight\s+operations\b",
        r"\barff\b",
        r"\bduty\s+manager\b",
    ]):
        return "operations_control"

    # High-priority keyword overrides based on title
    # 1. Management overrides (compliance and monitor, AMOS, MCC, MOC, AOG, ground ops, avionics)
    if (
        "compliance and monitor" in title_lower
        or "compliance monitor" in title_lower
        or "compliance & monitor" in title_lower
        or "compliance and monitoring" in title_lower
        or "compliance monitoring" in title_lower
        or "camaliance and monitor" in title_lower
        or "amos" in title_lower
        or re.search(r"\bmcc\b", title_lower)
        or re.search(r"\baog\b", title_lower)
        or "ground operation" in title_lower
        or "ground operantion" in title_lower
        or "ground operations" in title_lower
        or "ground ops" in title_lower
        or "avionics" in title_lower
        or "camo" in title_lower
        or "technical records" in title_lower
        or "tech records" in title_lower
    ):
        return "management"

    # 2. Corporate overrides (charter, safety, security, client, compliance)
    if (
        "charter" in title_lower
        or "safety" in title_lower
        or "safity" in title_lower
        or "security clint" in title_lower
        or "security client" in title_lower
        or "security" in title_lower
        or "client" in title_lower
        or "clint" in title_lower
        or "compliance" in title_lower
        or "compliamce" in title_lower
    ):
        return "corporate"

    # 3. Ground operations overrides (ARFF duty manager, cleaner, station agent, cargo, AMS, line service, LS)
    if (
        "arff duty manager" in title_lower
        or "cleaner" in title_lower
        or "station agent" in title_lower
        or "station agnet" in title_lower
        or "cargo" in title_lower
        or "line service" in title_lower
        or re.search(r"\bams\b", title_lower)
        or re.search(r"\bls\b", title_lower)
    ):
        return "ground_operations"

    # 4. Operations control overrides
    if "arff" in title_lower or "duty manager" in title_lower:
        return "operations_control"

    # 5. Check explicit matches from previous stages
    for value in [
        existing_category,
        primary_category,
        *(matched_categories or []),
        *(matched_filter_types or []),
    ]:
        canonical = normalize_job_category(value)
        if canonical:
            if canonical == "airports_only":
                if is_adani_or_malta_airport:
                    return "airports_only"
                continue
            return canonical

    text = f"{title} {description}".lower()

    # 6. Define weighted regex patterns for fallback inference
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
            r"\barff\b",
            r"\bduty manager\b",
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
            r"\bstation agnet\b",
            r"\bcargo\b",
            r"\bams\b",
            r"\bline service\b",
            r"\bls\b",
            r"\barff duty manager\b",
            r"\bcleaner\b",
        ],
        "management": [
            r"\bdirector\b",
            r"\bhead of\b",
            r"\bvice president\b",
            r"\b vp \b",
            r"\bgeneral manager\b",
            r"\bamos\b",
            r"\bmcc\b",
            r"\baog\b",
            r"\bground operations?\b",
            r"\bground ops\b",
            r"\bavionics\b",
            r"\bcompliance and monitor\b",
            r"\bcompliance monitor\b",
            r"\bcompliance & monitor\b",
            r"\bcompliance and monitoring\b",
            r"\bcompliance monitoring\b",
            r"\bcamaliance and monitor\b",
        ],
        "corporate": [
            r"\bcharter\b",
            r"\bsafety\b",
            r"\bsafity\b",
            r"\bsecurity\b",
            r"\bclient\b",
            r"\bclint\b",
            r"\bsecurity clint\b",
            r"\bsecurity client\b",
            r"\bcompliance\b",
            r"\bcompliamce\b",
            r"\bquality assurance\b",
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
            r"\bmaintenance control",
            r"\bb[12]\b.*engineer",  # Matches B1 Engineer, B2 Aircraft Engineer, etc.
            r"\bmoc\b",
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
