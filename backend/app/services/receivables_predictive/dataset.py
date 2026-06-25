from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any

from app.core.config import get_settings
from app.services.cashflow_projection.datasets import projectable_documents
from app.services.cashflow_projection.projection_engine import weekly_projection
from app.services.receivables_predictive.prioritization import (
    calculate_priority,
    priority_level,
)
from app.services.receivables_predictive.alerts import build_alerts
from app.services.receivables_predictive.risk_scoring import (
    RISK_LEVELS,
    confidence_for_document,
    risk_level,
    score_receivable,
)


LIMITATIONS = [
    "La moneda oficial de la demo es SOL.",
    "Documentos fuente en moneda extranjera pueden requerir conversión FX productiva.",
    "La fecha estimada no garantiza el cobro real.",
    "El score es una regla predictiva inicial, no una calificación crediticia formal.",
    "El análisis depende de documentos, pagos y conciliaciones registrados correctamente en SAP.",
    "No reemplaza criterio contable ni gestión profesional de cobranza.",
    "El módulo no modifica SAP.",
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


def _week(value: str) -> str:
    parsed = date.fromisoformat(value)
    iso = parsed.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def build_predictive_dataset(
    *,
    as_of_date: date | None = None,
    customer: str | None = None,
    risk: str | None = None,
    min_amount: float | None = None,
    days_overdue_min: int | None = None,
    include_closed: bool = False,
    scenario: str = "base",
) -> dict[str, Any]:
    if risk and risk not in RISK_LEVELS:
        raise ValueError("risk debe ser low, medium, high o critical")
    settings = get_settings()
    documents = projectable_documents(basis_date=as_of_date, scenario=scenario)
    basis = date.fromisoformat(documents["basis_date"])
    receivables = documents["receivables"]
    total_open = sum(item["open_amount"] for item in receivables)
    average_amount = total_open / len(receivables) if receivables else 0
    customer_amounts: defaultdict[str, float] = defaultdict(float)
    for item in receivables:
        customer_amounts[item["card_code"]] += item["open_amount"]

    cashflow = weekly_projection(
        basis_date=basis, horizon_weeks=13, scenario=scenario
    )
    deficit_weeks = {
        week["period"]
        for week in cashflow["weeks"]
        if week["projected_cash_balance"] < 0
    }
    items = []
    foreign_currencies: set[str] = set()
    for source in receivables:
        due = date.fromisoformat(source["due_date"])
        document_date = date.fromisoformat(source["document_date"])
        estimated = date.fromisoformat(source["estimated_collection_date"])
        days_overdue = (basis - due).days
        concentration = (
            customer_amounts[source["card_code"]] / total_open * 100
            if total_open else 0
        )
        cashflow_week = _week(source["estimated_collection_date"])
        in_deficit = cashflow_week in deficit_weeks
        score, score_reasons = score_receivable(
            days_overdue=days_overdue,
            open_amount=source["open_amount"],
            average_amount=average_amount,
            behavior=source["collection_behavior"],
            concentration_pct=concentration,
            has_history=source["has_history"],
            in_deficit_week=in_deficit,
            document_age_days=(basis - document_date).days,
        )
        level = risk_level(score)
        draft = {
            "doc_entry": source["doc_entry"],
            "doc_num": source["doc_num"],
            "card_code": source["card_code"],
            "card_name": source["card_name"],
            "doc_date": source["document_date"],
            "due_date": source["due_date"],
            "currency": settings.reporting_currency,
            "currency_symbol": settings.reporting_currency_symbol,
            "source_currency": source["currency"],
            "doc_total": source["document_total"],
            "paid_amount": source["paid_amount"],
            "open_amount": source["open_amount"],
            "days_overdue": days_overdue,
            "aging_bucket": _aging(days_overdue),
            "customer_median_delay_days": source["delay_days_used"],
            "customer_average_delay_days": source["average_delay_days"],
            "historical_paid_documents": source["historical_paid_documents"],
            "collection_behavior": source["collection_behavior"],
            "estimated_collection_date": source["estimated_collection_date"],
            "estimated_delay_days": (estimated - due).days,
            "risk_score": round(score, 2),
            "risk_level": level,
            "cashflow_week": cashflow_week,
            "cashflow_impact": source["open_amount"],
            "in_deficit_week": in_deficit,
            "concentration_pct": round(concentration, 2),
            "has_history": source["has_history"],
        }
        confidence, confidence_reasons = confidence_for_document(draft)
        draft["confidence"] = confidence
        draft["confidence_reasons"] = confidence_reasons
        priority_score, reason = calculate_priority(draft, average_amount)
        draft["priority_score"] = priority_score
        draft["priority_level"] = priority_level(priority_score)
        draft["explanation"] = (
            "; ".join(score_reasons) if score_reasons
            else "Documento sin factores de riesgo relevantes según las reglas actuales."
        )
        draft["priority_reason"] = reason
        if source["currency"] != settings.reporting_currency:
            foreign_currencies.add(str(source["currency"]))

        haystack = f"{draft['card_code']} {draft['card_name']}".lower()
        if customer and customer.lower() not in haystack:
            continue
        if risk and draft["risk_level"] != risk:
            continue
        if min_amount is not None and draft["open_amount"] < min_amount:
            continue
        if days_overdue_min is not None and days_overdue < days_overdue_min:
            continue
        items.append(draft)

    warnings = list(documents["warnings"])
    if include_closed:
        warnings.append(
            "include_closed no está disponible en esta fase; el dataset contiene documentos abiertos."
        )
    if foreign_currencies:
        warnings.append(
            "La demo usa SOL como moneda oficial. Documentos fuente en "
            f"{', '.join(sorted(foreign_currencies))} pueden requerir conversión "
            "para una versión productiva."
        )
    if not items:
        warnings.append("No hay documentos para los filtros seleccionados.")
    items.sort(key=lambda item: item["priority_score"], reverse=True)
    alerts = build_alerts(items, as_of_date=basis)
    return {
        "as_of_date": basis.isoformat(),
        "scenario": scenario,
        "currency": settings.reporting_currency,
        "currency_symbol": settings.reporting_currency_symbol,
        "summary": {
            "documents": len(items),
            "open_amount": round(sum(item["open_amount"] for item in items), 2),
            "high_risk_amount": round(
                sum(item["open_amount"] for item in items if item["risk_level"] == "high"), 2
            ),
            "critical_risk_amount": round(
                sum(item["open_amount"] for item in items if item["risk_level"] == "critical"), 2
            ),
            "foreign_currency_documents": sum(
                item["source_currency"] != settings.reporting_currency for item in items
            ),
        },
        "items": items,
        "alerts": alerts,
        "limitations": LIMITATIONS,
        "warnings": list(dict.fromkeys(warnings)),
    }
