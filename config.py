"""Configuration for GDELT outbreak early warning system."""

import os

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(ROOT, "data")
OUTPUT_DIR = os.path.join(ROOT, "outputs")
FIGURE_DIR = os.path.join(ROOT, "figures")

for d in [DATA_DIR, OUTPUT_DIR, FIGURE_DIR]:
    os.makedirs(d, exist_ok=True)

DISEASES = {
    "covid19": {
        "keywords": [
            "covid", "coronavirus", "SARS-CoV-2", "2019-nCoV",
            "novel coronavirus", "pneumonia wuhan"
        ],
        "who_don_query": "COVID-19",
        "owid_id": "COVID-19",
    },
    "ebola": {
        "keywords": [
            "ebola", "ebola virus", "EVD", "ebola hemorrhagic fever",
            "filovirus"
        ],
        "who_don_query": "Ebola",
        "owid_id": None,
    },
    "cholera": {
        "keywords": [
            "cholera", "vibrio cholerae", "acute watery diarrhea outbreak"
        ],
        "who_don_query": "Cholera",
        "owid_id": None,
    },
    "marburg": {
        "keywords": [
            "marburg", "marburg virus", "MVD", "marburg hemorrhagic fever"
        ],
        "who_don_query": "Marburg",
        "owid_id": None,
    },
    "mpox": {
        "keywords": [
            "mpox", "monkeypox", "MPXV", "monkeypox virus"
        ],
        "who_don_query": "mpox",
        "owid_id": None,
    },
    "dengue": {
        "keywords": [
            "dengue", "dengue fever", "dengue virus", "DENV",
            "dengue hemorrhagic fever", "dengue outbreak"
        ],
        "who_don_query": "Dengue",
        "owid_id": None,
    },
    "yellow_fever": {
        "keywords": [
            "yellow fever", "yellow fever virus", "YFV"
        ],
        "who_don_query": "Yellow fever",
        "owid_id": None,
    },
    "lassa": {
        "keywords": [
            "lassa", "lassa fever", "lassa virus", "LASV"
        ],
        "who_don_query": "Lassa",
        "owid_id": None,
    },
    "measles": {
        "keywords": [
            "measles", "measles outbreak", "rubeola", "measles virus"
        ],
        "who_don_query": "Measles",
        "owid_id": None,
    },
    "zika": {
        "keywords": [
            "zika", "zika virus", "ZIKV", "zika fever"
        ],
        "who_don_query": "Zika",
        "owid_id": None,
    },
    "avian_influenza": {
        "keywords": [
            "avian influenza", "bird flu", "H5N1", "H7N9", "H5N6",
            "avian flu", "highly pathogenic avian influenza"
        ],
        "who_don_query": "avian influenza",
        "owid_id": None,
    },
    "nipah": {
        "keywords": [
            "nipah", "nipah virus", "NiV"
        ],
        "who_don_query": "Nipah",
        "owid_id": None,
    },
    "rift_valley": {
        "keywords": [
            "rift valley fever", "RVF", "rift valley fever virus"
        ],
        "who_don_query": "Rift Valley",
        "owid_id": None,
    },
    "mers": {
        "keywords": [
            "MERS", "MERS-CoV", "middle east respiratory syndrome"
        ],
        "who_don_query": "MERS",
        "owid_id": None,
    },
    "polio": {
        "keywords": [
            "polio", "poliovirus", "polio outbreak", "wild poliovirus",
            "cVDPV", "circulating vaccine-derived poliovirus"
        ],
        "who_don_query": "polio",
        "owid_id": None,
    },
    "plague": {
        "keywords": [
            "plague", "bubonic plague", "pneumonic plague",
            "yersinia pestis", "plague outbreak"
        ],
        "who_don_query": "Plague",
        "owid_id": None,
    },
    "anthrax": {
        "keywords": [
            "anthrax", "bacillus anthracis", "anthrax outbreak"
        ],
        "who_don_query": "Anthrax",
        "owid_id": None,
    },
    "influenza_pandemic": {
        "keywords": [
            "influenza pandemic", "pandemic flu", "swine flu", "H1N1",
            "novel influenza", "new flu virus"
        ],
        "who_don_query": "influenza",
        "owid_id": None,
    },
}

BASE_COUNTRIES = {
    "US": "United States", "GB": "United Kingdom", "CN": "China",
    "IN": "India", "BR": "Brazil", "RU": "Russia", "FR": "France",
    "DE": "Germany", "JP": "Japan", "NG": "Nigeria", "CD": "DR Congo",
    "ZA": "South Africa", "ID": "Indonesia", "PK": "Pakistan",
    "BD": "Bangladesh", "MX": "Mexico", "IT": "Italy", "ES": "Spain",
    "AU": "Australia", "CA": "Canada", "UG": "Uganda", "KE": "Kenya",
    "ET": "Ethiopia", "SD": "Sudan", "SS": "South Sudan", "GH": "Ghana",
    "AO": "Angola", "MZ": "Mozambique", "TZ": "Tanzania", "CM": "Cameroon",
    "CI": "Cote d'Ivoire", "SN": "Senegal", "ML": "Mali", "BF": "Burkina Faso",
    "LR": "Liberia", "SL": "Sierra Leone", "GN": "Guinea", "TG": "Togo",
    "BJ": "Benin", "NE": "Niger", "TD": "Chad", "CF": "Central African Republic",
    "CG": "Congo", "GA": "Gabon",
    "PH": "Philippines", "VN": "Vietnam", "TH": "Thailand", "MM": "Myanmar",
    "MY": "Malaysia", "SG": "Singapore", "KR": "South Korea", "KP": "North Korea",
    "TW": "Taiwan", "HK": "Hong Kong",
    "AR": "Argentina", "CL": "Chile", "CO": "Colombia", "PE": "Peru",
    "VE": "Venezuela", "EC": "Ecuador", "BO": "Bolivia", "PY": "Paraguay",
    "UY": "Uruguay", "CU": "Cuba", "HT": "Haiti", "DO": "Dominican Republic",
    "GT": "Guatemala", "HN": "Honduras", "SV": "El Salvador", "NI": "Nicaragua",
    "CR": "Costa Rica", "PA": "Panama",
    "EG": "Egypt", "SA": "Saudi Arabia", "AE": "UAE", "QA": "Qatar",
    "KW": "Kuwait", "OM": "Oman", "BH": "Bahrain", "IQ": "Iraq",
    "IR": "Iran", "SY": "Syria", "JO": "Jordan", "LB": "Lebanon",
    "YE": "Yemen", "IL": "Israel", "TR": "Turkey",
    "UA": "Ukraine", "PL": "Poland", "RO": "Romania", "CZ": "Czech Republic",
    "HU": "Hungary", "AT": "Austria", "CH": "Switzerland", "NL": "Netherlands",
    "BE": "Belgium", "PT": "Portugal", "GR": "Greece", "SE": "Sweden",
    "NO": "Norway", "DK": "Denmark", "FI": "Finland", "IE": "Ireland",
    "NZ": "New Zealand",
}

DISEASE_CATEGORIES = {
    "viral_hemorrhagic": ["ebola", "marburg", "lassa", "rift_valley", "yellow_fever"],
    "respiratory": ["covid19", "mers", "influenza_pandemic", "avian_influenza"],
    "waterborne": ["cholera"],
    "vectorborne": ["dengue", "zika", "plague"],
    "vaccine_preventable": ["measles", "polio"],
    "zoonotic": ["nipah", "anthrax", "avian_influenza"],
    "emerging": ["mpox", "covid19", "mers"],
}

GDELT_API = "https://api.gdeltproject.org/api/v2/doc/doc"
GDELT_GEO_API = "https://api.gdeltproject.org/api/v2/geo/geo"

WHO_DON_RSS = "https://www.who.int/feeds/entity/don/en/rss.xml"
WHO_DON_PAGE = "https://www.who.int/emergencies/disease-outbreak-news"

PROMED_URL = "https://promedmail.org"

ANOMALY_METHODS = ["cusum", "bayesian_change_point", "prophet_residual", "zscore_rolling"]

SIGNIFICANCE_LEVEL = 0.05
CUSUM_THRESHOLD = 5.0
ROLLING_WINDOW_DAYS = 60
MIN_ALERT_INTERVAL_DAYS = 7

REQUEST_DELAY = 1.0
GDELT_TIMEOUT = 60
GDELT_MAX_RECORDS = 250
