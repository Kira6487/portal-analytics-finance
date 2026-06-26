from __future__ import annotations

from datetime import date
from typing import Any

from app.services.payables_predictive.alerts import build_alerts
from app.services.payables_predictive.concentration import concentration_analysis
from app.services.payables_predictive.dataset import build_predictive_dataset
from app.services.payables_predictive.explanations import build_explanations
from app.services.payables_predictive.prioritization import compact_priority_reason
from app.services.payables_predictive.recommendations import build_recommendations


def payment_priorities(
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
            "doc_num": item["doc_num"],
            "card_code": item["card_code"],
            "card_name": item["card_name"],
            "open_amount": item["open_amount"],
            "due_date": item["due_date"],
            "days_overdue": item["days_overdue"],
            "estimated_payment_date": item["estimated_payment_date"],
            "recommended_payment_date": item["recommended_payment_date"],
            "payment_priority_score": item["payment_priority_score"],
            "payment_priority_level": item["payment_priority_level"],
            "risk_level": item["risk_level"],
            "can_consider_deferral": item["can_consider_deferral"],
            "reason": compact_priority_reason(item),
        }
        for item in items
    ]
    all_items = dataset["items"]
    return {
        "summary": {
            "urgent_documents": sum(item["payment_priority_level"] == "urgent" for item in all_items),
            "urgent_amount": round(sum(item["open_amount"] for item in all_items if item["payment_priority_level"] == "urgent"), 2),
            "high_priority_documents": sum(item["payment_priority_level"] == "high" for item in all_items),
            "high_priority_amount": round(sum(item["open_amount"] for item in all_items if item["payment_priority_level"] == "high"), 2),
            "deferrable_documents": sum(item["can_consider_deferral"] for item in all_items),
            "deferrable_amount": round(sum(item["open_amount"] for item in all_items if item["can_consider_deferral"]), 2),
        },
        "items": compact,
        "recommendations": build_recommendations(all_items),
        "currency": dataset["currency"],
        "currency_symbol": dataset["currency_symbol"],
        "limitations": dataset["limitations"],
        "warnings": dataset["warnings"],
    }


def deferrable_payments(
    *,
    as_of_date: date | None = None,
    limit: int = 20,
    scenario: str = "base",
) -> dict[str, Any]:
    if limit < 1 or limit > 500:
        raise ValueError("limit debe estar entre 1 y 500")
    dataset = build_predictive_dataset(as_of_date=as_of_date, scenario=scenario)
    candidates = [
        item for item in dataset["items"] if item["can_consider_deferral"]
    ]
    candidates.sort(key=lambda item: (item["open_amount"], item["cash_pressure_score"]), reverse=True)
    items = [
        {
            "doc_num": item["doc_num"],
            "card_code": item["card_code"],
            "card_name": item["card_name"],
            "open_amount": item["open_amount"],
            "due_date": item["due_date"],
            "cashflow_week": item["cashflow_week"],
            "priority_level": item["payment_priority_level"],
            "risk_level": item["risk_level"],
            "reason": item["deferral_reason"],
        }
        for item in candidates[:limit]
    ]
    return {
        "summary": {
            "deferrable_documents": len(candidates),
            "deferrable_amount": round(sum(item["open_amount"] for item in candidates), 2),
            "potential_cash_relief": round(sum(item["open_amount"] for item in candidates), 2),
        },
        "items": items,
        "limitations": dataset["limitations"]
        + ["La postergacion requiere validacion de Tesoreria y negociacion con proveedor."],
        "currency": dataset["currency"],
        "currency_symbol": dataset["currency_symbol"],
        "warnings": dataset["warnings"],
    }


def executive_summary(
    *, as_of_date: date | None = None, scenario: str = "base"
) -> dict[str, Any]:
    dataset = build_predictive_dataset(as_of_date=as_of_date, scenario=scenario)
    concentration = concentration_analysis(as_of_date=as_of_date, scenario=scenario)
    items = dataset["items"]
    summary = dataset["summary"]
    alerts = build_alerts(items)
    history_amount = sum(item["open_amount"] for item in items if item["has_history"])
    history_pct = history_amount / summary["total_open_amount"] * 100 if summary["total_open_amount"] else 0
    foreign_docs = summary["foreign_currency_documents"]
    confidence = (
        "high" if history_pct > 70 and foreign_docs == 0
        else "medium" if history_pct >= 40
        else "low"
    )
    text = (
        f"Las obligaciones por pagar analizadas ascienden a S/ {summary['total_open_amount']:,.2f}. "
        f"El monto urgente es S/ {summary['urgent_amount']:,.2f}, el monto vencido es "
        f"S/ {summary['overdue_amount']:,.2f} y el monto revisable asciende a "
        f"S/ {summary['deferrable_amount']:,.2f}."
    )
    return {
        "title": "Analisis predictivo de cuentas por pagar",
        "summary": text,
        "key_findings": build_explanations(
            items, concentration["summary"]["top_5_concentration_pct"]
        ),
        "risks": [alert["message"] for alert in alerts[:20]],
        "recommended_actions": build_recommendations(items),
        "confidence": confidence,
        "currency": dataset["currency"],
        "currency_symbol": dataset["currency_symbol"],
        "limitations": dataset["limitations"],
        "warnings": dataset["warnings"],
    }
