from __future__ import annotations

from datetime import date, timedelta
from typing import Any


def build_alerts(items: list[dict[str, Any]], *, as_of_date: date) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []
    by_customer: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        by_customer.setdefault(item["card_code"], []).append(item)
        if item["aging_bucket"] == "90_plus":
            alerts.append(
                {
                    "type": "critical_90_plus",
                    "severity": "high",
                    "message": f"Documento {item['doc_num']} supera 90 días de vencimiento.",
                    "amount": item["open_amount"],
                    "currency": "SOL",
                }
            )
        if (
            date.fromisoformat(item["estimated_collection_date"])
            > as_of_date + timedelta(weeks=13)
        ):
            alerts.append(
                {
                    "type": "outside_cashflow_horizon",
                    "severity": "medium",
                    "message": f"Documento {item['doc_num']} se cobraría fuera de 13 semanas.",
                    "amount": item["open_amount"],
                    "currency": "SOL",
                }
            )
    for code, documents in by_customer.items():
        concentration = documents[0]["concentration_pct"]
        amount = sum(item["open_amount"] for item in documents)
        if concentration > 20:
            alerts.append(
                {
                    "type": "customer_concentration",
                    "severity": "high",
                    "message": f"El cliente {code} concentra {concentration:.1f}% de la CxC.",
                    "amount": round(amount, 2),
                    "currency": "SOL",
                }
            )
        overdue_count = sum(item["days_overdue"] > 0 for item in documents)
        if overdue_count >= 3:
            alerts.append(
                {
                    "type": "multiple_overdue_documents",
                    "severity": "medium",
                    "message": f"El cliente {code} tiene {overdue_count} documentos vencidos.",
                    "amount": round(
                        sum(item["open_amount"] for item in documents if item["days_overdue"] > 0), 2
                    ),
                    "currency": "SOL",
                }
            )
    high_amount = sum(
        item["open_amount"] for item in items
        if item["risk_level"] in ("high", "critical")
    )
    if high_amount:
        alerts.append(
            {
                "type": "high_risk_receivable",
                "severity": "high",
                "message": "Existe monto relevante en documentos de riesgo alto o crítico.",
                "amount": round(high_amount, 2),
                "currency": "SOL",
            }
        )
    if any(item["in_deficit_week"] for item in items):
        alerts.append(
            {
                "type": "cash_deficit_dependency",
                "severity": "high",
                "message": "Parte de la cobranza esperada coincide con semanas de déficit de caja.",
                "amount": round(
                    sum(item["open_amount"] for item in items if item["in_deficit_week"]), 2
                ),
                "currency": "SOL",
            }
        )
    return alerts
