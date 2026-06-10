# global-news-based-outbreak-detection-across-diseases
code by Quantifying structural bias in global news-based outbreak detection across 18 diseases, 2015–2024

Primary data:
- 241,246 news articles from GDELT GKG v2
- 18 diseases
- 26 outbreak events in the primary analysis
- 30 outbreak events in sensitivity analyses

---

## Repository layout

```text
├── README.md
│
├── config.py
├── fetch_gdelt.py
├── fetch_who.py
├── download_real_data.py
├── main.py
├── anomaly.py
├── validate.py
├── visualize.py
├── synthetic_data.py
├── saturation_analysis.py
├── policy_analysis.py
├── create_supplementary_figures.py
│
├── data/
│   ├── gdelt/
│   │   ├── timeseries/
│   │   └── gkg_disease/
│   └── who/
│
├── outputs/
│   ├── validation_results.csv
│   ├── validation_summary.json
│   └── saturation/
│       ├── saturation_results.csv
│       └── saturation_summary.json
│
└── figures/
    ├── publication_v4/
    └── publication_policy/
```

---

## What each script does

### `download_real_data.py`
Downloads and caches the GDELT GKG files required for the disease windows defined in `config.py`, then builds disease-level time series.

### `main.py`
Runs the full outbreak early-warning workflow:
1. loads real GDELT time series if available
2. fills gaps with synthetic series when needed
3. runs anomaly detection
4. validates alerts against WHO ground truth
5. writes summary outputs and figures

### `saturation_analysis.py`
Runs the main manuscript analysis:
- Michaelis-Menten saturation model
- comparison to alternative functional forms
- detection efficiency score (DES)
- disease-category residual summaries
- figure generation

### `policy_analysis.py`
Runs the exploratory policy analysis:
- Investment Priority Index (IPI)
- feasibility classification
- policy dashboard figure

### `create_supplementary_figures.py`
Builds supplementary figures for the appendix.

---

## Data inputs

### Required public sources
- GDELT GKG v2: `http://data.gdeltproject.org/gdeltv2/`
- WHO Disease Outbreak News: `https://www.who.int/emergencies/disease-outbreak-news`
- RSF World Press Freedom Index: `https://rsf.org/en/index`
- World Bank WDI: `https://data.worldbank.org`

### Curated local inputs
- `data/who/validation_events.csv`
- `data/gdelt/timeseries/*.csv`

---

## Quick start

### Environment

```bash
Python >= 3.10
pip install pandas numpy scipy matplotlib scikit-learn requests
```

### Run the pipeline

```bash
python download_real_data.py
python main.py
python saturation_analysis.py
python policy_analysis.py
python create_supplementary_figures.py
```

### Notes
- If real GDELT time series are already present in `data/gdelt/timeseries/`, `main.py` will use them directly.
- If some disease windows are missing, the pipeline falls back to the synthetic series defined in `synthetic_data.py`.
- Random seeds are fixed where applicable.

---

## Expected outputs

- `outputs/validation_results.csv`
- `outputs/validation_summary.json`
- `outputs/saturation/saturation_results.csv`
- `outputs/saturation/saturation_summary.json`
- `figures/publication_v4/fig1_saturation_curve.png`
- `figures/publication_v4/fig2_predicted_vs_actual.png`
- `figures/publication_policy/fig1_policy_dashboard.png`

---

## Citation

If you use this repository, please cite the manuscript and the underlying data sources, especially GDELT and WHO.

---

## License

All public data sources remain under their respective licenses. Analysis code is provided for academic use.
