"""GDELT GKG file downloader and parser.

Downloads GKG CSV files directly (no API rate limits) from:
  http://data.gdeltproject.org/gdeltv2/

GKG v2 format: tab-separated, 27+ fields
  Field 1: DATE (YYYYMMDDHHMMSS)
  Field 7: Themes
  Field 8: V2Themes
  Field 9: Locations
  Field 15: V2Tone

Strategy: download 1 file per day (first 15-min file = *000000.gkg.csv.zip)
"""
import os
import zipfile
import io
import time
from datetime import datetime, timedelta
from collections import defaultdict

import requests
import pandas as pd

from config import DATA_DIR, DISEASES

GKG_BASE = "http://data.gdeltproject.org/gdeltv2"
GKG_CACHE = os.path.join(DATA_DIR, "gdelt", "gkg_cache")
os.makedirs(GKG_CACHE, exist_ok=True)

DISEASE_THEME_KEYWORDS = [
    "EBOLA", "COVID", "CORONAVIRUS", "CHOLERA", "DENGUE", "ZIKA",
    "MEASLES", "PLAGUE", "MARBURG", "MONKEYPOX", "MPOX", "POLIO",
    "H5N1", "H7N9", "MERS", "NIPAH", "LASSA", "ANTHRAX",
    "YELLOW_FEVER", "RIFT_VALLEY", "SARS", "PANDEMIC", "EPIDEMIC",
    "HEALTH_PANDEMIC", "TAX_DISEASE", "OUTBREAK",
]

DISEASE_PATTERN_MAP = {
    "ebola": ["EBOLA", "EVD"],
    "covid19": ["COVID", "CORONAVIRUS", "SARS-COV", "2019-NCOV", "TAX_DISEASE_COVID", "COVID-19"],
    "cholera": ["CHOLERA"],
    "dengue": ["DENGUE"],
    "zika": ["ZIKA"],
    "measles": ["MEASLES"],
    "yellow_fever": ["YELLOW_FEVER", "YELLOW FEVER"],
    "marburg": ["MARBURG"],
    "mpox": ["MONKEYPOX", "MPOX", "MPXV"],
    "plague": ["PLAGUE"],
    "polio": ["POLIO", "POLIOVIRUS"],
    "avian_influenza": ["H5N1", "H7N9", "AVIAN_INFLUENZA", "BIRD_FLU", "HPAI"],
    "mers": ["MERS", "MERS-COV"],
    "nipah": ["NIPAH"],
    "lassa": ["LASSA"],
    "anthrax": ["ANTHRAX"],
    "rift_valley": ["RIFT_VALLEY", "RVF"],
    "influenza_pandemic": ["SWINE_FLU", "H1N1"],
}


def _make_gkg_url(date_obj):
    """Generate GKG file URL for first 15-min window of a given day."""
    ts = date_obj.strftime("%Y%m%d") + "000000"
    return f"{GKG_BASE}/{ts}.gkg.csv.zip"


def download_gkg_file(date_obj):
    """Download a single daily GKG file. Returns raw bytes or None."""
    url = _make_gkg_url(date_obj)
    fname = f"{date_obj.strftime('%Y%m%d')}_000000.gkg.csv.zip"
    cache_path = os.path.join(GKG_CACHE, fname)

    if os.path.exists(cache_path):
        with open(cache_path, "rb") as f:
            return f.read()

    try:
        resp = requests.get(url, timeout=120, headers={
            "User-Agent": "GDELT-Research/1.0 (academic; batch download)"
        })
        if resp.status_code == 200:
            with open(cache_path, "wb") as f:
                f.write(resp.content)
            return resp.content
        else:
            print(f"  HTTP {resp.status_code} for {date_obj.date()}")
            return None
    except Exception as e:
        print(f"  Error downloading {date_obj.date()}: {e}")
        return None


def parse_gkg_content(raw_bytes):
    """Parse GKG zip content. Returns list of article dicts."""
    try:
        with zipfile.ZipFile(io.BytesIO(raw_bytes)) as zf:
            names = zf.namelist()
            if not names:
                return []
            content = zf.read(names[0])
            text = content.decode("utf-8", errors="ignore")
    except Exception as e:
        return []

    articles = []
    for line in text.split("\n"):
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 16:
            continue

        try:
            date_str = parts[1]
            if len(date_str) >= 8:
                article_date = datetime.strptime(date_str[:8], "%Y%m%d")
            else:
                continue

            themes = (parts[7] if len(parts) > 7 else "") + " " + \
                     (parts[8] if len(parts) > 8 else "")
            themes_upper = themes.upper()

            tone_str = parts[15] if len(parts) > 15 else "0"
            tone_parts = tone_str.split(",")
            tone = float(tone_parts[0]) if tone_parts and tone_parts[0] else 0.0

            locations_str = parts[9] if len(parts) > 9 else ""
            countries = set()
            for loc in locations_str.split(";"):
                lp = loc.split("#")
                if len(lp) >= 2 and len(lp[1]) == 2:
                    countries.add(lp[1])

            articles.append({
                "date": article_date,
                "themes": themes_upper,
                "tone": tone,
                "countries": countries,
            })
        except Exception:
            continue

    return articles


def detect_disease(themes_text):
    """Detect which diseases are mentioned in GKG themes."""
    detected = set()
    for d_id, patterns in DISEASE_PATTERN_MAP.items():
        for pat in patterns:
            if pat in themes_text:
                detected.add(d_id)
                break
    return detected if detected else None


def download_and_process_daily_files(start_date, end_date, disease_ids=None):
    """
    Download 1 GKG file per day, parse for disease themes,
    build daily time series per disease.
    """
    if disease_ids is None:
        disease_ids = list(DISEASES.keys())

    print(f"\n[GKG] Downloading {start_date.date()} to {end_date.date()}")

    date_range = pd.date_range(start_date, end_date, freq="D")

    # {(disease_id, date): (article_count, tone_sum, tone_count, countries_set)}
    daily_data = defaultdict(lambda: [0, 0.0, 0, set()])

    total_days = len(date_range)
    for i, d in enumerate(date_range):
        raw = download_gkg_file(d)
        if raw is None:
            if (i + 1) % 30 == 0:
                print(f"  [{i+1}/{total_days}] days processed...")
            continue

        articles = parse_gkg_content(raw)
        for art in articles:
            diseases = detect_disease(art["themes"])
            if diseases is None:
                continue
            date_key = art["date"].date()
            for d_id in diseases:
                if d_id in disease_ids:
                    entry = daily_data[(d_id, date_key)]
                    entry[0] += 1
                    entry[1] += art["tone"]
                    entry[2] += 1
                    entry[3].update(art["countries"])

        if (i + 1) % 30 == 0:
            print(f"  [{i+1}/{total_days}] days processed...")
        time.sleep(0.3)  # Small delay to be nice to the server

    print(f"  Done. Processing {len(daily_data)} disease-day entries...")

    # Build per-disease time series
    ts_dict = {}
    for d_id in disease_ids:
        records = []
        for date_val in date_range:
            date_key = date_val.date()
            entry = daily_data.get((d_id, date_key), [0, 0.0, 0, set()])
            avg_tone = entry[1] / entry[2] if entry[2] > 0 else 0.0
            records.append({
                "date": date_val,
                "article_count": entry[0],
                "avg_tone": avg_tone,
                "n_countries": len(entry[3]),
            })

        df = pd.DataFrame(records).set_index("date")
        ts_dict[d_id] = df
        total = df["article_count"].sum()
        print(f"  {d_id}: {total:.0f} articles, {total_days} days")

    return ts_dict
