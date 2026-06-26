from __future__ import annotations

from typing import Any


def _safe_divide(numerator: float, denominator: float) -> float | None:
    if denominator is None or abs(denominator) < 0.005:
        return None
    return round(numerator / denominator, 4)


def liquidity_status(projected_cash: float, managerial_liquidity_ratio: float | None) -> str:
    if projected_cash < 0:
        return "critical"
    if managerial_liquidity_ratio is None:
        return "watch" if projected_cash > 0 else "stressed"
    if managerial_liquidity_ratio >= 1.2:
        return "healthy"
    if managerial_liquidity_ratio >= 1.0:
        return "watch"
    return "stressed"


def calculate_ratios(
    *,
    projected_cash: float,
    projected_ar: float,
    projected_ap: float,
    projected_assets: float,
    projected_liabilities: float,
) -> dict[str, Any]:
    working_capital = projected_cash + projected_ar - projected_ap
    managerial = _safe_divide(projected_cash + projected_ar, projected_ap)
    return {
        "working_capital": round(working_capital, 2),
        "cash_to_ap_ratio": _safe_divide(projected_cash, projected_ap),
        "ar_to_ap_ratio": _safe_divide(projected_ar, projected_ap),
        "liabilities_to_assets": _safe_divide(projected_liabilities, projected_assets),
        "managerial_liquidity_ratio": managerial,
        "liquidity_status": liquidity_status(projected_cash, managerial),
    }
