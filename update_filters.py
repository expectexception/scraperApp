import json

with open("scraper_manager/filter_title.json", "r") as f:
    data = json.load(f)

# Define new European keywords
european_ops_keywords = [
    "Agent technique d'exploitation", "Agent d'opérations", "Agent de préparation des vols", 
    "Régulateur de vol", "Superviseur Opérations", "Contrôleur de réseau",
    "Despachador de vuelo", "Técnico de Operaciones Vuelo", "Coordinador de vuelo", 
    "Controlador Operaciones", "Técnico de Despacho", "Técnico de operaciones",
    "Flugdienstberater", "Einsatzleiter", "Flugdienstleiter", "Verkehrsleiter", "Einsatzsteuerer",
    "Disponente al volo", "Coordinatore Operativo"
]

# Define core high-confidence single/short terms
core_acronyms_keywords = [
    "OCC", "IOCC", "NOC", "MCC", "Flight Dispatch", "Aircraft Dispatch", "Dispatching"
]

# See if Core_Function_Terms_Only exists, if not create it
core_exists = False
op_exists = False

for filter_group in data['Filters']:
    if filter_group['FilterType'] == 'Operative_Functional_Control_Keywords':
        op_exists = True
        # add only unique items to avoid duplicates
        for kw in european_ops_keywords:
            if kw not in filter_group['Keywords']:
                filter_group['Keywords'].append(kw)
    if filter_group['FilterType'] == 'Core_Function_Terms_Only':
        core_exists = True
        for kw in core_acronyms_keywords:
            if kw not in filter_group['Keywords']:
                filter_group['Keywords'].append(kw)

if not core_exists:
    # We must insert it since it has high weight in filter_manager.py
    data['Filters'].insert(0, {
        "FilterType": "Core_Function_Terms_Only",
        "DisplayName": "Core Operations Acronyms",
        "Description": "Absolutely certain single-word acronyms that uniquely define OCC roles.",
        "Keywords": core_acronyms_keywords,
        "NegativeKeywords": [
            "Pilot", "Cabin Crew", "Mechanic", "Technician", "Finance", "HR", "Sales", "Marketing"
        ]
    })

with open("scraper_manager/filter_title.json", "w") as f:
    json.dump(data, f, indent=2)

print("Filters updated successfully!")
