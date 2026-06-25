from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Any

from app.services.receivables_predictive.dataset import build_predictive_dataset
from app.services.receivables_predictive.risk_scoring import RISK_LEVELS, risk_level


def customer_scores(
    *,
    as_of_date: date | None = None,
    risk: str | None = None,
    limit: int = 50,
    scenario: str = "base",
) -> dict[str, Any]:
    if risk and risk not in RISK_LEVELS:
        raise ValueError("risk debe ser low, medium, high o critical")
    if limit < 1 or limit > 500:
        raise ValueError("limit debe estar entre 1 y 500")
    dataset = build_predictive_dataset(as_of_date=as_of_date, scenario=scenario)
    basis = date.fromisoformat(dataset["as_of_date"])
    grouped: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in dataset["items"]:
        grouped[item["card_code"]].append(item)
    customers = []
    total = dataset["summary"]["open_amount"]
    for code, items in grouped.items():
        open_amount = sum(item["open_amount"] for item in items)
        weighted = (
            sum(item["risk_score"] * item["open_amount"] for item in items) / open_amount
            if open_amount else 0
        )
        level = risk_level(weighted)
        if risk and level != risk:
            continue
        history = max(items, key=lambda item: item["historical_paid_documents"])
        customers.append(
            {
                "card_code": code,
                "card_name": items[0]["card_name"],
                "open_amount": round(open_amount, 2),
                "open_documents": len(items),
                "overdue_amount": round(
                    sum(item["open_amount"] for item in items if item["days_overdue"] > 0), 2
                ),
                "overdue_documents": sum(item["days_overdue"] > 0 for item in items),
                "weighted_risk_score": round(weighted, 2),
                "risk_level": level,
                "median_delay_days": history["customer_median_delay_days"],
                "average_delay_days": history["customer_average_delay_days"],
                "collection_behavior": history["collection_behavior"],
                "estimated_collection_amount_30d": round(
                    sum(
                        item["open_amount"] for item in items
                        if date.fromisoformat(item["estimated_collection_date"])
                        <= basis + timedelta(days=30)
                    ), 2
                ),
                "estimated_collection_amount_60d": round(
                    sum(
                        item["open_amount"] for item in items
                        if date.fromisoformat(item["estimated_collection_date"])
                        <= basis + timedelta(days=60)
                    ), 2
                ),
                "estimated_collection_amount_90d": round(
                    sum(
                        item["open_amount"] for item in items
                        if date.fromisoformat(item["estimated_collection_date"])
                        <= basis + timedelta(days=90)
                    ), 2
                ),
                "concentration_pct": round(open_amount / total * 100, 2) if total else 0,
                "priority_level": max(
                    items,
                    key=lambda item: item["priority_score"],
                )["priority_level"],
                "confidence": history["confidence"],
                "main_reason": max(items, key=lambda item: item["risk_score"])["explanation"],
            }
        )
    customers.sort(
        key=lambda item: (item["weighted_risk_score"], item["open_amount"]), reverse=True
    )
    all_customers = customers
    customers = all_customers[:limit]
    return {
        "customers": customers,
        "summary": {
            "total_open_amount": total,
            "high_risk_amount": round(
                sum(item["open_amount"] for item in all_customers if item["risk_level"] == "high"), 2
            ),
            "critical_risk_amount": round(
                sum(item["open_amount"] for item in all_customers if item["risk_level"] == "critical"), 2
            ),
            "customers_count": len(all_customers),
            "returned_customers": len(customers),
        },
        "currency": dataset["currency"],
        "currency_symbol": dataset["currency_symbol"],
        "limitations": dataset["limitations"],
        "warnings": dataset["warnings"],
    }
