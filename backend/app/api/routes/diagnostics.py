from fastapi import APIRouter

from app.core.config import get_settings
from app.core.database import DatabaseConnectionError, test_connection
from app.services.sap_diagnostics import run_sap_diagnostics


router = APIRouter(prefix="/api/diagnostics", tags=["diagnostics"])


@router.get("/health")
def diagnostics_health() -> dict:
    settings = get_settings()
    try:
        return test_connection()
    except DatabaseConnectionError as exc:
        return {
            "status": "error",
            "database_connection": False,
            "database": settings.db_name,
            "server": settings.db_server,
            "message": str(exc),
        }


@router.get("/sap-data")
def sap_data_diagnostics() -> dict:
    return run_sap_diagnostics()

