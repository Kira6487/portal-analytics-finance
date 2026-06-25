from fastapi.testclient import TestClient

from app.api.routes import receivables_predictive
from app.main import app


client = TestClient(app)

SAMPLE_ITEM = {
    "risk_score": 60,
    "risk_level": "high",
    "estimated_collection_date": "2026-01-15",
    "priority_score": 80,
    "priority_level": "urgent",
    "currency": "SOL",
}


def test_router_is_registered() -> None:
    paths = set(app.openapi()["paths"])
    for path in (
        "/api/receivables-predictive/dataset",
        "/api/receivables-predictive/customers",
        "/api/receivables-predictive/priorities",
        "/api/receivables-predictive/concentration",
        "/api/receivables-predictive/executive-summary",
    ):
        assert path in paths


def test_dataset_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(
        receivables_predictive,
        "build_predictive_dataset",
        lambda **kwargs: {
            "currency": "SOL",
            "currency_symbol": "S/",
            "summary": {},
            "items": [SAMPLE_ITEM],
            "limitations": [],
            "warnings": [],
        },
    )
    response = client.get("/api/receivables-predictive/dataset")
    assert response.status_code == 200
    data = response.json()
    assert data["currency"] == "SOL"
    assert {
        "risk_score", "risk_level", "estimated_collection_date",
        "priority_score", "priority_level", "currency",
    } <= data["items"][0].keys()


def test_customers_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(
        receivables_predictive,
        "customer_scores",
        lambda **kwargs: {
            "customers": [],
            "summary": {},
            "currency": "SOL",
            "currency_symbol": "S/",
            "warnings": [],
        },
    )
    response = client.get("/api/receivables-predictive/customers")
    assert response.status_code == 200


def test_priorities_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(
        receivables_predictive,
        "collection_priorities",
        lambda **kwargs: {
            "summary": {},
            "items": [],
            "currency": "SOL",
            "currency_symbol": "S/",
            "warnings": [],
        },
    )
    response = client.get("/api/receivables-predictive/priorities")
    assert response.status_code == 200


def test_concentration_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(
        receivables_predictive,
        "concentration_analysis",
        lambda **kwargs: {
            "summary": {},
            "top_customers": [],
            "currency": "SOL",
            "currency_symbol": "S/",
            "warnings": [],
        },
    )
    response = client.get("/api/receivables-predictive/concentration")
    assert response.status_code == 200


def test_executive_summary_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(
        receivables_predictive,
        "executive_summary",
        lambda **kwargs: {
            "title": "CxC",
            "summary": "Resumen",
            "confidence": "medium",
            "currency": "SOL",
            "currency_symbol": "S/",
            "warnings": [],
        },
    )
    response = client.get("/api/receivables-predictive/executive-summary")
    assert response.status_code == 200
    assert response.json()["currency"] == "SOL"


def test_invalid_risk_is_controlled() -> None:
    response = client.get("/api/receivables-predictive/dataset?risk=unknown")
    assert response.status_code == 422


def test_previous_phase_routes_remain_registered() -> None:
    paths = set(app.openapi()["paths"])
    assert "/api/diagnostics/health" in paths
    assert "/api/financial/receivables/open" in paths
    assert "/api/forecasting/income-statement/forecast" in paths
    assert "/api/cashflow-projection/weekly" in paths
