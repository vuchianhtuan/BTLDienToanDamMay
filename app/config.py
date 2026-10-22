"""Environment settings; never place deployment credentials in source code."""
import os
from dataclasses import dataclass
from sqlalchemy.engine import URL


@dataclass(frozen=True)
class Settings:
    database_url: str
    storage_backend: str
    storage_path: str
    max_file_bytes: int
    api_key: str

    @classmethod
    def from_env(cls):
        database_url = os.getenv("DATABASE_URL")
        if not database_url and os.getenv("DB_HOST"):
            database_url = URL.create(
                "postgresql+psycopg", username=os.getenv("DB_USER", "integrity"),
                password=os.getenv("DB_PASSWORD", ""), host=os.environ["DB_HOST"],
                port=int(os.getenv("DB_PORT", "5432")), database=os.getenv("DB_NAME", "integrity"),
            ).render_as_string(hide_password=False)
        return cls(
            database_url=database_url or "sqlite:///./integrity.db",
            storage_backend=os.getenv("STORAGE_BACKEND", "local"),
            storage_path=os.getenv("LOCAL_STORAGE_PATH", "./data"),
            max_file_bytes=int(os.getenv("MAX_FILE_BYTES", str(25 * 1024 * 1024))),
            api_key=os.getenv("APP_API_KEY", ""),
        )
