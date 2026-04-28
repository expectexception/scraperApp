import re
from typing import Dict, Tuple, Optional, List

class LocationManager:
    """
    Centralized utility for normalizing and standardizing job locations.
    Handles country code conversion, city-to-country mapping, and postal code resolution.
    """

    # Map from 2-letter ISO country codes to full country names (Comprehensive)
    CC_TO_NAME = {
        'AF': 'Afghanistan', 'AX': 'Åland Islands', 'AL': 'Albania', 'DZ': 'Algeria', 'AS': 'American Samoa',
        'AD': 'Andorra', 'AO': 'Angola', 'AI': 'Anguilla', 'AQ': 'Antarctica', 'AG': 'Antigua and Barbuda',
        'AR': 'Argentina', 'AM': 'Armenia', 'AW': 'Aruba', 'AU': 'Australia', 'AT': 'Austria',
        'AZ': 'Azerbaijan', 'BS': 'Bahamas', 'BH': 'Bahrain', 'BD': 'Bangladesh', 'BB': 'Barbados',
        'BY': 'Belarus', 'BE': 'Belgium', 'BZ': 'Belize', 'BJ': 'Benin', 'BM': 'Bermuda',
        'BT': 'Bhutan', 'BO': 'Bolivia', 'BQ': 'Bonaire, Sint Eustatius and Saba', 'BA': 'Bosnia and Herzegovina',
        'BW': 'Botswana', 'BV': 'Bouvet Island', 'BR': 'Brazil', 'IO': 'British Indian Ocean Territory',
        'BN': 'Brunei Darussalam', 'BG': 'Bulgaria', 'BF': 'Burkina Faso', 'BI': 'Burundi', 'CV': 'Cabo Verde',
        'KH': 'Cambodia', 'CM': 'Cameroon', 'CA': 'Canada', 'KY': 'Cayman Islands', 'CF': 'Central African Republic',
        'TD': 'Chad', 'CL': 'Chile', 'CN': 'China', 'CX': 'Christmas Island', 'CC': 'Cocos (Keeling) Islands',
        'CO': 'Colombia', 'KM': 'Comoros', 'CG': 'Congo', 'CD': 'Congo (DR)', 'CK': 'Cook Islands',
        'CR': 'Costa Rica', 'CI': 'Côte d\'Ivoire', 'HR': 'Croatia', 'CU': 'Cuba', 'CW': 'Curaçao',
        'CY': 'Cyprus', 'CZ': 'Czech Republic', 'DK': 'Denmark', 'DJ': 'Djibouti', 'DM': 'Dominica',
        'DO': 'Dominican Republic', 'EC': 'Ecuador', 'EG': 'Egypt', 'SV': 'El Salvador', 'GQ': 'Equatorial Guinea',
        'ER': 'Eritrea', 'EE': 'Estonia', 'SZ': 'Eswatini', 'ET': 'Ethiopia', 'FK': 'Falkland Islands',
        'FO': 'Faroe Islands', 'FJ': 'Fiji', 'FI': 'Finland', 'FR': 'France', 'GF': 'French Guiana',
        'PF': 'French Polynesia', 'TF': 'French Southern Territories', 'GA': 'Gabon', 'GM': 'Gambia',
        'GE': 'Georgia', 'DE': 'Germany', 'GH': 'Ghana', 'GI': 'Gibraltar', 'GR': 'Greece',
        'GL': 'Greenland', 'GD': 'Grenada', 'GP': 'Guadeloupe', 'GU': 'Guam', 'GT': 'Guatemala',
        'GG': 'Guernsey', 'GN': 'Guinea', 'GW': 'Guinea-Bissau', 'GY': 'Guyana', 'HT': 'Haiti',
        'HM': 'Heard Island and McDonald Islands', 'VA': 'Holy See', 'HN': 'Honduras', 'HK': 'Hong Kong',
        'HU': 'Hungary', 'IS': 'Iceland', 'IN': 'India', 'ID': 'Indonesia', 'IR': 'Iran', 'IQ': 'Iraq',
        'IE': 'Ireland', 'IM': 'Isle of Man', 'IL': 'Israel', 'IT': 'Italy', 'JM': 'Jamaica', 'JP': 'Japan',
        'JE': 'Jersey', 'JO': 'Jordan', 'KZ': 'Kazakhstan', 'KE': 'Kenya', 'KI': 'Kiribati', 'KP': 'North Korea',
        'KR': 'South Korea', 'KW': 'Kuwait', 'KG': 'Kyrgyzstan', 'LA': 'Laos', 'LV': 'Latvia', 'LB': 'Lebanon',
        'LS': 'Lesotho', 'LR': 'Liberia', 'LY': 'Libya', 'LI': 'Liechtenstein', 'LT': 'Lithuania',
        'LU': 'Luxembourg', 'MO': 'Macao', 'MG': 'Madagascar', 'MW': 'Malawi', 'MY': 'Malaysia',
        'MV': 'Maldives', 'ML': 'Mali', 'MT': 'Malta', 'MH': 'Marshall Islands', 'MQ': 'Martinique',
        'MR': 'Mauritania', 'MU': 'Mauritius', 'YT': 'Mayotte', 'MX': 'Mexico', 'FM': 'Micronesia',
        'MD': 'Moldova', 'MC': 'Monaco', 'MN': 'Mongolia', 'ME': 'Montenegro', 'MS': 'Montserrat',
        'MA': 'Morocco', 'MZ': 'Mozambique', 'MM': 'Myanmar', 'NA': 'Namibia', 'NR': 'Nauru', 'NP': 'Nepal',
        'NL': 'Netherlands', 'NC': 'New Caledonia', 'NZ': 'New Zealand', 'NI': 'Nicaragua', 'NE': 'Niger',
        'NG': 'Nigeria', 'NU': 'Niue', 'NF': 'Norfolk Island', 'MP': 'Northern Mariana Islands',
        'NO': 'Norway', 'OM': 'Oman', 'PK': 'Pakistan', 'PW': 'Palau', 'PS': 'Palestine', 'PA': 'Panama',
        'PG': 'Papua New Guinea', 'PY': 'Paraguay', 'PE': 'Peru', 'PH': 'Philippines', 'PN': 'Pitcairn',
        'PL': 'Poland', 'PT': 'Portugal', 'PR': 'Puerto Rico', 'QA': 'Qatar', 'RE': 'Réunion',
        'RO': 'Romania', 'RU': 'Russian Federation', 'RW': 'Rwanda', 'BL': 'Saint Barthélemy',
        'SH': 'Saint Helena', 'KN': 'Saint Kitts and Nevis', 'LC': 'Saint Lucia', 'MF': 'Saint Martin',
        'PM': 'Saint Pierre and Miquelon', 'VC': 'Saint Vincent and the Grenadines', 'WS': 'Samoa',
        'SM': 'San Marino', 'ST': 'Sao Tome and Principe', 'SA': 'Saudi Arabia', 'SN': 'Senegal',
        'RS': 'Serbia', 'SC': 'Seychelles', 'SL': 'Sierra Leone', 'SG': 'Singapore', 'SX': 'Sint Maarten',
        'SK': 'Slovakia', 'SI': 'Slovenia', 'SB': 'Solomon Islands', 'SO': 'Somalia', 'ZA': 'South Africa',
        'GS': 'South Georgia and the South Sandwich Islands', 'SS': 'South Sudan', 'ES': 'Spain',
        'LK': 'Sri Lanka', 'SD': 'Sudan', 'SR': 'Suriname', 'SJ': 'Svalbard and Jan Mayen', 'SE': 'Sweden',
        'CH': 'Switzerland', 'SY': 'Syria', 'TW': 'Taiwan', 'TJ': 'Tajikistan', 'TZ': 'Tanzania',
        'TH': 'Thailand', 'TL': 'Timor-Leste', 'TG': 'Togo', 'TK': 'Tokelau', 'TO': 'Tonga',
        'TT': 'Trinidad and Tobago', 'TN': 'Tunisia', 'TR': 'Turkey', 'TM': 'Turkmenistan',
        'TC': 'Turks and Caicos Islands', 'TV': 'Tuvalu', 'UG': 'Uganda', 'UA': 'Ukraine',
        'AE': 'United Arab Emirates', 'GB': 'United Kingdom', 'US': 'United States', 'UM': 'US Minor Outlying Islands',
        'UY': 'Uruguay', 'UZ': 'Uzbekistan', 'VU': 'Vanuatu', 'VE': 'Venezuela', 'VN': 'Viet Nam',
        'VG': 'Virgin Islands (British)', 'VI': 'Virgin Islands (U.S.)', 'WF': 'Wallis and Futuna',
        'EH': 'Western Sahara', 'YE': 'Yemen', 'ZM': 'Zambia', 'ZW': 'Zimbabwe'
    }

    # International postal country-prefix → (ISO-2-code, country name, default major-city)
    POSTAL_PREFIX_MAP = {
        'H':  ('HU', 'Hungary',     'Budapest'),
        'A':  ('AT', 'Austria',     'Vienna'),
        'D':  ('DE', 'Germany',     'Frankfurt'),
        'F':  ('FR', 'France',      'Paris'),
        'I':  ('IT', 'Italy',       'Milan'),
        'E':  ('ES', 'Spain',       'Madrid'),
        'P':  ('PT', 'Portugal',    'Lisbon'),
        'B':  ('BE', 'Belgium',     'Brussels'),
        'NL': ('NL', 'Netherlands', 'Amsterdam'),
        'CH': ('CH', 'Switzerland', 'Zurich'),
        'PL': ('PL', 'Poland',      'Warsaw'),
        'CZ': ('CZ', 'Czech Republic', 'Prague'),
        'SK': ('SK', 'Slovakia',    'Bratislava'),
        'RO': ('RO', 'Romania',     'Bucharest'),
        'BG': ('BG', 'Bulgaria',    'Sofia'),
        'HR': ('HR', 'Croatia',     'Zagreb'),
        'SI': ('SI', 'Slovenia',    'Ljubljana'),
        'GR': ('GR', 'Greece',      'Athens'),
        'LT': ('LT', 'Lithuania',   'Vilnius'),
        'LV': ('LV', 'Latvia',      'Riga'),
        'EE': ('EE', 'Estonia',     'Tallinn'),
        'SE': ('SE', 'Sweden',      'Stockholm'),
        'NO': ('NO', 'Norway',      'Oslo'),
        'DK': ('DK', 'Denmark',     'Copenhagen'),
        'FI': ('FI', 'Finland',     'Helsinki'),
        'GB': ('GB', 'United Kingdom', 'London'),
        'IE': ('IE', 'Ireland',     'Dublin'),
        'HU': ('HU', 'Hungary',     'Budapest'),
    }

    # Common cities or airport codes to Country mappings (Dynamic Aviation Logic)
    HUB_TO_COUNTRY = {
        # Europe
        'CPH': 'Denmark', 'ARN': 'Sweden', 'OSL': 'Norway', 'HEL': 'Finland',
        'LHR': 'United Kingdom', 'LGW': 'United Kingdom', 'STN': 'United Kingdom', 'MAN': 'United Kingdom',
        'CDG': 'France', 'ORY': 'France', 'NCE': 'France', 'AMS': 'Netherlands',
        'FRA': 'Germany', 'MUC': 'Germany', 'BER': 'Germany', 'HAM': 'Germany', 'DUS': 'Germany',
        'ZRH': 'Switzerland', 'GVA': 'Switzerland', 'VIE': 'Austria', 'BRU': 'Belgium',
        'MAD': 'Spain', 'BCN': 'Spain', 'PMI': 'Spain', 'LIS': 'Portugal', 'OPO': 'Portugal',
        'FCO': 'Italy', 'MXP': 'Italy', 'VCE': 'Italy', 'ATH': 'Greece', 'WAW': 'Poland',
        'PRG': 'Czech Republic', 'BUD': 'Hungary', 'OTP': 'Romania', 'SJJ': 'Bosnia and Herzegovina',
        'BEG': 'Serbia', 'ZAG': 'Croatia', 'LJU': 'Slovenia', 'SKP': 'North Macedonia', 'TIA': 'Albania',
        'DUB': 'Ireland', 'ORK': 'Ireland', 'KEF': 'Iceland',
        
        # Asia & Middle East
        'DXB': 'United Arab Emirates', 'AUH': 'United Arab Emirates', 'DOH': 'Qatar',
        'SIN': 'Singapore', 'HKG': 'Hong Kong', 'NRT': 'Japan', 'HND': 'Japan', 'ICN': 'South Korea',
        'PEK': 'China', 'PVG': 'China', 'CAN': 'China', 'BKK': 'Thailand', 'DMK': 'Thailand',
        'SGN': 'Vietnam', 'HAN': 'Vietnam', 'KUL': 'Malaysia', 'CGK': 'Indonesia', 'DPS': 'Indonesia',
        'MNL': 'Philippines', 'DEL': 'India', 'BOM': 'India', 'BLR': 'India', 'MAA': 'India',
        'SYD': 'Australia', 'MEL': 'Australia', 'BNE': 'Australia', 'AKL': 'New Zealand',
        'IST': 'Turkey', 'SAW': 'Turkey', 'TLV': 'Israel', 'AMM': 'Jordan', 'BEY': 'Lebanon',
        
        # Americas
        'JFK': 'United States', 'LAX': 'United States', 'ORD': 'United States', 'DFW': 'United States',
        'ATL': 'United States', 'SFO': 'United States', 'MIA': 'United States', 'EWR': 'United States',
        'YUL': 'Canada', 'YYZ': 'Canada', 'YVR': 'Canada', 'YYC': 'Canada',
        'MEX': 'Mexico', 'CUN': 'Mexico', 'GRU': 'Brazil', 'GIG': 'Brazil', 'EZE': 'Argentina',
        'SCL': 'Chile', 'BOG': 'Colombia', 'LIM': 'Peru', 'PTY': 'Panama',
        'SSA': 'Brazil', 'BSB': 'Brazil', 'CNF': 'Brazil', 'FOR': 'Brazil', 'POA': 'Brazil', # dnata Brasil
        'ALG': 'Algeria', 'ORN': 'Algeria', 'CZL': 'Algeria', 'AAE': 'Algeria', # Emploitic
        
        # Africa
        'JNB': 'South Africa', 'CPT': 'South Africa', 'CAI': 'Egypt', 'ADD': 'Ethiopia',
        'NBO': 'Kenya', 'CMN': 'Morocco', 'LOS': 'Nigeria',
    }

    CITY_TO_COUNTRY = {
        'sønderborg': 'Denmark', 'billund': 'Denmark', 'aarhus': 'Denmark',
        'appleton': 'United States', 'herndon': 'United States', 'luton': 'United Kingdom',
        'frankfurt': 'Germany', 'munich': 'Germany', 'berlin': 'Germany', 'hamburg': 'Germany',
        'düsseldorf': 'Germany', 'dusseldorf': 'Germany', 'cologne': 'Germany', 'koln': 'Germany',
        'dubai': 'United Arab Emirates', 'abu dhabi': 'United Arab Emirates', 'sharjah': 'United Arab Emirates',
        'budapest': 'Hungary', 'warsaw': 'Poland', 'prague': 'Czech Republic',
        'bucharest': 'Romania', 'vienna': 'Austria', 'zurich': 'Switzerland', 'geneva': 'Switzerland',
        # France — extensive coverage for Airbus & aviation hubs
        'paris': 'France', 'nice': 'France', 'lyon': 'France',
        'toulouse': 'France', 'blagnac': 'France', 'colomiers': 'France',
        'bordeaux': 'France', 'marseille': 'France', 'nantes': 'France',
        'strasbourg': 'France', 'montpellier': 'France', 'lille': 'France',
        'rennes': 'France', 'grenoble': 'France', 'saint-nazaire': 'France',
        'saint nazaire': 'France', 'méaulte': 'France', 'meaulte': 'France',
        'elancourt': 'France', 'élancourt': 'France', 'velizy': 'France',
        'marignane': 'France', 'istres': 'France',
        'madrid': 'Spain', 'barcelona': 'Spain', 'malaga': 'Spain', 'seville': 'Spain',
        'bilbao': 'Spain', 'puerto real': 'Spain', 'getafe': 'Spain',
        'lisbon': 'Portugal', 'faro': 'Portugal', 'porto': 'Portugal',
        'rome': 'Italy', 'milan': 'Italy', 'venice': 'Italy', 'naples': 'Italy',
        'turin': 'Italy', 'pomigliano': 'Italy',
        'athens': 'Greece', 'thessaloniki': 'Greece',
        'amsterdam': 'Netherlands', 'rotterdam': 'Netherlands', 'eindhoven': 'Netherlands',
        'brussels': 'Belgium', 'antwerp': 'Belgium', 'liege': 'Belgium',
        'london': 'United Kingdom', 'manchester': 'United Kingdom', 'birmingham': 'United Kingdom',
        'bristol': 'United Kingdom', 'filton': 'United Kingdom', 'broughton': 'United Kingdom',
        'stevenage': 'United Kingdom', 'newport': 'United Kingdom',
        'dublin': 'Ireland', 'shannon': 'Ireland',
        'stockholm': 'Sweden', 'gothenburg': 'Sweden', 'malmo': 'Sweden',
        'oslo': 'Norway', 'bergen': 'Norway', 'stavanger': 'Norway',
        'helsinki': 'Finland', 'vantaa': 'Finland', 'tampere': 'Finland',
        'montreal': 'Canada', 'toronto': 'Canada', 'vancouver': 'Canada', 'calgary': 'Canada',
        'sao paulo': 'Brazil', 'rio de janeiro': 'Brazil', 'brasilia': 'Brazil', 'salvador': 'Brazil',
        'aracaju': 'Brazil', 'fortaleza': 'Brazil', 'belo horizonte': 'Brazil', 'porto alegre': 'Brazil',
        'algiers': 'Algeria', 'oran': 'Algeria', 'constantine': 'Algeria', 'annaba': 'Algeria',
        'blida': 'Algeria', 'setif': 'Algeria', 'alger': 'Algeria',
        'philadelphia': 'United States', 'phoenix': 'United States', 'chicago': 'United States',
        'houston': 'United States', 'san antonio': 'United States', 'san diego': 'United States',
        'dallas': 'United States', 'san jose': 'United States', 'austin': 'United States',
        'memphis': 'United States', 'indianapolis': 'United States', 'jacksonville': 'United States',
        'fort worth': 'United States', 'columbus': 'United States', 'charlotte': 'United States',
        'riyadh': 'Saudi Arabia', 'jeddah': 'Saudi Arabia', 'dammam': 'Saudi Arabia',
        'kuwait city': 'Kuwait', 'muscat': 'Oman', 'manama': 'Bahrain',
        'singapore': 'Singapore', 'kuala lumpur': 'Malaysia', 'jakarta': 'Indonesia',
        'bangkok': 'Thailand', 'manila': 'Philippines', 'ho chi minh': 'Vietnam', 'hanoi': 'Vietnam',
        'tokyo': 'Japan', 'osaka': 'Japan', 'seoul': 'South Korea', 'beijing': 'China', 'shanghai': 'China',
        'hong kong': 'Hong Kong', 'taipei': 'Taiwan',
        'johannesburg': 'South Africa', 'cape town': 'South Africa', 'cairo': 'Egypt',
        'addis ababa': 'Ethiopia', 'nairobi': 'Kenya', 'lagos': 'Nigeria', 'casablanca': 'Morocco',
    }

    # Map for specific postal codes reported by user
    SPECIAL_IDENTIFIERS = {
        'lu2 9ly': 'United Kingdom', # Luton Airport
    }

    # Label prefixes to strip
    LABEL_PREFIXES_RE = re.compile(
        r'^(?:location|standort|lieu|ubicaci[oó]n|localisation|lokalizacja|lokalita'          
        r'|place|site|city|town|country|region|area|base|work location|job location|loc|pos)'
        r'\s*[:\-–]?\s*',
        re.IGNORECASE
    )

    # Regex for international postal prefixes (e.g., H-1095)
    POSTAL_PREFIX_RE = re.compile(r'^([A-Z]{1,3})-\d{3,6}(?:\s+(.+))?$', re.IGNORECASE)

    # Suffixes added by LinkedIn/job boards that obscure the real city name
    AREA_SUFFIX_RE = re.compile(
        r'\s+(area|region|metropolitan area|metro area|greater|district|province|prefecture|county)\s*$',
        re.IGNORECASE
    )

    @classmethod
    def normalize_location(cls, location_text: str, hint_country: Optional[str] = None) -> str:
        """
        Main entry point for normalizing a location string.
        Returns: "City, Country" or just "Country".
        """
        if not location_text or not isinstance(location_text, str):
            return "Unknown"

        # Step 1: Strip labels and clean whitespace
        cleaned = cls.LABEL_PREFIXES_RE.sub('', location_text).strip()
        cleaned = re.sub(r'\s+', ' ', cleaned)
        # Strip trailing punctuation (e.g., ;, ., ,)
        cleaned = cleaned.rstrip(';.,: ')
        if not cleaned:
            return "Unknown"

        # Step 1b: Strip area/region suffixes added by job boards (e.g. "Toulouse Area" → "Toulouse")
        # Only strip from single-segment locations (no commas) to avoid stripping valid region names
        if ',' not in cleaned:
            cleaned_no_area = cls.AREA_SUFFIX_RE.sub('', cleaned).strip()
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
            trailing_city = (m.group(2) or '').strip()
            if prefix in cls.POSTAL_PREFIX_MAP:
                iso, country, default_city = cls.POSTAL_PREFIX_MAP[prefix]
                city = trailing_city if trailing_city else default_city
                return f"{city}, {country}"

        # Step 3b: Handle Workday style locations (US-TX-Irving)
        # ^([A-Z]{2})-([A-Z]{2,3})-(.+)$ -> \3, \2, \1
        workday_match = re.match(r'^([A-Z]{2})-([A-Z]{2,3})-(.+)$', cleaned)
        if workday_match:
            cleaned = f"{workday_match.group(3)}, {workday_match.group(2)}, {workday_match.group(1)}"

        # Step 4: Split by common delimiters (comma, hyphen, slash)
        # Normalize delimiters to comma for processing
        normalized_delimiters = re.sub(r'\s+[-/|]\s+', ', ', cleaned)
        parts = [p.strip() for p in normalized_delimiters.split(',')]
        
        # New: Check EACH part for hub codes, postal code or country indicators
        new_parts = []
        is_us = False
        us_states = {'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA', 'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD', 'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ', 'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC', 'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY'}

        for part in parts:
            part_clean = part.strip()
            if not part_clean: continue
            part_upper = part_clean.upper()
            
            # 1. Aviation Hub Match - Keep original part
            if len(part_clean) == 3 and part_upper in cls.HUB_TO_COUNTRY:
                new_parts.append(part_clean)
                continue

            # 2. Try postal prefix match - Keep original part
            m = cls.POSTAL_PREFIX_RE.match(part_clean)
            if m:
                new_parts.append(part_clean)
                continue
            
            # 3. ISO Country Code Match - Be careful with 2-letter codes
            if part_upper in cls.CC_TO_NAME:
                # If it's 2-letters, keep it, we'll resolve later in Step 6
                # This prevents 'Aracaju - SE' -> 'Aracaju - Sweden'
                new_parts.append(part_clean)
                if part_upper == 'US': is_us = True
                continue
            
            # 4. US State Match
            if part_upper in us_states:
                new_parts.append(part_clean)
                is_us = True
                continue

            # 5. Common Airport Abbreviations
            if part_upper in ['USA', 'U.S.', 'U.S.A']:
                new_parts.append('United States')
                is_us = True
                continue
            if part_upper in ['UK', 'U.K.']:
                new_parts.append('United Kingdom')
                continue

            new_parts.append(part_clean)
        
        parts = []
        for p in new_parts:
            if p.upper() == 'US' and is_us:
                continue
            parts.append(p)

        if is_us and 'United States' not in [p.strip() for p in parts]:
            parts.append('United States')

        # Step 5: Check city mapping for first part if country is unknown/missing
        if len(parts) == 1:
            city_lower = parts[0].lower()
            if city_lower in cls.CITY_TO_COUNTRY:
                return f"{parts[0]}, {cls.CITY_TO_COUNTRY[city_lower]}"
            # Also check if it IS a country name already
            for cc, name in cls.CC_TO_NAME.items():
                if city_lower == name.lower():
                    return name

        # Final assembly
        # Filter out duplicates (if city and country became same)
        seen_parts = set()
        final_parts = []
        for p in parts:
            p_clean = p.strip()
            if p_clean.lower() not in seen_parts:
                final_parts.append(p_clean)
                seen_parts.add(p_clean.lower())
        
        # Step 6: Ensure Country Presence
        # a. Try to resolve country from city or hub mapping first (High confidence)
        resolved_country = None
        for p in final_parts:
            p_lower = p.lower()
            if p_lower in cls.CITY_TO_COUNTRY:
                resolved_country = cls.CITY_TO_COUNTRY[p_lower]
                break
            p_upper = p.upper()
            if len(p) == 3 and p_upper in cls.HUB_TO_COUNTRY:
                resolved_country = cls.HUB_TO_COUNTRY[p_upper]
                break
        
        # b. Check if any recognized full country name is already in final_parts
        has_full_country = False
        country_names_lower = [name.lower() for name in cls.CC_TO_NAME.values()]
        for p in final_parts:
            if p.lower() in country_names_lower:
                has_full_country = True
                break
        
        # c. If no full country name, but we have a resolved_country, append it
        if not has_full_country:
            if resolved_country:
                if resolved_country.lower() not in seen_parts:
                    final_parts.append(resolved_country)
                    has_full_country = True
            elif hint_country:
                if hint_country.lower() not in seen_parts:
                    final_parts.append(hint_country)
                    has_full_country = True
        
        # d. Only if still no country, look for remaining 2-letter codes that might be countries
        if not has_full_country:
            for p in final_parts:
                if len(p) == 2 and p.upper() in cls.CC_TO_NAME:
                    # Final guard: SE is almost always Sweden unless we have a Brazil hint
                    if p.upper() == 'SE' and hint_country == 'Brazil':
                        continue
                    final_parts[final_parts.index(p)] = cls.CC_TO_NAME[p.upper()]
                    break
        
        return ", ".join(final_parts)

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
