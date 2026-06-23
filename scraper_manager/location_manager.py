import re
from typing import Optional


class LocationManager:
    """
    Centralized utility for normalizing and standardizing job locations.
    Handles country code conversion, city-to-country mapping, and postal code resolution.
    """

    # Map from 2-letter ISO country codes to full country names (Comprehensive)
    CC_TO_NAME = {
        "AF": "Afghanistan",
        "AX": "Åland Islands",
        "AL": "Albania",
        "DZ": "Algeria",
        "AS": "American Samoa",
        "AD": "Andorra",
        "AO": "Angola",
        "AI": "Anguilla",
        "AQ": "Antarctica",
        "AG": "Antigua and Barbuda",
        "AR": "Argentina",
        "AM": "Armenia",
        "AW": "Aruba",
        "AU": "Australia",
        "AT": "Austria",
        "AZ": "Azerbaijan",
        "BS": "Bahamas",
        "BH": "Bahrain",
        "BD": "Bangladesh",
        "BB": "Barbados",
        "BY": "Belarus",
        "BE": "Belgium",
        "BZ": "Belize",
        "BJ": "Benin",
        "BM": "Bermuda",
        "BT": "Bhutan",
        "BO": "Bolivia",
        "BQ": "Bonaire, Sint Eustatius and Saba",
        "BA": "Bosnia and Herzegovina",
        "BW": "Botswana",
        "BV": "Bouvet Island",
        "BR": "Brazil",
        "IO": "British Indian Ocean Territory",
        "BN": "Brunei Darussalam",
        "BG": "Bulgaria",
        "BF": "Burkina Faso",
        "BI": "Burundi",
        "CV": "Cabo Verde",
        "KH": "Cambodia",
        "CM": "Cameroon",
        "CA": "Canada",
        "KY": "Cayman Islands",
        "CF": "Central African Republic",
        "TD": "Chad",
        "CL": "Chile",
        "CN": "China",
        "CX": "Christmas Island",
        "CC": "Cocos (Keeling) Islands",
        "CO": "Colombia",
        "KM": "Comoros",
        "CG": "Congo",
        "CD": "Congo (DR)",
        "CK": "Cook Islands",
        "CR": "Costa Rica",
        "CI": "Côte d'Ivoire",
        "HR": "Croatia",
        "CU": "Cuba",
        "CW": "Curaçao",
        "CY": "Cyprus",
        "CZ": "Czech Republic",
        "DK": "Denmark",
        "DJ": "Djibouti",
        "DM": "Dominica",
        "DO": "Dominican Republic",
        "EC": "Ecuador",
        "EG": "Egypt",
        "SV": "El Salvador",
        "GQ": "Equatorial Guinea",
        "ER": "Eritrea",
        "EE": "Estonia",
        "SZ": "Eswatini",
        "ET": "Ethiopia",
        "FK": "Falkland Islands",
        "FO": "Faroe Islands",
        "FJ": "Fiji",
        "FI": "Finland",
        "FR": "France",
        "GF": "French Guiana",
        "PF": "French Polynesia",
        "TF": "French Southern Territories",
        "GA": "Gabon",
        "GM": "Gambia",
        "GE": "Georgia",
        "DE": "Germany",
        "GH": "Ghana",
        "GI": "Gibraltar",
        "GR": "Greece",
        "GL": "Greenland",
        "GD": "Grenada",
        "GP": "Guadeloupe",
        "GU": "Guam",
        "GT": "Guatemala",
        "GG": "Guernsey",
        "GN": "Guinea",
        "GW": "Guinea-Bissau",
        "GY": "Guyana",
        "HT": "Haiti",
        "HM": "Heard Island and McDonald Islands",
        "VA": "Holy See",
        "HN": "Honduras",
        "HK": "Hong Kong",
        "HU": "Hungary",
        "IS": "Iceland",
        "IN": "India",
        "ID": "Indonesia",
        "IR": "Iran",
        "IQ": "Iraq",
        "IE": "Ireland",
        "IM": "Isle of Man",
        "IL": "Israel",
        "IT": "Italy",
        "JM": "Jamaica",
        "JP": "Japan",
        "JE": "Jersey",
        "JO": "Jordan",
        "KZ": "Kazakhstan",
        "KE": "Kenya",
        "KI": "Kiribati",
        "KP": "North Korea",
        "KR": "South Korea",
        "KW": "Kuwait",
        "KG": "Kyrgyzstan",
        "LA": "Laos",
        "LV": "Latvia",
        "LB": "Lebanon",
        "LS": "Lesotho",
        "LR": "Liberia",
        "LY": "Libya",
        "LI": "Liechtenstein",
        "LT": "Lithuania",
        "LU": "Luxembourg",
        "MO": "Macao",
        "MG": "Madagascar",
        "MW": "Malawi",
        "MY": "Malaysia",
        "MV": "Maldives",
        "ML": "Mali",
        "MT": "Malta",
        "MH": "Marshall Islands",
        "MQ": "Martinique",
        "MR": "Mauritania",
        "MU": "Mauritius",
        "YT": "Mayotte",
        "MX": "Mexico",
        "FM": "Micronesia",
        "MD": "Moldova",
        "MC": "Monaco",
        "MN": "Mongolia",
        "ME": "Montenegro",
        "MS": "Montserrat",
        "MA": "Morocco",
        "MZ": "Mozambique",
        "MM": "Myanmar",
        "NA": "Namibia",
        "NR": "Nauru",
        "NP": "Nepal",
        "NL": "Netherlands",
        "NC": "New Caledonia",
        "NZ": "New Zealand",
        "NI": "Nicaragua",
        "NE": "Niger",
        "NG": "Nigeria",
        "NU": "Niue",
        "NF": "Norfolk Island",
        "MP": "Northern Mariana Islands",
        "NO": "Norway",
        "OM": "Oman",
        "PK": "Pakistan",
        "PW": "Palau",
        "PS": "Palestine",
        "PA": "Panama",
        "PG": "Papua New Guinea",
        "PY": "Paraguay",
        "PE": "Peru",
        "PH": "Philippines",
        "PN": "Pitcairn",
        "PL": "Poland",
        "PT": "Portugal",
        "PR": "Puerto Rico",
        "QA": "Qatar",
        "RE": "Réunion",
        "RO": "Romania",
        "RU": "Russian Federation",
        "RW": "Rwanda",
        "BL": "Saint Barthélemy",
        "SH": "Saint Helena",
        "KN": "Saint Kitts and Nevis",
        "LC": "Saint Lucia",
        "MF": "Saint Martin",
        "PM": "Saint Pierre and Miquelon",
        "VC": "Saint Vincent and the Grenadines",
        "WS": "Samoa",
        "SM": "San Marino",
        "ST": "Sao Tome and Principe",
        "SA": "Saudi Arabia",
        "SN": "Senegal",
        "RS": "Serbia",
        "SC": "Seychelles",
        "SL": "Sierra Leone",
        "SG": "Singapore",
        "SX": "Sint Maarten",
        "SK": "Slovakia",
        "SI": "Slovenia",
        "SB": "Solomon Islands",
        "SO": "Somalia",
        "ZA": "South Africa",
        "GS": "South Georgia and the South Sandwich Islands",
        "SS": "South Sudan",
        "ES": "Spain",
        "LK": "Sri Lanka",
        "SD": "Sudan",
        "SR": "Suriname",
        "SJ": "Svalbard and Jan Mayen",
        "SE": "Sweden",
        "CH": "Switzerland",
        "SY": "Syria",
        "TW": "Taiwan",
        "TJ": "Tajikistan",
        "TZ": "Tanzania",
        "TH": "Thailand",
        "TL": "Timor-Leste",
        "TG": "Togo",
        "TK": "Tokelau",
        "TO": "Tonga",
        "TT": "Trinidad and Tobago",
        "TN": "Tunisia",
        "TR": "Turkey",
        "TM": "Turkmenistan",
        "TC": "Turks and Caicos Islands",
        "TV": "Tuvalu",
        "UG": "Uganda",
        "UA": "Ukraine",
        "AE": "United Arab Emirates",
        "GB": "United Kingdom",
        "US": "United States",
        "UM": "US Minor Outlying Islands",
        "UY": "Uruguay",
        "UZ": "Uzbekistan",
        "VU": "Vanuatu",
        "VE": "Venezuela",
        "VN": "Viet Nam",
        "VG": "Virgin Islands (British)",
        "VI": "Virgin Islands (U.S.)",
        "WF": "Wallis and Futuna",
        "EH": "Western Sahara",
        "YE": "Yemen",
        "ZM": "Zambia",
        "ZW": "Zimbabwe",
    }

    # International postal country-prefix → (ISO-2-code, country name, default major-city)
    POSTAL_PREFIX_MAP = {
        "H": ("HU", "Hungary", "Budapest"),
        "A": ("AT", "Austria", "Vienna"),
        "D": ("DE", "Germany", "Frankfurt"),
        "F": ("FR", "France", "Paris"),
        "I": ("IT", "Italy", "Milan"),
        "E": ("ES", "Spain", "Madrid"),
        "P": ("PT", "Portugal", "Lisbon"),
        "B": ("BE", "Belgium", "Brussels"),
        "NL": ("NL", "Netherlands", "Amsterdam"),
        "CH": ("CH", "Switzerland", "Zurich"),
        "PL": ("PL", "Poland", "Warsaw"),
        "CZ": ("CZ", "Czech Republic", "Prague"),
        "SK": ("SK", "Slovakia", "Bratislava"),
        "RO": ("RO", "Romania", "Bucharest"),
        "BG": ("BG", "Bulgaria", "Sofia"),
        "HR": ("HR", "Croatia", "Zagreb"),
        "SI": ("SI", "Slovenia", "Ljubljana"),
        "GR": ("GR", "Greece", "Athens"),
        "LT": ("LT", "Lithuania", "Vilnius"),
        "LV": ("LV", "Latvia", "Riga"),
        "EE": ("EE", "Estonia", "Tallinn"),
        "SE": ("SE", "Sweden", "Stockholm"),
        "NO": ("NO", "Norway", "Oslo"),
        "DK": ("DK", "Denmark", "Copenhagen"),
        "FI": ("FI", "Finland", "Helsinki"),
        "GB": ("GB", "United Kingdom", "London"),
        "IE": ("IE", "Ireland", "Dublin"),
        "HU": ("HU", "Hungary", "Budapest"),
    }

    # Common cities or airport codes to Country mappings (Dynamic Aviation Logic)
    HUB_TO_COUNTRY = {
        # Europe
        "CPH": "Denmark",
        "ARN": "Sweden",
        "OSL": "Norway",
        "HEL": "Finland",
        "LHR": "United Kingdom",
        "LGW": "United Kingdom",
        "STN": "United Kingdom",
        "MAN": "United Kingdom",
        "CDG": "France",
        "ORY": "France",
        "NCE": "France",
        "AMS": "Netherlands",
        "FRA": "Germany",
        "MUC": "Germany",
        "BER": "Germany",
        "HAM": "Germany",
        "DUS": "Germany",
        "ZRH": "Switzerland",
        "GVA": "Switzerland",
        "VIE": "Austria",
        "BRU": "Belgium",
        "MAD": "Spain",
        "BCN": "Spain",
        "PMI": "Spain",
        "LIS": "Portugal",
        "OPO": "Portugal",
        "FCO": "Italy",
        "MXP": "Italy",
        "VCE": "Italy",
        "ATH": "Greece",
        "WAW": "Poland",
        "PRG": "Czech Republic",
        "BUD": "Hungary",
        "OTP": "Romania",
        "SJJ": "Bosnia and Herzegovina",
        "BEG": "Serbia",
        "ZAG": "Croatia",
        "LJU": "Slovenia",
        "SKP": "North Macedonia",
        "TIA": "Albania",
        "DUB": "Ireland",
        "ORK": "Ireland",
        "KEF": "Iceland",
        # Asia & Middle East
        "DXB": "United Arab Emirates",
        "AUH": "United Arab Emirates",
        "DOH": "Qatar",
        "SIN": "Singapore",
        "HKG": "Hong Kong",
        "NRT": "Japan",
        "HND": "Japan",
        "ICN": "South Korea",
        "PEK": "China",
        "PVG": "China",
        "CAN": "China",
        "BKK": "Thailand",
        "DMK": "Thailand",
        "SGN": "Vietnam",
        "HAN": "Vietnam",
        "KUL": "Malaysia",
        "CGK": "Indonesia",
        "DPS": "Indonesia",
        "MNL": "Philippines",
        "DEL": "India",
        "BOM": "India",
        "BLR": "India",
        "MAA": "India",
        "SYD": "Australia",
        "MEL": "Australia",
        "BNE": "Australia",
        "AKL": "New Zealand",
        "IST": "Turkey",
        "SAW": "Turkey",
        "TLV": "Israel",
        "AMM": "Jordan",
        "BEY": "Lebanon",
        # Americas
        "JFK": "United States",
        "LAX": "United States",
        "ORD": "United States",
        "DFW": "United States",
        "ATL": "United States",
        "SFO": "United States",
        "MIA": "United States",
        "EWR": "United States",
        "YUL": "Canada",
        "YYZ": "Canada",
        "YVR": "Canada",
        "YYC": "Canada",
        "MEX": "Mexico",
        "CUN": "Mexico",
        "GRU": "Brazil",
        "GIG": "Brazil",
        "EZE": "Argentina",
        "SCL": "Chile",
        "BOG": "Colombia",
        "LIM": "Peru",
        "PTY": "Panama",
        "SSA": "Brazil",
        "BSB": "Brazil",
        "CNF": "Brazil",
        "FOR": "Brazil",
        "POA": "Brazil",  # dnata Brasil
        "ALG": "Algeria",
        "ORN": "Algeria",
        "CZL": "Algeria",
        "AAE": "Algeria",  # Emploitic
        # Africa
        "JNB": "South Africa",
        "CPT": "South Africa",
        "CAI": "Egypt",
        "ADD": "Ethiopia",
        "NBO": "Kenya",
        "CMN": "Morocco",
        "LOS": "Nigeria",
    }

    CITY_TO_COUNTRY = {
        "sønderborg": "Denmark",
        "billund": "Denmark",
        "aarhus": "Denmark",
        "appleton": "United States",
        "herndon": "United States",
        "luton": "United Kingdom",
        "frankfurt": "Germany",
        "munich": "Germany",
        "berlin": "Germany",
        "hamburg": "Germany",
        "düsseldorf": "Germany",
        "dusseldorf": "Germany",
        "cologne": "Germany",
        "koln": "Germany",
        "dubai": "United Arab Emirates",
        "abu dhabi": "United Arab Emirates",
        "sharjah": "United Arab Emirates",
        "budapest": "Hungary",
        "warsaw": "Poland",
        "prague": "Czech Republic",
        "bucharest": "Romania",
        "vienna": "Austria",
        "zurich": "Switzerland",
        "geneva": "Switzerland",
        # France — extensive coverage for Airbus & aviation hubs
        "paris": "France",
        "nice": "France",
        "lyon": "France",
        "toulouse": "France",
        "blagnac": "France",
        "colomiers": "France",
        "bordeaux": "France",
        "marseille": "France",
        "nantes": "France",
        "strasbourg": "France",
        "montpellier": "France",
        "lille": "France",
        "rennes": "France",
        "grenoble": "France",
        "saint-nazaire": "France",
        "saint nazaire": "France",
        "méaulte": "France",
        "meaulte": "France",
        "elancourt": "France",
        "élancourt": "France",
        "velizy": "France",
        "marignane": "France",
        "istres": "France",
        "madrid": "Spain",
        "barcelona": "Spain",
        "malaga": "Spain",
        "seville": "Spain",
        "bilbao": "Spain",
        "puerto real": "Spain",
        "getafe": "Spain",
        "lisbon": "Portugal",
        "faro": "Portugal",
        "porto": "Portugal",
        "rome": "Italy",
        "milan": "Italy",
        "venice": "Italy",
        "naples": "Italy",
        "turin": "Italy",
        "pomigliano": "Italy",
        "athens": "Greece",
        "thessaloniki": "Greece",
        "amsterdam": "Netherlands",
        "rotterdam": "Netherlands",
        "eindhoven": "Netherlands",
        "brussels": "Belgium",
        "antwerp": "Belgium",
        "liege": "Belgium",
        "london": "United Kingdom",
        "manchester": "United Kingdom",
        "birmingham": "United Kingdom",
        "bristol": "United Kingdom",
        "filton": "United Kingdom",
        "broughton": "United Kingdom",
        "stevenage": "United Kingdom",
        "newport": "United Kingdom",
        "dublin": "Ireland",
        "shannon": "Ireland",
        "stockholm": "Sweden",
        "gothenburg": "Sweden",
        "malmo": "Sweden",
        "oslo": "Norway",
        "bergen": "Norway",
        "stavanger": "Norway",
        "helsinki": "Finland",
        "vantaa": "Finland",
        "tampere": "Finland",
        "montreal": "Canada",
        "toronto": "Canada",
        "vancouver": "Canada",
        "calgary": "Canada",
        "sao paulo": "Brazil",
        "rio de janeiro": "Brazil",
        "brasilia": "Brazil",
        "salvador": "Brazil",
        "aracaju": "Brazil",
        "fortaleza": "Brazil",
        "belo horizonte": "Brazil",
        "porto alegre": "Brazil",
        "algiers": "Algeria",
        "oran": "Algeria",
        "constantine": "Algeria",
        "annaba": "Algeria",
        "blida": "Algeria",
        "setif": "Algeria",
        "alger": "Algeria",
        "philadelphia": "United States",
        "phoenix": "United States",
        "chicago": "United States",
        "houston": "United States",
        "san antonio": "United States",
        "san diego": "United States",
        "dallas": "United States",
        "san jose": "United States",
        "austin": "United States",
        "memphis": "United States",
        "indianapolis": "United States",
        "jacksonville": "United States",
        "fort worth": "United States",
        "columbus": "United States",
        "charlotte": "United States",
        "riyadh": "Saudi Arabia",
        "jeddah": "Saudi Arabia",
        "dammam": "Saudi Arabia",
        "kuwait city": "Kuwait",
        "muscat": "Oman",
        "manama": "Bahrain",
        "singapore": "Singapore",
        "kuala lumpur": "Malaysia",
        "jakarta": "Indonesia",
        "bangkok": "Thailand",
        "manila": "Philippines",
        "ho chi minh": "Vietnam",
        "hanoi": "Vietnam",
        "tokyo": "Japan",
        "osaka": "Japan",
        "seoul": "South Korea",
        "beijing": "China",
        "shanghai": "China",
        "hong kong": "Hong Kong",
        "taipei": "Taiwan",
        "johannesburg": "South Africa",
        "cape town": "South Africa",
        "cairo": "Egypt",
        "addis ababa": "Ethiopia",
        "nairobi": "Kenya",
        "lagos": "Nigeria",
        "casablanca": "Morocco",
        "montreal (st. laurent)": "Canada",
        "molinfaing": "Belgium",
        "bremen": "Germany",
        "sa-riyadh": "Saudi Arabia",
        "luxembourg": "Luxembourg",
        "tallinn": "Estonia",
        "weiswampach (lu)": "Luxembourg",
        "bangalore ho": "India",
        "europe/austria": "Austria",
        "geilenkirchen": "Germany",
        "moose jaw": "Canada",
        "langenhagen": "Germany",
        "deisslingen": "Germany",
        "weiswampach": "Luxembourg",
        "grace-hollogne": "Belgium",
        "luqa": "Malta",
        "ta'xbiex": "Malta",
        "lillestroem": "Norway",
        "lillestrøm": "Norway",
        "helsingborg": "Sweden",
        "kloten": "Switzerland",
        "spata": "Greece",
        "colombo": "Sri Lanka",
        "pune": "India",
        "mumbai": "India",
        "bangalore": "India",
        "boston": "United States",
        "smyrna": "United States",
        "wichita": "United States",
        "seattle": "United States",
        "mesa": "United States",
        "las vegas": "United States",
        "los angeles": "United States",
        "everett": "United States",
        "tulsa": "United States",
        "atlanta": "United States",
        "cleveland": "United States",
        "erlanger": "United States",
        "oxford": "United States",
        "mirabel": "Canada",
        "hamilton": "Canada",
        "moncton": "Canada",
        "heathrow": "United Kingdom",
        "maidstone": "United Kingdom",
        "deutsch-wagram": "Austria",
        "klagenfurt": "Austria",
        "ferlach": "Austria",
        "belgrade": "Serbia",
        "dorval": "Canada",
        "praha": "Czech Republic",
        "zweibrücken": "Germany",
        "zweibruecken": "Germany",
        "senningerberg": "Luxembourg",
        "christchurch": "New Zealand",
        "lausanne": "Switzerland",
        "konstanz": "Germany",
    }

    # Non-English country names/spellings seen on EU/LatAm career sites.
    # Mapped to the canonical English name used as a value in CC_TO_NAME.
    ALT_COUNTRY_NAMES = {
        "deutschland": "Germany",
        "österreich": "Austria",
        "osterreich": "Austria",
        "schweiz": "Switzerland",
        "suisse": "Switzerland",
        "svizzera": "Switzerland",
        "frankreich": "France",
        "italia": "Italy",
        "españa": "Spain",
        "espana": "Spain",
        "česká republika": "Czech Republic",
        "ceska republika": "Czech Republic",
        "polska": "Poland",
        "belgië": "Belgium",
        "belgie": "Belgium",
        "belgique": "Belgium",
        "nederland": "Netherlands",
        "luxemburg": "Luxembourg",
        "brasil": "Brazil",
        "méxico": "Mexico",
        "mexico": "Mexico",
        "danmark": "Denmark",
        "norge": "Norway",
        "sverige": "Sweden",
        "suomi": "Finland",
        "magyarország": "Hungary",
        "magyarorszag": "Hungary",
    }

    # Map for specific postal codes reported by user
    SPECIAL_IDENTIFIERS = {
        "lu2 9ly": "United Kingdom",  # Luton Airport
    }

    COMPANY_TO_LOCATION = {
        "air wisconsin": "Appleton, United States",
        "air transport services group": "Wilmington, United States",
        "atsg": "Wilmington, United States",
        "gridiron air": "United States",
        "frontier airlines": "Denver, United States",
        "mountain air cargo": "Denver, United States",
        "sun country airlines": "Minneapolis, United States",
        "cae": "Montreal, Canada",
        "air india": "India",
        "indigo": "India",
        "emirates": "Dubai, United Arab Emirates",
        "wizz air": "Budapest, Hungary",
        "ita airways": "Rome, Italy",
        "aegean airlines": "Athens, Greece",
        "lufthansa": "Germany",
        "british airways": "London, United Kingdom",
        "qatar": "Doha, Qatar",
        "singapore": "Singapore",
        "cathay": "Hong Kong",
        "ryanair": "Dublin, Ireland",
        "easyjet": "London, United Kingdom",
        "jetblue": "New York, United States",
        "southwest": "Dallas, United States",
        "american airlines": "Fort Worth, United States",
        "delta airlines": "Atlanta, United States",
        "fedex": "Memphis, United States",
        "ups airlines": "Louisville, United States",
        "boeing": "Arlington, United States",
        "airbus": "Toulouse, France",
        "jost group": "Luxembourg",
        "luxaviation": "Luxembourg",
    }

    US_STATES = {
        "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
        "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
        "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
        "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
        "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
        "alabama", "alaska", "arizona", "arkansas", "california", "colorado",
        "connecticut", "delaware", "florida", "georgia", "hawaii", "idaho",
        "illinois", "indiana", "iowa", "kansas", "kentucky", "louisiana",
        "maine", "maryland", "massachusetts", "michigan", "minnesota",
        "mississippi", "missouri", "montana", "nebraska", "nevada",
        "new hampshire", "new jersey", "new mexico", "new york",
        "north carolina", "north dakota", "ohio", "oklahoma", "oregon",
        "pennsylvania", "rhode island", "south carolina", "south dakota",
        "tennessee", "texas", "utah", "vermont", "virginia", "washington",
        "west virginia", "wisconsin", "wyoming"
    }

    # Label prefixes to strip
    LABEL_PREFIXES_RE = re.compile(
        r"^(?:location|standort|lieu|ubicaci[oó]n|localisation|lokalizacja|lokalita"
        r"|place|site|city|town|country|region|area|base|work location|job location|loc|pos)"
        r"\s*[:\-–]?\s*",
        re.IGNORECASE,
    )

    # Regex for international postal prefixes (e.g., H-1095)
    POSTAL_PREFIX_RE = re.compile(r"^([A-Z]{1,3})-\d{3,6}(?:\s+(.+))?$", re.IGNORECASE)

    # Suffixes added by LinkedIn/job boards that obscure the real city name
    AREA_SUFFIX_RE = re.compile(
        r"\s+(area|region|metropolitan area|metro area|greater|district|province|prefecture|county)\s*$",
        re.IGNORECASE,
    )

    @classmethod
    def normalize_location(
        cls, location_text: str, hint_country: Optional[str] = None, company: Optional[str] = None
    ) -> str:
        """
        Main entry point for normalizing a location string.
        Returns: "City, Country" or just "Country".
        """
        # Step 0: Handle Unknown / Empty locations by mapping company name
        is_unknown = False
        if not location_text or not isinstance(location_text, str):
            is_unknown = True
        else:
            cleaned_check = cls.LABEL_PREFIXES_RE.sub("", location_text).strip()
            if not cleaned_check or cleaned_check.lower() in ("unknown", "n/a", "none", "remote/unknown"):
                is_unknown = True

        if is_unknown:
            if company and isinstance(company, str):
                comp_lower = company.lower()
                for comp_key, fallback_loc in cls.COMPANY_TO_LOCATION.items():
                    if comp_key in comp_lower:
                        return fallback_loc
            return "Unknown"

        # Step 1: Strip labels and clean whitespace
        cleaned = cls.LABEL_PREFIXES_RE.sub("", location_text).strip()
        cleaned = re.sub(r"\s+", " ", cleaned)
        # Strip trailing punctuation and underscores (e.g., ;, ., ,, _)
        cleaned = cleaned.rstrip(";.,:_ ")
        if not cleaned:
            return "Unknown"

        # Step 1b: Strip area/region suffixes
        if "," not in cleaned:
            cleaned_no_area = cls.AREA_SUFFIX_RE.sub("", cleaned).strip()
            if cleaned_no_area:
                cleaned = cleaned_no_area

        # Step 2: Handle special identifiers (Postal codes like LU2 9LY)
        identifier_lower = cleaned.lower().strip()
        if identifier_lower in cls.SPECIAL_IDENTIFIERS:
            return cls.SPECIAL_IDENTIFIERS[identifier_lower]

        # Step 3: Handle postal prefixes (H-1095)
        m = cls.POSTAL_PREFIX_RE.match(cleaned)
        if m:
            prefix = m.group(1).upper()
            trailing_city = (m.group(2) or "").strip()
            if prefix in cls.POSTAL_PREFIX_MAP:
                iso, country, default_city = cls.POSTAL_PREFIX_MAP[prefix]
                city = trailing_city if trailing_city else default_city
                return f"{city}, {country}"

        # Step 3b: Handle Workday style locations (US-TX-Irving)
        detected_country = None
        workday_match = re.match(r"^([A-Z]{2})-([A-Z]{2,3})-(.+)$", cleaned)
        if workday_match:
            country_code = workday_match.group(1).upper()
            if workday_match.group(1).upper() in cls.CC_TO_NAME:
                detected_country = cls.CC_TO_NAME[country_code]
            cleaned = f"{workday_match.group(3)}, {workday_match.group(2)}, {workday_match.group(1)}"

        # Step 4: Extract Country Code inside parentheses, e.g. Weiswampach (LU)
        if not detected_country:
            paren_match = re.search(r"\(([A-Za-z]{2})\)", cleaned)
            if paren_match:
                code = paren_match.group(1).upper()
                if code in cls.CC_TO_NAME:
                    detected_country = cls.CC_TO_NAME[code]

        # Split by common delimiters (comma, hyphen, slash, semicolon)
        normalized_delimiters = re.sub(r"\s+[-/|;]\s+", ", ", cleaned)
        parts = [p.strip() for p in normalized_delimiters.split(",")]

        # If no delimiters, check if any city from CITY_TO_COUNTRY is in the text
        if len(parts) == 1:
            text_lower = cleaned.lower()
            for city_key, country_val in cls.CITY_TO_COUNTRY.items():
                if re.search(r'\b' + re.escape(city_key) + r'\b', text_lower):
                    city_name = city_key.title()
                    return f"{city_name}, {country_val}"

        # Detect country (full country names as substrings first, sorted by length desc)
        if not detected_country:
            sorted_countries = sorted(cls.CC_TO_NAME.values(), key=len, reverse=True)
            text_lower = cleaned.lower()
            for country_name in sorted_countries:
                if re.search(r'\b' + re.escape(country_name.lower()) + r'\b', text_lower):
                    detected_country = country_name
                    break

        # Non-English country names (Deutschland, Česká republika, etc.)
        if not detected_country:
            sorted_alt_names = sorted(cls.ALT_COUNTRY_NAMES.keys(), key=len, reverse=True)
            text_lower = cleaned.lower()
            for alt_name in sorted_alt_names:
                if re.search(r'\b' + re.escape(alt_name) + r'\b', text_lower):
                    detected_country = cls.ALT_COUNTRY_NAMES[alt_name]
                    break

        # Check if any part is a known city in CITY_TO_COUNTRY (prevents country/state collisions like IL -> Israel)
        if not detected_country:
            for part in parts:
                part_lower = part.lower().strip()
                if part_lower in cls.CITY_TO_COUNTRY:
                    detected_country = cls.CITY_TO_COUNTRY[part_lower]
                    break

        # If still not found, check parts for exact codes or abbreviations (in reverse order to find country first)
        if not detected_country:
            for part in reversed(parts):
                part_clean = part.strip()
                if not part_clean:
                    continue
                part_upper = part_clean.upper()
                
                # Check 2-letter or 3-letter codes
                if part_upper in cls.CC_TO_NAME:
                    detected_country = cls.CC_TO_NAME[part_upper]
                    break
                elif re.search(r'\b(?:USA|U\.S\.|U\.S\.A\.)\b', part_upper):
                    detected_country = "United States"
                    break
                elif re.search(r'\b(?:UK|U\.K\.)\b', part_upper):
                    detected_country = "United Kingdom"
                    break

        # Check hint_country
        if not detected_country and hint_country:
            detected_country = hint_country

        # Check company-to-location mapping
        if not detected_country and company:
            comp_lower = company.lower()
            for comp_key, fallback_loc in cls.COMPANY_TO_LOCATION.items():
                if comp_key in comp_lower:
                    if "," in fallback_loc:
                        detected_country = fallback_loc.split(",")[-1].strip()
                    else:
                        detected_country = fallback_loc
                    break

        # Check CITY_TO_COUNTRY keys
        if not detected_country:
            for part in parts:
                part_lower = part.lower()
                if part_lower in cls.CITY_TO_COUNTRY:
                    detected_country = cls.CITY_TO_COUNTRY[part_lower]
                    break

        # Final fallback check for country: check if any part is a US state abbreviation/name
        if not detected_country:
            for part in parts:
                part_clean = part.strip()
                if part_clean.upper() in cls.US_STATES or part_clean.lower() in cls.US_STATES:
                    detected_country = "United States"
                    break

        # If we still don't have a country, check if any part is 2-letters in CC_TO_NAME
        if not detected_country:
            for p in parts:
                if len(p) == 2 and p.upper() in cls.CC_TO_NAME:
                    detected_country = cls.CC_TO_NAME[p.upper()]
                    break

        # If we still have no country, return the cleaned text
        if not detected_country:
            return cleaned

        # CRITICAL: Check if any known city for this country is mentioned in the parts
        for part in parts:
            part_lower = part.lower()
            for city_key, country_val in cls.CITY_TO_COUNTRY.items():
                if country_val.lower() == detected_country.lower():
                    if re.search(r'\b' + re.escape(city_key) + r'\b', part_lower):
                        return f"{city_key.title()}, {detected_country}"

        # Now identify valid city candidates from parts
        def is_valid_city(part_str: str) -> bool:
            part_str_clean = part_str.strip()
            if not part_str_clean:
                return False
            # Check if it matches detected_country
            if part_str_clean.lower() == detected_country.lower():
                return False
            # Check if it is a country code
            if part_str_clean.upper() in cls.CC_TO_NAME:
                return False
            # Check if it has street address or building indicator
            address_indicators = [
                "straße", "strasse", "street", "road", "way", "fokkerweg", "close", "ave", 
                "avenue", "st.", "suite", "building", "airport", "headquarters", "home based",
                "flughafen", "location"
            ]
            if any(ind in part_str_clean.lower() for ind in address_indicators):
                return False
            # Check if it has digits (mostly postal/street numbers)
            digit_count = sum(c.isdigit() for c in part_str_clean)
            if digit_count > 0:
                return False
            # Check if it is a US state name/abbreviation
            if part_str_clean.upper() in cls.US_STATES or part_str_clean.lower() in cls.US_STATES:
                return False
            # Check for generic region/area names
            region_indicators = ["lower", "baden", "region", "area", "province", "county", "metropolitan"]
            if part_str_clean.lower() in region_indicators:
                return False
            return True

        city_candidates = [p for p in parts if is_valid_city(p)]

        if city_candidates:
            # Pick first candidate
            city = city_candidates[0]
            # Strip trailing parentheses, e.g. "Weiswampach (LU)" -> "Weiswampach"
            city = re.sub(r"\s*\([^)]*\)", "", city).strip()
            # If city is same as country, return country only
            if city.lower() == detected_country.lower():
                return detected_country
            return f"{city}, {detected_country}"
        
        return detected_country

    @classmethod
    def extract_country_code(cls, normalized_location: str) -> Optional[str]:
        """Extra convenience to get ISO code from normalized string"""
        if not normalized_location:
            return None

        loc_lower = normalized_location.lower()
        # Look for country names in the string
        for cc, name in cls.CC_TO_NAME.items():
            if name.lower() in loc_lower:
                return cc

        return None
