from __future__ import annotations

from typing import Any

import numpy as np


def evaluate_confidence(
    series: list[float], mape: float | None
) -> dict[str, Any]:
    values = np.asarray(series, dtype=float)
    months = len(values)
    mean = float(np.mean(values)) if months else 0
    volatility = float(np.std(values) / abs(mean)) if mean else float("inf")
    zero_ratio = float(np.mean(np.abs(values) < 1e-9)) if months else 1
    if months:
        q1, q3 = np.percentile(values, [25, 75])
        iqr = q3 - q1
        outlier_count = int(np.sum((values < q1 - 1.5 * iqr) | (values > q3 + 1.5 * iqr)))
    else:
        outlier_count = 0
    reasons = [
        f"Se evaluaron {months} meses de historia.",
        f"Volatilidad relativa (CV): {volatility:.2f}.",
    ]

    if months < 12 or (mape is not None and mape > 25) or volatility > 0.60 or zero_ratio > 0.15:
        level = "low"
        if months < 12:
            reasons.append("Hay menos de 12 meses disponibles.")
        if mape is not None and mape > 25:
            reasons.append(f"El MAPE de {mape:.2f}% supera 25%.")
        if volatility > 0.60:
            reasons.append("La serie presenta alta volatilidad.")
        if zero_ratio > 0.15:
            reasons.append("La serie contiene muchos meses en cero.")
    elif months > 24 and mape is not None and mape < 10 and volatility <= 0.35:
        level = "high"
        reasons.append("Cobertura extensa, error bajo y volatilidad controlada.")
    else:
        level = "medium"
        if mape is None:
            reasons.append("MAPE no calculable; la confianza se limita a media.")
        elif 10 <= mape <= 25:
            reasons.append(f"El MAPE de {mape:.2f}% está en rango medio.")
        elif volatility > 0.35:
            reasons.append("La volatilidad impide clasificar la confianza como alta.")
    return {
        "confidence": level,
        "confidence_reasons": reasons,
        "volatility_cv": round(volatility, 4) if np.isfinite(volatility) else None,
        "zero_months_pct": round(zero_ratio * 100, 2),
        "outlier_months": outlier_count,
    }


def forecast_bounds(
    forecast: float, *, mape: float | None, confidence: str
) -> tuple[float, float]:
    margin = (
        mape / 100
        if mape is not None
        else {"high": 0.10, "medium": 0.20, "low": 0.35}[confidence]
    )
    return max(0.0, forecast * (1 - margin)), max(0.0, forecast * (1 + margin))
