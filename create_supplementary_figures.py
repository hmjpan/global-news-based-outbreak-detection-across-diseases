import os
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

BASE = os.path.dirname(os.path.abspath(__file__))
OUTDIR = os.path.join(BASE, "supplement_figures")
os.makedirs(OUTDIR, exist_ok=True)

val = pd.read_csv(os.path.join(BASE, "outputs", "validation_results.csv"))
sat = pd.read_csv(os.path.join(BASE, "outputs", "saturation", "saturation_results.csv"))

sns.set_style("whitegrid")
plt.rcParams.update({"figure.dpi": 250, "font.size": 10})

# Figure S1: lead time by disease
fig, ax = plt.subplots(figsize=(10, 5))
order = val.groupby("disease")["lead_days_vs_who"].median().sort_values(ascending=False).index
sns.boxplot(data=val, x="disease", y="lead_days_vs_who", order=order, ax=ax, color="#8ecae6")
ax.set_title("Supplementary Figure S1. Lead time by disease")
ax.set_xlabel("Disease")
ax.set_ylabel("Lead days vs WHO")
ax.tick_params(axis='x', rotation=45)
fig.tight_layout()
fig.savefig(os.path.join(OUTDIR, "figS1_lead_time_by_disease.png"), bbox_inches="tight")
plt.close(fig)

# Figure S2: lead time distribution
fig, ax = plt.subplots(figsize=(8, 5))
sns.histplot(val.loc[val["detected"], "lead_days_vs_who"], bins=10, kde=True, ax=ax, color="#219ebc")
ax.set_title("Supplementary Figure S2. Distribution of detection lead times")
ax.set_xlabel("Lead days vs WHO")
ax.set_ylabel("Count")
fig.tight_layout()
fig.savefig(os.path.join(OUTDIR, "figS2_lead_time_distribution.png"), bbox_inches="tight")
plt.close(fig)

# Figure S3: saturation residuals vs deaths
fig, ax = plt.subplots(figsize=(8, 5))
sns.scatterplot(data=sat, x="deaths", y="residual", hue="category", ax=ax, s=80)
ax.set_xscale("log")
ax.axhline(0, color="black", lw=1, ls="--")
ax.set_title("Supplementary Figure S3. Residual coverage by outbreak size")
ax.set_xlabel("Deaths (log scale)")
ax.set_ylabel("Residual (actual - predicted)")
ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", title="Category")
fig.tight_layout()
fig.savefig(os.path.join(OUTDIR, "figS3_residuals_by_deaths.png"), bbox_inches="tight")
plt.close(fig)

# Figure S4: residuals by category
fig, ax = plt.subplots(figsize=(9, 5))
cat_order = sat.groupby("category")["residual"].mean().sort_values(ascending=False).index
sns.barplot(data=sat, x="category", y="residual", order=cat_order, estimator="mean", errorbar="sd", ax=ax, palette="viridis")
ax.axhline(0, color="black", lw=1, ls="--")
ax.set_title("Supplementary Figure S4. Mean residual by disease category")
ax.set_xlabel("Disease category")
ax.set_ylabel("Residual (articles)")
ax.tick_params(axis='x', rotation=30)
fig.tight_layout()
fig.savefig(os.path.join(OUTDIR, "figS4_residuals_by_category.png"), bbox_inches="tight")
plt.close(fig)

# Figure S5: DES distribution
fig, ax = plt.subplots(figsize=(8, 5))
sns.histplot(sat["residual_z"], bins=10, kde=True, ax=ax, color="#ffb703")
ax.set_title("Supplementary Figure S5. Distribution of standardized residuals")
ax.set_xlabel("Residual z-score")
ax.set_ylabel("Count")
fig.tight_layout()
fig.savefig(os.path.join(OUTDIR, "figS5_residual_z_distribution.png"), bbox_inches="tight")
plt.close(fig)

print(f"Saved supplementary figures to {OUTDIR}")