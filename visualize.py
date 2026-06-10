"""Visualize GDELT outbreak early warning results."""

import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from config import FIGURE_DIR, DISEASES

plt.rcParams.update({
    "figure.dpi": 150,
    "font.size": 10,
    "axes.titlesize": 13,
    "figure.figsize": (14, 6),
})


def plot_disease_timeseries(ts, disease_id, alerts_dict=None, events=None):
    """Plot article count timeseries with anomaly alerts and ground truth events."""
    fig, axes = plt.subplots(3, 1, figsize=(16, 10), sharex=True,
                              gridspec_kw={"height_ratios": [3, 2, 2]})

    dates = ts.index
    counts = ts["article_count"]

    ax = axes[0]
    ax.fill_between(dates, counts, alpha=0.3, color="steelblue")
    ax.plot(dates, counts, color="steelblue", linewidth=0.8)

    colors = {"cusum": "red", "bayesian_change_point": "orange",
              "zscore_rolling": "green", "prophet_residual": "purple"}
    if alerts_dict:
        for method, result in alerts_dict.items():
            alert_dates = result["alerts"]
            if len(alert_dates) > 0:
                alert_values = [counts.loc[d] if d in counts.index else counts.max() * 0.9
                               for d in alert_dates]
                ax.scatter(alert_dates, alert_values, color=colors.get(method, "red"),
                          marker="v", s=60, zorder=5, label=f"{method} alert",
                          edgecolors="black", linewidths=0.5)

    if events:
        for ev in events:
            for key, label, color in [("who_report_date", "WHO", "darkred"),
                                       ("first_known_case", "1st Case", "orange")]:
                dt = ev.get(key)
                if dt and dt in dates:
                    ax.axvline(x=dt, color=color, linestyle="--", alpha=0.7, linewidth=1.5)
                    ax.text(dt, ax.get_ylim()[1] * 0.95, label, rotation=90,
                           verticalalignment="top", fontsize=7, color=color)

    ax.set_ylabel("Articles / day")
    ax.set_title(f"{DISEASES.get(disease_id, {}).get('who_don_query', disease_id)} — GDELT News Coverage")
    ax.legend(fontsize=7, loc="upper left")
    ax.grid(True, alpha=0.3)

    ax2 = axes[1]
    if "avg_tone" in ts.columns and ts["avg_tone"].notna().any():
        tone = ts["avg_tone"].rolling(7, min_periods=1).mean()
        ax2.plot(dates, tone, color="darkorange", linewidth=1)
        ax2.axhline(y=0, color="gray", linestyle="-", linewidth=0.5)
        ax2.fill_between(dates, 0, tone, where=(tone < 0), color="red", alpha=0.15)
        ax2.set_ylabel("Avg Tone (7d MA)")
        ax2.grid(True, alpha=0.3)
        ax2.set_ylim(-10, 10)

    ax3 = axes[2]
    if alerts_dict:
        for method, result in alerts_dict.items():
            scores = result["scores"]
            if len(scores) > 0:
                ax3.plot(dates, scores, linewidth=0.7, alpha=0.7,
                        color=colors.get(method, "gray"), label=method)
        ax3.set_ylabel("Anomaly Score")
        ax3.legend(fontsize=7, loc="upper left")
        ax3.grid(True, alpha=0.3)

    ax3.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax3.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    fig.autofmt_xdate()

    fig.tight_layout()
    path = os.path.join(FIGURE_DIR, f"timeseries_{disease_id}.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved {path}")
    return path


def plot_lead_time_distribution(df_validation):
    """Plot histogram of lead times."""
    detected = df_validation[df_validation["detected"] == True].copy()
    if len(detected) == 0:
        print("  No detected events to plot.")
        return None

    lead_days = detected["lead_days_vs_who"].dropna()

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.hist(lead_days, bins=20, color="steelblue", edgecolor="white", alpha=0.8)
    ax.axvline(x=lead_days.median(), color="red", linestyle="--", linewidth=2,
              label=f"Median: {lead_days.median():.0f} days")
    ax.axvline(x=0, color="gray", linestyle="-", linewidth=1, label="WHO report date")

    ax.set_xlabel("Lead Time (days before WHO report)")
    ax.set_ylabel("Number of Outbreak Events")
    ax.set_title(f"GDELT Early Warning Lead Time Distribution\n"
                 f"(n={len(detected)} events, {detected['detected'].sum()} detected before WHO)")
    ax.legend()
    ax.grid(True, alpha=0.3)

    path = os.path.join(FIGURE_DIR, "lead_time_distribution.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved {path}")
    return path


def plot_detection_by_disease(by_disease):
    """Bar chart of detection rates per disease."""
    df = by_disease.sort_values("detection_rate", ascending=True)

    fig, ax = plt.subplots(figsize=(12, 7))
    bars = ax.barh(range(len(df)), df["detection_rate"] * 100, color="steelblue", edgecolor="white")

    for i, (_, row) in enumerate(df.iterrows()):
        ax.text(row["detection_rate"] * 100 + 1, i,
                f"{row['detection_rate']:.0%} (n={int(row['total'])})",
                va="center", fontsize=9)

    ax.set_yticks(range(len(df)))
    ax.set_yticklabels(df["disease"])
    ax.set_xlabel("Detection Rate (%)")
    ax.set_title("GDELT Early Warning Detection Rate by Disease")
    ax.set_xlim(0, 105)
    ax.grid(True, alpha=0.3, axis="x")

    path = os.path.join(FIGURE_DIR, "detection_by_disease.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved {path}")
    return path


def plot_lead_time_by_disease(by_disease):
    """Box plot of lead times by disease."""
    df = by_disease.dropna(subset=["median_lead"]).sort_values("median_lead")

    diseases = df["disease"].tolist()
    lead_values = df["median_lead"].tolist()

    fig, ax = plt.subplots(figsize=(12, 7))
    colors = ["#2ecc71" if v > 0 else "#e74c3c" for v in lead_values]
    bars = ax.barh(range(len(diseases)), lead_values, color=colors, edgecolor="white")

    for i, v in enumerate(lead_values):
        ax.text(v + 0.5 if v >= 0 else v - 3, i, f"{v:.0f}d",
                va="center", fontsize=10, fontweight="bold")

    ax.set_yticks(range(len(diseases)))
    ax.set_yticklabels([DISEASES.get(d, {}).get("who_don_query", d) for d in diseases])
    ax.axvline(x=0, color="black", linewidth=1)
    ax.set_xlabel("Median Lead Time (days)")
    ax.set_title("Median GDELT Lead Time vs WHO Report by Disease")
    ax.grid(True, alpha=0.3, axis="x")

    path = os.path.join(FIGURE_DIR, "lead_time_by_disease.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved {path}")
    return path


def plot_summary_dashboard(summary, by_disease):
    """Create a summary dashboard figure."""
    fig = plt.figure(figsize=(16, 10))

    gs = fig.add_gridspec(2, 3, hspace=0.35, wspace=0.35)

    ax1 = fig.add_subplot(gs[0, 0])
    labels = ["Detected\nBefore WHO", "Not Detected\nor After WHO"]
    detected = summary["gdelt_detected_before_who"]
    not_detected = summary["total_events"] - detected
    ax1.pie([detected, not_detected], labels=labels, autopct="%1.1f%%",
            colors=["#2ecc71", "#e74c3c"], startangle=90,
            textprops={"fontsize": 11})
    ax1.set_title(f"Detection Rate\n(n={summary['total_events']})", fontsize=13, fontweight="bold")

    ax2 = fig.add_subplot(gs[0, 1])
    if summary["median_lead_days"] is not None:
        stats_text = (
            f"Median Lead: {summary['median_lead_days']:.0f} days\n"
            f"Mean Lead:   {summary['mean_lead_days']:.0f} days\n"
            f"Max Lead:    {summary['max_lead_days']:.0f} days\n"
            f"Min Lead:    {summary['min_lead_days']:.0f} days\n"
            f"\nBefore 1st Case: {summary['detected_before_first_case']}"
        )
        ax2.text(0.5, 0.5, stats_text, transform=ax2.transAxes,
                fontsize=12, ha="center", va="center",
                fontfamily="monospace",
                bbox=dict(boxstyle="round", facecolor="lightblue", alpha=0.3))
        ax2.set_title("Lead Time Statistics", fontsize=13, fontweight="bold")
    ax2.axis("off")

    ax3 = fig.add_subplot(gs[0, 2])
    df = by_disease.sort_values("detection_rate", ascending=True)
    ax3.barh(range(len(df)), df["detection_rate"] * 100, color="steelblue", edgecolor="white")
    ax3.set_yticks(range(len(df)))
    ax3.set_yticklabels(df["disease"], fontsize=8)
    ax3.set_xlabel("Detection Rate (%)")
    ax3.set_title("By Disease", fontsize=13, fontweight="bold")
    ax3.set_xlim(0, 105)
    ax3.grid(True, alpha=0.3, axis="x")

    ax4 = fig.add_subplot(gs[1, :2])
    if "mean_lead" in by_disease.columns:
        df2 = by_disease.dropna(subset=["mean_lead"]).sort_values("mean_lead")
        lead_vals = df2["mean_lead"].values
        colors_bar = ["#2ecc71" if v > 0 else "#e74c3c" for v in lead_vals]
        ax4.barh(range(len(df2)), lead_vals, color=colors_bar, edgecolor="white")
        ax4.set_yticks(range(len(df2)))
        labels_short = [DISEASES.get(d, {}).get("who_don_query", d)[:20] for d in df2["disease"].values]
        ax4.set_yticklabels(labels_short, fontsize=8)
        ax4.axvline(x=0, color="black", linewidth=1)
        ax4.set_xlabel("Mean Lead Time (days)")
        ax4.set_title("Mean Lead Time by Disease", fontsize=13, fontweight="bold")
        ax4.grid(True, alpha=0.3, axis="x")

    fig.suptitle("GDELT Global Outbreak Early Warning System — Validation Dashboard",
                 fontsize=16, fontweight="bold", y=1.01)
    path = os.path.join(FIGURE_DIR, "summary_dashboard.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved {path}")
    return path


def plot_event_gantt(df_validation, n_events=30):
    """Gantt-style chart showing GDELT alert timing vs WHO reports."""
    df = df_validation.dropna(subset=["gdelt_first_alert"]).head(n_events).copy()

    for col in ["who_report_date", "gdelt_first_alert", "first_known_case"]:
        df[col] = pd.to_datetime(df[col])

    df = df.sort_values("lead_days_vs_who", ascending=False)

    fig, ax = plt.subplots(figsize=(16, max(8, n_events * 0.35)))

    for i, (_, row) in enumerate(df.iterrows()):
        who_d = row["who_report_date"]
        gdelt_d = row["gdelt_first_alert"]
        first_d = row["first_known_case"]

        min_date = min(who_d, gdelt_d)
        if pd.notna(first_d):
            min_date = min(min_date, pd.Timestamp(first_d))
        max_date = max(who_d, gdelt_d)

        ax.barh(i, (who_d - gdelt_d).days, left=gdelt_d.toordinal(),
               color="#2ecc71" if row["detected"] else "#e74c3c",
               height=0.5, alpha=0.8, edgecolor="white")

        ax.scatter([who_d.toordinal()], [i], color="darkred", s=80, zorder=5, marker="D")
        if pd.notna(first_d):
            ax.scatter([pd.Timestamp(first_d).toordinal()], [i], color="orange", s=60, zorder=5, marker="s")

        label = f"{row['disease'][:15]} | {row['country']}"
        ax.text(min_date.toordinal() - 1, i, label, ha="right", va="center", fontsize=8)

    ax.set_yticks(range(len(df)))
    ax.set_yticklabels([])
    ax.set_xlabel("Date")
    ax.set_title("GDELT Alert Timing vs WHO Report (Top Events)")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
    fig.autofmt_xdate()

    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], marker="D", color="w", markerfacecolor="darkred",
              markersize=10, label="WHO Report"),
        Line2D([0], [0], marker="s", color="w", markerfacecolor="orange",
              markersize=10, label="First Known Case"),
        Line2D([0], [0], color="#2ecc71", lw=4, label="GDELT Alert → WHO (lead time)"),
    ]
    ax.legend(handles=legend_elements, loc="lower right", fontsize=9)

    path = os.path.join(FIGURE_DIR, "event_gantt.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved {path}")
    return path
