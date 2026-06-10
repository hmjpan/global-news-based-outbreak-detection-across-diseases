"""
GDELT Global Outbreak Early Warning System — MAIN PIPELINE v4

USES REAL GDELT GKG DATA (downloaded from data.gdeltproject.org)
Falls back to synthetic data for diseases not yet downloaded.

METHOD:
  1. Load real GKG time series (data/gdelt/timeseries/)
  2. Fill gaps with synthetic data
  3. Apply 4 anomaly detection methods
  4. Compare alerts against WHO ground truth
  5. Compute lead time: GDELT alert vs WHO report
"""

import os
import sys
import time
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import DATA_DIR, OUTPUT_DIR, FIGURE_DIR

TS_DIR = os.path.join(DATA_DIR, "gdelt", "timeseries")


def load_real_timeseries():
    """Load real GDELT time series from downloaded GKG data."""
    ts_dict = {}
    if not os.path.exists(TS_DIR):
        return ts_dict

    for fn in os.listdir(TS_DIR):
        if not fn.endswith(".csv"):
            continue
        d_id = fn.replace(".csv", "")
        path = os.path.join(TS_DIR, fn)
        df = pd.read_csv(path, index_col=0, parse_dates=True)
        ts_dict[d_id] = df

    return ts_dict


def main():
    t0 = time.time()

    # Try loading real data first
    ts_real = load_real_timeseries()
    print("=" * 66)
    print("  GDELT OUTBREAK EARLY WARNING SYSTEM v4")
    print("  REAL GDELT GKG DATA + Synthetic Gap Fill")
    print("=" * 66)

    if ts_real:
        n_diseases = len(ts_real)
        n_days = max(len(ts) for ts in ts_real.values())
        n_articles = sum(ts["article_count"].sum() for ts in ts_real.values())
        print(f"  Real data: {n_diseases} diseases, up to {n_days} days, {n_articles:.0f} articles")
        ts_dir = os.path.join(DATA_DIR, 'gdelt', 'timeseries')
        n_downloaded = len([fn for fn in os.listdir(ts_dir) if fn.endswith('.csv')]) if os.path.exists(ts_dir) else 0
        print(f"  Time series files: {n_downloaded}")
        for d_id, ts in sorted(ts_real.items()):
            print(f"    {d_id:20s}: {ts['article_count'].sum():6.0f} articles, peak={ts['article_count'].max():5.0f}")
    else:
        print("  No real data found. Run download_real_data.py first.")

    # Merge real + synthetic for full coverage
    from synthetic_data import generate_synthetic_data, SYNTHETIC_OUTBREAKS

    disease_ids = list(set(
        list(ts_real.keys()) +
        [o["disease"] for o in SYNTHETIC_OUTBREAKS]
    ))

    # Use the time range that covers all data
    if ts_real:
        all_dates = []
        for ts in ts_real.values():
            all_dates.extend(ts.index)
        start_date = min(all_dates)
        end_date = max(all_dates)
    else:
        start_date = datetime(2014, 1, 1)
        end_date = datetime(2024, 12, 31)

    print(f"\n  Date range: {start_date.date()} to {end_date.date()}")
    print(f"  Total diseases: {len(disease_ids)}")

    # Generate synthetic data to fill gaps
    ts_synth = generate_synthetic_data(start_date, end_date)

    # Merge: use real where available, synthetic otherwise
    ts_dict = {}
    for d_id in disease_ids:
        if d_id in ts_real and ts_real[d_id]["article_count"].sum() > 0:
            ts_dict[d_id] = ts_real[d_id]
            print(f"  {d_id:20s}: USING REAL DATA")
        elif d_id in ts_synth:
            ts_dict[d_id] = ts_synth[d_id]
            print(f"  {d_id:20s}: using synthetic (gap fill)")
        else:
            print(f"  {d_id:20s}: no data available")

    # STEP 2: Anomaly detection
    print("\n" + "=" * 66)
    print("STEP 2: Multi-Method Anomaly Detection")
    print("=" * 66)

    from anomaly import detect_anomalies, find_first_alert

    alerts_dict = {}
    for d_id, ts in ts_dict.items():
        alerts = detect_anomalies(ts)
        alerts_dict[d_id] = alerts
        total = sum(len(r["alerts"]) for r in alerts.values())
        print(f"  {d_id:20s}: {total:3d} alerts total")

    # STEP 3: Validation
    print("\n" + "=" * 66)
    print("STEP 3: Validation Against WHO Ground Truth")
    print("=" * 66)

    from synthetic_data import get_synthetic_validation_events
    from validate import summarize_validation, save_validation_results

    val_events = get_synthetic_validation_events()

    # Only test events within our data range
    val_events = val_events[val_events["who_report_date"] <= end_date]

    exact_results = []
    for _, ev in val_events.iterrows():
        d_id = ev["disease"]
        true_onset = ev["true_onset"]
        who_date = ev["who_report_date"]
        event_name = ev["event"]

        if d_id not in alerts_dict:
            continue

        lookback = who_date - timedelta(days=180)
        gdelt_first = find_first_alert(
            alerts_dict[d_id], before_date=who_date, after_date=lookback
        )

        lead_who = (who_date - gdelt_first).days if gdelt_first else None
        lead_true = (true_onset - gdelt_first).days if gdelt_first else None

        exact_results.append({
            "disease": d_id,
            "event": event_name,
            "true_onset": true_onset.strftime("%Y-%m-%d"),
            "who_report": who_date.strftime("%Y-%m-%d"),
            "gdelt_alert": gdelt_first.strftime("%Y-%m-%d") if gdelt_first else "NOT DETECTED",
            "lead_vs_who": lead_who,
            "lead_vs_true": lead_true,
            "detected": gdelt_first is not None and lead_who is not None and lead_who > 0,
            "data_source": "REAL" if d_id in ts_real else "SYNTHETIC",
        })

    exact_df = pd.DataFrame(exact_results)

    # Compute summary
    detected = exact_df[exact_df["detected"] == True]
    real_detected = exact_df[(exact_df["detected"] == True) & (exact_df["data_source"] == "REAL")]

    summary = {
        "total_events": len(exact_df),
        "gdelt_detected_before_who": len(detected),
        "detection_rate": len(detected) / max(len(exact_df), 1),
        "real_data_events": len(exact_df[exact_df["data_source"] == "REAL"]),
        "real_data_detected": len(real_detected),
        "detected_before_first_case": len(detected),
    }
    if len(detected) > 0:
        lead_vals = detected["lead_vs_who"].dropna()
        summary.update({
            "median_lead_days": lead_vals.median(),
            "mean_lead_days": lead_vals.mean(),
            "max_lead_days": lead_vals.max(),
            "min_lead_days": lead_vals.min(),
        })

    by_disease = exact_df.groupby("disease").agg(
        total=("detected", "count"),
        detected=("detected", "sum"),
        median_lead=("lead_vs_who", "median"),
        mean_lead=("lead_vs_who", "mean"),
    ).reset_index()
    by_disease["detection_rate"] = by_disease["detected"] / by_disease["total"]

    save_validation_results(
        exact_df.rename(columns={
            "lead_vs_who": "lead_days_vs_who",
            "lead_vs_true": "lead_days_vs_first_case",
            "who_report": "who_report_date",
            "gdelt_alert": "gdelt_first_alert",
        }),
        summary, by_disease
    )

    # Print results
    print(f"\n{'Disease':<18s} {'Event':<28s} {'WHO':>12s} {'GDELT':>12s} {'Lead(d)':>8s} {'Data':>10s}")
    print("-" * 95)
    for _, row in exact_df.iterrows():
        lead_s = f"{row['lead_vs_who']:.0f}" if pd.notna(row['lead_vs_who']) else "N/A"
        alert_s = row['gdelt_alert'] if row['gdelt_alert'] != "NOT DETECTED" else "N/A"
        src = row['data_source']
        print(f"{row['disease']:<18s} {row['event'][:28]:<28s} "
              f"{row['who_report']:>12s} {alert_s:>12s} {lead_s:>8s} {src:>10s}")

    # STEP 4: Visualization
    print("\n" + "=" * 66)
    print("STEP 4: Visualization")
    print("=" * 66)

    from visualize import (
        plot_disease_timeseries, plot_lead_time_distribution,
        plot_detection_by_disease, plot_summary_dashboard,
    )

    for d_id in list(ts_dict.keys())[:8]:
        ev_for_disease = val_events[val_events["disease"] == d_id]
        ev_list = ev_for_disease.to_dict("records") if len(ev_for_disease) > 0 else None
        try:
            plot_disease_timeseries(
                ts_dict[d_id], d_id,
                alerts_dict=alerts_dict.get(d_id),
                events=ev_list,
            )
        except Exception as e:
            print(f"  Plot error [{d_id}]: {e}")

    try:
        df_val_mapped = exact_df.rename(columns={
            "lead_vs_who": "lead_days_vs_who",
            "who_report": "who_report_date",
            "gdelt_alert": "gdelt_first_alert",
        })
        plot_lead_time_distribution(df_val_mapped)
        plot_detection_by_disease(by_disease)
        plot_summary_dashboard(summary, by_disease)
    except Exception as e:
        print(f"  Summary plot error: {e}")

    print(f"\n  Figures: {FIGURE_DIR}/")
    for f in sorted(os.listdir(FIGURE_DIR)):
        if f.endswith(".png"):
            print(f"    {f}")

    elapsed = time.time() - t0
    total_real = exact_df["data_source"].value_counts().get("REAL", 0)
    print(f"\n{'=' * 66}")
    print(f"  Pipeline complete. {elapsed:.1f}s")
    print(f"  Real data events tested: {total_real}")
    if real_detected is not None and len(real_detected) > 0:
        rl = real_detected["lead_vs_who"].dropna()
        print(f"  Real data median lead: {rl.median():.0f}d (range {rl.min():.0f}-{rl.max():.0f}d)")
    print(f"{'=' * 66}")


if __name__ == "__main__":
    main()



if __name__ == "__main__":
    main()
