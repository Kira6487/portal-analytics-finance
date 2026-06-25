from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import get_connection
from app.queries.payables_queries import OPEN_PAYABLES_SQL
from app.queries.receivables_queries import OPEN_RECEIVABLES_SQL


def _bucket(days: int) -> tuple[str, str]:
    if days <= 0:
        return "No vencido", "not_due"
    if days <= 30:
        return "1-30", "days_1_30"
    if days <= 60:
        return "31-60", "days_31_60"
    if days <= 90:
        return "61-90", "days_61_90"
    return "90+", "days_90_plus"


def _open_items(
    *,
    kind: str,
    as_of_date: date | None = None,
    partner: str | None = None,
    risk: str | None = None,
    min_amount: float | None = None,
    days_min: int | None = None,
) -> dict[str, Any]:
    target = as_of_date or date.today()
    sql = OPEN_RECEIVABLES_SQL if kind == "receivables" else OPEN_PAYABLES_SQL
    warnings: list[str] = []
    try:
        with get_connection() as connection:
            rows = connection.execute(text(sql), {"as_of_date": target}).mappings().all()
    except SQLAlchemyError as exc:
        return {"summary": {}, "items": [], "aging": {}, "warnings": [str(exc)]}

    raw = []
    amounts = [float(row["open_amount"] or 0) for row in rows]
    high_amount = sorted(amounts)[max(0, int(len(amounts) * 0.9) - 1)] if amounts else 0
    aging = defaultdict(float)
    for row in rows:
        due = row["due_date"]
        days = (target - due.date()).days if hasattr(due, "date") else (target - due).days
        bucket_label, bucket_key = _bucket(days)
        amount = float(row["open_amount"] or 0)
        if kind == "receivables":
            level = "Bajo" if days <= 0 else "Medio" if days <= 30 else "Alto"
            if amount >= high_amount and high_amount > 0 and level == "Bajo":
                level = "Medio"
            elif amount >= high_amount and high_amount > 0 and level == "Medio":
                level = "Alto"
            if days > 90:
                level = "Crítico"
            label_key = "risk"
        else:
            level = "Normal" if days < -7 else "Próximo" if days <= 0 else "Vencido"
            if days > 30 or (days > 0 and amount >= high_amount and high_amount > 0):
                level = "Crítico"
            label_key = "payment_priority"

        item = {
            "partner_code": row["partner_code"],
            "partner_name": row["partner_name"],
            "document_number": int(row["document_number"]),
            "document_date": row["document_date"].date().isoformat(),
            "due_date": due.date().isoformat(),
            "currency": row["currency"],
            "document_total": round(float(row["document_total"] or 0), 2),
            "paid_amount": round(float(row["paid_amount"] or 0), 2),
            "open_amount": round(amount, 2),
            "days_overdue": days,
            "aging_bucket": bucket_label,
            label_key: level,
        }
        if partner and partner.lower() not in (
            f"{item['partner_code']} {item['partner_name']}".lower()
        ):
            continue
        if min_amount is not None and amount < min_amount:
            continue
        if days_min is not None and days < days_min:
            continue
        if risk and kind == "receivables" and level.lower() != risk.lower():
            continue
        raw.append(item)
        aging[bucket_key] += amount

    overdue = sum(item["open_amount"] for item in raw if item["days_overdue"] > 0)
    parties = len({item["partner_code"] for item in raw})
    if as_of_date and as_of_date < date.today():
        warnings.append(
            "SAP solo conserva el estado abierto actual; un as_of_date pasado no reconstruye documentos ya cerrados."
        )
    if not raw:
        warnings.append("No hay documentos abiertos para los filtros seleccionados.")
    risk_amount = sum(
        item["open_amount"]
        for item in raw
        if item.get("risk") in ("Alto", "Crítico")
        or item.get("payment_priority") == "Crítico"
    )
    count_key = "open_invoices" if kind == "receivables" else "open_bills"
    party_key = "customers" if kind == "receivables" else "vendors"
    risk_key = "high_risk_amount" if kind == "receivables" else "critical_amount"
    return {
        "as_of_date": target.isoformat(),
        "summary": {
            "open_amount": round(sum(item["open_amount"] for item in raw), 2),
            count_key: len(raw),
            party_key: parties,
            "overdue_amount": round(overdue, 2),
            risk_key: round(risk_amount, 2),
        },
        "items": raw,
        "aging": {
            key: round(aging[key], 2)
            for key in ("not_due", "days_1_30", "days_31_60", "days_61_90", "days_90_plus")
        },
        "warnings": warnings,
    }


def open_receivables(**kwargs: Any) -> dict[str, Any]:
    return _open_items(kind="receivables", partner=kwargs.pop("customer", None), **kwargs)


def open_payables(**kwargs: Any) -> dict[str, Any]:
    return _open_items(kind="payables", partner=kwargs.pop("vendor", None), **kwargs)
