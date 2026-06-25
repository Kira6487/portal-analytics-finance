from __future__ import annotations

from datetime import date
from typing import Any

from app.services.financial_statements import monthly_income_statement_series


DEFAULT_START = date(2019, 5, 1)


def build_income_statement_dataset(
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    include_budget: bool = True,
    growth_pct: float = 5.0,
) -> dict[str, Any]:
    start = date_from or DEFAULT_START
    end = date_to or date.today()
    statement = monthly_income_statement_series(date_from=start, date_to=end)
    rows = statement.get("periods", [])
    actual_by_period = {row["period"]: row for row in rows}
    periods = []
    warnings = list(statement.get("warnings", []))
    zero_revenue = 0
    for row in rows:
        period = row["period"]
        year, month = map(int, period.split("-"))
        revenue = float(row["revenue"])
        cost = float(row["cost_of_sales"])
        gross_profit = revenue - cost
        gross_margin_pct = gross_profit / revenue * 100 if revenue else None
        if revenue == 0:
            zero_revenue += 1

        prior = actual_by_period.get(f"{year - 1}-{month:02d}") if include_budget else None
        if prior:
            budget_revenue = round(float(prior["revenue"]) * (1 + growth_pct / 100), 2)
            budget_cost = round(float(prior["cost_of_sales"]) * (1 + growth_pct / 100), 2)
            budget_gross_profit = round(budget_revenue - budget_cost, 2)
            budget_gross_margin_pct = (
                round(budget_gross_profit / budget_revenue * 100, 2)
                if budget_revenue else None
            )
        else:
            budget_revenue = budget_cost = budget_gross_profit = None
            budget_gross_margin_pct = None

        periods.append(
            {
                "period": period,
                "year": year,
                "month": month,
                "revenue": round(revenue, 2),
                "cost_of_sales": round(cost, 2),
                "gross_profit": round(gross_profit, 2),
                "gross_margin_pct": (
                    round(gross_margin_pct, 2)
                    if gross_margin_pct is not None else None
                ),
                "budget_revenue": budget_revenue,
                "budget_cost": budget_cost,
                "budget_gross_profit": budget_gross_profit,
                "budget_gross_margin_pct": budget_gross_margin_pct,
            }
        )
    if zero_revenue:
        warnings.append(
            f"{zero_revenue} meses tienen ingresos cero; su margen porcentual es null."
        )
    if include_budget:
        warnings.append(
            "Presupuesto histórico simulado con el mismo mes del año anterior más "
            f"{growth_pct:.1f}%."
        )
    warnings.append(
        "La serie predictiva excluye asientos SAP TransType -3 de cierre de período "
        "para evitar reversiones técnicas de ingresos y costos."
    )
    return {
        "target": "income_statement_gross_margin",
        "data_max_date": rows[-1]["max_date"] if rows else None,
        "filters": {
            "date_from": start.isoformat(),
            "date_to": end.isoformat(),
            "include_budget": include_budget,
        },
        "periods": periods,
        "warnings": list(dict.fromkeys(warnings)),
    }
