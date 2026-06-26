from __future__ import annotations

from typing import Any


def build_explanations(
    *,
    scenario: str,
    weeks: list[dict[str, Any]],
    used_fallback: bool,
) -> list[str]:
    explanations = [
        "El Balance proyectado simplificado se construye a partir del Balance historico, flujo de caja proyectado, CxC predictiva y CxP predictiva.",
        "La caja final proyectada depende principalmente de cobros esperados y pagos durante el horizonte.",
        "CxC proyectada se reduce por cobros esperados y CxP proyectada se reduce por pagos esperados.",
        "El resultado es gerencial y no reemplaza el Balance oficial de SAP.",
        "La moneda oficial de reporte es SOL; documentos con moneda fuente distinta pueden requerir politica FX productiva.",
    ]
    if scenario == "optimistic":
        explanations.append("El escenario optimista adelanta cobros y mantiene pagos normales segun las reglas existentes.")
    elif scenario == "pessimistic":
        explanations.append("El escenario pesimista retrasa cobros y mantiene presion de pagos vencidos.")
    if any(week["liquidity_status"] == "critical" for week in weeks):
        explanations.append("La posicion de liquidez es critica cuando la caja proyectada cae por debajo de cero.")
    if used_fallback:
        explanations.append("La conexion SQL/ODBC no entrego datos reales; se devolvio una estructura de respuesta con warnings sin inventar documentos SAP.")
    return explanations
