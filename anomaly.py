"""Anomaly detection methods for disease outbreak early warning signals."""

import numpy as np
import pandas as pd
from scipy import stats
from datetime import timedelta

from config import CUSUM_THRESHOLD, ROLLING_WINDOW_DAYS, MIN_ALERT_INTERVAL_DAYS


def cusum_detection(series, threshold=CUSUM_THRESHOLD, drift=0.5):
    """
    Poisson CUSUM for count data anomaly detection.
    Returns alert dates where CUSUM exceeds threshold.
    """
    if len(series) < 14:
        return pd.Series(dtype="datetime64[ns]"), pd.Series(dtype=float)

    values = series.values.astype(float)
    baseline = np.nanmean(values)
    if baseline < 0.1:
        baseline = 0.5

    cusum_pos = np.zeros(len(values))
    cusum_neg = np.zeros(len(values))

    k = drift * np.sqrt(baseline) if baseline > 0 else drift

    for i in range(1, len(values)):
        cusum_pos[i] = max(0, cusum_pos[i - 1] + values[i] - baseline - k)
        cusum_neg[i] = max(0, cusum_neg[i - 1] + baseline - k - values[i])

    cusum_max = np.maximum(cusum_pos, cusum_neg)
    cusum_series = pd.Series(cusum_max, index=series.index)
    alerts = series.index[cusum_max > threshold * np.std(cusum_max[cusum_max > 0]) if np.any(cusum_max > 0) else threshold]

    alerts = _thin_alerts(alerts)
    return alerts, cusum_series


def bayesian_change_point(series, hazard=1.0 / 30, min_run_length=7):
    """
    Bayesian online change point detection (simplified).
    Uses a running mean shift detection via t-test on sliding windows.
    """
    if len(series) < 14:
        return pd.Series(dtype="datetime64[ns]"), pd.Series(dtype=float)

    values = series.values.astype(float)
    probs = np.zeros(len(values))

    for i in range(min_run_length * 2, len(values)):
        before = values[max(0, i - min_run_length * 2):i - min_run_length]
        after = values[i - min_run_length:i]

        if len(before) >= 7 and len(after) >= 3:
            try:
                t_stat, p_val = stats.ttest_ind(after, before, equal_var=False)
                probs[i] = 1.0 - p_val if not np.isnan(p_val) else 0.0
            except Exception:
                probs[i] = 0.0

    prob_series = pd.Series(probs, index=series.index)
    threshold = np.percentile(probs[probs > 0], 98) if np.any(probs > 0) else 0.99
    alerts = series.index[probs > threshold]

    alerts = _thin_alerts(alerts)
    return alerts, prob_series


def zscore_rolling_detection(series, window=ROLLING_WINDOW_DAYS, n_std=3.5):
    """
    Rolling z-score anomaly detection.
    """
    if len(series) < window:
        return pd.Series(dtype="datetime64[ns]"), pd.Series(dtype=float)

    rolling_mean = series.rolling(window=window, min_periods=max(7, window // 2)).mean()
    rolling_std = series.rolling(window=window, min_periods=max(7, window // 2)).std()

    z_scores = ((series - rolling_mean) / rolling_std.replace(0, np.nan)).fillna(0)
    alerts = series.index[z_scores > n_std]
    alerts = _thin_alerts(alerts)
    return alerts, z_scores


def prophet_residual_detection(series, window=ROLLING_WINDOW_DAYS):
    """
    Simple trend-seasonal decomposition residual anomaly detection.
    Uses moving average + residual thresholding instead of Prophet (no dependency).
    """
    if len(series) < window * 2:
        return pd.Series(dtype="datetime64[ns]"), pd.Series(dtype=float)

    values = series.values.astype(float)
    trend = pd.Series(values, index=series.index).rolling(
        window=window, center=True, min_periods=window // 2
    ).mean()

    detrended = values - trend.values
    detrended_series = pd.Series(detrended, index=series.index)

    residuals = detrended_series.rolling(
        window=7, center=True, min_periods=3
    ).std()

    threshold = 3.0 * residuals.median() if residuals.median() > 0 else 3.0
    anomaly_score = detrended_series.abs() / residuals.replace(0, np.nan)
    anomaly_score = anomaly_score.fillna(0)

    alerts = series.index[anomaly_score > 3.0]
    alerts = _thin_alerts(alerts)
    return alerts, anomaly_score


def _thin_alerts(alerts, min_interval=MIN_ALERT_INTERVAL_DAYS):
    """Remove consecutive alerts that are too close together."""
    if len(alerts) < 2:
        return alerts

    sorted_alerts = sorted(alerts)
    thinned = [sorted_alerts[0]]

    for alert in sorted_alerts[1:]:
        if (alert - thinned[-1]).days >= min_interval:
            thinned.append(alert)

    return pd.DatetimeIndex(thinned)


def detect_anomalies(ts, methods=None):
    """
    Apply all anomaly detection methods to a time series.
    Returns dict of {method_name: (alert_dates, score_series)}.
    """
    if methods is None:
        methods = ["cusum", "bayesian_change_point", "zscore_rolling", "prophet_residual"]

    if ts is None or len(ts) == 0:
        return {}

    counts = ts["article_count"] if "article_count" in ts.columns else ts.iloc[:, 0]

    results = {}
    for method in methods:
        if method == "cusum":
            alerts, scores = cusum_detection(counts)
        elif method == "bayesian_change_point":
            alerts, scores = bayesian_change_point(counts)
        elif method == "zscore_rolling":
            alerts, scores = zscore_rolling_detection(counts)
        elif method == "prophet_residual":
            alerts, scores = prophet_residual_detection(counts)
        else:
            continue

        results[method] = {"alerts": alerts, "scores": scores}

    return results


def find_first_alert(alerts_dict, before_date=None, after_date=None):
    """
    Find the earliest alert date from any method within a time window.
    Constrain to [after_date, before_date] if specified.
    """
    all_alerts = []
    for method, result in alerts_dict.items():
        alert_dates = result["alerts"]
        if len(alert_dates) == 0:
            continue
        if before_date is not None:
            alert_dates = alert_dates[alert_dates <= before_date]
        if after_date is not None:
            alert_dates = alert_dates[alert_dates >= after_date]
        if len(alert_dates) > 0:
            all_alerts.append(alert_dates.min())

    if all_alerts:
        return min(all_alerts)
    return None


def compute_alert_signal_strength(alerts_dict, date):
    """How many methods generated an alert within +/- 3 days of this date?"""
    count = 0
    total = 0
    for method, result in alerts_dict.items():
        total += 1
        for alert in result["alerts"]:
            if abs((alert - date).days) <= 3:
                count += 1
                break
    return count / max(total, 1)
