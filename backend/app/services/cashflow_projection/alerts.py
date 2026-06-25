from __future__ import annotations

from typing import Any


def build_alerts(
    *,
    weeks: list[dict[str, Any]],
    receivables: list[dict[str, Any]],
    payables: list[dict[str, Any]],
    top_customers: list[dict[str, Any]],
    top_vendors: list[dict[str, Any]],
    opening_cash_source: str,
    scenario: str,
) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []
    deficit = [week for week in weeks if week["projected_cash_balance"] < 0]
    if deficit:
        first = deficit[0]
        alerts.append(
            {
                "type": "cash_deficit",
                "severity": "high",
                "period": first["period"],
                "message": "La caja proyectada cae por debajo de cero.",
                "amount": first["projected_cash_balance"],
            }
        )
    if weeks:
        pressure = min(weeks, key=lambda week: week["net_cashflow"])
        alerts.append(
            {
                "type": "largest_net_outflow",
                "severity": "medium",
                "period": pressure["period"],
                "message": "Semana con mayor salida neta proyectada.",
                "amount": pressure["net_cashflow"],
            }
        )
    total_collections = sum(item["open_amount"] for item in receivables)
    top_collection = sum(item["amount"] for item in top_customers[:3])
    if total_collections and top_collection / total_collections > 0.5:
        alerts.append(
            {
                "type": "collection_concentration",
                "severity": "medium",
                "period": None,
                "message": "Más del 50% de la cobranza se concentra en tres clientes.",
                "amount": round(top_collection, 2),
            }
        )
    total_payments = sum(item["open_amount"] for item in payables)
    top_payment = sum(item["amount"] for item in top_vendors[:3])
    if total_payments and top_payment / total_payments > 0.5:
        alerts.append(
            {
                "type": "payment_concentration",
                "severity": "medium",
                "period": None,
                "message": "Más del 50% de los pagos se concentra en tres proveedores.",
                "amount": round(top_payment, 2),
            }
        )
    overdue_receivables = sum(
        item["open_amount"] for item in receivables if item["risk"] in ("medium", "high")
    )
    if overdue_receivables > total_collections * 0.25:
        alerts.append(
            {
                "type": "overdue_receivables",
                "severity": "high",
                "period": None,
                "message": "La CxC vencida representa una porción relevante de la cobranza.",
                "amount": round(overdue_receivables, 2),
            }
        )
    overdue_payables = sum(
        item["open_amount"] for item in payables if item["priority"] in ("overdue", "critical")
    )
    if overdue_payables > total_payments * 0.25:
        alerts.append(
            {
                "type": "overdue_payables",
                "severity": "high",
                "period": None,
                "message": "La CxP vencida representa una presión inmediata de caja.",
                "amount": round(overdue_payables, 2),
            }
        )
    if opening_cash_source == "zero_default":
        alerts.append(
            {
                "type": "opening_cash_unreliable",
                "severity": "high",
                "period": None,
                "message": "No se identificó caja inicial; se utilizó cero.",
                "amount": 0,
            }
        )
    foreign_amount = sum(
        item["open_amount"] for item in receivables + payables
        if item.get("currency") != "SOL"
    )
    if foreign_amount:
        alerts.append(
            {
                "type": "foreign_currency_exposure",
                "severity": "medium",
                "period": None,
                "message": "Existen documentos fuente en moneda distinta de SOL.",
                "amount": round(foreign_amount, 2),
            }
        )
    if scenario == "pessimistic" and deficit:
        alerts.append(
            {
                "type": "pessimistic_deficit",
                "severity": "high",
                "period": deficit[0]["period"],
                "message": "El escenario pesimista genera semanas con déficit.",
                "amount": min(week["projected_cash_balance"] for week in deficit),
            }
        )
    return alerts
