from __future__ import annotations

from typing import Any


def build_recommendations(items: list[dict[str, Any]]) -> list[str]:
    recommendations = []
    if any(item["risk_level"] == "critical" for item in items):
        recommendations.append("Priorizar gestión inmediata de documentos críticos.")
    if any(item["concentration_pct"] > 20 for item in items):
        recommendations.append("Realizar seguimiento directo a clientes concentradores.")
    if any(item["in_deficit_week"] for item in items):
        recommendations.append(
            "Priorizar cobranzas que sostienen semanas con déficit de caja."
        )
    if any(not item["has_history"] and item["priority_level"] in ("high", "urgent") for item in items):
        recommendations.append(
            "Validar manualmente documentos de monto alto sin historial suficiente."
        )
    if any(item["aging_bucket"] == "90_plus" for item in items):
        recommendations.append(
            "Evaluar provisión, cobranza legal o revisión contable para documentos 90+, sin automatizar acciones."
        )
    if any(item["source_currency"] != "SOL" for item in items):
        recommendations.append(
            "Validar la conversión a SOL de documentos fuente en moneda extranjera."
        )
    return recommendations
