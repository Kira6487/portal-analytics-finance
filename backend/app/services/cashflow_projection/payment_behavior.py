from __future__ import annotations

from collections import defaultdict
from statistics import mean, median
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import get_connection
from app.core.config import get_settings
from app.queries.cashflow_projection_queries import (
    CUSTOMER_PAYMENT_BEHAVIOR_SQL,
    VENDOR_PAYMENT_BEHAVIOR_SQL,
)


def _behavior_label(delay: float, *, vendor: bool) -> str:
    prefix = "se_paga_" if vendor else ""
    if delay <= 0:
        return f"{prefix}puntual"
    if delay <= 7:
        return f"{prefix}atraso_leve"
    if delay <= 30:
        return f"{prefix}atraso_moderado"
    return f"{prefix}atraso_critico"


def _aggregate(rows, *, vendor: bool) -> list[dict[str, Any]]:
    grouped: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["card_code"])].append(dict(row))
    results = []
    for code, documents in grouped.items():
        delays = [int(row["delay_days"] or 0) for row in documents]
        count = len(documents)
        median_delay = float(median(delays))
        results.append(
            {
                "card_code": code,
                "card_name": next(
                    (row["card_name"] for row in documents if row["card_name"]), None
                ),
                "paid_documents": count,
                "average_delay_days": round(mean(delays), 2),
                "median_delay_days": round(median_delay, 2),
                "total_paid_amount": round(
                    sum(float(row["paid_amount"] or 0) for row in documents), 2
                ),
                "last_payment_date": max(row["payment_date"] for row in documents)
                .date()
                .isoformat(),
                "behavior": _behavior_label(median_delay, vendor=vendor),
                "confidence": "high" if count >= 10 else "medium" if count >= 3 else "low",
            }
        )
    results.sort(key=lambda item: item["total_paid_amount"], reverse=True)
    return results


def get_payment_behavior(
    *, behavior_type: str = "all", limit: int = 50
) -> dict[str, Any]:
    if behavior_type not in ("customers", "vendors", "all"):
        raise ValueError("type debe ser customers, vendors o all")
    if limit < 1 or limit > 5000:
        raise ValueError("limit debe estar entre 1 y 5000")
    warnings = [
        "El atraso se calcula con la última fecha de pago aplicada a cada documento.",
        "Los importes gerenciales usan valores locales SAP y se reportan en SOL.",
    ]
    customers: list[dict[str, Any]] = []
    vendors: list[dict[str, Any]] = []
    try:
        with get_connection() as connection:
            if behavior_type in ("customers", "all"):
                rows = connection.execute(
                    text(CUSTOMER_PAYMENT_BEHAVIOR_SQL)
                ).mappings().all()
                customers = _aggregate(rows, vendor=False)[:limit]
            if behavior_type in ("vendors", "all"):
                rows = connection.execute(
                    text(VENDOR_PAYMENT_BEHAVIOR_SQL)
                ).mappings().all()
                vendors = _aggregate(rows, vendor=True)[:limit]
    except SQLAlchemyError as exc:
        warnings.append(f"No se pudo obtener el historial de pagos: {exc}")
    settings = get_settings()
    return {
        "customers": customers,
        "vendors": vendors,
        "currency": settings.reporting_currency,
        "currency_symbol": settings.reporting_currency_symbol,
        "warnings": warnings,
    }


def behavior_maps() -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], list[str]]:
    result = get_payment_behavior(behavior_type="all", limit=5000)
    return (
        {item["card_code"]: item for item in result["customers"]},
        {item["card_code"]: item for item in result["vendors"]},
        result["warnings"],
    )
