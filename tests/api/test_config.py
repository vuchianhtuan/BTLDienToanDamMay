from sqlalchemy.engine import make_url

from app.config import Settings


def test_database_password_special_characters(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("DB_HOST", "db")
    password = "demo@:/?#%secret"
    monkeypatch.setenv("DB_PASSWORD", password)
    url = make_url(Settings.from_env().database_url)
    assert url.password == password
    assert url.host == "db" and url.database == "integrity"
