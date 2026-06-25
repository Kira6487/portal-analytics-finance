from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import get_connection
from app.queries.financial_queries import (
    ACCOUNT_MOVEMENTS_SQL,
    ACCOUNTS_SQL,
    AVAILABLE_PERIOD_SQL,
    BALANCE_MOVEMENTS_SQL,
    COST_CENTERS_SQL,
    CURRENCIES_SQL,
    DIMENSION_COLUMNS_SQL,
)
from app.services.financial_mapping import (
    FINANCIAL_GROUPS,
    classify_account,
    signed_amount,
)


DIMENSIONS = ("OcrCode", "OcrCode2", "OcrCode3", "OcrCode4", "OcrCode5")


def _serialize(value: Any) -> Any:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return float(value) if value is not None else value


def resolve_dates(
    year: int | None = None,
    month: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> tuple[date, date]:
    today = date.today()
    if date_from or date_to:
        start = date_from or date(2019, 1, 1)
        end = date_to or today
    elif year and month:
        start = date(year, month, 1)
        end = date(year + (month == 12), 1 if month == 12 else month + 1, 1)
        end = date.fromordinal(end.toordinal() - 1)
    elif year:
        start, end = date(year, 1, 1), date(year, 12, 31)
    else:
        start, end = date(today.year, 1, 1), today
    if start > end:
        raise ValueError("date_from no puede ser posterior a date_to")
    return start, end


def _period_key(value: date, group_by: str) -> str:
    if group_by == "year":
        return str(value.year)
    if group_by == "quarter":
        return f"{value.year}-Q{((value.month - 1) // 3) + 1}"
    return value.strftime("%Y-%m")


def _empty_period(period: str) -> dict[str, Any]:
    return {
        "period": period,
        "revenue": 0.0,
        "cost_of_sales": 0.0,
        "gross_profit": 0.0,
        "operating_expenses": 0.0,
        "administrative_expenses": 0.0,
        "selling_expenses": 0.0,
        "financial_expenses": 0.0,
        "other_income": 0.0,
        "other_expenses": 0.0,
        "operating_profit": 0.0,
        "estimated_net_profit": 0.0,
        "unclassified": 0.0,
    }


def income_statement(
    *,
    year: int | None = None,
    month: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    dimension: str | None = None,
    cost_center: str | None = None,
    group_by: str = "month",
) -> dict[str, Any]:
    start, end = resolve_dates(year, month, date_from, date_to)
    if group_by not in ("month", "quarter", "year"):
        raise ValueError("group_by debe ser month, quarter o year")
    if dimension and dimension not in DIMENSIONS:
        raise ValueError(f"Dimensión inválida. Use: {', '.join(DIMENSIONS)}")
    sql = ACCOUNT_MOVEMENTS_SQL
    params: dict[str, Any] = {"date_from": start, "date_to": end}
    if cost_center:
        selected = dimension or "OcrCode"
        if selected not in DIMENSIONS:
            raise ValueError("Dimensión inválida")
        sql += f" AND J.[{selected}] = :cost_center"
        params["cost_center"] = cost_center

    periods: dict[str, dict[str, Any]] = {}
    account_totals: defaultdict[str, float] = defaultdict(float)
    unclassified_accounts: set[str] = set()
    warnings: list[str] = []
    try:
        with get_connection() as connection:
            rows = connection.execute(text(sql), params).mappings()
            for row in rows:
                mapping = classify_account(dict(row))
                group = mapping["financial_group"]
                # GroupMask 8 contains closing/result transfer accounts and is excluded.
                if int(row["group_mask"] or 0) == 8:
                    continue
                amount = signed_amount(
                    group, float(row["debit"] or 0), float(row["credit"] or 0)
                )
                key = _period_key(row["posting_date"], group_by)
                item = periods.setdefault(key, _empty_period(key))
                field = {
                    "Ingresos": "revenue",
                    "Costo de ventas": "cost_of_sales",
                    "Gastos operativos": "operating_expenses",
                    "Gastos administrativos": "administrative_expenses",
                    "Gastos de ventas": "selling_expenses",
                    "Gastos financieros": "financial_expenses",
                    "Otros ingresos": "other_income",
                    "Otros gastos": "other_expenses",
                    "No clasificado": "unclassified",
                }.get(group)
                if field:
                    item[field] += amount
                    account_totals[mapping["format_code"]] += abs(amount)
                if group == "No clasificado" and abs(amount) > 0.005:
                    unclassified_accounts.add(mapping["format_code"])
    except SQLAlchemyError as exc:
        return {
            "filters": {"date_from": start.isoformat(), "date_to": end.isoformat()},
            "summary": {},
            "periods": [],
            "warnings": [f"No se pudo construir el Estado de Resultados: {exc}"],
        }

    for item in periods.values():
        item["operating_expenses"] += (
            item["administrative_expenses"] + item["selling_expenses"]
        )
        item["gross_profit"] = item["revenue"] - item["cost_of_sales"]
        item["operating_profit"] = item["gross_profit"] - item["operating_expenses"]
        item["estimated_net_profit"] = (
            item["operating_profit"]
            + item["other_income"]
            - item["other_expenses"]
            - item["financial_expenses"]
        )
        for key, value in item.items():
            if key != "period":
                item[key] = round(value, 2)

    ordered = [periods[key] for key in sorted(periods)]
    numeric = [key for key in _empty_period("").keys() if key != "period"]
    summary = {key: round(sum(p[key] for p in ordered), 2) for key in numeric}
    summary.update(
        {
            "total_revenue": summary.pop("revenue", 0),
            "total_cost": summary.pop("cost_of_sales", 0),
            "unclassified_amount": summary.pop("unclassified", 0),
        }
    )
    if unclassified_accounts:
        warnings.append(
            f"{len(unclassified_accounts)} cuentas con movimiento quedaron sin clasificar."
        )
    if any(p["revenue"] < 0 for p in ordered):
        warnings.append("Hay periodos con ingresos netos negativos; revisar notas de crédito o signos.")
    movement_total = sum(account_totals.values())
    if movement_total and account_totals and max(account_totals.values()) / movement_total > 0.5:
        warnings.append("Más del 50% del movimiento se concentra en una sola cuenta.")
    if not ordered:
        warnings.append("No hay movimientos para los filtros seleccionados.")
    warnings.append(
        "Mapeo contable preliminar: debe ser validado por Contabilidad antes de uso oficial."
    )
    return {
        "filters": {
            "date_from": start.isoformat(),
            "date_to": end.isoformat(),
            "group_by": group_by,
            "dimension": dimension,
            "cost_center": cost_center,
        },
        "summary": summary,
        "periods": ordered,
        "unclassified_accounts_count": len(unclassified_accounts),
        "warnings": warnings,
    }


def balance_summary(
    *, as_of_date: date | None = None, year: int | None = None, month: int | None = None
) -> dict[str, Any]:
    target = as_of_date
    if not target:
        if year and month:
            _, target = resolve_dates(year, month)
        elif year:
            target = date(year, 12, 31)
        else:
            target = date.today()
    totals = defaultdict(float)
    unclassified: list[str] = []
    warnings = [
        "Vista gerencial simplificada; no reemplaza el Balance oficial emitido por SAP."
    ]
    try:
        with get_connection() as connection:
            rows = connection.execute(
                text(BALANCE_MOVEMENTS_SQL), {"as_of_date": target}
            ).mappings()
            for row in rows:
                mapping = classify_account(dict(row))
                group = mapping["financial_group"]
                amount = signed_amount(
                    group, float(row["debit"] or 0), float(row["credit"] or 0)
                )
                totals[group] += amount
                if group == "No clasificado" and abs(amount) > 0.005:
                    unclassified.append(mapping["format_code"])
    except SQLAlchemyError as exc:
        return {"as_of_date": target.isoformat(), "warnings": [str(exc)]}

    assets, liabilities, equity = totals["Activos"], totals["Pasivos"], totals["Patrimonio"]
    period_result = (
        totals["Ingresos"] + totals["Otros ingresos"]
        - totals["Costo de ventas"] - totals["Gastos operativos"]
        - totals["Gastos administrativos"] - totals["Gastos de ventas"]
        - totals["Gastos financieros"] - totals["Otros gastos"]
    )
    difference = assets - liabilities - equity - period_result
    debt_to_assets = liabilities / assets if assets else None
    warnings.append(
        "No se separó corriente/no corriente; liquidez corriente y capital de trabajo no están disponibles."
    )
    if unclassified:
        warnings.append(f"{len(set(unclassified))} cuentas de balance no fueron clasificadas.")
    return {
        "as_of_date": target.isoformat(),
        "assets": round(assets, 2),
        "liabilities": round(liabilities, 2),
        "equity": round(equity, 2),
        "period_result": round(period_result, 2),
        "balance_check_difference": round(difference, 2),
        "ratios": {
            "debt_to_assets": round(debt_to_assets, 4) if debt_to_assets is not None else None,
            "working_capital": None,
            "current_ratio": None,
        },
        "unclassified_amount": round(totals["No clasificado"], 2),
        "warnings": warnings,
    }


def metadata() -> dict[str, Any]:
    warnings: list[str] = []
    with get_connection() as connection:
        period = connection.execute(text(AVAILABLE_PERIOD_SQL)).mappings().one()
        accounts = connection.execute(text(ACCOUNTS_SQL)).mappings().all()
        centers = connection.execute(text(COST_CENTERS_SQL)).mappings().all()
        dimension_columns = {
            row["COLUMN_NAME"]
            for row in connection.execute(text(DIMENSION_COLUMNS_SQL)).mappings()
        }
        currencies = [
            row["currency"] for row in connection.execute(text(CURRENCIES_SQL)).mappings()
        ]
    mappings = [classify_account(dict(row)) for row in accounts if row["postable"] == "Y"]
    unclassified = [m for m in mappings if m["financial_group"] == "No clasificado"]
    min_date, max_date = period["min_date"], period["max_date"]
    years = list(range(min_date.year, max_date.year + 1)) if min_date and max_date else []
    dimensions = [
        field for field in DIMENSIONS if field in dimension_columns
    ]
    if unclassified:
        warnings.append(f"{len(unclassified)} cuentas contabilizables sin clasificación.")
    return {
        "available_period": {
            "min_date": _serialize(min_date),
            "max_date": _serialize(max_date),
            "years": years,
            "months_count": int(period["months_count"] or 0),
        },
        "dimensions": {
            "available_fields": dimensions,
            "cost_centers_count": len(centers),
            "cost_centers": [
                {
                    "code": row["code"],
                    "name": row["name"],
                    "dimension": int(row["dimension"]),
                }
                for row in centers
            ],
        },
        "currencies": currencies,
        "financial_groups": list(FINANCIAL_GROUPS),
        "accounts": {
            "classified": len(mappings) - len(unclassified),
            "unclassified": len(unclassified),
            "total_postable": len(mappings),
        },
        "budget": {
            "real_budget_available": False,
            "simulated_budget_available": True,
        },
        "warnings": warnings,
    }
