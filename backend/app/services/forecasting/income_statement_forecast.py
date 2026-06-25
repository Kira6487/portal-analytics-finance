from __future__ import annotations

from datetime import date
from typing import Any

from app.services.forecasting.backtesting import run_backtesting
from app.services.forecasting.confidence import evaluate_confidence, forecast_bounds
from app.services.forecasting.dataset_builder import build_income_statement_dataset
from app.services.forecasting.explanations import build_explanations
from app.services.forecasting.models import create_model
from app.services.forecasting.recommendations import build_recommendations


LIMITATIONS = [
    "El presupuesto es simulado y no corresponde a un presupuesto oficial SAP.",
    "El mapeo contable es preliminar y está pendiente de validación por Contabilidad.",
    "Las cuentas clase 8 permanecen excluidas para evitar doble conteo.",
    "La moneda oficial de reporte aún no ha sido definida.",
    "La Fase 1 detectó alta volatilidad en los movimientos mensuales.",
    "El forecast es una estimación gerencial, no un estado financiero oficial.",
    "La proyección debe validarse antes de decisiones financieras críticas.",
]


def _next_period(period: str, offset: int) -> str:
    year, month = map(int, period.split("-"))
    absolute = year * 12 + month - 1 + offset
    return f"{absolute // 12}-{absolute % 12 + 1:02d}"


def _future_budget(
    historical: list[dict[str, Any]], period: str, growth_pct: float = 5.0
) -> tuple[float | None, float | None]:
    year, month = map(int, period.split("-"))
    prior_key = f"{year - 1}-{month:02d}"
    prior = next((row for row in historical if row["period"] == prior_key), None)
    if not prior:
        return None, None
    factor = 1 + growth_pct / 100
    return (
        round(float(prior["revenue"]) * factor, 2),
        round(float(prior["cost_of_sales"]) * factor, 2),
    )


def generate_forecast(
    *,
    horizon: int = 6,
    include_budget: bool = True,
    basis_date: date | None = None,
    test_months: int = 6,
) -> dict[str, Any]:
    if horizon not in (3, 6, 12):
        raise ValueError("horizon debe ser 3, 6 o 12")
    dataset = build_income_statement_dataset(
        date_to=basis_date, include_budget=include_budget
    )
    historical = dataset["periods"]
    if len(historical) < 2:
        return {
            "module": "income_statement_forecast",
            "forecast_periods": [],
            "limitations": LIMITATIONS,
            "warnings": ["No hay historia suficiente para generar forecast."],
        }
    backtest = run_backtesting(historical, target="all", test_months=test_months)
    selected_models: dict[str, dict[str, Any]] = {}
    predictions: dict[str, list[float]] = {}
    warnings = list(dataset.get("warnings", [])) + list(backtest.get("warnings", []))

    for target in ("revenue", "cost_of_sales"):
        result = backtest["results"][target]
        winner = result.get("best_model")
        model_name = winner["model"] if winner else "naive_last_value"
        if not winner:
            warnings.append(f"{target}: fallback a naive_last_value.")
            winner = {"model": model_name, "mae": None, "mape": None, "rmse": None}
        series = [float(row[target]) for row in historical]
        try:
            prediction = create_model(model_name).fit(series).predict(horizon)
        except Exception as exc:
            warnings.append(
                f"{target}: el modelo ganador falló al reentrenar ({exc}); "
                "se usó naive_last_value."
            )
            model_name = "naive_last_value"
            prediction = create_model(model_name).fit(series).predict(horizon)
        predictions[target] = [max(0.0, float(value)) for value in prediction]
        confidence = evaluate_confidence(series, winner.get("mape"))
        selected_models[target] = {
            "model": model_name,
            "mape": winner.get("mape"),
            "mae": winner.get("mae"),
            "rmse": winner.get("rmse"),
            **confidence,
        }

    last_period = historical[-1]["period"]
    forecast_periods = []
    for index in range(horizon):
        period = _next_period(last_period, index + 1)
        revenue = predictions["revenue"][index]
        cost = predictions["cost_of_sales"][index]
        gross_profit = revenue - cost
        margin = gross_profit / revenue * 100 if revenue else None
        revenue_budget, cost_budget = (
            _future_budget(historical, period) if include_budget else (None, None)
        )
        gross_budget = (
            revenue_budget - cost_budget
            if revenue_budget is not None and cost_budget is not None else None
        )
        revenue_variance = (
            revenue - revenue_budget if revenue_budget is not None else None
        )
        gross_variance = (
            gross_profit - gross_budget if gross_budget is not None else None
        )
        revenue_low, revenue_high = forecast_bounds(
            revenue,
            mape=selected_models["revenue"]["mape"],
            confidence=selected_models["revenue"]["confidence"],
        )
        cost_low, cost_high = forecast_bounds(
            cost,
            mape=selected_models["cost_of_sales"]["mape"],
            confidence=selected_models["cost_of_sales"]["confidence"],
        )
        forecast_periods.append(
            {
                "period": period,
                "real": None,
                "revenue_forecast": round(revenue, 2),
                "revenue_lower": round(revenue_low, 2),
                "revenue_upper": round(revenue_high, 2),
                "revenue_budget": revenue_budget,
                "revenue_vs_budget": round(revenue_variance, 2) if revenue_variance is not None else None,
                "revenue_vs_budget_pct": (
                    round(revenue_variance / abs(revenue_budget) * 100, 2)
                    if revenue_budget else None
                ),
                "cost_forecast": round(cost, 2),
                "cost_lower": round(cost_low, 2),
                "cost_upper": round(cost_high, 2),
                "cost_budget": cost_budget,
                "gross_profit_forecast": round(gross_profit, 2),
                "gross_margin_pct_forecast": round(margin, 2) if margin is not None else None,
                "gross_profit_budget": round(gross_budget, 2) if gross_budget is not None else None,
                "gross_profit_vs_budget": round(gross_variance, 2) if gross_variance is not None else None,
                "gross_profit_vs_budget_pct": (
                    round(gross_variance / abs(gross_budget) * 100, 2)
                    if gross_budget else None
                ),
                "status": (
                    "favorable" if gross_variance is not None and gross_variance > 0.005
                    else "unfavorable" if gross_variance is not None and gross_variance < -0.005
                    else "neutral"
                ),
            }
        )

    explanations = build_explanations(selected_models, forecast_periods)
    recommendations = build_recommendations(selected_models, forecast_periods)
    effective_basis = basis_date.isoformat() if basis_date else dataset.get("data_max_date")
    return {
        "module": "income_statement_forecast",
        "horizon_months": horizon,
        "basis_date": effective_basis,
        "selected_models": selected_models,
        "backtesting": backtest,
        "forecast_periods": forecast_periods,
        "recent_history": historical[-12:],
        "explanations": explanations,
        "recommendations": recommendations,
        "limitations": LIMITATIONS,
        "warnings": list(dict.fromkeys(warnings)),
    }


def executive_summary(*, horizon: int = 6) -> dict[str, Any]:
    result = generate_forecast(horizon=horizon)
    selected = result.get("selected_models", {})
    confidences = [item["confidence"] for item in selected.values()]
    overall = (
        "low" if "low" in confidences else "medium" if "medium" in confidences else "high"
    )
    periods = result.get("forecast_periods", [])
    revenue_total = sum(row["revenue_forecast"] for row in periods)
    gross_total = sum(row["gross_profit_forecast"] for row in periods)
    below = sum(
        row["status"] == "unfavorable" for row in periods
    )
    summary = (
        f"Para los próximos {horizon} meses se proyectan ingresos acumulados de "
        f"{revenue_total:,.2f} y margen bruto acumulado de {gross_total:,.2f}. "
        f"{below} meses quedan por debajo del presupuesto simulado en margen bruto."
    )
    return {
        "title": "Proyección de ingresos y margen bruto",
        "summary": summary,
        "key_findings": result.get("explanations", []),
        "risks": [
            limitation for limitation in result.get("limitations", [])
            if "volatilidad" in limitation.lower() or "moneda" in limitation.lower()
        ],
        "recommended_actions": result.get("recommendations", []),
        "confidence": overall,
        "warnings": result.get("warnings", []),
    }
