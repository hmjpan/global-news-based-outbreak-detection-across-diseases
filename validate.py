"""Lead-time validation: compare GDELT alerts with official WHO reports."""

import os
import json
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from config import DATA_DIR, OUTPUT_DIR, DISEASES


def calculate_lead_time(gdelt_first_alert, official_date):
    """Compute lead time in days. Positive = GDELT alert came before official report."""
    if gdelt_first_alert is None:
        return None
    return (official_date - gdelt_first_alert).days


def validate_outbreak(disease_id, country_code, ts, alerts_dict, event_info):
    """
    For a single outbreak event, compute whether GDELT gave advance warning.

    event_info: dict with keys 'who_report_date', 'first_known_case', 'event'
    """
    who_date = event_info["who_report_date"]
    if isinstance(who_date, str):
        who_date = datetime.strptime(who_date, "%Y-%m-%d")

    first_case = event_info.get("first_known_case")
    if isinstance(first_case, str):
        first_case = datetime.strptime(first_case, "%Y-%m-%d")
    elif first_case is None:
        first_case = who_date

    lookback_start = first_case - timedelta(days=60)
    lookback_end = who_date + timedelta(days=14)

    gdelt_first_alert = None
    alert_method = None

    for method, result in alerts_dict.items():
        alerts = result["alerts"]
        if len(alerts) == 0:
            continue

        in_window = alerts[(alerts >= lookback_start) & (alerts <= lookback_end)]
        if len(in_window) > 0:
            first = in_window.min()
            if gdelt_first_alert is None or first < gdelt_first_alert:
                gdelt_first_alert = first
                alert_method = method

    lead_days = calculate_lead_time(gdelt_first_alert, who_date)

    first_case_lead = None
    if gdelt_first_alert is not None and first_case is not None:
        first_case_lead = (first_case - gdelt_first_alert).days

    result = {
        "disease": disease_id,
        "disease_name": DISEASES.get(disease_id, {}).get("who_don_query", disease_id),
        "country": country_code,
        "event": event_info.get("event", ""),
        "who_report_date": who_date.strftime("%Y-%m-%d"),
        "first_known_case": first_case.strftime("%Y-%m-%d") if first_case else None,
        "gdelt_first_alert": gdelt_first_alert.strftime("%Y-%m-%d") if gdelt_first_alert else None,
        "alert_method": alert_method,
        "lead_days_vs_who": lead_days,
        "lead_days_vs_first_case": first_case_lead,
        "detected": gdelt_first_alert is not None and lead_days is not None and lead_days > 0,
        "detected_before_first_case": gdelt_first_alert is not None and first_case_lead is not None and first_case_lead > 0,
    }

    return result


def run_full_validation(all_ts_dict, all_alerts_dict, validation_events):
    """
    Run validation for all events against all available time series.
    """
    results = []

    for _, event in validation_events.iterrows():
        d_id = event["disease"]
        country = event["country"]

        ts = all_ts_dict.get(d_id)
        alerts = all_alerts_dict.get(d_id, {})

        if ts is None:
            print(f"  [SKIP] No time series for {d_id}")
            continue

        event_info = {
            "who_report_date": event["who_report_date"],
            "first_known_case": event.get("first_known_case"),
            "event": event.get("event", ""),
        }

        result = validate_outbreak(d_id, country, ts, alerts, event_info)
        results.append(result)

    df = pd.DataFrame(results)
    return df


def summarize_validation(df):
    """Generate summary statistics for validation results."""
    detected = df[df["detected"] == True]
    total = len(df)

    summary = {
        "total_events": total,
        "gdelt_detected_before_who": len(detected),
        "detection_rate": len(detected) / max(total, 1),
        "median_lead_days": detected["lead_days_vs_who"].median() if len(detected) > 0 else None,
        "mean_lead_days": detected["lead_days_vs_who"].mean() if len(detected) > 0 else None,
        "max_lead_days": detected["lead_days_vs_who"].max() if len(detected) > 0 else None,
        "min_lead_days": detected["lead_days_vs_who"].min() if len(detected) > 0 else None,
        "detected_before_first_case": len(detected[detected["detected_before_first_case"] == True]) if len(detected) > 0 else 0,
    }

    by_disease = df.groupby("disease").agg(
        total=("detected", "count"),
        detected=("detected", "sum"),
        median_lead=("lead_days_vs_who", "median"),
        mean_lead=("lead_days_vs_who", "mean"),
    ).reset_index()
    by_disease["detection_rate"] = by_disease["detected"] / by_disease["total"]

    return summary, by_disease, df


def save_validation_results(df, summary, by_disease):
    """Save validation results to disk."""
    csv_path = os.path.join(OUTPUT_DIR, "validation_results.csv")
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"\n[RESULTS] Saved to {csv_path}")

    summary_path = os.path.join(OUTPUT_DIR, "validation_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump({
            "summary": {k: (float(v) if isinstance(v, (np.floating, np.integer)) and not np.isnan(v) else
                           str(v) if isinstance(v, pd.Timestamp) else v)
                        for k, v in summary.items()},
            "by_disease": by_disease.to_dict(orient="records"),
        }, f, indent=2, ensure_ascii=False)
    print(f"[RESULTS] Summary saved to {summary_path}")

    print("\n" + "=" * 60)
    print("VALIDATION RESULTS")
    print("=" * 60)
    print(f"Total outbreak events tested: {summary['total_events']}")
    print(f"GDELT detected BEFORE WHO:  {summary['gdelt_detected_before_who']} ({summary['detection_rate']:.1%})")
    if summary["median_lead_days"] is not None:
        print(f"Median lead time:          {summary['median_lead_days']:.0f} days")
        print(f"Mean lead time:            {summary['mean_lead_days']:.0f} days")
        print(f"Range:                      {summary['min_lead_days']:.0f} to {summary['max_lead_days']:.0f} days")
        print(f"Detected before 1st case:   {summary['detected_before_first_case']} events")
    print("\nBy disease:")
    print(by_disease.to_string(index=False))
