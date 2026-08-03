"""First-run setup wizard tests."""

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Language, User, WorkspaceSettings
from app.models.enums import Role
from tests.conftest import ADMIN_PASSWORD

VALID_SETUP = {
    "workspace_name": "Coffee Terminology",
    "languages": [{"code": "de"}, {"code": "en", "name": "English (UK)"}],
    "admin_email": "admin@example.org",
    "admin_display_name": "Admin",
    "admin_password": ADMIN_PASSWORD,
}


class TestSetupStatus:
    def test_a_fresh_instance_reports_incomplete(self, client: TestClient):
        assert client.get("/api/setup").json() == {"completed": False}

    def test_it_reports_complete_once_an_account_exists(self, client: TestClient, admin: User):
        assert client.get("/api/setup").json() == {"completed": True}


class TestRunningSetup:
    def test_it_creates_the_workspace_languages_and_admin(
        self, client: TestClient, db: Session
    ):
        response = client.post("/api/setup", json=VALID_SETUP)

        assert response.status_code == 201
        assert response.json()["role"] == "admin"

        assert db.scalar(select(WorkspaceSettings)).name == "Coffee Terminology"
        languages = db.scalars(select(Language).order_by(Language.position)).all()
        assert [(language.code, language.name) for language in languages] == [
            ("de", "German"),
            ("en", "English (UK)"),
        ]
        assert db.scalar(select(User)).role == Role.ADMIN

    def test_the_admin_can_sign_in_afterwards(self, client: TestClient):
        client.post("/api/setup", json=VALID_SETUP)

        response = client.post(
            "/api/auth/login",
            json={"email": VALID_SETUP["admin_email"], "password": ADMIN_PASSWORD},
        )

        assert response.status_code == 200

    def test_it_closes_itself_afterwards(self, client: TestClient):
        client.post("/api/setup", json=VALID_SETUP)

        response = client.post("/api/setup", json=VALID_SETUP)

        assert response.status_code == 409

    def test_it_is_refused_when_an_account_already_exists(
        self, client: TestClient, admin: User
    ):
        """The wizard is unauthenticated, so this is what keeps it shut."""
        assert client.post("/api/setup", json=VALID_SETUP).status_code == 409

    def test_an_unknown_language_code_is_rejected(self, client: TestClient, db: Session):
        response = client.post(
            "/api/setup", json={**VALID_SETUP, "languages": [{"code": "klingon"}]}
        )

        assert response.status_code == 422
        assert db.scalar(select(User)) is None

    def test_a_region_tag_is_rejected(self, client: TestClient):
        response = client.post("/api/setup", json={**VALID_SETUP, "languages": [{"code": "de-DE"}]})

        assert response.status_code == 422

    def test_language_codes_are_normalised(self, client: TestClient, db: Session):
        client.post("/api/setup", json={**VALID_SETUP, "languages": [{"code": " DE "}]})

        assert db.scalar(select(Language)).code == "de"

    def test_the_same_language_twice_is_rejected(self, client: TestClient):
        response = client.post(
            "/api/setup", json={**VALID_SETUP, "languages": [{"code": "de"}, {"code": "de"}]}
        )

        assert response.status_code == 422

    def test_at_least_one_language_is_required(self, client: TestClient):
        assert client.post("/api/setup", json={**VALID_SETUP, "languages": []}).status_code == 422

    def test_a_short_admin_password_is_rejected(self, client: TestClient, db: Session):
        response = client.post("/api/setup", json={**VALID_SETUP, "admin_password": "short"})

        assert response.status_code == 422
        assert db.scalar(select(User)) is None

    def test_the_response_does_not_contain_the_password(self, client: TestClient):
        response = client.post("/api/setup", json=VALID_SETUP)

        assert ADMIN_PASSWORD not in response.text
        assert "password_hash" not in response.text
