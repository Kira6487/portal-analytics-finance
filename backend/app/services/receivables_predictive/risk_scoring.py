from __future__ import annotations

from typing import Any


RISK_LEVELS = ("low", "medium", "high", "critical")


def risk_level(score: float) -> str:
    if score < 25:
        return "low"
    if score < 50:
        return "medium"
    if score < 75:
        return "high"
    return "critical"


def score_receivable(
    *,
    days_overdue: int,
    open_amount: float,
    average_amount: float,
    behavior: str,
    concentration_pct: float,
    has_history: bool,
    in_deficit_week: bool,
    document_age_days: int,
) -> tuple[float, list[str]]:
    reasons: list[str] = []
    if days_overdue <= 0:
        score = 5 if days_overdue < -30 else 15
    elif days_overdue <= 30:
        score = 25
        reasons.append("Documento vencido entre 1 y 30 días.")
    elif days_overdue <= 60:
        score = 45
        reasons.append("Documento vencido entre 31 y 60 días.")
    elif days_overdue <= 90:
        score = 65
        reasons.append("Documento vencido entre 61 y 90 días.")
    else:
        score = 80
        reasons.append("Documento vencido por más de 90 días.")

    if "critico" in behavior:
        score += 30
        reasons.append("Cliente con atraso histórico crítico.")
    elif "moderado" in behavior:
        score += 20
        reasons.append("Cliente con atraso histórico moderado.")
    elif "leve" in behavior:
        score += 10
        reasons.append("Cliente con atraso histórico leve.")
    if average_amount > 0 and open_amount > average_amount * 1.5:
        score += 10
        reasons.append("Monto superior al promedio de la cartera.")
    if concentration_pct > 20:
        score += 15
        reasons.append("Cliente concentra más del 20% de la cartera.")
    if not has_history:
        score += 10
        reasons.append("Cliente sin historial suficiente.")
    if in_deficit_week:
        score += 15
        reasons.append("Cobranza estimada dentro de una semana con déficit.")
    if document_age_days > 180 and days_overdue > 0:
        score += 5
        reasons.append("Documento con antigüedad superior a 180 días.")
    return float(min(100, max(0, score))), reasons


def confidence_for_document(item: dict[str, Any]) -> tuple[str, list[str]]:
    count = int(item.get("historical_paid_documents") or 0)
    source_currency = item.get("source_currency")
    reasons = [f"Cliente con {count} documentos históricos pagados."]
    if item.get("due_date"):
        reasons.append("Documento con fecha de vencimiento válida.")
    if source_currency != "SOL":
        reasons.append(
            f"Documento fuente en {source_currency}; no hay conversión FX productiva."
        )
        return "low", reasons
    if count > 10:
        return "high", reasons
    if count >= 3:
        return "medium", reasons
    return "low", reasons
