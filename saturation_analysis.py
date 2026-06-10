"""
Saturation Curve Analysis: Media Attention Ceiling

Key equation:  Coverage = Vmax × Deaths / (Km + Deaths)

Vmax = maximum possible daily news articles for this disease (ceiling)
Km   = deaths needed to reach half of Vmax (sensitivity threshold)

LOW Km + HIGH Vmax = "media hysteria" (few deaths trigger massive coverage)
HIGH Km + LOW Vmax = "media neglect" (many deaths, little coverage)

Residual = actual - predicted = TRUE over/under-reporting after
           controlling for the mechanical effect of outbreak size.
"""
import os, sys, json
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
from scipy import stats

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import OUTPUT_DIR, FIGURE_DIR

OUT_DIR = os.path.join(OUTPUT_DIR, "saturation")
FIG_DIR = os.path.join(FIGURE_DIR, "publication_v4")
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(FIG_DIR, exist_ok=True)

plt.rcParams.update({"figure.dpi": 250, "font.size": 10,
                     "axes.titlesize": 12, "axes.labelsize": 11})

# ── Data ─────────────────────────────────────────────────────
# (deaths, peak_articles, event_name, cfr, gdp, category, country)
DATA = [
    (1, 41, "Polio Pakistan 2019", 0.7, 1500, "vaccine_preventable", "PK"),
    (1, 34, "Mpox UK 2022", 0.0, 46000, "emerging", "GB"),
    (4, 102, "Anthrax Zambia 2023", 0.6, 1300, "zoonotic", "ZM"),
    (1, 24, "H5N1 US dairy 2024", 1.7, 76000, "zoonotic", "US"),
    (20, 109, "Zika Brazil 2015", 0.01, 8700, "vectorborne", "BR"),
    (3, 7, "Rift Valley Uganda 2018", 30.0, 950, "viral_hemorrhagic", "UG"),
    (39, 91, "MERS South Korea 2015", 21.0, 34000, "respiratory", "KR"),
    (77, 112, "Ebola Uganda 2022", 47.0, 950, "viral_hemorrhagic", "UG"),
    (12, 15, "Marburg Eq. Guinea 2023", 70.6, 8000, "viral_hemorrhagic", "GQ"),
    (15, 15, "Marburg Rwanda 2024", 22.7, 950, "viral_hemorrhagic", "RW"),
    (100, 81, "Cholera Syria 2022", 0.1, 2000, "waterborne", "SY"),
    (21, 16, "Nipah Kerala 2018", 91.3, 2000, "zoonotic", "IN"),
    (83, 42, "Measles Samoa 2019", 1.5, 4000, "vaccine_preventable", "WS"),
    (209, 84, "Plague Madagascar 2017", 8.7, 500, "vectorborne", "MG"),
    (4500, 1394, "COVID-19 Wuhan 2020", 8.2, 10500, "respiratory", "CN"),
    (300, 91, "MERS Saudi Arabia 2014", 37.5, 23000, "respiratory", "SA"),
    (100, 18, "Yellow fever Nigeria 2017", 2.8, 2200, "viral_hemorrhagic", "NG"),
    (500, 81, "Cholera Haiti 2022", 2.5, 1700, "waterborne", "HT"),
    (580, 42, "Measles Philippines 2019", 1.2, 3500, "vaccine_preventable", "PH"),
    (2287, 112, "Ebola DRC 2018", 65.9, 550, "viral_hemorrhagic", "CD"),
    (400, 18, "Yellow fever Angola 2016", 9.3, 2500, "viral_hemorrhagic", "AO"),
    (1800, 81, "Cholera Malawi 2022", 3.1, 650, "waterborne", "MW"),
    (200, 9, "Lassa Nigeria 2024", 18.2, 2200, "viral_hemorrhagic", "NG"),
    (2500, 112, "Ebola West Africa 2014", 65.8, 1000, "viral_hemorrhagic", "GN"),
    (35000, 1394, "COVID-19 Italy 2020", 14.6, 35000, "respiratory", "IT"),
    (616, 24, "H7N9 China 2013", 39.3, 7000, "respiratory", "CN"),
    (1200, 34, "Mpox DRC 2024", 4.8, 550, "emerging", "CD"),
    (1700, 43, "Dengue Bangladesh 2023", 0.5, 2600, "vectorborne", "BD"),
    (2000, 43, "Dengue Brazil 2024", 0.1, 9000, "vectorborne", "BR"),
    (284000, 34, "H1N1 Swine flu 2009", 0.5, 8000, "respiratory", "MX"),
]

def mm_func(x, Vmax, Km):
    return Vmax * x / (Km + x)


def fit_saturation_curve():
    print("=" * 60)
    print("MEDIA SATURATION CURVE ANALYSIS")
    print("  Coverage = Vmax × Deaths / (Km + Deaths)")
    print("=" * 60)

    deaths = np.array([d[0] for d in DATA], dtype=float)
    articles = np.array([d[1] for d in DATA], dtype=float)

    # Fit on log-scaled X to handle the wide range
    deaths_log = np.log10(deaths + 1)

    popt, pcov = curve_fit(
        mm_func, deaths, articles,
        p0=[200, 1000],
        bounds=([10, 1], [10000, 100000]),
        maxfev=10000
    )
    Vmax, Km = popt

    predicted = mm_func(deaths, Vmax, Km)
    residuals = articles - predicted
    residuals_z = (residuals - residuals.mean()) / residuals.std()

    ss_res = np.sum((articles - predicted)**2)
    ss_tot = np.sum((articles - np.mean(articles))**2)
    r2 = 1 - ss_res / ss_tot

    print(f"  Vmax = {Vmax:.0f}  (ceiling: max daily articles)")
    print(f"  Km   = {Km:.0f}  (deaths to reach 50% ceiling)")
    print(f"  R2   = {r2:.3f}  (outbreak size explains {r2*100:.0f}% of variance)")
    print(f"  Residual std = {residuals.std():.0f} articles")
    print()
    print(f"  Outbreak size explains {r2*100:.0f}% of media coverage variance.")
    print(f"  The remaining {100-r2*100:.0f}% is the 'attention bias' signal.")
    print()

    # Build results dataframe
    results = []
    for i, d in enumerate(DATA):
        results.append({
            "event": d[2],
            "deaths": d[0],
            "peak_articles": d[1],
            "cfr": d[3],
            "gdp": d[4],
            "category": d[5],
            "country": d[6],
            "predicted": predicted[i],
            "residual": residuals[i],
            "residual_z": residuals_z[i],
            "over_reported": residuals[i] > 0,
        })
    df = pd.DataFrame(results).sort_values("residual", ascending=False)

    # Top 5 over/under
    print("  Most OVER-reported (above saturation curve):")
    for _, r in df.head(5).iterrows():
        print(f"    {r['event'][:40]:<40s} deaths={r['deaths']:>7,.0f}  "
              f"actual={r['peak_articles']:>5.0f}  pred={r['predicted']:>5.0f}  Δ=+{r['residual']:.0f}")
    print("  Most UNDER-reported (below saturation curve):")
    for _, r in df.tail(5).iterrows():
        print(f"    {r['event'][:40]:<40s} deaths={r['deaths']:>7,.0f}  "
              f"actual={r['peak_articles']:>5.0f}  pred={r['predicted']:>5.0f}  Δ={r['residual']:.0f}")

    return df, Vmax, Km, r2, predicted


def analyze_residuals(df):
    """
    After controlling for outbreak size, what drives over/under reporting?

    residuals ~ CFR + log(GDP) + is_respiratory + is_high_income
    """
    print("\n" + "=" * 60)
    print("WHAT DRIVES OVER/UNDER-REPORTING?")
    print("  (After controlling for outbreak size)")
    print("=" * 60)

    df_a = df.copy()
    df_a["log_gdp"] = np.log10(df_a["gdp"])
    df_a["high_income"] = (df_a["gdp"] > 15000).astype(int)
    df_a["respiratory"] = (df_a["category"] == "respiratory").astype(int)
    df_a["viral_hemorrhagic"] = (df_a["category"] == "viral_hemorrhagic").astype(int)
    df_a["waterborne"] = (df_a["category"] == "waterborne").astype(int)

    predictors = ["cfr", "log_gdp", "respiratory", "high_income"]
    print(f"\n  Correlations with residual (over/under-reporting signal):")
    print(f"  {'Predictor':<25s} {'r':>8s} {'p':>8s}")
    print("  " + "-" * 45)

    corr_res = {}
    for var in predictors:
        valid = df_a[[var, "residual"]].dropna()
        r, p = stats.pearsonr(valid[var], valid["residual"])
        sig = "***" if p < 0.01 else ("**" if p < 0.05 else "")
        corr_res[var] = (r, p)
        print(f"  {var:<25s} {r:>8.3f} {p:>8.4f} {sig}")

    # Multiple regression
    from sklearn.linear_model import LinearRegression
    X = df_a[predictors].fillna(0).values
    y = df_a["residual"].values
    model = LinearRegression().fit(X, y)
    r2_res = model.score(X, y)
    coefs = dict(zip(predictors, model.coef_))

    print(f"\n  Multiple regression: residual ~ CFR + log(GDP) + respiratory + high_income")
    print(f"  R2 = {r2_res:.3f}")
    for k, v in coefs.items():
        print(f"    {k:<20s}: {v:+8.1f}")

    # By category
    cat_res = df_a.groupby("category")["residual"].agg(["mean", "std", "count"])
    print(f"\n  Mean residual by disease category:")
    for cat, row in cat_res.iterrows():
        direction = "OVER" if row["mean"] > 0 else "UNDER"
        print(f"    {cat:<25s}: {row['mean']:+7.1f} ({direction}-reported, n={int(row['count'])})")

    return df_a, corr_res, r2_res, coefs


def plot_saturation(df, Vmax, Km, r2, predicted, df_a, corr_res, r2_res, coefs):
    """Generate saturation curve figures."""

    # Figure 1: Saturation curve + residuals
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))

    # A: Saturation curve (log X)
    ax = axes[0, 0]
    deaths_all = np.array([d[0] for d in DATA])
    articles_all = np.array([d[1] for d in DATA])

    # Smooth curve
    x_smooth = np.logspace(0, 5.5, 200)
    y_smooth = mm_func(x_smooth, Vmax, Km)

    ax.plot(x_smooth, y_smooth, "k-", linewidth=2, alpha=0.6, label="Saturation curve")
    ax.fill_between(x_smooth, y_smooth * 0.5, y_smooth * 2.0,
                    color="gray", alpha=0.1, label="±2× band")

    # Points colored by residual
    colors = ["#e74c3c" if r > 0 else "#3498db" for r in df["residual"].values]
    sizes = np.abs(df["residual"].values) * 1.5 + 30
    ax.scatter(deaths_all, articles_all, c=colors, s=sizes, alpha=0.85,
              edgecolors="white", linewidth=0.3, zorder=5)

    # Annotate extremes
    for _, r in df.head(3).iterrows():
        ax.annotate(r["event"][:25], (r["deaths"], r["peak_articles"]),
                   fontsize=6, color="#e74c3c", fontweight="bold",
                   xytext=(10, 10), textcoords="offset points")
    for _, r in df.tail(3).iterrows():
        ax.annotate(r["event"][:25], (r["deaths"], r["peak_articles"]),
                   fontsize=6, color="#3498db",
                   xytext=(10, -10), textcoords="offset points")

    ax.set_xscale("log")
    ax.set_xlabel("Deaths")
    ax.set_ylabel("Peak Daily News Articles")
    ax.set_title(f"A  Media Saturation Curve\n"
                f"Coverage = {Vmax:.0f} × Deaths / ({Km:.0f} + Deaths), R² = {r2:.2f}")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    # B: Residuals ranked
    ax = axes[0, 1]
    df_sorted = df.sort_values("residual")
    colors2 = ["#e74c3c" if r > 0 else "#3498db" for r in df_sorted["residual"]]
    ax.barh(range(len(df_sorted)), df_sorted["residual"].values, color=colors2, edgecolor="white")
    ax.axvline(x=0, color="black", linewidth=1)
    ax.set_yticks(range(len(df_sorted)))
    labels = [f"{r['event'][:40]}" for _, r in df_sorted.iterrows()]
    ax.set_yticklabels(labels, fontsize=6)
    ax.set_xlabel("Residual (actual − predicted articles)")
    ax.set_title("B  Over/Under-Reporting After Controlling\nfor Outbreak Size")

    # Add Vmax and Km annotations
    ymax = ax.get_ylim()[1]
    for i, (_, r) in enumerate(df_sorted.iterrows()):
        if r["residual"] > 0:
            ax.text(r["residual"] + 2, i, f"+{r['residual']:.0f}", fontsize=6, va="center", color="#e74c3c")
        else:
            ax.text(r["residual"] - 10, i, f"{r['residual']:.0f}", fontsize=6, va="center", color="#3498db", ha="right")

    ax.grid(True, alpha=0.3, axis="x")

    # C: What drives residuals?
    ax = axes[1, 0]
    ax.scatter(df_a["cfr"], df_a["residual"], s=80, alpha=0.7,
              c=df_a["high_income"], cmap="RdYlGn", edgecolors="white", linewidth=0.3)

    # Label key outliers
    for _, r in df_a.iterrows():
        if abs(r["residual"]) > 200:
            ax.annotate(r["event"][:20], (r["cfr"], r["residual"]),
                       fontsize=6, alpha=0.8)

    ax.set_xlabel("Case Fatality Rate (%)")
    ax.set_ylabel("Residual (over/under reported)")
    ax.set_title("C  Does Lethality Explain Over-Reporting?")
    if corr_res:
        r_val = corr_res["cfr"][0]
        p_val = corr_res["cfr"][1]
        ax.text(0.95, 0.05, f"r = {r_val:.2f}, p = {p_val:.3f}",
               transform=ax.transAxes, ha="right", fontsize=9,
               bbox=dict(facecolor="white", alpha=0.8))
    ax.axhline(y=0, color="gray", linestyle="--", linewidth=0.5)
    ax.grid(True, alpha=0.3)

    # D: Category-level residuals
    ax = axes[1, 1]
    cat_stats = df_a.groupby("category")["residual"].agg(["mean", "std", "count"]).sort_values("mean", ascending=True)
    y_pos = np.arange(len(cat_stats))
    colors3 = ["#3498db" if m < 0 else "#e74c3c" for m in cat_stats["mean"]]
    ax.barh(y_pos, cat_stats["mean"], xerr=cat_stats["std"].fillna(0), color=colors3, edgecolor="white", alpha=0.9)
    ax.axvline(0, color="black", linewidth=1)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(cat_stats.index, fontsize=8)
    ax.set_xlabel("Mean residual (actual − predicted articles)")
    ax.set_title("D  Category-level residuals after size adjustment")
    for i, (cat, row) in enumerate(cat_stats.iterrows()):
        ax.text(row["mean"] + (5 if row["mean"] >= 0 else -5), i, f"n={int(row['count'])}",
                va="center", ha="left" if row["mean"] >= 0 else "right", fontsize=7)
    ax.grid(True, axis="x", alpha=0.3)
    ax.axvspan(0, ax.get_xlim()[1], color="#e74c3c", alpha=0.03)
    ax.axvspan(ax.get_xlim()[0], 0, color="#3498db", alpha=0.03)

    # Compact annotations inside panel for context
    ax.text(0.98, 0.02, f"Vmax={Vmax:.0f}  Km={Km:.0f}\nR²={r2:.2f}\nResidual model R²={r2_res:.2f}",
            transform=ax.transAxes, ha="right", va="bottom", fontsize=8,
            bbox=dict(boxstyle="round", facecolor="white", alpha=0.8, edgecolor="0.8"))

    fig.suptitle("When Does Death Become Invisible? Quantifying Media Attention Ceilings",
                fontsize=14, fontweight="bold", y=1.01)
    fig.tight_layout()
    path = os.path.join(FIG_DIR, "fig1_saturation_curve.png")
    fig.savefig(path, dpi=250, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved {path}")

    # Figure 2: Predicted vs Actual
    fig2, ax = plt.subplots(figsize=(8, 8))
    ax.scatter(df["predicted"], df["peak_articles"], s=100,
              c=df["residual"], cmap="RdBu_r", edgecolors="white", linewidth=0.3,
              vmin=-200, vmax=200)

    # Identity line
    max_val = max(df["predicted"].max(), df["peak_articles"].max()) * 1.1
    ax.plot([0, max_val], [0, max_val], "k--", linewidth=1, alpha=0.3)

    # Shade over/under regions
    ax.fill_between([0, max_val], [0, max_val], max_val, color="red", alpha=0.03)
    ax.fill_between([0, max_val], 0, [0, max_val], color="blue", alpha=0.03)

    # Annotate
    for _, r in df.iterrows():
        ax.annotate(r["event"][:25], (r["predicted"], r["peak_articles"]),
                   fontsize=6, alpha=0.7,
                   xytext=(3, 3), textcoords="offset points")

    ax.set_xlabel("Predicted Coverage (from death count alone)")
    ax.set_ylabel("Actual Peak Daily Articles")
    ax.set_title("Predicted vs Actual Media Coverage\n(above line = over-reported)")
    cbar = plt.colorbar(ax.collections[0], ax=ax)
    cbar.set_label("Residual (articles)")
    ax.grid(True, alpha=0.3)

    fig2.tight_layout()
    path = os.path.join(FIG_DIR, "fig2_predicted_vs_actual.png")
    fig2.savefig(path, dpi=250, bbox_inches="tight")
    plt.close(fig2)
    print(f"  Saved {path}")


def main():
    df, Vmax, Km, r2, predicted = fit_saturation_curve()
    df_a, corr_res, r2_res, coefs = analyze_residuals(df)
    plot_saturation(df, Vmax, Km, r2, predicted, df_a, corr_res, r2_res, coefs)

    # Save
    df.to_csv(os.path.join(OUT_DIR, "saturation_results.csv"), index=False)
    summary = {
        "Vmax": Vmax, "Km": Km, "r2_saturation": r2,
        "r2_residuals": r2_res,
        "over_reported_count": int(df["over_reported"].sum()),
        "under_reported_count": int((~df["over_reported"]).sum()),
    }
    with open(os.path.join(OUT_DIR, "saturation_summary.json"), "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\n{'=' * 60}")
    print(f"  Analysis complete.")
    print(f"  Figures: {FIG_DIR}/")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
