"""Scraper-side job category taxonomy helpers."""

CANONICAL_JOB_CATEGORIES = {
    'operations_control_center': 'Operations Control Center',
    'flight_operations': 'Flight Operations',
    'passenger_services': 'Passenger Services',
    'ground_operations': 'Ground Operations',
    'airport_operations': 'Airport Operations',
    'maintenance_engineering': 'Maintenance & Engineering',
    'air_cargo_logistics': 'Air Cargo & Logistics',
    'air_traffic_control': 'Air Traffic Control',
    'corporate_business': 'Corporate & Business Aviation',
    'training': 'Training',
    'other': 'Other',
}

LEGACY_CATEGORY_ALIASES = {
    'operations_control_center': {'operations_control_center', 'Operations Control Center', 'occ', 'dispatcher'},
    'flight_operations': {'flight_operations', 'Flight Operations', 'flight_crew', 'Flight Crew'},
    'passenger_services': {'passenger_services', 'Passenger Services', 'cabin_crew', 'Cabin Crew'},
    'ground_operations': {'ground_operations', 'Ground Operations', 'ground_staff', 'Ground Staff', 'Ground Ops'},
    'airport_operations': {'airport_operations', 'Airport Operations'},
    'maintenance_engineering': {'maintenance_engineering', 'Maintenance & Engineering', 'maintenance', 'Engineering'},
    'air_cargo_logistics': {'air_cargo_logistics', 'Air Cargo & Logistics', 'cargo', 'air cargo'},
    'air_traffic_control': {'air_traffic_control', 'Air Traffic Control', 'Air Traffic Controller'},
    'corporate_business': {'corporate_business', 'Corporate & Business Aviation', 'Corporate / Business', 'management', 'Management'},
    'training': {'training', 'Training'},
    'other': {'other', 'Other'},
}

FILTER_CATEGORY_MAP = {
    'Core Operations Acronyms': 'operations_control_center',
    'Core Operational Roles': 'operations_control_center',
    'Supervisory Level': 'operations_control_center',
    'Management & Executive': 'operations_control_center',
    'Flight Crew': 'flight_operations',
    'Cabin Crew': 'passenger_services',
    'Ground Operations': 'ground_operations',
    'Maintenance & Engineering': 'maintenance_engineering',
    'Core_Function_Terms_Only': 'operations_control_center',
    'Operative_Functional_Control_Keywords': 'operations_control_center',
    'Supervisory_Level_Control_Keywords': 'operations_control_center',
    'Management_Executive_Control_Keywords': 'operations_control_center',
    'Flight_Deck_Crew': 'flight_operations',
    'Cabin_Crew_Inflight': 'passenger_services',
    'Ground_Airport_Operations': 'ground_operations',
    'Maintenance_Engineering': 'maintenance_engineering',
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
        values = [item.strip() for item in values.split(',') if item.strip()]

    normalized = []
    for value in values:
        canonical = normalize_job_category(value)
        if canonical and canonical not in normalized:
            normalized.append(canonical)
    return normalized


def infer_job_category(title='', description='', primary_category=None, matched_categories=None, matched_filter_types=None, existing_category=None):
    for value in [existing_category, primary_category, *(matched_categories or []), *(matched_filter_types or [])]:
        canonical = normalize_job_category(value)
        if canonical:
            return canonical

    text = f"{title} {description}".lower()

    if any(token in text for token in ['occ', 'iocc', 'noc', 'mcc', 'dispatcher', 'dispatch officer', 'flight dispatch', 'operations control', 'crew control', 'load control', 'network operations']):
        return 'operations_control_center'
    if any(token in text for token in ['pilot', 'captain', 'first officer', 'copilot', 'flight crew']):
        return 'flight_operations'
    if any(token in text for token in ['cabin crew', 'flight attendant', 'purser', 'inflight', 'passenger service']):
        return 'passenger_services'
    if any(token in text for token in ['air traffic control', 'air traffic controller', 'tower controller', 'approach controller', 'radar controller', 'atc']):
        return 'air_traffic_control'
    if any(token in text for token in ['cargo', 'freight', 'airfreight', 'warehouse', 'logistics', 'loadmaster']):
        return 'air_cargo_logistics'
    if any(token in text for token in ['airport operations', 'airport agent', 'airside', 'gate agent', 'check-in', 'ticketing', 'station agent', 'terminal operations']):
        return 'airport_operations'
    if any(token in text for token in ['ramp', 'baggage', 'ground handler', 'ground ops', 'marshalling', 'pushback', 'turnaround coordinator']):
        return 'ground_operations'
    if any(token in text for token in ['technician', 'mechanic', 'mro', 'avionics', 'maintenance engineer', 'line maintenance', 'base maintenance']):
        return 'maintenance_engineering'
    if any(token in text for token in ['training', 'trainer', 'instructor', 'simulator instructor', 'ground school']):
        return 'training'
    if any(token in text for token in ['director', 'vice president', 'head of', 'general manager', 'corporate', 'business aviation', 'charter', 'vip', 'finance', 'legal', 'marketing', 'sales']):
        return 'corporate_business'
    return 'other'


def matches_selected_categories(selected_categories, primary_category=None, matched_categories=None, matched_filter_types=None):
    normalized_selected = normalize_job_categories(selected_categories)
    if not normalized_selected:
        return True

    matched = set()
    for value in [primary_category, *(matched_categories or []), *(matched_filter_types or [])]:
        canonical = normalize_job_category(value)
        if canonical:
            matched.add(canonical)

    return bool(matched.intersection(normalized_selected))