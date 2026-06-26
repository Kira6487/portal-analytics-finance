from __future__ import annotations

from typing import Any


def document_explanation(reasons: list[str], risk_reasons: list[str]) -> str:
    combined = reasons + [reason for reason in risk_reasons if reason not in reasons]
    if combined:
        return " ".join(combined)
    return (
        "La prioridad de pago combina dias vencidos, monto pendiente, "
        "concentracion del proveedor y coincidencia con semanas de deficit de caja."
    )


def build_explanations(items: list[dict[str, Any]], top5_concentration_pct: float) -> list[str]:
    explanations = [
        "La prioridad de pago combina dias vencidos, monto pendiente, concentracion del proveedor y semanas de deficit de caja.",
        "La fecha estimada de pago se basa en el vencimiento del documento y el comportamiento historico de pago al proveedor.",
        "La fecha recomendada es una sugerencia gerencial y no programa pagos automaticamente.",
        "La moneda oficial de reporte es Soles / SOL; se conserva la moneda fuente para futuras politicas FX.",
    ]
    if top5_concentration_pct > 40:
        explanations.append(
            f"Los 5 principales proveedores concentran {top5_concentration_pct:.2f}% de CxP abierta."
        )
    if any(item.get("can_consider_deferral") for item in items):
        explanations.append(
            "Un documento puede marcarse como revisable si no esta vencido, tiene prioridad baja/media y cae en semana de presion de caja."
        )
    return explanations
