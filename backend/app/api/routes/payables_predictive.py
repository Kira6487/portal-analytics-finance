from datetime import date
from typing import Any, Callable

from fastapi import APIRouter, HTTPException, Query

from app.services.payables_predictive.analysis import (
    deferrable_payments,
    executive_summary,
    payment_priorities,
)
from app.services.payables_predictive.concentration import concentration_analysis
from app.services.payables_predictive.dataset import build_predictive_dataset
from app.services.payables_predictive.vendor_scoring import vendor_scores


router = APIRouter(prefix="/api/payables-predictive", tags=["payables-predictive"])


def _execute(operation: Callable[..., dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
    try:
        return operation(**kwargs)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        return {
            "status": "error",
            "warnings": [f"No se pudo completar el analisis predictivo de CxP: {exc}"],
            "limitations": ["El error fue controlado y no se modifico SAP."],
            "currency": "SOL",
            "currency_symbol": "S/",
        }


@router.get("/dataset")
def predictive_dataset(
    as_of_date: date | None = None,
    vendor: str | None = None,
    priority: str | None = None,
    risk: str | None = None,
    min_amount: float | None = Query(default=None, ge=0),
    days_overdue_min: int | None = None,
    scenario: str = "base",
    include_closed: bool = False,
) -> dict[str, Any]:
    return _execute(
        build_predictive_dataset,
        as_of_date=as_of_date,
        vendor=vendor,
        priority=priority,
        risk=risk,
        min_amount=min_amount,
        days_overdue_min=days_overdue_min,
        scenario=scenario,
        include_closed=include_closed,
    )


@router.get("/vendors")
def predictive_vendors(
    as_of_date: date | None = None,
    priority: str | None = None,
    risk: str | None = None,
    limit: int = Query(default=50, ge=1, le=500),
    scenario: str = "base",
) -> dict[str, Any]:
    return _execute(
        vendor_scores,
        as_of_date=as_of_date,
        priority=priority,
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
        payment_priorities, as_of_date=as_of_date, limit=limit, scenario=scenario
    )


@router.get("/deferrable")
def predictive_deferrable(
    as_of_date: date | None = None,
    limit: int = Query(default=20, ge=1, le=500),
    scenario: str = "base",
) -> dict[str, Any]:
    return _execute(
        deferrable_payments, as_of_date=as_of_date, limit=limit, scenario=scenario
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
