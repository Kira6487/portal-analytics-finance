from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import get_connection
from app.queries.financial_queries import (
    HISTORICAL_COLLECTIONS_SQL,
    HISTORICAL_PAYMENTS_SQL,
)
from app.queries.payables_queries import OPEN_PAYABLES_SQL
from app.queries.receivables_queries import OPEN_RECEIVABLES_SQL
from app.services.financial_statements import resolve_dates


def _key(value: date, bucket: str) -> str:
    value = value.date() if hasattr(value, "date") else value
    if bucket == "week":
        iso = value.isocalendar()
        return f"{iso.year}-W{iso.week:02d}"
    return value.strftime("%Y-%m")


def cashflow_base(
    *, date_from: date | None = None, date_to: date | None = None, bucket: str = "week"
) -> dict[str, Any]:
    if bucket not in ("week", "month"):
        raise ValueError("bucket debe ser week o month")
    start, end = resolve_dates(date_from=date_from, date_to=date_to)
    periods: defaultdict[str, dict[str, float]] = defaultdict(
        lambda: {
            "collections": 0.0,
            "payments": 0.0,
            "expected_collections": 0.0,
            "expected_payments": 0.0,
        }
    )
    warnings = [
        "Caja inicial no determinada: el flujo muestra movimientos y no saldo bancario conciliado.",
        "Cobros y pagos esperados usan documentos que permanecen abiertos actualmente; no reconstruyen snapshots históricos.",
    ]
    try:
        with get_connection() as connection:
            params = {"date_from": start, "date_to": end, "as_of_date": end}
            collections = connection.execute(
                text(HISTORICAL_COLLECTIONS_SQL), params
            ).mappings()
            for row in collections:
                periods[_key(row["movement_date"], bucket)]["collections"] += float(
                    row["amount"] or 0
                )
            payments = connection.execute(
                text(HISTORICAL_PAYMENTS_SQL), params
            ).mappings()
            for row in payments:
                periods[_key(row["movement_date"], bucket)]["payments"] += float(
                    row["amount"] or 0
                )
            for row in connection.execute(
                text(OPEN_RECEIVABLES_SQL), params
            ).mappings():
                due = row["due_date"]
                if start <= due.date() <= end:
                    periods[_key(due, bucket)]["expected_collections"] += float(
                        row["open_amount"] or 0
                    )
            for row in connection.execute(text(OPEN_PAYABLES_SQL), params).mappings():
                due = row["due_date"]
                if start <= due.date() <= end:
                    periods[_key(due, bucket)]["expected_payments"] += float(
                        row["open_amount"] or 0
                    )
    except SQLAlchemyError as exc:
        return {"filters": {}, "summary": {}, "periods": [], "warnings": [str(exc)]}

    items = []
    for period in sorted(periods):
        values = periods[period]
        net = (
            values["collections"] - values["payments"]
            + values["expected_collections"] - values["expected_payments"]
        )
        items.append(
            {
                "period": period,
                **{key: round(value, 2) for key, value in values.items()},
                "net_cashflow": round(net, 2),
            }
        )
    summary = {
        "historical_collections": round(sum(p["collections"] for p in items), 2),
        "historical_payments": round(sum(p["payments"] for p in items), 2),
        "expected_collections": round(sum(p["expected_collections"] for p in items), 2),
        "expected_payments": round(sum(p["expected_payments"] for p in items), 2),
        "net_cashflow": round(sum(p["net_cashflow"] for p in items), 2),
        "estimated_cash": None,
    }
    return {
        "filters": {"bucket": bucket, "date_from": start.isoformat(), "date_to": end.isoformat()},
        "summary": summary,
        "periods": items,
        "warnings": warnings,
    }
