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
    """
    import re

    source_lower = (source or "").lower()
    company_lower = (company or "").lower()
    title_lower = (title or "").lower()
    
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

    # 1. SPECIFIC TITLE KEYWORD MATCHING (Strongest signal)

    # Maintenance & Engineering
    if any(re.search(p, title_lower) for p in [
        r"\bmaintenance\b",
        r"\bmanteinance\b",
        r"\btechnician\b",
        r"\bmechanic\b",
        r"\bmec\b",
        r"\bpart[- ]145\b",
        r"\bstores\s+(operative|keeper|person)\b",
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
        r"\b(b1|b2|lame|certifying staff|certifying)(\b|\.\d)",
        r"\b(camo|mcc|moc|amos|aog)\b",
        r"\btechnical\s+records?\b",
        r"\btech\s+records?\b",
        r"\ba&p\b",
        r"\ba\s*&\s*p\b",
        r"\bmaintenance controller\b",
        r"\bmaintenance instructor\b",
        r"\b(aircraft|licensed|avionics|propulsion|powerplant|camo|mcc|moc|hangar|line|base|maintenance|b1|b2|lame|structures|structural|propulsion)\s+engineer\b"
    ]):
        return "maintenance"

    # Ground Operations (Ramp, Cargo, Airport Station Services)
    if any(re.search(p, title_lower) for p in [
        r"\bramp\b",
        r"\bground\s+(ops|operations|operator|handler|handling|staff|agent|service|support|safety)\b",
        r"\bairport\s+(agent|ops|operations|officer|helper|representative|lead|manager|services)\b",
        r"\bpassenger\s+(service|handling|agent|representative)\b",
        r"\bgate\s+agent\b",
        r"\bstation\s+(agent|supervisor|load master|loadmaster|representative)\b",
        r"\bbaggage\b",
        r"\bluggage\b",
        r"\bcleaner\b",
        r"\bcabin\s+cleaner\b",
        r"\bload\s+(control|planner|planning|coordinator|master|controller)\b",
        r"\bload\s+controller\b",
        r"\bloadmaster\b",
        r"\bweight\s+and\s+balance\b",
        r"\bline\s+service\b",
        r"\bams\b",
        r"\bls\b",
        r"\bcargo\b",
        r"\bwheelchair\b",
        r"\bcatering\b",
        r"\bdnata\b",
        r"\bturnaround\b",
        r"\bturn\s*around\b",
        r"\bstoc\b",
        r"\btrc\b",
        r"\bops\s+agent\b",
        r"\boperations\s+agent\b",
        r"\bterminal\b",
        r"\bagente\s+de\s+rampa\b",  # Spanish: ramp agent
        r"\bagent\s+de\s+piste\b",   # French: ramp agent
        r"\bagente\s+de\s+aeropuerto\b",
    ]):
        return "ground_operations"

    # Crew Control
    # Filter out titles like "Airport Operations Crew" or "Ground Operations Crew" which belong to ground_operations
    if ("crew" in title_lower or "roster" in title_lower) and not any(kw in title_lower for kw in ["ground", "airport", "maintenance"]):
        return "crew_control"

    # Operations Control (Dispatch, OCC, Flight Ops, Pilot)
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
        r"\bflight\s+ops\b",
        r"\bflight\s+coordinator\b",
        r"\boperations\s+support\b",
        r"\bops\s+support\b",
        r"\barff\b",
        r"\bduty\s+manager\b",
        r"\bfoo\b",
        r"\bflight\s+data\b",
        r"\bfdm\b",
        r"\bpilot\b",
        r"\bcaptain\b",
        r"\bfirst\s+officer\b",
        r"\bflight\s+instructor\b",
        r"\bexaminer\b",
        r"\binstructor\b",
        r"\baviation\s+operations\b",
        r"\baeronautical\b",
        r"\brégulateur\b",
        r"\brégulation\b",
        r"\bexploitation\b",
        r"\bcco\b",
        r"\bfollower\b",
        r"\bscheduler\b",
    ]):
        return "operations_control"

    # Corporate (Finance, HR, Safety, Compliance)
    if any(re.search(p, title_lower) for p in [
        r"\bsafety\b",
        r"\bsafity\b",
        r"\bsecurity\b",
        r"\bclient\b",
        r"\bclint\b",
        r"\bcompliance\b",
        r"\bcompliamce\b",
        r"\bquality\b",
        r"\baudit(or)?\b",
        r"\bregulatory\b",
        r"\bfinance\b",
        r"\baccounting\b",
        r"\bprocurement\b",
        r"\bpurchasing\b",
        r"\bbuyer\b",
        r"\bsupply\s+chain\b",
        r"\bhuman\s+resources\b",
        r"\bhr\b",
        r"\brecruiter\b",
        r"\blegal\b",
        r"\bmarketing\b",
        r"\bsales\b",
        r"\bit\s+support\b",
        r"\bdeveloper\b",
        r"\bsoftware\b",
        r"\bdesigner\b",
        r"\banalyst\b",
        r"\bcontract(s)?\b",
        r"\bsubject\s+matter\s+expert\b",
        r"\bsme\b",
        r"\bdocumentation\b",
        r"\bcommercial\b",
        r"\bpricing\b",
        r"\bdistribution\b",
        r"\bdevelopment\b",
    ]):
        return "corporate"

    # General Management (if not matched by specific roles above)
    if any(re.search(p, title_lower) for p in [
        r"\bdirector\b",
        r"\bhead\b",
        r"\bvp\b",
        r"\bvice\s+president\b",
        r"\bgeneral\s+manager\b",
        r"\bchief\b",
        r"\bmanager\b",
    ]):
        return "management"

    # 2. FALLBACK DESCRIPTION-BASED KEYWORD MATCHING
    text = f"{title} {description}".lower()

    # Maintenance
    if any(re.search(p, text) for p in [
        r"\bmaintenance\b", r"\btechnician\b", r"\bmechanic\b", r"\bavionics\b",
        r"\bpart[- ]145\b", r"\bhangar\b", r"\b(b1|b2|lame)\b", r"\bcamo\b", r"\bmcc\b"
    ]):
        return "maintenance"

    # Crew Control
    if any(re.search(p, text) for p in [
        r"\bcrew control\b", r"\bcrew schedul", r"\bcrew roster", r"\bcrew planning\b",
        r"\bcrew planner\b", r"\bcrew allocat", r"\bcrew coordinator\b", r"\baircrew\b"
    ]):
        return "crew_control"

    # Ground Operations
    if any(re.search(p, text) for p in [
        r"\bramp\b", r"\bbaggage\b", r"\bturnaround\b", r"\bground handler\b",
        r"\bground operations\b", r"\bairport operations\b", r"\bstation agent\b",
        r"\bcargo\b", r"\bdnata\b"
    ]):
        return "ground_operations"

    # Operations Control
    if any(re.search(p, text) for p in [
        r"\bocc\b", r"\biocc\b", r"\bnoc\b", r"\bsoc\b", r"\bdispatcher\b", r"\bdispatch\b",
        r"\bflight dispatch", r"\bflight planning\b", r"\bflight operations\b", r"\bpilot\b"
    ]):
        return "operations_control"

    # Corporate
    if any(re.search(p, text) for p in [
        r"\bsafety\b", r"\bsecurity\b", r"\bcompliance\b", r"\bquality\b", r"\baudit\b",
        r"\bfinance\b", r"\bhuman resources\b", r"\bhr\b", r"\blegal\b", r"\baccounting\b"
    ]):
        return "corporate"

    # 3. Fallback logic: check explicit matches from previous stages
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
