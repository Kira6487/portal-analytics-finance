from __future__ import annotations

import math
from typing import Any

import numpy as np

from app.services.forecasting.models import available_models


def calculate_metrics(actual: list[float], predicted: list[float]) -> dict[str, float | None]:
    actual_array = np.asarray(actual, dtype=float)
    predicted_array = np.asarray(predicted, dtype=float)
    errors = actual_array - predicted_array
    mae = float(np.mean(np.abs(errors)))
    rmse = float(math.sqrt(np.mean(errors ** 2)))
    nonzero = np.abs(actual_array) > 1e-9
    mape = (
        float(np.mean(np.abs(errors[nonzero] / actual_array[nonzero])) * 100)
        if nonzero.any() else None
    )
    return {
        "mae": round(mae, 2),
        "mape": round(mape, 2) if mape is not None else None,
        "rmse": round(rmse, 2),
    }


def backtest_series(
    series: list[float], *, target: str, test_months: int = 6
) -> dict[str, Any]:
    if test_months < 1:
        raise ValueError("test_months debe ser mayor que cero.")
    if len(series) <= test_months:
        return {
            "target": target,
            "models": [],
            "best_model": None,
            "warnings": ["No hay suficientes meses para separar entrenamiento y prueba."],
        }
    train, actual = series[:-test_months], series[-test_months:]
    results = []
    for model in available_models():
        try:
            predicted = model.fit(train).predict(test_months)
            predicted = [max(0.0, float(value)) for value in predicted]
            results.append(
                {
                    "model": model.name,
                    **calculate_metrics(actual, predicted),
                    "status": "valid",
                    "predictions": [round(value, 2) for value in predicted],
                }
            )
        except Exception as exc:
            results.append(
                {"model": model.name, "status": "failed", "error": str(exc)}
            )

    valid = [item for item in results if item["status"] == "valid"]
    with_mape = [item for item in valid if item["mape"] is not None]
    if with_mape:
        winner = min(with_mape, key=lambda item: (item["mape"], item["mae"]))
    elif valid:
        winner = min(valid, key=lambda item: item["mae"])
    else:
        winner = None
    warnings = []
    if winner is None:
        warnings.append("Todos los modelos fallaron; se usará naive_last_value.")
    return {
        "target": target,
        "train_months": len(train),
        "test_months": test_months,
        "models": results,
        "best_model": (
            {
                key: winner[key]
                for key in ("model", "mae", "mape", "rmse")
            } if winner else None
        ),
        "warnings": warnings,
    }


def run_backtesting(
    periods: list[dict[str, Any]], *, target: str = "all", test_months: int = 6
) -> dict[str, Any]:
    targets = (
        ("revenue", "cost_of_sales") if target == "all" else (target,)
    )
    if any(item not in ("revenue", "cost_of_sales") for item in targets):
        raise ValueError("target debe ser revenue, cost_of_sales o all")
    results = {
        item: backtest_series(
            [float(row[item]) for row in periods],
            target=item,
            test_months=test_months,
        )
        for item in targets
    }
    warnings = [
        warning
        for result in results.values()
        for warning in result.get("warnings", [])
    ]
    return {"test_months": test_months, "results": results, "warnings": warnings}
