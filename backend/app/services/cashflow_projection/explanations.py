from __future__ import annotations

from typing import Any


def build_explanations(
    *,
    scenario: str,
    weeks: list[dict[str, Any]],
    top_customers: list[dict[str, Any]],
    total_collections: float,
    opening_cash_source: str,
) -> list[str]:
    explanations = [
        "La proyección se construyó con documentos abiertos de CxC y CxP.",
        f"El escenario {scenario} aplica fechas estimadas según historial de pago y reglas documentales.",
    ]
    if weeks:
        pressure = min(weeks, key=lambda week: week["net_cashflow"])
        explanations.append(
            f"La mayor presión de caja se concentra en {pressure['period']} "
            f"con flujo neto de {pressure['net_cashflow']:,.2f}."
        )
    if total_collections and top_customers:
        top_amount = sum(item["amount"] for item in top_customers[:4])
        explanations.append(
            f"Los cuatro principales clientes concentran "
            f"{top_amount / total_collections * 100:.1f}% de la cobranza proyectada."
        )
    explanations.append(
        {
            "manual": "La caja inicial fue enviada explícitamente por parámetro.",
            "detected": "La caja inicial se estimó desde cuentas contables de clase 10 identificadas como caja/bancos.",
            "zero_default": "La caja inicial no pudo determinarse; se utilizó cero.",
        }[opening_cash_source]
    )
    return explanations
