from __future__ import annotations

from typing import Any


def build_alerts(
    *,
    weeks: list[dict[str, Any]],
    scenario: str,
    forecast_confidence: str,
    warnings: list[str],
    balance_check_difference: float,
    opening_cash_source: str,
) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []
    for week in weeks:
        if week["projected_cash"] < 0:
            alerts.append(
                {
                    "type": "negative_projected_cash",
                    "severity": "critical",
                    "message": f"Caja proyectada negativa en {week['period']}.",
                    "amount": week["projected_cash"],
                    "currency": "SOL",
                }
            )
        if week["projected_working_capital"] < 0:
            alerts.append(
                {
                    "type": "negative_working_capital",
                    "severity": "high",
                    "message": f"Capital de trabajo proyectado negativo en {week['period']}.",
                    "amount": week["projected_working_capital"],
                    "currency": "SOL",
                }
            )
        if week["projected_ap"] > week["projected_ar"] + week["projected_cash"]:
            alerts.append(
                {
                    "type": "ap_exceeds_liquid_resources",
                    "severity": "high",
                    "message": f"CxP supera caja mas CxC en {week['period']}.",
                    "amount": round(week["projected_ap"] - week["projected_ar"] - week["projected_cash"], 2),
                    "currency": "SOL",
                }
            )
    if scenario == "pessimistic" and any(week["projected_cash"] < 0 for week in weeks):
        alerts.append(
            {
                "type": "pessimistic_deficit",
                "severity": "critical",
                "message": "El escenario pesimista presenta deficit de caja.",
                "amount": min((week["projected_cash"] for week in weeks), default=0),
                "currency": "SOL",
            }
        )
    if forecast_confidence == "low":
        alerts.append(
            {
                "type": "low_forecast_confidence",
                "severity": "medium",
                "message": "El forecast de ingresos/costos tiene confianza baja.",
                "amount": 0,
                "currency": "SOL",
            }
        )
    if any("moneda" in warning.lower() or "fx" in warning.lower() for warning in warnings):
        alerts.append(
            {
                "type": "fx_policy_pending",
                "severity": "medium",
                "message": "Hay documentos con moneda fuente distinta de SOL o politica FX pendiente.",
                "amount": 0,
                "currency": "SOL",
            }
        )
    if abs(balance_check_difference or 0) > 0.005:
        alerts.append(
            {
                "type": "managerial_balance_difference",
                "severity": "medium",
                "message": "Existe diferencia de cuadre gerencial en el balance base.",
                "amount": round(balance_check_difference, 2),
                "currency": "SOL",
            }
        )
    if opening_cash_source in ("fallback_zero", "unavailable"):
        alerts.append(
            {
                "type": "opening_cash_not_validated",
                "severity": "high",
                "message": "La caja inicial no fue validada por Tesoreria.",
                "amount": 0,
                "currency": "SOL",
            }
        )
    return alerts[:50]
