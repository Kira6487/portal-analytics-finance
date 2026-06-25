from __future__ import annotations

from datetime import date
from typing import Any

from app.services.cashflow_projection.projection_engine import weekly_projection


def compare_scenarios(
    *,
    basis_date: date | None = None,
    horizon_weeks: int = 13,
    opening_cash: float | None = None,
) -> dict[str, Any]:
    results = [
        weekly_projection(
            basis_date=basis_date,
            horizon_weeks=horizon_weeks,
            scenario=scenario,
            opening_cash=opening_cash,
        )
        for scenario in ("optimistic", "base", "pessimistic")
    ]
    scenarios = [
        {
            "scenario": result["scenario"],
            "ending_cash": result["summary"]["ending_cash"],
            "minimum_cash": result["summary"]["minimum_cash"],
            "deficit_weeks": result["summary"]["deficit_weeks"],
            "expected_collections": result["summary"]["expected_collections"],
            "expected_payments": result["summary"]["expected_payments"],
        }
        for result in results
    ]
    optimistic, base, pessimistic = scenarios
    explanation = (
        f"Entre el escenario optimista y el pesimista existe una diferencia de "
        f"{optimistic['ending_cash'] - pessimistic['ending_cash']:,.2f} en caja final. "
        f"El escenario base presenta {base['deficit_weeks']} semanas en déficit."
    )
    recommendations = list(
        dict.fromkeys(
            recommendation
            for result in results
            for recommendation in result["recommendations"]
        )
    )
    warnings = list(
        dict.fromkeys(
            warning for result in results for warning in result["warnings"]
        )
    )
    return {
        "basis_date": results[0]["basis_date"],
        "horizon_weeks": horizon_weeks,
        "opening_cash": results[0]["opening_cash"],
        "currency": results[0]["currency"],
        "currency_symbol": results[0]["currency_symbol"],
        "scenarios": scenarios,
        "comparison_explanation": explanation,
        "recommendations": recommendations,
        "limitations": results[0]["limitations"],
        "warnings": warnings,
    }


def executive_summary(
    *,
    basis_date: date | None = None,
    horizon_weeks: int = 13,
    scenario: str = "base",
    opening_cash: float | None = None,
) -> dict[str, Any]:
    result = weekly_projection(
        basis_date=basis_date,
        horizon_weeks=horizon_weeks,
        scenario=scenario,
        opening_cash=opening_cash,
    )
    summary = result["summary"]
    text = (
        f"En el escenario {scenario}, la caja final proyectada a "
        f"{horizon_weeks} semanas es {summary['ending_cash']:,.2f}; "
        f"la caja mínima es {summary['minimum_cash']:,.2f} y se detectan "
        f"{summary['deficit_weeks']} semanas en déficit."
    )
    return {
        "title": f"Flujo de caja proyectado a {horizon_weeks} semanas",
        "summary": text,
        "key_findings": result["explanations"],
        "risks": [alert["message"] for alert in result["alerts"]],
        "recommended_actions": result["recommendations"],
        "confidence": summary["confidence"],
        "currency": result["currency"],
        "currency_symbol": result["currency_symbol"],
        "limitations": result["limitations"],
        "warnings": result["warnings"],
    }
