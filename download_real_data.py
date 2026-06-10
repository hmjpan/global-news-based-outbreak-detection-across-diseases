"""
GDELT GKG Downloader — PowerShell WebClient for 30x faster downloads.
"""
import os, sys, io, zipfile, time, subprocess, argparse
from datetime import datetime, timedelta
from collections import defaultdict
import pandas as pd, numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import DATA_DIR

GKG_BASE = "http://data.gdeltproject.org/gdeltv2"
CACHE_DIR = os.path.join(DATA_DIR, "gdelt", "gkg_disease")
os.makedirs(CACHE_DIR, exist_ok=True)

WINDOWS = [
    ("covid19", "2019-11-01", "2020-05-31"),
    ("covid19", "2020-10-01", "2021-02-28"),
    ("ebola", "2018-06-01", "2018-10-31"),
    ("ebola", "2022-07-01", "2022-12-31"),
    ("cholera", "2022-08-01", "2023-01-31"),
    ("mpox", "2022-03-01", "2022-08-31"),
    ("mpox", "2023-09-01", "2024-08-31"),
    ("dengue", "2023-04-01", "2023-10-31"),
    ("dengue", "2023-11-01", "2024-05-31"),
    ("measles", "2018-10-01", "2019-03-31"),
    ("marburg", "2022-05-01", "2022-10-31"),
    ("marburg", "2023-01-01", "2023-05-31"),
    ("marburg", "2024-08-01", "2024-11-30"),
    ("zika", "2015-04-01", "2016-01-31"),
    ("yellow_fever", "2015-11-01", "2016-05-31"),
    ("yellow_fever", "2017-08-01", "2018-01-31"),
    ("plague", "2017-06-01", "2017-12-31"),
    ("mers", "2015-04-01", "2015-08-31"),
    ("nipah", "2018-03-01", "2018-08-31"),
    ("avian_influenza", "2024-02-01", "2024-07-31"),
    ("polio", "2019-01-01", "2019-09-30"),
    ("lassa", "2023-11-01", "2024-04-30"),
    ("anthrax", "2023-10-01", "2024-02-29"),
]

PATTERNS = {
    "covid19": ["COVID", "CORONAVIRUS", "SARS-COV", "2019-NCOV"],
    "ebola": ["EBOLA", "EVD"], "cholera": ["CHOLERA"], "dengue": ["DENGUE"],
    "zika": ["ZIKA"], "measles": ["MEASLES"], "yellow_fever": ["YELLOW_FEVER"],
    "marburg": ["MARBURG"], "mpox": ["MONKEYPOX", "MPOX", "MPXV"],
    "plague": ["PLAGUE"], "polio": ["POLIO"],
    "avian_influenza": ["H5N1", "H7N9", "AVIAN_INFLUENZA", "BIRD_FLU"],
    "mers": ["MERS", "MERS-COV"], "nipah": ["NIPAH"],
    "lassa": ["LASSA"], "anthrax": ["ANTHRAX"],
    "rift_valley": ["RIFT_VALLEY"], "influenza_pandemic": ["H1N1", "SWINE_FLU"],
}


def detect_disease(themes_text):
    upper = themes_text.upper()
    found = set()
    for d_id, pats in PATTERNS.items():
        for p in pats:
            if p in upper:
                found.add(d_id)
                break
    return found or None


def download_file(date_obj):
    """Download using PowerShell WebClient (30x faster than urllib)."""
    ts = date_obj.strftime("%Y%m%d") + "000000"
    fname = f"{ts}.gkg.csv.zip"
    path = os.path.join(CACHE_DIR, fname)
    if os.path.exists(path):
        with open(path, "rb") as f:
            return f.read(), 0
    url = f"{GKG_BASE}/{fname}"
    try:
        ps_cmd = (
            f'$wc=New-Object System.Net.WebClient;'
            f'$wc.Headers.Add("User-Agent","Mozilla/5.0");'
            f'try{{$wc.DownloadFile("{url}","{path}");Write-Host "OK"}}catch{{Write-Host "ERR:$($_.Exception.Response.StatusCode.value__)"}}'
        )
        r = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", ps_cmd],
            capture_output=True, text=True, timeout=120
        )
        out = r.stdout.strip()
        if out.startswith("ERR:404"):
            return None, 1
        if out.startswith("ERR:"):
            return None, 2
        if out == "OK" and os.path.exists(path):
            with open(path, "rb") as f:
                return f.read(), 0
        return None, 2
    except subprocess.TimeoutExpired:
        return None, 3
    except Exception:
        return None, 3


def process_file(data, counts, tones):
    if data is None:
        return 0
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            names = zf.namelist()
            if not names:
                return 0
            text = zf.read(names[0]).decode("utf-8", errors="ignore")
    except Exception:
        return 0

    n = 0
    for line in text.split("\n"):
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 16:
            continue
        themes = (parts[7] if len(parts) > 7 else "") + " " + (parts[8] if len(parts) > 8 else "")
        diseases = detect_disease(themes)
        if diseases is None:
            continue
        date_str = parts[1][:8] if len(parts) > 1 and len(parts[1]) >= 8 else ""
        if len(date_str) != 8:
            continue
        try:
            dk = datetime.strptime(date_str, "%Y%m%d").date()
        except ValueError:
            continue
        tone_s = parts[15].split(",")[0] if len(parts) > 15 else "0"
        try:
            tone = float(tone_s)
        except ValueError:
            tone = 0.0
        for d_id in diseases:
            counts[d_id][dk] += 1
            tones[d_id][dk].append(tone)
        n += 1
    return n


def main():
    print("Starting...", flush=True)
    all_dates = set()
    for _, s, e in WINDOWS:
        sd = datetime.strptime(s, "%Y-%m-%d")
        ed = datetime.strptime(e, "%Y-%m-%d")
        d = sd
        while d <= ed:
            all_dates.add(d.date())
            d += timedelta(days=1)

    all_dates = sorted(all_dates)

    cached = set()
    for fn in os.listdir(CACHE_DIR):
        if fn.endswith(".gkg.csv.zip") and len(fn) >= 13:
            try:
                cached.add(datetime.strptime(fn[:8], "%Y%m%d").date())
            except ValueError:
                pass

    todo = [d for d in all_dates if d not in cached]
    todo = sorted(todo, reverse=True)  # Start with recent files (faster CDN access)
    print(f"Total: {len(all_dates)}, Cached: {len(cached)}, To download: {len(todo)}", flush=True)

    counts = defaultdict(lambda: defaultdict(int))
    tones = defaultdict(lambda: defaultdict(list))

    t0 = time.time()
    downloaded = 0
    errors = 0
    articles = 0
    total = len(todo)

    print(f"Starting downloads...", flush=True)
    for i, day in enumerate(todo):
        dt = datetime(day.year, day.month, day.day)
        data, err = download_file(dt)
        if err:
            errors += 1
            if errors <= 5 or errors % 100 == 0:
                print(f"  [{i}/{total}] {day} HTTP{err} skip", flush=True)
            continue
        downloaded += 1
        n = process_file(data, counts, tones)
        articles += n

        if (i + 1) % 10 == 0 or n > 50:
            elapsed = time.time() - t0
            rate = (i + 1) / max(elapsed, 1) * 60
            eta = (total - i - 1) / max(rate, 0.01)
            print(f"  [{i+1}/{total}] {day} | +{n} art | {rate:.0f} d/min | ETA {eta:.0f} min", flush=True)

    # Process cached files too
    print(f"\nProcessing {len(cached)} cached files...", flush=True)
    for day in sorted(cached):
        dt = datetime(day.year, day.month, day.day)
        data, _ = download_file(dt)
        if data:
            process_file(data, counts, tones)

    # Build time series
    all_dates_full = sorted(set(all_dates) | cached)
    date_range = pd.date_range(all_dates_full[0], all_dates_full[-1], freq="D")
    ts_dir = os.path.join(DATA_DIR, "gdelt", "timeseries")
    os.makedirs(ts_dir, exist_ok=True)

    ts_dict = {}
    for d_id in PATTERNS:
        recs = []
        for dv in date_range:
            dk = dv.date()
            c = counts[d_id].get(dk, 0)
            tlist = tones[d_id].get(dk, [])
            at = sum(tlist) / len(tlist) if tlist else 0.0
            recs.append({"date": dv, "article_count": c, "avg_tone": at})
        df = pd.DataFrame(recs).set_index("date")
        if df["article_count"].sum() > 0:
            ts_dict[d_id] = df
            df.to_csv(os.path.join(ts_dir, f"{d_id}.csv"))
            print(f"  {d_id:20s}: {df['article_count'].sum():8.0f} articles, peak={df['article_count'].max():6.0f}")

    elapsed = time.time() - t0
    print(f"\nDone. {downloaded} files, {articles} articles, {errors} errors in {elapsed/60:.1f} min")
    return ts_dict


if __name__ == "__main__":
    main()
