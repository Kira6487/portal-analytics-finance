from pathlib import Path
import sys


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import get_settings  # noqa: E402
from app.core.database import DatabaseConnectionError, test_connection  # noqa: E402
from app.services.sap_diagnostics import run_sap_diagnostics  # noqa: E402


def main() -> int:
    settings = get_settings()
    print("=== Analytics Finance SAP B1 | Fase 1 ===")
    print(f"Servidor: {settings.db_server}")
    print(f"Base de datos: {settings.db_name}")
    print(f"Driver: {settings.db_driver}")
    try:
        health = test_connection()
        print(f"Conexión: {health['message']}")
    except DatabaseConnectionError as exc:
        print(f"Conexión: ERROR - {exc}")
        return 1

    result = run_sap_diagnostics()
    accounting = result.get("accounting_data", {})
    tables = result.get("tables", {})
    detected = sum(1 for exists in tables.values() if exists)
    print(f"Fecha mínima de asientos: {accounting.get('min_date')}")
    print(f"Fecha máxima de asientos: {accounting.get('max_date')}")
    print(f"Tablas detectadas: {detected}/{len(tables)}")
    print(f"Meses disponibles: {accounting.get('available_months', 0)}")
    print(
        "Conclusión inicial: "
        f"{result.get('forecast_readiness', {}).get('general_conclusion', 'No disponible')}"
    )
    limitations = result.get("limitations", [])
    print("Limitaciones:")
    if limitations:
        for limitation in limitations:
            print(f"- {limitation}")
    else:
        print("- No se detectaron limitaciones automáticas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

