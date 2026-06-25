from dataclasses import dataclass
from functools import lru_cache
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.engine import URL


BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_DIR = BACKEND_DIR.parent

load_dotenv(PROJECT_DIR / ".env.local", override=False)
load_dotenv(BACKEND_DIR / ".env.local", override=False)


def _optional_port(value: str | None) -> int | None:
    if value is None or not value.strip():
        return None
    return int(value)


@dataclass(frozen=True)
class Settings:
    """Local demo settings. Production must use a secret manager."""

    db_server: str = os.getenv("DB_SERVER", "CFR-I7-1")
    db_port: int | None = _optional_port(os.getenv("DB_PORT"))
    db_name: str = os.getenv("DB_NAME", "SBO_MEDINET_MIGRACION")
    db_user: str = os.getenv("DB_USER", "sa")
    db_password: str = os.getenv("DB_PASSWORD", "B1Admin")
    db_driver: str = os.getenv("DB_DRIVER", "ODBC Driver 17 for SQL Server")
    app_env: str = os.getenv("APP_ENV", "local")

    @property
    def database_url(self) -> URL:
        return URL.create(
            "mssql+pyodbc",
            username=self.db_user,
            password=self.db_password,
            host=self.db_server,
            port=self.db_port,
            database=self.db_name,
            query={
                "driver": self.db_driver,
                "TrustServerCertificate": "yes",
            },
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()

