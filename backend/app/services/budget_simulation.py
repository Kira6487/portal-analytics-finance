from __future__ import annotations

from datetime import date
from typing import Any

from app.services.dimensions_profitability import dimensions_profitability
from app.services.financial_statements import income_statement


def simulated_budget(
    *,
    year: int | None = None,
    basis_year: int | None = None,
    growth_pct: float = 5.0,
    method: str = "prior_year",
) -> dict[str, Any]:
    target = year or date.today().year
    basis = basis_year or target - 1
    if method not in ("prior_year", "historical_average", "rolling_12m"):
        raise ValueError("method debe ser prior_year, historical_average o rolling_12m")
    warnings = [
        "Presupuesto simulado generado para demo. No corresponde a presupuesto oficial SAP."
    ]
    factor = 1 + growth_pct / 100
    if method == "prior_year":
        source = income_statement(year=basis, group_by="month")
        source_periods = source.get("periods", [])
    elif method == "rolling_12m":
        source = income_statement(
            date_from=date(basis, 1, 1), date_to=date(basis, 12, 31), group_by="month"
        )
        source_periods = source.get("periods", [])
        warnings.append("rolling_12m usa el año base completo en esta primera versión.")
    else:
        history = income_statement(
            date_from=date(2019, 1, 1), date_to=date(basis, 12, 31), group_by="month"
        )
        rows = history.get("periods", [])
        averages = {}
        fields = (
            "revenue", "cost_of_sales", "administrative_expenses",
            "selling_expenses", "financial_expenses", "other_income", "other_expenses",
        )
        for field in fields:
            averages[field] = sum(row[field] for row in rows) / len(rows) if rows else 0
        source_periods = [{"period": f"{basis}-{month:02d}", **averages} for month in range(1, 13)]

    by_month = {int(row["period"][-2:]): row for row in source_periods}
    periods = []
    for month in range(1, 13):
        row = by_month.get(month, {})
        revenue = float(row.get("revenue", 0)) * factor
        cost = float(row.get("cost_of_sales", 0)) * factor
        admin = float(row.get("administrative_expenses", 0)) * factor
        selling = float(row.get("selling_expenses", 0)) * factor
        financial = float(row.get("financial_expenses", 0)) * factor
        other = (
            float(row.get("other_expenses", 0))
            - float(row.get("other_income", 0))
        ) * factor
        expenses = admin + selling + financial + other
        periods.append(
            {
                "period": f"{target}-{month:02d}",
                "revenue_budget": round(revenue, 2),
                "cost_budget": round(cost, 2),
                "administrative_expense_budget": round(admin, 2),
                "selling_expense_budget": round(selling, 2),
                "financial_expense_budget": round(financial, 2),
                "other_budget": round(other, 2),
                "expense_budget": round(expenses, 2),
                "operating_profit_budget": round(revenue - cost - expenses, 2),
            }
        )
    if not source_periods:
        warnings.append("El periodo base no tiene movimientos; el presupuesto resultó en cero.")
    dimension_source = dimensions_profitability(
        year=basis, dimension="OcrCode2", group_by="dimension"
    )
    dimension_budget = [
        {
            "dimension_code": item["dimension_code"],
            "dimension_name": item["dimension_name"],
            "revenue_budget": round(item["revenue"] * factor, 2),
            "cost_budget": round(item["cost"] * factor, 2),
            "expense_budget": round(item["expenses"] * factor, 2),
            "operating_profit_budget": round(item["operating_profit"] * factor, 2),
        }
        for item in dimension_source.get("items", [])
    ]
    if not dimension_budget:
        warnings.append("No se pudo generar presupuesto por OcrCode2 para el año base.")
    return {
        "budget_type": "simulated",
        "method": method,
        "basis_year": basis,
        "target_year": target,
        "growth_pct": growth_pct,
        "periods": periods,
        "dimensions": {
            "field": "OcrCode2",
            "items": dimension_budget,
        },
        "warnings": warnings,
    }


def income_statement_vs_budget(
    *, year: int | None = None, basis_year: int | None = None,
    growth_pct: float = 5.0, method: str = "prior_year"
) -> dict[str, Any]:
    target = year or date.today().year
    actual = income_statement(year=target, group_by="month")
    budget = simulated_budget(
        year=target, basis_year=basis_year, growth_pct=growth_pct, method=method
    )
    actual_by_period = {row["period"]: row for row in actual.get("periods", [])}
    periods = []
    for planned in budget["periods"]:
        period = planned["period"]
        real = actual_by_period.get(period, {})
        revenue_real = float(real.get("revenue", 0))
        revenue_budget = planned["revenue_budget"]
        profit_real = float(real.get("estimated_net_profit", 0))
        profit_budget = planned["operating_profit_budget"]
        revenue_variance = revenue_real - revenue_budget
        profit_variance = profit_real - profit_budget
        periods.append(
            {
                "period": period,
                "revenue_real": revenue_real,
                "revenue_budget": revenue_budget,
                "revenue_variance": round(revenue_variance, 2),
                "revenue_variance_pct": (
                    round(revenue_variance / abs(revenue_budget) * 100, 2)
                    if revenue_budget else None
                ),
                "operating_profit_real": profit_real,
                "operating_profit_budget": profit_budget,
                "operating_profit_variance": round(profit_variance, 2),
                "status": (
                    "favorable" if profit_variance > 0.005
                    else "desfavorable" if profit_variance < -0.005
                    else "neutro"
                ),
            }
        )
    return {
        "target_year": target,
        "periods": periods,
        "warnings": [
            "Comparación usa presupuesto simulado porque no existen registros presupuestales en SAP."
        ] + actual.get("warnings", []),
    }
