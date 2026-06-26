from fastapi.testclient import TestClient

from app.api.routes import payables_predictive
from app.main import app


client = TestClient(app)

SAMPLE_ITEM = {
    "payment_priority_score": 85,
    "payment_priority_level": "urgent",
    "estimated_payment_date": "2026-01-15",
    "recommended_payment_date": "2026-01-15",
    "risk_score": 70,
    "risk_level": "high",
    "currency": "SOL",
    "currency_symbol": "S/",
}


def test_router_is_registered() -> None:
    paths = set(app.openapi()["paths"])
    for path in (
        "/api/payables-predictive/dataset",
        "/api/payables-predictive/vendors",
        "/api/payables-predictive/priorities",
        "/api/payables-predictive/deferrable",
        "/api/payables-predictive/concentration",
        "/api/payables-predictive/executive-summary",
    ):
        assert path in paths


def test_dataset_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(
        payables_predictive,
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
    response = client.get("/api/payables-predictive/dataset")
    assert response.status_code == 200
    data = response.json()
    assert data["currency"] == "SOL"
    assert {
        "payment_priority_score",
        "payment_priority_level",
        "estimated_payment_date",
        "recommended_payment_date",
        "risk_score",
        "risk_level",
        "currency",
        "currency_symbol",
    } <= data["items"][0].keys()


def test_vendors_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(
        payables_predictive,
        "vendor_scores",
        lambda **kwargs: {
            "vendors": [],
            "summary": {},
            "currency": "SOL",
            "currency_symbol": "S/",
            "warnings": [],
        },
    )
    response = client.get("/api/payables-predictive/vendors")
    assert response.status_code == 200


def test_priorities_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(
        payables_predictive,
        "payment_priorities",
        lambda **kwargs: {
            "summary": {},
            "items": [],
            "currency": "SOL",
            "currency_symbol": "S/",
            "warnings": [],
        },
    )
    response = client.get("/api/payables-predictive/priorities")
    assert response.status_code == 200


def test_deferrable_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(
        payables_predictive,
        "deferrable_payments",
        lambda **kwargs: {
            "summary": {},
            "items": [],
            "limitations": [],
            "currency": "SOL",
            "currency_symbol": "S/",
            "warnings": [],
        },
    )
    response = client.get("/api/payables-predictive/deferrable")
    assert response.status_code == 200


def test_concentration_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(
        payables_predictive,
        "concentration_analysis",
        lambda **kwargs: {
            "summary": {},
            "top_vendors": [],
            "currency": "SOL",
            "currency_symbol": "S/",
            "warnings": [],
        },
    )
    response = client.get("/api/payables-predictive/concentration")
    assert response.status_code == 200


def test_executive_summary_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(
        payables_predictive,
        "executive_summary",
        lambda **kwargs: {
            "title": "CxP",
            "summary": "Resumen",
            "confidence": "medium",
            "currency": "SOL",
            "currency_symbol": "S/",
            "warnings": [],
        },
    )
    response = client.get("/api/payables-predictive/executive-summary")
    assert response.status_code == 200
    assert response.json()["currency"] == "SOL"


def test_invalid_filters_are_controlled() -> None:
    risk_response = client.get("/api/payables-predictive/dataset?risk=unknown")
    priority_response = client.get("/api/payables-predictive/dataset?priority=unknown")
    scenario_response = client.get("/api/payables-predictive/dataset?scenario=stress")
    assert risk_response.status_code == 422
    assert priority_response.status_code == 422
    assert scenario_response.status_code == 422


def test_previous_phase_routes_remain_registered() -> None:
    paths = set(app.openapi()["paths"])
    assert "/api/diagnostics/health" in paths
    assert "/api/financial/payables/open" in paths
    assert "/api/forecasting/income-statement/forecast" in paths
    assert "/api/cashflow-projection/weekly" in paths
    assert "/api/receivables-predictive/dataset" in paths
