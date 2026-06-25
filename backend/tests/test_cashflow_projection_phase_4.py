from fastapi.testclient import TestClient

from app.api.routes import cashflow_projection
from app.main import app


client = TestClient(app)

WEEKLY = {
    "module": "cashflow_projection",
    "summary": {},
    "weeks": [],
    "alerts": [],
    "explanations": [],
    "recommendations": [],
    "limitations": [],
    "warnings": [],
}


def test_router_is_registered() -> None:
    paths = set(app.openapi()["paths"])
    assert "/api/cashflow-projection/payment-behavior" in paths
    assert "/api/cashflow-projection/projectable-documents" in paths
    assert "/api/cashflow-projection/weekly" in paths
    assert "/api/cashflow-projection/scenarios" in paths
    assert "/api/cashflow-projection/executive-summary" in paths


def test_payment_behavior(monkeypatch) -> None:
    monkeypatch.setattr(
        cashflow_projection,
        "get_payment_behavior",
        lambda **kwargs: {"customers": [], "vendors": [], "warnings": []},
    )
    response = client.get("/api/cashflow-projection/payment-behavior")
    assert response.status_code == 200
    assert {"customers", "vendors", "warnings"} <= response.json().keys()


def test_projectable_documents(monkeypatch) -> None:
    monkeypatch.setattr(
        cashflow_projection,
        "projectable_documents",
        lambda **kwargs: {"receivables": [], "payables": [], "warnings": []},
    )
    response = client.get("/api/cashflow-projection/projectable-documents")
    assert response.status_code == 200


def test_weekly_scenarios(monkeypatch) -> None:
    monkeypatch.setattr(
        cashflow_projection, "weekly_projection", lambda **kwargs: WEEKLY
    )
    for scenario in ("base", "optimistic", "pessimistic"):
        response = client.get(
            f"/api/cashflow-projection/weekly?horizon_weeks=13&scenario={scenario}"
        )
        assert response.status_code == 200
        assert {
            "summary", "weeks", "alerts", "explanations",
            "recommendations", "limitations",
        } <= response.json().keys()


def test_scenarios_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(
        cashflow_projection,
        "compare_scenarios",
        lambda **kwargs: {"scenarios": [], "warnings": []},
    )
    response = client.get("/api/cashflow-projection/scenarios")
    assert response.status_code == 200


def test_executive_summary(monkeypatch) -> None:
    monkeypatch.setattr(
        cashflow_projection,
        "executive_summary",
        lambda **kwargs: {
            "title": "Caja",
            "summary": "Resumen",
            "confidence": "low",
            "warnings": [],
        },
    )
    response = client.get("/api/cashflow-projection/executive-summary")
    assert response.status_code == 200


def test_invalid_horizon_is_controlled() -> None:
    response = client.get("/api/cashflow-projection/weekly?horizon_weeks=12")
    assert response.status_code == 422


def test_previous_phase_endpoints_remain_registered() -> None:
    paths = set(app.openapi()["paths"])
    assert "/api/diagnostics/health" in paths
    assert "/api/financial/income-statement" in paths
    assert "/api/forecasting/income-statement/forecast" in paths
