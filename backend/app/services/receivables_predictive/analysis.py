from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any

from app.services.receivables_predictive.alerts import build_alerts
from app.services.receivables_predictive.customer_scoring import customer_scores
from app.services.receivables_predictive.dataset import build_predictive_dataset
from app.services.receivables_predictive.explanations import build_explanations
from app.services.receivables_predictive.recommendations import build_recommendations


def collection_priorities(
    *,
    as_of_date: date | None = None,
    limit: int = 20,
    scenario: str = "base",
) -> dict[str, Any]:
    if limit < 1 or limit > 500:
        raise ValueError("limit debe estar entre 1 y 500")
    dataset = build_predictive_dataset(as_of_date=as_of_date, scenario=scenario)
    items = dataset["items"][:limit]
    compact = [
        {
            "doc_entry": item["doc_entry"],
            "doc_num": item["doc_num"],
            "card_code": item["card_code"],
            "card_name": item["card_name"],
            "open_amount": item["open_amount"],
            "due_date": item["due_date"],
            "days_overdue": item["days_overdue"],
            "estimated_collection_date": item["estimated_collection_date"],
            "risk_level": item["risk_level"],
            "priority_score": item["priority_score"],
            "priority_level": item["priority_level"],
            "reason": item["priority_reason"],
        }
        for item in items
    ]
    return {
        "summary": {
            "urgent_documents": sum(item["priority_level"] == "urgent" for item in items),
            "urgent_amount": round(
                sum(item["open_amount"] for item in items if item["priority_level"] == "urgent"), 2
            ),
            "high_priority_documents": sum(item["priority_level"] == "high" for item in items),
            "high_priority_amount": round(
                sum(item["open_amount"] for item in items if item["priority_level"] == "high"), 2
            ),
        },
        "items": compact,
        "recommendations": build_recommendations(dataset["items"]),
        "currency": dataset["currency"],
        "currency_symbol": dataset["currency_symbol"],
        "limitations": dataset["limitations"],
        "warnings": dataset["warnings"],
    }


def concentration_analysis(
    *, as_of_date: date | None = None, scenario: str = "base"
) -> dict[str, Any]:
    dataset = build_predictive_dataset(as_of_date=as_of_date, scenario=scenario)
    grouped: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in dataset["items"]:
        grouped[item["card_code"]].append(item)
    total = dataset["summary"]["open_amount"]
    customers = []
    for code, items in grouped.items():
        amount = sum(item["open_amount"] for item in items)
        customers.append(
            {
                "card_code": code,
                "card_name": items[0]["card_name"],
                "open_amount": round(amount, 2),
                "concentration_pct": round(amount / total * 100, 2) if total else 0,
                "high_risk_amount": round(
                    sum(item["open_amount"] for item in items if item["risk_level"] == "high"), 2
                ),
                "critical_risk_amount": round(
                    sum(item["open_amount"] for item in items if item["risk_level"] == "critical"), 2
                ),
                "documents": len(items),
            }
        )
    customers.sort(key=lambda item: item["open_amount"], reverse=True)
    top5 = sum(item["open_amount"] for item in customers[:5]) / total * 100 if total else 0
    top10 = sum(item["open_amount"] for item in customers[:10]) / total * 100 if total else 0
    concentration_risk = "high" if top5 > 60 else "medium" if top5 > 40 else "low"
    return {
        "summary": {
            "total_open_amount": total,
            "top_5_concentration_pct": round(top5, 2),
            "top_10_concentration_pct": round(top10, 2),
            "concentration_risk": concentration_risk,
        },
        "top_customers": customers[:10],
        "explanations": build_explanations(dataset["items"], top5),
        "recommendations": build_recommendations(dataset["items"]),
        "currency": dataset["currency"],
        "currency_symbol": dataset["currency_symbol"],
        "limitations": dataset["limitations"],
        "warnings": dataset["warnings"],
    }


def executive_summary(
    *, as_of_date: date | None = None, scenario: str = "base"
) -> dict[str, Any]:
    dataset = build_predictive_dataset(as_of_date=as_of_date, scenario=scenario)
    concentration = concentration_analysis(as_of_date=as_of_date, scenario=scenario)
    alerts = build_alerts(
        dataset["items"], as_of_date=date.fromisoformat(dataset["as_of_date"])
    )
    summary = dataset["summary"]
    history_amount = sum(
        item["open_amount"] for item in dataset["items"] if item["has_history"]
    )
    history_pct = history_amount / summary["open_amount"] * 100 if summary["open_amount"] else 0
    foreign = summary["foreign_currency_documents"]
    confidence = (
        "high" if history_pct > 70 and foreign == 0
        else "medium" if history_pct >= 40
        else "low"
    )
    text = (
        f"La cartera abierta analizada asciende a S/ {summary['open_amount']:,.2f}. "
        f"El monto de riesgo alto es S/ {summary['high_risk_amount']:,.2f} y el "
        f"monto crítico es S/ {summary['critical_risk_amount']:,.2f}."
    )
    return {
        "title": "Análisis predictivo de cuentas por cobrar",
        "summary": text,
        "key_findings": build_explanations(
            dataset["items"], concentration["summary"]["top_5_concentration_pct"]
        ),
        "risks": [alert["message"] for alert in alerts[:20]],
        "recommended_actions": build_recommendations(dataset["items"]),
        "confidence": confidence,
        "currency": dataset["currency"],
        "currency_symbol": dataset["currency_symbol"],
        "limitations": dataset["limitations"],
        "warnings": dataset["warnings"],
    }
