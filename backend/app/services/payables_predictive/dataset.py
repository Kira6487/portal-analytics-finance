from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any

from app.core.config import get_settings
from app.models.payables_predictive_schemas import SCENARIOS
from app.services.cashflow_projection.datasets import projectable_documents
from app.services.cashflow_projection.projection_engine import weekly_projection
from app.services.payables_predictive.alerts import build_alerts
from app.services.payables_predictive.explanations import document_explanation
from app.services.payables_predictive.payment_dates import (
    estimate_payment_date,
    recommend_payment_date,
)
from app.services.payables_predictive.prioritization import (
    calculate_payment_priority,
    priority_level,
    validate_priority,
)
from app.services.payables_predictive.risk_scoring import (
    confidence_for_document,
    risk_level,
    score_payable_risk,
    validate_risk,
)


FX_WARNING = (
    "La demo presenta importes en SOL usando valores locales SAP. Documentos "
    "con moneda fuente distinta de SOL requieren politica FX productiva antes "
    "de produccion."
)

LIMITATIONS = [
    "La moneda oficial de demo es SOL.",
    "Documentos en moneda extranjera pueden requerir conversion futura.",
    "La fecha recomendada no programa pagos automaticamente.",
    "La clasificacion de prioridad es una regla gerencial inicial.",
    "Depende de que SAP tenga documentos, pagos y conciliaciones correctamente registrados.",
    "No reemplaza criterio de Tesoreria ni Contabilidad.",
    "No modifica SAP.",
    "No debe usarse como instruccion automatica de pago.",
]


def _aging(days: int) -> str:
    if days <= 0:
        return "not_due"
    if days <= 30:
        return "1_30"
    if days <= 60:
        return "31_60"
    if days <= 90:
        return "61_90"
    return "90_plus"


def _week(value: date) -> str:
    iso = value.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def _normalize_payment_behavior(value: str) -> str:
    mapping = {
        "se_paga_puntual": "pago_puntual",
        "se_paga_atraso_leve": "atraso_leve",
        "se_paga_atraso_moderado": "atraso_moderado",
        "se_paga_atraso_critico": "atraso_critico",
        "sin_historial_suficiente": "sin_historial",
    }
    return mapping.get(value or "", value or "sin_historial")


def _deferral_decision(
    *,
    days_overdue: int,
    days_until_due: int,
    priority: str,
    risk: str,
    in_deficit_week: bool,
    concentration_pct: float,
) -> tuple[bool, str]:
    if days_overdue > 0:
        return False, "Documento vencido; no debe tratarse como postergable."
    if days_until_due <= 7:
        return False, "Documento vence en los proximos 7 dias."
    if priority not in ("low", "medium"):
        return False, "Prioridad de pago elevada."
    if risk == "critical":
        return False, "Riesgo critico por no atender el pago."
    if concentration_pct > 20:
        return False, "Proveedor altamente concentrador; requiere revision directa."
    if in_deficit_week:
        return True, "Documento no vencido en semana de presion de caja; revisar posible negociacion."
    return False, "No cae en una semana deficitaria."


def _cash_pressure_score(
    *,
    concentration_pct: float,
    overdue_amount: float,
    open_amount: float,
    deficit_amount: float,
    documents: int,
) -> float:
    overdue_ratio = overdue_amount / open_amount * 100 if open_amount else 0
    deficit_ratio = deficit_amount / open_amount * 100 if open_amount else 0
    score = concentration_pct * 1.4 + overdue_ratio * 0.35 + deficit_ratio * 0.35 + min(documents, 10) * 2
    return round(min(100, max(0, score)), 2)


def _validate_scenario(value: str) -> None:
    if value not in SCENARIOS:
        raise ValueError("scenario debe ser base, optimistic o pessimistic")


def build_predictive_dataset(
    *,
    as_of_date: date | None = None,
    vendor: str | None = None,
    priority: str | None = None,
    risk: str | None = None,
    min_amount: float | None = None,
    days_overdue_min: int | None = None,
    include_closed: bool = False,
    scenario: str = "base",
) -> dict[str, Any]:
    _validate_scenario(scenario)
    validate_priority(priority)
    validate_risk(risk)
    settings = get_settings()
    documents = projectable_documents(basis_date=as_of_date, scenario=scenario)
    basis = date.fromisoformat(documents["basis_date"])
    payables = documents["payables"]
    total_open = sum(item["open_amount"] for item in payables)
    average_amount = total_open / len(payables) if payables else 0

    vendor_amounts: defaultdict[str, float] = defaultdict(float)
    vendor_overdue: defaultdict[str, float] = defaultdict(float)
    vendor_documents: defaultdict[str, int] = defaultdict(int)
    for item in payables:
        due = date.fromisoformat(item["due_date"])
        amount = float(item["open_amount"] or 0)
        vendor_amounts[item["card_code"]] += amount
        vendor_documents[item["card_code"]] += 1
        if (basis - due).days > 0:
            vendor_overdue[item["card_code"]] += amount

    cashflow = weekly_projection(basis_date=basis, horizon_weeks=13, scenario=scenario)
    deficit_weeks = {
        week["period"]
        for week in cashflow["weeks"]
        if week["projected_cash_balance"] < 0 or week.get("status") == "deficit"
    }

    raw_items: list[dict[str, Any]] = []
    foreign_currencies: set[str] = set()
    for source in payables:
        due = date.fromisoformat(source["due_date"])
        document_date = date.fromisoformat(source["document_date"])
        amount = float(source["open_amount"] or 0)
        days_overdue = (basis - due).days
        days_until_due = (due - basis).days
        source_currency = source.get("currency") or settings.reporting_currency
        concentration = vendor_amounts[source["card_code"]] / total_open * 100 if total_open else 0
        projected_estimated = date.fromisoformat(source["estimated_payment_date"])
        estimated = estimate_payment_date(
            due_date=due,
            as_of_date=basis,
            vendor_median_payment_delay_days=int(source.get("delay_days_used") or 0),
            has_history=bool(source.get("has_history")),
            scenario=scenario,
        )
        if estimated != projected_estimated and scenario == "base":
            estimated = projected_estimated
        cashflow_week = _week(estimated)
        in_deficit = cashflow_week in deficit_weeks
        vendor_pressure = _cash_pressure_score(
            concentration_pct=concentration,
            overdue_amount=vendor_overdue[source["card_code"]],
            open_amount=vendor_amounts[source["card_code"]],
            deficit_amount=amount if in_deficit else 0,
            documents=vendor_documents[source["card_code"]],
        )
        behavior = _normalize_payment_behavior(source.get("payment_behavior"))
        priority_score, priority_reasons = calculate_payment_priority(
            days_overdue=days_overdue,
            days_until_due=days_until_due,
            open_amount=amount,
            average_amount=average_amount,
            concentration_pct=concentration,
            in_deficit_week=in_deficit,
            has_history=bool(source.get("has_history")),
            payment_behavior=behavior,
            vendor_pressure_score=vendor_pressure,
            document_age_days=(basis - document_date).days,
        )
        priority_name = priority_level(priority_score)
        risk_score, risk_reasons = score_payable_risk(
            days_overdue=days_overdue,
            open_amount=amount,
            average_amount=average_amount,
            concentration_pct=concentration,
            in_deficit_week=in_deficit,
            has_history=bool(source.get("has_history")),
            source_currency=source_currency,
            reporting_currency=settings.reporting_currency,
            vendor_pressure_score=vendor_pressure,
        )
        risk_name = risk_level(risk_score)
        recommended, recommendation_reason = recommend_payment_date(
            due_date=due,
            as_of_date=basis,
            estimated_payment_date=estimated,
            days_overdue=days_overdue,
            days_until_due=days_until_due,
            priority_level=priority_name,
            in_deficit_week=in_deficit,
        )
        can_defer, deferral_reason = _deferral_decision(
            days_overdue=days_overdue,
            days_until_due=days_until_due,
            priority=priority_name,
            risk=risk_name,
            in_deficit_week=in_deficit,
            concentration_pct=concentration,
        )
        item = {
            "doc_entry": int(source["doc_entry"]),
            "doc_num": int(source["doc_num"]),
            "card_code": source["card_code"],
            "card_name": source["card_name"],
            "doc_date": source["document_date"],
            "due_date": source["due_date"],
            "currency": settings.reporting_currency,
            "currency_symbol": settings.reporting_currency_symbol,
            "source_currency": source_currency,
            "doc_total": source["document_total"],
            "paid_amount": source["paid_amount"],
            "open_amount": round(amount, 2),
            "days_overdue": days_overdue,
            "aging_bucket": _aging(days_overdue),
            "vendor_median_payment_delay_days": int(source.get("delay_days_used") or 0),
            "vendor_average_payment_delay_days": source.get("average_delay_days"),
            "historical_paid_documents": int(source.get("historical_paid_documents") or 0),
            "payment_behavior": behavior,
            "estimated_payment_date": estimated.isoformat(),
            "recommended_payment_date": recommended.isoformat(),
            "estimated_delay_days": (estimated - due).days,
            "cashflow_week": cashflow_week,
            "cashflow_impact": round(amount, 2),
            "payment_priority_score": priority_score,
            "payment_priority_level": priority_name,
            "cash_pressure_score": vendor_pressure,
            "risk_score": risk_score,
            "risk_level": risk_name,
            "can_consider_deferral": can_defer,
            "deferral_reason": deferral_reason,
            "recommendation_reason": recommendation_reason,
            "in_deficit_week": in_deficit,
            "concentration_pct": round(concentration, 2),
            "has_history": bool(source.get("has_history")),
        }
        confidence, confidence_reasons = confidence_for_document(item)
        item["confidence"] = confidence
        item["confidence_reasons"] = confidence_reasons
        item["explanation"] = document_explanation(priority_reasons, risk_reasons)
        if source_currency != settings.reporting_currency:
            foreign_currencies.add(str(source_currency))
        raw_items.append(item)

    filtered = []
    for item in raw_items:
        haystack = f"{item['card_code']} {item['card_name']}".lower()
        if vendor and vendor.lower() not in haystack:
            continue
        if priority and item["payment_priority_level"] != priority:
            continue
        if risk and item["risk_level"] != risk:
            continue
        if min_amount is not None and item["open_amount"] < min_amount:
            continue
        if days_overdue_min is not None and item["days_overdue"] < days_overdue_min:
            continue
        filtered.append(item)

    filtered.sort(
        key=lambda item: (item["payment_priority_score"], item["risk_score"], item["open_amount"]),
        reverse=True,
    )
    warnings = list(documents.get("warnings", []))
    if include_closed:
        warnings.append(
            "include_closed no esta disponible en esta fase; el dataset contiene documentos abiertos."
        )
    if foreign_currencies:
        warnings.append(FX_WARNING)
    if not filtered:
        warnings.append("No hay documentos para los filtros seleccionados.")
    return {
        "as_of_date": basis.isoformat(),
        "scenario": scenario,
        "currency": settings.reporting_currency,
        "currency_symbol": settings.reporting_currency_symbol,
        "summary": {
            "documents": len(filtered),
            "total_open_amount": round(sum(item["open_amount"] for item in filtered), 2),
            "urgent_amount": round(
                sum(item["open_amount"] for item in filtered if item["payment_priority_level"] == "urgent"), 2
            ),
            "high_priority_amount": round(
                sum(item["open_amount"] for item in filtered if item["payment_priority_level"] == "high"), 2
            ),
            "overdue_amount": round(
                sum(item["open_amount"] for item in filtered if item["days_overdue"] > 0), 2
            ),
            "deferrable_amount": round(
                sum(item["open_amount"] for item in filtered if item["can_consider_deferral"]), 2
            ),
            "foreign_currency_documents": sum(
                item["source_currency"] != settings.reporting_currency for item in filtered
            ),
        },
        "items": filtered,
        "alerts": build_alerts(filtered),
        "limitations": LIMITATIONS,
        "warnings": list(dict.fromkeys(warnings)),
    }
