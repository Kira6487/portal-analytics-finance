from __future__ import annotations

from typing import Any


def build_recommendations(
    selected_models: dict[str, dict[str, Any]],
    forecast_periods: list[dict[str, Any]],
) -> list[str]:
    recommendations: list[str] = []
    if any(
        row.get("revenue_vs_budget_pct") is not None
        and row["revenue_vs_budget_pct"] < -10
        for row in forecast_periods
    ):
        recommendations.append(
            "Revisar causas comerciales y las principales cuentas de ingreso: "
            "hay meses con ingresos proyectados más de 10% bajo presupuesto."
        )
    if any(
        row.get("gross_profit_vs_budget_pct") is not None
        and row["gross_profit_vs_budget_pct"] < -10
        for row in forecast_periods
    ):
        recommendations.append(
            "Revisar costo de ventas y estructura de margen en los meses con "
            "brecha de margen bruto superior a 10%."
        )
    if any(item["confidence"] == "low" for item in selected_models.values()):
        recommendations.append(
            "Usar el forecast solo como referencia gerencial y validarlo "
            "manualmente antes de decisiones críticas."
        )
    if any((item.get("volatility_cv") or 0) > 0.60 for item in selected_models.values()):
        recommendations.append(
            "Analizar eventos no recurrentes y asientos extraordinarios que "
            "expliquen la alta volatilidad."
        )
    if any((item.get("outlier_months") or 0) > 0 for item in selected_models.values()):
        recommendations.append(
            "Revisar los meses atípicos y sus asientos o documentos extraordinarios "
            "antes de aprobar el forecast."
        )
    recommendations.append(
        "Cargar un presupuesto oficial o validar el presupuesto simulado con Gerencia."
    )
    return list(dict.fromkeys(recommendations))
