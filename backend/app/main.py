from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.diagnostics import router as diagnostics_router


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


@app.get("/")
def root() -> dict:
    return {
        "name": "Analytics Finance SAP B1",
        "phase": "Fase 1 - Diagnóstico de datos",
        "docs": "/docs",
    }

