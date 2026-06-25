from __future__ import annotations

from typing import Any


def priority_level(score: float) -> str:
    if score < 25:
        return "low"
    if score < 50:
        return "medium"
    if score < 75:
        return "high"
    return "urgent"


def calculate_priority(item: dict[str, Any], average_amount: float) -> tuple[float, str]:
    score = item["risk_score"] * 0.55
    if average_amount and item["open_amount"] > average_amount * 1.5:
        score += 15
    if item["days_overdue"] > 90:
        score += 15
    elif item["days_overdue"] > 30:
        score += 10
    elif item["days_overdue"] > 0:
        score += 5
    if item["in_deficit_week"]:
        score += 15
    if item["concentration_pct"] > 20:
        score += 10
    if not item["has_history"]:
        score += 5
    score = round(min(100, max(0, score)), 2)
    reasons = []
    if item["days_overdue"] > 0:
        reasons.append("documento vencido")
    if item["risk_level"] in ("high", "critical"):
        reasons.append("riesgo elevado")
    if item["open_amount"] > average_amount * 1.5:
        reasons.append("monto alto")
    if item["in_deficit_week"]:
        reasons.append("impacta semana con déficit")
    return score, ", ".join(reasons).capitalize() or "Prioridad calculada por reglas."
