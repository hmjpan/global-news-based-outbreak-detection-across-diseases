"""Fetch WHO Disease Outbreak News (DON) as ground truth for validation."""

import os
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime

import pandas as pd
import requests

from config import WHO_DON_RSS, WHO_DON_PAGE, DATA_DIR, DISEASES, REQUEST_DELAY


def fetch_who_don_rss():
    """Fetch WHO DON items from the RSS feed."""
    print("\n[WHO] Fetching Disease Outbreak News RSS...")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    try:
        resp = requests.get(WHO_DON_RSS, headers=headers, timeout=60)
        resp.raise_for_status()
    except Exception as e:
        print(f"  [ERROR] Failed to fetch WHO DON RSS: {e}")
        return []

    root = ET.fromstring(resp.content)
    ns = {"atom": "http://www.w3.org/2005/Atom"}

    items = []
    for entry in root.findall("atom:entry", ns):
        title = entry.find("atom:title", ns)
        link = entry.find("atom:link", ns)
        published = entry.find("atom:published", ns)
        summary = entry.find("atom:summary", ns)

        title_text = title.text if title is not None else ""
        link_href = link.attrib.get("href", "") if link is not None else ""
        pub_text = published.text if published is not None else ""
        summary_text = summary.text if summary is not None else ""

        disease_match = _detect_disease(title_text, summary_text)

        items.append({
            "title": title_text,
            "url": link_href,
            "published": pub_text,
            "summary": summary_text,
            "disease_detected": disease_match,
            "source": "WHO_DON",
        })

    print(f"  Fetched {len(items)} WHO DON entries")
    return items


def _detect_disease(title, summary):
    text = (title + " " + summary).lower()

    for d_id, d_info in DISEASES.items():
        for kw in d_info["keywords"]:
            if kw.lower() in text:
                return d_id
    return "unknown"


MANUAL_VALIDATION_EVENTS = [
    {"disease": "covid19", "country": "CN", "who_report_date": "2020-01-05",
     "event": "COVID-19 Wuhan outbreak", "first_known_case": "2019-12-01"},
    {"disease": "covid19", "country": "IT", "who_report_date": "2020-02-21",
     "event": "COVID-19 Italy outbreak", "first_known_case": "2020-01-31"},
    {"disease": "covid19", "country": "US", "who_report_date": "2020-03-11",
     "event": "COVID-19 pandemic declared", "first_known_case": "2020-01-21"},
    {"disease": "ebola", "country": "CD", "who_report_date": "2018-08-01",
     "event": "Ebola North Kivu/Ituri", "first_known_case": "2018-07-28"},
    {"disease": "ebola", "country": "GN", "who_report_date": "2021-02-14",
     "event": "Ebola Guinea 2021 resurgence", "first_known_case": "2021-01-28"},
    {"disease": "ebola", "country": "UG", "who_report_date": "2022-09-20",
     "event": "Ebola Uganda Sudan strain", "first_known_case": "2022-09-11"},
    {"disease": "marburg", "country": "GQ", "who_report_date": "2023-02-13",
     "event": "Marburg Equatorial Guinea", "first_known_case": "2023-01-07"},
    {"disease": "marburg", "country": "TZ", "who_report_date": "2023-03-21",
     "event": "Marburg Tanzania", "first_known_case": "2023-03-16"},
    {"disease": "marburg", "country": "RW", "who_report_date": "2024-09-27",
     "event": "Marburg Rwanda", "first_known_case": "2024-09-20"},
    {"disease": "mpox", "country": "GB", "who_report_date": "2022-05-07",
     "event": "Mpox UK first 2022 case", "first_known_case": "2022-05-04"},
    {"disease": "mpox", "country": "CD", "who_report_date": "2024-08-14",
     "event": "Mpox PHEIC 2024", "first_known_case": "2023-09-01"},
    {"disease": "cholera", "country": "HT", "who_report_date": "2022-10-02",
     "event": "Cholera Haiti resurgence", "first_known_case": "2022-09-25"},
    {"disease": "cholera", "country": "MW", "who_report_date": "2023-02-01",
     "event": "Cholera Malawi outbreak", "first_known_case": "2022-03-01"},
    {"disease": "dengue", "country": "BR", "who_report_date": "2024-02-07",
     "event": "Dengue Brazil surge", "first_known_case": "2024-01-01"},
    {"disease": "dengue", "country": "BD", "who_report_date": "2023-08-11",
     "event": "Dengue Bangladesh record", "first_known_case": "2023-06-01"},
    {"disease": "yellow_fever", "country": "NG", "who_report_date": "2017-12-12",
     "event": "Yellow fever Nigeria", "first_known_case": "2017-09-01"},
    {"disease": "zika", "country": "BR", "who_report_date": "2015-11-11",
     "event": "Zika Brazil PHEIC", "first_known_case": "2015-04-01"},
    {"disease": "measles", "country": "PH", "who_report_date": "2019-02-07",
     "event": "Measles Philippines outbreak", "first_known_case": "2019-01-01"},
    {"disease": "measles", "country": "CD", "who_report_date": "2019-12-01",
     "event": "Measles DRC", "first_known_case": "2019-01-01"},
    {"disease": "polio", "country": "PK", "who_report_date": "2019-06-01",
     "event": "Polio Pakistan surge", "first_known_case": "2019-01-01"},
    {"disease": "avian_influenza", "country": "CN", "who_report_date": "2013-03-31",
     "event": "H7N9 China", "first_known_case": "2013-02-19"},
    {"disease": "avian_influenza", "country": "US", "who_report_date": "2024-04-01",
     "event": "H5N1 US dairy cattle", "first_known_case": "2024-03-25"},
    {"disease": "nipah", "country": "IN", "who_report_date": "2018-05-20",
     "event": "Nipah Kerala India", "first_known_case": "2018-05-02"},
    {"disease": "mers", "country": "SA", "who_report_date": "2014-04-20",
     "event": "MERS Saudi Arabia surge", "first_known_case": "2014-03-01"},
    {"disease": "mers", "country": "KR", "who_report_date": "2015-05-20",
     "event": "MERS South Korea nosocomial", "first_known_case": "2015-05-11"},
    {"disease": "plague", "country": "MG", "who_report_date": "2017-10-01",
     "event": "Plague Madagascar pneumonic", "first_known_case": "2017-08-23"},
    {"disease": "lassa", "country": "NG", "who_report_date": "2024-02-01",
     "event": "Lassa fever Nigeria 2024", "first_known_case": "2024-01-01"},
    {"disease": "rift_valley", "country": "UG", "who_report_date": "2018-06-01",
     "event": "Rift Valley fever Uganda", "first_known_case": "2018-05-01"},
    {"disease": "anthrax", "country": "ZM", "who_report_date": "2023-12-01",
     "event": "Anthrax Zambia", "first_known_case": "2023-11-01"},
    {"disease": "influenza_pandemic", "country": "MX", "who_report_date": "2009-04-24",
     "event": "H1N1 swine flu pandemic", "first_known_case": "2009-03-17"},
]

# Extended events from ProMED and other sources
PROMED_EVENTS = [
    {"disease": "ebola", "country": "CD", "who_report_date": "2014-03-23",
     "event": "Ebola West Africa (start in Guinea, spread to DRC)", "first_known_case": "2013-12-26"},
    {"disease": "ebola", "country": "LR", "who_report_date": "2014-03-30",
     "event": "Ebola Liberia", "first_known_case": "2014-03-01"},
    {"disease": "ebola", "country": "SL", "who_report_date": "2014-05-25",
     "event": "Ebola Sierra Leone", "first_known_case": "2014-05-01"},
    {"disease": "dengue", "country": "IN", "who_report_date": "2023-10-01",
     "event": "Dengue India surge 2023", "first_known_case": "2023-07-01"},
    {"disease": "dengue", "country": "PE", "who_report_date": "2023-06-01",
     "event": "Dengue Peru emergency", "first_known_case": "2023-03-01"},
    {"disease": "cholera", "country": "SY", "who_report_date": "2022-09-10",
     "event": "Cholera Syria", "first_known_case": "2022-08-25"},
    {"disease": "cholera", "country": "LB", "who_report_date": "2022-10-06",
     "event": "Cholera Lebanon", "first_known_case": "2022-10-01"},
    {"disease": "mpox", "country": "NG", "who_report_date": "2017-10-01",
     "event": "Mpox Nigeria resurgence", "first_known_case": "2017-09-01"},
    {"disease": "yellow_fever", "country": "AO", "who_report_date": "2016-02-01",
     "event": "Yellow fever Angola", "first_known_case": "2015-12-05"},
    {"disease": "measles", "country": "WS", "who_report_date": "2019-11-15",
     "event": "Measles Samoa epidemic", "first_known_case": "2019-09-01"},
    {"disease": "avian_influenza", "country": "VN", "who_report_date": "2024-03-01",
     "event": "H5N1 Vietnam human case", "first_known_case": "2024-02-01"},
    {"disease": "marburg", "country": "GH", "who_report_date": "2022-07-07",
     "event": "Marburg Ghana first", "first_known_case": "2022-06-26"},
]


def get_validation_events():
    all_events = MANUAL_VALIDATION_EVENTS + PROMED_EVENTS

    for ev in all_events:
        for key in ["who_report_date", "first_known_case"]:
            if isinstance(ev[key], str):
                ev[key] = datetime.strptime(ev[key], "%Y-%m-%d")

    df = pd.DataFrame(all_events)
    df = df.drop_duplicates(subset=["disease", "country", "who_report_date"])

    csv_path = os.path.join(DATA_DIR, "who", "validation_events.csv")
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"\n[VALIDATION] {len(df)} ground truth events saved to {csv_path}")
    return df


if __name__ == "__main__":
    items = fetch_who_don_rss()
    df_events = get_validation_events()
    print(f"\nDone. {len(items)} WHO RSS entries, {len(df_events)} validation events.")
