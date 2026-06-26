from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Any

from app.services.payables_predictive.dataset import build_predictive_dataset
from app.services.payables_predictive.prioritization import priority_level, validate_priority
from app.services.payables_predictive.risk_scoring import risk_level, validate_risk


def vendor_scores(
    *,
    as_of_date: date | None = None,
    priority: str | None = None,
    risk: str | None = None,
    limit: int = 50,
    scenario: str = "base",
) -> dict[str, Any]:
    validate_priority(priority)
    validate_risk(risk)
    if limit < 1 or limit > 500:
        raise ValueError("limit debe estar entre 1 y 500")
    dataset = build_predictive_dataset(as_of_date=as_of_date, scenario=scenario)
    basis = date.fromisoformat(dataset["as_of_date"])
    grouped: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in dataset["items"]:
        grouped[item["card_code"]].append(item)
    vendors = []
    total = dataset["summary"]["total_open_amount"]
    for code, items in grouped.items():
        amount = sum(item["open_amount"] for item in items)
        weighted_priority = (
            sum(item["payment_priority_score"] * item["open_amount"] for item in items) / amount
            if amount else 0
        )
        weighted_risk = (
            sum(item["risk_score"] * item["open_amount"] for item in items) / amount
            if amount else 0
        )
        vendor_priority = priority_level(weighted_priority)
        vendor_risk = risk_level(weighted_risk)
        if priority and vendor_priority != priority:
            continue
        if risk and vendor_risk != risk:
            continue
        history = max(items, key=lambda item: item["historical_paid_documents"])
        vendors.append(
            {
                "card_code": code,
                "card_name": items[0]["card_name"],
                "open_amount": round(amount, 2),
                "open_documents": len(items),
                "overdue_amount": round(sum(item["open_amount"] for item in items if item["days_overdue"] > 0), 2),
                "overdue_documents": sum(item["days_overdue"] > 0 for item in items),
                "weighted_priority_score": round(weighted_priority, 2),
                "weighted_risk_score": round(weighted_risk, 2),
                "priority_level": vendor_priority,
                "risk_level": vendor_risk,
                "median_payment_delay_days": history["vendor_median_payment_delay_days"],
                "average_payment_delay_days": history["vendor_average_payment_delay_days"],
                "payment_behavior": history["payment_behavior"],
                "amount_due_7d": round(
                    sum(item["open_amount"] for item in items if date.fromisoformat(item["due_date"]) <= basis + timedelta(days=7)),
                    2,
                ),
                "amount_due_30d": round(
                    sum(item["open_amount"] for item in items if date.fromisoformat(item["due_date"]) <= basis + timedelta(days=30)),
                    2,
                ),
                "amount_due_60d": round(
                    sum(item["open_amount"] for item in items if date.fromisoformat(item["due_date"]) <= basis + timedelta(days=60)),
                    2,
                ),
                "amount_due_90d": round(
                    sum(item["open_amount"] for item in items if date.fromisoformat(item["due_date"]) <= basis + timedelta(days=90)),
                    2,
                ),
                "concentration_pct": round(amount / total * 100, 2) if total else 0,
                "cash_pressure_score": round(
                    sum(item["cash_pressure_score"] * item["open_amount"] for item in items) / amount if amount else 0,
                    2,
                ),
                "confidence": history["confidence"],
                "main_reason": max(items, key=lambda item: item["payment_priority_score"])["explanation"],
            }
        )
    vendors.sort(key=lambda item: (item["cash_pressure_score"], item["open_amount"]), reverse=True)
    all_vendors = vendors
    vendors = all_vendors[:limit]
    return {
        "vendors": vendors,
        "summary": {
            "total_open_amount": total,
            "urgent_amount": round(sum(item["open_amount"] for item in all_vendors if item["priority_level"] == "urgent"), 2),
            "high_priority_amount": round(sum(item["open_amount"] for item in all_vendors if item["priority_level"] == "high"), 2),
            "vendors_count": len(all_vendors),
            "returned_vendors": len(vendors),
        },
        "currency": dataset["currency"],
        "currency_symbol": dataset["currency_symbol"],
        "limitations": dataset["limitations"],
        "warnings": dataset["warnings"],
    }
