import json

with open("scraper_manager/filter_title.json", "r") as f:
    data = json.load(f)

# Massive expansion dictionaries
new_occ_keywords = [
    # General & Global English Variations
    "Operations Control Center", "Network Operations", "System Operations", "Integrated Operations",
    "Flight Operations", "Operations Controller", "Ops Controller", "Ops Control", "Flight Ops",
    "Operations Officer", "Ops Officer", "Flight Movement", "Aircraft Movement", "Movement Controller",
    "Operations Coordinator", "Ops Coordinator", "Operations Analyst", "Ops Analyst",
    "Flight Superintendent", "Operations Superintendent", "Flight Follower", "Flight Supervisor",
    
    # European/Global additions (French/Spanish/German/Italian/Portuguese)
    "Centre de Contrôle des Opérations", "Contrôleur de Vol", "Officier de Permanence",
    "Centro de Control de Operaciones", "Despachante de Vuelo", "Oficial de Operaciones",
    "Verkehrszentrale", "Flugbetrieb", "Operationskontrolle", "Flugdienst",
    "Centro Operativo", "Addetto Operativo", "Controllore di Volo",
    "Centro de Controle de Operações", "Despachante Operacional de Voo", "Oficial de Operações",

    # Regional Specific (Middle East / Asia)
    "Operations Duty Controller", "OCC Duty Officer", "Network Duty Manager", "AOC Controller",
    "Airline Operations Controller", "Operations Support Officer"
]

new_crew_keywords = [
    # Crew Control / Tracking / Scheduling
    "Crew Roistering", "Crew Rostering", "Rostering Officer", "Rostering Controller",
    "Crew Planner", "Crew Planning", "Crew Management", "Crew Allocator", "Crew Allocation",
    "Crew Support", "Crew Logistics", "Crew Services", "Crew Administrator",
    
    # Global Variations
    "Gestion des Équipages", "Planification des Équipages",
    "Control de Tripulaciones", "Planificación de Tripulaciones",
    "Crew-Planung", "Crew-Einsatz", "Crew-Steuerung",
    "Gestione Equipaggi", "Pianificazione Equipaggi"
]

new_load_keywords = [
    # Load Control / Turnaround / Weight & Balance
    "Turnaround Coordinator", "TRC", "Turnaround Controller", "Turn Controller",
    "Ramp Controller", "Ramp Coordinator", "Redcap", "Red Cap",
    "Load Sheet Officer", "Load Planner", "Centralised Load Control", "CLC",
    
    # Global Variations
    "Coordinateur de Vol", "Superviseur Piste", "Agent de Trafic",
    "Coordinador de Vuelo", "Supervisor de Rampa", "Agente de Tráfico",
    "Vorfeldkontrolleur", "Loadcontroller", "Abfertigungskoordinator",
    "Addetto al Centramento", "Coordinatore di Rampa"
]

new_maintenance_keywords = [
    "Maintenance Controller", "MCC Controller", "MOC Controller", "Maintenance Operations Center",
    "Defect Controller", "Technical Controller", "Tech Controller", "AOG Desk", "AOG Controller"
]

for filter_group in data['Filters']:
    if filter_group['FilterType'] == 'Operative_Functional_Control_Keywords':
        filter_group['Keywords'].extend([k for k in new_occ_keywords if k not in filter_group['Keywords']])
        filter_group['Keywords'].extend([k for k in new_crew_keywords if k not in filter_group['Keywords']])
        filter_group['Keywords'].extend([k for k in new_load_keywords if k not in filter_group['Keywords']])
    elif filter_group['FilterType'] == 'Maintenance_Engineering_Control':
         filter_group['Keywords'].extend([k for k in new_maintenance_keywords if k not in filter_group['Keywords']])

with open("scraper_manager/filter_title.json", "w") as f:
    json.dump(data, f, indent=2)

print("Expansion successful.")
