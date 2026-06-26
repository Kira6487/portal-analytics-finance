from __future__ import annotations

from typing import Any


def build_recommendations(items: list[dict[str, Any]]) -> list[str]:
    recommendations: list[str] = []
    if any(item["payment_priority_level"] == "urgent" and item["days_overdue"] > 0 for item in items):
        recommendations.append("Priorizar revision de documentos urgentes vencidos con Tesoreria.")
    if any(item.get("in_deficit_week") for item in items):
        recommendations.append("Revisar calendario de pagos en semanas deficitarias antes de ejecutar desembolsos.")
    if any(item.get("concentration_pct", 0) > 20 for item in items):
        recommendations.append("Dar seguimiento directo a proveedores concentradores y evaluar negociacion de condiciones.")
    if any(item.get("can_consider_deferral") for item in items):
        recommendations.append("Evaluar negociacion de plazo para pagos revisables; no postergar automaticamente.")
    if any(item.get("source_currency") != item.get("currency") for item in items):
        recommendations.append("Validar politica FX productiva para documentos con moneda fuente distinta de SOL.")
    if any(not item.get("has_history") for item in items):
        recommendations.append("Validar manualmente proveedores sin historial suficiente.")
    if any(item["risk_level"] == "critical" and item.get("in_deficit_week") for item in items):
        recommendations.append("Revisar cobranza prioritaria en CxC y pagos no criticos cuando existan pagos criticos con caja insuficiente.")
    if not recommendations:
        recommendations.append("Mantener monitoreo semanal de vencimientos, concentracion y caja proyectada.")
    return recommendations
