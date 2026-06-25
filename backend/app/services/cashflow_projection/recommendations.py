from __future__ import annotations

from typing import Any


def build_recommendations(
    *, alerts: list[dict[str, Any]], opening_cash_source: str
) -> list[str]:
    kinds = {alert["type"] for alert in alerts}
    recommendations = []
    if "cash_deficit" in kinds or "pessimistic_deficit" in kinds:
        recommendations.extend(
            [
                "Priorizar la cobranza de los clientes que concentran los mayores montos.",
                "Revisar pagos fuertes de la semana crítica y postergar obligaciones no críticas cuando sea viable.",
            ]
        )
    if "collection_concentration" in kinds:
        recommendations.append(
            "Establecer seguimiento especial a los clientes que concentran la cobranza."
        )
    if "overdue_receivables" in kinds:
        recommendations.append("Ejecutar un plan específico de cobranza sobre CxC vencida.")
    if "overdue_payables" in kinds:
        recommendations.append(
            "Revisar obligaciones vencidas y acordar una priorización de pagos."
        )
    if opening_cash_source == "zero_default":
        recommendations.append(
            "Configurar cuentas de caja/bancos o enviar opening_cash manualmente."
        )
    recommendations.append("Definir la moneda oficial de reporte financiero.")
    return list(dict.fromkeys(recommendations))
