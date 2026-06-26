from fastapi.testclient import TestClient

from app.api.routes import balance_projection
from app.main import app


client = TestClient(app)


def test_router_is_registered() -> None:
    paths = set(app.openapi()["paths"])
    for path in (
        "/api/balance-projection/dataset",
        "/api/balance-projection/weekly",
        "/api/balance-projection/scenarios",
        "/api/balance-projection/drivers",
        "/api/balance-projection/executive-summary",
    ):
        assert path in paths


def test_dataset_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(
        balance_projection,
        "build_projection_dataset",
        lambda **kwargs: {
            "module": "balance_projection",
            "basis_date": "2025-12-31",
            "currency": "SOL",
            "currency_symbol": "S/",
            "base_balance": {},
            "inputs": {},
            "warnings": [],
            "limitations": [],
        },
    )
    response = client.get("/api/balance-projection/dataset")
    assert response.status_code == 200
    assert response.json()["currency"] == "SOL"


def test_weekly_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(
        balance_projection,
        "weekly_balance_projection",
        lambda **kwargs: {
            "module": "balance_projection_weekly",
            "basis_date": "2025-12-31",
            "horizon_weeks": 13,
            "scenario": "base",
            "currency": "SOL",
            "currency_symbol": "S/",
            "summary": {},
            "weeks": [],
            "ratios": {},
            "alerts": [],
            "explanations": [],
            "recommendations": [],
            "limitations": [],
            "warnings": [],
        },
    )
    response = client.get("/api/balance-projection/weekly")
    assert response.status_code == 200
    data = response.json()
    assert {
        "summary",
        "weeks",
        "ratios",
        "alerts",
        "explanations",
        "recommendations",
        "limitations",
    } <= data.keys()
    assert data["currency"] == "SOL"


def test_scenarios_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(
        balance_projection,
        "compare_scenarios",
        lambda **kwargs: {
            "module": "balance_projection_scenarios",
            "basis_date": "2025-12-31",
            "horizon_weeks": 13,
            "currency": "SOL",
            "currency_symbol": "S/",
            "scenarios": [],
            "comparison_explanation": "",
            "recommendations": [],
            "limitations": [],
            "warnings": [],
        },
    )
    response = client.get("/api/balance-projection/scenarios")
    assert response.status_code == 200


def test_drivers_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(
        balance_projection,
        "drivers_analysis",
        lambda **kwargs: {
            "module": "balance_projection_drivers",
            "currency": "SOL",
            "currency_symbol": "S/",
            "top_positive_drivers": [],
            "top_negative_drivers": [],
            "cash_drivers": [],
            "working_capital_drivers": [],
            "explanations": [],
            "warnings": [],
        },
    )
    response = client.get("/api/balance-projection/drivers")
    assert response.status_code == 200


def test_executive_summary_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(
        balance_projection,
        "executive_summary",
        lambda **kwargs: {
            "title": "Balance proyectado",
            "summary": "Resumen",
            "key_findings": [],
            "risks": [],
            "recommended_actions": [],
            "confidence": "low",
            "currency": "SOL",
            "currency_symbol": "S/",
            "limitations": [],
            "warnings": [],
        },
    )
    response = client.get("/api/balance-projection/executive-summary")
    assert response.status_code == 200
    assert response.json()["currency"] == "SOL"


def test_invalid_filters_are_controlled() -> None:
    scenario_response = client.get("/api/balance-projection/weekly?scenario=stress")
    horizon_response = client.get("/api/balance-projection/weekly?horizon_weeks=9")
    assert scenario_response.status_code == 422
    assert horizon_response.status_code == 422


def test_backend_returns_controlled_error(monkeypatch) -> None:
    def fail(**kwargs):
        raise RuntimeError("SQL Server/ODBC unavailable")

    monkeypatch.setattr(balance_projection, "build_projection_dataset", fail)
    response = client.get("/api/balance-projection/dataset")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert data["currency"] == "SOL"


def test_previous_phase_routes_remain_registered() -> None:
    paths = set(app.openapi()["paths"])
    assert "/api/diagnostics/health" in paths
    assert "/api/financial/balance-summary" in paths
    assert "/api/forecasting/income-statement/forecast" in paths
    assert "/api/cashflow-projection/weekly" in paths
    assert "/api/receivables-predictive/dataset" in paths
    assert "/api/payables-predictive/dataset" in paths
