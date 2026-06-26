from __future__ import annotations

from datetime import date
from typing import Any

from app.models.balance_projection_schemas import SCENARIOS
from app.services.balance_projection.projection_engine import weekly_balance_projection
from app.services.balance_projection.recommendations import build_recommendations


def compare_scenarios(
    *,
    basis_date: date | None = None,
    horizon_weeks: int = 13,
    opening_cash: float | None = None,
) -> dict[str, Any]:
    results = []
    warnings: list[str] = []
    limitations: list[str] = []
    all_alerts: list[dict[str, Any]] = []
    for scenario in ("optimistic", "base", "pessimistic"):
        projection = weekly_balance_projection(
            basis_date=basis_date,
            horizon_weeks=horizon_weeks,
            scenario=scenario,
            opening_cash=opening_cash,
        )
        summary = projection["summary"]
        results.append(
            {
                "scenario": scenario,
                "ending_cash": summary["ending_cash"],
                "minimum_cash": summary["minimum_cash"],
                "working_capital_end": summary["working_capital_end"],
                "projected_ar_end": summary["projected_ar_end"],
                "projected_ap_end": summary["projected_ap_end"],
                "deficit_weeks": summary["deficit_weeks"],
                "liquidity_status": summary["liquidity_status"],
            }
        )
        warnings.extend(projection.get("warnings", []))
        limitations = projection.get("limitations", limitations)
        all_alerts.extend(projection.get("alerts", []))
        basis = projection["basis_date"]
        currency = projection["currency"]
        symbol = projection["currency_symbol"]
    base = next(item for item in results if item["scenario"] == "base")
    pessimistic = next(item for item in results if item["scenario"] == "pessimistic")
    comparison = (
        f"El escenario base termina con caja S/ {base['ending_cash']:,.2f}; "
        f"el pesimista termina con S/ {pessimistic['ending_cash']:,.2f} y "
        f"{pessimistic['deficit_weeks']} semanas en deficit."
    )
    recommendations = build_recommendations(
        weeks=[],
        alerts=all_alerts,
        forecast_confidence="low" if any("forecast" in warning.lower() for warning in warnings) else "medium",
        opening_cash_source="fallback_zero" if any("caja inicial" in warning.lower() for warning in warnings) else "detected",
        warnings=warnings,
    )
    return {
        "module": "balance_projection_scenarios",
        "basis_date": basis,
        "horizon_weeks": horizon_weeks,
        "currency": currency,
        "currency_symbol": symbol,
        "scenarios": results,
        "comparison_explanation": comparison,
        "recommendations": recommendations,
        "limitations": limitations,
        "warnings": list(dict.fromkeys(warnings)),
    }


def scenario_values() -> tuple[str, ...]:
    return SCENARIOS
