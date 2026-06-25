from datetime import date
from typing import Any, Callable

from fastapi import APIRouter, HTTPException, Query

from app.services.cashflow_projection.datasets import projectable_documents
from app.services.cashflow_projection.payment_behavior import get_payment_behavior
from app.services.cashflow_projection.projection_engine import weekly_projection
from app.services.cashflow_projection.scenarios import (
    compare_scenarios,
    executive_summary,
)


router = APIRouter(prefix="/api/cashflow-projection", tags=["cashflow-projection"])


def _execute(operation: Callable[..., dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
    try:
        return operation(**kwargs)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        return {
            "status": "error",
            "warnings": [f"No se pudo completar la proyección de caja: {exc}"],
            "limitations": ["El error fue controlado y no se modificó información en SAP."],
        }


@router.get("/payment-behavior")
def payment_behavior(
    behavior_type: str = Query(default="all", alias="type"),
    limit: int = Query(default=50, ge=1, le=500),
) -> dict[str, Any]:
    return _execute(
        get_payment_behavior, behavior_type=behavior_type, limit=limit
    )


@router.get("/projectable-documents")
def get_projectable_documents(
    basis_date: date | None = None,
    scenario: str = "base",
) -> dict[str, Any]:
    return _execute(
        projectable_documents, basis_date=basis_date, scenario=scenario
    )


@router.get("/weekly")
def get_weekly_projection(
    basis_date: date | None = None,
    horizon_weeks: int = 13,
    scenario: str = "base",
    opening_cash: float | None = None,
) -> dict[str, Any]:
    return _execute(
        weekly_projection,
        basis_date=basis_date,
        horizon_weeks=horizon_weeks,
        scenario=scenario,
        opening_cash=opening_cash,
    )


@router.get("/scenarios")
def get_scenario_comparison(
    basis_date: date | None = None,
    horizon_weeks: int = 13,
    opening_cash: float | None = None,
) -> dict[str, Any]:
    return _execute(
        compare_scenarios,
        basis_date=basis_date,
        horizon_weeks=horizon_weeks,
        opening_cash=opening_cash,
    )


@router.get("/executive-summary")
def get_executive_summary(
    basis_date: date | None = None,
    horizon_weeks: int = 13,
    scenario: str = "base",
    opening_cash: float | None = None,
) -> dict[str, Any]:
    return _execute(
        executive_summary,
        basis_date=basis_date,
        horizon_weeks=horizon_weeks,
        scenario=scenario,
        opening_cash=opening_cash,
    )
