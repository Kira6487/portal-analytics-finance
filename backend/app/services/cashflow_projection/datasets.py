from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import get_connection
from app.core.config import get_settings
from app.queries.cashflow_projection_queries import DATA_BASIS_DATE_SQL
from app.queries.payables_queries import OPEN_PAYABLES_SQL
from app.queries.receivables_queries import OPEN_RECEIVABLES_SQL
from app.services.cashflow_projection.payment_behavior import behavior_maps


SCENARIOS = ("base", "optimistic", "pessimistic")
DOCUMENT_LIMITATIONS = [
    "La moneda oficial de reporte está pendiente de definición.",
    "Solo se consideran documentos que permanecen abiertos en SAP.",
    "Las fechas estimadas no garantizan el comportamiento futuro.",
    "No se modifica SAP ni se crean documentos.",
]


def resolve_basis_date(value: date | None = None) -> date:
    if value:
        return value
    with get_connection() as connection:
        row = connection.execute(text(DATA_BASIS_DATE_SQL)).mappings().one()
    raw = row["basis_date"]
    return raw.date() if hasattr(raw, "date") else raw


def _as_date(value) -> date:
    return value.date() if hasattr(value, "date") else value


def _estimated_date(
    *,
    due_date: date,
    document_date: date,
    basis_date: date,
    delay_days: int,
    scenario: str,
    receivable: bool,
) -> date:
    base = due_date + timedelta(days=delay_days)
    if receivable:
        if scenario == "optimistic":
            estimated = base - timedelta(days=7)
        elif scenario == "pessimistic":
            estimated = base + timedelta(days=15)
        else:
            estimated = base
        return max(basis_date, document_date, estimated)
    if scenario == "optimistic":
        estimated = due_date
    else:
        estimated = base
    if due_date <= basis_date:
        return basis_date
    return max(basis_date, estimated)


def projectable_documents(
    *, basis_date: date | None = None, scenario: str = "base"
) -> dict[str, Any]:
    if scenario not in SCENARIOS:
        raise ValueError("scenario debe ser base, optimistic o pessimistic")
    basis = resolve_basis_date(basis_date)
    settings = get_settings()
    customer_behavior, vendor_behavior, warnings = behavior_maps()
    receivables = []
    payables = []
    try:
        with get_connection() as connection:
            receivable_rows = connection.execute(
                text(OPEN_RECEIVABLES_SQL), {"as_of_date": basis}
            ).mappings().all()
            payable_rows = connection.execute(
                text(OPEN_PAYABLES_SQL), {"as_of_date": basis}
            ).mappings().all()
    except SQLAlchemyError as exc:
        return {
            "basis_date": basis.isoformat(),
            "scenario": scenario,
            "receivables": [],
            "payables": [],
            "warnings": warnings + [str(exc)],
        }

    for row in receivable_rows:
        behavior = customer_behavior.get(str(row["partner_code"]))
        delay = int(round(behavior["median_delay_days"])) if behavior else 7
        delay = max(-30, min(90, delay))
        due = _as_date(row["due_date"])
        document_date = _as_date(row["document_date"])
        estimated = _estimated_date(
            due_date=due,
            document_date=document_date,
            basis_date=basis,
            delay_days=delay,
            scenario=scenario,
            receivable=True,
        )
        overdue = (basis - due).days
        receivables.append(
            {
                "doc_entry": int(row["doc_entry"]),
                "doc_num": int(row["document_number"]),
                "card_code": row["partner_code"],
                "card_name": row["partner_name"],
                "document_date": document_date.isoformat(),
                "due_date": due.isoformat(),
                "estimated_collection_date": estimated.isoformat(),
                "currency": row["currency"],
                "document_total": round(float(row["document_total"] or 0), 2),
                "paid_amount": round(float(row["paid_amount"] or 0), 2),
                "open_amount": round(float(row["open_amount"] or 0), 2),
                "delay_days_used": delay,
                "has_history": behavior is not None,
                "history_confidence": behavior["confidence"] if behavior else "none",
                "historical_paid_documents": behavior["paid_documents"] if behavior else 0,
                "average_delay_days": behavior["average_delay_days"] if behavior else None,
                "collection_behavior": behavior["behavior"] if behavior else "sin_historial_suficiente",
                "risk": "high" if overdue > 30 else "medium" if overdue > 0 else "low",
            }
        )

    for row in payable_rows:
        behavior = vendor_behavior.get(str(row["partner_code"]))
        delay = int(round(behavior["median_delay_days"])) if behavior else 0
        delay = max(-15, min(60, delay))
        due = _as_date(row["due_date"])
        document_date = _as_date(row["document_date"])
        estimated = _estimated_date(
            due_date=due,
            document_date=document_date,
            basis_date=basis,
            delay_days=delay,
            scenario=scenario,
            receivable=False,
        )
        overdue = (basis - due).days
        payables.append(
            {
                "doc_entry": int(row["doc_entry"]),
                "doc_num": int(row["document_number"]),
                "card_code": row["partner_code"],
                "card_name": row["partner_name"],
                "document_date": document_date.isoformat(),
                "due_date": due.isoformat(),
                "estimated_payment_date": estimated.isoformat(),
                "currency": row["currency"],
                "document_total": round(float(row["document_total"] or 0), 2),
                "paid_amount": round(float(row["paid_amount"] or 0), 2),
                "open_amount": round(float(row["open_amount"] or 0), 2),
                "delay_days_used": delay,
                "has_history": behavior is not None,
                "history_confidence": behavior["confidence"] if behavior else "none",
                "historical_paid_documents": behavior["paid_documents"] if behavior else 0,
                "average_delay_days": behavior["average_delay_days"] if behavior else None,
                "payment_behavior": behavior["behavior"] if behavior else "sin_historial_suficiente",
                "priority": "critical" if overdue > 30 else "overdue" if overdue > 0 else "normal",
            }
        )

    if any(not item["has_history"] for item in receivables):
        warnings.append("Algunas CxC usan atraso por defecto de 7 días por falta de historial.")
    if any(not item["has_history"] for item in payables):
        warnings.append("Algunas CxP usan vencimiento contractual por falta de historial.")
    return {
        "basis_date": basis.isoformat(),
        "scenario": scenario,
        "currency": settings.reporting_currency,
        "currency_symbol": settings.reporting_currency_symbol,
        "receivables": receivables,
        "payables": payables,
        "limitations": DOCUMENT_LIMITATIONS,
        "warnings": list(dict.fromkeys(warnings)),
    }
