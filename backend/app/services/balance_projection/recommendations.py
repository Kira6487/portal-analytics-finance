from __future__ import annotations

from typing import Any


def build_recommendations(
    *,
    weeks: list[dict[str, Any]],
    alerts: list[dict[str, Any]],
    forecast_confidence: str,
    opening_cash_source: str,
    warnings: list[str],
) -> list[str]:
    recommendations: list[str] = []
    if any(week["projected_cash"] < 0 for week in weeks):
        recommendations.append("Priorizar cobranza de documentos criticos y revisar pagos urgentes o revisables.")
    if any(week["projected_working_capital"] < 0 for week in weeks):
        recommendations.append("Revisar estructura de CxC/CxP porque el capital de trabajo proyectado se vuelve negativo.")
    if any(alert["type"] == "ap_exceeds_liquid_resources" for alert in alerts):
        recommendations.append("Evaluar calendario de pagos cuando CxP supere caja mas CxC.")
    if forecast_confidence == "low":
        recommendations.append("No usar el forecast de ingresos/costos como unico criterio de decision.")
    if opening_cash_source in ("fallback_zero", "unavailable"):
        recommendations.append("Validar caja inicial con Tesoreria o enviar opening_cash como parametro.")
    if any("concentr" in warning.lower() for warning in warnings):
        recommendations.append("Dar seguimiento directo a clientes o proveedores concentradores.")
    if any("moneda" in warning.lower() or "fx" in warning.lower() for warning in warnings):
        recommendations.append("Definir politica FX productiva para documentos con moneda fuente distinta de SOL.")
    if any("sql server" in warning.lower() or "odbc" in warning.lower() for warning in warnings):
        recommendations.append("Resolver conectividad SQL Server/ODBC antes de usar metricas proyectadas para decision.")
    if not recommendations:
        recommendations.append("Monitorear semanalmente caja, CxC, CxP y capital de trabajo bajo los tres escenarios.")
    return recommendations
