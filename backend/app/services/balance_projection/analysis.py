from __future__ import annotations

from datetime import date
from typing import Any

from app.services.balance_projection.projection_engine import weekly_balance_projection


def executive_summary(
    *,
    basis_date: date | None = None,
    horizon_weeks: int = 13,
    scenario: str = "base",
    opening_cash: float | None = None,
) -> dict[str, Any]:
    projection = weekly_balance_projection(
        basis_date=basis_date,
        horizon_weeks=horizon_weeks,
        scenario=scenario,
        opening_cash=opening_cash,
    )
    summary = projection["summary"]
    ratios = projection["ratios"]
    confidence_reasons = []
    if any("SQL/ODBC" in warning or "SQL Server" in warning for warning in projection["warnings"]):
        confidence = "low"
        confidence_reasons.append("Conexion SQL Server/ODBC no disponible.")
    elif summary["opening_cash_source"] in ("detected", "parameter"):
        confidence = "medium"
        confidence_reasons.append("Caja inicial detectada o enviada por parametro.")
    else:
        confidence = "low"
        confidence_reasons.append("Caja inicial no validada.")
    if any("moneda" in warning.lower() or "fx" in warning.lower() for warning in projection["warnings"]):
        confidence = "low" if confidence == "medium" else confidence
        confidence_reasons.append("Hay documentos con moneda fuente distinta de SOL o politica FX pendiente.")
    confidence_reasons.append("Otros activos, otros pasivos y patrimonio se mantienen constantes.")
    text = (
        f"La posicion financiera proyectada en escenario {scenario} termina con caja "
        f"S/ {summary['ending_cash']:,.2f}, capital de trabajo S/ "
        f"{summary['working_capital_end']:,.2f} y liquidez gerencial "
        f"{ratios.get('managerial_liquidity_ratio')}."
    )
    return {
        "title": "Balance proyectado simplificado y posicion financiera futura",
        "summary": text,
        "key_findings": projection["explanations"],
        "risks": [alert["message"] for alert in projection["alerts"][:20]],
        "recommended_actions": projection["recommendations"],
        "confidence": confidence,
        "confidence_reasons": confidence_reasons,
        "currency": projection["currency"],
        "currency_symbol": projection["currency_symbol"],
        "limitations": projection["limitations"],
        "warnings": projection["warnings"],
    }
