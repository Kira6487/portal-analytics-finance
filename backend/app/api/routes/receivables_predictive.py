from datetime import date
from typing import Any, Callable

from fastapi import APIRouter, HTTPException, Query

from app.services.receivables_predictive.analysis import (
    collection_priorities,
    concentration_analysis,
    executive_summary,
)
from app.services.receivables_predictive.customer_scoring import customer_scores
from app.services.receivables_predictive.dataset import build_predictive_dataset


router = APIRouter(
    prefix="/api/receivables-predictive", tags=["receivables-predictive"]
)


def _execute(operation: Callable[..., dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
    try:
        return operation(**kwargs)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        return {
            "status": "error",
            "warnings": [f"No se pudo completar el análisis predictivo de CxC: {exc}"],
            "limitations": ["El error fue controlado y no se modificó SAP."],
        }


@router.get("/dataset")
def predictive_dataset(
    as_of_date: date | None = None,
    customer: str | None = None,
    risk: str | None = None,
    min_amount: float | None = Query(default=None, ge=0),
    days_overdue_min: int | None = None,
    include_closed: bool = False,
    scenario: str = "base",
) -> dict[str, Any]:
    return _execute(
        build_predictive_dataset,
        as_of_date=as_of_date,
        customer=customer,
        risk=risk,
        min_amount=min_amount,
        days_overdue_min=days_overdue_min,
        include_closed=include_closed,
        scenario=scenario,
    )


@router.get("/customers")
def predictive_customers(
    as_of_date: date | None = None,
    risk: str | None = None,
    limit: int = Query(default=50, ge=1, le=500),
    scenario: str = "base",
) -> dict[str, Any]:
    return _execute(
        customer_scores,
        as_of_date=as_of_date,
        risk=risk,
        limit=limit,
        scenario=scenario,
    )


@router.get("/priorities")
def predictive_priorities(
    as_of_date: date | None = None,
    limit: int = Query(default=20, ge=1, le=500),
    scenario: str = "base",
) -> dict[str, Any]:
    return _execute(
        collection_priorities,
        as_of_date=as_of_date,
        limit=limit,
        scenario=scenario,
    )


@router.get("/concentration")
def predictive_concentration(
    as_of_date: date | None = None,
    scenario: str = "base",
) -> dict[str, Any]:
    return _execute(
        concentration_analysis, as_of_date=as_of_date, scenario=scenario
    )


@router.get("/executive-summary")
def predictive_executive_summary(
    as_of_date: date | None = None,
    scenario: str = "base",
) -> dict[str, Any]:
    return _execute(executive_summary, as_of_date=as_of_date, scenario=scenario)
