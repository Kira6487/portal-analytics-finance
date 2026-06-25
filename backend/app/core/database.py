from functools import lru_cache
from typing import Any

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings


class DatabaseConnectionError(RuntimeError):
    """Database failure suitable for API responses."""


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    try:
        return create_engine(
            settings.database_url,
            pool_pre_ping=True,
            pool_recycle=1800,
            connect_args={"timeout": 10},
        )
    except (SQLAlchemyError, ValueError, ModuleNotFoundError) as exc:
        raise DatabaseConnectionError(
            "No se pudo configurar SQL Server. Revise pyodbc, el driver ODBC "
            "y las variables de conexión."
        ) from exc


def get_connection():
    """Return a SQLAlchemy connection. The caller must close it."""
    try:
        return get_engine().connect()
    except (SQLAlchemyError, DatabaseConnectionError) as exc:
        raise DatabaseConnectionError(
            f"No fue posible conectar con SQL Server: {exc}"
        ) from exc


def test_connection() -> dict[str, Any]:
    settings = get_settings()
    try:
        with get_connection() as connection:
            row = connection.execute(
                text(
                    """
                    SELECT
                        1 AS TestConnection,
                        DB_NAME() AS database_name,
                        SYSDATETIME() AS server_datetime
                    """
                )
            ).mappings().one()
        return {
            "status": "ok",
            "database_connection": row["TestConnection"] == 1,
            "database": row["database_name"],
            "server": settings.db_server,
            "server_datetime": row["server_datetime"],
            "message": "Conexión exitosa a SAP B1 SQL Server",
        }
    except (SQLAlchemyError, DatabaseConnectionError) as exc:
        raise DatabaseConnectionError(str(exc)) from exc

