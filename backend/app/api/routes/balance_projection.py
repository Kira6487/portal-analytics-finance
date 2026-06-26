from datetime import date
from typing import Any, Callable

from fastapi import APIRouter, HTTPException, Query

from app.services.balance_projection.analysis import executive_summary
from app.services.balance_projection.dataset import build_projection_dataset
from app.services.balance_projection.drivers import drivers_analysis
from app.services.balance_projection.projection_engine import weekly_balance_projection
from app.services.balance_projection.scenarios import compare_scenarios


router = APIRouter(prefix="/api/balance-projection", tags=["balance-projection"])


def _execute(operation: Callable[..., dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
    try:
        return operation(**kwargs)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        return {
            "status": "error",
            "warnings": [f"No se pudo completar el Balance proyectado: {exc}"],
            "limitations": ["El error fue controlado y no se modifico SAP."],
            "currency": "SOL",
            "currency_symbol": "S/",
        }


@router.get("/dataset")
def projection_dataset(
    basis_date: date | None = None,
    opening_cash: float | None = Query(default=None),
    scenario: str = "base",
) -> dict[str, Any]:
    return _execute(
        build_projection_dataset,
        basis_date=basis_date,
        opening_cash=opening_cash,
        scenario=scenario,
    )


@router.get("/weekly")
def projection_weekly(
    basis_date: date | None = None,
    horizon_weeks: int = Query(default=13, ge=1, le=52),
    scenario: str = "base",
    opening_cash: float | None = Query(default=None),
) -> dict[str, Any]:
    return _execute(
        weekly_balance_projection,
        basis_date=basis_date,
        horizon_weeks=horizon_weeks,
        scenario=scenario,
        opening_cash=opening_cash,
    )


@router.get("/scenarios")
def projection_scenarios(
    basis_date: date | None = None,
    horizon_weeks: int = Query(default=13, ge=1, le=52),
    opening_cash: float | None = Query(default=None),
) -> dict[str, Any]:
    return _execute(
        compare_scenarios,
        basis_date=basis_date,
        horizon_weeks=horizon_weeks,
        opening_cash=opening_cash,
    )


@router.get("/drivers")
def projection_drivers(
    basis_date: date | None = None,
    horizon_weeks: int = Query(default=13, ge=1, le=52),
    scenario: str = "base",
    opening_cash: float | None = Query(default=None),
) -> dict[str, Any]:
    return _execute(
        drivers_analysis,
        basis_date=basis_date,
        horizon_weeks=horizon_weeks,
        scenario=scenario,
        opening_cash=opening_cash,
    )


@router.get("/executive-summary")
def projection_executive_summary(
    basis_date: date | None = None,
    horizon_weeks: int = Query(default=13, ge=1, le=52),
    scenario: str = "base",
    opening_cash: float | None = Query(default=None),
) -> dict[str, Any]:
    return _execute(
        executive_summary,
        basis_date=basis_date,
        horizon_weeks=horizon_weeks,
        scenario=scenario,
        opening_cash=opening_cash,
    )
