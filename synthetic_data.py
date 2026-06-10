"""
Synthetic data generator for outbreak early warning system validation.

Generates realistic GDELT-like daily article count time series with:
  - Baseline news noise (Poisson process)
  - Seasonal patterns (disease-specific)
  - Outbreak signals (controlled injection with known true dates)
  - Tone shifts (sentiment changes during outbreaks)

This allows EXACT validation: we know the true outbreak start date,
so we can precisely measure detection delay and false positive rate.

For Nature submission: replace with real GDELT BigQuery data.
"""
import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from config import DATA_DIR, DISEASES

np.random.seed(42)


def generate_baseline_noise(n_days, base_rate=2.0, dispersion=1.5):
    """Generate baseline daily article counts (negative binomial noise)."""
    noise = np.random.negative_binomial(n=base_rate, p=1.0 / (1.0 + dispersion), size=n_days)
    return noise.astype(float)


def generate_seasonal_pattern(n_days, amplitude=3.0, period=365, phase=0):
    """Generate seasonal sinusoidal pattern."""
    t = np.arange(n_days)
    return amplitude * np.sin(2 * np.pi * (t + phase) / period)


def generate_outbreak_signal(n_days, onset_day, peak_day, peak_height, decay_rate=0.05):
    """
    Generate a realistic outbreak signal:
      - Slow ramp-up from onset_day to peak_day
      - Exponential decay after peak
    """
    t = np.arange(n_days)
    signal = np.zeros(n_days)

    # Ramp-up phase
    ramp_mask = (t >= onset_day) & (t <= peak_day)
    ramp_duration = max(peak_day - onset_day, 1)
    signal[ramp_mask] = peak_height * ((t[ramp_mask] - onset_day) / ramp_duration) ** 1.5

    # Decay phase
    decay_mask = t > peak_day
    days_after_peak = t[decay_mask] - peak_day
    signal[decay_mask] = peak_height * np.exp(-decay_rate * days_after_peak)

    return signal


def generate_tone_signal(n_days, onset_day, peak_day, tone_shift=-5.0, decay_rate=0.03):
    """
    Generate tone (sentiment) shift during outbreaks.
    Tone becomes more negative during outbreak, returns to baseline.
    """
    t = np.arange(n_days)
    tone = np.zeros(n_days)

    event_mask = t >= onset_day
    days_after = t[event_mask] - onset_day
    tone[event_mask] = tone_shift * np.exp(-decay_rate * days_after)

    return tone


# Known outbreak events with TRUE onset dates (earlier than WHO reports)
# These are the "injected" signals we will try to detect
SYNTHETIC_OUTBREAKS = [
    {"disease": "covid19", "country": "CN",
     "true_onset": datetime(2019, 12, 8),    # True first signal in news
     "peak": datetime(2020, 2, 15),           # Peak media coverage
     "who_report": datetime(2020, 1, 5),      # WHO DON publication
     "peak_articles": 800, "event": "COVID-19 Wuhan"},
    {"disease": "covid19", "country": "IT",
     "true_onset": datetime(2020, 2, 10),
     "peak": datetime(2020, 3, 20),
     "who_report": datetime(2020, 2, 21),
     "peak_articles": 500, "event": "COVID-19 Italy"},
    {"disease": "ebola", "country": "CD",
     "true_onset": datetime(2018, 7, 20),
     "peak": datetime(2018, 9, 1),
     "who_report": datetime(2018, 8, 1),
     "peak_articles": 300, "event": "Ebola DRC North Kivu"},
    {"disease": "ebola", "country": "UG",
     "true_onset": datetime(2022, 9, 5),
     "peak": datetime(2022, 10, 10),
     "who_report": datetime(2022, 9, 20),
     "peak_articles": 250, "event": "Ebola Uganda Sudan"},
    {"disease": "marburg", "country": "GQ",
     "true_onset": datetime(2023, 1, 20),
     "peak": datetime(2023, 2, 28),
     "who_report": datetime(2023, 2, 13),
     "peak_articles": 180, "event": "Marburg Equatorial Guinea"},
    {"disease": "marburg", "country": "RW",
     "true_onset": datetime(2024, 9, 15),
     "peak": datetime(2024, 10, 5),
     "who_report": datetime(2024, 9, 27),
     "peak_articles": 150, "event": "Marburg Rwanda"},
    {"disease": "mpox", "country": "GB",
     "true_onset": datetime(2022, 4, 25),
     "peak": datetime(2022, 5, 20),
     "who_report": datetime(2022, 5, 7),
     "peak_articles": 200, "event": "Mpox UK 2022"},
    {"disease": "mpox", "country": "CD",
     "true_onset": datetime(2023, 11, 1),
     "peak": datetime(2024, 1, 15),
     "who_report": datetime(2024, 8, 14),
     "peak_articles": 350, "event": "Mpox DRC 2024"},
    {"disease": "cholera", "country": "HT",
     "true_onset": datetime(2022, 9, 15),
     "peak": datetime(2022, 11, 1),
     "who_report": datetime(2022, 10, 2),
     "peak_articles": 120, "event": "Cholera Haiti"},
    {"disease": "cholera", "country": "MW",
     "true_onset": datetime(2022, 12, 1),
     "peak": datetime(2023, 2, 1),
     "who_report": datetime(2023, 2, 1),
     "peak_articles": 90, "event": "Cholera Malawi"},
    {"disease": "dengue", "country": "BR",
     "true_onset": datetime(2023, 11, 15),
     "peak": datetime(2024, 2, 15),
     "who_report": datetime(2024, 2, 7),
     "peak_articles": 160, "event": "Dengue Brazil 2024"},
    {"disease": "dengue", "country": "BD",
     "true_onset": datetime(2023, 6, 1),
     "peak": datetime(2023, 8, 15),
     "who_report": datetime(2023, 8, 11),
     "peak_articles": 140, "event": "Dengue Bangladesh 2023"},
    {"disease": "zika", "country": "BR",
     "true_onset": datetime(2015, 8, 1),
     "peak": datetime(2015, 11, 15),
     "who_report": datetime(2015, 11, 11),
     "peak_articles": 280, "event": "Zika Brazil 2015"},
    {"disease": "measles", "country": "PH",
     "true_onset": datetime(2018, 12, 15),
     "peak": datetime(2019, 2, 15),
     "who_report": datetime(2019, 2, 7),
     "peak_articles": 200, "event": "Measles Philippines 2019"},
    {"disease": "measles", "country": "WS",
     "true_onset": datetime(2019, 9, 1),
     "peak": datetime(2019, 11, 15),
     "who_report": datetime(2019, 11, 15),
     "peak_articles": 100, "event": "Measles Samoa 2019"},
    {"disease": "yellow_fever", "country": "NG",
     "true_onset": datetime(2017, 10, 1),
     "peak": datetime(2017, 12, 1),
     "who_report": datetime(2017, 12, 12),
     "peak_articles": 80, "event": "Yellow Fever Nigeria"},
    {"disease": "yellow_fever", "country": "AO",
     "true_onset": datetime(2015, 12, 15),
     "peak": datetime(2016, 3, 1),
     "who_report": datetime(2016, 2, 1),
     "peak_articles": 130, "event": "Yellow Fever Angola"},
    {"disease": "plague", "country": "MG",
     "true_onset": datetime(2017, 8, 10),
     "peak": datetime(2017, 10, 15),
     "who_report": datetime(2017, 10, 1),
     "peak_articles": 110, "event": "Plague Madagascar"},
    {"disease": "mers", "country": "KR",
     "true_onset": datetime(2015, 5, 8),
     "peak": datetime(2015, 6, 10),
     "who_report": datetime(2015, 5, 20),
     "peak_articles": 160, "event": "MERS South Korea"},
    {"disease": "mers", "country": "SA",
     "true_onset": datetime(2014, 3, 15),
     "peak": datetime(2014, 5, 1),
     "who_report": datetime(2014, 4, 20),
     "peak_articles": 120, "event": "MERS Saudi Arabia"},
    {"disease": "nipah", "country": "IN",
     "true_onset": datetime(2018, 5, 1),
     "peak": datetime(2018, 5, 28),
     "who_report": datetime(2018, 5, 20),
     "peak_articles": 90, "event": "Nipah Kerala"},
    {"disease": "anthrax", "country": "ZM",
     "true_onset": datetime(2023, 11, 1),
     "peak": datetime(2023, 12, 10),
     "who_report": datetime(2023, 12, 1),
     "peak_articles": 60, "event": "Anthrax Zambia"},
    {"disease": "lassa", "country": "NG",
     "true_onset": datetime(2024, 1, 1),
     "peak": datetime(2024, 2, 15),
     "who_report": datetime(2024, 2, 1),
     "peak_articles": 70, "event": "Lassa Nigeria 2024"},
    {"disease": "polio", "country": "PK",
     "true_onset": datetime(2019, 3, 1),
     "peak": datetime(2019, 6, 15),
     "who_report": datetime(2019, 6, 1),
     "peak_articles": 50, "event": "Polio Pakistan"},
    {"disease": "avian_influenza", "country": "CN",
     "true_onset": datetime(2013, 3, 1),
     "peak": datetime(2013, 4, 20),
     "who_report": datetime(2013, 3, 31),
     "peak_articles": 200, "event": "H7N9 China"},
    {"disease": "avian_influenza", "country": "US",
     "true_onset": datetime(2024, 3, 20),
     "peak": datetime(2024, 5, 1),
     "who_report": datetime(2024, 4, 1),
     "peak_articles": 180, "event": "H5N1 US Dairy"},
    {"disease": "influenza_pandemic", "country": "MX",
     "true_onset": datetime(2009, 3, 18),
     "peak": datetime(2009, 5, 1),
     "who_report": datetime(2009, 4, 24),
     "peak_articles": 600, "event": "H1N1 Swine Flu"},
    {"disease": "rift_valley", "country": "UG",
     "true_onset": datetime(2018, 5, 15),
     "peak": datetime(2018, 6, 20),
     "who_report": datetime(2018, 6, 1),
     "peak_articles": 40, "event": "Rift Valley Uganda"},
]


def generate_synthetic_data(start_date, end_date, outbreaks=None):
    """
    Generate synthetic daily article count + tone time series
    for all diseases, aggregating signals from individual outbreak events.
    """
    if outbreaks is None:
        outbreaks = SYNTHETIC_OUTBREAKS

    date_range = pd.date_range(start_date, end_date, freq="D")
    n_days = len(date_range)
    t0 = start_date

    # Per-disease aggregation
    disease_signals = {}
    disease_tones = {}

    for disease_id in set(o["disease"] for o in outbreaks):
        disease_signals[disease_id] = np.zeros(n_days)
        disease_tones[disease_id] = np.zeros(n_days)

    # Add baseline noise for all diseases
    for disease_id in disease_signals:
        disease_signals[disease_id] += generate_baseline_noise(n_days, base_rate=2.0)

    # Add outbreak signals
    for ob in outbreaks:
        d_id = ob["disease"]
        onset_day = (ob["true_onset"] - t0).days
        peak_day = (ob["peak"] - t0).days

        if onset_day < 0 or peak_day >= n_days:
            continue

        # Article count signal
        signal = generate_outbreak_signal(
            n_days, onset_day, peak_day,
            peak_height=ob["peak_articles"],
            decay_rate=0.03
        )
        disease_signals[d_id] += signal

        # Tone signal
        tone = generate_tone_signal(
            n_days, onset_day, peak_day,
            tone_shift=-6.0, decay_rate=0.02
        )
        disease_tones[d_id] += tone

    # Build DataFrames
    ts_dict = {}
    for d_id in disease_signals:
        # Add small random jitter for realism
        counts = np.maximum(0, disease_signals[d_id] +
                           np.random.normal(0, max(1, disease_signals[d_id].std() * 0.1), n_days))

        # Average tone across outbreaks (baseline ~0, goes negative during outbreaks)
        tones = disease_tones[d_id] + np.random.normal(0, 0.5, n_days)

        df = pd.DataFrame({
            "article_count": counts,
            "avg_tone": tones,
        }, index=date_range)

        ts_dict[d_id] = df

    return ts_dict


def get_synthetic_validation_events():
    """
    Build validation events DataFrame with both:
      - true_onset (ground truth - what algorithm should detect)
      - who_report (official report date - for lead time calculation)
    """
    events = []
    for ob in SYNTHETIC_OUTBREAKS:
        events.append({
            "disease": ob["disease"],
            "country": ob["country"],
            "event": ob["event"],
            "who_report_date": ob["who_report"],
            "first_known_case": ob["true_onset"],
            "true_onset": ob["true_onset"],
            "peak_date": ob["peak"],
            "peak_articles": ob["peak_articles"],
        })

    df = pd.DataFrame(events)
    return df
