from fastapi.testclient import TestClient

from app.api.routes import diagnostics, forecasting
from app.main import app


client = TestClient(app)

SAMPLE_DATASET = {
    "target": "income_statement_gross_margin",
    "periods": [
        {
            "period": f"2024-{month:02d}",
            "year": 2024,
            "month": month,
            "revenue": 100 + month,
            "cost_of_sales": 60 + month,
            "gross_profit": 40,
            "gross_margin_pct": 40,
            "budget_revenue": None,
            "budget_cost": None,
            "budget_gross_profit": None,
            "budget_gross_margin_pct": None,
        }
        for month in range(1, 13)
    ],
    "warnings": [],
}

SAMPLE_FORECAST = {
    "module": "income_statement_forecast",
    "selected_models": {},
    "forecast_periods": [],
    "explanations": [],
    "recommendations": [],
    "limitations": [],
    "warnings": [],
}


def test_forecasting_router_is_registered() -> None:
    paths = set(app.openapi()["paths"])
    assert "/api/forecasting/income-statement/dataset" in paths
    assert "/api/forecasting/income-statement/backtest" in paths
    assert "/api/forecasting/income-statement/forecast" in paths
    assert "/api/forecasting/income-statement/executive-summary" in paths


def test_dataset_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(
        forecasting, "build_income_statement_dataset", lambda **kwargs: SAMPLE_DATASET
    )
    response = client.get("/api/forecasting/income-statement/dataset")
    assert response.status_code == 200
    assert {"target", "periods", "warnings"} <= response.json().keys()


def test_backtest_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(
        forecasting, "build_income_statement_dataset", lambda **kwargs: SAMPLE_DATASET
    )
    response = client.get("/api/forecasting/income-statement/backtest")
    assert response.status_code == 200
    assert {"test_months", "results", "warnings"} <= response.json().keys()


def test_forecast_horizon_3(monkeypatch) -> None:
    monkeypatch.setattr(forecasting, "generate_forecast", lambda **kwargs: SAMPLE_FORECAST)
    response = client.get("/api/forecasting/income-statement/forecast?horizon=3")
    assert response.status_code == 200
    assert {
        "selected_models", "forecast_periods", "explanations",
        "recommendations", "limitations",
    } <= response.json().keys()


def test_forecast_horizon_6(monkeypatch) -> None:
    monkeypatch.setattr(forecasting, "generate_forecast", lambda **kwargs: SAMPLE_FORECAST)
    response = client.get("/api/forecasting/income-statement/forecast?horizon=6")
    assert response.status_code == 200


def test_executive_summary(monkeypatch) -> None:
    monkeypatch.setattr(
        forecasting,
        "executive_summary",
        lambda **kwargs: {
            "title": "Proyección",
            "summary": "Resumen",
            "key_findings": [],
            "risks": [],
            "recommended_actions": [],
            "confidence": "medium",
            "warnings": [],
        },
    )
    response = client.get("/api/forecasting/income-statement/executive-summary")
    assert response.status_code == 200
    assert {"title", "summary", "confidence"} <= response.json().keys()


def test_invalid_horizon_returns_422() -> None:
    response = client.get("/api/forecasting/income-statement/forecast?horizon=4")
    assert response.status_code == 422


def test_previous_phase_routes_remain_registered() -> None:
    paths = set(app.openapi()["paths"])
    assert "/api/diagnostics/health" in paths
    assert "/api/financial/income-statement" in paths


def test_health_still_works(monkeypatch) -> None:
    monkeypatch.setattr(
        diagnostics,
        "test_connection",
        lambda: {"status": "ok", "database_connection": True},
    )
    response = client.get("/api/diagnostics/health")
    assert response.status_code == 200
