"""Authentication tests.

Weighted towards what must *not* happen: the happy path shows up in the first
manual click-through, a missing authorisation check does not.
"""

import uuid
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password, hash_session_token, verify_password
from app.db.base import utcnow
from app.models import User, UserSession
from app.models.enums import Role
from tests.conftest import ADMIN_PASSWORD, USER_PASSWORD, sign_in

COOKIE = get_settings().session_cookie_name


@pytest.fixture
def viewer(db: Session) -> User:
    account = User(
        email="viewer@example.org",
        display_name="Viewer",
        password_hash=hash_password(USER_PASSWORD),
        role=Role.VIEWER,
    )
    db.add(account)
    db.commit()
    return account


class TestPasswordHashing:
    def test_the_hash_does_not_contain_the_password(self):
        stored = hash_password(ADMIN_PASSWORD)

        assert ADMIN_PASSWORD not in stored
        assert stored.startswith("$argon2id$")

    def test_the_same_password_hashes_differently_each_time(self):
        """Per-hash salt: identical passwords must not produce identical rows."""
        assert hash_password(ADMIN_PASSWORD) != hash_password(ADMIN_PASSWORD)

    def test_verification_accepts_the_password_and_rejects_others(self):
        stored = hash_password(ADMIN_PASSWORD)

        assert verify_password(ADMIN_PASSWORD, stored)
        assert not verify_password(ADMIN_PASSWORD + "x", stored)

    def test_a_malformed_hash_is_rejected_rather_than_raising(self):
        assert not verify_password(ADMIN_PASSWORD, "not-a-hash")


class TestLogin:
    def test_valid_credentials_return_the_profile_and_set_a_cookie(
        self, client: TestClient, admin: User
    ):
        response = client.post(
            "/api/auth/login", json={"email": admin.email, "password": ADMIN_PASSWORD}
        )

        assert response.status_code == 200
        assert response.json()["email"] == admin.email
        assert "password_hash" not in response.json()
        assert COOKIE in response.cookies

    def test_the_session_cookie_is_http_only(self, client: TestClient, admin: User):
        """Not readable from JavaScript, so an XSS bug cannot lift the session."""
        response = client.post(
            "/api/auth/login", json={"email": admin.email, "password": ADMIN_PASSWORD}
        )

        header = response.headers["set-cookie"].lower()
        assert "httponly" in header
        assert "samesite=lax" in header

    def test_a_wrong_password_is_rejected(self, client: TestClient, admin: User):
        response = client.post(
            "/api/auth/login", json={"email": admin.email, "password": "wrong-password"}
        )

        assert response.status_code == 401
        assert COOKIE not in response.cookies

    def test_an_unknown_address_gives_the_same_answer_as_a_wrong_password(
        self, client: TestClient, admin: User
    ):
        """No user enumeration through differing responses."""
        unknown = client.post(
            "/api/auth/login", json={"email": "nobody@example.org", "password": "whatever-it-is"}
        )
        wrong = client.post(
            "/api/auth/login", json={"email": admin.email, "password": "wrong-password"}
        )

        assert unknown.status_code == wrong.status_code == 401
        assert unknown.json() == wrong.json()

    def test_a_deactivated_account_cannot_sign_in(
        self, client: TestClient, db: Session, viewer: User
    ):
        viewer.is_active = False
        db.commit()

        response = client.post(
            "/api/auth/login", json={"email": viewer.email, "password": USER_PASSWORD}
        )

        assert response.status_code == 401

    def test_the_address_is_matched_case_insensitively(self, client: TestClient, admin: User):
        response = client.post(
            "/api/auth/login", json={"email": "ADMIN@Example.ORG", "password": ADMIN_PASSWORD}
        )

        assert response.status_code == 200


class TestSessions:
    def test_only_the_token_hash_is_stored(self, client: TestClient, db: Session, admin: User):
        """A leaked database must not hand over usable sessions."""
        response = client.post(
            "/api/auth/login", json={"email": admin.email, "password": ADMIN_PASSWORD}
        )
        token = response.cookies[COOKIE]

        stored = db.scalars(select(UserSession)).all()
        assert len(stored) == 1
        assert stored[0].token_hash != token
        assert stored[0].token_hash == hash_session_token(token)

    def test_the_session_identifies_the_user(self, client: TestClient, admin: User):
        sign_in(client, admin.email, ADMIN_PASSWORD)

        response = client.get("/api/auth/me")

        assert response.status_code == 200
        assert response.json()["email"] == admin.email

    def test_without_a_cookie_there_is_no_user(self, client: TestClient):
        assert client.get("/api/auth/me").status_code == 401

    def test_timestamps_carry_a_timezone_when_read_from_the_database(
        self, client: TestClient, db: Session, admin: User
    ):
        """SQLite hands back naive datetimes, PostgreSQL does not.

        Without normalising, the same field serialises with an offset when the
        object was just created and without one when it was loaded, and a
        client would read the second form as local time.
        """
        sign_in(client, admin.email, ADMIN_PASSWORD)
        db.expire_all()

        created_at = client.get("/api/auth/me").json()["created_at"]

        assert created_at.endswith("Z") or created_at.endswith("+00:00"), created_at

    def test_an_invented_token_is_rejected(self, client: TestClient, admin: User):
        client.cookies.set(COOKIE, "a-token-nobody-issued")

        assert client.get("/api/auth/me").status_code == 401

    def test_an_expired_session_is_rejected_and_removed(
        self, client: TestClient, db: Session, admin: User
    ):
        sign_in(client, admin.email, ADMIN_PASSWORD)
        session = db.scalars(select(UserSession)).one()
        session.expires_at = utcnow() - timedelta(seconds=1)
        db.commit()

        assert client.get("/api/auth/me").status_code == 401
        assert db.scalars(select(UserSession)).all() == []

    def test_logout_ends_the_session(self, client: TestClient, db: Session, admin: User):
        sign_in(client, admin.email, ADMIN_PASSWORD)

        assert client.post("/api/auth/logout").status_code == 204
        assert db.scalars(select(UserSession)).all() == []
        assert client.get("/api/auth/me").status_code == 401

    def test_logging_out_twice_is_not_an_error(self, client: TestClient, admin: User):
        sign_in(client, admin.email, ADMIN_PASSWORD)
        client.post("/api/auth/logout")

        assert client.post("/api/auth/logout").status_code == 204

    def test_deactivating_an_account_ends_its_sessions(
        self, client: TestClient, db: Session, admin: User, viewer: User
    ):
        """An account switched off must lose access immediately, not at expiry."""
        other = TestClient(client.app)
        other.post("/api/auth/login", json={"email": viewer.email, "password": USER_PASSWORD})
        assert other.get("/api/auth/me").status_code == 200

        sign_in(client, admin.email, ADMIN_PASSWORD)
        client.patch(f"/api/users/{viewer.id}", json={"is_active": False})

        assert other.get("/api/auth/me").status_code == 401


class TestPasswordChange:
    def test_changing_the_password_requires_the_current_one(
        self, client: TestClient, admin: User
    ):
        sign_in(client, admin.email, ADMIN_PASSWORD)

        response = client.post(
            "/api/auth/password",
            json={"current_password": "not-it", "new_password": "a-brand-new-passphrase"},
        )

        assert response.status_code == 403

    def test_a_new_password_replaces_the_old_one(
        self, client: TestClient, db: Session, admin: User
    ):
        sign_in(client, admin.email, ADMIN_PASSWORD)
        new_password = "a-brand-new-passphrase"

        assert (
            client.post(
                "/api/auth/password",
                json={"current_password": ADMIN_PASSWORD, "new_password": new_password},
            ).status_code
            == 204
        )

        db.expire_all()
        assert verify_password(new_password, db.get(User, admin.id).password_hash)

    def test_changing_the_password_signs_every_session_out(
        self, client: TestClient, db: Session, admin: User
    ):
        """The way to react to a suspected compromise."""
        elsewhere = TestClient(client.app)
        elsewhere.post("/api/auth/login", json={"email": admin.email, "password": ADMIN_PASSWORD})
        sign_in(client, admin.email, ADMIN_PASSWORD)

        client.post(
            "/api/auth/password",
            json={"current_password": ADMIN_PASSWORD, "new_password": "a-brand-new-passphrase"},
        )

        assert elsewhere.get("/api/auth/me").status_code == 401

    def test_a_short_password_is_rejected(self, client: TestClient, admin: User):
        sign_in(client, admin.email, ADMIN_PASSWORD)

        response = client.post(
            "/api/auth/password",
            json={"current_password": ADMIN_PASSWORD, "new_password": "short"},
        )

        assert response.status_code == 422


class TestRoles:
    def test_a_viewer_cannot_reach_admin_routes(self, client: TestClient, viewer: User):
        sign_in(client, viewer.email, USER_PASSWORD)

        assert client.get("/api/users").status_code == 403

    def test_an_admin_can(self, client: TestClient, admin: User):
        sign_in(client, admin.email, ADMIN_PASSWORD)

        assert client.get("/api/users").status_code == 200

    def test_admin_routes_reject_anonymous_callers(self, client: TestClient):
        assert client.get("/api/users").status_code == 401

    @pytest.mark.parametrize(
        ("holder", "required", "allowed"),
        [
            (Role.ADMIN, Role.EDITOR, True),
            (Role.APPROVER, Role.EDITOR, True),
            (Role.EDITOR, Role.EDITOR, True),
            (Role.CONTRIBUTOR, Role.EDITOR, False),
            (Role.VIEWER, Role.ADMIN, False),
        ],
    )
    def test_roles_are_cumulative(self, holder: Role, required: Role, allowed: bool):
        assert holder.can_act_as(required) is allowed


class TestUserManagement:
    def test_an_admin_creates_an_account(self, client: TestClient, admin: User):
        sign_in(client, admin.email, ADMIN_PASSWORD)

        response = client.post(
            "/api/users",
            json={
                "email": "editor@example.org",
                "display_name": "Editor",
                "password": USER_PASSWORD,
                "role": "editor",
            },
        )

        assert response.status_code == 201
        assert response.json()["role"] == "editor"

    def test_the_new_account_can_sign_in(self, client: TestClient, admin: User):
        sign_in(client, admin.email, ADMIN_PASSWORD)
        client.post(
            "/api/users",
            json={
                "email": "editor@example.org",
                "display_name": "Editor",
                "password": USER_PASSWORD,
                "role": "editor",
            },
        )
        client.post("/api/auth/logout")

        response = client.post(
            "/api/auth/login", json={"email": "editor@example.org", "password": USER_PASSWORD}
        )

        assert response.status_code == 200

    def test_a_duplicate_address_is_refused(self, client: TestClient, admin: User):
        sign_in(client, admin.email, ADMIN_PASSWORD)

        response = client.post(
            "/api/users",
            json={
                "email": admin.email.upper(),
                "display_name": "Impostor",
                "password": USER_PASSWORD,
            },
        )

        assert response.status_code == 409

    def test_the_last_admin_cannot_be_demoted(self, client: TestClient, admin: User):
        """Otherwise the instance needs database access to recover."""
        sign_in(client, admin.email, ADMIN_PASSWORD)

        response = client.patch(f"/api/users/{admin.id}", json={"role": "viewer"})

        assert response.status_code == 409

    def test_the_last_admin_cannot_be_deactivated(self, client: TestClient, admin: User):
        sign_in(client, admin.email, ADMIN_PASSWORD)

        response = client.patch(f"/api/users/{admin.id}", json={"is_active": False})

        assert response.status_code == 409

    def test_an_admin_can_step_down_once_another_exists(
        self, client: TestClient, admin: User
    ):
        sign_in(client, admin.email, ADMIN_PASSWORD)
        client.post(
            "/api/users",
            json={
                "email": "second.admin@example.org",
                "display_name": "Second Admin",
                "password": USER_PASSWORD,
                "role": "admin",
            },
        )

        response = client.patch(f"/api/users/{admin.id}", json={"role": "editor"})

        assert response.status_code == 200

    def test_updating_an_unknown_account_is_a_404(self, client: TestClient, admin: User):
        sign_in(client, admin.email, ADMIN_PASSWORD)

        response = client.patch(f"/api/users/{uuid.uuid4()}", json={"display_name": "Ghost"})

        assert response.status_code == 404

    def test_the_listing_never_exposes_password_hashes(self, client: TestClient, admin: User):
        sign_in(client, admin.email, ADMIN_PASSWORD)

        body = client.get("/api/users").text

        assert "password_hash" not in body
        assert "$argon2id$" not in body
