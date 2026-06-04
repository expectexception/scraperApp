"""Scraper-side job category taxonomy helpers."""

CANONICAL_JOB_CATEGORIES = {
    "operations_control_center": "Operations Control Center",
    "flight_operations": "Flight Operations",
    "passenger_station_services": "Passenger & Station Services",
    "ground_operations": "Ground Operations",
    "maintenance_engineering": "Maintenance & Engineering",
    "air_cargo_logistics": "Air Cargo & Logistics",
    "air_traffic_control": "Air Traffic Control",
    "safety_security_quality": "Safety, Security & Quality",
    "corporate_support": "Corporate & Support",
    "training": "Training",
    "other": "Other",
}

LEGACY_CATEGORY_ALIASES = {
    "operations_control_center": {
        "operations_control_center",
        "OCC",
        "IOCC",
        "dispatcher",
        "dispatch",
        "flight dispatch",
        "ops control",
        "network control",
        "crew control",
        "load control",
        "flight preparation",
        "régulation des vols",
        "préparation des vols",
        "répartiteur",
        "despacho de vuelos",
        "centro de controle",
    },
    "flight_operations": {
        "flight_operations",
        "Pilot",
        "Captain",
        "First Officer",
        "flight crew",
        "flight deck",
        "pilote",
        "commandant de bord",
        "piloto",
        "copiloto",
    },
    "passenger_station_services": {
        "passenger_services",
        "airport_operations",
        "Passenger & Station Services",
        "Gate Agent",
        "Check-in",
        "ticketing",
        "station agent",
        "customer service agent",
        "agent d'escale",
        "agente de tráfico",
    },
    "ground_operations": {
        "ground_operations",
        "ground_staff",
        "Ramp Agent",
        "baggage handler",
        "turnaround coordinator",
        "TRC",
        "marshalling",
        "agent de piste",
        "agente de rampa",
        "gepäckabfertiger",
    },
    "maintenance_engineering": {
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
    "air_cargo_logistics": {
        "air_cargo_logistics",
        "Cargo",
        "Freight",
        "Logistics",
        "Warehouse",
        "Loadmaster",
        "fret aérien",
        "logística de carga",
    },
    "air_traffic_control": {
        "air_traffic_control",
        "ATC",
        "Air Traffic Controller",
        "tower controller",
        "contrôleur aérien",
        "controlador de tráfico aéreo",
    },
    "safety_security_quality": {
        "safety_security_quality",
        "Safety",
        "Security",
        "Quality Assurance",
        "Compliance",
        "SMS",
        "sûreté aérienne",
        "seguridad operacional",
    },
    "corporate_support": {
        "corporate_business",
        "corporate",
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
    "training": {"training", "Training", "Instructor", "Trainer", "formation"},
    "other": {"other", "Other"},
}

FILTER_CATEGORY_MAP = {
    "Core_Function_Terms_Only": "operations_control_center",
    "Operative_Functional_Control_Keywords": "operations_control_center",
    "Supervisory_Level_Control_Keywords": "operations_control_center",
    "Management_Executive_Control_Keywords": "operations_control_center",
    "Maintenance_Engineering_Control": "maintenance_engineering",
    "Operations_Performance_Analytics": "operations_control_center",
    "Flight_Deck_Crew": "flight_operations",
    "Cabin_Crew_Inflight": "passenger_station_services",
    "Ground_Airport_Operations": "ground_operations",
    "Entry_Level_Operations_Roles": "operations_control_center",
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
        "operations_control_center": [
            r"\bocc\b",
            r"\biocc\b",
            r"\bnoc\b",
            r"\bsoc\b",
            r"\bdispatcher?\b",
            r"\bdispatch\b",
            r"\bflight dispatch",
            r"\bload control",
            r"\bcrew control",
            r"\bnetwork operat",
            r"\brégul",
            r"\brépartiteur\b",
            r"\bpréparation des vols\b",
            r"\bscheduler\b",
            r"\brostering\b",
            r"\bflight planning\b",
            r"\bdespacho\b",
            r"\bcontrol de vuelo\b",
            r"\boperator\b",
            r"\boperations operator\b",
        ],
        "flight_operations": [
            r"\bpilot\b",
            r"\bcaptain\b",
            r"\bfirst officer\b",
            r"\bcopilot\b",
            r"\bflight crew\b",
            r"\bflight deck\b",
            r"\be-?f-?b\b",
            r"\bflight operation",
            r"\bperformance engineer",
        ],
        "passenger_station_services": [
            r"\bgate agent\b",
            r"\bcheck-?in\b",
            r"\bticketing\b",
            r"\bpassenger service",
            r"\bstation agent\b",
            r"\bescale\b",
            r"\bcustomer service\b",
            r"\bcabin crew\b",
            r"\bflight attendant\b",
            r"\bpurser\b",
            r"\blounge\b",
        ],
        "ground_operations": [
            r"\bramp\b",
            r"\bbaggage\b",
            r"\bturnaround\b",
            r"\btrc\b",
            r"\bground handler?\b",
            r"\bground ops\b",
            r"\bmarshalling\b",
            r"\bpushback\b",
        ],
        "maintenance_engineering": [
            r"\btechnician\b",
            r"\bmechanic\b",
            r"\bmro\b",
            r"\bavionics\b",
            r"\bmaintenance control",
            r"\bmcc\b",
            r"\bb[12]\b.*engineer",  # Matches B1 Engineer, B2 Aircraft Engineer, etc.
        ],
        "air_cargo_logistics": [
            r"\bcargo\b",
            r"\bfreight\b",
            r"\bwarehouse\b",
            r"\blogistics\b",
            r"\bloadmaster\b",
        ],
        "air_traffic_control": [
            r"\bair traffic control",
            r"\batc\b",
            r"\btower controller\b",
        ],
        "safety_security_quality": [
            r"\bsafety\b",
            r"\bsecurity\b",
            r"\bquality assurance\b",
            r"\bcompliance\b",
            r"\bsms\b",
            r"\baudit",
            r"\bregulatory\b",
        ],
        "corporate_support": [
            r"\bfinance\b",
            r"\bhuman resources\b",
            r"\bhr\b",
            r"\bit support\b",
            r"\blegal\b",
            r"\baccounting\b",
            r"\badministration\b",
        ],
        "training": [
            r"\btraining\b",
            r"\btrainer\b",
            r"\binstructor\b",
            r"\bformation\b",
        ],
    }

    for category, patterns in inference_patterns.items():
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return category

    return "other"


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
