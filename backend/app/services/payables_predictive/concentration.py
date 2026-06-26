from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any

from app.services.payables_predictive.dataset import build_predictive_dataset
from app.services.payables_predictive.explanations import build_explanations
from app.services.payables_predictive.recommendations import build_recommendations


def concentration_analysis(
    *, as_of_date: date | None = None, scenario: str = "base"
) -> dict[str, Any]:
    dataset = build_predictive_dataset(as_of_date=as_of_date, scenario=scenario)
    grouped: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    weekly_pressure: defaultdict[str, float] = defaultdict(float)
    for item in dataset["items"]:
        grouped[item["card_code"]].append(item)
        weekly_pressure[item["cashflow_week"]] += item["open_amount"]
    total = dataset["summary"]["total_open_amount"]
    vendors = []
    for code, items in grouped.items():
        amount = sum(item["open_amount"] for item in items)
        concentration_pct = amount / total * 100 if total else 0
        urgent_amount = sum(
            item["open_amount"] for item in items if item["payment_priority_level"] == "urgent"
        )
        overdue_amount = sum(item["open_amount"] for item in items if item["days_overdue"] > 0)
        vendors.append(
            {
                "card_code": code,
                "card_name": items[0]["card_name"],
                "open_amount": round(amount, 2),
                "concentration_pct": round(concentration_pct, 2),
                "urgent_amount": round(urgent_amount, 2),
                "overdue_amount": round(overdue_amount, 2),
                "documents": len(items),
                "dependency_risk": "high" if concentration_pct > 20 else "medium" if concentration_pct > 10 else "low",
                "cash_pressure_score": round(
                    sum(item["cash_pressure_score"] * item["open_amount"] for item in items) / amount if amount else 0,
                    2,
                ),
            }
        )
    vendors.sort(key=lambda item: item["open_amount"], reverse=True)
    top5 = sum(item["open_amount"] for item in vendors[:5]) / total * 100 if total else 0
    top10 = sum(item["open_amount"] for item in vendors[:10]) / total * 100 if total else 0
    concentration_risk = "high" if top5 > 60 else "medium" if top5 > 40 else "low"
    pressure = [
        {"cashflow_week": week, "payments_amount": round(amount, 2)}
        for week, amount in sorted(weekly_pressure.items(), key=lambda pair: pair[1], reverse=True)
    ][:10]
    return {
        "summary": {
            "total_open_amount": total,
            "top_5_concentration_pct": round(top5, 2),
            "top_10_concentration_pct": round(top10, 2),
            "concentration_risk": concentration_risk,
        },
        "top_vendors": vendors[:10],
        "weekly_pressure": pressure,
        "explanations": build_explanations(dataset["items"], top5),
        "recommendations": build_recommendations(dataset["items"]),
        "currency": dataset["currency"],
        "currency_symbol": dataset["currency_symbol"],
        "limitations": dataset["limitations"],
        "warnings": dataset["warnings"],
    }
