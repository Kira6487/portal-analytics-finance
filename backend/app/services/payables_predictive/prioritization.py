from __future__ import annotations

from typing import Any

from app.models.payables_predictive_schemas import PRIORITY_LEVELS


def priority_level(score: float) -> str:
    if score < 25:
        return "low"
    if score < 50:
        return "medium"
    if score < 75:
        return "high"
    return "urgent"


def validate_priority(value: str | None) -> None:
    if value and value not in PRIORITY_LEVELS:
        raise ValueError("priority debe ser low, medium, high o urgent")


def calculate_payment_priority(
    *,
    days_overdue: int,
    days_until_due: int,
    open_amount: float,
    average_amount: float,
    concentration_pct: float,
    in_deficit_week: bool,
    has_history: bool,
    payment_behavior: str,
    vendor_pressure_score: float,
    document_age_days: int,
) -> tuple[float, list[str]]:
    reasons: list[str] = []
    if days_overdue > 90:
        score = 90
        reasons.append("Documento vencido por mas de 90 dias.")
    elif days_overdue > 60:
        score = 80
        reasons.append("Documento vencido entre 61 y 90 dias.")
    elif days_overdue > 30:
        score = 65
        reasons.append("Documento vencido entre 31 y 60 dias.")
    elif days_overdue > 0:
        score = 50
        reasons.append("Documento vencido entre 1 y 30 dias.")
    elif days_until_due <= 7:
        score = 35
        reasons.append("Documento vence dentro de los proximos 7 dias.")
    elif days_until_due <= 30:
        score = 20
        reasons.append("Documento vence dentro de 15 a 30 dias.")
    else:
        score = 10
        reasons.append("Documento no vencido con vencimiento mayor a 30 dias.")

    if average_amount > 0 and open_amount > average_amount:
        score += 10
        reasons.append("Monto pendiente alto frente al promedio de CxP.")
    if concentration_pct > 20:
        score += 15
        reasons.append("Proveedor concentra mas del 20% de CxP.")
    if in_deficit_week:
        score += 15
        reasons.append("Pago cae en una semana con deficit de caja.")
    if not has_history:
        score += 5
        reasons.append("Proveedor sin historial suficiente.")
    if payment_behavior in ("pago_puntual", "atraso_leve") or vendor_pressure_score >= 60:
        score += 10
        reasons.append("Proveedor recurrente o con presion acumulada relevante.")
    if document_age_days > 180 and days_overdue > 0:
        score += 5
        reasons.append("Documento con antiguedad superior a 180 dias.")

    return round(min(100, max(0, score)), 2), reasons


def compact_priority_reason(item: dict[str, Any]) -> str:
    reasons = []
    if item["days_overdue"] > 0:
        reasons.append("documento vencido")
    if item["open_amount"] > 0 and item.get("concentration_pct", 0) > 20:
        reasons.append("proveedor concentrador")
    if item.get("in_deficit_week"):
        reasons.append("semana con deficit")
    if item["payment_priority_level"] in ("urgent", "high"):
        reasons.append("prioridad elevada")
    return ", ".join(reasons).capitalize() + "." if reasons else item["explanation"]
