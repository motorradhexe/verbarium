from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app

client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["name"] == "Verbarium"


def test_health_reports_the_configured_database():
    """The reported backend must match the configuration.

    CI runs this suite once per supported database. Without asserting the
    connection, the PostgreSQL run would pass even with no server reachable.
    """
    settings = get_settings()

    payload = client.get("/health").json()

    assert payload["database"]["backend"] == settings.db_backend
    assert payload["database"]["connected"] is True
