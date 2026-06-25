from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import get_connection
from app.core.config import get_settings
from app.queries.cashflow_projection_queries import OPENING_CASH_SQL
from app.services.cashflow_projection.alerts import build_alerts
from app.services.cashflow_projection.datasets import projectable_documents
from app.services.cashflow_projection.explanations import build_explanations
from app.services.cashflow_projection.recommendations import build_recommendations


HORIZONS = (4, 8, 13, 26)
LIMITATIONS = [
    "La moneda oficial de la demo es SOL; documentos fuente en otras monedas requieren validación FX.",
    "La proyección usa documentos abiertos y no incluye eventos futuros no registrados.",
    "Las fechas estimadas se basan en historial y no garantizan comportamiento real.",
    "CxC y CxP dependen de que SAP esté correctamente conciliado.",
    "No se consideran líneas de crédito, préstamos futuros ni pagos no registrados.",
    "No se modifica SAP ni se crean documentos.",
    "Es una vista gerencial y no un estado financiero oficial.",
]


def _opening_cash(
    basis: date, manual: float | None
) -> tuple[float, str, list[str]]:
    if manual is not None:
        return float(manual), "manual", []
    try:
        with get_connection() as connection:
            row = connection.execute(
                text(OPENING_CASH_SQL), {"basis_date": basis}
            ).mappings().one()
        amount = float(row["opening_cash"] or 0)
        accounts = int(row["accounts_count"] or 0)
        if accounts and abs(amount) > 0.005:
            return amount, "detected", [
                f"Caja inicial estimada desde {accounts} cuentas clase 10 de caja/bancos."
            ]
    except SQLAlchemyError as exc:
        return 0.0, "zero_default", [f"No se pudo estimar caja inicial: {exc}"]
    return 0.0, "zero_default", [
        "No se pudo determinar caja inicial con suficiente confianza. "
        "Se usó opening_cash=0; puede enviarlo como parámetro."
    ]


def _rank(items: list[dict[str, Any]], *, date_field: str) -> list[dict[str, Any]]:
    grouped: defaultdict[tuple[str, str], float] = defaultdict(float)
    for item in items:
        grouped[(str(item["card_code"]), str(item["card_name"]))] += item["open_amount"]
    return [
        {"card_code": key[0], "card_name": key[1], "amount": round(amount, 2)}
        for key, amount in sorted(grouped.items(), key=lambda pair: pair[1], reverse=True)
    ][:10]


def _confidence(
    receivables: list[dict[str, Any]],
    payables: list[dict[str, Any]],
    opening_cash_source: str,
) -> dict[str, Any]:
    all_docs = receivables + payables
    total = sum(item["open_amount"] for item in all_docs)
    identified = sum(item["open_amount"] for item in all_docs if item["has_history"])
    coverage = identified / total * 100 if total else 0
    foreign = sum(item["open_amount"] for item in all_docs if item["currency"] != "SOL")
    foreign_pct = foreign / total * 100 if total else 0
    reasons = [f"{coverage:.1f}% del monto proyectado tiene historial identificado."]
    if opening_cash_source == "manual":
        reasons.append("La caja inicial fue enviada por parámetro.")
    elif opening_cash_source == "detected":
        reasons.append("La caja inicial fue detectada contablemente.")
    else:
        reasons.append("La caja inicial no fue identificada.")
    if foreign_pct:
        reasons.append(
            f"{foreign_pct:.1f}% del monto proviene de documentos fuente no SOL."
        )
    else:
        reasons.append("Todos los documentos fuente están alineados con SOL.")
    if coverage > 70 and opening_cash_source in ("manual", "detected") and not foreign_pct:
        level = "high"
    elif coverage >= 40 and opening_cash_source in ("manual", "detected"):
        level = "medium"
    else:
        level = "low"
    return {
        "confidence": level,
        "history_coverage_pct": round(coverage, 2),
        "foreign_currency_amount_pct": round(foreign_pct, 2),
        "confidence_reasons": reasons,
    }


def weekly_projection(
    *,
    basis_date: date | None = None,
    horizon_weeks: int = 13,
    scenario: str = "base",
    opening_cash: float | None = None,
) -> dict[str, Any]:
    if horizon_weeks not in HORIZONS:
        raise ValueError("horizon_weeks debe ser 4, 8, 13 o 26")
    documents = projectable_documents(basis_date=basis_date, scenario=scenario)
    settings = get_settings()
    basis = date.fromisoformat(documents["basis_date"])
    opening, opening_source, opening_warnings = _opening_cash(basis, opening_cash)
    week_start = basis - timedelta(days=basis.weekday())
    horizon_end = week_start + timedelta(days=horizon_weeks * 7 - 1)
    buckets = [
        {
            "week_start": week_start + timedelta(days=index * 7),
            "week_end": week_start + timedelta(days=index * 7 + 6),
            "expected_collections": 0.0,
            "expected_payments": 0.0,
            "collections_count": 0,
            "payments_count": 0,
        }
        for index in range(horizon_weeks)
    ]

    def add(items, field, amount_field, count_field):
        for item in items:
            movement_date = date.fromisoformat(item[field])
            if week_start <= movement_date <= horizon_end:
                index = (movement_date - week_start).days // 7
                buckets[index][amount_field] += item["open_amount"]
                buckets[index][count_field] += 1

    add(
        documents["receivables"], "estimated_collection_date",
        "expected_collections", "collections_count",
    )
    add(
        documents["payables"], "estimated_payment_date",
        "expected_payments", "payments_count",
    )

    cash = opening
    weeks = []
    for bucket in buckets:
        net = bucket["expected_collections"] - bucket["expected_payments"]
        cash += net
        weeks.append(
            {
                "period": f"{bucket['week_start'].isocalendar().year}-W"
                f"{bucket['week_start'].isocalendar().week:02d}",
                "week_start": bucket["week_start"].isoformat(),
                "week_end": bucket["week_end"].isoformat(),
                "expected_collections": round(bucket["expected_collections"], 2),
                "expected_payments": round(bucket["expected_payments"], 2),
                "net_cashflow": round(net, 2),
                "projected_cash_balance": round(cash, 2),
                "collections_count": bucket["collections_count"],
                "payments_count": bucket["payments_count"],
                "status": "deficit" if cash < 0 else "warning" if cash < opening * 0.2 else "positive",
            }
        )

    top_customers = _rank(documents["receivables"], date_field="estimated_collection_date")
    top_vendors = _rank(documents["payables"], date_field="estimated_payment_date")
    alerts = build_alerts(
        weeks=weeks,
        receivables=documents["receivables"],
        payables=documents["payables"],
        top_customers=top_customers,
        top_vendors=top_vendors,
        opening_cash_source=opening_source,
        scenario=scenario,
    )
    expected_collections = sum(week["expected_collections"] for week in weeks)
    expected_payments = sum(week["expected_payments"] for week in weeks)
    minimum_cash = min((week["projected_cash_balance"] for week in weeks), default=opening)
    critical = min(weeks, key=lambda week: week["projected_cash_balance"]) if weeks else None
    confidence = _confidence(documents["receivables"], documents["payables"], opening_source)
    explanations = build_explanations(
        scenario=scenario,
        weeks=weeks,
        top_customers=top_customers,
        total_collections=sum(item["open_amount"] for item in documents["receivables"]),
        opening_cash_source=opening_source,
    )
    recommendations = build_recommendations(
        alerts=alerts, opening_cash_source=opening_source
    )
    return {
        "module": "cashflow_projection",
        "basis_date": basis.isoformat(),
        "horizon_weeks": horizon_weeks,
        "scenario": scenario,
        "opening_cash": round(opening, 2),
        "currency": settings.reporting_currency,
        "currency_symbol": settings.reporting_currency_symbol,
        "opening_cash_source": opening_source,
        "summary": {
            "expected_collections": round(expected_collections, 2),
            "expected_payments": round(expected_payments, 2),
            "net_cashflow": round(expected_collections - expected_payments, 2),
            "ending_cash": round(cash, 2),
            "minimum_cash": round(minimum_cash, 2),
            "deficit_weeks": sum(week["projected_cash_balance"] < 0 for week in weeks),
            "critical_week": critical["period"] if critical else None,
            "receivables_projected": sum(week["collections_count"] for week in weeks),
            "payables_projected": sum(week["payments_count"] for week in weeks),
            **confidence,
        },
        "weeks": weeks,
        "top_collection_customers": top_customers,
        "top_payment_vendors": top_vendors,
        "alerts": alerts,
        "explanations": explanations,
        "recommendations": recommendations,
        "limitations": LIMITATIONS,
        "warnings": list(dict.fromkeys(documents["warnings"] + opening_warnings)),
    }
