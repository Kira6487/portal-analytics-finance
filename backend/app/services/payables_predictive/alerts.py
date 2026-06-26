from __future__ import annotations

from collections import defaultdict
from typing import Any


def build_alerts(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []
    vendor_overdue_count: defaultdict[str, int] = defaultdict(int)
    vendor_amounts: defaultdict[str, float] = defaultdict(float)
    deficit_amount = 0.0
    for item in items:
        vendor_amounts[item["card_code"]] += item["open_amount"]
        if item["days_overdue"] > 0:
            vendor_overdue_count[item["card_code"]] += 1
        if item["days_overdue"] > 90 or item["risk_level"] == "critical":
            alerts.append(
                {
                    "type": "critical_overdue_payable",
                    "severity": "critical",
                    "message": f"Documento {item['doc_num']} requiere revision prioritaria de pago.",
                    "amount": item["open_amount"],
                    "currency": item["currency"],
                }
            )
        if item.get("in_deficit_week"):
            deficit_amount += item["open_amount"]
        if not item.get("has_history") and item["risk_level"] in ("high", "critical"):
            alerts.append(
                {
                    "type": "vendor_without_history_high_amount",
                    "severity": "high",
                    "message": f"Proveedor {item['card_code']} no tiene historial suficiente y presenta monto relevante.",
                    "amount": item["open_amount"],
                    "currency": item["currency"],
                }
            )
        if item.get("source_currency") != item.get("currency") and item["open_amount"] > 0:
            alerts.append(
                {
                    "type": "foreign_currency_payable",
                    "severity": "medium",
                    "message": f"Documento {item['doc_num']} tiene moneda fuente {item['source_currency']} y se reporta en SOL local SAP.",
                    "amount": item["open_amount"],
                    "currency": item["currency"],
                }
            )

    for code, amount in vendor_amounts.items():
        sample = next(item for item in items if item["card_code"] == code)
        if sample.get("concentration_pct", 0) > 20:
            alerts.append(
                {
                    "type": "vendor_concentration",
                    "severity": "high",
                    "message": f"El proveedor {code} concentra S/ {amount:,.2f} en obligaciones abiertas.",
                    "amount": round(amount, 2),
                    "currency": sample["currency"],
                }
            )
        if vendor_overdue_count[code] >= 3:
            alerts.append(
                {
                    "type": "multiple_overdue_documents",
                    "severity": "high",
                    "message": f"El proveedor {code} tiene varios documentos vencidos.",
                    "amount": round(amount, 2),
                    "currency": sample["currency"],
                }
            )

    if deficit_amount > 0:
        alerts.append(
            {
                "type": "payments_in_deficit_weeks",
                "severity": "high",
                "message": f"Pagos por S/ {deficit_amount:,.2f} caen en semanas deficitarias.",
                "amount": round(deficit_amount, 2),
                "currency": "SOL",
            }
        )
    return alerts[:50]
