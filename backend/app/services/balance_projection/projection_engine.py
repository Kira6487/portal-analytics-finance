from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from app.models.balance_projection_schemas import HORIZON_WEEKS, MANAGERIAL_LIMITATIONS
from app.services.balance_projection.alerts import build_alerts
from app.services.balance_projection.dataset import build_projection_dataset, validate_scenario
from app.services.balance_projection.explanations import build_explanations
from app.services.balance_projection.ratios import calculate_ratios, liquidity_status
from app.services.balance_projection.recommendations import build_recommendations


def _fallback_cashflow_weeks(
    *, basis: date, horizon_weeks: int, opening_cash: float
) -> list[dict[str, Any]]:
    start = basis - timedelta(days=basis.weekday())
    return [
        {
            "period": f"{(start + timedelta(days=i * 7)).isocalendar().year}-W{(start + timedelta(days=i * 7)).isocalendar().week:02d}",
            "week_start": (start + timedelta(days=i * 7)).isoformat(),
            "week_end": (start + timedelta(days=i * 7 + 6)).isoformat(),
            "expected_collections": 0.0,
            "expected_payments": 0.0,
            "net_cashflow": 0.0,
            "projected_cash_balance": round(opening_cash, 2),
            "collections_count": 0,
            "payments_count": 0,
            "status": "warning",
        }
        for i in range(horizon_weeks)
    ]


def weekly_balance_projection(
    *,
    basis_date: date | None = None,
    horizon_weeks: int = 13,
    scenario: str = "base",
    opening_cash: float | None = None,
) -> dict[str, Any]:
    validate_scenario(scenario)
    if horizon_weeks not in HORIZON_WEEKS:
        raise ValueError("horizon_weeks debe ser 4, 8, 13 o 26")
    dataset = build_projection_dataset(
        basis_date=basis_date, opening_cash=opening_cash, scenario=scenario
    )
    basis = date.fromisoformat(dataset["basis_date"])
    base = dataset["base_balance"]
    cashflow = dataset["source_data"]["cashflow"]
    cashflow_weeks = cashflow.get("weeks", [])[:horizon_weeks]
    if not cashflow_weeks:
        cashflow_weeks = _fallback_cashflow_weeks(
            basis=basis,
            horizon_weeks=horizon_weeks,
            opening_cash=float(base["cash"]),
        )
    total_ar = float(base["accounts_receivable"])
    total_ap = float(base["accounts_payable"])
    other_assets = float(base["other_assets_constant"])
    other_liabilities = float(base["other_liabilities_constant"])
    projected_result = float(base["projected_result_proxy"])

    cumulative_collections = 0.0
    cumulative_payments = 0.0
    weeks: list[dict[str, Any]] = []
    for source in cashflow_weeks:
        cumulative_collections += float(source.get("expected_collections") or 0)
        cumulative_payments += float(source.get("expected_payments") or 0)
        projected_cash = float(source.get("projected_cash_balance") or 0)
        projected_ar = max(0.0, total_ar - cumulative_collections)
        projected_ap = max(0.0, total_ap - cumulative_payments)
        projected_assets = max(0.0, projected_cash + projected_ar + other_assets)
        projected_liabilities = max(0.0, projected_ap + other_liabilities)
        projected_equity = float(base["equity"]) + projected_result
        ratios = calculate_ratios(
            projected_cash=projected_cash,
            projected_ar=projected_ar,
            projected_ap=projected_ap,
            projected_assets=projected_assets,
            projected_liabilities=projected_liabilities,
        )
        balance_difference = projected_assets - projected_liabilities - projected_equity
        weeks.append(
            {
                "period": source["period"],
                "week_start": source["week_start"],
                "week_end": source["week_end"],
                "projected_cash": round(projected_cash, 2),
                "projected_ar": round(projected_ar, 2),
                "projected_ap": round(projected_ap, 2),
                "projected_working_capital": ratios["working_capital"],
                "net_cashflow": round(float(source.get("net_cashflow") or 0), 2),
                "collections": round(float(source.get("expected_collections") or 0), 2),
                "payments": round(float(source.get("expected_payments") or 0), 2),
                "projected_assets": round(projected_assets, 2),
                "projected_liabilities": round(projected_liabilities, 2),
                "projected_equity": round(projected_equity, 2),
                "managerial_balance_difference": round(balance_difference, 2),
                "ratios": ratios,
                "liquidity_status": ratios["liquidity_status"],
            }
        )
    ending = weeks[-1] if weeks else None
    ending_ratios = ending["ratios"] if ending else {}
    statuses = [week["liquidity_status"] for week in weeks]
    overall_status = (
        "critical" if "critical" in statuses else "stressed" if "stressed" in statuses else "watch" if "watch" in statuses else "healthy"
    )
    alerts = build_alerts(
        weeks=weeks,
        scenario=scenario,
        forecast_confidence=dataset["inputs"]["forecast_confidence"],
        warnings=dataset["warnings"],
        balance_check_difference=float(base["balance_check_difference"]),
        opening_cash_source=dataset["inputs"]["opening_cash_source"],
    )
    explanations = build_explanations(
        scenario=scenario,
        weeks=weeks,
        used_fallback=bool(dataset["inputs"]["used_fallback"]),
    )
    recommendations = build_recommendations(
        weeks=weeks,
        alerts=alerts,
        forecast_confidence=dataset["inputs"]["forecast_confidence"],
        opening_cash_source=dataset["inputs"]["opening_cash_source"],
        warnings=dataset["warnings"],
    )
    return {
        "module": "balance_projection_weekly",
        "basis_date": dataset["basis_date"],
        "horizon_weeks": horizon_weeks,
        "scenario": scenario,
        "currency": dataset["currency"],
        "currency_symbol": dataset["currency_symbol"],
        "summary": {
            "opening_cash": round(float(base["cash"]), 2),
            "opening_cash_source": dataset["inputs"]["opening_cash_source"],
            "ending_cash": ending["projected_cash"] if ending else round(float(base["cash"]), 2),
            "minimum_cash": min((week["projected_cash"] for week in weeks), default=round(float(base["cash"]), 2)),
            "projected_ar_end": ending["projected_ar"] if ending else round(total_ar, 2),
            "projected_ap_end": ending["projected_ap"] if ending else round(total_ap, 2),
            "working_capital_end": ending["projected_working_capital"] if ending else round(float(base["working_capital"]), 2),
            "liquidity_status": overall_status or liquidity_status(float(base["cash"]), ending_ratios.get("managerial_liquidity_ratio")),
            "deficit_weeks": sum(week["projected_cash"] < 0 for week in weeks),
            "projected_result_proxy": round(projected_result, 2),
        },
        "weeks": weeks,
        "ratios": ending_ratios,
        "alerts": alerts,
        "explanations": explanations,
        "recommendations": recommendations,
        "limitations": MANAGERIAL_LIMITATIONS,
        "warnings": dataset["warnings"],
    }
