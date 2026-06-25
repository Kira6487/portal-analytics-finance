from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import get_connection
from app.queries.financial_queries import ACCOUNT_MOVEMENTS_SQL, COST_CENTERS_SQL
from app.services.financial_mapping import classify_account, signed_amount
from app.services.financial_statements import DIMENSIONS, resolve_dates


def dimensions_profitability(
    *,
    year: int | None = None,
    month: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    dimension: str = "OcrCode2",
    group_by: str = "dimension",
) -> dict[str, Any]:
    if dimension not in DIMENSIONS:
        raise ValueError(f"Dimensión inválida. Use: {', '.join(DIMENSIONS)}")
    if group_by not in ("dimension", "month"):
        raise ValueError("group_by debe ser dimension o month")
    start, end = resolve_dates(year, month, date_from, date_to)
    totals: defaultdict[str, defaultdict[str, float]] = defaultdict(
        lambda: defaultdict(float)
    )
    names: dict[str, str] = {}
    warnings: list[str] = []
    try:
        with get_connection() as connection:
            for center in connection.execute(text(COST_CENTERS_SQL)).mappings():
                names[str(center["code"])] = str(center["name"])
            rows = connection.execute(
                text(ACCOUNT_MOVEMENTS_SQL), {"date_from": start, "date_to": end}
            ).mappings()
            for row in rows:
                code = row[dimension]
                if not code or int(row["group_mask"] or 0) == 8:
                    continue
                mapping = classify_account(dict(row))
                group = mapping["financial_group"]
                amount = signed_amount(
                    group, float(row["debit"] or 0), float(row["credit"] or 0)
                )
                key = (
                    row["posting_date"].strftime("%Y-%m")
                    if group_by == "month"
                    else str(code)
                )
                totals[key][group] += amount
    except SQLAlchemyError as exc:
        return {"dimension": dimension, "summary": {}, "items": [], "warnings": [str(exc)]}

    items = []
    for key, values in totals.items():
        revenue = values["Ingresos"] + values["Otros ingresos"]
        cost = values["Costo de ventas"]
        expenses = sum(
            values[group]
            for group in (
                "Gastos operativos", "Gastos administrativos", "Gastos de ventas",
                "Gastos financieros", "Otros gastos",
            )
        )
        profit = revenue - cost - expenses
        items.append(
            {
                "dimension_code": key,
                "dimension_name": names.get(key, key),
                "revenue": round(revenue, 2),
                "cost": round(cost, 2),
                "expenses": round(expenses, 2),
                "gross_profit": round(revenue - cost, 2),
                "operating_profit": round(profit, 2),
                "operating_margin_pct": round(profit / revenue * 100, 2) if revenue else None,
                "unclassified": round(values["No clasificado"], 2),
            }
        )
    items.sort(key=lambda item: item["operating_profit"], reverse=True)
    for rank, item in enumerate(items, 1):
        item["rank"] = rank
    if not items:
        warnings.append(f"No hay movimientos para {dimension} en el periodo seleccionado.")
    return {
        "dimension": dimension,
        "filters": {"date_from": start.isoformat(), "date_to": end.isoformat(), "group_by": group_by},
        "summary": {
            "total_revenue": round(sum(i["revenue"] for i in items), 2),
            "total_cost": round(sum(i["cost"] for i in items), 2),
            "total_expense": round(sum(i["expenses"] for i in items), 2),
            "operating_profit": round(sum(i["operating_profit"] for i in items), 2),
        },
        "items": items,
        "warnings": warnings + ["Mapeo contable preliminar sujeto a validación."],
    }
