from __future__ import annotations

from datetime import date
from typing import Any, Callable

from app.core.config import get_settings
from app.models.balance_projection_schemas import MANAGERIAL_LIMITATIONS, SCENARIOS
from app.services.cashflow_projection.projection_engine import weekly_projection as cashflow_weekly_projection
from app.services.financial_statements import balance_summary
from app.services.forecasting.income_statement_forecast import generate_forecast
from app.services.payables_predictive.dataset import build_predictive_dataset as build_payables_dataset
from app.services.receivables_predictive.dataset import build_predictive_dataset as build_receivables_dataset


def validate_scenario(scenario: str) -> None:
    if scenario not in SCENARIOS:
        raise ValueError("scenario debe ser base, optimistic o pessimistic")


def safe_call(operation: Callable[..., dict[str, Any]], **kwargs: Any) -> tuple[dict[str, Any], list[str]]:
    try:
        result = operation(**kwargs)
    except Exception as exc:
        return {}, [str(exc)]
    if result.get("status") == "error":
        return {}, list(result.get("warnings", [result.get("message", "Error controlado")]))
    return result, list(result.get("warnings", []))


def _summary_amount(result: dict[str, Any], *keys: str) -> float:
    summary = result.get("summary", {})
    for key in keys:
        if key in summary and summary[key] is not None:
            return float(summary[key] or 0)
    return 0.0


def _forecast_result(basis_date: date | None) -> tuple[float, str, list[str]]:
    forecast, warnings = safe_call(
        generate_forecast,
        horizon=3,
        include_budget=True,
        basis_date=basis_date,
    )
    periods = forecast.get("forecast_periods", [])
    projected_result = sum(float(item.get("gross_profit_forecast") or 0) for item in periods)
    selected = forecast.get("selected_models", {})
    confidences = [item.get("confidence") for item in selected.values()]
    confidence = "low" if "low" in confidences or not confidences else "medium" if "medium" in confidences else "high"
    if periods:
        warnings.append("Se usa margen bruto proyectado como aproximacion limitada del resultado proyectado.")
    return round(projected_result, 2), confidence, warnings


def build_projection_dataset(
    *,
    basis_date: date | None = None,
    opening_cash: float | None = None,
    scenario: str = "base",
) -> dict[str, Any]:
    validate_scenario(scenario)
    settings = get_settings()
    warnings: list[str] = []

    balance, balance_warnings = safe_call(balance_summary, as_of_date=basis_date)
    warnings.extend(f"Balance base: {warning}" for warning in balance_warnings)

    cashflow, cashflow_warnings = safe_call(
        cashflow_weekly_projection,
        basis_date=basis_date,
        horizon_weeks=13,
        scenario=scenario,
        opening_cash=opening_cash,
    )
    warnings.extend(f"Flujo de caja: {warning}" for warning in cashflow_warnings)

    receivables, ar_warnings = safe_call(
        build_receivables_dataset,
        as_of_date=basis_date,
        scenario=scenario,
    )
    warnings.extend(f"CxC predictiva: {warning}" for warning in ar_warnings)

    payables, ap_warnings = safe_call(
        build_payables_dataset,
        as_of_date=basis_date,
        scenario=scenario,
    )
    warnings.extend(f"CxP predictiva: {warning}" for warning in ap_warnings)

    projected_result, forecast_confidence, forecast_warnings = _forecast_result(basis_date)
    warnings.extend(f"Forecast: {warning}" for warning in forecast_warnings)

    effective_basis = (
        cashflow.get("basis_date")
        or receivables.get("as_of_date")
        or payables.get("as_of_date")
        or balance.get("as_of_date")
        or (basis_date.isoformat() if basis_date else date.today().isoformat())
    )
    cashflow_summary = cashflow.get("summary", {})
    opening_source = cashflow.get("opening_cash_source")
    if opening_cash is not None and not opening_source:
        opening_source = "parameter"
    elif not opening_source:
        opening_source = "fallback_zero"
    base_cash = float(cashflow.get("opening_cash") if cashflow.get("opening_cash") is not None else (opening_cash or 0))
    base_ar = _summary_amount(receivables, "open_amount", "total_open_amount")
    base_ap = _summary_amount(payables, "total_open_amount", "open_amount")
    assets = float(balance.get("assets") or 0)
    liabilities = float(balance.get("liabilities") or 0)
    equity = float(balance.get("equity") or 0)
    period_result = float(balance.get("period_result") or 0)

    other_assets = max(0.0, assets - base_cash - base_ar)
    other_liabilities = max(0.0, liabilities - base_ap)
    working_capital = base_cash + base_ar - base_ap
    used_fallback = not cashflow.get("weeks") or not balance or not receivables or not payables
    if used_fallback:
        warnings.append(
            "Conexion SQL/ODBC o datos base no disponibles; no se inventaron documentos ni saldos SAP."
        )

    return {
        "module": "balance_projection",
        "basis_date": effective_basis,
        "scenario": scenario,
        "currency": settings.reporting_currency,
        "currency_symbol": settings.reporting_currency_symbol,
        "base_balance": {
            "assets": round(assets, 2),
            "liabilities": round(liabilities, 2),
            "equity": round(equity, 2),
            "cash": round(base_cash, 2),
            "accounts_receivable": round(base_ar, 2),
            "accounts_payable": round(base_ap, 2),
            "working_capital": round(working_capital, 2),
            "period_result": round(period_result, 2),
            "projected_result_proxy": projected_result,
            "other_assets_constant": round(other_assets, 2),
            "other_liabilities_constant": round(other_liabilities, 2),
            "balance_check_difference": round(float(balance.get("balance_check_difference") or 0), 2),
        },
        "inputs": {
            "receivables_documents": int(receivables.get("summary", {}).get("documents") or len(receivables.get("items", []))),
            "payables_documents": int(payables.get("summary", {}).get("documents") or len(payables.get("items", []))),
            "cashflow_weeks": len(cashflow.get("weeks", [])) or 13,
            "opening_cash_source": opening_source,
            "forecast_confidence": forecast_confidence,
            "used_fallback": used_fallback,
        },
        "source_data": {
            "cashflow": cashflow,
            "receivables": receivables,
            "payables": payables,
            "forecast_projected_result": projected_result,
            "forecast_confidence": forecast_confidence,
        },
        "warnings": list(dict.fromkeys(warnings)),
        "limitations": MANAGERIAL_LIMITATIONS,
    }
