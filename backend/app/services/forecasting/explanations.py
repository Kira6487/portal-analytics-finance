from __future__ import annotations

from typing import Any


def build_explanations(
    selected_models: dict[str, dict[str, Any]],
    forecast_periods: list[dict[str, Any]],
) -> list[str]:
    explanations = []
    labels = {"revenue": "ingresos", "cost_of_sales": "costo de ventas"}
    for target, result in selected_models.items():
        mape = result.get("mape")
        metric = f"MAPE {mape:.2f}%" if mape is not None else f"MAE {result.get('mae', 0):,.2f}"
        explanations.append(
            f"El modelo seleccionado para {labels[target]} fue "
            f"{result['model']} porque obtuvo el menor error válido ({metric}) "
            "en el backtesting."
        )
    explanations.append(
        "El margen bruto proyectado se calcula como ingresos proyectados menos "
        "costo de ventas proyectado; no se pronostica de forma independiente."
    )
    below = sum(
        1 for row in forecast_periods
        if row.get("gross_profit_budget") is not None
        and row["gross_profit_forecast"] < row["gross_profit_budget"]
    )
    if below:
        explanations.append(
            f"El margen bruto proyectado queda por debajo del presupuesto simulado "
            f"en {below} de {len(forecast_periods)} meses."
        )
    explanations.append(
        "El presupuesto usado es simulado porque SAP no contiene registros "
        "presupuestales utilizables."
    )
    return explanations
