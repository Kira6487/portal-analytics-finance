from __future__ import annotations

from typing import Any

from app.models.payables_predictive_schemas import RISK_LEVELS


def risk_level(score: float) -> str:
    if score < 25:
        return "low"
    if score < 50:
        return "medium"
    if score < 75:
        return "high"
    return "critical"


def validate_risk(value: str | None) -> None:
    if value and value not in RISK_LEVELS:
        raise ValueError("risk debe ser low, medium, high o critical")


def score_payable_risk(
    *,
    days_overdue: int,
    open_amount: float,
    average_amount: float,
    concentration_pct: float,
    in_deficit_week: bool,
    has_history: bool,
    source_currency: str | None,
    reporting_currency: str,
    vendor_pressure_score: float,
) -> tuple[float, list[str]]:
    reasons: list[str] = []
    if days_overdue <= 0:
        score = 10
    elif days_overdue <= 30:
        score = 35
        reasons.append("Pago vencido entre 1 y 30 dias.")
    elif days_overdue <= 60:
        score = 50
        reasons.append("Pago vencido entre 31 y 60 dias.")
    elif days_overdue <= 90:
        score = 70
        reasons.append("Pago vencido entre 61 y 90 dias.")
    else:
        score = 85
        reasons.append("Pago vencido por mas de 90 dias.")

    if average_amount > 0 and open_amount > average_amount * 1.5:
        score += 10
        reasons.append("Monto pendiente superior al promedio de CxP.")
    if concentration_pct > 20:
        score += 15
        reasons.append("Proveedor concentra mas del 20% de la obligacion abierta.")
    if in_deficit_week:
        score += 15
        reasons.append("Pago coincide con semana de deficit de caja.")
    if not has_history:
        score += 10
        reasons.append("Proveedor sin historial suficiente.")
    if source_currency and source_currency != reporting_currency and open_amount > average_amount:
        score += 10
        reasons.append("Monto alto con moneda fuente distinta de SOL sin politica FX productiva.")
    if vendor_pressure_score >= 70:
        score += 10
        reasons.append("Alta presion acumulada por proveedor.")

    return round(min(100, max(0, score)), 2), reasons


def confidence_for_document(item: dict[str, Any]) -> tuple[str, list[str]]:
    count = int(item.get("historical_paid_documents") or 0)
    source_currency = item.get("source_currency")
    reasons = [f"Proveedor con {count} documentos historicos pagados."]
    if item.get("due_date"):
        reasons.append("Fecha de vencimiento valida.")
    else:
        reasons.append("Falta fecha de vencimiento.")
        return "low", reasons
    if source_currency and source_currency != "SOL":
        reasons.append(
            f"Documento fuente en {source_currency}; no hay conversion FX productiva."
        )
        return "low", reasons
    reasons.append("Documento reportado en moneda oficial SOL.")
    if count > 10:
        return "high", reasons
    if count >= 3:
        return "medium", reasons
    return "low", reasons
