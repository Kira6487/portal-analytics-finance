from fastapi.testclient import TestClient

from app.api.routes import diagnostics, financial
from app.main import app


client = TestClient(app)


def test_financial_router_is_registered() -> None:
    paths = set(app.openapi()["paths"])
    assert "/api/financial/metadata" in paths
    assert "/api/financial/income-statement" in paths
    assert "/api/financial/budget/simulated" in paths


def test_metadata_response(monkeypatch) -> None:
    monkeypatch.setattr(
        financial,
        "metadata",
        lambda: {
            "available_period": {},
            "dimensions": {},
            "budget": {},
            "warnings": [],
        },
    )
    response = client.get("/api/financial/metadata")
    assert response.status_code == 200
    assert {"available_period", "dimensions", "budget"} <= response.json().keys()


def test_income_statement_response(monkeypatch) -> None:
    monkeypatch.setattr(
        financial,
        "income_statement",
        lambda **kwargs: {
            "filters": kwargs,
            "summary": {},
            "periods": [],
            "warnings": ["Sin datos"],
        },
    )
    response = client.get("/api/financial/income-statement?year=1900")
    assert response.status_code == 200
    assert {"filters", "summary", "periods", "warnings"} <= response.json().keys()


def test_simulated_budget_response(monkeypatch) -> None:
    monkeypatch.setattr(
        financial,
        "simulated_budget",
        lambda **kwargs: {
            "budget_type": "simulated",
            "periods": [],
            "warnings": [],
        },
    )
    response = client.get("/api/financial/budget/simulated")
    assert response.status_code == 200
    assert response.json()["budget_type"] == "simulated"


def test_health_endpoint_remains_available(monkeypatch) -> None:
    monkeypatch.setattr(
        diagnostics,
        "test_connection",
        lambda: {"status": "ok", "database_connection": True},
    )
    response = client.get("/api/diagnostics/health")
    assert response.status_code == 200
    assert response.json()["database_connection"] is True


def test_invalid_financial_filter_returns_422() -> None:
    response = client.get("/api/financial/income-statement?month=13")
    assert response.status_code == 422
