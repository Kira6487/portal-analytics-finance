from datetime import date
from typing import Any, Callable

from fastapi import APIRouter, HTTPException, Query

from app.services.budget_simulation import (
    income_statement_vs_budget,
    simulated_budget,
)
from app.services.cashflow_base import cashflow_base
from app.services.dimensions_profitability import dimensions_profitability
from app.services.financial_statements import (
    balance_summary,
    income_statement,
    metadata,
)
from app.services.open_items import open_payables, open_receivables


router = APIRouter(prefix="/api/financial", tags=["financial"])


def _execute(operation: Callable[..., dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
    try:
        return operation(**kwargs)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        return {
            "status": "error",
            "warnings": [f"No se pudo completar la consulta financiera: {exc}"],
        }


@router.get("/metadata")
def financial_metadata() -> dict[str, Any]:
    return _execute(metadata)


@router.get("/income-statement")
def get_income_statement(
    year: int | None = None,
    month: int | None = Query(default=None, ge=1, le=12),
    date_from: date | None = None,
    date_to: date | None = None,
    dimension: str | None = None,
    cost_center: str | None = None,
    group_by: str = "month",
) -> dict[str, Any]:
    return _execute(
        income_statement,
        year=year,
        month=month,
        date_from=date_from,
        date_to=date_to,
        dimension=dimension,
        cost_center=cost_center,
        group_by=group_by,
    )


@router.get("/income-statement-vs-budget")
def get_income_statement_vs_budget(
    year: int | None = None,
    basis_year: int | None = None,
    growth_pct: float = 5,
    method: str = "prior_year",
) -> dict[str, Any]:
    return _execute(
        income_statement_vs_budget,
        year=year,
        basis_year=basis_year,
        growth_pct=growth_pct,
        method=method,
    )


@router.get("/balance-summary")
def get_balance_summary(
    as_of_date: date | None = None,
    year: int | None = None,
    month: int | None = Query(default=None, ge=1, le=12),
) -> dict[str, Any]:
    return _execute(
        balance_summary, as_of_date=as_of_date, year=year, month=month
    )


@router.get("/receivables/open")
def get_open_receivables(
    as_of_date: date | None = None,
    customer: str | None = None,
    risk: str | None = None,
    min_amount: float | None = Query(default=None, ge=0),
    days_overdue_min: int | None = None,
) -> dict[str, Any]:
    return _execute(
        open_receivables,
        as_of_date=as_of_date,
        customer=customer,
        risk=risk,
        min_amount=min_amount,
        days_min=days_overdue_min,
    )


@router.get("/payables/open")
def get_open_payables(
    as_of_date: date | None = None,
    vendor: str | None = None,
    min_amount: float | None = Query(default=None, ge=0),
    days_due_min: int | None = None,
) -> dict[str, Any]:
    return _execute(
        open_payables,
        as_of_date=as_of_date,
        vendor=vendor,
        min_amount=min_amount,
        days_min=days_due_min,
    )


@router.get("/cashflow/base")
def get_cashflow_base(
    date_from: date | None = None,
    date_to: date | None = None,
    bucket: str = "week",
) -> dict[str, Any]:
    return _execute(
        cashflow_base, date_from=date_from, date_to=date_to, bucket=bucket
    )


@router.get("/profitability/dimensions")
def get_dimensions_profitability(
    year: int | None = None,
    month: int | None = Query(default=None, ge=1, le=12),
    date_from: date | None = None,
    date_to: date | None = None,
    dimension: str = "OcrCode2",
    group_by: str = "dimension",
) -> dict[str, Any]:
    return _execute(
        dimensions_profitability,
        year=year,
        month=month,
        date_from=date_from,
        date_to=date_to,
        dimension=dimension,
        group_by=group_by,
    )


@router.get("/budget/simulated")
def get_simulated_budget(
    year: int | None = None,
    basis_year: int | None = None,
    growth_pct: float = 5,
    method: str = "prior_year",
) -> dict[str, Any]:
    return _execute(
        simulated_budget,
        year=year,
        basis_year=basis_year,
        growth_pct=growth_pct,
        method=method,
    )
