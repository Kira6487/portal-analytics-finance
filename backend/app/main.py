from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.diagnostics import router as diagnostics_router
from app.api.routes.financial import router as financial_router
from app.api.routes.forecasting import router as forecasting_router
from app.api.routes.cashflow_projection import router as cashflow_projection_router
from app.api.routes.receivables_predictive import router as receivables_predictive_router
from app.api.routes.payables_predictive import router as payables_predictive_router


app = FastAPI(
    title="Analytics Finance SAP B1",
    description="API de solo lectura para diagnóstico financiero de SAP Business One.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(diagnostics_router)
app.include_router(financial_router)
app.include_router(forecasting_router)
app.include_router(cashflow_projection_router)
app.include_router(receivables_predictive_router)
app.include_router(payables_predictive_router)


@app.get("/")
def root() -> dict:
    return {
        "name": "Analytics Finance SAP B1",
        "phase": "Fase 6 - Cuentas por pagar predictivas",
        "docs": "/docs",
    }
