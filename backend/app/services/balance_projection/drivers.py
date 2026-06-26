from __future__ import annotations

from datetime import date
from typing import Any

from app.services.balance_projection.projection_engine import weekly_balance_projection


def drivers_analysis(
    *,
    basis_date: date | None = None,
    horizon_weeks: int = 13,
    scenario: str = "base",
    opening_cash: float | None = None,
) -> dict[str, Any]:
    projection = weekly_balance_projection(
        basis_date=basis_date,
        horizon_weeks=horizon_weeks,
        scenario=scenario,
        opening_cash=opening_cash,
    )
    weeks = projection["weeks"]
    collections = sum(week["collections"] for week in weeks)
    payments = sum(week["payments"] for week in weeks)
    net = sum(week["net_cashflow"] for week in weeks)
    ar_reduction = weeks[0]["projected_ar"] - weeks[-1]["projected_ar"] if len(weeks) > 1 else 0
    ap_reduction = weeks[0]["projected_ap"] - weeks[-1]["projected_ap"] if len(weeks) > 1 else 0
    top_positive = [
        {"driver": "Cobros esperados", "amount": round(collections, 2), "currency": projection["currency"]},
        {"driver": "Reduccion proyectada de CxP", "amount": round(max(0, ap_reduction), 2), "currency": projection["currency"]},
    ]
    top_negative = [
        {"driver": "Pagos esperados", "amount": round(payments, 2), "currency": projection["currency"]},
        {"driver": "Reduccion proyectada de CxC", "amount": round(max(0, ar_reduction), 2), "currency": projection["currency"]},
    ]
    cash_drivers = [
        {"driver": "Variacion neta de caja", "amount": round(net, 2), "currency": projection["currency"]},
        {"driver": "Semana de menor caja", "period": min(weeks, key=lambda week: week["projected_cash"])["period"] if weeks else None},
    ]
    working_capital_drivers = [
        {"driver": "Capital de trabajo final", "amount": projection["summary"]["working_capital_end"], "currency": projection["currency"]},
        {"driver": "Ratio liquidez gerencial final", "value": projection["ratios"].get("managerial_liquidity_ratio")},
    ]
    return {
        "module": "balance_projection_drivers",
        "currency": projection["currency"],
        "currency_symbol": projection["currency_symbol"],
        "top_positive_drivers": top_positive,
        "top_negative_drivers": top_negative,
        "cash_drivers": cash_drivers,
        "working_capital_drivers": working_capital_drivers,
        "explanations": projection["explanations"],
        "limitations": projection["limitations"],
        "warnings": projection["warnings"],
    }
