from __future__ import annotations

from typing import Any


def build_explanations(
    items: list[dict[str, Any]], concentration_pct: float
) -> list[str]:
    history_coverage = (
        sum(item["open_amount"] for item in items if item["has_history"])
        / sum(item["open_amount"] for item in items)
        * 100
        if items and sum(item["open_amount"] for item in items) else 0
    )
    return [
        "El riesgo combina días vencidos, monto pendiente, historial de atraso, "
        "concentración e impacto en caja.",
        "La fecha estimada usa vencimiento más la mediana histórica de atraso del cliente.",
        f"El top 5 de clientes concentra {concentration_pct:.1f}% de la cartera.",
        f"{history_coverage:.1f}% del monto analizado tiene historial de cobranza identificado.",
        "La moneda oficial de reporte fue definida como Soles / SOL para esta demo.",
    ]
