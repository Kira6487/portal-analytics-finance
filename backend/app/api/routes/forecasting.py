from datetime import date
from typing import Any, Callable

from fastapi import APIRouter, HTTPException, Query

from app.services.forecasting.backtesting import run_backtesting
from app.services.forecasting.dataset_builder import build_income_statement_dataset
from app.services.forecasting.income_statement_forecast import (
    executive_summary,
    generate_forecast,
)


router = APIRouter(prefix="/api/forecasting", tags=["forecasting"])


def _execute(operation: Callable[..., dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
    try:
        return operation(**kwargs)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        return {
            "status": "error",
            "warnings": [f"No se pudo completar el proceso predictivo: {exc}"],
            "limitations": [
                "El endpoint controló el error y no modificó información en SAP."
            ],
        }


@router.get("/income-statement/dataset")
def income_statement_dataset(
    date_from: date | None = None,
    date_to: date | None = None,
    include_budget: bool = True,
) -> dict[str, Any]:
    return _execute(
        build_income_statement_dataset,
        date_from=date_from,
        date_to=date_to,
        include_budget=include_budget,
    )


@router.get("/income-statement/backtest")
def income_statement_backtest(
    target: str = "all",
    test_months: int = Query(default=6, ge=1, le=24),
) -> dict[str, Any]:
    dataset = _execute(build_income_statement_dataset, include_budget=False)
    if dataset.get("status") == "error":
        return dataset
    return _execute(
        run_backtesting,
        periods=dataset["periods"],
        target=target,
        test_months=test_months,
    )


@router.get("/income-statement/forecast")
def income_statement_forecast(
    horizon: int = 6,
    include_budget: bool = True,
    basis_date: date | None = None,
    test_months: int = Query(default=6, ge=1, le=24),
) -> dict[str, Any]:
    return _execute(
        generate_forecast,
        horizon=horizon,
        include_budget=include_budget,
        basis_date=basis_date,
        test_months=test_months,
    )


@router.get("/income-statement/executive-summary")
def income_statement_executive_summary(horizon: int = 6) -> dict[str, Any]:
    return _execute(executive_summary, horizon=horizon)
